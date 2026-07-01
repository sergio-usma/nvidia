#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# INNOVALABS — Setup inicial del stack Docker
# ═══════════════════════════════════════════════════════════════
# Ejecutar UNA VEZ antes del primer 'docker compose up'.
# Valida el entorno, crea directorios, descarga modelos y
# genera el archivo .env si no existe.
#
# Uso:
#   chmod +x setup.sh
#   ./setup.sh              # Modo interactivo
#   ./setup.sh --check      # Solo verificar (no modificar nada)
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colores ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${CYAN}ℹ${NC} $1"; }
header() { echo -e "\n${BOLD}$1${NC}"; }

CHECK_ONLY=false
if [[ "${1:-}" == "--check" ]]; then
    CHECK_ONLY=true
fi

ERRORS=0

# ─────────────────────────────────────────────
header "═══ INNOVALABS — Verificación de entorno ═══"
# ─────────────────────────────────────────────

# ── 1. Arquitectura ──
header "1. Arquitectura del sistema"
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]]; then
    ok "Arquitectura: $ARCH (Jetson compatible)"
else
    warn "Arquitectura: $ARCH (esperado: aarch64 para Jetson)"
fi

# Detectar JetPack
if [[ -f /etc/nv_tegra_release ]]; then
    JP_VERSION=$(cat /etc/nv_tegra_release | head -1)
    ok "Tegra detectado: $JP_VERSION"
else
    warn "No se detectó /etc/nv_tegra_release (¿es un Jetson?)"
fi

# ── 2. Docker ──
header "2. Docker"
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null || echo "desconocida")
    ok "Docker instalado: $DOCKER_VERSION"
else
    fail "Docker no encontrado. Instalar con: sudo apt install docker.io"
    ((ERRORS++))
fi

if command -v docker &>/dev/null && docker compose version &>/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version 2>/dev/null || echo "desconocida")
    ok "Docker Compose: $COMPOSE_VERSION"
else
    fail "Docker Compose V2 no encontrado. Instalar con: sudo apt install docker-compose-plugin"
    ((ERRORS++))
fi

# ── 3. NVIDIA Container Runtime ──
header "3. NVIDIA Container Runtime"
if docker info 2>/dev/null | grep -q "nvidia"; then
    ok "NVIDIA runtime detectado en Docker"
elif [[ -f /etc/nvidia-container-runtime/config.toml ]]; then
    ok "nvidia-container-runtime config encontrada"
else
    fail "NVIDIA Container Runtime no detectado"
    info "Instalar con: sudo apt install nvidia-container-toolkit"
    info "Luego: sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker"
    ((ERRORS++))
fi

# ── 4. CUDA ──
header "4. CUDA"
if [[ -d /usr/local/cuda ]]; then
    CUDA_VERSION=$(cat /usr/local/cuda/version.json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['cuda']['version'])" 2>/dev/null || echo "detectado")
    ok "CUDA encontrado: $CUDA_VERSION en /usr/local/cuda"
else
    fail "CUDA no encontrado en /usr/local/cuda"
    info "En JetPack 6.2.2, CUDA debería estar instalado automáticamente"
    ((ERRORS++))
fi

# ── 5. llama-cli ──
header "5. llama-cli"
LLAMA_CLI_PATHS=(
    "$HOME/.local/bin/llama-cli"
    "/usr/local/bin/llama-cli"
    "$HOME/llama.cpp/build/bin/llama-cli"
)
LLAMA_CLI_FOUND=""
for path in "${LLAMA_CLI_PATHS[@]}"; do
    if [[ -x "$path" ]]; then
        LLAMA_CLI_FOUND="$path"
        break
    fi
done

if [[ -n "$LLAMA_CLI_FOUND" ]]; then
    ok "llama-cli encontrado: $LLAMA_CLI_FOUND"
else
    fail "llama-cli no encontrado en rutas conocidas"
    info "Compilar con: cmake -B build -DGGML_CUDA=ON && cmake --build build --target llama-cli"
    info "Rutas buscadas: ${LLAMA_CLI_PATHS[*]}"
    ((ERRORS++))
fi

# ── 6. Modelo GGUF ──
header "6. Modelo Qwen3.5-27B GGUF"
MODEL_DIRS=(
    "$HOME/.cache/llama.cpp"
    "$HOME/models"
    "/models"
)
MODEL_FILE="unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf"
MODEL_FOUND=""
for dir in "${MODEL_DIRS[@]}"; do
    if [[ -f "$dir/$MODEL_FILE" ]]; then
        MODEL_FOUND="$dir/$MODEL_FILE"
        SIZE=$(du -h "$MODEL_FOUND" 2>/dev/null | cut -f1)
        break
    fi
done

if [[ -n "$MODEL_FOUND" ]]; then
    ok "Modelo encontrado: $MODEL_FOUND ($SIZE)"
else
    warn "Modelo GGUF no encontrado: $MODEL_FILE"
    info "Directorios buscados: ${MODEL_DIRS[*]}"
    info "Descargar con: huggingface-cli download unsloth/Qwen3.5-27B-GGUF $MODEL_FILE"
fi

# ── 7. Python y pytrends ──
header "7. Python (para Scout)"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    ok "Python: $PY_VERSION"
else
    fail "Python3 no encontrado"
    ((ERRORS++))
fi

if python3 -c "import pytrends" 2>/dev/null; then
    ok "pytrends instalado"
else
    warn "pytrends no instalado (pip install pytrends)"
    info "El Scout usará modo fallback sin Google Trends"
fi

# ── 8. Memoria ──
header "8. Memoria disponible"
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
FREE_RAM=$(free -m | awk '/^Mem:/{print $7}')
ok "RAM total: ${TOTAL_RAM} MB | Disponible: ${FREE_RAM} MB"
if [[ $TOTAL_RAM -lt 50000 ]]; then
    warn "Se recomiendan 64 GB para el pipeline completo (detectados: ${TOTAL_RAM} MB)"
fi

# ─────────────────────────────────────────────
# Fase de configuración (omitir si --check)
# ─────────────────────────────────────────────

if [[ "$CHECK_ONLY" == true ]]; then
    header "═══ Resumen (solo verificación) ═══"
    if [[ $ERRORS -gt 0 ]]; then
        fail "$ERRORS problemas críticos encontrados"
        exit 1
    else
        ok "Entorno compatible. Ejecutar sin --check para configurar."
        exit 0
    fi
fi

header "═══ Configuración ═══"

# ── Crear directorios ──
info "Creando directorios..."
sudo mkdir -p /opt/innovalabs/scripts
sudo mkdir -p /var/opt/innovalabs/historias
sudo chown -R "$USER:$USER" /opt/innovalabs /var/opt/innovalabs
ok "Directorios creados"

# ── Copiar scout_trends.py si existe en el directorio actual ──
if [[ -f "./scout_trends.py" ]]; then
    cp ./scout_trends.py /opt/innovalabs/scripts/
    chmod +x /opt/innovalabs/scripts/scout_trends.py
    ok "scout_trends.py copiado a /opt/innovalabs/scripts/"
elif [[ -f "/opt/innovalabs/scripts/scout_trends.py" ]]; then
    ok "scout_trends.py ya existe en /opt/innovalabs/scripts/"
else
    warn "scout_trends.py no encontrado. Copiarlo manualmente a /opt/innovalabs/scripts/"
fi

# ── Generar .env si no existe ──
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        info "Generando .env desde .env.example..."
        cp .env.example .env

        # Auto-detectar rutas
        if [[ -n "$LLAMA_CLI_FOUND" ]]; then
            sed -i "s|LLAMA_CLI_PATH=.*|LLAMA_CLI_PATH=$LLAMA_CLI_FOUND|" .env
        fi
        if [[ -n "$MODEL_FOUND" ]]; then
            MODEL_DIR=$(dirname "$MODEL_FOUND")
            sed -i "s|LLAMA_MODELS_DIR=.*|LLAMA_MODELS_DIR=$MODEL_DIR|" .env
        fi

        # Generar encryption key
        ENC_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s|N8N_ENCRYPTION_KEY=.*|N8N_ENCRYPTION_KEY=$ENC_KEY|" .env

        ok ".env generado con rutas auto-detectadas"
        warn "Revisar y ajustar .env antes de continuar (especialmente GSHEETS_SPREADSHEET_ID)"
    else
        fail ".env.example no encontrado en el directorio actual"
        ((ERRORS++))
    fi
else
    ok ".env ya existe"
fi

# ── Descargar modelos de Ollama ──
header "═══ Descarga de modelos ═══"
info "¿Descargar los 3 modelos de Ollama ahora? (puede tardar ~15 min)"
info "Modelos: glm-4.7-flash, deepseek-r1:8b, nemotron-3-nano"
read -rp "  [S/n]: " DOWNLOAD_MODELS
DOWNLOAD_MODELS=${DOWNLOAD_MODELS:-S}

if [[ "${DOWNLOAD_MODELS,,}" == "s" ]]; then
    info "Levantando Ollama temporalmente para descargar modelos..."
    docker compose up -d ollama
    sleep 10

    MODELS=("glm-4.7-flash:latest" "deepseek-r1:8b" "nemotron-3-nano:latest")
    for model in "${MODELS[@]}"; do
        info "Descargando $model..."
        docker exec innovalabs-ollama ollama pull "$model" && \
            ok "$model descargado" || \
            fail "Error descargando $model"
    done

    docker compose stop ollama
    ok "Modelos descargados. Ollama detenido."
else
    info "Omitiendo descarga. Descargar manualmente con:"
    info "  docker exec innovalabs-ollama ollama pull glm-4.7-flash:latest"
    info "  docker exec innovalabs-ollama ollama pull deepseek-r1:8b"
    info "  docker exec innovalabs-ollama ollama pull nemotron-3-nano:latest"
fi

# ─────────────────────────────────────────────
header "═══ Resumen final ═══"
# ─────────────────────────────────────────────

if [[ $ERRORS -gt 0 ]]; then
    fail "$ERRORS problemas críticos encontrados. Resolver antes de continuar."
    exit 1
fi

ok "Setup completado exitosamente"
echo ""
info "Próximos pasos:"
echo "  1. Revisar y ajustar el archivo .env"
echo "  2. Levantar el stack:  docker compose up -d"
echo "  3. Acceder a n8n:      http://localhost:${N8N_PORT:-5678}"
echo "  4. Importar el workflow: INNOVALABS_Literature_Factory_v1.0.json"
echo "  5. Configurar las credenciales de Google Sheets en n8n"
echo "  6. Activar el workflow"
echo ""
