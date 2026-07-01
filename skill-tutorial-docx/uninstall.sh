#!/usr/bin/env bash
# =============================================================================
# uninstall.sh — Desinstalador del Skill /tutorial-docx
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

CLAUDE_DIR="${HOME}/.claude"
COMMANDS_DIR="${CLAUDE_DIR}/commands"

echo ""
echo -e "${BOLD}${RED}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${RED}║     Skill /tutorial-docx — Desinstalador v1.0           ║${NC}"
echo -e "${BOLD}${RED}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Confirmar
read -r -p "¿Deseas desinstalar el skill /tutorial-docx? [s/N] " confirm
[[ "${confirm,,}" == "s" ]] || { echo "Cancelado."; exit 0; }

# Eliminar archivos
BUILDER="${CLAUDE_DIR}/tutorial_docx_builder.py"
SKILL="${COMMANDS_DIR}/tutorial-docx.md"

if [ -f "${BUILDER}" ]; then
    rm "${BUILDER}"
    ok "Eliminado: ${BUILDER}"
else
    warn "No encontrado: ${BUILDER}"
fi

if [ -f "${SKILL}" ]; then
    rm "${SKILL}"
    ok "Eliminado: ${SKILL}"
else
    warn "No encontrado: ${SKILL}"
fi

# Ofrecer eliminar python-docx (opcional)
echo ""
read -r -p "¿Desinstalar también python-docx? [s/N] " rm_dep
if [[ "${rm_dep,,}" == "s" ]]; then
    pip3 uninstall python-docx -y && ok "python-docx desinstalado" || warn "No se pudo desinstalar python-docx"
fi

echo ""
ok "Desinstalación completada."
echo ""
