# Parte B — Manos a la Obra

## Diez proyectos reales con IA local en el Jetson AGX Orin

---

Esta parte es el puente entre el conocimiento técnico y el valor tangible. Con la infraestructura de la Parte A completamente operativa, aquí construirá diez proyectos prácticos que resuelven necesidades reales: automatización empresarial, procesamiento de audio y documentos, generación de contenido, atención al cliente y exposición de servicios a Internet.

Cada proyecto está diseñado para ser completamente funcional desde el primer día, adaptable a su caso de uso específico y extensible mediante las secciones de escalabilidad incluidas en cada capítulo.

---

| Capítulo | Proyecto | Tecnologías principales |
|---|---|---|
| 19 | Entorno Python + VSCode | Python 3.12, venv, PyTorch, CUDA 13.2.1 |
| 20 | jetson-containers | Docker, dustynv containers, JetPack 7.2 |
| 21 | PDF a Pódcast | TTS, LLM, pipeline offline completo |
| 22 | Bot de Transcripción | Faster-Whisper, LLM, Telegram |
| 23 | Agencia de Turismo | OpenClaw, NemoClaw, RAG, herramientas |
| 24 | Embudo de Ventas | Ollama, pipeline de generación, Telegram |
| 25 | Contenido para LinkedIn | Hermes-3, adaptación de estilo, publicación |
| 26 | Asistente de Voz | llama.cpp, Whisper, TTS, latencia <500ms |
| 27 | RAG Empresarial | ChromaDB, nomic-embed-text, vLLM |
| 28 | Microservicios SAAS | Cloudflare Tunnel, SSL, JWT, exposición a Internet |

---

> **CONSEJO:** Antes de comenzar cada proyecto, ejecute `jetson-mem` para verificar la memoria disponible. Si hay contenedores de proyectos anteriores corriendo, deténgalos con `docker stop $(docker ps -q)` para liberar VRAM. Todos los proyectos incluyen instrucciones de limpieza al final de su capítulo.

> **NOTA:** Los proyectos de esta parte están diseñados para ejecutarse de forma independiente. Sin embargo, los Capítulos 23 (Turismo) y 24 (Embudo de Ventas) requieren OpenClaw instalado (Capítulo 11A), y el Capítulo 27 (RAG) requiere que Ollama esté corriendo con el modelo `nomic-embed-text` disponible.
