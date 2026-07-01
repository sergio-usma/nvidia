# Capítulo 5 — Entorno de Shell y Herramientas de Desarrollo

## Introducción

Un entorno de shell bien configurado puede ahorrar horas de trabajo repetitivo durante el ciclo de vida de un proyecto de inferencia: cambiar modos de energía, monitorear memoria, activar entornos virtuales, descargar modelos y diagnosticar problemas de rendimiento. Esta parte construye ese entorno desde cero con todos los elementos necesarios para el trabajo en JetPack 7.2.

**Prerequisito:** Partes 1–4 completadas. Las variables de entorno críticas (`HF_TOKEN`, `CUDA_HOME`, `TORCH_CUDA_ARCH_LIST`) ya deben estar en `~/.bashrc` (configuradas en Capítulo 2, Sección 2.5).

**Tiempo estimado:** 20–30 minutos.

**Al final de esta parte tendrá:**
- Estructura de directorios de trabajo organizada
- `.bashrc` completo con aliases de productividad, monitoreo y modos de energía
- Entorno virtual Python (`~/venvs/llm`) para instalar paquetes sin contaminar el sistema
- `huggingface-hub` instalado (comando `hf` para descargar modelos)
- Herramientas adicionales: `git-lfs`, `aria2`, `ffmpeg`, `nvtop`
- Script de auditoría completa del sistema (`jetson-audit`)

---

## 5.1 Estructura de Directorios de Trabajo

Antes de instalar herramientas, cree la estructura de directorios que usarán los scripts y pipelines del resto del libro:

```bash
# Crear estructura base
mkdir -p ~/scripts                         # scripts de automatización
mkdir -p ~/venvs                           # entornos virtuales Python
mkdir -p ~/projects                        # repos clonados (device skills, etc.)
mkdir -p ~/jetson-ai-data/{outputs,benchmarks,logs}  # datos de trabajo
mkdir -p /var/tmp/openclaw-compile-cache   # caché Node.js para OpenClaw

# Si NVMe está montado en /data (de la Parte 4):
mkdir -p /data/models/{huggingface,gguf,ollama}

# Verificar
ls -la ~/ | grep -E "scripts|venvs|projects|jetson"
```

```
# Salida esperada
drwxrwxr-x  2 jetson jetson  4096 ... jetson-ai-data
drwxrwxr-x  2 jetson jetson  4096 ... projects
drwxrwxr-x  2 jetson jetson  4096 ... scripts
drwxrwxr-x  2 jetson jetson  4096 ... venvs
```

---

## 5.2 Bloque Completo de ~/.bashrc para JetPack 7.2

El archivo `~/.bashrc` ya tiene las variables críticas al inicio (configuradas en Capítulo 2). Ahora se añade el bloque de aliases y funciones de productividad al final del archivo.

> **IMPORTANTE:** Este bloque va al **final** de `~/.bashrc`, después del bloque `case $- in`. Los aliases solo necesitan estar disponibles en shells interactivos, no en Docker ni systemd.

```bash
# Agregar el bloque de aliases al final de ~/.bashrc
cat >> ~/.bashrc << 'ALIASES'

# ════════════════════════════════════════════════════════════════
# JETSON AGX ORIN — Entorno de Desarrollo JP 7.2
# CUDA 13.2.1 | Python 3.12 | sm_87 (Ampere)
# ════════════════════════════════════════════════════════════════

# ── TensorRT y librerías tegra ────────────────────────────────────
export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:$LD_LIBRARY_PATH

# ── Compilación paralela (usa todos los núcleos) ─────────────────
export MAKEFLAGS="-j$(nproc)"
export CMAKE_BUILD_PARALLEL_LEVEL=$(nproc)

# ── HuggingFace (si no está ya en PATH global de la Parte 2) ─────
export HF_HUB_ENABLE_HF_TRANSFER=1    # descargas más rápidas con hf_transfer

# ── Directorios de trabajo ────────────────────────────────────────
export MODELS_DIR="/data/models"       # NVMe; usar ~/models si no hay NVMe
export SCRIPTS_DIR="$HOME/scripts"

# ── venv llm — activar/desactivar rápido ─────────────────────────
alias llm='source ~/venvs/llm/bin/activate && echo "(llm) venv activo"'
alias da='deactivate 2>/dev/null && echo "venv desactivado"'

# ── Modos de energía ──────────────────────────────────────────────
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MAXN: 50W + frecuencias bloqueadas"'
alias pwr-30w='sudo nvpmodel -m 2 && sudo jetson_clocks && echo "30W activo"'
alias pwr-15w='sudo nvpmodel -m 3 && sudo jetson_clocks --restore && echo "15W — bajo consumo"'
alias pwr-status='sudo nvpmodel -q 2>/dev/null | grep -v WARN'

# ── Monitoreo rápido ──────────────────────────────────────────────
alias jtop='sudo jtop'
alias stats='tegrastats --interval 1000'
alias temps='paste <(cat /sys/class/thermal/thermal_zone*/type 2>/dev/null) <(awk "{printf \"%.1f°C\n\", \$1/1000}" /sys/class/thermal/thermal_zone*/temp 2>/dev/null)'
alias jetson-mem='free -h | awk "/^Mem:/{print \"RAM: \"\$3\" usados / \"\$2\" total / \"\$7\" libres\"}" && echo "" && swapon --show'

# ── Contenedores Docker ───────────────────────────────────────────
alias dps='docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
alias dstats='docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"'
alias dlogs='docker logs -f --tail 50'

# ── Sistema de archivos ───────────────────────────────────────────
alias ls='ls --color=auto'
alias ll='ls -alFh --color=auto'
alias la='ls -A --color=auto'
alias ..='cd ..'
alias ...='cd ../..'
alias mkdir='mkdir -pv'
alias disk='df -h | grep -Ev "tmpfs|loop|udev"'
alias ports='ss -tulnp'

# ── Git ───────────────────────────────────────────────────────────
alias gs='git status'
alias gd='git diff'
alias gl='git log --oneline -15 --graph'
alias gp='git pull'

# ── Actualización del sistema ─────────────────────────────────────
alias update='sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y'

# ── Sesiones tmux ────────────────────────────────────────────────
alias tm='tmux attach -t main 2>/dev/null || tmux new-session -s main'
alias tm-llm='tmux attach -t llm 2>/dev/null || tmux new-session -s llm'

# ── Auditoría completa del sistema ───────────────────────────────
jetson-audit() {
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║            AUDITORÍA — JETSON AGX ORIN              ║"
    echo "╚══════════════════════════════════════════════════════╝"

    echo ""
    echo "── [1] Modo de energía ──"
    sudo nvpmodel -q 2>/dev/null | grep -v WARN

    echo ""
    echo "── [2] Memoria ──"
    free -h | awk '/^Mem:/{print "  RAM: "$3" usados / "$2" total / "$7" libres"}'
    swapon --show | awk 'NR>1{print "  Swap:", $1, $3, "PRIO="$5}'

    echo ""
    echo "── [3] Contenedores activos ──"
    docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null || echo "  (Docker no activo)"

    echo ""
    echo "── [4] Consumo RAM por contenedor ──"
    docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}} ({{.MemPerc}})" 2>/dev/null || echo "  (sin contenedores)"

    echo ""
    echo "── [5] Modelos Ollama en GPU ──"
    ollama ps 2>/dev/null | tail -n +2 || echo "  Ollama offline / vacío"

    echo ""
    echo "── [6] Endpoints de inferencia ──"
    curl -s http://localhost:8000/v1/models 2>/dev/null | \
      python3 -c "import sys,json; [print('  vLLM:8000 →',m['id']) for m in json.load(sys.stdin)['data']]" \
      2>/dev/null || echo "  vLLM:8000 → offline"
    curl -s http://localhost:8080/v1/models 2>/dev/null | \
      python3 -c "import sys,json; [print('  llama.cpp:8080 →',m['id']) for m in json.load(sys.stdin)['data']]" \
      2>/dev/null || echo "  llama.cpp:8080 → offline"
    curl -s http://localhost:11434/api/version 2>/dev/null | \
      python3 -c "import sys,json; print('  Ollama:11434 → v'+json.load(sys.stdin).get('version','?'))" \
      2>/dev/null || echo "  Ollama:11434 → offline"

    echo ""
    echo "── [7] Temperatura ──"
    paste \
      <(cat /sys/class/thermal/thermal_zone*/type 2>/dev/null) \
      <(awk '{printf "%.1f°C\n", $1/1000}' /sys/class/thermal/thermal_zone*/temp 2>/dev/null) \
      | grep -E "CPU|GPU|Board|PMIC|thermal" | head -6 | sed 's/^/  /'

    echo ""
    echo "── [8] Política de restart de contenedores ──"
    docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
    for c in json.load(sys.stdin):
        n = c['Name'].lstrip('/')
        p = c['HostConfig']['RestartPolicy']['Name']
        s = c['State']['Status']
        flag = '[WARN]  AUTO' if p in ['always','unless-stopped'] else '[OK] manual'
        print(f'  {flag}  {n}: restart={p} ({s})')
except: print('  Sin contenedores')
" 2>/dev/null || echo "  (Docker no activo)"

    echo ""
    echo "══════════════════════════════════════════════════════"
}

# ── Bienvenida al abrir terminal (status rápido) ──────────────────
if [[ $- == *i* ]]; then
    POWER_MODE=$(sudo nvpmodel -q 2>/dev/null | grep "NV Power Mode" | awk '{print $NF}')
    RAM_FREE=$(free -h | awk '/^Mem:/{print $7}')
    echo "Jetson AGX Orin 64GB | JP 7.2 | Modo: ${POWER_MODE:-?} | Libre: ${RAM_FREE}"
fi

# ── Deduplicar PATH (evita bloat en recargas sucesivas) ──────────
export PATH=$(echo -n "$PATH" | awk -v RS=: -v ORS=: '!x[$0]++' | sed 's/:$//')

ALIASES

source ~/.bashrc
echo "[OK] Bloque de aliases cargado"
```

Verifique que los aliases están disponibles:

```bash
# Probar algunos aliases
pwr-status         # muestra modo de energía
jetson-mem         # muestra estado de memoria
disk               # muestra disco sin tmpfs/loops
```

```
# Salida esperada de pwr-status
NV Power Mode: MAXN
0

# Salida esperada de jetson-mem
RAM: 12Gi usados / 62Gi total / 50Gi libres

NAME            TYPE      SIZE USED PRIO
/dev/zram0      partition 7.8G   0B  100
/data/swapfile  file       16G   0B   -2
```

---

## 5.3 Herramientas Adicionales de Desarrollo

Algunas herramientas no se instalaron en el Capítulo 1 porque no eran críticas para el primer arranque. Instálelas ahora:

```bash
# Herramientas de desarrollo multimedia y descarga
sudo apt install -y \
  git-lfs \
  aria2 \
  ffmpeg \
  nvtop \
  iotop \
  p7zip-full \
  lm-sensors \
  rsync \
  libopenblas-dev liblapack-dev \
  libopenmpi-dev libomp-dev \
  portaudio19-dev libsndfile1-dev \
  libjpeg-dev libpng-dev libtiff-dev libwebp-dev \
  libavcodec-dev libavformat-dev libswscale-dev
```

**Por qué cada grupo:**

| Herramienta | Uso |
|-------------|-----|
| `git-lfs` | Clonar repositorios con modelos y archivos grandes en Git LFS |
| `aria2` | Descargas paralelas de modelos grandes (hasta 16 hilos simultáneos) |
| `ffmpeg` | Procesamiento de audio para Whisper STT y video para modelos multimodales |
| `nvtop` | Monitor de GPU alternativo a jtop (vista estilo `top` para procesos GPU) |
| `libopenblas-dev` | Álgebra lineal — requerido para compilar PyTorch y llama.cpp |
| `portaudio19-dev` | Captura de audio en tiempo real para pipelines de voz |
| `libavcodec-dev` | Codecs de video para FFmpeg Python bindings |

```bash
# Inicializar git-lfs
git lfs install
echo "[OK] git-lfs inicializado"
```

---

## 5.4 Entorno Virtual Python — venv `llm`

Ubuntu 24.04 protege su instalación de Python del sistema y bloquea `pip install` global con el error `externally-managed-environment`. La solución es crear un entorno virtual aislado donde puede instalar lo que necesite sin riesgo de romper el sistema.

### 5.4.1 Qué es y para qué sirve el venv `llm`

```
~/venvs/llm/                 ← directorio del entorno virtual
├── bin/python3              ← Python 3.12 propio (copia del sistema)
├── bin/pip                  ← pip propio para este entorno
├── bin/hf                   ← comando para descargar modelos HuggingFace
├── lib/python3.12/
│   └── site-packages/
│       ├── torch/           ← PyTorch compilado para CUDA 13, sm_87 (Parte 11)
│       ├── torchvision/     ← compilado desde fuente para sm_87 (Parte 11)
│       ├── huggingface_hub/ ← cliente HF para descargar modelos
│       └── numpy, requests, ...
```

**Cuándo activar el venv:**
- Antes de `pip install` de cualquier paquete
- Antes de ejecutar scripts Python que usen PyTorch
- Antes de `hf download` o `hf auth login`
- Al ejecutar Jetson Device Skills o BSP Skills (Capítulo 13)

**Cuándo NO es necesario:**
- Comandos Docker (`docker run`, `docker ps`, etc.)
- Ollama (`ollama run`, `ollama pull`)
- OpenClaw (`openclaw`, `claw-*`)
- Comandos de sistema (`ssh`, `tmux`, `git`, `curl`, `htop`)

### 5.4.2 Crear el venv

```bash
# Verificar Python 3.12 disponible
python3 --version
```

```
# Salida esperada
Python 3.12.3
```

```bash
# Crear el entorno virtual
python3 -m venv ~/venvs/llm

# Activar
source ~/venvs/llm/bin/activate
```

El prompt cambia al activar:

```
(llm) jetson@jetson-orin:~$    ← venv activo
```

```bash
# Actualizar pip dentro del venv
pip install --upgrade pip setuptools wheel
```

```
# Salida esperada
Successfully installed pip-24.x.x setuptools-xx.x.x wheel-0.x.x
```

### 5.4.3 Instalar paquetes base

```bash
# Paquetes esenciales en el venv llm
# (con el venv activo — el prompt muestra "(llm)")
pip install \
  huggingface-hub \
  hf-transfer \
  requests \
  numpy \
  pillow \
  tqdm \
  rich

echo "[OK] Paquetes base instalados"
```

**Tiempo estimado:** 2–3 minutos.

> **NOTA:** PyTorch y torchvision se instalan en el Capítulo 11, porque requieren wheels específicos de JetPack 7.2 que no están en PyPI. No intente `pip install torch` desde PyPI — descargará la versión x86_64 que no funciona en arm64.

### 5.4.4 Autenticar HuggingFace en el venv

```bash
# Con el venv activo, autenticar con el token configurado en Parte 2
#
hf auth login --token "$HF_TOKEN"
```

```
# Salida esperada
Token is valid (scope: read).
Your token has been saved to /home/jetson/.cache/huggingface/token
Login successful
```

```bash
# Verificar el comando hf
hf --version
hf whoami
```

```
# Salida esperada
huggingface_hub 0.x.x
Tu-usuario-de-HuggingFace
```

```bash
# Desactivar el venv
deactivate
```

---

## 5.5 Script de Auditoría Completa del Sistema

La función `jetson-audit` ya está en `~/.bashrc` (sección 5.2). Pruébela ahora para verificar el estado base del sistema antes de instalar los componentes de inferencia:

```bash
# Ejecutar auditoría completa
jetson-audit
```

```
# Salida esperada (sistema limpio, sin modelos)
╔══════════════════════════════════════════════════════╗
║            AUDITORÍA — JETSON AGX ORIN              ║
╚══════════════════════════════════════════════════════╝

── [1] Modo de energía ──
NV Power Mode: MAXN
0

── [2] Memoria ──
  RAM: 11Gi usados / 62Gi total / 51Gi libres
  Swap: /dev/zram0 7.8G PRIO=100
  Swap: /data/swapfile 16G PRIO=-2

── [3] Contenedores activos ──
  (Docker no activo)

── [4] Consumo RAM por contenedor ──
  (sin contenedores)

── [5] Modelos Ollama en GPU ──
  Ollama offline / vacío

── [6] Endpoints de inferencia ──
  vLLM:8000 → offline
  llama.cpp:8080 → offline
  Ollama:11434 → offline

── [7] Temperatura ──
  CPU-therm   52.8°C
  GPU-therm   48.2°C
  Tboard      42.5°C

── [8] Política de restart de contenedores ──
  Sin contenedores

══════════════════════════════════════════════════════
```

Un sistema en estado limpio muestra ~51 GB libres, sin contenedores activos y todos los endpoints offline — exactamente lo que se busca antes de elegir qué modelo cargar.

---

## 5.6 Verificación Final del Capítulo

```bash
# Verificación completa del entorno de shell
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     VERIFICACIÓN CAPÍTULO 5 — RESULTADO         ║"
echo "╚══════════════════════════════════════════════╝"

echo ""
echo "── Aliases cargados ──"
alias llm       2>/dev/null && echo "[OK] alias llm (activar venv)"   || echo "[ERROR] alias llm"
alias jetson-mem 2>/dev/null && echo "[OK] alias jetson-mem"           || echo "[ERROR] alias jetson-mem"
alias pwr-maxn  2>/dev/null && echo "[OK] alias pwr-maxn"             || echo "[ERROR] alias pwr-maxn"
type jetson-audit 2>/dev/null | head -1 && echo "[OK] función jetson-audit" || echo "[ERROR] jetson-audit"

echo ""
echo "── Herramientas adicionales ──"
which aria2c && aria2c --version | head -1   || echo "[ERROR] aria2 no instalado"
which git-lfs && git lfs version             || echo "[ERROR] git-lfs no instalado"
which ffmpeg  && ffmpeg -version 2>&1 | head -1 || echo "[ERROR] ffmpeg no instalado"

echo ""
echo "── venv llm ──"
ls ~/venvs/llm/bin/activate 2>/dev/null \
  && echo "[OK] venv existe en ~/venvs/llm" \
  || echo "[ERROR] venv no creado"
ls ~/venvs/llm/bin/hf 2>/dev/null \
  && echo "[OK] comando hf disponible" \
  || echo "[WARN]  hf no en venv (instalar con: pip install huggingface-hub)"

echo ""
echo "── HuggingFace token ──"
[ -f ~/.cache/huggingface/token ] \
  && echo "[OK] Token HF cacheado: $(head -c 15 ~/.cache/huggingface/token)..." \
  || echo "[WARN]  Token HF no cacheado (ejecutar: hf auth login)"

echo ""
echo "── Variables de entorno ──"
echo "  MAKEFLAGS:           ${MAKEFLAGS}"
echo "  TORCH_CUDA_ARCH:     ${TORCH_CUDA_ARCH_LIST}"
echo "  HF_HUB_ENABLE_HF_TRANSFER: ${HF_HUB_ENABLE_HF_TRANSFER}"
```

```
# Salida esperada
╔══════════════════════════════════════════════╗
║     VERIFICACIÓN CAPÍTULO 5 — RESULTADO         ║
╚══════════════════════════════════════════════╝

── Aliases cargados ──
[OK] alias llm (activar venv)
[OK] alias jetson-mem
[OK] alias pwr-maxn
jetson-audit is a function
[OK] función jetson-audit

── Herramientas adicionales ──
/usr/bin/aria2c
aria2 version 1.37.0
/usr/bin/git-lfs
git-lfs/3.x.x (GitHub; linux arm64; ...)
/usr/bin/ffmpeg
ffmpeg version 6.1.1 ...

── venv llm ──
[OK] venv existe en ~/venvs/llm
[OK] comando hf disponible

── HuggingFace token ──
[OK] Token HF cacheado: hf_oauth_xxxxxxx...

── Variables de entorno ──
  MAKEFLAGS:           -j12
  TORCH_CUDA_ARCH:     8.7
  HF_HUB_ENABLE_HF_TRANSFER: 1
```

| Error | Causa | Solución |
|-------|-------|---------|
| Aliases no disponibles | `source ~/.bashrc` no ejecutado | `source ~/.bashrc` |
| `venv no creado` | Paso 5.4.2 omitido | `python3 -m venv ~/venvs/llm` |
| `hf` no en venv | huggingface-hub no instalado | Activar venv + `pip install huggingface-hub` |
| `MAKEFLAGS` vacío | Bloque de aliases no pegado correctamente | Verificar el final de `~/.bashrc` |

> **Próximo paso:** El Capítulo 6 optimiza la red para maximizar la velocidad de descarga de modelos grandes — crítico cuando el modelo más pequeño de los 10 pesa 4 GB y el mayor llega a 26 GB.
