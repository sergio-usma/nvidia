# Apéndice — Referencia Rápida

## A.1 Especificaciones del Hardware

| Componente | Especificación |
|-----------|----------------|
| **SoC** | NVIDIA Jetson AGX Orin |
| **GPU** | Ampere, 2048 CUDA Cores, sm_87 |
| **CPU** | 12-core ARM Cortex-A78AE |
| **RAM** | 64 GB LPDDR5 (unificada CPU+GPU) |
| **Almacenamiento** | 64 GB eMMC + expansión NVMe |
| **AI Performance** | 275 TOPS |
| **Potencia máxima** | 60W (configurada a 50W MAXN) |
| **Conectividad** | Gigabit Ethernet, USB 3.2, PCIe, CAN |

## A.2 Versiones de Software — JetPack 7.2

| Componente | Versión |
|-----------|---------|
| **JetPack** | 7.2 |
| **L4T** | r39.2 |
| **Ubuntu** | 24.04.4 LTS |
| **Kernel** | 6.8.12-tegra |
| **CUDA** | 13.2.1 |
| **cuDNN** | 9.x |
| **TensorRT** | 10.x |
| **Python** | 3.12.3 |
| **GPU Arch** | sm_87 |

---

## A.3 Modos de Energía

```bash
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks'  # 50W, máximo rendimiento
alias pwr-30w='sudo nvpmodel -m 2'                           # 30W, balance
alias pwr-15w='sudo nvpmodel -m 3'                           # 15W, bajo consumo
```

| Modo | Potencia | Caso de uso |
|------|----------|-------------|
| MAXN (`-m 0`) | 50W | Inferencia LLM >9B, modelos MoE |
| 30W (`-m 2`) | 30W | Inferencia LLM ≤9B, STT, TTS, agentes |
| 15W (`-m 3`) | 15W | Limpieza, espera, tareas ligeras |

---

## A.4 Mapa de Puertos

| Puerto | Servicio | Fase | Notas |
|--------|----------|------|-------|
| **22** | SSH | 1 | Siempre activo |
| **3000** | Open WebUI | 1 | Interfaz web para modelos |
| **3001** | Uptime Kuma | 3 | Monitor de disponibilidad |
| **5000** | Flask — Agencia IA | 3 | Frontend web del capstone |
| **5678** | N8N | 1 | Automatización de workflows |
| **8000** | vLLM / faster-whisper | 1 | No usar ambos simultáneamente |
| **8001** | vLLM (puerto alternativo) | 1 | Cuando faster-whisper ocupa :8000 |
| **8080** | llama.cpp | 1 | Motor de inferencia alternativo |
| **8088** | Nginx gateway | 3 | Reverse proxy único de entrada |
| **8880** | kokoro-tts | 1/2 | TTS alta calidad (español/inglés) |
| **9000** | RAG API (FastAPI) | 2 | RAG empresarial ChromaDB |
| **9100** | JWT Auth Gateway | 3 | Autenticación de clientes API |
| **10200** | piper-tts | 1/2 | TTS rápido CPU (<200ms) |
| **11434** | Ollama | 1+2 | Modelos locales sin contenedor |
| **18789** | OpenClaw / NemoClaw | 1 | Orquestador de agentes IA |
| **8888** | JupyterLab | 2 | Notebooks con GPU |
| **8188** | ComfyUI | 2 | Generación de imágenes |
| **8123** | Home Assistant | 2 | IoT |

> **Conflicto :8000:** faster-whisper y vLLM usan el mismo puerto por defecto. Para usarlos en el mismo Jetson, lanzar vLLM en :8001 con `--port 8001`. El pipeline STT → LLM debe ser secuencial (uno a la vez) o usar puertos distintos.

---

## A.5 Aliases Completos de ~/.bashrc

### Energía y sistema

```bash
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks'
alias pwr-30w='sudo nvpmodel -m 2'
alias pwr-15w='sudo nvpmodel -m 3'
alias sys-status='~/scripts/maintenance/system-status.sh'
alias motors-status='sys-status'
alias health-check='~/scripts/maintenance/health-check.sh'
alias jetson-clean='~/scripts/jetson-clean.sh'

# Docker bajo demanda (clean-start: Docker deshabilitado en boot)
alias docker-on='sudo systemctl start docker.socket && sudo systemctl start docker'
alias docker-off='sudo systemctl stop docker && sudo systemctl stop docker.socket'

# Python venv LLM
alias llm-env='source ~/venvs/llm/bin/activate'
```

### Motores de inferencia — 

```bash
# vLLM
alias start-qwen35='pwr-maxn && docker run -d --name qwen35-35b --restart no \
  --runtime nvidia --network host --ipc host --shm-size 8g \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
    --gpu-memory-utilization 0.70 --enable-prefix-caching \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder \
    --served-model-name qwen35 --max-model-len 8192 --host 0.0.0.0 --port 8000" && \
  until curl -sf http://localhost:8000/v1/models > /dev/null; do sleep 20; done && \
  echo "[OK] qwen35 listo"'
alias stop-qwen35='docker stop qwen35-35b'
alias kill-qwen35='docker stop qwen35-35b && docker rm qwen35-35b'

# llama.cpp
alias start-nemotron='pwr-maxn && docker run -d --name nemotron --restart no \
  --runtime nvidia --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
  --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
  --ctx-size 16384 --port 8080 --host 0.0.0.0 --alias nemotron-omni --n-gpu-layers 999 && \
  until curl -sf http://localhost:8080/v1/models > /dev/null; do sleep 15; done && \
  echo "[OK] nemotron listo"'
alias stop-nemotron='docker stop nemotron'
alias kill-nemotron='docker stop nemotron && docker rm nemotron'

# Open WebUI
alias start-webui='docker run -d --name open-webui --runtime nvidia --restart no \
  --network host -v open-webui:/app/backend/data \
  -e WEBUI_SECRET_KEY=$(openssl rand -hex 16) \
  ghcr.io/open-webui/open-webui:main && echo "[OK] Open WebUI en http://localhost:3000"'
alias stop-webui='docker stop open-webui'
alias kill-webui='docker stop open-webui && docker rm open-webui'
```

###  — Mantenimiento

```bash
alias check-ready='~/scripts/maintenance/check-ready.sh'
alias clean-ai-containers='~/scripts/maintenance/clean-ai-containers.sh'
alias switch-project='~/scripts/maintenance/switch-project.sh'
alias hf-cache='~/scripts/maintenance/hf-cache-clean.sh'
alias jc-status='~/scripts/jetson-containers-status.sh'
```

### STT / TTS — Parts 13C, 18, 29

```bash
# faster-whisper STT (:8000)
alias start-whisper='docker run --runtime nvidia -d --name faster-whisper --restart no \
  --network host -e WHISPER_MODEL=large-v3 -e WHISPER_DEVICE=cuda \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  dustynv/faster-whisper:r39.2.0 && echo "faster-whisper iniciando en :8000"'
alias stop-whisper='docker stop faster-whisper && docker rm faster-whisper'
alias whisper-logs='docker logs faster-whisper --follow'

# kokoro-tts (:8880)
alias start-kokoro='docker run --runtime nvidia -d --name kokoro-tts --restart no \
  --network host -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  dustynv/kokoro-tts:r39.2.0 && echo "kokoro-tts iniciando en :8880"'
alias stop-kokoro='docker stop kokoro-tts && docker rm kokoro-tts'
alias kokoro-logs='docker logs kokoro-tts --follow'

# Pipeline completo de voz
alias voice-assistant='source ~/venvs/llm/bin/activate && python3 ~/scripts/voice_assistant_pipeline.py'
alias transcribir='source ~/venvs/llm/bin/activate && python3 ~/scripts/diarize_and_transcribe.py'
alias tts-es='source ~/venvs/llm/bin/activate && python3 ~/scripts/tts_kokoro.py'
alias tts-rapido='source ~/venvs/llm/bin/activate && python3 ~/scripts/tts_piper.py'
```

### N8N — Part 27

```bash
alias start-n8n='cd ~/stacks/n8n && docker compose up -d && cd -'
alias stop-n8n='cd ~/stacks/n8n && docker compose down && cd -'
alias restart-n8n='cd ~/stacks/n8n && docker compose restart && cd -'
alias n8n-status='cd ~/stacks/n8n && docker compose ps && cd -'
alias n8n-logs='cd ~/stacks/n8n && docker compose logs --tail=50 -f && cd -'
alias update-n8n='cd ~/stacks/n8n && docker compose pull && docker compose up -d && cd -'
alias kill-n8n='cd ~/stacks/n8n && docker compose down -v && cd -'
alias n8n-url='echo "http://$(hostname -I | awk "{print \$1}"):5678"'

# Combo: N8N + OpenClaw
alias agency-automation-start='start-n8n && openclaw-start'
alias agency-automation-stop='stop-n8n && openclaw-stop'
```

### Computer Vision — Part 28

```bash
alias start-vision='docker run --runtime nvidia -d --name gemma4-e4b-llama --restart no \
  --network host -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server -hf unsloth/gemma-4-E4B:Q4_K_M \
    --ctx-size 32768 --n-gpu-layers 999 --port 8080 --alias gemma4-e4b --host 0.0.0.0'
alias ocr-imagen='source ~/venvs/llm/bin/activate && python3 ~/scripts/ocr_pipeline.py'
alias ocr-llm='source ~/venvs/llm/bin/activate && python3 ~/scripts/ocr_to_llm.py'
alias vision-describe='source ~/venvs/llm/bin/activate && python3 ~/scripts/vision_describe.py'
alias nanoowl-detect='source ~/venvs/llm/bin/activate && python3 ~/scripts/nanoowl_detect.py'
alias video-monitor='source ~/venvs/llm/bin/activate && python3 ~/scripts/video_monitor.py'
```

### Docker Compose Stacks — Part 8.6

```bash
alias start-voice-stack='cd ~/stacks/voice && docker compose up -d && cd -'
alias stop-voice-stack='cd ~/stacks/voice && docker compose down && cd -'
alias start-webui-stack='cd ~/stacks/webui-whisper && docker compose up -d && cd -'
alias stop-webui-stack='cd ~/stacks/webui-whisper && docker compose down && cd -'
alias stack-status='echo "=== voice ===" && docker compose -f ~/stacks/voice/compose.yml ps 2>/dev/null; echo "=== webui-whisper ===" && docker compose -f ~/stacks/webui-whisper/compose.yml ps 2>/dev/null'
```

### Gateway e Infraestructura — Parts 30 + 31

```bash
# Nginx + JWT + Cloudflare
alias start-gateway='~/scripts/gateway/gateway-manage.sh start'
alias stop-gateway='~/scripts/gateway/gateway-manage.sh stop'
alias restart-gateway='~/scripts/gateway/gateway-manage.sh restart'
alias gateway-status='~/scripts/gateway/gateway-manage.sh status'
alias gateway-logs='~/scripts/gateway/gateway-manage.sh logs'
alias gateway-clients='curl -s "http://localhost:9100/admin/clientes?admin_key=$(grep ADMIN_KEY ~/scripts/gateway/.env | cut -d= -f2)" | python3 -m json.tool'
alias new-client='~/scripts/gateway/new-client.sh'
alias uptime-kuma='echo "http://localhost:3001"'

# Agencia IA (capstone)
alias agency-start='~/scripts/agency-start.sh'
alias agency-stop='~/scripts/agency-stop.sh'
alias agency-status='curl -s http://localhost:5000/health | python3 -m json.tool'
alias agency-logs='tail -f ~/logs/flask_agencia.log'
alias agency-vllm-logs='docker logs qwen35-35b --follow'
alias agency-n8n-logs='cd ~/stacks/n8n && docker compose logs --tail=50 -f'
```

---

## A.6 Contenedores NVIDIA Oficiales

| Motor | Imagen | Puerto |
|-------|--------|--------|
| vLLM (modelos generales) | `ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin` | 8000 |
| vLLM (Gemma 4) | `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` | 8000 |
| llama.cpp | `ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin` | 8080 |

### Patrón docker run para vLLM

```bash
sudo docker run -d \
  --name <alias> \
  --runtime nvidia \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  vllm serve <HF_MODEL_ID> \
    --gpu-memory-utilization <0.70|0.75|0.80> \
    --served-model-name <alias> \
    --max-model-len <8192|16384|32768> \
    --host 0.0.0.0 \
    --port 8000
```

### Patrón docker run para llama.cpp

```bash
sudo docker run -d \
  --name <alias> \
  --runtime nvidia \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo <HF_REPO> \
    --hf-file <GGUF_FILE> \
    --ctx-size <16384|32768> \
    --n-gpu-layers 999 \
    --host 0.0.0.0 \
    --port 8080 \
    --alias <alias>
```

---

## A.7 Top 10 Modelos Recomendados — JP 7.2

| # | Modelo | Motor | Contenedor | ~tok/s |
|---|--------|-------|-----------|--------|
| 1 | Qwen3.5-35B-A3B-quantized.w4a16 (MoE) | vLLM | latest-jetson-orin | 30–35 |
| 2 | NVIDIA-Nemotron-3-Nano-Omni | llama.cpp | llama_cpp | ~39 |
| 3 | Qwen3-VL-4B (Vision) | vLLM | latest-jetson-orin | ~58 |
| 4 | Cosmos-Reason2-2B | vLLM | latest-jetson-orin | ~59 |
| 5 | Gemma-4-26B-A4B (MoE) | vLLM | gemma4-jetson-orin | ~32 |
| 6 | Qwen3.5-9B | vLLM | latest-jetson-orin | ~55 |
| 7 | Nemotron3-Nano-4B | llama.cpp | llama_cpp | ~43 |
| 8 | Qwen3.5-4B | vLLM | latest-jetson-orin | ~50 |
| 9 | Gemma-4-E4B (multimodal) | vLLM | gemma4-jetson-orin | ~50 |
| 10 | GPT-OSS-20B | vLLM | latest-jetson-orin | ~42 |

### Política de `--gpu-memory-utilization`

| Tamaño del modelo | Valor recomendado |
|-------------------|-------------------|
| ≤9B | 0.80 |
| 9B–20B | 0.75 |
| >20B o MoE | 0.70 |
| Si OOM ocurre | Reducir 0.05 y reintentar |

---

## A.8 Contenedores jetson-containers

| Contenedor | Puerto | Uso |
|-----------|--------|-----|
| `dustynv/faster-whisper:r39.2.0` | 8000 | STT (transcripción) |
| `dustynv/speaches:r39.2.0` | 8000 | STT en tiempo real |
| `dustynv/kokoro-tts:r39.2.0` | 8880 | TTS alta calidad |
| `dustynv/piper-tts:r39.2.0` | 10200 | TTS rápido (voz) |
| `dustynv/comfyui:r39.2.0` | 8188 | Generación de imágenes |
| `dustynv/jupyterlab:r39.2.0` | 8888 | Notebooks con GPU |
| `dustynv/nanodb:r39.2.0` | 7860 | Vector DB embebida |
| `dustynv/homeassistant-core:r39.2.0` | 8123 | IoT |

> **NOTA:** Los tags `r39.2.0` son para JP 7.2 / L4T r39.2. Verifique disponibilidad con `curl -s "https://hub.docker.com/v2/repositories/dustynv/<nombre>/tags/..."` antes de hacer `docker pull`.

---

## A.9 Presupuesto de Memoria — Combinaciones Comunes

| Combinación de servicios | RAM estimada | Seguro |
|--------------------------|-------------|--------|
| OS solo | ~12 GB | ✅ |
| OS + Ollama (7B) | ~20 GB | ✅ |
| OS + vLLM (35B MoE) | ~34 GB | ✅ |
| OS + llama.cpp (nemotron) | ~22 GB | ✅ |
| OS + faster-whisper (large-v3) | ~17 GB | ✅ |
| OS + Ollama (7B) + kokoro-tts + faster-whisper (small) | ~26 GB | ✅ |
| OS + vLLM (35B) + faster-whisper | ~39 GB | ✅ con cautela |
| OS + vLLM (35B) + Open WebUI | ~37 GB | ✅ |
| OS + N8N + PostgreSQL | ~14 GB | ✅ |
| OS + N8N + PostgreSQL + Ollama (4B) | ~19 GB | ✅ |
| OS + faster-whisper + kokoro-tts (voice stack) | ~17 GB | ✅ |
| OS + faster-whisper + kokoro-tts + Ollama (4B) | ~22 GB | ✅ pipeline voz completo |
| OS + Gateway (Nginx+JWT+cloudflared) | ~12.3 GB | ✅ overhead mínimo |
| OS + Agencia completa en espera (Flask+OpenClaw+N8N+Ollama 4B) | ~20 GB | ✅ |
| OS + Agencia completa en generación (+ vLLM 35B) | ~46 GB | ✅ |
| Dos modelos LLM grandes simultáneos | >55 GB | ⚠️ Evitar |

**Regla:** Siempre verifique con `check-ready 20 "nombre-proyecto"` antes de lanzar un pipeline.

---

## A.10 Comandos de Diagnóstico Rápido

```bash
# Estado completo del sistema
sys-status

# Verificar todos los endpoints activos (puertos de todos los servicios)
for p in 8000 8001 8080 3000 11434 18789 8880 10200 9000 5678 5000 8088 9100 3001; do
  result=$(curl -sf --max-time 1 http://localhost:$p/health 2>/dev/null \
    || curl -sf --max-time 1 http://localhost:$p/v1/models 2>/dev/null \
    || curl -sf --max-time 1 http://localhost:$p/api/version 2>/dev/null \
    || curl -sf --max-time 1 http://localhost:$p/healthz 2>/dev/null)
  [ -n "$result" ] && echo "  [OK] :$p activo" || true
done

# RAM libre
free -h | awk '/^Mem:/{printf "%s libres de %s\n", $7, $2}'

# Temperatura
cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "%.1f°C\n", $1/1000}'

# Modo de energía actual
nvpmodel -q 2>/dev/null | grep "NV Power Mode"

# Contenedores activos
docker ps --format "table {{.Names}}\t{{.Status}}"

# Logs de un contenedor (últimas 50 líneas)
docker logs <nombre> --tail 50

# Endpoints activos
for p in 8000 8080 3000 11434 18789 8880 10200 9000; do
  curl -sf http://localhost:$p/v1/models --max-time 1 > /dev/null 2>&1 && echo "  [OK] :$p activo" || true
done

# Espacio en disco
df -h / /data 2>/dev/null | awk 'NR>0{printf "  %s: %s usados, %s libres\n", $6, $3, $4}'

# Caché de HuggingFace
du -sh ~/.cache/huggingface 2>/dev/null | awk '{print "  HF cache: " $1}'
```

---

## A.11 Convenciones de Tags de Verificación

| Tag | Significado |
|-----|-------------|
| `` | Comando probado y funcionando en JetPack 7.2 |
| `` | Probado en JP 6.2 — probable que funcione en JP 7.2 |
| `[REQUIERE VERIFICACIÓN]` | No verificado en JP 7.2 — puede necesitar ajustes |
| `[NEEDS VERIFICATION]` | Equivalente en inglés |

---

## A.12 Diferencias Críticas JP 6.2 → JP 7.2

| Componente | JP 6.2 | JP 7.2 |
|-----------|--------|--------|
| Ubuntu | 22.04 | **24.04** |
| Python | 3.10 | **3.12** |
| CUDA | 12.6 | **13.2.1** |
| L4T | r36.5 | **r39.2** |
| Kernel | 5.15 | **6.8** |
| PyTorch wheel | `jp/v61` | **`jp/v72`** |
| Container tags | `r36.4.0` | **`r39.2.0`** |
| TensorRT | 8.x | **10.x** |

---

## A.13 Estructura de Directorios del Libro

```
D:\Documents\Jetson\eBook\book\
├── phase1\                          ← Configuración y operación del sistema
│   ├── part-00-introduction\
│   ├── part-01-first-boot\
│   ├── part-02-base-system\
│   ├── part-03-performance\
│   ├── part-04-memory-storage\
│   ├── part-05-shell-environment\
│   ├── part-06-network\
│   ├── part-07-remote-access\
│   ├── part-08-docker\              ← Docker + NVIDIA NCT + §8.6 Docker Compose
│   ├── part-12-inference-engines\
│   ├── part-13-agentic-ai-stack\   ← original (referencia)
│   ├── part-13a-openclaw\          ← standalone OpenClaw
│   ├── part-13b-nemoclaw\          ← standalone NemoClaw
│   ├── part-13c-open-webui\        ← standalone Open WebUI
│   ├── part-13d-tool-calling\      ← standalone Tool Calling
│   ├── part-14-model-benchmarking\
│   ├── part-15-production-deployment\
│   ├── part-16-troubleshooting\
│   ├── part-27-n8n\                ← N8N + PostgreSQL ARM64
│   ├── part-28-computer-vision\    ← OCR + Gemma4 VQA + nanoowl
│   ├── part-29-tts-stt\            ← faster-whisper + kokoro-tts + piper
│   └── appendix\
├── phase2\                          ← Proyectos prácticos de IA
│   ├── part-17-python-vscode-dev\
│   ├── part-18-jetson-containers\
│   ├── part-19-image-video-generation\  ← ComfyUI + SD WebUI + AnimateDiff
│   ├── part-19-pdf-to-podcast\
│   ├── part-20-audio-transcription-bot\
│   ├── part-21-tourism-agency\
│   ├── part-22-sales-funnel\
│   ├── part-23-linkedin-content\
│   ├── part-24-voice-assistant\
│   ├── part-25-rag-empresarial\
│   └── part-26-system-maintenance\
├── phase3\                          ← Infraestructura SAAS y capstone
│   ├── part-30-microservices-saas\  ← Nginx + JWT + Cloudflare Tunnel
│   ├── part-31-ai-agency-capstone\  ← Agencia IA completa (Flask + OpenClaw + N8N)
│   ├── part-32-daily-prayers\       ← Proyecto independiente YouTube Shorts + TikTok
│   └── part-33-conclusion\          ← Reflexiones y futuro de la IA
├── glosario\                        ← Términos técnicos del libro
└── manuscript\                      ← Ensamblaje final para KDP
```

---

## A.14 Directorios de Modelos en el Jetson

| Motor | Ruta en el Jetson | Notas |
|-------|-------------------|-------|
| HuggingFace / vLLM | `~/.cache/huggingface/hub/` | Snapshots automáticos; montado con `-v` en docker run |
| Ollama | `~/.ollama/models/` | Formato blob propio; no compatible con HF |
| GGUF (llama.cpp) | `$HOME/.cache/huggingface/hub/` | Los repos HF con GGUF se descargan automáticamente |
| Tiktoken | `~/.cache/tiktoken/` | Encodings pre-descargados para GPT OSS 20B |
| vLLM KV cache | `~/.cache/vllm/` | Bloques KV automáticos; se borra con `jetson-clean` |
| Modelos grandes (>20 GB) | `/data/models/` | Siempre en NVMe, NUNCA en eMMC (solo 64 GB) |

**Verificar uso de espacio por motor:**

```bash
# Resumen de espacio por directorio de modelos
du -sh ~/.cache/huggingface/hub/ 2>/dev/null || echo "(vacío)"
du -sh ~/.ollama/models/ 2>/dev/null || echo "(vacío)"
du -sh ~/.cache/tiktoken/ 2>/dev/null || echo "(vacío)"
du -sh /data/models/ 2>/dev/null || echo "(vacío)"

# Ver modelos HuggingFace individuales con tamaño
du -sh ~/.cache/huggingface/hub/models--*/ 2>/dev/null | sort -h

# Ver espacio total disponible en NVMe
df -h /data 2>/dev/null || df -h / | tail -1
```

**Limpiar caché HuggingFace de modelos no usados:**

```bash
# Listar todos los modelos descargados
ls -la ~/.cache/huggingface/hub/

# Eliminar un modelo específico (reemplazar el nombre exacto)
# ADVERTENCIA: no reversible; deberá volver a descargar si lo necesita
rm -rf ~/.cache/huggingface/hub/models--Kbenkhaled--Qwen3.5-35B-A3B-quantized.w4a16/
```

---

## A.15 Nomenclatura GGUF — Guía Rápida

Los archivos GGUF incluyen el nivel de cuantización en el nombre. Esta tabla explica los sufijos más comunes:

| Sufijo | Bits/peso | RAM típica (7B) | RAM típica (30B) | Calidad | Uso recomendado |
|--------|-----------|----------------|------------------|---------|-----------------|
| `Q2_K` | ~2.6 bit | ~3 GB | ~10 GB | Baja | Solo si hay restricción extrema de RAM |
| `Q4_0` | 4 bit | ~5 GB | ~16 GB | Media | No recomendado; use Q4_K_M |
| `Q4_K_S` | 4 bit | ~4.8 GB | ~15 GB | Media | Versión reducida de Q4_K_M |
| `Q4_K_M` | 4 bit | ~5.2 GB | ~17 GB | **Buena** | **Recomendado para uso general** |
| `IQ4_XS` | ~4.25 bit | ~4.9 GB | ~16 GB | Buena | Cuantización GGUF mejorada (menor que Q4_K_M) |
| `Q5_K_M` | 5 bit | ~6.2 GB | ~20 GB | Muy buena | Cuando hay RAM de sobra |
| `Q6_K` | 6 bit | ~7.3 GB | ~24 GB | Alta | Cerca de la calidad FP16 |
| `Q8_0` | 8 bit | ~9 GB | ~30 GB | Muy alta | Máxima calidad GGUF disponible |
| `F16` | 16 bit | ~14 GB | ~60 GB | Completa | Solo modelos <4B en Jetson |

**Regla práctica para el Jetson AGX Orin 64GB:**

| Tamaño del modelo | Cuantización recomendada | RAM estimada | Nodo de energía |
|-------------------|--------------------------|-------------|-----------------|
| 2B–4B | `Q8_0` o `F16` | 2–6 GB | 30W |
| 7B–9B | `Q4_K_M` o `Q8_0` | 5–9 GB | 30W |
| 14B–20B | `Q4_K_M` | 8–12 GB | MAXN |
| 26B–35B | `Q4_K_M` o `IQ4_XS` | 14–20 GB | MAXN |

> **NOTA:** Los archivos con `_K_M` usan un método de cuantización "K-quant" con matrices mixtas que preserva mejor la calidad en capas de atención críticas. Para un mismo nivel de bits, `Q4_K_M` es superior a `Q4_0`.

---

## A.16 Script de Limpieza `jetson-clean.sh` Completo

El script completo instalado en `~/scripts/jetson-clean.sh` (ver §14.1):

```bash
# Reinstalar el script si se pierde
mkdir -p ~/scripts

cat > ~/scripts/jetson-clean.sh << 'EOF'
#!/bin/bash

mostrar_diagnostico() {
    echo "  [1] Memoria:"
    free -h | awk 'NR==1 || NR==2' | sed 's/^/      /'
    echo "  [2] Contenedores activos:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | sed 's/^/      /'
    echo "  [3] RAM por contenedor:"
    docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | sed 's/^/      /'
    echo "  [4] Modelos Ollama:"
    systemctl is-active --quiet ollama \
      && ollama ps 2>/dev/null | sed 's/^/      /' \
      || echo "      Ollama offline"
    echo "  [5] Endpoints activos:"
    curl -s http://localhost:8000/v1/models 2>/dev/null | \
      python3 -c "import sys,json; [print('      vLLM:8000 →',m['id']) for m in json.load(sys.stdin)['data']]" \
      2>/dev/null || echo "      vLLM:8000 → offline"
    curl -s http://localhost:8080/v1/models 2>/dev/null | \
      python3 -c "import sys,json; [print('      llama.cpp:8080 →',m['id']) for m in json.load(sys.stdin)['data']]" \
      2>/dev/null || echo "      llama.cpp:8080 → offline"
}

echo "╔══════════════════════════════════════════════════════╗"
echo "║              ESTADO INICIAL (DIAGNÓSTICO)            ║"
echo "╚══════════════════════════════════════════════════════╝"
mostrar_diagnostico

echo "╔══════════════════════════════════════════════════════╗"
echo "║                  EJECUTANDO LIMPIEZA                 ║"
echo "╚══════════════════════════════════════════════════════╝"

CONTAINERS=$(docker ps --format '{{.Names}}' \
  | grep -E "vllm|llama|qwen|gemma|nemotron|cosmos|gpt|openclaw|open-webui")
if [ -n "$CONTAINERS" ]; then
    echo "→ Eliminando contenedores (docker rm -f)..."
    echo "$CONTAINERS" | sed 's/^/    - /'
    docker rm -f $CONTAINERS >/dev/null 2>&1
    echo "  OK Listo."
else
    echo "→ Sin contenedores de inferencia activos."
fi

echo "→ Limpiando procesos huérfanos..."
sudo pkill -f vllm 2>/dev/null || true
sudo pkill -f "python.*qwen\|python.*gemma\|python.*llama" 2>/dev/null || true

if systemctl is-active --quiet ollama; then
    echo "→ Descargando modelos Ollama de GPU..."
    for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
        curl -s http://localhost:11434/api/generate \
          -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null
        echo "    OK $m descargado"
    done
    sudo systemctl stop ollama 2>/dev/null && echo "  OK Ollama detenido"
fi

echo "→ Liberando page cache y swap..."
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sudo swapoff -a && sudo swapon -a 2>/dev/null || true
sleep 5

echo "╔══════════════════════════════════════════════════════╗"
echo "║               ESTADO FINAL (REPORTE)                 ║"
echo "╚══════════════════════════════════════════════════════╝"
mostrar_diagnostico
EOF

chmod +x ~/scripts/jetson-clean.sh
echo "[OK] jetson-clean.sh instalado"
```

---

## A.17 Script de Variables de Entorno (`llm-vars`)

```bash
# Reinstalar llm-env.sh si se pierde
mkdir -p ~/scripts/llm/env

cat > ~/scripts/llm/env/llm-env.sh << 'ENVEOF'
#!/bin/bash
# Activar antes de lanzar modelos gated (Gemma 4 E4B, GPT OSS 20B)
export HF_TOKEN="hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXX"   # ← REEMPLAZAR
export VLLM_API_KEY=""
export CUDA_HOME="/usr/local/cuda-13.2"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"
export TIKTOKEN_ENCODINGS_BASE="$HOME/.cache/tiktoken"
echo "[OK] llm-vars: HF_TOKEN ${HF_TOKEN:0:10}..."
ENVEOF

chmod 600 ~/scripts/llm/env/llm-env.sh
echo "alias llm-vars='source ~/scripts/llm/env/llm-env.sh'" >> ~/.bash_aliases
source ~/.bash_aliases
```

---

## A.18 Referencia de Stacks — ¿Qué Iniciar para Cada Caso de Uso?

Esta tabla resume qué servicios iniciar según la tarea, en orden de arranque.

| Caso de uso | Servicios | Alias / Comando | Modo energético | RAM aprox. |
|-------------|-----------|-----------------|-----------------|------------|
| **Chat básico con LLM** | Ollama | `ollama serve && ollama run qwen3.5:7b` | 30W | ~20 GB |
| **Chat con UI web** | `docker-on` + Open WebUI + Ollama | `start-webui && ollama serve` | 30W | ~22 GB |
| **Modelo grande (35B)** | `docker-on` + vLLM | `start-qwen35` | MAXN | ~34 GB |
| **Transcripción de audio** | `docker-on` + faster-whisper | `start-whisper` | 30W | ~17 GB |
| **Síntesis de voz (TTS)** | `docker-on` + kokoro-tts | `start-kokoro` | 30W | ~14 GB |
| **Asistente de voz offline** | `docker-on` + faster-whisper + Ollama (4B) | `start-whisper && ollama serve` → `voice-assistant` | 30W | ~22 GB |
| **Visión por computadora** | `docker-on` + gemma4-e4b llama.cpp | `start-vision` | MAXN | ~18 GB |
| **RAG empresarial** | Ollama + FastAPI RAG | `ollama serve && source venv && python3 rag_server.py` | 30W | ~22 GB |
| **Agentes IA (OpenClaw)** | Ollama + OpenClaw | `ollama serve && openclaw-start` | 30W | ~22 GB |
| **Automatización N8N** | `docker-on` + N8N + PostgreSQL | `start-n8n` | 30W | ~14 GB |
| **Agencia IA completa** | Todo | `agency-start` | 30W → MAXN | ~46 GB |
| **Exposición a internet** | Nginx + JWT + cloudflared | `start-gateway` | 30W | +0.3 GB |

### Secuencia de limpieza universal

Después de cualquier pipeline, ejecutar siempre:

```bash
jetson-clean   # Detiene contenedores, limpia procesos, libera caché
pwr-15w        # Modo ahorro hasta el próximo uso
```

### Cuándo usar `pwr-maxn` vs `pwr-30w`

```
pwr-maxn  → modelos >9B, arranque de vLLM, pipeline con 35B activo
pwr-30w   → STT/TTS, Ollama ≤7B, agentes, N8N, RAG, espera activa
pwr-15w   → sin inferencia activa, limpieza, SSH únicamente
```

> **Regla final:** El Jetson arranca siempre en `multi-user.target` sin Docker ni modelos. Cada servicio se inicia manualmente o via alias bajo demanda, y se detiene con `jetson-clean` al terminar. Este ciclo garantiza que los 64 GB de RAM estén siempre disponibles para el modelo que los necesite.

---

## A.19 Tabla de Errores Frecuentes — Referencia Rápida

| Error | Causa | Solución rápida |
|-------|-------|-----------------|
| `CUDA out of memory` | RAM GPU insuficiente | `jetson-clean` → reducir `--gpu-memory-utilization 0.65` |
| `Content: None` en respuesta | `--reasoning-parser` activo | Omitir `--reasoning-parser` del comando |
| `address already in use :8000` | faster-whisper y vLLM simultáneos | Usar `--port 8001` para vLLM |
| `docker: Cannot connect to daemon` | Docker no iniciado | `docker-on` |
| `nvidia-smi not found` | Normal en Jetson | Usar `jtop` o `nvcc --version` |
| N8N no alcanza `localhost:8000` | Aislamiento bridge Docker | Usar `172.18.0.1` (IP gateway bridge) |
| `NemoClaw repo not found` | Repo de JetsonHacks no existe | Usar `curl -fsSL nvidia.com/nemoclaw.sh | bash` |
| Cloudflare Tunnel caído | Credenciales expiradas | `cloudflared tunnel login && sudo systemctl restart cloudflared` |
| `pwr-15w` no funciona | Alias usa `-m 1` incorrecto | Verificar que el alias usa `-m 3` (ver A.3) |
| `llm-env` activa entorno equivocado | Alias conflicto | `llm-env` = venv Python; `llm-vars` = tokens/rutas |
| ComfyUI no carga modelo | AnimateDiff node falta | `docker exec comfyui pip install -r /root/ComfyUI/custom_nodes/ComfyUI-AnimateDiff-Evolved/requirements.txt` |
| SD WebUI — imagen muy oscura | VAE no configurado | Settings → SD VAE → seleccionar `vae-ft-mse-840000-ema-pruned.safetensors` |

---

## A.20 Aliases de Generación de Imágenes y Video — Capítulo 19

```bash
# Agregar al ~/.bash_aliases

# ComfyUI (:8188) — Workflows visuales
alias start-comfyui='cd ~/stacks/comfyui && docker compose up -d && echo "[OK] ComfyUI en http://localhost:8188 (espere 60s)"'
alias stop-comfyui='docker stop comfyui && echo "[OK] ComfyUI detenido"'
alias logs-comfyui='docker logs comfyui --follow'

# SD WebUI (:7860) — Interfaz clásica txt2img / img2img
alias start-sdwebui='cd ~/stacks/sd-webui && docker compose up -d && echo "[OK] SD WebUI en http://localhost:7860 (espere 90s)"'
alias stop-sdwebui='docker stop sd-webui && echo "[OK] SD WebUI detenido"'
alias logs-sdwebui='docker logs sd-webui --follow'

# Monitoreo durante generación
alias monitor-gen='watch -n 2 "docker stats comfyui sd-webui --no-stream 2>/dev/null; echo; free -h | grep Mem"'

# Gestión de modelos
alias list-models='echo "=== Checkpoints ==="; ls -lh ~/models/checkpoints/ 2>/dev/null; echo "=== LoRA ==="; ls -lh ~/models/loras/ 2>/dev/null; echo "=== VAE ==="; ls -lh ~/models/vae/ 2>/dev/null'
alias list-generated='ls -lt ~/stacks/comfyui/output/ ~/stacks/sd-webui/output/ 2>/dev/null | head -20'

# Scripts auxiliares
alias preflight-gen='~/scripts/preflight-image-gen.sh'
alias status-gen='~/scripts/status-image-generation.sh'
alias download-sd='~/scripts/download-sd-models.sh'
```

---

## A.21 Árbol de Directorios del Jetson (Sistema Operativo)

Esta es la estructura de directorios que se crea durante el libro en el Jetson AGX Orin:

```
/home/jetson/
├── scripts/                         # Todos los scripts del libro
│   ├── maintenance/
│   │   ├── check-ready.sh           # Pre-check de recursos (Cap 18)
│   │   ├── clean-ai-containers.sh   # Limpieza de contenedores (Cap 26)
│   │   ├── switch-project.sh        # Cambio entre proyectos (Cap 26)
│   │   ├── hf-cache-clean.sh        # Limpieza caché HuggingFace (Cap 26)
│   │   ├── health-check.sh          # Check de salud del sistema (Cap 26)
│   │   └── system-status.sh         # Estado general del sistema (Cap 26)
│   ├── llm/
│   │   └── env/
│   │       └── llm-env.sh           # Variables: HF_TOKEN, CUDA paths (Cap 15)
│   ├── gateway/
│   │   ├── gateway-manage.sh        # Gestión Nginx + JWT + Cloudflare (Cap 30)
│   │   ├── new-client.sh            # Alta de nuevos clientes API (Cap 30)
│   │   └── .env                     # ADMIN_KEY, CLOUDFLARE_TOKEN
│   ├── jetson-clean.sh              # Limpieza profunda con diagnóstico (Cap 14)
│   ├── switch-model.sh              # Cambio rápido entre modelos LLM (Cap 12)
│   ├── agency-start.sh              # Arranque agencia IA completa (Cap 31)
│   ├── agency-stop.sh               # Detención agencia IA (Cap 31)
│   ├── download-sd-models.sh        # Descarga checkpoints SD (Cap 19)
│   ├── generate-anime-batch.py      # Generación lote anime via API (Cap 19)
│   ├── generate-animatediff.py      # Video con AnimateDiff via API (Cap 19)
│   ├── generate-pixart.py           # Imágenes con PixArt-Alpha (Cap 19)
│   ├── status-image-generation.sh   # Estado ComfyUI + SD WebUI (Cap 19)
│   ├── preflight-image-gen.sh       # Pre-check antes de generar (Cap 19)
│   └── voice_assistant_pipeline.py  # Pipeline STT+LLM+TTS (Cap 29)
│
├── venvs/                           # Entornos virtuales Python
│   ├── llm/                         # PyTorch + transformers + vLLM
│   └── sdtools/                     # Diffusers + PixArt
│
├── models/                          # Modelos de imagen (compartidos ComfyUI/SD WebUI)
│   ├── checkpoints/                 # Modelos SD 1.5, SDXL, Pony...
│   ├── loras/                       # Adaptadores LoRA
│   ├── vae/                         # VAE mejorado
│   ├── embeddings/                  # Textual inversion
│   ├── controlnet/                  # ControlNet
│   ├── upscalers/                   # ESRGAN upscalers
│   └── animatediff/                 # Motion modules
│
├── stacks/                          # Docker Compose stacks (G10)
│   ├── n8n/
│   │   ├── docker-compose.yml       # N8N + PostgreSQL (Cap 27)
│   │   └── .env
│   ├── comfyui/
│   │   ├── docker-compose.yml       # ComfyUI (Cap 19)
│   │   ├── output/                  # Imágenes y videos generados
│   │   └── workflows/               # Workflows guardados
│   ├── sd-webui/
│   │   ├── docker-compose.yml       # SD WebUI AUTOMATIC1111 (Cap 19)
│   │   ├── output/                  # Imágenes generadas
│   │   └── extensions/              # Extensiones instaladas
│   ├── voice/
│   │   └── compose.yml              # faster-whisper + kokoro-tts (Cap 8)
│   └── webui-whisper/
│       └── compose.yml              # Open WebUI + whisper (Cap 8)
│
├── projects/                        # Proyectos de IA (Phase 2)
│   ├── pdf2podcast/                 # Cap 19 — PDF a pódcast
│   ├── transcription-bot/           # Cap 20 — Bot de transcripción
│   ├── tourism-agency/              # Cap 21 — Agencia de turismo
│   ├── sales-funnel/                # Cap 22 — Funnel de ventas
│   ├── linkedin-content/            # Cap 23 — Contenido LinkedIn
│   ├── voice-assistant/             # Cap 24 — Asistente de voz
│   ├── rag-empresarial/             # Cap 25 — RAG empresarial
│   ├── pixart-output/               # Cap 19 — Imágenes PixArt
│   └── daily-prayers/               # Cap 32 — Pipeline YouTube Shorts
│
├── logs/                            # Logs de servicios
│   ├── flask_agencia.log            # Agencia IA Flask (Cap 31)
│   └── gateway.log                  # Nginx + JWT gateway (Cap 30)
│
└── .bash_aliases                    # Todos los aliases del libro (G9)

# Directorios de caché de modelos LLM
~/.cache/
├── huggingface/
│   └── hub/
│       └── models--*/               # Modelos HF descargados automáticamente
├── vllm/                            # KV cache de vLLM
└── tiktoken/                        # Encodings para GPT-OSS-20B

~/.ollama/
└── models/                          # Modelos Ollama (formato blob)
```

---

## A.22 Inventario Completo de Scripts

| Script | Ubicación | Descripción | Capítulo |
|--------|-----------|-------------|---------|
| `check-ready.sh` | `~/scripts/maintenance/` | Pre-check de RAM y espacio antes de pipeline | 18 |
| `clean-ai-containers.sh` | `~/scripts/maintenance/` | Limpia contenedores de proyectos IA | 26 |
| `switch-project.sh` | `~/scripts/maintenance/` | Cambia entre proyectos activos | 26 |
| `hf-cache-clean.sh` | `~/scripts/maintenance/` | Limpia caché HuggingFace de modelos no usados | 26 |
| `health-check.sh` | `~/scripts/maintenance/` | Verifica salud: endpoints, RAM, temperatura | 26 |
| `system-status.sh` | `~/scripts/maintenance/` | Estado general del Jetson (contenedores, RAM, modos) | 26 |
| `jetson-clean.sh` | `~/scripts/` | Limpieza profunda: contenedores + procesos + page cache | 14 |
| `llm-env.sh` | `~/scripts/llm/env/` | Variables de entorno: HF_TOKEN, CUDA, paths | 15 |
| `switch-model.sh` | `~/scripts/` | Cambio rápido entre motores de inferencia | 12 |
| `agency-start.sh` | `~/scripts/` | Arranque orquestado de agencia IA completa | 31 |
| `agency-stop.sh` | `~/scripts/` | Detención limpia de agencia IA | 31 |
| `gateway-manage.sh` | `~/scripts/gateway/` | Gestión de Nginx + JWT + Cloudflare Tunnel | 30 |
| `new-client.sh` | `~/scripts/gateway/` | Alta de cliente API con JWT | 30 |
| `download-sd-models.sh` | `~/scripts/` | Descarga checkpoints SD 1.5 + SDXL + VAE | 19 |
| `generate-anime-batch.py` | `~/scripts/` | Generación en lote via API de SD WebUI | 19 |
| `generate-animatediff.py` | `~/scripts/` | Video corto con AnimateDiff via API ComfyUI | 19 |
| `generate-pixart.py` | `~/scripts/` | Imágenes con PixArt-Alpha vía Diffusers | 19 |
| `status-image-generation.sh` | `~/scripts/` | Estado de ComfyUI y SD WebUI | 19 |
| `preflight-image-gen.sh` | `~/scripts/` | Pre-check antes de sesión de generación de imágenes | 19 |
| `voice_assistant_pipeline.py` | `~/scripts/` | Pipeline completo STT → LLM → TTS offline | 29 |
| `diarize_and_transcribe.py` | `~/scripts/` | Transcripción con diarización de hablantes | 29 |
| `tts_kokoro.py` | `~/scripts/` | Síntesis de voz alta calidad con kokoro-tts | 29 |
| `tts_piper.py` | `~/scripts/` | TTS rápido con piper (baja latencia) | 29 |
| `ocr_pipeline.py` | `~/scripts/` | OCR con pytesseract + EasyOCR | 28 |
| `ocr_to_llm.py` | `~/scripts/` | OCR + análisis LLM de documentos | 28 |
| `vision_describe.py` | `~/scripts/` | Descripción de imágenes con Gemma 4 E4B | 28 |
| `nanoowl_detect.py` | `~/scripts/` | Detección de objetos zero-shot con nanoowl | 28 |
| `video_monitor.py` | `~/scripts/` | Monitoreo de video con detección en tiempo real | 28 |

---

## A.23 Puertos — Referencia Ampliada por Capítulo

| Puerto | Servicio | Capítulo | Protocolo | Notas |
|--------|----------|---------|-----------|-------|
| 22 | SSH | 2 | TCP | Siempre activo; `ssh jetson` |
| 3000 | Open WebUI | 13C | HTTP | Interfaz web para LLMs |
| 3001 | Uptime Kuma | 30 | HTTP | Monitor de disponibilidad |
| 5000 | Flask (Agencia IA) | 31 | HTTP | Frontend web con SSE |
| 5432 | PostgreSQL (N8N) | 27 | TCP | Solo interno, no exponer |
| 5678 | N8N | 27 | HTTP | Automatización de workflows |
| 7860 | SD WebUI | 19 | HTTP | AUTOMATIC1111 txt2img / img2img |
| 8000 | vLLM / faster-whisper | 12/29 | HTTP | Conflicto: no usar simultáneamente |
| 8001 | vLLM (alternativo) | 12 | HTTP | Cuando faster-whisper ocupa :8000 |
| 8080 | llama.cpp | 12 | HTTP | Motor GGUF; compatible OpenAI API |
| 8088 | Nginx gateway | 30 | HTTP | Reverse proxy único de entrada |
| 8123 | Home Assistant | — | HTTP | IoT (opcional) |
| 8188 | ComfyUI | 19 | HTTP | Workflows visuales imagen/video |
| 8888 | JupyterLab | 17 | HTTP | Notebooks con GPU via SSH tunnel |
| 8880 | kokoro-tts | 29 | HTTP | TTS alta calidad (español/inglés) |
| 9000 | RAG API (FastAPI) | 25 | HTTP | RAG empresarial ChromaDB |
| 9100 | JWT Auth Gateway | 30 | HTTP | Autenticación de clientes API |
| 10200 | piper-tts | 29 | HTTP | TTS rápido CPU (<200ms) |
| 11434 | Ollama | 12 | HTTP | Modelos locales sin contenedor |
| 18789 | OpenClaw / NemoClaw | 12/13A | HTTP | Orquestador de agentes IA |

**Conflictos a gestionar:**
- `:8000` — `faster-whisper` y `vLLM` comparten puerto. Lanzar vLLM en `:8001` si ambos son necesarios simultáneamente.
- `:7860` — `SD WebUI` y `nanoDB WebUI` comparten puerto. No correr ambos al mismo tiempo.
- `:8080` — `llama.cpp` y `piper-tts` pueden compartir si se usa piper en contenedor separado con `--network host` pero puertos distintos.

---

## A.24 Script de Instalación Limpia — Jetson Recién Flasheado

Este script automatiza la configuración inicial del Jetson AGX Orin (Capítulos 1–8). Ejecútelo una sola vez en un sistema recién flasheado con JetPack 7.2 **después del primer arranque y configuración de usuario**.

```bash
# Descargar y ejecutar
# OPCIÓN A — Si tiene el libro en el Jetson:
bash ~/projects/setup-jetson.sh

# OPCIÓN B — Crear el script manualmente:
cat > ~/setup-jetson.sh << 'SETUP_EOF'
#!/bin/bash
# setup-jetson.sh — Configuración inicial Jetson AGX Orin / JP 7.2
# Tiempo estimado: 15-25 minutos (depende de la velocidad de internet)

set -euo pipefail
LOG="$HOME/setup-jetson.log"
exec > >(tee -a "$LOG") 2>&1
echo "[$(date)] Iniciando configuración inicial del Jetson AGX Orin JP 7.2"

# ── 1. Actualización del sistema ─────────────────────────────────────
echo ""
echo "══ [1/8] Actualizando sistema ══"
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  curl wget git vim htop net-tools tree jq \
  build-essential cmake pkg-config \
  python3-pip python3-venv python3-dev \
  nvme-cli smartmontools hdparm \
  aria2 nmap iftop nethogs \
  tmux screen \
  ffmpeg libsndfile1 portaudio19-dev \
  alsa-utils libespeak-ng-dev espeak-ng \
  tesseract-ocr tesseract-ocr-spa libtesseract-dev \
  nginx logrotate \
  libnss3-tools

# ── 2. Docker + NVIDIA Container Toolkit ─────────────────────────────
echo ""
echo "══ [2/8] Instalando Docker + NVIDIA Container Toolkit ══"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sudo bash
  sudo usermod -aG docker jetson
fi

if ! dpkg -l | grep -q nvidia-container-toolkit; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  sudo apt update && sudo apt install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
fi

# Deshabilitar Docker en arranque (inicio bajo demanda con docker-on)
sudo systemctl disable docker.socket docker
sudo systemctl stop docker.socket docker 2>/dev/null || true
echo "[OK] Docker instalado — iniciado bajo demanda con 'docker-on'"

# ── 3. Estructura de directorios ─────────────────────────────────────
echo ""
echo "══ [3/8] Creando estructura de directorios ══"
mkdir -p ~/scripts/maintenance ~/scripts/llm/env ~/scripts/gateway
mkdir -p ~/projects ~/stacks ~/logs ~/data/models
mkdir -p ~/venvs
sudo chown -R jetson:jetson /data 2>/dev/null || true
echo "[OK] Directorios creados"

# ── 4. Python — Entornos Virtuales ───────────────────────────────────
echo ""
echo "══ [4/8] Creando entornos virtuales Python ══"
if [ ! -d ~/venvs/dev ]; then
  python3 -m venv ~/venvs/dev
  ~/venvs/dev/bin/pip install --upgrade pip wheel setuptools
  echo "[OK] venv dev creado"
fi

if [ ! -d ~/venvs/llm ]; then
  python3 -m venv ~/venvs/llm
  ~/venvs/llm/bin/pip install --upgrade pip wheel setuptools
  echo "[OK] venv llm creado"
fi

# ── 5. .bashrc — Variables de entorno ────────────────────────────────
echo ""
echo "══ [5/8] Configurando .bashrc ══"
if ! grep -q "# JETSON JP7.2 CONFIG" ~/.bashrc; then
cat >> ~/.bashrc << 'BASHRC_EOF'

# JETSON JP7.2 CONFIG — añadido por setup-jetson.sh
export CUDA_HOME="/usr/local/cuda-13.2"
export PATH="$CUDA_HOME/bin:$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"
export TORCH_CUDA_ARCH_LIST="8.7"
export HF_TOKEN=""          # Completar en: https://huggingface.co/settings/tokens
export OPENROUTER_API_KEY="" # Completar en: https://openrouter.ai/keys
export OPENROUTER_URL="https://openrouter.ai/api/v1"
export VLLM_API_KEY=""      # Completar si usa vLLM con autenticación
export HISTSIZE=10000
export HISTFILESIZE=20000
[[ -f ~/.bash_aliases ]] && source ~/.bash_aliases
BASHRC_EOF
  echo "[OK] .bashrc configurado"
fi

# ── 6. .bash_aliases ─────────────────────────────────────────────────
echo ""
echo "══ [6/8] Instalando aliases ══"
if [ ! -f ~/.bash_aliases ]; then
  curl -fsSL "$HOME/scripts/bash_aliases_template.sh" -o ~/.bash_aliases 2>/dev/null || \
  cat > ~/.bash_aliases << 'ALIAS_EOF'
# Energía
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks'
alias pwr-30w='sudo nvpmodel -m 2'
alias pwr-15w='sudo nvpmodel -m 3'
# Docker
alias docker-on='sudo systemctl start docker.socket && sudo systemctl start docker'
alias docker-off='sudo systemctl stop docker && sudo systemctl stop docker.socket'
# Python venvs
alias dev-env='source ~/venvs/dev/bin/activate'
alias llm-env='source ~/venvs/llm/bin/activate'
ALIAS_EOF
  echo "[OK] .bash_aliases básico instalado — ver A.26 del Apéndice para la versión completa"
fi

# ── 7. SWAP + ZRAM (si no están configurados) ─────────────────────────
echo ""
echo "══ [7/8] Verificando SWAP ══"
SWAP_TOTAL=$(swapon --show 2>/dev/null | wc -l)
if [ "$SWAP_TOTAL" -eq 0 ]; then
  echo "[WARN] Sin swap configurado — ver Capítulo 4 para configurar ZRAM y swap"
else
  echo "[OK] Swap activo: $(swapon --show | tail -1)"
fi

# ── 8. Verificación final ─────────────────────────────────────────────
echo ""
echo "══ [8/8] Verificación final ══"
echo "  Ubuntu: $(lsb_release -rs)"
echo "  Kernel: $(uname -r)"
echo "  CUDA:   $(nvcc --version 2>/dev/null | grep 'release' | awk '{print $6}' | tr -d ',') "
echo "  Python: $(python3 --version)"
echo "  Docker: $(docker --version 2>/dev/null | awk '{print $3}' | tr -d ',')"
echo ""
echo "══ [OK] Configuración inicial completada ══"
echo "   Siguiente paso: Capítulo 4 (Memoria y Almacenamiento)"
echo "   Log: $LOG"
echo ""
echo "   IMPORTANTE: Cierre la sesión SSH y vuelva a conectar para"
echo "   que los cambios de grupo (docker) y .bashrc tengan efecto."
SETUP_EOF

chmod +x ~/setup-jetson.sh
echo "[OK] setup-jetson.sh listo — ejecutar: bash ~/setup-jetson.sh"
```

---

## A.25 `.bashrc` Completo para JetPack 7.2

Plantilla de `.bashrc` con todas las variables de entorno necesarias para el libro. Añada estas líneas al final del `.bashrc` existente (no reemplazar el archivo completo):

```bash
# ── Añadir al final de ~/.bashrc ──────────────────────────────────────
# Ruta CUDA 13.2.1 (JetPack 7.2)
export CUDA_HOME="/usr/local/cuda-13.2"
export PATH="$CUDA_HOME/bin:$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"

# Arquitectura GPU Jetson AGX Orin (Ampere sm_87)
export TORCH_CUDA_ARCH_LIST="8.7"

# HuggingFace
export HF_TOKEN=""          # https://huggingface.co/settings/tokens
export HF_HOME="$HOME/.cache/huggingface"
export HF_HUB_OFFLINE=0    # Cambiar a 1 para modo offline total

# APIs externas (opcionales)
export OPENROUTER_API_KEY="" # https://openrouter.ai/keys
export OPENROUTER_URL="https://openrouter.ai/api/v1"
export VLLM_API_KEY=""      # Solo si vLLM usa autenticación

# Historial extendido
export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTCONTROL=ignoredups:erasedups

# Aliases
[[ -f ~/.bash_aliases ]] && source ~/.bash_aliases

# Prompt informativo (muestra venv activo)
if [ -n "$VIRTUAL_ENV" ]; then
  VENV_NAME="($(basename $VIRTUAL_ENV)) "
fi
PS1="${VENV_NAME}\u@\h:\w\$ "
```

**Verificar que .bashrc está correctamente cargado:**

```bash
source ~/.bashrc
echo "CUDA_HOME: $CUDA_HOME"
echo "HF_TOKEN:  ${HF_TOKEN:0:10}..."
nvcc --version 2>/dev/null | grep release || echo "[WARN] CUDA no en PATH"
```

---

## A.26 `.bash_aliases` Consolidado — Instalación en Un Paso

Archivo completo de aliases del libro. Instálelo con:

```bash
# Hacer backup del archivo existente
[ -f ~/.bash_aliases ] && cp ~/.bash_aliases ~/.bash_aliases.bak

# Instalar la versión consolidada
cat > ~/.bash_aliases << 'ALIASES_EOF'
# ══════════════════════════════════════════════════════════════════════
# ~/.bash_aliases — Jetson AGX Orin 64GB / JetPack 7.2
# Generado por: Libro "Getting Started with NVIDIA Jetson AGX Orin"
# ══════════════════════════════════════════════════════════════════════

# ── Energía y rendimiento (Cap 3) ─────────────────────────────────────
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "[OK] Modo MAXN (50W)"'
alias pwr-30w='sudo nvpmodel -m 2 && echo "[OK] Modo 30W"'
alias pwr-15w='sudo nvpmodel -m 3 && echo "[OK] Modo 15W"'
alias pwr-status='sudo nvpmodel -q && sudo jetson_clocks --show 2>/dev/null | head -5'

# ── Docker bajo demanda (Cap 8) ────────────────────────────────────────
alias docker-on='sudo systemctl start docker.socket && sudo systemctl start docker && echo "[OK] Docker activo"'
alias docker-off='sudo systemctl stop docker && sudo systemctl stop docker.socket && echo "[OK] Docker detenido"'
alias docker-status='docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# ── Python venvs (Cap 5 y 17) ─────────────────────────────────────────
alias dev-env='source ~/venvs/dev/bin/activate && echo "[OK] venv dev"'
alias llm-env='source ~/venvs/llm/bin/activate && echo "[OK] venv llm"'
alias llm-vars='source ~/scripts/llm/env/llm-env.sh'

# ── Descargas (Cap 6) ─────────────────────────────────────────────────
alias dl-model='bash ~/scripts/dl-model.sh'
dl() { aria2c -x16 -s16 -k5M --dir="${3:-.}" -o "${2:-$(basename $1)}" "$1"; }
alias dl-iso='aria2c -x16 -s16 -k5M --summary-interval=5'
alias dl-dataset='aria2c -x8 -s8 -k5M --disk-cache=64M --summary-interval=10'

# ── Mantenimiento (Cap 26) ─────────────────────────────────────────────
alias jetson-clean='~/scripts/jetson-clean.sh'
alias check-ready='~/scripts/maintenance/check-ready.sh'
alias clean-ai-containers='~/scripts/maintenance/clean-ai-containers.sh'
alias switch-project='~/scripts/maintenance/switch-project.sh'
alias hf-cache='~/scripts/maintenance/hf-cache-clean.sh'
alias health-check='~/scripts/maintenance/health-check.sh'
alias sys-status='~/scripts/maintenance/system-status.sh'
alias motors-status='~/scripts/maintenance/system-status.sh'

# ── Motores de inferencia — Ollama (Cap 12) ───────────────────────────
alias ollama-start='sudo systemctl start ollama && echo "[OK] Ollama activo en :11434"'
alias ollama-stop='sudo systemctl stop ollama'
alias ollama-models='ollama list'
alias ollama-ps='ollama ps'

# ── Motores de inferencia — vLLM (Cap 12) ────────────────────────────
alias start-qwen35='pwr-maxn && docker run -d --name qwen35-35b --restart no \
  --runtime nvidia --network host --ipc host --shm-size 8g \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
    --gpu-memory-utilization 0.70 --enable-prefix-caching \
    --served-model-name qwen35 --max-model-len 8192 --host 0.0.0.0 --port 8000" && \
  until curl -sf http://localhost:8000/v1/models > /dev/null; do sleep 20; done && \
  echo "[OK] qwen35 listo en :8000"'
alias stop-qwen35='docker stop qwen35-35b && docker rm qwen35-35b'
alias vllm-logs='docker logs qwen35-35b --follow'

# ── Motores de inferencia — llama.cpp (Cap 12) ────────────────────────
alias start-nemotron='pwr-maxn && docker run -d --name nemotron --restart no \
  --runtime nvidia --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
  --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
  --ctx-size 16384 --port 8080 --host 0.0.0.0 --n-gpu-layers 999 && \
  until curl -sf http://localhost:8080/v1/models > /dev/null; do sleep 15; done && \
  echo "[OK] nemotron listo en :8080"'
alias stop-nemotron='docker stop nemotron && docker rm nemotron'

# ── Open WebUI (Cap 13C) ──────────────────────────────────────────────
alias start-webui='docker run -d --name open-webui --runtime nvidia --restart no \
  --network host -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main && echo "[OK] Open WebUI en http://localhost:3000"'
alias stop-webui='docker stop open-webui && docker rm open-webui'
alias webui-logs='docker logs open-webui --follow'

# ── OpenClaw / NemoClaw (Caps 13A, 13B) ──────────────────────────────
alias openclaw-start='cd ~/projects/openclaw && node index.js &'
alias openclaw-stop='pkill -f "node.*openclaw" && echo "[OK] OpenClaw detenido"'
alias claw-status='curl -sf http://localhost:18789/health && echo " OpenClaw activo" || echo " OpenClaw offline"'

# ── STT / TTS (Caps 13C, 18, 29) ─────────────────────────────────────
alias start-whisper='docker run --runtime nvidia -d --name faster-whisper --restart no \
  --network host -e WHISPER_MODEL=large-v3 -e WHISPER_DEVICE=cuda \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  dustynv/faster-whisper:r39.2.0 && echo "[OK] faster-whisper en :8000"'
alias stop-whisper='docker stop faster-whisper && docker rm faster-whisper'
alias whisper-logs='docker logs faster-whisper --follow'

alias start-kokoro='docker run --runtime nvidia -d --name kokoro-tts --restart no \
  --network host -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  dustynv/kokoro-tts:r39.2.0 && echo "[OK] kokoro-tts en :8880"'
alias stop-kokoro='docker stop kokoro-tts && docker rm kokoro-tts'
alias kokoro-logs='docker logs kokoro-tts --follow'

# Pipeline de voz
alias voice-assistant='dev-env && python3 ~/scripts/voice_assistant_pipeline.py'
alias transcribir='dev-env && python3 ~/scripts/diarize_and_transcribe.py'
alias tts-es='dev-env && python3 ~/scripts/tts_kokoro.py'
alias tts-rapido='dev-env && python3 ~/scripts/tts_piper.py'

# ── N8N (Cap 27) ──────────────────────────────────────────────────────
alias start-n8n='cd ~/stacks/n8n && docker compose up -d && cd -'
alias stop-n8n='cd ~/stacks/n8n && docker compose down && cd -'
alias n8n-logs='cd ~/stacks/n8n && docker compose logs --tail=50 -f && cd -'
alias n8n-url='echo "http://$(hostname -I | awk "{print \$1}"):5678"'

# ── Computer Vision (Cap 28) ──────────────────────────────────────────
alias start-vision='docker run --runtime nvidia -d --name gemma4-e4b-llama --restart no \
  --network host -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server -hf unsloth/gemma-4-E4B:Q4_K_M \
  --ctx-size 32768 --n-gpu-layers 999 --port 8080 --alias gemma4-e4b --host 0.0.0.0'
alias stop-vision='docker stop gemma4-e4b-llama && docker rm gemma4-e4b-llama'
alias ocr-imagen='dev-env && python3 ~/scripts/ocr_pipeline.py'
alias ocr-llm='dev-env && python3 ~/scripts/ocr_to_llm.py'
alias vision-describe='dev-env && python3 ~/scripts/vision_describe.py'
alias nanoowl-detect='dev-env && python3 ~/scripts/nanoowl_detect.py'
alias video-monitor='dev-env && python3 ~/scripts/video_monitor.py'

# ── Generación de imágenes / video (Cap 19) ───────────────────────────
alias start-comfyui='cd ~/stacks/comfyui && docker compose up -d && cd - && echo "[OK] ComfyUI en :8188 (espere 60s)"'
alias stop-comfyui='docker stop comfyui && docker rm comfyui'
alias start-sdwebui='cd ~/stacks/sd-webui && docker compose up -d && cd - && echo "[OK] SD WebUI en :7860 (espere 90s)"'
alias stop-sdwebui='docker stop sd-webui && docker rm sd-webui'
alias list-models='ls -lh ~/models/checkpoints/ 2>/dev/null; ls -lh ~/models/loras/ 2>/dev/null'

# ── JupyterLab (Cap 17) ───────────────────────────────────────────────
alias jupyter-start='dev-env && jupyter lab --no-browser --port=8888 --ip=0.0.0.0 &'
alias jupyter-stop='pkill -f jupyter && echo "[OK] Jupyter detenido"'

# ── RAG Empresarial (Cap 25) ──────────────────────────────────────────
alias rag-start='dev-env && uvicorn api.rag_api:app --host 0.0.0.0 --port 9000 &'
alias rag-stop='pkill -f "uvicorn.*rag_api" && echo "[OK] RAG API detenida"'
alias rag-query='dev-env && python3 ~/projects/rag-empresarial/scripts/query.py'

# ── Pipeline PDF-to-Podcast (Cap 19) ─────────────────────────────────
alias pdf2podcast='bash ~/projects/pdf2podcast/pdf2podcast.sh'

# ── LinkedIn / Social (Cap 23) ────────────────────────────────────────
alias linkedin-local='USE_LOCAL_LLM=true  python3 ~/projects/linkedin-content/scripts/pipeline.py'
alias linkedin-cloud='USE_LOCAL_LLM=false python3 ~/projects/linkedin-content/scripts/pipeline.py'

# ── Gateway / Infraestructura (Caps 30, 31) ──────────────────────────
alias start-gateway='~/scripts/gateway/gateway-manage.sh start'
alias stop-gateway='~/scripts/gateway/gateway-manage.sh stop'
alias gateway-status='~/scripts/gateway/gateway-manage.sh status'
alias new-client='~/scripts/gateway/new-client.sh'
alias agency-start='~/scripts/agency-start.sh'
alias agency-stop='~/scripts/agency-stop.sh'
alias agency-status='curl -s http://localhost:5000/health | python3 -m json.tool'

# ── Capstone 02 — Daily Prayers / Video (Cap 32) ─────────────────────
alias daily-prayers='python3 ~/projects/daily-prayers/orchestrator.py'

# ── Diagnóstico rápido ────────────────────────────────────────────────
alias jetson-mem='free -h | awk "/^Mem:/{printf \"RAM: %s usados, %s libres de %s\n\", \$3, \$7, \$2}"'
alias jetson-temp='cat /sys/devices/virtual/thermal/thermal_zone*/temp 2>/dev/null | awk "{printf \"%.1f°C \", \$1/1000}" && echo'
alias jetson-ports='for p in 3000 5000 5678 7860 8000 8001 8080 8088 8188 8880 8888 9000 9100 11434 18789; do curl -sf http://localhost:$p/health --max-time 1 > /dev/null 2>&1 && echo "  :$p activo" || true; done'
alias jetson-audit='sys-status'

ALIASES_EOF

source ~/.bash_aliases
echo "[OK] .bash_aliases instalado — $(grep "^alias" ~/.bash_aliases | wc -l) aliases disponibles"
```

---

## A.27 Paquetes `apt` Organizados por Categoría

Lista consolidada de todos los paquetes `apt` instalados a lo largo del libro, organizados para facilitar la instalación selectiva:

```bash
# ── Sistema base y herramientas esenciales (Caps 1–3) ─────────────────
sudo apt install -y \
  curl wget git vim nano htop net-tools tree jq \
  build-essential cmake pkg-config \
  software-properties-common apt-transport-https \
  ca-certificates gnupg lsb-release

# ── Python y desarrollo (Cap 5, 17) ───────────────────────────────────
sudo apt install -y \
  python3-pip python3-venv python3-dev python3-setuptools \
  python3-wheel ipython3

# ── Almacenamiento y NVMe (Cap 4) ─────────────────────────────────────
sudo apt install -y \
  nvme-cli smartmontools hdparm parted gdisk

# ── Red y descargas (Cap 6) ───────────────────────────────────────────
sudo apt install -y \
  aria2 nmap iftop nethogs iproute2 \
  dnsutils traceroute mtr

# ── Acceso remoto (Cap 7) ─────────────────────────────────────────────
sudo apt install -y \
  openssh-server xrdp

# ── Audio y multimedia (Caps 17, 29) ─────────────────────────────────
sudo apt install -y \
  ffmpeg libsndfile1 portaudio19-dev \
  alsa-utils libespeak-ng-dev espeak-ng \
  sox libsox-fmt-all

# ── Computer Vision (Cap 28) ──────────────────────────────────────────
sudo apt install -y \
  tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
  libtesseract-dev libleptonica-dev \
  libopencv-dev python3-opencv

# ── Web e infraestructura (Caps 30, 31) ──────────────────────────────
sudo apt install -y \
  nginx \
  libnss3-tools          # mkcert (SSL local)

# Certbot (solo si se usa SSL público sin Cloudflare Tunnel):
# sudo apt install -y certbot python3-certbot-nginx

# ── Mantenimiento del sistema (Cap 26) ────────────────────────────────
sudo apt install -y \
  logrotate cron \
  sysstat iostat \
  lsof psmisc procps

# ── Herramientas de shell (Cap 5) ─────────────────────────────────────
sudo apt install -y \
  tmux screen \
  bat fd-find ripgrep fzf \
  zsh  # opcional (zsh como shell alternativo)

# ── Verificar total de paquetes instalados ────────────────────────────
dpkg --get-selections | wc -l
```

**Resumen por capítulo:**

| Categoría | Paquetes clave | Cap |
|---|---|---|
| Sistema base | curl, wget, git, build-essential, cmake | 1–3 |
| Python | python3-pip, python3-venv, python3-dev | 5, 17 |
| Almacenamiento | nvme-cli, smartmontools, hdparm | 4 |
| Red | aria2, nmap, iftop, nethogs | 6 |
| Remote | openssh-server, xrdp | 7 |
| Audio/Multimedia | ffmpeg, libsndfile1, portaudio19-dev, alsa-utils | 17, 29 |
| Computer Vision | tesseract-ocr, libopencv-dev | 28 |
| Infraestructura | nginx, libnss3-tools | 30, 31 |
| Mantenimiento | logrotate, cron, sysstat | 26 |
| Shell tools | tmux, bat, fzf, ripgrep | 5 |

---

## A.28 Scripts de Verificación por Grupo de Capítulos

Ejecute estos scripts para verificar que los grupos de capítulos están correctamente configurados:

### Verificación — Capítulos 1–8 (Base del Sistema)

```bash
#!/bin/bash
# verify-base.sh — Verifica configuración base (Caps 1–8)

echo "╔══════════════════════════════════════════════════════╗"
echo "║     VERIFICACIÓN — CAPS 1-8 BASE DEL SISTEMA        ║"
echo "╚══════════════════════════════════════════════════════╝"

# Sistema
echo "── Sistema ──"
lsb_release -d | awk '{print "  Ubuntu:", $2, $3}'
uname -r | xargs -I{} echo "  Kernel: {}"
nvcc --version 2>/dev/null | grep release | awk '{print "  CUDA:", $6}' | tr -d ',' \
  || echo "  [WARN] CUDA no en PATH — source ~/.bashrc"

# RAM y almacenamiento
echo ""
echo "── Recursos ──"
free -h | awk '/^Mem:/{printf "  RAM total: %s (libre: %s)\n", $2, $7}'
df -h / | awk 'NR==2{printf "  Disco /: %s usado de %s (%s)\n", $3, $2, $5}'
df -h /data 2>/dev/null | awk 'NR==2{printf "  NVMe /data: %s usado de %s\n", $3, $2}'

# Swap/ZRAM
echo ""
echo "── Swap / ZRAM ──"
swapon --show 2>/dev/null | tail -n +2 | while read l; do echo "  [OK] $l"; done
[ "$(swapon --show 2>/dev/null | wc -l)" -eq 0 ] && echo "  [WARN] Sin swap configurado (ver Cap 4)"

# Docker
echo ""
echo "── Docker ──"
if command -v docker &>/dev/null; then
  docker --version | awk '{print "  Docker:", $3}' | tr -d ','
  docker info 2>/dev/null | grep "Runtimes" | grep -q nvidia \
    && echo "  [OK] Runtime nvidia disponible" \
    || echo "  [WARN] Runtime nvidia no configurado (ver Cap 8)"
else
  echo "  [ERROR] Docker no instalado"
fi

# SSH
echo ""
echo "── SSH ──"
systemctl is-active ssh > /dev/null 2>&1 \
  && echo "  [OK] SSH activo (puerto 22)" \
  || echo "  [WARN] SSH no activo"

echo ""
echo "════════════════════════════════════════════════════════"
```

### Verificación — Capítulos 12–13 (Motores de Inferencia)

```bash
#!/bin/bash
# verify-inference.sh — Verifica motores de inferencia (Caps 12–13)

echo "╔══════════════════════════════════════════════════════╗"
echo "║   VERIFICACIÓN — CAPS 12-13 MOTORES DE INFERENCIA   ║"
echo "╚══════════════════════════════════════════════════════╝"

# Ollama
echo "── Ollama ──"
if command -v ollama &>/dev/null; then
  ollama_ver=$(ollama --version 2>/dev/null | awk '{print $2}')
  echo "  [OK] Ollama $ollama_ver instalado"
  ollama list 2>/dev/null | tail -n +2 | while read m _; do echo "    Modelo: $m"; done
  curl -sf http://localhost:11434/api/version > /dev/null \
    && echo "  [OK] API activa en :11434" \
    || echo "  [INFO] Ollama offline (sudo systemctl start ollama)"
else
  echo "  [WARN] Ollama no instalado"
fi

# vLLM
echo ""
echo "── vLLM ──"
curl -sf http://localhost:8000/v1/models > /dev/null \
  && echo "  [OK] vLLM activo en :8000" \
  || echo "  [INFO] vLLM offline (start-qwen35)"

# llama.cpp
echo ""
echo "── llama.cpp ──"
curl -sf http://localhost:8080/v1/models > /dev/null \
  && echo "  [OK] llama.cpp activo en :8080" \
  || echo "  [INFO] llama.cpp offline (start-nemotron)"

# OpenClaw
echo ""
echo "── OpenClaw / NemoClaw ──"
curl -sf http://localhost:18789/health > /dev/null \
  && echo "  [OK] OpenClaw activo en :18789" \
  || echo "  [INFO] OpenClaw offline (openclaw-start)"

# HF Token
echo ""
echo "── HuggingFace ──"
[ -n "$HF_TOKEN" ] \
  && echo "  [OK] HF_TOKEN configurado (${HF_TOKEN:0:10}...)" \
  || echo "  [WARN] HF_TOKEN vacío — necesario para modelos gated (Gemma, GPT-OSS)"

echo ""
echo "════════════════════════════════════════════════════════"
```

### Verificación — Capítulos 17–25 (Proyectos de IA)

```bash
#!/bin/bash
# verify-projects.sh — Verifica proyectos de IA (Caps 17–25)

echo "╔══════════════════════════════════════════════════════╗"
echo "║      VERIFICACIÓN — CAPS 17-25 PROYECTOS DE IA      ║"
echo "╚══════════════════════════════════════════════════════╝"

# Python venvs
echo "── Python venvs ──"
[ -d ~/venvs/dev ] && echo "  [OK] venv dev" || echo "  [WARN] venv dev faltante (python3 -m venv ~/venvs/dev)"
[ -d ~/venvs/llm ] && echo "  [OK] venv llm" || echo "  [WARN] venv llm faltante"

# Servicios activos
echo ""
echo "── Servicios activos ──"
SERVICIOS=(
  "8000:faster-whisper/vLLM"
  "8880:kokoro-tts"
  "11434:Ollama"
  "9000:RAG API"
  "8888:JupyterLab"
  "5678:N8N"
  "3000:Open WebUI"
  "18789:OpenClaw"
)
for s in "${SERVICIOS[@]}"; do
  puerto="${s%%:*}"
  nombre="${s#*:}"
  curl -sf "http://localhost:$puerto" --max-time 1 > /dev/null 2>&1 \
    && echo "  [OK] :$puerto $nombre" \
    || echo "  [  ] :$puerto $nombre — offline"
done

# Directorios de proyectos
echo ""
echo "── Proyectos ──"
PROYECTOS=(pdf2podcast transcription-bot tourism-agency sales-funnel
           linkedin-content voice-assistant rag-empresarial daily-prayers)
for p in "${PROYECTOS[@]}"; do
  [ -d ~/projects/$p ] \
    && echo "  [OK] ~/projects/$p" \
    || echo "  [  ] ~/projects/$p — no creado aún"
done

echo ""
echo "════════════════════════════════════════════════════════"
```

**Instalar como aliases:**

```bash
chmod +x ~/scripts/verify-base.sh ~/scripts/verify-inference.sh ~/scripts/verify-projects.sh

echo "alias verify-base='bash ~/scripts/verify-base.sh'" >> ~/.bash_aliases
echo "alias verify-inference='bash ~/scripts/verify-inference.sh'" >> ~/.bash_aliases
echo "alias verify-projects='bash ~/scripts/verify-projects.sh'" >> ~/.bash_aliases
source ~/.bash_aliases
```

---

## A.29 Scripts de Mantenimiento del Sistema (Capítulo 26)

Estos scripts son el núcleo del sistema de mantenimiento. Créelos con los comandos de instalación de cada sección del Capítulo 26, o use los bloques siguientes para instalarlos directamente.

### check-ready.sh — Verificación Pre-Pipeline

```bash
cat > ~/scripts/maintenance/check-ready.sh << 'SCRIPT_EOF'
#!/bin/bash
# check-ready.sh — Verifica que el Jetson está listo para un pipeline de IA
# Uso: check-ready.sh <min-RAM-GB> "nombre-pipeline"
# Retorna 0 si listo, 1 si no cumple requisitos

MIN_RAM="${1:-20}"
PIPELINE="${2:-pipeline}"

check_ram() {
    LIBRE=$(free -g | awk '/^Mem:/{print $7}')
    [ "$LIBRE" -ge "$MIN_RAM" ] && return 0 || { echo "[ERROR] RAM: $LIBRE GB libre, necesita $MIN_RAM GB"; return 1; }
}

check_temp() {
    TEMP=$(cat /sys/devices/virtual/thermal/thermal_zone0/temp 2>/dev/null || echo "0")
    TEMP_C=$((TEMP / 1000))
    [ "$TEMP_C" -lt 75 ] && return 0 || { echo "[WARN] Temperatura alta: ${TEMP_C}°C (óptimo <75°C)"; return 0; }
}

check_disk() {
    USO=$(df / | awk 'NR==2{print $5}' | tr -d '%')
    [ "$USO" -lt 90 ] && return 0 || { echo "[ERROR] Disco casi lleno: ${USO}% usado"; return 1; }
}

ERRORES=0
echo "── Pre-check: $PIPELINE ──"
check_ram || ((ERRORES++))
check_temp
check_disk || ((ERRORES++))

if [ "$ERRORES" -eq 0 ]; then
    echo "[OK] Sistema listo para $PIPELINE"
    exit 0
else
    echo "[WARN] $ERRORES problema(s) detectado(s). Ejecute: jetson-clean"
    exit 1
fi
SCRIPT_EOF
chmod +x ~/scripts/maintenance/check-ready.sh
echo "[OK] check-ready.sh instalado"
```

### clean-ai-containers.sh — Limpieza de Contenedores

```bash
cat > ~/scripts/maintenance/clean-ai-containers.sh << 'SCRIPT_EOF'
#!/bin/bash
# clean-ai-containers.sh — Detiene y limpia contenedores de proyectos IA
# Uso: clean-ai-containers.sh [--all | nombre-proyecto]

PROYECTO="${1:-}"
PATRONES="vllm|llama|qwen|gemma|kokoro|whisper|nemotron|comfyui|sd-webui|openclaw|open-webui"
[ -n "$PROYECTO" ] && PATRONES="$PROYECTO"

echo "── Limpiando contenedores ──"
CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E "$PATRONES" || true)

if [ -z "$CONTAINERS" ]; then
    echo "  Sin contenedores de IA activos"
else
    echo "$CONTAINERS" | while read c; do
        docker stop "$c" > /dev/null 2>&1 && docker rm "$c" > /dev/null 2>&1
        echo "  [OK] Detenido: $c"
    done
fi

# Liberar memoria
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
RAM_LIBRE=$(free -h | awk '/^Mem:/{print $7}')
echo "  RAM libre: $RAM_LIBRE"
SCRIPT_EOF
chmod +x ~/scripts/maintenance/clean-ai-containers.sh
echo "[OK] clean-ai-containers.sh instalado"
```

### switch-project.sh — Cambio entre Proyectos

```bash
cat > ~/scripts/maintenance/switch-project.sh << 'SCRIPT_EOF'
#!/bin/bash
# switch-project.sh — Cambia entre proyectos de IA liberando recursos
# Uso: switch-project.sh <nombre-proyecto>

NUEVO_PROYECTO="${1:-}"
if [ -z "$NUEVO_PROYECTO" ]; then
    echo "Uso: switch-project.sh <nombre>"
    echo "Disponibles: pdf2podcast | transcription | tourism | sales | linkedin | voice | rag | agency"
    exit 1
fi

echo "── Cambiando al proyecto: $NUEVO_PROYECTO ──"
echo "  1. Liberando recursos actuales..."
~/scripts/maintenance/clean-ai-containers.sh
sleep 2

echo "  2. Iniciando $NUEVO_PROYECTO..."
case "$NUEVO_PROYECTO" in
  pdf2podcast)      echo "  Inicie: start-kokoro && ollama-start" ;;
  transcription)    echo "  Inicie: start-whisper && ollama-start" ;;
  tourism|agency)   echo "  Inicie: openclaw-start && ollama-start" ;;
  voice)            echo "  Inicie: start-whisper && start-kokoro && ollama-start" ;;
  rag)              echo "  Inicie: ollama-start && rag-start" ;;
  *)                echo "  Proyecto '$NUEVO_PROYECTO' — inicie los servicios manualmente" ;;
esac

echo "[OK] Recursos liberados — listo para $NUEVO_PROYECTO"
SCRIPT_EOF
chmod +x ~/scripts/maintenance/switch-project.sh
echo "[OK] switch-project.sh instalado"
```

### hf-cache-clean.sh — Limpieza de Caché HuggingFace

```bash
cat > ~/scripts/maintenance/hf-cache-clean.sh << 'SCRIPT_EOF'
#!/bin/bash
# hf-cache-clean.sh — Limpia caché HuggingFace de modelos no usados
# Uso: hf-cache-clean.sh [--list | --all | nombre-modelo]

CACHE_DIR="$HOME/.cache/huggingface/hub"

if [ ! -d "$CACHE_DIR" ]; then
    echo "[INFO] Caché vacío: $CACHE_DIR"
    exit 0
fi

case "${1:-}" in
  --list)
    echo "── Modelos en caché HuggingFace ──"
    du -sh "$CACHE_DIR"/models--*/ 2>/dev/null | sort -h | awk '{printf "  %s  %s\n", $1, $2}'
    TOTAL=$(du -sh "$CACHE_DIR" 2>/dev/null | awk '{print $1}')
    echo "  Total: $TOTAL"
    ;;
  --all)
    echo "[WARN] Esto eliminará TODO el caché HuggingFace ($CACHE_DIR)"
    read -p "¿Confirmar? (sí/no): " CONF
    [ "$CONF" = "sí" ] && rm -rf "$CACHE_DIR" && echo "[OK] Caché eliminado" || echo "Cancelado"
    ;;
  "")
    echo "Uso: hf-cache-clean.sh [--list | --all | nombre-modelo-parcial]"
    echo "  --list : listar modelos en caché con tamaño"
    echo "  --all  : eliminar TODO el caché"
    echo "  texto  : eliminar modelos cuyo nombre contenga 'texto'"
    ;;
  *)
    PATRON="$1"
    ENCONTRADOS=$(ls "$CACHE_DIR" 2>/dev/null | grep -i "$PATRON" || true)
    if [ -z "$ENCONTRADOS" ]; then
        echo "[INFO] Sin modelos con '$PATRON' en caché"
    else
        echo "── Modelos encontrados ──"
        echo "$ENCONTRADOS" | while read m; do
            SIZE=$(du -sh "$CACHE_DIR/$m" | awk '{print $1}')
            echo "  $m ($SIZE)"
        done
        read -p "¿Eliminar estos modelos? (sí/no): " CONF
        if [ "$CONF" = "sí" ]; then
            echo "$ENCONTRADOS" | while read m; do
                rm -rf "$CACHE_DIR/$m" && echo "  [OK] Eliminado: $m"
            done
        fi
    fi
    ;;
esac
SCRIPT_EOF
chmod +x ~/scripts/maintenance/hf-cache-clean.sh
echo "[OK] hf-cache-clean.sh instalado"
```

### health-check.sh — Verificación de Salud Semanal

```bash
cat > ~/scripts/maintenance/health-check.sh << 'SCRIPT_EOF'
#!/bin/bash
# health-check.sh — Diagnóstico semanal completo del Jetson
# Recomienda programar semanalmente: 0 8 * * 1 ~/scripts/maintenance/health-check.sh

LOG_FILE="$HOME/logs/health-$(date +%Y%m%d).log"
mkdir -p "$HOME/logs"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "══════════════════════════════════════════════════"
echo "  HEALTH CHECK — $(date '+%Y-%m-%d %H:%M:%S')"
echo "══════════════════════════════════════════════════"

# Temperatura
echo "── Temperatura ──"
for z in /sys/devices/virtual/thermal/thermal_zone*/temp; do
    T=$(cat "$z" 2>/dev/null)
    [ -n "$T" ] && printf "  %s: %.1f°C\n" "$(basename $(dirname $z))" "$((T / 1000))"
done

# RAM
echo ""
echo "── Memoria ──"
free -h | awk '/^Mem:/{printf "  RAM: %s total, %s disponible\n", $2, $7}'
swapon --show 2>/dev/null | tail -n +2 | awk '{printf "  Swap %s: %s\n", $2, $3}'

# Disco
echo ""
echo "── Almacenamiento ──"
df -h / /data 2>/dev/null | tail -n +2 | awk '{printf "  %s: %s usados (%s)\n", $6, $3, $5}'
CACHE_SIZE=$(du -sh ~/.cache/huggingface/hub 2>/dev/null | awk '{print $1}')
echo "  HF cache: ${CACHE_SIZE:-vacío}"

# Servicios en arranque (no deberían correr)
echo ""
echo "── Servicios ──"
systemctl is-active docker > /dev/null 2>&1 \
  && echo "  [WARN] Docker corriendo en boot — use 'docker-off' y deshabilítelo" \
  || echo "  [OK] Docker deshabilitado en boot"
systemctl is-enabled ollama > /dev/null 2>&1 \
  && echo "  [WARN] Ollama habilitado en arranque — puede consumir VRAM al iniciar" \
  || echo "  [OK] Ollama no habilitado en arranque"

echo ""
echo "  Log guardado en: $LOG_FILE"
echo "══════════════════════════════════════════════════"
SCRIPT_EOF
chmod +x ~/scripts/maintenance/health-check.sh
echo "[OK] health-check.sh instalado"
```

### system-status.sh — Estado Rápido del Sistema

```bash
cat > ~/scripts/maintenance/system-status.sh << 'SCRIPT_EOF'
#!/bin/bash
# system-status.sh — Estado general del Jetson en 5 segundos

echo "╔══════════════════════════════════════════════════════╗"
echo "║                ESTADO DEL SISTEMA                    ║"
echo "╚══════════════════════════════════════════════════════╝"

# Modo energético
MODO=$(sudo nvpmodel -q 2>/dev/null | grep "NV Power Mode" | awk '{print $NF}')
echo "  Modo energético: ${MODO:-desconocido}"

# RAM
free -h | awk '/^Mem:/{printf "  RAM: %s total / %s libre / %s usados\n", $2, $7, $3}'

# Temperatura
T=$(cat /sys/devices/virtual/thermal/thermal_zone0/temp 2>/dev/null || echo "0")
echo "  Temperatura: $((T / 1000))°C"

# Docker
CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l)
echo "  Contenedores activos: $CONTAINERS"
[ "$CONTAINERS" -gt 0 ] && docker ps --format "    {{.Names}} — {{.Status}}" 2>/dev/null

# Ollama
if systemctl is-active ollama > /dev/null 2>&1; then
    MODELOS=$(ollama ps 2>/dev/null | tail -n +2 | wc -l)
    echo "  Ollama: activo ($MODELOS modelos en VRAM)"
else
    echo "  Ollama: offline"
fi

# Endpoints
echo "  Endpoints:"
for p in 8000 8080 11434 18789 3000 8880 9000 5678; do
    curl -sf "http://localhost:$p" --max-time 0.5 > /dev/null 2>&1 && echo "    :$p activo"
done

echo "╚══════════════════════════════════════════════════════╝"
SCRIPT_EOF
chmod +x ~/scripts/maintenance/system-status.sh
echo "[OK] system-status.sh instalado"
```

**Instalar todos los scripts de mantenimiento en un paso:**

```bash
# Crear directorio y ejecutar cada bloque de instalación anterior
mkdir -p ~/scripts/maintenance
# (ejecutar cada bloque cat > ... SCRIPT_EOF de arriba)

# Agregar aliases (ya en A.26, verificar que estén activos)
grep -q "check-ready" ~/.bash_aliases \
  || echo "alias check-ready='~/scripts/maintenance/check-ready.sh'" >> ~/.bash_aliases
source ~/.bash_aliases

# Programar health-check semanal (lunes 8 AM)
(crontab -l 2>/dev/null; echo "0 8 * * 1 $HOME/scripts/maintenance/health-check.sh") | crontab -
echo "[OK] health-check programado: lunes 8 AM"
```

---

*Fin del Apéndice — Referencia Rápida.*
