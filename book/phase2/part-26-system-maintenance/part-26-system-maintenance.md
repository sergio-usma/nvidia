# Capítulo 26 — Mantenimiento del Sistema y Scripts de Limpieza

## Introducción

Este capítulo reúne todos los scripts de mantenimiento, monitoreo y limpieza que hacen que el Jetson funcione de forma fiable a lo largo del tiempo. Es una referencia transversal que los demás capítulos de  citan constantemente.

Un sistema de inferencia que no se mantiene acumula problemas: contenedores huérfanos que ocupan RAM, imágenes antiguas que llenan el disco, temperaturas elevadas que reducen el rendimiento, logs que crecen indefinidamente. Los scripts de este capítulo resuelven todos esos escenarios.

**Prerrequisitos:** Capítulos 19–25 completados (proyectos de IA activos).

**Al final de este capítulo tendrá:**
- Sistema de verificación pre-pipeline que todos los proyectos pueden invocar
- Script de limpieza parametrizable de contenedores de proyectos
- Script de salud semanal con log histórico
- Benchmark automatizado para verificar que el rendimiento no degradó
- Aliases de mantenimiento en `~/.bash_aliases`
- Limpieza de caché Hugging Face configurable

---

## 26.1 Directorio de Scripts de Mantenimiento

```bash
# Crear estructura de scripts de mantenimiento
mkdir -p ~/scripts/maintenance

ls ~/scripts/
```

```
# Estructura resultante
maintenance/
├── check-ready.sh      # Verificación pre-pipeline
├── clean-ai-containers.sh       # Limpieza de contenedores de proyectos
├── switch-project.sh            # Cambio entre proyectos de IA
├── hf-cache-clean.sh      # Limpieza caché Hugging Face
├── health-check.sh        # Diagnóstico semanal completo
└── system-status.sh       # Estado general del sistema (rápido)
```

---

## 26.2 Script 1 — Verificación Pre-Pipeline

Este script es el guardián que cada pipeline debe invocar antes de arrancar. Previene fallos por RAM insuficiente, temperatura elevada o disco lleno.

```bash
# ~/scripts/maintenance/check-ready.sh
#!/bin/bash
#
# Verifica que el sistema está listo para ejecutar un proyecto de IA.
# Uso: check-ready.sh <min-ram-GB> "nombre-proyecto"
# Ejemplo: check-ready 20 "PDF-to-podcast"
# Retorna: 0 si listo, 1 si no cumple los requisitos
#

MIN_RAM_GB="${1:-20}"
PIPELINE_NAME="${2:-proyecto}"
MAX_TEMP_C=75
MIN_DISK_GB=10

PASS=true
echo "── Verificación pre-proyecto: $PIPELINE_NAME ──"

# RAM disponible
LIBRE_GB=$(awk '/MemAvailable/{printf "%.0f", $2/1024/1024}' /proc/meminfo)
if [ "$LIBRE_GB" -lt "$MIN_RAM_GB" ]; then
  echo "  [WARN]  RAM libre: ${LIBRE_GB} GB (mínimo ${MIN_RAM_GB} GB requerido)"
  echo "      Solución: ejecute 'clean-ai-containers && pwr-15w && sleep 10'"
  PASS=false
else
  echo "  [OK] RAM libre: ${LIBRE_GB} GB (mínimo ${MIN_RAM_GB} GB)"
fi

# Temperatura
TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
if [ -f "$TEMP_FILE" ]; then
  TEMP_C=$(awk '{printf "%.0f", $1/1000}' "$TEMP_FILE")
  if [ "$TEMP_C" -gt "$MAX_TEMP_C" ]; then
    echo "  [WARN]  Temperatura: ${TEMP_C}°C (límite ${MAX_TEMP_C}°C)"
    echo "      Espere que el sistema enfríe antes de continuar"
    PASS=false
  else
    echo "  [OK] Temperatura: ${TEMP_C}°C"
  fi
fi

# Espacio en disco
DISCO_LIBRE=$(df / --output=avail -BG | tail -1 | tr -d 'G ')
if [ "$DISCO_LIBRE" -lt "$MIN_DISK_GB" ]; then
  echo "  [WARN]  Disco libre: ${DISCO_LIBRE} GB (mínimo ${MIN_DISK_GB} GB)"
  echo "      Solución: 'docker image prune -f' o limpie archivos temporales"
  PASS=false
else
  echo "  [OK] Disco libre: ${DISCO_LIBRE} GB"
fi

# Contenedores activos que podrían interferir
ACTIVOS=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "whisper|kokoro|piper|vllm|llama" | head -5)
if [ -n "$ACTIVOS" ]; then
  echo "  [INFO] Contenedores GPU activos:"
  echo "$ACTIVOS" | while read n; do echo "      - $n"; done
  echo "      Verifique que no habrá conflictos de memoria"
fi

echo ""
if [ "$PASS" = true ]; then
  echo "  [OK] Sistema listo para: $PIPELINE_NAME"
  exit 0
else
  echo "  [ERROR] Sistema NO listo para: $PIPELINE_NAME — resuelva los problemas indicados"
  exit 1
fi
```

```bash
chmod +x ~/scripts/maintenance/check-ready.sh

# Agregar alias
echo "alias check-ready='~/scripts/maintenance/check-ready.sh'" >> ~/.bash_aliases
source ~/.bash_aliases

# Probar
check-ready 20 "PDF-to-podcast"
```

---

## 26.3 Script 2 — Limpieza de Contenedores de Proyectos

```bash
# ~/scripts/maintenance/clean-ai-containers.sh
#!/bin/bash
#
# Detiene y elimina contenedores de proyectos de IA.
# Uso: clean-ai-containers.sh [--dry-run]
#

DRY_RUN=false
[ "$1" = "--dry-run" ] && DRY_RUN=true

# Patrones de contenedores de proyectos (no incluye motores base: vllm, llama, webui, openclaw)
AI_CONTAINER_PATTERNS=(
  "faster-whisper"
  "kokoro-tts"
  "kokoro"
  "piper-tts"
  "piper"
  "speaches"
  "comfyui"
  "stable-diff"
  "stable_diff"
  "vila"
  "homeassistant"
  "home-assistant"
  "llama-factory"
  "jupyterlab"
  "nanodb"
  "whisper"
)

# Construir patrón grep
GREP_PATTERN=$(IFS="|"; echo "${AI_CONTAINER_PATTERNS[*]}")

echo "── Limpieza de contenedores de proyectos ──"
[ "$DRY_RUN" = true ] && echo "   [MODO DRY-RUN — solo muestra lo que haría]"

CONTENEDORES=$(docker ps -a --format "{{.Names}}" 2>/dev/null | grep -E "$GREP_PATTERN" || true)

if [ -z "$CONTENEDORES" ]; then
  echo "  [OK] No hay contenedores de proyectos activos ni detenidos"
else
  while IFS= read -r nombre; do
    STATUS=$(docker inspect --format "{{.State.Status}}" "$nombre" 2>/dev/null)
    if [ "$DRY_RUN" = false ]; then
      echo "  Deteniendo y eliminando: $nombre ($STATUS)..."
      docker stop "$nombre" 2>/dev/null && docker rm "$nombre" 2>/dev/null || true
    else
      echo "  [dry-run] Eliminaría: $nombre ($STATUS)"
    fi
  done <<< "$CONTENEDORES"
fi

# Liberar caché del sistema
if [ "$DRY_RUN" = false ]; then
  echo ""
  echo "── Liberando caché del sistema ──"
  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
  
  echo ""
  echo "── Estado post-limpieza ──"
  free -h | awk '/^Mem:/{printf "  RAM libre: %s de %s total\n", $7, $2}'
  
  RESTANTES=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "$GREP_PATTERN" | wc -l)
  if [ "$RESTANTES" -eq 0 ]; then
    echo "  [OK] Limpieza completada"
  else
    echo "  [WARN]  Quedan $RESTANTES contenedores — requieren revisión manual"
  fi
fi
```

```bash
chmod +x ~/scripts/maintenance/clean-ai-containers.sh
echo "alias clean-ai-containers='~/scripts/maintenance/clean-ai-containers.sh'" >> ~/.bash_aliases
source ~/.bash_aliases
```

---

## 26.4 Script 3 — Cambio entre Pipelines

Cuando necesite cambiar de un pipeline activo a otro, este script limpia el estado anterior y prepara el sistema:

```bash
# ~/scripts/maintenance/switch-project.sh
#!/bin/bash
#
# Cambia de un proyecto activo a otro: limpia el estado anterior y prepara el siguiente.
# Uso: switch-project.sh <nombre_proyecto_destino> [--power-mode maxn|30w|15w]
#

PROYECTO_DESTINO="${1:-}"
POWER_MODE="${2:-30w}"

if [ -z "$PROYECTO_DESTINO" ]; then
  echo "Uso: switch-project.sh <proyecto> [--power-mode maxn|30w|15w]"
  echo "Proyectos disponibles:"
  echo "  pdf2podcast, transcription-bot, tourism-agency, sales-funnel,"
  echo "  linkedin-content, voice-assistant, rag-empresarial"
  exit 1
fi

echo "══════════════════════════════════════════════════"
echo "  CAMBIO DE PROYECTO → $PROYECTO_DESTINO"
echo "══════════════════════════════════════════════════"

# 1. Limpiar estado anterior
echo ""
echo "1/3 — Limpiando contenedores del proyecto anterior..."
~/scripts/maintenance/clean-ai-containers.sh

# 2. Esperar que la memoria se libere
echo ""
echo "2/3 — Esperando estabilización del sistema..."
sleep 5
free -h | awk '/^Mem:/{printf "  RAM disponible: %s\n", $7}'

# 3. Aplicar modo energético
echo ""
echo "3/3 — Configurando modo energético: $POWER_MODE"
case "$POWER_MODE" in
  maxn|MAXN)   pwr-maxn ;;
  30w|30W)     pwr-30w ;;
  15w|15W)     pwr-15w ;;
  *)           echo "  [WARN]  Modo no reconocido: $POWER_MODE (usando 30w)" && pwr-30w ;;
esac

echo ""
echo "  [OK] Sistema listo para proyecto: $PROYECTO_DESTINO"
echo "  [INFO] Ejecute: check-ready 20 $PROYECTO_DESTINO"
```

```bash
chmod +x ~/scripts/maintenance/switch-project.sh
echo "alias switch-project='~/scripts/maintenance/switch-project.sh'" >> ~/.bash_aliases
source ~/.bash_aliases
```

---

## 26.5 Script 4 — Limpieza de Caché Hugging Face

Los modelos descargados por contenedores se acumulan en `~/.cache/huggingface`. Este script identifica qué se puede limpiar de forma segura.

```bash
# ~/scripts/maintenance/hf-cache-clean.sh
#!/bin/bash
#
# Gestión del caché de Hugging Face.
# Uso: hf-cache-clean.sh [--list | --clean-snapshots | --full-clean]
#

HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"
MODO="${1:---list}"

echo "── Caché Hugging Face: $HF_CACHE ──"

case "$MODO" in
  --list)
    echo "Modelos en caché:"
    du -sh "$HF_CACHE"/{hub,datasets}/* 2>/dev/null \
      | sort -h -r \
      | head -20 \
      | awk '{printf "  %s  %s\n", $1, $2}'
    echo ""
    TOTAL=$(du -sh "$HF_CACHE" 2>/dev/null | cut -f1)
    echo "Total: $TOTAL"
    ;;
  
  --clean-snapshots)
    # Elimina snapshots antiguos dejando solo el más reciente de cada modelo
    echo "Limpiando snapshots antiguos (conserva el más reciente de cada modelo)..."
    find "$HF_CACHE/hub" -name "snapshots" -type d 2>/dev/null | while read snap_dir; do
      PADRE=$(dirname "$snap_dir")
      # Contar snapshots
      TOTAL_SNAPS=$(ls "$snap_dir" 2>/dev/null | wc -l)
      if [ "$TOTAL_SNAPS" -gt 1 ]; then
        echo "  $(basename $PADRE): $TOTAL_SNAPS snapshots — conservando el más reciente"
        ls -t "$snap_dir" | tail -n +2 | while read viejo; do
          rm -rf "$snap_dir/$viejo"
          echo "    Eliminado: $viejo"
        done
      fi
    done
    echo "[OK] Limpieza de snapshots completada"
    ;;
  
  --clean-model)
    # Eliminar un modelo específico
    MODELO="${2:-}"
    if [ -z "$MODELO" ]; then
      echo "Uso: hf-cache-clean.sh --clean-model <nombre_modelo>"
      echo "Ejemplo: hf-cache-clean.sh --clean-model microsoft--phi-2"
      exit 1
    fi
    DIR_MODELO="$HF_CACHE/hub/models--$MODELO"
    if [ -d "$DIR_MODELO" ]; then
      TAMANIO=$(du -sh "$DIR_MODELO" | cut -f1)
      echo "Eliminando $MODELO ($TAMANIO)..."
      rm -rf "$DIR_MODELO"
      echo "[OK] Eliminado: $MODELO"
    else
      echo "[WARN]  Modelo no encontrado en caché: $MODELO"
      echo "   Busque con: hf-cache-clean.sh --list"
    fi
    ;;
  
  --full-clean)
    TAMANIO=$(du -sh "$HF_CACHE" 2>/dev/null | cut -f1)
    echo "[WARN]  ADVERTENCIA: Esto eliminará TODO el caché ($TAMANIO)"
    echo "   Los modelos se descargarán de nuevo la próxima vez"
    read -p "   ¿Continuar? (escriba 'si' para confirmar): " CONFIRM
    if [ "$CONFIRM" = "si" ]; then
      rm -rf "$HF_CACHE"
      mkdir -p "$HF_CACHE"
      echo "[OK] Caché Hugging Face limpiado completamente"
    else
      echo "Cancelado"
    fi
    ;;
  
  *)
    echo "Opciones: --list | --clean-snapshots | --clean-model <nombre> | --full-clean"
    ;;
esac
```

```bash
chmod +x ~/scripts/maintenance/hf-cache-clean.sh
echo "alias hf-cache='~/scripts/maintenance/hf-cache-clean.sh'" >> ~/.bash_aliases
source ~/.bash_aliases

# Ver qué hay en el caché
hf-cache --list
```

---

## 26.6 Script 5 — Verificación de Salud Semanal

Ejecute este script una vez por semana para asegurarse de que el sistema está funcionando correctamente. Registra los resultados en un log histórico.

```bash
# ~/scripts/maintenance/health-check.sh
#!/bin/bash
#
# Diagnóstico completo del sistema con log histórico.
# Ejecutar semanalmente para detectar degradación de rendimiento.
#

LOG_DIR="$HOME/logs/health"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/health_$(date +%Y%m%d_%H%M%S).log"

log() {
  echo "$1" | tee -a "$LOG_FILE"
}

log "╔══════════════════════════════════════════════════════════╗"
log "║    DIAGNÓSTICO DE SALUD — JETSON AGX ORIN 64GB          ║"
log "║    $(date '+%Y-%m-%d %H:%M:%S')                                    ║"
log "╚══════════════════════════════════════════════════════════╝"

# ── Hardware ──────────────────────────────────────────────
log ""
log "═══ HARDWARE ═══"

# Temperatura
TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "%.1f", $1/1000}')
log "  Temperatura: ${TEMP}°C"
[ "$(echo "$TEMP > 70" | bc -l)" = "1" ] && log "  [WARN]  Temperatura alta — verificar ventilación"

# RAM
free -h | awk '/^Mem:/{printf "  RAM: %s usados de %s (%s libre)\n", $3, $2, $7}' | tee -a "$LOG_FILE"

# Almacenamiento
df -h / | awk 'NR==2{printf "  Disco raíz: %s usados de %s (%s libre)\n", $3, $2, $4}' | tee -a "$LOG_FILE"
df -h /data 2>/dev/null | awk 'NR==2{printf "  NVMe (/data): %s usados de %s (%s libre)\n", $3, $2, $4}' | tee -a "$LOG_FILE"

# Uptime
uptime | awk '{printf "  Uptime: %s %s %s\n", $3, $4, $5}' | tee -a "$LOG_FILE"

# ── Software ──────────────────────────────────────────────
log ""
log "═══ SOFTWARE ═══"

# Docker
DOCKER_VER=$(docker version --format "{{.Server.Version}}" 2>/dev/null || echo "no disponible")
log "  Docker: $DOCKER_VER"

# CUDA
CUDA_VER=$(nvcc --version 2>/dev/null | grep "release" | awk '{print $6}' | tr -d ',' || echo "no disponible")
log "  CUDA: $CUDA_VER"

# Ollama
OLLAMA_VER=$(ollama version 2>/dev/null || echo "no disponible")
log "  Ollama: $OLLAMA_VER"

# Python
PY_VER=$(python3.12 --version 2>/dev/null || python3 --version 2>/dev/null || echo "no disponible")
log "  Python: $PY_VER"

# ── Benchmark de rendimiento ──────────────────────────────
log ""
log "═══ BENCHMARK DE RENDIMIENTO ═══"

# Verificar que Ollama tiene un modelo disponible para test
if systemctl is-active --quiet ollama || sudo systemctl start ollama 2>/dev/null; then
  MODELOS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | head -3)
  
  if [ -n "$MODELOS" ]; then
    MODELO_TEST=$(echo "$MODELOS" | head -1)
    log "  Benchmark LLM con: $MODELO_TEST"
    
    INICIO=$(date +%s%3N)
    RESPUESTA=$(curl -s http://localhost:11434/api/generate \
      -d "{\"model\": \"$MODELO_TEST\", \"prompt\": \"What is 2+2? One word answer.\", \"stream\": false}" \
      --max-time 60 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
total_duration_ns = data.get('total_duration', 0)
eval_count = data.get('eval_count', 0)
if total_duration_ns > 0 and eval_count > 0:
    tok_per_sec = eval_count / (total_duration_ns / 1e9)
    print(f'{tok_per_sec:.1f} tok/s ({eval_count} tokens)')
else:
    print('N/A')
" 2>/dev/null || echo "timeout/error")
    
    log "  Velocidad: $RESPUESTA"
    
    sudo systemctl stop ollama 2>/dev/null
  else
    log "  [INFO] Sin modelos Ollama instalados para benchmark"
    sudo systemctl stop ollama 2>/dev/null
  fi
else
  log "  [WARN]  Ollama no disponible para benchmark"
fi

# Benchmark de disco (escritura)
log ""
log "  Benchmark NVMe (escritura secuencial):"
DISCO_BENCH=$(dd if=/dev/zero of=/tmp/bench_test bs=1M count=512 conv=fdatasync 2>&1 | grep -o '[0-9.]* [MG]B/s' | tail -1)
rm -f /tmp/bench_test
log "  Velocidad escritura: ${DISCO_BENCH:-N/A}"

# ── Servicios del sistema ─────────────────────────────────
log ""
log "═══ SERVICIOS ═══"

SERVICIOS=("ssh" "NetworkManager" "docker")
for svc in "${SERVICIOS[@]}"; do
  STATUS=$(systemctl is-active "$svc" 2>/dev/null)
  if [ "$STATUS" = "active" ]; then
    log "  [OK] $svc: activo"
  else
    log "  ○  $svc: $STATUS"
  fi
done

# ── Docker imágenes ───────────────────────────────────────
log ""
log "═══ DOCKER ═══"
IMG_TOTAL=$(docker images | tail -n +2 | wc -l)
IMG_TAMANIO=$(docker system df --format "{{.Size}}" 2>/dev/null | head -1 || echo "N/A")
log "  Total imágenes: $IMG_TOTAL"
log "  Espacio Docker: $(docker system df 2>/dev/null | grep 'Images' | awk '{print $4}')"

# ── Resumen ───────────────────────────────────────────────
log ""
log "═══ RESUMEN ═══"
log "  Log guardado en: $LOG_FILE"
log "  Próxima revisión: $(date -d '+7 days' '+%Y-%m-%d' 2>/dev/null || date -v+7d '+%Y-%m-%d' 2>/dev/null)"

log ""
log "════════════════════════════════════════════════════════"

# Mostrar historial de benchmarks previos
PREVIOS=$(ls -t "$LOG_DIR"/health_*.log 2>/dev/null | head -5)
if [ $(echo "$PREVIOS" | wc -l) -gt 1 ]; then
  echo ""
  echo "── Historial de velocidad LLM ──"
  echo "$PREVIOS" | while read log_prev; do
    FECHA=$(basename "$log_prev" | sed 's/health_//;s/_.*//')
    VEL=$(grep "Velocidad:" "$log_prev" 2>/dev/null | head -1 | awk '{print $3, $4}')
    echo "  $(echo $FECHA | sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/'): ${VEL:-N/A}"
  done
fi
```

```bash
chmod +x ~/scripts/maintenance/health-check.sh
echo "alias health-check='~/scripts/maintenance/health-check.sh'" >> ~/.bash_aliases
source ~/.bash_aliases

# Ejecutar diagnóstico
health-check
```

---

## 26.7 Script 6 — Estado General del Sistema (Rápido)

Para un vistazo rápido del sistema sin ejecutar benchmarks:

```bash
# ~/scripts/maintenance/system-status.sh
#!/bin/bash
#
# Estado del sistema en 2-3 segundos.
# Llamado por: motors-status (Capítulo 15), check-ready, etc.
#

echo "╔══════════════════════════════════════════════╗"
echo "║       ESTADO DEL SISTEMA — JETSON            ║"
echo "╚══════════════════════════════════════════════╝"

# RAM
free -h | awk '/^Mem:/{printf "  RAM:  %s / %s  (libre: %s)\n", $3, $2, $7}'

# Temperatura
TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "%.0f", $1/1000}')
[ -n "$TEMP" ] && printf "  Temp: %s°C\n" "$TEMP"

# Modo energético actual
POWER=$(cat /sys/kernel/debug/bpmp/debug/clk/emc/rate 2>/dev/null | awk '{printf "%.0f MHz", $1/1e6}' 2>/dev/null || echo "N/A")
NVPMODEL=$(nvpmodel -q 2>/dev/null | grep "NV Power Mode:" | cut -d: -f2 | xargs || echo "N/A")
echo "  Modo energético: $NVPMODEL"

echo ""
echo "── Contenedores activos ──"
CONTAINERS=$(docker ps --format "  {{.Names}}\t→ {{.Status}}" 2>/dev/null)
if [ -z "$CONTAINERS" ]; then
  echo "  (ninguno)"
else
  echo "$CONTAINERS"
fi

echo ""
echo "── Servicios de inferencia ──"
endpoints=(
  "Ollama:11434:/api/version"
  "vLLM:8000:/v1/models"
  "llama.cpp:8080:/v1/models"
  "OpenClaw:18789:/api/health"
  "Open WebUI:3000:"
  "faster-whisper:8000:/v1/models"
  "kokoro-tts:8880:/v1/voices"
)

for ep in "${endpoints[@]}"; do
  NOMBRE=$(echo "$ep" | cut -d: -f1)
  PUERTO=$(echo "$ep" | cut -d: -f2)
  PATH_CHECK=$(echo "$ep" | cut -d: -f3)
  
  if curl -sf "http://localhost:${PUERTO}${PATH_CHECK}" --max-time 2 > /dev/null 2>&1; then
    printf "  [OK] %-20s puerto %s\n" "$NOMBRE" "$PUERTO"
  fi
done

echo "════════════════════════════════════════════════"
```

```bash
chmod +x ~/scripts/maintenance/system-status.sh

# Actualizar el alias motors-status de Part 15 para incluir este script
# (o crear un alias separado)
echo "alias sys-status='~/scripts/maintenance/system-status.sh'" >> ~/.bash_aliases
source ~/.bash_aliases
```

---

## 26.8 Aliases de Mantenimiento — Resumen Completo

Agregue estos aliases al final de `~/.bash_aliases` para tener todo el mantenimiento accesible:

```bash
# Agregar al final de ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ═══ MANTENIMIENTO ═══

# Verificación pre-proyecto
alias check-ready='~/scripts/maintenance/check-ready.sh'

# Limpieza de contenedores de proyectos
alias clean-ai-containers='~/scripts/maintenance/clean-ai-containers.sh'

# Cambio entre proyectos de IA
alias switch-project='~/scripts/maintenance/switch-project.sh'

# Caché Hugging Face
alias hf-cache='~/scripts/maintenance/hf-cache-clean.sh'

# Diagnóstico semanal completo
alias health-check='~/scripts/maintenance/health-check.sh'

# Estado rápido del sistema
alias sys-status='~/scripts/maintenance/system-status.sh'

# Limpieza rápida de todos los contenedores de proyectos
alias jetson-clean='clean-ai-containers && sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null && free -h | awk "/^Mem:/{printf \"RAM libre: %s de %s\\n\", \$7, \$2}"'
EOF

source ~/.bash_aliases
```

---

## 26.9 Logs y Rotación

Los logs del sistema de mantenimiento se acumulan en `~/logs/`. Configure la rotación para que no llenen el disco:

```bash
# Configurar logrotate para los logs del Jetson
sudo tee /etc/logrotate.d/jetson-maintenance << 'EOF'
/home/jetson/logs/health/*.log {
    weekly
    rotate 12
    compress
    missingok
    notifempty
    create 644 jetson jetson
}
EOF

# Verificar la configuración
sudo logrotate -d /etc/logrotate.d/jetson-maintenance
```

---

## 26.10 Programar el Health Check Semanal

```bash
# Programar health-check los lunes a las 7:00 AM
# (solo si el sistema está encendido — cron se ejecuta en horario)
(crontab -l 2>/dev/null; echo "0 7 * * 1 ~/scripts/maintenance/health-check.sh >> ~/logs/health/cron_health.log 2>&1") | crontab -

# Verificar
crontab -l | grep health
```

```
# Salida esperada
0 7 * * 1 ~/scripts/maintenance/health-check.sh >> ~/logs/health/cron_health.log 2>&1
```

---

## 26.11 Guía de Referencia Rápida de Mantenimiento

> **[INFOGRAFÍA — VERSIÓN IMPRESA]** *Guía de Referencia Rápida de Mantenimiento* — Se recomienda convertir este esquema en una infografía de alta resolución para la versión KDP. Requisitos: texto mínimo 10 pt, paleta teal `#0F3D3D` / accent `#1D9CB8`, formato monocromático disponible para impresión B&W.


```
╔═══════════════════════════════════════════════════════════════════╗
║           REFERENCIA RÁPIDA — MANTENIMIENTO JETSON               ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ANTES de cada proyecto:                                          ║
║    check-ready 20 <nombre>                                        ║
║                                                                   ║
║  DESPUÉS de cada proyecto:                                        ║
║    clean-ai-containers && pwr-15w                                 ║
║                                                                   ║
║  CAMBIAR entre proyectos:                                         ║
║    switch-project <destino> [--power-mode 30w]                   ║
║                                                                   ║
║  LIMPIAR caché HuggingFace:                                       ║
║    hf-cache --list                        # Ver qué hay          ║
║    hf-cache --clean-snapshots             # Limpiar snapshots    ║
║    hf-cache --clean-model microsoft--phi-2  # Un modelo          ║
║                                                                   ║
║  ESTADO del sistema (rápido):                                     ║
║    sys-status                                                     ║
║                                                                   ║
║  DIAGNÓSTICO semanal completo:                                    ║
║    health-check                                                   ║
║                                                                   ║
║  LIMPIEZA profunda de contenedores de proyectos:                  ║
║    jetson-clean                                                   ║
║                                                                   ║
║  MODOS DE ENERGÍA:                                               ║
║    pwr-maxn    → 50W, máximo rendimiento (inferencia LLM 30B+)  ║
║    pwr-30w     → 30W, balance (inferencia LLM <9B, STT, TTS)    ║
║    pwr-15w     → 15W, bajo consumo (limpieza, espera)            ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 26.12 Verificación Final del Capítulo

```bash
# Verificación completa de los scripts de mantenimiento
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     VERIFICACIÓN CAPÍTULO 26 — SCRIPTS DE MANTENIMIENTO ║"
echo "╚══════════════════════════════════════════════════════════╝"

echo ""
echo "── Scripts instalados ──"
SCRIPTS=(
  "check-ready.sh"
  "clean-ai-containers.sh"
  "switch-project.sh"
  "hf-cache-clean.sh"
  "health-check.sh"
  "system-status.sh"
)
for s in "${SCRIPTS[@]}"; do
  if [ -x ~/scripts/maintenance/$s ]; then
    echo "  [OK] $s (ejecutable)"
  elif [ -f ~/scripts/maintenance/$s ]; then
    echo "  [WARN]  $s existe pero no tiene permisos de ejecución — chmod +x"
  else
    echo "  ○  $s no encontrado"
  fi
done

echo ""
echo "── Aliases configurados ──"
for alias_name in check-ready clean-ai-containers switch-project hf-cache health-check sys-status jetson-clean; do
  type "$alias_name" 2>/dev/null | grep -q "alias" \
    && echo "  [OK] $alias_name" \
    || echo "  ○  $alias_name → agregar a ~/.bash_aliases (ver §26.8)"
done

echo ""
echo "── Cron semanal ──"
crontab -l 2>/dev/null | grep -q "health-check" \
  && echo "  [OK] Health check semanal programado" \
  || echo "  ○  Sin cron programado (ver §26.10)"

echo ""
echo "── Directorios de logs ──"
[ -d ~/logs/health ] \
  && echo "  [OK] ~/logs/health/ existe" \
  || echo "  ○  Crear: mkdir -p ~/logs/health"

echo ""
echo "════════════════════════════════════════════════════════"
```

> **Próximo paso:** El Capítulo 20 (Despliegue en Producción) cubre el hardening del sistema, UFW, watchdogs de servicio y las mejores prácticas para mantener el Jetson operativo de forma continua.
