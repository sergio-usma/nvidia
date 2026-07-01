#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# INNOVALABS — Verificación completa del sistema
# ═══════════════════════════════════════════════════════════════
# Ejecutar después de completar la instalación para validar
# que todos los componentes están operativos.
#
# Uso:
#   chmod +x verify_system.sh
#   ./verify_system.sh
# ═══════════════════════════════════════════════════════════════

set -uo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0; FAIL=0; WARN=0

check() {
  if eval "$2" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $1"; ((PASS++))
  else
    echo -e "  ${RED}✗${NC} $1"; ((FAIL++))
  fi
}

warn_check() {
  if eval "$2" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $1"; ((PASS++))
  else
    echo -e "  ${YELLOW}⚠${NC} $1 (no crítico)"; ((WARN++))
  fi
}

echo ""
echo "═══ INNOVALABS — Verificación del sistema ═══"
echo ""

echo "── Hardware y OS ──"
check "Arquitectura aarch64"            '[[ "$(uname -m)" == "aarch64" ]]'
check "Ubuntu 22.04"                    'lsb_release -d 2>/dev/null | grep -q "22.04"'
check "Kernel tegra"                    'uname -r | grep -q tegra'
check "RAM >= 60 GB"                    '[[ $(free -m | awk "/Mem:/{print \$2}") -ge 60000 ]]'
warn_check "Swap >= 8 GB"              '[[ $(free -m | awk "/Swap:/{print \$2}") -ge 8000 ]]'
check "Timezone America/Bogota"         'timedatectl 2>/dev/null | grep -q "America/Bogota"'

echo ""
echo "── NVIDIA / CUDA ──"
check "JetPack 6.2.2"                  'dpkg -l 2>/dev/null | grep -q "nvidia-jetpack.*6.2.2"'
check "CUDA 12.6 (nvcc)"              'nvcc --version 2>&1 | grep -q "12.6"'
check "/usr/local/cuda existe"         'test -d /usr/local/cuda'
check "CUDA en PATH"                   'which nvcc > /dev/null 2>&1'
check "LD_LIBRARY_PATH con CUDA"       'echo $LD_LIBRARY_PATH | grep -q cuda'
warn_check "cuDNN 9.x"                'cat /usr/include/cudnn_version.h 2>/dev/null | grep -q "CUDNN_MAJOR 9"'
warn_check "TensorRT 10.x"            'dpkg -l 2>/dev/null | grep -q "tensorrt.*10\."'

echo ""
echo "── Docker ──"
check "Docker instalado"               'docker --version > /dev/null 2>&1'
check "Docker Compose V2"              'docker compose version > /dev/null 2>&1'
check "NVIDIA runtime en Docker"       'docker info 2>/dev/null | grep -q nvidia'
check "Docker socket accesible"        'test -S /var/run/docker.sock'
check "Usuario en grupo docker"        'groups | grep -q docker'

echo ""
echo "── Ollama ──"
OLLAMA_NATIVE=$(which ollama 2>/dev/null && echo "native" || echo "")
OLLAMA_DOCKER=$(docker inspect innovalabs-ollama 2>/dev/null && echo "docker" || echo "")
if [[ -n "$OLLAMA_NATIVE" ]]; then
  echo -e "  ${GREEN}✓${NC} Ollama (instalación nativa)"
  ((PASS++))
elif [[ -n "$OLLAMA_DOCKER" ]]; then
  echo -e "  ${GREEN}✓${NC} Ollama (contenedor Docker)"
  ((PASS++))
else
  echo -e "  ${RED}✗${NC} Ollama no encontrado"
  ((FAIL++))
fi
check "Ollama API respondiendo"        'curl -sf http://localhost:11434/api/tags > /dev/null'
check "Modelo: glm-4.7-flash"         'curl -sf http://localhost:11434/api/tags | grep -q "glm-4.7-flash"'
check "Modelo: deepseek-r1:8b"        'curl -sf http://localhost:11434/api/tags | grep -q "deepseek-r1"'
check "Modelo: nemotron-3-nano"        'curl -sf http://localhost:11434/api/tags | grep -q "nemotron"'

echo ""
echo "── llama.cpp ──"
check "llama-cli en PATH"             'which llama-cli > /dev/null 2>&1'

# Buscar el modelo GGUF
MODEL_FOUND=false
for dir in ~/.cache/llama.cpp ~/models /models; do
  if ls "$dir"/*Qwen3.5-27B*Q4*.gguf 2>/dev/null | head -1 > /dev/null; then
    MODEL_FOUND=true
    MODEL_PATH=$(ls "$dir"/*Qwen3.5-27B*Q4*.gguf 2>/dev/null | head -1)
    MODEL_SIZE=$(du -h "$MODEL_PATH" 2>/dev/null | cut -f1)
    echo -e "  ${GREEN}✓${NC} Modelo GGUF Qwen3.5-27B ($MODEL_SIZE en $dir)"
    ((PASS++))
    break
  fi
done
if [[ "$MODEL_FOUND" == "false" ]]; then
  echo -e "  ${RED}✗${NC} Modelo GGUF Qwen3.5-27B no encontrado"
  ((FAIL++))
fi

echo ""
echo "── Python ──"
check "Python 3.10+"                   'python3 --version 2>&1 | grep -qE "3\.(1[0-9]|[2-9][0-9])"'

# Verificar pytrends en venv o sistema
PYTRENDS_OK=false
if python3 -c "import pytrends" 2>/dev/null; then
  PYTRENDS_OK=true
elif [[ -f /opt/innovalabs/venv/bin/activate ]]; then
  if bash -c "source /opt/innovalabs/venv/bin/activate && python3 -c 'import pytrends'" 2>/dev/null; then
    PYTRENDS_OK=true
  fi
fi
if [[ "$PYTRENDS_OK" == "true" ]]; then
  echo -e "  ${GREEN}✓${NC} pytrends instalado"
  ((PASS++))
else
  echo -e "  ${YELLOW}⚠${NC} pytrends no instalado (Scout usará modo fallback)"
  ((WARN++))
fi

echo ""
echo "── n8n ──"
N8N_NATIVE=$(which n8n 2>/dev/null && echo "native" || echo "")
N8N_DOCKER=$(docker inspect innovalabs-n8n 2>/dev/null && echo "docker" || echo "")
if [[ -n "$N8N_NATIVE" ]]; then
  echo -e "  ${GREEN}✓${NC} n8n (instalación nativa)"
  ((PASS++))
elif [[ -n "$N8N_DOCKER" ]]; then
  echo -e "  ${GREEN}✓${NC} n8n (contenedor Docker)"
  ((PASS++))
else
  echo -e "  ${RED}✗${NC} n8n no encontrado"
  ((FAIL++))
fi
check "n8n respondiendo"               'curl -sf http://localhost:5678/healthz > /dev/null'

echo ""
echo "── Estructura de archivos ──"
check "scout_trends.py"                'test -f /opt/innovalabs/scripts/scout_trends.py'
warn_check "writer_bridge.sh"          'test -f /opt/innovalabs/scripts/writer_bridge.sh'
check "Directorio de historias"        'test -d /var/opt/innovalabs/historias'
check "Permisos de escritura"          'test -w /var/opt/innovalabs/historias'

echo ""
echo "── Test funcional del Scout ──"
SCOUT_CMD="python3 /opt/innovalabs/scripts/scout_trends.py --dry-run"
if [[ -f /opt/innovalabs/venv/bin/activate ]]; then
  SCOUT_CMD="bash -c 'source /opt/innovalabs/venv/bin/activate && $SCOUT_CMD'"
fi
SCOUT_OUTPUT=$(eval "$SCOUT_CMD" 2>/dev/null)
if echo "$SCOUT_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['tema']" 2>/dev/null; then
  echo -e "  ${GREEN}✓${NC} Scout dry-run produce JSON válido"
  ((PASS++))
else
  echo -e "  ${RED}✗${NC} Scout dry-run falló"
  ((FAIL++))
fi

# ── Resumen ──
echo ""
echo "══════════════════════════════════════════"
TOTAL=$((PASS + FAIL + WARN))
echo -e "  ${GREEN}$PASS pasaron${NC} / ${RED}$FAIL fallaron${NC} / ${YELLOW}$WARN advertencias${NC}  (total: $TOTAL)"

if [[ $FAIL -eq 0 ]]; then
  echo ""
  echo -e "  ${GREEN}Sistema listo para producción.${NC}"
  echo "  Siguiente paso: importar el workflow en n8n y activar."
else
  echo ""
  echo -e "  ${RED}Hay $FAIL problemas que resolver antes de activar el pipeline.${NC}"
  echo "  Revisar la sección correspondiente en INSTALL.md."
fi
echo "══════════════════════════════════════════"
echo ""
