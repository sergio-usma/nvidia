# Introducción

## Sobre este libro

*Getting Started with NVIDIA Jetson AGX Orin 64GB (JetPack 7.2)* es una guía técnica completa diseñada para llevarle desde el primer arranque del dispositivo hasta el despliegue de sistemas de inteligencia artificial en producción. En sus páginas encontrará configuraciones verificadas, comandos con salida esperada, diagnóstico de errores comunes y proyectos prácticos que demuestran el potencial real del hardware.

Este libro cubre la plataforma **NVIDIA Jetson AGX Orin 64GB con JetPack 7.2**, que incluye:

| Componente | Versión |
|---|---|
| Sistema operativo | Ubuntu 24.04 LTS |
| JetPack | 7.2 (L4T r39.2) |
| CUDA | 13.2.1 |
| Python | 3.12 |
| Kernel Linux | 6.8 |
| Arquitectura GPU | NVIDIA Ampere (sm_87) |

Todos los comandos, scripts y configuraciones han sido verificados en este entorno específico. Cuando un procedimiento difiere de versiones anteriores de JetPack (especialmente JP 6.2), se indica explícitamente.

---

## A quién está dirigido

Este libro está pensado para profesionales técnicos que se acercan al Jetson por primera vez, aunque con experiencia previa en alguno de estos campos:

- **Desarrolladores de software** con conocimiento básico de Linux que desean desplegar modelos de IA sin depender de la nube
- **Ingenieros de IA y Machine Learning** que quieren llevar sus modelos a producción en hardware de borde
- **Ingenieros de robótica y visión artificial** que necesitan potencia de cómputo local con aceleración GPU
- **Emprendedores tecnológicos** que buscan construir productos de IA con costos operativos controlados

No se requiere experiencia previa con hardware Jetson ni con el ecosistema NVIDIA. Sí se asume familiaridad básica con la línea de comandos de Linux (navegar directorios, editar archivos, ejecutar scripts) y conceptos generales de programación en Python.

---

## Qué aprenderá

El libro está organizado en tres partes que progresan desde la configuración del sistema hasta proyectos de producción:

**Parte A — Fundamentos**  
Configura el Jetson desde cero: sistema operativo, red, almacenamiento, acceso remoto, Docker, los tres motores de inferencia principales (Ollama, llama.cpp, vLLM), el stack de IA agéntica completo, visión artificial, voz, generación de imágenes y el ciclo completo de benchmarking y despliegue en producción.

**Parte B — Manos a la Obra**  
Construye diez proyectos prácticos completos: desde un entorno de desarrollo Python con VSCode Remote SSH hasta un sistema multiagente de RAG empresarial, pasando por bots de transcripción, pipelines PDF-a-pódcast, asistentes de voz offline y microservicios expuestos a Internet.

**Parte C — Capstone**  
Dos proyectos de alta complejidad que integran todo lo aprendido: una agencia de IA completa con presencia web y un sistema de automatización de contenido en video para plataformas como YouTube Shorts y TikTok.

Al finalizar el libro, usted habrá:
- Configurado y optimizado un entorno Jetson AGX Orin listo para producción
- Desplegado los tres principales motores de inferencia con gestión eficiente de VRAM
- Construido más de diez proyectos prácticos con IA local
- Comprendido la arquitectura de un stack de IA agéntica completo
- Aprendido a exponer servicios de IA de forma segura a Internet

---

## Cómo usar este libro

**Lectura secuencial (recomendada):** Los capítulos de la Parte A están diseñados para leerse en orden. Cada uno asume que los anteriores han sido completados. En particular, los capítulos 6, 12 y 17 crean variables de entorno, aliases y scripts que los capítulos posteriores utilizan sin repetir su definición.

**Saltar a proyectos:** Si ya tiene experiencia con la configuración base del Jetson, puede comenzar directamente desde el Capítulo 19 (Parte B). En ese caso, asegúrese de tener instalados al menos Ollama (Cap. 10), el entorno de shell configurado (Cap. 6) y Docker (Cap. 9).

**Referencia rápida:** El Apéndice consolida todos los aliases, scripts, paquetes apt, variables de entorno y comandos de verificación en una sola sección de consulta rápida. Es el lugar al que acudir cuando necesite recordar un comando específico sin releer el capítulo completo.

---

## Requisitos previos

**Hardware:**
- NVIDIA Jetson AGX Orin 64GB (Developer Kit o producción)
- Módulo NVMe SSD de al menos 500 GB (recomendado: 1 TB, NVMe Gen4)
- Conexión a Internet durante la configuración inicial (los proyectos funcionan completamente offline una vez configurados)
- Monitor, teclado y mouse para la configuración inicial (o acceso SSH si ya tiene JetPack instalado)

**Software:**
- JetPack 7.2 instalado en el Jetson (el Capítulo 2 explica cómo instalarlo desde cero)
- Una computadora con Windows, macOS o Linux para conectarse por SSH y transferir archivos

**Conocimientos previos:**
- Manejo básico de terminal Linux (ls, cd, nano/vim, sudo)
- Conceptos básicos de Python (variables, funciones, pip)
- Opcionalmente: Docker, redes TCP/IP básicas

---

## Convenciones tipográficas

A lo largo del libro se utilizan los siguientes elementos visuales:

**Bloques de código**  
Los comandos y fragmentos de código aparecen en bloques con fondo gris. Las líneas que comienzan con `$` son comandos que usted ejecuta. Las líneas sin `$` son salidas esperadas del sistema.

```bash
$ sudo apt update
Hit:1 http://ports.ubuntu.com/ubuntu-ports noble InRelease
Reading package lists... Done
```

**Etiquetas de verificación**  
Los comandos verificados en el hardware de prueba se marcan con `[VERIFIED ON JP 7.2]`. Los comandos que deberían funcionar pero no han sido verificados en JP 7.2 llevan `[NEEDS VERIFICATION]`.

**Callouts**

> **NOTA:** Información adicional útil para comprender el contexto.

> **CONSEJO:** Recomendación para optimizar el proceso o evitar errores comunes.

> **ADVERTENCIA:** Acción que puede causar pérdida de datos o dejar el sistema en estado inconsistente si no se sigue correctamente.

> **IMPORTANTE:** Paso crítico que no debe omitirse.

**Infografías**  
Los diagramas de arquitectura y flujo están marcados con un comentario `<!-- INFOGRAFÍA -->` en el archivo fuente, indicando el concepto que ilustran. En la versión impresa final, estos comentarios serán reemplazados por ilustraciones profesionales.

---

## Configuraciones de almacenamiento

El libro soporta dos configuraciones de almacenamiento, que se indican cuando el procedimiento difiere:

- **Configuración A:** Sistema operativo en eMMC interno; NVMe como volumen `/data`
- **Configuración B:** Sistema operativo instalado directamente en NVMe (recomendada para mejor rendimiento)

Si no está seguro de su configuración, ejecute `df -h /` en el Jetson: si la raíz `/` aparece en un dispositivo `nvme0n1`, está en Configuración B.

---

## Recursos adicionales

- **Documentación oficial NVIDIA Jetson:** `https://developer.nvidia.com/embedded/jetpack`
- **Repositorio jetson-containers (dustynv):** `https://github.com/dusty-nv/jetson-containers`
- **NVIDIA NGC:** `https://catalog.ngc.nvidia.com`
- **Hugging Face Hub:** `https://huggingface.co`
- **OpenRouter (API cloud gratuita):** `https://openrouter.ai`

---

> **NOTA:** Este libro está escrito íntegramente en español. Los comandos, nombres de archivos, variables de entorno y fragmentos de código permanecen en inglés —el idioma nativo de Linux, Python y el ecosistema NVIDIA— para evitar confusiones al copiarlos directamente en la terminal.
