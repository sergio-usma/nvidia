#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# INNOVALABS — Writer Bridge
# ═══════════════════════════════════════════════════════════════
# Script puente que n8n ejecuta para invocar llama-cli
# dentro del contenedor 'innovalabs-writer' via docker exec.
#
# Uso (desde el nodo Execute Command de n8n):
#   /opt/innovalabs/scripts/writer_bridge.sh \
#     --prompt "Tu prompt aquí..." \
#     --output "/shared/historia_H-123_raw.txt"
#
# Parámetros opcionales:
#   --model   "nombre_modelo.gguf"   (default: variable de entorno)
#   --ctx     8192                    (ventana de contexto)
#   --tokens  8000                    (máx tokens salida)
#   --temp    0.8                     (temperatura)
#   --repeat  1.1                     (penalización de repetición)
#   --ngl     999                     (capas GPU)
#
# El archivo de salida se escribe en /shared/ (volumen compartido
# entre n8n y writer), accesible desde ambos contenedores.
#
# Exit codes:
#   0 = OK
#   1 = Error de parámetros
#   2 = Writer container no disponible
#   3 = Error de ejecución de llama-cli
#   4 = Output vacío o demasiado corto
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Defaults ──
CONTAINER="innovalabs-writer"
MODEL_FILE="${QWEN_MODEL_FILE:-unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf}"
MODEL_PATH="/models/${MODEL_FILE}"
CTX_SIZE="${LLAMA_CTX_SIZE:-8192}"
MAX_TOKENS="${LLAMA_MAX_TOKENS:-8000}"
TEMPERATURE="0.8"
REPEAT_PENALTY="1.1"
NGL="${LLAMA_NGL:-999}"
PROMPT=""
OUTPUT_FILE=""
TIMEOUT=1800  # 30 minutos

# ── Logging (a stderr, stdout libre para n8n) ──
log() { echo "[WRITER-BRIDGE $(date '+%H:%M:%S')] $1" >&2; }

# ── Parsear argumentos ──
while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt)   PROMPT="$2"; shift 2 ;;
        --output)   OUTPUT_FILE="$2"; shift 2 ;;
        --model)    MODEL_FILE="$2"; MODEL_PATH="/models/$2"; shift 2 ;;
        --ctx)      CTX_SIZE="$2"; shift 2 ;;
        --tokens)   MAX_TOKENS="$2"; shift 2 ;;
        --temp)     TEMPERATURE="$2"; shift 2 ;;
        --repeat)   REPEAT_PENALTY="$2"; shift 2 ;;
        --ngl)      NGL="$2"; shift 2 ;;
        --timeout)  TIMEOUT="$2"; shift 2 ;;
        *)          log "Argumento desconocido: $1"; exit 1 ;;
    esac
done

# ── Validar parámetros requeridos ──
if [[ -z "$PROMPT" ]]; then
    log "ERROR: --prompt es requerido"
    exit 1
fi

if [[ -z "$OUTPUT_FILE" ]]; then
    # Generar nombre automático
    OUTPUT_FILE="/shared/historia_$(date +%s)_raw.txt"
    log "Output auto-generado: $OUTPUT_FILE"
fi

# ── Verificar que el contenedor Writer está corriendo ──
log "Verificando contenedor $CONTAINER..."
if ! docker inspect --format='{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q "true"; then
    log "ERROR: Contenedor $CONTAINER no está corriendo"
    log "Intentando levantar..."
    docker start "$CONTAINER" 2>/dev/null || {
        log "ERROR: No se pudo iniciar $CONTAINER"
        exit 2
    }
    sleep 3
fi

# ── Verificar que el modelo existe en el contenedor ──
log "Verificando modelo en $MODEL_PATH..."
if ! docker exec "$CONTAINER" test -f "$MODEL_PATH"; then
    log "ERROR: Modelo no encontrado en $CONTAINER:$MODEL_PATH"
    log "Modelos disponibles:"
    docker exec "$CONTAINER" ls -la /models/ 2>&1 >&2 || true
    exit 2
fi

# ── Escribir prompt a archivo temporal (evita problemas de escape en CLI) ──
PROMPT_FILE="/shared/.prompt_$(date +%s%N).txt"
log "Escribiendo prompt a archivo temporal..."
docker exec "$CONTAINER" sh -c "cat > $PROMPT_FILE" <<< "$PROMPT"

# ── Construir y ejecutar el comando ──
LLAMA_CMD="llama-cli \
  -m ${MODEL_PATH} \
  -ngl ${NGL} \
  -c ${CTX_SIZE} \
  -n ${MAX_TOKENS} \
  --temp ${TEMPERATURE} \
  --repeat-penalty ${REPEAT_PENALTY} \
  -f ${PROMPT_FILE} \
  2>/dev/null"

log "Ejecutando llama-cli (timeout: ${TIMEOUT}s)..."
log "  Modelo: $MODEL_FILE"
log "  Contexto: $CTX_SIZE | Max tokens: $MAX_TOKENS"
log "  Temp: $TEMPERATURE | Repeat penalty: $REPEAT_PENALTY"
log "  GPU layers: $NGL"

START_TIME=$(date +%s)

# Ejecutar con timeout
# La salida va directamente al archivo dentro del contenedor
if timeout "$TIMEOUT" docker exec "$CONTAINER" sh -c \
    "${LLAMA_CMD} > ${OUTPUT_FILE}"; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 124 ]]; then
        log "ERROR: Timeout alcanzado (${TIMEOUT}s)"
    else
        log "ERROR: llama-cli falló con código $EXIT_CODE"
    fi
fi

# ── Limpiar prompt temporal ──
docker exec "$CONTAINER" rm -f "$PROMPT_FILE" 2>/dev/null || true

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
log "Tiempo de ejecución: ${ELAPSED}s"

# ── Verificar output ──
if [[ $EXIT_CODE -ne 0 ]]; then
    exit 3
fi

# Verificar que el archivo existe y tiene contenido mínimo
OUTPUT_SIZE=$(docker exec "$CONTAINER" wc -c < "$OUTPUT_FILE" 2>/dev/null || echo "0")
OUTPUT_SIZE=$(echo "$OUTPUT_SIZE" | tr -d '[:space:]')

if [[ "$OUTPUT_SIZE" -lt 500 ]]; then
    log "ERROR: Output demasiado corto ($OUTPUT_SIZE bytes). Posible generación fallida."
    exit 4
fi

log "Output generado: $OUTPUT_FILE ($OUTPUT_SIZE bytes)"

# ── Emitir metadata a stdout (para n8n) ──
cat <<EOF
{
  "output_file": "$OUTPUT_FILE",
  "output_size_bytes": $OUTPUT_SIZE,
  "execution_time_seconds": $ELAPSED,
  "model": "$MODEL_FILE",
  "parameters": {
    "ctx": $CTX_SIZE,
    "max_tokens": $MAX_TOKENS,
    "temperature": $TEMPERATURE,
    "repeat_penalty": $REPEAT_PENALTY,
    "ngl": $NGL
  }
}
EOF

log "Writer bridge completado exitosamente"
exit 0
