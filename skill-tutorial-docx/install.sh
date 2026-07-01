#!/usr/bin/env bash
# =============================================================================
# install.sh — Instalador del Skill /tutorial-docx para Claude Code
# =============================================================================
# Instala el skill que transforma archivos Markdown / texto plano en tutoriales
# IT profesionales en formato DOCX (estilo O'Reilly / Apress), en español.
#
# Compatibilidad: Linux / macOS con Claude Code CLI instalado.
# Dependencia:    Python 3 + pip (python-docx se instala automáticamente)
# =============================================================================

set -euo pipefail

# ── Colores ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
section() { echo -e "\n${BOLD}$*${NC}"; echo "$(printf '─%.0s' {1..60})"; }

# ── Rutas destino ─────────────────────────────────────────────────────────────
CLAUDE_DIR="${HOME}/.claude"
COMMANDS_DIR="${CLAUDE_DIR}/commands"
BUILDER_DEST="${CLAUDE_DIR}/tutorial_docx_builder.py"
SKILL_DEST="${COMMANDS_DIR}/tutorial-docx.md"

# Directorio donde está este script (independiente de desde dónde se llame)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     Skill /tutorial-docx — Instalador v1.0              ║${NC}"
echo -e "${BOLD}${CYAN}║     Generador de Tutoriales IT Profesionales en DOCX     ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Verificar requisitos ───────────────────────────────────────────────────
section "1. Verificando requisitos del sistema"

command -v python3 &>/dev/null || error "Python 3 no está instalado. Instálalo con: sudo apt install python3"
ok "Python 3 encontrado: $(python3 --version)"

command -v pip3 &>/dev/null || {
    warn "pip3 no encontrado. Intentando instalar..."
    sudo apt-get install -y python3-pip 2>/dev/null || error "No se pudo instalar pip3. Instálalo manualmente."
}
ok "pip3 encontrado: $(pip3 --version | cut -d' ' -f1-2)"

# Verificar que Claude Code esté instalado (opcional pero informativo)
if command -v claude &>/dev/null; then
    ok "Claude Code CLI encontrado: $(claude --version 2>/dev/null | head -1 || echo 'instalado')"
else
    warn "Claude Code CLI no encontrado en PATH. El skill se instalará igualmente pero"
    warn "necesitarás tener Claude Code instalado para poder usarlo."
fi

# ── 2. Instalar python-docx ───────────────────────────────────────────────────
section "2. Instalando dependencia Python: python-docx"

if python3 -c "import docx" &>/dev/null; then
    CURRENT_VER=$(python3 -c "import docx; print(docx.__version__)" 2>/dev/null || echo "desconocida")
    ok "python-docx ya instalado (versión ${CURRENT_VER})"
else
    info "Instalando python-docx..."
    pip3 install python-docx --quiet || error "No se pudo instalar python-docx."
    ok "python-docx instalado correctamente"
fi

# Verificar versión mínima
DOCX_VER=$(python3 -c "import docx; print(docx.__version__)" 2>/dev/null || echo "0.0.0")
REQUIRED_VER="1.1.0"
python3 -c "
v = '${DOCX_VER}'.split('.')
r = '${REQUIRED_VER}'.split('.')
ok = tuple(int(x) for x in v) >= tuple(int(x) for x in r)
exit(0 if ok else 1)
" || {
    warn "Versión de python-docx (${DOCX_VER}) inferior a la recomendada (${REQUIRED_VER})."
    warn "Actualizando..."
    pip3 install --upgrade python-docx --quiet
    ok "python-docx actualizado"
}

# ── 3. Crear directorios de destino ───────────────────────────────────────────
section "3. Preparando directorios de Claude Code"

mkdir -p "${COMMANDS_DIR}"
ok "Directorio commands: ${COMMANDS_DIR}"

# ── 4. Instalar archivos ──────────────────────────────────────────────────────
section "4. Instalando archivos del skill"

# Hacer backup si ya existen versiones previas
if [ -f "${BUILDER_DEST}" ]; then
    BACKUP="${BUILDER_DEST}.bak.$(date +%Y%m%d_%H%M%S)"
    cp "${BUILDER_DEST}" "${BACKUP}"
    warn "Versión previa del builder guardada en: ${BACKUP}"
fi

if [ -f "${SKILL_DEST}" ]; then
    BACKUP="${SKILL_DEST}.bak.$(date +%Y%m%d_%H%M%S)"
    cp "${SKILL_DEST}" "${BACKUP}"
    warn "Versión previa del skill guardada en: ${BACKUP}"
fi

# Copiar archivos
cp "${SCRIPT_DIR}/tutorial_docx_builder.py" "${BUILDER_DEST}"
ok "Builder instalado en: ${BUILDER_DEST}"

cp "${SCRIPT_DIR}/tutorial-docx.md" "${SKILL_DEST}"
ok "Skill instalado en: ${SKILL_DEST}"

# ── 5. Verificar instalación ──────────────────────────────────────────────────
section "5. Verificando la instalación"

# Verificar importación del builder
python3 -c "
import sys
sys.path.insert(0, '${CLAUDE_DIR}')
from tutorial_docx_builder import generate_tutorial_docx, create_document
print('Builder importado correctamente')
" || error "El builder no se puede importar. Revisa los errores anteriores."
ok "Módulo Python: importación verificada"

# Verificar que el skill está accesible
[ -f "${SKILL_DEST}" ] || error "El archivo del skill no se encuentra en ${SKILL_DEST}"
ok "Skill Claude Code: accesible en ${SKILL_DEST}"

# Test de generación rápida
info "Ejecutando prueba de generación de DOCX..."
python3 - <<'PYEOF'
import sys
sys.path.insert(0, f"{__import__('os').path.expanduser('~')}/.claude")
from tutorial_docx_builder import generate_tutorial_docx

content = {
    "title":    "Prueba de Instalación",
    "subtitle": "Skill /tutorial-docx",
    "version":  "v1.0",
    "date":     "2026",
    "specs":    {"Estado": "Instalación verificada"},
    "chapters": [{
        "number": 1, "title": "Verificación del Sistema",
        "description": "Test de instalación",
        "label": "Fase", "toc_label": "Fase 1",
        "objective": "Confirmar que el skill funciona correctamente.",
        "sections": [
            {"type": "body",    "content": "La instalación del skill se ha completado con éxito."},
            {"type": "callout", "callout_type": "CONSEJO",
             "content": "Usa /tutorial-docx <ruta/archivo.md> en Claude Code para generar tutoriales."}
        ]
    }],
    "appendices": []
}
out = generate_tutorial_docx(content, "/tmp/skill_install_test.docx")
import os
size = os.path.getsize(out)
assert size > 5000, f"Archivo demasiado pequeño: {size} bytes"
PYEOF
ok "Prueba de generación DOCX: correcta (/tmp/skill_install_test.docx)"

# ── 6. Resumen final ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          ✓  Instalación completada con éxito             ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Cómo usar el skill:${NC}"
echo ""
echo -e "  Dentro de Claude Code, escribe:"
echo -e "  ${CYAN}/tutorial-docx /ruta/al/archivo.md${NC}"
echo ""
echo -e "  Ejemplo:"
echo -e "  ${CYAN}/tutorial-docx ~/Desktop/mi_guia.md${NC}"
echo ""
echo -e "  El archivo .docx se generará en la misma carpeta que el archivo de entrada."
echo ""
