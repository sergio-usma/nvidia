# NVIDIA Jetson AGX Orin 64GB — JetPack 7.2
# GUÍA DEFINITIVA: Agente IA de Producción

> **Hardware verificado:** Jetson AGX Orin 64GB · JetPack 7.2-b187 · L4T r39.2 · Ubuntu 24.04.4 LTS  
> **Objetivo:** Agente personal completamente automatizado via OpenClaw + WhatsApp  
> **Modo de trabajo:** Headless (sin monitor) · Acceso via SSH desde Windows 11  

---

## ⚡ TARJETA DE REFERENCIA RÁPIDA

```
IPs Y ACCESO
  Jetson:         192.168.1.100 (estática)
  Windows:        192.168.1.33
  SSH (Windows):  ssh jetson
  SSH (manual):   ssh jetson@192.168.1.100

PUERTOS ACTIVOS
  :22    → SSH
  :3389  → XRDP (mstsc)
  :4000  → NoMachine
  :11434 → Ollama API
  :8000  → vLLM (OpenAI-compatible)
  :8080  → llama.cpp (OpenAI-compatible)
  :3000  → Open WebUI
  :18789 → OpenClaw Gateway + Web UI

VENV LLM (activar antes de pip install o python con modelos)
  source ~/venvs/llm/bin/activate
  deactivate                          # para salir

OPENCLAW
  claw-status                         # estado del gateway y WhatsApp
  claw-restart                        # reiniciar gateway
  claw-logs                           # ver logs en tiempo real
  claw-tui                            # interfaz de terminal
  claw-wa                             # solo logs WhatsApp
  openclaw config get gateway.auth.token  # obtener token para Web UI

WEB UI OPENCLAW (ejecutar en Windows PowerShell, no en Jetson)
  ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
  → http://localhost:18789/#token=TU_TOKEN

MODELOS Y MODOS
  mode-openclaw     → Gemma 4 E2B / vLLM   · 30W · ~32 tok/s · :8000
  mode-lite         → Gemma 4 E2B / llama   · 30W · ~35 tok/s · :8080
  mode-longdoc      → Nemotron3 30B / vLLM  · MAXN · ~38 tok/s · :8000
  mode-multimodal   → Nemotron Omni / llama · MAXN · ~39 tok/s · :8080
  mode-ollama       → Ollama libre          · 30W
  mode-idle         → Todo apagado          · 15W
  model-status      → qué está activo ahora

RECURSOS
  jetson-audit      → auditoría completa de memoria y procesos
  jetson-clean      → limpiar todo (antes de workload pesado)
  jetson-mem        → memoria rápida

PODER
  pwr-idle          → 15W  (nada corriendo)
  pwr-30w           → 30W  (modelos pequeños)
  pwr-maxn          → MAXN (modelos 30B)
  pwr-status        → modo actual

TMUX (trabajo headless)
  tm                → sesión 'main'
  tm-llm            → sesión 'llm' (para modelos)
  Ctrl+A d          → detach (salir sin matar)
  Ctrl+A |          → split vertical
  Ctrl+A -          → split horizontal
```

---

## PARTE 1 — DIAGNÓSTICO INICIAL

Antes de ejecutar cualquier cosa, determina dónde estás.

### 1.1 Verificación del sistema (ejecutar via SSH desde Windows)

```bash
# ── Conectar al Jetson ────────────────────────────────────────────
# Desde Windows PowerShell:
ssh jetson
# Si no funciona con alias: ssh jetson@192.168.1.100

# ── Una vez conectado, ejecutar diagnóstico ───────────────────────
echo "=== DIAGNÓSTICO JETSON AGX ORIN ===" && \
echo "OS: $(lsb_release -d | cut -f2)" && \
echo "JetPack: $(dpkg -l | grep 'nvidia-jetpack ' | awk '{print $3}' 2>/dev/null || echo 'verificar manualmente')" && \
echo "CUDA: $(nvcc --version 2>/dev/null | grep release | awk '{print $5}' | tr -d ',' || echo 'nvcc no en PATH')" && \
echo "Python: $(python3 --version)" && \
echo "Node: $(node --version 2>/dev/null || echo 'no instalado')" && \
echo "Docker: $(docker --version 2>/dev/null | awk '{print $3}' | tr -d ',' || echo 'no instalado')" && \
echo "Ollama: $(ollama --version 2>/dev/null || echo 'no instalado')" && \
echo "OpenClaw: $(openclaw --version 2>/dev/null || echo 'no instalado')" && \
echo "hf CLI: $(hf --version 2>/dev/null || echo 'no instalado')" && \
echo "venv llm: $([ -d ~/venvs/llm ] && echo 'existe' || echo 'NO existe')" && \
echo "HF token: $([ -f ~/.cache/huggingface/token ] && echo 'cacheado ✅' || echo 'NO cacheado ❌')" && \
echo "IP: $(hostname -I | awk '{print $1}')" && \
echo "Memoria libre: $(free -h | awk '/^Mem:/{print $7}')" && \
echo "Modo poder: $(sudo nvpmodel -q 2>/dev/null | grep 'NV Power Mode' || echo 'N/A')"
```

### 1.2 Árbol de decisión — ¿qué hacer ahora?

```
¿Resultado del diagnóstico?
│
├── OpenClaw instalado + WhatsApp linked + modelo activo
│   → Ir directamente a PARTE 4.5 (uso cotidiano)
│   → O a PARTE 7 (casos de uso con prompts)
│
├── OpenClaw instalado pero NO configurado / sin WhatsApp
│   → Ir a PARTE 4.2 (verificar instalación existente)
│   → Luego PARTE 4.3 (configurar desde cero)
│
├── OpenClaw NO instalado, pero Docker/Ollama/venv SÍ
│   → Ir a PARTE 4.1 (instalar OpenClaw)
│   → Luego PARTE 4.3 (configurar)
│
└── Fresh install / sistema recién flasheado
    → Ir a PARTE 2 completa (base) → PARTE 3 → PARTE 4
    → Referencia: jetson-orin-jp72-fresh-start.md para pasos 0-19
```

---

## PARTE 2 — ENTORNO BASE

> ℹ️ Si tu sistema ya está completamente configurado (SSH funciona, Docker corre, Ollama responde), puedes saltar a **PARTE 3**. Esta sección es para quienes configuran desde cero o quieren entender el fundamento.

### 2.1 Acceso SSH desde Windows (la forma correcta)

**Todo el trabajo se hace via SSH desde Windows. El Jetson corre headless (sin monitor).**

```powershell
# ── En Windows PowerShell ─────────────────────────────────────────

# Opción 1: Si tienes el alias 'jetson' configurado en SSH config
ssh jetson

# Opción 2: Directo
ssh jetson@192.168.1.100

# Opción 3: Con tmux (recomendado para sesiones largas)
ssh jetson "tmux attach -t main 2>/dev/null || tmux new-session -s main"
```

Si SSH pide contraseña cada vez, configurar acceso por clave:

```powershell
# En Windows PowerShell — generar clave si no existe
ssh-keygen -t ed25519 -C "windows-jetson-$(Get-Date -Format 'yyyyMMdd')"

# Copiar clave al Jetson
type "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh jetson@192.168.1.100 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"

# Verificar
ssh jetson "echo OK sin contraseña"
```

### 2.2 tmux — sesiones persistentes para trabajo headless

Si una conexión SSH se cae, los procesos dentro de tmux siguen corriendo.

```bash
# ── Desde SSH en el Jetson ────────────────────────────────────────

# Crear sesiones base (solo la primera vez)
tmux new-session -d -s main   # sesión principal
tmux new-session -d -s llm    # sesión para modelos pesados

# Conectar a sesión
tmux attach -t main

# Comandos tmux (prefijo: Ctrl+A)
# Ctrl+A d       → detach (desconectar sin matar procesos)
# Ctrl+A |       → split vertical
# Ctrl+A -       → split horizontal
# Ctrl+A flechas → moverse entre paneles
# Ctrl+A c       → nueva ventana
# Ctrl+A n/p     → siguiente/anterior ventana

# La config de ~/.tmux.conf ya define Ctrl+A como prefijo
# (en lugar del default Ctrl+B)
```

### 2.3 Variables de entorno — solución permanente

**El problema:** En Ubuntu 24.04, el archivo `~/.bashrc` tiene un bloque de early-return para shells no interactivos:

```bash
case $- in
    *i*) ;;
      *) return;;   ← TODO lo que está DESPUÉS de aquí no se ejecuta
esac               ← en contextos Docker, systemd, scripts, etc.
```

Si `HF_TOKEN` o `VLLM_API_KEY` están definidos después de este bloque, Docker, systemd y los scripts nunca los verán.

**Solución — editar ~/.bashrc:**

```bash
# Abrir ~/.bashrc
micro ~/.bashrc
# o: nano ~/.bashrc
```

Mover estas líneas al **inicio del archivo** (antes de cualquier otro bloque):

```bash
# ══════════════════════════════════════════════════════════════════
# EXPORTS GLOBALES — DEBEN ESTAR AL INICIO (antes del bloque case)
# Aplican en: shells interactivos, SSH, Docker, systemd, scripts
# ══════════════════════════════════════════════════════════════════
export HF_TOKEN="hf_oauth_TU_TOKEN_COMPLETO_AQUI"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"        # alias que usan algunos tools
export VLLM_API_KEY="vllm-local"
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export PATH="$HOME/.npm-global/bin:$PATH"
export PATH="$PATH:$HOME/.local/bin"
export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache
export OPENCLAW_NO_RESPAWN=1
export TORCH_CUDA_ARCH_LIST="8.7"               # Orin = Ampere sm_87
# ══════════════════════════════════════════════════════════════════
```

Aplicar:
```bash
source ~/.bashrc
echo $HF_TOKEN  # debe mostrar tu token
```

Además, para Docker y systemd, agregar a `/etc/environment`:

```bash
# Extraer valor del token
HF_VAL=$(grep 'export HF_TOKEN' ~/.bashrc | head -1 | sed 's/.*HF_TOKEN=//;s/"//g;s/export //')

# Agregar a /etc/environment (sin "export", sin comillas)
echo "HF_TOKEN=${HF_VAL}" | sudo tee -a /etc/environment
echo "HUGGING_FACE_HUB_TOKEN=${HF_VAL}" | sudo tee -a /etc/environment

# Limpiar duplicados o placeholders si existen
sudo sed -i '/hf_YOUR_TOKEN_HERE/d' /etc/environment
sudo sed -i '/^HF_TOKEN=hf_/!{/^HF_TOKEN=/d}' /etc/environment 2>/dev/null || true

# Verificar (solo deben aparecer líneas con el token real)
grep HF /etc/environment
```

### 2.4 El venv `llm` — qué es, cuándo usarlo y cuándo NO

> ℹ️ **Para usuarios no familiarizados con venvs:** Un virtualenv (entorno virtual) es una copia aislada de Python con sus propias librerías. Ubuntu 24.04 protege el Python del sistema y no permite instalar paquetes directamente con `pip` (da error "externally-managed-environment"). La solución es crear un entorno virtual donde SÍ puedes instalar lo que necesites sin afectar el sistema.

```
~/venvs/llm/              ← directorio del entorno virtual
├── bin/python3           ← Python 3.12 propio
├── bin/pip               ← pip propio
├── lib/python3.12/       ← librerías instaladas aquí (no en el sistema)
│   └── site-packages/
│       ├── torch/        ← PyTorch para Jetson (CUDA 13, sm_87)
│       ├── torchvision/  ← compilado desde source para sm_87
│       ├── huggingface_hub/  ← incluye el comando 'hf'
│       └── ...
└── bin/hf               ← comando 'hf' para descargar modelos
```

**Cuándo activar el venv:**
```bash
source ~/venvs/llm/bin/activate
```
- Antes de `pip install` de cualquier paquete Python
- Antes de `import torch` en scripts Python
- Antes de `hf download` o `hf auth login`
- Al ejecutar Jetson Device Skills o BSP Skills
- Al ejecutar scripts que usen PyTorch

**Cuándo NO necesitas el venv:**
- Comandos Docker (docker run, docker ps, etc.)
- Comandos Ollama (ollama run, ollama pull, etc.)
- Comandos OpenClaw (openclaw, claw-*)
- SSH, tmux, git, curl, htop, etc.
- El comando `hf` si ya está en PATH global (verificar con `which hf`)

**Verificar que el venv existe:**
```bash
ls ~/venvs/llm/bin/activate && echo "venv OK" || echo "venv NO existe"
```

**Crear el venv si no existe:**
```bash
python3 --version  # debe ser 3.12.x
python3 -m venv ~/venvs/llm
source ~/venvs/llm/bin/activate
pip install --upgrade pip
pip install huggingface-hub requests numpy
```

**El prompt cambia cuando el venv está activo:**
```
(llm) jetson@jetson-orin:~$   ← venv activo
jetson@jetson-orin:~$          ← sin venv
```

### 2.5 Token HuggingFace — setup en 3 lugares

```bash
# Paso 1: Activar venv donde está instalado 'hf'
source ~/venvs/llm/bin/activate

# Paso 2: Login con 'hf' (NO huggingface-cli — ese comando está deprecado)
hf auth login --token $HF_TOKEN

# Verificar que se cacheó en disco
cat ~/.cache/huggingface/token
# Debe mostrar: hf_oauth_...

# Desactivar venv (ya no necesario)
deactivate

# Paso 3: Verificar en Docker (el volumen mount lleva el token automáticamente)
docker run --rm \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cat /root/.cache/huggingface/token | head -c 15 && echo '... ✅'"
```

### 2.6 Crear estructura de directorios

```bash
# Estructura base del proyecto
mkdir -p ~/scripts
mkdir -p ~/models/hf           # donde van los modelos descargados
mkdir -p ~/venvs               # entornos virtuales Python
mkdir -p ~/projects            # repos clonados (device-skills, etc.)
mkdir -p ~/jetson-ai-data/outputs  # outputs de pipelines
mkdir -p /var/tmp/openclaw-compile-cache  # caché Node.js

# Scripts de status ya descritos en el fresh-start
# Si no tienes ~/scripts/status.sh, créalo más adelante con el alias 'jstatus'
```

---

## PARTE 3 — GESTIÓN DE RECURSOS

> Esta parte es la más crítica. La memoria unificada del Jetson puede convertirse en tu mayor problema si no la gestionas correctamente.

### 3.1 Por qué la Jetson es diferente

```
GPU discreta (PC normal):
  CPU RAM: 32GB (solo CPU)          GPU VRAM: 24GB (solo GPU)
  Si se llena VRAM → el proceso GPU muere, el sistema sigue normal

Jetson AGX Orin 64GB:
  ┌─────────────────────────────────────────────────────────┐
  │             POOL UNIFICADO: 64 GB                       │
  │  OS(3GB) │ OpenClaw(0.5GB) │ LLM pesos │ KV cache LLM  │
  │  Docker  │ Ollama          │ Page cache │ tmux, ssh...  │
  └─────────────────────────────────────────────────────────┘
  Si el pool se llena → TODO SE CONGELA (requiere apagado físico)
  No hay separación: 1 proceso puede matar el sistema completo
```

**Los tres tipos de memoria "fantasma":**

| Tipo | Causa | Detección | Cuánta RAM |
|------|-------|-----------|-----------|
| Contenedor Docker con restart automático | `--restart unless-stopped` o `always` | `docker ps` | 3–50 GB |
| vLLM pre-allocate | Reserva `gpu_mem_util × 64GB` AL ARRANCAR el contenedor, no en la primera petición | `docker stats` | 15–50 GB |
| Ollama keep_alive | Mantiene el modelo 5 min después del último uso | `ollama ps` | 2–20 GB |
| Page cache del kernel | Archivos de modelo cacheados en RAM tras uso | `free -h` buff/cache | 2–10 GB |
| Open-WebUI | No carga modelos, pero si tiene Ollama como backend, un clic = modelo cargado | `ollama ps` | 0 GB propio |

### 3.2 Auditoría completa de recursos

```bash
# ── DIAGNÓSTICO RÁPIDO (30 segundos) ─────────────────────────────

# 1. Memoria del sistema
free -h
# Mirar: 'available' — debe ser >50GB cuando idle

# 2. ¿Qué contenedores están activos?
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}"

# 3. ¿Cuánta RAM consume cada contenedor?
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# 4. ¿Qué modelos de Ollama están en GPU ahora mismo?
ollama ps
# Vacío = nada en GPU | Lista = modelo activo en memoria

# 5. ¿Qué endpoints de inferencia responden?
curl -s http://localhost:8000/v1/models 2>/dev/null | \
  python3 -c "import sys,json; [print('vLLM:8000 →', m['id']) for m in json.load(sys.stdin)['data']]" \
  2>/dev/null || echo "vLLM:8000 → offline"

curl -s http://localhost:8080/v1/models 2>/dev/null | \
  python3 -c "import sys,json; [print('llama.cpp:8080 →', m['id']) for m in json.load(sys.stdin)['data']]" \
  2>/dev/null || echo "llama.cpp:8080 → offline"

ollama ps 2>/dev/null || echo "Ollama → offline"

# 6. ¿Qué política de restart tienen los contenedores? (¿cuáles auto-arrancan?)
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
    for c in json.load(sys.stdin):
        n = c['Name'].lstrip('/')
        p = c['HostConfig']['RestartPolicy']['Name']
        s = c['State']['Status']
        riesgo = '⚠️ AUTO-ARRANCA' if p in ['always','unless-stopped'] else '✓ manual'
        print(f'  {riesgo}  {n:30} restart={p} ({s})')
except: print('  Sin contenedores')
" 2>/dev/null || echo "Sin contenedores"
```

### 3.3 Modos de poder

```bash
# Ver modo actual
sudo nvpmodel -q

# Cambiar modo (efecto inmediato)
sudo nvpmodel -m 0   # MAXN — 12 cores CPU, máxima GPU freq, ~50W
sudo nvpmodel -m 1   # 15W  — 4 cores CPU
sudo nvpmodel -m 2   # 30W  — 8 cores CPU  
sudo nvpmodel -m 3   # 50W  — 12 cores CPU (alias de MAXN en JP 7.2)

# Boostear clocks al máximo para el modo actual
sudo jetson_clocks

# Restaurar clocks por defecto (menos ruido, menos calor)
sudo jetson_clocks --restore
```

**Guía por workload:**

| Tarea | Modo | Nota |
|-------|------|------|
| Idle / OpenClaw solo | 15W | Gateway pesa ~500MB, no necesita más |
| Gemma 4 E2B (cualquier engine) | 30W | E2B es eficiente, no necesita MAXN |
| Nemotron3 30B-A3B o Nemotron Omni | MAXN | 30B activos necesitan max bandwidth |
| Compilar torchvision / builds | 30W | CPU intensivo, GPU no es bottleneck |

### 3.4 Presupuesto de memoria por modelo

```
TOTAL DISPONIBLE: ~61 GB (64GB - 3GB sistema)

Backend A: Gemma 4 E2B / vLLM (bfloat16, gpu_util=0.55)
  Modelo:     ~4.6 GB
  KV cache:   ~33 GB reservados (55% de 61GB)
  Efectivo:   ~15 GB (el KV cache no se llena hasta que haya requests)
  Libre:      ~49 GB para OS y OpenClaw

Backend B: Gemma 4 E2B / llama.cpp (GGUF Q4_K_S)
  Modelo:     ~2.5 GB
  KV cache:   ~1 GB (ctx 32768)
  Total:      ~3.5 GB  ← mínima huella, ideal para máxima disponibilidad
  Libre:      ~57 GB

Backend C: Nemotron3 30B-A3B / vLLM (AWQ, gpu_util=0.80)
  Modelo:     ~17 GB
  KV cache:   ~32 GB
  Total:      ~26 GB
  Libre:      ~35 GB — MONITOREAR ACTIVAMENTE

Backend D: Nemotron Omni / llama.cpp (GGUF Q4_K_M)
  Modelo:     ~20 GB
  KV cache:   ~4 GB (ctx 8192)
  Total:      ~24 GB
  Libre:      ~37 GB

REGLA: free -h → 'available' debe ser >50GB antes de iniciar un modelo
NUNCA: dos backends simultáneos
```

### 3.5 Limpieza completa de recursos

**Modo manual:**

```bash
# Paso 1: Detener contenedores de inferencia
docker stop vllm-openclaw llama-openclaw 2>/dev/null
docker rm vllm-openclaw llama-openclaw 2>/dev/null

# Paso 2: Detener Open-WebUI si no lo usas
docker stop open-webui 2>/dev/null

# Paso 3: Descargar modelos de Ollama de la GPU
# Opción A: mediante API (no detiene el servicio)
for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
  curl -s http://localhost:11434/api/generate \
    -d "{\"model\": \"$m\", \"keep_alive\": 0}" > /dev/null
  echo "Descargado: $m"
done
# Opción B: detener el servicio completo
sudo systemctl stop ollama

# Paso 4: Liberar page cache del kernel
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Paso 5: Verificar
sleep 3
free -h
# 'available' debe ser >55GB
```

**Modo script (ejecutar con `jetson-clean`):**
```bash
# Script guardado en ~/scripts/jetson-clean.sh
# Se configura en PARTE 6 con su alias jetson-clean
```

### 3.6 Hardening de producción (ejecutar una sola vez)

```bash
# ── 1. POLÍTICAS DE RESTART: LLM containers nunca deben auto-arrancar ──
for container in vllm-openclaw llama-openclaw; do
  docker update --restart=no $container 2>/dev/null && \
    echo "✓ $container → restart=no" || \
    echo "- $container aún no existe (normal)"
done

# Open-WebUI puede tener restart=always (es ligero, ~200MB RAM)
# Pero si no quieres que abra al boot: docker update --restart=no open-webui

# ── 2. OLLAMA: descargar modelos inmediatamente tras cada uso ──
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/production.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=0"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama 2>/dev/null || true
echo "✓ Ollama configurado (keep_alive=0, max_loaded=1)"

# ── 3. PROTECCIÓN OOM DEL KERNEL ──
sudo tee /etc/sysctl.d/99-jetson-oom.conf << 'EOF'
# Preferir matar procesos antes que kernel panic por OOM
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1
vm.swappiness = 1
vm.vfs_cache_pressure = 200
EOF
sudo sysctl -p /etc/sysctl.d/99-jetson-oom.conf
echo "✓ Protección OOM aplicada"

# ── 4. CACHÉ NODE.JS (reduce tiempo de inicio de OpenClaw) ──
mkdir -p /var/tmp/openclaw-compile-cache
echo "✓ Cache Node.js creada"

# ── 5. VERIFICACIÓN ──
echo ""
echo "=== Hardening completo ==="
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys,json
try:
  for c in json.load(sys.stdin):
    n = c['Name'].lstrip('/')
    p = c['HostConfig']['RestartPolicy']['Name']
    flag = '⚠️' if p in ['always','unless-stopped'] else '✅'
    print(f'  {flag} {n}: restart={p}')
except: print('  Sin contenedores')
" 2>/dev/null

---

## PARTE 4 — OPENCLAW (PROTAGONISTA)

OpenClaw es el agente central. Todo lo demás (vLLM, llama.cpp, Ollama) son backends de inferencia que OpenClaw usa para responder. Sin modelo activo, OpenClaw arranca pero no puede generar respuestas.

```
Windows                    Jetson AGX Orin 64GB
  WhatsApp ────────────→   OpenClaw Gateway :18789
  Web UI   ────────────→       ↓ (llama al modelo activo)
  TUI      ────────────→   vLLM :8000 / llama.cpp :8080 / Ollama :11434
                               ↓
                           google/gemma-4-E2B-it (u otro modelo)
```

### 4.1 ¿Está OpenClaw instalado?

```bash
# Verificar
openclaw --version
# Esperado: OpenClaw 2026.6.x

# Si no está instalado → ir a 4.1.1
# Si está instalado pero no configurado → ir a 4.2
# Si está configurado y funcionando → ir a 4.5 (uso cotidiano)
```

#### 4.1.1 Instalar OpenClaw (si no está instalado)

> **Importante:** El paquete npm se llama `openclaw`, no `@openclaw/cli`. Este último no existe en npm.

```bash
# ── Método recomendado: script oficial ───────────────────────────
# Maneja la versión de Node, instala el daemon y arranca el onboarding
curl -fsSL https://openclaw.ai/install.sh | bash

# ── Alternativa manual con npm ────────────────────────────────────
npm install -g openclaw@latest
openclaw onboard --install-daemon

# ── Verificar después de instalar ────────────────────────────────
openclaw --version
node --version   # debe ser v22.19+

# Si 'openclaw' no se encuentra después de instalar:
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 4.2 Verificar instalación existente

```bash
# Estado completo del gateway
openclaw gateway status

# ¿El systemd service existe y está habilitado?
systemctl --user status openclaw-gateway.service

# Si no está como servicio systemd:
openclaw gateway install
systemctl --user enable openclaw-gateway.service

# Verificar que la config JSON es válida
python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null && echo "JSON ✅" || echo "JSON ❌"

# Ver configuración actual del modelo
openclaw models set  # muestra el modelo activo
grep '"primary"' ~/.openclaw/openclaw.json

# Estado de canales
openclaw channels status --probe
```

### 4.3 Configuración completa de OpenClaw

Esta es la configuración probada en producción con todos los patches aplicados:

```bash
# ── Crear backup de la config existente primero ──────────────────
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# ── Generar el token del gateway ─────────────────────────────────
GATEWAY_TOKEN=$(openclaw doctor --generate-gateway-token 2>/dev/null | grep -o '[a-f0-9]\{20,\}' | head -1)
echo "Token generado: $GATEWAY_TOKEN"
# Si el comando anterior no funciona, usar: openssl rand -hex 24
```

```bash
# ── Escribir la configuración completa ───────────────────────────
cat > ~/.openclaw/openclaw.json << EOF
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
      "token": "${GATEWAY_TOKEN:-REEMPLAZAR_CON_OPENCLAW_DOCTOR}"
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
            "id": "google/gemma-4-E2B-it",
            "name": "Gemma 4 E2B (local vLLM)",
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

# Validar
python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null && echo "✅ Config JSON válida" || echo "❌ Error en JSON"

# Aplicar
openclaw gateway restart
sleep 5
openclaw doctor
```

**Errores comunes en la config (todos verificados en producción):**

```
❌ INCORRECTO                          ✅ CORRECTO
"profile": "default"               → "profile": "full"
"profile": "coding"                → "profile": "full"  ← coding elimina WhatsApp reply tool
"apiKey": "VLLM_API_KEY"           → "apiKey": "vllm-local"  ← era el nombre de la var
"id": "vllm/google/gemma-4-E2B-it" → "id": "google/gemma-4-E2B-it"  ← sin prefijo
"primary": "vllm/google/gemma4-..."  → "primary": "vllm/google/gemma-4-..."  ← guión en gemma-4
"contextWindow": 128000            → "contextWindow": 65536  ← debe coincidir con --max-model-len
"maxTokens": 8192 (= contextWindow) → "maxTokens": 4096  ← dejar espacio para input
"memorySearch": {"enabled": true}  → "memorySearch": {"enabled": false}  ← sin OpenAI key falla
```

### 4.4 Web UI de OpenClaw desde Windows

> ⚠️ **Error crítico documentado:** El túnel SSH del Web UI de OpenClaw se ejecuta desde **Windows PowerShell**, NO desde el Jetson. Ejecutarlo desde el Jetson hacia sí mismo produce `Permission denied (publickey)`.

```powershell
# ── En Windows PowerShell (NO en el Jetson) ───────────────────────
# Mantener esta ventana abierta mientras usas el Web UI
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

```
# Abrir en navegador de Windows
http://localhost:18789/#token=TU_TOKEN_AQUI
```

Obtener el token:
```bash
# En el Jetson via SSH
openclaw config get gateway.auth.token
```

**Alternativa sin túnel — NoMachine:**

Si NoMachine está corriendo (`:4000`), conectar con NoMachine desde Windows y abrir en el navegador interno del escritorio virtual:
```
http://127.0.0.1:18789/#token=TU_TOKEN
```

### 4.5 Canal WhatsApp

```bash
# ── Setup inicial (solo la primera vez) ──────────────────────────

# Paso 1: Ejecutar onboarding (aparece QR code en terminal)
openclaw onboard

# Durante el wizard:
# ✓ Channel: WhatsApp
# ✓ dmPolicy: Pairing (recomendado)
# ✓ Search provider: Brave Search
# ✓ Hooks: habilitar todos los 5
# ✓ Gateway service: Install (systemd user service)
# ✓ Hatch: Browser (acceder via túnel desde Windows)

# Paso 2: Escanear QR con tu teléfono
# WhatsApp → Configuración → Dispositivos vinculados → Vincular dispositivo
# Apuntar la cámara al QR en la terminal

# Paso 3: Aprobar tu número (llega código al chat del bot)
openclaw pairing list whatsapp
# Muestra: pending  +573XXXXXXXXX  code: XXXXXX
openclaw pairing approve whatsapp TU_CODIGO
# Output esperado:
# "Approved whatsapp sender +573XXXXXXXXX"
# "Command owner configured whatsapp:+573XXXXXXXXX"  ← automático

# Paso 4: Verificar
openclaw channels status --probe
# Esperado: WhatsApp default: enabled, configured, linked, running, connected
```

**Si WhatsApp se desconecta (logs muestran "session logged out"):**
```bash
openclaw channels auth login whatsapp
# Escanear QR nuevamente
```

**Políticas de DM:**
```bash
# Pairing (default): nuevos remitentes reciben código de 6 caracteres
openclaw config set channels.whatsapp.dmPolicy pairing

# Allowlist: solo números pre-aprobados, el resto es bloqueado
openclaw config set channels.whatsapp.dmPolicy allowlist
openclaw config set channels.whatsapp.dmAllowFrom '["+573XXXXXXXXX","+573XXXXXXXXY"]'
```

### 4.6 Gestión del gateway en el día a día

```bash
# Estado completo
openclaw gateway status

# Reiniciar (necesario después de cambiar config)
openclaw gateway restart && sleep 3 && openclaw gateway status

# Ver logs en tiempo real
openclaw logs --follow

# Solo logs de WhatsApp
openclaw logs --follow | grep -i whatsapp

# Solo errores
openclaw logs --follow | grep -i error

# Interfaz de terminal (TUI)
openclaw tui
# Dentro del TUI: /new → nueva sesión | /compact → compactar | /quit → salir

# Verificar qué herramientas tiene el agente disponibles
openclaw doctor | grep -A 20 "Skills"

# Si hay problema de modelo no encontrado: verificar endpoint primero
curl -s http://localhost:8000/v1/models | python3 -c \
  "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
```

### 4.7 Skills recomendados para OpenClaw

Los skills amplían las capacidades del agente. Desde el gateway, verificar disponibles:

```bash
openclaw skills list --verbose
openclaw skills check
```

**Skills útiles para los casos de uso de este setup:**

```bash
# Web search (ya configurado con Brave)
# → Permite al agente buscar información actualizada

# Memory core (viene por defecto)
# → Recuerda conversaciones entre sesiones

# File transfer
# → Permite enviar/recibir archivos via WhatsApp

# Para instalar skills adicionales:
openclaw skills install <nombre-del-skill>

# Verificar instalación
openclaw skills check
```

> 📝 La lista completa de skills disponibles en ClawHub: `https://docs.openclaw.ai/clawhub`

---

## PARTE 5 — BACKENDS DE INFERENCIA

### 5.1 Guía de selección

```
¿Qué necesito hacer ahora?
│
├── Responder WhatsApp, analizar imagen, búsqueda web
│   → mode-openclaw (Gemma 4 E2B / vLLM)
│   ↳ 128K ctx · tool calling · imagen · 15GB RAM · 30W
│
├── Mismo agente pero máxima RAM disponible / modo nocturno
│   → mode-lite (Gemma 4 E2B / llama.cpp)
│   ↳ 32K ctx · solo texto · 3.5GB RAM · 30W · inicia en 20 segundos
│
├── PDF de 100MB+ / libro de 300 páginas / contrato largo
│   → mode-longdoc (Nemotron3 30B-A3B / vLLM)
│   ↳ 256K ctx · razonamiento avanzado · solo texto · 26GB RAM · MAXN
│
├── Transcribir audio/video, conferencias → notas, podcast desde audio
│   → mode-multimodal (Nemotron Omni / llama.cpp)
│   ↳ 256K ctx · texto+imagen+audio+video · 24GB RAM · MAXN
│
└── Explorar modelos, desarrollo, demos, modelos pequeños
    → mode-ollama + ollama run <modelo>
    ↳ Flexible · hasta 64GB · descargar y probar cualquier modelo
```

**Tabla comparativa:**

| | Gemma E2B vLLM | Gemma E2B llama | Nemotron3 30B | Nemotron Omni |
|---|---|---|---|---|
| tok/s | ~32 | ~35 | ~38 | ~39 |
| RAM | ~15GB | ~3.5GB | ~26GB | ~24GB |
| Arranque | ~3 min | ~20 seg | ~10 min | ~2 min |
| Contexto | 128K | 32K | 256K | 256K |
| Texto | ✅ | ✅ | ✅ | ✅ |
| Imagen | ✅ | ❌ | ❌ | ✅ |
| Audio | ❌ | ❌ | ❌ | ✅ |
| Video | ❌ | ❌ | ❌ | ✅ |
| Tool calling | ✅ gemma4 | básico | ✅ hermes | básico |
| Razonamiento | ❌ | ❌ | ✅ config | ✅ config |
| Puerto | 8000 | 8080 | 8000 | 8080 |
| Modo poder | 30W | 30W | MAXN | MAXN |

### 5.2 Backend A: Gemma 4 E2B via vLLM ✅ (verificado en producción)

**Cuándo:** Agente WhatsApp por defecto, respuestas con imagen, tool calling

```bash
# ── Pre-requisitos ────────────────────────────────────────────────
# Limpiar memoria
docker rm -f vllm-openclaw llama-openclaw 2>/dev/null
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sleep 5

# Verificar memoria libre antes de iniciar
FREE=$(free -g | awk '/^Mem:/{print $7}')
echo "Libre: ${FREE}GB (necesitas >50GB)"
[ "$FREE" -lt 50 ] && echo "⚠️ Limpia más antes de continuar" || echo "✅ OK"

# ── Ajustar poder ─────────────────────────────────────────────────
sudo nvpmodel -m 2 && sudo jetson_clocks

# ── Iniciar vLLM ─────────────────────────────────────────────────
# NOTA: --restart no (no unless-stopped — evita arranque fantasma)
# NOTA: bash -c "cd /opt && source venv/bin/activate && vllm serve ..."
#   es OBLIGATORIO — esta imagen no tiene entrypoint de servidor
docker run --runtime nvidia -d \
  --name vllm-openclaw \
  --restart no \
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

# ── Esperar inicio (poll — no sleep fijo) ────────────────────────
echo -n "Esperando vLLM (primera vez ~3-5 min)"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " ✅"

# ── Verificar ────────────────────────────────────────────────────
curl -s http://localhost:8000/v1/models | python3 -c \
  "import sys,json; print('Modelo activo:', json.load(sys.stdin)['data'][0]['id'])"

# ── Actualizar OpenClaw ───────────────────────────────────────────
openclaw models set vllm/google/gemma-4-E2B-it
openclaw gateway restart
```

### 5.3 Backend B: Gemma 4 E2B via llama.cpp

**Cuándo:** Modo nocturno, mínima RAM, arranque rápido, Ollama corriendo en paralelo

```bash
docker rm -f vllm-openclaw llama-openclaw 2>/dev/null
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sudo nvpmodel -m 2 && sudo jetson_clocks

docker run --runtime nvidia -d \
  --name llama-openclaw \
  --restart no \
  --network host \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_S \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias gemma-e2b \
    --host 0.0.0.0

echo -n "Esperando llama.cpp"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 5
done
echo " ✅ (puerto 8080)"

# Actualizar config de OpenClaw para usar puerto 8080
# Editar ~/.openclaw/openclaw.json:
# "baseUrl": "http://127.0.0.1:8080/v1"
# "id": "gemma-e2b"
# "primary": "vllm/gemma-e2b"
# "contextWindow": 32768
openclaw gateway restart
```

### 5.4 Backend C: Nemotron3 30B-A3B via vLLM

**Cuándo:** PDFs de 100MB+, documentos legales, contexto de 256K tokens, razonamiento

> ℹ️ **Arquitectura:** MoE híbrido — 30B parámetros totales, solo 3.5B activos por forward pass. Mamba-2 + Attention. AWQ W4A16 no requiere HF auth para Orin.

```bash
# CRÍTICO: verificar >50GB libre antes de iniciar
jetson-clean  # o manualmente: para contenedores + drop cache
FREE=$(free -g | awk '/^Mem:/{print $7}')
[ "$FREE" -lt 50 ] && echo "⚠️ STOP: necesitas más memoria libre" && return

sudo nvpmodel -m 0 && sudo jetson_clocks

docker run --runtime nvidia -d \
  --name vllm-openclaw \
  --restart no \
  --network host --ipc host --shm-size 8g \
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
      --default-chat-template-kwargs '{\"enable_thinking\": false}' \
      --host 0.0.0.0 --port 8000"

echo "Esperando Nemotron3 30B (~10 min en primera descarga)..."
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo "  $(docker logs vllm-openclaw 2>&1 | tail -1)"; sleep 30
done
echo "✅ Nemotron3 30B listo"

# Control de razonamiento por request:
# Con cadena de pensamiento:
# "extra_body": {"chat_template_kwargs": {"enable_thinking": true}}
# Sin cadena de pensamiento (default configurado arriba):
# "extra_body": {"chat_template_kwargs": {"enable_thinking": false}}
```

### 5.5 Backend D: Nemotron Omni via llama.cpp

**Cuándo:** Audio de conferencias, vídeos de clases, imágenes con texto, multimodal nativo

```bash
jetson-clean
sudo nvpmodel -m 0 && sudo jetson_clocks

docker run --runtime nvidia -d \
  --name llama-openclaw \
  --restart no \
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

echo -n "Esperando Nemotron Omni"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 20
done
echo " ✅ (puerto 8080)"

# Test con razonamiento activado:
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nemotron-omni","messages":[{"role":"user","content":"Hola"}],
       "chat_template_kwargs":{"enable_thinking":true},"max_tokens":100}'
```

### 5.6 Ollama — exploración y desarrollo

```bash
# Iniciar Ollama (si no está activo)
sudo systemctl start ollama

# Listar modelos disponibles localmente
ollama list

# Ver qué está en GPU ahora mismo
ollama ps

# Correr un modelo
ollama run gemma4:latest
ollama run gemma4:26b
# (Ctrl+D para salir)

# Descargar modelo sin correrlo
ollama pull qwen3:8b

# Parar un modelo manualmente
ollama stop gemma4:latest

# Descargar de GPU sin parar el servicio (keep_alive=0)
curl -s http://localhost:11434/api/generate \
  -d '{"model":"gemma4:latest","keep_alive":0}' > /dev/null

# ADVERTENCIA: Ollama y vLLM no pueden coexistir con modelos grandes
# Antes de mode-longdoc o mode-multimodal:
sudo systemctl stop ollama
```

---

## PARTE 6 — SISTEMA DE AUTOMATIZACIÓN

> ℹ️ Esta sección es un **feature adicional**. Todo lo documentado en Partes 1-5 tiene sus pasos manuales completos. Los scripts y aliases aquí documentados son atajos opcionales para usuarios que prefieren automatizar.

### 6.1 ~/.bashrc completo — aliases y funciones

Agregar al **inicio** de `~/.bashrc` (después de los exports, antes del bloque interactivo):

```bash
# ══════════════════════════════════════════════════════════════════
# ALIASES Y FUNCIONES — JETSON AGX ORIN JP 7.2
# ══════════════════════════════════════════════════════════════════

# ── ENTORNO ────────────────────────────────────────────────────────

# Activar venv llm (alias del fresh-start)
alias llmenv='source ~/venvs/llm/bin/activate && echo "venv llm activado — (llm) en el prompt"'

# tmux (alias del fresh-start)
alias tm='tmux attach -t main 2>/dev/null || tmux new-session -s main'
alias tm-llm='tmux attach -t llm 2>/dev/null || tmux new-session -s llm'

# ── STATUS Y MONITOREO ─────────────────────────────────────────────

# Script de status completo (del fresh-start)
alias jstatus='~/scripts/status.sh'

# Monitor interactivo de Jetson
alias jtop='jtop'

# GPU snapshot
alias gpu='nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader 2>/dev/null || tegrastats --interval 1000 &; sleep 2; kill %1'

# Auditoría completa de memoria y procesos
jetson-audit() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  printf  "║   AUDITORÍA JETSON AGX ORIN — %-25s  ║\n" "$(date '+%H:%M:%S %d/%m/%Y')"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
  echo "── MEMORIA ──"
  free -h | grep -E "Mem|Swap"
  echo ""
  echo "── CONTENEDORES ACTIVOS ──"
  local n=$(docker ps -q 2>/dev/null | wc -l)
  if [ "$n" -gt 0 ]; then
    docker ps --format "  {{.Names}}: {{.Status}} ({{.RunningFor}})"
    echo ""
    docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}} ({{.MemPerc}})"
  else
    echo "  Ninguno"
  fi
  echo ""
  echo "── RESTART POLICIES ──"
  docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
  for c in json.load(sys.stdin):
    n = c['Name'].lstrip('/')
    p = c['HostConfig']['RestartPolicy']['Name']
    s = c['State']['Status']
    r = '⚠️  AUTO' if p in ['always','unless-stopped'] else '✓ manual'
    print(f'  {r}  {n:28} restart={p} ({s})')
except: pass
" 2>/dev/null || echo "  Sin contenedores"
  echo ""
  echo "── OLLAMA EN GPU ──"
  local ol=$(ollama ps 2>/dev/null | tail -n +2 | wc -l)
  [ "$ol" -gt 0 ] && ollama ps || echo "  Ningún modelo cargado"
  echo ""
  echo "── ENDPOINTS DE INFERENCIA ──"
  curl -s http://localhost:8000/v1/models 2>/dev/null | \
    python3 -c "import sys,json; [print(f'  vLLM:8000  → {m[\"id\"]}') for m in json.load(sys.stdin)['data']]" \
    2>/dev/null || echo "  vLLM:8000  → offline"
  curl -s http://localhost:8080/v1/models 2>/dev/null | \
    python3 -c "import sys,json; [print(f'  llama:8080 → {m[\"id\"]}') for m in json.load(sys.stdin)['data']]" \
    2>/dev/null || echo "  llama:8080 → offline"
  curl -s http://localhost:11434/api/tags 2>/dev/null | \
    python3 -c "import sys,json; [print(f'  Ollama     → {m[\"name\"]} (descargado)') for m in json.load(sys.stdin).get('models',[])]" \
    2>/dev/null || echo "  Ollama     → offline"
  echo ""
  echo "── OPENCLAW ──"
  openclaw gateway status 2>/dev/null | grep -E "reachable|running|error|WhatsApp" || echo "  Estado desconocido"
  echo ""
}

# Memoria rápida
alias jetson-mem='free -h && echo "" && docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}}" 2>/dev/null'

# Qué modelo está activo
alias model-status='
echo "── vLLM :8000 ──";
curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c "import sys,json; [print(\"  \",m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" 2>/dev/null || echo "  offline";
echo "── llama.cpp :8080 ──";
curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -c "import sys,json; [print(\"  \",m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" 2>/dev/null || echo "  offline";
echo "── Ollama :11434 ──";
ollama ps 2>/dev/null | tail -n +2 || echo "  offline/vacío"
'

# ── LIMPIEZA ────────────────────────────────────────────────────────

# Limpieza total (alias del script)
alias jetson-clean='~/scripts/jetson-clean.sh'

# Solo page cache (seguro, no afecta servicios)
alias jetson-dropcache='sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches" && echo "Cache dropped: $(free -h | awk \"/^Mem:/{print \$7}\") libres"'

# Fixear restart policies en todos los contenedores LLM
alias docker-fix-restart='for c in vllm-openclaw llama-openclaw; do docker update --restart=no $c 2>/dev/null && echo "✓ $c → restart=no" || echo "- $c no existe"; done'

# ── MODOS DE OPERACIÓN ──────────────────────────────────────────────

# Idle: todo apagado, 15W
alias mode-idle='~/scripts/switch-model.sh stop'

# OpenClaw: Gemma 4 E2B / vLLM (agente principal)
alias mode-openclaw='~/scripts/switch-model.sh gemma-vllm'

# Lite: Gemma 4 E2B / llama.cpp (bajo consumo)
alias mode-lite='~/scripts/switch-model.sh gemma-llama'

# Longdoc: Nemotron3 30B-A3B / vLLM (documentos largos)
alias mode-longdoc='~/scripts/switch-model.sh nemotron-text'

# Multimodal: Nemotron Omni / llama.cpp (audio/video)
alias mode-multimodal='~/scripts/switch-model.sh nemotron-omni'

# Ollama: usar Ollama con cualquier modelo
alias mode-ollama='
docker stop vllm-openclaw llama-openclaw 2>/dev/null;
sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches";
sleep 5;
sudo systemctl start ollama;
sudo nvpmodel -m 2 && sudo jetson_clocks;
echo "✅ Ollama activo — libre: $(free -h | awk \"/^Mem:/{print \$7}\")";
echo "Uso: ollama run <modelo>"
'

# ── PODER ────────────────────────────────────────────────────────────
alias pwr-idle='sudo nvpmodel -m 1 && sudo jetson_clocks --restore && sudo nvpmodel -q'
alias pwr-30w='sudo nvpmodel -m 2 && sudo jetson_clocks && sudo nvpmodel -q'
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && sudo nvpmodel -q'
alias pwr-status='sudo nvpmodel -q'

# ── OPENCLAW ─────────────────────────────────────────────────────────
alias claw-status='openclaw gateway status && echo "" && openclaw channels status --probe'
alias claw-restart='openclaw gateway restart && sleep 3 && openclaw gateway status'
alias claw-logs='openclaw logs --follow'
alias claw-wa='openclaw logs --follow | grep -i whatsapp'
alias claw-errors='openclaw logs --follow | grep -i error'
alias claw-doctor='openclaw doctor'
alias claw-tui='openclaw tui'
alias claw-pair='openclaw pairing list whatsapp'
alias claw-token='openclaw config get gateway.auth.token'

# ── OLLAMA ────────────────────────────────────────────────────────────
alias ollist='ollama list'
alias olps='ollama ps'
alias olstop='for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null && echo "Descargado: $m"; done'
alias ollama-start='sudo systemctl start ollama && echo "Ollama iniciado"'
alias ollama-stop='olstop; sudo systemctl stop ollama && echo "Ollama detenido"'

# ── DOCKER ────────────────────────────────────────────────────────────
alias docker-all='docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.RunningFor}}"'

# ── VENV ─────────────────────────────────────────────────────────────
alias venv-status='[ -d ~/venvs/llm ] && echo "venv llm: ✅ existe" || echo "venv llm: ❌ no existe"; python3 -c "import torch; print(\"PyTorch: \"+torch.__version__+\" | CUDA: \"+str(torch.cuda.is_available()))" 2>/dev/null || echo "PyTorch: no disponible (activa venv con llmenv)"'

# ── HF / MODELOS ─────────────────────────────────────────────────────
alias hf-models='ls ~/models/hf/ 2>/dev/null || echo "~/models/hf/ vacío"'
alias hf-whoami='source ~/venvs/llm/bin/activate && hf whoami; deactivate'

# ══════════════════════════════════════════════════════════════════
# FIN DE ALIASES
# ══════════════════════════════════════════════════════════════════
```

Aplicar:
```bash
source ~/.bashrc
```

### 6.2 Scripts (features adicionales)

Cada script tiene su alias correspondiente. Los scripts son opcionales — los pasos manuales están documentados en las partes anteriores.

#### Script 1: jetson-clean.sh (alias: `jetson-clean`)

```bash
cat > ~/scripts/jetson-clean.sh << 'EOF'
#!/bin/bash
echo "╔══════════════════════════════════════╗"
echo "║    LIMPIEZA JETSON AGX ORIN 64GB     ║"
echo "╚══════════════════════════════════════╝"

echo "→ Deteniendo inferencia..."
docker stop vllm-openclaw llama-openclaw 2>/dev/null && \
  echo "  ✓ Contenedores LLM detenidos" || echo "  ✓ No había contenedores LLM"

docker stop open-webui 2>/dev/null && \
  echo "  ✓ Open-WebUI detenido" || echo "  - Open-WebUI no estaba activo"

echo "→ Descargando modelos Ollama de GPU..."
for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
  curl -s http://localhost:11434/api/generate \
    -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null
  echo "  ✓ $m descargado"
done

echo "→ Deteniendo servicio Ollama..."
sudo systemctl stop ollama 2>/dev/null && \
  echo "  ✓ Ollama detenido" || echo "  - No estaba activo"

echo "→ Liberando page cache..."
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
echo "  ✓ Cache liberada"

sleep 3
FREE=$(free -h | awk '/^Mem:/{print $7}')
CONT=$(docker ps -q 2>/dev/null | wc -l)
echo ""
echo "══════════════════════════════════════"
echo "  Memoria disponible: $FREE"
echo "  Contenedores activos: $CONT"
echo "══════════════════════════════════════"
EOF
chmod +x ~/scripts/jetson-clean.sh
```

#### Script 2: switch-model.sh (aliases: `mode-openclaw`, `mode-lite`, `mode-longdoc`, `mode-multimodal`, `mode-idle`)

```bash
cat > ~/scripts/switch-model.sh << 'SWITCHER'
#!/bin/bash
MODEL=${1:-help}
CONFIG="$HOME/.openclaw/openclaw.json"

print_usage() {
  echo ""
  echo "Uso: switch-model.sh <modo>"
  echo "  gemma-vllm    — Gemma 4 E2B / vLLM   · :8000 · 30W  · ~32 tok/s"
  echo "  gemma-llama   — Gemma 4 E2B / llama   · :8080 · 30W  · ~35 tok/s"
  echo "  nemotron-text — Nemotron3 30B / vLLM  · :8000 · MAXN · ~38 tok/s"
  echo "  nemotron-omni — Nemotron Omni / llama · :8080 · MAXN · ~39 tok/s"
  echo "  stop          — Todo apagado, 15W idle"
  echo ""
}

stop_all() {
  docker stop vllm-openclaw llama-openclaw 2>/dev/null
  docker rm vllm-openclaw llama-openclaw 2>/dev/null
  for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
    curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null
  done
  sleep 5
  sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
  sleep 3
  echo "  Libre: $(free -h | awk '/^Mem:/{print $7}')"
}

wait_model() {
  local port=$1 name=$2
  echo -n "  Esperando $name en :$port"
  local t=0
  while ! curl -s http://localhost:${port}/v1/models > /dev/null 2>&1; do
    echo -n "."; sleep 15; t=$((t+1))
    [ $t -gt 80 ] && echo " ❌ Timeout" && return 1
  done; echo " ✅"
}

update_openclaw_config() {
  local model_id=$1 base_url=$2 ctx=$3 max_tok=$4 input=$5
  python3 - << PYEOF
import json
with open('$CONFIG') as f: c = json.load(f)
c.setdefault('agents',{}).setdefault('defaults',{})
c['agents']['defaults']['model'] = {'primary': 'vllm/${model_id}'}
c['agents']['defaults']['models'] = {'vllm/${model_id}': {}}
c['models']['providers']['vllm'] = {
    'baseUrl': '${base_url}', 'api': 'openai-completions',
    'apiKey': 'vllm-local', 'timeoutSeconds': 300,
    'models': [{'id': '${model_id}', 'name': '${model_id}',
        'reasoning': False, 'input': ${input},
        'cost': {'input':0,'output':0,'cacheRead':0,'cacheWrite':0},
        'contextWindow': ${ctx}, 'maxTokens': ${max_tok}}]
}
with open('$CONFIG', 'w') as f: json.dump(c, f, indent=2)
print('  ✅ Config OpenClaw actualizada')
PYEOF
}

case $MODEL in
  gemma-vllm)
    echo "══ MODO: Gemma 4 E2B / vLLM ══"
    stop_all
    sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g \
      -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve google/gemma-4-E2B-it --dtype bfloat16 --max-model-len 65536 \
        --gpu-memory-utilization 0.55 --enable-auto-tool-choice \
        --tool-call-parser gemma4 --reasoning-parser gemma4 --host 0.0.0.0 --port 8000"
    wait_model 8000 "Gemma 4 E2B vLLM"
    update_openclaw_config "google/gemma-4-E2B-it" "http://127.0.0.1:8000/v1" 65536 4096 '["text","image"]'
    openclaw gateway restart
    echo "✅ mode-openclaw activo";;

  gemma-llama)
    echo "══ MODO: Gemma 4 E2B / llama.cpp ══"
    stop_all
    sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name llama-openclaw --restart no --network host \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_S \
        --ctx-size 32768 --n-gpu-layers 999 --port 8080 --alias gemma-e2b --host 0.0.0.0
    wait_model 8080 "Gemma 4 E2B llama.cpp"
    update_openclaw_config "gemma-e2b" "http://127.0.0.1:8080/v1" 32768 4096 '["text"]'
    openclaw gateway restart
    echo "✅ mode-lite activo";;

  nemotron-text)
    echo "══ MODO: Nemotron3 30B-A3B / vLLM ══"
    stop_all
    FREE=$(free -g | awk '/^Mem:/{print $7}')
    [ "$FREE" -lt 50 ] && echo "⚠️ Memoria insuficiente (${FREE}GB < 50GB)" && exit 1
    sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g \
      -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ \
        --gpu-memory-utilization 0.80 --trust-remote-code --max-model-len 32768 \
        --enable-auto-tool-choice --tool-call-parser hermes \
        --default-chat-template-kwargs '{\"enable_thinking\": false}' --host 0.0.0.0 --port 8000"
    wait_model 8000 "Nemotron3 30B vLLM"
    update_openclaw_config "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ" "http://127.0.0.1:8000/v1" 32768 8192 '["text"]'
    openclaw gateway restart
    echo "✅ mode-longdoc activo";;

  nemotron-omni)
    echo "══ MODO: Nemotron Omni / llama.cpp ══"
    stop_all
    sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name llama-openclaw --restart no --network host \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
        --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
        --ctx-size 8192 --n-gpu-layers 999 --port 8080 --alias nemotron-omni --host 0.0.0.0
    wait_model 8080 "Nemotron Omni llama.cpp"
    update_openclaw_config "nemotron-omni" "http://127.0.0.1:8080/v1" 8192 4096 '["text","image","audio"]'
    openclaw gateway restart
    echo "✅ mode-multimodal activo";;

  stop)
    echo "══ MODO: IDLE ══"
    stop_all
    sudo systemctl stop ollama 2>/dev/null
    sudo nvpmodel -m 1 && sudo jetson_clocks --restore
    echo "✅ Todo detenido — 15W — libre: $(free -h | awk '/^Mem:/{print $7}')";;

  *) print_usage;;
esac
SWITCHER
chmod +x ~/scripts/switch-model.sh
```

#### Script 3: verify-stack.sh (alias: `jetson-verify`)

```bash
cat > ~/scripts/verify-stack.sh << 'VERIFY'
#!/bin/bash
pass=0; fail=0

check() {
  local label=$1; shift
  local result
  result=$(eval "$@" 2>/dev/null)
  local expected="${!#}"
  if echo "$result" | grep -q "$expected"; then
    echo "  ✅ $label"; pass=$((pass+1))
  else
    echo "  ❌ $label → ${result:0:50}"; fail=$((fail+1))
  fi
}

echo "═══════════════════════════════════════════"
echo "  VERIFICACIÓN DEL STACK — $(date '+%H:%M %d/%m/%Y')"
echo "═══════════════════════════════════════════"
echo ""

echo "── SISTEMA ──"
check "Ubuntu 24.04"        "lsb_release -r" "24.04"
check "CUDA en PATH"        "nvcc --version" "release 13"
check "Docker nvidia"       "docker info | grep Runtime" "nvidia"
check "Python 3.12"         "python3 --version" "3.12"
check "Node.js 22+"         "node --version" "v22"
check "OpenClaw instalado"  "openclaw --version" "OpenClaw"
echo ""

echo "── ENTORNO ──"
check "venv llm existe"     "ls ~/venvs/llm/bin/activate" "activate"
check "HF token en disco"   "cat ~/.cache/huggingface/token | head -c 5" "hf_"
check "HF token en env"     "echo \$HF_TOKEN | head -c 5" "hf_"
check "hf CLI disponible"   "hf --version" "."
echo ""

echo "── OPENCLAW ──"
check "Gateway activo"      "openclaw gateway status" "reachable"
check "JSON config válido"  "python3 -m json.tool ~/.openclaw/openclaw.json" "agents"
check "Profile = full"      "grep '\"profile\"' ~/.openclaw/openclaw.json" "full"
check "apiKey correcto"     "grep '\"apiKey\"' ~/.openclaw/openclaw.json | grep -v 'VLLM_API_KEY'" "vllm-local"
check "WhatsApp linked"     "openclaw channels status --probe 2>/dev/null" "linked"
echo ""

echo "── INFERENCIA ──"
MODEL=$(curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || \
  curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || \
  echo "ninguno")
echo "  Modelo activo: $MODEL"
[ "$MODEL" = "ninguno" ] && echo "  ⚠️  Ningún backend activo — usar mode-openclaw" && fail=$((fail+1)) || pass=$((pass+1))
echo ""

echo "── MEMORIA ──"
FREE=$(free -g | awk '/^Mem:/{print $7}')
echo "  Libre: ${FREE}GB"
[ "$FREE" -lt 45 ] && echo "  ⚠️  Memoria baja" && fail=$((fail+1)) || echo "  ✅ OK" && pass=$((pass+1))
echo ""

echo "══════════════════════════════════════"
echo "  ✅ Passed: $pass  ❌ Failed: $fail"
echo "══════════════════════════════════════"
VERIFY
chmod +x ~/scripts/verify-stack.sh
echo 'alias jetson-verify="~/scripts/verify-stack.sh"' >> ~/.bashrc
```

#### Script 4: startup.sh (alias: `jetson-startup`)

```bash
cat > ~/scripts/startup.sh << 'STARTUP'
#!/bin/bash
# Ejecutar tras cada reboot para restaurar el stack

echo "=== Startup Jetson AI Stack ==="
source ~/.bashrc

# Esperar Docker
until docker info > /dev/null 2>&1; do echo "Esperando Docker..."; sleep 5; done

# Limpiar estados residuales del boot
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Modo poder por defecto: 30W (suficiente para Gemma E2B)
sudo nvpmodel -m 2 && sudo jetson_clocks

# Arrancar modelo por defecto
echo "Iniciando Gemma 4 E2B..."
~/scripts/switch-model.sh gemma-vllm

echo "=== Stack listo ==="
echo "OpenClaw: $(openclaw gateway status 2>/dev/null | grep -o 'reachable\|unreachable')"
echo "Modelo: $(curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"data\"][0][\"id\"])' 2>/dev/null || echo 'cargando...')"
echo "Libre: $(free -h | awk '/^Mem:/{print $7}')"
STARTUP
chmod +x ~/scripts/startup.sh
echo 'alias jetson-startup="~/scripts/startup.sh"' >> ~/.bashrc
```

#### Script 5: harden.sh (alias: `jetson-harden` — ejecutar una sola vez)

```bash
cat > ~/scripts/harden.sh << 'HARDEN'
#!/bin/bash
echo "=== Hardening Jetson AGX Orin (una sola vez) ==="

docker-fix-restart 2>/dev/null || \
  for c in vllm-openclaw llama-openclaw; do
    docker update --restart=no $c 2>/dev/null && echo "✓ $c → restart=no"
  done

sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/production.conf > /dev/null << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=0"
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollama 2>/dev/null
echo "✓ Ollama: keep_alive=0, max_models=1"

sudo tee /etc/sysctl.d/99-jetson-oom.conf > /dev/null << 'EOF'
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1
vm.swappiness = 1
vm.vfs_cache_pressure = 200
EOF
sudo sysctl -p /etc/sysctl.d/99-jetson-oom.conf
echo "✓ OOM protection aplicada"

mkdir -p /var/tmp/openclaw-compile-cache ~/scripts ~/models/hf ~/projects
echo "✓ Directorios creados"
echo "=== Hardening completo ==="
HARDEN
chmod +x ~/scripts/harden.sh
echo 'alias jetson-harden="~/scripts/harden.sh"' >> ~/.bashrc
```

Aplicar todos los aliases:
```bash
source ~/.bashrc
```

---

## PARTE 7 — OPENCLAW EN PRODUCCIÓN

### 7.1 Operación diaria

```bash
# Al conectarse via SSH cada día:

# 1. Verificar estado
claw-status

# 2. Si el modelo no está activo:
mode-openclaw   # (o el modo que necesites)

# 3. Abrir Web UI desde Windows PowerShell:
# ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
# http://localhost:18789/#token=$(claw-token via SSH)

# 4. Enviar mensaje de prueba por WhatsApp y verificar respuesta
```

### 7.2 Checklist pre-workload pesado

```bash
# Ejecutar antes de: PDF largo, audio, video, múltiples requests
jetson-audit           # ver estado actual
jetson-clean           # limpiar todo
# Elegir modo apropiado:
mode-longdoc           # para PDFs de 100MB+
mode-multimodal        # para audio/video
# Verificar
jetson-mem             # debe mostrar >50GB libres
```

### 7.3 Workflows con prompts reales

#### Agencia de turismo (mode-openclaw)

Configurar BOOTSTRAP.md del workspace:
```bash
cat > ~/.openclaw/workspace/BOOTSTRAP.md << 'EOF'
# Agente de Agencia de Turismo Colombia

Soy el asistente virtual de [Tu Agencia], especializada en turismo por Colombia.

## Destinos: Cartagena, Medellín, Bogotá, Eje Cafetero, Amazonas, Sierra Nevada, Guajira

## Al recibir una consulta:
1. Ofrecer siempre 3 opciones: económico / estándar / premium
2. Incluir: duración, punto de encuentro, qué llevar, precio aproximado
3. En WhatsApp: máximo 3 párrafos cortos
4. Idioma: detectar automáticamente (español/inglés)

## Escalación: "Para reservas confirmadas escríbenos a [contacto]"
EOF
```

Prompt ejemplo de cliente:
```
"Quiero visitar Cartagena 5 días con mi familia, somos 4 personas"
→ El agente responde con 3 paquetes + detalles
```

#### Podcast desde PDF (mode-longdoc)

```bash
mode-longdoc
# Esperar ~10 min primera vez
```

Prompt en Web UI o WhatsApp:
```
[Adjuntar PDF]

Convierte este documento en script de podcast de 30 minutos.
Formato: 2 presentadores (Ana = analítica, Luis = explica)
Estructura: intro gancho → 5 segmentos → cierre con acción
Cada segmento: concepto → ejemplo real → qué hacer al respecto
Tono: conversacional, educativo, no académico
Idioma: español colombiano
```

#### Grabación → notas (mode-multimodal)

```bash
mode-multimodal
# Esperar ~2 min
```

Prompt con archivo de audio enviado por WhatsApp:
```
[Nota de voz o archivo de audio]

Transcribe y organiza en:
1. RESUMEN (5 bullets)
2. DECISIONES tomadas
3. TAREAS (tarea · responsable · fecha)
4. CONCEPTOS nuevos explicados
Formato: Notion-friendly (## para secciones)
```

#### Contenido para redes (mode-openclaw)

```
Crea calendario de contenido para 1 semana para agencia de turismo Colombia.
Formato por día:
📱 Instagram: caption 200 palabras + 15 hashtags ESP + 5 ENG
💼 LinkedIn: post profesional 250 palabras
📲 Status WhatsApp: frase <100 caracteres
Tono: auténtico, apasionado por Colombia. Evitar clichés genéricos.
```

### 7.4 Recuperación de errores comunes

```bash
# Error: "model not found by provider"
curl -s http://localhost:8000/v1/models | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
# Ajustar "id" en config con lo que devuelve este comando
openclaw gateway restart

# Error: WhatsApp no responde aunque recibe mensajes
grep '"profile"' ~/.openclaw/openclaw.json  # debe decir "full"
# Si dice "coding": cambiar a "full" y claw-restart

# Error: OOM / sistema lento
jetson-clean
free -h  # verificar recuperación
mode-openclaw  # reiniciar con modelo fresco

# Error: Gateway no arranca
openclaw doctor
python3 -m json.tool ~/.openclaw/openclaw.json  # verificar JSON
openclaw gateway start
```

---

## APÉNDICE A — REGISTRO DE PATCHES

Todos los errores encontrados durante la instalación real en producción:

| # | Componente | Error | Causa raíz | Fix |
|---|---|---|---|---|
| P1 | hf download | Descarga incorrecta | `--exclude "a" "b"` trata "b" como archivo | Usar `--exclude` por cada patrón |
| P2 | HF_TOKEN | Vacío en Docker/systemd | Definido después de `case $- in *i*)` | Mover exports al inicio del bashrc |
| P3 | HF CLI | `huggingface-cli: not found` | Comando deprecado | Usar `hf` (instalado en el venv llm) |
| P4 | OpenShell | `npm 404 @openshell/cli` | No existe en npm | `curl ... NVIDIA/OpenShell/install.sh | sh` |
| P5 | OpenClaw | `npm 404 @openclaw/cli` | No existe en npm | `curl -fsSL https://openclaw.ai/install.sh | bash` |
| P6 | vLLM | Puerto 8000 nunca abre | Imagen x86 `vllm/vllm-openai` en arm64 | `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` |
| P7 | vLLM | `exec: "--model": not found` | Sin entrypoint de servidor en imagen nvidia-ai-iot | `bash -c "cd /opt && source venv/bin/activate && vllm serve ..."` |
| P8 | vLLM | `sleep 10` insuficiente | Modelos tardan 3-10 min | Loop de polling con curl |
| P9 | vLLM | OOM al iniciar | `gpu_mem_util 0.75` > RAM libre | Limpiar Ollama + page cache antes |
| P10 | OpenClaw config | Unknown model error | `models.providers["qwen"]` incorrecto | Usar proveedor `vllm`, no `qwen` |
| P11 | OpenClaw config | ID con prefijo | `"id": "vllm/google/..."` | `"id": "google/..."` (sin prefijo) |
| P12 | OpenClaw config | apiKey literal | `"apiKey": "VLLM_API_KEY"` (nombre de var) | `"apiKey": "vllm-local"` (valor) |
| P13 | OpenClaw config | Typo en nombre | `"primary": "...gemma4-E2B-it"` | `"primary": "...gemma-4-E2B-it"` (con guión) |
| P14 | OpenClaw config | Context overflow | `maxTokens = contextWindow` → 0 tokens para input | `maxTokens: 4096`, `contextWindow: 65536` |
| P15 | OpenClaw config | WhatsApp no responde | `"profile": "coding"` elimina herramienta `message` | `"profile": "full"` |
| P16 | OpenClaw config | Profile inválido | `"profile": "default"` no existe | Válidos: minimal/coding/messaging/**full** |
| P17 | OpenClaw config | Memory search error silencioso | Requiere OpenAI API key | `"memorySearch": {"enabled": false}` |
| P18 | NemoClaw | Repositorio no existe | `jetsonhacks/NemoClaw-Orin` ficticio | `curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash` |
| P19 | NemoClaw | Parches iptables | Solo JP 6.x (kernel 5.15) los necesita | JP 7.2 kernel 6.8: no requiere parches |
| P20 | SSH túnel | `Permission denied (publickey)` | Ejecutado desde Jetson hacia sí mismo | Ejecutar desde Windows PowerShell |
| P21 | Recursos | Modelo fantasma en RAM | `--restart unless-stopped` + vLLM pre-alloca al arrancar | `--restart no` en todos los LLM containers |
| P22 | docker-compose | Imagen x86 | `vllm/vllm-openai:v0.22.0-ubuntu2404` solo x86 | `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` |

---

## APÉNDICE B — PUERTOS Y SERVICIOS

```
Puerto  Servicio          Administrado por    Auto-arranca
:22     SSH               systemd (sshd)      ✅ sí
:3000   Open WebUI        Docker              configurar según necesidad
:3389   XRDP              systemd (xrdp)      ✅ sí
:4000   NoMachine         NX daemon           ✅ sí
:8000   vLLM              Docker (manual)     ❌ NO (restart=no)
:8080   llama.cpp         Docker (manual)     ❌ NO (restart=no)
:11434  Ollama            systemd (ollama)    ✅ sí (pero vacío al arrancar)
:18789  OpenClaw Gateway  systemd user        ✅ sí
```

---

## APÉNDICE C — ESTRUCTURA DE DIRECTORIOS

```
/home/jetson/
├── .bashrc                    ← Exports globales AL INICIO + aliases al final
├── .cache/huggingface/
│   └── token                  ← Token HF cacheado (Docker lo monta con -v)
├── .openclaw/
│   ├── openclaw.json          ← Config principal (validar con python3 -m json.tool)
│   ├── openclaw.json.bak.*    ← Backups automáticos
│   └── workspace/
│       ├── BOOTSTRAP.md       ← Instrucciones del agente (personalizar)
│       ├── IDENTITY.md        ← Auto-generado por OpenClaw
│       └── USER.md            ← Auto-generado por OpenClaw
├── .config/systemd/user/
│   └── openclaw-gateway.service  ← Servicio systemd del gateway
├── .ssh/
│   ├── authorized_keys        ← Claves públicas de Windows
│   ├── config                 ← Config SSH (Host github.com, etc.)
│   └── github_ed25519         ← Clave privada GitHub
├── models/
│   └── hf/                    ← Modelos HuggingFace descargados
│       ├── gemma-4-E2B-it/    ← ~5GB
│       └── gemma-4-E4B-it/    ← ~15GB (del fresh-start)
├── venvs/
│   └── llm/                   ← venv Python 3.12
│       └── bin/
│           ├── activate        ← source ~/venvs/llm/bin/activate
│           ├── python3         ← Python 3.12 propio
│           ├── pip             ← pip propio
│           └── hf              ← CLI de HuggingFace
├── scripts/
│   ├── status.sh              ← alias jstatus
│   ├── jetson-clean.sh        ← alias jetson-clean
│   ├── switch-model.sh        ← aliases mode-*
│   ├── verify-stack.sh        ← alias jetson-verify
│   ├── startup.sh             ← alias jetson-startup
│   └── harden.sh              ← alias jetson-harden
├── projects/
│   ├── jetson-device-skills/  ← git clone NVIDIA-AI-IOT
│   └── jetson-bsp-skills/     ← git clone NVIDIA-AI-IOT
└── .tmux.conf                 ← Config tmux (Ctrl+A como prefijo)
```

---

## APÉNDICE D — DESDE WINDOWS: TODO LO QUE NECESITAS

```powershell
# ── Conectar al Jetson ────────────────────────────────────────────
ssh jetson                                    # con alias en SSH config
ssh jetson@192.168.1.100                      # directo

# ── Túnel para Web UI de OpenClaw ────────────────────────────────
# (mantener esta ventana abierta)
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
# Luego: http://localhost:18789/#token=TOKEN

# ── Verificar conectividad ────────────────────────────────────────
@(22,3389,4000,11434,8000,3000,18789) | ForEach-Object {
    $r = Test-NetConnection -ComputerName 192.168.1.100 -Port $_ -WarningAction SilentlyContinue
    $label = @{22="SSH";3389="XRDP";4000="NoMachine";11434="Ollama";8000="vLLM";3000="OpenWebUI";18789="OpenClaw"}[$_]
    "$label ($_): $(if($r.TcpTestSucceeded){'✅'}else{'❌'})"
}

# ── Copiar archivos al Jetson ─────────────────────────────────────
scp C:\Users\sergi\archivo.pdf jetson:~/
scp C:\Users\sergi\archivo.pdf jetson:~/jetson-ai-data/

# ── Copiar archivos desde el Jetson ──────────────────────────────
scp jetson:~/jetson-ai-data/outputs/resultado.md C:\Users\sergi\

# ── Escritorio remoto ─────────────────────────────────────────────
mstsc /v:192.168.1.100         # XRDP
# NoMachine: abrir cliente → 192.168.1.100:4000

# ── Test Ollama desde PowerShell ─────────────────────────────────
Invoke-RestMethod "http://192.168.1.100:11434/api/tags" |
    Select-Object -ExpandProperty models | Select-Object name

# ── Test vLLM desde PowerShell ───────────────────────────────────
$body = '{"model":"google/gemma-4-E2B-it","messages":[{"role":"user","content":"Hola"}],"max_tokens":50}' | ConvertFrom-Json | ConvertTo-Json
Invoke-RestMethod -Uri "http://192.168.1.100:8000/v1/chat/completions" -Method Post -ContentType "application/json" -Body $body |
    Select-Object -ExpandProperty choices | ForEach-Object {$_.message.content}
```

---

*Versión 3.0 — 2026-06-28 · Jetson AGX Orin 64GB · JetPack 7.2 · OpenClaw 2026.6.10*
*Todos los comandos verificados en producción durante sesión de instalación documentada*
