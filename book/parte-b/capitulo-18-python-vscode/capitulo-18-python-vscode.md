# Capítulo 17 — Entorno de Desarrollo Python con VSCode Remote SSH

## Introducción

Los capítulos de la Fase 1 convirtieron el Jetson en un servidor de inferencia de clase enterprise. Esta primera parte de la Fase 2 da un paso diferente: configurar el Jetson como un entorno de desarrollo Python remoto al que se accede cómodamente desde Windows o macOS usando Visual Studio Code con la extensión Remote SSH.

Con esta configuración, el Jetson es el servidor donde se ejecuta el código — con su GPU de 275 TOPS, sus 64 GB de RAM unificada y todos los modelos instalados — mientras que su computadora actúa como interfaz gráfica. Puede editar código, depurar, ver gráficas y ejecutar notebooks Jupyter, todo con la apariencia de un entorno local pero el poder del Jetson.

> **NOTA:** Este capítulo integra el entorno de desarrollo Python con PyTorch y los frameworks de IA. Al ubicarlo aquí, el lector tiene todos los motores de inferencia instalados (Capítulo 12) y puede experimentar con ellos directamente desde Python, lo que hace los ejemplos mucho más prácticos e inmediatos.

**Prerequisitos:**
- Capítulo 7 completada (SSH + IP estática)
- Capítulo 8 completada (Docker + NVIDIA NCT)
- Al menos un motor de inferencia activo (Capítulo 12/14)
- VSCode instalado en su computadora

**Tiempo estimado de configuración:** 30–45 minutos

**Al final de este capítulo podrá:**
- Desarrollar Python en el Jetson desde VSCode en su PC
- Ejecutar notebooks Jupyter en el Jetson y verlos en su browser
- Instalar PyTorch con soporte CUDA 13.2.1 para JP 7.2
- Llamar a los modelos LLM desde Python (Ollama, vLLM, llama.cpp)
- Aplicar patrones de limpieza de memoria entre experimentos

---

## 17.1 Configurar VSCode Remote SSH

> **NOTA — Capítulo previo:** Si configuró el acceso remoto SSH en el Capítulo 7, ya tiene una conexión SSH funcional al Jetson y su clave pública instalada. En ese caso, puede saltarse la sección 17.1.2 (ya tiene el archivo `~/.ssh/config` creado) e ir directamente a la sección 17.1.3 para conectar VSCode. Si se saltó el Capítulo 7, siga todos los pasos de esta sección.

### 17.1.1 Instalar la Extensión Remote SSH en VSCode

En su computadora (Windows/macOS/Linux):

1. Abra **Visual Studio Code**
2. Vaya a **Extensions** (`Ctrl+Shift+X` / `Cmd+Shift+X`)
3. Busque `Remote - SSH` (publicada por Microsoft)
4. Haga clic en **Install**

También instale las extensiones complementarias:
- **Remote - SSH: Editing Configuration Files** (misma colección de Microsoft)
- **Python** (Microsoft) — se instalará automáticamente en el Jetson cuando conecte

### 17.1.2 Configurar el Archivo SSH Config

**En Windows (PowerShell o Notepad):** Edite `C:\Users\<SuUsuario>\.ssh\config`

**En macOS/Linux (terminal):** Edite `~/.ssh/config`

```
# Configuración SSH para el Jetson
Host jetson
    HostName 192.168.1.100
    User jetson
    IdentityFile ~/.ssh/id_jetson
    ServerAliveInterval 60
    ServerAliveCountMax 5
    ForwardAgent yes
```

> Reemplace `192.168.1.100` con la IP estática del Jetson configurada en el Capítulo 7.

### 17.1.3 Conectar VSCode al Jetson

1. En VSCode, pulse `F1` (o `Ctrl+Shift+P`) para abrir el Command Palette
2. Escriba **Remote-SSH: Connect to Host...**
3. Seleccione `jetson` (aparece gracias al archivo config)
4. Se abre una nueva ventana de VSCode conectada al Jetson
5. En la esquina inferior izquierda verá: **SSH: jetson**

La primera conexión tarda ~1 minuto mientras VSCode instala su servidor en el Jetson. Las siguientes conexiones son inmediatas.

### 17.1.4 Instalar Extensiones Python en el Jetson (desde VSCode)

Con la ventana de VSCode conectada al Jetson:

1. Abra **Extensions** (`Ctrl+Shift+X`)
2. Busque e instale en el Jetson (no en su PC):
   - **Python** (Microsoft)
   - **Jupyter** (Microsoft)
   - **Pylance** (Microsoft)

Estas extensiones se instalan en el Jetson y se ejecutan allí. Su PC solo muestra la interfaz.

---

## 17.2 Crear el Entorno Virtual de Desarrollo

> **NOTA — Capítulo previo:** En el Capítulo 5 (Entorno de Shell) se creó el venv `~/venvs/llm` para los motores de inferencia. En este capítulo crearemos un venv separado `~/venvs/dev` dedicado al desarrollo Python — más limpio que instalar librerías de desarrollo en el mismo venv que los motores. Si ya creó el entorno `dev` en algún capítulo anterior, verifique con `ls ~/venvs/` y omita la creación.

### 17.2.1 Entorno Virtual para Desarrollo Python

Abra un terminal integrado en VSCode (`Ctrl+Ñ` o `Ctrl+` ` `): verá una terminal que se ejecuta directamente en el Jetson.

```bash
# Crear el entorno virtual de desarrollo
python3.12 -m venv ~/venvs/dev

# Activar
source ~/venvs/dev/bin/activate

# Verificar Python
python --version
```

```
# Salida esperada
Python 3.12.3
```

```bash
# Instalar dependencias básicas de desarrollo
pip install --upgrade pip wheel setuptools
pip install ipykernel notebook jupyterlab rich requests httpx
```

### 17.2.2 Seleccionar el Intérprete Python en VSCode

1. Pulse `F1` → **Python: Select Interpreter**
2. Seleccione: **Enter interpreter path...**
3. Escriba: `/home/jetson/venvs/dev/bin/python`
4. VSCode ahora usará este entorno por defecto para IntelliSense, debugging y ejecución

---

## 17.3 PyTorch con CUDA 13.2.1 para JetPack 7.2

> **NOTA — Conceptos clave para principiantes:**
>
> - **PyTorch:** La librería de aprendizaje profundo (deep learning) más usada en investigación y producción. Es el "motor" que ejecuta los modelos de IA como redes neuronales. Con PyTorch puede entrenar modelos, hacer inferencia, manipular datos multidimensionales, y mucho más.
>
> - **CUDA:** La interfaz de programación paralela de NVIDIA que permite usar la GPU (no la CPU) para cálculos matemáticos. Sin CUDA, PyTorch usa solo la CPU y es entre 5× y 100× más lento dependiendo de la operación.
>
> - **Wheel file (`.whl`):** Un archivo de instalación precompilado para Python — como un instalador `.exe` de Windows pero para paquetes Python. Los wheels son específicos para la arquitectura del procesador (x86_64 para PC, arm64 para Jetson) y la versión de CUDA. No puede usar un wheel de x86_64 en el Jetson ARM64.
>
> - **`cp312`:** En el nombre del wheel (`torch-2.x.x-cp312-cp312-linux_aarch64.whl`), `cp312` indica que fue compilado para **CPython 3.12** — la versión de Python del Jetson con JP 7.2. Si intenta instalar un wheel `cp310` (Python 3.10), `pip` lo rechazará automáticamente.
>
> - **Tensores CUDA:** En PyTorch, un "tensor" es un arreglo multidimensional (similar a un NumPy array). Un tensor CUDA es un tensor que vive en la memoria de la GPU. Las operaciones entre tensores CUDA se ejecutan en paralelo con miles de CUDA cores — lo que hace la GPU tan rápida para IA.

PyTorch en el Jetson no se instala con el pip normal — el wheel genérico de PyPI está compilado para x86_64. NVIDIA proporciona wheels específicos para JP 7.2.

### 17.3.1 Instalar PyTorch para JP 7.2

```bash
# Activar el venv de desarrollo
source ~/venvs/dev/bin/activate

# Instalar PyTorch desde el índice de paquetes de NVIDIA para Jetson
# (wheel ARM64 + CUDA 13.2.1, compilado para sm_87 = Orin Ampere)
pip install torch torchvision torchaudio \
  --index-url https://pypi.jetson-ai-lab.io/sbsa/cu129

# Alternativamente, desde el repositorio JP 7.2 de NVIDIA:
# pip install torch --index-url https://developer.download.nvidia.com/compute/redist/jp/v72/pytorch/
```

> **NOTA:** El índice `pypi.jetson-ai-lab.io` puede estar sujeto a cambios. Si falla, busque "JetPack 7.2 PyTorch wheel" en la documentación oficial de NVIDIA Jetson AI Lab. La variable CUDA correcta para JP 7.2 es `cu129` (CUDA 12.9/13.x en la nomenclatura de pip).

```bash
# Verificar PyTorch + CUDA
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA disponible: {torch.cuda.is_available()}')
print(f'Dispositivo: {torch.cuda.get_device_name(0)}')
print(f'Memoria GPU total: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"
```

```
# Salida esperada
PyTorch: 2.x.x+cu129
CUDA disponible: True
Dispositivo: Orin (nvgpu)
Memoria GPU total: 64.0 GB
```

### 17.3.2 Prueba de Tensor CUDA

```python
# test_cuda.py
import torch

# Crear tensores en GPU
a = torch.randn(1000, 1000).cuda()
b = torch.randn(1000, 1000).cuda()

# Operación en GPU
c = torch.matmul(a, b)

print(f"Tensor en GPU: {c.device}")
print(f"Forma del resultado: {c.shape}")
print(f"Suma: {c.sum().item():.2f}")
print("[OK] PyTorch + CUDA funcionando correctamente")
```

```bash
# Ejecutar desde el terminal del Jetson (o con el botón Run en VSCode)
python test_cuda.py
```

```
# Salida esperada
Tensor en GPU: cuda:0
Forma del resultado: torch.Size([1000, 1000])
Suma: 312.45   ← este valor varía con cada ejecución (números aleatorios)
[OK] PyTorch + CUDA funcionando correctamente
```

> **¿Qué está pasando en este test?**
>
> Se crean dos matrices de 1000×1000 elementos aleatorios directamente en la GPU (`torch.randn(...).cuda()`). Luego se multiplican (`torch.matmul`) — una operación de 1 billón de multiplicaciones/sumas que la CPU tardaría ~5 segundos pero la GPU del Jetson resuelve en milisegundos gracias a sus 2048 CUDA cores trabajando en paralelo. El resultado es otro tensor 1000×1000 en GPU. La "Suma" es simplemente la suma de todos los elementos, que varía porque los números de entrada son aleatorios.

---

## 17.4 Jupyter Notebooks en el Jetson

Jupyter Notebooks permiten combinar código Python, texto, gráficas y outputs en un solo documento interactivo. Con VSCode Remote SSH puede abrir notebooks en el browser de su PC mientras el código se ejecuta en el Jetson.

### 17.4.1 Iniciar JupyterLab

```bash
# En el terminal del Jetson (via VSCode)
source ~/venvs/dev/bin/activate
jupyter lab --no-browser --ip=0.0.0.0 --port=8888 \
  --NotebookApp.token='jetson2024'
```

```
# Salida esperada
[I 2026-06-28 10:00:00.000 ServerApp] Jupyter Server 2.x.x is running at:
[I 2026-06-28 10:00:00.000 ServerApp] http://192.168.1.100:8888/lab?token=jetson2024
[I 2026-06-28 10:00:00.000 ServerApp]     http://127.0.0.1:8888/lab?token=jetson2024
```

Abra en el browser de su PC: `http://192.168.1.100:8888/lab?token=jetson2024`

Verá la interfaz de JupyterLab. El código que ejecute allí corre en el Jetson.

### 17.4.2 Notebooks desde VSCode

VSCode con la extensión Jupyter puede abrir archivos `.ipynb` directamente:

1. En VSCode Remote (conectado al Jetson), cree un nuevo archivo `experimento.ipynb`
2. Seleccione el kernel: **Python 3 (~/venvs/dev)** o el que creó
3. Ejecute celdas normalmente con `Shift+Enter`

El código corre en el Jetson pero la interfaz aparece en su PC.

---

## 17.5 Experimento 1 — Llamar a Ollama desde Python

Este experimento conecta Python con el servidor Ollama local (instalado en el Capítulo 12) usando la API compatible con OpenAI.

### 17.5.1 Prerrequisitos de Memoria

Antes de iniciar este experimento, verifique el estado del sistema:

```bash
# En terminal del Jetson
free -h | awk '/^Mem:/{printf "RAM: %s usados de %s, %s libres\n", $3, $2, $7}'
motors-status   # alias de Capítulo 15
```

Si Ollama no está activo, inícielo:

```bash
ollama-start    # alias de Capítulo 12, o:
sudo systemctl start ollama
```

### 17.5.2 Cliente Python con SDK de OpenAI

```bash
# Instalar el SDK de OpenAI (compatible con Ollama, vLLM y llama.cpp)
pip install openai
```

```python
# experimento_1_ollama.py
from openai import OpenAI

# Ollama expone una API compatible con OpenAI en el puerto 11434
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Ollama no requiere clave real
)

# Listar modelos disponibles
modelos = client.models.list()
print("Modelos Ollama disponibles:")
for m in modelos.data:
    print(f"  - {m.id}")

# Generar una respuesta
respuesta = client.chat.completions.create(
    model="qwen3:7b",  # usar un modelo instalado en la Capítulo 12
    messages=[
        {"role": "system", "content": "Eres un experto en IA y computación embebida."},
        {"role": "user", "content": "¿Qué ventajas tiene la memoria unificada del Jetson para la inferencia de LLMs?"}
    ],
    max_tokens=300
)

print("\n── Respuesta ──")
print(respuesta.choices[0].message.content)
print(f"\n── Tokens ──")
print(f"  Prompt: {respuesta.usage.prompt_tokens}")
print(f"  Completion: {respuesta.usage.completion_tokens}")
print(f"  Total: {respuesta.usage.total_tokens}")
```

```
# Salida esperada
Modelos Ollama disponibles:
  - qwen3:7b
  - deepseek-r1:7b
  - ...

── Respuesta ──
La memoria unificada del Jetson AGX Orin ofrece varias ventajas clave para la inferencia de LLMs:

1. **Sin cuello de botella PCIe**: En una GPU discreta, los datos deben transferirse entre la RAM del sistema y la VRAM de la GPU a través del bus PCIe, lo que limita el ancho de banda...

── Tokens ──
  Prompt: 45
  Completion: 287
  Total: 332
```

### 17.5.3 Streaming de Tokens en Tiempo Real

```python
# experimento_1b_streaming.py
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

print("Respuesta en streaming (token por token):\n")

# stream=True activa el modo streaming
stream = client.chat.completions.create(
    model="qwen3:7b",
    messages=[{"role": "user", "content": "Explica qué es CUDA en 3 oraciones."}],
    max_tokens=150,
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)

print("\n\n[OK] Streaming completado")
```

---

## 17.6 Experimento 2 — Llamar a vLLM desde Python

vLLM expone exactamente la misma API que OpenAI, con el mismo SDK. Solo cambia el `base_url` y el nombre del modelo.

### 17.6.1 Prerrequisitos de Memoria

```bash
# Lanzar vLLM si no está activo (alias de Capítulo 15)
start-qwen35    # lanza el modelo 35B de Capítulo 14
# o start-qwen4b para el modelo de 4B (más rápido, usa menos RAM)
```

### 17.6.2 Cliente Python para vLLM

```python
# experimento_2_vllm.py
from openai import OpenAI
import time

# vLLM en el puerto 8000 — misma API que OpenAI
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # vLLM no requiere clave por defecto
)

# Verificar qué modelo está activo
modelos = client.models.list()
modelo_activo = modelos.data[0].id
print(f"Modelo activo en vLLM: {modelo_activo}")

# Benchmark: medir tokens por segundo
inicio = time.time()

respuesta = client.chat.completions.create(
    model=modelo_activo,
    messages=[
        {"role": "user", "content": "Escribe un análisis de 200 palabras sobre las ventajas del edge computing."}
    ],
    max_tokens=300
)

duracion = time.time() - inicio
tokens_salida = respuesta.usage.completion_tokens
tps = tokens_salida / duracion

print(f"\n── Rendimiento ──")
print(f"  Tokens generados: {tokens_salida}")
print(f"  Tiempo total: {duracion:.2f} seg")
print(f"  Velocidad: {tps:.1f} tok/s")
print(f"\n── Respuesta ──")
print(respuesta.choices[0].message.content)
```

### 17.6.3 Comparar Velocidad entre Motores

```python
# experimento_2b_benchmark.py
from openai import OpenAI
import time

PREGUNTA = "¿Qué es un transformer en el contexto de inteligencia artificial? Responde en 2 oraciones."
MAX_TOKENS = 100

def medir_velocidad(nombre, url, modelo, api_key="no-key"):
    try:
        client = OpenAI(base_url=url, api_key=api_key)
        inicio = time.time()
        r = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": PREGUNTA}],
            max_tokens=MAX_TOKENS
        )
        dt = time.time() - inicio
        tps = r.usage.completion_tokens / dt
        return f"  [OK] {nombre}: {tps:.1f} tok/s ({r.usage.completion_tokens} tokens en {dt:.1f}s)"
    except Exception as e:
        return f"  [WARN]  {nombre}: no disponible ({str(e)[:50]})"

print("═══ Benchmark de motores de inferencia ═══")
# Ajuste los nombres de modelos según los que tenga instalados
print(medir_velocidad("Ollama qwen3:7b", "http://localhost:11434/v1", "qwen3:7b", "ollama"))
print(medir_velocidad("vLLM qwen35",     "http://localhost:8000/v1",  "qwen35"))
print(medir_velocidad("llama.cpp",        "http://localhost:8080/v1",  "nemotron-omni"))
print("═══════════════════════════════════════════")
```

---

## 17.7 Experimento 3 — Hugging Face Transformers Directo (sin contenedor)

Para modelos pequeños (≤3B parámetros), puede cargarlos directamente en Python usando la librería `transformers` de Hugging Face, sin necesidad de contenedores ni servidores HTTP.

### 17.7.1 Instalar Transformers

```bash
# En el venv de desarrollo
pip install transformers accelerate sentencepiece
```

### 17.7.2 Cargar un Modelo Pequeño Directamente

```python
# experimento_3_transformers.py
import torch
from transformers import pipeline

print(f"CUDA disponible: {torch.cuda.is_available()}")
print(f"Cargando modelo... (primera vez descarga ~1-2 GB)")

# Cargar un modelo pequeño directamente en GPU
# phi-2 es un buen ejemplo: 2.7B parámetros, ~5GB con float16
pipe = pipeline(
    "text-generation",
    model="microsoft/phi-2",
    device=0,              # GPU 0 (la GPU del Jetson)
    torch_dtype=torch.float16  # float16 reduce a la mitad el uso de RAM
)

print("[OK] Modelo cargado\n")

# Generar respuesta
resultado = pipe(
    "Explain what a neural network is in simple terms:",
    max_new_tokens=100,
    do_sample=False
)

print(resultado[0]["generated_text"])
```

### 17.7.3 Limpieza de Memoria tras el Experimento

```python
# Siempre liberar memoria GPU después de terminar con un modelo directo
import gc
import torch

# Eliminar el pipeline y el modelo de la GPU
del pipe
gc.collect()
torch.cuda.empty_cache()

# Verificar liberación
print(f"Memoria GPU reservada: {torch.cuda.memory_reserved(0) / 1e9:.2f} GB")
print(f"Memoria GPU asignada: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")
print("[OK] Memoria GPU liberada")
```

```
# Salida esperada
Memoria GPU reservada: 0.00 GB
Memoria GPU asignada: 0.00 GB
[OK] Memoria GPU liberada
```

> **IMPORTANTE:** Si no ejecuta la limpieza y luego intenta arrancar un contenedor vLLM o llama.cpp, el modelo Hugging Face sigue ocupando RAM en la GPU y puede causar OOM. Siempre limpie antes de cambiar de motor.

---

## 17.8 Patrón de Desarrollo Recomendado

<!-- INFOGRAFÍA: Patrón de Desarrollo en Jetson AGX Orin — diagrama circular/cíclico de 5 pasos: 1. Verificar estado (motors-status / free -h) → 2. Lanzar motor (start-qwen35 / ollama / vllm) → 3. Desarrollar/Experimentar (VSCode + Jupyter + Python) → 4. Terminar y Limpiar (kill model / gc.collect()) → 5. Verificar memoria libre → vuelve al paso 1. Paleta NVIDIA #0F3D3D / #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light — pendiente de diseño gráfico -->

El flujo de trabajo eficiente para desarrollar con LLMs en el Jetson sigue este ciclo:

```
┌──────────────────────────────────────────────────────────────┐
│  CICLO DE DESARROLLO EN JETSON (desde VSCode Remote SSH)     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Verificar estado inicial                                  │
│     motors-status / check-ready / free -h                   │
│                                                              │
│  2. Lanzar motor necesario                                   │
│     start-qwen35 / start-nemotron / sudo systemctl start ollama │
│                                                              │
│  3. Desarrollar y experimentar                               │
│     (VSCode + notebook Jupyter + Python scripts)             │
│                                                              │
│  4. Terminar experimento y limpiar                           │
│     kill-qwen35 / del modelo; gc.collect(); empty_cache()   │
│                                                              │
│  5. Verificar que la memoria quedó libre                     │
│     free -h / motors-status                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 17.8.1 Script de Verificación Pre-Experimento

```python
# utils/pre_check.py — ejecutar al inicio de cada notebook
import subprocess
import psutil

def check_system():
    """Verifica que el sistema está listo para experimentar."""
    mem = psutil.virtual_memory()
    libres_gb = mem.available / 1e9
    total_gb = mem.total / 1e9
    uso_pct = mem.percent
    
    print(f"═══ Estado del Sistema ═══")
    print(f"RAM: {libres_gb:.1f} GB libres de {total_gb:.1f} GB ({uso_pct:.0f}% usado)")
    
    if libres_gb < 20:
        print("[WARN]  Menos de 20 GB libres — considere ejecutar jetson-clean antes")
    else:
        print(f"[OK] Sistema listo ({libres_gb:.0f} GB disponibles)")
    
    # Verificar endpoints activos
    import requests
    endpoints = [
        ("Ollama", "http://localhost:11434/api/version"),
        ("vLLM", "http://localhost:8000/v1/models"),
        ("llama.cpp", "http://localhost:8080/v1/models"),
    ]
    print("\n─── Motores activos ───")
    for nombre, url in endpoints:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"  [OK] {nombre}")
        except:
            print(f"  ○  {nombre} → offline")
    print("══════════════════════════")

check_system()
```

```bash
# Instalar psutil
pip install psutil
```

---

## 17.9 Limpieza Post-Experimento

```bash
# Limpieza completa después de una sesión de desarrollo
# Ejecutar en el terminal del Jetson (no en Python)

# 1. Detener motores activos
kill-qwen35 2>/dev/null || true
kill-nemotron 2>/dev/null || true
kill-qwen4b 2>/dev/null || true
sudo systemctl stop ollama 2>/dev/null || true

# 2. Limpiar caché del sistema
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# 3. Verificar estado final
echo "Estado post-limpieza:"
free -h | awk '/^Mem:/{printf "RAM: %s usados de %s, %s libres\n", $3, $2, $7}'
motors-status

# 4. Bajar a modo bajo consumo
pwr-15w
```

---

## 17.10 Verificación Final del Capítulo

```bash
# Verificación de configuración de desarrollo
echo "╔══════════════════════════════════════════════════════╗"
echo "║    VERIFICACIÓN CAPÍTULO 17 — ENTORNO DE DESARROLLO    ║"
echo "╚══════════════════════════════════════════════════════╝"

echo ""
echo "── Entorno virtual ──"
source ~/venvs/dev/bin/activate
python --version | grep -q "3.12" \
  && echo "  [OK] Python 3.12 activo" \
  || echo "  [WARN]  Verificar versión de Python"

echo ""
echo "── PyTorch + CUDA ──"
python -c "
import torch
if torch.cuda.is_available():
    print(f'  [OK] PyTorch {torch.__version__} con CUDA {torch.version.cuda}')
    print(f'  [OK] GPU: {torch.cuda.get_device_name(0)}')
    print(f'  [OK] Memoria GPU: {torch.cuda.get_device_properties(0).total_memory/1e9:.0f} GB')
else:
    print('  [WARN]  CUDA no disponible — revisar instalación de PyTorch para JP 7.2')
" 2>/dev/null

echo ""
echo "── Librerías de desarrollo ──"
python -c "
import importlib
libs = ['openai', 'requests', 'httpx', 'jupyter', 'notebook']
for lib in libs:
    try:
        importlib.import_module(lib)
        print(f'  [OK] {lib}')
    except ImportError:
        print(f'  ○  {lib} → no instalado (pip install {lib})')
"

echo ""
echo "════════════════════════════════════════════════════"
```

```
# Salida esperada
── Entorno virtual ──
  [OK] Python 3.12 activo

── PyTorch + CUDA ──
  [OK] PyTorch 2.x.x con CUDA 12.9
  [OK] GPU: Orin (nvgpu)
  [OK] Memoria GPU: 64 GB

── Librerías de desarrollo ──
  [OK] openai
  [OK] requests
  [OK] httpx
  [OK] jupyter
  [OK] notebook
```

---

## 17.9 Mini-Proyecto: Transcriptor de Audio con GPU

Este proyecto une todo lo aprendido en el capítulo: VSCode Remote SSH para editar el notebook, el venv `dev` como kernel, y la GPU del Jetson para acelerar la transcripción de audio en español.

**Factor wow:** Con su Jetson, puede transcribir un audio de 10 minutos en menos de 2 minutos — completamente offline, sin enviar datos a ningún servidor externo, con calidad comparable a servicios cloud.

### 17.9.1 Requisito Previo: faster-whisper activo

```bash
# Verificar que faster-whisper está corriendo (capítulo 29)
curl -sf http://localhost:8000/health && echo "[OK] faster-whisper activo" \
  || echo "[!] Iniciar faster-whisper primero (ver Capítulo 29, sección 29.1.2)"
```

### 17.9.2 Notebook — audio_transcriber.ipynb

Cree el archivo `~/notebooks/audio_transcriber.ipynb` en VSCode y agregue las siguientes celdas:

```python
# Celda 1 — Instalar dependencias
import subprocess
subprocess.run(["pip", "install", "openai", "pydub", "tqdm"], capture_output=True)
print("✓ Dependencias instaladas")
```

```python
# Celda 2 — Verificar conexión con faster-whisper
import requests

try:
    r = requests.get("http://localhost:8000/health", timeout=3)
    print(f"✓ faster-whisper activo — status: {r.status_code}")
except Exception as e:
    print(f"✗ faster-whisper no disponible: {e}")
    print("  → Inicie faster-whisper con: docker start faster-whisper")
```

```python
# Celda 3 — Función de transcripción
import requests
import time
from pathlib import Path

def transcribir_audio(ruta_audio: str, idioma: str = "es", timestamps: bool = False) -> dict:
    """
    Transcribe un archivo de audio usando faster-whisper via API HTTP.
    
    Args:
        ruta_audio: Ruta al archivo WAV, MP3 o M4A
        idioma: Código de idioma ('es' para español, 'en' para inglés)
        timestamps: Si True, incluye timestamps a nivel de palabra
    
    Returns:
        dict con 'texto', 'duracion_audio', 'tiempo_transcripcion', 'ratio_velocidad'
    """
    inicio = time.time()
    ruta = Path(ruta_audio)
    
    if not ruta.exists():
        raise FileNotFoundError(f"Audio no encontrado: {ruta_audio}")
    
    # Preparar parámetros
    params = {
        "model": "whisper-1",
        "language": idioma,
        "response_format": "verbose_json" if timestamps else "json"
    }
    if timestamps:
        params["timestamp_granularities[]"] = "word"
    
    # Enviar al API
    with open(ruta_audio, "rb") as f:
        r = requests.post(
            "http://localhost:8000/v1/audio/transcriptions",
            files={"file": (ruta.name, f, "audio/wav")},
            data=params,
            timeout=300
        )
    r.raise_for_status()
    datos = r.json()
    
    tiempo_total = time.time() - inicio
    duracion = datos.get("duration", 0)
    
    return {
        "texto": datos.get("text", "").strip(),
        "duracion_audio": round(duracion, 1),
        "tiempo_transcripcion": round(tiempo_total, 1),
        "ratio_velocidad": round(duracion / max(tiempo_total, 0.1), 1),
        "palabras": datos.get("words", []) if timestamps else []
    }

print("✓ Función transcribir_audio() lista")
```

```python
# Celda 4 — Preparar audio de prueba (grabar 20s desde micrófono)
import subprocess
from pathlib import Path

audio_path = Path.home() / "notebooks" / "audio_prueba.wav"
audio_path.parent.mkdir(exist_ok=True)

print("Grabando 20 segundos... Hable ahora en español:")
print("(Pruebe: 'El Jetson AGX Orin tiene 64 gigabytes de memoria unificada y puede ejecutar modelos de inteligencia artificial localmente.')")
print()

subprocess.run([
    "arecord", "-D", "hw:0,0", "-f", "S16_LE",
    "-r", "16000", "-c", "1", "-d", "20",
    str(audio_path)
], check=False)

if audio_path.exists():
    size_kb = audio_path.stat().st_size // 1024
    print(f"✓ Audio grabado: {audio_path} ({size_kb} KB)")
else:
    print("⚠ No se pudo grabar (sin micrófono USB). Transfiera un archivo .wav vía SCP.")
    print("  En Windows: scp archivo.wav jetson:~/notebooks/audio_prueba.wav")
```

```python
# Celda 5 — Transcribir y mostrar resultado
resultado = transcribir_audio(str(audio_path), idioma="es", timestamps=True)

print(f"╔══════════════════════════════════════════════════════╗")
print(f"║  RESULTADO DE TRANSCRIPCIÓN                         ║")
print(f"╚══════════════════════════════════════════════════════╝")
print(f"  Duración del audio : {resultado['duracion_audio']} s")
print(f"  Tiempo transcripción: {resultado['tiempo_transcripcion']} s")
print(f"  Velocidad          : {resultado['ratio_velocidad']}× tiempo real")
print(f"")
print(f"  TEXTO:")
print(f"  {resultado['texto']}")

if resultado["palabras"]:
    print(f"\n  PRIMERAS 5 PALABRAS CON TIMESTAMPS:")
    for w in resultado["palabras"][:5]:
        print(f"    [{w['start']:.2f}s] {w['word']}")
```

```
# Salida esperada:
╔══════════════════════════════════════════════════════╗
║  RESULTADO DE TRANSCRIPCIÓN                         ║
╚══════════════════════════════════════════════════════╝
  Duración del audio : 20.0 s
  Tiempo transcripción: 4.2 s
  Velocidad          : 4.8× tiempo real

  TEXTO:
  El Jetson AGX Orin tiene 64 gigabytes de memoria unificada y puede ejecutar
  modelos de inteligencia artificial localmente.

  PRIMERAS 5 PALABRAS CON TIMESTAMPS:
    [0.00s] El
    [0.18s] Jetson
    [0.52s] AGX
    [0.78s] Orin
    [0.98s] tiene
```

```python
# Celda 6 — Guardar transcripción en archivo Markdown
import json
from datetime import datetime

salida_md = Path.home() / "notebooks" / f"transcripcion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

contenido = f"""# Transcripción de Audio
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
Archivo: {audio_path.name}  
Duración: {resultado['duracion_audio']}s | Velocidad: {resultado['ratio_velocidad']}× tiempo real

## Texto

{resultado['texto']}
"""

salida_md.write_text(contenido)
print(f"✓ Transcripción guardada en: {salida_md}")
```

> **Próximo paso:** El Capítulo 18 cubre en profundidad el ecosistema jetson-containers — las 51 imágenes Docker optimizadas para Jetson que serán la base de todos los proyectos de la Fase 2.
