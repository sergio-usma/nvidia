# Capítulo 9 — Docker y NVIDIA Container Toolkit

## Introducción

Docker es el sistema de contenedores que permite ejecutar aplicaciones de forma aislada, reproducible y sin contaminar el sistema base. En el Jetson, Docker tiene un papel especialmente importante: los modelos de lenguaje más avanzados (Capítulo 14) se distribuyen como imágenes Docker precompiladas para ARM64+CUDA, lo que elimina la necesidad de compilar manualmente cientos de dependencias.

El NVIDIA Container Toolkit es la pieza que conecta Docker con el GPU del Jetson. Sin él, un contenedor Docker no puede acceder a CUDA ni al acelerador GPU — sería equivalente a ejecutar el modelo en CPU pura.

**Prerequisito:** Capítulo 1 (primer arranque) y Capítulo 2 (configuración base del sistema) completados.

**Tiempo estimado:** 20–30 minutos.

**Al final de esta parte tendrá:**
- Docker Engine instalado y configurado para el usuario actual
- NVIDIA Container Toolkit instalado y habilitado
- Capacidad de ejecutar contenedores con acceso al GPU del Jetson
- Docker desactivado en el arranque (arquitectura de arranque limpio)

---

## 8.0 Conceptos Básicos de Docker (lectura antes de instalar)

Si ya conoce Docker, puede saltar directamente a §8.1. Esta sección explica los conceptos que se usan en todos los capítulos de este libro.

### 8.0.1 Imagen, contenedor e instancia

| Concepto | Analogía | Descripción práctica |
|----------|----------|----------------------|
| **Imagen** | Receta de cocina | Archivo de solo lectura con todo el software. Se descarga una vez y ocupa espacio en disco (2–15 GB típicamente) |
| **Contenedor** | Plato cocinado | Instancia viva de una imagen. Tiene su propio sistema de archivos, red y proceso. Se crea desde la imagen |
| **Volumen** | Nevera externa | Directorio del Jetson montado dentro del contenedor. Los datos persisten aunque borre el contenedor |

```bash
# Ver imagenes descargadas (lo que ocupa disco):
docker images

# Ver contenedores activos (lo que ocupa RAM):
docker ps

# Ver TODOS los contenedores, incluyendo los detenidos:
docker ps -a

# Ver cuanto espacio usa Docker en total:
docker system df
```

```
# Salida de docker system df:
TYPE            TOTAL   ACTIVE  SIZE      RECLAIMABLE
Images          8       3       28.5GB    15.2GB (53%)
Containers      3       2       234MB     0B (0%)
Local Volumes   5       3       4.2GB     1.1GB (26%)
```

### 8.0.2 Ciclo de vida de un contenedor

```bash
# Crear y arrancar un contenedor en segundo plano (-d = detached):
docker run -d --name mi-servicio imagen:tag

# Ver sus logs en tiempo real:
docker logs -f mi-servicio
# Ctrl+C para dejar de ver logs (el contenedor sigue corriendo)

# Detener gracefully (espera hasta 10 segundos):
docker stop mi-servicio

# Iniciar un contenedor detenido (recupera su estado):
docker start mi-servicio

# Eliminar un contenedor detenido (libera el nombre):
docker rm mi-servicio

# Forzar parada inmediata y eliminar en un solo comando:
docker rm -f mi-servicio

# Entrar a un contenedor en ejecucion:
docker exec -it mi-servicio bash
```

### 8.0.3 Limpieza de recursos

```bash
# Eliminar contenedores detenidos + imagenes huerfanas + cache de build:
docker system prune

# Igual pero incluye volumenes no utilizados (PRECAUCION: borra datos):
# docker system prune --volumes

# Ver cuanta RAM usa cada contenedor activo:
docker stats --no-stream
```

```
# Salida de docker stats --no-stream:
CONTAINER ID   NAME          CPU %   MEM USAGE / LIMIT    MEM %
a3f7c2e9d4b1   open-webui    0.5%    312MiB / 60.7GiB     0.5%
8b2c4e1f9a3d   vllm-container  48.2%   14.8GiB / 60.7GiB   24.4%
```

### 8.0.4 Directorios de almacenamiento

Por defecto, Docker almacena todo en `/var/lib/docker/`. En el Jetson con NVMe, conviene moverlo o usar volumes nombrados:

```bash
# Ver donde esta el directorio de Docker:
docker info | grep "Docker Root Dir"
# Salida: Docker Root Dir: /var/lib/docker

# Los volumenes nombrados (datos persistentes) estan en:
ls /var/lib/docker/volumes/

# Las imagenes (en formato overlay2) estan en:
ls /var/lib/docker/overlay2/ | wc -l  # numero de capas
```

> **IMPORTANTE para el Jetson:** Los modelos de HuggingFace que descargan los contenedores se guardan en `~/.cache/huggingface/` del Jetson (montado como volumen). Nunca dentro del contenedor — si borra el contenedor, los modelos permanecen. Esto se configura en §8.5.

---

## 8.1 Instalar Docker Engine

Ubuntu 24.04 en el Jetson viene sin Docker instalado. Se instala desde el repositorio oficial de Docker (no desde los paquetes de Ubuntu, que suelen estar desactualizados).

### 8.1.1 Instalación desde el Repositorio Oficial de Docker

```bash
# 1. Instalar dependencias
sudo apt update
sudo apt install -y ca-certificates curl gnupg
```

```bash
# 2. Agregar la clave GPG de Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

```bash
# 3. Agregar el repositorio de Docker para Ubuntu 24.04 (noble) en ARM64
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Actualizar e instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

```bash
# 5. Verificar la instalación
sudo docker run --rm hello-world
```

```
# Salida esperada
Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon...
```

### 8.1.2 Usar Docker sin sudo

Por defecto, Docker requiere `sudo`. Agréguese al grupo `docker` para evitarlo:

```bash
# Agregar el usuario actual al grupo docker
sudo usermod -aG docker $USER

# Aplicar el cambio de grupo sin necesidad de cerrar sesión
newgrp docker

# Verificar
docker run --rm hello-world
```

```
# Salida esperada (igual que antes pero sin sudo)
Hello from Docker!
```

> **NOTA DE SEGURIDAD:** Los miembros del grupo `docker` tienen acceso root efectivo al sistema. En un servidor de producción compartido esto sería una vulnerabilidad; en el Jetson personal es el comportamiento esperado y cómodo.

### 8.1.3 Configurar Docker para el Arranque Limpio

Siguiendo la arquitectura de arranque limpio (Capítulo 15 §15.0), Docker no debe iniciarse automáticamente en cada reboot:

```bash
# Desactivar Docker en el arranque
sudo systemctl disable docker
sudo systemctl disable docker.socket

# Verificar que quedó desactivado
systemctl is-enabled docker
```

```
# Salida esperada
disabled
```

> **¿Cuándo se inicia Docker entonces?** Cuando ejecute `start-qwen35`, `start-nemotron` o cualquier alias de la Sección 15.8, estos contienen `sudo systemctl start docker` al inicio. También puede iniciarlo manualmente con `sudo systemctl start docker`.

---

## 8.2 Instalar NVIDIA Container Toolkit

El NVIDIA Container Toolkit (NCT) le permite a Docker pasar el GPU del Jetson a los contenedores. Sin él, cualquier imagen que use CUDA fallará.

### 8.2.1 Instalación del NVIDIA Container Toolkit

```bash
# 1. Agregar el repositorio de NVIDIA para el NCT
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 2. Instalar el toolkit
sudo apt update
sudo apt install -y nvidia-container-toolkit
```

```bash
# 3. Configurar Docker para usar el runtime NVIDIA
sudo nvidia-ctk runtime configure --runtime=docker
```

```
# Salida esperada
INFO[0000] Loading config from /etc/docker/daemon.json
INFO[0000] Wrote updated config to /etc/docker/daemon.json
INFO[0000] It is recommended that the docker daemon be restarted.
```

```bash
# 4. Reiniciar Docker para aplicar la configuración
sudo systemctl restart docker
```

### 8.2.2 Verificar el NVIDIA Container Toolkit

```bash
# Ejecutar un contenedor con acceso al GPU y verificar CUDA
# NOTA: En Jetson se usa --runtime nvidia, NO --gpus all (que no funciona en ARM)
sudo docker run --rm --runtime=nvidia \
  ubuntu:22.04 \
  bash -c "ls /proc/driver/nvidia/gpus/ && echo '[OK] GPU accesible desde contenedor'"
```

```
# Salida esperada
0000:00:00.0
[OK] GPU accesible desde contenedor
```

```bash
# Verificar CUDA dentro de un contenedor oficial de NVIDIA
docker run --rm --runtime=nvidia \
  --network host \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  nvcc --version
```

```
# Salida esperada (tarda 2-5 min la primera vez — descarga la imagen)
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on ...
Cuda compilation tools, release 13.2, V13.2.91
Build cuda_13.2...
```

> **IMPORTANTE:** En el Jetson siempre se usa `--runtime nvidia` (o `--runtime=nvidia`), nunca `--gpus all`. La opción `--gpus all` es para GPUs discretas x86 y falla en la arquitectura ARM unificada del Jetson.

---

## 8.3 Arquitectura de GPU en Contenedores Jetson

<!-- INFOGRAFÍA: Arquitectura de GPU en Contenedores Jetson — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


Entender cómo Docker accede al GPU del Jetson evita errores comunes:

```
┌──────────────────────────────────────────────────────────┐
│                    ARQUITECTURA JETSON                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Memoria Unificada (64 GB LPDDR5)         │   │
│  │  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │   CPU (ARM)     │  │    GPU (Ampere)      │  │   │
│  │  │  12 núcleos     │  │    2048 CUDA cores   │  │   │
│  │  └─────────────────┘  └─────────────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│                           │                              │
│                    /dev/nvidia0                          │
│                    /dev/nvidiactl                        │
│                    /dev/nvidia-uvm*                      │
│                           │                              │
│   ┌──────────────────────────────────────────────┐      │
│   │  Docker + NVIDIA Container Toolkit           │      │
│   │  --runtime nvidia → monta /dev/nvidia*       │      │
│   │  en el contenedor → CUDA funciona            │      │
│   └──────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

**Por qué no hay `nvidia-smi` en el Jetson:**
En GPUs discretas (PC/servidor), `nvidia-smi` muestra estadísticas del GPU incluyendo VRAM. En el Jetson, la memoria es unificada (CPU y GPU comparten la misma RAM física) y no existe una interfaz SMI de la misma forma. En su lugar, use:
- `jtop` — monitor integrado de Jetson (RAM total + GPU + temperatura)
- `tegrastats` — estadísticas en terminal
- `nvcc --version` dentro de contenedores — confirma que CUDA está disponible

---

## 8.4 Comandos Esenciales de Docker para el Jetson

### 8.4.1 Gestión de Imágenes

```bash
# Ver imágenes descargadas (ordenadas por tamaño)
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | sort -k3 -h -r

# Descargar una imagen específica
docker pull ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin

# Eliminar una imagen específica
docker rmi ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin

# Eliminar imágenes huérfanas (sin contenedor asociado, recupera espacio)
docker image prune -f

# Ver espacio total ocupado por Docker
docker system df
```

### 8.4.2 Gestión de Contenedores

```bash
# Ver contenedores activos
docker ps

# Ver todos los contenedores (incluyendo detenidos)
docker ps -a

# Ver logs de un contenedor en tiempo real
docker logs -f nombre-contenedor

# Entrar a un contenedor en ejecución
docker exec -it nombre-contenedor bash

# Detener un contenedor (gracefully, 10 seg timeout)
docker stop nombre-contenedor

# Eliminar un contenedor detenido
docker rm nombre-contenedor

# Detener y eliminar en un solo comando
docker stop nombre-contenedor && docker rm nombre-contenedor
```

### 8.4.3 Estructura de un docker run para Jetson

Todo `docker run` de modelos LLM en el Jetson sigue este patrón:

```bash
sudo docker run \
  --runtime nvidia \           # Acceso al GPU del Jetson (OBLIGATORIO)
  -d \                         # Modo daemon (en segundo plano)
  --name mi-modelo \           # Nombre para gestionar el contenedor
  --restart no \               # NO reiniciar automáticamente (arranque limpio)
  --network host \             # Compartir red del host (puerto directo al Jetson)
  --ipc host \                 # Compartir memoria IPC (necesario para vLLM)
  --shm-size 8g \              # Shared memory (vLLM necesita 8GB+)
  -v /host/path:/container/path \  # Volumen: caché de modelos (persistente)
  imagen:tag \                 # Imagen Docker a usar
  comando args                 # Comando a ejecutar dentro del contenedor
```

**Por qué `--network host`:** Al compartir la red del host, el contenedor escucha directamente en la IP del Jetson (ej: `:8000`). Sin `--network host`, necesitaría `-p 8000:8000` para publicar el puerto y usar la IP del Jetson para acceder desde otras máquinas.

### 8.4.4 Tres ejemplos concretos de docker run en el Jetson

**Ejemplo 1 — vLLM con Gemma 4 E2B (API OpenAI-compatible, puerto 8000):**

```bash
# Asegurar que el cache de HuggingFace existe
mkdir -p ~/.cache/huggingface

# Lanzar vLLM
# Tiempo estimado: 3-5 minutos (descarga del modelo la primera vez)
# Consumo RAM: ~15 GB   Modo: 30W
docker run -d \
  --name vllm-gemma \
  --runtime nvidia \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -e HF_TOKEN="${HF_TOKEN}" \
  -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
  --model google/gemma-3-4b-it \
  --host 0.0.0.0 --port 8000 \
  --api-key "${VLLM_API_KEY:-vllm-local}" \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85

# Monitorear arranque:
docker logs -f vllm-gemma | grep -E "started|error|Uvicorn"
# Salida esperada: INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Ejemplo 2 — llama.cpp servidor con modelo GGUF (API OpenAI-compatible, puerto 8080):**

```bash
# Primero descargar el modelo GGUF si no existe (ver Capitulo 12):
# hf download Qwen/Qwen3-8B-GGUF --include "Qwen3-8B-Q4_K_M.gguf" --local-dir ~/data/models/gguf/

GGUF_PATH=$(ls ~/data/models/gguf/Qwen3-8B-Q4*.gguf 2>/dev/null | head -1)
[ -z "$GGUF_PATH" ] && echo "[ERROR] Modelo GGUF no encontrado en ~/data/models/gguf/" && exit 1

# Nota: llama.cpp se usa compilado desde fuente (Capitulo 12), no desde Docker.
# Para Docker con llama.cpp de NVIDIA:
# Tiempo estimado: 20-60 segundos   Consumo RAM: ~6 GB   Modo: 30W
docker run -d \
  --name llamacpp-server \
  --runtime nvidia \
  --restart no \
  --network host \
  -v $(dirname $GGUF_PATH):/models \
  ghcr.io/ggml-org/llama.cpp:server \
  -m /models/$(basename $GGUF_PATH) \
  --host 0.0.0.0 --port 8080 \
  -c 32768 -ngl 999 --flash-attn

docker logs -f llamacpp-server | grep -E "llama server|error|HTTP"
# Salida esperada: llama server listening at http://0.0.0.0:8080
```

**Ejemplo 3 — NVIDIA Cosmos (modelo generativo de video, via NGC):**

```bash
# Cosmos requiere NGC CLI y cuenta en NVIDIA NGC (gratuita)
# Ver Capitulo 19 para el tutorial completo de generacion de video

# Instalar NGC CLI si no esta instalado:
pip install ngccli

# Autenticar con NGC (solo la primera vez):
# IMPORTANTE: reemplaza TU_NGC_API_KEY con tu API key de catalog.ngc.nvidia.com
ngc config set

# Descargar la imagen de Cosmos desde NGC:
ngc registry image pull nvcr.io/nvidia/cosmos/cosmos-predict2:latest

# Lanzar para generacion de video (requiere MAXN + ~40 GB RAM):
sudo nvpmodel -m 0 && sudo jetson_clocks
docker run -d \
  --name cosmos-predict \
  --runtime nvidia \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 16g \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -v $HOME/data/cosmos-output:/workspace/output \
  nvcr.io/nvidia/cosmos/cosmos-predict2:latest

docker logs -f cosmos-predict | grep -E "ready|error|port"
```

> **NOTA:** Para todos los contenedores de inferencia, use siempre `--restart no` — si el Jetson reinicia, el contenedor no arrancará automáticamente y no consumirá RAM hasta que lo inicie explícitamente. Esto es la filosofía clean-start.

---

## 8.5 Configurar el Directorio de Caché de Modelos

Los modelos de lenguaje pesan entre 2 GB y 30 GB. Sin un directorio de caché persistente montado como volumen, cada vez que borre o recree un contenedor tendría que volver a descargar el modelo completo. La configuración correcta descarga el modelo una vez y lo reutiliza indefinidamente.

### 8.5.1 Crear el directorio de caché

```bash
# Opcion A: cache en el directorio home (eMMC o NVMe, segun donde este /)
mkdir -p ~/.cache/huggingface

# Opcion B (recomendada si tiene NVMe montado en /data — ver Capitulo 4):
mkdir -p /data/hf-cache
mkdir -p ~/.cache/huggingface

# Crear enlace simbolico para que ambas rutas apunten al mismo lugar:
# (si /data existe y tiene el espacio del NVMe)
[ -d /data/hf-cache ] && ln -sf /data/hf-cache ~/.cache/huggingface && \
  echo "[OK] Cache en NVMe via symlink" || echo "[INFO] Cache en home"

# Verificar espacio disponible:
df -h ~/.cache/huggingface
```

### 8.5.2 La regla universal del volumen de caché

> **REGLA:** Todo `docker run` que descargue o use un modelo de HuggingFace **debe** incluir este flag:
>
> `-v $HOME/.cache/huggingface:/root/.cache/huggingface`
>
> Sin este flag, el contenedor descarga el modelo en su capa efímera de escritura y lo pierde al ser eliminado.

```bash
# Verificar que el montaje funciona correctamente:
docker run --rm \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ubuntu:24.04 \
  ls /root/.cache/huggingface/

# Si el cache tiene modelos, los vera listados. Si esta vacio, mostrara nada.
```

### 8.5.3 Mover el cache de Docker a NVMe (opcional, para ahorrar eMMC)

Si tiene un NVMe y quiere que las imágenes Docker también se almacenen allí:

```bash
# 1. Detener Docker
sudo systemctl stop docker

# 2. Copiar los datos existentes al NVMe
sudo rsync -a /var/lib/docker/ /data/docker/

# 3. Configurar Docker para usar el nuevo directorio
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "data-root": "/data/docker",
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
EOF

# 4. Reiniciar Docker
sudo systemctl start docker
docker info | grep "Docker Root Dir"
# Salida: Docker Root Dir: /data/docker
```

---

## 8.6 Docker Compose: Orquestar Múltiples Contenedores

Docker Compose permite definir y lanzar stacks de múltiples contenedores con un solo comando. En el Jetson, es ideal para combinar servicios que trabajan juntos: un frontend (Open WebUI) con un backend TTS (kokoro), o un servidor de transcripción (faster-whisper) con una API de audio.

**Convención de directorios para stacks en el Jetson:**

```bash
# Cada stack vive en su propio subdirectorio bajo ~/stacks/
# Estructura canonica:
~/stacks/
  webui/           # Open WebUI
    compose.yml
  voice/           # TTS + STT
    compose.yml
  n8n/             # Automatizacion N8N
    compose.yml
  rag/             # RAG + ChromaDB
    compose.yml
```

```bash
# Crear la estructura de directorios:
mkdir -p ~/stacks/{webui,voice,n8n,rag}
```

> **IMPORTANTE — Regla de oro para Jetson:** Los contenedores con GPU de inferencia (vLLM, llama.cpp, faster-whisper con CUDA) deben usar `restart: "no"` para mantener la arquitectura de arranque limpio. Los contenedores sin GPU (frontends, bases de datos, APIs ligeras) pueden usar `restart: unless-stopped`. En caso de duda: `restart: "no"` es siempre seguro.

### 8.6.1 Instalar Docker Compose

`docker-compose-plugin` ya se instaló en §8.1.1 como parte del paquete de Docker. Verifique:

```bash
# Verificar disponibilidad de docker compose (con espacio, no guión)
docker compose version
```

```
# Salida esperada
Docker Compose version v2.x.x
```

> **NOTA:** En sistemas antiguos existe `docker-compose` (con guión, versión 1). El plugin `docker compose` (sin guión, versión 2) es el estándar actual y el que se usa en todos los ejemplos de este libro.

### 8.6.2 Stack Básico: Open WebUI + faster-whisper

Este es el stack de productividad offline más útil para el día a día: interfaz web para LLMs y transcripción de audio. Ambos servicios son livianos y pueden coexistir con el LLM que se cargue bajo demanda.

```bash
# Crear directorio para el stack
mkdir -p ~/stacks/webui-whisper
cat > ~/stacks/webui-whisper/compose.yml << 'EOF'
name: webui-whisper

services:

  # ── Open WebUI ─────────────────────────────────────────────
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    restart: unless-stopped          # OK — sin GPU, solo UI
    network_mode: host
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - OPENAI_API_BASE_URL=http://localhost:8000/v1  # ← vLLM cuando esté activo
      - OLLAMA_BASE_URL=http://localhost:11434         # ← Ollama cuando esté activo
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ── faster-whisper STT ────────────────────────────────────
  faster-whisper:
    image: dustynv/faster-whisper:r39.2.0
    container_name: faster-whisper
    restart: "no"                    # OBLIGATORIO — contenedor GPU
    runtime: nvidia
    network_mode: host
    volumes:
      - ${HOME}/.cache/huggingface:/root/.cache/huggingface
    environment:
      - WHISPER_MODEL=medium         # small para <1 GB RAM; large-v3 para máxima calidad
      - WHISPER_DEVICE=cuda
      - WHISPER_COMPUTE_TYPE=float16
      - WHISPER_LANGUAGE=es

volumes:
  open-webui-data:                   # Volumen nombrado — persiste entre reinicios
EOF
```

```bash
# Iniciar el stack
cd ~/stacks/webui-whisper
docker compose up -d

# Verificar que ambos contenedores estén activos
docker compose ps
```

```
# Salida esperada
NAME              IMAGE                                    STATUS
faster-whisper    dustynv/faster-whisper:r39.2.0          running
open-webui        ghcr.io/open-webui/open-webui:main      running (healthy)
```

```bash
# Ver logs de todos los contenedores del stack
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f faster-whisper

# Detener el stack (sin borrar volúmenes)
docker compose down

# Detener y borrar volúmenes (¡PRECAUCIÓN: borra datos de Open WebUI!)
# docker compose down --volumes
```

### 8.6.3 Stack de Voz: faster-whisper + kokoro-tts

Para el pipeline completo STT + TTS del Capítulo 29:

```bash
mkdir -p ~/stacks/voice
cat > ~/stacks/voice/compose.yml << 'EOF'
name: voice-stack

services:

  # ── STT: faster-whisper ───────────────────────────────────
  faster-whisper:
    image: dustynv/faster-whisper:r39.2.0
    container_name: faster-whisper
    restart: "no"
    runtime: nvidia
    network_mode: host
    volumes:
      - ${HOME}/.cache/huggingface:/root/.cache/huggingface
    environment:
      - WHISPER_MODEL=large-v3
      - WHISPER_DEVICE=cuda
      - WHISPER_COMPUTE_TYPE=float16
      - WHISPER_LANGUAGE=es
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/health"]
      interval: 20s
      timeout: 10s
      retries: 5
      start_period: 120s             # Da tiempo para descargar el modelo en primer uso

  # ── TTS: kokoro ───────────────────────────────────────────
  kokoro-tts:
    image: dustynv/kokoro-tts:r39.2.0
    container_name: kokoro-tts
    restart: "no"
    runtime: nvidia
    network_mode: host
    volumes:
      - ${HOME}/.cache/huggingface:/root/.cache/huggingface
    depends_on:
      faster-whisper:
        condition: service_healthy   # Espera a que whisper esté listo antes de iniciar
EOF
```

```bash
# Iniciar el stack de voz
cd ~/stacks/voice
docker compose up -d

# Esperar a que faster-whisper esté healthy (hasta 3 min en primer uso)
echo -n "Esperando stack de voz"
until docker compose ps --format json 2>/dev/null | \
  python3 -c "import sys,json; data=json.load(sys.stdin); \
  print('ok') if all(s.get('Health','healthy')=='healthy' or s.get('State')=='running' \
  for s in data) else print('wait')" 2>/dev/null | grep -q ok; do
  echo -n "."; sleep 10
done
echo " [OK] Stack de voz activo"

# Test STT
echo "Testing STT..."
curl -s http://localhost:8000/health && echo "[OK] faster-whisper :8000 OK"

# Test TTS
echo "Testing TTS..."
curl -s http://localhost:8880/health && echo "[OK] kokoro-tts :8880 OK"
```

### 8.6.4 Comandos Esenciales de Docker Compose

```bash
# ── Gestión del stack ─────────────────────────────────────────────────
# Iniciar todos los servicios (en segundo plano)
docker compose up -d

# Detener todos los servicios (contenedores quedan parados, no borrados)
docker compose down

# Reiniciar un servicio específico sin tocar los otros
docker compose restart faster-whisper

# Escalar (no aplica para GPU en Jetson — solo 1 instancia por GPU)
# docker compose up -d --scale faster-whisper=1

# ── Inspección ───────────────────────────────────────────────────────
# Estado de los servicios
docker compose ps

# Logs de todos los servicios (últimas 50 líneas + streaming)
docker compose logs --tail=50 -f

# Uso de recursos del stack
docker compose stats

# ── Actualizar imágenes ──────────────────────────────────────────────
# Descargar versiones más recientes de las imágenes
docker compose pull

# Reiniciar con las nuevas imágenes
docker compose up -d

# ── Limpieza ─────────────────────────────────────────────────────────
# Borrar contenedores e imágenes del stack (mantiene volúmenes nombrados)
docker compose down --rmi all

# Borrar TODO incluyendo datos (¡DESTRUCTIVO — requiere confirmación mental!)
# docker compose down --rmi all --volumes
```

### 8.6.5 Estructura de un compose.yml para el Jetson

```yaml
# Plantilla canónica para servicios con GPU en Jetson AGX Orin JP 7.2
name: mi-stack

services:

  mi-servicio-gpu:
    image: ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin  # imagen ARM64+CUDA
    container_name: mi-servicio-gpu
    restart: "no"              # SIEMPRE "no" para servicios de inferencia GPU
    runtime: nvidia            # OBLIGATORIO — equivalente a --runtime nvidia
    network_mode: host         # Compartir red del host (sin mapeo de puertos)
    shm_size: "8g"             # Shared memory para vLLM
    ipc: host                  # Para PyTorch multiprocessing
    volumes:
      - ${HOME}/.cache/huggingface:/root/.cache/huggingface
    environment:
      - VARIABLE=valor
    command: bash -c "cd /opt && source venv/bin/activate && vllm serve ..."

  mi-servicio-cpu:
    image: postgres:16-alpine  # Imagen estándar — sin GPU
    container_name: mi-db
    restart: unless-stopped    # OK para servicios sin GPU
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=segura
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:               # Volumen nombrado — persiste entre reinicios del contenedor
```

> **Regla de la coma con GPU:** Si el servicio toca `/dev/nvidia*`, usa `restart: "no"` y `runtime: nvidia`. Si no tiene GPU, puede usar `restart: unless-stopped`.

### 8.6.6 Aliases para Gestión de Stacks

```bash
# Agregar al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── Docker Compose stacks ────────────────────────────────────────────
alias start-voice-stack='cd ~/stacks/voice && docker compose up -d && cd -'
alias stop-voice-stack='cd ~/stacks/voice && docker compose down && cd -'
alias start-webui-stack='cd ~/stacks/webui-whisper && docker compose up -d && cd -'
alias stop-webui-stack='cd ~/stacks/webui-whisper && docker compose down && cd -'
alias stack-status='docker compose -f ~/stacks/voice/compose.yml ps 2>/dev/null; docker compose -f ~/stacks/webui-whisper/compose.yml ps 2>/dev/null'
alias stack-logs='docker compose -f ~/stacks/voice/compose.yml logs --tail=30 2>/dev/null'
EOF

source ~/.bashrc
```

---

## 8.7 Verificación Final del Capítulo

```bash
# Verificación completa de Docker + NVIDIA Container Toolkit
echo "╔═════════════════════════════════════════════════════╗"
echo "║    VERIFICACIÓN CAPÍTULO 8 — DOCKER + NVIDIA NCT      ║"
echo "╚═════════════════════════════════════════════════════╝"

echo ""
echo "── Docker Engine ──"
docker version --format "  [OK] Docker {{.Server.Version}} ({{.Server.Os}}/{{.Server.Arch}})" \
  2>/dev/null || echo "  [ERROR] Docker no accesible (¿ejecutar sudo systemctl start docker?)"

echo ""
echo "── Grupo Docker ──"
groups | grep -q docker \
  && echo "  [OK] Usuario en grupo docker (sin sudo necesario)" \
  || echo "  [WARN]  Usuario NO en grupo docker — ejecute: sudo usermod -aG docker \$USER"

echo ""
echo "── Docker en arranque ──"
systemctl is-enabled docker 2>/dev/null | grep -q "disabled" \
  && echo "  [OK] Docker desactivado en boot (arranque limpio)" \
  || echo "  [WARN]  Docker activo en boot — ejecute: sudo systemctl disable docker"

echo ""
echo "── NVIDIA Container Toolkit ──"
nvidia-ctk --version 2>/dev/null \
  && echo "  [OK] nvidia-ctk instalado" \
  || echo "  [ERROR] nvidia-ctk no instalado — ver Sección 8.2"

echo ""
echo "── Runtime NVIDIA en Docker ──"
docker info 2>/dev/null | grep -q "nvidia" \
  && echo "  [OK] Runtime nvidia configurado" \
  || echo "  [WARN]  Runtime nvidia no detectado — ejecute: sudo nvidia-ctk runtime configure --runtime=docker"

echo ""
echo "── Test GPU en contenedor ──"
docker run --rm --runtime=nvidia ubuntu:22.04 \
  ls /proc/driver/nvidia/gpus/ 2>/dev/null \
  && echo "  [OK] GPU accesible desde contenedor" \
  || echo "  [ERROR] GPU no accesible — verificar instalación NCT"

echo ""
echo "── Imágenes NVIDIA disponibles ──"
docker images | grep -E "nvidia-ai-iot|dustynv" \
  | awk '{printf "  [OK] %s:%s (%s)\n", $1, $2, $7}' \
  || echo "  ℹ️  Sin imágenes NVIDIA descargadas todavía (se descargan con los modelos)"

echo ""
echo "════════════════════════════════════════════════════"
```

```
# Salida esperada
── Docker Engine ──
  [OK] Docker 27.x.x (linux/arm64)

── Grupo Docker ──
  [OK] Usuario en grupo docker (sin sudo necesario)

── Docker en arranque ──
  [OK] Docker desactivado en boot (arranque limpio)

── NVIDIA Container Toolkit ──
  nvidia-ctk version 1.x.x
  [OK] nvidia-ctk instalado

── Runtime NVIDIA en Docker ──
  [OK] Runtime nvidia configurado

── Test GPU en contenedor ──
  0000:00:00.0
  [OK] GPU accesible desde contenedor

── Imágenes NVIDIA disponibles ──
  ℹ️  Sin imágenes NVIDIA descargadas todavía (se descargan con los modelos)
```

> **Próximo paso:** Con Docker y el NVIDIA Container Toolkit configurados, el Capítulo 12 puede ejecutar los contenedores de inferencia de NVIDIA. Antes de continuar con los capítulos de modelos, el Capítulo 16 cubre el troubleshooting de los errores más comunes.
