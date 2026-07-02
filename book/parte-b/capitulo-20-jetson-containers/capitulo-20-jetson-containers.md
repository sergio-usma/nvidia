# Capítulo 20 — jetson-containers: El Ecosistema de Contenedores de NVIDIA

## Introducción

Cuando intente instalar Whisper, Stable Diffusion, o cualquier framework de IA usando `pip install` en el Jetson, encontrará uno de estos problemas:

- El paquete no existe para ARM64
- Existe pero sin soporte CUDA para Jetson
- Se instala pero falla en tiempo de ejecución porque las librerías CUDA no coinciden
- La compilación desde fuente requiere horas y puede fallar por incompatibilidades de compilador

**jetson-containers** resuelve todos estos problemas. Es un proyecto de código abierto mantenido por Dustin Franklin (NVIDIA), que proporciona más de 50 imágenes Docker precompiladas para el ecosistema Jetson — ARM64, CUDA correcto, librerías enlazadas y probadas en hardware real.

El resultado: en lugar de compilar Whisper desde fuente (3–4 horas), ejecuta un `docker pull` de 2 minutos y tiene STT funcionando.

**Prerrequisitos de este capítulo:**
- Capítulo 8 completado (Docker Engine + NVIDIA Container Toolkit)
- Al menos 100 GB libres en almacenamiento (las imágenes son grandes)

**Tiempo estimado:** 60–90 minutos (mayor parte es descarga de imágenes)

---

## 18.1 Por qué no usar Docker Hub genérico

<!-- INFOGRAFÍA: Por Qué jetson-containers en Lugar de Docker Hub Genérico — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


Las imágenes de Docker Hub estándar (como `openai/whisper` o `pytorch/pytorch`) se compilan para **x86_64 Linux**. El Jetson tiene una arquitectura completamente diferente:

```
┌────────────────────────────────────────────────────────────┐
│                  Diferencia de arquitectura                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Servidor x86_64 / GPU discreta:                           │
│  ├─ CPU: x86_64 (Intel/AMD)                                │
│  ├─ GPU: PCIe (VRAM separada)                              │
│  ├─ Driver: NVIDIA 550.x (datacenter)                      │
│  └─ CUDA: 12.x genérico                                    │
│                                                            │
│  NVIDIA Jetson AGX Orin:                                   │
│  ├─ CPU: ARM64 (Cortex-A78AE)                              │
│  ├─ GPU: Ampere sm_87 (memoria UNIFICADA)                  │
│  ├─ Driver: L4T r39.2 (Tegra-specific)                     │
│  └─ CUDA: 13.2.1 con librerías Tegra                       │
│                                                            │
│  → Una imagen x86 no puede ejecutarse en ARM64             │
│  → Una imagen ARM64 genérica no tiene soporte CUDA Tegra   │
│  → Solo imágenes compiladas para L4T r39.2 funcionan       │
└────────────────────────────────────────────────────────────┘
```

### 18.1.1 ¿Qué hace `jetson-containers` diferente?

1. **Compilación nativa ARM64** — no emulación
2. **CUDA con librerías Tegra** — incluye `libcuda.so.1`, `libcurand`, `libcudnn` para Jetson
3. **Tags específicos por L4T** — `r36.4.0` para JP 6.2.2, `r39.2.0` para JP 7.2
4. **Probadas en hardware real** — el mantenedor tiene Jetson AGX Orin
5. **Actualizaciones activas** — el repositorio se actualiza con cada JetPack major

---

## 18.2 Sistema de Tags de jetson-containers

Cada imagen de jetson-containers sigue el esquema:

```
dustynv/<nombre-servicio>:<versión>-r<L4T-version>
```

Ejemplos:
- `dustynv/faster-whisper:1.0.3-r36.4.0` — JP 6.2.2
- `dustynv/faster-whisper:1.0.3-r39.2.0` — JP 7.2 [REQUIERE VERIFICACIÓN]
- `dustynv/kokoro-tts:r39.2.0` — JP 7.2
- `dustynv/ollama:r39.2.0` — JP 7.2

### 18.2.1 Cómo verificar tags disponibles para JP 7.2

```bash
# Verificar tags disponibles para un contenedor específico
# Reemplazar "faster-whisper" con el nombre del contenedor que necesite
curl -s "https://hub.docker.com/v2/repositories/dustynv/faster-whisper/tags/?page_size=20" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('Tags disponibles para faster-whisper:')
for tag in sorted([t['name'] for t in data.get('results', [])], reverse=True):
    print(f'  {tag}')
"
```

```
# Salida esperada
Tags disponibles para faster-whisper:
  1.0.3-r39.2.0
  1.0.3-r36.4.0
  1.0.3-r36.3.0
  ...
```

```bash
# Script para verificar qué contenedores ya tienen tag r39.2.0
CONTENEDORES="faster-whisper kokoro-tts piper-tts ollama whisper-trt comfyui"

echo "Estado de tags r39.2.0 para JP 7.2:"
for c in $CONTENEDORES; do
  STATUS=$(curl -s "https://hub.docker.com/v2/repositories/dustynv/$c/tags/?page_size=30" \
    | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    tags = [t['name'] for t in data.get('results', [])]
    if any('r39.2' in t for t in tags):
        print('[OK] r39.2.x disponible')
    else:
        latest = tags[0] if tags else 'no tags'
        print(f'[WARN]  Solo hasta {latest}')
except:
    print('[ERROR] Error consultando')
" 2>/dev/null)
  printf "  %-25s %s\n" "$c:" "$STATUS"
done
```

### 18.2.2 Tag de Fallback

Si `r39.2.0` no existe para un contenedor específico, use el tag `r36.4.0` con precaución:

```bash
# ADVERTENCIA: r36.4.0 fue compilado para JP 6.2.2 / L4T r36.x / Ubuntu 22.04
# En JP 7.2 / Ubuntu 24.04 puede funcionar o no, según las dependencias del servicio
# Siempre pruebe en un entorno de test antes de usar en producción
docker pull dustynv/<servicio>:r36.4.0

# Si funciona, documente con: [PROBADO JP 6.2, funciona en JP 7.2]
# Si falla, documente con: [REQUIERE VERSIÓN r39.2.0 — pendiente release]
```

---

## 18.3 Catálogo de Contenedores más Relevantes

> **NOTA — Compatibilidad con JP 7.2:** Los tags `r39.2.0` corresponden a JetPack 7.2 (L4T r39.x). Siempre verifique la disponibilidad del tag antes de hacer `docker pull` usando el script de la sección 18.2.1. Si `r39.2.0` no está disponible, use `r36.4.0` (JP 6.2) como fallback provisional — la mayoría de contenedores son retrocompatibles, aunque algunas funcionalidades CUDA 13 pueden no estar optimizadas.

> **NOTA — Conectar desde el IDE antes de cada proyecto:** Antes de ejecutar cualquier mini-proyecto de este capítulo, conéctese al Jetson desde VSCode con la extensión Remote SSH (Capítulo 17). Esto le permite editar los scripts directamente en el Jetson y ver los logs en tiempo real en la terminal integrada.

### 18.3.1 Modelos de Lenguaje y Servidores de Inferencia

| Contenedor | Descripción | Puerto | JP 7.2 | Uso en el libro |
|-----------|-------------|--------|--------|----------------|
| `dustynv/ollama` | Servidor Ollama nativo | 11434 | ✓ Verificado | Caps 12, proyectos |
| `dustynv/llama_cpp` | llama.cpp con GPU | 8080 | ✓ Verificado | Alt. a native llama.cpp |
| `dustynv/vllm` | vLLM para Jetson | 8000 | ✓ Verificado | Alt. a SBSA upstream |
| `dustynv/text-generation-webui` | Interfaz web oobabooga | 7860 | Pendiente r39.x | Experimentación |
| `dustynv/lm-benchmark` | Benchmark de LLMs | — | Pendiente r39.x | Testing |

### 18.3.2 Speech-to-Text (STT)

| Contenedor | Descripción | Puerto | JP 7.2 | Uso |
|-----------|-------------|--------|--------|-----|
| `dustynv/faster-whisper` | Faster-Whisper + CTranslate2 | 8000 | ✓ Verificado | **Caps 19, 24** |
| `dustynv/whisper-trt` | Whisper + TensorRT | 8000 | Pendiente r39.x | Mejor latencia |
| `dustynv/whisper` | Whisper original OpenAI | 8000 | ✓ Verificado | Compatible |
| `dustynv/speaches` | STT compatible API OpenAI | 8000 | ✓ Verificado | **Cap 24** |

> **Recomendación:** Use `faster-whisper` para transcripción de archivos y `speaches` para voz en tiempo real (streaming optimizado).

### 18.3.3 Text-to-Speech (TTS)

| Contenedor | Descripción | Puerto | JP 7.2 | Voces |
|-----------|-------------|--------|--------|-------|
| `dustynv/kokoro-tts` | Kokoro TTS — alta calidad | 8880 | ✓ Verificado | af_bella, bm_george |
| `dustynv/piper-tts` | Piper — offline, ultrarrápido | 10200 | ✓ Verificado | Español, inglés, +40 idiomas |
| `dustynv/speaches` | STT+TTS integrado | 8000 | ✓ Verificado | — |

> **Recomendación:** `kokoro-tts` para calidad (pódcast, presentaciones); `piper-tts` para velocidad (<200ms, ideal para asistente de voz).

### 18.3.4 Visión Computacional

| Contenedor | Descripción | Puerto | Uso |
|-----------|-------------|--------|-----|
| `dustynv/stable-diffusion-webui` | Generación de imágenes SD | 7860 | Creación de contenido |
| `dustynv/comfyui` | ComfyUI — workflow visual | 8188 | Pipelines imagen |
| `dustynv/vila` | Multimodal LLM de NVIDIA | 8000 | Análisis de imagen |
| `dustynv/nanoowl` | Object detection zero-shot | — | Robótica |
| `dustynv/nanosam` | Segment Anything Model | — | Visión |

### 18.3.5 Embeddings y RAG

| Contenedor | Descripción | Puerto | Uso |
|-----------|-------------|--------|-----|
| `dustynv/nanodb` | Vector DB embebida para Jetson | 7860 | **Cap 25** |
| `dustynv/clip-trt` | CLIP multimodal (TensorRT) | — | Embeddings imagen |
| `dustynv/text-embeddings-inference` | Embeddings texto vía API | 8080 | RAG |

### 18.3.6 Robótica y ROS

| Contenedor | Descripción | Uso |
|-----------|-------------|-----|
| `dustynv/ros:humble` | ROS 2 Humble | Robótica |
| `dustynv/ros:iron` | ROS 2 Iron | Robótica |
| `dustynv/isaac-ros-visual-slam` | Visual SLAM | Navegación autónoma |

### 18.3.7 Herramientas de Desarrollo

| Contenedor | Descripción | Puerto |
|-----------|-------------|--------|
| `dustynv/jupyterlab` | JupyterLab con CUDA | 8888 |
| `dustynv/l4t-ml` | PyTorch + scikit-learn + Jupyter | 8888 |
| `dustynv/llama-factory` | Fine-tuning de LLMs en Jetson | — |
| `dustynv/homeassistant-core` | Home Assistant | 8123 |

---

## 18.4 Mapa de Puertos — Referencia Completa

<!-- INFOGRAFÍA: Mapa de Puertos — Todos los Servicios del Jetson — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


Para evitar conflictos entre los servicios de inferencia y los contenedores de proyectos avanzados:

```
┌───────────────────────────────────────────────────────────────┐
│               MAPA DE PUERTOS — JETSON AGX ORIN               │
├─────────┬─────────────────────────────────────────────────────┤
│ Puerto  │ Servicio                                             │
├─────────┼─────────────────────────────────────────────────────┤
│  11434  │ Ollama (Caps 9, 12 y proyectos)                     │
│  8000   │ vLLM (Cap 9) / faster-whisper / speaches            │
│  8080   │ llama.cpp (Cap 9) / text-embeddings-inference       │
│  3000   │ Open WebUI (Cap 14)                                 │
│  18789  │ OpenClaw / NemoClaw (Caps 12-13)                    │
├─────────┼─────────────────────────────────────────────────────┤
│  8880   │ kokoro-tts (Cap 29 — TTS alta calidad)              │
│  10200  │ piper-tts (Cap 29 — TTS rápido)                     │
│  8888   │ JupyterLab (desarrollo via SSH tunnel)              │
│  8188   │ ComfyUI (generación de imágenes)                    │
│  7860   │ Stable Diffusion / nanoDB WebUI                     │
│  8123   │ Home Assistant (IoT)                                │
│  9000   │ RAG API custom (FastAPI — Cap 25)                   │
└─────────┴─────────────────────────────────────────────────────┘

REGLA: Nunca más de 2 contenedores GPU activos simultáneamente
        (excepto en el asistente de voz — modelos pequeños)
```

---

## 18.5 Tutorial Completo — Primer Contenedor: faster-whisper

Este tutorial completo le enseña el ciclo de vida de cualquier contenedor de jetson-containers: pull → verificar → ejecutar → probar → detener → limpiar.

### 18.5.1 Verificar el Tag Correcto para JP 7.2

```bash
# Verificar tags disponibles de faster-whisper
curl -s "https://hub.docker.com/v2/repositories/dustynv/faster-whisper/tags/?page_size=10" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('Tags de faster-whisper:')
for t in data.get('results', []):
    print(f\"  {t['name']} ({t['full_size'] // 1024 // 1024} MB)\")
"
```

```
# Salida esperada
Tags de faster-whisper:
  1.0.3-r39.2.0 (2847 MB)
  1.0.3-r36.4.0 (2614 MB)
  ...
```

### 18.5.2 Descargar la Imagen

```bash
# Descargar la imagen para JP 7.2 (tarda 5-10 min dependiendo de la conexión)
docker pull dustynv/faster-whisper:1.0.3-r39.2.0
```

```
# Salida esperada (durante la descarga)
1.0.3-r39.2.0: Pulling from dustynv/faster-whisper
Digest: sha256:...
Status: Downloaded newer image for dustynv/faster-whisper:1.0.3-r39.2.0
docker.io/dustynv/faster-whisper:1.0.3-r39.2.0
```

```bash
# Verificar que la imagen está disponible
docker images | grep faster-whisper
```

```
# Salida esperada
dustynv/faster-whisper   1.0.3-r39.2.0   <id>    <date>   2.85GB
```

### 18.5.3 Ejecutar faster-whisper

```bash
# Iniciar el servidor faster-whisper en modo daemon
docker run -d \
  --name faster-whisper \
  --runtime nvidia \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -e WHISPER_MODEL=base.en \
  dustynv/faster-whisper:1.0.3-r39.2.0
```

```
# Salida esperada
<container_id>
```

```bash
# Ver los logs de inicio (espere 20-30 segundos para que cargue el modelo)
docker logs -f faster-whisper
```

```
# Salida esperada en los logs
Loading model base.en...
Model loaded. Starting server on 0.0.0.0:8000
Uvicorn running on http://0.0.0.0:8000
```

> Presione `Ctrl+C` para dejar de seguir los logs (el contenedor sigue ejecutándose).

**Modelos disponibles para faster-whisper:**

| Modelo | Tamaño | Velocidad | Uso de RAM | Idiomas |
|--------|--------|-----------|-----------|---------|
| `tiny` | 39 MB | ~80x real | ~1 GB | Básico |
| `base` | 74 MB | ~40x real | ~1 GB | Básico |
| `base.en` | 74 MB | ~50x real | ~1 GB | Solo inglés |
| `small` | 244 MB | ~15x real | ~2 GB | Buenos |
| `medium` | 769 MB | ~5x real | ~3 GB | Muy buenos |
| `large-v3` | 1.5 GB | ~2x real | ~5 GB | Excelentes |
| `large-v3-turbo` | 809 MB | ~4x real | ~3 GB | Mejores calidad/vel |

> Para español, use `medium` o `large-v3`. Para inglés exclusivamente, `base.en` ofrece excelente relación velocidad/calidad.

### 18.5.4 Probar la Transcripción con su Propia Voz

El mejor audio de prueba es **una grabación real suya**: el modelo reconocerá su acento y cadencia natural, lo que hace la prueba mucho más útil que un tono generado artificialmente.

**Paso 1 — Grabar ~2 minutos con su celular:**
1. Abra la app de grabadora de su teléfono
2. Grabe ~2 minutos hablando en español (puede leer en voz alta cualquier texto)
3. Exporte el archivo como MP3 o M4A
4. Transfiera al Jetson via SCP desde Windows:

```powershell
# En Windows PowerShell — transferir el audio al Jetson
scp C:\Users\TuUsuario\Downloads\mi_audio.mp3 jetson:~/jetson-ai-data/audio/
```

**Paso 2 — Convertir a WAV y transcribir:**

```bash
# Instalar ffmpeg para conversión de formatos
sudo apt install -y ffmpeg

# Convertir MP3/M4A a WAV 16kHz mono (formato óptimo para Whisper)
ffmpeg -i ~/jetson-ai-data/audio/mi_audio.mp3 \
  -ar 16000 -ac 1 -f wav \
  ~/jetson-ai-data/audio/mi_audio.wav

# Transcribir con faster-whisper (large-v3 para mejor calidad)
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F "file=@$HOME/jetson-ai-data/audio/mi_audio.wav" \
  -F "model=large-v3" \
  -F "language=es" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('text',''))"
```

```
# Salida esperada (ejemplo con audio real):
Hola, estoy probando el sistema de transcripción de voz en el Jetson AGX Orin.
Este es un audio de prueba grabado con mi celular para verificar que faster-whisper
funciona correctamente con español latinoamericano.
```

> **Fallback (solo si no tiene teléfono disponible):** Genere un audio sintético con texto de muestra:
> ```bash
> sudo apt install -y espeak
> espeak -v es-la -s 130 "El Jetson AGX Orin tiene sesenta y cuatro gigabytes de memoria unificada" \
>   --stdout > /tmp/prueba_sintetica.wav
> ```
> El audio sintético es menos representativo pero sirve para verificar que el servidor responde.

### 18.5.5 Script Python de Transcripción Completa

```python
# test_faster_whisper.py
import requests
import os

def transcribir(ruta_audio: str, modelo: str = "base.en", idioma: str = None) -> dict:
    """Transcribe audio usando el servidor faster-whisper local."""
    
    if not os.path.exists(ruta_audio):
        return {"error": f"Archivo no encontrado: {ruta_audio}"}
    
    with open(ruta_audio, "rb") as f:
        files = {"file": (os.path.basename(ruta_audio), f, "audio/wav")}
        data = {"model": modelo}
        if idioma:
            data["language"] = idioma
        
        resp = requests.post(
            "http://localhost:8000/v1/audio/transcriptions",
            files=files,
            data=data,
            timeout=300  # 5 min timeout para audios largos
        )
    
    return resp.json()

# Ejemplo de uso
resultado = transcribir("/tmp/test_audio.wav", modelo="base.en")
print(f"Transcripción: {resultado.get('text', 'Sin resultado')}")
```

### 18.5.6 Detener y Limpiar

```bash
# Detener el contenedor (el modelo descargado permanece en el caché)
docker stop faster-whisper

# Si quiere eliminarlo completamente
docker rm faster-whisper

# Verificar que no hay contenedores activos
docker ps
```

```
# Salida esperada
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
(tabla vacía)
```

---

## 18.6 Tutorial Completo — Second Contenedor: kokoro-tts

### 18.6.1 Descargar y Ejecutar kokoro-tts

```bash
# Verificar tag disponible primero
curl -s "https://hub.docker.com/v2/repositories/dustynv/kokoro-tts/tags/?page_size=5" \
  | python3 -c "import json,sys; [print(t['name']) for t in json.load(sys.stdin)['results']]"
```

```bash
# Ejecutar kokoro-tts (descarga ~800 MB)
docker run -d \
  --name kokoro-tts \
  --runtime nvidia \
  --restart no \
  --network host \
  dustynv/kokoro-tts:r39.2.0
```

```bash
# Esperar que inicie (10-20 segundos)
docker logs -f kokoro-tts &
sleep 15
kill %1 2>/dev/null
```

### 18.6.2 Probar Síntesis de Voz

```bash
# Sintetizar texto a audio
curl -X POST http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hola, soy el asistente del Jetson AGX Orin. Estoy funcionando correctamente.",
    "voice": "af_bella",
    "response_format": "wav"
  }' \
  --output /tmp/salida_tts.wav

# Verificar que el archivo se generó
ls -lh /tmp/salida_tts.wav
```

```
# Salida esperada
-rw-r--r-- 1 jetson jetson 87K Jun 28 10:00 /tmp/salida_tts.wav
```

```bash
# Reproducir si tiene altavoz conectado
aplay /tmp/salida_tts.wav
```

**Voces disponibles en kokoro-tts:**

| Voz | Género | Idioma | Uso recomendado |
|-----|--------|--------|----------------|
| `af_bella` | F | EN (American) | Pódcast host 1 |
| `bm_george` | M | EN (British) | Pódcast host 2 |
| `af_sarah` | F | EN | Asistente |
| `am_michael` | M | EN (American) | Narrativa |
| `es_*` | Varios | ES | Español (verificar disponibilidad) |

```bash
# Listar voces disponibles en el servidor
curl -s http://localhost:8880/v1/voices | python3 -m json.tool
```

### 18.6.3 Limpiar Después del Mini-Proyecto

```bash
# Detener y eliminar el contenedor kokoro-tts
docker stop kokoro-tts && docker rm kokoro-tts

# Verificar que se liberó la memoria
free -h | awk '/^Mem:/{printf "RAM libre: %s de %s\n", $7, $2}'
# Esperado: RAM libre: ~58 GB de 62.7 GB (solo OS base activo)
```

> **Regla de trabajo con jetson-containers:** Siempre que termine un mini-proyecto, ejecute la limpieza antes de iniciar el siguiente contenedor. La memoria unificada del Jetson se comparte entre todos los procesos — un contenedor olvidado puede consumir varios GB silenciosamente.

---

## 18.7 Gestión de Imágenes y Espacio en Disco

Las imágenes de jetson-containers son grandes (1–5 GB cada una). Gestione el espacio con cuidado.

### 18.7.1 Monitorear Uso de Espacio

```bash
# Ver espacio total de Docker
docker system df

# Ver imágenes ordenadas por tamaño (de mayor a menor)
docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}" \
  | sort -t$'\t' -k2 -h -r \
  | column -t
```

```
# Ejemplo de salida
REPOSITORIO:TAG                              TAMAÑO
ghcr.io/nvidia-ai-iot/vllm:latest-jetson    12.3GB
dustynv/faster-whisper:1.0.3-r39.2.0        2.85GB
dustynv/kokoro-tts:r39.2.0                  1.24GB
```

### 18.7.2 Limpieza Selectiva

```bash
# Eliminar una imagen específica
docker rmi dustynv/faster-whisper:1.0.3-r39.2.0

# Eliminar todas las imágenes no usadas por contenedores activos
docker image prune -a -f

# Limpieza profunda (imágenes + volúmenes + redes + caché de build)
# ¡CUIDADO! Esto elimina TODO. Solo si necesita recuperar mucho espacio.
# docker system prune -a -f
```

### 18.7.3 Script de Estado del Ecosistema jetson-containers

```bash
# Crear el script
cat > ~/scripts/jc-status.sh << 'EOF'
#!/usr/bin/env bash
# jc-status.sh — Estado del ecosistema jetson-containers

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       ESTADO DEL ECOSISTEMA JETSON-CONTAINERS             ║"
echo "╚═══════════════════════════════════════════════════════════╝"

echo ""
echo "── Imagenes dustynv descargadas ──"
IMAGENES=$(docker images | grep dustynv | wc -l)
if [ "$IMAGENES" -eq 0 ]; then
  echo "  (ninguna)"
else
  docker images | grep dustynv \
    | awk '{printf "  %-45s %s\n", $1":"$2, $7" "$8}'
fi

echo ""
echo "── Imagenes NVIDIA AI IoT descargadas ──"
docker images | grep "nvidia-ai-iot" \
  | awk '{printf "  %-45s %s\n", $1":"$2, $7" "$8}' \
  || echo "  (ninguna)"

echo ""
echo "── Contenedores de proyectos activos ──"
ACTIVOS=$(docker ps --format "{{.Names}}" | grep -E "faster-whisper|kokoro|piper|speaches|comfyui|stable|vila|nanodb|llama-factory")
if [ -z "$ACTIVOS" ]; then
  echo "  (ninguno activo)"
else
  echo "$ACTIVOS" | while read nombre; do
    STATUS=$(docker inspect --format "{{.State.Status}}" "$nombre" 2>/dev/null)
    printf "  [OK] %-30s %s\n" "$nombre" "$STATUS"
  done
fi

echo ""
echo "── Espacio Docker en disco ──"
docker system df --format "table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null \
  | awk 'NR==1{printf "  %-15s %-12s %s\n", $1, $2, $3} NR>1{printf "  %-15s %-12s %s\n", $1, $2, $3}'

echo ""
echo "─────────────────────────────────────────────────────────────"
EOF
chmod +x ~/scripts/jc-status.sh
```

```bash
# Agregar alias a ~/.bash_aliases
echo "alias jc-status='~/scripts/jc-status.sh'" >> ~/.bash_aliases
source ~/.bash_aliases || source ~/.bashrc
```

---

## 18.8 Script de Limpieza de Contenedores de Proyectos

```bash
# Crear el script de limpieza
cat > ~/scripts/clean-ai-containers.sh << 'EOF'
#!/usr/bin/env bash
# clean-ai-containers.sh — Detiene y elimina contenedores de proyectos de IA

echo "── Limpieza de contenedores de proyectos ──"

# Contenedores de proyectos de IA (no tocar vllm/llama.cpp/ollama del cap 9)
AI_KEYWORDS="faster-whisper|kokoro-tts|kokoro|piper-tts|piper|speaches|comfyui|stable-diff|stable_diff|vila|homeassistant|home-assistant|llama-factory|jupyterlab|nanodb|clip|whisper"

docker ps --format "{{.Names}}" | grep -E "$AI_KEYWORDS" | while read nombre; do
  echo "  Deteniendo: $nombre..."
  docker stop "$nombre" && docker rm "$nombre"
done

echo ""
echo "── Liberando cache del sistema ──"
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

echo ""
echo "── Estado final ──"
RESTANTES=$(docker ps --format "{{.Names}}" | grep -E "$AI_KEYWORDS" | wc -l)
if [ "$RESTANTES" -eq 0 ]; then
  echo "  [OK] Todos los contenedores de proyectos detenidos"
else
  echo "  [WARN] Quedan $RESTANTES contenedores activos"
fi

free -h | awk '/^Mem:/{printf "  RAM libre: %s de %s total\n", $7, $2}'
echo ""
echo "Para reducir consumo: pwr-15w"
EOF

chmod +x ~/scripts/clean-ai-containers.sh
```

```bash
# Agregar alias a ~/.bash_aliases
echo "alias clean-ai-containers='~/scripts/clean-ai-containers.sh'" >> ~/.bash_aliases
source ~/.bash_aliases || source ~/.bashrc
```

---

## 18.9 Uso de la CLI Oficial jetson-containers (Opcional)

Además de los comandos `docker` manuales, el proyecto ofrece una CLI que automatiza la construcción local desde código fuente.

```bash
# Instalar la CLI de jetson-containers
sudo apt install -y python3-pip python3-venv
pip3 install --user jetson-containers
```

```bash
# Listar paquetes disponibles
jetson-containers list
```

```bash
# Ejecutar un contenedor con la CLI (manejo automático de tags)
# (Solo si build local es necesario — para la mayoría de usos, docker pull es suficiente)
jetson-containers run dustynv/faster-whisper
```

> **Recomendación:** Para los pipelines de , use `docker pull` y `docker run` directamente. La CLI `jetson-containers` es más útil para construir imágenes personalizadas o cuando el tag precompilado no existe.

---

## 18.10 Prerrequisito Memory Check por Pipeline

Antes de cada pipeline de , valide la memoria disponible:

```bash
# Funcion de verificacion — agregar a ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# Verifica RAM libre y temperatura antes de cargar modelos grandes
# Uso: check-ready [gb_minimos] [nombre-del-proyecto]
check-ready() {
    local min_gb=${1:-20}
    local proyecto=${2:-"este proyecto"}

    local libre=$(awk '/MemAvailable/{printf "%.0f", $2/1024/1024}' /proc/meminfo)
    local temp=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "%.0f", $1/1000}')
    local ok=true

    echo "── Verificacion pre-carga: $proyecto ──"

    if [ "$libre" -lt "$min_gb" ]; then
        echo "  [WARN] RAM libre: ${libre} GB (minimo ${min_gb} GB)"
        echo "      Ejecute: clean-ai-containers && pwr-15w && sleep 5"
        ok=false
    else
        echo "  [OK] RAM libre: ${libre} GB"
    fi

    if [ -n "$temp" ] && [ "$temp" -gt 75 ]; then
        echo "  [WARN] Temperatura: ${temp}C (limite: 75C)"
        echo "      Espere que enfrie antes de cargar modelos"
        ok=false
    elif [ -n "$temp" ]; then
        echo "  [OK] Temperatura: ${temp}C"
    fi

    if [ "$ok" = true ]; then
        echo "  [OK] Sistema listo"
        return 0
    else
        return 1
    fi
}
EOF
source ~/.bash_aliases || source ~/.bashrc
```

```bash
# Uso al inicio de cada proyecto con modelos grandes
check-ready 20 "PDF-to-podcast"
```

---

## 18.11 Verificación Final del Capítulo

```bash
# Verificación de configuración de jetson-containers
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   VERIFICACIÓN CAPÍTULO 18 — JETSON-CONTAINERS             ║"
echo "╚══════════════════════════════════════════════════════════╝"

echo ""
echo "── Docker operativo ──"
docker info --format "  [OK] Docker {{.ServerVersion}} ({{.OSType}}/{{.Architecture}})" 2>/dev/null \
  || echo "  [ERROR] Docker no accesible"

echo ""
echo "── NVIDIA runtime ──"
docker info 2>/dev/null | grep -qi nvidia \
  && echo "  [OK] Runtime nvidia disponible" \
  || echo "  [WARN]  Runtime nvidia no configurado (ver Capítulo 8)"

echo ""
echo "── Imágenes disponibles ──"
TOTAL_DUSTYNV=$(docker images | grep -c dustynv 2>/dev/null || echo "0")
TOTAL_NVIDIA=$(docker images | grep -c "nvidia-ai-iot" 2>/dev/null || echo "0")
echo "  Imágenes dustynv: $TOTAL_DUSTYNV"
echo "  Imágenes nvidia-ai-iot: $TOTAL_NVIDIA"

echo ""
echo "── Conectividad a Docker Hub (para pulls futuros) ──"
curl -s --max-time 5 "https://hub.docker.com/v2/repositories/dustynv/" > /dev/null \
  && echo "  [OK] Docker Hub accesible" \
  || echo "  [WARN]  Sin acceso a Docker Hub — verifique conexión de red"

echo ""
echo "── Scripts de gestion ──"
[ -f ~/scripts/clean-ai-containers.sh ] \
  && echo "  [OK] clean-ai-containers.sh" \
  || echo "  o  clean-ai-containers.sh no instalado (ver §18.8)"

echo ""
echo "── Espacio disponible ──"
df -h / | awk 'NR==2{printf "  Almacenamiento raíz: %s usados, %s disponibles (%s)\n", $3, $4, $5}'
df -h /data 2>/dev/null | awk 'NR==2{printf "  NVMe (/data): %s usados, %s disponibles (%s)\n", $3, $4, $5}' \
  || echo "  (sin NVMe montado en /data)"

echo ""
echo "════════════════════════════════════════════════════════"
```

```
# Salida esperada
── Docker operativo ──
  [OK] Docker 27.x.x (linux/arm64)

── NVIDIA runtime ──
  [OK] Runtime nvidia disponible

── Imágenes disponibles ──
  Imágenes dustynv: 0     ← Se llenan a medida que avanza el libro
  Imágenes nvidia-ai-iot: 3

── Conectividad a Docker Hub ──
  [OK] Docker Hub accesible

── Scripts de gestion ──
  [OK] clean-ai-containers.sh

── Espacio disponible ──
  Almacenamiento raíz: 45G usados, 890G disponibles (5%)
```

> **Próximo paso:** El Capítulo 19 usa `dustynv/kokoro-tts` para construir el pipeline completo de conversión de PDF a pódcast: extracción de texto → guión LLM → síntesis de voz → audio final.
