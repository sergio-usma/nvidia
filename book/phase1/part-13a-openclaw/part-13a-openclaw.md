# Capítulo 13A — OpenClaw: Bot de Telegram con IA Local en el Jetson AGX Orin

## Introducción

OpenClaw convierte el Jetson AGX Orin en un agente de IA completamente funcional accesible desde **Telegram** — el canal principal de este capítulo. En lugar de un simple chatbot, OpenClaw es un **gateway de agentes** que conecta los modelos LLM locales con el mundo real: búsqueda web, herramientas de sistema, memoria de sesión, ejecución de código y cambio dinámico de backends de inferencia.

**El proyecto de este capítulo:** Construir un bot de Telegram privado, alojado en el Jetson, que responde preguntas, busca en la web, analiza archivos y cambia automáticamente de modelo según la tarea — todo sin enviar datos a servicios externos. Este mismo bot puede monetizarse dando acceso a terceros via allowlist.

Este capítulo cubre únicamente OpenClaw. Para NemoClaw (capa de seguridad), consulte el Capítulo 13B. Para Open WebUI con SSL, el Capítulo 14.

> **Prerrequisito:** Al menos un motor de inferencia activo del Capítulo anterior antes de iniciar OpenClaw. Sin modelo respondiendo en el puerto configurado, el gateway arranca pero no puede generar respuestas.

**Modo energético recomendado:** 30W (`pwr-30w`) para el gateway en reposo. Cambie a MAXN (`pwr-maxn` + `sudo jetson_clocks`) cuando active el motor de inferencia para tareas intensivas.

---

## 13A.1 Arquitectura de OpenClaw en JetPack 7.2

<!-- INFOGRAFÍA: Arquitectura de OpenClaw en JetPack 7.2 — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


```
Arquitectura OpenClaw — Jetson AGX Orin 64GB (JP 7.2)
══════════════════════════════════════════════════════

Canales de entrada               Jetson AGX Orin 64GB
─────────────────                ───────────────────────────────────────────
  Telegram Bot  [PRIMARY] ────→  OpenClaw Gateway  :18789 (loopback)
  WhatsApp App  [OPCIONAL] ───→      |  (SSH tunnel desde Windows)
  Navegador Web (WebUI)   ────→      |
  Terminal TUI            ────→      |
                                     v  (router de solicitudes + tools)
                              +──────────────────────────────────────+
                              |  Herramientas disponibles:          |
                              |  - Busqueda web (Brave Search API)  |
                              |  - Sistema de archivos              |
                              |  - Ejecucion de codigo Python       |
                              |  - Memoria de sesion                |
                              +──────────────────────────────────────+
                                     |
                                     v  (backend activo, uno a la vez)
                              +──────────────────────────────────────+
                              |  vLLM :8000  llama.cpp :8080        |
                              |  Ollama :11434                      |
                              +──────────────────────────────────────+
                                     |
                              Modelo activo (gemma4-E4B, qwen35...)
                              ~1-3 segundos @ 30W, datos 100% locales
```

OpenClaw actúa como un router inteligente: recibe la solicitud del canal de entrada (Telegram en este capítulo), la enruta al backend de inferencia correcto, ejecuta las herramientas que el modelo solicita (búsqueda web, código) y entrega la respuesta. **Un solo modelo puede estar activo a la vez** (memoria unificada 64 GB).

---

## 13A.2 Prerrequisitos

### 13A.2.1 Node.js v22

OpenClaw requiere Node.js v22. JetPack 7.2 puede incluirlo, pero verifique antes de instalar:

```bash
# Verificar Node.js
node --version
npm --version
```

```
# Salida esperada:
v22.23.1
10.9.x
```

```bash
# Si Node.js no está disponible o es una versión <20:
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar instalación (tarda ~2 minutos)
node --version   # v22.23.1
npm --version    # 10.x.x
```

> **IMPORTANTE:** No use el Node.js del repositorio de Ubuntu 24.04 (`apt install nodejs` sin NodeSource). Ese paquete instala la versión 18.x, incompatible con OpenClaw.

### 13A.2.2 Motor de inferencia activo

OpenClaw necesita un modelo respondiendo en el momento de arranque del gateway. Verifique antes de continuar:

```bash
# Verificar que al menos un motor de inferencia está activo
curl -sf http://localhost:8000/v1/models > /dev/null && echo "[OK] vLLM activo en :8000" \
  || curl -sf http://localhost:8080/v1/models > /dev/null && echo "[OK] llama.cpp activo en :8080" \
  || curl -sf http://localhost:11434/api/tags > /dev/null && echo "[OK] Ollama activo en :11434" \
  || echo "[ERROR] Sin motor activo — inicie uno antes de configurar OpenClaw (ver Capítulo 12)"
```

---

## 13A.3 Instalación de OpenClaw

El instalador oficial verifica la versión de Node, instala el daemon y prepara el onboarding inicial:

```bash
# Método recomendado: instalador oficial
# Tarda 2-3 minutos — descarga el paquete npm y configura el servicio systemd de usuario
curl -fsSL https://openclaw.ai/install.sh | bash
```

```
# Salida esperada al final del instalador:
[OK] OpenClaw 2026.6.10 installed
[OK] Node.js v22.23.1 detected
[OK] Daemon configured as systemd user service
→ Run 'openclaw onboard' to configure your first agent
```

```bash
# Si el comando 'openclaw' no se encuentra después de instalar:
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verificar instalación
openclaw --version
# Esperado: OpenClaw 2026.6.10
```

**Método alternativo (instalación sin script):**

```bash
# Si el instalador oficial falla por restricciones de red
npm install -g openclaw@latest
openclaw onboard --install-daemon

# Verificar
openclaw --version
```

> **Error común — paquete npm incorrecto:** Si ve alguna guía que usa `@openclaw/cli` o `@openshell/cli`, ese nombre de paquete no existe en el registro npm. El nombre correcto es simplemente `openclaw` (sin prefijo `@`).

---

## 13A.4 Configuración de Producción

La configuración reside en `~/.openclaw/openclaw.json`. La siguiente es la configuración completa verificada en producción con todos los parches aplicados.

### 13A.4.1 Generar el Token del Gateway

```bash
# Generar token de seguridad para el gateway
GATEWAY_TOKEN=$(openssl rand -hex 24)
echo "Token generado: $GATEWAY_TOKEN"
# Salida ejemplo: Token generado: a3f7c2e9d4b1a8f6c3d2e5a7b4c9d1e2f3a6b8c4d7e9f2
```

### 13A.4.2 Configuración JSON Completa

```bash
# Hacer backup si existe configuración previa
cp ~/.openclaw/openclaw.json \
   ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Escribir configuración de producción
cat > ~/.openclaw/openclaw.json << EOF
{
  "agents": {
    "defaults": {
      "workspace": "/home/jetson/.openclaw/workspace",
      "models": {
        "vllm/google/gemma-4-E4B-it": {}
      },
      "model": {
        "primary": "vllm/google/gemma-4-E4B-it"
      },
      "compaction": {
        "reserveTokensFloor": 6000
      },
      "timeoutSeconds": 300,
      "memorySearch": {
        "enabled": false
      },
      "bootstrapMaxChars": 20000,
      "bootstrapTotalMaxChars": 150000,
      "contextInjection": "always"
    }
  },
  "gateway": {
    "mode": "local",
    "auth": {
      "mode": "token",
      "token": "${GATEWAY_TOKEN}"
    },
    "port": 18789,
    "bind": "loopback",
    "tailscale": { "mode": "off", "resetOnExit": false },
    "controlUi": { "allowInsecureAuth": true },
    "nodes": {
      "denyCommands": [
        "camera.snap", "camera.clip", "screen.record",
        "contacts.add", "calendar.add", "reminders.add",
        "sms.send", "sms.search"
      ]
    }
  },
  "session": {
    "dmScope": "per-channel-peer"
  },
  "tools": {
    "profile": "full",
    "web": {
      "search": { "provider": "brave", "enabled": true }
    }
  },
  "plugins": {
    "entries": {
      "vllm": { "enabled": true },
      "whatsapp": { "enabled": true },
      "brave": {
        "config": { "webSearch": { "apiKey": "TU_BRAVE_API_KEY" } },
        "enabled": true
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "vllm": {
        "baseUrl": "http://127.0.0.1:8000/v1",
        "api": "openai-completions",
        "apiKey": "vllm-local",
        "timeoutSeconds": 300,
        "models": [
          {
            "id": "google/gemma-4-E4B-it",
            "name": "Gemma 4 E4B (local vLLM)",
            "reasoning": false,
            "input": ["text", "image"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 65536,
            "maxTokens": 4096
          }
        ]
      }
    }
  },
  "auth": {
    "profiles": {
      "vllm:default": { "provider": "vllm", "mode": "api_key" }
    }
  },
  "channels": {
    "whatsapp": {
      "enabled": true,
      "selfChatMode": false,
      "dmPolicy": "pairing"
    }
  },
  "commands": {
    "ownerAllowFrom": ["whatsapp:+57XXXXXXXXXX"]
  },
  "hooks": {
    "internal": {
      "enabled": true,
      "entries": {
        "session-memory": { "enabled": true },
        "boot-md": { "enabled": true },
        "bootstrap-extra-files": { "enabled": true },
        "command-logger": { "enabled": true },
        "compaction-notifier": { "enabled": true }
      }
    }
  }
}
EOF

# Validar JSON
python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null \
  && echo "[OK] Config JSON válida" \
  || echo "[ERROR] Error en JSON — revisar con: python3 -m json.tool ~/.openclaw/openclaw.json"
```

```bash
# Aplicar configuración y arrancar el gateway
openclaw gateway restart
sleep 5
openclaw doctor
```

```
# Salida esperada de 'openclaw doctor':
[OK] Gateway: running on port 18789
[OK] Model: vllm/google/gemma-4-E4B-it (connected)
[OK] Tools profile: full
[OK] WhatsApp: enabled (pending pairing)
```

### 13A.4.3 Tabla de Errores Críticos de Configuración (todos verificados en producción)

| Campo incorrecto | Valor que falla | Valor correcto | Consecuencia |
|-----------------|-----------------|----------------|--------------|
| `tools.profile` | `"default"` | `"full"` | WhatsApp no puede responder mensajes |
| `tools.profile` | `"coding"` | `"full"` | Perfil coding elimina la herramienta de respuesta WhatsApp |
| `models.providers.vllm.apiKey` | `"VLLM_API_KEY"` | `"vllm-local"` | Error de autenticación contra el endpoint local |
| `models.providers.vllm.models[].id` | `"vllm/google/gemma-4-E4B-it"` | `"google/gemma-4-E4B-it"` | El prefijo `vllm/` no va en el campo `id` del modelo |
| `agents.defaults.model.primary` | `"vllm/google/gemma4-E4B-it"` | `"vllm/google/gemma-4-E4B-it"` | El guión en `gemma-4` es obligatorio |
| `models.providers.vllm.models[].maxTokens` | `65536` | `4096` | Si maxTokens == contextWindow, no queda espacio para el input |
| `agents.defaults.memorySearch.enabled` | `true` | `false` | Falla silenciosamente sin API key de OpenAI |

---

## 13A.5 Acceso Web UI desde Windows (Túnel SSH)

El gateway escucha únicamente en `loopback` (127.0.0.1:18789), inaccesible desde la red local por diseño. Para acceder desde Windows se requiere un túnel SSH.

> **ADVERTENCIA:** El túnel SSH se ejecuta **desde Windows** hacia el Jetson, NO al revés. Si lo ejecuta desde el propio Jetson, recibirá `Permission denied (publickey)`.

```powershell
# En Windows PowerShell — mantener esta ventana abierta mientras usa el Web UI
# Reemplazar 192.168.1.100 con la IP de su Jetson
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

Abra en el navegador de Windows:

```
http://localhost:18789/#token=TU_TOKEN_AQUI
```

```bash
# Obtener el token desde el Jetson
openclaw config get gateway.auth.token
# Salida: abc123def456...  (48 caracteres hexadecimales)
```

**Alternativa — NoMachine (más sencilla, sin túnel):**

Si tiene NoMachine instalado (Capítulo 7), conéctese con el cliente NoMachine desde Windows y abra el navegador dentro del escritorio virtual del Jetson:

```
http://127.0.0.1:18789/#token=TU_TOKEN
```

---

## 13A.6 Canal Telegram — Configuración del Bot (Canal Principal)

Telegram es el canal primario de este capítulo. A diferencia de WhatsApp, no requiere vincular un número de teléfono personal — el bot corre con un token independiente y puede atender a múltiples usuarios.

### 13A.6.1 Crear el bot en Telegram

```
# PASO 1: En la app de Telegram, buscar @BotFather y enviar:
/newbot

# BotFather preguntara el nombre y el username:
# Nombre del bot: Jetson AI Assistant
# Username: jetson_tuusuario_bot  (debe terminar en "bot")

# BotFather entregara el token:
# Done! Use this token to access the HTTP API:
# 7123456789:AAGxxxxxxxxxx-xxxxxxxxxxxxxxxxx
#
# IMPORTANTE: reemplaza TU_TOKEN_TELEGRAM_AQUI con este token en el siguiente paso
```

```bash
# PASO 2: Configurar el token en OpenClaw
# IMPORTANTE: reemplaza TU_TOKEN_TELEGRAM_AQUI con el token de @BotFather
openclaw config set channels.telegram.botToken "TU_TOKEN_TELEGRAM_AQUI"
openclaw config set channels.telegram.enabled true

# Politica por defecto: allowlist (solo su cuenta puede hablar con el bot)
# Primero obtenga su Telegram user ID: busque @userinfobot en Telegram y enviele /start
# Salida: Your User ID is 123456789
# IMPORTANTE: reemplaza TU_TELEGRAM_USER_ID con ese numero
openclaw config set channels.telegram.dmPolicy allowlist
openclaw config set channels.telegram.dmAllowFrom '[TU_TELEGRAM_USER_ID]'

# Reiniciar gateway para aplicar
openclaw gateway restart
sleep 3

# Verificar que el canal Telegram esta activo
openclaw channels status --probe
```

```
# Salida esperada:
Telegram default: enabled, configured, linked, running, connected [OK]
```

### 13A.6.2 Probar el bot desde Telegram

```
# En la app de Telegram:
# 1. Buscar su bot por el username (@jetson_tuusuario_bot)
# 2. Enviar /start o cualquier mensaje
# 3. El bot deberia responder en 1-5 segundos

# Mensaje de prueba: "Hola, quien eres?"
# Respuesta esperada: El agente se identifica y confirma que el modelo esta activo
```

```bash
# Ver los mensajes entrantes y respuestas en tiempo real (en el Jetson):
openclaw logs --tail 20 --follow

# Filtrar solo mensajes de Telegram:
openclaw logs --channel telegram --follow
```

### 13A.6.3 Dar acceso a otros usuarios (opcional — monetizacion)

```bash
# Agregar mas usuarios a la allowlist de Telegram
# Cada usuario debe decirle su Telegram user ID via otro canal
# IMPORTANTE: reemplaza los IDs de ejemplo con los reales
openclaw config set channels.telegram.dmAllowFrom '[123456789, 987654321, 456789123]'
openclaw gateway restart
```

> **IDEA DE PROYECTO:** Un bot de Telegram conectado al Jetson puede ofrecerse como servicio a familias, empresas o equipos de trabajo por suscripcion mensual. El Jetson corre 24/7 con 15W en modo idle y se activa el motor de inferencia bajo demanda cuando llega un mensaje. El costo de hardware (~2.000 USD) se amortiza rapidamente con 5-10 suscriptores.

### 13A.6.4 Canal WhatsApp (opcional)

Si prefiere WhatsApp en lugar de (o además de) Telegram, la configuración requiere vincular su número de teléfono:

```bash
# Iniciar asistente de onboarding para WhatsApp
openclaw onboard
# Durante el asistente, seleccionar:
# [x] Channel: WhatsApp
# [x] dmPolicy: pairing
# [x] Search provider: Brave Search

# En el telefono: WhatsApp -> Configuracion -> Dispositivos vinculados -> Vincular dispositivo
# Apuntar la camara al QR que aparece en la terminal del Jetson

# Aprobar el numero del remitente:
openclaw pairing list whatsapp
# Salida: pending  +573XXXXXXXXX  code: A7K2M9
openclaw pairing approve whatsapp A7K2M9

# Verificar:
openclaw channels status --probe
# WhatsApp default: enabled, configured, linked, running, connected [OK]
```

> **NOTA:** WhatsApp requiere que el numero del Jetson este vinculado como "dispositivo adicional" de su cuenta. Si se desconecta (sesion expirada), reautentique con `openclaw channels auth login whatsapp`.

---

## 13A.7 Cambiar el Modelo de Inferencia

Para cambiar el modelo que usa OpenClaw, actualice la configuración y reinicie el gateway:

```bash
# Cambiar a Qwen3.5 35B (si vLLM está sirviendo qwen35 en :8000)
openclaw config set \
  agents.defaults.model.primary "vllm/qwen35" \
  models.providers.vllm.models.0.id "qwen35" \
  models.providers.vllm.models.0.contextWindow 8192

openclaw gateway restart
sleep 3
openclaw doctor | grep "Model:"
# Salida esperada: [OK] Model: vllm/qwen35 (connected)
```

```bash
# Cambiar a llama.cpp (Nemotron Omni en :8080)
openclaw config set \
  agents.defaults.model.primary "llama/nemotron-omni" \
  models.providers.llama.baseUrl "http://127.0.0.1:8080/v1" \
  models.providers.llama.models.0.id "nemotron-omni"

openclaw gateway restart
```

---

## 13A.8 Gestión del Gateway en el Día a Día

```bash
# Estado completo del gateway
openclaw gateway status

# Reiniciar (necesario después de cambiar openclaw.json)
openclaw gateway restart && sleep 3 && openclaw gateway status

# Ver logs en tiempo real
openclaw logs --follow

# Filtrar solo logs de WhatsApp
openclaw logs --follow | grep -i whatsapp

# Filtrar solo errores
openclaw logs --follow | grep -i error

# Interfaz TUI interactiva en la terminal
openclaw tui
# Dentro del TUI: /new → nueva sesión | /compact → compactar contexto | /quit → salir

# Verificar que el modelo responde antes de depurar OpenClaw
curl -s http://localhost:8000/v1/models \
  | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
```

---

## 13A.9 Skills de OpenClaw

Los skills amplían las capacidades del agente con herramientas adicionales.

```bash
# Ver skills instalados
openclaw skills list --verbose

# Verificar estado de todos los skills
openclaw skills check

# Instalar un skill del registro ClawHub
openclaw skills install <nombre-del-skill>

# Skills recomendados para el Jetson:
# jetson-system   → información del hardware, temperatura, modo de energía
# file-manager    → gestión de archivos via chat o WhatsApp
# code-executor   → ejecutar scripts Python desde WhatsApp (usar con precaución)
```

---

## 13A.10 Aliases para el Día a Día

```bash
# Agregar al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── OpenClaw ───────────────────────────────────────────────────────────
alias openclaw-start='openclaw gateway start && sleep 3 && openclaw gateway status'
alias openclaw-stop='openclaw gateway stop'
alias openclaw-restart='openclaw gateway restart && sleep 3 && openclaw doctor'
alias openclaw-status='openclaw gateway status && openclaw channels status'
alias openclaw-logs='openclaw logs --follow'
alias openclaw-doctor='openclaw doctor'
alias openclaw-wa='openclaw channels status --probe | grep -i whatsapp'
EOF

source ~/.bashrc
```

---

## 13A.11 Solución de Problemas

### Error: `model not found` al arrancar el gateway

**Causa:** El backend de inferencia no está activo o el ID del modelo no coincide.

```bash
# Verificar que vLLM está activo y con el modelo correcto
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# Si vLLM no está corriendo, iniciarlo (ver Part 12 o alias start-qwen35/start-nemotron)
start-qwen35   # o el alias correspondiente al modelo configurado

# Reiniciar OpenClaw después de que el modelo esté listo
openclaw gateway restart
```

### Error: `Permission denied` al abrir el Web UI

**Causa:** El túnel SSH se ejecutó desde el Jetson en lugar de desde Windows.

```bash
# INCORRECTO (desde el Jetson):
ssh -N -L 18789:127.0.0.1:18789 localhost   # ← No hacer esto

# CORRECTO (desde Windows PowerShell):
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

### WhatsApp: mensajes sin respuesta del agente

**Causa más común:** El perfil de herramientas no es `"full"`.

```bash
# Verificar el perfil actual
grep '"profile"' ~/.openclaw/openclaw.json

# Si muestra "default", "coding" o cualquier otro valor:
openclaw config set tools.profile full
openclaw gateway restart
```

### Gateway arranca pero no conecta al modelo

```bash
# Verificar URL del backend en la config
python3 -c "
import json
with open('/home/jetson/.openclaw/openclaw.json') as f:
    c = json.load(f)
url = c['models']['providers']['vllm']['baseUrl']
print('Backend URL:', url)
"

# Probar conectividad al backend directamente
curl -sf "$URL/models" && echo "[OK] Backend accesible" || echo "[ERROR] Backend no responde"
```

---

## 13A.12 Modos de Backend — Cambio de Motor de Inferencia

OpenClaw puede conectarse a cualquiera de los tres motores instalados en el Capítulo anterior. Para tareas diferentes, use el backend más apropiado:

| Tarea | Backend recomendado | Comando |
|-------|---------------------|---------|
| Chat rapido, preguntas generales | Ollama (qwen3:8b) | `mode-ollama` |
| Agente con tool calling (por defecto) | vLLM + Gemma 4 E2B | `mode-vllm` |
| Bajo consumo, modo nocturno | llama.cpp + Gemma 4 E2B GGUF | `mode-lite` |
| Documentos largos (256K+ contexto) | vLLM + Nemotron3 30B | `mode-longdoc` |
| Audio, video, multimodal | llama.cpp + Nemotron Omni | `mode-multimodal` |

### 13A.12.1 Script de cambio de backend

Guarde este script en `~/scripts/switch-model.sh`:

```bash
cat > ~/scripts/switch-model.sh << 'EOF'
#!/usr/bin/env bash
# switch-model.sh -- Cambia el backend de inferencia de OpenClaw
# Uso: switch-model.sh [vllm-gemma|lite-gemma|longdoc|multimodal|ollama|stop]
set -euo pipefail

MODE=${1:-help}
GATEWAY_URL="http://localhost:18789"

stop_all_backends() {
  echo "Deteniendo backends activos..."
  pkill -f "llama-server" 2>/dev/null || true
  docker stop vllm-container 2>/dev/null || true
  pkill -f "ollama serve" 2>/dev/null || true
  sudo systemctl stop ollama 2>/dev/null || true
  sleep 2
  echo "[OK] Backends detenidos"
}

wait_backend() {
  local url=$1
  local name=$2
  echo -n "Esperando $name..."
  for i in $(seq 1 60); do
    curl -sf "$url" > /dev/null 2>&1 && { echo " [OK]"; return 0; }
    sleep 5; echo -n "."
  done
  echo " [ERROR] Timeout esperando $name"
  return 1
}

case "$MODE" in
  vllm-gemma)
    echo "=== Modo: vLLM + Gemma 4 E2B (tool calling, 128K contexto) ==="
    sudo nvpmodel -m 2 && echo "Modo 30W activado"
    stop_all_backends
    docker-on
    docker run -d --name vllm-container --rm --runtime nvidia --network host \
      -v $HOME/.cache/huggingface:/root/.cache/huggingface \
      vllm/vllm-openai:v0.22.0-ubuntu2404 \
      --model google/gemma-3-4b-it \
      --host 0.0.0.0 --port 8000 \
      --api-key "${VLLM_API_KEY:-vllm-local}" \
      --max-model-len 8192 --gpu-memory-utilization 0.85
    wait_backend "http://localhost:8000/v1/models" "vLLM"
    openclaw config set agents.defaults.model.primary "vllm/gemma4-e2b"
    openclaw gateway restart
    echo "[OK] OpenClaw -> vLLM (Gemma 4 E2B) en :8000"
    ;;
  lite-gemma)
    echo "=== Modo: llama.cpp + Gemma 4 E2B GGUF (liviano, bajo consumo) ==="
    sudo nvpmodel -m 2 && echo "Modo 30W activado"
    stop_all_backends
    GGUF=$(ls ~/data/models/gguf/gemma*.gguf 2>/dev/null | head -1)
    [ -z "$GGUF" ] && { echo "[ERROR] No se encontro GGUF de Gemma en ~/data/models/gguf/"; exit 1; }
    ~/llama.cpp/build/bin/llama-server \
      -m "$GGUF" \
      --host 0.0.0.0 --port 8080 \
      -c 32768 -n -1 -ngl 999 --flash-attn &
    wait_backend "http://localhost:8080/health" "llama.cpp"
    openclaw config set agents.defaults.model.primary "llamacpp/gemma4-e2b"
    openclaw gateway restart
    echo "[OK] OpenClaw -> llama.cpp (Gemma 4 E2B) en :8080"
    ;;
  longdoc)
    echo "=== Modo: vLLM + Nemotron3 30B (documentos largos, 256K contexto) ==="
    sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MAXN activado"
    stop_all_backends
    docker-on
    docker run -d --name vllm-container --rm --runtime nvidia --network host \
      -v $HOME/.cache/huggingface:/root/.cache/huggingface \
      vllm/vllm-openai:v0.22.0-ubuntu2404 \
      --model nvidia/Nemotron-3-30B-A3B-Instruct \
      --host 0.0.0.0 --port 8000 \
      --api-key "${VLLM_API_KEY:-vllm-local}" \
      --max-model-len 32768 --gpu-memory-utilization 0.95
    wait_backend "http://localhost:8000/v1/models" "vLLM Nemotron3"
    openclaw config set agents.defaults.model.primary "vllm/nemotron3"
    openclaw gateway restart
    echo "[OK] OpenClaw -> vLLM (Nemotron3 30B) en :8000 -- MAXN activo"
    ;;
  ollama)
    echo "=== Modo: Ollama (rapido, sin contenedor) ==="
    sudo nvpmodel -m 2 && echo "Modo 30W activado"
    stop_all_backends
    sudo systemctl start ollama
    wait_backend "http://localhost:11434/api/tags" "Ollama"
    openclaw config set agents.defaults.model.primary "ollama/qwen3:8b"
    openclaw gateway restart
    echo "[OK] OpenClaw -> Ollama (qwen3:8b) en :11434"
    ;;
  stop)
    echo "=== Deteniendo todo y volviendo a modo idle ==="
    openclaw gateway stop 2>/dev/null || true
    stop_all_backends
    sudo nvpmodel -m 3 && echo "Modo 15W activado"
    docker-off 2>/dev/null || true
    echo "[OK] Sistema en idle 15W -- solo SSH activo"
    ;;
  *)
    echo "Uso: switch-model.sh [vllm-gemma|lite-gemma|longdoc|ollama|stop]"
    echo ""
    echo "  vllm-gemma   vLLM + Gemma 4 E2B (30W, tool calling, defecto)"
    echo "  lite-gemma   llama.cpp + Gemma 4 E2B GGUF (30W, rapido, bajo consumo)"
    echo "  longdoc      vLLM + Nemotron3 30B (MAXN, 256K contexto)"
    echo "  ollama       Ollama (30W, sin Docker, qwen3:8b)"
    echo "  stop         Detener todo, volver a 15W idle"
    ;;
esac
EOF

chmod +x ~/scripts/switch-model.sh
```

```bash
# Aliases para el cambio de modo (agregar a ~/.bash_aliases)
alias mode-vllm='~/scripts/switch-model.sh vllm-gemma'
alias mode-lite='~/scripts/switch-model.sh lite-gemma'
alias mode-longdoc='~/scripts/switch-model.sh longdoc'
alias mode-ollama='~/scripts/switch-model.sh ollama'
alias mode-stop='~/scripts/switch-model.sh stop'
```

```bash
source ~/.bash_aliases || source ~/.bashrc

# Ejemplo de uso:
mode-vllm      # Activar vLLM + Gemma (modo por defecto para Telegram bot)
mode-stop      # Liberar toda la RAM (15W idle)
```

---

## 13A.13 Plugins de OpenClaw (ClawHub)

OpenClaw tiene un registro de plugins (ClawHub) con skills adicionales que amplian las capacidades del agente:

```bash
# Ver plugins disponibles
openclaw skills list --registry

# Instalar el plugin de informacion del Jetson
openclaw skills install jetson-system
# El agente puede responder: "Cual es la temperatura del Jetson?"
# "Cuanta RAM disponible hay?" "En que modo de energia estamos?"

# Instalar gestor de archivos (acceso a ~/data/ via chat)
openclaw skills install file-manager

# Instalar ejecutor de codigo Python (PRECAUCION: da al agente acceso de ejecucion)
openclaw skills install code-executor

# Ver plugins instalados y su estado
openclaw skills status

# Recargar plugins sin reiniciar el gateway
openclaw skills reload
```

> **ADVERTENCIA:** El plugin `code-executor` permite al agente ejecutar codigo Python arbitrario. Use la capa de seguridad de NemoClaw (Capitulo 13B) antes de habilitarlo si comparte el bot con otros usuarios.

---

## Resumen del Capítulo 13A

OpenClaw transforma el Jetson en un agente de IA accesible desde Telegram. Los puntos criticos de la configuracion son:

- `tools.profile` debe ser `"full"` — cualquier otro valor limita las capacidades del agente
- El campo `models.providers.vllm.models[].id` no lleva el prefijo `vllm/` — ese va en `agents.defaults.model.primary`
- `memorySearch.enabled` debe ser `false` a menos que tenga una API key de OpenAI configurada
- El gateway escucha en loopback `:18789` — acceda desde Windows solo via tunel SSH
- Telegram es el canal primario (no requiere vincular numero personal), WhatsApp es opcional

El siguiente capitulo (13B) cubre NemoClaw — la capa de seguridad L7 que envuelve a OpenClaw con politicas de red y aislamiento del sistema de archivos, indispensable antes de dar acceso a terceros.
