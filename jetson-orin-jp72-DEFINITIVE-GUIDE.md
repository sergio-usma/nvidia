# NVIDIA Jetson AGX Orin 64GB — JetPack 7.2
# Guía Definitiva: Agente IA de Producción con OpenClaw

> **Estado:** Verificado en producción · 2026-06-28
> **Hardware:** Jetson AGX Orin 64GB · JetPack 7.2-b187 · L4T r39.2 · Ubuntu 24.04
> **Objetivo:** Agente personal completamente automatizado — agencia de turismo, generación de podcasts, notas de conferencias, atención al cliente por WhatsApp

---

## TARJETA DE REFERENCIA RÁPIDA

```
IP JETSON:   192.168.1.100 (estática)
IP WINDOWS:  192.168.1.33
SSH:         jetson@192.168.1.100
OPENCLAW UI: http://localhost:18789   (desde Windows, con túnel SSH activo)

COMANDOS DE USO DIARIO:
  jetson-audit         → qué hay en memoria ahora mismo
  jetson-clean         → limpiar todo antes de un workload pesado
  mode-openclaw        → agente WhatsApp (Gemma 4 E2B / vLLM, 30W)
  mode-lite            → mismo modelo, llama.cpp, menor RAM, 30W
  mode-longdoc         → Nemotron3 30B / vLLM, documentos largos, MAXN
  mode-multimodal      → Nemotron Omni / llama.cpp, audio+video, MAXN
  mode-idle            → apagar todo, 15W

MODELOS Y SUS CARACTERÍSTICAS:
  google/gemma-4-E2B-it          → ~32 tok/s · 15GB · texto+imagen · 128K ctx
  google/gemma-4-E2B-it (GGUF)   → ~35 tok/s · 3.5GB · texto · 32K ctx
  Nemotron3-30B-A3B-AWQ          → ~38 tok/s · 26GB · texto · 256K ctx
  Nemotron-Omni (GGUF Q4_K_M)   → ~39 tok/s · 24GB · texto+img+audio+video · 256K ctx

PUERTOS:
  8000  → vLLM (OpenAI-compatible API)
  8080  → llama.cpp (OpenAI-compatible API)
  11434 → Ollama
  18789 → OpenClaw Gateway + Web UI
  22    → SSH
  3389  → XRDP
  4000  → NoMachine
```

---

## Índice

**Parte 1 — Fundación del sistema**
- [1.1 Hardware y capacidades](#11-hardware-y-capacidades)
- [1.2 Acceso remoto desde Windows](#12-acceso-remoto-desde-windows)
- [1.3 Variables de entorno (configuración permanente)](#13-variables-de-entorno-configuración-permanente)
- [1.4 Token de Hugging Face (solución definitiva)](#14-token-de-hugging-face-solución-definitiva)

**Parte 2 — Dominio de recursos**
- [2.1 Por qué la Jetson es diferente a todo lo demás](#21-por-qué-la-jetson-es-diferente-a-todo-lo-demás)
- [2.2 Modos de energía](#22-modos-de-energía)
- [2.3 Presupuesto de memoria por modelo](#23-presupuesto-de-memoria-por-modelo)
- [2.4 Auditoría completa de recursos](#24-auditoría-completa-de-recursos)
- [2.5 Limpieza exhaustiva](#25-limpieza-exhaustiva)
- [2.6 Hardening de producción (ejecutar una sola vez)](#26-hardening-de-producción-ejecutar-una-sola-vez)
- [2.7 Aliases maestros de gestión de recursos](#27-aliases-maestros-de-gestión-de-recursos)

**Parte 3 — Backends de inferencia**
- [3.1 Guía de selección de modelo](#31-guía-de-selección-de-modelo)
- [3.2 Backend A: Gemma 4 E2B via vLLM (agente por defecto)](#32-backend-a-gemma-4-e2b-via-vllm)
- [3.3 Backend B: Gemma 4 E2B via llama.cpp (bajo consumo)](#33-backend-b-gemma-4-e2b-via-llamacpp)
- [3.4 Backend C: Nemotron3 30B-A3B via vLLM (documentos largos)](#34-backend-c-nemotron3-30b-a3b-via-vllm)
- [3.5 Backend D: Nemotron Omni via llama.cpp (multimodal)](#35-backend-d-nemotron-omni-via-llamacpp)
- [3.6 Script switcher de modelos](#36-script-switcher-de-modelos)

**Parte 4 — OpenClaw: instalación y configuración**
- [4.1 Instalación de OpenClaw](#41-instalación-de-openclaw)
- [4.2 Configuración completa verificada](#42-configuración-completa-verificada)
- [4.3 Canal WhatsApp](#43-canal-whatsapp)
- [4.4 Web UI desde Windows](#44-web-ui-desde-windows)
- [4.5 Gestión del gateway](#45-gestión-del-gateway)

**Parte 5 — Operaciones de producción**
- [5.1 Secuencia de arranque tras reboot](#51-secuencia-de-arranque-tras-reboot)
- [5.2 Checklist pre-workload](#52-checklist-pre-workload)
- [5.3 Monitoreo y watchdog](#53-monitoreo-y-watchdog)
- [5.4 Recuperación de OOM](#54-recuperación-de-oom)

**Parte 6 — Workflows de casos de uso**
- [6.1 Agencia de turismo automatizada](#61-agencia-de-turismo-automatizada)
- [6.2 Podcast desde PDF de 100MB+](#62-podcast-desde-pdf-de-100mb)
- [6.3 Grabaciones → notas y presentaciones](#63-grabaciones--notas-y-presentaciones)
- [6.4 Atención al cliente por WhatsApp](#64-atención-al-cliente-por-whatsapp)
- [6.5 Generación de contenido](#65-generación-de-contenido)

**Apéndice**
- [A. Registro de patches verificados](#a-registro-de-patches-verificados)
- [B. Estructura de directorios](#b-estructura-de-directorios)
- [C. Checklist de verificación del stack completo](#c-checklist-de-verificación-del-stack-completo)

---

# PARTE 1 — FUNDACIÓN DEL SISTEMA

## 1.1 Hardware y capacidades

```
┌─────────────────────────────────────────────────────────────────┐
│           NVIDIA Jetson AGX Orin Developer Kit                  │
├─────────────────┬───────────────────────────────────────────────┤
│ GPU             │ Orin nvgpu · Ampere sm_87 · 2048 CUDA cores   │
│ CPU             │ ARM Cortex-A78AE · 12 cores (8 online) 2.2GHz │
│ RAM             │ 64 GB LPDDR5 ECC (UNIFICADA CPU+GPU)          │
│ SSD             │ 931.5 GB NVMe (modelos y datos)               │
│ eMMC            │ 59.2 GB (sistema operativo)                   │
│ AI Performance  │ 275 TOPS (modo MAXN)                          │
├─────────────────┼───────────────────────────────────────────────┤
│ JetPack         │ 7.2-b187                                       │
│ L4T             │ r39.2 (Jetson Linux 39.2)                     │
│ OS              │ Ubuntu 24.04.4 LTS                             │
│ Kernel          │ 6.8.12-1021-tegra                             │
│ CUDA            │ 13.2.1 (sm_87)                                │
│ TensorRT        │ 10.16.2                                        │
│ Python          │ 3.12.3                                         │
│ Docker          │ runtime=nvidia (default)                      │
│ Node.js         │ v22.23.1                                      │
├─────────────────┼───────────────────────────────────────────────┤
│ IP Jetson       │ 192.168.1.100 (estática)                      │
│ IP Windows      │ 192.168.1.33                                  │
│ SSH             │ :22 key-based                                 │
│ NoMachine       │ :4000 virtual XFCE4                           │
│ XRDP            │ :3389 (Windows mstsc)                         │
│ Display         │ Xorg dummy 1920×1080 (headless)               │
│ Boot            │ multi-user.target (sin GDM)                   │
└─────────────────┴───────────────────────────────────────────────┘
```

> **JP 7.2 SBSA:** A diferencia de JP 6.x (Tegra-specific), JP 7.2 usa el stack SBSA (Server Base System Architecture) unificado con Ubuntu 24.04 y kernel 6.8. Esto significa que contenedores arm64 SBSA estándar corren nativamente, eliminando los parches de iptables-legacy que eran necesarios en JP 6.x.

---

## 1.2 Acceso remoto desde Windows

### SSH básico

```powershell
# PowerShell en Windows
ssh jetson@192.168.1.100
# Contraseña del sistema o clave SSH
```

### Configurar acceso por clave (recomendado — sin contraseña)

```powershell
# En PowerShell de Windows — generar clave si no existe
ssh-keygen -t ed25519 -C "windows-to-jetson"

# Copiar clave pública al Jetson
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh jetson@192.168.1.100 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# Verificar que funciona sin contraseña
ssh jetson@192.168.1.100 "echo OK"
```

### Túnel SSH para el Web UI de OpenClaw

> ⚠️ **Error común:** El comando del túnel se ejecuta **DESDE WINDOWS**, no desde el Jetson. Ejecutarlo desde el Jetson hacia sí mismo produce `Permission denied (publickey)`.

```powershell
# WINDOWS PowerShell — mantener esta ventana abierta mientras uses el Web UI
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

Luego abrir en el navegador de Windows:
```
http://localhost:18789/#token=TU_TOKEN_AQUI
```

Obtener el token:
```bash
# En el Jetson
openclaw config get gateway.auth.token
```

### Alternativa: NoMachine (escritorio completo)

Si NoMachine está corriendo (`:4000`), abrir NoMachine en Windows, conectar a `192.168.1.100`, y abrir un navegador dentro de esa sesión en `http://127.0.0.1:18789`.

---

## 1.3 Variables de entorno (configuración permanente)

### El problema con ~/.bashrc

El `HF_TOKEN` en `~/.bashrc` estaba definido **después** del bloque `case $- in *i*)`. Ese bloque hace un `return` temprano para shells no-interactivos (Docker, systemd, cron, scripts). Resultado: el token nunca se exporta en ningún contexto automatizado.

### Solución definitiva — editar ~/.bashrc

Abrir con `micro ~/.bashrc` y mover estas líneas al **principio del archivo**, antes de cualquier otro bloque:

```bash
# ── EXPORTS: DEBEN ESTAR AL INICIO (antes del bloque case $- in) ──
export HF_TOKEN="hf_oauth_TU_TOKEN_COMPLETO"
export HUGGING_FACE_HUB_TOKEN="hf_oauth_TU_TOKEN_COMPLETO"
export VLLM_API_KEY="none"
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export PATH="$HOME/.npm-global/bin:$PATH"
export PATH="$PATH:$HOME/.local/bin"
export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache
export OPENCLAW_NO_RESPAWN=1
# ─────────────────────────────────────────────────────────────────
```

Después del bloque interactivo, pueden quedar los aliases, completions, etc.

---

## 1.4 Token de Hugging Face (solución definitiva)

Ejecutar estos tres pasos una sola vez:

```bash
# Paso 1: Caché en disco (lo usan los volúmenes Docker)
source ~/.bashrc
hf auth login --token $HF_TOKEN
cat ~/.cache/huggingface/token  # verificar: debe mostrar hf_oauth_...

# Paso 2: /etc/environment (systemd + Docker daemon, sin export, sin comillas)
HF_VAL=$(cat ~/.cache/huggingface/token)
echo "HF_TOKEN=${HF_VAL}" | sudo tee -a /etc/environment
echo "HUGGING_FACE_HUB_TOKEN=${HF_VAL}" | sudo tee -a /etc/environment
# Limpiar si hay líneas placeholder de sesiones anteriores:
sudo sed -i '/hf_YOUR_TOKEN_HERE/d' /etc/environment
grep HF /etc/environment  # verificar: solo aparece el token real

# Paso 3: Verificar en contexto Docker (el más importante)
docker run --rm \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cat /root/.cache/huggingface/token | head -c 15 && echo '...OK'"
```

Con esto, **ningún contenedor necesita `-e HF_TOKEN`** — el volumen mount lleva el token automáticamente.

---

# PARTE 2 — DOMINIO DE RECURSOS

## 2.1 Por qué la Jetson es diferente a todo lo demás

```
GPU discreta normal (RTX 4090, etc.):
  ┌────────────┐     ┌──────────────────────────────┐
  │   CPU RAM  │     │           VRAM 24GB           │
  │   32–64GB  │     │  (solo GPU, completamente     │
  │  (solo CPU)│     │   separada del sistema)       │
  └────────────┘     └──────────────────────────────┘
  Si el modelo llena la VRAM → OOM en GPU → proceso muere
  Sistema operativo sigue funcionando con normalidad

Jetson AGX Orin 64GB:
  ┌─────────────────────────────────────────────────────────────┐
  │                  POOL UNIFICADO: 64 GB                      │
  │  OS (~3GB) │ OpenClaw (~0.5GB) │ LLM pesos │ KV cache LLM  │
  │  Page cache│ Docker overhead   │ CUDA ctx  │ Buffers        │
  └─────────────────────────────────────────────────────────────┘
  Si el modelo llena el pool → OOM en sistema → TODO SE CONGELA
  No hay separación: un OOM puede requerir apagado físico
```

### Los tres tipos de "modelos fantasma"

**Tipo 1: Contenedor Docker con restart policy automática**
```bash
# Al usar --restart unless-stopped, el contenedor sobrevive reboots
# vLLM reserva gpu_memory_utilization × 64GB EN EL MOMENTO DE ARRANCAR
# No cuando llega la primera petición — al segundo de iniciar el contenedor
# Ejemplo: --gpu-memory-utilization 0.55 → 35GB reservados inmediatamente

# DETECCIÓN:
docker ps
docker stats --no-stream
```

**Tipo 2: Ollama con keep_alive**
```bash
# Ollama mantiene modelos en VRAM por defecto 5 minutos tras el último uso
# Open-WebUI trigger: solo abrir la interfaz y hacer clic en un modelo → CARGADO

# DETECCIÓN:
ollama ps  # muestra modelos en GPU en este momento
```

**Tipo 3: Linux page cache de archivos de modelo**
```bash
# Después de cargar un modelo, el kernel cachea sus archivos en RAM
# Puede ocupar 2–10GB adicionales que free -h muestra como "buff/cache"

# DETECCIÓN:
free -h
# La columna buff/cache grande indica esto

# SOLUCIÓN:
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

---

## 2.2 Modos de energía

```bash
# Ver modo actual
sudo nvpmodel -q

# Cambiar modo (efecto inmediato, sin reboot)
sudo nvpmodel -m 0   # MAXN   — 50W, 12 cores CPU, GPU a máxima frecuencia
sudo nvpmodel -m 1   # 15W    — 4 cores CPU, frecuencias reducidas
sudo nvpmodel -m 2   # 30W    — 8 cores CPU
sudo nvpmodel -m 3   # 50W    — 12 cores CPU (alias de MAXN en algunos builds)

# Activar frecuencias máximas después de cambiar modo
sudo jetson_clocks

# Restaurar frecuencias por defecto (menos ruido, menos consumo)
sudo jetson_clocks --restore
```

### Tabla de decisión por workload

| Workload | Modo | Watts reales | Tok/s aprox | Costo Colombia (~$0.07/kWh) |
|---|---|---|---|---|
| Sistema solo / idle | 15W | ~8W | — | ~$0.41/mes |
| Gemma 4 E2B (vLLM o llama.cpp) | 30W | ~25W | ~32–35 | ~$1.29/mes |
| Nemotron3 30B-A3B (vLLM) | MAXN | ~45W | ~38 | ~$2.32/mes |
| Nemotron Omni (llama.cpp) | MAXN | ~45W | ~39 | ~$2.32/mes |

> Costo mensual = Watts × 24h × 30 días / 1000 × tarifa kWh

---

## 2.3 Presupuesto de memoria por modelo

```
POOL TOTAL: 64 GB
─────────────────────────────────────────────────────────────
Reservas fijas:
  OS Ubuntu 24.04 + kernel:           ~2.0 GB
  Docker daemon + containerd:          ~0.3 GB
  OpenClaw gateway + Node.js:          ~0.5 GB
  Procesos del sistema (ssh, etc.):    ~0.2 GB
  TOTAL FIJO:                         ~3.0 GB

DISPONIBLE PARA INFERENCIA:          ~61 GB
─────────────────────────────────────────────────────────────

Backend A — Gemma 4 E2B / vLLM (bfloat16):
  Pesos del modelo:                    ~4.6 GB
  Reserva KV cache (util=0.55):       ~33 GB
  TOTAL:                              ~15 GB usados efectivamente
  LIBRE:                              ~49 GB

Backend B — Gemma 4 E2B / llama.cpp (GGUF Q4_K_S):
  Pesos del modelo:                    ~2.5 GB
  KV cache (ctx 32768):                ~1.0 GB
  TOTAL:                               ~3.5 GB
  LIBRE:                              ~57 GB  ← máxima disponibilidad

Backend C — Nemotron3 30B-A3B / vLLM (AWQ W4A16):
  Pesos del modelo:                   ~17 GB
  Reserva KV cache (util=0.80):       ~49 GB → limitado a ctx disponible
  TOTAL:                              ~26 GB
  LIBRE:                              ~35 GB

Backend D — Nemotron Omni / llama.cpp (GGUF Q4_K_M):
  Pesos del modelo:                   ~20 GB
  KV cache (ctx 8192):                ~4 GB
  TOTAL:                              ~24 GB
  LIBRE:                              ~37 GB
─────────────────────────────────────────────────────────────

REGLA DE ORO: free -h → 'available' debe ser >50GB antes de iniciar
NUNCA: dos backends corriendo simultáneamente
```

---

## 2.4 Auditoría completa de recursos

Instalar primero:

```bash
# jtop: monitor visual de Jetson (obligatorio)
sudo pip3 install jetson-stats --break-system-packages
sudo systemctl restart jtop.service 2>/dev/null || sudo reboot
# Uso: jtop (presiona g=GPU, m=Memoria, p=Procesos, q=salir)
```

Comandos de auditoría:

```bash
# ── VISTA RÁPIDA ─────────────────────────────────────────────────
# ¿Qué está corriendo?
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}"

# ¿Cuánta RAM consume cada contenedor?
docker stats --no-stream --format \
  "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# ¿Qué modelos de Ollama están en GPU ahora mismo?
ollama ps

# ¿Cuánta RAM libre hay en el sistema?
free -h

# ── VISTA DETALLADA ───────────────────────────────────────────────
# ¿Qué endpoints de inferencia están activos?
curl -s http://localhost:8000/v1/models 2>/dev/null | \
  python3 -c "import sys,json; [print('vLLM:8000 →', m['id']) for m in json.load(sys.stdin)['data']]" \
  2>/dev/null || echo "vLLM:8000 → offline"

curl -s http://localhost:8080/v1/models 2>/dev/null | \
  python3 -c "import sys,json; [print('llama.cpp:8080 →', m['id']) for m in json.load(sys.stdin)['data']]" \
  2>/dev/null || echo "llama.cpp:8080 → offline"

curl -s http://localhost:11434/api/tags 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); [print('Ollama → loaded:', m['name']) for m in d.get('models',[])]" \
  2>/dev/null || echo "Ollama:11434 → offline"

# ¿Qué política de restart tienen los contenedores?
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
    cs = json.load(sys.stdin)
    for c in cs:
        name = c['Name'].lstrip('/')
        policy = c['HostConfig']['RestartPolicy']['Name']
        status = c['State']['Status']
        flag = '⚠️ AUTO-STARTS' if policy in ['always','unless-stopped'] else '✓ manual'
        print(f'{flag}  {name:30} restart={policy} ({status})')
except: pass
" 2>/dev/null || echo "Sin contenedores"

# ── HARDWARE RAW ─────────────────────────────────────────────────
# Consumo real de hardware (2 muestras, 2 segundos)
sudo tegrastats --interval 2000 &
sleep 5
kill %1 2>/dev/null
```

---

## 2.5 Limpieza exhaustiva

```bash
cat > ~/scripts/jetson-clean.sh << 'CLEAN'
#!/bin/bash
# LIMPIEZA TOTAL — ejecutar antes de cualquier workload exigente

echo ""
echo "╔══════════════════════════════════════╗"
echo "║    LIMPIEZA JETSON AGX ORIN 64GB     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Contenedores Docker ────────────────────────────────────────
echo "→ Deteniendo contenedores de inferencia..."
docker stop vllm-openclaw llama-openclaw 2>/dev/null && echo "  ✓ Contenedores LLM detenidos" || echo "  ✓ No había contenedores LLM"

echo "→ Deteniendo Open-WebUI..."
docker stop open-webui 2>/dev/null && echo "  ✓ Open-WebUI detenido" || echo "  ✓ Open-WebUI no estaba activo"

# ── 2. Ollama ────────────────────────────────────────────────────
echo "→ Descargando modelos de Ollama de la memoria..."
LOADED=$(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}')
if [ -n "$LOADED" ]; then
  for model in $LOADED; do
    curl -s http://localhost:11434/api/generate \
      -d "{\"model\": \"$model\", \"keep_alive\": 0}" > /dev/null 2>&1
    echo "  ✓ Descargado: $model"
  done
else
  echo "  ✓ No había modelos Ollama cargados"
fi

echo "→ Deteniendo servicio Ollama..."
sudo systemctl stop ollama 2>/dev/null && echo "  ✓ Ollama detenido" || echo "  ✓ Ollama no estaba activo"

# ── 3. Caché del kernel ──────────────────────────────────────────
echo "→ Liberando caché de páginas del kernel..."
sudo sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
echo "  ✓ Caché liberada"

# ── 4. Verificación ──────────────────────────────────────────────
sleep 3
FREE=$(free -h | awk '/^Mem:/{print $7}')
CONTAINERS=$(docker ps -q 2>/dev/null | wc -l)
OLLAMA_MODELS=$(ollama ps 2>/dev/null | tail -n +2 | wc -l)

echo ""
echo "══════════════════════════════════════"
echo "  Memoria disponible: $FREE"
echo "  Contenedores activos: $CONTAINERS"
echo "  Modelos Ollama en GPU: $OLLAMA_MODELS"
echo "══════════════════════════════════════"
echo ""

if echo "$FREE" | grep -qE '^[5-9][0-9]|^[6-9][0-9]'; then
  echo "  ✅ Sistema listo para workload exigente"
else
  echo "  ⚠️  Memoria disponible podría ser baja. Espera 30s y repite."
fi
echo ""
CLEAN
chmod +x ~/scripts/jetson-clean.sh
```

---

## 2.6 Hardening de producción (ejecutar una sola vez)

Ejecutar esto después de la instalación inicial para dejar el sistema configurado correctamente:

```bash
cat > ~/scripts/jetson-harden.sh << 'HARDEN'
#!/bin/bash
echo "=== Hardening de producción Jetson AGX Orin ==="

# 1. Deshabilitar auto-restart en todos los contenedores LLM
echo "→ Fijando políticas de restart..."
for container in vllm-openclaw llama-openclaw open-webui; do
  docker update --restart=no $container 2>/dev/null && \
    echo "  ✓ $container → restart=no" || \
    echo "  - $container no existe aún (normal)"
done

# 2. Ollama: descarga inmediata tras cada uso
echo "→ Configurando Ollama keep_alive=0..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/keepalive.conf > /dev/null << 'EOF'
[Service]
Environment="OLLAMA_KEEP_ALIVE=0"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama 2>/dev/null || true
echo "  ✓ Ollama configurado para descargar modelos inmediatamente tras cada uso"

# 3. Protección OOM del kernel
echo "→ Aplicando protección OOM..."
sudo tee /etc/sysctl.d/99-jetson-oom.conf > /dev/null << 'EOF'
# Jetson AGX Orin — OOM protection
# Preferir matar procesos antes que kernel panic
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1
# Sin swap en Jetson típicamente
vm.swappiness = 1
# Mayor presión sobre caché para liberar memoria antes
vm.vfs_cache_pressure = 200
EOF
sudo sysctl -p /etc/sysctl.d/99-jetson-oom.conf
echo "  ✓ OOM killer configurado"

# 4. Caché de compilación para Node.js
echo "→ Optimizaciones Node.js..."
mkdir -p /var/tmp/openclaw-compile-cache
echo "  ✓ Caché de compilación Node.js creada"

# 5. Crear estructura de directorios
echo "→ Creando estructura de trabajo..."
mkdir -p ~/scripts
mkdir -p ~/jetson-ai-data/models/hf
mkdir -p ~/jetson-ai-data/workspaces
mkdir -p ~/jetson-ai-data/outputs
mkdir -p ~/.config/systemd/user
echo "  ✓ Directorios creados"

# 6. Instalar jtop si no está
echo "→ Verificando jetson-stats..."
if command -v jtop &> /dev/null; then
  echo "  ✓ jtop ya instalado"
else
  sudo pip3 install jetson-stats --break-system-packages 2>/dev/null && \
    echo "  ✓ jtop instalado" || echo "  ⚠️  Instalar manualmente: sudo pip3 install jetson-stats"
fi

echo ""
echo "=== Hardening completo ==="
echo "Verificar con: jetson-audit"
HARDEN
chmod +x ~/scripts/jetson-harden.sh
bash ~/scripts/jetson-harden.sh
```

---

## 2.7 Aliases maestros de gestión de recursos

Añadir al **inicio** de `~/.bashrc` (después de los exports, antes del bloque interactivo):

```bash
# =====================================================================
# GESTIÓN DE RECURSOS — JETSON AGX ORIN 64GB
# =====================================================================

# ── AUDITORÍA ─────────────────────────────────────────────────────

# Snapshot completo del estado del sistema
jetson-audit() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║           AUDITORÍA JETSON AGX ORIN                     ║"
  echo "║              $(date '+%Y-%m-%d %H:%M:%S')                  ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
  echo "── MEMORIA DEL SISTEMA ──"
  free -h
  echo ""
  echo "── CONTENEDORES DOCKER ACTIVOS ──"
  local running=$(docker ps -q 2>/dev/null | wc -l)
  if [ "$running" -gt 0 ]; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
    echo ""
    docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}} ({{.MemPerc}})"
  else
    echo "  Ninguno"
  fi
  echo ""
  echo "── POLÍTICAS DE RESTART (contenedores en riesgo) ──"
  docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
    for c in json.load(sys.stdin):
        n = c['Name'].lstrip('/')
        p = c['HostConfig']['RestartPolicy']['Name']
        s = c['State']['Status']
        flag = '⚠️  AUTO' if p in ['always','unless-stopped'] else '✓ manual'
        print(f'  {flag}  {n:28} restart={p} ({s})')
except: pass
" 2>/dev/null || echo "  Sin contenedores"
  echo ""
  echo "── MODELOS OLLAMA EN GPU ──"
  local ollama_loaded=$(ollama ps 2>/dev/null | tail -n +2 | wc -l)
  if [ "$ollama_loaded" -gt 0 ]; then
    ollama ps
  else
    echo "  Ninguno"
  fi
  echo ""
  echo "── ENDPOINTS DE INFERENCIA ──"
  curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c "
import sys,json
try: [print(f'  vLLM:8000    → {m[\"id\"]}') for m in json.load(sys.stdin)['data']]
except: print('  vLLM:8000    → offline')
" 2>/dev/null || echo "  vLLM:8000    → offline"
  curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -c "
import sys,json
try: [print(f'  llama.cpp:8080 → {m[\"id\"]}') for m in json.load(sys.stdin)['data']]
except: print('  llama.cpp:8080 → offline')
" 2>/dev/null || echo "  llama.cpp:8080 → offline"
  curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import sys,json
try:
    d = json.load(sys.stdin)
    ms = d.get('models',[])
    if ms: [print(f'  Ollama:11434  → {m[\"name\"]} (descargado, no cargado)') for m in ms]
    else: print('  Ollama:11434  → sin modelos descargados')
except: print('  Ollama:11434  → offline')
" 2>/dev/null || echo "  Ollama:11434  → offline"
  echo ""
  echo "── GATEWAY OPENCLAW ──"
  openclaw gateway status 2>/dev/null | grep -E "reachable|running|error" || echo "  Estado desconocido"
  echo ""
}

# Memoria rápida
alias jetson-mem='echo "── Memoria ──" && free -h && echo "" && echo "── Contenedores ──" && docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null'

# Monitor interactivo
alias jetson-top='jtop'

# Hardware raw
alias jetson-hw='sudo tegrastats --interval 2000'

# ── LIMPIEZA ───────────────────────────────────────────────────────

# Limpieza total
alias jetson-clean='~/scripts/jetson-clean.sh'

# Solo caché del kernel (seguro, no impacta servicios)
alias jetson-dropcache='sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches" && echo "Cache dropped. Libre: $(free -h | awk \"/^Mem:/{print \$7}\")"'

# Descargar todos los modelos de Ollama sin detener el servicio
alias ollama-flush='for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null && echo "Descargado: $m"; done'

# Fixear políticas de restart tras crear nuevos contenedores
alias docker-fix-restart='for c in vllm-openclaw llama-openclaw open-webui; do docker update --restart=no $c 2>/dev/null && echo "✓ $c → restart=no"; done'

# ── MODOS DE OPERACIÓN ─────────────────────────────────────────────

# IDLE: todo apagado, 15W
alias mode-idle='
echo "→ Activando MODO IDLE...";
docker stop vllm-openclaw llama-openclaw open-webui 2>/dev/null;
for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null;
done;
sudo systemctl stop ollama 2>/dev/null;
sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches";
sudo nvpmodel -m 1 && sudo jetson_clocks --restore;
echo "✅ IDLE 15W — libre: $(free -h | awk \"/^Mem:/{print \$7}\")";
'

# OPENCLAW: agente WhatsApp por defecto (Gemma 4 E2B / vLLM, 30W)
alias mode-openclaw='~/scripts/switch-model.sh gemma-vllm'

# LITE: Gemma 4 E2B / llama.cpp, mínima RAM, 30W
alias mode-lite='~/scripts/switch-model.sh gemma-llama'

# LONGDOC: Nemotron3 30B para documentos largos / vLLM, MAXN
alias mode-longdoc='~/scripts/switch-model.sh nemotron-text'

# MULTIMODAL: Nemotron Omni para audio/video / llama.cpp, MAXN
alias mode-multimodal='~/scripts/switch-model.sh nemotron-omni'

# OLLAMA: usar Ollama con cualquier modelo
alias mode-ollama='
echo "→ Activando MODO OLLAMA...";
docker stop vllm-openclaw llama-openclaw 2>/dev/null;
sudo sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches";
sleep 5;
sudo systemctl start ollama;
sudo nvpmodel -m 2 && sudo jetson_clocks;
echo "✅ Ollama activo — libre: $(free -h | awk \"/^Mem:/{print \$7}\")";
echo "Uso: ollama run <modelo>";
'

# WEBUI: Open-WebUI sin inferencia activa
alias mode-webui='docker start open-webui 2>/dev/null && echo "Open-WebUI en http://192.168.1.100:3000" || echo "Contenedor open-webui no encontrado"'

# ── PODER ──────────────────────────────────────────────────────────
alias pwr-idle='sudo nvpmodel -m 1 && sudo jetson_clocks --restore && sudo nvpmodel -q'
alias pwr-30w='sudo nvpmodel -m 2 && sudo jetson_clocks && sudo nvpmodel -q'
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && sudo nvpmodel -q'
alias pwr-status='sudo nvpmodel -q && cat /sys/bus/i2c/drivers/ina3221x/*/iio:device*/in_power*_input 2>/dev/null | awk "{sum+=\$1} END {print \"Power: \"sum/1000\"W\"}" 2>/dev/null || echo "(instalar jetson-stats para medición de watts)"'

# ── OLLAMA ─────────────────────────────────────────────────────────
alias ollama-list='ollama list'
alias ollama-loaded='ollama ps'
alias ollama-start='sudo systemctl start ollama && echo "Ollama iniciado"'
alias ollama-stop='ollama-flush; sudo systemctl stop ollama && echo "Ollama detenido"'
alias ollama-safe-run='f(){ mode-idle; sleep 5; sudo systemctl start ollama; ollama run "$1"; }; f'

# ── DOCKER ─────────────────────────────────────────────────────────
alias docker-all='docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.RunningFor}}"'
alias docker-clean='docker container prune -f && docker image prune -f'

# ── OPENCLAW ───────────────────────────────────────────────────────
alias claw-status='openclaw gateway status && openclaw channels status --probe'
alias claw-restart='openclaw gateway restart && sleep 3 && openclaw gateway status'
alias claw-logs='openclaw logs --follow'
alias claw-wa='openclaw logs --follow | grep -i whatsapp'
alias claw-errors='openclaw logs --follow | grep -i error'
alias claw-doctor='openclaw doctor'
alias claw-tui='openclaw tui'
alias claw-pair='openclaw pairing list whatsapp'

# ── MODELO STATUS ──────────────────────────────────────────────────
alias model-status='
echo "── vLLM (8000) ──";
curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c "import sys,json; [print(\" \", m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" 2>/dev/null || echo "  offline";
echo "── llama.cpp (8080) ──";
curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -c "import sys,json; [print(\" \", m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" 2>/dev/null || echo "  offline";
echo "── Ollama (11434) ──";
ollama ps 2>/dev/null | tail -n +2 || echo "  offline";
'

# =====================================================================
# FIN DE ALIASES
# =====================================================================
```

Aplicar inmediatamente:
```bash
source ~/.bashrc
```

---

# PARTE 3 — BACKENDS DE INFERENCIA

## 3.1 Guía de selección de modelo

```
¿Qué necesitas hacer?
│
├── Responder mensajes WhatsApp, analizar imágenes enviadas por clientes
│   → mode-openclaw (Backend A — Gemma 4 E2B / vLLM)
│   ↳ 32 tok/s · 128K ctx · herramienta de búsqueda web · tool calling
│
├── Mismo agente pero quieres gastar menos RAM / energía (por las noches)
│   → mode-lite (Backend B — Gemma 4 E2B / llama.cpp)
│   ↳ 35 tok/s · 3.5GB RAM · 30W · arranque en 20 segundos
│
├── Procesar PDF de 100MB+, libro de 300 páginas, contrato largo
│   → mode-longdoc (Backend C — Nemotron3 30B-A3B / vLLM)
│   ↳ 38 tok/s · 256K ctx · razonamiento avanzado · texto solamente
│
├── Transcribir grabación de audio/vídeo → notas/podcast/presentación
│   → mode-multimodal (Backend D — Nemotron Omni / llama.cpp)
│   ↳ 39 tok/s · texto+imagen+audio+vídeo nativo · 256K ctx
│
└── Explorar modelos, probar cosas nuevas, demos rápidos
    → mode-ollama + ollama run <modelo>
    ↳ ollama pull qwen3:8b / llama3.1:8b / etc.
```

### Tabla comparativa completa

| | Gemma E2B vLLM | Gemma E2B llama | Nemotron3 30B | Nemotron Omni |
|---|---|---|---|---|
| **Tok/s** | ~32 | ~35 | ~38 | ~39 |
| **RAM usada** | ~15GB | ~3.5GB | ~26GB | ~24GB |
| **Arranque** | ~3 min | ~20 seg | ~10 min | ~2 min |
| **Contexto** | 128K | 32K | 256K | 256K |
| **Texto** | ✅ | ✅ | ✅ | ✅ |
| **Imagen** | ✅ | ❌ | ❌ | ✅ |
| **Audio** | ❌ | ❌ | ❌ | ✅ |
| **Video** | ❌ | ❌ | ❌ | ✅ |
| **Tool calling** | ✅ gemma4 | básico | ✅ hermes | básico |
| **Razonamiento** | ❌ | ❌ | ✅ configurable | ✅ configurable |
| **Modo poder** | 30W | 30W | MAXN | MAXN |
| **Puerto** | 8000 | 8080 | 8000 | 8080 |
| **Contenedor** | vllm-openclaw | llama-openclaw | vllm-openclaw | llama-openclaw |

---

## 3.2 Backend A: Gemma 4 E2B via vLLM

**Status:** ✅ Verificado en producción

```bash
# Arranque manual (el alias mode-openclaw hace todo esto automáticamente)
docker rm -f vllm-openclaw 2>/dev/null
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sudo nvpmodel -m 2 && sudo jetson_clocks

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

# Esperar inicio (3–5 min primera vez, más rápido con caché)
echo "Esperando vLLM..."
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  sleep 15; echo "  Cargando... $(docker logs vllm-openclaw 2>&1 | tail -1)"
done
echo "✅ Gemma 4 E2B / vLLM listo en puerto 8000"

# Verificar
curl -s http://localhost:8000/v1/models | python3 -c \
  "import sys,json; [print('Modelo activo:', m['id']) for m in json.load(sys.stdin)['data']]"
```

**Notas técnicas:**
- `bash -c "cd /opt && source venv/bin/activate && vllm serve ..."` es **obligatorio** — la imagen no tiene entrypoint de servidor
- `--restart no` (no `unless-stopped`) para evitar arranque fantasma tras reboot
- `--gpu-memory-utilization 0.55` → reserva ~35GB para KV cache, deja ~26GB para OS + OpenClaw
- El modelo tiene 128K tokens de contexto pero `--max-model-len 65536` es suficiente para conversaciones largas y más eficiente en memoria

---

## 3.3 Backend B: Gemma 4 E2B via llama.cpp

**Cuándo usar:** Modo nocturno, bajo consumo, máxima disponibilidad de RAM

```bash
docker rm -f llama-openclaw 2>/dev/null
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

echo "Esperando llama.cpp..."
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  sleep 5; echo "  Cargando..."
done
echo "✅ Gemma 4 E2B / llama.cpp listo en puerto 8080"
```

**Verificar:**
```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma-e2b","messages":[{"role":"user","content":"Di hola"}],"max_tokens":20}'
```

---

## 3.4 Backend C: Nemotron3 30B-A3B via vLLM

**Cuándo usar:** PDFs de 100MB+, contratos legales, investigación, 256K tokens de contexto

**Arquitectura:** MoE híbrido (Mamba-2 + Attention) — 30B totales, solo 3.5B activos por forward pass

```bash
# CRÍTICO: limpiar memoria antes de este modelo
jetson-clean
sleep 10
FREE=$(free -g | awk '/^Mem:/{print $7}')
echo "Memoria disponible: ${FREE}GB"
[ "$FREE" -lt 50 ] && echo "⚠️ Memoria baja. Espera más." || echo "✅ Suficiente memoria"

sudo nvpmodel -m 0 && sudo jetson_clocks

docker run --runtime nvidia -d \
  --name vllm-openclaw \
  --restart no \
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
      --default-chat-template-kwargs '{\"enable_thinking\": false}' \
      --host 0.0.0.0 \
      --port 8000"

echo "Esperando Nemotron3 30B (primera vez: ~10 min)..."
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  sleep 30; echo "  $(docker logs vllm-openclaw 2>&1 | tail -1)"
done
echo "✅ Nemotron3 30B-A3B / vLLM listo"
```

**Control de razonamiento:**
```bash
# Activar razonamiento (más lento, mayor calidad para tareas complejas)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ",
    "messages": [{"role":"user","content":"Analiza este contrato y señala riesgos legales."}],
    "extra_body": {"chat_template_kwargs": {"enable_thinking": true}}
  }'

# Desactivar razonamiento (más rápido, para respuestas directas)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ",
    "messages": [{"role":"user","content":"¿Cuál es la capital de Colombia?"}],
    "extra_body": {"chat_template_kwargs": {"enable_thinking": false}},
    "max_tokens": 20
  }'
```

> **Nota:** El checkpoint AWQ de `stelterlab` no requiere autenticación HF para Orin (es un mirror comunitario). Si quieres la versión oficial NVFP4 de NVIDIA (requiere HF auth y Thor preferentemente), usa `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4`.

---

## 3.5 Backend D: Nemotron Omni via llama.cpp

**Cuándo usar:** Audio de conferencias, vídeos de clases, imágenes con texto, procesamiento multimodal

**Capacidades:** Texto + Imagen + Audio + Vídeo — 30B totales, 3B activos, GGUF Q4_K_M

```bash
jetson-clean
sleep 10
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

echo "Esperando Nemotron Omni..."
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  sleep 20; echo "  Cargando..."
done
echo "✅ Nemotron 3 Nano Omni / llama.cpp listo en puerto 8080"
```

**Uso con razonamiento activado:**
```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nemotron-omni",
    "messages": [{"role":"user","content":"Hola, ¿qué puedes procesar?"}],
    "max_tokens": 256,
    "chat_template_kwargs": {"enable_thinking": true}
  }'
```

---

## 3.6 Script switcher de modelos

```bash
cat > ~/scripts/switch-model.sh << 'SWITCHER'
#!/bin/bash
# Switcher completo: limpia, ajusta poder, arranca modelo, actualiza OpenClaw
set -e

MODEL=${1:-help}
CONFIG="$HOME/.openclaw/openclaw.json"

print_usage() {
  echo ""
  echo "Uso: switch-model.sh <modo>"
  echo ""
  echo "  gemma-vllm    — Gemma 4 E2B / vLLM   · puerto 8000 · 30W · ~32 tok/s"
  echo "  gemma-llama   — Gemma 4 E2B / llama   · puerto 8080 · 30W · ~35 tok/s"
  echo "  nemotron-text — Nemotron3 30B-A3B      · puerto 8000 · MAXN · ~38 tok/s"
  echo "  nemotron-omni — Nemotron Omni          · puerto 8080 · MAXN · ~39 tok/s"
  echo "  stop          — Parar todo, modo idle 15W"
  echo ""
}

stop_all() {
  echo "→ Deteniendo inferencia..."
  docker stop vllm-openclaw llama-openclaw 2>/dev/null || true
  docker rm vllm-openclaw llama-openclaw 2>/dev/null || true
  for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
    curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null
  done
  sleep 5
  sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
  sleep 3
  FREE=$(free -g | awk '/^Mem:/{print $7}')
  echo "  Libre: ${FREE}GB"
  if [ "$FREE" -lt 45 ]; then
    echo "  ⚠️  Memoria baja. Esperando 30 segundos más..."
    sleep 30
  fi
}

wait_model() {
  local port=$1
  local name=$2
  echo -n "→ Esperando $name en puerto $port"
  local tries=0
  while ! curl -s http://localhost:${port}/v1/models > /dev/null 2>&1; do
    echo -n "."
    sleep 15
    tries=$((tries+1))
    [ $tries -gt 80 ] && echo " ❌ Timeout" && return 1
  done
  echo " ✅"
}

update_config() {
  local model_id=$1 base_url=$2 ctx=$3 max_tok=$4 input_json=$5
  python3 - << PYEOF
import json

with open('$CONFIG') as f:
    c = json.load(f)

c.setdefault('agents', {}).setdefault('defaults', {})
c['agents']['defaults']['model'] = {'primary': 'vllm/${model_id}'}
c['agents']['defaults']['models'] = {'vllm/${model_id}': {}}

c.setdefault('models', {}).setdefault('providers', {})
c['models']['providers']['vllm'] = {
    'baseUrl': '${base_url}',
    'api': 'openai-completions',
    'apiKey': 'vllm-local',
    'timeoutSeconds': 300,
    'models': [{
        'id': '${model_id}',
        'name': '${model_id}',
        'reasoning': False,
        'input': ${input_json},
        'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
        'contextWindow': ${ctx},
        'maxTokens': ${max_tok}
    }]
}

with open('$CONFIG', 'w') as f:
    json.dump(c, f, indent=2)
print('  ✅ Config OpenClaw actualizada')
PYEOF
}

case $MODEL in

  gemma-vllm)
    echo "═══ MODO: Gemma 4 E2B / vLLM ═══"
    stop_all
    sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name vllm-openclaw --restart no \
      --network host --ipc host --shm-size 8g \
      -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
      bash -c "cd /opt && source venv/bin/activate && \
        vllm serve google/gemma-4-E2B-it \
          --dtype bfloat16 --max-model-len 65536 --gpu-memory-utilization 0.55 \
          --enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4 \
          --host 0.0.0.0 --port 8000"
    wait_model 8000 "Gemma 4 E2B vLLM"
    update_config "google/gemma-4-E2B-it" "http://127.0.0.1:8000/v1" 65536 4096 '["text","image"]'
    openclaw gateway restart
    echo "✅ Modo OPENCLAW activo — agente WhatsApp listo"
    ;;

  gemma-llama)
    echo "═══ MODO: Gemma 4 E2B / llama.cpp ═══"
    stop_all
    sudo nvpmodel -m 2 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name llama-openclaw --restart no \
      --network host \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_S \
        --ctx-size 32768 --n-gpu-layers 999 \
        --port 8080 --alias gemma-e2b --host 0.0.0.0
    wait_model 8080 "Gemma 4 E2B llama.cpp"
    update_config "gemma-e2b" "http://127.0.0.1:8080/v1" 32768 4096 '["text"]'
    openclaw gateway restart
    echo "✅ Modo LITE activo — bajo consumo, mínima RAM"
    ;;

  nemotron-text)
    echo "═══ MODO: Nemotron3 30B-A3B / vLLM ═══"
    stop_all
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
          --default-chat-template-kwargs '{\"enable_thinking\": false}' \
          --host 0.0.0.0 --port 8000"
    wait_model 8000 "Nemotron3 30B vLLM"
    update_config "stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ" "http://127.0.0.1:8000/v1" 32768 8192 '["text"]'
    openclaw gateway restart
    echo "✅ Modo LONGDOC activo — 256K contexto, razonamiento avanzado"
    ;;

  nemotron-omni)
    echo "═══ MODO: Nemotron Omni / llama.cpp ═══"
    stop_all
    sudo nvpmodel -m 0 && sudo jetson_clocks
    docker run --runtime nvidia -d \
      --name llama-openclaw --restart no \
      --network host \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
      llama-server \
        --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
        --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
        --ctx-size 8192 --n-gpu-layers 999 \
        --port 8080 --alias nemotron-omni --host 0.0.0.0
    wait_model 8080 "Nemotron Omni llama.cpp"
    update_config "nemotron-omni" "http://127.0.0.1:8080/v1" 8192 4096 '["text","image","audio"]'
    openclaw gateway restart
    echo "✅ Modo MULTIMODAL activo — audio/video/imagen/texto"
    ;;

  stop)
    stop_all
    sudo nvpmodel -m 1 && sudo jetson_clocks --restore
    echo "✅ TODO DETENIDO — 15W idle — libre: $(free -h | awk '/^Mem:/{print $7}')"
    ;;

  *)
    print_usage
    ;;
esac
SWITCHER
chmod +x ~/scripts/switch-model.sh
```

---

# PARTE 4 — OPENCLAW: INSTALACIÓN Y CONFIGURACIÓN

## 4.1 Instalación de OpenClaw

```bash
# Método recomendado: instalador oficial
# (verifica versión de Node, instala OpenClaw, configura daemon)
curl -fsSL https://openclaw.ai/install.sh | bash

# Si openclaw no se encuentra después:
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verificar
openclaw --version   # debe mostrar 2026.6.10 o superior
node --version       # debe ser v22.19+ (se tienen v22.23.1)
```

> **Paquete npm:** `openclaw` (no `@openclaw/cli` — ese no existe)
> **Instalador alternativo:** `npm install -g openclaw@latest && openclaw onboard --install-daemon`

---

## 4.2 Configuración completa verificada

Esta es la configuración probada en producción con todas las correcciones aplicadas:

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
      "token": "REEMPLAZAR_CON_TOKEN_REAL"
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

# Generar token de gateway
openclaw doctor --generate-gateway-token
# Copiar el token generado y reemplazar "REEMPLAZAR_CON_TOKEN_REAL" arriba

# Validar JSON
python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null && echo "✅ JSON válido"
```

### Puntos críticos de configuración (no obvios)

```
❌ INCORRECTO → ✅ CORRECTO

"profile": "default"                → "profile": "full"
(no existe "default"; válidos: minimal/coding/messaging/full)

"apiKey": "VLLM_API_KEY"           → "apiKey": "vllm-local"
(nombre de variable, no el valor)

"id": "vllm/google/gemma-4-E2B-it" → "id": "google/gemma-4-E2B-it"
(sin prefijo del provider en el id)

"primary": "vllm/google/gemma4-E2B-it" → "primary": "vllm/google/gemma-4-E2B-it"
(gemma-4 con guión, no gemma4)

"contextWindow": 128000             → "contextWindow": 65536
(debe coincidir con --max-model-len del servidor vLLM)

"maxTokens": 8192                   → "maxTokens": 4096
(no puede ser igual a contextWindow — deja espacio para el input)

"memorySearch": { "enabled": true } → "memorySearch": { "enabled": false }
(requiere OpenAI API key; sin ella falla silenciosamente en cada turno)

"profile": "coding"                 → "profile": "full"
(coding elimina herramientas message y whatsapp_login; el agente recibe
mensajes pero no puede responder por WhatsApp)
```

---

## 4.3 Canal WhatsApp

### Proceso de vinculación

```bash
# Paso 1: Ejecutar onboarding (genera QR)
openclaw onboard

# Durante el wizard:
# - Channel: WhatsApp
# - Usar un número dedicado (recomendado: eSIM separada)
# - dmPolicy: Pairing
# - Search: Brave Search
# - Hooks: habilitar todos los 5
# - Gateway service: Install (systemd user service)
# - Hatch: Browser

# Paso 2: Escanear QR con WhatsApp
# WhatsApp → Ajustes → Dispositivos vinculados → Vincular dispositivo
# (el QR aparece en la terminal durante el onboarding)

# Paso 3: Aprobar tu propio número (llega código de emparejamiento)
openclaw pairing list whatsapp
# Muestra: pending  +57XXXXXXXXXX  code: XXXXXX

openclaw pairing approve whatsapp CODIGO_AQUI
# Output: "Approved whatsapp sender +57XXXXXXXXXX"
# Output: "Command owner configured whatsapp:+57XXXXXXXXXX" (automático)

# Paso 4: Verificar
openclaw channels status --probe
# Esperado: WhatsApp default: enabled, configured, linked, running, connected
```

### Política de DMs

```bash
# Pairing (recomendado): nuevos remitentes reciben código, tú apruebas
openclaw config set channels.whatsapp.dmPolicy pairing

# Allowlist: solo números pre-aprobados
openclaw config set channels.whatsapp.dmPolicy allowlist
openclaw config set channels.whatsapp.dmAllowFrom '["+573XXXXXXXXX","+573XXXXXXXXY"]'

# Para turismo: clientes nuevos necesitan código, contactos existentes pasan directo
# → usar dmPolicy=pairing con dmAllowFrom para clientes VIP
```

### Troubleshooting WhatsApp

```bash
# Ver logs de WhatsApp en tiempo real
openclaw logs --follow | grep -i whatsapp

# Si aparece "session logged out":
openclaw channels auth login whatsapp
# Escanear QR nuevamente

# Si mensajes llegan pero no hay respuesta (verificar tool profile):
grep '"profile"' ~/.openclaw/openclaw.json
# Debe decir "full", nunca "coding" o "default"

# Ver si la restricción de herramientas está activa:
openclaw logs --follow | grep "tool policy removed"
# Si aparece "message" en la lista de herramientas removidas → cambiar profile a "full"
```

---

## 4.4 Web UI desde Windows

```powershell
# WINDOWS — mantener abierto mientras se usa el Web UI
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

```
# En el navegador de Windows
http://localhost:18789/#token=TU_TOKEN_AQUI
```

### Obtener el token

```bash
# En el Jetson
openclaw config get gateway.auth.token
```

### Acceso directo via NoMachine (alternativa sin túnel)

Con NoMachine ya configurado, conectar a `192.168.1.100:4000` y abrir en el navegador interno:
```
http://127.0.0.1:18789/#token=TU_TOKEN
```

---

## 4.5 Gestión del gateway

```bash
# Estado
openclaw gateway status

# Reiniciar (necesario después de cambiar config)
openclaw gateway restart
sleep 5

# Ver logs del gateway
openclaw logs --follow

# Instalar como servicio systemd (si no está instalado)
openclaw gateway install
systemctl --user enable openclaw-gateway.service

# El gateway es LIGERO (~500MB RAM) y puede quedar como servicio persistente
# A diferencia de los contenedores LLM, el gateway SÍ puede auto-arrancar

# Verificar estado del servicio systemd
systemctl --user status openclaw-gateway.service
```

---

# PARTE 5 — OPERACIONES DE PRODUCCIÓN

## 5.1 Secuencia de arranque tras reboot

Después de cada reinicio, el gateway de OpenClaw arranca automáticamente. Los contenedores LLM **no** (así está configurado intencionalmente). Secuencia recomendada:

```bash
# ── INMEDIATAMENTE DESPUÉS DEL REBOOT ──────────────────────────────

# 1. Verificar que el gateway arrancó
openclaw gateway status
# Si no: openclaw gateway start

# 2. Verificar WhatsApp (puede necesitar reconexión)
openclaw channels status --probe

# 3. Revisar estado de la memoria
jetson-audit

# 4. Arrancar el modelo deseado
mode-openclaw      # caso más común: agente WhatsApp

# 5. Confirmar que todo está listo
model-status
jetson-mem
```

### Script de arranque automático (opcional)

```bash
cat > ~/scripts/startup.sh << 'EOF'
#!/bin/bash
# Ejecutar después de cada reboot

echo "=== Arranque Jetson AI Stack ==="

source ~/.bashrc

# Esperar Docker
echo "→ Esperando Docker..."
until docker info > /dev/null 2>&1; do sleep 5; done

# Limpiar estados residuales
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Configurar poder para uso ligero inicial
sudo nvpmodel -m 2
sudo jetson_clocks

# Arrancar modelo por defecto
echo "→ Iniciando Gemma 4 E2B..."
~/scripts/switch-model.sh gemma-vllm

echo "=== Stack listo ==="
echo "Free: $(free -h | awk '/^Mem:/{print $7}')"
echo "OpenClaw: $(openclaw gateway status 2>/dev/null | grep -o 'reachable\|unreachable')"
EOF
chmod +x ~/scripts/startup.sh

# Activar servicio de arranque (opcional — si quieres carga automática del modelo)
cat > ~/.config/systemd/user/jetson-ai-startup.service << 'EOF'
[Unit]
Description=Jetson AI Stack Startup
After=openclaw-gateway.service docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/sleep 30
ExecStart=/home/jetson/scripts/startup.sh
StandardOutput=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
# Habilitar solo si quieres arranque automático:
# systemctl --user enable jetson-ai-startup.service
```

---

## 5.2 Checklist pre-workload

Antes de cualquier tarea exigente (PDF grande, audio largo, vídeo):

```bash
echo "=== CHECKLIST PRE-WORKLOAD ==="
echo ""

# 1. Estado de memoria
FREE_GB=$(free -g | awk '/^Mem:/{print $7}')
echo "1. Memoria libre: ${FREE_GB}GB"
[ "$FREE_GB" -lt 50 ] && echo "   ⚠️  Ejecutar jetson-clean primero" || echo "   ✅ OK"

# 2. Contenedores de inferencia
CONTAINERS=$(docker ps --filter "name=vllm-openclaw\|llama-openclaw" -q | wc -l)
echo "2. Contenedores LLM activos: $CONTAINERS"
[ "$CONTAINERS" -gt 1 ] && echo "   ⚠️  Más de un contenedor LLM — detener el no necesario" || echo "   ✅ OK"

# 3. Modo de poder
POWER=$(sudo nvpmodel -q 2>/dev/null | grep "NV Power Mode:" | awk '{print $NF}')
echo "3. Modo de poder: $POWER"

# 4. Endpoint activo
MODEL=$(curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || \
  curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || \
  echo "ninguno")
echo "4. Modelo activo: $MODEL"

# 5. Gateway
GW=$(openclaw gateway status 2>/dev/null | grep -o 'reachable\|unreachable' || echo "desconocido")
echo "5. Gateway OpenClaw: $GW"

echo ""
```

---

## 5.3 Monitoreo y watchdog

```bash
# Monitor en tiempo real (actualiza cada 3 segundos)
watch -n 3 '
echo "=== $(date) ==="
echo ""
echo "MEMORIA:"
free -h | grep Mem
echo ""
echo "CONTENEDORES:"
docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}} ({{.MemPerc}})" 2>/dev/null
echo ""
echo "THROUGHPUT vLLM:"
curl -s http://localhost:8000/metrics 2>/dev/null | grep "vllm:generation_tokens_total" | tail -1 || echo "  offline"
'

# Watchdog básico (ejecutar en background, alerta si memoria cae)
cat > ~/scripts/watchdog.sh << 'WD'
#!/bin/bash
THRESHOLD=10  # Alerta si quedan menos de 10GB libres

while true; do
  FREE=$(free -g | awk '/^Mem:/{print $7}')
  if [ "$FREE" -lt "$THRESHOLD" ]; then
    MSG="⚠️ ALERTA MEMORIA: solo ${FREE}GB disponibles en Jetson"
    echo "$(date): $MSG"
    # Intentar aliviar presión
    sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
    sleep 30
    FREE2=$(free -g | awk '/^Mem:/{print $7}')
    if [ "$FREE2" -lt 5 ]; then
      echo "$(date): CRÍTICO — deteniendo inferencia"
      docker stop vllm-openclaw llama-openclaw 2>/dev/null
    fi
  fi
  sleep 60
done
WD
chmod +x ~/scripts/watchdog.sh
```

---

## 5.4 Recuperación de OOM

Si la Jetson se congela o el proceso muere por OOM:

```bash
# Si el sistema responde (pero está lento):
# 1. Matar procesos que consumen más memoria
docker stop vllm-openclaw llama-openclaw 2>/dev/null
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sleep 30
free -h  # verificar recuperación

# Si el sistema no responde:
# → Apagado físico (mantener botón de poder 10 segundos)
# → Reboot
# → Al arrancar, ejecutar startup.sh o mode-openclaw

# Prevenir OOM futuro — verificar configuración:
grep "gpu-memory-utilization" <(docker inspect vllm-openclaw 2>/dev/null)
# Debe ser 0.55 para Gemma E2B, 0.80 para Nemotron (con memoria limpia)
```

---

# PARTE 6 — WORKFLOWS DE CASOS DE USO

## 6.1 Agencia de turismo automatizada

**Modelo:** `mode-openclaw` (Gemma 4 E2B / vLLM) para respuestas rápidas
**Canal:** WhatsApp
**Contexto:** El agente responde 24/7 a consultas de turistas

### Instrucciones del agente (BOOTSTRAP.md)

```bash
cat > ~/.openclaw/workspace/BOOTSTRAP.md << 'EOF'
# Agente de Agencia de Turismo Colombia

Soy el asistente virtual de [Nombre de Agencia], agencia de turismo especializada en Colombia.

## Mi rol
- Asesorar sobre destinos, tours y paquetes en Colombia
- Proveer itinerarios detallados con día a día
- Cotizar tours y paquetes
- Gestionar preguntas sobre reservas

## Destinos que manejo
- Cartagena (colonial, caribe, islas)
- Medellín (ciudad, pueblos paisa, naturaleza)
- Bogotá (cultura, historia, gastronomía)
- Eje Cafetero (fincas, pueblos patrimonio)
- Amazonia, Sierra Nevada, Guajira

## Estilo de respuesta
- Cálido, apasionado por Colombia, profesional
- Siempre ofrecer 3 opciones: económico / estándar / premium
- Incluir detalles prácticos: punto de encuentro, qué llevar, duración exacta
- En WhatsApp: máximo 3 párrafos por respuesta para no saturar
- Si piden info compleja: "Te envío el itinerario detallado en PDF"

## Cuando no puedo responder
"Para reservas y confirmaciones, te conecto con nuestro equipo: [contacto]"

## Idiomas
Responder en el idioma del cliente (español o inglés automáticamente)
EOF
```

### Prompts de ejemplo que los clientes pueden enviar

```
"Quiero hacer un tour por Cartagena con mi familia de 4 personas, tenemos 5 días"
→ El agente responde con 3 opciones de paquete con precios

"Pueden enviarme fotos del hotel?"
→ El agente puede procesar y describir imágenes si las envías tú

"What's the best time to visit the Coffee Region?"
→ El agente detecta inglés y responde en inglés
```

---

## 6.2 Podcast desde PDF de 100MB+

**Modelo:** `mode-longdoc` (Nemotron3 30B-A3B / vLLM) — 256K tokens de contexto

```bash
# Paso 1: Cambiar a modelo de documentos largos
mode-longdoc
# Esperar ~10 minutos para el primer inicio

# Paso 2: Verificar que el modelo cargó
model-status
# Debe mostrar: stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ

# Paso 3: En el Web UI de OpenClaw o via WhatsApp
# Subir el PDF y enviar el prompt:
```

**Prompt para generación de podcast:**
```
Tengo este documento de [X] páginas sobre [TEMA].

Conviértelo en un script de podcast de 30 minutos con estas características:
- 2 presentadores: Ana (analítica, hace preguntas) y Luis (explica, da contextos)
- Formato: intro gancho → 5 segmentos temáticos → cierre con acción
- Cada segmento: concepto principal → ejemplo real → qué significa para el oyente
- Tono: conversacional, educativo, accesible (no académico)
- Incluir momentos de humor natural
- Idioma: español colombiano
- Al final: 5 preguntas de reflexión para los oyentes

Estructura cada segmento con: [ANA]: ... [LUIS]: ...
```

**Para libros de 300+ páginas:**
```bash
# Dividir en chunks si el PDF excede el contexto
# Nemotron3 tiene 256K tokens pero un PDF de 300 páginas pueden ser ~300K tokens

# Estrategia: procesar por capítulos
# Enviar introducción + índice primero para que el modelo entienda la estructura
# Luego enviar capítulos en orden

# Ejemplo de prompt por capítulo:
"Este es el capítulo 3 de un libro sobre [TEMA]. Resumen de capítulos anteriores: [RESUMEN].
Extrae los puntos clave de este capítulo para el segmento 3 del podcast que estamos creando."
```

---

## 6.3 Grabaciones → notas y presentaciones

**Modelo:** `mode-multimodal` (Nemotron Omni / llama.cpp) — procesa audio nativo

```bash
mode-multimodal
# Esperar ~2 minutos

# Verificar
curl -s http://localhost:8080/v1/models | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])"
# Debe mostrar: nemotron-omni
```

**Enviar audio por WhatsApp con prompt:**
```
[Enviar nota de voz o archivo de audio de la conferencia]

Transcribe y estructura esta grabación en:

1. RESUMEN EJECUTIVO (5 bullets, máximo 2 líneas cada uno)
2. DECISIONES TOMADAS (lista numerada con responsable si se menciona)
3. TAREAS Y COMPROMISOS (formato: Tarea · Responsable · Fecha si aplica)
4. CONCEPTOS CLAVE explicados brevemente
5. PREGUNTAS SIN RESPONDER o temas para próxima reunión

Formato Notion-friendly (usa ## para secciones, - para bullets)
```

**Para convertir en presentación:**
```
Con base en la transcripción anterior, crea los títulos y bullets para una presentación de 10 diapositivas:
- Diapositiva 1: Título y subtítulo
- Diapositivas 2-9: Un concepto por diapositiva (título + 4 bullets máximo)
- Diapositiva 10: Próximos pasos y cierre

Formato para Google Slides / PowerPoint
```

---

## 6.4 Atención al cliente por WhatsApp

**Modelo:** `mode-openclaw` (Gemma 4 E2B / vLLM) — respuestas rápidas, herramienta web

```bash
# Configurar múltiples números de clientes en la allowlist
openclaw config set channels.whatsapp.dmAllowFrom \
  '["+573XXXXXXXXX","+573XXXXXXXXY","+573XXXXXXXXZ"]'
# O dejar en "pairing" y aprobar uno a uno
```

**BOOTSTRAP.md para atención al cliente:**
```bash
cat > ~/.openclaw/workspace/BOOTSTRAP.md << 'EOF'
# Agente de Atención al Cliente

Soy el asistente de [Empresa]. Ayudo a los clientes con:
- Consultas sobre productos/servicios
- Estado de pedidos y reservas
- Problemas y reclamaciones
- Información general

## Proceso de respuesta
1. Saludar por nombre (si está en el contexto)
2. Identificar el problema en la primera línea
3. Respuesta completa y accionable
4. Cierre con siguiente paso claro

## Escalación (cuando no puedo resolver)
"Entiendo tu situación. Voy a conectarte con nuestro equipo especializado.
¿Prefieres que te contacten por WhatsApp, email o teléfono?"

## Tono
Cálido pero eficiente. Máximo 3 párrafos cortos en WhatsApp.
Evitar: "Lo siento mucho", "Entiendo tu frustración" (suena robótico)
Usar: respuestas directas y soluciones concretas.

## Horario
Respondo 24/7. Para temas urgentes fuera de horario: [número de emergencias]
EOF
```

---

## 6.5 Generación de contenido

**Modelo:** `mode-openclaw` para rapidez, `mode-longdoc` para contenido largo y profundo

**Prompt: semana de contenido para redes sociales**
```
Crea el calendario de contenido para una semana (lunes a domingo) para una
agencia de turismo en Colombia. Para cada día:

Plataforma: Instagram + LinkedIn + WhatsApp Status
Formato:
  📱 Instagram: Caption [150-200 palabras] + 15 hashtags españoles + 5 ingleses
  💼 LinkedIn: Post profesional [200-250 palabras] enfocado en tendencias de turismo
  📲 Status: Frase inspiradora [máximo 100 caracteres]

Tono: auténtico, apasionado por Colombia, no genérico
Evitar frases como: "¿Listo para tu próxima aventura?" o "No te lo pierdas"
Incluir datos curiosos reales de Colombia cuando sea relevante
```

**Prompt: guía de destino para blog/PDF**
```
Crea una guía completa de [DESTINO, Colombia] para turistas internacionales:

Secciones:
1. Por qué visitar [DESTINO] (3 razones únicas y auténticas)
2. Cuándo ir y por qué (temporadas, clima, eventos locales)
3. Cómo llegar y moverse (transporte interno, tips)
4. Dónde quedarse (3 opciones: económico / boutique / lujo con rango de precios)
5. Qué comer y dónde (5 restaurantes auténticos, no turísticos)
6. Qué hacer: top 10 experiencias (mezcla: cultura / naturaleza / gastronomía)
7. Qué NO hacer (errores comunes de turistas)
8. Presupuesto diario estimado (3 niveles)
9. Frases útiles en español local

Longitud: 1500-2000 palabras
Tono: como si lo escribiera un local apasionado, no una guía genérica
```

---

# APÉNDICE

## A. Registro de patches verificados

Todos estos errores se encontraron y resolvieron durante la instalación real en el Jetson AGX Orin 64GB con JP 7.2.

| # | Paso | Error | Causa raíz | Fix |
|---|---|---|---|---|
| P1 | hf download | Descarga archivos incorrectos | Múltiples patrones en un solo `--exclude` | Usar `--exclude` separado por patrón |
| P2 | Entorno | HF_TOKEN vacío en Docker/systemd | Variable definida después del bloque `case $- in` en bashrc | Mover exports al inicio del bashrc; caché en disco; `/etc/environment` |
| P3 | OpenShell | `npm error 404 @openshell/cli` | Paquete inexistente en npm | `curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh \| sh` |
| P4 | OpenClaw | `npm error 404 @openclaw/cli` | Paquete incorrecto | `curl -fsSL https://openclaw.ai/install.sh \| bash` o `npm install -g openclaw@latest` |
| P5 | vLLM | Contenedor no arranca / port 8000 muerto | Imagen x86 (`vllm/vllm-openai`) en arm64 Jetson | `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` |
| P6 | vLLM | `exec: "--model": executable file not found` | Imagen nvidia-ai-iot sin entrypoint de servidor | `bash -c "cd /opt && source venv/bin/activate && vllm serve ..."` |
| P7 | vLLM | `sleep 10` insuficiente | Modelos grandes tardan 3-10 minutos | Loop de polling con `curl` |
| P8 | vLLM | OOM al iniciar | `gpu_memory_utilization 0.75` > RAM libre (42.7GB < 46GB) | Detener Ollama antes, limpiar caché, bajar utilización |
| P9 | OpenClaw | `Unknown model: qwen/Qwen3-8B` | Proveedor equivocado (`qwen` en vez de `vllm`) | Usar `vllm/MODEL_ID` como primary, configurar `models.providers.vllm` |
| P10 | OpenClaw | Model id incorrecto | `"id": "vllm/google/gemma-4-E2B-it"` con prefijo | El `id` en providers debe ser el id exacto de `/v1/models` sin prefijo |
| P11 | OpenClaw | `apiKey` literal string | `"apiKey": "VLLM_API_KEY"` (nombre de variable) | `"apiKey": "vllm-local"` (valor literal) |
| P12 | OpenClaw | Context overflow en vLLM | `maxTokens = contextWindow` → 0 tokens para input | `maxTokens: 4096`, `contextWindow: 65536`, `compaction.reserveTokensFloor: 6000` |
| P13 | OpenClaw | WhatsApp recibe pero no responde | `tools.profile: "coding"` elimina herramienta `message` | `"profile": "full"` |
| P14 | OpenClaw | `tools.profile: "default"` inválido | No existe; valores válidos: minimal/coding/messaging/full | `"profile": "full"` |
| P15 | OpenClaw | Memory search falla silenciosamente | Requiere OpenAI API key (no configurada) | `"memorySearch": {"enabled": false}` |
| P16 | NemoClaw | `jetsonhacks/NemoClaw-Orin` no existe | URL inventada en guía original | Usar `curl -fsSL https://www.nvidia.com/nemoclaw.sh \| bash` con JP 7.2 |
| P17 | NemoClaw | Parches iptables-legacy | Solo necesarios en JP 6.x (kernel 5.15) | JP 7.2 con kernel 6.8 no necesita parches |
| P18 | docker-compose | Imagen x86 en compose | `vllm/vllm-openai:v0.22.0-ubuntu2404` solo es x86 | `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` + entrypoint bash |
| P19 | SSH túnel | `Permission denied (publickey)` | Ejecutado desde el Jetson hacia sí mismo | Ejecutar desde Windows: `ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100` |
| P20 | Recursos | Modelo cargado sin saberlo | `--restart unless-stopped` + vLLM reserva RAM al arrancar | `--restart no` en todos los contenedores LLM; auditoría con `jetson-audit` |

---

## B. Estructura de directorios

```
/home/jetson/
├── .bashrc                          # Variables y aliases (exports al inicio)
├── .cache/
│   └── huggingface/
│       └── token                   # Token HF cacheado (volumen Docker)
├── .openclaw/
│   ├── openclaw.json               # Config principal OpenClaw
│   ├── openclaw.json.bak           # Backup automático
│   ├── workspace/
│   │   ├── BOOTSTRAP.md            # Instrucciones del agente
│   │   ├── IDENTITY.md             # Identidad del agente (auto-generado)
│   │   └── USER.md                 # Info del usuario (auto-generado)
│   └── agents/main/sessions/       # Historial de sesiones
├── .config/systemd/user/
│   ├── openclaw-gateway.service    # Gateway (auto-arranque)
│   └── jetson-ai-startup.service   # Stack completo (opcional)
├── scripts/
│   ├── switch-model.sh             # Switcher de modelos
│   ├── jetson-clean.sh             # Limpieza de recursos
│   ├── jetson-harden.sh            # Hardening inicial
│   ├── startup.sh                  # Arranque post-reboot
│   └── watchdog.sh                 # Monitor de memoria
└── jetson-ai-data/
    ├── models/hf/                  # Modelos HuggingFace descargados
    ├── workspaces/                 # Workspaces por proyecto
    └── outputs/                   # Outputs de pipelines
```

---

## C. Checklist de verificación del stack completo

```bash
#!/bin/bash
echo "═══════════════════════════════════════════════════════"
echo "   VERIFICACIÓN COMPLETA DEL STACK"
echo "   $(date)"
echo "═══════════════════════════════════════════════════════"
echo ""

check() {
  local name=$1; local cmd=$2; local expected=$3
  local result=$(eval "$cmd" 2>/dev/null)
  if echo "$result" | grep -q "$expected"; then
    echo "  ✅ $name"
  else
    echo "  ❌ $name → got: ${result:0:60}"
  fi
}

echo "── SISTEMA ──"
check "Ubuntu 24.04"      "lsb_release -r" "24.04"
check "JetPack 7.2"       "cat /etc/nv_tegra_release 2>/dev/null || dpkg -l | grep jetpack" "7.2"
check "CUDA disponible"   "nvcc --version" "release 13"
check "Docker nvidia"     "docker info | grep -i runtime" "nvidia"
check "Python 3.12"       "python3 --version" "3.12"
check "Node.js 22+"       "node --version" "v22"
echo ""

echo "── HF TOKEN ──"
check "Token en disco"    "cat ~/.cache/huggingface/token | head -c 5" "hf_"
check "Token en env"      "echo \$HF_TOKEN | head -c 5" "hf_"
check "Token en /etc/env" "grep HF_TOKEN /etc/environment | head -c 20" "HF_TOKEN=hf"
echo ""

echo "── INFERENCIA ──"
check "vLLM endpoint"     "curl -s http://localhost:8000/v1/models" "data"
echo "  Modelo activo: $(curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "ninguno")"
echo ""

echo "── OPENCLAW ──"
check "Gateway activo"    "openclaw gateway status" "reachable"
check "WhatsApp linked"   "openclaw channels status --probe" "linked"
check "JSON config válido" "python3 -m json.tool ~/.openclaw/openclaw.json" "agents"
check "Profile correcto"  "grep profile ~/.openclaw/openclaw.json" "full"
check "apiKey correcto"   "grep apiKey ~/.openclaw/openclaw.json | grep -v VLLM_API_KEY" "vllm-local"
echo ""

echo "── MEMORIA ──"
FREE=$(free -g | awk '/^Mem:/{print $7}')
echo "  Disponible: ${FREE}GB"
[ "$FREE" -lt 45 ] && echo "  ⚠️  Memoria baja" || echo "  ✅ Memoria OK"
echo ""

echo "── RESTART POLICIES ──"
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys,json
try:
  for c in json.load(sys.stdin):
    n = c['Name'].lstrip('/')
    p = c['HostConfig']['RestartPolicy']['Name']
    flag = '⚠️  RIESGO' if p in ['always','unless-stopped'] else '✅'
    print(f'  {flag} {n}: restart={p}')
except: print('  Sin contenedores')
" 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════════════"
```

Guardar y ejecutar:
```bash
chmod +x ~/scripts/verify-stack.sh
~/scripts/verify-stack.sh
```

---

## Resumen de comandos por letra

```
A → jetson-audit        auditoria de recursos
C → jetson-clean        limpieza total
D → docker-fix-restart  fijar políticas de contenedores
F → mode-idle           free / idle mode
H → ~/scripts/jetson-harden.sh  hardening inicial
L → claw-logs           ver logs openclaw
M → model-status        qué modelo está activo
O → mode-openclaw       agente whatsapp gemma
P → pwr-status          modo de poder actual
Q → claw-tui            interfaz de terminal openclaw
R → claw-restart        reiniciar gateway
S → ~/scripts/verify-stack.sh  verificación completa
T → jetson-top          monitor interactivo (jtop)
V → ~/scripts/switch-model.sh  cambiar modelo
W → claw-wa             logs whatsapp en tiempo real
```

---

*Versión: 2.0 — 2026-06-28 · Jetson AGX Orin 64GB · JetPack 7.2 · OpenClaw 2026.6.10*
*Todos los comandos verificados en producción durante esta sesión de instalación*
