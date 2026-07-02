# Capítulo 30 — Microservicios y Despliegue SAAS: Exponer el Jetson a Internet

## Introducción

Los capítulos anteriores construyeron los servicios del Jetson para uso local: LLMs, STT, TTS, agentes, automatización. Este capítulo los expone a internet de forma segura, convirtiendo el Jetson AGX Orin en un servidor de IA-as-a-Service (AIaaS) accesible desde cualquier dispositivo del mundo sin necesidad de IP pública estática.

**Lo que se construirá:**

<!-- INFOGRAFÍA: Arquitectura AIaaS sobre Jetson AGX Orin — flujo desde cliente en internet hasta servicios de IA internos: Cloudflare Tunnel → Cloudflared → Nginx reverse proxy → JWT middleware → vLLM / STT / TTS / OpenClaw / N8N / Open WebUI, con indicación de puertos y capas de seguridad — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->

```
Internet (cliente)
    ↓ HTTPS (Cloudflare Tunnel — sin abrir puertos en el router)
Cloudflared daemon (Jetson) → Nginx reverse proxy
    ↓ /api/llm   → vLLM :8000
    ↓ /api/stt   → faster-whisper :8000
    ↓ /api/tts   → kokoro-tts :8880
    ↓ /api/agent → OpenClaw :18789
    ↓ /n8n       → N8N :5678
    ↓ /          → Open WebUI :3000
    ↓ JWT middleware → autenticación por cliente
```

**Presupuesto de recursos del stack de infraestructura:**

| Componente | RAM | CPU |
|-----------|-----|-----|
| Nginx (proxy) | ~50 MB | <1% |
| Cloudflared | ~30 MB | <0.5% |
| JWT middleware (FastAPI) | ~80 MB | <1% |
| Uptime Kuma (monitoreo) | ~150 MB | <1% |
| **Total infraestructura** | **~310 MB** | **~3%** |

El overhead de infraestructura es mínimo — no afecta los modelos de IA.

**Modo energético:** 30W base. MAXN solo cuando el LLM procese una petición activa.

**Prerrequisito:** Cuenta de Cloudflare (gratuita) con un dominio propio (o el subdominio `*.trycloudflare.com` gratuito para pruebas).

---

## 30.1 Nginx como Reverse Proxy

Nginx actúa como el único punto de entrada al Jetson. Enruta las peticiones al servicio correcto según la ruta URL y aplica cabeceras de seguridad globales.

### 30.1.1 Instalar Nginx

```bash
sudo apt update
sudo apt install -y nginx

# Verificar instalación
nginx -v
```

```
# Salida esperada
nginx version: nginx/1.24.x (Ubuntu)
```

```bash
# Detener el servicio por defecto (lo gestionaremos manualmente)
sudo systemctl stop nginx
sudo systemctl disable nginx
echo "[OK] Nginx instalado, gestionado bajo demanda"
```

### 30.1.2 Configuración del Reverse Proxy

```bash
# Crear la configuración para el Jetson AI gateway
sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

sudo tee /etc/nginx/sites-available/jetson-ai << 'NGINX_EOF'
# Jetson AGX Orin — AI Gateway Reverse Proxy
# Puerto 80 → redirige a HTTPS (Cloudflare termina TLS, Nginx recibe HTTP local)

limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=llm_limit:10m rate=2r/s;

server {
    listen 8088;                    # Puerto local (Cloudflare apunta aquí)
    server_name _;

    # ── Seguridad global ─────────────────────────────────────
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    client_max_body_size 100M;      # Permite subir archivos de audio grandes
    proxy_read_timeout 300s;        # LLMs pueden tardar en responder
    proxy_connect_timeout 10s;

    # ── Open WebUI (interfaz principal) ─────────────────────
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";  # WebSocket para chat streaming
    }

    # ── vLLM API (LLM inference) ─────────────────────────────
    location /api/llm/ {
        limit_req zone=llm_limit burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_buffering off;        # Streaming de tokens sin buffering
    }

    # ── llama.cpp (llm alternativo) ──────────────────────────
    location /api/llm-cpp/ {
        limit_req zone=llm_limit burst=3 nodelay;
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    # ── faster-whisper STT ───────────────────────────────────
    location /api/stt/ {
        limit_req zone=api_limit burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 100M;  # Archivos de audio pueden ser grandes
    }

    # ── kokoro-tts ───────────────────────────────────────────
    location /api/tts/ {
        limit_req zone=api_limit burst=10 nodelay;
        proxy_pass http://127.0.0.1:8880/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # ── OpenClaw Agent Gateway ────────────────────────────────
    location /api/agent/ {
        limit_req zone=api_limit burst=5 nodelay;
        proxy_pass http://127.0.0.1:18789/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # ── N8N Workflows ────────────────────────────────────────
    location /n8n/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://127.0.0.1:5678/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # ── Health check (para Uptime Kuma y Cloudflare) ─────────
    location /health {
        return 200 '{"status":"ok","host":"jetson-agx-orin"}';
        add_header Content-Type application/json;
    }

    # ── Bloquear acceso directo a endpoints internos ─────────
    location ~ ^/(v1|metrics|openapi) {
        return 403 '{"error":"Acceso directo no permitido"}';
        add_header Content-Type application/json;
    }
}
NGINX_EOF

# Activar la configuración
sudo ln -sf /etc/nginx/sites-available/jetson-ai /etc/nginx/sites-enabled/jetson-ai
sudo rm -f /etc/nginx/sites-enabled/default

# Verificar la configuración
sudo nginx -t
```

```
# Salida esperada
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

```bash
# Iniciar Nginx
sudo systemctl start nginx
echo "[OK] Nginx activo en puerto 8088"

# Verificar que responde
curl -s http://localhost:8088/health | python3 -m json.tool
```

```json
{
    "status": "ok",
    "host": "jetson-agx-orin"
}
```

---

## 30.2 Autenticación JWT con FastAPI

El middleware JWT protege los endpoints de la API. Cada cliente recibe un token único; el middleware lo verifica antes de pasar la petición al servicio correspondiente.

### 30.2.1 Instalar Dependencias

```bash
#
source ~/venvs/llm/bin/activate
pip install fastapi uvicorn python-jose[cryptography] python-multipart httpx
```

### 30.2.2 Servidor de Autenticación JWT

```python
#!/usr/bin/env python3
"""
jwt_gateway.py — Middleware de autenticación JWT para el Jetson AI Gateway
Puerto: 9100 (entre Nginx y los servicios backend)
"""
import os
import time
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import httpx

# ── Configuración ──────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CAMBIAR_POR_VALOR_ALEATORIO_openssl_rand_hex_32")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 30  # 30 días para tokens de cliente
CLIENTS_FILE = Path.home() / "scripts" / "gateway" / "clients.json"

app = FastAPI(title="Jetson AI Gateway Auth", docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ── Gestión de clientes ───────────────────────────────────────────────────
def cargar_clientes() -> dict:
    if CLIENTS_FILE.exists():
        return json.loads(CLIENTS_FILE.read_text())
    return {}

def guardar_clientes(clientes: dict) -> None:
    CLIENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CLIENTS_FILE.write_text(json.dumps(clientes, indent=2, ensure_ascii=False))

def crear_token(client_id: str, scopes: list = None) -> str:
    """Genera un JWT para un cliente específico."""
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    data = {
        "sub": client_id,
        "scopes": scopes or ["llm", "stt", "tts"],
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(token: str) -> dict:
    """Verifica y decodifica un JWT. Lanza excepción si es inválido."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        clientes = cargar_clientes()
        client_id = payload.get("sub")
        if client_id not in clientes:
            raise HTTPException(status_code=401, detail="Cliente no registrado")
        if not clientes[client_id].get("activo", True):
            raise HTTPException(status_code=403, detail="Cliente desactivado")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")

# ── Endpoints de administración ───────────────────────────────────────────
@app.post("/admin/clientes/{client_id}")
async def registrar_cliente(
    client_id: str,
    scopes: list = None,
    admin_key: str = None
):
    """Registra un nuevo cliente y genera su token JWT. Requiere admin_key."""
    expected_key = os.getenv("ADMIN_KEY", "cambiar_esta_clave_admin")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Clave de administrador incorrecta")

    clientes = cargar_clientes()
    token = crear_token(client_id, scopes or ["llm", "stt", "tts"])
    clientes[client_id] = {
        "activo": True,
        "scopes": scopes or ["llm", "stt", "tts"],
        "creado": datetime.now().isoformat(),
        "token_hash": hashlib.sha256(token.encode()).hexdigest()[:16]
    }
    guardar_clientes(clientes)
    return {"client_id": client_id, "token": token, "scopes": scopes}

@app.delete("/admin/clientes/{client_id}")
async def desactivar_cliente(client_id: str, admin_key: str = None):
    """Desactiva un cliente sin borrar su registro."""
    expected_key = os.getenv("ADMIN_KEY", "cambiar_esta_clave_admin")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Clave de administrador incorrecta")

    clientes = cargar_clientes()
    if client_id not in clientes:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    clientes[client_id]["activo"] = False
    guardar_clientes(clientes)
    return {"mensaje": f"Cliente {client_id} desactivado"}

@app.get("/admin/clientes")
async def listar_clientes(admin_key: str = None):
    expected_key = os.getenv("ADMIN_KEY", "cambiar_esta_clave_admin")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Clave de administrador incorrecta")
    clientes = cargar_clientes()
    return {k: {**v, "token_hash": v.get("token_hash", "—")} for k, v in clientes.items()}

# ── Endpoint de verificación (para Nginx auth_request) ───────────────────
@app.get("/auth/verify")
async def verificar_acceso(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Verifica el JWT del header Authorization. Devuelve 200 o 401."""
    payload = verificar_token(credentials.credentials)
    return {"client_id": payload["sub"], "scopes": payload.get("scopes", [])}

# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    clientes = cargar_clientes()
    activos = sum(1 for c in clientes.values() if c.get("activo", True))
    return {"status": "ok", "clientes_activos": activos}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9100, log_level="warning")
```

```bash
# Guardar el script
mkdir -p ~/scripts/gateway
cp /dev/stdin ~/scripts/gateway/jwt_gateway.py << 'HEREDOC'
# (pegar el contenido del script anterior)
HEREDOC

# Configurar variables de entorno
cat > ~/scripts/gateway/.env << 'EOF'
JWT_SECRET_KEY=REEMPLAZAR_CON_openssl_rand_hex_32
ADMIN_KEY=REEMPLAZAR_CON_clave_secreta_administrador
EOF
chmod 600 ~/scripts/gateway/.env

# Iniciar el servidor JWT (en background)
source ~/venvs/llm/bin/activate
source ~/scripts/gateway/.env
nohup python3 ~/scripts/gateway/jwt_gateway.py \
  > ~/logs/jwt_gateway.log 2>&1 &
echo $! > ~/scripts/gateway/jwt_gateway.pid
echo "[OK] JWT Gateway iniciado en :9100 (PID $(cat ~/scripts/gateway/jwt_gateway.pid))"
```

### 30.2.3 Registrar el Primer Cliente

```bash
# Generar claves seguras antes de comenzar
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export ADMIN_KEY=$(openssl rand -hex 16)
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" > ~/scripts/gateway/.env
echo "ADMIN_KEY=$ADMIN_KEY" >> ~/scripts/gateway/.env
echo "[OK] Claves generadas y guardadas"

# Registrar un cliente (por ejemplo, el agente de la agencia)
ADMIN_KEY=$(grep ADMIN_KEY ~/scripts/gateway/.env | cut -d= -f2)
curl -s -X POST "http://localhost:9100/admin/clientes/agencia-turismo" \
  -G \
  --data-urlencode "admin_key=$ADMIN_KEY" \
  --data-urlencode "scopes=llm" \
  --data-urlencode "scopes=stt" \
  | python3 -m json.tool
```

```json
{
    "client_id": "agencia-turismo",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "scopes": ["llm", "stt"]
}
```

```bash
# Verificar que el token funciona
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # ← el token del paso anterior
curl -s http://localhost:9100/auth/verify \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

```json
{
    "client_id": "agencia-turismo",
    "scopes": ["llm", "stt"]
}
```

---

## 30.3 Cloudflare Tunnel: Sin Abrir Puertos en el Router

Cloudflare Tunnel establece una conexión saliente cifrada desde el Jetson hacia la red de Cloudflare. No requiere IP estática, no abre puertos en el router, y el tráfico pasa por HTTPS automáticamente.

### 30.3.1 Instalar cloudflared

```bash
# Descargar el binario ARM64 de cloudflared
curl -L "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" \
  -o /tmp/cloudflared

sudo install -m 755 /tmp/cloudflared /usr/local/bin/cloudflared

# Verificar
cloudflared --version
```

```
# Salida esperada
cloudflared version 2025.x.x (built ...)
```

### 30.3.2 Autenticación con Cloudflare

```bash
# Autenticar con la cuenta de Cloudflare
# Se abrirá una URL — copie y pegue en el navegador de su PC
cloudflared tunnel login
```

```
Please open the following URL and log in with your Cloudflare account:
https://dash.cloudflare.com/argotunnel?callback=...

Leave cloudflared running to download the cert automatically.
You have successfully logged in.
If you wish to copy your credentials to a server, they have been saved to:
/root/.cloudflared/cert.pem
```

### 30.3.3 Crear el Túnel

```bash
# Crear un túnel nombrado
cloudflared tunnel create jetson-ai

# Verificar que se creó
cloudflared tunnel list
```

```
# Salida esperada
ID                                   NAME       CREATED              CONNECTIONS
a1b2c3d4-e5f6-7890-abcd-ef1234567890 jetson-ai  2026-06-29T10:00:00Z 0
```

```bash
# Anotar el ID del túnel (necesario para la configuración)
TUNNEL_ID=$(cloudflared tunnel list --output json | \
  python3 -c "import sys,json; data=json.load(sys.stdin); \
  print(next(t['id'] for t in data if t['name']=='jetson-ai'))")
echo "Tunnel ID: $TUNNEL_ID"
```

### 30.3.4 Configurar el Túnel

```bash
# Crear la configuración del túnel
sudo mkdir -p /etc/cloudflared

sudo tee /etc/cloudflared/config.yml << CLOUDFLARE_EOF
tunnel: $TUNNEL_ID
credentials-file: /root/.cloudflared/$TUNNEL_ID.json

# Reglas de entrada: qué URL pública apunta a qué servicio local
ingress:
  # Open WebUI (interfaz principal)
  - hostname: jetson.sudominio.com        # ← REEMPLAZAR con su dominio
    service: http://localhost:8088         # → Nginx (que luego enruta a Open WebUI)

  # API endpoints con subdominio
  - hostname: api.sudominio.com           # ← REEMPLAZAR con su dominio
    service: http://localhost:8088         # → Nginx (que luego enruta /api/*)

  # Regla catch-all obligatoria al final
  - service: http_status:404
CLOUDFLARE_EOF

echo "[OK] Configuración del túnel creada"
echo "IMPORTANTE: Reemplazar 'sudominio.com' con su dominio real antes de continuar"
```

```bash
# Agregar el registro DNS en Cloudflare (automático)
cloudflared tunnel route dns jetson-ai jetson.sudominio.com
cloudflared tunnel route dns jetson-ai api.sudominio.com

# Verificar la configuración
cloudflared tunnel ingress validate
```

### 30.3.5 Iniciar el Túnel

```bash
# Test manual (ver logs en tiempo real)
cloudflared tunnel run jetson-ai

# En otra terminal, verificar conectividad
curl -s https://jetson.sudominio.com/health
# Debe devolver: {"status":"ok","host":"jetson-agx-orin"}
```

```bash
# Instalar cloudflared como servicio (se inicia automáticamente al arrancar)
sudo cloudflared service install

# NOTA: A diferencia de Docker, cloudflared como servicio del sistema es deseable —
# no consume GPU y es necesario para la conectividad remota permanente.
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# Verificar
systemctl status cloudflared
```

```
# Salida esperada
● cloudflared.service - cloudflared
     Loaded: loaded (/etc/systemd/system/cloudflared.service; enabled)
     Active: active (running) since ...
```

---

## 30.4 Monitoreo con Uptime Kuma

Uptime Kuma es un monitor de disponibilidad self-hosted que alerta cuando un servicio cae. Se ejecuta como contenedor Docker sin GPU.

```bash
# Iniciar Uptime Kuma
docker run -d \
  --name uptime-kuma \
  --restart no \
  -p 127.0.0.1:3001:3001 \
  -v uptime-kuma-data:/app/data \
  louislam/uptime-kuma:1

echo "[OK] Uptime Kuma en http://localhost:3001"
echo "   Acceder via Cloudflare Tunnel: https://monitor.sudominio.com"
```

Una vez accedido a la interfaz web, añadir los siguientes monitores:

| Monitor | URL | Tipo | Intervalo |
|---------|-----|------|-----------|
| Jetson Gateway | `http://localhost:8088/health` | HTTP | 60s |
| JWT Auth | `http://localhost:9100/health` | HTTP | 60s |
| vLLM (cuando activo) | `http://localhost:8000/v1/models` | HTTP | 120s |
| Ollama (cuando activo) | `http://localhost:11434/api/version` | HTTP | 120s |
| faster-whisper (cuando activo) | `http://localhost:8000/health` | HTTP | 60s |
| Cloudflare Tunnel | `https://jetson.sudominio.com/health` | HTTP | 120s |

---

## 30.5 Logging Estructurado y Logrotate

```bash
# Crear directorio de logs centralizado
mkdir -p ~/logs/gateway

# Configurar logrotate para los logs del gateway
sudo tee /etc/logrotate.d/jetson-gateway << 'EOF'
/home/jetson/logs/gateway/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 jetson jetson
    postrotate
        # Reiniciar nginx para reabrir el archivo de log
        /bin/systemctl reload nginx 2>/dev/null || true
    endscript
}
EOF

echo "[OK] Logrotate configurado para ~/logs/gateway/"
```

```bash
# Configurar Nginx para logs estructurados JSON
sudo tee /etc/nginx/conf.d/log_format.conf << 'EOF'
log_format json_combined escape=json
    '{'
        '"timestamp":"$time_iso8601",'
        '"remote_addr":"$remote_addr",'
        '"method":"$request_method",'
        '"uri":"$request_uri",'
        '"status":$status,'
        '"bytes":$body_bytes_sent,'
        '"duration":$request_time,'
        '"user_agent":"$http_user_agent",'
        '"x_forwarded_for":"$http_x_forwarded_for"'
    '}';

access_log /home/jetson/logs/gateway/access.log json_combined;
error_log  /home/jetson/logs/gateway/error.log warn;
EOF

sudo nginx -t && sudo systemctl reload nginx
echo "[OK] Logs JSON activos en ~/logs/gateway/"
```

---

## 30.6 Scripts de Gestión del Gateway

```bash
# Script completo de gestión del gateway
cat > ~/scripts/gateway/gateway-manage.sh << 'EOF'
#!/bin/bash
# gateway-manage.sh — Gestión del stack de infraestructura del Jetson AI Gateway
set -euo pipefail

VENV="$HOME/venvs/llm"
JWT_PID_FILE="$HOME/scripts/gateway/jwt_gateway.pid"
ENV_FILE="$HOME/scripts/gateway/.env"

start_gateway() {
    echo "Iniciando stack de infraestructura..."

    # Nginx
    echo -n "  Nginx..."
    sudo systemctl start nginx
    echo " [OK] (:8088)"

    # JWT Gateway
    echo -n "  JWT Gateway..."
    source "$VENV/bin/activate"
    [ -f "$ENV_FILE" ] && source "$ENV_FILE"
    if ! pgrep -f "jwt_gateway.py" > /dev/null; then
        mkdir -p "$HOME/logs/gateway"
        nohup python3 "$HOME/scripts/gateway/jwt_gateway.py" \
          > "$HOME/logs/gateway/jwt_gateway.log" 2>&1 &
        echo $! > "$JWT_PID_FILE"
        sleep 2
    fi
    echo " [OK] (:9100)"

    # Cloudflare Tunnel (ya debería estar activo como servicio del sistema)
    echo -n "  Cloudflare Tunnel..."
    if systemctl is-active cloudflared &>/dev/null; then
        echo " [OK] (activo como servicio)"
    else
        echo " [WARN]  No activo — ejecute: sudo systemctl start cloudflared"
    fi

    # Uptime Kuma
    echo -n "  Uptime Kuma..."
    if docker ps --format '{{.Names}}' | grep -q "uptime-kuma"; then
        echo " [OK] (:3001)"
    else
        echo " [WARN]  No activo — ejecute: docker start uptime-kuma"
    fi

    echo ""
    echo "[OK] Gateway de infraestructura activo"
    echo "   Interface:   http://$(hostname -I | awk '{print $1}'):8088"
    echo "   JWT Auth:    http://localhost:9100"
    echo "   Monitoring:  http://localhost:3001"
}

stop_gateway() {
    echo "Deteniendo stack de infraestructura..."

    # JWT Gateway
    if [ -f "$JWT_PID_FILE" ]; then
        kill "$(cat "$JWT_PID_FILE")" 2>/dev/null || true
        rm -f "$JWT_PID_FILE"
    fi
    pkill -f "jwt_gateway.py" 2>/dev/null || true
    echo "  [OK] JWT Gateway detenido"

    # Nginx
    sudo systemctl stop nginx
    echo "  [OK] Nginx detenido"

    echo "  [INFO] Cloudflare Tunnel permanece activo (servicio del sistema)"
    echo "  [INFO] Uptime Kuma permanece activo (without restart: no)"
}

status_gateway() {
    echo "═══════════════════════════════════════════════════"
    echo "Estado del Jetson AI Gateway"
    echo "═══════════════════════════════════════════════════"
    echo ""

    # Nginx
    nginx_status=$(systemctl is-active nginx 2>/dev/null || echo "inactivo")
    echo "  Nginx ($nginx_status):"
    [ "$nginx_status" = "active" ] && \
      curl -sf http://localhost:8088/health 2>/dev/null | python3 -m json.tool | \
      sed 's/^/    /' || echo "    [ERROR] No responde"

    # JWT
    echo ""
    echo "  JWT Gateway:"
    jwt_status=$(curl -sf http://localhost:9100/health 2>/dev/null) && \
      echo "    [OK] Activo — $(echo "$jwt_status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"clientes_activos\"]} clientes')")" || \
      echo "    [ERROR] No responde"

    # Cloudflare
    echo ""
    echo "  Cloudflare Tunnel:"
    systemctl is-active cloudflared &>/dev/null && \
      echo "    [OK] Activo" || echo "    [ERROR] Inactivo"

    # Uptime Kuma
    echo ""
    echo "  Uptime Kuma:"
    docker ps --format '{{.Names}} ({{.Status}})' | grep "uptime-kuma" && true || \
      echo "    [ERROR] No activo"
}

logs_gateway() {
    echo "Logs del gateway (Ctrl+C para salir):"
    tail -f "$HOME/logs/gateway/"*.log 2>/dev/null || \
      echo "Sin logs disponibles todavía"
}

case "${1:-help}" in
    start)   start_gateway ;;
    stop)    stop_gateway ;;
    restart) stop_gateway; sleep 2; start_gateway ;;
    status)  status_gateway ;;
    logs)    logs_gateway ;;
    *)       echo "Uso: $0 {start|stop|restart|status|logs}" ;;
esac
EOF

chmod +x ~/scripts/gateway/gateway-manage.sh
```

---

## 30.7 Aliases

```bash
# Agregar al ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── Jetson AI Gateway ────────────────────────────────────────────────
alias start-gateway='~/scripts/gateway/gateway-manage.sh start'
alias stop-gateway='~/scripts/gateway/gateway-manage.sh stop'
alias restart-gateway='~/scripts/gateway/gateway-manage.sh restart'
alias gateway-status='~/scripts/gateway/gateway-manage.sh status'
alias gateway-logs='~/scripts/gateway/gateway-manage.sh logs'
alias gateway-clients='curl -s "http://localhost:9100/admin/clientes?admin_key=$(grep ADMIN_KEY ~/scripts/gateway/.env | cut -d= -f2)" | python3 -m json.tool'
alias new-client='~/scripts/gateway/new-client.sh'
alias uptime-kuma='xdg-open http://localhost:3001 2>/dev/null || echo "Abrir: http://localhost:3001"'
EOF

source ~/.bash_aliases
```

```bash
# Script auxiliar para crear nuevos clientes JWT
cat > ~/scripts/gateway/new-client.sh << 'EOF'
#!/bin/bash
CLIENT_ID="${1:-cliente-nuevo}"
ADMIN_KEY=$(grep ADMIN_KEY ~/scripts/gateway/.env | cut -d= -f2)
echo "Creando cliente: $CLIENT_ID"
curl -s -X POST "http://localhost:9100/admin/clientes/$CLIENT_ID" \
  -G \
  --data-urlencode "admin_key=$ADMIN_KEY" \
  --data-urlencode "scopes=llm" \
  --data-urlencode "scopes=stt" \
  --data-urlencode "scopes=tts" \
  | python3 -m json.tool
EOF
chmod +x ~/scripts/gateway/new-client.sh
```

---

## 30.8 Solución de Problemas

### Nginx: `[emerg] bind() to 0.0.0.0:8088 failed`

```bash
# Ver qué proceso usa el puerto 8088
sudo lsof -i :8088 2>/dev/null | head -5
sudo ss -tlnp | grep 8088

# Si hay otro proceso, cambia el puerto en /etc/nginx/sites-available/jetson-ai
# Buscar "listen 8088" y cambiar por otro puerto libre (ej: 8089)
# También actualizar /etc/cloudflared/config.yml
```

### Cloudflare Tunnel: `ERR_TUNNEL_CONNECTION_FAILED`

```bash
# Verificar estado del servicio
sudo systemctl status cloudflared
sudo journalctl -u cloudflared --since "5 minutes ago" --no-pager

# El error más común: credenciales expiradas — reautenticar
cloudflared tunnel login
sudo systemctl restart cloudflared
```

### JWT Gateway: `address already in use :9100`

```bash
# Ver qué tiene el puerto 9100
sudo lsof -i :9100

# Matar el proceso anterior si quedó huérfano
pkill -f "jwt_gateway.py" || true
sleep 2
source ~/venvs/llm/bin/activate && source ~/scripts/gateway/.env
nohup python3 ~/scripts/gateway/jwt_gateway.py \
  > ~/logs/gateway/jwt_gateway.log 2>&1 &
```

### Cliente recibe `403 Forbidden` desde Nginx

```bash
# Verificar que el token JWT es válido
TOKEN="su_token_aqui"
curl -v http://localhost:9100/auth/verify \
  -H "Authorization: Bearer $TOKEN"

# Si responde 200: el problema es la regla de Nginx (revisar location blocks)
# Si responde 401/403: el token expiró o el cliente está desactivado

# Verificar estado del cliente en la base de datos
curl -s "http://localhost:9100/admin/clientes?admin_key=$(grep ADMIN_KEY ~/scripts/gateway/.env | cut -d= -f2)"
```

---

## 30.9 Cómo Revertir Esta Configuración

Si necesita deshacer la exposición a internet y volver al acceso solo local:

```bash
# 1. Detener y deshabilitar Cloudflare Tunnel
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared
echo "[OK] Cloudflare Tunnel desactivado — el Jetson ya no es accesible desde internet"

# 2. Detener Nginx
sudo systemctl stop nginx
sudo systemctl disable nginx

# 3. Detener JWT Gateway
pkill -f "jwt_gateway.py" 2>/dev/null || true

# 4. (Opcional) Cerrar el túnel en Cloudflare
# Entrar a dash.cloudflare.com → Zero Trust → Tunnels → Eliminar el túnel

# 5. Verificar que no hay puertos expuestos al exterior
sudo ufw status
# Solo deben aparecer los puertos 22 (SSH) y 4000 (NoMachine) como permitidos

# 6. Revertir UFW si se añadieron reglas para este capítulo
# sudo ufw delete allow 8088/tcp
# sudo ufw delete allow 9100/tcp

echo "[OK] Jetson en modo local — accesible solo vía SSH (ssh jetson)"
```

> **NOTA de seguridad:** Mientras Cloudflare Tunnel esté activo (`systemctl is-active cloudflared`), sus servicios son accesibles desde internet. Verifique siempre el estado del túnel antes de iniciar los motores de inferencia.

---

## 30.10 Ciberseguridad — Buenas Prácticas y Lista de Verificación

Exponer el Jetson a internet introduce riesgos reales si la configuración no se hace correctamente. Esta sección consolida las prácticas de seguridad esenciales para este despliegue.

### 30.10.1 Puertos que NUNCA deben ser accesibles desde internet

Los servicios de IA deben ser accesibles **únicamente a través de Nginx**, no directamente desde internet:

```bash
# Verificar que los servicios internos NO están expuestos externamente
# Estos puertos deben estar BLOQUEADOS en el router y en UFW:
echo "══ Puertos internos (deben ser locales únicamente) ══"
for puerto in 8000 11434 18789 5678 3000 8880 8888 9100; do
    netstat -tlnp 2>/dev/null | grep ":$puerto " \
      && echo "  [LOCAL] Puerto $puerto — verificar que no pasa por Cloudflare Tunnel directamente"
done

# Verificar que UFW bloquea acceso directo desde red externa
sudo ufw status verbose | grep -E "8000|11434|18789|5678|3000|8880"
```

**Reglas UFW para proteger los servicios internos:**

```bash
# Denegar acceso directo a los servicios de IA desde redes externas
# (Cloudflare Tunnel conecta por salida, no entrada — no requiere puertos abiertos)
sudo ufw deny in from any to any port 8000    # vLLM — solo via /api/llm
sudo ufw deny in from any to any port 11434   # Ollama — solo via /api/llm
sudo ufw deny in from any to any port 18789   # OpenClaw — solo via /api/agent
sudo ufw deny in from any to any port 5678    # N8N — solo via /n8n
sudo ufw deny in from any to any port 3000    # Open WebUI — solo via /
sudo ufw deny in from any to any port 8880    # kokoro-tts — solo via /api/tts
sudo ufw deny in from any to any port 9100    # JWT FastAPI — solo acceso interno

# Permitir solo el puerto de Nginx y SSH
sudo ufw allow 8088/tcp comment "Nginx — Cloudflare apunta aquí"
sudo ufw allow 22/tcp comment "SSH"
sudo ufw enable

sudo ufw status verbose
```

> **IMPORTANTE:** Cloudflare Tunnel establece conexiones **salientes** desde el Jetson hacia la red de Cloudflare. No requiere abrir ningún puerto en el router. Si tiene reglas de port-forwarding previas en el router, elimínelas.

### 30.10.2 Autenticación — Nunca deje endpoints sin protección

Todos los endpoints expuestos a internet deben requerir JWT. Verifique que ninguno responde sin token:

```bash
# Prueba: intentar acceder a /api/llm sin token — debe devolver 401
curl -s -o /dev/null -w "%{http_code}" https://jetson.sudominio.com/api/llm/v1/models
# Salida esperada: 401

# Prueba: intentar acceder a /n8n sin token — debe devolver 401 o redirigir a login
curl -s -o /dev/null -w "%{http_code}" https://jetson.sudominio.com/n8n/
# Salida esperada: 302 (redirect a login de N8N) o 401
```

### 30.10.3 Certificados SSL — Alternativas Gratuitas

Cloudflare Tunnel gestiona el SSL del tráfico entre el cliente y Cloudflare automáticamente. Para servicios internos o acceso directo por IP (ej. desde la LAN), use certificados gratuitos:

**Opción A — mkcert (para LAN / desarrollo):**

```bash
# Instalar mkcert (ver también §13C.11 — Open WebUI)
sudo apt install -y libnss3-tools
curl -Lo /usr/local/bin/mkcert https://dl.filippo.io/mkcert/latest?for=linux/arm64
chmod +x /usr/local/bin/mkcert
mkcert -install

# Generar certificado para el Jetson en LAN
mkcert jetson.local "192.168.*.* " localhost
# Genera: jetson.local+1.pem y jetson.local+1-key.pem
```

**Opción B — Let's Encrypt (para dominio público, certbot):**

```bash
# Solo si el Jetson tiene IP pública y un dominio DNS configurado
# (No aplica si usa Cloudflare Tunnel — Cloudflare gestiona el TLS)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d jetson.sudominio.com --non-interactive --agree-tos -m admin@sudominio.com

# Renovación automática (añadir al crontab del sistema)
echo "0 3 * * 0 root certbot renew --quiet" | sudo tee /etc/cron.d/certbot-renew
```

**Opción C — ZeroSSL (alternativa gratuita a Let's Encrypt):**

```bash
# ZeroSSL ofrece 3 certificados SSL gratuitos de 90 días
# Registro en: https://zerossl.com/
# Genera un certificado wildcard con validación DNS via panel web
# Descarga los archivos .crt y .key e instálalos en Nginx
```

> **CONSEJO:** Si usa Cloudflare Tunnel, el SSL público está gestionado por Cloudflare y no necesita Let's Encrypt ni ZeroSSL para el acceso externo. Use mkcert únicamente para acceso seguro dentro de la LAN.

### 30.10.4 Rotación de Secretos

Los tokens y secretos deben rotarse periódicamente:

```bash
# Rotar la clave secreta del JWT cada 90 días
# (Script de rotación — añadir a crontab o ejecutar manualmente)

NEW_SECRET=$(openssl rand -hex 32)
echo "Nuevo JWT_SECRET: $NEW_SECRET"
echo ""
echo "Actualizar en:"
echo "  1. ~/projects/jwt-auth/auth_service.py  (linea JWT_SECRET)"
echo "  2. ~/.bash_aliases  (export JWT_SECRET=...)"
echo "  3. Reiniciar el servicio JWT: sudo systemctl restart jwt-auth"
```

### 30.10.5 Lista de Verificación de Seguridad

Antes de dejar el Jetson expuesto a internet de forma permanente, verifique cada punto:

```bash
echo "══ Lista de Verificación de Seguridad — Capítulo 30 ══"

# 1. Cloudflare Tunnel activo
systemctl is-active cloudflared > /dev/null 2>&1 \
  && echo "  [OK] Cloudflare Tunnel activo" \
  || echo "  [WARN] Cloudflare Tunnel no está corriendo"

# 2. JWT middleware activo
curl -sf http://localhost:9100/health > /dev/null \
  && echo "  [OK] JWT middleware respondiendo" \
  || echo "  [WARN] JWT middleware no activo"

# 3. Nginx activo
systemctl is-active nginx > /dev/null 2>&1 \
  && echo "  [OK] Nginx activo" \
  || echo "  [WARN] Nginx no está corriendo"

# 4. Verificar que /api/llm requiere autenticación
CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/llm/v1/models)
[ "$CODE" = "401" ] \
  && echo "  [OK] /api/llm requiere autenticación (401)" \
  || echo "  [WARN] /api/llm responde $CODE — verificar JWT middleware"

# 5. UFW activo
sudo ufw status | grep -q "Status: active" \
  && echo "  [OK] UFW activo" \
  || echo "  [WARN] UFW inactivo — ejecutar: sudo ufw enable"

echo "══════════════════════════════════════════════════════"
```

---

## Resumen del Capítulo

El Jetson AGX Orin es ahora un servidor de IA accesible desde internet con arquitectura de producción:

- **Nginx** como punto de entrada único (puerto 8088), enruta `/api/llm`, `/api/stt`, `/api/tts`, `/api/agent`, `/n8n` y `/` hacia los servicios correctos
- **Rate limiting** integrado en Nginx: 10 peticiones/segundo para API general, 2/segundo para LLM (protege contra abuso)
- **JWT FastAPI** (puerto 9100) gestiona clientes, genera tokens y los valida — cada cliente recibe su token único
- **Cloudflare Tunnel** expone todo al internet sin IP pública ni puertos abiertos en el router
- **Uptime Kuma** monitorea disponibilidad y envía alertas cuando un servicio cae
- **Logs JSON** estructurados con logrotate diario, rotación 7 días

El siguiente capítulo (Capítulo 31) ensambla todo lo construido en los capítulos anteriores en un **Capstone de Agencia de IA**: frontend web Flask, agentes OpenClaw, automatización N8N y facturación conceptual, todo operando como un SAAS funcional desde el Jetson.
