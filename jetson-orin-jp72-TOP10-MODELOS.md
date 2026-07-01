# Jetson AGX Orin 64GB — JetPack 7.2
# Top 10 Modelos IA: Guía de Instalación, Testing y Producción

> **Hardware:** Jetson AGX Orin 64GB · JetPack 7.2 · L4T r39.2 · CUDA 13.2.1 · sm_87  
> **Propósito:** Experimentar con todos los modelos vía OpenClaw, Open-WebUI, Python y pipelines  
> **Fuente oficial:** https://www.jetson-ai-lab.com/models  

---

## ⚡ PLAN MODE — Análisis antes de empezar

### Qué tenemos y qué necesitamos

```
JETSON AGX ORIN 64GB — ESTADO ACTUAL
  ✅ JetPack 7.2, Docker nvidia runtime, venv llm
  ✅ OpenClaw 2026.6.10 funcionando con WhatsApp
  ✅ Gemma 4 E2B via vLLM (ya en producción)
  ✅ Open-WebUI corriendo
  ❓ NGC CLI (necesario solo para Cosmos Reason 2B vía vLLM)
  ❓ Tiktoken encodings (necesarios para GPT OSS 20B)
  ❓ Imágenes Docker: latest-jetson-orin, gemma4-jetson-orin

IMÁGENES CONTAINER REQUERIDAS
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin     ← 6 modelos
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin     ← 2 modelos Gemma
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin ← 4 modelos llama.cpp
```

### Mapa de los 10 modelos en el Orin 64GB

```
MODELO                    PARAMS     RAM EST  ENGINE    PUERTO   TOK/S   MODALITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Qwen3.5 35B-A3B (MoE)  35B/3B act ~26GB    vLLM      :8000    ~30-35  Texto
2. Nemotron Nano Omni      30B/3B act ~24GB    llama.cpp :8080    ~39     T+I+A+V
3. Qwen3-VL-4B             4B         ~6GB     vLLM      :8000    ~58     T+I
4. Cosmos Reason 2 2B      2B         ~4GB     vLLM/:8010 :8010   ~59     T+I+V
                                               llama.cpp  :8080
5. Gemma 4 26B-A4B (MoE)  25.8B/3.8B ~24GB   vLLM      :8000    ~32     T+I
                                               llama.cpp  :8080
6. Qwen3.5 9B              9B         ~12GB    vLLM      :8000    ~55     Texto
7. Nemotron3 Nano 4B       4B         ~4GB     llama.cpp :8080    ~43     Texto
8. Qwen3.5 4B              4B         ~5GB     vLLM      :8000    ~50     Texto
9. Gemma 4 E4B             ~5B        ~10GB    vLLM      :8000    ~50     T+I+A
                                               llama.cpp  :8080
10. GPT OSS 20B            21B/3.6B   ~18GB    vLLM      :8000    ~42     Texto
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
T=Texto I=Imagen A=Audio V=Video
```

### Prerequisitos especiales por modelo

| Modelo | Prerequisito extra |
|--------|-------------------|
| Cosmos Reason 2 2B (vLLM) | NGC CLI + cuenta NGC + API key |
| GPT OSS 20B | Tiktoken encodings pre-descargados |
| Gemma 4 E4B | HF token (modelo gated de Google) |
| Todos | `--restart no` en docker run — NUNCA `unless-stopped` |

---

## SECCIÓN 0 — Pre-flight: Configuración Base

### 0.1 Pull de imágenes Docker (hacerlo una sola vez)

```bash
# En una sesión tmux para no perder la conexión
tmux attach -t main 2>/dev/null || tmux new-session -s main

# Imagen principal vLLM para Orin (usada por 6 de los 10 modelos)
docker pull ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin

# Imagen vLLM especial para modelos Gemma (usada por Gemma 4 E2B, E4B, 26B)
docker pull ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin

# Imagen llama.cpp (usada por Omni, Cosmos, Gemma 4B, Nemotron 4B)
docker pull ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin

# Verificar que están disponibles
docker images | grep -E "vllm|llama_cpp"
```

### 0.2 Prerequisito: Tiktoken para GPT OSS 20B

```bash
# Descargar encodings necesarios para GPT OSS 20B (solo una vez)
mkdir -p $HOME/.cache/tiktoken
wget -q https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken \
  -O $HOME/.cache/tiktoken/cl100k_base.tiktoken
wget -q https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken \
  -O $HOME/.cache/tiktoken/o200k_base.tiktoken
ls -lh $HOME/.cache/tiktoken/
# Debe mostrar dos archivos .tiktoken de varios MB
```

### 0.3 Prerequisito: NGC CLI para Cosmos Reason 2B (vía vLLM)

> ℹ️ Solo necesario si quieres el path vLLM de Cosmos (FP8). El path llama.cpp no requiere NGC.

```bash
# Descargar e instalar NGC CLI para arm64
cd ~/Downloads
wget -O ngccli_arm64.zip \
  https://api.ngc.nvidia.com/v2/resources/nvidia/ngc-apps/ngc_cli/versions/4.13.0/files/ngccli_arm64.zip
unzip ngccli_arm64.zip
chmod u+x ngc-cli/ngc
sudo mv ngc-cli/ngc /usr/local/bin/
ngc --version

# Configurar con tu cuenta NGC
# Crear cuenta gratuita en: https://ngc.nvidia.com
# Generar API key en: https://ngc.nvidia.com/setup/api-key
ngc config set
# Ingresar: API key, org=nim, team=nvidia, format=json

# Verificar acceso
ngc registry model list | head -5
```

### 0.4 Función de limpieza y verificación pre-modelo

```bash
# Guardar en ~/.bashrc la función check-ready
check-ready() {
  echo "── Memoria libre ──"
  free -h | grep Mem
  FREE=$(free -g | awk '/^Mem:/{print $7}')
  [ "$FREE" -lt 50 ] && echo "⚠️ Solo ${FREE}GB libres — ejecutar jetson-clean" \
    || echo "✅ ${FREE}GB disponibles"
  echo ""
  echo "── Contenedores activos ──"
  docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null || echo "  Ninguno"
  echo ""
  echo "── Ollama en GPU ──"
  ollama ps 2>/dev/null | tail -n +2 | awk '{print "  "$0}' || echo "  Ninguno"
}
```

---

## SECCIÓN 1 — Modelo 1: Qwen3.5 35B-A3B (MoE)

### Especificaciones
```
Parámetros:    35B total / 3B activos por forward pass (MoE)
Modalidades:   Texto únicamente
Contexto:      256K tokens
Precisión:     W4A16 (Orin) — cuantización AWQ
Licencia:      Apache 2.0
RAM estimada:  ~26GB (pesos) + KV cache
Engine:        vLLM únicamente
Puerto:        8000
Imagen:        ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin
Fuerte en:     Razonamiento, tool calling, código, 100+ idiomas
```

### Pre-flight
```bash
jetson-clean     # o manualmente: docker stop + drop_caches
check-ready      # verificar >50GB libres
pwr-maxn         # o: sudo nvpmodel -m 0 && sudo jetson_clocks
```

### Servir el modelo

**Opción A: Sin especulative decoding (más estable, inicio más rápido)**
```bash
docker run --runtime nvidia -d \
  --name qwen35-35b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.80 \
      --enable-prefix-caching \
      --reasoning-parser qwen3 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --host 0.0.0.0 \
      --port 8000"
```

**Opción B: Con MTP Speculative Decoding (+15-20% throughput)**
```bash
docker run --runtime nvidia -d \
  --name qwen35-35b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.80 \
      --enable-prefix-caching \
      --reasoning-parser qwen3 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --speculative-config '{\"method\": \"mtp\", \"num_speculative_tokens\": 4}' \
      --host 0.0.0.0 \
      --port 8000"
```

### Esperar inicio
```bash
echo -n "Esperando Qwen3.5 35B-A3B (~10 min primera descarga)"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " ✅"
curl -s http://localhost:8000/v1/models | python3 -c \
  "import sys,json; print('Activo:', json.load(sys.stdin)['data'][0]['id'])"
```

### Tests
```bash
JETSON_HOST=localhost

# Test 1: Respuesta básica
curl -s http://$JETSON_HOST:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16",
       "messages":[{"role":"user","content":"Explica computación cuántica en 1 oración."}],
       "max_tokens":100}' | python3 -c \
  "import sys,json; r=json.load(sys.stdin); print(r['choices'][0]['message']['content'])"

# Test 2: Razonamiento con cadena de pensamiento
curl -s http://$JETSON_HOST:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16",
       "messages":[{"role":"user","content":"¿Cuántas 'r' hay en la palabra 'ferrocarril'? Piensa paso a paso."}],
       "max_tokens":300}' | python3 -c \
  "import sys,json; r=json.load(sys.stdin); print(r['choices'][0]['message']['content'])"

# Test 3: Tool calling
curl -s http://$JETSON_HOST:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16",
    "messages": [{"role":"user","content":"¿Cuál es el clima en Bogotá?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {"type":"object","properties":{"location":{"type":"string"}},"required":["location"]}
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 200
  }' | python3 -m json.tool
```

### Python client
```python
# Activar venv: source ~/venvs/llm/bin/activate
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
MODEL = "Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16"

# Sin razonamiento (rápido)
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "¿Cuál es la capital de Colombia?"}],
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    max_tokens=50
)
print(resp.choices[0].message.content)

# Con razonamiento activado
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Resuelve: Si tengo 15 manzanas y doy 1/3, ¿cuántas quedan?"}],
    extra_body={"chat_template_kwargs": {"enable_thinking": True}},
    max_tokens=500
)
print(resp.choices[0].message.content)
```

### Integración OpenClaw
```bash
micro ~/.openclaw/openclaw.json
```
Actualizar el bloque `models.providers.vllm`:
```json
{
  "baseUrl": "http://127.0.0.1:8000/v1",
  "api": "openai-completions",
  "apiKey": "vllm-local",
  "timeoutSeconds": 300,
  "models": [{
    "id": "Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16",
    "name": "Qwen3.5 35B-A3B (MoE)",
    "reasoning": true,
    "input": ["text"],
    "contextWindow": 32768,
    "maxTokens": 8192,
    "cost": {"input":0,"output":0,"cacheRead":0,"cacheWrite":0}
  }]
}
```
Y en `agents.defaults.model`:
```json
"model": {"primary": "vllm/Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16"}
```

### Integración Open-WebUI
Open-WebUI auto-descubre modelos de vLLM si está conectado a `http://localhost:8000`.
- Ir a: **Admin Panel → Connections → Add OpenAI Connection**
- URL: `http://192.168.1.100:8000/v1`
- API Key: `not-needed`
- El modelo aparecerá automáticamente en la lista

### Cleanup
```bash
docker stop qwen35-35b && docker rm qwen35-35b
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

---

## SECCIÓN 2 — Modelo 2: Nemotron 3 Nano Omni

### Especificaciones
```
Parámetros:    30B total / 3B activos (MoE)
Modalidades:   Texto + Imagen + Audio + Video (multimodal nativo)
Contexto:      256K tokens
Precisión:     GGUF Q4_K_M
Licencia:      NVIDIA Open Model License
RAM estimada:  ~24GB
Engine:        llama.cpp (única opción Orin)
Puerto:        8080
Imagen:        ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin
Fuerte en:     Transcripción audio, análisis video, visión avanzada
```

### Pre-flight
```bash
jetson-clean
check-ready     # necesitas >50GB para iniciar con margen
pwr-maxn
```

### Servir el modelo

```bash
docker run --runtime nvidia -d \
  --name nemotron-omni \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
    --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
    --ctx-size 8192 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias nemotron-omni \
    --host 0.0.0.0

# Esperar inicio (~2-3 min)
echo -n "Esperando Nemotron Omni"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " ✅"
```

### Tests
```bash
# Test 1: Texto básico con razonamiento
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nemotron-omni",
       "messages":[{"role":"user","content":"Analiza las ventajas del edge computing en turismo."}],
       "chat_template_kwargs":{"enable_thinking":true},
       "max_tokens":500}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Test 2: Imagen (URL pública)
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nemotron-omni",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Cartagena_de_Indias.jpg/1200px-Cartagena_de_Indias.jpg"}},
        {"type": "text", "text": "Describe esta imagen y dónde podría estar. ¿Es buen destino turístico?"}
      ]
    }],
    "max_tokens": 400
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Test 3: Audio (requiere archivo de audio local en el Jetson)
# Opción: enviar un audio base64
# Ejemplo básico con archivo WAV local:
# (Adaptar según necesidad)
```

### Python client con imagen local
```python
import base64
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")

# Con imagen local
def analyze_image(image_path: str, prompt: str):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    ext = image_path.split(".")[-1].lower()
    mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png"}.get(ext,"image/jpeg")
    
    resp = client.chat.completions.create(
        model="nemotron-omni",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        extra_body={"chat_template_kwargs": {"enable_thinking": True}},
        max_tokens=1000
    )
    return resp.choices[0].message.content

# Uso
# result = analyze_image("/home/jetson/foto.jpg", "Describe la escena y detecta anomalías")
# print(result)
```

### Cleanup
```bash
docker stop nemotron-omni && docker rm nemotron-omni
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

---

## SECCIÓN 3 — Modelo 3: Qwen3-VL-4B

### Especificaciones
```
Parámetros:    4B
Modalidades:   Texto + Imagen (Vision-Language Agent)
Contexto:      256K tokens
Precisión:     AWQ 4-bit (W4A16)
Licencia:      Apache 2.0
RAM estimada:  ~6GB  ← muy eficiente
Engine:        vLLM
Puerto:        8000
Imagen:        ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin
Fuerte en:     GUI automation, OCR 32 idiomas, código desde imagen, grounding 2D/3D
```

> 💡 Con solo ~6GB, puedes correr este modelo y tener 55GB libres para otras cosas.

### Pre-flight
```bash
jetson-clean
check-ready
pwr-30w     # E2B suficiente, no necesita MAXN
```

### Servir el modelo
```bash
docker run --runtime nvidia -d \
  --name qwen3-vl-4b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit \
      --gpu-memory-utilization 0.30 \
      --max-model-len 16384 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Qwen3-VL-4B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " ✅ (~6GB usados)"
```

### Tests
```bash
# Test 1: Análisis de imagen con URL
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Guatap%C3%A9_Pier.jpg/1200px-Guatap%C3%A9_Pier.jpg"}},
        {"type": "text", "text": "¿Qué actividades turísticas se pueden hacer en este lugar?"}
      ]
    }],
    "max_tokens": 300
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Test 2: OCR de imagen con texto
# (Útil para facturas, documentos, capturas de pantalla)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Free_WiFi_hotspot_sign.jpg/800px-Free_WiFi_hotspot_sign.jpg"}},
        {"type": "text", "text": "Extrae todo el texto visible en esta imagen."}
      ]
    }],
    "max_tokens": 200
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Cleanup
```bash
docker stop qwen3-vl-4b && docker rm qwen3-vl-4b
```

---

## SECCIÓN 4 — Modelo 4: Cosmos Reason 2 2B

### Especificaciones
```
Parámetros:    2B
Modalidades:   Texto + Imagen + Video (spatial reasoning nativo)
Contexto:      256K tokens
Precisión:     FP8 (vLLM/NGC) | Q8_0 GGUF (llama.cpp)
Licencia:      NVIDIA Open Model License
RAM estimada:  ~4GB  ← mínima huella
Engine:        vLLM (requiere NGC) en :8010 | llama.cpp en :8080
Imagen:        latest-jetson-orin (vLLM) | latest-jetson-orin (llama)
Fuerte en:     Detección de anomalías, razonamiento espacial, análisis de escenas
```

> ⚠️ El path vLLM requiere NGC CLI y cuenta. El path llama.cpp es mucho más simple.

### Opción A: llama.cpp (recomendado, sin requisitos extra)

```bash
jetson-clean
check-ready
pwr-30w

docker run --runtime nvidia -d \
  --name cosmos-reason2 \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    -hf Kbenkhaled/Cosmos-Reason2-2B-GGUF:Q8_0 \
    -c 8192 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias cosmos-reason2 \
    --host 0.0.0.0

echo -n "Esperando Cosmos Reason 2 2B"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 10
done
echo " ✅ (Q8_0 GGUF)"
```

### Opción B: vLLM con FP8 vía NGC (mayor precisión, más complejo)

```bash
# Paso 1: Descargar modelo FP8 desde NGC
ngc registry model download-version "nim/nvidia/cosmos-reason2-2b:1208-fp8-static-kv8" \
  --dest ~/.cache/huggingface/hub
MODEL_PATH="$HOME/.cache/huggingface/hub/cosmos-reason2-2b_v1208-fp8-static-kv8"

# Paso 2: Crear caché de torch.compile (acelera reinicios)
mkdir -p ~/.cache/vllm

# Paso 3: Limpiar y servir
jetson-clean
sudo sysctl -w vm.drop_caches=3

docker run --runtime nvidia -d \
  --name cosmos-reason2-fp8 \
  --restart no \
  --network host \
  -v $MODEL_PATH:/models/cosmos-reason2-2b:ro \
  -v $HOME/.cache/vllm:/root/.cache/vllm \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve /models/cosmos-reason2-2b \
      --served-model-name nvidia/cosmos-reason2-2b-fp8 \
      --max-model-len 8192 \
      --gpu-memory-utilization 0.80 \
      --reasoning-parser qwen3 \
      --media-io-kwargs '{\"video\": {\"num_frames\": -1}}' \
      --enable-prefix-caching \
      --port 8010"

echo -n "Esperando Cosmos FP8 (primera vez: torch.compile ~5 min)"
until curl -s http://localhost:8010/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " ✅ (FP8 vía vLLM)"
```

### Tests
```bash
# Con llama.cpp (puerto 8080)
PORT=8080; MODEL="cosmos-reason2"

# Test: Razonamiento espacial con imagen
curl -s http://localhost:$PORT/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"image_url\", \"image_url\": {\"url\": \"https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Single_passenger_train_bogota.jpg/1200px-Single_passenger_train_bogota.jpg\"}},
        {\"type\": \"text\", \"text\": \"¿Hay alguna anomalía o elemento inusual en esta escena? Describe el contexto espacial.\"}
      ]
    }],
    \"max_tokens\": 400
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Cleanup
```bash
docker stop cosmos-reason2 cosmos-reason2-fp8 2>/dev/null
docker rm cosmos-reason2 cosmos-reason2-fp8 2>/dev/null
```

---

## SECCIÓN 5 — Modelo 5: Gemma 4 26B-A4B (MoE)

### Especificaciones
```
Parámetros:    25.8B total / 3.8B activos (MoE)
Modalidades:   Texto + Imagen
Contexto:      256K tokens
Precisión:     AWQ 4-bit (vLLM) | GGUF Q4_K_M (llama.cpp)
Licencia:      Apache 2.0
RAM estimada:  ~24GB
Engine:        vLLM (AWQ) en :8000 | llama.cpp (GGUF) en :8080
Imagen:        ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin (vLLM)
               ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin (llama)
Fuerte en:     Razonamiento largo, multimodal, tool calling, coding
```

### Opción A: vLLM (AWQ — tool calling nativo)

```bash
jetson-clean
check-ready     # necesitas ~40GB libres
pwr-maxn

docker run --runtime nvidia -d \
  --name gemma4-26b-vllm \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit \
      --gpu-memory-utilization 0.80 \
      --enable-auto-tool-choice \
      --reasoning-parser gemma4 \
      --tool-call-parser gemma4 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Gemma 4 26B-A4B vLLM (~8-12 min)"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " ✅"
```

### Opción B: llama.cpp (GGUF — más eficiente en RAM)

```bash
jetson-clean
check-ready
pwr-maxn

docker run --runtime nvidia -d \
  --name gemma4-26b-llama \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo ggml-org/gemma-4-26B-A4B-it-GGUF \
    --hf-file gemma-4-26B-A4B-it-Q4_K_M.gguf \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias gemma4-26b \
    --host 0.0.0.0

echo -n "Esperando Gemma 4 26B-A4B llama.cpp"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 20
done
echo " ✅"
```

### Tests
```bash
# Test tool calling con vLLM (puerto 8000)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
    "messages": [{"role":"user","content":"Busca información sobre Cartagena Colombia para turistas"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "web_search",
        "description": "Search the web",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 300
  }' | python3 -m json.tool
```

### Cleanup
```bash
docker stop gemma4-26b-vllm gemma4-26b-llama 2>/dev/null
docker rm gemma4-26b-vllm gemma4-26b-llama 2>/dev/null
```

---

## SECCIÓN 6 — Modelo 6: Qwen3.5 9B

### Especificaciones
```
Parámetros:    9B (denso)
Modalidades:   Texto
Contexto:      128K tokens
Precisión:     W4A16 AWQ
Licencia:      Apache 2.0
RAM estimada:  ~12GB
Engine:        vLLM
Puerto:        8000
Tok/s:         ~55 (más rápido entre los modelos grandes)
Fuerte en:     Velocidad + calidad, coding, razonamiento, multilingüe
```

### Servir
```bash
jetson-clean
pwr-30w    # 9B no necesita MAXN

docker run --runtime nvidia -d \
  --name qwen35-9b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-9B-quantized.w4a16 \
      --gpu-memory-utilization 0.40 \
      --enable-prefix-caching \
      --reasoning-parser qwen3 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Qwen3.5 9B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do echo -n "."; sleep 15; done
echo " ✅ (~12GB, ~55 tok/s)"
```

### Tests
```bash
# Benchmark de velocidad
time curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Kbenkhaled/Qwen3.5-9B-quantized.w4a16",
       "messages":[{"role":"user","content":"Escribe un poema de 4 versos sobre la Jetson."}],
       "max_tokens":200}' | python3 -c \
  "import sys,json; r=json.load(sys.stdin); print(r['choices'][0]['message']['content'])"

# Tool calling
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Kbenkhaled/Qwen3.5-9B-quantized.w4a16",
       "messages":[{"role":"user","content":"Genera código Python para descargar un archivo."}],
       "extra_body":{"chat_template_kwargs":{"enable_thinking":false}},
       "max_tokens":400}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Cleanup
```bash
docker stop qwen35-9b && docker rm qwen35-9b
```

---

## SECCIÓN 7 — Modelo 7: Nemotron3 Nano 4B

### Especificaciones
```
Parámetros:    4B (denso)
Modalidades:   Texto únicamente
Contexto:      256K tokens
Precisión:     GGUF Q4_K_M
Licencia:      NVIDIA Nemotron Open Model License
RAM estimada:  ~4GB  ← mínima huella en todo el top 10
Engine:        llama.cpp
Puerto:        8080
Tok/s:         ~43
Fuerte en:     Eficiencia extrema, muchos contextos en paralelo, latencia baja
```

> 💡 Con solo 4GB es el modelo más eficiente. Ideal para pipelines donde necesitas RAM para otras cosas.

### Servir
```bash
jetson-clean
pwr-30w   # 4B es eficiente, no necesita MAXN

docker run --runtime nvidia -d \
  --name nemotron3-4b \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF \
    --hf-file NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf \
    --ctx-size 8196 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias nemotron3-4b \
    --host 0.0.0.0

echo -n "Esperando Nemotron3 Nano 4B"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do echo -n "."; sleep 10; done
echo " ✅ (~4GB, ~43 tok/s)"
```

### Tests
```bash
# Test de latencia (debería ser el más rápido en TTFT)
time curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nemotron3-4b",
       "messages":[{"role":"user","content":"¿Cuál es el plan de gobierno de Colombia?"}],
       "max_tokens":200}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Test de contexto largo (hasta 256K)
# Enviar un documento largo y hacer Q&A:
LONG_CONTEXT=$(python3 -c "print('La historia de Colombia ' * 500)")
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"nemotron3-4b\",
       \"messages\":[{\"role\":\"user\",\"content\":\"Contexto: $LONG_CONTEXT\n\nPregunta: Resume lo más importante.\"}],
       \"max_tokens\":300}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Cleanup
```bash
docker stop nemotron3-4b && docker rm nemotron3-4b
```

---

## SECCIÓN 8 — Modelo 8: Qwen3.5 4B

### Especificaciones
```
Parámetros:    4B
Modalidades:   Texto
Contexto:      Nativo largo
Precisión:     AWQ 4-bit
Licencia:      Apache 2.0
RAM estimada:  ~5GB
Engine:        vLLM
Puerto:        8000
Tok/s:         ~50
Fuerte en:     Velocidad + razonamiento + tool calling en package compacto
```

### Servir
```bash
jetson-clean
pwr-30w

docker run --runtime nvidia -d \
  --name qwen35-4b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cyankiwi/Qwen3.5-4B-AWQ-4bit \
      --gpu-memory-utilization 0.25 \
      --enable-prefix-caching \
      --reasoning-parser qwen3 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Qwen3.5 4B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do echo -n "."; sleep 15; done
echo " ✅ (~5GB, ~50 tok/s)"
```

### Tests
```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"cyankiwi/Qwen3.5-4B-AWQ-4bit",
       "messages":[{"role":"user","content":"Escribe un script bash para monitorear memoria en Jetson."}],
       "extra_body":{"chat_template_kwargs":{"enable_thinking":false}},
       "max_tokens":400}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Cleanup
```bash
docker stop qwen35-4b && docker rm qwen35-4b
```

---

## SECCIÓN 9 — Modelo 9: Gemma 4 E4B

### Especificaciones
```
Parámetros:    ~5B
Modalidades:   Texto + Imagen + Audio (multimodal Google)
Contexto:      128K tokens
Precisión:     bfloat16 (vLLM) | Q4_K_M GGUF (llama.cpp)
Licencia:      Apache 2.0 (modelo gated — requiere HF token)
RAM estimada:  ~10GB (vLLM) | ~3GB (llama.cpp GGUF)
Engine:        vLLM (gemma4-jetson-orin) | llama.cpp
Puertos:       :8000 (vLLM) | :8080 (llama.cpp)
Tok/s:         ~50 (vLLM) | ~55 (llama.cpp)
Fuerte en:     Multimodal compacto, tool calling nativo gemma4
```

> ⚠️ Modelo gated: requiere HF token y aceptar licencia en huggingface.co/google/gemma-4-E4B-it

### Verificar token HF
```bash
source ~/venvs/llm/bin/activate
hf whoami
# Debe mostrar tu usuario de HuggingFace
# Si no: hf auth login --token $HF_TOKEN
```

### Opción A: vLLM
```bash
jetson-clean
pwr-30w

docker run --runtime nvidia -d \
  --name gemma4-e4b-vllm \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve google/gemma-4-E4B-it \
      --dtype bfloat16 \
      --gpu-memory-utilization 0.50 \
      --enable-auto-tool-choice \
      --reasoning-parser gemma4 \
      --tool-call-parser gemma4 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Gemma 4 E4B vLLM"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do echo -n "."; sleep 20; done
echo " ✅ (bfloat16)"
```

### Opción B: llama.cpp (menor RAM, sin gating)
```bash
jetson-clean
pwr-30w

docker run --runtime nvidia -d \
  --name gemma4-e4b-llama \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    -hf unsloth/gemma-4-E4B:Q4_K_M \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias gemma4-e4b \
    --host 0.0.0.0

echo -n "Esperando Gemma 4 E4B llama.cpp"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do echo -n "."; sleep 15; done
echo " ✅ (Q4_K_M GGUF, ~3GB)"
```

### Tests con imagen
```bash
# Test con imagen (vLLM puerto 8000)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Medellin.jpg/1200px-Medellin.jpg"}},
        {"type": "text", "text": "¿Qué ciudad es esta y qué la hace atractiva para el turismo?"}
      ]
    }],
    "max_tokens": 300
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Cleanup
```bash
docker stop gemma4-e4b-vllm gemma4-e4b-llama 2>/dev/null
docker rm gemma4-e4b-vllm gemma4-e4b-llama 2>/dev/null
```

---

## SECCIÓN 10 — Modelo 10: GPT OSS 20B

### Especificaciones
```
Parámetros:    21B total / 3.6B activos (MoE — OpenAI style)
Modalidades:   Texto únicamente
Contexto:      128K tokens
Precisión:     W4A16 AWQ
Licencia:      Apache 2.0
RAM estimada:  ~18GB
Engine:        vLLM
Puerto:        8000
Tok/s:         ~42
Requisito:     Tiktoken encodings (descargados en Sección 0.2)
Fuerte en:     Compatibilidad API OpenAI, estilo chatGPT, razonamiento
```

> ⚠️ **Prerequisito:** Los archivos tiktoken deben estar en `$HOME/.cache/tiktoken/` (ver Sección 0.2)

### Verificar prerequisitos
```bash
ls -lh $HOME/.cache/tiktoken/
# Debe mostrar: cl100k_base.tiktoken y o200k_base.tiktoken
# Si no están: volver a Sección 0.2
```

### Servir
```bash
jetson-clean
pwr-maxn    # 20B necesita MAXN

docker run --runtime nvidia -d \
  --name gpt-oss-20b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -v $HOME/.cache/tiktoken:/etc/encodings \
  -e TIKTOKEN_ENCODINGS_BASE=/etc/encodings \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve openai/gpt-oss-20b \
      --gpu-memory-utilization 0.80 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando GPT OSS 20B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do echo -n "."; sleep 30; done
echo " ✅ (~18GB, ~42 tok/s)"
```

### Tests
```bash
# Test 1: Respuesta estilo GPT
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-oss-20b",
       "messages":[
         {"role":"system","content":"Eres un asistente de agencia de turismo en Colombia."},
         {"role":"user","content":"Dame 3 razones para visitar el Eje Cafetero."}
       ],
       "max_tokens":300}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Test 2: Conversación multi-turn
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-oss-20b",
       "messages":[
         {"role":"user","content":"Hola, necesito planear un viaje"},
         {"role":"assistant","content":"¡Hola! Con gusto te ayudo. ¿A dónde quieres ir?"},
         {"role":"user","content":"A Cartagena, por 5 días, con $2 millones de pesos."}
       ],
       "max_tokens":400}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Python client (estilo OpenAI 100% compatible)
```python
# source ~/venvs/llm/bin/activate
from openai import OpenAI

# Compatible con la API de OpenAI — drop-in replacement
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

stream = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "Explain what makes Colombia special in 3 points."}],
    max_tokens=300,
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

### Cleanup
```bash
docker stop gpt-oss-20b && docker rm gpt-oss-20b
```

---

## SECCIÓN 11 — Herramientas de Benchmarking

### 11.1 Script de benchmark universal

```bash
cat > ~/scripts/benchmark-model.sh << 'BENCH'
#!/bin/bash
# Benchmark de cualquier modelo activo
# Uso: benchmark-model.sh <puerto> <model-id> [iteraciones]

PORT=${1:-8000}
MODEL_ID=${2:-"auto"}
ITERS=${3:-5}

# Auto-detectar model ID si no se especifica
if [ "$MODEL_ID" = "auto" ]; then
  MODEL_ID=$(curl -s http://localhost:$PORT/v1/models 2>/dev/null | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null)
fi

echo "══════════════════════════════════════════════════"
echo "  BENCHMARK: $MODEL_ID"
echo "  Puerto: $PORT | Iteraciones: $ITERS"
echo "══════════════════════════════════════════════════"

PROMPT="Explain the concept of edge computing in exactly 50 words."
TOTAL_TOKS=0
TOTAL_TIME=0

for i in $(seq 1 $ITERS); do
  START=$(date +%s%3N)
  
  RESPONSE=$(curl -s http://localhost:$PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"$MODEL_ID\",
      \"messages\": [{\"role\": \"user\", \"content\": \"$PROMPT\"}],
      \"max_tokens\": 100
    }" 2>/dev/null)
  
  END=$(date +%s%3N)
  ELAPSED=$(( END - START ))
  
  TOKENS=$(echo "$RESPONSE" | python3 -c \
    "import sys,json; r=json.load(sys.stdin); print(r.get('usage',{}).get('completion_tokens',0))" 2>/dev/null)
  
  CONTENT=$(echo "$RESPONSE" | python3 -c \
    "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'][:80])" 2>/dev/null)
  
  TOKS_PER_SEC=$(python3 -c "print(f'{$TOKENS / ($ELAPSED/1000):.1f}')" 2>/dev/null || echo "N/A")
  
  echo "  Run $i: ${ELAPSED}ms | ${TOKENS} tokens | ${TOKS_PER_SEC} tok/s"
  echo "         └─ ${CONTENT}..."
  
  TOTAL_TOKS=$((TOTAL_TOKS + TOKENS))
  TOTAL_TIME=$((TOTAL_TIME + ELAPSED))
done

AVG_TOKS=$((TOTAL_TOKS / ITERS))
AVG_TIME=$((TOTAL_TIME / ITERS))
AVG_SPEED=$(python3 -c "print(f'{$AVG_TOKS / ($AVG_TIME/1000):.1f}')" 2>/dev/null || echo "N/A")

echo ""
echo "  ── PROMEDIO ($ITERS runs) ──"
echo "  Tokens: $AVG_TOKS | Tiempo: ${AVG_TIME}ms | Velocidad: ${AVG_SPEED} tok/s"
echo "══════════════════════════════════════════════════"
BENCH
chmod +x ~/scripts/benchmark-model.sh
alias bench-model='~/scripts/benchmark-model.sh'
```

Uso:
```bash
bench-model 8000       # auto-detecta modelo en puerto 8000
bench-model 8080 nemotron-omni 10   # modelo en 8080, 10 iteraciones
```

### 11.2 Benchmark comparativo — todos los modelos

```bash
cat > ~/scripts/benchmark-all.sh << 'BENCHALL'
#!/bin/bash
# Benchmark todos los modelos en secuencia

RESULTS_FILE="$HOME/jetson-ai-data/benchmark_results_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p "$HOME/jetson-ai-data"

echo "BENCHMARK COMPARATIVO — TOP 10 MODELOS" > "$RESULTS_FILE"
echo "Fecha: $(date)" >> "$RESULTS_FILE"
echo "Hardware: Jetson AGX Orin 64GB JetPack 7.2" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

declare -A MODELS=(
  ["qwen35-35b"]="8000|Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16|Qwen3.5 35B-A3B MoE"
  ["nemotron-omni"]="8080|nemotron-omni|Nemotron Omni 30B"
  ["qwen3-vl-4b"]="8000|cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit|Qwen3-VL-4B"
  ["cosmos-reason2"]="8080|cosmos-reason2|Cosmos Reason 2B"
  ["gemma4-26b"]="8000|cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit|Gemma 4 26B-A4B"
  ["qwen35-9b"]="8000|Kbenkhaled/Qwen3.5-9B-quantized.w4a16|Qwen3.5 9B"
  ["nemotron3-4b"]="8080|nemotron3-4b|Nemotron3 Nano 4B"
  ["qwen35-4b"]="8000|cyankiwi/Qwen3.5-4B-AWQ-4bit|Qwen3.5 4B"
  ["gemma4-e4b"]="8000|google/gemma-4-E4B-it|Gemma 4 E4B"
  ["gpt-oss-20b"]="8000|openai/gpt-oss-20b|GPT OSS 20B"
)

# Esta función requiere correr cada modelo por separado
# Usar: bench-model <puerto> [modelo] [iteraciones]
echo "Para benchmark completo, ejecutar cada modelo por separado con:"
echo "  ~/scripts/switch-all-10-models.sh <nombre> && bench-model <puerto>"
echo ""
echo "Resultados se guardarán en: $RESULTS_FILE"
BENCHALL
chmod +x ~/scripts/benchmark-all.sh
```

### 11.3 Python pipeline de testing completo

```python
#!/usr/bin/env python3
"""
test_all_models.py — Testea el modelo activo en profundidad
Uso: source ~/venvs/llm/bin/activate && python3 ~/scripts/test_all_models.py
"""

import json
import time
import base64
from pathlib import Path
from openai import OpenAI


def get_active_model(port: int) -> tuple[str, str]:
    """Detecta el modelo activo en el puerto dado."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/v1/models", timeout=3) as r:
            data = json.loads(r.read())
            model_id = data["data"][0]["id"]
            return model_id, f"http://localhost:{port}/v1"
    except:
        return None, None


def test_model(port: int = 8000):
    """Test completo del modelo activo en el puerto dado."""
    
    model_id, base_url = get_active_model(port)
    if not model_id:
        # Probar puerto alternativo
        model_id, base_url = get_active_model(8080 if port == 8000 else 8000)
    
    if not model_id:
        print("❌ No hay modelo activo en puerto 8000 ni 8080")
        return
    
    print(f"\n{'═'*55}")
    print(f"  TESTING: {model_id}")
    print(f"  URL: {base_url}")
    print(f"{'═'*55}\n")
    
    client = OpenAI(base_url=base_url, api_key="not-needed")
    
    tests = [
        {
            "name": "Respuesta básica",
            "messages": [{"role": "user", "content": "Di 'hola mundo' en exactamente 3 palabras."}],
            "max_tokens": 20
        },
        {
            "name": "Razonamiento",
            "messages": [{"role": "user", "content": "Si tengo $100, gasto 30% en comida y 25% en transporte, ¿cuánto me queda?"}],
            "max_tokens": 150
        },
        {
            "name": "Código Python",
            "messages": [{"role": "user", "content": "Escribe una función Python que calcule fibonacci de forma eficiente. Solo el código."}],
            "max_tokens": 200
        },
        {
            "name": "Multilingüe",
            "messages": [{"role": "user", "content": "Translate: 'Welcome to Colombia, the only risk is wanting to stay.' to Spanish and French."}],
            "max_tokens": 100
        },
        {
            "name": "JSON estructurado",
            "messages": [{"role": "user", "content": "Devuelve un JSON con info de 2 destinos turísticos de Colombia. Solo el JSON, sin explicación."}],
            "max_tokens": 300
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"  ── {test['name']} ──")
        t0 = time.time()
        
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=test["messages"],
                max_tokens=test["max_tokens"]
            )
            
            elapsed = time.time() - t0
            content = resp.choices[0].message.content
            tokens = resp.usage.completion_tokens if resp.usage else 0
            tps = tokens / elapsed if elapsed > 0 else 0
            
            print(f"  ✅ {elapsed:.2f}s | {tokens} tokens | {tps:.1f} tok/s")
            print(f"     → {content[:120]}{'...' if len(content) > 120 else ''}\n")
            
            results.append({
                "test": test["name"],
                "time": round(elapsed, 2),
                "tokens": tokens,
                "tps": round(tps, 1),
                "ok": True
            })
            
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            results.append({"test": test["name"], "ok": False, "error": str(e)})
    
    # Resumen
    ok = [r for r in results if r.get("ok")]
    if ok:
        avg_tps = sum(r["tps"] for r in ok) / len(ok)
        print(f"\n{'─'*40}")
        print(f"  RESUMEN: {len(ok)}/{len(tests)} tests exitosos")
        print(f"  Velocidad promedio: {avg_tps:.1f} tok/s")
        print(f"{'─'*40}\n")
    
    return results


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    test_model(port)
```

Guardar y ejecutar:
```bash
# Guardar como ~/scripts/test_model.py
cp /dev/stdin ~/scripts/test_model.py << 'EOF'
# (pegar el código Python de arriba)
EOF
chmod +x ~/scripts/test_model.py
alias test-model='source ~/venvs/llm/bin/activate && python3 ~/scripts/test_model.py'
```

Uso:
```bash
mode-openclaw      # iniciar un modelo
test-model         # testear el activo en puerto 8000
test-model 8080    # testear el activo en puerto 8080
```

---

## SECCIÓN 12 — Integración con Open-WebUI

### Conectar cada modelo a Open-WebUI

Open-WebUI puede conectarse a vLLM y llama.cpp directamente como backend OpenAI-compatible:

```bash
# 1. Verificar que Open-WebUI está corriendo
docker ps | grep open-webui
curl -s http://localhost:3000 > /dev/null && echo "WebUI OK"
```

Desde el navegador (Windows: `http://192.168.1.100:3000`):

1. **Admin Panel** → **Settings** → **Connections**
2. **OpenAI API** → **Add**:
   - Para vLLM (puerto 8000): `http://192.168.1.100:8000/v1` | API Key: `not-needed`
   - Para llama.cpp (puerto 8080): `http://192.168.1.100:8080/v1` | API Key: `not-needed`
3. Los modelos aparecen automáticamente en el selector de modelo

### Cambiar conexión cuando cambias de modelo

Cuando cambias de modo con `switch-model.sh`, el puerto puede cambiar (8000 vs 8080). Si usas Open-WebUI a la vez, asegúrate de seleccionar la conexión correcta o configura ambas y selecciona el modelo adecuado en el chat.

---

## SECCIÓN 13 — Integración OpenClaw: Switch Extendido (10 modelos)

El switcher de modelos de la guía principal cubre 4 modelos. Aquí se extiende para los 10:

```bash
cat >> ~/scripts/switch-model.sh << 'EXTRA'

  # ── TOP 10 MODELOS ADICIONALES ────────────────────────────────

  qwen35-35b)
    echo "══ Qwen3.5 35B-A3B MoE / vLLM ══"
    stop_all; sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g \
      -e NVIDIA_VISIBLE_DEVICES=all \
      ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
        --gpu-memory-utilization 0.80 --enable-prefix-caching \
        --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_coder \
        --host 0.0.0.0 --port 8000"
    wait_model 8000 "Qwen3.5 35B-A3B"
    update_openclaw_config "Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16" "http://127.0.0.1:8000/v1" 32768 8192 '["text"]'
    openclaw gateway restart; echo "✅ Qwen3.5 35B-A3B activo";;

  qwen3-vl)
    echo "══ Qwen3-VL-4B / vLLM ══"
    stop_all; sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g -e NVIDIA_VISIBLE_DEVICES=all \
      ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit \
        --gpu-memory-utilization 0.30 --max-model-len 16384 --host 0.0.0.0 --port 8000"
    wait_model 8000 "Qwen3-VL-4B"
    update_openclaw_config "cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit" "http://127.0.0.1:8000/v1" 16384 4096 '["text","image"]'
    openclaw gateway restart; echo "✅ Qwen3-VL-4B activo (VLM, ~58 tok/s)";;

  cosmos)
    echo "══ Cosmos Reason 2 2B / llama.cpp ══"
    stop_all; sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d --name llama-openclaw --restart no \
      --network host -v $HOME/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server -hf Kbenkhaled/Cosmos-Reason2-2B-GGUF:Q8_0 -c 8192 \
        --n-gpu-layers 999 --port 8080 --alias cosmos-reason2 --host 0.0.0.0
    wait_model 8080 "Cosmos Reason 2B"
    update_openclaw_config "cosmos-reason2" "http://127.0.0.1:8080/v1" 8192 2048 '["text","image"]'
    openclaw gateway restart; echo "✅ Cosmos Reason 2B activo";;

  gemma4-26b)
    echo "══ Gemma 4 26B-A4B / vLLM ══"
    stop_all; sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g -e NVIDIA_VISIBLE_DEVICES=all \
      -v $HOME/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit \
        --gpu-memory-utilization 0.80 --enable-auto-tool-choice \
        --reasoning-parser gemma4 --tool-call-parser gemma4 --host 0.0.0.0 --port 8000"
    wait_model 8000 "Gemma 4 26B-A4B"
    update_openclaw_config "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit" "http://127.0.0.1:8000/v1" 32768 8192 '["text","image"]'
    openclaw gateway restart; echo "✅ Gemma 4 26B-A4B activo";;

  qwen35-9b)
    echo "══ Qwen3.5 9B / vLLM ══"
    stop_all; sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g -e NVIDIA_VISIBLE_DEVICES=all \
      ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve Kbenkhaled/Qwen3.5-9B-quantized.w4a16 \
        --gpu-memory-utilization 0.40 --enable-prefix-caching \
        --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_coder \
        --host 0.0.0.0 --port 8000"
    wait_model 8000 "Qwen3.5 9B"
    update_openclaw_config "Kbenkhaled/Qwen3.5-9B-quantized.w4a16" "http://127.0.0.1:8000/v1" 32768 4096 '["text"]'
    openclaw gateway restart; echo "✅ Qwen3.5 9B activo (~55 tok/s)";;

  nemotron4b)
    echo "══ Nemotron3 Nano 4B / llama.cpp ══"
    stop_all; sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d --name llama-openclaw --restart no \
      --network host -v $HOME/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server --hf-repo nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF \
        --hf-file NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf \
        --ctx-size 8196 --n-gpu-layers 999 --port 8080 --alias nemotron3-4b --host 0.0.0.0
    wait_model 8080 "Nemotron3 Nano 4B"
    update_openclaw_config "nemotron3-4b" "http://127.0.0.1:8080/v1" 8192 2048 '["text"]'
    openclaw gateway restart; echo "✅ Nemotron3 4B activo (~43 tok/s, ~4GB)";;

  qwen35-4b)
    echo "══ Qwen3.5 4B / vLLM ══"
    stop_all; sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g -e NVIDIA_VISIBLE_DEVICES=all \
      ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve cyankiwi/Qwen3.5-4B-AWQ-4bit \
        --gpu-memory-utilization 0.25 --enable-prefix-caching \
        --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_coder \
        --host 0.0.0.0 --port 8000"
    wait_model 8000 "Qwen3.5 4B"
    update_openclaw_config "cyankiwi/Qwen3.5-4B-AWQ-4bit" "http://127.0.0.1:8000/v1" 16384 4096 '["text"]'
    openclaw gateway restart; echo "✅ Qwen3.5 4B activo (~50 tok/s)";;

  gemma4-e4b)
    echo "══ Gemma 4 E4B / vLLM ══"
    stop_all; sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g -e NVIDIA_VISIBLE_DEVICES=all \
      -v $HOME/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve google/gemma-4-E4B-it \
        --dtype bfloat16 --gpu-memory-utilization 0.50 --enable-auto-tool-choice \
        --reasoning-parser gemma4 --tool-call-parser gemma4 --host 0.0.0.0 --port 8000"
    wait_model 8000 "Gemma 4 E4B"
    update_openclaw_config "google/gemma-4-E4B-it" "http://127.0.0.1:8000/v1" 32768 4096 '["text","image"]'
    openclaw gateway restart; echo "✅ Gemma 4 E4B activo (~50 tok/s)";;

  gpt-oss)
    echo "══ GPT OSS 20B / vLLM ══"
    [ ! -f "$HOME/.cache/tiktoken/cl100k_base.tiktoken" ] && \
      echo "❌ Tiktoken no encontrado — ejecutar Sección 0.2" && exit 1
    stop_all; sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g -e NVIDIA_VISIBLE_DEVICES=all \
      -v $HOME/.cache/huggingface:/root/.cache/huggingface \
      -v $HOME/.cache/tiktoken:/etc/encodings \
      -e TIKTOKEN_ENCODINGS_BASE=/etc/encodings \
      ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve openai/gpt-oss-20b --gpu-memory-utilization 0.80 --host 0.0.0.0 --port 8000"
    wait_model 8000 "GPT OSS 20B"
    update_openclaw_config "openai/gpt-oss-20b" "http://127.0.0.1:8000/v1" 32768 4096 '["text"]'
    openclaw gateway restart; echo "✅ GPT OSS 20B activo (~42 tok/s)";;

EXTRA
```

Nuevos aliases:
```bash
echo 'alias mode-qwen35-35b="~/scripts/switch-model.sh qwen35-35b"' >> ~/.bashrc
echo 'alias mode-qwen3-vl="~/scripts/switch-model.sh qwen3-vl"' >> ~/.bashrc
echo 'alias mode-cosmos="~/scripts/switch-model.sh cosmos"' >> ~/.bashrc
echo 'alias mode-gemma26b="~/scripts/switch-model.sh gemma4-26b"' >> ~/.bashrc
echo 'alias mode-qwen9b="~/scripts/switch-model.sh qwen35-9b"' >> ~/.bashrc
echo 'alias mode-nemotron4b="~/scripts/switch-model.sh nemotron4b"' >> ~/.bashrc
echo 'alias mode-qwen4b="~/scripts/switch-model.sh qwen35-4b"' >> ~/.bashrc
echo 'alias mode-gemma4b="~/scripts/switch-model.sh gemma4-e4b"' >> ~/.bashrc
echo 'alias mode-gpt="~/scripts/switch-model.sh gpt-oss"' >> ~/.bashrc
source ~/.bashrc
```

---

## SECCIÓN 14 — Tabla de Referencia Final

### Todos los modelos en una vista

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║ # MODELO              ALIAS            ENGINE   PORT  PWR  RAM   TOK/S  MODALITIES      ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║ 1 Qwen3.5 35B-A3B    mode-qwen35-35b  vLLM     8000  MAXN ~26GB ~30-35 T               ║
║ 2 Nemotron Omni 30B  mode-multimodal  llama.cpp 8080  MAXN ~24GB ~39    T+I+A+V         ║
║ 3 Qwen3-VL-4B        mode-qwen3-vl    vLLM     8000  30W  ~6GB  ~58    T+I             ║
║ 4 Cosmos Reason 2 2B mode-cosmos      llama.cpp 8080  30W  ~4GB  ~59    T+I+V           ║
║ 5 Gemma 4 26B-A4B    mode-gemma26b    vLLM     8000  MAXN ~24GB ~32    T+I             ║
║ 6 Qwen3.5 9B         mode-qwen9b      vLLM     8000  30W  ~12GB ~55    T               ║
║ 7 Nemotron3 Nano 4B  mode-nemotron4b  llama.cpp 8080  30W  ~4GB  ~43    T               ║
║ 8 Qwen3.5 4B         mode-qwen4b      vLLM     8000  30W  ~5GB  ~50    T               ║
║ 9 Gemma 4 E4B        mode-gemma4b     vLLM     8000  30W  ~10GB ~50    T+I+A           ║
║10 GPT OSS 20B        mode-gpt         vLLM     8000  MAXN ~18GB ~42    T               ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║   + existentes en guía principal:                                                       ║
║   Gemma 4 E2B        mode-openclaw    vLLM     8000  30W  ~15GB ~32    T+I  ← default  ║
║   Gemma 4 E2B        mode-lite        llama.cpp 8080  30W  ~3.5G ~35    T              ║
║   Nemotron3 30B-A3B  mode-longdoc     vLLM     8000  MAXN ~26GB ~38    T               ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝

T=Texto  I=Imagen  A=Audio  V=Video
```

### Ranking por caso de uso

| Necesidad | Mejor modelo | Alias |
|---|---|---|
| Más rápido (tok/s) | Cosmos Reason 2 2B (~59) | `mode-cosmos` |
| Más eficiente (RAM) | Cosmos 2B o Nemotron3 4B (~4GB) | `mode-cosmos` / `mode-nemotron4b` |
| Mejor razonamiento | Qwen3.5 35B-A3B | `mode-qwen35-35b` |
| Mejor multimodal texto+imagen | Qwen3-VL-4B (OCR, GUI) | `mode-qwen3-vl` |
| Mejor multimodal completo | Nemotron Omni (T+I+A+V) | `mode-multimodal` |
| Mayor contexto estable | Qwen3.5 35B-A3B / Gemma4 26B (256K) | `mode-qwen35-35b` |
| Mejor tool calling | Qwen3.5 9B o 35B | `mode-qwen9b` |
| Compatibilidad OpenAI 100% | GPT OSS 20B | `mode-gpt` |
| Agente WhatsApp diario | Gemma 4 E2B (default) | `mode-openclaw` |
| Documentos largos | Nemotron3 30B-A3B | `mode-longdoc` |

---

*Versión 1.0 — 2026-06-28 · Jetson AGX Orin 64GB · JetPack 7.2 · CUDA 13.2.1*  
*Fuentes: jetson-ai-lab.com/models — todos los comandos verificados contra páginas oficiales*
