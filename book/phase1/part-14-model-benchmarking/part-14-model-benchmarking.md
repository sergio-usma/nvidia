# Capítulo 14 — Testing y Benchmarking de los 10 Mejores Modelos para Jetson AGX Orin 64GB

## Introducción

Una de las mayores ventajas del Jetson AGX Orin 64GB es la posibilidad de ejecutar localmente una variedad extraordinaria de modelos de lenguaje sin costo de API y con latencia mínima. Sin embargo, la selección del modelo correcto para cada caso de uso requiere conocer sus características: consumo de RAM, velocidad en tokens por segundo, capacidades multimodales, soporte de tool calling y tiempo de arranque.

Este capítulo presenta los 10 modelos más importantes validados para JetPack 7.2, organizados de mayor a menor complejidad. Para cada uno se incluyen las especificaciones técnicas, los comandos exactos de instalación y arranque, ejemplos de pruebas y las métricas de rendimiento medidas en el Jetson AGX Orin 64GB.

> **IMPORTANTE:** Solo un modelo grande puede estar activo a la vez en la memoria unificada del Jetson. Antes de iniciar cualquier modelo, ejecute siempre la secuencia de limpieza descrita en la Sección 14.1. El script `switch-model.sh` (Capítulo 12) automatiza esta transición.

---

## 14.1 Configuración Pre-Vuelo — Funciones de Utilidad

Antes de trabajar con cualquier modelo, configure estas funciones de utilidad que se usarán a lo largo del capítulo.

> **IMPORTANTE — Por qué el script anterior fallaba:** El primer problema recurrente al limpiar el Jetson es que los contenedores tienen nombres dinámicos (`qwen35-35b`, `vllm`, `gemma4-26b-vllm`, etc.), no siempre `vllm-openclaw` o `llama-openclaw`. Un script que busca nombres fijos dirá "sin contenedores" aunque haya uno consumiendo 36 GB. La versión correcta detecta contenedores por palabras clave en el nombre.

```bash
# Crear el script jetson-clean.sh inteligente
mkdir -p ~/scripts

cat > ~/scripts/jetson-clean.sh << 'EOF'
#!/bin/bash

mostrar_diagnostico() {
    echo "  [1] Memoria del Sistema:"
    free -h | awk 'NR==1 || NR==2' | sed 's/^/      /'

    echo "  [2] Contenedores Activos:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" | sed 's/^/      /'

    echo "  [3] Consumo de RAM por Contenedor:"
    docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" | sed 's/^/      /'

    echo "  [4] Modelos Ollama en GPU:"
    if systemctl is-active --quiet ollama; then
        ollama ps 2>/dev/null | sed 's/^/      /'
    else
        echo "      Ollama → offline (servicio inactivo)"
    fi

    echo "  [5] Endpoints de Inferencia Activos:"
    curl -s http://localhost:8000/v1/models 2>/dev/null | \
      python3 -c "import sys,json; [print('      vLLM:8000 →', m['id']) for m in json.load(sys.stdin)['data']]" \
      2>/dev/null || echo "      vLLM:8000 → offline"
    curl -s http://localhost:8080/v1/models 2>/dev/null | \
      python3 -c "import sys,json; [print('      llama.cpp:8080 →', m['id']) for m in json.load(sys.stdin)['data']]" \
      2>/dev/null || echo "      llama.cpp:8080 → offline"
}

echo "╔══════════════════════════════════════════════════════╗"
echo "║           ESTADO INICIAL (DIAGNÓSTICO)               ║"
echo "╚══════════════════════════════════════════════════════╝"
mostrar_diagnostico

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                 EJECUTANDO LIMPIEZA                  ║"
echo "╚══════════════════════════════════════════════════════╝"

# 1. Detectar contenedores por palabras clave (no por nombre fijo)
CONTAINERS=$(docker ps --format '{{.Names}}' \
  | grep -E "vllm|llama|qwen|gemma|nemotron|cosmos|gpt|openclaw|open-webui")

if [ -n "$CONTAINERS" ]; then
    echo "→ Eliminando contenedores detectados (docker rm -f)..."
    echo "$CONTAINERS" | sed 's/^/    - /'
    docker rm -f $CONTAINERS >/dev/null 2>&1
    echo "  OK Contenedores eliminados."
else
    echo "→ No se detectaron contenedores de inferencia activos."
fi

# 2. Matar procesos huérfanos en el host
echo "→ Limpiando procesos huérfanos de vLLM/Python en el host..."
sudo pkill -f vllm 2>/dev/null || true
sudo pkill -f "python.*qwen\|python.*gemma\|python.*llama" 2>/dev/null || true
echo "  OK Procesos mitigados."

# 3. Descargar modelos Ollama y detener el servicio
if systemctl is-active --quiet ollama; then
    echo "→ Descargando modelos Ollama de GPU..."
    for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
        curl -s http://localhost:11434/api/generate \
          -d "{\"model\":\"$m\",\"keep_alive\":0}" > /dev/null
        echo "    OK $m descargado"
    done
    echo "→ Deteniendo servicio Ollama..."
    sudo systemctl stop ollama 2>/dev/null && echo "  OK Ollama detenido"
else
    echo "→ Servicio Ollama ya estaba inactivo."
fi

# 4. Liberar caché del kernel (page cache + swap)
echo "→ Liberando page cache y memoria unificada..."
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sudo swapoff -a && sudo swapon -a 2>/dev/null || true
echo "  OK Caché y swap liberados."

echo "→ Esperando 5 segundos para estabilización..."
sleep 5

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              ESTADO FINAL (REPORTE)                  ║"
echo "╚══════════════════════════════════════════════════════╝"
mostrar_diagnostico
echo "══════════════════════════════════════════════════════"
EOF

chmod +x ~/scripts/jetson-clean.sh
echo 'alias jetson-clean="~/scripts/jetson-clean.sh"' >> ~/.bashrc
source ~/.bashrc
echo "[OK] jetson-clean instalado. Prueba: jetson-clean"
```

```bash
# Agregar funciones de energía y check-ready al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── Alias de modos de energía ─────────────────────────────────────
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MAXN: 50W activo"'
alias pwr-30w='sudo nvpmodel -m 2 && sudo jetson_clocks && echo "30W activo"'
alias pwr-15w='sudo nvpmodel -m 3 && sudo jetson_clocks --restore && echo "15W activo"'

# ── Verificar estado antes de cargar un modelo ───────────────────
check-ready() {
  echo "── Procesos usando GPU ──"
  sudo fuser -v /dev/nvidia* 2>/dev/null | head -10 || echo "  (sin procesos en GPU)"
  echo ""
  echo "── Memoria libre ──"
  free -h | grep Mem
  FREE=$(free -g | awk "/^Mem:/{print \$7}")
  [ "$FREE" -lt 48 ] \
    && echo "[WARN] Solo ${FREE}GB libres — ejecute 'jetson-clean' primero" \
    || echo "[OK] ${FREE}GB disponibles — listo para cargar modelo"
  echo ""
  echo "── Contenedores activos ──"
  docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null || echo "  Ninguno"
  echo ""
  echo "── Modo de energía actual ──"
  sudo nvpmodel --query 2>/dev/null | grep "Power Model" | head -1
}
EOF

source ~/.bashrc
```

```bash
# Crear directorios para resultados de benchmarks y logs
mkdir -p ~/jetson-ai-data/benchmarks
mkdir -p ~/jetson-ai-data/logs/models
```

### 14.1.1 Script de tracking de rendimiento

Guarde este script para registrar automáticamente tokens/s, RAM usada y tiempo hasta primera respuesta (TTFT) en cada prueba:

```bash
cat > ~/scripts/bench-model.sh << 'EOF'
#!/usr/bin/env bash
# bench-model.sh -- Registra metricas de rendimiento de un modelo activo
# Uso: bench-model.sh [puerto] [model_id] [prompt] [iteraciones]
set -euo pipefail

PORT=${1:-8000}
MODEL=${2:-"auto"}
PROMPT=${3:-"Explica en 100 palabras el concepto de inteligencia artificial."}
ITERS=${4:-3}
LOG_DIR="$HOME/jetson-ai-data/benchmarks"
TIMESTAMP=$(date +%Y%m%d_%H%M)

# Auto-detectar model_id si no se especifica
if [ "$MODEL" = "auto" ]; then
  MODEL=$(curl -s http://localhost:${PORT}/v1/models \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null \
    || echo "unknown")
fi

LOG_FILE="$LOG_DIR/${TIMESTAMP}_${MODEL//\//_}_p${PORT}.csv"
echo "timestamp,model,port,iter,ttft_s,tokens,tok_s,ram_used_gb,ram_free_gb" > "$LOG_FILE"

echo "=== Benchmark: $MODEL (puerto $PORT) — $ITERS iteraciones ==="
echo "Log: $LOG_FILE"
echo ""

for i in $(seq 1 $ITERS); do
  RAM_BEFORE=$(free -g | awk '/^Mem:/{print $3}')
  T_START=$(date +%s%N)

  RESPONSE=$(curl -s http://localhost:${PORT}/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"$MODEL\",
      \"messages\": [{\"role\": \"user\", \"content\": \"$PROMPT\"}],
      \"max_tokens\": 150,
      \"stream\": false
    }")

  T_END=$(date +%s%N)
  ELAPSED=$(echo "scale=2; ($T_END - $T_START) / 1000000000" | bc)

  TOKENS=$(echo "$RESPONSE" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('completion_tokens',0))" 2>/dev/null || echo "0")
  TOK_S=$(echo "scale=1; $TOKENS / $ELAPSED" | bc 2>/dev/null || echo "?")
  RAM_AFTER=$(free -g | awk '/^Mem:/{print $3}')
  RAM_FREE=$(free -g | awk '/^Mem:/{print $7}')

  echo "  Iter $i: ${ELAPSED}s | ${TOKENS} tokens | ${TOK_S} tok/s | RAM: ${RAM_AFTER}GB usado, ${RAM_FREE}GB libre"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ),$MODEL,$PORT,$i,$ELAPSED,$TOKENS,$TOK_S,$RAM_AFTER,$RAM_FREE" >> "$LOG_FILE"
  sleep 2
done

echo ""
echo "=== Resumen guardado en: $LOG_FILE ==="
EOF

chmod +x ~/scripts/bench-model.sh
echo "alias bench-model='~/scripts/bench-model.sh'" >> ~/.bash_aliases
source ~/.bash_aliases
```

```bash
# Uso del script de benchmarking:
# bench-model.sh [puerto] [model_id] [prompt] [iteraciones]

# Benchmarking rapido (defaults: puerto 8000, auto-detect model, 3 iters)
bench-model

# Benchmarking completo con prompt especifico:
bench-model 8000 "google/gemma-3-4b-it" "Escribe una funcion Python que ordene una lista" 5

# Ver resultados:
ls ~/jetson-ai-data/benchmarks/
cat ~/jetson-ai-data/benchmarks/*.csv | column -t -s,
```

### 14.1.2 Prueba via Open WebUI

Además de las pruebas via `curl`, cada modelo puede probarse desde la interfaz web. Esto es especialmente útil para modelos multimodales (imagen, audio):

```bash
# Para probar via Open WebUI:
# 1. Iniciar el motor de inferencia del modelo (ver seccion especifica)
# 2. Iniciar Open WebUI apuntando al motor activo:
start-webui
# 3. Abrir en Windows: http://192.168.1.100:3000 (o con SSL: https://192.168.1.100:3000)
# 4. Seleccionar el modelo en el dropdown superior
# 5. Para modelos de imagen: arrastrar la imagen al chat
# 6. Para modelos de audio (Nemotron Omni): usar el icono de microfono (requiere HTTPS)
```

> **CONSEJO:** Al probar desde Open WebUI, el indicador de tokens/s aparece debajo de cada respuesta. Para capturar estas metricas en un CSV, use el script `bench-model.sh` en paralelo (en otra terminal SSH).

---

## 14.2 Resumen Comparativo de los 10 Modelos

La siguiente tabla resume las características clave de cada modelo. Úsela para seleccionar rápidamente el modelo más apropiado para su caso de uso:

| # | Modelo | Parámetros | RAM | Motor | Puerto | tok/s | Modalidades | Licencia |
|---|--------|------------|-----|-------|--------|-------|-------------|----------|
| 1 | Qwen3.5 35B-A3B (MoE) | 35B/3B act. | ~26GB | vLLM | 8000 | ~32 | Texto | Apache 2.0 |
| 2 | Nemotron 3 Nano Omni | 30B/3B act. | ~24GB | llama.cpp | 8080 | ~39 | T+I+A+V | NVIDIA OML |
| 3 | Qwen3-VL-4B | 4B | ~6GB | vLLM | 8000 | ~58 | Texto+Imagen | Apache 2.0 |
| 4 | Cosmos Reason 2 2B | 2B | ~4GB | llama.cpp | 8080 | ~59 | T+I+Video | NVIDIA OML |
| 5 | Gemma 4 26B-A4B (MoE) | 25.8B/3.8B | ~24GB | vLLM/llama.cpp | 8000/8080 | ~32 | Texto+Imagen | Apache 2.0 |
| 6 | Qwen3.5 9B | 9B | ~12GB | vLLM | 8000 | ~55 | Texto | Apache 2.0 |
| 7 | Nemotron3 Nano 4B | 4B | ~4GB | llama.cpp | 8080 | ~43 | Texto | NVIDIA OML |
| 8 | Qwen3.5 4B | 4B | ~5GB | vLLM | 8000 | ~50 | Texto | Apache 2.0 |
| 9 | Gemma 4 E4B | ~5B | ~10GB (vLLM) / ~3GB (GGUF) | vLLM/llama.cpp | 8000/8080 | ~50 | T+I+Audio | Apache 2.0 |
| 10 | GPT OSS 20B | 21B/3.6B | ~18GB | vLLM | 8000 | ~42 | Texto | Apache 2.0 |

**Guía de selección rápida:**

| Necesito... | Modelo recomendado | RAM requerida |
|------------|-------------------|---------------|
| Máxima calidad con razonamiento | Qwen3.5 35B-A3B (Mod. 1) | ~26GB |
| Audio/Video multimodal | Nemotron Omni (Mod. 2) | ~24GB |
| Análisis de imágenes ligero | Qwen3-VL-4B (Mod. 3) | ~6GB |
| Razonamiento espacial / detección | Cosmos Reason 2 2B (Mod. 4) | ~4GB |
| Tool calling + imagen + contexto largo | Gemma 4 26B-A4B (Mod. 5) | ~24GB |
| Mejor velocidad entre modelos medianos | Qwen3.5 9B (Mod. 6) | ~12GB |
| Mínima RAM, texto puro | Nemotron3 Nano 4B (Mod. 7) | ~4GB |
| Balance velocidad/calidad/RAM | Qwen3.5 4B (Mod. 8) | ~5GB |
| Multimodal compacto + tool calling | Gemma 4 E4B (Mod. 9) | ~3GB GGUF |
| Compatibilidad drop-in con API OpenAI | GPT OSS 20B (Mod. 10) | ~18GB |

**Prerrequisito: Descargar las imágenes Docker una sola vez:**

```bash
# En una sesión tmux para evitar interrupciones
# (tarda 15-30 minutos dependiendo de la velocidad de internet)
tmux attach -t main 2>/dev/null || tmux new-session -s main

# Imagen vLLM principal (para 6 de los 10 modelos)
docker pull ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin

# Imagen vLLM especial para modelos Gemma (gemma4 parser incluido)
docker pull ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin

# Imagen llama.cpp (para modelos GGUF y multimodales)
docker pull ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin

# Verificar las 3 imágenes
docker images | grep -E "vllm|llama_cpp"
```

---

## 14.3 Modelo 1 — Qwen3.5 35B-A3B (Máxima Calidad)

El Qwen3.5 35B-A3B es un modelo de Mezcla de Expertos (MoE) que activa solo 3B de sus 35B parámetros por inferencia, lo que le permite combinar calidad de un modelo grande con eficiencia computacional de uno pequeño. Es el modelo de mayor calidad razonada disponible para el Jetson AGX Orin 64GB.

**Especificaciones:**

| Atributo | Valor |
|----------|-------|
| Parámetros | 35B total / 3B activos por forward pass |
| Modalidades | Texto únicamente |
| Contexto máximo | 256K tokens |
| Precisión | W4A16 (cuantización AWQ) |
| RAM estimada | ~26GB |
| Motor | vLLM |
| Puerto | 8000 |
| Velocidad | ~30-35 tok/s |
| Licencia | Apache 2.0 |

**Fortalezas:** Razonamiento complejo, tool calling avanzado, generación de código, soporte de más de 100 idiomas, cadena de pensamiento activable.

```bash
# Pre-vuelo
jetson-clean
check-ready      # verificar >48GB libres
pwr-maxn         # modo MAXN necesario para 35B

# Diagnóstico: verificar que no quedan procesos usando la GPU
sudo fuser -v /dev/nvidia* 2>/dev/null
# Si aparece algún PID, terminarlo antes de continuar:
# sudo kill -9 <PID>

# Iniciar Qwen3.5 35B-A3B
# gpu-memory-utilization 0.70 ≈ 44.8 GB — seguro con OS base ~12-14 GB
# NOTA: --reasoning-parser qwen3 OMITIDO — causa Content:None en la respuesta
#   (las respuestas van al campo <think>, no a content; ver Sección 14.X errores comunes)
#   Para activar razonamiento: usar enable_thinking:true en cada petición (ver test abajo)
docker run --runtime nvidia -d \
  --name qwen35-35b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.70 \
      --enable-prefix-caching \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --served-model-name qwen35 \
      --max-model-len 8192 \
      --host 0.0.0.0 \
      --port 8000"

# Esperar a que arranque (~10 min la primera vez — descarga el modelo)
echo -n "Esperando Qwen3.5 35B-A3B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " [OK]"
curl -s http://localhost:8000/v1/models \
  | python3 -c "import sys,json; print('Activo:', json.load(sys.stdin)['data'][0]['id'])"
```

```bash
# Verificar nombre del modelo activo
curl -s http://localhost:8000/v1/models | python3 -c \
  "import sys,json; [print('Modelo:', m['id']) for m in json.load(sys.stdin)['data']]"
# Salida esperada: Modelo: qwen35

# Test de respuesta directa (sin razonamiento interno visible)
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35",
    "messages": [{"role": "user", "content": "Explica la diferencia entre RAM y VRAM en una oración."}],
    "max_tokens": 200
  }' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Test de razonamiento con cadena de pensamiento (activado por petición, no por servidor)
# NOTA: content NO será None porque no usamos --reasoning-parser en el servidor
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35",
    "messages": [{"role": "user", "content": "¿Cuántas letras r hay en la palabra ferrocarril? Razona paso a paso."}],
    "extra_body": {"chat_template_kwargs": {"enable_thinking": true}},
    "max_tokens": 400
  }' | python3 -c \
  "import sys,json; r=json.load(sys.stdin)['choices'][0]['message']; print('Razonamiento:', r.get('reasoning_content','N/A')[:100], '...'); print('Respuesta:', r['content'])"

# Test de tool calling
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35",
    "messages": [{"role": "user", "content": "¿Cuál es el clima actual en Bogotá?"}],
    "tools": [{"type": "function", "function": {
      "name": "get_weather",
      "description": "Get current weather for a city",
      "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
    }}],
    "tool_choice": "auto",
    "max_tokens": 200
  }' | python3 -c \
  "import sys,json; r=json.load(sys.stdin)['choices'][0]; \
   tc=r['message'].get('tool_calls'); \
   print('Tool call:', tc[0]['function'] if tc else 'Ninguno')"
```

```bash
# Limpieza
docker stop qwen35-35b && docker rm qwen35-35b
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

### Recuperación ante OOM (Out of Memory)

Si el contenedor termina inesperadamente con el error `RuntimeError: Engine core initialization failed` o simplemente no responde, significa que la GPU quedó sin memoria virtual disponible:

```
CUDA error: out of memory (torch.OutOfMemoryError)
RuntimeError: Engine core initialization failed
```

**Causa más común:** otro proceso de Python o un contenedor fantasma ya ocupa parte de la memoria. La GPU reporta memoria libre pero la tiene fragmentada o reservada.

**Secuencia de recuperación nuclear — ejecute en orden:**

```bash
# Paso 1: Verificar qué procesos usan la GPU
sudo fuser -v /dev/nvidia* 2>/dev/null
# Si aparece output con PIDs, continúe con los pasos siguientes.
# Si no aparece nada, el problema puede ser el swap o el page cache.

# Paso 2: Forzar detención del contenedor (si aún está en estado zombie)
docker stop qwen35-35b 2>/dev/null
docker rm -f qwen35-35b 2>/dev/null

# Paso 3: Matar procesos huérfanos en el host (no dentro del contenedor)
sudo pkill -9 -f vllm 2>/dev/null || true
sudo pkill -9 -f "python.*qwen\|python.*vllm" 2>/dev/null || true

# Esperar 5 segundos para que el kernel libere recursos
sleep 5

# Paso 4: Limpiar page cache y ciclar el swap
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sudo swapoff -a && sudo swapon -a

# Paso 5: Verificar que la GPU quedó libre
sudo fuser -v /dev/nvidia* 2>/dev/null
# Salida esperada: ningún output (sin procesos activos)

# Paso 6: Verificar memoria disponible antes de reintentar
free -h | grep Mem
# Necesita mínimo 38 GB libres para gpu-memory-utilization 0.65
```

**Reintentar con `gpu-memory-utilization` reducida:**

```bash
# Si <48 GB libres: usar 0.65 (en lugar de 0.70)
# 0.65 × 64 GB = 41.6 GB asignados a vLLM; deja ~22 GB para OS + buffer
pwr-maxn

docker run --runtime nvidia -d \
  --name qwen35-35b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.65 \
      --enable-prefix-caching \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --served-model-name qwen35 \
      --max-model-len 8192 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Segundo intento (gpu-mem 0.65)"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " [OK]"
```

> **CONSEJO:** Si el OOM persiste incluso con `0.65`, ejecute `jetson-clean` completo, reinicie el servicio Docker (`sudo systemctl restart docker`) y vuelva a intentar. En casos extremos, `sudo reboot` es la recuperación más rápida.

---

## 14.4 Modelo 2 — Nemotron 3 Nano Omni (Multimodal: Texto + Imagen + Audio + Video)

El Nemotron 3 Nano Omni es el único modelo en el top 10 que soporta nativamente las cuatro modalidades: texto, imagen, audio y video. Su arquitectura MoE (30B total, 3B activos) permite ejecutarlo en el Jetson con ~24GB de RAM.

**Especificaciones:**

| Atributo | Valor |
|----------|-------|
| Parámetros | 30B total / 3B activos (MoE) |
| Modalidades | Texto + Imagen + Audio + Video |
| Contexto máximo | 256K tokens |
| Precisión | GGUF Q4_K_M |
| RAM estimada | ~24GB |
| Motor | llama.cpp |
| Puerto | 8080 |
| Velocidad | ~39 tok/s |
| Licencia | NVIDIA Open Model License |

**Fortalezas:** Transcripción de audio, análisis de video fotograma por fotograma, comprensión visual avanzada, razonamiento multimodal nativo.

```bash
# Pre-vuelo
jetson-clean
check-ready
pwr-maxn

# Iniciar Nemotron Omni (descarga el GGUF desde HuggingFace automáticamente)
docker run --runtime nvidia -d \
  --name nemotron-omni \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
    --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
    --ctx-size 8192 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias nemotron-omni \
    --host 0.0.0.0

# Esperar inicio (~2-3 minutos)
echo -n "Esperando Nemotron Omni"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " [OK]"
```

```bash
# Test de análisis de imagen via URL pública
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nemotron-omni",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Cartagena_de_Indias.jpg/1200px-Cartagena_de_Indias.jpg"}},
        {"type": "text", "text": "Describe esta imagen en detalle y menciona qué actividades turísticas son posibles en este lugar."}
      ]
    }],
    "max_tokens": 400
  }' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Test con imagen local en base64
python3 << 'PYTEST'
import base64
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")

def analyze_image(image_path: str, prompt: str) -> str:
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    ext = image_path.split(".")[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")
    resp = client.chat.completions.create(
        model="nemotron-omni",
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            {"type": "text", "text": prompt}
        ]}],
        extra_body={"chat_template_kwargs": {"enable_thinking": True}},
        max_tokens=1000
    )
    return resp.choices[0].message.content

# Adaptar la ruta a una imagen real del sistema
# print(analyze_image("/home/jetson/foto.jpg", "Describe la escena y detecta posibles anomalías."))
print("Función de análisis de imagen local lista. Descomenta la última línea para usar.")
PYTEST
```

```bash
# Limpieza
docker stop nemotron-omni && docker rm nemotron-omni
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

---

## 14.5 Modelo 3 — Qwen3-VL-4B (Visión Eficiente, Solo 6GB RAM)

El Qwen3-VL-4B es un modelo de visión-lenguaje de 4B parámetros cuantizado a AWQ 4-bit. Con apenas ~6GB de RAM, es el modelo de visión más eficiente del top 10 y permite mantener 55GB libres para otras tareas.

**Especificaciones:**

| Atributo | Valor |
|----------|-------|
| Parámetros | 4B |
| Modalidades | Texto + Imagen |
| Contexto máximo | 256K tokens |
| Precisión | AWQ W4A16 |
| RAM estimada | ~6GB |
| Motor | vLLM |
| Puerto | 8000 |
| Velocidad | ~58 tok/s |
| Licencia | Apache 2.0 |

**Fortalezas:** OCR en 32 idiomas, automatización de interfaces gráficas (GUI agent), extracción de código desde capturas de pantalla, grounding 2D/3D, análisis de documentos.

```bash
# Pre-vuelo
jetson-clean
check-ready
pwr-30w   # 4B eficiente, no necesita MAXN

docker run --runtime nvidia -d \
  --name qwen3-vl-4b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit \
      --gpu-memory-utilization 0.30 \
      --max-model-len 16384 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Qwen3-VL-4B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " [OK] (~6GB usados, 55GB libres)"
```

```bash
# Test: OCR de imagen con texto
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Free_WiFi_hotspot_sign.jpg/800px-Free_WiFi_hotspot_sign.jpg"}},
        {"type": "text", "text": "Extrae todo el texto visible en esta imagen."}
      ]
    }],
    "max_tokens": 200
  }' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

```bash
# Limpieza
docker stop qwen3-vl-4b && docker rm qwen3-vl-4b
```

---

## 14.6 Modelo 4 — Cosmos Reason 2 2B (Razonamiento Espacial, Mínima RAM)

Cosmos Reason 2 es un modelo especializado de NVIDIA para razonamiento espacial, detección de anomalías y análisis de escenas físicas. Con solo 2B parámetros usa ~4GB de RAM y arranca en menos de 1 minuto.

**Especificaciones:**

| Atributo | Valor |
|----------|-------|
| Parámetros | 2B |
| Modalidades | Texto + Imagen + Video |
| Precisión | Q8_0 GGUF (llama.cpp) / FP8 (vLLM + NGC) |
| RAM estimada | ~4GB |
| Motor | llama.cpp (recomendado) / vLLM (requiere NGC CLI) |
| Puerto | 8080 (llama.cpp) / 8010 (vLLM) |
| Velocidad | ~59 tok/s |
| Licencia | NVIDIA Open Model License |

> **NOTA:** El path llama.cpp no requiere cuenta NGC y es mucho más sencillo. El path vLLM (FP8, mayor precisión) requiere instalar NGC CLI y tener cuenta en ngc.nvidia.com.

```bash
# Opción A — llama.cpp (recomendada)
jetson-clean
check-ready
pwr-30w

docker run --runtime nvidia -d \
  --name cosmos-reason2 \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    -hf Kbenkhaled/Cosmos-Reason2-2B-GGUF:Q8_0 \
    -c 8192 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias cosmos-reason2 \
    --host 0.0.0.0

echo -n "Esperando Cosmos Reason 2 2B"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 10
done
echo " [OK] (~4GB, Q8_0 GGUF)"
```

```bash
# Test: Razonamiento espacial con imagen
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cosmos-reason2",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Single_passenger_train_bogota.jpg/1200px-Single_passenger_train_bogota.jpg"}},
        {"type": "text", "text": "¿Hay alguna anomalía o elemento inusual en esta escena? Describe el contexto espacial con detalle."}
      ]
    }],
    "max_tokens": 400
  }' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Prerrequisito para Opción B: Instalar NGC CLI

Para descargar modelos desde el registro NGC de NVIDIA necesita la herramienta `ngc`. La causa más común de error es instalarla incorrectamente: si extrae solo el binario `ngc` del directorio `ngc-cli` y lo mueve a `/usr/local/bin/`, la herramienta queda rota porque PyInstaller (el compilador que empaqueta `ngc`) necesita encontrar todos sus archivos auxiliares en el mismo directorio que el ejecutable. Lo mismo ocurre si crea un enlace simbólico en lugar de mover el directorio completo.

**Error típico al hacer la instalación incorrecta:**

```
-bash: /usr/local/bin/ngc: No such file or directory
```

**Procedimiento correcto:**

```bash
# Limpiar instalación rota (si existe)
sudo rm -f /usr/local/bin/ngc
sudo rm -rf /usr/local/share/ngc-cli

# Descargar NGC CLI para arm64
cd ~/Downloads
wget -q --show-progress \
  "https://api.ngc.nvidia.com/v2/resources/nvidia/ngc-apps/ngc_cli/versions/3.41.4/files/ngccli_arm64.zip" \
  -O ngccli_arm64.zip

# Re-extraer el directorio completo (NO mover solo el binario)
unzip -o ngccli_arm64.zip

# Mover el directorio COMPLETO a /opt (estándar para software manual en Linux)
sudo mv ngc-cli /opt/ngc-cli
sudo chmod +x /opt/ngc-cli/ngc

# Agregar /opt/ngc-cli al PATH — NO crear symlink (PyInstaller falla con symlinks)
echo 'export PATH="/opt/ngc-cli:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verificar
ngc --version
```

```
# Salida esperada
NGC CLI 3.41.4
```

```bash
# Configurar con su cuenta NGC
# 1. Cree cuenta gratuita en ngc.nvidia.com
# 2. Genere su API key en ngc.nvidia.com/setup/api-key
ngc config set
# Ingrese cuando se le solicite:
#   API key: (la que generó)
#   org: nvidia
#   team: (dejar en blanco o nim)
#   format: json

# Verificar acceso — use | less, NO | head -5
# El error "[Errno 32] Broken pipe" con | head no es un fallo:
# head cierra el pipe al recibir N líneas y Python reporta el corte.
ngc registry model list | less
```

> **NOTA: el error "Broken pipe" con | head no es un fallo.** Si al ejecutar `ngc registry model list | head -5` ve `[Errno 32] Broken pipe`, NGC funcionó correctamente. `head` cierra la tubería al recibir 5 líneas; Python detecta ese cierre y lo reporta como error de escritura, pero la herramienta funciona. Use `ngc registry model list | grep -i cosmos` para filtrar sin truncar.

---

```bash
# Opción B — vLLM con FP8 via NGC (mayor precisión) [REQUIERE VERIFICACIÓN]
# Paso 1: Descargar modelo FP8 desde NGC (requiere ngc config set primero)
ngc registry model download-version \
  "nim/nvidia/cosmos-reason2-2b:1208-fp8-static-kv8" \
  --dest ~/.cache/huggingface/hub

MODEL_PATH="$HOME/.cache/huggingface/hub/cosmos-reason2-2b_v1208-fp8-static-kv8"
jetson-clean

docker run --runtime nvidia -d \
  --name cosmos-reason2-fp8 \
  --restart no \
  --network host \
  -v $MODEL_PATH:/models/cosmos-reason2-2b:ro \
  -v $HOME/.cache/vllm:/root/.cache/vllm \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve /models/cosmos-reason2-2b \
      --served-model-name nvidia/cosmos-reason2-2b-fp8 \
      --max-model-len 8192 \
      --gpu-memory-utilization 0.75 \
      --reasoning-parser qwen3 \
      --enable-prefix-caching \
      --port 8010"

# Primera vez: ~5 minutos (torch.compile del modelo FP8)
echo -n "Esperando Cosmos FP8 (primera vez: torch.compile ~5 min)"
until curl -s http://localhost:8010/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " [OK] (FP8 vía vLLM en :8010)"
```

```bash
# Limpieza
docker stop cosmos-reason2 cosmos-reason2-fp8 2>/dev/null
docker rm cosmos-reason2 cosmos-reason2-fp8 2>/dev/null
```

---

## 14.7 Modelo 5 — Gemma 4 26B-A4B (MoE, Multimodal con Tool Calling)

Gemma 4 26B-A4B es el modelo más versátil del top 10: soporta texto e imagen, incluye tool calling nativo mediante el parser `gemma4`, y su arquitectura MoE (3.8B activos de 25.8B) lo hace eficiente para un modelo de este tamaño.

**Especificaciones:**

| Atributo | Valor |
|----------|-------|
| Parámetros | 25.8B total / 3.8B activos (MoE) |
| Modalidades | Texto + Imagen |
| Contexto máximo | 256K tokens |
| Precisión | AWQ 4-bit (vLLM) / Q4_K_M GGUF (llama.cpp) |
| RAM estimada | ~24GB |
| Motor | vLLM (gemma4-jetson-orin) / llama.cpp |
| Puerto | 8000 (vLLM) / 8080 (llama.cpp) |
| Velocidad | ~32 tok/s |
| Licencia | Apache 2.0 |

```bash
# Opción A: vLLM con AWQ y tool calling nativo
jetson-clean
check-ready   # necesita ~40GB libres
pwr-maxn

docker run --runtime nvidia -d \
  --name gemma4-26b-vllm \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit \
      --gpu-memory-utilization 0.75 \
      --enable-auto-tool-choice \
      --reasoning-parser gemma4 \
      --tool-call-parser gemma4 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Gemma 4 26B-A4B vLLM (~8-12 min)"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " [OK]"
```

```bash
# Opción B: llama.cpp con GGUF (menor RAM, más eficiente)
jetson-clean
check-ready
pwr-maxn

docker run --runtime nvidia -d \
  --name gemma4-26b-llama \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo ggml-org/gemma-4-26B-A4B-it-GGUF \
    --hf-file gemma-4-26B-A4B-it-Q4_K_M.gguf \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias gemma4-26b \
    --host 0.0.0.0

echo -n "Esperando Gemma 4 26B-A4B llama.cpp"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 20
done
echo " [OK]"
```

```bash
# Limpieza
docker stop gemma4-26b-vllm gemma4-26b-llama 2>/dev/null
docker rm gemma4-26b-vllm gemma4-26b-llama 2>/dev/null
```

---

## 14.8 Modelo 6 — Qwen3.5 9B (Mejor Velocidad entre Modelos Medianos)

El Qwen3.5 9B ofrece la mejor relación velocidad/calidad del top 10: ~55 tok/s con 9B de parámetros y ~12GB de RAM. Es el modelo ideal cuando se necesita respuesta rápida sin sacrificar demasiado en calidad.

```bash
# Servir Qwen3.5 9B
jetson-clean
pwr-30w   # 9B no necesita MAXN

docker run --runtime nvidia -d \
  --name qwen35-9b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-9B-quantized.w4a16 \
      --gpu-memory-utilization 0.40 \
      --enable-prefix-caching \
      --reasoning-parser qwen3 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Qwen3.5 9B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " [OK] (~12GB, ~55 tok/s)"
```

```bash
# Benchmark de velocidad
time curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Kbenkhaled/Qwen3.5-9B-quantized.w4a16",
       "messages":[{"role":"user","content":"Escribe un poema de 4 versos sobre inteligencia artificial en el borde."}],
       "extra_body":{"chat_template_kwargs":{"enable_thinking":false}},
       "max_tokens":200}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

```bash
# Limpieza
docker stop qwen35-9b && docker rm qwen35-9b
```

---

## 14.9 Modelo 7 — Nemotron3 Nano 4B (Mínima RAM, Máximo Paralelismo)

Con solo ~4GB de RAM, el Nemotron3 Nano 4B es el modelo más liviano del top 10. Su arquitectura optimizada para baja latencia lo hace ideal para pipelines que necesitan respuestas rápidas o ejecutar múltiples contextos en paralelo con la RAM restante.

```bash
# Servir Nemotron3 Nano 4B
jetson-clean
pwr-30w

docker run --runtime nvidia -d \
  --name nemotron3-4b \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    --hf-repo nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF \
    --hf-file NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf \
    --ctx-size 8196 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias nemotron3-4b \
    --host 0.0.0.0

echo -n "Esperando Nemotron3 Nano 4B"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 10
done
echo " [OK] (~4GB, ~43 tok/s)"
```

```bash
# Test de contexto largo
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nemotron3-4b",
       "messages":[{"role":"user","content":"¿Cuál es la diferencia entre edge computing y cloud computing en el contexto de IoT y robótica?"}],
       "max_tokens":300}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

```bash
# Limpieza
docker stop nemotron3-4b && docker rm nemotron3-4b
```

---

## 14.10 Modelo 8 — Qwen3.5 4B (Equilibrio Velocidad/Calidad en Paquete Compacto)

El Qwen3.5 4B es el punto óptimo para desarrollo diario: 4B parámetros en AWQ 4-bit, ~5GB RAM, ~50 tok/s, razonamiento activable y tool calling. Es el modelo más práctico para desarrollo y pruebas rápidas.

```bash
# Servir Qwen3.5 4B
jetson-clean
pwr-30w

docker run --runtime nvidia -d \
  --name qwen35-4b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cyankiwi/Qwen3.5-4B-AWQ-4bit \
      --gpu-memory-utilization 0.25 \
      --enable-prefix-caching \
      --reasoning-parser qwen3 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Qwen3.5 4B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " [OK] (~5GB, ~50 tok/s)"
```

```bash
# Test de generación de código
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"cyankiwi/Qwen3.5-4B-AWQ-4bit",
       "messages":[{"role":"user","content":"Escribe un script bash para monitorear el uso de memoria del Jetson cada 5 segundos y escribirlo en un log."}],
       "extra_body":{"chat_template_kwargs":{"enable_thinking":false}},
       "max_tokens":400}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

```bash
# Limpieza
docker stop qwen35-4b && docker rm qwen35-4b
```

---

## 14.11 Modelo 9 — Gemma 4 E4B (Multimodal Google, Texto + Imagen + Audio)

El Gemma 4 E4B de Google es un modelo multimodal de ~5B parámetros que soporta texto, imagen y audio. Tiene dos modos de despliegue con características muy distintas:

| | Opción A — vLLM (bfloat16) | Opción B — llama.cpp (GGUF Q4) |
|---|---|---|
| **RAM** | ~10 GB | ~3 GB |
| **Tok/s** | ~50 | ~45 |
| **Tool calling** | Si (gemma4 nativo) | Basico |
| **Multimodal** | Si (texto + imagen) | Solo texto |
| **Token HF requerido** | Si (modelo gated) | No (GGUF de Unsloth) |
| **Arranque** | ~3 min | ~20 seg |
| **Puerto** | 8000 | 8080 |
| **Mejor para** | Produccion, Open WebUI, agentes | Prototipado rapido, bajo consumo |

> **ADVERTENCIA:** La Opción A usa el modelo oficial gated de Google. Debe aceptar los términos en `huggingface.co/google/gemma-4-E4B-it` y tener `$HF_TOKEN` configurado.

### 14.11.1 Opción A — vLLM con bfloat16 (tool calling nativo)

```bash
# Verificar token HuggingFace antes de iniciar
source ~/venvs/llm/bin/activate
hf whoami
# Debe mostrar su nombre de usuario en HuggingFace
# Si falla: hf auth login --token $HF_TOKEN
```

```bash
jetson-clean
pwr-30w

docker run --runtime nvidia -d \
  --name gemma4-e4b-vllm \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve google/gemma-4-E4B-it \
      --dtype bfloat16 \
      --gpu-memory-utilization 0.50 \
      --enable-auto-tool-choice \
      --reasoning-parser gemma4 \
      --tool-call-parser gemma4 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando Gemma 4 E4B vLLM (~3 min primer arranque)"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 20
done
echo " [OK] Gemma 4 E4B bfloat16 (~10GB RAM)"
```

```bash
# Test de texto con tool calling:
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [{"role": "user", "content": "Cual es la raiz cuadrada de 144?"}],
    "max_tokens": 100
  }' | python3 -c \
  "import sys,json; r=json.load(sys.stdin); print(r['choices'][0]['message']['content'])"
```

```bash
# Test de analisis de imagen (capacidad multimodal):
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Medellin.jpg/1200px-Medellin.jpg"}},
        {"type": "text", "text": "Que ciudad es esta y que la hace atractiva para visitantes?"}
      ]
    }],
    "max_tokens": 300
  }' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

```bash
# Benchmark de rendimiento (Opcion A):
bench-model 8000 "google/gemma-4-E4B-it" "Explica el concepto de memoria unificada en 80 palabras." 3
```

### 14.11.2 Opción B — llama.cpp GGUF (bajo consumo, arranque rapido)

La versión GGUF cuantizada Q4_K_M de Unsloth no requiere token de HuggingFace y arranca en ~20 segundos:

```bash
jetson-clean
pwr-30w

docker run --runtime nvidia -d \
  --name gemma4-e4b-llama \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    -hf unsloth/gemma-4-E4B:Q4_K_M \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias gemma4-e4b \
    --host 0.0.0.0

echo -n "Esperando Gemma 4 E4B llama.cpp"
until curl -s http://localhost:8080/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 10
done
echo " [OK] Gemma 4 E4B GGUF Q4 (~3GB RAM)"
```

```bash
# Test de texto (Opcion B — solo texto, sin multimodal):
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4-e4b",
    "messages": [{"role": "user", "content": "Genera un haiku sobre inteligencia artificial."}],
    "max_tokens": 80
  }' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

```bash
# Benchmark de rendimiento (Opcion B):
bench-model 8080 "gemma4-e4b" "Explica el concepto de memoria unificada en 80 palabras." 3
```

```bash
# Comparacion directa A vs B (ejecutar una a la vez):
# Opcion A: ~50 tok/s, ~10GB RAM, soporta imagenes, tool calling nativo
# Opcion B: ~45 tok/s,  ~3GB RAM, solo texto, arranque en 20 seg
```

```bash
# Limpieza
docker stop gemma4-e4b-vllm 2>/dev/null; docker rm gemma4-e4b-vllm 2>/dev/null
docker stop gemma4-e4b-llama 2>/dev/null; docker rm gemma4-e4b-llama 2>/dev/null
```

---

## 14.12 Modelo 10 — GPT OSS 20B (Compatibilidad Drop-in con API OpenAI)

El GPT OSS 20B de OpenAI es un modelo MoE de 21B parámetros (3.6B activos) con la API completamente compatible con OpenAI. Cualquier aplicación que funcione con `openai.ChatCompletion` funciona con este modelo sin cambios en el código.

> **ADVERTENCIA:** Requiere los archivos de encodings tiktoken pre-descargados en `$HOME/.cache/tiktoken/`. Sin estos archivos, el modelo falla al iniciar.

```bash
# Prerrequisito: Descargar encodings tiktoken
mkdir -p $HOME/.cache/tiktoken
wget -q https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken \
  -O $HOME/.cache/tiktoken/cl100k_base.tiktoken
wget -q https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken \
  -O $HOME/.cache/tiktoken/o200k_base.tiktoken

# Verificar
ls -lh $HOME/.cache/tiktoken/
# Salida esperada:
# -rw-r--r-- 1 jetson jetson  1.7M cl100k_base.tiktoken
# -rw-r--r-- 1 jetson jetson  2.1M o200k_base.tiktoken
```

```bash
# Servir GPT OSS 20B
jetson-clean
pwr-maxn   # 20B necesita MAXN

docker run --runtime nvidia -d \
  --name gpt-oss-20b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -v $HOME/.cache/tiktoken:/etc/encodings \
  -e TIKTOKEN_ENCODINGS_BASE=/etc/encodings \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve openai/gpt-oss-20b \
      --gpu-memory-utilization 0.75 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando GPT OSS 20B"
until curl -s http://localhost:8000/v1/models > /dev/null 2>&1; do
  echo -n "."; sleep 30
done
echo " [OK] (~18GB, ~42 tok/s)"
```

```python
# Cliente Python — compatible 100% con el SDK de OpenAI
# source ~/venvs/llm/bin/activate && python3 este_script.py

from openai import OpenAI

# Drop-in replacement: solo cambiar la base_url
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

# Streaming response (igual que con la API real de OpenAI)
stream = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "system", "content": "Eres un asistente de viajes especialista en Colombia."},
        {"role": "user", "content": "Dame 3 razones para visitar el Eje Cafetero."}
    ],
    max_tokens=300,
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

```bash
# Limpieza
docker stop gpt-oss-20b && docker rm gpt-oss-20b
```

---

## 14.13 Script de Benchmarking Universal

El siguiente script mide la velocidad de cualquier modelo activo en cualquier puerto, reportando tokens por segundo promedio después de N iteraciones:

```bash
# Crear script de benchmark
cat > ~/scripts/benchmark-model.sh << 'BENCH'
#!/bin/bash
# Uso: benchmark-model.sh [puerto] [model-id] [iteraciones]
PORT=${1:-8000}
MODEL_ID=${2:-"auto"}
ITERS=${3:-5}

# Auto-detectar model ID si no se especifica
if [ "$MODEL_ID" = "auto" ]; then
  MODEL_ID=$(curl -s http://localhost:$PORT/v1/models 2>/dev/null | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null)
fi

[ -z "$MODEL_ID" ] && { echo "[ERROR] No hay modelo activo en :$PORT"; exit 1; }

echo "═══════════════════════════════════════════════"
echo "  BENCHMARK: $MODEL_ID"
echo "  Puerto: $PORT | Iteraciones: $ITERS"
echo "═══════════════════════════════════════════════"

PROMPT="Explain edge computing in exactly 50 words in Spanish."
TOTAL_TOKS=0; TOTAL_TIME=0

for i in $(seq 1 $ITERS); do
  START=$(date +%s%3N)
  RESP=$(curl -s http://localhost:$PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL_ID\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}],\"max_tokens\":100}")
  END=$(date +%s%3N)
  ELAPSED=$(( END - START ))
  TOKS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('usage',{}).get('completion_tokens',0))")
  TPS=$(python3 -c "print(f'{$TOKS/($ELAPSED/1000):.1f}')")
  echo "  Run $i: ${ELAPSED}ms | $TOKS tokens | $TPS tok/s"
  TOTAL_TOKS=$((TOTAL_TOKS + TOKS))
  TOTAL_TIME=$((TOTAL_TIME + ELAPSED))
done

AVG_TOKS=$((TOTAL_TOKS / ITERS))
AVG_TIME=$((TOTAL_TIME / ITERS))
AVG_TPS=$(python3 -c "print(f'{$AVG_TOKS/($AVG_TIME/1000):.1f}')")

echo ""
echo "  ── PROMEDIO ($ITERS runs) ──"
echo "  Tokens: $AVG_TOKS | Tiempo: ${AVG_TIME}ms | Velocidad: ${AVG_TPS} tok/s"
echo "═══════════════════════════════════════════════"
BENCH

chmod +x ~/scripts/benchmark-model.sh
alias bench-model='~/scripts/benchmark-model.sh'
echo "Alias bench-model configurado. Agregar a ~/.bashrc para persistir."
```

```bash
# Uso del benchmark
bench-model 8000                      # auto-detecta modelo en puerto 8000
bench-model 8080 nemotron-omni 10    # 10 iteraciones en puerto 8080
bench-model 8000 openai/gpt-oss-20b 3   # 3 iteraciones, modelo específico
```

---

## 14.14 Script de Testing Completo en Python

```python
#!/usr/bin/env python3
"""
test_model.py — Test completo del modelo activo en cualquier puerto.
Uso: source ~/venvs/llm/bin/activate && python3 ~/scripts/test_model.py [--port 8000]
"""
import json, time, sys, urllib.request
from openai import OpenAI

def get_active_model(port: int):
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/v1/models", timeout=3) as r:
            data = json.loads(r.read())
            return data["data"][0]["id"], f"http://localhost:{port}/v1"
    except Exception:
        return None, None

def run_tests(port: int = 8000):
    model_id, base_url = get_active_model(port)
    if not model_id:
        model_id, base_url = get_active_model(8080 if port == 8000 else 8000)
    if not model_id:
        print("[ERROR] No hay modelo activo en puerto 8000 ni 8080"); return

    print(f"\n{'═'*55}")
    print(f"  TESTING: {model_id}")
    print(f"  URL: {base_url}")
    print(f"{'═'*55}\n")

    client = OpenAI(base_url=base_url, api_key="not-needed")
    tests = [
        {"name": "Respuesta básica",
         "messages": [{"role": "user", "content": "Di 'hola mundo' en exactamente 3 palabras."}],
         "max_tokens": 20},
        {"name": "Razonamiento matemático",
         "messages": [{"role": "user", "content": "Si tengo $100, gasto 30% en comida y 25% en transporte, ¿cuánto me queda?"}],
         "max_tokens": 150},
        {"name": "Generación de código",
         "messages": [{"role": "user", "content": "Escribe solo el código Python para calcular fibonacci recursivamente."}],
         "max_tokens": 200},
        {"name": "Multilingüe",
         "messages": [{"role": "user", "content": "Translate to Spanish: 'The only risk in Colombia is wanting to stay.'"}],
         "max_tokens": 80},
        {"name": "JSON estructurado",
         "messages": [{"role": "user", "content": "Devuelve solo un JSON con 2 ciudades de Colombia y su población aproximada."}],
         "max_tokens": 150},
    ]

    for test in tests:
        print(f"  ── {test['name']} ──")
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=test["messages"],
                max_tokens=test["max_tokens"]
            )
            elapsed = time.time() - t0
            content = resp.choices[0].message.content
            toks = resp.usage.completion_tokens if resp.usage else 0
            tps = toks / elapsed if elapsed > 0 else 0
            print(f"  [OK] {elapsed:.2f}s | {toks} tokens | {tps:.1f} tok/s")
            print(f"     → {content[:120]}{'...' if len(content) > 120 else ''}\n")
        except Exception as e:
            print(f"  [ERROR] Error: {e}\n")

port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
run_tests(port)
```

```bash
# Guardar y ejecutar
cat > ~/scripts/test_model.py << 'EOF'
# (pegar el contenido del bloque Python anterior aquí)
EOF
chmod +x ~/scripts/test_model.py

# Uso
source ~/venvs/llm/bin/activate
python3 ~/scripts/test_model.py           # puerto 8000 por defecto
python3 ~/scripts/test_model.py --port 8080  # modelos llama.cpp
```

---

## 14.15 Resumen de Resultados — Tabla de Benchmarks Consolidada

Resultados medidos en Jetson AGX Orin 64GB · JetPack 7.2 · modo MAXN (cuando aplica):

| Modelo | RAM | tok/s | TTFT | Tool Calling | Imagen | Audio/Video | Ideal para |
|--------|-----|-------|------|-------------|--------|-------------|------------|
| Qwen3.5 35B-A3B | ~26GB | ~32 | ~2.5s | Sí (qwen3) | No | No | Máxima calidad, razonamiento |
| Nemotron Omni 30B | ~24GB | ~39 | ~1.8s | No | Sí | Sí | Multimedia, transcripción |
| Qwen3-VL-4B | ~6GB | ~58 | ~0.9s | No | Sí | No | OCR, GUI agent, visión liviana |
| Cosmos Reason 2 2B | ~4GB | ~59 | ~0.7s | No | Sí | Video | Anomalías, robótica, escenas |
| Gemma 4 26B-A4B | ~24GB | ~32 | ~2.2s | Sí (gemma4) | Sí | No | Versátil, tool calling + imagen |
| Qwen3.5 9B | ~12GB | ~55 | ~1.1s | Sí (qwen3) | No | No | Velocidad con calidad |
| Nemotron3 Nano 4B | ~4GB | ~43 | ~0.6s | No | No | No | Mínima latencia, alta paralelización |
| Qwen3.5 4B | ~5GB | ~50 | ~0.8s | Sí (qwen3) | No | No | Desarrollo, pruebas diarias |
| Gemma 4 E4B (GGUF) | ~3GB | ~55 | ~0.7s | Sí (gemma4) | Sí | Sí | Multimodal compacto |
| GPT OSS 20B | ~18GB | ~42 | ~1.5s | No | No | No | Compatibilidad OpenAI |

> **CONSEJO:** Para integración con OpenClaw (Capítulo 13), priorice modelos con tool calling nativo: Qwen3.5 35B-A3B, Gemma 4 26B-A4B y Gemma 4 E4B. El perfil `gemma4` es el más estable para respuestas de WhatsApp.

---

## Resumen del Capítulo

Este capítulo cubrió los 10 modelos más importantes para el Jetson AGX Orin 64GB con JetPack 7.2: comandos exactos de instalación, pruebas de validación, scripts de benchmarking y guías de selección por caso de uso.

Los puntos clave son:
- Las **tres imágenes Docker** (`latest-jetson-orin`, `gemma4-jetson-orin`, `llama_cpp:latest-jetson-orin`) cubren los 10 modelos del top
- La función `jetson-clean` es obligatoria antes de cada cambio de modelo para liberar la memoria unificada
- Los **modelos MoE** (Qwen3.5 35B, Gemma 4 26B, Nemotron Omni) ofrecen calidad de modelo grande con eficiencia de modelo pequeño
- El modelo más eficiente por caso de uso depende de la modalidad requerida (texto, imagen, audio, video) y la RAM disponible

El siguiente capítulo (Capítulo 15) cubre el despliegue en producción: endurecimiento del sistema, watchdogs, firewall UFW, automatización del arranque y gestión del registro de parches.
