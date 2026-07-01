# Capítulo 19 — Generación de Imágenes y Videos: ComfyUI, SD WebUI y AnimateDiff

## Introducción

El NVIDIA Jetson AGX Orin 64 GB no es solo un servidor de inferencia de texto. Con su GPU Ampere de 2048 núcleos CUDA y 64 GB de memoria unificada, es completamente capaz de ejecutar modelos de difusión estable para generar imágenes fotorrealistas, arte de estilo anime y videos cortos — todo completamente offline, sin enviar sus datos a servicios en la nube.

Este capítulo instala y configura dos herramientas complementarias:

- **ComfyUI** — interfaz basada en nodos (grafos), ideal para automatización, pipelines y AnimateDiff; puerto **8188**
- **Stable Diffusion WebUI (AUTOMATIC1111)** — interfaz clásica, ideal para exploración rápida y generación manual; puerto **7860**

Ambas usan la misma colección de modelos (checkpoints, LoRA, VAE) almacenada en `~/models/` — así descarga cada modelo una sola vez y lo usa en cualquiera de los dos sistemas.

> **[INFOGRAFÍA — VERSIÓN IMPRESA]** *Arquitectura de generación de imágenes en Jetson: modelos compartidos entre ComfyUI y SD WebUI* — Se recomienda convertir este esquema en una infografía de alta resolución para la versión KDP. Requisitos: texto mínimo 10 pt, paleta teal `#0F3D3D` / accent `#1D9CB8`, formato monocromático disponible para impresión B&W.

**Prerrequisitos:**
- Capítulo 8 completado (Docker + NVIDIA Container Toolkit)
- Capítulo 18 completado (jetson-containers, familiaridad con sistema de tags)
- Al menos 80 GB libres en almacenamiento (modelos son grandes: 2–8 GB cada uno)

**Tiempo estimado:**
- Descarga de imágenes Docker: 30–60 minutos (según velocidad de red)
- Descarga de modelos SD 1.5: ~2 GB — 5–10 minutos
- Descarga de modelos SDXL: ~7 GB — 15–25 minutos
- Primera imagen generada: ~10–30 segundos (SD 1.5) / ~45–90 segundos (SDXL)

**Modo de energía:** MAXN durante toda la sesión de generación

**Al final de este capítulo tendrá:**
- ComfyUI corriendo en `http://localhost:8188`
- SD WebUI corriendo en `http://localhost:7860`
- Al menos un checkpoint SD 1.5 y uno SDXL instalados
- Scripts para generar imágenes vía API (sin interfaz gráfica)
- AnimateDiff configurado para generar videos cortos
- Aliases para iniciar/detener cada servicio

---

## 19.1 Prerrequisito — Verificación del Sistema

```bash
# Verificar recursos antes de iniciar
check-ready 40 "image-generation"

# Activar modo MAXN (obligatorio para generación de imágenes)
pwr-maxn

# Activar jetson_clocks para rendimiento máximo de GPU
sudo jetson_clocks

# Verificar que la GPU está activa y disponible
nvcc --version

# Ver uso actual de memoria (base line antes de iniciar contenedores)
free -h

# Ver espacio disponible (necesita 80 GB mínimo para modelos)
df -h ~
```

```
# Salida esperada de free -h (Jetson limpio sin modelos en RAM)
               total        used        free      shared  buff/cache   available
Mem:            62Gi        2.1Gi       58Gi       220Mi       2.3Gi       59Gi
Swap:           31Gi          0B        31Gi

# Salida esperada de nvcc --version
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on ...
Cuda compilation tools, release 13.2, V13.2.1
```

---

## 19.2 Estructura de Directorios para Modelos Compartidos

La clave de esta configuración es que **ambos programas — ComfyUI y SD WebUI — leen modelos desde el mismo directorio `~/models/`**. Descargue cada modelo una sola vez y estará disponible en ambas interfaces.

```bash
# Crear estructura de directorios unificada para modelos
mkdir -p ~/models/{checkpoints,loras,vae,embeddings,controlnet,upscalers,animatediff}
mkdir -p ~/stacks/comfyui
mkdir -p ~/stacks/sd-webui

# Verificar la estructura
tree ~/models/ -L 1
```

```
models/
├── checkpoints/     <- Modelos principales SD 1.5 / SDXL / Pony
├── loras/           <- LoRA: estilos, personajes, poses
├── vae/             <- VAE: mejora colores y nitidez
├── embeddings/      <- Textual inversion: conceptos especiales
├── controlnet/      <- ControlNet: control de pose/bordes
├── upscalers/       <- Real-ESRGAN, BSRGAN: mejora resolución
└── animatediff/     <- Motion modules para AnimateDiff
```

---

## 19.3 ComfyUI — Pipeline Visual de Generación de Imágenes

ComfyUI usa un sistema de **nodos conectados** (similar a Blender o TouchDesigner). Cada nodo realiza una operación: cargar modelo, codificar prompt, hacer denoising, decodificar imagen. La flexibilidad es enorme: puede construir pipelines complejos con ControlNet, AnimateDiff e img2img en el mismo workflow.

### 19.3.1 Verificar Disponibilidad de la Imagen para JP 7.2

```bash
# Verificar que el tag r39.2.0 está disponible para ComfyUI
# NOTA: Verifique que la URL siga activa antes de ejecutar
curl -s "https://hub.docker.com/v2/repositories/dustynv/comfyui/tags/?page_size=20" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
tags = [t['name'] for t in data.get('results', [])]
print('Tags disponibles:')
for t in sorted(tags, reverse=True)[:8]:
    print(f'  {t}')
"
```

```
# Salida esperada
Tags disponibles:
  r39.2.0
  r36.4.0
  r36.3.0
  ...
```

### 19.3.2 Descargar la Imagen de ComfyUI

```bash
# Descargar ComfyUI para JP 7.2 (tarda 10-20 min)
docker pull dustynv/comfyui:r39.2.0
```

```
# Progreso de descarga esperado
r39.2.0: Pulling from dustynv/comfyui
...
Status: Downloaded newer image for dustynv/comfyui:r39.2.0
```

### 19.3.3 Docker Compose para ComfyUI

```bash
# Crear el archivo docker-compose.yml para ComfyUI
cat > ~/stacks/comfyui/docker-compose.yml << 'EOF'
# ~/stacks/ es el directorio estándar para todos los Docker Compose del Jetson (ver Capítulo 8)
services:
  comfyui:
    image: dustynv/comfyui:r39.2.0
    container_name: comfyui
    runtime: nvidia
    restart: "no"
    network_mode: host
    volumes:
      - $HOME/models/checkpoints:/root/ComfyUI/models/checkpoints
      - $HOME/models/loras:/root/ComfyUI/models/loras
      - $HOME/models/vae:/root/ComfyUI/models/vae
      - $HOME/models/embeddings:/root/ComfyUI/models/embeddings
      - $HOME/models/controlnet:/root/ComfyUI/models/controlnet
      - $HOME/models/upscalers:/root/ComfyUI/models/upscale_models
      - $HOME/models/animatediff:/root/ComfyUI/models/animatediff_models
      - $HOME/.cache/huggingface:/root/.cache/huggingface
      - $HOME/stacks/comfyui/output:/root/ComfyUI/output
      - $HOME/stacks/comfyui/workflows:/root/ComfyUI/user/default/workflows
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    command: python3 main.py --listen 0.0.0.0 --port 8188 --enable-cors-header
EOF

# Crear directorio de output
mkdir -p ~/stacks/comfyui/{output,workflows}

echo "[OK] Docker Compose de ComfyUI listo en ~/stacks/comfyui/"
```

### 19.3.4 Arrancar ComfyUI

```bash
# Iniciar ComfyUI
cd ~/stacks/comfyui && docker compose up -d

# Verificar que el contenedor inició
docker ps | grep comfyui

# Monitorear el arranque (tarda 30-60 segundos en cargar)
docker logs comfyui --follow
```

```
# Salida esperada en logs
[ComfyUI] Starting server
[ComfyUI] To see the GUI go to: http://0.0.0.0:8188
[ComfyUI] NVIDIA JetPack 7.2 detected
[ComfyUI] PyTorch: 2.x.x
[ComfyUI] CUDA: 13.2.1
[ComfyUI] Loaded 0 checkpoint models (instale primero un checkpoint)
```

Una vez activo, acceda desde su PC Windows:

```
http://<IP-del-Jetson>:8188
```

> **NOTA — Acceso remoto:** Para acceder a ComfyUI desde Windows, use el SSH tunnel definido en Capítulo 7: `ssh -L 8188:localhost:8188 jetson`. Luego abra `http://localhost:8188` en su navegador.

### 19.3.5 Instalación del Primer Checkpoint (SD 1.5)

El **checkpoint** es el modelo principal. Stable Diffusion 1.5 (SD 1.5) es el punto de partida: pesa ~2 GB, genera imágenes 512×512 en ~10–20 segundos en el Jetson, y es compatible con miles de LoRA y extensiones.

```bash
# Crear script de descarga de modelos
cat > ~/scripts/download-sd-models.sh << 'EOF'
#!/bin/bash
# Descarga modelos SD para Jetson — ejecutar antes de iniciar ComfyUI o SD WebUI
# NOTA: Verifique que las URLs sigan activas antes de ejecutar

MODELS_DIR="$HOME/models"

echo "[INFO] Iniciando descarga de modelos Stable Diffusion..."
echo "       Directorio destino: $MODELS_DIR"
echo ""

# SD 1.5 base (requisito mínimo — ~2.1 GB)
if [ ! -f "$MODELS_DIR/checkpoints/v1-5-pruned-emaonly.safetensors" ]; then
    echo "[INFO] Descargando SD 1.5 (~2.1 GB)..."
    # ⚠ Reemplaza <HF_TOKEN> con tu token de Hugging Face si los modelos son privados
    wget -q --show-progress \
      "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" \
      -O "$MODELS_DIR/checkpoints/v1-5-pruned-emaonly.safetensors"
    echo "[OK] SD 1.5 descargado"
else
    echo "[OK] SD 1.5 ya existe — omitiendo"
fi

# Realistic Vision V6 — fotorrealista (~2.1 GB)
if [ ! -f "$MODELS_DIR/checkpoints/realisticVisionV60B1_v51HyperVAE.safetensors" ]; then
    echo "[INFO] Descargando Realistic Vision V6 (~2.1 GB)..."
    wget -q --show-progress \
      "https://civitai.com/api/download/models/245598" \
      -O "$MODELS_DIR/checkpoints/realisticVisionV60B1_v51HyperVAE.safetensors"
    echo "[OK] Realistic Vision V6 descargado"
else
    echo "[OK] Realistic Vision V6 ya existe — omitiendo"
fi

# VAE mejorado (mejora nitidez y colores)
if [ ! -f "$MODELS_DIR/vae/vae-ft-mse-840000-ema-pruned.safetensors" ]; then
    echo "[INFO] Descargando VAE mejorado (~335 MB)..."
    wget -q --show-progress \
      "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors" \
      -O "$MODELS_DIR/vae/vae-ft-mse-840000-ema-pruned.safetensors"
    echo "[OK] VAE descargado"
else
    echo "[OK] VAE ya existe — omitiendo"
fi

echo ""
echo "[OK] Modelos disponibles:"
ls -lh "$MODELS_DIR/checkpoints/"
ls -lh "$MODELS_DIR/vae/"
EOF

chmod +x ~/scripts/download-sd-models.sh

# Ejecutar la descarga
~/scripts/download-sd-models.sh
```

> **NOTA — CivitAI:** Los modelos de CivitAI a veces requieren iniciar sesión. Si la descarga falla, visite civitai.com, descargue el archivo manualmente y cópielo a `~/models/checkpoints/` via SCP: `scp modelo.safetensors jetson:~/models/checkpoints/`.

---

## 19.4 Stable Diffusion WebUI (AUTOMATIC1111)

SD WebUI ofrece una interfaz más tradicional con pestañas: `txt2img`, `img2img`, `Extras` (upscaling), `PNG Info` e `Inpainting`. Es ideal para exploración rápida sin necesidad de construir grafos de nodos.

### 19.4.1 Verificar Disponibilidad de la Imagen

```bash
# Verificar tag r39.2.0 para stable-diffusion-webui
# NOTA: Verifique que la URL siga activa antes de ejecutar
curl -s "https://hub.docker.com/v2/repositories/dustynv/stable-diffusion-webui/tags/?page_size=10" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
tags = [t['name'] for t in data.get('results', [])]
print('Tags disponibles para stable-diffusion-webui:')
for t in sorted(tags, reverse=True)[:5]:
    print(f'  {t}')
if not any('r39.2' in t for t in tags):
    print('[WARN] Tag r39.2.0 no disponible aun — use r36.4.0 con precaucion (JP 6.2)')
"
```

### 19.4.2 Docker Compose para SD WebUI

```bash
# Crear docker-compose.yml para SD WebUI
cat > ~/stacks/sd-webui/docker-compose.yml << 'EOF'
# ~/stacks/ es el directorio estándar para todos los Docker Compose del Jetson (ver Capítulo 8)
services:
  sd-webui:
    image: dustynv/stable-diffusion-webui:r39.2.0
    container_name: sd-webui
    runtime: nvidia
    restart: "no"
    network_mode: host
    volumes:
      - $HOME/models/checkpoints:/data/models/Stable-diffusion
      - $HOME/models/loras:/data/models/Lora
      - $HOME/models/vae:/data/models/VAE
      - $HOME/models/embeddings:/data/embeddings
      - $HOME/models/controlnet:/data/models/ControlNet
      - $HOME/models/upscalers:/data/models/ESRGAN
      - $HOME/stacks/sd-webui/output:/data/output
      - $HOME/stacks/sd-webui/extensions:/data/extensions
      - $HOME/.cache/huggingface:/root/.cache/huggingface
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - COMMANDLINE_ARGS=--listen --port 7860 --api --no-half-vae --xformers
EOF

mkdir -p ~/stacks/sd-webui/{output,extensions}

echo "[OK] Docker Compose de SD WebUI listo en ~/stacks/sd-webui/"
```

> **NOTA — flags importantes:**
> - `--api` habilita la API REST en `/sdapi/v1/` (necesaria para automatización)
> - `--no-half-vae` evita problemas de color en imágenes en Jetson
> - `--xformers` mejora el rendimiento de atención en GPU Ampere

### 19.4.3 Arrancar SD WebUI

```bash
# Iniciar SD WebUI
cd ~/stacks/sd-webui && docker compose up -d

# Monitorear el arranque (tarda 60-120 segundos la primera vez)
docker logs sd-webui --follow
```

```
# Salida esperada
Running on local URL:  http://0.0.0.0:7860
To create a public link, set `share=True` in `launch()`
Startup time: 45.3s ...
Model loaded in 12.4s (load weights from disk: 8.1s, ...)
```

### 19.4.4 Primera Imagen en SD WebUI

En la interfaz web (`http://<IP-Jetson>:7860`):

1. Pestaña **txt2img**
2. **Prompt:** `portrait of a woman, professional photo, sharp focus, 8k, photorealistic`
3. **Negative prompt:** `deformed, ugly, blurry, watermark, text, cartoon, anime, nsfw`
4. **Sampling method:** DPM++ 2M Karras
5. **Sampling steps:** 25
6. **Width/Height:** 512 × 512 (para SD 1.5) / 1024 × 1024 (para SDXL)
7. **CFG Scale:** 7
8. Clic en **Generate**

**Tiempo estimado para SD 1.5 a 512×512, 25 pasos:**
- Jetson en MAXN + jetson_clocks: ~10–20 segundos
- Jetson sin jetson_clocks: ~25–40 segundos

---

## 19.5 Modelos SDXL para Mayor Calidad

Stable Diffusion XL (SDXL) genera imágenes de 1024×1024 con calidad notablemente superior a SD 1.5. Requiere ~7–8 GB de VRAM — perfectamente manejable con los 64 GB de memoria unificada del Jetson.

### 19.5.1 Descargar SDXL Base

```bash
# Descargar SDXL 1.0 base (~6.9 GB) — tarda 15-20 minutos
# ⚠ Reemplaza <HF_TOKEN> con tu token de Hugging Face (si tienes uno)
# NOTA: Verifique que la URL siga activa antes de ejecutar
wget -q --show-progress \
  "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
  -O ~/models/checkpoints/sd_xl_base_1.0.safetensors

echo "[OK] SDXL base descargado: $(du -h ~/models/checkpoints/sd_xl_base_1.0.safetensors | cut -f1)"
```

### 19.5.2 Modelos Recomendados por Caso de Uso

| Modelo | Tamaño | Caso de uso | Tiempo/imagen Jetson |
|--------|--------|-------------|---------------------|
| SD 1.5 base | 2.1 GB | Prototipado rápido | ~15 seg (512×512) |
| Realistic Vision V6 | 2.1 GB | Fotografías de personas | ~15 seg (512×512) |
| SDXL 1.0 | 6.9 GB | Calidad máxima | ~60 seg (1024×1024) |
| Pony Diffusion V6 | 5.8 GB | Arte ilustración | ~50 seg (1024×1024) |
| DreamShaper XL | 6.7 GB | Versátil | ~55 seg (1024×1024) |

> **CONSEJO:** Empiece con SD 1.5 + Realistic Vision para familiarizarse con los parámetros. Cuando necesite calidad de presentación, migre a SDXL.

---

## 19.6 Generación de Imágenes de Estilo Anime

Los modelos de anime en SD usan técnicas de fine-tuning en datasets de manga y anime. Son modelos SD 1.5 o Pony Diffusion con estilo visual específico.

### 19.6.1 Descargar Modelo de Anime

```bash
# Anything V5 — modelo anime popular (~2.2 GB)
# NOTA: Verifique que la URL siga activa antes de ejecutar
wget -q --show-progress \
  "https://huggingface.co/stablediffusionapi/anything-v5/resolve/main/anything-v5-PrtRE.safetensors" \
  -O ~/models/checkpoints/anything-v5.safetensors

echo "[OK] Anything V5 descargado"
```

### 19.6.2 Prompts y Parámetros para Anime

La sintaxis de prompts para anime difiere del fotorrealismo:

```
# Prompt positivo típico para anime (SD 1.5 / Anything)
masterpiece, best quality, 1girl, solo, long hair, blue eyes, school uniform,
cherry blossoms, detailed background, soft lighting, anime style

# Negative prompt para anime — evitar deformidades típicas
(worst quality:1.4), (low quality:1.4), (bad anatomy:1.3), watermark,
signature, text, blurry, deformed hands, extra fingers, missing fingers,
fused fingers, bad proportions, gross proportions, nsfw
```

> **NOTA — Sintaxis de pesos:** `(texto:1.3)` aumenta la importancia del término al 130%. Use con moderación — pesos > 1.5 producen resultados inestables.

### 19.6.3 Script API para Generación en Lote

```python
#!/usr/bin/env python3
# ~/scripts/generate-anime-batch.py
# Genera múltiples imágenes via API de SD WebUI sin interfaz gráfica
import requests
import base64
import json
from pathlib import Path
from datetime import datetime

SD_API = "http://localhost:7860"
OUTPUT_DIR = Path.home() / "stacks/sd-webui/output/anime"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = [
    "masterpiece, 1girl, long silver hair, sunset, detailed background",
    "masterpiece, 1boy, samurai armor, cherry blossoms, cinematic",
    "masterpiece, cat girl, cozy cafe, warm lighting, slice of life",
]

def generate_image(prompt: str, index: int) -> str:
    payload = {
        "prompt": prompt,
        "negative_prompt": "(worst quality:1.4), deformed, extra fingers, watermark, nsfw",
        "steps": 25,
        "cfg_scale": 7,
        "width": 512,
        "height": 768,
        "sampler_name": "DPM++ 2M Karras",
        "restore_faces": False,
        "batch_size": 1,
    }
    response = requests.post(f"{SD_API}/sdapi/v1/txt2img", json=payload, timeout=120)
    response.raise_for_status()
    result = response.json()
    img_data = base64.b64decode(result["images"][0])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"anime_{ts}_{index:02d}.png"
    output_path.write_bytes(img_data)
    return str(output_path)

if __name__ == "__main__":
    print(f"[INFO] Generando {len(PROMPTS)} imágenes anime...")
    for i, prompt in enumerate(PROMPTS, 1):
        print(f"  [{i}/{len(PROMPTS)}] {prompt[:60]}...")
        path = generate_image(prompt, i)
        print(f"  [OK] Guardada: {path}")
    print(f"\n[OK] Todas las imagenes en: {OUTPUT_DIR}")
```

```bash
# Asegurarse de que SD WebUI está activo y ejecutar el script
cd ~/stacks/sd-webui && docker compose up -d
sleep 90  # esperar arranque completo

python3 ~/scripts/generate-anime-batch.py
```

---

## 19.7 Generación de Video con AnimateDiff

AnimateDiff es una extensión de ComfyUI que agrega **motion modules** a los modelos SD 1.5, permitiendo generar clips de video de 8–24 fotogramas a partir de un prompt de texto. Los clips son cortos (~1–3 segundos), pero la calidad del movimiento es notablemente fluida.

### 19.7.1 Requisitos de Memoria para AnimateDiff

AnimateDiff requiere significativamente más memoria que la generación de imágenes estáticas:

| Configuración | VRAM estimada | Tiempo/clip |
|--------------|--------------|------------|
| SD 1.5 + 8 frames, 512×512 | ~8 GB | 3–5 min |
| SD 1.5 + 16 frames, 512×512 | ~12 GB | 6–10 min |
| SD 1.5 + 24 frames, 512×512 | ~16 GB | 10–15 min |

> **ADVERTENCIA:** Con 64 GB de memoria unificada, estos valores son manejables, pero generar más de 16 frames a 512×512 puede causar que el sistema swap a disco — monitoree con `jtop` durante la generación.

### 19.7.2 Descargar el Motion Module de AnimateDiff

```bash
# AnimateDiff v3 motion module — el más compatible con SD 1.5 (~1.7 GB)
# NOTA: Verifique que la URL siga activa antes de ejecutar
wget -q --show-progress \
  "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v3.ckpt" \
  -O ~/models/animatediff/mm_sd_v15_v3.ckpt

echo "[OK] AnimateDiff motion module: $(du -h ~/models/animatediff/mm_sd_v15_v3.ckpt | cut -f1)"
```

### 19.7.3 Instalar el Nodo AnimateDiff en ComfyUI

```bash
# Acceder al contenedor ComfyUI para instalar el custom node
docker exec -it comfyui bash -c "
  cd /root/ComfyUI/custom_nodes && \
  git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git && \
  cd ComfyUI-AnimateDiff-Evolved && \
  pip install -r requirements.txt && \
  echo '[OK] AnimateDiff-Evolved instalado'
"

# Reiniciar ComfyUI para cargar el nuevo nodo
cd ~/stacks/comfyui
docker compose restart comfyui

# Esperar que reinicie
echo "Esperando reinicio de ComfyUI..."
until curl -sf http://localhost:8188 > /dev/null 2>&1; do
  sleep 5
  echo "  ..."
done
echo "[OK] ComfyUI reiniciado con AnimateDiff"
```

### 19.7.4 Workflow de AnimateDiff via API

ComfyUI permite enviar workflows completos como JSON via API, sin necesidad de la interfaz gráfica:

```python
#!/usr/bin/env python3
# ~/scripts/generate-animatediff.py
# Genera un video corto con AnimateDiff via API de ComfyUI
import requests
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

COMFYUI_API = "http://localhost:8188"
OUTPUT_DIR = Path.home() / "stacks/comfyui/output/videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Workflow de AnimateDiff (SD 1.5 + motion module)
WORKFLOW = {
    "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
    },
    "2": {
        "class_type": "ADE_AnimateDiffLoaderWithContext",
        "inputs": {
            "model": ["1", 0],
            "motion_model": "mm_sd_v15_v3.ckpt",
            "context_length": 16,
            "context_stride": 1,
            "context_overlap": 4,
            "closed_loop": False
        }
    },
    "3": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "a woman walking in a park, cherry blossoms, cinematic, smooth motion",
            "clip": ["1", 1]
        }
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "deformed, blurry, watermark, extra fingers, bad anatomy, nsfw",
            "clip": ["1", 1]
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 512, "height": 512, "batch_size": 16}
    },
    "6": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["2", 0],
            "positive": ["3", 0],
            "negative": ["4", 0],
            "latent_image": ["5", 0],
            "seed": 42,
            "steps": 20,
            "cfg": 7.5,
            "sampler_name": "euler_ancestral",
            "scheduler": "karras",
            "denoise": 1.0
        }
    },
    "7": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["6", 0], "vae": ["1", 2]}
    },
    "8": {
        "class_type": "VHS_VideoCombine",
        "inputs": {
            "images": ["7", 0],
            "frame_rate": 8,
            "loop_count": 0,
            "filename_prefix": "animatediff",
            "format": "video/h264-mp4",
            "pingpong": False,
            "save_output": True
        }
    }
}

def queue_prompt(workflow: dict) -> str:
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFYUI_API}/prompt", data=data)
    response = urllib.request.urlopen(req)
    result = json.loads(response.read())
    return result["prompt_id"]

def wait_for_completion(prompt_id: str, timeout: int = 600) -> bool:
    print(f"  [INFO] Prompt ID: {prompt_id}")
    start = time.time()
    while time.time() - start < timeout:
        response = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
        history = response.json()
        if prompt_id in history:
            status = history[prompt_id].get("status", {})
            if status.get("completed", False):
                return True
            if status.get("status_str") == "error":
                print("  [ERROR] Error en la generacion")
                return False
        time.sleep(5)
        elapsed = int(time.time() - start)
        print(f"  ... {elapsed}s transcurridos (timeout: {timeout}s)")
    return False

if __name__ == "__main__":
    print("[INFO] Iniciando generacion de video con AnimateDiff...")
    print("       Esto puede tardar 6-15 minutos en Jetson MAXN")
    print("")
    prompt_id = queue_prompt(WORKFLOW)
    if wait_for_completion(prompt_id):
        print(f"\n[OK] Video generado!")
        print(f"     Buscar en: ~/stacks/comfyui/output/")
        print(f"     Comando: ls -lh ~/stacks/comfyui/output/")
    else:
        print("\n[ERROR] Timeout o error en la generacion")
        print("        Revise los logs: docker logs comfyui --tail 50")
```

```bash
# Ejecutar la generación de video (asegúrese de que ComfyUI esté activo)
python3 ~/scripts/generate-animatediff.py
```

### 19.7.5 Convertir el Video a GIF para Compartir

```bash
# Convertir el MP4 generado a GIF (instalar ffmpeg si no está disponible)
# sudo apt install -y ffmpeg

# Localizar el video más reciente
ULTIMO_VIDEO=$(ls -t ~/stacks/comfyui/output/*.mp4 2>/dev/null | head -1)

if [ -n "$ULTIMO_VIDEO" ]; then
    GIF_OUTPUT="${ULTIMO_VIDEO%.mp4}.gif"
    ffmpeg -i "$ULTIMO_VIDEO" \
      -vf "fps=8,scale=512:-1:flags=lanczos,palettegen=stats_mode=full" \
      /tmp/palette.png -y
    ffmpeg -i "$ULTIMO_VIDEO" -i /tmp/palette.png \
      -filter_complex "fps=8,scale=512:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer" \
      "$GIF_OUTPUT" -y
    echo "[OK] GIF generado: $GIF_OUTPUT ($(du -h $GIF_OUTPUT | cut -f1))"
else
    echo "[WARN] No se encontro ningun archivo .mp4 en ~/stacks/comfyui/output/"
fi
```

---

## 19.8 PixArt-Alpha y Alternativas Ligeras

PixArt-Alpha es un modelo de difusión basado en transformers (no UNet) que produce imágenes de alta calidad con modelos de solo ~500 MB — ideal cuando la memoria es limitada o cuando los checkpoints SDXL son demasiado pesados.

### 19.8.1 Generación con PixArt via Diffusers

```bash
# Instalar diffusers en el venv de IA (o crear uno dedicado)
python3 -m venv ~/venvs/sdtools
source ~/venvs/sdtools/bin/activate
pip install --upgrade pip
pip install diffusers transformers accelerate torch

echo "[OK] Entorno sdtools listo"
```

```python
#!/usr/bin/env python3
# ~/scripts/generate-pixart.py
# Genera imágenes con PixArt-Alpha via Diffusers (sin Docker)
# Ventaja: modelo ~500 MB vs 2-7 GB de checkpoints SD
from diffusers import PixArtAlphaPipeline
import torch
from pathlib import Path
from datetime import datetime

# ⚠ Reemplaza HF_TOKEN con tu token si el modelo requiere autenticación
import os
HF_TOKEN = os.environ.get("HF_TOKEN", None)

OUTPUT_DIR = Path.home() / "projects/pixart-output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("[INFO] Cargando PixArt-Alpha (512px)...")
pipe = PixArtAlphaPipeline.from_pretrained(
    "PixArt-alpha/PixArt-XL-2-512x512",
    torch_dtype=torch.float16,
    use_auth_token=HF_TOKEN,
)
pipe = pipe.to("cuda")

PROMPTS = [
    "A serene mountain landscape at golden hour, photorealistic, 8k",
    "Ancient Japanese temple in autumn, fog, cinematic lighting",
]

for i, prompt in enumerate(PROMPTS, 1):
    print(f"[{i}/{len(PROMPTS)}] Generando: {prompt[:50]}...")
    image = pipe(
        prompt=prompt,
        negative_prompt="ugly, blurry, watermark, deformed",
        num_inference_steps=20,
        guidance_scale=4.5,
    ).images[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"pixart_{ts}_{i:02d}.png"
    image.save(path)
    print(f"  [OK] Guardada: {path}")

print(f"\n[OK] Imagenes en: {OUTPUT_DIR}")
```

```bash
# Ejecutar generación con PixArt
source ~/venvs/sdtools/bin/activate
python3 ~/scripts/generate-pixart.py
```

```
# Salida esperada
[INFO] Cargando PixArt-Alpha (512px)...
Downloading shards: 100%|██████████| 2/2 [03:45<00:00]
[1/2] Generando: A serene mountain landscape at golden hour...
  [OK] Guardada: /home/jetson/projects/pixart-output/pixart_20260629_142301_01.png
[2/2] Generando: Ancient Japanese temple in autumn...
  [OK] Guardada: /home/jetson/projects/pixart-output/pixart_20260629_142345_02.png

[OK] Imagenes en: /home/jetson/projects/pixart-output
```

---

## 19.9 Aliases y Scripts de Gestión

```bash
# Agregar aliases al ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ══════════════════════════════════════════════
# GENERACION DE IMAGENES Y VIDEO
# ══════════════════════════════════════════════

# Iniciar ComfyUI
alias start-comfyui='cd ~/stacks/comfyui && docker compose up -d && echo "[OK] ComfyUI iniciando en http://localhost:8188 (espere 60s)"'

# Detener ComfyUI
alias stop-comfyui='docker stop comfyui && echo "[OK] ComfyUI detenido"'

# Iniciar SD WebUI
alias start-sdwebui='cd ~/stacks/sd-webui && docker compose up -d && echo "[OK] SD WebUI iniciando en http://localhost:7860 (espere 90s)"'

# Detener SD WebUI
alias stop-sdwebui='docker stop sd-webui && echo "[OK] SD WebUI detenido"'

# Ver logs en tiempo real
alias logs-comfyui='docker logs comfyui --follow'
alias logs-sdwebui='docker logs sd-webui --follow'

# Ver GPU mientras genera (abrir en segunda terminal SSH)
alias monitor-gen='watch -n 2 "docker stats comfyui sd-webui --no-stream 2>/dev/null; echo; free -h | grep Mem"'

# Listar modelos instalados
alias list-models='echo "=== Checkpoints ==="; ls -lh ~/models/checkpoints/ 2>/dev/null; echo "=== LoRA ==="; ls -lh ~/models/loras/ 2>/dev/null; echo "=== VAE ==="; ls -lh ~/models/vae/ 2>/dev/null'

# Listar imágenes generadas (más recientes primero)
alias list-generated='ls -lt ~/stacks/comfyui/output/ ~/stacks/sd-webui/output/ 2>/dev/null | head -20'
EOF

source ~/.bash_aliases
echo "[OK] Aliases de generacion de imagenes cargados"
```

### 19.9.1 Script de Estado General

```bash
cat > ~/scripts/status-image-generation.sh << 'EOF'
#!/bin/bash
# Estado de los servicios de generación de imágenes

echo "══════════════════════════════════════════"
echo "  ESTADO — GENERACION DE IMAGENES/VIDEO"
echo "══════════════════════════════════════════"

echo ""
echo "── Contenedores activos ──"
COMFYUI_STATUS=$(docker inspect -f '{{.State.Status}}' comfyui 2>/dev/null || echo "no iniciado")
SDWEBUI_STATUS=$(docker inspect -f '{{.State.Status}}' sd-webui 2>/dev/null || echo "no iniciado")
printf "  %-20s %s\n" "ComfyUI (8188):" "$COMFYUI_STATUS"
printf "  %-20s %s\n" "SD WebUI (7860):" "$SDWEBUI_STATUS"

echo ""
echo "── Modelos instalados ──"
CHECKPOINTS=$(ls ~/models/checkpoints/*.safetensors 2>/dev/null | wc -l)
LORAS=$(ls ~/models/loras/*.safetensors 2>/dev/null | wc -l)
VAES=$(ls ~/models/vae/*.safetensors 2>/dev/null | wc -l)
ANIMATEDIFF=$(ls ~/models/animatediff/*.ckpt 2>/dev/null | wc -l)
printf "  %-20s %s checkpoints\n" "Checkpoints:" "$CHECKPOINTS"
printf "  %-20s %s LoRA\n" "LoRA:" "$LORAS"
printf "  %-20s %s VAE\n" "VAE:" "$VAES"
printf "  %-20s %s motion modules\n" "AnimateDiff:" "$ANIMATEDIFF"
printf "  %-20s %s\n" "Espacio total:" "$(du -sh ~/models/ 2>/dev/null | cut -f1)"

echo ""
echo "── Imagenes generadas ──"
COMFY_IMGS=$(find ~/stacks/comfyui/output -name "*.png" -o -name "*.mp4" 2>/dev/null | wc -l)
SDWEB_IMGS=$(find ~/stacks/sd-webui/output -name "*.png" 2>/dev/null | wc -l)
printf "  %-20s %s archivos\n" "ComfyUI output:" "$COMFY_IMGS"
printf "  %-20s %s archivos\n" "SD WebUI output:" "$SDWEB_IMGS"

echo ""
echo "── Uso de recursos ──"
free -h | grep "^Mem:"
docker stats --no-stream comfyui sd-webui 2>/dev/null

echo ""
echo "── Comandos disponibles ──"
echo "  start-comfyui / stop-comfyui"
echo "  start-sdwebui / stop-sdwebui"
echo "  logs-comfyui  / logs-sdwebui"
echo "  monitor-gen   / list-models"
EOF

chmod +x ~/scripts/status-image-generation.sh
echo "[OK] Script de estado listo"
```

---

## 19.10 Monitoreo Durante la Generación

La generación de imágenes es intensiva en GPU y memoria. Use estas herramientas en una segunda terminal SSH para monitorear el sistema mientras genera:

```bash
# Terminal 1 (donde corre la generación)
start-comfyui
# ... generar imágenes en la UI ...

# Terminal 2 (monitoreo — abrir nueva sesión SSH)
# Ver GPU, CPU y memoria del Jetson en tiempo real
jtop

# Ver logs del contenedor en tiempo real
docker logs comfyui --follow

# Monitoreo ligero de CPU/RAM de contenedores (refresco cada 2 segundos)
docker stats comfyui sd-webui

# Ver estadísticas de un solo frame (snapshot)
docker stats comfyui --no-stream
```

```
# Salida esperada de docker stats durante generación SDXL
CONTAINER ID   NAME        CPU %   MEM USAGE / LIMIT   MEM %   NET I/O
a3b4c5d6e7f8   comfyui     248%    11.2GiB / 62GiB     18.1%   ...
```

> **ATENCIÓN — RAM alta:** Si `MEM USAGE` supera 40 GB mientras genera, el sistema empezará a usar swap, ralentizando drásticamente la generación. En ese caso: reduzca el número de frames en AnimateDiff, o cambie a modelos SD 1.5 en lugar de SDXL, o detenga Ollama y otros servicios antes de generar.

### 19.10.1 Script de Pre-vuelo para Generación

```bash
cat > ~/scripts/preflight-image-gen.sh << 'EOF'
#!/bin/bash
# Pre-check antes de iniciar sesión de generación de imágenes pesada

echo "[INFO] Pre-check de generacion de imagenes..."

# Verificar modo energético
MODO=$(cat /sys/kernel/debug/bpmp/debug/clk/emc/state 2>/dev/null || nvpmodel -q 2>/dev/null | grep 'NV Power Mode' | awk '{print $NF}')
echo "  Modo energetico: $MODO"
echo "  [CONSEJO] Use 'pwr-maxn' para maxima velocidad de generacion"

# Verificar RAM disponible
RAM_LIBRE=$(free -g | awk '/^Mem:/ {print $7}')
echo "  RAM disponible: ${RAM_LIBRE} GB"
if [ "$RAM_LIBRE" -lt 20 ]; then
    echo "  [WARN] Menos de 20 GB disponibles — cierre otros servicios antes de generar"
fi

# Verificar espacio en disco
ESPACIO=$(df -BG ~ | awk 'NR==2 {gsub("G","",$4); print $4}')
echo "  Espacio en disco: ${ESPACIO} GB libres"
if [ "$ESPACIO" -lt 20 ]; then
    echo "  [WARN] Menos de 20 GB libres — puede quedarse sin espacio para modelos"
fi

# Listar servicios activos que usan memoria
echo ""
echo "  Servicios activos con RAM > 500 MB:"
docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}}" 2>/dev/null \
  | grep -v "0B / " || echo "    (ninguno)"

# Verificar checkpoints disponibles
echo ""
CHECKPOINTS=$(ls ~/models/checkpoints/*.safetensors 2>/dev/null)
if [ -z "$CHECKPOINTS" ]; then
    echo "  [ERROR] No hay checkpoints instalados"
    echo "          Ejecute: ~/scripts/download-sd-models.sh"
else
    echo "  Checkpoints disponibles:"
    ls -lh ~/models/checkpoints/*.safetensors | awk '{printf "    %s %s\n", $5, $9}' | xargs -I{} basename {}
fi

echo ""
echo "[OK] Pre-check completo"
EOF

chmod +x ~/scripts/preflight-image-gen.sh
```

---

## 19.11 Resolución de Problemas Frecuentes

### Error: "CUDA out of memory"

```bash
# Liberar memoria: detener todos los contenedores que usen GPU
docker stop comfyui sd-webui ollama 2>/dev/null || true

# Verificar cuánta memoria está libre ahora
free -h

# Reducir batch size en el workflow de ComfyUI:
# En el nodo KSampler → batch_size: 1 (no más de 1 imagen a la vez)
# En AnimateDiff → reducir frames de 16 a 8
```

### Error: "No module named animatediff"

```bash
# El custom node no cargó correctamente — reinstalar
docker exec -it comfyui bash -c "
  ls /root/ComfyUI/custom_nodes/ && \
  cd /root/ComfyUI/custom_nodes/ComfyUI-AnimateDiff-Evolved && \
  pip install -r requirements.txt 2>&1 | tail -5
"
docker compose -f ~/stacks/comfyui/docker-compose.yml restart comfyui
```

### La interfaz de ComfyUI no carga (timeout)

```bash
# Verificar que el contenedor está activo y cuál es el error
docker ps | grep comfyui
docker logs comfyui --tail 30

# Si el puerto 8188 está en uso por otro proceso
sudo lsof -i :8188
```

### Imágenes generadas muy oscuras o con colores mal

```bash
# Causa: VAE incorrecto o sin VAE configurado
# En SD WebUI: Settings → Stable Diffusion → SD VAE → seleccionar el .safetensors descargado
# En ComfyUI: agregar nodo VAELoader y conectarlo al decoder

# Verificar que el VAE está en el directorio correcto
ls -lh ~/models/vae/
```

---

## 19.12 Resumen del Capítulo

En este capítulo configuró un sistema completo de generación de imágenes y video en el Jetson AGX Orin:

| Componente | Función | Puerto | Estado |
|-----------|---------|--------|--------|
| ComfyUI | Workflows visuales de imagen/video | 8188 | `restart: "no"` |
| SD WebUI | Interfaz clásica txt2img / img2img | 7860 | `restart: "no"` |
| AnimateDiff | Módulo de video en ComfyUI | — | Nodo en ComfyUI |
| PixArt-Alpha | Modelo ligero vía Diffusers | — | Script Python |

**Modelos instalados:**
- SD 1.5 base — 2.1 GB — generación rápida
- Realistic Vision V6 — 2.1 GB — fotografías
- SDXL 1.0 — 6.9 GB — calidad máxima
- Anything V5 — 2.2 GB — estilo anime
- AnimateDiff MM v3 — 1.7 GB — generación de video

**Filosofía aplicada:**
- `restart: "no"` en ambos servicios — no arrancan solos al reiniciar el Jetson
- Modelos en `~/models/` compartidos entre ComfyUI y SD WebUI
- Aliases `start-comfyui` / `start-sdwebui` para iniciar manualmente
- Monitoreo con `jtop` y `docker stats` durante la generación

---

## VERIFICACIÓN CAPÍTULO 19

```bash
# Verificación completa del capítulo 19

echo "══════════════════════════════════════════════"
echo "  VERIFICACION — CAPITULO 19"
echo "══════════════════════════════════════════════"
echo ""

ERRORES=0

# Verificar directorios de modelos
for DIR in checkpoints loras vae embeddings animatediff; do
    if [ -d "$HOME/models/$DIR" ]; then
        printf "  [OK] ~/models/%-20s existe\n" "$DIR/"
    else
        printf "  [ERROR] ~/models/%-20s NO existe\n" "$DIR/"
        ERRORES=$((ERRORES + 1))
    fi
done

echo ""

# Verificar stacks
for STACK in comfyui sd-webui; do
    if [ -f "$HOME/stacks/$STACK/docker-compose.yml" ]; then
        printf "  [OK] ~/stacks/%-20s OK\n" "$STACK/"
    else
        printf "  [ERROR] ~/stacks/%-20s SIN docker-compose.yml\n" "$STACK/"
        ERRORES=$((ERRORES + 1))
    fi
done

echo ""

# Verificar que al menos hay 1 checkpoint
CHECKPOINTS=$(ls ~/models/checkpoints/*.safetensors 2>/dev/null | wc -l)
if [ "$CHECKPOINTS" -gt 0 ]; then
    echo "  [OK] $CHECKPOINTS checkpoint(s) instalado(s)"
else
    echo "  [ERROR] Sin checkpoints — ejecute: ~/scripts/download-sd-models.sh"
    ERRORES=$((ERRORES + 1))
fi

echo ""

# Verificar aliases
for ALIAS in start-comfyui stop-comfyui start-sdwebui stop-sdwebui logs-comfyui logs-sdwebui; do
    if grep -q "$ALIAS" ~/.bash_aliases 2>/dev/null; then
        printf "  [OK] alias %-25s definido\n" "$ALIAS"
    else
        printf "  [WARN] alias %-25s no encontrado en ~/.bash_aliases\n" "$ALIAS"
    fi
done

echo ""

# Verificar scripts
for SCRIPT in download-sd-models.sh status-image-generation.sh preflight-image-gen.sh; do
    if [ -x "$HOME/scripts/$SCRIPT" ]; then
        printf "  [OK] ~/scripts/%-35s ejecutable\n" "$SCRIPT"
    else
        printf "  [WARN] ~/scripts/%-35s no encontrado\n" "$SCRIPT"
    fi
done

echo ""

# Test rápido: iniciar ComfyUI y verificar respuesta HTTP
echo "── Test de arranque ComfyUI (30 segundos) ──"
cd ~/stacks/comfyui && docker compose up -d 2>/dev/null
INTENTOS=0
until curl -sf http://localhost:8188 > /dev/null 2>&1; do
    sleep 5
    INTENTOS=$((INTENTOS + 1))
    if [ $INTENTOS -ge 6 ]; then
        echo "  [WARN] ComfyUI no respondio en 30s — revise: docker logs comfyui --tail 20"
        break
    fi
done
if curl -sf http://localhost:8188 > /dev/null 2>&1; then
    echo "  [OK] ComfyUI responde en http://localhost:8188"
fi
docker stop comfyui 2>/dev/null

echo ""
if [ $ERRORES -eq 0 ]; then
    echo "[OK] Capitulo 19 completado sin errores criticos"
else
    echo "[WARN] $ERRORES error(es) encontrado(s) — revise los items marcados con [ERROR]"
fi
echo ""
echo "Próximo capítulo: Capítulo 20 — Despliegue en Producción (Hardening, UFW, systemd)"
```

---

*Capítulo 19 completado. Siguiente: Capítulo 20 — Despliegue en Producción.*
