# INNOVALABS — Docker Stack
## Documentación del entorno containerizado v1.0

> **Target:** NVIDIA Jetson AGX Orin (aarch64, 64GB RAM unificada)  
> **JetPack:** 6.2.2 / CUDA 12.6 / NVIDIA Container Toolkit

---

## Arquitectura de servicios

```
┌─────────────────────── Host (Jetson AGX Orin) ───────────────────────┐
│                                                                       │
│  /usr/local/cuda ──────────────────┐ (mount ro)                      │
│  ~/.local/bin/llama-cli ────────┐  │                                 │
│  ~/.cache/llama.cpp/  ───────┐  │  │                                 │
│                              │  │  │                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    Docker Network (bridge)                      │ │
│  │                                                                 │ │
│  │  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐  │ │
│  │  │   OLLAMA    │    │   WRITER     │    │       N8N         │  │ │
│  │  │             │    │              │    │                   │  │ │
│  │  │ API :11434  │◄───│ llama-cli    │◄───│  Workflow Engine  │  │ │
│  │  │             │    │ + CUDA       │    │  + Docker CLI     │  │ │
│  │  │ 3 modelos:  │    │              │    │                   │  │ │
│  │  │ • GLM-4.7   │    │ 1 modelo:    │    │  Ejecuta:         │  │ │
│  │  │ • DS-R1:8b  │    │ • Qwen3.5   │    │  • HTTP → Ollama  │  │ │
│  │  │ • Nemotron  │    │   27B Q4     │    │  • exec → Writer  │  │ │
│  │  │             │    │              │    │  • Python scripts  │  │ │
│  │  └─────────────┘    └──────┬───────┘    └────────┬──────────┘  │ │
│  │                            │                     │              │ │
│  │                     ┌──────┴─────────────────────┴──────┐      │ │
│  │                     │     shared_workspace (volume)      │      │ │
│  │                     │  /shared/historia_*_raw.txt        │      │ │
│  │                     └────────────────────────────────────┘      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  /var/opt/innovalabs/historias/  ←── Archivos .md finales             │
│  /opt/innovalabs/scripts/       ←── scout_trends.py, writer_bridge   │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## ¿Por qué 3 contenedores?

El pipeline tiene una restricción particular: el Agente Escritor (Qwen3.5-27B) se ejecuta con `llama-cli`, que necesita acceso directo a CUDA y al modelo GGUF de ~18 GB. Mientras que los otros 3 agentes (Estratega, Arquitecto, Editor) corren vía la API HTTP de Ollama.

| Servicio | Rol | GPU | Comunicación |
|----------|-----|-----|-------------|
| **ollama** | Inferencia de 3 modelos ligeros | Sí (runtime nvidia) | HTTP API `:11434` |
| **writer** | Ejecución de Qwen3.5-27B via llama-cli | Sí (runtime nvidia) | `docker exec` + volumen compartido |
| **n8n** | Orquestación del pipeline completo | No | HTTP + exec + filesystem |

El **writer** es un sidecar "dormido" (`sleep infinity`) que consume 0% CPU hasta que n8n lo despierta con `docker exec`. Esto evita instalar CUDA dentro del contenedor de n8n y mantiene cada servicio con una responsabilidad única.

---

## Instalación paso a paso

### 1. Clonar/copiar los archivos

```bash
# Crear directorio del proyecto
mkdir -p ~/innovalabs-stack && cd ~/innovalabs-stack

# Copiar los archivos entregados:
#   docker-compose.yml
#   .env.example
#   setup.sh
#   scripts/writer_bridge.sh
```

### 2. Ejecutar verificación del entorno

```bash
chmod +x setup.sh
./setup.sh --check
```

Esto valida sin modificar nada: arquitectura, Docker, NVIDIA runtime, CUDA, llama-cli, modelo GGUF, Python y memoria.

### 3. Ejecutar setup completo

```bash
./setup.sh
```

El script:
- Crea los directorios `/opt/innovalabs/scripts` y `/var/opt/innovalabs/historias`
- Genera `.env` desde `.env.example` con rutas auto-detectadas
- Opcionalmente descarga los 3 modelos de Ollama

### 4. Ajustar `.env`

```bash
nano .env
```

Campos críticos a verificar:

| Variable | Qué poner |
|----------|-----------|
| `GSHEETS_SPREADSHEET_ID` | ID de tu Google Sheet (de la URL) |
| `LLAMA_CLI_PATH` | Ruta al binario llama-cli en el host |
| `LLAMA_MODELS_DIR` | Directorio donde está el .gguf |
| `N8N_ENCRYPTION_KEY` | Generado automáticamente por setup.sh |
| `N8N_BASIC_AUTH_PASSWORD` | Cambiar por una contraseña segura |

### 5. Levantar el stack

```bash
docker compose up -d
```

Verificar que todo está sano:

```bash
# Estado de los contenedores
docker compose ps

# Logs en tiempo real
docker compose logs -f

# Health checks
docker inspect --format='{{.State.Health.Status}}' innovalabs-ollama
docker inspect --format='{{.State.Health.Status}}' innovalabs-n8n
```

### 6. Verificar servicios individuales

```bash
# Ollama respondiendo
curl http://localhost:11434/api/tags

# Writer tiene acceso al modelo
docker exec innovalabs-writer ls -lh /models/

# Writer tiene acceso a CUDA
docker exec innovalabs-writer ls /usr/local/cuda/lib64/libcudart*

# n8n tiene acceso a Docker CLI
docker exec innovalabs-n8n docker --version

# n8n puede hacer exec al Writer
docker exec innovalabs-n8n docker exec innovalabs-writer echo "Comunicación OK"
```

### 7. Importar el workflow en n8n

1. Abrir `http://localhost:5678` en el navegador
2. Login con las credenciales de `.env`
3. Settings → Import from File → seleccionar `INNOVALABS_Literature_Factory_v1.0.json`
4. Configurar credenciales de Google Sheets (OAuth2)
5. Reemplazar los Spreadsheet IDs en los nodos de Google Sheets

---

## Patch del workflow para Docker

El workflow JSON original usa `llama-cli` directamente. En Docker, el nodo del Escritor debe usar el script `writer_bridge.sh`. Hay dos nodos que necesitan ajuste:

### Nodo "📝 Compilar Prompt del Escritor"

Reemplazar la generación del comando llama-cli por:

```javascript
// En lugar de generar el comando llama-cli directo,
// generar la llamada al writer_bridge.sh

const outputFile = `/shared/historia_${data.ID}_raw.txt`;

const command = `/opt/innovalabs/scripts/writer_bridge.sh \
  --prompt "${escapedPrompt}" \
  --output "${outputFile}" \
  --ctx 8192 \
  --tokens 8000 \
  --temp 0.8 \
  --repeat 1.1`;

return [{
  json: {
    ...data,
    llama_command: command,
    output_file: outputFile
  }
}];
```

### Nodo "📄 Leer Historia Raw"

Cambiar la lectura del archivo para usar la ruta `/shared/`:

```javascript
// El archivo ahora está en el volumen compartido /shared/
const outputFile = prevData.output_file;  // Ya apunta a /shared/...

let rawStory;
try {
  rawStory = fs.readFileSync(outputFile, 'utf-8');
} catch (e) {
  throw new Error(`No se pudo leer: ${outputFile}. Error: ${e.message}`);
}
```

### Nodo "🔄 Reiniciar Ollama" (sub-flujo de errores)

Ya funciona sin cambios porque n8n tiene el docker.sock montado:

```bash
docker restart innovalabs-ollama && sleep 10
```

Cambiar `ollama` → `innovalabs-ollama` (nombre del contenedor).

### Nodo "🔍 Scout" (Execute Command)

El scout se ejecuta con Python del host. Como n8n corre en Alpine (sin Python), hay dos opciones:

**Opción A** — Ejecutar via Docker en el host:
```bash
docker exec innovalabs-writer python3 /opt/innovalabs/scripts/scout_trends.py
```
(Requiere instalar pytrends en el writer o montar los scripts ahí)

**Opción B (recomendada)** — Montar Python del host en n8n:
Agregar al servicio n8n en docker-compose.yml:
```yaml
volumes:
  - /usr/bin/python3:/usr/bin/python3:ro
  - /usr/lib/python3:/usr/lib/python3:ro
  - /usr/local/lib/python3.10:/usr/local/lib/python3.10:ro
```

**Opción C** — Usar un nodo HTTP Request en n8n que llame a un micro-servicio Flask del Scout (más limpio pero requiere un servicio adicional).

---

## Comandos de operación

### Ciclo de vida

```bash
# Levantar todo
docker compose up -d

# Parar todo (mantiene datos)
docker compose down

# Parar y eliminar volúmenes (DESTRUCTIVO)
docker compose down -v

# Reiniciar un servicio específico
docker compose restart ollama

# Ver logs de un servicio
docker compose logs -f n8n --tail=100

# Escalar (no aplicable, concurrency=1)
```

### Monitoreo

```bash
# Uso de memoria por contenedor
docker stats --no-stream

# GPU en uso
tegrastats  # En el host (JetPack tool)

# Estado de la cola en Google Sheets
# → Abrir el spreadsheet y revisar la columna Estado

# Historias generadas
ls -lt /var/opt/innovalabs/historias/ | head -20

# Ejecuciones de n8n
# → http://localhost:5678/executions
```

### Troubleshooting

```bash
# Writer no arranca
docker compose logs writer
docker exec innovalabs-writer ls -la /usr/local/bin/llama-cli
docker exec innovalabs-writer ls -la /models/

# Ollama no carga modelos
docker exec innovalabs-ollama ollama list
docker compose logs ollama | grep -i error

# n8n no puede ejecutar docker exec
docker exec innovalabs-n8n docker ps
# Si falla → verificar que /var/run/docker.sock está montado

# OOM durante escritura
docker compose logs writer | tail -50
dmesg | grep -i "oom\|killed"  # En el host
# Solución: reducir --ctx o --tokens en writer_bridge.sh

# Ollama lento en cargar modelos
# Normal: primera carga de cada modelo toma 30-60s
# Reducir OLLAMA_KEEP_ALIVE en .env para liberar VRAM más rápido
```

---

## Seguridad

### Docker Socket

El montaje de `docker.sock` en n8n le da acceso completo al Docker daemon. Esto es necesario para `docker exec` al writer y `docker restart` a ollama. Mitigaciones:

- n8n solo es accesible localmente (`:5678` en localhost)
- Autenticación básica habilitada
- En producción, considerar Docker rootless o un proxy de socket como `tecnativa/docker-socket-proxy`

### Credenciales de Google Sheets

Las credenciales OAuth2 se almacenan encriptadas en el volumen `n8n_data` usando la `N8N_ENCRYPTION_KEY`. Si se pierde esta clave, las credenciales deben reconfigurarse.

---

## Alternativa: n8n nativo (sin Docker)

Si la complejidad del sidecar Writer resulta excesiva, la alternativa más simple es:

```bash
# Solo Ollama en Docker
docker compose up -d ollama

# n8n nativo via npm
npm install -g n8n
export N8N_DEFAULT_EXECUTION_TIMEOUT=1800
n8n start --tunnel
```

Ventajas: acceso directo a llama-cli, Python, y filesystem del host.
Desventaja: n8n no se reinicia automáticamente y requiere gestionar el proceso (systemd service recomendado).
