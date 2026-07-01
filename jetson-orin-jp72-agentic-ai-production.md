# Agentic AI Production Stack on NVIDIA Jetson AGX Orin 64GB — JetPack 7.2
## llama.cpp · Ollama · vLLM · OpenClaw · NemoClaw · jetson-containers

**Tags:** `jetson` `jetpack-7.2` `agentic-ai` `vllm` `ollama` `llama-cpp` `openclaw` `nemoclaw` `jetson-containers` `edge-ai` `ubuntu-24.04` `cuda-13` `sbsa`

> **This is Part 2 of 2.** Part 1 covers headless setup with SSH and NoMachine. This part covers the full AI production stack: inference engines, agentic frameworks, and NVIDIA resources.

---

## The SBSA Shift — Why JetPack 7.2 Changes Everything

JetPack 7.2 / L4T r39.2 aligns AGX Orin with the standard Arm server software ecosystem used by platforms such as Jetson Thor and DGX Spark. AGX Orin can now run mainstream Arm64 `arm64-SBSA` containers and binaries, rather than requiring separate Jetson-specific builds.

In practical terms:

```
JetPack 6.x                    JetPack 7.2
─────────────────               ─────────────────────────────────
Jetson-specific containers      arm64-SBSA + Jetson containers
dustynv/ollama:r36.x            Official vLLM upstream containers ✅
NVIDIA-AI-IOT custom builds     Standard PyPI / pip packages ✅
Tegra-only paths                Unified CUDA 13 across Arm targets ✅
```

This guide uses **both paths**: NVIDIA's curated jetson-containers where they offer the best performance, and upstream SBSA containers where they now work natively.

---

## Hardware & Software Reference

| Component | Value |
|-----------|-------|
| Hardware | Jetson AGX Orin Developer Kit 64GB |
| JetPack | 7.2-b187 |
| L4T | r39.2 (Jetson Linux 39.2) |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | 6.8.12-tegra |
| CUDA | 13.2.1 |
| GPU | Ampere (nvgpu) — sm_87 |
| RAM | 64GB LPDDR5 unified (GPU+CPU share same pool) |
| Storage | 931GB NVMe (primary) |
| Python | 3.12.3 |

---

## Prerequisites

- Part 1 complete: headless, SSH, NoMachine, XFCE4 working
- Docker installed with `default-runtime: nvidia`
- UFW active with ports open

Verify before starting:

```bash
# Docker with NVIDIA runtime
docker info | grep "Default Runtime"
# → Default Runtime: nvidia

# CUDA accessible
nvcc --version 2>/dev/null || echo "Run: sudo apt install nvidia-cuda-dev -y && \
  echo 'export PATH=/usr/local/cuda/bin:\$PATH' >> ~/.bashrc && source ~/.bashrc"

# Available memory
free -h
# → Mem: 61Gi
```

---

## Step 1 — Power Mode Management

The Jetson AGX Orin 64GB has five power modes. Choosing the right one **directly impacts
inference speed, electricity cost, and system temperature.** Running at MAXN 24/7 is
unnecessary for most workloads and significantly increases operating cost.

### 1.1 Available Power Modes

```bash
# See all available modes on your board
sudo nvpmodel -p --verbose | grep -E "MODE|POWER"
```

| Mode | Command | TDP | Use Case |
|------|---------|-----|---------|
| MODE_10W | `sudo nvpmodel -m 1` | ~10W | Monitoring only, no inference |
| **MODE_15W** | **`sudo nvpmodel -m 2`** | **~15W** | **Default — idle, small models (1B–4B)** |
| MODE_30W | `sudo nvpmodel -m 3` | ~30W | Medium models (7B–14B) |
| MODE_50W | `sudo nvpmodel -m 4` | ~50W | Large models (27B+), multi-user |
| MAXN | `sudo nvpmodel -m 0` | ~60W | 70B models, benchmarking, peak bursts |

### 1.2 Electricity Cost Analysis

> Based on typical electricity rates in Colombia (~$0.20 USD/kWh), running 24/7.

| Mode | Monthly kWh | Monthly Cost USD | vs MAXN Savings |
|------|------------|-----------------|----------------|
| MAXN (60W) | 43.2 kWh | ~$8.64 | — |
| MODE_50W | 36.0 kWh | ~$7.20 | ~$1.44 |
| MODE_30W | 21.6 kWh | ~$4.32 | ~$4.32 |
| **MODE_15W** | **10.8 kWh** | **~$2.16** | **~$6.48** |

> Switching from MAXN to MODE_15W as default saves **~$77 USD/year** with no quality loss
> for small and medium models.

### 1.3 Model-to-Power-Mode Recommendation

| Model Size | Engine | Recommended Mode | Notes |
|-----------|--------|-----------------|-------|
| Embeddings (nomic-embed-text) | Ollama | **MODE_15W** | Trivial compute |
| 1B – 4B (gemma3:1b, gemma4) | Ollama | **MODE_15W** | Fully sufficient |
| 7B – 8B (Qwen3-8B, gemma4:8b) | Ollama / vLLM | **MODE_30W** | Good efficiency |
| 14B (Qwen3-14B) | vLLM / llama.cpp | **MODE_30W** | Balanced |
| 27B – 32B (Qwen3-32B) | vLLM / llama.cpp | **MODE_50W** | Needs bandwidth |
| 70B+ (llama3-70B Q4) | llama.cpp | **MAXN** | Full memory bandwidth required |
| Multi-user production burst | vLLM | **MAXN** | Maximize throughput |

### 1.4 Set Default to MODE_15W

```bash
# Set MODE_15W as the boot default
sudo nvpmodel -m 2

# Verify
sudo nvpmodel -q
# → NV Power Mode: MODE_15W

# Persist across reboots
sudo tee /etc/systemd/system/jetson-power-default.service << 'EOF'
[Unit]
Description=Jetson AGX Orin Default Power Mode 15W
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nvpmodel -m 2

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jetson-power-default
sudo systemctl start jetson-power-default
```

### 1.5 Power Mode Aliases — Quick Switching

```bash
cat >> ~/.bashrc << 'ALIASES'

# ── Jetson Power Mode ──────────────────────────────────────────
alias pwr-status='sudo nvpmodel -q'
alias pwr-10w='sudo nvpmodel -m 1 && echo "MODE_10W active"'
alias pwr-15w='sudo nvpmodel -m 2 && echo "MODE_15W active (default)"'
alias pwr-30w='sudo nvpmodel -m 3 && echo "MODE_30W active"'
alias pwr-50w='sudo nvpmodel -m 4 && echo "MODE_50W active"'
alias pwr-max='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MAXN + clocks locked"'
alias pwr-save='sudo nvpmodel -m 2 && echo "Back to MODE_15W"'
ALIASES

source ~/.bashrc
```

Usage examples:
```bash
pwr-status              # Check current mode
pwr-30w                 # Before loading Qwen3-8B
pwr-50w                 # Before loading a 27B model
pwr-max                 # Before a 70B llama.cpp session
pwr-save                # Return to 15W when done
```

### 1.6 jetson_clocks — Only When Needed

`sudo jetson_clocks` locks all clocks to maximum within the current power envelope.
It is **not needed for routine inference** — only for benchmarking or sustained 70B sessions.

```bash
# Pattern for heavy workloads:
pwr-max                  # Switch to MAXN + lock clocks

# ... run heavy inference ...

pwr-save                 # Return to 15W when done
```

---


## Step 2 — CUDA PATH and Dev Tools

```bash
# Install CUDA development tools (nvcc not in PATH by default in JP 7.2)
sudo apt install nvidia-cuda-dev -y

# Add to PATH
echo 'export CUDA_HOME=/usr/local/cuda' >> ~/.bashrc
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
nvcc --version
# → Cuda compilation tools, release 13.2, ...

# Additional build tools
sudo apt install -y \
  build-essential cmake ninja-build \
  libopenblas-dev libcurl4-openssl-dev \
  libhdf5-dev
```

---

## Step 3 — jetson-containers Framework

jetson-containers provides pre-built Docker images with per-architecture indexes (jp6, jp7, sbsa, amd64) and automated container selection based on JetPack version. The `autotag` tool selects the correct container image for your L4T version.

```bash
# Clone the repository
cd ~
git clone https://github.com/dusty-nv/jetson-containers
cd jetson-containers

# Install the framework tools
bash install.sh

# Verify autotag works (shows which container would be selected)
./autotag ollama
# → dustynv/ollama:r39.2-cu132-24.04 (or similar for JP 7.2)

# Create persistent data directories
mkdir -p ~/jetson-ai-data/models/ollama
mkdir -p ~/jetson-ai-data/models/hf
mkdir -p ~/jetson-ai-data/models/gguf
mkdir -p ~/jetson-ai-data/logs

# Add the tools to PATH
echo 'export PATH=$HOME/jetson-containers:$PATH' >> ~/.bashrc
source ~/.bashrc
```

---

## Step 4 — Inference Engine 1: Ollama

Ollama uses llama.cpp internally and provides the simplest OpenAI-compatible API for LLMs. Best for text chat, RAG, and single-request pipelines. On AGX Orin 64GB, it comfortably runs models up to 70B using quantized GGUF format.

> **⚠️ JP 7.2 Container Note:** The NVIDIA-AI-IOT Ollama container `r38.2.arm64-sbsa-cu130-24.04` targets Jetson Thor (L4T r38.x) and enters a restart loop on JP 7.2 (L4T r39.2). Use the **native installer** instead — it detects the GPU correctly and is the method recommended in the JP 7.2 Getting Started guide.

### 4.1 Native Installation (Verified Working on JP 7.2)

```bash
# Official installer — detects arm64 and GPU automatically
curl -fsSL https://ollama.com/install.sh | sh
```

You will see:
```
WARNING: Unsupported JetPack version detected. GPU may not be supported
>>> NVIDIA JetPack ready.
>>> The Ollama API is now available at 127.0.0.1:11434.
```

The warning is cosmetic — Ollama 0.x does not yet recognize JP 7.2's version string, but GPU detection still succeeds via the CUDA libraries. The final line **"NVIDIA JetPack ready"** confirms GPU access.

### 4.2 Configure Network Access (Critical)

By default, Ollama binds to `127.0.0.1` (localhost only). This must be changed to `0.0.0.0` for remote access from Windows or other containers.

```bash
# Create systemd override
sudo mkdir -p /etc/systemd/system/ollama.service.d/

sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF
# OLLAMA_NUM_PARALLEL=2  → handle 2 simultaneous requests (good for agentic pipelines)
# OLLAMA_MAX_LOADED_MODELS=1 → prevents multiple models in VRAM (important when
#                               running vLLM alongside Ollama)

sudo systemctl daemon-reload
sudo systemctl restart ollama
sleep 3

# Verify binding — must show *:11434, not 127.0.0.1:11434
sudo ss -tlnp | grep 11434
# LISTEN 0  4096  *:11434  *:*  users:(("ollama",...))

# Verify API responds
curl http://localhost:11434/api/tags
# → {"models":[]}
```

### 4.3 Recommended Power Mode for Ollama

```bash
# For models 1B-4B (gemma3:1b, gemma4:4b, nomic-embed-text)
pwr-15w   # MODE_15W is sufficient — saves energy

# For models 7B-8B (qwen3:8b, gemma4:latest)
pwr-30w   # MODE_30W recommended for responsive chat

# Check current mode before pulling/running
pwr-status
```

### 4.4 Pull Models

```bash
# Models recommended for AGX Orin 64GB agentic pipelines

# Tool-calling models (required for OpenClaw)
ollama pull qwen3:8b              # 5GB  — fast, excellent tool calling
ollama pull qwen3:14b             # 9GB  — higher quality tool calling

# General purpose
ollama pull gemma4:latest         # 9.6GB — Google's multimodal model
ollama pull gemma3:4b             # 2.5GB — fast general use

# Embedding model for RAG
ollama pull nomic-embed-text      # 274MB — fast local embeddings

# Large models (use full 64GB unified memory)
ollama pull qwen3:32b             # 20GB  — premium quality
ollama pull gemma4:26b            # 17GB  — Gemma 4 MoE

# Monitor download progress
ollama list
```

### 4.4 Verify GPU is Active

```bash
# Run with --verbose to see GPU metrics
ollama run qwen3:8b --verbose "Explain edge AI in one sentence" 2>&1 | \
  grep -E "eval rate|layers|cuda"
```

Expected output confirming GPU:
```
eval rate:     25+ tokens/s   ← GPU confirmed (CPU-only would be 2-5 tok/s)
```

```bash
# Monitor GPU utilization during inference
# Terminal 1 — start inference
ollama run qwen3:8b "Write a 200 word technical explanation of transformers"

# Terminal 2 — watch GPU
sudo tegrastats | grep -o "GR3D_FREQ [0-9]*%@\[[0-9,]*\]"
# Note: on JP 7.2 the format is GR3D_FREQ 0%@[0,0]
# For short prompts with fast models, GPU may complete work between 1-second samples
# Use longer prompts or watch nvidia-smi for reliable GPU load readings

watch -n0.5 nvidia-smi
```

### 4.5 API Test

```bash
# From Jetson — direct API call
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "Hello from JP 7.2!"}],
    "max_tokens": 100
  }' | python3 -m json.tool

# List available models
curl http://localhost:11434/api/tags | \
  python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

From **Windows PowerShell**:
```powershell
# Verify remote access
Invoke-RestMethod -Uri "http://192.168.1.100:11434/api/tags" |
    Select-Object -ExpandProperty models |
    ForEach-Object { [PSCustomObject]@{
        Name = $_.name
        "Size(GB)" = [math]::Round($_.size / 1GB, 1)
    }} | Format-Table -AutoSize
```

### 4.6 Open WebUI for Ollama

```bash
# Browser-based chat interface connected to Ollama
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  --network host \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui-data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  ghcr.io/open-webui/open-webui:main

sudo ufw allow 8080/tcp comment "Open WebUI"

# Wait ~90 seconds for first start, then:
# Access from Windows browser: http://192.168.1.100:8080
# Create a local admin account on first visit
```

### 4.7 Verify Complete Ollama Setup

```bash
# Full status check
echo "=== Ollama Status ==="

echo -n "Service:      "
systemctl is-active ollama

echo -n "Network bind: "
sudo ss -tlnp | grep 11434 | grep -o "*:11434" || echo "Check binding"

echo -n "GPU:          "
ollama run gemma3:1b --verbose "test" 2>&1 | grep "eval rate" | \
  awk '{print $3, $4, "(>20 tok/s = GPU active)"}'

echo -n "Models:       "
ollama list | tail -n +2 | wc -l
echo "models installed"

ollama list
```

---

## Step 5 — Inference Engine 2: llama.cpp (GGUF / Quantized)

llama.cpp on Jetson benefits from the **unified memory architecture**: GPU offload (`-ngl 999`) uses the same physical LPDDR5 RAM as CPU, but executes layers through CUDA cores — achieving 3–5x speedup over CPU-only inference.

> **⚠️ JP 7.2 Container Incompatibility:** The jetson-containers `dustynv/llama_cpp:r36.4` image was built against CUDA 12.8 and fails on JP 7.2 with `libcudart.so.12: cannot open shared object file` (JP 7.2 ships CUDA 13). **Build from source** — it uses the host CUDA 13 toolchain that Ollama already confirmed working.

> **⚠️ Port conflict:** Open WebUI occupies port 8080. Use port **9090** for llama.cpp.

### 5.1 Prerequisites

```bash
# Create venv if it does not exist yet
python3 -m venv ~/venvs/llm
source ~/venvs/llm/bin/activate
pip install --upgrade pip huggingface-hub

# HuggingFace login (browser flow)
hf auth login
# Follow the URL — authorize in browser, return to terminal

# Save token permanently in .bashrc (required for Docker -e HF_TOKEN=$HF_TOKEN)
# Without this, vLLM containers show rate-limit warnings during model download
TOKEN=$(cat ~/.cache/huggingface/token)
echo "export HF_TOKEN=\"$TOKEN\"" >> ~/.bashrc
source ~/.bashrc

# Verify
echo $HF_TOKEN | head -c 15
# → hf_xxxxxxxxxxxxx...
```

### 5.2 Download GGUF Model

```bash
source ~/venvs/llm/bin/activate
mkdir -p ~/jetson-ai-data/models/gguf

# Qwen3 8B Q4_K_M — 5GB, fast, tool calling capable (verified on JP 7.2)
hf download Qwen/Qwen3-8B-GGUF \
  --include "Qwen3-8B-Q4_K_M.gguf" \
  --local-dir ~/jetson-ai-data/models/gguf/

# Other verified repo names:
# hf download Qwen/Qwen3-14B-GGUF   --include "Qwen3-14B-Q4_K_M.gguf"  --local-dir ~/jetson-ai-data/models/gguf/
# hf download google/gemma-3-4b-it-GGUF --include "gemma-3-4b-it-Q4_K_M.gguf" --local-dir ~/jetson-ai-data/models/gguf/

# Verify download
ls -lh ~/jetson-ai-data/models/gguf/*.gguf
```

> **HuggingFace repo naming note:** `Qwen/Qwen3.6-27B-GGUF` does not exist.
> Correct names: `Qwen/Qwen3-8B-GGUF`, `Qwen/Qwen3-14B-GGUF`, etc. (no `.6` suffix in GGUF repos).

### 5.3 Build llama.cpp from Source (Required for JP 7.2 / CUDA 13)

The Docker container approach fails due to CUDA version mismatch (container=CUDA 12, host=CUDA 13).
Build natively — it uses the same CUDA 13 toolchain already working with Ollama.

```bash
sudo apt install cmake build-essential libcurl4-openssl-dev -y

cd ~
git clone --depth 1 https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Run inside tmux to survive SSH disconnections (~10-15 min build)
tmux new -s llama-build

export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH

cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES="87" \
  -DGGML_CUDA_F16=ON \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j 4
# Ctrl+A d to detach from tmux while it builds
# tmux attach -t llama-build to check progress
```

### 5.4 Launch llama.cpp Server

```bash
# Set power mode before launching (adjust per model size)
pwr-30w   # 7B-8B models → MODE_30W
# pwr-50w  # 27B models  → MODE_50W
# pwr-max  # 70B models  → MAXN

~/llama.cpp/build/bin/llama-server \
  --model ~/jetson-ai-data/models/gguf/Qwen3-8B-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 9090 \
  --n-gpu-layers 999 \
  --ctx-size 8192 \
  --parallel 2 \
  --threads $(nproc)
```

Successful startup output:
```
I device_info:
I   - CUDA0   : Orin (62817 MiB, 59531 MiB free)   ← GPU confirmed
I srv  llama_server: server is listening on http://0.0.0.0:9090
```

**Verified performance on AGX Orin 64GB / JP 7.2 (Qwen3-8B Q4_K_M, ctx 8192, parallel 2):**
```
Prompt eval:  45.13 tokens/sec
Generation:    7.61 tokens/sec
```

### 5.5 Test the API

```bash
# Health check
curl http://localhost:9090/health
# → {"status":"ok"}

# Basic chat test
curl http://localhost:9090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-8b",
    "messages": [{"role": "user", "content": "Hello from llama.cpp on JP 7.2!"}],
    "max_tokens": 100
  }' | python3 -m json.tool
```

#### Qwen3 Thinking Mode — Important

Qwen3 models enable "thinking mode" by default. The generated text appears in `reasoning_content` instead of `content` (which shows as empty). Two solutions:

**Option A — Disable thinking per request with `/no_think` (recommended):**
```bash
curl http://localhost:9090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-8b",
    "messages": [{"role": "user", "content": "Hello! /no_think"}],
    "max_tokens": 100
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
msg = r['choices'][0]['message']
print(msg.get('content') or msg.get('reasoning_content', ''))
"
```

**Option B — Disable globally via system prompt:**
```json
{"role": "system", "content": "You are a helpful assistant. /no_think"}
```

**Option C — Parse `reasoning_content` in client code:**
```python
response = r["choices"][0]["message"]
answer = response.get("content") or response.get("reasoning_content", "")
```

```bash
# Open firewall
sudo ufw allow 9090/tcp comment "llama.cpp server"
```

### 5.6 Install as Systemd Service

```bash
sudo tee /etc/systemd/system/llama-server.service << 'EOF'
[Unit]
Description=llama.cpp GGUF Inference Server — Jetson AGX Orin JP 7.2
After=network.target

[Service]
Type=simple
User=jetson
Environment="CUDA_HOME=/usr/local/cuda"
Environment="PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib/aarch64-linux-gnu/tegra"
ExecStart=/home/jetson/llama.cpp/build/bin/llama-server \
  --model /home/jetson/jetson-ai-data/models/gguf/Qwen3-8B-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 9090 \
  --n-gpu-layers 999 \
  --ctx-size 8192 \
  --parallel 2 \
  --threads 8
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable llama-server
sudo systemctl start llama-server

# Verify
sudo systemctl status llama-server
curl http://localhost:9090/health
```

### 5.7 Inference Engine Summary (Verified on AGX Orin 64GB / JP 7.2)

| Engine | Method | Port | GPU | tok/s gen | Best For |
|--------|--------|------|-----|-----------|---------|
| Ollama | Native installer | 11434 | ✅ | ~25+ | Chat, RAG, embeddings |
| llama.cpp | Build from source | 9090 | ✅ 7-45 | GGUF models, large quant |
| vLLM | Upstream Docker | 8000 | Next step | Production, tool calling |

> Generation rate difference: llama.cpp at 7.61 tok/s vs Ollama at 25 tok/s is expected —
> Qwen3-8B is larger than gemma3:1b, and `--parallel 2` reserves context for two concurrent
> requests. Single-slot peak throughput is higher.

---


## Step 6 — Inference Engine 3: vLLM (Production Serving)

vLLM 0.22.0 uses PagedAttention and continuous batching for maximum throughput. With JetPack 7.2 SBSA alignment, **the official upstream vLLM container runs natively** on AGX Orin — no custom NVIDIA-AI-IOT builds required.

> **Key JP 7.2 finding:** The official container `vllm/vllm-openai:v0.22.0-ubuntu2404` includes
> Arm64 and sm_87 support. It works on AGX Orin via the SBSA compatibility layer introduced in JP 7.2.

### 6.1 Prerequisites

```bash
# Create model cache directory
mkdir -p ~/jetson-ai-data/models/hf

# Verify Docker has nvidia runtime
docker info | grep "Default Runtime"
# → Default Runtime: nvidia
```

#### HuggingFace Token — Persistent Setup (Required)

vLLM downloads models inside the container at startup. Without a valid token, downloads are
rate-limited and you will see:
```
Warning: You are sending unauthenticated requests to the HF Hub.
Please set a HF_TOKEN to enable higher rate limits and faster downloads.
```

Fix — store the token permanently in `.bashrc` so every session and every Docker `-e` flag
picks it up automatically:

```bash
# One-time setup after hf auth login
TOKEN=$(cat ~/.cache/huggingface/token)
echo "export HF_TOKEN=\"$TOKEN\"" >> ~/.bashrc
source ~/.bashrc

# Verify the token is loaded
echo $HF_TOKEN | head -c 15
# → hf_xxxxxxxxxxxxx...

# The Docker run commands use -e HF_TOKEN=$HF_TOKEN
# which now resolves automatically from the environment
```

> If you rotate your HuggingFace token, run `hf auth login` again and re-run the
> `echo export HF_TOKEN...` line above to refresh it in `.bashrc`.

### 6.2 Launch vLLM

```bash
# Set power mode before launching vLLM
pwr-30w   # gemma-4-E4B-it (4B) → MODE_30W sufficient
# pwr-50w  # for 14B+ models
# pwr-max  # for 27B+ or multi-user production

docker run --runtime nvidia -d \
  --name vllm \
  --network host \
  --ipc host \
  --shm-size 8g \
  --restart unless-stopped \
  -e HF_TOKEN=$HF_TOKEN \
  -v ~/jetson-ai-data/models/hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
  google/gemma-4-E4B-it \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.70
```

> **Note:** Pass the model as a positional argument (no `--model` flag). The `--model` option
> works but shows a deprecation warning in 0.22.0+.

### 6.3 Monitor Startup

Startup has two distinct phases — **be patient, both take time**:

```bash
docker logs vllm --follow
```

**Phase 1 — Model download** (~5-30 min depending on connection, ~15GB for gemma-4-E4B-it):
```
Starting to load model google/gemma-4-E4B-it...
Loading safetensors checkpoint shards: 100%   ← download complete
```

**Phase 2 — CUDA graph compilation** (~3-5 min, runs once then cached):
```
Dynamo bytecode transform time: XX s
Graph capturing finished in XX secs
Application startup complete.                 ← READY
```

#### Expected warnings during startup (all cosmetic, safe to ignore)

```
UserWarning: Found GPU0 Orin which is of compute capability (CC) 8.7.
- 8.0 which supports hardware CC >=8.0,<9.0 except {8.7}
```
This warning appears because the PyTorch inside the container was compiled for CC 8.0/9.0/10.0
but explicitly excludes 8.7 (Jetson Orin's architecture). vLLM falls back to PTX JIT compilation,
which works correctly — inference runs normally. Startup takes slightly longer on first run
while PTX is compiled; subsequent restarts are faster.

```
Unknown vLLM environment variable: VLLM_BUILD_COMMIT / VLLM_BUILD_PIPELINE / VLLM_IMAGE_TAG
```
These are internal build metadata variables in the container. Harmless.

### 6.4 Verify and Test

```bash
# Check API is responding
curl http://localhost:8000/health
# → {"status":"ok"}

# List loaded models
curl http://localhost:8000/v1/models | python3 -m json.tool

# Chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [
      {"role": "user", "content": "Explain edge AI in 3 bullet points."}
    ],
    "max_tokens": 200
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(r['choices'][0]['message']['content'])
print(f\"Tokens: {r['usage']['completion_tokens']}\")
"

# JSON structured output
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [{"role": "user", "content": "List 3 AI use cases as JSON"}],
    "response_format": {"type": "json_object"},
    "max_tokens": 300
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(r['choices'][0]['message']['content'])
"
```

**Verified output on AGX Orin 64GB / JP 7.2 / vLLM 0.22.0:**
```
model:   google/gemma-4-E4B-it
tokens:  164 completion tokens
time:    ~25 seconds total
JSON:    ✅ structured output works
```

From **Windows PowerShell**:
```powershell
$body = @{
    model    = "google/gemma-4-E4B-it"
    messages = @(@{role="user"; content="Hello from Windows via vLLM on JP 7.2!"})
    max_tokens = 100
} | ConvertTo-Json -Depth 3

Invoke-RestMethod `
    -Uri "http://192.168.1.100:8000/v1/chat/completions" `
    -Method Post -ContentType "application/json" -Body $body |
    Select-Object -ExpandProperty choices |
    ForEach-Object { $_.message.content }
```

### 6.5 vLLM with Tool-Calling Models (Required for OpenClaw)

OpenClaw requires native tool-calling support. Gemma-4-E4B supports basic tool calling,
but Qwen3 models have stronger tool-calling performance for agentic workflows.

```bash
# Stop current vLLM instance
docker stop vllm && docker rm vllm

# Download a tool-calling optimized model
# (if not already downloaded)
source ~/venvs/llm/bin/activate
hf download Qwen/Qwen3-8B \
  --local-dir ~/jetson-ai-data/models/hf/Qwen3-8B

# Launch vLLM with tool-calling enabled
docker run --runtime nvidia -d \
  --name vllm \
  --network host \
  --ipc host \
  --shm-size 8g \
  --restart unless-stopped \
  -e HF_TOKEN=$HF_TOKEN \
  -v ~/jetson-ai-data/models/hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
  Qwen/Qwen3-8B \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.75 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

Test tool calling:
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-8B",
    "messages": [{"role": "user", "content": "What is 42 * 17? Use the calculator tool."}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "calculator",
        "description": "Perform arithmetic calculations",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string", "description": "Math expression to evaluate"}
          },
          "required": ["expression"]
        }
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 200
  }' | python3 -m json.tool
# Look for: "tool_calls": [{"function": {"name": "calculator", ...}}]
```

### 6.6 Open Firewall

```bash
sudo ufw allow 8000/tcp comment "vLLM API"
```

### 6.7 vLLM as Systemd Service

```bash
sudo tee /etc/systemd/system/vllm-container.service << 'EOF'
[Unit]
Description=vLLM Production Inference Server — Jetson AGX Orin JP 7.2
After=docker.service network.target
Requires=docker.service

[Service]
Type=simple
User=jetson
EnvironmentFile=/etc/vllm.env
Restart=on-failure
RestartSec=30
TimeoutStartSec=600
ExecStartPre=-/usr/bin/docker rm -f vllm
ExecStart=/usr/bin/docker run --runtime nvidia \
  --name vllm \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e HF_TOKEN=${HF_TOKEN} \
  -v /home/jetson/jetson-ai-data/models/hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
  google/gemma-4-E4B-it \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.70
ExecStop=/usr/bin/docker stop vllm
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create env file with HF token
sudo tee /etc/vllm.env << EOF
HF_TOKEN=$(cat ~/.cache/huggingface/token)
EOF
sudo chmod 600 /etc/vllm.env

sudo systemctl daemon-reload
sudo systemctl enable vllm-container
```

### 6.8 Three-Engine Summary (All Verified on JP 7.2)

| Engine | Container/Method | Port | GPU | Status | Best For |
|--------|-----------------|------|-----|--------|---------|
| Ollama | Native installer | 11434 | ✅ | ✅ Running | Chat, RAG, embeddings |
| llama.cpp | Build from source | 9090 | ✅ | ✅ Running | GGUF quantized, 70B+ |
| vLLM 0.22.0 | `vllm/vllm-openai:v0.22.0-ubuntu2404` | 8000 | ✅ | ✅ Running | Production, tool calling, JSON |

> **Memory note:** All three engines share the 64GB unified RAM pool.
> Running them simultaneously is possible but each loaded model consumes VRAM.
> For production, pick one primary engine based on your workload.

---


## Step 7 — Open WebUI (Chat Interface)

Provides a ChatGPT-like browser interface for all inference engines.

```bash
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  --network host \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  ghcr.io/open-webui/open-webui:main

# Open firewall
sudo ufw allow 8080/tcp comment "Open WebUI"

# Wait for startup
docker logs open-webui --follow
# Wait for: "Application startup complete."
```

Access at `http://<JETSON_IP>:8080`

To add vLLM as a second provider in Open WebUI:
- Settings → Connections → OpenAI API
- URL: `http://localhost:8000/v1`
- Key: `none`

---

## Step 8 — PyTorch for JP 7.2 (SBSA Path)

For JetPack 7.2 SBSA, install PyTorch using the SBSA PyPI index: `uv pip install torch torchvision torchaudio --index-url https://pypi.jetson-ai-lab.io/sbsa/cu129`

```bash
# Create virtual environment
python3 -m venv ~/venvs/llm
source ~/venvs/llm/bin/activate
pip install --upgrade pip uv

# Install PyTorch via SBSA index (JP 7.2 CUDA 13 path)
uv pip install torch torchvision torchaudio \
  --index-url https://pypi.jetson-ai-lab.io/sbsa/cu129 \
  --extra-index-url https://pypi.org/simple

# Verify
python3 -c "
import torch
print('PyTorch     :', torch.__version__)
print('CUDA avail  :', torch.cuda.is_available())
print('CUDA version:', torch.version.cuda)
if torch.cuda.is_available():
    print('GPU         :', torch.cuda.get_device_name(0))
    print('GPU memory  :', torch.cuda.get_device_properties(0).total_memory // (1024**3), 'GB')
    x = torch.randn(3, 3).cuda()
    print('GPU tensor  :', x.shape, 'on', x.device)
"
```

### Or use the NVIDIA NGC PyTorch iGPU Container

For containerized workflows, NVIDIA provides a purpose-built iGPU container:

```bash
# PyTorch iGPU container (optimized for Jetson integrated GPU)
docker run --runtime nvidia -it --rm \
  --network host \
  -v ~/jetson-ai-data:/workspace \
  nvcr.io/nvidia/pytorch:26.02-py3-igpu \
  python3 -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

---

## Step 9 — Model Selection Guide for AGX Orin 64GB

Based on the Jetson AI Lab model directory and JP 7.2 benchmarks:

| Model | Parameters | VRAM | Engine | Tool Calling | Best For |
|-------|-----------|------|--------|-------------|---------|
| Gemma 4 E4B | 4B | ~8GB | vLLM/llama.cpp | ✓ | Fast general use |
| Qwen3.6 8B | 8B | ~10GB | vLLM/Ollama | ✓ | Balanced quality/speed |
| Qwen3.6 27B | 27B | ~18GB | vLLM | ✓ | Best quality, tool calling |
| Gemma 4 26B-A4B | MoE 26B | ~15GB | vLLM | ✓ | Efficient large model |
| Qwen3.6 35B-A3B | MoE 35B | ~8GB active | vLLM | ✓ | High capacity, low cost |
| MiniMax M2.7 | MoE 230B | ~40GB | llama.cpp | ✓ | Max capability on 64GB |
| Nemotron 3 Nano Omni | MoE 30B | ~10GB | vLLM | ✓ | Vision+language+audio |
| nomic-embed-text | — | ~0.3GB | Ollama | — | RAG embeddings |

### Model Download via HuggingFace CLI

```bash
source ~/venvs/llm/bin/activate
pip install huggingface-hub

# Login (required for gated models like Gemma, Llama)
hf auth login

# Download model
hf download Qwen/Qwen3.6-27B \
  --local-dir ~/jetson-ai-data/models/hf/Qwen3.6-27B \
  --exclude "*.msgpack" "*.h5" "flax*" "tf_*"

# Verify
ls -lh ~/jetson-ai-data/models/hf/Qwen3.6-27B/
du -sh ~/jetson-ai-data/models/hf/Qwen3.6-27B/
```

---

## Step 10 — OpenClaw on AGX Orin (Path B: AGX-class Setup)

For AGX Orin, use Path B: serve a local model with vLLM in Docker, then point OpenClaw at it through the onboarding wizard. Unlike the Nano route, on AGX-class Jetsons the model choice matters more — any model capable of tool calling works.

### 10.1 Prerequisites for OpenClaw

```bash
# Node.js (required for OpenClaw/OpenShell)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version    # v22.x.x
npm --version

# Install OpenShell CLI
npm install -g @openshell/cli

# Verify
openshell --version
```

### 10.2 Ensure vLLM is Running with Tool Calling

OpenClaw requires a tool-calling capable model. Qwen3.6 27B is recommended for AGX Orin 64GB.

```bash
# Start vLLM with tool calling (if not already running)
docker run --runtime nvidia -d \
  --name vllm-openclaw \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e HF_TOKEN=$HF_TOKEN \
  -v ~/jetson-ai-data/models/hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
    --model Qwen/Qwen3.6-27B \
    --dtype bfloat16 \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.80 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes

# Wait for startup and verify
sleep 10
curl http://localhost:8000/v1/models | python3 -m json.tool
```

### 10.3 Install OpenClaw

```bash
# Install OpenClaw
npm install -g @openclaw/cli

# Verify
openclaw --version

# Run the onboarding wizard
# It will ask for the inference provider — point it to your local vLLM
openclaw onboard
```

During onboarding, configure:
- Provider: **Local (OpenAI-compatible)**
- Base URL: `http://localhost:8000/v1`
- API Key: `none`
- Model: `Qwen/Qwen3.6-27B`

### 10.4 Start OpenClaw Gateway

```bash
# Start the OpenClaw gateway (bound to localhost for security)
nohup openclaw gateway run > ~/.openclaw/gateway.log 2>&1 &

# Verify it started
sleep 3
openclaw channels status --probe

# Access the OpenClaw UI
# Open in NoMachine browser: http://localhost:18788
```

### 10.5 Multi-Agent Demo

```bash
# Download and run the multi-agent debate demo
curl -fsSL https://raw.githubusercontent.com/NVIDIA-AI-IOT/jetson-ai-lab/main/public/code-samples/openclaw-orin-nano/multi-agent-debate.py \
  -o /tmp/debate.py

python3 /tmp/debate.py --demo
# Results saved to ~/debate_aurora_vs_sage.md
```

---

## Step 11 — NemoClaw (Security Layer on OpenClaw)

NemoClaw adds privacy and security controls to OpenClaw. With JetPack 7.2, Jetson devices come preconfigured with the required dependencies to deploy NemoClaw-based workflows without manual environment setup.

### 11.1 One-Command Install (JP 7.2 Native)

```bash
# Official NVIDIA single-command installer
# JetPack 7.2 ships all prerequisites
curl -fsSL nvidia.com/nemoclaw.sh | bash

# Verify
nemoclaw --version 2>/dev/null || \
  openshell --version
```

### 11.2 JetsonHacks NemoClaw-Orin (More Robust Setup)

The jetsonhacks NemoClaw-Orin repository provides Jetson-specific scripts for installation and recovery, avoiding common pitfalls related to ARM64 architecture and edge resource constraints.

```bash
# Clone the Jetson-specific NemoClaw helper
cd ~
git clone https://github.com/jetsonhacks/NemoClaw-Orin
cd NemoClaw-Orin

# Read the setup guide
cat README.md

# Step 1: Prepare the Jetson host
./setup-jetson-orin.sh

# Step 2: Onboard NemoClaw
# Stop other large LLM containers first to free memory
docker stop ollama vllm 2>/dev/null || true
sleep 3

./onboard-nemoclaw.sh

# Step 3: Start NemoClaw
./restart-nemoclaw.sh

# Step 4: Check status
./forward-openclaw.sh status
```

### 11.3 NemoClaw Architecture

```
                    Browser (port 18789)
                           │
                    policy-proxy.js
                    ┌──────────────────┐
                    │  Security Layer  │
                    │  • L7 REST policy│
                    │  • Filesystem    │
                    │    isolation     │
                    │  • Network       │
                    │    enforcement   │
                    └──────────────────┘
                           │
                    OpenClaw Gateway (port 18788)
                           │
              ┌────────────┴────────────┐
              │                         │
       Local vLLM               NVIDIA build.nvidia.com
       (Qwen3.6 27B)            (cloud fallback)
```

### 11.4 Configure Local Inference Provider

```bash
# Point NemoClaw to local vLLM (fully offline, private)
openshell inference set \
  --provider local \
  --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3.6-27B \
  --no-verify

# Verify configuration
openshell inference list
```

### 11.5 Recovery After Reboot

```bash
# After each reboot, restore NemoClaw
cd ~/NemoClaw-Orin
./restart-nemoclaw.sh

# Restore sandbox if needed
./recover-sandbox.sh my-sandbox

# Restore browser forward
./forward-openclaw.sh
```

---

## Step 12 — Jetson Agent Skills

Jetson Skills are packaged, agent-executable instructions for Jetson-specific tasks: BSP customization, clock settings, fan profiles, nvpmodel modes, memory audits, model benchmarks, diagnostics, and container recommendations.

### 12.1 Jetson Device Skills

```bash
# Clone device skills
git clone https://github.com/NVIDIA-AI-IOT/jetson-device-skills \
  ~/projects/jetson-device-skills

cd ~/projects/jetson-device-skills

source ~/venvs/llm/bin/activate
pip install -r requirements.txt 2>/dev/null || \
  pip install openai requests pydantic

# Read available skills
ls skills/
cat README.md | head -80
```

**Available skill categories:**

| Skill Category | What it Does | Practical Value |
|---------------|-------------|----------------|
| Memory Optimization | Tunes DRAM carveouts, kernel reservations, user-space processes | More RAM for LLMs |
| Model Benchmarking | Measures tok/s, latency across models and engines | Choose best model for your use case |
| Linux Customization | BSP configuration, I/O, clock settings, fan control | Production deployment |
| Package Recommendations | Suggests optimal container for workload | Skip trial-and-error |
| Diagnostics | GPU, thermal, memory health checks | Debugging |

### 12.2 Run Memory Optimization Skill

```bash
cd ~/projects/jetson-device-skills

# Check current memory usage before optimization
free -h
sudo tegrastats --interval 1000 &
sleep 3
kill %1

# Run memory optimization skill
python3 run_skill.py \
  --skill memory_optimization \
  --backend ollama \
  --base-url http://localhost:11434 \
  --model qwen3:8b

# Check memory after optimization
free -h
```

### 12.3 Run Model Benchmarking Skill

```bash
# Benchmark models across available engines
python3 run_skill.py \
  --skill model_benchmarking \
  --models "qwen3:8b,gemma4:latest" \
  --engines "ollama,vllm" \
  --output ~/jetson-ai-data/benchmark_results.json

# View results
python3 -m json.tool ~/jetson-ai-data/benchmark_results.json
```

### 12.4 Jetson BSP Skills

```bash
# Clone BSP skills
git clone https://github.com/NVIDIA-AI-IOT/jetson-bsp-skills \
  ~/projects/jetson-bsp-skills

cd ~/projects/jetson-bsp-skills
source ~/venvs/llm/bin/activate
pip install -r requirements.txt 2>/dev/null

# These skills can automate:
# - Custom carrier board bring-up
# - Fan curve configuration
# - Power profile tuning
# - I/O configuration
cat README.md
```

---

## Step 13 — Production Agentic Pipeline

### 13.1 Full Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │  Jetson AGX Orin 64GB | JetPack 7.2        │
                    │                                             │
                    │  Inference Layer                            │
                    │  ┌──────────────────────────────────────┐  │
                    │  │ Ollama :11434  │ vLLM :8000         │  │
                    │  │ (SBSA container│ (upstream vllm     │  │
                    │  │  chat/RAG)    │  production serve)  │  │
                    │  │ llama.cpp :8080│                    │  │
                    │  │ (GGUF/quant)  │                    │  │
                    │  └──────────────────────────────────────┘  │
                    │                                             │
                    │  Agentic Layer                              │
                    │  ┌──────────────────────────────────────┐  │
                    │  │ OpenClaw Gateway :18788               │  │
                    │  │   └── NemoClaw (security wrapper)    │  │
                    │  │         ├── policy-proxy.js           │  │
                    │  │         ├── Landlock filesystem       │  │
                    │  │         └── L7 REST enforcement       │  │
                    │  └──────────────────────────────────────┘  │
                    │                                             │
                    │  Interface Layer                            │
                    │  ┌──────────────────────────────────────┐  │
                    │  │ Open WebUI :8080  │ NemoClaw UI :18789│ │
                    │  └──────────────────────────────────────┘  │
                    └─────────────────────────────────────────────┘
                                        │
                            ┌───────────┴────────────┐
                            │   Windows 11 / Remote   │
                            │  SSH :22 | NX :4000    │
                            └────────────────────────┘
```

### 13.2 Docker Compose for Full Stack

```bash
mkdir -p ~/jetson-ai-data/compose
cat > ~/jetson-ai-data/compose/docker-compose.yml << 'EOF'
services:

  # NOTE: Ollama runs as native systemd service on JP 7.2 (not Docker).
  # Install:    curl -fsSL https://ollama.com/install.sh | sh
  # Configure:  /etc/systemd/system/ollama.service.d/override.conf
  # The NVIDIA-AI-IOT container (r38.x) targets Thor (L4T r38), not Orin JP 7.2.
  # Ollama API will be at: http://localhost:11434

  vllm:
    image: vllm/vllm-openai:v0.22.0-ubuntu2404
    container_name: vllm
    network_mode: host
    runtime: nvidia
    restart: unless-stopped
    shm_size: '8gb'
    ipc: host
    volumes:
      - /home/jetson/jetson-ai-data/models/hf:/root/.cache/huggingface
    environment:
      - HF_TOKEN=${HF_TOKEN}
    command: >
      --model Qwen/Qwen3.6-27B
      --dtype bfloat16
      --max-model-len 16384
      --gpu-memory-utilization 0.80
      --enable-auto-tool-choice
      --tool-call-parser hermes

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    network_mode: host
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - OLLAMA_BASE_URL=http://localhost:11434

volumes:
  open-webui-data:
EOF

# Create env file
cat > ~/jetson-ai-data/compose/.env << 'EOF'
HF_TOKEN=hf_your_token_here
EOF
chmod 600 ~/jetson-ai-data/compose/.env

# Deploy (not vllm and ollama simultaneously unless memory allows)
cd ~/jetson-ai-data/compose
docker compose up -d ollama open-webui

# When ready for production serving with vLLM:
docker compose stop ollama
docker compose up -d vllm
```

### 13.3 Python Client for Agentic Pipelines

```python
# ~/projects/agentic/jetson_pipeline.py
"""
Production agentic pipeline using OpenAI-compatible APIs.
Works with Ollama, vLLM, and llama.cpp on Jetson AGX Orin.
"""

from openai import OpenAI
import json
import time
from typing import Optional

class JetsonInferenceClient:
    """Unified client for all inference engines on Jetson."""

    BACKENDS = {
        "ollama":    "http://localhost:11434/v1",
        "vllm":      "http://localhost:8000/v1",
        "llama_cpp": "http://localhost:8080/v1",
    }

    def __init__(self, backend: str = "vllm"):
        if backend not in self.BACKENDS:
            raise ValueError(f"Backend must be one of {list(self.BACKENDS)}")
        self.backend = backend
        self.client = OpenAI(
            base_url=self.BACKENDS[backend],
            api_key="none"   # Local servers don't need a key
        )

    def chat(self, prompt: str, model: str, system: str = "",
             tools: Optional[list] = None, max_tokens: int = 512) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        kwargs = dict(model=model, messages=messages, max_tokens=max_tokens)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        elapsed = time.time() - start
        tokens = response.usage.completion_tokens

        print(f"[{self.backend}] {tokens} tokens in {elapsed:.1f}s "
              f"({tokens/elapsed:.0f} tok/s)")
        return response.choices[0].message.content

    def embed(self, text: str, model: str = "nomic-embed-text") -> list:
        """Get embeddings for RAG pipelines."""
        response = self.client.embeddings.create(input=text, model=model)
        return response.data[0].embedding


def multi_step_pipeline(query: str):
    """Multi-step reasoning pipeline using vLLM."""
    client = JetsonInferenceClient("vllm")
    model = "Qwen/Qwen3.6-27B"

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    # Step 1: Analyze the query
    analysis = client.chat(
        prompt=f"Analyze this query and identify the key components: {query}",
        model=model,
        system="You are a concise analyst. Output 3 bullet points.",
        max_tokens=200
    )
    print(f"\nAnalysis:\n{analysis}")

    # Step 2: Generate a plan
    plan = client.chat(
        prompt=f"Given this analysis:\n{analysis}\n\nCreate a 3-step action plan.",
        model=model,
        system="You are a planning expert. Be specific and actionable.",
        max_tokens=300
    )
    print(f"\nPlan:\n{plan}")

    # Step 3: Execute step 1
    execution = client.chat(
        prompt=f"Execute step 1 of this plan:\n{plan}",
        model=model,
        system="You are a practical executor. Provide concrete output.",
        max_tokens=400
    )
    print(f"\nExecution:\n{execution}")

    return {"analysis": analysis, "plan": plan, "execution": execution}


if __name__ == "__main__":
    result = multi_step_pipeline(
        "How can I optimize LLM inference throughput on Jetson AGX Orin 64GB "
        "for a multi-user production deployment?"
    )
    print("\nPipeline complete.")
```

---

## Step 14 — NVIDIA Resources and Blueprints

### 14.1 NVIDIA Build — AI Blueprints

NVIDIA provides production-ready AI application blueprints deployable on Jetson:

| Blueprint | Use Case | URL |
|-----------|---------|-----|
| Video Search & Summarization | Vision agents, surveillance | build.nvidia.com/blueprints |
| PDF to Podcast | Document processing, audio | build.nvidia.com/nvidia/pdf-to-podcast |
| NVIDIA NIM | Microservice inference | build.nvidia.com |
| Retrieval-Augmented Generation | Local knowledge base | build.nvidia.com |

```bash
# Test NVIDIA NIM API compatibility (cloud inference fallback)
# Replace with your NVIDIA API key from build.nvidia.com
export NVIDIA_API_KEY="nvapi-your-key-here"

curl https://integrate.api.nvidia.com/v1/chat/completions \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/nemotron-3-ultra-253b-reward",
    "messages": [{"role": "user", "content": "Hello from Jetson!"}],
    "max_tokens": 100
  }' | python3 -m json.tool
```

### 14.2 Jetson AI Lab — Model Browser

The Jetson AI Lab model browser provides auto-generated `docker run` commands for every model and engine combination:

**URL:** https://www.jetson-ai-lab.com/models/

Featured models for AGX Orin 64GB include MiniMax M2.7 (MoE 230B via llama.cpp), Qwen3.6 35B-A3B via vLLM, Qwen3.6 27B via vLLM, Nemotron 3 Nano Omni VLM via vLLM/llama.cpp/Ollama, and the full Gemma 4 family.

For each model, the site generates the exact `docker run` command for your device and chosen inference engine.

### 14.3 NGC PyTorch iGPU Container

```bash
# NVIDIA NGC PyTorch optimized for Jetson iGPU
docker run --runtime nvidia -it \
  --network host \
  -v ~/jetson-ai-data:/workspace \
  nvcr.io/nvidia/pytorch:26.02-py3-igpu \
  python3

# Inside container — full PyTorch + CUDA environment
# import torch; torch.cuda.is_available()  → True
```

### 14.4 Key GitHub Repositories

```bash
# jetson-containers — main framework
git clone https://github.com/dusty-nv/jetson-containers

# Jetson AI Lab website and tutorials
git clone https://github.com/NVIDIA-AI-IOT/jetson-ai-lab

# Jetson Device Skills (memory opt, benchmarking, customization)
git clone https://github.com/NVIDIA-AI-IOT/jetson-device-skills

# Jetson BSP Skills (Linux/BSP automation)
git clone https://github.com/NVIDIA-AI-IOT/jetson-bsp-skills

# NemoClaw on Orin (Jetsonhacks helper scripts)
git clone https://github.com/jetsonhacks/NemoClaw-Orin

# DeepStream Coding Agent (vision pipelines)
git clone https://github.com/NVIDIA-AI-IOT/DeepStream_Coding_Agent
```

---

## Step 15 — Monitoring and Maintenance

### 15.1 GPU and System Monitor

```bash
# Install jtop via pipx
pipx install jetson-stats
pipx ensurepath && source ~/.bashrc

# Launch full system monitor
jtop

# Quick GPU check
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu \
  --format=csv,noheader,nounits

# Continuous tegrastats
sudo tegrastats --interval 1000
```

### 15.2 LLM Stack Status Script

```bash
cat > ~/scripts/llm-status.sh << 'EOF'
#!/bin/bash
G="\033[92m"; R="\033[91m"; Y="\033[93m"; C="\033[96m"; N="\033[0m"

echo -e "${C}=== Jetson AGX Orin LLM Stack — JetPack 7.2 ===${N}"
echo "$(date) | $(hostname -I | awk '{print $1}')"
echo ""

echo -e "${C}── GPU ──────────────────────────────────────────${N}"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
  --format=csv,noheader,nounits | \
  awk -F', ' '{printf "  Util: %s%% | VRAM: %s/%s MiB | Temp: %s°C\n",$1,$2,$3,$4}'
echo ""

echo -e "${C}── Inference Engines ────────────────────────────${N}"
for port_name in "11434:Ollama" "8000:vLLM" "8080:llama.cpp"; do
  port="${port_name%%:*}"
  name="${port_name##*:}"
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:$port/v1/models)
  [ "$code" = "200" ] && \
    echo -e "  ${G}✅ $name :$port${N}" || \
    echo -e "  ${R}❌ $name :$port${N}"
done
echo ""

echo -e "${C}── Containers ───────────────────────────────────${N}"
docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null
echo ""

echo -e "${C}── Agentic Stack ────────────────────────────────${N}"
openclaw channels status 2>/dev/null | head -5 || echo "  OpenClaw: not running"
echo ""

echo -e "${C}── Power Mode ───────────────────────────────────${N}"
sudo nvpmodel -q 2>/dev/null | grep "NV Power Mode" | sed 's/^/  /'
EOF

chmod +x ~/scripts/llm-status.sh
echo "alias llmstatus='~/scripts/llm-status.sh'" >> ~/.bashrc
source ~/.bashrc
```

### 15.3 Memory Management for Large Models

```bash
# Check available memory before loading a large model
free -h

# See what's using GPU/unified memory
docker stats --no-stream 2>/dev/null | head -10

# Release GPU memory from a stopped Ollama model
docker exec ollama ollama stop <model-name>

# Full GPU context release (kills all CUDA processes)
# Use only when switching modes or troubleshooting
sudo fuser -k /dev/nvidia* 2>/dev/null || true

# Verify memory freed
free -h
```

### 15.4 Power-Aware Workflow Aliases

```bash
cat >> ~/.bashrc << 'ALIASES'

# ── Power Mode ─────────────────────────────────────────────────
# Default is MODE_15W (set at boot by systemd service)
# Use these aliases before loading large models

alias pwr-status='sudo nvpmodel -q && echo "RAM: $(free -h | grep Mem | awk "{print \$3\"/\"\$2}")"'
alias pwr-10w='sudo nvpmodel -m 1 && echo "MODE_10W — monitoring only"'
alias pwr-15w='sudo nvpmodel -m 2 && echo "MODE_15W — default (1B-4B models)"'
alias pwr-30w='sudo nvpmodel -m 3 && echo "MODE_30W — 7B-14B models"'
alias pwr-50w='sudo nvpmodel -m 4 && echo "MODE_50W — 27B+ models"'
alias pwr-max='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MAXN — 70B models / peak production"'
alias pwr-save='sudo nvpmodel -m 2 && echo "Returned to MODE_15W default"'

# ── Inference Mode Switching (power-aware) ──────────────────────
alias mode-ollama-light='pwr-15w; ollama ps'
alias mode-ollama-medium='pwr-30w; ollama ps'

mode-vllm() {
  MODEL="${1:-google/gemma-4-E4B-it}"
  PWR="${2:-30w}"
  echo "Power: $PWR | Model: $MODEL"
  pwr-$PWR
  for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
    ollama stop "$m" 2>/dev/null
  done
  sleep 2
  docker stop vllm 2>/dev/null; docker rm vllm 2>/dev/null
  docker run --runtime nvidia -d \
    --name vllm --network host --ipc host --shm-size 8g \
    -e HF_TOKEN=$HF_TOKEN \
    -v $HOME/jetson-ai-data/models/hf:/root/.cache/huggingface \
    vllm/vllm-openai:v0.22.0-ubuntu2404 \
    $MODEL --dtype bfloat16 --max-model-len 8192 --gpu-memory-utilization 0.70
  echo "vLLM starting → docker logs vllm --follow"
}

mode-save() {
  docker stop vllm 2>/dev/null; docker rm vllm 2>/dev/null
  for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
    ollama stop "$m" 2>/dev/null
  done
  pwr-save
  echo "All inference stopped. Back to MODE_15W."
}

ALIASES

source ~/.bashrc
```

Usage examples:

```bash
# Morning start — light work
pwr-status                          # Check current mode
ollama run gemma3:1b "hello"        # Runs fine at MODE_15W

# Switch to medium model
pwr-30w                             # Switch before loading
ollama run qwen3:8b "analyze this"  # 7B model, comfortable at 30W

# Start vLLM for production session
mode-vllm google/gemma-4-E4B-it 30w  # 4B model at 30W
mode-vllm Qwen/Qwen3-8B 50w          # 8B model at 50W

# End of session — save energy
mode-save                           # Stop all inference, back to 15W
```

---

## Port Reference

| Port | Service | Container Image |
|------|---------|----------------|
| 11434 | Ollama API (OpenAI-compat) | native systemd service — `curl -fsSL https://ollama.com/install.sh \| sh` |
| 8000 | vLLM API (OpenAI-compat) | `vllm/vllm-openai:v0.22.0-ubuntu2404` |
| 8080 | llama.cpp server + Open WebUI | `$(autotag llama_cpp)` / `open-webui:main` |
| 18788 | OpenClaw Gateway | native |
| 18789 | NemoClaw UI (browser) | native |

---

## Quick Reference Commands

```bash
# === Power (always set before heavy inference) ===
pwr-status       # current mode + RAM
pwr-15w          # default — idle, 1B-4B models, embeddings
pwr-30w          # 7B-14B models
pwr-50w          # 27B+ models
pwr-max          # 70B models, benchmarking, peak production
pwr-save         # return to 15W after heavy session

# === Inference ===

# Ollama: pull and test model
docker exec ollama ollama pull qwen3:8b
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"Hello"}]}'

# vLLM: check loaded model
curl http://localhost:8000/v1/models | python3 -m json.tool

# llama.cpp: serve GGUF (native build — container fails on JP 7.2 CUDA 13)
pwr-30w   # or pwr-50w for 27B models
~/llama.cpp/build/bin/llama-server \
  --model ~/jetson-ai-data/models/gguf/Qwen3-8B-Q4_K_M.gguf \
  --host 0.0.0.0 --port 9090 --n-gpu-layers 999 --ctx-size 8192

# === Agentic ===

# Start OpenClaw gateway
openclaw gateway run

# Start NemoClaw (after setup)
cd ~/NemoClaw-Orin && ./restart-nemoclaw.sh

# Check agent status
openclaw channels status --probe

# === Performance ===

# Set max performance
sudo nvpmodel -m 0 && sudo jetson_clocks

# Live GPU monitor
sudo tegrastats --interval 500

# Full stack status
llmstatus
```

---

## Troubleshooting

### vLLM OOM on JP 7.2

```bash
# Reduce GPU utilization
# Change --gpu-memory-utilization 0.80 to 0.65

# Or reduce context length
# Add: --max-model-len 8192 instead of 16384

# Check what's consuming unified memory
free -h
docker stats --no-stream
```

### SBSA Container Architecture Mismatch

```bash
# Verify your container is built for arm64
docker inspect native (curl -fsSL https://ollama.com/install.sh | sh) | \
  grep Architecture

# If wrong architecture, find the correct tag
# Ollama runs natively on JP 7.2 — check systemd service instead
systemctl status ollama
journalctl -u ollama -n 20 --no-pager
```

### OpenClaw Not Connecting to vLLM

```bash
# Verify vLLM is up and accepting connections
curl http://localhost:8000/v1/models

# Verify tool calling model is loaded
curl http://localhost:8000/v1/models | \
  python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"

# Re-run OpenClaw onboarding to reset provider
openclaw onboard
```

### NemoClaw Fails After Reboot

```bash
cd ~/NemoClaw-Orin

# Step 1: Restore gateway
./restart-nemoclaw.sh

# Step 2: Restore sandbox
./recover-sandbox.sh my-sandbox

# Step 3: Restore browser forward
./forward-openclaw.sh

# Step 4: Check status
openclaw channels status --probe
```

---

## Summary

This setup delivers a complete, production-ready agentic AI stack on NVIDIA Jetson AGX Orin 64GB with JetPack 7.2:

| Component | Status | Notes |
|-----------|--------|-------|
| Ollama (SBSA container) | Production | Best for chat, RAG, quick prototyping |
| vLLM (upstream SBSA) | Production | Best for multi-user, structured output, tool calling |
| llama.cpp | Production | Best for quantized GGUF, very large models |
| Open WebUI | Production | Browser interface for all engines |
| OpenClaw (Path B) | Production | Agentic workflows, tool calling, AGX-class setup |
| NemoClaw | Production | Security wrapper, privacy-first agent sandbox |
| Jetson Agent Skills | Available | Memory opt, benchmarking, Linux customization |
| PyTorch (SBSA) | Available | `pypi.jetson-ai-lab.io/sbsa/cu129` |

All services are OpenAI API compatible. Any client using the standard OpenAI Python SDK can connect by setting `base_url` to the appropriate local endpoint.

---

## Official Resources

| Resource | URL |
|----------|-----|
| JetPack 7.2 Downloads | https://developer.nvidia.com/embedded/jetpack/downloads |
| Jetson AI Lab (models + tutorials) | https://www.jetson-ai-lab.com |
| jetson-containers (GitHub) | https://github.com/dusty-nv/jetson-containers |
| Jetson Device Skills | https://github.com/NVIDIA-AI-IOT/jetson-device-skills |
| NemoClaw-Orin (JetsonHacks) | https://github.com/jetsonhacks/NemoClaw-Orin |
| NVIDIA Build (Blueprints + NIMs) | https://build.nvidia.com/blueprints |
| NVIDIA AGX Orin Getting Started | https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/quick_start.html |
| NGC PyTorch iGPU Container | https://catalog.ngc.nvidia.com/orgs/nvidia/-/containers/pytorch/26.02-py3-igpu |
| JetPack 7.2 Forum Thread | https://forums.developer.nvidia.com/t/jetpack-7-2-jetson-linux-r39-2-on-jetson-agx-orin-developer-kit-getting-started-and-feedback-thread/372156 |

---

*Platform: NVIDIA Jetson AGX Orin Developer Kit 64GB · JetPack 7.2 (L4T r39.2) · Ubuntu 24.04 LTS · CUDA 13.2.1 · sm_87*
