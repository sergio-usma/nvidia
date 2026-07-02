# Capítulo 10 — Motores de Inferencia (llama.cpp, vLLM y Ollama)

**Getting Started with NVIDIA Jetson AGX Orin 64GB (JetPack 7.2)**
*Capítulo 12 de 16*

---

## Objetivo de esta parte

Al completar esta parte, habrá instalado y verificado tres motores de inferencia de LLM en su Jetson AGX Orin: **Ollama** (el más sencillo), **llama.cpp compilado desde fuente** (para modelos GGUF cuantizados) y **vLLM** (para producción con tool calling). También comprenderá cuándo usar cada uno y cómo configurarlos para trabajar juntos o de forma independiente.

**Prerrequisitos:**
- Sistema base configurado (Capítulo 2)
- Docker instalado con runtime NVIDIA (Capítulo 8)
- Token de HuggingFace configurado (ver Sección 12.3.1)

### 12.0 Crear el Entorno Virtual Python para LLM

Antes de comenzar, cree el entorno virtual Python que se usará para interactuar con los motores de inferencia desde código Python:

```bash
# Verificar si el venv 'llm' ya existe (de un capitulo anterior)
ls ~/venvs/llm 2>/dev/null && echo "[OK] venv llm ya existe — omitir creacion" || echo "[INFO] Creando venv llm..."

# Crear el entorno virtual 'llm' para JP 7.2 (solo si no existe)
[ ! -d ~/venvs/llm ] && python3.12 -m venv ~/venvs/llm

# Activar el entorno
source ~/venvs/llm/bin/activate

# Instalar dependencias base para interactuar con cualquier motor vía OpenAI SDK
pip install --upgrade pip
pip install openai requests httpx

# Para experimentos con HuggingFace Transformers (modelos pequeños sin contenedor):
pip install transformers accelerate

# Desactivar cuando no se use
deactivate

# Alias permanente en ~/.bashrc para activar rápido
echo "alias llm-env='source ~/venvs/llm/bin/activate'" >> ~/.bashrc
source ~/.bashrc
```

> **NOTA:** Este venv se usa exclusivamente para código Python que **llama a** los motores de inferencia (Ollama, vLLM, llama.cpp). Los propios motores de inferencia corren dentro de contenedores Docker o como servicios del sistema — no dentro del venv.

### 12.0.1 Iniciar Docker bajo demanda (clean-start)

El Jetson arranca con Docker deshabilitado en boot (Capítulo 8 + Capítulo 15). Antes de cualquier `docker run`, inicie el daemon explícitamente:

```bash
# Iniciar Docker cuando lo necesite
sudo systemctl start docker.socket && sudo systemctl start docker
docker info | grep "Server Version"
# Salida esperada: Server Version: 26.x.x

# Para detenerlo después (libera ~500MB RAM):
sudo systemctl stop docker && sudo systemctl stop docker.socket
```

Estos dos comandos tienen aliases en `~/.bashrc`:
```bash
alias docker-on='sudo systemctl start docker.socket && sudo systemctl start docker'
alias docker-off='sudo systemctl stop docker && sudo systemctl stop docker.socket'
```

> **CONSEJO:** Añada estos aliases ya en este punto. El Apéndice los documenta en el bloque completo de `~/.bashrc`.

---

## Introducción: ¿Qué es un motor de inferencia?

Un **motor de inferencia** (*inference engine*) es el software que toma un modelo de lenguaje grande (LLM) —un archivo de varios gigabytes con millones o billones de parámetros— y lo hace funcionar para responder preguntas. Sin un motor de inferencia, un modelo es solo datos; con él, se convierte en una API que cualquier aplicación puede consultar.

El Jetson AGX Orin 64GB tiene una característica única: su memoria de **64 GB LPDDR5 es compartida entre CPU y GPU** (memoria unificada). Esto significa que los LLMs no necesitan "caber en VRAM" como en una tarjeta gráfica discreta —toda la RAM del sistema está disponible para el modelo. Un modelo de 40 GB cabe perfectamente en el Jetson; en un PC con una RTX 4090 de 24 GB de VRAM no cabría.

### ¿Por qué hay tres motores diferentes?

Cada motor tiene sus ventajas:

| Motor | Instalación | Puerto | Mejor para |
|-------|-------------|--------|------------|
| **Ollama** | Instalador nativo | 11434 | Chat, RAG, exploración, embeddings |
| **llama.cpp** | Compilar desde fuente | 9090 | Modelos GGUF cuantizados, 70B+ |
| **vLLM** | Contenedor Docker | 8000 | Producción, tool calling, JSON estructurado |

> **Regla de oro:** Solo puede ejecutar un modelo grande a la vez. Los tres motores comparten los mismos 64 GB de RAM unificada. Planifique qué motor necesita según su caso de uso antes de iniciarlo.

---

## 12.1 Motor de Inferencia 1: Ollama

Ollama es el motor más sencillo de instalar y usar. Internamente utiliza llama.cpp y expone una API compatible con OpenAI en el puerto 11434. Es ideal para desarrollo, pruebas rápidas, y pipelines de RAG (*Retrieval-Augmented Generation*).

### 12.1.1 Instalación nativa

En JetPack 7.2, el contenedor Docker de NVIDIA para Ollama (`r38.2.arm64-sbsa-cu130-24.04`) **no funciona** en el Jetson AGX Orin con JP 7.2 (L4T r39.2) porque está dirigido al Jetson Thor (L4T r38.x) y entra en un bucle de reinicios. Utilice siempre el **instalador nativo**:

```bash
# Instalador oficial — detecta arm64 y la GPU automáticamente
curl -fsSL https://ollama.com/install.sh | sh
```

Verá la siguiente salida durante la instalación (puede tardar **2-3 minutos**):

```
>>> Downloading ollama...
>>> Installing ollama to /usr/local/bin...
WARNING: Unsupported JetPack version detected. GPU may not be supported
>>> NVIDIA JetPack ready.
>>> The Ollama API is now available at 127.0.0.1:11434.
>>> Enabling and starting ollama service...
```

> **IMPORTANTE:** El mensaje `WARNING: Unsupported JetPack version detected` es cosmético. Ollama 0.x aún no reconoce la cadena de versión de JP 7.2, pero la detección de GPU funciona correctamente a través de las bibliotecas CUDA. La línea **"NVIDIA JetPack ready"** confirma que la GPU está activa.

Verifique la instalación:

```bash
ollama --version
sudo systemctl status ollama
```

Salida esperada:

```
ollama version is 0.x.x
● ollama.service - Ollama Service
     Loaded: loaded (/etc/systemd/system/ollama.service; enabled)
     Active: active (running)
```

### 12.1.2 Configurar acceso desde la red (crítico)

Por defecto, Ollama solo acepta conexiones desde `127.0.0.1` (el propio Jetson). Para acceder desde Windows, otros contenedores o aplicaciones remotas, debe cambiarlo a `0.0.0.0`:

```bash
# Crear el directorio de override de systemd
sudo mkdir -p /etc/systemd/system/ollama.service.d/

# Crear el archivo de configuración
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF
```

**¿Qué hace cada variable?**
- `OLLAMA_HOST=0.0.0.0` — acepta conexiones desde cualquier IP (no solo localhost)
- `OLLAMA_ORIGINS=*` — permite CORS desde cualquier origen (necesario para Open WebUI)
- `OLLAMA_NUM_PARALLEL=2` — maneja 2 peticiones simultáneas (útil para pipelines agénticos)
- `OLLAMA_MAX_LOADED_MODELS=1` — evita que múltiples modelos ocupen RAM simultáneamente

```bash
# Aplicar los cambios
sudo systemctl daemon-reload
sudo systemctl restart ollama
sleep 3

# Verificar que el binding es correcto
sudo ss -tlnp | grep 11434
```

Salida esperada (debe mostrar `*:11434`, no `127.0.0.1:11434`):

```
LISTEN 0  4096  *:11434  *:*  users:(("ollama",pid=XXXX,fd=3))
```

```bash
# Abrir el firewall
sudo ufw allow 11434/tcp comment "Ollama API"
```

### 12.1.3 Control de keep_alive (esencial para memoria)

Ollama mantiene el modelo en memoria **5 minutos** después de la última petición. En el Jetson, esto puede bloquear la RAM cuando quiere cambiar a vLLM u otro motor. Para descargar el modelo manualmente en cualquier momento:

```bash
# Descargar un modelo de GPU/RAM sin parar el servicio
curl -s http://localhost:11434/api/generate \
  -d '{"model":"nombre-del-modelo","keep_alive":0}' > /dev/null

# Verificar que no hay modelos cargados
ollama ps
```

Para un keep_alive de 5 minutos (el valor por defecto de Ollama es razonable para el Jetson), configure explícitamente el override de systemd. Si prefiere liberar memoria inmediatamente después de cada conversación, use `0`:

```bash
# OPCION A: keep_alive=5m (comportamiento razonable — libera memoria a los 5 min)
sudo tee -a /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
Environment="OLLAMA_KEEP_ALIVE=5m"
EOF

# OPCION B: keep_alive=0 (libera memoria inmediatamente tras cada peticion)
# Util cuando trabaja con multiples motores y necesita la RAM libre
# sudo tee -a /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
# Environment="OLLAMA_KEEP_ALIVE=0"
# EOF

sudo systemctl daemon-reload && sudo systemctl restart ollama
```

> **IMPORTANTE:** Con `OLLAMA_KEEP_ALIVE=5m`, el modelo permanece en RAM 5 minutos entre consultas. Use el alias `stop-ollama` cuando termine de trabajar para liberar la memoria antes de iniciar otro motor. No use `OLLAMA_KEEP_ALIVE=-1` (infinito) en el Jetson — impedirá iniciar vLLM o llama.cpp.

### 12.1.4 Descarga y gestión de modelos

```bash
# Modelos recomendados para Jetson AGX Orin 64GB

# Tool calling (requerido para agentes)
ollama pull qwen3:8b              # 5 GB  — rápido, excelente tool calling
ollama pull qwen3:14b             # 9 GB  — mayor calidad

# Uso general
ollama pull gemma4:latest         # 9.6 GB — Google Gemma 4, multimodal
ollama pull gemma3:4b             # 2.5 GB — rápido, uso general

# Embedding para RAG
ollama pull nomic-embed-text      # 274 MB — embeddings locales rápidos

# Modelos grandes (usan la memoria unificada de 64 GB)
ollama pull qwen3:32b             # 20 GB — calidad premium
ollama pull gemma4:26b            # 17 GB — Gemma 4 MoE

# Ver modelos instalados
ollama list
```

Salida esperada de `ollama list`:

```
NAME                    ID              SIZE      MODIFIED
qwen3:8b                a8d9d84b3c66    5.2 GB    2 minutes ago
gemma4:latest           adc7671b8ca6    9.4 GB    5 minutes ago
nomic-embed-text:latest 0a109f422b47    274 MB    1 hour ago
```

### 12.1.5 Modos de energía recomendados

```bash
# Modelos 1B–4B
sudo nvpmodel -m 3    # MODE_15W — suficiente, ahorra energía

# Modelos 7B–8B
sudo nvpmodel -m 2    # MODE_30W — recomendado para chat responsivo

# Modelos 14B–32B
sudo nvpmodel -m 0    # MAXN (50W) — máximo rendimiento
sudo jetson_clocks
```

> **NOTA:** Al ejecutar `sudo nvpmodel -m X`, el Jetson mostrará un diálogo interactivo solicitando confirmación de reinicio (escriba `yes`). Tras el reinicio, el nuevo modo quedará activo. Consulte el Capítulo 5 para detalles sobre los modos de energía disponibles.

### 12.1.6 Verificar acceso a la GPU

```bash
# Correr con verbose para ver métricas de GPU
ollama run qwen3:8b --verbose "Explica edge AI en una frase" 2>&1 | \
  grep -E "eval rate|layers|cuda"
```

Salida esperada (confirma GPU activa):

```
eval rate:     25+ tokens/s   ← GPU confirmada (CPU-only sería 2-5 tok/s)
```

```bash
# Monitorear utilización de GPU durante inferencia (en otra terminal)
sudo tegrastats | grep -o "GR3D_FREQ [0-9]*%@\[[0-9,]*\]"
```

### 12.1.7 Test de la API

```bash
# Desde el Jetson — llamada directa a la API
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "Hola desde JP 7.2!"}],
    "max_tokens": 100
  }' | python3 -m json.tool

# Listar modelos disponibles
curl http://localhost:11434/api/tags | \
  python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

Desde **Windows PowerShell**:

```powershell
# Verificar acceso remoto
Invoke-RestMethod -Uri "http://192.168.1.100:11434/api/tags" |
    Select-Object -ExpandProperty models |
    ForEach-Object { [PSCustomObject]@{
        Nombre  = $_.name
        "Tamaño(GB)" = [math]::Round($_.size / 1GB, 1)
    }} | Format-Table -AutoSize
```

Salida esperada:

```
Nombre                  Tamaño(GB)
------                  ----------
qwen3:8b                5.2
gemma4:latest           9.4
nomic-embed-text:latest 0.3
```

### 12.1.8 Verificación completa de Ollama

```bash
echo "=== Estado de Ollama ==="

echo -n "Servicio:      "
systemctl is-active ollama

echo -n "Binding red:   "
sudo ss -tlnp | grep 11434 | grep -o "\*:11434" || echo "Revisar binding"

echo -n "GPU activa:    "
ollama run gemma3:1b --verbose "test" 2>&1 | grep "eval rate" | \
  awk '{print $3, $4, "(>20 tok/s = GPU activa)"}'

echo -n "Modelos:       "
ollama list | tail -n +2 | wc -l
echo "modelos instalados"

ollama list
```

---

## 12.2 Motor de Inferencia 2: llama.cpp (compilado desde fuente)

llama.cpp es el motor de referencia para modelos en formato **GGUF** (cuantizados). Sus ventajas en el Jetson son significativas: al usar `--n-gpu-layers 999`, descarga todos los pesos al procesador GPU de la memoria unificada y los ejecuta a través de los núcleos CUDA, logrando una aceleración de 3–5x sobre la inferencia por CPU.

### 12.2.1 ¿Por qué compilar desde fuente en JP 7.2?

JetPack 7.2 incluye **CUDA 13.2.1**. Los contenedores Docker precompilados de llama.cpp disponibles en Docker Hub (como `dustynv/llama_cpp:r36.4`) fueron compilados contra CUDA 12 y fallan en JP 7.2 con el error:

```
libcudart.so.12: cannot open shared object file: No such file or directory
```

La solución es compilar llama.cpp directamente en el Jetson usando el toolchain de CUDA 13 que ya está instalado y verificado (el mismo que usa Ollama). El proceso tarda **10-15 minutos** pero solo debe realizarse una vez.

> **NOTA:** El contenedor `ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin` del GitHub Container Registry de NVIDIA-AI-IOT es diferente a los contenedores de Docker Hub. Éste sí es compatible con JP 7.2 y se usa en los Backends C y D de la Sección 12.4. La compilación desde fuente que se documenta aquí es la alternativa para servir modelos GGUF propios en un flujo de trabajo independiente.

### 12.2.2 Prerrequisitos

```bash
# Instalar dependencias de compilación
sudo apt install -y cmake build-essential libcurl4-openssl-dev

# Activar el venv llm y verificar herramienta hf
source ~/venvs/llm/bin/activate
pip install --upgrade huggingface-hub

# Verificar que hf CLI está disponible
hf --version
```

### 12.2.3 Descargar un modelo GGUF

Antes de compilar, descargue el modelo que usará. Esto permite verificar más tarde que el servidor funciona:

```bash
source ~/venvs/llm/bin/activate
mkdir -p ~/jetson-ai-data/models/gguf

# Qwen3 8B Q4_K_M — 5 GB, rápido, excelente tool calling (verificado en JP 7.2)
hf download Qwen/Qwen3-8B-GGUF \
  --include "Qwen3-8B-Q4_K_M.gguf" \
  --local-dir ~/jetson-ai-data/models/gguf/
```

> **ADVERTENCIA:** El nombre exacto del repositorio importa. `Qwen/Qwen3.6-27B-GGUF` no existe. Los nombres correctos son `Qwen/Qwen3-8B-GGUF`, `Qwen/Qwen3-14B-GGUF`, etc. (sin el sufijo `.6` en los repositorios GGUF).

```bash
# Otros modelos GGUF verificados
# hf download Qwen/Qwen3-14B-GGUF --include "Qwen3-14B-Q4_K_M.gguf" --local-dir ~/jetson-ai-data/models/gguf/
# hf download google/gemma-3-4b-it-GGUF --include "gemma-3-4b-it-Q4_K_M.gguf" --local-dir ~/jetson-ai-data/models/gguf/

# Verificar la descarga
ls -lh ~/jetson-ai-data/models/gguf/*.gguf
```

Salida esperada:

```
-rw-rw-r-- 1 jetson jetson 5.2G Jun 28 10:30 Qwen3-8B-Q4_K_M.gguf
```

### 12.2.4 Compilar llama.cpp desde fuente

Ejecute este proceso dentro de una sesión **tmux** para que sobreviva a desconexiones SSH (la compilación tarda 10-15 minutos):

```bash
# Abrir sesión tmux
tmux new -s llama-build

# Clonar el repositorio
cd ~
git clone --depth 1 https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Configurar las variables de entorno de CUDA
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH

# Configurar el build con soporte CUDA 13 y arquitectura sm_87 (Orin)
cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES="87" \
  -DGGML_CUDA_F16=ON \
  -DCMAKE_BUILD_TYPE=Release
```

Salida esperada de cmake (extracto):

```
-- CUDA found: /usr/local/cuda
-- CUDA version: 13.2.1
-- GGML_CUDA_ARCHITECTURES: 87
-- Configuring done
```

```bash
# Compilar (usar -j 4 para no saturar la RAM)
cmake --build build --config Release -j 4

# Puede desconectarse del tmux mientras compila (Ctrl+A d)
# Para verificar el progreso: tmux attach -t llama-build
```

Al finalizar verá:

```
[100%] Linking CXX executable llama-server
[100%] Built target llama-server
```

```bash
# Verificar los binarios compilados
ls ~/llama.cpp/build/bin/
# llama-server  llama-cli  llama-bench  (entre otros)
```

### 12.2.5 Iniciar el servidor llama.cpp

```bash
# Ajustar el modo de energía según el modelo
sudo nvpmodel -m 2   # MODE_30W para modelos 7B-8B
# sudo nvpmodel -m 0 && sudo jetson_clocks   # MAXN para 27B+

# Iniciar el servidor
~/llama.cpp/build/bin/llama-server \
  --model ~/jetson-ai-data/models/gguf/Qwen3-8B-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --n-gpu-layers 999 \
  --ctx-size 8192 \
  --parallel 2 \
  --threads $(nproc)
```

Salida esperada al iniciar exitosamente:

```
I device_info:
I   - CUDA0   : Orin (62817 MiB, 59531 MiB free)   ← GPU confirmada
I llama_model_loader: loaded meta data with 32 key-value pairs
I llama_model_loader: Qwen3-8B-Q4_K_M.gguf
I srv  llama_server: server is listening on http://0.0.0.0:8080
```

> **CONSEJO:** El indicador clave es `CUDA0 : Orin` en los logs. Si ve `CPU` en lugar de `CUDA0`, verifique que `--n-gpu-layers 999` está incluido en el comando.

**Rendimiento verificado en AGX Orin 64GB / JP 7.2 (Qwen3-8B Q4_K_M, contexto 8192, 2 slots paralelos):**

```
Prompt eval:  45.13 tokens/seg
Generación:    7.61 tokens/seg
```

> **NOTA:** La velocidad de generación (7.61 tok/s) parece baja comparada con Ollama (25+ tok/s) porque `--parallel 2` reserva memoria de contexto para dos peticiones simultáneas, reduciendo la velocidad por petición. Con un solo slot (`--parallel 1`) el rendimiento sube. Para uso en producción con múltiples clientes, `--parallel 2` es el equilibrio correcto.

```bash
# Abrir el firewall
sudo ufw allow 8080/tcp comment "llama.cpp server"
```

### 12.2.6 Probar la API

```bash
# Health check
curl http://localhost:8080/health
```

Salida esperada:

```
{"status":"ok"}
```

```bash
# Chat básico
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-8b",
    "messages": [{"role": "user", "content": "Hola desde llama.cpp en JP 7.2!"}],
    "max_tokens": 100
  }' | python3 -m json.tool
```

### 12.2.7 Modo de razonamiento en Qwen3 (importante)

Los modelos Qwen3 activan el "modo de pensamiento" (*thinking mode*) por defecto. El texto generado aparece en el campo `reasoning_content` en lugar de `content` (que puede aparecer vacío). Hay tres soluciones:

**Opción A — Deshabilitar por petición con `/no_think` (recomendado):**

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-8b",
    "messages": [{"role": "user", "content": "Hola! /no_think"}],
    "max_tokens": 100
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
msg = r['choices'][0]['message']
print(msg.get('content') or msg.get('reasoning_content', ''))
"
```

**Opción B — Deshabilitar globalmente con system prompt:**

```json
{"role": "system", "content": "You are a helpful assistant. /no_think"}
```

**Opción C — Parsear `reasoning_content` en el código cliente:**

```python
response = r["choices"][0]["message"]
answer = response.get("content") or response.get("reasoning_content", "")
```

### 12.2.8 Crear unit file systemd (solo referencia — NO habilitar en boot)

> **ATENCIÓN — Arquitectura clean-start:** El Jetson debe arrancar siempre sin motores de inferencia activos. **NO** ejecute `sudo systemctl enable llama-server` si quiere mantener el arranque limpio. El unit file se crea como referencia para lanzamiento bajo demanda mediante `sudo systemctl start llama-server`. Véase el Capítulo 15 §15.8 para los aliases de lanzamiento bajo demanda que son el método recomendado.

```bash
sudo tee /etc/systemd/system/llama-server.service << 'EOF'
[Unit]
Description=llama.cpp GGUF Inference Server — Jetson AGX Orin JP 7.2
After=network.target

[Service]
Type=simple
User=jetson
Environment="CUDA_HOME=/usr/local/cuda"
Environment="PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib/aarch64-linux-gnu/tegra"
ExecStart=/home/jetson/llama.cpp/build/bin/llama-server \
  --model /home/jetson/jetson-ai-data/models/gguf/Qwen3-8B-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --n-gpu-layers 999 \
  --ctx-size 8192 \
  --parallel 2 \
  --threads 8
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
# NO habilitar en boot: sudo systemctl enable llama-server  ← NO ejecutar

# Lanzar bajo demanda (solo cuando necesite el motor):
sudo systemctl start llama-server

# Auditoría post-instalación — verificar que NO está habilitado en boot:
systemctl is-enabled llama-server   # debe responder: disabled

# Verificar servicio activo:
sudo systemctl status llama-server
curl http://localhost:8080/health
```

Salida esperada:

```
● llama-server.service - llama.cpp GGUF Inference Server
     Active: active (running)
{"status":"ok"}
```

> **CONSEJO:** El alias `llama-start` en `~/.bashrc` (documentado en Capítulo 15 §15.8) es la forma más práctica de lanzar llama.cpp bajo demanda. Utilice el unit file solo si necesita integración con otros servicios de systemd.

---

## 12.3 Motor de Inferencia 3: vLLM (Producción)

vLLM 0.22.0 utiliza **PagedAttention** y *continuous batching* para maximizar el rendimiento en producción. Con la alineación SBSA introducida en JetPack 7.2, el contenedor upstream oficial de vLLM funciona nativamente en el AGX Orin —sin necesidad de compilaciones específicas para Jetson.

### 12.3.1 Token de HuggingFace — Configuración permanente (obligatorio)

vLLM descarga los modelos dentro del contenedor al arrancar. Sin un token válido, las descargas están limitadas en velocidad y verá advertencias.

> **NOTA — Dos tipos de token de HuggingFace:**
>
> HuggingFace maneja dos mecanismos de autenticación distintos, y ambos son **complementarios** — tener ambos es lo correcto:
>
> - **Token estático** (`hf_xxxx...`): Se genera manualmente en `huggingface.co/settings/tokens` y se copia en la variable `HF_TOKEN`. Este token tiene permisos que usted define (lectura, escritura) y no expira a menos que lo revoque explícitamente.
>
> - **Token OAuth** (`hf auth login`): Es el token que genera el CLI interactivo de HuggingFace. Crea el archivo `~/.cache/huggingface/token` y permite que herramientas como `huggingface-cli` y `transformers` accedan automáticamente sin necesitar la variable `HF_TOKEN`.
>
> En la práctica ambos pueden apuntar al mismo token: genere uno estático en la web → ejecútelo en `hf auth login` → queda guardado en `~/.cache/huggingface/token` Y disponible como variable de entorno. **Si aún no ejecutó `hf auth login`, hágalo ahora:**
>
> ```bash
> source ~/venvs/llm/bin/activate
> hf auth login
> # Pegue su token estático cuando lo solicite, o autorice via navegador
> ```

El token debe configurarse en **tres ubicaciones** para garantizar que siempre esté disponible:

**Ubicación 1: `~/.bashrc`**

```bash
# Después de hf auth login, capturar el token
hf auth login   # Siga las instrucciones, autorice en el navegador

TOKEN=$(cat ~/.cache/huggingface/token)
echo "export HF_TOKEN=\"$TOKEN\"" >> ~/.bashrc
source ~/.bashrc

# Verificar
echo $HF_TOKEN | head -c 15
# → hf_xxxxxxxxxxxxx...
```

**Ubicación 2: `/etc/environment` (para servicios del sistema)**

```bash
echo "HF_TOKEN=$(cat ~/.cache/huggingface/token)" | sudo tee -a /etc/environment
```

**Ubicación 3: `~/.cache/huggingface/token` (ya existe tras `hf auth login`)**

```bash
ls -la ~/.cache/huggingface/token
# -rw------- 1 jetson jetson 37 Jun 28 10:00 /home/jetson/.cache/huggingface/token
```

> **CONSEJO:** Si rota su token de HuggingFace, ejecute `hf auth login` de nuevo y repita el paso de `echo export HF_TOKEN...` para actualizar `~/.bashrc`.

### 12.3.2 Enfoque A: Contenedor SBSA upstream (uso general)

Este enfoque usa el contenedor oficial de vLLM Project y es ideal para uso general, pruebas, y modelos que no requieren la integración con OpenClaw:

```bash
# Crear directorio de caché de modelos
mkdir -p ~/jetson-ai-data/models/hf

# Verificar que Docker tiene el runtime nvidia configurado
docker info | grep "Default Runtime"
# → Default Runtime: nvidia
```

```bash
# Ajustar modo de energía
sudo nvpmodel -m 2   # MODE_30W para modelos 4B-8B
# sudo nvpmodel -m 0 && sudo jetson_clocks   # MAXN para 14B+

# Lanzar vLLM con Gemma 4 E4B (modelo por defecto)
docker run --runtime nvidia -d \
  --name vllm \
  --network host \
  --ipc host \
  --shm-size 8g \
  --restart no \
  -e HF_TOKEN=$HF_TOKEN \
  -v ~/jetson-ai-data/models/hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
  google/gemma-4-E4B-it \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.70
```

> **ADVERTENCIA:** Use siempre `--restart no` (nunca `--restart unless-stopped`). Un contenedor de vLLM con restart automático que se inicia al arrancar el sistema consume silenciosamente 10-15 GB de RAM unificada antes de que usted inicie sesión, dejando el sistema con poca memoria disponible. Esto se detalla en el Capítulo 15.

### 12.3.3 Monitorear el arranque de vLLM

El arranque de vLLM tiene **dos fases distintas** que pueden tomar varios minutos cada una:

```bash
docker logs vllm --follow
```

**Fase 1 — Descarga del modelo** (~5-30 minutos en la primera ejecución, ~15 GB para gemma-4-E4B-it):

```
Starting to load model google/gemma-4-E4B-it...
Loading safetensors checkpoint shards: 100%   ← descarga completa
```

**Fase 2 — Compilación del grafo CUDA** (~3-5 minutos, se ejecuta una sola vez y queda en caché):

```
Dynamo bytecode transform time: XX s
Graph capturing finished in XX secs
Application startup complete.                 ← LISTO
```

#### Advertencias esperadas durante el arranque (todas son cosméticas)

```
UserWarning: Found GPU0 Orin which is of compute capability (CC) 8.7.
- 8.0 which supports hardware CC >=8.0,<9.0 except {8.7}
```

Esta advertencia aparece porque PyTorch dentro del contenedor fue compilado para CC 8.0/9.0/10.0 pero excluye explícitamente 8.7 (la arquitectura del Jetson Orin). vLLM recurre a la compilación PTX JIT, que funciona correctamente —la inferencia se ejecuta con normalidad. El primer arranque tarda un poco más mientras se compila PTX; los reinicios posteriores son más rápidos.

```
Unknown vLLM environment variable: VLLM_BUILD_COMMIT / VLLM_BUILD_PIPELINE
```

Metadatos internos del contenedor. Inofensivos.

### 12.3.4 Verificar y probar vLLM

```bash
# Verificar que la API responde
curl http://localhost:8000/health
```

Salida esperada:

```
{"status":"ok"}
```

```bash
# Listar modelos cargados
curl http://localhost:8000/v1/models | python3 -m json.tool

# Chat completion básico
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [
      {"role": "user", "content": "Explica edge AI en 3 puntos breves."}
    ],
    "max_tokens": 200
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(r['choices'][0]['message']['content'])
print(f\"Tokens: {r['usage']['completion_tokens']}\")
"

# Salida estructurada JSON
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E4B-it",
    "messages": [{"role": "user", "content": "Lista 3 casos de uso de IA como JSON"}],
    "response_format": {"type": "json_object"},
    "max_tokens": 300
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(r['choices'][0]['message']['content'])
"
```

Desde **Windows PowerShell**:

```powershell
$body = @{
    model    = "google/gemma-4-E4B-it"
    messages = @(@{role="user"; content="Hola desde Windows via vLLM en JP 7.2!"})
    max_tokens = 100
} | ConvertTo-Json -Depth 3

Invoke-RestMethod `
    -Uri "http://192.168.1.100:8000/v1/chat/completions" `
    -Method Post -ContentType "application/json" -Body $body |
    Select-Object -ExpandProperty choices |
    ForEach-Object { $_.message.content }
```

### 12.3.5 vLLM con modelos de tool calling (requerido para OpenClaw)

OpenClaw requiere soporte nativo de *tool calling*. Qwen3 tiene mejor rendimiento que Gemma 4 E4B para flujos de trabajo agénticos:

```bash
# Parar la instancia actual
docker stop vllm && docker rm vllm

# Descargar el modelo
source ~/venvs/llm/bin/activate
hf download Qwen/Qwen3-8B \
  --local-dir ~/jetson-ai-data/models/hf/Qwen3-8B

# Lanzar vLLM con tool calling habilitado
docker run --runtime nvidia -d \
  --name vllm \
  --network host \
  --ipc host \
  --shm-size 8g \
  --restart no \
  -e HF_TOKEN=$HF_TOKEN \
  -v ~/jetson-ai-data/models/hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
  Qwen/Qwen3-8B \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.75 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

Probar tool calling:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-8B",
    "messages": [{"role": "user", "content": "¿Cuánto es 42 × 17? Usa la calculadora."}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "calculadora",
        "description": "Realiza cálculos aritméticos",
        "parameters": {
          "type": "object",
          "properties": {
            "expresion": {"type": "string", "description": "Expresión matemática"}
          },
          "required": ["expresion"]
        }
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 200
  }' | python3 -m json.tool
```

En la respuesta busque: `"tool_calls": [{"function": {"name": "calculadora", ...}}]`

```bash
# Abrir firewall
sudo ufw allow 8000/tcp comment "vLLM API"
```

### 12.3.6 vLLM como servicio systemd

Un **servicio systemd** es un proceso gestionado por el sistema operativo que puede configurarse para iniciarse automáticamente al arrancar el Jetson, sin intervención del usuario. `systemd` es el gestor de servicios de Ubuntu 24.04 — el mismo sistema que controla Docker, SSH y el servidor de NoMachine.

Convertir vLLM en un servicio systemd significa que cada vez que el Jetson se encienda (o reinicie), vLLM arrancará solo y estará listo antes de que inicie sesión.

> **ADVERTENCIA — Cuándo activar (y cuándo NO) el inicio automático:**
>
> Habilitar `vllm-container.service` con `systemctl enable` tiene una consecuencia directa: vLLM **reservará 10–15 GB de RAM unificada en el arranque**, antes de que usted abra cualquier aplicación.
>
> **Active el inicio automático solo si:**
> - El Jetson está dedicado exclusivamente a servir vLLM (servidor de producción 24/7)
> - No ejecuta otros modelos LLM en paralelo (Ollama, llama.cpp)
> - Tiene scripts de monitoreo de memoria activos (ver Capítulo 15)
>
> **No active el inicio automático si:**
> - Usa el Jetson para múltiples proyectos (benchmarking, TTS, Computer Vision, etc.)
> - Tiene otros contenedores que también consumen VRAM (Open WebUI, Whisper, etc.)
> - Experimenta con diferentes modelos — en ese caso, use el alias `vllm-start` del Capítulo 15 para lanzar vLLM bajo demanda
>
> La guía en este capítulo **no habilita** el inicio automático. El `systemctl enable` queda comentado intencionalmente.

```bash
# Crear archivo de variables de entorno (seguro: solo legible por root)
sudo tee /etc/vllm.env << EOF
HF_TOKEN=$(cat ~/.cache/huggingface/token)
EOF
sudo chmod 600 /etc/vllm.env

# Crear servicio systemd
sudo tee /etc/systemd/system/vllm-container.service << 'EOF'
[Unit]
Description=vLLM Production Inference Server — Jetson AGX Orin JP 7.2
After=docker.service network.target
Requires=docker.service

[Service]
Type=simple
User=jetson
EnvironmentFile=/etc/vllm.env
Restart=on-failure
RestartSec=30
TimeoutStartSec=600
ExecStartPre=-/usr/bin/docker rm -f vllm
ExecStart=/usr/bin/docker run --runtime nvidia \
  --name vllm \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e HF_TOKEN=${HF_TOKEN} \
  -v /home/jetson/jetson-ai-data/models/hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.22.0-ubuntu2404 \
  google/gemma-4-E4B-it \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.70
ExecStop=/usr/bin/docker stop vllm
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
# NO habilitar por defecto — ver Capitulo 15 sobre gestion de recursos
# sudo systemctl enable vllm-container  # solo si lo desea en produccion 24/7
```

---

## 12.4 Modos de Backend y Selección de Motor

> **NOTA:** Los modos de producción avanzados (cambio automático entre backends, switch-model.sh, contenedores NVIDIA-AI-IOT optimizados) se tratan en detalle en el **Capítulo 12 — OpenClaw**, donde se integran con el stack agéntico completo. Esta sección cubre la selección básica de motor para uso cotidiano.

### Guía rápida de selección de motor

```
?Que necesito hacer?
|
+-- Chat general, RAG, pruebas rapidas
|   -> Ollama (puerto 11434)
|   | Mas facil de instalar y gestionar, ideal para explorar modelos
|
+-- Modelos cuantizados GGUF (7B-70B), bajo uso de RAM
|   -> llama.cpp (puerto 8080)
|   | Compilado desde fuente, mejor rendimiento para GGUF, tool calling basico
|
+-- Produccion, tool calling avanzado, JSON estructurado
    -> vLLM (puerto 8000)
      Mas lento arrancando (~3 min), pero mejor calidad de salida y JSON schema
```

> **CONSEJO:** Ejecute solo un motor a la vez. Los tres comparten los 64 GB de RAM unificada del Jetson. Antes de cambiar de motor, use `stop-ollama`, `stop-llama` o `stop-vllm` para liberar la memoria.

---

## 12.6 Open WebUI — Interfaz de Chat para Todos los Motores

Open WebUI proporciona una interfaz web similar a ChatGPT que funciona con cualquier motor de inferencia compatible con la API de OpenAI. Se ejecuta en un contenedor Docker liviano y es accesible desde el navegador de Windows — sin instalar nada adicional en Windows.

> **IMPORTANTE:** Open WebUI usa el puerto **3000** en el host del Jetson. El contenedor internamente corre en el 8080, pero se mapea al 3000 para no conflictuar con llama.cpp (también en 8080). Ambos pueden coexistir.

### 12.6.1 Instalación

```bash
# Verificar que Docker esta activo
docker info | grep "Server Version" || docker-on

# Instalar Open WebUI
# --restart no = filosofia clean-start (no arranca con el sistema)
# --network host = acceso directo a los motores locales
docker run -d \
  --name open-webui \
  --restart no \
  --network host \
  -p 3000:8080 \
  -v open-webui-data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -e WEBUI_SECRET_KEY=$(openssl rand -hex 32) \
  ghcr.io/open-webui/open-webui:main

sudo ufw allow 3000/tcp comment "Open WebUI"
```

```bash
# Monitorear el primer arranque (~90 segundos):
docker logs -f open-webui 2>&1 | grep -E "started|error|Running"
# Salida esperada al finalizar:
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)

# Verificar que responde:
until curl -s http://localhost:3000 > /dev/null 2>&1; do
  sleep 5; echo -n "."
done
echo " [OK] Open WebUI disponible en http://192.168.1.100:3000"
```

### 12.6.2 Primer acceso y configuracion inicial

Acceda desde Windows: `http://192.168.1.100:3000`

**Primera vez:**
1. Clic en **Sign up** (no en Sign in) → crear cuenta de administrador
2. Use un email y contraseña — quedan guardados localmente en el Jetson
3. En la pantalla principal, seleccione el modelo del dropdown superior

**Para acceder via SSH tunnel desde Windows** (sin exponer el puerto 3000 en la red):

```bash
# [WINDOWS POWERSHELL]
ssh -L 3000:localhost:3000 jetson -N
# Abrir en el navegador: http://localhost:3000
```

### 12.6.3 Aliases para arranque y parada bajo demanda

```bash
# Agregar a ~/.bash_aliases en el Jetson
# -------------------------------------------------
# Open WebUI

alias start-webui='docker start open-webui && \
  echo "Iniciando Open WebUI..." && \
  sleep 3 && \
  docker logs --tail 5 open-webui 2>&1 | grep -E "started|Running|error" && \
  echo "[OK] Open WebUI en http://192.168.1.100:3000"'

alias stop-webui='docker stop open-webui && \
  echo "[OK] Open WebUI detenido (RAM liberada)"'

alias webui-status='docker inspect open-webui --format="Estado: {{.State.Status}}" 2>/dev/null || echo "[WARN] Open WebUI no instalado"'

alias webui-logs='docker logs -f open-webui'
```

```bash
source ~/.bash_aliases || source ~/.bashrc

# Uso normal:
start-webui    # Iniciar
webui-status   # Ver estado
webui-logs     # Ver logs en tiempo real (Ctrl+C para salir)
stop-webui     # Detener y liberar memoria
```

### 12.6.4 Cambiar de motor de inferencia

Open WebUI puede apuntar a cualquier motor activo sin reinstalarse.

**Forma 1 — Panel de administracion** (recomendado para cambios permanentes):

1. Acceder a Open WebUI como admin → icono de perfil → **Admin Panel**
2. Ir a **Settings → Connections**
3. En la seccion **Ollama**: la URL base por defecto es `http://localhost:11434`
4. Para agregar vLLM o llama.cpp como proveedor adicional:
   - Clic en el `+` junto a **OpenAI API**
   - URL: `http://localhost:8000/v1` (vLLM) o `http://localhost:8080/v1` (llama.cpp)
   - API Key: `vllm-local` (cualquier string no vacio)
   - Guardar → los modelos aparecen en el dropdown

**Forma 2 — Variable de entorno** (para cambiar el backend por defecto al relanzar):

```bash
# Detener Open WebUI
stop-webui

# Relanzar apuntando a vLLM como proveedor OpenAI
docker run -d \
  --name open-webui \
  --restart no \
  --network host \
  -p 3000:8080 \
  -v open-webui-data:/app/backend/data \
  -e OPENAI_API_BASE_URL=http://localhost:8000/v1 \
  -e OPENAI_API_KEY=vllm-local \
  ghcr.io/open-webui/open-webui:main

docker logs -f open-webui | grep -E "started|Running"
```

### 12.6.5 Casos de uso principales

| Caso de uso | Motor recomendado | Configuracion |
|-------------|-------------------|---------------|
| Chat general, preguntas rapidas | Ollama (qwen3:8b) | URL Ollama por defecto |
| Documentos largos (256K+ ctx) | vLLM (Nemotron3 30B) | OpenAI API localhost:8000 |
| Bajo consumo, uso nocturno | llama.cpp (Gemma 4 E2B GGUF) | OpenAI API localhost:8080 |
| Carga de PDFs e imagenes | Ollama (gemma4) + panel integrado | Funcion nativa |
| RAG sobre documentos propios | Ollama + nomic-embed-text | Ver Capitulo 25 |

### 12.6.6 Monitoreo durante uso

```bash
# Ver conversaciones activas y errores
docker logs -f open-webui --tail 20

# Ver uso de recursos del contenedor
docker stats open-webui --no-stream

# Ver cuanto espacio usa la base de datos de conversaciones
docker system df -v | grep open-webui-data
```

### 12.6.7 SSL para Open WebUI (microfono en el navegador)

Los navegadores modernos (Chrome, Edge) solo permiten acceso al microfono en conexiones HTTPS. Para habilitar entrada de voz en Open WebUI, necesita un certificado SSL local. El procedimiento completo se trata en el **Capitulo 14 — Open WebUI SSL + Proyecto Nemotron**.

### 12.6.8 Pipelines — Integracion avanzada

Open WebUI soporta "pipelines" — funciones Python que procesan las peticiones antes y despues del LLM:

```bash
# Iniciar servidor de pipelines (solo cuando lo necesite)
docker run -d \
  --name pipelines-server \
  --restart no \
  --network host \
  -v ~/stacks/pipelines:/app/pipelines \
  ghcr.io/open-webui/pipelines:main

docker logs -f pipelines-server | grep -E "started|error"

# En Open WebUI: Settings -> Connections -> Pipeline -> http://localhost:9099
```

> **NOTA:** Los pipelines y el enrutado de modelos avanzado se tratan en profundidad en el **Capitulo 12 — OpenClaw**, donde se integran con el bot de Telegram.


---

## Resumen: Los tres motores de inferencia verificados

| Motor | Puerto | RAM tipica | Tok/s | Mejor para |
|-------|--------|------------|-------|------------|
| **Ollama** | 11434 | 3–20 GB | 25–45 | Chat, RAG, exploración, embeddings |
| **llama.cpp** | 8080 | 3–24 GB | 35–45 | GGUF cuantizados, bajo consumo, arranque rapido |
| **vLLM** | 8000 | 15–30 GB | 32–38 | Producción, tool calling, JSON estructurado |
| **Open WebUI** | 3000 | ~200 MB | — | Interfaz de usuario para todos los motores |

> **IMPORTANTE — un motor a la vez:** Los tres motores comparten los 64 GB de RAM unificada. Antes de iniciar un motor, detenga el anterior con `stop-ollama`, `stop-llama` o `stop-vllm`.

## ¿Qué sigue?

En el **Capitulo siguiente** instalará OpenClaw — el gateway de agentes que transforma el Jetson en un asistente de IA accesible desde Telegram, con soporte para tool calling, búsqueda web y cambio dinámico de modelos.

---

*Capítulo 12 de 16 — Getting Started with NVIDIA Jetson AGX Orin 64GB (JetPack 7.2)*
* Ubuntu 24.04.4 · CUDA 13.2.1 · L4T r39.2 · Python 3.12.3*
