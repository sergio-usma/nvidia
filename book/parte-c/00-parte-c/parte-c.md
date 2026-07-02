# Parte C — Capstone

## Proyectos de alto impacto que integran todo lo aprendido

---

Esta parte es la culminación del libro. Los dos proyectos Capstone no son ejercicios académicos: son sistemas de producción completos que integran simultáneamente los motores de inferencia, el stack agéntico, las herramientas de automatización, la visión artificial, la síntesis de voz y la infraestructura de despliegue que construyó a lo largo de las Partes A y B.

Un proyecto Capstone demuestra que el conocimiento es funcional cuando se combina. Aquí no hay andamiajes ni simplificaciones: trabaja con la misma arquitectura que una agencia de IA real, el mismo pipeline que un creador de contenido profesional.

---

| Proyecto | Descripción | Tecnologías integradas |
|---|---|---|
| **Capstone 01** | Agencia de IA con Presencia Web | OpenClaw + NemoClaw + Open WebUI + Cloudflare Tunnel + JWT + SSL + monitoreo |
| **Capstone 02** | Automatización de YouTube Shorts y TikTok | LLM + TTS + SD WebUI + AnimateDiff + ffmpeg + pipeline editorial completo |

---

## Antes de comenzar

Los proyectos Capstone asumen que los siguientes servicios están instalados y verificados:

**Para Capstone 01:**
- OpenClaw y NemoClaw (Cap. 11A y 11B)
- Open WebUI (Cap. 11C)
- N8N operativo (Cap. 15)
- Microservicios y Cloudflare Tunnel configurados (Cap. 28)
- Al menos un motor de inferencia corriendo (Ollama o vLLM)

**Para Capstone 02:**
- Ollama o llama.cpp con un modelo de 7B disponible (Cap. 10)
- TTS configurado (Cap. 13)
- SD WebUI o ComfyUI instalados (Cap. 14)
- ffmpeg disponible (`sudo apt install -y ffmpeg`)

---

## Gestión de memoria en proyectos Capstone

Con 64 GB de memoria unificada, el Jetson AGX Orin puede ejecutar stacks complejos, pero cada recurso ocupa espacio. La siguiente tabla muestra los umbrales de referencia:

| Estado del sistema | Uso estimado de RAM unificada |
|---|---|
| Sistema operativo (reposo) | ~12 GB |
| Ollama con modelo 7B cargado | ~18 GB |
| vLLM con modelo 13B | ~28 GB |
| SD WebUI con SDXL | ~10–14 GB adicionales |
| Pipeline Capstone 01 completo | ~42–46 GB |
| Pipeline Capstone 02 (secuencial) | ~20–24 GB (pico) |

> **ADVERTENCIA:** No intente ejecutar ambos proyectos Capstone simultáneamente. Utilice `jetson-mem` antes de lanzar cada componente y detenga los servicios del proyecto anterior antes de comenzar el siguiente.

---

> **CONSEJO:** Si durante el desarrollo de un Capstone experimenta errores de OOM (Out of Memory), ejecute `docker stop $(docker ps -q) && sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches` para liberar memoria y reintentar.
