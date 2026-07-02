# Capítulo 1 — Inicio Rápido y Especificaciones del Hardware

## Sobre Este Libro

Este libro es una guía de instalación, configuración y uso avanzado de la **NVIDIA Jetson AGX Orin 64GB** con **JetPack 7.2**. Está pensado para quien llega al dispositivo por primera vez y quiere convertirlo en una plataforma de inferencia local completamente funcional: desde el primer encendido hasta un sistema agéntico capaz de recibir preguntas por Telegram, ejecutar modelos de 35 mil millones de parámetros y responder de forma autónoma — sin enviar ni un solo token a servidores externos.

Cada paso de esta guía fue ejecutado y verificado en un Jetson AGX Orin 64GB real corriendo JetPack 7.2-b187. Los comandos incluyen la salida esperada para que pueda confirmar en cada momento que el sistema responde correctamente.

### A quién está dirigido

- **Desarrolladores** que llegan al Jetson desde el mundo de las APIs cloud y quieren inferencia local sin costo por token.
- **Ingenieros de IA/ML** que necesitan un entorno de experimentación con GPU real, sin restricciones de cuota ni latencia de red.
- **Ingenieros de robótica** que requieren inferencia de visión y lenguaje en el borde (edge) con consumo energético controlado.

No se asume experiencia previa con Jetson ni con Linux embebido. Se asume que sabe usar una terminal y que ha ejecutado comandos en Linux o macOS al menos una vez.

### Cómo usar este libro

El libro está organizado en 16 partes más un apéndice. Puede seguirlo de principio a fin si parte de un Jetson sin configurar, o saltar directamente a las secciones que necesita si ya tiene parte del sistema operativo listo:

| Si ya tiene... | Salte a... |
|----------------|-----------|
| Jetson sin flashear | Capítulo 1 — Primer arranque |
| Ubuntu instalado, sin SSH | Capítulo 2 — Configuración base |
| SSH funcionando | Capítulo 3 — Performance tuning |
| Base completa, quiere AI | Capítulo 12 — Motores de inferencia |
| Todo listo, quiere agentes | Capítulo 13 — Stack agéntico |

> **NOTA:** Los capítulos de inferencia de IA (motores de inferencia, agentes, benchmarking, producción) son los más densos y representan el núcleo de valor del libro. Los capítulos de configuración base construyen la infraestructura que los sustenta.

### Convenciones tipográficas y bloques del libro

Cada capítulo sigue una estructura pedagógica consistente. Antes de ejecutar cualquier comando, familiarícese con estos bloques:

**Bloques de código**
```bash
# Los bloques bash contienen comandos para la terminal del Jetson
# Salvo que se indique "[EN WINDOWS POWERSHELL]" o "[EN WINDOWS TERMINAL]"
```

**Salida esperada**
```bash
# Los bloques sin encabezado "bash" muestran lo que debe ver en pantalla
# Si su salida difiere, el capítulo de Troubleshooting explica las causas más comunes
```

**Notas de aviso — lea ANTES de ejecutar:**

| Bloque | Significado |
|--------|-------------|
| `> **IMPORTANTE:**` | Paso donde un error puede bloquear el avance. Lea y verifique antes de ejecutar. |
| `> **ADVERTENCIA:**` | Acción irreversible o peligrosa. Tenga backup o snapshot antes de continuar. |
| `> **NOTA:**` | Contexto adicional, no obligatorio para seguir el flujo. |
| `> **CONSEJO:**` | Optimización o alternativa que puede ignorar si está siguiendo el flujo principal. |
| `[REQUIERE VERIFICACIÓN]` | El comando es correcto en principio pero puede variar con versiones futuras del software. Verifique la documentación oficial si falla. |

**Sobre los placeholders**

Cuando vea un valor en MAYÚSCULAS como `hf_SU_TOKEN_AQUI` o `TU_CORREO@gmail.com`, debe reemplazarlo con su valor real antes de ejecutar. El libro siempre añade una nota indicando dónde obtenerlo. **No ejecute comandos con placeholders sin reemplazarlos primero** — el sistema aceptará el comando pero fallará más adelante de forma difícil de diagnosticar.

**Filosofía de ejecución — Jetson "en limpio"**

Este libro sigue un principio fundamental: **el Jetson arranca sin ningún servicio de IA activo**. Ningún modelo LLM, ningún contenedor Docker, ningún agente. El sistema inicia con solo los servicios mínimos del sistema operativo (~12 GB de RAM libre de 64 GB).

Para activar cualquier servicio se usa un alias o un script específico. Para desactivarlo, un alias o script de limpieza. Esto garantiza:
- Sin errores de out-of-memory (OOM) por procesos acumulados en segundo plano
- Transición limpia entre diferentes cargas de trabajo (LLM grande → visión → TTS)
- Reproducibilidad: el sistema siempre parte del mismo estado conocido

Esta filosofía se establece en el Capítulo 5 (shell y aliases) y se refuerza a lo largo de todo el libro.

**Sobre las secciones de Troubleshooting**

Cada capítulo termina con una sección de errores frecuentes. Los errores están documentados con:
1. El mensaje de error exacto que verá en la terminal
2. La causa probable
3. El comando de solución

Si un comando falla, busque primero en la sección de troubleshooting del capítulo actual y luego en el Capítulo 21 (Troubleshooting general).

---

## 1.1 ¿Qué es la NVIDIA Jetson AGX Orin 64GB?

La Jetson AGX Orin 64GB es una computadora de alto rendimiento del tamaño de una palma de la mano, diseñada para ejecutar cargas de trabajo de inteligencia artificial directamente en el borde de la red (sin conexión a servidores externos). NVIDIA la posiciona como la plataforma de edge AI más potente de su catálogo: 275 TOPS (Tera-Operaciones Por Segundo) de rendimiento de inferencia, suficiente para ejecutar modelos de lenguaje de hasta 35 mil millones de parámetros en tiempo real.

La característica más importante para el trabajo con LLMs es su **memoria unificada**: los 64 GB de RAM LPDDR5 son compartidos entre la CPU (12 núcleos ARM) y la GPU (Ampere sm_87). No existe una "VRAM separada" como en una tarjeta gráfica de escritorio — toda la memoria disponible puede usarse para el modelo. Esto significa que un modelo de 26 GB puede cargarse completamente en memoria con decenas de gigabytes de margen, algo imposible en una GPU de escritorio con 16 GB de VRAM.

```bash
┌───────────────────────────────────────────────────────────────┐
│           NVIDIA Jetson AGX Orin 64GB — Arquitectura          │
├────────────────────────┬──────────────────────────────────────┤
│  CPU: ARM Cortex-A78AE │  GPU: Orin (Ampere sm_87)            │
│  12 núcleos @ 2.2 GHz  │  2048 CUDA cores                     │
│  8 núcleos en línea    │  64 Tensor Cores                     │
├────────────────────────┴──────────────────────────────────────┤
│           MEMORIA UNIFICADA: 64 GB LPDDR5 ECC                 │
│    (CPU y GPU comparten el mismo pool de memoria física)      │
├───────────────────────────────────────────────────────────────┤
│  DLA (Deep Learning Accelerator): 2 × DLA v3.0               │
│  PVA (Programmable Vision Accelerator): 2 unidades           │
│  NVEnc / NVDec: codificación/decodificación de video 8K      │
├───────────────────────────────────────────────────────────────┤
│  Storage NVMe: 931 GB SSD M.2 (expandible)                   │
│  eMMC: 59 GB (arranque del sistema operativo)                │
│  Conectividad: 10GbE + GbE + USB 3.2 + USB-C + CAN + I2C     │
│  Consumo: 15W (modo ahorro) → 50W (MAXN, máximo rendimiento) │
└───────────────────────────────────────────────────────────────┘
```

### Por qué la memoria unificada cambia las reglas

En una PC con GPU dedicada, la memoria de la GPU (VRAM) está físicamente separada de la RAM del sistema. Un modelo que ocupe 20 GB no puede cargarse en una GPU con 16 GB de VRAM, sin importar cuánta RAM tenga la PC. En el Jetson, esa distinción no existe. El sistema operativo, los procesos del servidor, el motor de inferencia y el modelo comparten el mismo banco de 64 GB. Esto implica dos consecuencias prácticas:

1. **Puede ejecutar modelos mucho más grandes** de lo que permite cualquier GPU de escritorio convencional hasta la gama professional.
2. **Debe gestionar la memoria con cuidado**: el sistema operativo y los servicios activos consumen entre 12 y 14 GB al arrancar, lo que deja ~50 GB disponibles para modelos. Si dos motores de inferencia están activos simultáneamente, se reparten ese espacio. Las partes de gestión de memoria de este libro (Capítulo 4, Capítulo 14, Capítulo 15) tratan exactamente este punto.

---

## 1.2 Especificaciones Técnicas Completas

### Hardware

| Componente | Especificación |
|------------|---------------|
| GPU | Orin (nvgpu) — Arquitectura Ampere |
| Compute Capability | **sm_87** — `TORCH_CUDA_ARCH_LIST="8.7"` |
| Núcleos CUDA | 2048 |
| Tensor Cores | 64 |
| CPU | ARM Cortex-A78AE, 12 núcleos (8 en línea), 2.2 GHz |
| Memoria | **64 GB LPDDR5 ECC, unificada CPU+GPU** |
| Ancho de banda de memoria | 204.8 GB/s |
| Rendimiento AI | **275 TOPS** (modo MAXN) |
| DLA | 2 × Deep Learning Accelerator v3.0 |
| PVA | 2 × Programmable Vision Accelerator |
| Almacenamiento NVMe | 931.5 GB SSD M.2 (típico con Developer Kit) |
| Almacenamiento eMMC | 59.2 GB (OS interno) |
| Conectividad Ethernet | 10 GbE + 1 GbE |
| USB | USB 3.2 Gen2 × 4 + USB-C (DisplayPort) |
| Consumo | 15W (modo 1) / 30W (modo 2) / 50W (MAXN, modo 0) |
| Dimensiones (módulo) | 100 × 87 mm |

### Software Stack (JetPack 7.2)

| Componente | Versión |
|------------|---------|
| JetPack | 7.2-b187 |
| L4T (Jetson Linux) | **r39.2** |
| Sistema Operativo | Ubuntu 24.04.4 LTS (aarch64) |
| Kernel | **6.8.12-1021-tegra** |
| CUDA | **13.2.1** |
| TensorRT | 10.16.2 |
| cuDNN | 9.x (incluido en JetPack) |
| cuSPARSELt | 0.7.1.0 |
| Python por defecto | **3.12.3** |
| Docker Engine | 27.x (runtime nvidia por defecto) |
| Arquitectura binaria | aarch64 (arm64) |

> **IMPORTANTE — Tres restricciones no negociables en JetPack 7.2:**
> 1. **Nunca `nvidia-smi`** — ese comando no existe en Jetson. Use `jtop`, `tegrastats` o `nvcc --version` dentro de contenedores.
> 2. **Nunca `sudo apt dist-upgrade`** — rompe el BSP de JetPack. Solo `sudo apt upgrade -y`.
> 3. **Nunca `--gpus all` en Docker** — no funciona en Jetson. Use `--runtime nvidia` con las variables de entorno adecuadas.

---

## 1.3 JetPack 7.2 vs JetPack 6.2 — Qué Cambió

Si viene de una instalación anterior con JetPack 6.2, esta tabla resume los cambios críticos que afectan todos los comandos del tutorial:

| Componente | JetPack 6.2 | **JetPack 7.2** | Impacto |
|------------|------------|-----------------|---------|
| Ubuntu | 22.04 LTS | **24.04 LTS** | Paquetes distintos, `pip` con venv obligatorio |
| Kernel | 5.15.185-tegra | **6.8.12-tegra** | Drivers actualizados |
| L4T | r36.5 | **r39.2** | BSP nuevo — reflash obligatorio |
| CUDA | 12.6 | **13.2.1** | Wheels de PyTorch distintos (`jp/v72`) |
| Python | 3.10 | **3.12** | Wheels con sufijo `cp312`, no `cp310` |
| Método de instalación | SDK Manager + Linux | **ISO unificado + Rufus** |  No requiere máquina Linux auxiliar |
| NemoClaw | No disponible | **1 comando** | Stack agéntico completo incluido |
| OpenClaw | No disponible | **Via NemoClaw** | Gateway WhatsApp integrado |
| Jetson Agent Skills | No disponible | **Integrado** | Automatización de workflows |
| `pip install` global | Permitido | **Bloqueado en Ubuntu 24.04** | Requiere `venv` o `--break-system-packages` |

**Lo que NO cambia:** NetworkManager, SSH, XRDP (mismo fix de pantalla negra), NoMachine, Docker, Ollama, GitHub SSH, tmux, aliases de bashrc.

---

## 1.4 Arquitectura del Sistema al Final de Este Libro

<!-- INFOGRAFÍA: Arquitectura del Sistema al Final del Libro — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


Al completar todos los capítulos, su Jetson quedará configurado como se muestra a continuación. Tenga presente esta imagen al seguir el tutorial — cada parte construye un componente de este sistema final:

```bash
WINDOWS 11 (192.168.1.33)
         │
         │  SSH :22           → terminal, administración
         │  NoMachine :4000   → GUI remota (XFCE4 virtual)
         │  XRDP :3389        → escritorio Windows nativo
         │  Túnel SSH :18789  → OpenClaw Web UI
         │
         ▼
JETSON AGX ORIN 64GB (192.168.1.100)
┌──────────────────────────────────────────────────────────────┐
│  Sistema base: Ubuntu 24.04 · multi-user.target             │
│  Performance: nvpmodel + jetson_clocks (MAXN/30W/15W)       │
│  Memoria: ZRAM 8GB + swap 16GB en NVMe                      │
│                                                              │
│  Capa de Inferencia (bajo demanda, NO en boot):             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Ollama     │  │  llama.cpp   │  │  vLLM (SBSA)     │   │
│  │  :11434     │  │  :8080       │  │  :8000           │   │
│  │  (nativo)   │  │  (Docker)    │  │  (Docker)        │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                                                              │
│  Capa Agéntica:                                             │
│  ┌──────────────────────┐  ┌───────────────────────────┐   │
│  │  OpenClaw Gateway    │  │  NemoClaw (proxy seguro)  │   │
│  │  :18789 (loopback)   │  │  sobre OpenClaw           │   │
│  │  WhatsApp + Skills   │  │                           │   │
│  └──────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  Herramientas de operación:                                 │
│  jetson-clean  jetson-audit  switch-model.sh  jtop          │
└──────────────────────────────────────────────────────────────┘
```

---

## 1.5 Material Necesario

Antes de comenzar, asegúrese de tener lo siguiente:

### Hardware imprescindible

| Elemento | Para qué se usa |
|----------|----------------|
| NVIDIA Jetson AGX Orin 64GB Developer Kit | El dispositivo principal |
| USB tipo A de mínimo 16 GB (vacío) | Crear el USB booteable con la ISO de JetPack 7.2 |
| Cable Ethernet + switch o router | Conectar el Jetson a la red local (más estable que WiFi) |
| Monitor + teclado + mouse | **Solo para el primer boot** (wizard OEM). Después es todo headless. |
| PC Windows 10/11 | Host de trabajo desde donde operará el Jetson por SSH |

### Software en Windows (antes de comenzar)

| Software | Dónde obtenerlo |
|----------|----------------|
| Rufus (para crear el USB booteable) | rufus.ie |
| SSH client (incluido en Windows 10+) | Ya instalado — abra PowerShell y ejecute `ssh` |
| NoMachine Client | nomachine.com/download |
| Terminal de Windows o PowerShell 7+ | Incluido en Windows 10/11 |

### Credenciales en línea (opcionales, para capítulos avanzados)

| Servicio | Para qué |
|----------|---------|
| Cuenta en huggingface.co + token API | Descargar modelos privativos (Gemma, Llama) — Capítulo 9 |
| Cuenta en ngc.nvidia.com + API key | Descargar modelos NGC (Cosmos Reason, Nemotron FP8) — Capítulo 10 |
| Cuenta en Telegram + bot creado con @BotFather | Vincular el agente OpenClaw — Capítulo 12 (recomendado) |
| Cuenta en WhatsApp Business | Vincular el agente OpenClaw como canal alternativo — Capítulo 12 (opcional) |
| Cuenta Google Cloud + Service Account | N8N con Google Sheets/Drive/Gmail — Capítulo 16 |

> **CONSEJO:** Las cuentas de HuggingFace y NGC son gratuitas. Los modelos de uso abierto (Qwen, Gemma, GPT OSS) no requieren token. El token de HuggingFace solo es necesario para modelos con licencia de acceso controlado (Llama, Gemma con gate).

> **¿Telegram o WhatsApp?** Este libro usa Telegram como canal principal para OpenClaw porque crear un bot es instantáneo (vía @BotFather, sin aprobación), la API es gratuita y sin límites prácticos, y la latencia es menor. WhatsApp requiere una cuenta Business verificada y un número de teléfono dedicado. Las instrucciones de WhatsApp se incluyen como alternativa en el Capítulo 12.

---

## 1.6 Verificación de Especificaciones del Sistema

Una vez que su Jetson esté en funcionamiento (después de el Capítulo 1), puede confirmar en cualquier momento que las especificaciones coinciden ejecutando:

```bash
# Diagnóstico completo del sistema
echo "=== DIAGNÓSTICO JETSON AGX ORIN ===" && \
echo "OS:      $(lsb_release -d | cut -f2)" && \
echo "Kernel:  $(uname -r)" && \
echo "JetPack: $(dpkg -l | grep 'nvidia-jetpack ' | awk '{print $3}' 2>/dev/null || echo 'verificar con: dpkg -l | grep jetpack')" && \
echo "L4T:     $(cat /etc/nv_tegra_release 2>/dev/null | head -1 || echo 'ver /etc/nv_tegra_release')" && \
echo "CUDA:    $(nvcc --version 2>/dev/null | grep release | awk '{print $5}' | tr -d ',' || echo 'nvcc no en PATH — ver Capítulo 2')" && \
echo "Python:  $(python3 --version)" && \
echo "RAM:     $(free -h | awk '/^Mem:/{print $2}') total, $(free -h | awk '/^Mem:/{print $7}') libres" && \
echo "IP:      $(hostname -I | awk '{print $1}')" && \
echo "Poder:   $(sudo nvpmodel -q 2>/dev/null | grep 'NV Power Mode' || echo 'nvpmodel -q')"
```

```bash
# Salida esperada en un Jetson AGX Orin 64GB con JetPack 7.2
=== DIAGNÓSTICO JETSON AGX ORIN ===
OS:      Ubuntu 24.04.4 LTS
Kernel:  6.8.12-1021-tegra
JetPack: 7.2-b187
L4T:     # R39 (release), REVISION: 2.0, ...
CUDA:    13.2.1,
Python:  Python 3.12.3
RAM:     62Gi total, 50Gi libres
IP:      192.168.1.100
Poder:   NV Power Mode: MODE_30W_2CORE
```

---

> **A partir de el Capítulo 1, todos los comandos se ejecutan en la terminal del Jetson** (salvo los que llevan el comentario "# En Windows PowerShell"). El Capítulo 1 cubre el primer encendido y la configuración inicial del sistema operativo — el único momento en que necesitará un monitor físico conectado al Jetson.
