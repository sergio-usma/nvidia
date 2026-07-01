# Jetson AGX Orin 64GB — JetPack 7.2
# OpenClaw Production Agent: Complete Setup Guide

**Board:** NVIDIA Jetson AGX Orin 64GB Developer Kit
**OS:** Ubuntu 24.04.4 LTS · L4T r39.2 · JetPack 7.2-b187
**Target:** Fully automated personal agent — content creation, tourism agency, podcast generation, conference notes, client service

---

## Table of Contents

1. [Hardware & Prerequisites](#1-hardware--prerequisites)
2. [SSH Tunnel — Web UI from Windows](#2-ssh-tunnel--web-ui-from-windows)
3. [Power & Electricity Management](#3-power--electricity-management)
4. [Memory Management Strategy](#4-memory-management-strategy)
5. [Model Selection Guide](#5-model-selection-guide)
6. [Inference Backend A — Gemma 4 E2B via vLLM (Default)](#6-inference-backend-a--gemma-4-e2b-via-vllm-default)
7. [Inference Backend B — Gemma 4 E2B via llama.cpp](#7-inference-backend-b--gemma-4-e2b-via-llamacpp)
8. [Inference Backend C — Nemotron3 Nano 30B-A3B via vLLM](#8-inference-backend-c--nemotron3-nano-30b-a3b-via-vllm)
9. [Inference Backend D — Nemotron 3 Nano Omni via llama.cpp](#9-inference-backend-d--nemotron-3-nano-omni-via-llamacpp)
10. [Model Switcher Scripts](#10-model-switcher-scripts)
11. [OpenClaw Installation](#11-openclaw-installation)
12. [OpenClaw Configuration](#12-openclaw-configuration)
13. [WhatsApp Channel Setup](#13-whatsapp-channel-setup)
14. [Production Stability & OOM Prevention](#14-production-stability--oom-prevention)
15. [Use Case Workflows](#15-use-case-workflows)
16. [Startup & Reboot Recovery](#16-startup--reboot-recovery)
17. [Quick Reference](#17-quick-reference)
18. [Resource Audit & Ghost Model Prevention](#18-resource-audit--ghost-model-prevention)

---

## 18. Resource Audit & Ghost Model Prevention

> **What happened:** You ran `ollama ps` (empty), thought everything was off, opened Open-WebUI, and found `google/gemma-4-E2B-it` fully loaded. The answer is in `docker ps`: the `vllm-openclaw` container had been running for 2 hours with `--restart unless-stopped`. vLLM **reserves GPU memory at container startup** — not at first request. So the model was consuming ~15 GB of your unified RAM the entire time, silently, with no ollama fingerprint to find it.

### Why the 64GB unified memory is deceptive

On discrete GPUs, VRAM and system RAM are separate. On Jetson the 64GB pool is **shared** — the OS, CPU processes, GPU kernels, Docker containers, and LLM weights all compete for the same physical memory. Three things make "ghost" memory consumption invisible:

| Source | Why it's invisible | How much it takes |
|---|---|---|
| Docker container with `--restart unless-stopped` | Survives reboots, starts before you log in | Full model weight + KV cache |
| vLLM's KV cache pre-allocation | Reserves `gpu_memory_utilization × total_RAM` at startup, not first request | 15–50 GB depending on config |
| Ollama keep-alive | Holds model in memory for 5 min after last use by default | Full model weight |
| Open-WebUI | Doesn't load models itself, but shows what backends have loaded | 0 extra — just a mirror |
| Linux page cache | Caches recently used model files in RAM | 2–10 GB silently |

---

### Section 18.1 — Complete memory audit (run anytime)

```bash
# ── STEP 1: What Docker containers are running and using? ──────────
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.RunningFor}}"
# Look for: vllm-*, llama-*, open-webui, ollama containers

# ── STEP 2: How much RAM is each container actually consuming? ─────
docker stats --no-stream --format \
  "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"

# ── STEP 3: What models does Ollama have loaded in GPU memory? ──────
ollama ps
# Empty = nothing loaded. Lists = model name, size, until (expiry time)

# ── STEP 4: What models are available (downloaded but not loaded)? ──
ollama list

# ── STEP 5: What's the actual RAM usage right now? ─────────────────
free -h
# 'available' is what matters — should be 55GB+ when idle

# ── STEP 6: What processes are using GPU memory? ───────────────────
sudo tegrastats | head -5
# Look for: RAM X/65536MB — X is current usage

# ── STEP 7: Which Docker containers will auto-start on reboot? ──────
docker inspect $(docker ps -aq) 2>/dev/null | \
  python3 -c "
import sys,json
containers = json.load(sys.stdin)
for c in containers:
    name = c['Name'].lstrip('/')
    policy = c['HostConfig']['RestartPolicy']['Name']
    status = c['State']['Status']
    print(f'{name:30} restart={policy:20} status={status}')
"
```

**What to expect when idle (nothing running):**

```
free -h output:
               total        used        free      shared  buff/cache   available
Mem:            62Gi        3.0Gi       55Gi       100Mi       4.0Gi       58Gi

docker ps output:
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
(empty — nothing should be running)

ollama ps output:
NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL
(empty)
```

---

### Section 18.2 — Install jetson-stats (jtop) — mandatory for headless monitoring

```bash
# Install jetson-stats (jtop) — the definitive Jetson resource monitor
sudo pip3 install jetson-stats --break-system-packages
sudo systemctl restart jtop.service 2>/dev/null || true

# Launch interactive monitor
jtop
# Press: g = GPU tab, m = Memory tab, p = Processes tab, q = quit
```

`jtop` shows in real time:
- Unified memory usage split by process
- GPU utilization and clock speed
- Power consumption (watts)
- CPU core usage
- All running processes consuming GPU

---

### Section 18.3 — Complete cleanup (nuke everything, start fresh)

Run this before any heavy pipeline or when you suspect memory is contaminated:

```bash
#!/bin/bash
# FULL CLEANUP — run before any demanding workload

echo "=== Jetson Resource Cleanup ==="

# 1. Stop ALL Docker containers (including hidden ones)
echo "→ Stopping all Docker containers..."
RUNNING=$(docker ps -q)
if [ -n "$RUNNING" ]; then
  docker stop $RUNNING
  echo "  Stopped: $(docker ps -a --format '{{.Names}}' | tr '\n' ' ')"
else
  echo "  No containers running"
fi

# 2. Unload Ollama models (don't stop the service, just flush models)
echo "→ Flushing Ollama models from memory..."
LOADED=$(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}')
if [ -n "$LOADED" ]; then
  for model in $LOADED; do
    curl -s http://localhost:11434/api/generate \
      -d "{\"model\": \"$model\", \"keep_alive\": 0}" > /dev/null
    echo "  Unloaded: $model"
  done
else
  echo "  No Ollama models loaded"
fi

# 3. Stop Ollama service entirely if not needed
echo "→ Stopping Ollama service..."
sudo systemctl stop ollama 2>/dev/null && echo "  Ollama stopped" || echo "  Ollama not running"

# 4. Drop Linux page cache (frees 2–10 GB of cached model files)
echo "→ Dropping page cache..."
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# 5. Wait and verify
sleep 5
FREE=$(free -h | awk '/^Mem:/{print $7}')
echo ""
echo "=== Cleanup complete ==="
echo "Available memory: $FREE"
echo "Running containers: $(docker ps -q | wc -l)"
echo "Ollama models loaded: $(ollama ps 2>/dev/null | tail -n +2 | wc -l)"
```

Save as `~/scripts/jetson-clean.sh` and `chmod +x`:

```bash
mkdir -p ~/scripts
# Paste the above into the file, then:
chmod +x ~/scripts/jetson-clean.sh
alias jetson-clean="~/scripts/jetson-clean.sh"
```

---

### Section 18.4 — Fix restart policies (prevent ghost containers on boot)

This is the root cause. vLLM was started with `--restart unless-stopped`, which means it **auto-starts after every reboot** — even if you didn't ask for it.

```bash
# Check restart policy for all containers
docker inspect $(docker ps -aq --format '{{.Names}}') 2>/dev/null | \
  python3 -c "
import sys, json
for c in json.load(sys.stdin):
    print(f\"{c['Name'].lstrip('/')}: {c['HostConfig']['RestartPolicy']['Name']}\")
"

# Disable auto-restart for containers you want to control manually
docker update --restart=no vllm-openclaw
docker update --restart=no llama-openclaw
docker update --restart=no open-webui

# Only OpenClaw gateway should auto-start (it's lightweight, ~500MB)
# openclaw-gateway.service is managed by systemd, not Docker — this is correct

# Verify changes
docker inspect vllm-openclaw | python3 -c \
  "import sys,json; c=json.load(sys.stdin)[0]; \
   print('Restart policy:', c['HostConfig']['RestartPolicy']['Name'])"
# Expected: no
```

**Restart policy guide:**

| Policy | Behavior | Use for |
|---|---|---|
| `no` | Never auto-starts | All LLM containers (you control when they run) |
| `unless-stopped` | Starts on reboot unless you manually stopped it | Nothing on Jetson — too aggressive |
| `always` | Always starts, even if you stopped it | Nothing on Jetson |
| `on-failure` | Restarts only on crash | Nothing critical that needs all RAM |

> **Rule:** LLM containers should **never** have `restart=always` or `restart=unless-stopped` on a memory-constrained device. Only set restart policies on lightweight services (databases, message queues) that don't consume GPU memory.

---

### Section 18.5 — Ollama keep-alive control

Ollama holds models in memory for 5 minutes by default after the last request. For production use, change this.

```bash
# Option A — Set keep_alive to 0 globally (unload immediately after each request)
sudo systemctl edit ollama
# Add:
[Service]
Environment="OLLAMA_KEEP_ALIVE=0"

# Option B — Set per-request (useful for one-off batch tasks)
curl http://localhost:11434/api/generate \
  -d '{"model": "qwen3:8b", "prompt": "Hello", "keep_alive": 0}'

# Option C — Force unload any model right now
curl http://localhost:11434/api/generate \
  -d '{"model": "MODEL_NAME_HERE", "keep_alive": 0}'

# Check what's loaded
ollama ps

# List all downloaded models (not necessarily loaded)
ollama list

# Completely stop Ollama when not needed
sudo systemctl stop ollama

# Start Ollama when needed
sudo systemctl start ollama
```

---

### Section 18.6 — Comprehensive resource management aliases

Add this complete block to `~/.bashrc` (after the existing PATH exports):

```bash
# =====================================================
# JETSON ORIN AGX — RESOURCE MANAGEMENT
# =====================================================

# ── AUDITORÍA ─────────────────────────────────────

# Full snapshot: containers + stats + ollama + memory
alias jetson-audit='
echo "=== $(date) ===";
echo "";
echo "── Docker containers ──";
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" 2>/dev/null || echo "  none";
echo "";
echo "── Docker memory usage ──";
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null;
echo "";
echo "── Ollama loaded models ──";
ollama ps 2>/dev/null;
echo "";
echo "── System memory ──";
free -h;
echo "";
echo "── Inference endpoints ──";
curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c "import sys,json; [print(\"  vLLM:8000\", m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" 2>/dev/null || echo "  vLLM:8000 offline";
curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -c "import sys,json; [print(\"  llama.cpp:8080\", m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" 2>/dev/null || echo "  llama.cpp:8080 offline";
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; [print(\"  Ollama:\", m[\"name\"]) for m in json.load(sys.stdin).get(\"models\",[])]" 2>/dev/null || echo "  Ollama:11434 offline";
'

# Quick memory check
alias jetson-mem='free -h && echo "" && docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" 2>/dev/null'

# Check restart policies
alias jetson-restart-policies='docker inspect $(docker ps -aq) 2>/dev/null | python3 -c "
import sys, json
cs = json.load(sys.stdin)
for c in cs:
    n = c[\"Name\"].lstrip(\"/\")
    p = c[\"HostConfig\"][\"RestartPolicy\"][\"Name\"]
    s = c[\"State\"][\"Status\"]
    print(f\"{n:35} restart={p:20} ({s})\")
" 2>/dev/null || echo "No containers"'

# Interactive monitor (press q to quit)
alias jetson-top='jtop'

# Tegrastats snapshot (raw NVIDIA stats)
alias jetson-hw='sudo tegrastats --interval 2000 &; sleep 6; kill %1 2>/dev/null'

# ── LIMPIEZA ──────────────────────────────────────

# Nuclear option: stop everything, drop caches
alias jetson-clean='~/scripts/jetson-clean.sh'

# Stop only inference (keep open-webui, OpenClaw running)
alias jetson-stop-inference='
docker stop vllm-openclaw llama-openclaw 2>/dev/null;
for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null;
done;
sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches";
echo "Inference stopped. Free: $(free -h | awk \"/^Mem:/{print \$7}\")";
'

# Drop page cache only (safe, no service impact)
alias jetson-dropcache='sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches" && echo "Cache dropped. Free: $(free -h | awk \"/^Mem:/{print \$7}\")"'

# ── CARGAS DE TRABAJO: MODOS ──────────────────────

# MODE: Idle — everything off, 15W, max RAM available
alias mode-idle='
docker stop vllm-openclaw llama-openclaw open-webui 2>/dev/null;
sudo systemctl stop ollama 2>/dev/null;
sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches";
sudo nvpmodel -m 1;
sudo jetson_clocks --restore;
echo "MODE: IDLE — 15W, all inference stopped";
echo "Free: $(free -h | awk \"/^Mem:/{print \$7}\")";
'

# MODE: OpenClaw only — Gemma 4 E2B via vLLM, 30W
alias mode-openclaw='~/scripts/switch-model.sh gemma-vllm'

# MODE: Gemma lightweight — llama.cpp, 30W, minimal RAM
alias mode-lite='~/scripts/switch-model.sh gemma-llama'

# MODE: Long document — Nemotron3 30B, MAXN
alias mode-longdoc='~/scripts/switch-model.sh nemotron-text'

# MODE: Multimodal — Nemotron Omni, MAXN, audio+video
alias mode-multimodal='~/scripts/switch-model.sh nemotron-omni'

# MODE: Ollama only — start Ollama, stop vLLM
alias mode-ollama='
docker stop vllm-openclaw llama-openclaw 2>/dev/null;
sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches";
sleep 5;
sudo systemctl start ollama;
sudo nvpmodel -m 2;
sudo jetson_clocks;
echo "MODE: OLLAMA — 30W, use: ollama run <model>";
echo "Free: $(free -h | awk \"/^Mem:/{print \$7}\")";
'

# MODE: Open-WebUI only (no inference — connect to external or local Ollama)
alias mode-webui='
docker stop vllm-openclaw llama-openclaw 2>/dev/null;
docker start open-webui 2>/dev/null || echo "open-webui container not found";
echo "Open-WebUI started. Access at http://192.168.1.100:3000 or via tunnel";
'

# ── MODELOS: OLLAMA ───────────────────────────────

# List available models
alias ollama-list='ollama list'

# What is currently loaded in GPU memory
alias ollama-loaded='ollama ps'

# Unload all Ollama models from memory
alias ollama-unload-all='
for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
  echo "Unloading $m...";
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null;
done;
echo "All Ollama models unloaded";
'

# Pull and run a model (ensures resources are free first)
alias ollama-safe-run='f(){ jetson-stop-inference; ollama run "$1"; }; f'

# ── DOCKER ────────────────────────────────────────

# Full container overview with restart policies
alias docker-full='docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.RunningFor}}"'

# Disable auto-restart on all LLM containers (run once after setup)
alias docker-fix-restart='
docker update --restart=no vllm-openclaw 2>/dev/null && echo "Fixed: vllm-openclaw";
docker update --restart=no llama-openclaw 2>/dev/null && echo "Fixed: llama-openclaw";
docker update --restart=no open-webui 2>/dev/null && echo "Fixed: open-webui";
echo "All LLM containers set to restart=no";
'

# Remove stopped containers (free disk space, not RAM)
alias docker-prune='docker container prune -f && echo "Stopped containers removed"'

# ── POWER SHORTCUTS ───────────────────────────────
alias pwr-idle='sudo nvpmodel -m 1 && sudo jetson_clocks --restore && echo "15W idle"'
alias pwr-30w='sudo nvpmodel -m 2 && sudo jetson_clocks && echo "30W inference"'
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MAXN 50W"'
alias pwr-status='sudo nvpmodel -q'
```

Apply immediately:
```bash
source ~/.bashrc
```

---

### Section 18.7 — Pre-workload checklist

Before starting any demanding pipeline (OpenClaw, video processing, large doc analysis):

```bash
# Run this every time before a heavy workload
jetson-audit          # See what's running
jetson-clean          # Stop everything, drop caches
# Pick your mode:
mode-openclaw         # for WhatsApp agent + tool calling
mode-longdoc          # for 300-page PDF processing
mode-multimodal       # for audio/video → notes
# Verify
jetson-mem            # confirm 50GB+ free before starting
```

---

### Section 18.8 — Prevent Open-WebUI from loading models automatically

Open-WebUI itself doesn't load models, but if it's configured to use a local Ollama or vLLM as backend, it will discover and display them. The danger: users (or yourself) clicking on a model in Open-WebUI will trigger Ollama to load it immediately.

```bash
# Option A — Stop Open-WebUI when not in use (safest)
docker stop open-webui

# Option B — Disconnect Open-WebUI from local Ollama
# Set OLLAMA_BASE_URL to an invalid address so it can't trigger loads
docker update --env-add OLLAMA_BASE_URL=http://localhost:0 open-webui
docker restart open-webui

# Option C — Only run Open-WebUI when you explicitly want it
# Remove restart policy (already covered in Section 18.4):
docker update --restart=no open-webui
# Then start manually when needed:
docker start open-webui
```

---

### Section 18.9 — One-time hardening (run after initial setup)

```bash
echo "=== Applying Jetson production hardening ==="

# 1. Fix all restart policies
docker-fix-restart

# 2. Set Ollama keep_alive to 0 (unload after each request)
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/keepalive.conf << 'EOF'
[Service]
Environment="OLLAMA_KEEP_ALIVE=0"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama 2>/dev/null || true
echo "Ollama keep_alive set to 0"

# 3. Install jetson-stats for jtop monitoring
sudo pip3 install jetson-stats --break-system-packages 2>/dev/null || \
  pip3 install jetson-stats --break-system-packages
echo "jtop installed"

# 4. Apply OOM protection sysctl
sudo tee /etc/sysctl.d/99-jetson-oom.conf << 'EOF'
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1
vm.swappiness = 1
vm.vfs_cache_pressure = 200
EOF
sudo sysctl -p /etc/sysctl.d/99-jetson-oom.conf
echo "OOM protection applied"

# 5. Verify
echo ""
echo "=== Hardening complete ==="
echo "Restart policies:"
jetson-restart-policies
```

---

### Summary: the three rules for Jetson memory hygiene

```
RULE 1 — audit first, start second
  Always run: jetson-audit
  Before any workload confirm available > 50GB

RULE 2 — use mode aliases, never raw docker run
  mode-idle         ← before heavy non-LLM work
  mode-openclaw     ← for agent/WhatsApp use
  mode-longdoc      ← for PDF/document tasks
  mode-multimodal   ← for audio/video processing
  mode-ollama       ← for Ollama model exploration

RULE 3 — no LLM container should ever restart automatically
  docker update --restart=no <container>
  The only thing that auto-starts: openclaw-gateway.service (lightweight)
```

---

## 1. Hardware & Prerequisites

```
NVIDIA Jetson AGX Orin 64GB
├── GPU:     Orin nvgpu · Ampere sm_87
├── CPU:     ARM Cortex-A78AE · 12 cores @ 2.2GHz
├── RAM:     64 GB LPDDR5 ECC unified (GPU + CPU share)
├── SSD:     931.5 GB NVMe (model storage)
├── eMMC:    59.2 GB (OS)
├── AI:      275 TOPS (MAXN mode)
├── CUDA:    13.2.1
├── Python:  3.12.3
└── Docker:  runtime=nvidia (default)

Windows Host (192.168.1.33) ←→ Jetson (192.168.1.100 static)
```

### Required tools on Jetson

```bash
# Verify essential tools
docker --version
hf --version          # huggingface_hub CLI (NOT huggingface-cli)
node --version        # v22.23.1+
npm --version         # 11+
openclaw --version    # 2026.6.10+
nvpmodel -q           # power mode check
```

### HF Token — One-time setup (permanent fix)

The token must be in three places to work in all contexts:

```bash
# 1. Cache to disk (picked up by Docker volume mount)
hf auth login --token $(grep 'export HF_TOKEN' ~/.bashrc | sed 's/.*HF_TOKEN=//;s/"//g')

# 2. /etc/environment (systemd + Docker daemon)
HF_VAL=$(grep 'export HF_TOKEN' ~/.bashrc | sed 's/.*HF_TOKEN=//;s/"//g')
echo "HF_TOKEN=${HF_VAL}" | sudo tee -a /etc/environment
echo "HUGGING_FACE_HUB_TOKEN=${HF_VAL}" | sudo tee -a /etc/environment
# Remove any placeholder lines:
sudo sed -i '/HF_TOKEN=hf_YOUR_TOKEN_HERE/d' /etc/environment

# 3. Move export lines to TOP of ~/.bashrc (above the 'case $- in' block)
# Open editor and move these lines before the interactive guard:
micro ~/.bashrc
# Move to top:
# export HF_TOKEN="hf_oauth_..."
# export VLLM_API_KEY="none"
# export CUDA_HOME=/usr/local/cuda
# export PATH=/usr/local/cuda/bin:$PATH
# export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Verify
source ~/.bashrc
echo $HF_TOKEN
cat ~/.cache/huggingface/token
```

---

## 2. SSH Tunnel — Web UI from Windows

> ⚠️ **Common mistake:** The SSH tunnel command must be run **FROM WINDOWS**, not from the Jetson. Running it from the Jetson connects to itself and fails with "Permission denied (publickey)".

### From Windows PowerShell (correct)

```powershell
# Open a PowerShell window on your Windows 11 machine
# Keep this window open while using the Web UI
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
# Enter your Jetson password when prompted
```

If you prefer key-based auth (no password):

```powershell
# On Windows — generate key if you don't have one
ssh-keygen -t ed25519 -C "windows-openclaw"

# Copy public key to Jetson
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh jetson@192.168.1.100 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Now the tunnel works without password
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

### Open the Web UI

After the tunnel is established, open in any Windows browser:

```
http://localhost:18789/#token=YOUR_GATEWAY_TOKEN
```

Get your token:
```bash
# On Jetson:
openclaw config get gateway.auth.token
```

### Alternative — NoMachine (already installed)

If NoMachine is configured on the Jetson, open a browser inside the NoMachine session:

```
http://127.0.0.1:18789/#token=YOUR_GATEWAY_TOKEN
```

---

## 3. Power & Electricity Management

The Jetson AGX Orin has four power modes. **Only one LLM runs at a time**, so power mode selection determines which model is practical and what it costs.

### Power modes

```bash
# Check current mode
sudo nvpmodel -q

# Set mode (takes effect immediately, no reboot)
sudo nvpmodel -m 0   # MAXN — 50W, all 12 CPU cores, max GPU clock
sudo nvpmodel -m 1   # 15W  — 4 CPU cores, lowest consumption
sudo nvpmodel -m 2   # 30W  — 8 CPU cores
sudo nvpmodel -m 3   # 50W  — 12 CPU cores (alias for MAXN on some builds)

# Boost clocks after setting mode (recommended for inference)
sudo jetson_clocks

# Reset clocks to default (lower noise, lower power after inference done)
sudo jetson_clocks --restore
```

### Recommended mode per model

| Model | Recommended Mode | Typical Power | Est. Monthly Cost (24/7) |
|---|---|---|---|
| Gemma 4 E2B (vLLM/llama.cpp) | MODE_30W | ~25W avg | ~$1.80/month |
| Nemotron3 Nano 30B-A3B (vLLM) | MAXN | ~45W avg | ~$3.25/month |
| Nemotron 3 Nano Omni (llama.cpp) | MAXN | ~45W avg | ~$3.25/month |
| Idle (no LLM) | MODE_15W | ~8W avg | ~$0.58/month |

> Assumes $0.10/kWh. Adjust for your Colombian electricity rate (~$0.07/kWh → multiply by 0.7).

### Power management aliases

Add to `~/.bashrc`:

```bash
# Power management shortcuts
alias pwr-idle='sudo nvpmodel -m 1 && sudo jetson_clocks --restore && echo "MODE: 15W idle"'
alias pwr-light='sudo nvpmodel -m 2 && sudo jetson_clocks && echo "MODE: 30W light inference"'
alias pwr-full='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MODE: MAXN 50W full inference"'
alias pwr-status='sudo nvpmodel -q && tegrastats --interval 1000 &; sleep 3; kill %1 2>/dev/null'
```

### Auto power management script

```bash
cat > ~/scripts/auto-power.sh << 'EOF'
#!/bin/bash
# Set power based on which model is about to run
MODEL=$1
case $MODEL in
  gemma*|small*)
    sudo nvpmodel -m 2  # 30W enough for E2B
    sudo jetson_clocks
    echo "Power: 30W for $MODEL"
    ;;
  nemotron*|large*)
    sudo nvpmodel -m 0  # MAXN for 30B models
    sudo jetson_clocks
    echo "Power: MAXN for $MODEL"
    ;;
  idle|stop)
    sudo nvpmodel -m 1  # 15W idle
    sudo jetson_clocks --restore
    echo "Power: 15W idle"
    ;;
esac
EOF
chmod +x ~/scripts/auto-power.sh
```

---

## 4. Memory Management Strategy

The Jetson AGX Orin 64GB has **unified memory** — GPU and CPU share the same 64GB pool. This is both a strength and a risk: you can run bigger models than a discrete GPU allows, but OOM crashes freeze the entire system with no recovery.

### Memory budget per model

```
Total unified RAM: 64 GB
OS + system daemons: ~3 GB
OpenClaw gateway: ~0.5 GB
Available for inference: ~60.5 GB

Model memory requirements:
├── Gemma 4 E2B (bfloat16):          ~10 GB model + ~5 GB KV cache = 15 GB total
├── Gemma 4 E2B (GGUF Q4_K_S):       ~2.5 GB model + ~1 GB KV cache = 3.5 GB total
├── Nemotron3 30B-A3B (AWQ W4A16):   ~18 GB model + ~8 GB KV cache = 26 GB total
└── Nemotron3 30B Omni (GGUF Q4_K_M): ~20 GB model + ~4 GB KV cache = 24 GB total

NEVER run two models simultaneously — they will OOM and hard-freeze the Jetson.
```

### The Golden Rule: one model at a time

```bash
# ALWAYS stop the current model before starting another
docker stop vllm-openclaw 2>/dev/null
docker rm vllm-openclaw 2>/dev/null
sleep 5  # wait for unified memory to fully release

# Verify memory is free before starting new model
free -h
# 'available' should show 55GB+ before starting any LLM
```

### Memory pressure prevention

```bash
# Drop page cache before starting a large model
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
free -h  # re-check

# Monitor during inference
watch -n 5 'free -h && echo "---" && tegrastats 2>/dev/null | head -1'
```

### OOM killer protection

```bash
# Add to /etc/sysctl.d/99-jetson-oom.conf
sudo tee /etc/sysctl.d/99-jetson-oom.conf << 'EOF'
# Prevent OOM from freezing the system — prefer killing processes over kernel panic
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1
# Reduce swappiness (no swap on Jetson typically)
vm.swappiness = 1
# Drop caches more aggressively
vm.vfs_cache_pressure = 200
EOF
sudo sysctl -p /etc/sysctl.d/99-jetson-oom.conf
```

### GPU memory utilization guidelines

| Model size | Max `--gpu-memory-utilization` | Why |
|---|---|---|
| < 5GB | 0.30 | Leave room for OS and KV cache growth |
| 5–20GB | 0.50–0.60 | Safe headroom for long conversations |
| 20–40GB | 0.70–0.75 | Tight but stable with monitoring |
| > 40GB | 0.80 | Requires MAXN + all other processes stopped |

---

## 5. Model Selection Guide

### Performance comparison (AGX Orin 64GB · JP 7.2)

| Model | Engine | Tok/s | VRAM | Modalities | Context | Best For |
|---|---|---|---|---|---|---|
| **Gemma 4 E2B** | vLLM | ~32 | 15 GB | Text + Image + Audio | 128K | Default agent · fast replies |
| **Gemma 4 E2B** | llama.cpp | ~35 | 3.5 GB | Text + Image | 128K | Low-power mode · more RAM for other tasks |
| **Nemotron3 30B-A3B** | vLLM | ~35–40 | 26 GB | Text | 256K | Long docs · reasoning · code |
| **Nemotron3 Nano Omni** | llama.cpp | ~39 | 24 GB | Text + Image + Audio + Video | 256K | Conference → notes · PDF → podcast · multimodal |

### Decision tree for your use cases

```
What task?
│
├── Quick WhatsApp reply, casual chat, image description
│   └── Gemma 4 E2B via vLLM (Backend A) — fastest startup, best tool calling
│
├── Low power / overnight / idle watchdog
│   └── Gemma 4 E2B via llama.cpp (Backend B) — 3.5 GB RAM, runs at 30W
│
├── Long PDF processing (100MB+), complex reasoning, 300-page docs
│   └── Nemotron3 30B-A3B via vLLM (Backend C) — 256K context, strong reasoning
│
├── Audio transcription, video → notes, conference recordings
│   └── Nemotron3 Nano Omni via llama.cpp (Backend D) — true multimodal
│
└── Tourism content, podcast scripts, presentations from recordings
    └── Nemotron3 Nano Omni via llama.cpp (Backend D) — audio/video input native
```

---

## 6. Inference Backend A — Gemma 4 E2B via vLLM (Default)

**Status:** ✅ Verified working · ~32 tok/s · 15 GB RAM · 128K context

### When to use
- Default OpenClaw agent backend
- WhatsApp conversations with image understanding
- Tool calling and web search integration
- Moderate document processing (<100 pages)

### Start server

```bash
# Set power mode
sudo nvpmodel -m 2  # 30W sufficient for E2B
sudo jetson_clocks

# Free memory
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Stop any running model
docker rm -f vllm-openclaw 2>/dev/null
sleep 5

# Start Gemma 4 E2B via vLLM
docker run --runtime nvidia -d \
  --name vllm-openclaw \
  --restart unless-stopped \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve google/gemma-4-E2B-it \
      --dtype bfloat16 \
      --max-model-len 65536 \
      --gpu-memory-utilization 0.55 \
      --enable-auto-tool-choice \
      --tool-call-parser gemma4 \
      --reasoning-parser gemma4 \
      --host 0.0.0.0 \
      --port 8000"

# Wait for startup
echo "Waiting for vLLM..."
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  sleep 15; echo "  Loading..."
done
echo "✅ Gemma 4 E2B via vLLM ready"
```

### Verify

```bash
curl -s http://localhost:8000/v1/models | python3 -c \
  "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
# Expected: google/gemma-4-E2B-it

curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemma-4-E2B-it","messages":[{"role":"user","content":"Hello, say hi in one word"}]}'
```

### OpenClaw config for this backend

```json
"model": { "primary": "vllm/google/gemma-4-E2B-it" },
"models": { "vllm/google/gemma-4-E2B-it": {} }
```
```json
"models": { "providers": { "vllm": {
  "baseUrl": "http://127.0.0.1:8000/v1",
  "api": "openai-completions",
  "apiKey": "vllm-local",
  "models": [{ "id": "google/gemma-4-E2B-it", "contextWindow": 65536, "maxTokens": 4096, "input": ["text", "image"] }]
}}}
```

---

## 7. Inference Backend B — Gemma 4 E2B via llama.cpp

**Expected:** ~35 tok/s · 3.5 GB RAM (Q4_K_S) · OpenAI-compatible API on port 8080

### When to use
- Low-power overnight operation (30W mode)
- When you need maximum RAM headroom for other tasks
- Faster startup time than vLLM (~20 sec vs ~3 min)
- When you don't need vLLM's advanced batching

### Start server

```bash
# Set power mode
sudo nvpmodel -m 2  # 30W — E2B is efficient enough
sudo jetson_clocks

# Free memory
docker rm -f vllm-openclaw llama-openclaw 2>/dev/null
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sleep 3

# Start Gemma 4 E2B via llama.cpp
docker run --runtime nvidia -d \
  --name llama-openclaw \
  --restart unless-stopped \
  --network host \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_S \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias gemma-4-e2b \
    --host 0.0.0.0

# Wait for startup (faster than vLLM)
echo "Waiting for llama.cpp..."
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  sleep 5; echo "  Loading..."
done
echo "✅ Gemma 4 E2B via llama.cpp ready"
```

### Verify

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-e2b",
    "messages": [{"role": "user", "content": "Hello, say hi in one word"}]
  }'
```

### OpenClaw config for this backend

> Note: llama.cpp runs on port 8080, not 8000. Update OpenClaw config accordingly.

```json
"models": { "providers": { "vllm": {
  "baseUrl": "http://127.0.0.1:8080/v1",
  "api": "openai-completions",
  "apiKey": "vllm-local",
  "models": [{ "id": "gemma-4-e2b", "contextWindow": 32768, "maxTokens": 4096, "input": ["text"] }]
}}}
```

---

## 8. Inference Backend C — Nemotron3 Nano 30B-A3B via vLLM

**Expected:** ~35–40 tok/s · 26 GB RAM · 256K context · Text only · Strong reasoning

### When to use
- Processing very long PDFs (100MB+, 300+ pages)
- Complex reasoning tasks: itinerary planning, research synthesis
- Long conversation history (256K context = full book in memory)
- Code generation, technical writing

### Architecture note
- 30B total parameters, only **3.5B active per forward pass** (MoE)
- Uses AWQ W4A16 quantization for Orin (no HF auth required)
- Hybrid Mamba-2 + MoE + Attention architecture
- Configurable reasoning traces (`enable_thinking`)

### Start server

```bash
# Set power mode — 30B model needs full power
sudo nvpmodel -m 0  # MAXN
sudo jetson_clocks

# Free memory — critical before 30B model
docker rm -f vllm-openclaw llama-openclaw 2>/dev/null
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sleep 10
free -h  # verify 55GB+ available

# Start Nemotron3 Nano 30B-A3B via vLLM
# Uses community AWQ checkpoint (no HF auth required for Orin)
docker run --runtime nvidia -d \
  --name vllm-openclaw \
  --restart unless-stopped \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ \
      --gpu-memory-utilization 0.80 \
      --trust-remote-code \
      --max-model-len 32768 \
      --enable-auto-tool-choice \
      --tool-call-parser hermes \
      --host 0.0.0.0 \
      --port 8000"

# Wait — this model takes ~8-12 min on first run (downloads + loads)
echo "Waiting for Nemotron3 30B (this takes ~10 min first run)..."
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  sleep 30; echo "  Still loading... $(docker logs vllm-openclaw 2>&1 | tail -1)"
done
echo "✅ Nemotron3 30B-A3B via vLLM ready"
```

### Reasoning control

```bash
# With reasoning (slower, higher quality — for complex tasks)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ",
    "messages": [{"role": "user", "content": "Plan a 7-day Colombia tour itinerary"}],
    "extra_body": {"chat_template_kwargs": {"enable_thinking": true}}
  }'

# Without reasoning (faster, lower TTFT — for quick responses)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ",
    "messages": [{"role": "user", "content": "What is the capital of Colombia?"}],
    "extra_body": {"chat_template_kwargs": {"enable_thinking": false}},
    "max_tokens": 50
  }'
```

### To disable reasoning by default (add to vllm serve command)

```bash
# Add this flag to the docker run command above:
--default-chat-template-kwargs '{"enable_thinking": false}'
```

### OpenClaw config for this backend

```json
"model": { "primary": "vllm/stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ" },
"models": { "vllm/stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ": {} }
```
```json
"models": { "providers": { "vllm": {
  "baseUrl": "http://127.0.0.1:8000/v1",
  "api": "openai-completions",
  "apiKey": "vllm-local",
  "timeoutSeconds": 300,
  "models": [{
    "id": "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ",
    "name": "Nemotron3 30B (local)",
    "contextWindow": 32768,
    "maxTokens": 8192,
    "reasoning": true,
    "input": ["text"]
  }]
}}}
```

---

## 9. Inference Backend D — Nemotron 3 Nano Omni via llama.cpp

**Expected:** ~39 tok/s · 24 GB RAM · 256K context · Text + Image + Audio + Video

### When to use
- Conference recording → structured notes
- Audio voice messages → transcription and summary
- Video clips → text description and analysis
- PDF with embedded images → comprehensive analysis
- Podcast script generation from audio content

### Architecture note
- 30B total / 3B active MoE
- True multimodal: processes text, image, audio, and video natively
- GGUF Q4_K_M: good quality/size tradeoff for Orin

### Start server

```bash
# Set power mode
sudo nvpmodel -m 0  # MAXN — Omni needs it for multimodal processing
sudo jetson_clocks

# Free memory
docker rm -f vllm-openclaw llama-openclaw 2>/dev/null
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sleep 10
free -h  # verify 55GB+ available

# Start Nemotron 3 Nano Omni via llama.cpp
docker run --runtime nvidia -d \
  --name llama-openclaw \
  --restart unless-stopped \
  --network host \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
    --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
    --ctx-size 8192 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias nemotron-omni \
    --host 0.0.0.0

# Wait for startup
echo "Waiting for Nemotron Omni..."
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  sleep 20; echo "  Loading..."
done
echo "✅ Nemotron 3 Nano Omni via llama.cpp ready"
```

### Verify with reasoning enabled

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nemotron-omni",
    "messages": [{"role": "user", "content": "Summarize this in 3 bullet points: AI agents are transforming how we work."}],
    "max_tokens": 256,
    "chat_template_kwargs": {"enable_thinking": true}
  }'
```

### OpenClaw config for this backend

> Note: llama.cpp on port 8080.

```json
"model": { "primary": "vllm/nemotron-omni" },
"models": { "vllm/nemotron-omni": {} }
```
```json
"models": { "providers": { "vllm": {
  "baseUrl": "http://127.0.0.1:8080/v1",
  "api": "openai-completions",
  "apiKey": "vllm-local",
  "timeoutSeconds": 300,
  "models": [{
    "id": "nemotron-omni",
    "name": "Nemotron Omni (local)",
    "contextWindow": 8192,
    "maxTokens": 4096,
    "reasoning": true,
    "input": ["text", "image", "audio"]
  }]
}}}
```

---

## 10. Model Switcher Scripts

These scripts handle the full lifecycle: stop old model, free memory, set power, start new model, update OpenClaw config, restart gateway.

### Setup

```bash
mkdir -p ~/scripts
```

### Main switcher

```bash
cat > ~/scripts/switch-model.sh << 'SWITCHER'
#!/bin/bash
set -e

MODEL=${1:-help}
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"

print_usage() {
  echo ""
  echo "Usage: switch-model.sh <model>"
  echo ""
  echo "Available models:"
  echo "  gemma-vllm    — Gemma 4 E2B via vLLM   (port 8000, 30W, ~32 tok/s)"
  echo "  gemma-llama   — Gemma 4 E2B via llama   (port 8080, 30W, ~35 tok/s)"
  echo "  nemotron-text — Nemotron3 30B-A3B vLLM  (port 8000, MAXN, ~38 tok/s)"
  echo "  nemotron-omni — Nemotron Omni llama.cpp  (port 8080, MAXN, ~39 tok/s)"
  echo "  stop          — Stop all LLMs, idle power"
  echo ""
}

stop_all_models() {
  echo "→ Stopping all LLM containers..."
  docker stop vllm-openclaw llama-openclaw 2>/dev/null || true
  docker rm vllm-openclaw llama-openclaw 2>/dev/null || true
  sleep 5
  sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
  sleep 3
  FREE=$(free -g | awk '/^Mem:/{print $7}')
  echo "→ Free memory: ${FREE}GB"
  if [ "$FREE" -lt 50 ]; then
    echo "⚠️  Low memory after stop. Wait 30s and retry."
    sleep 30
  fi
}

wait_for_port() {
  PORT=$1
  echo -n "→ Waiting for port $PORT"
  for i in $(seq 1 60); do
    if curl -s http://localhost:${PORT}/v1/models > /dev/null 2>&1; then
      echo " ✅"
      return 0
    fi
    echo -n "."
    sleep 15
  done
  echo " ❌ Timeout"
  return 1
}

update_openclaw() {
  MODEL_ID=$1
  BASE_URL=$2
  CONTEXT=$3
  MAX_TOKENS=$4
  INPUT=$5

  python3 - << PYEOF
import json, sys

with open('$OPENCLAW_CONFIG') as f:
    config = json.load(f)

# Update primary model
config.setdefault('agents', {}).setdefault('defaults', {})
config['agents']['defaults']['model'] = {'primary': 'vllm/${MODEL_ID}'}
config['agents']['defaults']['models'] = {'vllm/${MODEL_ID}': {}}

# Update provider
config.setdefault('models', {}).setdefault('providers', {})
config['models']['providers']['vllm'] = {
    'baseUrl': '${BASE_URL}',
    'api': 'openai-completions',
    'apiKey': 'vllm-local',
    'timeoutSeconds': 300,
    'models': [{
        'id': '${MODEL_ID}',
        'name': '${MODEL_ID}',
        'reasoning': False,
        'input': ${INPUT},
        'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
        'contextWindow': ${CONTEXT},
        'maxTokens': ${MAX_TOKENS}
    }]
}

with open('$OPENCLAW_CONFIG', 'w') as f:
    json.dump(config, f, indent=2)
print('✅ OpenClaw config updated')
PYEOF
}

case $MODEL in
  gemma-vllm)
    echo "=== Switching to Gemma 4 E2B via vLLM ==="
    stop_all_models
    sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name vllm-openclaw --restart unless-stopped \
      --network host --ipc host --shm-size 8g \
      -e NVIDIA_VISIBLE_DEVICES=all \
      -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve google/gemma-4-E2B-it \
          --dtype bfloat16 --max-model-len 65536 \
          --gpu-memory-utilization 0.55 \
          --enable-auto-tool-choice --tool-call-parser gemma4 \
          --host 0.0.0.0 --port 8000"
    wait_for_port 8000
    update_openclaw "google/gemma-4-E2B-it" "http://127.0.0.1:8000/v1" 65536 4096 '["text","image"]'
    openclaw gateway restart
    echo "✅ Done — Gemma 4 E2B via vLLM active"
    ;;

  gemma-llama)
    echo "=== Switching to Gemma 4 E2B via llama.cpp ==="
    stop_all_models
    sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name llama-openclaw --restart unless-stopped \
      --network host \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server \
        -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_S \
        --ctx-size 32768 --n-gpu-layers 999 \
        --port 8080 --alias gemma-4-e2b --host 0.0.0.0
    wait_for_port 8080
    update_openclaw "gemma-4-e2b" "http://127.0.0.1:8080/v1" 32768 4096 '["text"]'
    openclaw gateway restart
    echo "✅ Done — Gemma 4 E2B via llama.cpp active"
    ;;

  nemotron-text)
    echo "=== Switching to Nemotron3 30B-A3B via vLLM ==="
    stop_all_models
    sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name vllm-openclaw --restart unless-stopped \
      --network host --ipc host --shm-size 8g \
      -e NVIDIA_VISIBLE_DEVICES=all \
      -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ \
          --gpu-memory-utilization 0.80 \
          --trust-remote-code --max-model-len 32768 \
          --enable-auto-tool-choice --tool-call-parser hermes \
          --host 0.0.0.0 --port 8000"
    wait_for_port 8000
    update_openclaw "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ" "http://127.0.0.1:8000/v1" 32768 8192 '["text"]'
    openclaw gateway restart
    echo "✅ Done — Nemotron3 30B-A3B via vLLM active"
    ;;

  nemotron-omni)
    echo "=== Switching to Nemotron 3 Nano Omni via llama.cpp ==="
    stop_all_models
    sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name llama-openclaw --restart unless-stopped \
      --network host \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server \
        --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
        --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
        --ctx-size 8192 --n-gpu-layers 999 \
        --port 8080 --alias nemotron-omni --host 0.0.0.0
    wait_for_port 8080
    update_openclaw "nemotron-omni" "http://127.0.0.1:8080/v1" 8192 4096 '["text","image","audio"]'
    openclaw gateway restart
    echo "✅ Done — Nemotron Omni via llama.cpp active"
    ;;

  stop)
    stop_all_models
    sudo nvpmodel -m 1 && sudo jetson_clocks --restore
    echo "✅ All models stopped — idle 15W mode"
    ;;

  *)
    print_usage
    ;;
esac
SWITCHER
chmod +x ~/scripts/switch-model.sh
```

### Add aliases

```bash
echo '' >> ~/.bashrc
echo '# Model switcher' >> ~/.bashrc
echo 'alias model-gemma-fast="~/scripts/switch-model.sh gemma-vllm"' >> ~/.bashrc
echo 'alias model-gemma-lite="~/scripts/switch-model.sh gemma-llama"' >> ~/.bashrc
echo 'alias model-nemotron="~/scripts/switch-model.sh nemotron-text"' >> ~/.bashrc
echo 'alias model-omni="~/scripts/switch-model.sh nemotron-omni"' >> ~/.bashrc
echo 'alias model-stop="~/scripts/switch-model.sh stop"' >> ~/.bashrc
echo 'alias model-status="docker ps | grep -E \"vllm|llama\" && curl -s http://localhost:8000/v1/models 2>/dev/null || curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -m json.tool"' >> ~/.bashrc
source ~/.bashrc
```

### Usage

```bash
model-gemma-fast    # Gemma 4 E2B via vLLM — daily agent
model-gemma-lite    # Gemma 4 E2B via llama.cpp — low power
model-nemotron      # Nemotron3 30B — long docs
model-omni          # Nemotron Omni — audio/video/multimodal
model-stop          # Stop everything, idle mode
model-status        # Check what's running
```

---

## 11. OpenClaw Installation

```bash
# Install via official installer (recommended — handles Node version check)
curl -fsSL https://openclaw.ai/install.sh | bash

# Verify
openclaw --version   # 2026.6.10+
node --version       # v22.23.1+

# If openclaw not found after install:
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.bashrc
```

---

## 12. OpenClaw Configuration

### Full production config

```bash
cat > ~/.openclaw/openclaw.json << 'EOF'
{
  "agents": {
    "defaults": {
      "workspace": "/home/jetson/.openclaw/workspace",
      "models": {
        "vllm/google/gemma-4-E2B-it": {}
      },
      "model": {
        "primary": "vllm/google/gemma-4-E2B-it"
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
      "token": "GENERATE_WITH: openclaw doctor --generate-gateway-token"
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
        "config": { "webSearch": { "apiKey": "YOUR_BRAVE_API_KEY" } },
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
            "id": "google/gemma-4-E2B-it",
            "name": "Gemma 4 E2B (local)",
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

python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null && echo "JSON OK"
```

### Generate a proper gateway token

```bash
openclaw doctor --generate-gateway-token
# Copy the output and replace the placeholder in openclaw.json
```

### Start gateway and onboard

```bash
openclaw gateway restart
sleep 5
openclaw onboard
# During onboarding wizard:
# Channel: WhatsApp
# dmPolicy: Pairing (recommended)
# Search: Brave Search
# Hooks: enable all 5
# Gateway service: Install (systemd)
# Hatch: Browser
```

---

## 13. WhatsApp Channel Setup

### Link your phone

```bash
# Run onboarding which shows QR code
openclaw onboard

# Or re-link manually:
openclaw channels auth login whatsapp
# Open WhatsApp → Settings → Linked Devices → Link a Device → Scan QR
```

### Approve yourself

After scanning QR and sending a message from your phone:

```bash
openclaw pairing list whatsapp
# Shows pending code

openclaw pairing approve whatsapp YOUR_PAIRING_CODE
# Output: "Approved whatsapp sender +57XXXXXXXXXX"
# Output: "Command owner configured whatsapp:+57XXXXXXXXXX"
```

### Verify

```bash
openclaw channels status --probe
# Expected: WhatsApp default: enabled, configured, linked, running, connected
```

### Important: tool profile must be "full"

The `coding` tool profile removes `message` and `whatsapp_login` tools, silently preventing WhatsApp replies. Always use `full` or `messaging` for WhatsApp-enabled agents.

```json
"tools": { "profile": "full" }
```

---

## 14. Production Stability & OOM Prevention

### Watchdog service

```bash
cat > ~/scripts/watchdog.sh << 'EOF'
#!/bin/bash
# Watchdog: monitors memory and restarts inference if something goes wrong

LOG="$HOME/.openclaw/watchdog.log"
THRESHOLD_GB=8  # alert if less than 8GB free

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

while true; do
  FREE_GB=$(free -g | awk '/^Mem:/{print $7}')

  if [ "$FREE_GB" -lt "$THRESHOLD_GB" ]; then
    log "⚠️  LOW MEMORY: ${FREE_GB}GB free — dropping caches"
    sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
    sleep 10
    FREE_GB=$(free -g | awk '/^Mem:/{print $7}')
    log "After cache drop: ${FREE_GB}GB free"

    if [ "$FREE_GB" -lt 5 ]; then
      log "❌ CRITICAL: ${FREE_GB}GB — stopping inference containers"
      docker stop vllm-openclaw llama-openclaw 2>/dev/null
      sleep 30
      log "Containers stopped. Manual restart required."
      # Send WhatsApp alert via openclaw if gateway is still up
      openclaw run "System alert: inference container stopped due to OOM. Memory was ${FREE_GB}GB." 2>/dev/null || true
    fi
  fi

  sleep 60
done
EOF
chmod +x ~/scripts/watchdog.sh
```

### Docker container health check

```bash
# Add to docker run command for automatic restart on crash:
# --restart unless-stopped (already included in all commands above)
# --memory-swap -1 (allow using all unified memory, no artificial cap)

# Check container health
docker inspect vllm-openclaw | python3 -c \
  "import sys,json; c=json.load(sys.stdin)[0]; print('Status:', c['State']['Status'])"
```

### Systemd service for vLLM (optional — alternative to docker --restart)

```bash
cat > ~/.config/systemd/user/vllm-gemma.service << 'EOF'
[Unit]
Description=vLLM Gemma 4 E2B inference server
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
RemainAfterExit=no
ExecStartPre=-/usr/bin/docker rm -f vllm-openclaw
ExecStartPre=/bin/sh -c 'sync && echo 3 > /proc/sys/vm/drop_caches'
ExecStart=/usr/bin/docker run --runtime nvidia \
  --name vllm-openclaw \
  --network host --ipc host --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  -v /home/jetson/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve google/gemma-4-E2B-it \
      --dtype bfloat16 --max-model-len 65536 \
      --gpu-memory-utilization 0.55 \
      --enable-auto-tool-choice --tool-call-parser gemma4 \
      --host 0.0.0.0 --port 8000"
ExecStop=/usr/bin/docker stop vllm-openclaw
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable vllm-gemma.service
systemctl --user start vllm-gemma.service
```

### Memory monitoring dashboard

```bash
# Real-time monitoring (useful during heavy tasks)
watch -n 3 '
echo "=== $(date) ==="
free -h | grep Mem
echo ""
echo "Docker containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "vllm|llama|openclaw"
echo ""
echo "vLLM status:"
curl -s http://localhost:8000/health 2>/dev/null && echo "vLLM:8000 OK" || \
  curl -s http://localhost:8080/health 2>/dev/null && echo "llama:8080 OK" || echo "No inference server"
'
```

---

## 15. Use Case Workflows

### Workflow 1 — Tourism Agency Automation

**Model:** Gemma 4 E2B (vLLM) for speed, Nemotron3 30B for complex itineraries

**WhatsApp trigger:** Client sends message → agent replies with tour info, prices, availability

**Setup agent instructions in BOOTSTRAP.md:**

```bash
cat > ~/.openclaw/workspace/BOOTSTRAP.md << 'EOF'
# Tourism Agency Agent

You are an AI agent for [Agency Name], a tourism company in Colombia. You help clients:
- Discover and plan tours in Colombia (Cartagena, Medellín, Bogotá, coffee region, Amazon)
- Provide detailed itineraries with day-by-day breakdown
- Quote prices and packages
- Handle reservations and inquiries
- Respond in the client's language (Spanish or English)

## Response style
- Warm, professional, enthusiastic about Colombia
- Always include practical details: departure times, meeting points, what to bring
- For complex itineraries, use numbered lists with clear headings
- Suggest 3 options when asked for recommendations (budget/mid/premium)

## Current packages
[Add your packages, prices, and availability here]
EOF
```

### Workflow 2 — Podcast from PDF (100MB+ documents)

**Model:** Nemotron3 30B-A3B (vLLM) — 256K context, handles full books

**Step 1 — Switch to long-context model:**
```bash
model-nemotron
```

**Step 2 — Send PDF via WhatsApp or web UI, then prompt:**
```
Convert this document into a podcast script. Format:
- Opening hook (30 seconds)
- 5 main segments with natural dialogue between 2 hosts
- Each segment: key insight, example, listener takeaway
- Closing with action items
Language: [Spanish/English]
Tone: Conversational, educational, engaging
```

**Step 3 — Generate audio (future integration):**
```bash
# Once script is generated, use a TTS skill or external service
# The agent can use the openai-whisper-api skill for speech generation
```

### Workflow 3 — Conference/Class Recording → Notes & Presentations

**Model:** Nemotron 3 Nano Omni (llama.cpp) — native audio input

**Switch to multimodal model:**
```bash
model-omni
```

**Send audio file via WhatsApp with prompt:**
```
Transcribe and structure this recording into:
1. Executive summary (5 bullet points)
2. Key decisions made
3. Action items with owners and deadlines
4. Full transcript with speaker turns
Format for easy copy-paste into Notion/Obsidian
```

**For video recordings:**
```
Convert this class recording to study notes:
1. Topic outline with timestamps
2. Key concepts explained simply
3. Examples and case studies mentioned
4. Questions to review
5. Recommended follow-up resources
```

### Workflow 4 — Client Service Automation

**Model:** Gemma 4 E2B (vLLM) — fast responses, WhatsApp native

**WhatsApp DM policy:** Set to `pairing` for selective access, or `open` with `dmAllowFrom` allowlist for known clients

```bash
# Allowlist specific client numbers
openclaw config set channels.whatsapp.dmAllowFrom '["+573XXXXXXXXX","+573XXXXXXXXY"]'
openclaw config set channels.whatsapp.dmPolicy allowlist
openclaw gateway restart
```

**Agent instructions for client service:**

```bash
cat > ~/.openclaw/workspace/BOOTSTRAP.md << 'EOF'
# Client Service Agent

You are a professional customer service agent. When clients message:
1. Greet them by name if known from context
2. Identify their need within the first response
3. Provide complete answers — do not ask clarifying questions unless truly needed
4. Always end with a clear next step or offer to help further

## Escalation
If you cannot resolve: "I'll connect you with our team directly. Please expect a response within 2 hours."

## Response time
This is an automated first response. Aim for answers under 150 words for WhatsApp.
EOF
```

### Workflow 5 — Content Generation

**Model:** Nemotron3 30B-A3B (vLLM) for quality, Gemma 4 E2B for speed

**Via WhatsApp:**
```
Create a week's worth of Instagram content for a Colombian tourism agency:
- Monday: Inspirational destination photo caption
- Tuesday: Travel tip
- Wednesday: Behind-the-scenes story
- Thursday: Client testimonial format
- Friday: Weekend getaway promotion
- Saturday: Cultural highlight
- Sunday: Motivational travel quote

Include hashtags in Spanish and English for each post.
```

---

## 16. Startup & Reboot Recovery

After every reboot, the following sequence is needed:

### Manual recovery sequence

```bash
# 1. Source environment
source ~/.bashrc

# 2. Set power mode
sudo nvpmodel -m 2  # or 0 for large models

# 3. Start preferred model (choose one)
model-gemma-fast     # most common choice

# 4. Verify model
curl -s http://localhost:8000/v1/models | python3 -c \
  "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"

# 5. OpenClaw restarts automatically (systemd service)
openclaw gateway status

# 6. Verify WhatsApp
openclaw channels status --probe
```

### Auto-start script

```bash
cat > ~/scripts/startup.sh << 'EOF'
#!/bin/bash
# Run after reboot to restore full stack

echo "=== Jetson AI Stack Startup ==="

# Source environment
source ~/.bashrc

# Drop caches from boot
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Set power mode (default: 30W for Gemma E2B)
sudo nvpmodel -m 2
sudo jetson_clocks

# Wait for Docker
until docker info > /dev/null 2>&1; do
  echo "Waiting for Docker..."
  sleep 5
done

# Start default model
echo "Starting Gemma 4 E2B..."
docker run --runtime nvidia -d \
  --name vllm-openclaw --restart unless-stopped \
  --network host --ipc host --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve google/gemma-4-E2B-it \
      --dtype bfloat16 --max-model-len 65536 \
      --gpu-memory-utilization 0.55 \
      --enable-auto-tool-choice --tool-call-parser gemma4 \
      --host 0.0.0.0 --port 8000"

# Wait for model
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo "Waiting for vLLM..."
  sleep 20
done

echo "✅ vLLM ready"
echo "✅ OpenClaw: $(systemctl --user is-active openclaw-gateway.service)"
echo "=== Stack ready ==="
EOF
chmod +x ~/scripts/startup.sh
```

### Systemd startup trigger (optional — auto-runs after reboot)

```bash
cat > ~/.config/systemd/user/jetson-ai-startup.service << 'EOF'
[Unit]
Description=Jetson AI Stack Startup
After=network-online.target docker.service openclaw-gateway.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/home/jetson/scripts/startup.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable jetson-ai-startup.service
```

---

## 17. Quick Reference

### Commands summary

```bash
# Model switching
model-gemma-fast      # Gemma 4 E2B via vLLM   (port 8000)
model-gemma-lite      # Gemma 4 E2B via llama   (port 8080)
model-nemotron        # Nemotron3 30B-A3B vLLM  (port 8000)
model-omni            # Nemotron Omni llama.cpp  (port 8080)
model-stop            # Stop all, idle power
model-status          # Check what's running

# Power modes
pwr-idle              # 15W — no inference running
pwr-light             # 30W — for Gemma E2B
pwr-full              # MAXN — for 30B models

# OpenClaw
openclaw gateway status
openclaw gateway restart
openclaw channels status --probe
openclaw logs --follow
openclaw doctor
openclaw tui

# Memory
free -h
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
docker stats --no-stream

# SSH tunnel (run on Windows, not Jetson)
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

### Ports

| Service | Port | Notes |
|---|---|---|
| vLLM | 8000 | OpenAI-compatible API |
| llama.cpp | 8080 | OpenAI-compatible API |
| OpenClaw Gateway | 18789 | Web UI + WS |
| SSH | 22 | Key-based auth |
| NoMachine | 4000 | Virtual desktop |
| XRDP | 3389 | Windows RDP |

### Model quick reference

| Command | Model | Engine | Power | RAM | Tok/s | Input |
|---|---|---|---|---|---|---|
| `model-gemma-fast` | Gemma 4 E2B | vLLM | 30W | 15GB | ~32 | Text+Image |
| `model-gemma-lite` | Gemma 4 E2B | llama.cpp | 30W | 3.5GB | ~35 | Text |
| `model-nemotron` | Nemotron3 30B-A3B | vLLM | MAXN | 26GB | ~38 | Text |
| `model-omni` | Nemotron Omni | llama.cpp | MAXN | 24GB | ~39 | Text+Image+Audio+Video |

### Web UI access (from Windows)

```powershell
# Terminal 1 — keep open
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100

# Browser
http://localhost:18789/#token=YOUR_TOKEN
```

---

*Guide version: 2026-06-28 · Verified on Jetson AGX Orin 64GB · JetPack 7.2 · OpenClaw 2026.6.10*
