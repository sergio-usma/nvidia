# Capítulo 27 — N8N: Automatización de Flujos de Trabajo con IA Local

## Introducción

N8N es una plataforma de automatización de flujos de trabajo de código abierto que corre en el Jetson AGX Orin 64GB sin ninguna dependencia de la nube. A diferencia de Zapier o Make, N8N se ejecuta completamente en su dispositivo: los datos no salen de su red local, no hay límites de ejecuciones y puede conectar directamente los motores de inferencia locales (vLLM, Ollama, llama.cpp) con cualquier servicio externo.

La propuesta de valor en el contexto del Jetson es clara: N8N actúa como el *orquestador de macroprocesos*, mientras que OpenClaw o el modelo LLM actúa como el *cerebro de razonamiento*. Un flujo típico es: webhook entrante → llamada al modelo local → procesamiento del resultado → acción (email, Slack, base de datos, otro servicio web).

**Presupuesto de memoria para este capítulo:**

| Componente | RAM estimada |
|-----------|-------------|
| OS base JetPack 7.2 | ~12 GB |
| N8N container | ~400 MB |
| PostgreSQL container | ~200 MB |
| **Total N8N stack** | **~12.6 GB** |
| + Ollama con Qwen3:7B | +8 GB = ~20.6 GB |
| + vLLM con Qwen3.5-4B | +5 GB = ~17.6 GB |

**Modo energético:** 30W (`pwr-30w`) — N8N es CPU-bound entre llamadas al LLM. Solo cuando el modelo LLM esté activo generando tokens necesitará el modo apropiado para ese modelo.

> **Prerrequisito:** Docker activo (`docker-on`) y un motor de inferencia iniciado (Capítulo 12). N8N puede orquestar llamadas a Ollama, vLLM o llama.cpp desde nodos HTTP.

---

## 27.1 Compatibilidad ARM64 con JetPack 7.2

Antes de instalar, verifique que la imagen oficial de N8N tiene soporte para ARM64 (arquitectura del Jetson):

```bash
# Verificar soporte ARM64 de la imagen n8n
docker-on
docker pull n8nio/n8n:latest

# Verificar arquitectura de la imagen descargada
docker inspect n8nio/n8n:latest | python3 -c \
  "import sys,json; img=json.load(sys.stdin)[0]; print('Arquitectura:', img['Architecture'], img['Os'])"
```

```
# Salida esperada:
Arquitectura: arm64 linux
```

```bash
# Verificar también la imagen de PostgreSQL
docker pull postgres:16-alpine
docker inspect postgres:16-alpine | python3 -c \
  "import sys,json; img=json.load(sys.stdin)[0]; print('PostgreSQL arquitectura:', img['Architecture'])"
```

```
# Salida esperada:
PostgreSQL arquitectura: arm64
```

> **NOTA:** Ambas imágenes (`n8nio/n8n` y `postgres:16-alpine`) tienen compilaciones oficiales para ARM64. No hay problema de compatibilidad con el Jetson AGX Orin.

---

## 27.2 Instalación con Docker Compose

N8N requiere una base de datos persistente para guardar flujos, credenciales y ejecuciones. PostgreSQL es la opción recomendada sobre SQLite para entornos de producción.

### 27.2.1 Crear el Directorio y el Archivo Compose

```bash
# Crear directorio de trabajo para N8N
mkdir -p ~/stacks/n8n/{data,postgres-data,local-files}
# ~/stacks/ es el directorio estándar para todos los Docker Compose del Jetson (ver §8.6)
cd ~/stacks/n8n
```

```bash
# Generar una clave de cifrado segura para N8N
N8N_ENCRYPTION_KEY=$(openssl rand -hex 24)
echo "Clave generada: $N8N_ENCRYPTION_KEY"
# Guardar este valor — se usará en el archivo .env
```

```bash
# Crear archivo de variables de entorno
cat > ~/stacks/n8n/.env << EOF
# N8N Configuration
N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
WEBHOOK_URL=http://$(hostname -I | awk '{print $1}'):5678/

# PostgreSQL
POSTGRES_DB=n8n
POSTGRES_USER=n8n_user
POSTGRES_PASSWORD=$(openssl rand -hex 16)
POSTGRES_HOST=postgres

# N8N → PostgreSQL
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n_user
DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD:-$(openssl rand -hex 16)}

# Timezone
GENERIC_TIMEZONE=America/Bogota
TZ=America/Bogota

# Execution settings
EXECUTIONS_DATA_SAVE_ON_ERROR=all
EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=true
EOF

echo "[OK] Archivo .env creado en ~/stacks/n8n/.env"
cat ~/stacks/n8n/.env
```

```bash
# Crear el archivo docker-compose.yml
cat > ~/stacks/n8n/docker-compose.yml << 'COMPOSE_EOF'
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: n8n-postgres
    restart: "no"
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - n8n-network

  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: "no"
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=${N8N_HOST}
      - N8N_PORT=${N8N_PORT}
      - N8N_PROTOCOL=${N8N_PROTOCOL}
      - WEBHOOK_URL=${WEBHOOK_URL}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - DB_TYPE=${DB_TYPE}
      - DB_POSTGRESDB_HOST=${DB_POSTGRESDB_HOST}
      - DB_POSTGRESDB_PORT=${DB_POSTGRESDB_PORT}
      - DB_POSTGRESDB_DATABASE=${DB_POSTGRESDB_DATABASE}
      - DB_POSTGRESDB_USER=${DB_POSTGRESDB_USER}
      - DB_POSTGRESDB_PASSWORD=${DB_POSTGRESDB_PASSWORD}
      - GENERIC_TIMEZONE=${GENERIC_TIMEZONE}
      - TZ=${TZ}
      - EXECUTIONS_DATA_SAVE_ON_ERROR=${EXECUTIONS_DATA_SAVE_ON_ERROR}
      - EXECUTIONS_DATA_SAVE_ON_SUCCESS=${EXECUTIONS_DATA_SAVE_ON_SUCCESS}
      - EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=${EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS}
    volumes:
      - ./data:/home/node/.n8n
      - ./local-files:/data/local-files
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - n8n-network

networks:
  n8n-network:
    driver: bridge
COMPOSE_EOF

echo "[OK] docker-compose.yml creado"
```

### 27.2.2 Iniciar el Stack

```bash
# Iniciar N8N y PostgreSQL
cd ~/stacks/n8n
docker compose up -d

# Ver los logs de inicio (tarda 30-60 segundos la primera vez)
docker compose logs -f
# Esperar la línea: "Editor is now accessible via: http://0.0.0.0:5678/"
# Presionar Ctrl+C para salir de los logs
```

```
# Salida esperada (extracto):
n8n-postgres | LOG:  database system is ready to accept connections
n8n          | Editor is now accessible via: http://0.0.0.0:5678/
n8n          | Press "o" to open in Browser
```

```bash
# Verificar que ambos contenedores están corriendo
docker compose ps
```

```
# Salida esperada:
NAME            IMAGE                COMMAND                  SERVICE    CREATED         STATUS
n8n             n8nio/n8n:latest     "tini -- /docker-ent…"   n8n        30 seconds ago  Up 28 seconds
n8n-postgres    postgres:16-alpine   "docker-entrypoint.s…"   postgres   30 seconds ago  Up 29 seconds (healthy)
```

```bash
# Abrir el firewall para acceso desde la red local
sudo ufw allow 5678/tcp comment "N8N Workflow Automation"

# Verificar acceso
curl -sf http://localhost:5678/ > /dev/null && echo "[OK] N8N accesible en :5678"
```

Abra en el navegador desde cualquier equipo de la red local:

```
http://192.168.1.100:5678
```

En la primera visita, N8N solicita crear una cuenta de administrador local.

---

## 27.3 Configuración de Acceso Seguro

### 27.3.1 Autenticación Básica (Opción A — Más Simple)

```bash
# Agregar autenticación básica al archivo .env
cat >> ~/stacks/n8n/.env << 'EOF'

# Basic Auth
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=CAMBIE_ESTA_CONTRASEÑA_SEGURA
EOF

# Reiniciar para aplicar
cd ~/stacks/n8n && docker compose restart n8n
```

### 27.3.2 Verificar Webhook URL

Los webhooks de N8N reciben peticiones en la URL configurada. Verifique que la URL de webhook está configurada correctamente:

```bash
# Ver la URL de webhook configurada
grep WEBHOOK_URL ~/stacks/n8n/.env
# Esperado: WEBHOOK_URL=http://192.168.1.100:5678/

# Probar que N8N responde en la URL raíz
curl -I http://localhost:5678/
# Esperado: HTTP/1.1 200 OK (o 302 redirect al login)
```

---

## 27.4 Primeros Nodos: Llamar a los Motores de Inferencia

### 27.4.1 Nodo HTTP Request → Ollama

N8N se conecta a Ollama mediante el nodo "HTTP Request". Desde la interfaz web:

1. **Nuevo flujo** → "+" → Nodo "HTTP Request"
2. **Method:** POST
3. **URL:** `http://localhost:11434/api/generate`
4. **Body:** JSON
5. **Body Content:**

```json
{
  "model": "qwen3:7b",
  "prompt": "{{ $json.prompt }}",
  "stream": false
}
```

6. **Response Format:** JSON

Para probar este nodo desde la terminal antes de usar la interfaz:

```bash
# Probar la llamada a Ollama que usará N8N
# (Requiere Ollama activo: sudo systemctl start ollama && ollama run qwen3:7b)
curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:7b",
    "prompt": "Responde en una oración: ¿qué es el edge computing?",
    "stream": false
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"
```

### 27.4.2 Nodo HTTP Request → vLLM (API OpenAI)

vLLM expone la API OpenAI estándar. Configuración del nodo HTTP Request para vLLM:

1. **Method:** POST
2. **URL:** `http://localhost:8000/v1/chat/completions`
3. **Headers:** `Content-Type: application/json`
4. **Body Content:**

```json
{
  "model": "qwen35",
  "messages": [
    {"role": "system", "content": "Eres un asistente experto en automatización."},
    {"role": "user", "content": "{{ $json.user_message }}"}
  ],
  "max_tokens": 500,
  "temperature": 0.7
}
```

5. **Response processing:** `{{ $json.choices[0].message.content }}`

```bash
# Probar la llamada a vLLM que usará N8N
# (Requiere vLLM activo: start-qwen35 o start-qwen4b)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35",
    "messages": [{"role": "user", "content": "Di hola en 5 palabras."}],
    "max_tokens": 50
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

---

## 27.5 Pipeline de Ejemplo: Webhook → LLM → Email

Este pipeline completo recibe una pregunta via webhook, la procesa con el LLM local y envía la respuesta por email.

### 27.5.1 Diseño del Pipeline

> **[INFOGRAFÍA — VERSIÓN IMPRESA]** *Diseño del Pipeline: Webhook → LLM → Email* — Se recomienda convertir este esquema en una infografía de alta resolución para la versión KDP. Requisitos: texto mínimo 10 pt, paleta teal `#0F3D3D` / accent `#1D9CB8`, formato monocromático disponible para impresión B&W.


```
Trigger: Webhook POST /webhook/pregunta-llm
         { "pregunta": "¿Cuáles son los beneficios del edge AI?" }
                │
                ▼
         Nodo HTTP Request → vLLM :8000
         POST /v1/chat/completions
                │
                ▼ respuesta del modelo
         Nodo Set → extraer texto de choices[0].message.content
                │
                ▼
         Nodo Email → enviar respuesta a destinatario configurado
                │
                ▼
         Respuesta HTTP → {"status": "enviado", "preview": "..."}
```

### 27.5.2 Crear el Pipeline via Importación JSON

```bash
# Guardar el flujo N8N como JSON para importar
cat > ~/stacks/n8n/local-files/flujo-webhook-llm-email.json << 'FLOW_EOF'
{
  "name": "Webhook → LLM → Email",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "pregunta-llm",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "webhook-trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [250, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/v1/chat/completions",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {"name": "Content-Type", "value": "application/json"}
          ]
        },
        "sendBody": true,
        "contentType": "json",
        "body": "={{ JSON.stringify({\"model\": \"qwen35\", \"messages\": [{\"role\": \"system\", \"content\": \"Eres un asistente técnico experto. Responde en español con claridad y precisión.\"},{\"role\": \"user\", \"content\": $json.body.pregunta}], \"max_tokens\": 600}) }}",
        "options": {}
      },
      "id": "call-vllm",
      "name": "Llamar vLLM",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [450, 300]
    },
    {
      "parameters": {
        "values": {
          "string": [
            {
              "name": "respuesta_llm",
              "value": "={{ $json.choices[0].message.content }}"
            },
            {
              "name": "pregunta_original",
              "value": "={{ $('Webhook').item.json.body.pregunta }}"
            }
          ]
        },
        "options": {}
      },
      "id": "set-values",
      "name": "Extraer Respuesta",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [650, 300]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({\"status\": \"procesado\", \"pregunta\": $json.pregunta_original, \"respuesta\": $json.respuesta_llm}) }}"
      },
      "id": "respond-webhook",
      "name": "Responder Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [850, 300]
    }
  ],
  "connections": {
    "Webhook": {"main": [[{"node": "Llamar vLLM", "type": "main", "index": 0}]]},
    "Llamar vLLM": {"main": [[{"node": "Extraer Respuesta", "type": "main", "index": 0}]]},
    "Extraer Respuesta": {"main": [[{"node": "Responder Webhook", "type": "main", "index": 0}]]}
  }
}
FLOW_EOF

echo "[OK] Flujo exportado en ~/stacks/n8n/local-files/flujo-webhook-llm-email.json"
echo "Para importar: N8N → File → Import from file → seleccionar el archivo"
```

### 27.5.3 Probar el Pipeline

```bash
# Activar el flujo desde la interfaz de N8N primero (botón "Activate")
# Luego probar el webhook desde la terminal

# Prerrequisito: vLLM activo con start-qwen35 o start-qwen4b
curl -sf http://localhost:8000/v1/models > /dev/null \
  || { echo "[ERROR] vLLM no activo. Ejecute: start-qwen4b"; exit 1; }

# Enviar pregunta al webhook de N8N
curl -s -X POST http://localhost:5678/webhook/pregunta-llm \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Cuáles son las tres ventajas principales del edge AI sobre la nube?"}' \
  | python3 -c "
import sys,json
resp = json.load(sys.stdin)
print('Estado:', resp.get('status'))
print('Pregunta:', resp.get('pregunta'))
print('Respuesta:', resp.get('respuesta')[:300], '...')
"
```

```
# Salida esperada:
Estado: procesado
Pregunta: ¿Cuáles son las tres ventajas principales del edge AI sobre la nube?
Respuesta: Las tres ventajas principales del edge AI son: 1) Latencia mínima — el procesamiento ocurre localmente...
```

---

## 27.6 Pipeline de Integración con OpenClaw

Este pipeline recibe un mensaje de texto via webhook y lo envía al gateway de OpenClaw como una instrucción de agente:

```bash
# Probar la integración con OpenClaw antes de crear el flujo
# (Requiere OpenClaw gateway activo: openclaw-start)

OPENCLAW_TOKEN=$(openclaw config get gateway.auth.token 2>/dev/null || echo "TU_TOKEN_AQUI")

# Enviar instrucción al agente OpenClaw desde N8N via HTTP
curl -s -X POST http://localhost:18789/api/agent/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENCLAW_TOKEN" \
  -d '{
    "task": "Resume en 3 puntos clave el estado actual de la inteligencia artificial en dispositivos edge",
    "channel": "api",
    "format": "json"
  }' | python3 -m json.tool 2>/dev/null || echo "[REQUIERE VERIFICACIÓN] — consultar documentación de OpenClaw para el endpoint exacto de la API"
```

**Configuración del nodo HTTP Request para OpenClaw en N8N:**

1. **Method:** POST
2. **URL:** `http://localhost:18789/api/agent/run`
3. **Headers:**
   - `Content-Type: application/json`
   - `Authorization: Bearer {{ $credentials.openclaw_token }}`
4. **Body:**

```json
{
  "task": "{{ $json.body.tarea }}",
  "channel": "api",
  "format": "json"
}
```

> **NOTA:** El endpoint exacto de la API de OpenClaw puede variar según la versión. Consulte `openclaw doctor` y la documentación oficial en `docs.openclaw.ai` para confirmar los endpoints disponibles en su instalación.

---

## 27.7 Pipeline de Procesamiento de Email Entrante

> **[INFOGRAFÍA — VERSIÓN IMPRESA]** *Pipeline: Email Entrante → LLM → Respuesta Automática* — Se recomienda convertir este esquema en una infografía de alta resolución para la versión KDP. Requisitos: texto mínimo 10 pt, paleta teal `#0F3D3D` / accent `#1D9CB8`, formato monocromático disponible para impresión B&W.

Este pipeline monitorea una bandeja de entrada de Gmail y procesa cada email con el LLM:

```bash
# Crear credencial de Gmail en N8N:
# Settings → Credentials → Add Credential → Gmail OAuth2 API
# (Requiere cuenta en console.cloud.google.com para OAuth2)

# Una vez configurada la credencial, el flujo es:
# Trigger: Gmail Trigger (cada 5 minutos)
#          ↓
# Filter: Si el email tiene asunto que contiene "IA:" o "AI:"
#          ↓
# HTTP Request → vLLM (procesar el contenido del email)
#          ↓
# Gmail → Responder al remitente con el análisis del LLM
```

El flujo completo se configura desde la interfaz web de N8N con los nodos de Gmail (requieren credenciales OAuth2). La parte que sí se puede configurar directamente via API es la llamada al LLM:

```bash
# Probar el procesamiento de texto de email via vLLM
EMAIL_CONTENT="Asunto: Propuesta de colaboración en proyecto de IA
De: cliente@empresa.com
Cuerpo: Estimados, tenemos un proyecto de automatización de procesos con IA y nos gustaría explorar opciones de colaboración. ¿Podrían agendar una reunión esta semana?"

curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json
print(json.dumps({
  'model': 'qwen35',
  'messages': [
    {'role': 'system', 'content': 'Analiza el email y extrae: (1) tipo de solicitud, (2) urgencia (alta/media/baja), (3) respuesta sugerida en 2 oraciones. Responde en JSON.'},
    {'role': 'user', 'content': '$EMAIL_CONTENT'}
  ],
  'max_tokens': 400
}))
")" | python3 -c "import sys,json; print(json.dumps(json.loads(json.load(sys.stdin)['choices'][0]['message']['content']), indent=2, ensure_ascii=False))"
```

---

## 27.8 Monitoreo y Logs

```bash
# Ver logs de N8N en tiempo real
docker compose -f ~/stacks/n8n/docker-compose.yml logs -f n8n

# Ver logs de PostgreSQL
docker compose -f ~/stacks/n8n/docker-compose.yml logs -f postgres

# Ver solo los últimos 50 líneas (útil para debugging)
docker compose -f ~/stacks/n8n/docker-compose.yml logs --tail=50 n8n

# Ver ejecuciones activas desde la terminal
curl -s http://localhost:5678/api/v1/executions?status=running \
  -H "X-N8N-API-KEY: TU_API_KEY" \
  2>/dev/null | python3 -m json.tool

# Estado de recursos del stack completo
docker stats n8n n8n-postgres --no-stream
```

```
# Salida esperada de docker stats:
CONTAINER ID   NAME          CPU %   MEM USAGE / LIMIT     MEM %
abc123         n8n           2.3%    380MiB / 62.7GiB      0.6%
def456         n8n-postgres  0.8%    185MiB / 62.7GiB      0.3%
```

---

## 27.9 Scripts y Aliases

```bash
# Crear scripts de gestión para N8N
cat > ~/scripts/n8n-manage.sh << 'N8N_SCRIPT'
#!/bin/bash
# Uso: n8n-manage.sh [start|stop|restart|status|logs|update]

N8N_DIR="$HOME/stacks/n8n"

case "$1" in
  start)
    echo "Iniciando N8N stack..."
    docker-on 2>/dev/null || sudo systemctl start docker.socket docker
    cd "$N8N_DIR" && docker compose up -d
    echo -n "Esperando N8N"
    until curl -sf http://localhost:5678/ > /dev/null; do echo -n "."; sleep 5; done
    JETSON_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo "[OK] N8N disponible en http://${JETSON_IP}:5678"
    ;;
  stop)
    cd "$N8N_DIR" && docker compose stop
    echo "N8N detenido (datos preservados en ~/stacks/n8n/)"
    ;;
  restart)
    cd "$N8N_DIR" && docker compose restart
    until curl -sf http://localhost:5678/ > /dev/null; do sleep 5; done
    echo "[OK] N8N reiniciado"
    ;;
  status)
    cd "$N8N_DIR" && docker compose ps
    curl -sf http://localhost:5678/ > /dev/null && echo "Web: accesible en :5678" || echo "Web: no responde"
    ;;
  logs)
    cd "$N8N_DIR" && docker compose logs -f n8n
    ;;
  update)
    echo "Actualizando N8N (preservando datos)..."
    cd "$N8N_DIR"
    docker compose pull
    docker compose up -d
    until curl -sf http://localhost:5678/ > /dev/null; do sleep 5; done
    echo "[OK] N8N actualizado"
    ;;
  kill)
    echo "Deteniendo y eliminando contenedores (datos en ~/stacks/n8n/ intactos)..."
    cd "$N8N_DIR" && docker compose down
    echo "Contenedores eliminados. Los datos persisten en ~/stacks/n8n/data/ y ~/stacks/n8n/postgres-data/"
    ;;
  *)
    echo "Uso: $0 [start|stop|restart|status|logs|update|kill]"
    exit 1
    ;;
esac
N8N_SCRIPT

chmod +x ~/scripts/n8n-manage.sh
```

```bash
# Agregar aliases al ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── N8N Workflow Automation ──────────────────────────────────────────────
alias start-n8n='~/scripts/n8n-manage.sh start'
alias stop-n8n='~/scripts/n8n-manage.sh stop'
alias restart-n8n='~/scripts/n8n-manage.sh restart'
alias n8n-status='~/scripts/n8n-manage.sh status'
alias n8n-logs='~/scripts/n8n-manage.sh logs'
alias update-n8n='~/scripts/n8n-manage.sh update'
alias kill-n8n='~/scripts/n8n-manage.sh kill'
alias n8n-url='echo "http://$(hostname -I | awk '"'"'{print $1}'"'"'):5678"'
EOF

source ~/.bash_aliases
echo "[OK] Aliases de N8N configurados"
```

### 27.9.1 Flujo Típico de Trabajo

```bash
# Iniciar el stack completo para una sesión de automatización
pwr-30w          # N8N es CPU-bound — 30W es suficiente
docker-on        # activar Docker si está desactivado
start-n8n        # iniciar N8N + PostgreSQL

# (Opcional) Iniciar también el motor LLM si los flujos lo requieren
start-qwen4b     # modelo ligero para flujos de N8N (50 tok/s, solo 5GB)

# Ver URL de acceso
n8n-url
# → http://192.168.1.100:5678

# Trabajar en los flujos desde el navegador...

# Al terminar la sesión
stop-n8n         # detener N8N (PostgreSQL también)
kill-qwen4b      # liberar RAM del modelo
pwr-15w          # modo ahorro energético
```

---

## 27.10 Integración Avanzada: N8N + OpenClaw + vLLM

> **[INFOGRAFÍA — VERSIÓN IMPRESA]** *Integración: N8N + OpenClaw + vLLM* — Se recomienda convertir este esquema en una infografía de alta resolución para la versión KDP. Requisitos: texto mínimo 10 pt, paleta teal `#0F3D3D` / accent `#1D9CB8`, formato monocromático disponible para impresión B&W.


El stack completo de automatización agéntica combina N8N como orquestador con OpenClaw como agente de razonamiento:

```
Fuente externa (email, Slack, webhook, cron)
        │
        ▼
   N8N (orquestador de flujos)
        │  ← decide qué tipo de tarea es
        ├─→ Tarea simple: HTTP Request → vLLM :8000 → respuesta directa
        └─→ Tarea compleja: HTTP Request → OpenClaw :18789 → agente autónomo
                                              │
                                              ├─ Búsqueda web
                                              ├─ Ejecución de código
                                              ├─ Lectura de archivos
                                              └─ Respuesta multi-paso
```

**Presupuesto de memoria para el stack completo:**

| Componente | RAM |
|-----------|-----|
| OS base | ~12 GB |
| N8N + PostgreSQL | ~0.6 GB |
| Qwen3.5-4B via vLLM | ~5 GB |
| OpenClaw gateway | ~0.2 GB |
| **Total** | **~17.8 GB** — deja 46 GB libres |

```bash
# Alias para el stack completo de automatización
cat >> ~/.bash_aliases << 'EOF'

alias agency-automation-start='
  pwr-30w && docker-on
  start-n8n
  start-qwen4b
  openclaw-start
  echo "[OK] Stack N8N + vLLM + OpenClaw listo"
  echo "  N8N:      http://$(hostname -I | awk '"'"'{print $1}'"'"'):5678"
  echo "  vLLM:     http://localhost:8000/v1"
  echo "  OpenClaw: http://localhost:18789 (via túnel SSH)"
'

alias agency-automation-stop='
  stop-n8n
  kill-qwen4b
  openclaw-stop
  pwr-15w
  echo "[OK] Stack detenido"
'
EOF

source ~/.bash_aliases
```

---

## 27.11 Solución de Problemas

### N8N no puede conectar a PostgreSQL al iniciar

```bash
# Síntoma: n8n logs muestra "connection refused" o "ECONNREFUSED"
docker compose -f ~/stacks/n8n/docker-compose.yml logs postgres | tail -20
# Si PostgreSQL no llegó a "ready to accept connections", esperar o reiniciar

# Verificar que PostgreSQL está healthy
docker inspect n8n-postgres | python3 -c \
  "import sys,json; h=json.load(sys.stdin)[0]['State']['Health']; print('PostgreSQL:', h['Status'])"
# Esperado: PostgreSQL: healthy

# Reiniciar solo PostgreSQL si está en estado unhealthy
cd ~/stacks/n8n && docker compose restart postgres
sleep 10
docker compose restart n8n
```

### Los webhooks no reciben peticiones desde la red local

```bash
# Verificar que UFW permite el puerto 5678
sudo ufw status | grep 5678
# Si no aparece: sudo ufw allow 5678/tcp comment "N8N"

# Verificar que N8N está escuchando en 0.0.0.0 (no solo localhost)
ss -tlnp | grep 5678
# Esperado: *:5678 o 0.0.0.0:5678

# Verificar la variable WEBHOOK_URL en el .env
grep WEBHOOK_URL ~/stacks/n8n/.env
# Debe usar la IP real del Jetson, no localhost ni 127.0.0.1
```

### El nodo HTTP Request no puede conectar a vLLM

```bash
# Causa: vLLM usa localhost pero N8N corre en una red Docker bridge
# Solución: usar la IP del host desde la perspectiva del contenedor

# Obtener la IP del host en la red Docker
docker exec n8n ip route | grep default | awk '{print $3}'
# Salida ejemplo: 172.18.0.1

# Usar esa IP en el nodo HTTP Request de N8N en lugar de localhost:
# http://172.18.0.1:8000/v1/chat/completions

# Verificar conectividad desde dentro del contenedor N8N
docker exec n8n curl -sf http://172.18.0.1:8000/v1/models \
  && echo "[OK] vLLM accesible desde N8N" \
  || echo "[ERROR] vLLM no accesible — verificar que vLLM usa --network host"
```

> **EXPLICACIÓN:** Los contenedores Docker en red `bridge` (como N8N y PostgreSQL en su compose) no pueden usar `localhost` para acceder a servicios del host. Los servicios que usan `--network host` (vLLM, llama.cpp, Ollama) son accesibles via la IP gateway del bridge Docker (típicamente `172.18.0.1`). Use esta IP en los nodos HTTP Request de N8N.

### N8N consume demasiada CPU en modo idle

```bash
# N8N en modo idle no debería usar más del 2-3% de CPU
docker stats n8n --no-stream | awk '{print "CPU:", $3, "RAM:", $4}'

# Si el CPU es alto (>10%), verificar flujos activos
# Settings → Executions → ver si hay ejecuciones colgadas

# Cancelar ejecuciones colgadas desde la interfaz:
# Executions → filtrar por "Running" → cancelar manualmente
```

---

## 27.12 Backup y Restauración

```bash
# Backup completo de N8N (flujos + credenciales + ejecuciones)
cd ~/stacks/n8n
FECHA=$(date +%Y%m%d_%H%M)

# Exportar desde PostgreSQL
docker exec n8n-postgres pg_dump -U n8n_user n8n > ~/backups/n8n_backup_${FECHA}.sql
echo "[OK] Backup SQL: ~/backups/n8n_backup_${FECHA}.sql"

# También copiar los archivos de configuración
tar czf ~/backups/n8n_files_${FECHA}.tar.gz \
  ~/stacks/n8n/.env \
  ~/stacks/n8n/data/ \
  ~/stacks/n8n/local-files/
echo "[OK] Backup archivos: ~/backups/n8n_files_${FECHA}.tar.gz"
```

```bash
# Restaurar desde backup SQL
cat ~/backups/n8n_backup_FECHA.sql | docker exec -i n8n-postgres psql -U n8n_user n8n
cd ~/stacks/n8n && docker compose restart n8n
```

---

## Resumen del Capítulo

N8N en el Jetson AGX Orin proporciona un orquestador de flujos de trabajo completamente local:

- **Docker Compose** con PostgreSQL garantiza persistencia de flujos y credenciales entre reinicios
- **Puerto 5678** — permitir en UFW para acceso desde la red local
- `restart: "no"` — N8N y PostgreSQL no arrancan solos al reiniciar el Jetson; use `start-n8n` para iniciarlos manualmente cuando los necesite
- **IP del host Docker** (`172.18.0.1` típicamente) en lugar de `localhost` para llamar a vLLM/Ollama desde los nodos HTTP de N8N
- **`start-n8n` / `stop-n8n`** — aliases que gestionan todo el stack (N8N + PostgreSQL)
- Con 30W y el modelo Qwen3.5-4B (~5 GB), el stack completo consume solo ~18 GB de los 64 GB disponibles

El siguiente capítulo (Capítulo 28) cubre Computer Vision y OCR: pipelines para análisis de imágenes, reconocimiento de texto y detección de objetos en tiempo real usando los contenedores de la NVIDIA Jetson AI Lab.
