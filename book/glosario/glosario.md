# Glosario — Términos Técnicos

Este glosario reúne los términos técnicos más importantes del libro, organizados alfabéticamente. Cuando un término se usa por primera vez en un capítulo, se explica en contexto; aquí encontrará la definición de referencia rápida.

---

## A

**AGX Orin (NVIDIA Jetson AGX Orin)**
Sistema en chip (SoC) de NVIDIA diseñado para IA en el borde. La variante de 64 GB usada en este libro integra una GPU Ampere (2048 núcleos CUDA, sm_87), 12 núcleos CPU ARM Cortex-A78AE y 64 GB de memoria LPDDR5 unificada (compartida entre CPU y GPU). Ofrece hasta 275 TOPS de rendimiento de inferencia.

**alias (shell alias)**
Abreviación definida en `~/.bash_aliases` que sustitye un comando largo por una palabra corta. Ejemplo: `alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks'`. En este libro, todos los aliases se añaden a `~/.bash_aliases`, no a `~/.bashrc`.

**AnimateDiff**
Extensión del ecosistema Stable Diffusion que añade módulos de movimiento (_motion modules_) a los modelos de imagen. Permite generar clips de video cortos (8–24 fotogramas) a partir de un prompt de texto. Se integra como nodo personalizado en ComfyUI.

**API REST**
Interfaz de programación de aplicaciones basada en el protocolo HTTP. Los motores de inferencia del libro (vLLM, llama.cpp, Ollama) exponen una API REST compatible con el estándar OpenAI: `POST /v1/chat/completions`. Esto permite que cualquier cliente diseñado para OpenAI funcione con modelos locales sin cambiar el código.

**Arquitectura de memoria unificada**
En el Jetson, la CPU y la GPU comparten el mismo banco de memoria física (64 GB LPDDR5). No existe la separación VRAM/RAM que hay en una PC de escritorio. Ventaja: los modelos pueden acceder a toda la RAM. Desventaja: CPU y GPU compiten por el ancho de banda de memoria.

---

## B

**bash_aliases (`~/.bash_aliases`)**
Archivo de texto en el directorio home del usuario donde se definen los aliases de shell. Ubuntu lo carga automáticamente si existe y si `~/.bashrc` incluye la línea `[ -f ~/.bash_aliases ] && . ~/.bash_aliases`. En este libro todos los comandos cortos se almacenan aquí, no directamente en `~/.bashrc`.

**Batch size**
Número de imágenes o tokens procesados simultáneamente en una pasada de la GPU. Un batch mayor aumenta el rendimiento pero requiere más memoria. En el Jetson, para generación de imágenes, `batch_size=1` es el valor recomendado para modelos SDXL.

---

## C

**Checkpoint (SD Checkpoint)**
Archivo que contiene los pesos de un modelo de difusión estable completo. Extensión `.safetensors` (preferida) o `.ckpt`. Los checkpoints definen el "estilo" base de la generación (fotorrealista, anime, ilustración). Tamaño típico: 2 GB (SD 1.5) a 7 GB (SDXL).

**clean-start (arranque limpio)**
Filosofía central de este libro: el Jetson arrancar con el mínimo de servicios activos (solo SSH y NoMachine). Ningún contenedor ni modelo se inicia automáticamente al encender. Cada servicio se lanza manualmente bajo demanda con un alias y se detiene con `jetson-clean`. Esto garantiza que los 64 GB de RAM estén siempre disponibles para el modelo que los necesite.

**Cloudflare Tunnel (`cloudflared`)**
Servicio de Cloudflare que crea un túnel cifrado entre el Jetson e Internet sin necesidad de abrir puertos en el router ni tener IP pública estática. El Jetson se conecta hacia afuera al servidor de Cloudflare, que actúa como proxy inverso. Usado en el Capítulo 28.

**ComfyUI**
Interfaz web de generación de imágenes basada en un sistema de nodos conectados (grafo de procesamiento). Permite construir pipelines complejos de difusión estable: modelos, LoRA, ControlNet, VAE, AnimateDiff. Puerto por defecto: 8188. Más flexible que SD WebUI pero con curva de aprendizaje mayor.

**ControlNet**
Extensión de Stable Diffusion que permite controlar la composición de una imagen mediante una imagen de referencia: bordes (_Canny_), poses humanas (_OpenPose_), mapas de profundidad, etc. Requiere modelos ControlNet adicionales (~1.4 GB cada uno).

**Contenedor Docker**
Instancia en ejecución de una imagen Docker. Es un proceso aislado del sistema host, con su propio sistema de archivos, red y variables de entorno. En el Jetson, todos los contenedores deben incluir `--runtime nvidia` para acceder a la GPU, y `--restart no` para cumplir la filosofía de arranque limpio.

**CUDA (Compute Unified Device Architecture)**
Plataforma de computación paralela de NVIDIA. En JP 7.2, la versión es 13.2.1. Los modelos de IA usan CUDA para ejecutar operaciones matriciales en la GPU. En el Jetson, `nvidia-smi` no está disponible; use `nvcc --version` para verificar CUDA.

**cuDNN (CUDA Deep Neural Network library)**
Biblioteca de NVIDIA que implementa primitivas de redes neuronales profundas optimizadas para GPU. Las capas convolucionales, de atención y de activación usan cuDNN internamente. Incluida en JetPack 7.2 (versión 9.x).

**Cuantización**
Técnica para reducir el tamaño de un modelo LLM convirtiendo los pesos de punto flotante de 16 o 32 bits a enteros de menor precisión (4, 5, 8 bits). El formato GGUF para llama.cpp usa cuantización; el sufijo `Q4_K_M` indica cuantización de 4 bits con matrices K. Ver Apéndice A.15.

---

## D

**Daemon**
Proceso del sistema operativo que corre en segundo plano sin interacción del usuario. En este libro se evita configurar servicios de IA como daemons (no `systemctl enable`) para respetar la filosofía de arranque limpio. Solo SSH, NoMachine y el kernel son daemons permanentes.

**Diarización**
Proceso de identificar quién habla en cada segmento de un audio con múltiples hablantes. En el Capítulo 13, se usa `pyannote/speaker-diarization` para asignar etiquetas "SPEAKER_00", "SPEAKER_01", etc. a cada fragmento transcrito por Whisper.

**Diffusers (biblioteca de Hugging Face)**
Biblioteca Python de código abierto de Hugging Face para modelos de difusión (Stable Diffusion, SDXL, PixArt, etc.). Permite cargar y ejecutar estos modelos directamente en Python sin necesidad de una interfaz web. Usada en el Capítulo 19 para PixArt-Alpha.

**Docker**
Plataforma de contenedores que empaqueta una aplicación con todas sus dependencias en una unidad portátil. En el Jetson, Docker es el mecanismo principal para ejecutar servicios de IA con las librerías CUDA correctas, sin contaminar el sistema base.

**Docker Compose**
Herramienta de Docker para definir y gestionar aplicaciones multi-contenedor mediante un archivo YAML (`docker-compose.yml`). En este libro, todos los stacks con múltiples servicios se almacenan en `~/stacks/<nombre-stack>/` (regla G10).

---

## E

**eMMC (embedded MultiMediaCard)**
Almacenamiento flash integrado en el Jetson AGX Orin (64 GB). Es la memoria de arranque del sistema operativo. No es ideal para almacenar modelos LLM grandes (>10 GB) por velocidad y durabilidad. Para modelos grandes, se recomienda un disco NVMe externo montado en `/data/`.

**Embeddings**
Representación numérica de texto (o imágenes) como un vector de números reales en un espacio de alta dimensión. Los textos semánticamente similares tienen vectores cercanos. Usados en RAG (Capítulo 25) para buscar fragmentos relevantes de documentos.

---

## F

**faster-whisper**
Implementación de Whisper de OpenAI optimizada con CTranslate2. Transcribe audio a texto con menor uso de RAM y mayor velocidad que la implementación original. Puerto por defecto: 8000. Contenedor: `dustynv/faster-whisper:r39.2.0`.

**Fine-tuning**
Proceso de ajustar los pesos de un modelo pre-entrenado con datos específicos del dominio. LoRA y QLoRA son técnicas de fine-tuning eficientes en memoria. El Capítulo 9 menciona `llama-factory` como herramienta de fine-tuning en el Jetson.

---

## G

**GGUF (GPT-Generated Unified Format)**
Formato de archivo de llama.cpp para modelos cuantizados. Sucesor de GGML. Un archivo GGUF contiene los pesos del modelo, la arquitectura, el tokenizador y los metadatos en un solo archivo portátil. Compatible con llama.cpp, Ollama y LM Studio.

**GPU (Unidad de Procesamiento Gráfico)**
Procesador especializado en operaciones matriciales paralelas. En el Jetson, la GPU Ampere (sm_87) tiene 2048 núcleos CUDA y acceso a la memoria unificada. Es el componente crítico para la inferencia rápida de modelos LLM e imágenes.

---

## H

**HuggingFace (Hugging Face Hub)**
Plataforma online que aloja modelos de IA, datasets y bibliotecas. Los modelos se descargan automáticamente con `transformers`, `diffusers` o `vllm`. Los archivos se almacenan en `~/.cache/huggingface/hub/`. Para modelos privados o gated, se necesita `HF_TOKEN`.

**HF_TOKEN**
Token de acceso personal de Hugging Face. Necesario para descargar modelos gated (Gemma, GPT-OSS-20B, Llama). Se almacena como variable de entorno en `~/scripts/llm/env/llm-env.sh` y se carga con el alias `llm-vars`. Nunca se hardcodea en scripts.

---

## I

**Imagen Docker**
Plantilla de solo lectura que contiene el sistema operativo base, las dependencias y el código de una aplicación. Las imágenes para el Jetson deben ser compiladas para ARM64 con soporte CUDA Tegra. Las imágenes de `dustynv/` (jetson-containers) cumplen este requisito.

**Inferencia**
Proceso de usar un modelo entrenado para generar una predicción o respuesta a partir de una entrada. En el contexto LLM, inferencia es generar texto token a token a partir de un prompt. Diferente de entrenamiento (ajustar pesos) o fine-tuning.

---

## J

**JetPack (NVIDIA JetPack SDK)**
Suite de software de NVIDIA para el Jetson. Incluye L4T (Linux for Tegra), CUDA, cuDNN, TensorRT, OpenCV y librerías de IA. Este libro usa JetPack 7.2 (L4T r39.2, Ubuntu 24.04, CUDA 13.2.1).

**jetson_clocks**
Comando de NVIDIA que fija las frecuencias de CPU, GPU y memoria a sus valores máximos, desactivando el escalado dinámico. Debe ejecutarse después de `nvpmodel` para garantizar el rendimiento máximo. El alias `pwr-maxn` incluye `sudo jetson_clocks` automáticamente.

**jetson-containers**
Proyecto de código abierto mantenido por Dustin Franklin (NVIDIA) que proporciona más de 50 imágenes Docker precompiladas para el ecosistema Jetson: faster-whisper, kokoro-tts, ComfyUI, JupyterLab, etc. Los tags siguen el patrón `dustynv/<servicio>:r<L4T-version>`.

**jtop**
Herramienta de monitoreo para el Jetson (equivalente a `top` pero específico para NVIDIA Jetson). Muestra en tiempo real: uso de CPU por núcleo, uso de GPU, temperatura, frecuencias, modo de energía, RAM y swap. Instalación: `sudo pip3 install jetson-stats`. Uso: `jtop`.

---

## K

**Kernel (núcleo del sistema operativo)**
Componente central del sistema operativo que gestiona el hardware, la memoria y los procesos. En JP 7.2, el kernel es la versión 6.8.12-tegra, adaptado por NVIDIA para el SoC del Jetson (controladores Tegra, acceso directo a GPU).

**kokoro-tts**
Motor de síntesis de voz de alta calidad. Soporta múltiples voces en inglés y español. Puerto por defecto: 8880. Contenedor: `dustynv/kokoro-tts:r39.2.0`. Compatible con la API de voz de OpenAI (`/v1/audio/speech`).

---

## L

**L4T (Linux for Tegra)**
Sistema operativo de NVIDIA basado en Ubuntu, optimizado para los SoC Tegra del Jetson. En JP 7.2, L4T es la versión r39.2 sobre Ubuntu 24.04. Las imágenes Docker de jetson-containers se etiquetan con el número de L4T (ej. `r39.2.0`).

**llama.cpp**
Motor de inferencia de código abierto escrito en C++ para modelos GGUF. Compatible con CPU y GPU. En el Jetson, se usa la imagen `ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin` de NVIDIA AI IoT. Puerto por defecto: 8080.

**LoRA (Low-Rank Adaptation)**
Técnica de fine-tuning eficiente que añade adaptadores de rango bajo a un modelo existente. Los archivos `.safetensors` de LoRA son pequeños (50–500 MB) y modifican el estilo o comportamiento del modelo base sin reentrenar todos los pesos. Ampliamente usados en Stable Diffusion.

**LLM (Large Language Model, Modelo de Lenguaje Grande)**
Modelo de IA entrenado sobre grandes cantidades de texto para generar, completar o responder texto de forma coherente. Ejemplos: Qwen3.5-35B, Gemma-4, Nemotron-3. La inferencia de LLMs es la carga de trabajo principal de este libro.

---

## M

**MAXN (modo de energía)**
Modo de máximo rendimiento del Jetson (50W). Activa todos los núcleos de CPU y GPU a su frecuencia máxima. Se activa con `pwr-maxn` (`sudo nvpmodel -m 0 && sudo jetson_clocks`). Necesario para modelos LLM grandes (>9B parámetros) y generación de imágenes.

**Motion module (AnimateDiff)**
Archivo de pesos que añade conocimiento de movimiento temporal a un modelo SD 1.5, permitiendo generar secuencias de fotogramas coherentes en lugar de imágenes estáticas. Se almacena en `~/models/animatediff/`. Extensión `.ckpt`.

---

## N

**N8N**
Plataforma de automatización de workflows de código abierto, auto-hospedable. Permite conectar servicios externos (Gmail, Google Sheets, Telegram, webhooks) con flujos condicionales y nodos de transformación. Puerto por defecto: 5678. Usado en el Capítulo 27.

**NemoClaw**
Orquestador de seguridad y routing de NVIDIA para el ecosistema de agentes IA en el Jetson. Actúa como gateway entre los agentes externos (Telegram, WhatsApp) y los modelos LLM locales. Ver Capítulo 13.

**NoMachine**
Software de escritorio remoto de alta performance. Permite acceder a la interfaz gráfica del Jetson desde Windows con latencia muy baja, ideal para trabajo sin monitor. Puerto por defecto: 4000. Se configura en el Capítulo 2.

**nvpmodel**
Herramienta de NVIDIA para cambiar el modo de energía del Jetson. Los modos principales en JP 7.2 son: `-m 0` (MAXN, 50W), `-m 2` (30W), `-m 3` (15W). Siempre combinarlo con `jetson_clocks` para modo MAXN.

---

## O

**Ollama**
Servidor de inferencia local para modelos LLM en formato GGUF y safetensors. Simplifica la descarga y gestión de modelos con comandos como `ollama pull qwen3.5:7b`. Puerto por defecto: 11434. Incluye una API compatible con el formato de OpenAI.

**OpenClaw**
Orquestador de agentes IA de NVIDIA para el Jetson. Permite construir agentes de Telegram, WhatsApp y otros canales que usan LLMs locales como backend. Puerto por defecto: 18789. Ver Capítulo 12.

**OpenAI-compatible API**
Convención de API REST que sigue el mismo esquema que la API de OpenAI (endpoints `/v1/chat/completions`, `/v1/models`, `/v1/audio/speech`). Todos los motores del libro (vLLM, llama.cpp, Ollama) exponen esta interfaz, lo que permite usar cualquier cliente OpenAI con modelos locales sin modificar el código.

---

## P

**piper-tts**
Motor de síntesis de voz (TTS) rápido y ligero, diseñado para funcionar en CPU con latencia baja (<200ms). Soporta más de 40 idiomas incluido el español. Puerto por defecto: 10200. Contenedor: `dustynv/piper-tts:r39.2.0`.

**PixArt-Alpha**
Modelo de difusión basado en transformers (DiT) para generación de imágenes de alta calidad. El modelo pesa ~500 MB (mucho menor que los checkpoints SD), lo que lo hace eficiente en el Jetson. Disponible vía la biblioteca `diffusers` de Hugging Face.

**Prompt**
Texto de entrada que se proporciona a un modelo LLM o de imagen para guiar su generación. En LLMs, es la instrucción o pregunta del usuario. En Stable Diffusion, es la descripción de la imagen deseada (prompt positivo) y lo que se quiere evitar (prompt negativo).

**Python 3.12**
Versión de Python incluida en Ubuntu 24.04 / JetPack 7.2. Cambio importante respecto a JP 6.2 que usaba Python 3.10. Algunos paquetes pueden no estar disponibles para 3.12 aún; verificar compatibilidad antes de instalar.

---

## R

**RAG (Retrieval-Augmented Generation)**
Técnica que combina un motor de búsqueda de vectores (embeddings + ChromaDB) con un LLM. En lugar de responder solo con el conocimiento del modelo, el sistema primero recupera fragmentos relevantes de documentos propios y los inyecta en el prompt del LLM. Permite crear "asistentes sobre documentos" sin fine-tuning. Ver Capítulo 25.

**restart: "no" (Docker)**
Política de reinicio de contenedores Docker que indica que el contenedor NO debe reiniciarse automáticamente tras un fallo o reinicio del sistema. Es la política central de la filosofía clean-start de este libro. Todos los contenedores usan `restart: "no"`.

---

## S

**safetensors**
Formato de archivo de pesos de modelo desarrollado por Hugging Face. Más seguro que `.ckpt` (no ejecuta código Python al cargar), más rápido de cargar y más compacto. Extensión preferida para checkpoints y LoRA en Stable Diffusion.

**sd_87 (sm_87)**
Arquitectura de la GPU del Jetson AGX Orin. "sm" significa Streaming Multiprocessor. La arquitectura Ampere en el Jetson es sm_87. Algunas herramientas (PyTorch, TensorRT) necesitan compilar kernels específicos para sm_87 para funcionar correctamente.

**SD WebUI (Stable Diffusion WebUI, AUTOMATIC1111)**
Interfaz web de código abierto para Stable Diffusion. Ofrece pestañas txt2img, img2img, Extras (upscaling) e Inpainting. Puerto por defecto: 7860. Contenedor: `dustynv/stable-diffusion-webui:r39.2.0`.

**SSH (Secure Shell)**
Protocolo criptográfico para acceso remoto a la terminal del Jetson. En este libro, la conexión siempre es `ssh jetson` (con alias en `~/.ssh/config` del PC de desarrollo).

**SSH tunnel (túnel SSH)**
Mecanismo para redirigir tráfico de red a través de una conexión SSH cifrada. Ejemplo: `ssh -L 8188:localhost:8188 jetson` redirige el puerto local 8188 al puerto 8188 del Jetson, permitiendo acceder a ComfyUI desde el navegador de Windows sin exponer el servicio a Internet.

**Stable Diffusion (SD)**
Familia de modelos de difusión latente para generación de imágenes a partir de texto. Las versiones principales son SD 1.5 (~2 GB, 512×512) y SDXL (~7 GB, 1024×1024). Ejecutables en el Jetson mediante ComfyUI o SD WebUI.

**swap (espacio de intercambio)**
Área del disco usada como extensión de la RAM cuando la memoria física se agota. En el Jetson, se configura ZRAM (swap comprimida en RAM) y un archivo de swap en el SSD. El Capítulo 4 configura 16–32 GB de swap. El uso excesivo de swap indica que el modelo es demasiado grande para la configuración actual.

**systemd**
Sistema de inicialización y gestión de servicios de Linux. Los servicios marcados con `systemctl enable` arrancan automáticamente al iniciar el sistema. En este libro, solo SSH y NoMachine están habilitados; todos los servicios de IA se inician manualmente.

---

## T

**TensorRT**
Librería de NVIDIA para optimizar modelos de IA para inferencia en GPU. Convierte modelos PyTorch/ONNX a un formato optimizado para el hardware específico. En JP 7.2, TensorRT es la versión 10.x. El contenedor `dustynv/whisper-trt` usa TensorRT para acelerar la transcripción.

**Token**
Unidad básica de texto que procesa un LLM. Un token es aproximadamente una palabra o sub-palabra (4 caracteres en promedio en inglés). Los LLMs tienen un límite de tokens de contexto (`--max-model-len`). El rendimiento se mide en tokens por segundo (tok/s).

**TOPS (Tera Operations Per Second)**
Unidad de rendimiento de IA. El Jetson AGX Orin 64 GB ofrece 275 TOPS de inferencia INT8. No confundir con tok/s (tokens por segundo), que depende del modelo y el motor de inferencia.

**TTS (Text-to-Speech)**
Tecnología de síntesis de voz que convierte texto en audio. En este libro se usan kokoro-tts (alta calidad, puerto 8880) y piper-tts (rápido, puerto 10200). El Capítulo 13 cubre ambos en detalle.

---

## U

**UFW (Uncomplicated Firewall)**
Herramienta simplificada para gestionar reglas de firewall en Ubuntu. Se configura en el Capítulo 20 para bloquear todos los puertos excepto SSH (22) y los servicios expuestos intencionalmente. Comandos clave: `sudo ufw status`, `sudo ufw allow 22/tcp`, `sudo ufw enable`.

**Unified Memory (memoria unificada)**
Ver _Arquitectura de memoria unificada_.

---

## V

**VAD (Voice Activity Detection)**
Algoritmo que detecta cuándo hay voz activa en un flujo de audio, filtrando el silencio. En el pipeline de asistente de voz (Capítulo 24), VAD determina cuándo el usuario ha terminado de hablar para iniciar la transcripción con Whisper.

**VAE (Variational Autoencoder)**
Componente de Stable Diffusion que codifica imágenes al espacio latente y las decodifica de vuelta a píxeles. Un VAE mejorado (como `vae-ft-mse-840000`) corrige la saturación de colores y mejora la nitidez respecto al VAE base.

**venv (entorno virtual Python)**
Entorno Python aislado que contiene sus propias dependencias sin afectar al sistema base. En este libro se usa `~/venvs/llm/` para PyTorch/transformers y `~/venvs/sdtools/` para Diffusers/PixArt. Activación: `source ~/venvs/llm/bin/activate`.

**vLLM**
Motor de inferencia de alto rendimiento para modelos LLM en GPU. Implementa técnicas como PagedAttention para maximizar el throughput. Compatible con modelos de HuggingFace. Imagen para Jetson: `ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin`. Puerto por defecto: 8000.

---

## W

**Whisper (OpenAI Whisper)**
Modelo de reconocimiento de voz (STT) de código abierto de OpenAI. Soporta más de 90 idiomas. Las variantes van desde `tiny` (~39 MB) hasta `large-v3` (~1.5 GB). El Jetson corre `large-v3` con faster-whisper para máxima precisión en español.

**Workflow (ComfyUI)**
En ComfyUI, un workflow es un grafo de nodos conectados que define el pipeline completo de generación: desde cargar el modelo hasta guardar la imagen final. Los workflows se guardan en formato JSON y pueden compartirse o reutilizarse.

---

## Z

**ZRAM**
Dispositivo de swap que comprime datos en RAM en lugar de escribirlos al disco. Ofrece un compromiso entre velocidad (más rápido que swap en disco) y capacidad (los datos comprimidos ocupan menos). Configurado en el Capítulo 4 para el Jetson. Alias: `zramctl` para verificar estado.

---

*Fin del Glosario. Para definiciones no encontradas aquí, consulte la documentación oficial de NVIDIA JetPack 7.2 o el foro de NVIDIA Developer Forums.*
