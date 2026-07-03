# Capítulo 11 — Stack de Inteligencia Artificial Agéntica: OpenClaw, NemoClaw, Jetson Agent Skills y Open WebUI

## Introducción

Ejecutar un modelo de lenguaje en el Jetson es solo la primera mitad del trabajo. La segunda mitad —y la más valiosa en producción— consiste en convertir ese modelo en un **agente**: un sistema que recibe solicitudes, planifica acciones, ejecuta herramientas y entrega resultados sin intervención humana. En JetPack 7.2, NVIDIA ha consolidado un stack agéntico completo que corre enteramente en el dispositivo y que se puede controlar desde WhatsApp, un navegador web o la terminal.

Este capítulo cubre las cuatro capas del stack:

1. **OpenClaw** — el agente central que conecta el modelo de lenguaje con el mundo exterior (WhatsApp, herramientas web, búsqueda, memoria de sesión).
2. **NemoClaw** — la capa de seguridad y privacidad que envuelve a OpenClaw con políticas L7, aislamiento de sistema de archivos y control de red.
3. **Jetson Agent Skills** — paquetes de instrucciones ejecutables por el agente para tareas específicas del Jetson: optimización de memoria, benchmarking de modelos, configuración del BSP.
4. **Open WebUI** — interfaz gráfica estilo ChatGPT que conecta a todos los motores de inferencia (Ollama, vLLM, llama.cpp) desde cualquier navegador de la red local.

> **IMPORTANTE:** Antes de comenzar este capítulo, asegúrese de tener al menos un motor de inferencia activo (Capítulo 12). OpenClaw requiere que el modelo esté sirviendo peticiones en el momento del arranque del gateway. Sin modelo activo, OpenClaw inicia pero no puede generar respuestas.

---

## 11.1 OpenClaw — El Agente Central

### 11.1.1 Arquitectura de OpenClaw en JetPack 7.2

OpenClaw actúa como intermediario inteligente entre los canales de entrada (WhatsApp, navegador, terminal) y los backends de inferencia (vLLM, llama.cpp, Ollama). El modelo de lenguaje es el "cerebro"; OpenClaw es el "sistema nervioso" que conecta ese cerebro con el mundo.

<!-- INFOGRAFÍA: Arquitectura de OpenClaw en el Jetson AGX Orin 64GB — diagrama de flujo mostrando canales de entrada (WhatsApp, Navegador, Terminal) → OpenClaw Gateway :18789 → router de solicitudes → backends (vLLM :8000, llama.cpp :8080, Ollama :11434) → modelo LLM activo. Paleta NVIDIA #0F3D3D / #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light — pendiente de diseño gráfico -->

```bash
Arquitectura de OpenClaw en el Jetson AGX Orin 64GB
════════════════════════════════════════════════════

Windows / Teléfono            Jetson AGX Orin 64GB
─────────────────             ─────────────────────────────────────────────
  WhatsApp App  ──────────→   OpenClaw Gateway  :18789
  Navegador Web ──────────→       │
  Terminal TUI  ──────────→       ▼ (router de solicitudes)
                            ┌─────────────────────────────────┐
                            │  Backend activo (uno a la vez)  │
                            │  vLLM :8000  llama.cpp :8080    │
                            │  Ollama :11434                  │
                            └─────────────────────────────────┘
                                    │
                            google/gemma-4-E2B-it (u otro modelo)
                            (responde en ~1-3 segundos @ 30W)
```

La restricción principal de la memoria unificada del Jetson se aplica aquí: **solo un modelo grande puede estar activo a la vez**. El script `switch-model.sh` (documentado en el Capítulo 12) gestiona este ciclo de vida automáticamente y actualiza la configuración de OpenClaw después de cada cambio.

### 11.1.2 Prerrequisitos para OpenClaw

OpenClaw es una aplicación Node.js. JetPack 7.2 incluye Node.js v22 en su imagen base, pero si la instalación no está disponible, ejecute:

```bash
# Verificar si Node.js ya está instalado
node --version
npm --version

# Salida esperada:
# v22.23.1
# 10.9.x
```

```bash
# Si Node.js no está instalado: agregar el repositorio oficial de NodeSource
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar (toma ~2 minutos)
node --version   # v22.23.1
npm --version    # 10.x.x
```

> **NOTA:** No use el Node.js del repositorio de Ubuntu 24.04 (`apt install nodejs` sin el repositorio de NodeSource). Esa versión es la 18.x, demasiado antigua para OpenClaw.

### 11.1.3 Instalación de OpenClaw

El método recomendado utiliza el instalador oficial de OpenClaw, que verifica la versión de Node, instala el daemon y ejecuta el onboarding inicial:

```bash
# Método recomendado: instalador oficial
# (tarda 2-3 minutos — descarga el paquete npm y configura el servicio systemd)
curl -fsSL https://openclaw.ai/install.sh | bash
```

```bash
# Salida esperada al final del instalador:
# [OK] OpenClaw 2026.6.10 installed
# [OK] Node.js v22.23.1 detected
# [OK] Daemon configured as systemd user service
# → Run 'openclaw onboard' to configure your first agent
```

```bash
# Si el comando 'openclaw' no se encuentra después de instalar:
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verificar instalación
openclaw --version
# Esperado: OpenClaw 2026.6.10
```

> **IMPORTANTE:** El paquete npm se llama `openclaw` (sin prefijo `@`). Si en alguna guía ve `@openclaw/cli`, ese nombre de paquete no existe en el registro de npm. El nombre correcto es simplemente `openclaw`.

**Método alternativo (instalación manual):**

```bash
# Si el instalador oficial falla por restricciones de red:
npm install -g openclaw@latest
openclaw onboard --install-daemon

# Verificar
openclaw --version   # 2026.6.10 o superior
```

### 11.1.4 Configuración de Producción de OpenClaw

La configuración de OpenClaw reside en `~/.openclaw/openclaw.json`. A continuación se presenta la configuración completa verificada en producción con todos los parches aplicados.

Primero, genere un token de autenticación para el gateway:

```bash
# Generar token de seguridad para el gateway
GATEWAY_TOKEN=$(openclaw doctor --generate-gateway-token 2>/dev/null \
  | grep -o '[a-f0-9]\{20,\}' | head -1)
echo "Token generado: $GATEWAY_TOKEN"

# Si el comando anterior no funciona, usar OpenSSL directamente:
GATEWAY_TOKEN=$(openssl rand -hex 24)
echo "Token generado: $GATEWAY_TOKEN"
```

Luego, cree la configuración completa:

```bash
# Hacer backup de la configuración existente (si existe)
cp ~/.openclaw/openclaw.json \
   ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Escribir la configuración completa de producción
cat > ~/.openclaw/openclaw.json << EOF
{
  "agents": {
    "defaults": {
      "workspace": "/home/jetson/.openclaw/workspace",
      "models": {
        "vllm/google/gemma-4-E2B-it": {}
      },
      "model": {
        "primary": "vllm/google/gemma-4-E2B-it"
      },
      "compaction": {
        "reserveTokensFloor": 6000
      },
      "timeoutSeconds": 300,
      "memorySearch": {
        "enabled": false
      },
      "bootstrapMaxChars": 20000,
      "bootstrapTotalMaxChars": 150000,
      "contextInjection": "always"
    }
  },
  "gateway": {
    "mode": "local",
    "auth": {
      "mode": "token",
      "token": "${GATEWAY_TOKEN}"
    },
    "port": 18789,
    "bind": "loopback",
    "tailscale": { "mode": "off", "resetOnExit": false },
    "controlUi": { "allowInsecureAuth": true },
    "nodes": {
      "denyCommands": [
        "camera.snap", "camera.clip", "screen.record",
        "contacts.add", "calendar.add", "reminders.add",
        "sms.send", "sms.search"
      ]
    }
  },
  "session": {
    "dmScope": "per-channel-peer"
  },
  "tools": {
    "profile": "full",
    "web": {
      "search": { "provider": "brave", "enabled": true }
    }
  },
  "plugins": {
    "entries": {
      "vllm": { "enabled": true },
      "whatsapp": { "enabled": true },
      "brave": {
        "config": { "webSearch": { "apiKey": "TU_BRAVE_API_KEY" } },
        "enabled": true
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "vllm": {
        "baseUrl": "http://127.0.0.1:8000/v1",
        "api": "openai-completions",
        "apiKey": "vllm-local",
        "timeoutSeconds": 300,
        "models": [
          {
            "id": "google/gemma-4-E2B-it",
            "name": "Gemma 4 E2B (local vLLM)",
            "reasoning": false,
            "input": ["text", "image"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 65536,
            "maxTokens": 4096
          }
        ]
      }
    }
  },
  "auth": {
    "profiles": {
      "vllm:default": { "provider": "vllm", "mode": "api_key" }
    }
  },
  "channels": {
    "whatsapp": {
      "enabled": true,
      "selfChatMode": false,
      "dmPolicy": "pairing"
    }
  },
  "commands": {
    "ownerAllowFrom": ["whatsapp:+57XXXXXXXXXX"]
  },
  "hooks": {
    "internal": {
      "enabled": true,
      "entries": {
        "session-memory": { "enabled": true },
        "boot-md": { "enabled": true },
        "bootstrap-extra-files": { "enabled": true },
        "command-logger": { "enabled": true },
        "compaction-notifier": { "enabled": true }
      }
    }
  }
}
EOF

# Validar que el JSON es correcto
python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null \
  && echo "[OK] Config JSON válida" \
  || echo "[ERROR] Error en JSON — revisar con: python3 -m json.tool ~/.openclaw/openclaw.json"

# Aplicar la configuración y reiniciar el gateway
openclaw gateway restart
sleep 5
openclaw doctor
```

```bash
# Salida esperada de 'openclaw doctor':
# [OK] Gateway: running on port 18789
# [OK] Model: vllm/google/gemma-4-E2B-it (connected)
# [OK] Tools profile: full
# [OK] WhatsApp: enabled (pending pairing)
```

**Tabla de errores comunes en la configuración (todos verificados en producción):**

| Campo incorrecto | Valor que falla | Valor correcto | Consecuencia del error |
|-----------------|-----------------|----------------|------------------------|
| `tools.profile` | `"default"` | `"full"` | WhatsApp no puede responder mensajes |
| `tools.profile` | `"coding"` | `"full"` | Perfil coding elimina la herramienta de respuesta WhatsApp |
| `models.providers.vllm.apiKey` | `"VLLM_API_KEY"` | `"vllm-local"` | Error de autenticación contra el endpoint local |
| `models.providers.vllm.models[].id` | `"vllm/google/gemma-4-E2B-it"` | `"google/gemma-4-E2B-it"` | El prefijo `vllm/` no va en el `id` del modelo |
| `agents.defaults.model.primary` | `"vllm/google/gemma4-..."` | `"vllm/google/gemma-4-..."` | La guión en `gemma-4` es obligatoria |
| `models.providers.vllm.models[].contextWindow` | `128000` | `65536` | Debe coincidir con `--max-model-len` del contenedor vLLM |
| `models.providers.vllm.models[].maxTokens` | `65536` | `4096` | Si maxTokens == contextWindow, no queda espacio para el input |
| `agents.defaults.memorySearch.enabled` | `true` | `false` | Falla sin API key de OpenAI configurada |

### 11.1.5 Web UI de OpenClaw desde Windows

OpenClaw incluye una interfaz web que escucha en el puerto 18789 del Jetson, enlazada únicamente a `loopback` (127.0.0.1) por seguridad. Para acceder desde un equipo Windows en la misma red local, es necesario crear un túnel SSH.

> **ADVERTENCIA:** El túnel SSH se ejecuta **desde Windows** hacia el Jetson, NO al revés. Si intenta ejecutar el SSH desde el propio Jetson apuntando a sí mismo, recibirá el error `Permission denied (publickey)`.

```powershell
# En Windows PowerShell — mantener esta ventana abierta mientras usa el Web UI
# Reemplazar 192.168.1.100 con la IP de su Jetson
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

Una vez activo el túnel, abra en el navegador de Windows:

```bash
http://localhost:18789/#token=TU_TOKEN_AQUI
```

Para obtener el token desde el Jetson:

```bash
# En el Jetson (via SSH en otra terminal)
openclaw config get gateway.auth.token
# Salida: abc123def456...  (su token de 48 caracteres hexadecimales)
```

**Alternativa sin túnel SSH — NoMachine:**

Si tiene NoMachine instalado en el Jetson (Capítulo 7), conéctese con el cliente NoMachine desde Windows y abra el navegador dentro del escritorio virtual del Jetson:

```bash
http://127.0.0.1:18789/#token=TU_TOKEN
```

Esta opción es más sencilla y no requiere mantener abierto el túnel SSH.

### 11.1.6 Canal WhatsApp — Configuración Inicial

WhatsApp es el canal principal de interacción con el agente OpenClaw. La configuración inicial requiere escanear un código QR desde el teléfono.

```bash
# Paso 1: Ejecutar el asistente de onboarding
# Aparecerá un código QR en la terminal (o abrir http://localhost:18789 para verlo en el navegador)
openclaw onboard

# Durante el asistente, seleccionar:
# OK Channel: WhatsApp
# OK dmPolicy: Pairing (recomendado — cada nuevo contacto recibe un código)
# OK Search provider: Brave Search (requiere API key en brave.com/search/api/)
# OK Hooks: habilitar los 5 disponibles
# OK Gateway service: Install (registra como servicio systemd de usuario)
# OK Hatch: Browser (accede via túnel desde Windows)
```

```bash
# Paso 2: Escanear el código QR con el teléfono
# En WhatsApp → Configuración → Dispositivos vinculados → Vincular dispositivo
# Apuntar la cámara al QR en la terminal del Jetson

# Paso 3: Aprobar el número de teléfono que usará el agente
openclaw pairing list whatsapp
# Salida: pending  +573XXXXXXXXX  code: A7K2M9

# Aprobar usando el código del paso anterior
openclaw pairing approve whatsapp TU_CODIGO_6_CHARS
# Salida esperada:
# Approved whatsapp sender +573XXXXXXXXX
# Command owner configured whatsapp:+573XXXXXXXXX  ← asignado automáticamente como propietario

# Paso 4: Verificar que WhatsApp está conectado
openclaw channels status --probe
# Salida esperada:
# WhatsApp default: enabled, configured, linked, running, connected [OK]
```

**Si WhatsApp se desconecta** (los logs muestran `session logged out` o `QR required`):

```bash
# Re-autenticar escaneando un nuevo QR
openclaw channels auth login whatsapp
```

**Políticas de acceso de WhatsApp:**

```bash
# Política pairing (defecto): nuevos contactos reciben código de 6 caracteres
openclaw config set channels.whatsapp.dmPolicy pairing

# Política allowlist: solo números pre-autorizados, el resto es rechazado silenciosamente
openclaw config set channels.whatsapp.dmPolicy allowlist
openclaw config set channels.whatsapp.dmAllowFrom '["+573XXXXXXXXX","+571XXXXXXXX"]'
```

### 11.1.7 Gestión del Gateway en el Día a Día

```bash
# Ver estado completo del gateway
openclaw gateway status

# Reiniciar (necesario después de cambiar openclaw.json)
openclaw gateway restart && sleep 3 && openclaw gateway status

# Ver logs en tiempo real
openclaw logs --follow

# Filtrar solo logs de WhatsApp
openclaw logs --follow | grep -i whatsapp

# Filtrar solo errores
openclaw logs --follow | grep -i error

# Interfaz TUI interactiva en la terminal
openclaw tui
# Dentro del TUI: /new → nueva sesión | /compact → compactar contexto | /quit → salir

# Verificar qué herramientas tiene disponibles el agente
openclaw doctor | grep -A 20 "Skills"

# Verificar que el endpoint del modelo está respondiendo antes de depurar OpenClaw
curl -s http://localhost:8000/v1/models \
  | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
# Salida esperada:
# google/gemma-4-E2B-it
```

### 11.1.8 Skills de OpenClaw

Los skills amplían las capacidades del agente con herramientas adicionales. OpenClaw 2026.6.x incluye por defecto: memory core (memoria entre sesiones), web search (búsqueda Brave), y file transfer.

```bash
# Ver skills instalados y disponibles
openclaw skills list --verbose

# Verificar estado de todos los skills
openclaw skills check

# Instalar un skill adicional del registro ClawHub
openclaw skills install <nombre-del-skill>

# Verificar instalación
openclaw skills check
```

> **NOTA:** El catálogo completo de skills está disponible en la documentación oficial de OpenClaw en `docs.openclaw.ai/clawhub`. Los skills más útiles para el Jetson incluyen: `jetson-system` (información del hardware), `file-manager` (gestión de archivos via chat) y `code-executor` (ejecutar scripts Python desde WhatsApp).

---

## 11.2 NemoClaw — Capa de Seguridad sobre OpenClaw

NemoClaw agrega privacidad y control de seguridad a OpenClaw mediante un proxy de políticas que intercepta todas las solicitudes antes de que lleguen al gateway. Con JetPack 7.2, Jetson viene preconfigurado con las dependencias necesarias para NemoClaw sin configuración manual adicional.

### 11.2.1 Arquitectura de NemoClaw

```bash
Arquitectura NemoClaw — JetPack 7.2
═══════════════════════════════════

 Navegador / WhatsApp
        │
        ▼ puerto 18789
 ┌─────────────────────┐
 │  policy-proxy.js    │   ← NemoClaw Security Layer
 │  ─────────────────  │
 │  • Políticas L7 REST│
 │  • Aislamiento de   │
 │    sistema de arch. │
 │  • Control de red   │
 └─────────────────────┘
        │
        ▼ puerto 18788
 OpenClaw Gateway
        │
 ┌──────┴──────┐
 │             │
 vLLM :8000  build.nvidia.com
 (local,      (cloud fallback,
  privado)     deshabilitado por defecto)
```

NemoClaw añade tres capas de protección que OpenClaw por sí solo no tiene:
1. **Políticas L7 REST**: puede bloquear rutas de API específicas (por ejemplo, prohibir que el agente llame a `files.delete`)
2. **Aislamiento del sistema de archivos**: el agente solo puede leer/escribir en directorios explícitamente permitidos
3. **Control de red**: puede prohibir que el agente haga solicitudes hacia internet o hacia IPs privadas de la red corporativa

### 11.2.2 Instalación con un Solo Comando (JP 7.2)

```bash
# Instalación oficial NVIDIA — un solo comando
# JetPack 7.2 incluye todas las dependencias; tarda 3-5 minutos
curl -fsSL nvidia.com/nemoclaw.sh | bash

# Verificar instalación
nemoclaw --version 2>/dev/null || \
  python3 -c "import nemoclaw; print('NemoClaw instalado')" 2>/dev/null
```

### 11.2.3 Verificación de la Instalación y Gestión Manual

Una vez instalado con el script oficial, gestione NemoClaw directamente mediante su CLI:

```bash
# Verificar estado del proxy
nemoclaw status
# Salida esperada:
# NemoClaw proxy: running on :18789
# OpenClaw gateway: connected
# Inference backend: connected

# Detener el proxy
nemoclaw stop

# Iniciar el proxy
nemoclaw start

# Reiniciar (útil tras cambio de modelo de inferencia)
nemoclaw restart
```

> **ADVERTENCIA:** El script `curl -fsSL nvidia.com/nemoclaw.sh | bash` crea el servicio pero **no lo habilita en boot** de forma automática. Esto es correcto para la arquitectura clean-start del Jetson. Utilice `nemoclaw start` cuando necesite el proxy activo.

### 11.2.4 Recuperación Después de un Reinicio

NemoClaw no persiste entre reinicios salvo que se configure explícitamente (no recomendado en esta guía). La secuencia de recuperación tras reinicio es:

```bash
# Secuencia de restauración post-reinicio

# Paso 1: Asegurarse de que el motor de inferencia está activo
# (Ejecute start-qwen35, start-nemotron u otro alias antes de NemoClaw)
curl -sf http://localhost:8000/v1/models > /dev/null || \
  curl -sf http://localhost:11434/api/tags > /dev/null
echo "[OK] Motor de inferencia activo"

# Paso 2: Iniciar NemoClaw
nemoclaw start

# Paso 3: Verificar el estado
nemoclaw status

# Paso 4: Verificar el endpoint del gateway
curl -sf http://localhost:18789/health && echo "[OK] Gateway en :18789 activo"
```

> **CONSEJO:** Añada el alias `start-nemoclaw='nemoclaw start'` a `~/.bashrc` para lanzarlo bajo demanda. El Capítulo 15 §15.8 documenta el patrón completo de aliases start/stop para todos los servicios del stack.

### 11.2.5 Configurar el Proveedor de Inferencia Local

Para ejecutar NemoClaw en modo completamente offline y privado, apuntarlo al servidor vLLM o Ollama local:

```bash
# Configurar NemoClaw para usar vLLM local (sin dependencia de internet)
nemoclaw config set \
  --inference-provider local \
  --base-url http://localhost:8000/v1 \
  --model qwen35

# Para usar Ollama en lugar de vLLM:
nemoclaw config set \
  --inference-provider local \
  --base-url http://localhost:11434/v1 \
  --model qwen3:7b

# Verificar la configuración activa
nemoclaw config show
# Salida esperada:
# inference.provider: local
# inference.base-url: http://localhost:8000/v1
# inference.model: qwen35
# status: connected [OK]
```

---

## 11.3 Jetson Agent Skills — Habilidades Automatizadas para el Dispositivo

Los Jetson Agent Skills son paquetes de instrucciones ejecutables por el agente que automatizan tareas específicas del hardware Jetson: optimización de memoria, benchmarking de modelos, configuración del BSP (Board Support Package), perfiles de ventilador y diagnósticos de hardware.

Existen dos repositorios principales:
- **jetson-device-skills**: Habilidades de software (memoria, benchmarking, diagnósticos)
- **jetson-bsp-skills**: Habilidades de hardware (BSP, carrier board, I/O, energía)

### 11.3.1 Jetson Device Skills — Instalación

```bash
# Clonar Jetson Device Skills
git clone https://github.com/NVIDIA-AI-IOT/jetson-device-skills.git \
  ~/projects/jetson-device-skills

cd ~/projects/jetson-device-skills

# Activar el entorno virtual del Jetson e instalar dependencias
source ~/venvs/llm/bin/activate
pip install -r requirements.txt 2>/dev/null || \
  pip install openai requests pydantic fastapi uvicorn

# Ver skills disponibles
ls skills/ 2>/dev/null || cat README.md | head -80
```

**Categorías de skills disponibles:**

| Categoría | Qué Automatiza | Valor Práctico |
|-----------|----------------|----------------|
| Memory Optimization | Ajusta reservas DRAM, configuraciones del kernel, procesos de usuario | Libera hasta 4-6 GB para LLMs grandes |
| Model Benchmarking | Mide tokens/segundo y latencia entre modelos y motores | Elige el mejor modelo para su caso de uso sin prueba y error |
| Linux Customization | Configuración BSP, I/O, velocidades de reloj, perfil de ventilador | Preparación para despliegue en producción |
| Package Recommendations | Sugiere el contenedor óptimo para la carga de trabajo | Ahorra horas de investigación de compatibilidad |
| Diagnostics | Verificaciones de salud de GPU, térmica y memoria | Depuración rápida de problemas de rendimiento |

### 11.3.2 Skill de Optimización de Memoria

El skill de optimización de memoria analiza el estado actual del sistema y sugiere (y opcionalmente aplica) configuraciones que liberan RAM para los modelos LLM:

```bash
# Verificar uso de memoria antes de la optimización
free -h
# Salida ejemplo:
#               total        used        free      shared  buff/cache   available
# Mem:           59Gi        12Gi        40Gi       1.2Gi       6.8Gi        46Gi

# Ejecutar el skill de optimización de memoria
cd ~/projects/jetson-device-skills
source ~/venvs/llm/bin/activate

python3 run_skill.py \
  --skill memory_optimization \
  --backend ollama \
  --base-url http://localhost:11434 \
  --model gemma4:latest

# El agente analizará el sistema, propondrá acciones y esperará su aprobación
# antes de aplicar cambios (modo interactivo por defecto)

# Verificar memoria después de la optimización
free -h
```

### 11.3.3 Skill de Benchmarking de Modelos

Este skill mide el rendimiento de diferentes modelos y motores de inferencia y genera un reporte comparativo:

```bash
# Benchmark de modelos disponibles en los motores activos
cd ~/projects/jetson-device-skills
source ~/venvs/llm/bin/activate

python3 run_skill.py \
  --skill model_benchmarking \
  --models "gemma4:latest,qwen3:8b" \
  --engines "ollama,vllm" \
  --output ~/jetson-ai-data/benchmark_results.json

# Ver resultados estructurados
python3 -m json.tool ~/jetson-ai-data/benchmark_results.json

# Salida esperada (extracto):
# {
#   "results": [
#     {"model": "gemma4:2b", "engine": "ollama", "tokens_per_sec": 45.2, "ttft_ms": 820},
#     {"model": "gemma4:2b", "engine": "vllm",   "tokens_per_sec": 38.1, "ttft_ms": 1100},
#     {"model": "qwen3:8b",  "engine": "ollama", "tokens_per_sec": 22.4, "ttft_ms": 1350}
#   ]
# }
```

> **NOTA:** El Capítulo 14 de este libro cubre el benchmarking en detalle: top 10 modelos recomendados para el Jetson AGX Orin 64GB, metodología de medición y tablas comparativas completas.

### 11.3.4 Jetson BSP Skills — Configuración del Board Support Package

Los BSP Skills automatizan tareas de configuración a nivel de hardware que normalmente requerirían editar manualmente archivos de configuración del kernel o del gestor de energía:

```bash
# Clonar Jetson BSP Skills
git clone https://github.com/NVIDIA-AI-IOT/jetson-bsp-skills.git \
  ~/projects/jetson-bsp-skills

cd ~/projects/jetson-bsp-skills
source ~/venvs/llm/bin/activate
pip install -r requirements.txt 2>/dev/null

# Ver skills disponibles y documentación
cat README.md
```

**Tareas que automatizan los BSP Skills:**

```bash
# Ejemplos de habilidades BSP (la sintaxis exacta varía según la versión del repositorio)
# Revisar README.md del repositorio para la sintaxis actual

# Configuración de curva de ventilador personalizada
python3 run_skill.py --skill fan_profile --mode quiet   # silencioso (desarrollo)
python3 run_skill.py --skill fan_profile --mode performance  # máximo flujo de aire

# Configuración de perfil de energía personalizado
python3 run_skill.py --skill power_profile --mode maxn    # modo MAXN (50W, máximo rendimiento)
python3 run_skill.py --skill power_profile --mode 30w     # modo 30W (equilibrado)

# Bring-up de carrier board personalizado (para hardware propio)
python3 run_skill.py --skill carrier_board_bringup --config my_board.yaml

# Diagnóstico completo del hardware
python3 run_skill.py --skill diagnostics --full-report \
  --output ~/jetson-ai-data/hardware_report.json
```

> **CONSEJO:** Los BSP Skills son especialmente valiosos en proyectos de robótica e IoT donde el Jetson se integra en una placa carrier personalizada. En lugar de depurar manualmente los archivos de Device Tree, el agente puede guiar el proceso a través de una interfaz de chat.

---

## 11.4 Open WebUI — Interfaz Gráfica para Todos los Motores

Open WebUI proporciona una interfaz web estilo ChatGPT que conecta con cualquier motor de inferencia compatible con la API de OpenAI. Es la opción más accesible para usuarios que prefieren una interfaz gráfica en lugar de la terminal o WhatsApp.

### 11.4.1 Instalación de Open WebUI

```bash
# Iniciar Open WebUI conectado a Ollama
# (tarda 3-5 minutos en descargar la imagen la primera vez)
docker run -d \
  --name open-webui \
  --restart no \
  --network host \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  ghcr.io/open-webui/open-webui:main

# Abrir el firewall para acceso desde la red local
sudo ufw allow 3000/tcp comment "Open WebUI"

# Esperar a que la aplicación arranque (30-60 segundos)
docker logs open-webui --follow
# Esperar la línea: "Application startup complete."
# Presionar Ctrl+C para salir de los logs (el contenedor sigue corriendo)
```

```bash
# Verificar que Open WebUI está activo
curl -s http://localhost:3000 | grep -o '<title>[^<]*</title>'
# Salida esperada: <title>Open WebUI</title>
```

Acceda desde el navegador en su red local:

```bash
http://192.168.1.100:3000
```

En la primera visita, Open WebUI le pedirá crear una cuenta de administrador local (sin conexión a internet — los datos se guardan en el volumen Docker `open-webui`).

> **ADVERTENCIA:** El puerto por defecto de Open WebUI es 8080, lo que genera conflicto con el servidor llama.cpp (también en 8080). En la configuración de este libro, Open WebUI usa el **puerto 3000** para evitar este conflicto. Si ya tiene Open WebUI corriendo en 8080, detenga el contenedor y reinícielo con `-p 3000:8080`.

### 11.4.2 Conectar Open WebUI a Múltiples Motores de Inferencia

Open WebUI puede conectarse simultáneamente a Ollama y a cualquier endpoint compatible con la API de OpenAI (vLLM, llama.cpp):

```bash
# Reconfigurar Open WebUI con múltiples backends
docker stop open-webui
docker rm open-webui

docker run -d \
  --name open-webui \
  --restart no \
  --network host \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -e OPENAI_API_BASE_URLS="http://localhost:8000/v1;http://localhost:8080/v1" \
  -e OPENAI_API_KEYS="vllm-local;llama-local" \
  ghcr.io/open-webui/open-webui:main
```

Alternativamente, desde la interfaz gráfica:
- Configuración (icono de engranaje) → Connections → OpenAI API
- Agregar URL: `http://localhost:8000/v1` (vLLM) con API Key: `vllm-local`
- Agregar URL: `http://localhost:8080/v1` (llama.cpp) con API Key: cualquier texto

### 11.4.3 Configuración para Open WebUI como Interfaz de OpenClaw

Open WebUI también puede usarse como interfaz de chat para el gateway OpenClaw, apuntando al endpoint local de vLLM que OpenClaw utiliza:

```bash
# El modelo activo en vLLM ya está disponible en Open WebUI automáticamente
# si configuró OPENAI_API_BASE_URLS con http://localhost:8000/v1

# Para verificar que Open WebUI ve el modelo de vLLM:
curl -s http://localhost:8000/v1/models \
  | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
# Salida esperada: google/gemma-4-E2B-it

# En Open WebUI → seleccionar el modelo en el desplegable superior izquierdo
# Los mismos modelos que vLLM sirve aparecen disponibles automáticamente
```

### 11.4.4 Mapa de Puertos del Stack Agéntico Completo

Una vez instalados todos los componentes, el Jetson expone los siguientes puertos:

| Puerto | Servicio | Descripción | Acceso desde Red Local |
|--------|---------|-------------|------------------------|
| 11434 | Ollama API | Motor de inferencia Ollama | Sí (`http://IP:11434`) |
| 8000 | vLLM API | Motor de inferencia vLLM (SBSA) | Sí (`http://IP:8000/v1`) |
| 8080 | llama.cpp server | Motor de inferencia llama.cpp | Sí (`http://IP:8080/v1`) |
| 18789 | OpenClaw Gateway | Gateway agéntico (solo loopback) | Solo via túnel SSH |
| 3000 | Open WebUI | Interfaz gráfica web | Sí (`http://IP:3000`) |

> **IMPORTANTE:** El puerto 18789 (OpenClaw Gateway) está enlazado a `127.0.0.1` (loopback), lo que significa que **no es accesible directamente desde la red local**. Para acceder desde Windows, use el túnel SSH descrito en la sección 13.1.5. Esta restricción es intencional por seguridad: el gateway tiene acceso completo a las herramientas del sistema.

---

## 11.5 Verificación del Stack Completo

Ejecute este script de verificación para confirmar que todos los componentes están operativos:

```bash
#!/bin/bash
# verify-agentic-stack.sh — Verificación completa del stack agéntico

echo "═══ Verificación del Stack Agéntico — $(date) ═══"
echo ""

# 1. Verificar motores de inferencia
echo "─── Motores de inferencia ───"
check_port() {
    local name=$1
    local port=$2
    if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1 || \
       curl -sf "http://localhost:${port}/api/tags" > /dev/null 2>&1 || \
       curl -sf "http://localhost:${port}/v1/models" > /dev/null 2>&1; then
        echo "  [OK] ${name} en :${port} — ACTIVO"
    else
        echo "  [ERROR] ${name} en :${port} — INACTIVO"
    fi
}

check_port "Ollama"    11434
check_port "vLLM"      8000
check_port "llama.cpp" 8080

echo ""

# 2. Verificar OpenClaw
echo "─── OpenClaw Gateway ───"
if openclaw gateway status 2>/dev/null | grep -q "running"; then
    echo "  [OK] OpenClaw Gateway — ACTIVO en :18789"
else
    echo "  [ERROR] OpenClaw Gateway — INACTIVO"
    echo "     → Ejecute: openclaw gateway restart"
fi

echo ""

# 3. Verificar Open WebUI
echo "─── Open WebUI ───"
if curl -sf http://localhost:3000 > /dev/null; then
    echo "  [OK] Open WebUI — ACTIVO en :3000"
else
    echo "  [ERROR] Open WebUI — INACTIVO"
    echo "     → Ejecute: docker start open-webui"
fi

echo ""

# 4. Estado de memoria
echo "─── Memoria del Sistema ───"
free -h | awk '/^Mem:/{printf "  Total: %s | Usada: %s | Disponible: %s\n", $2, $3, $7}'

echo ""

# 5. Modelos activos en vLLM (si está corriendo)
if curl -sf http://localhost:8000/v1/models > /dev/null 2>&1; then
    echo "─── Modelos activos en vLLM ───"
    curl -s http://localhost:8000/v1/models \
      | python3 -c "import sys,json; [print('  •', m['id']) for m in json.load(sys.stdin)['data']]"
fi

echo ""
echo "═══ Verificación completada ═══"
```

```bash
# Ejecutar el script de verificación
chmod +x ~/scripts/verify-agentic-stack.sh
~/scripts/verify-agentic-stack.sh
```

```bash
# Salida esperada con todos los componentes activos:
# ═══ Verificación del Stack Agéntico — Sat Jun 28 14:32:15 UTC 2026 ═══
#
# ─── Motores de inferencia ───
#   [ERROR] Ollama    en :11434 — INACTIVO   (normal si vLLM está activo)
#   [OK] vLLM      en :8000  — ACTIVO
#   [ERROR] llama.cpp en :8080  — INACTIVO   (normal — solo uno activo a la vez)
#
# ─── OpenClaw Gateway ───
#   [OK] OpenClaw Gateway — ACTIVO en :18789
#
# ─── Open WebUI ───
#   [OK] Open WebUI — ACTIVO en :3000
#
# ─── Memoria del Sistema ───
#   Total: 59Gi | Usada: 18Gi | Disponible: 38Gi
#
# ─── Modelos activos en vLLM ───
#   • google/gemma-4-E2B-it
#
# ═══ Verificación completada ═══
```

---

## 11.6 Solución de Problemas Comunes

### OpenClaw: `Error: model not found`

**Causa:** El modelo no está cargado en vLLM o el endpoint no está respondiendo.

```bash
# Verificar que vLLM está activo y con el modelo correcto
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# Si vLLM no está corriendo, iniciarlo con switch-model.sh
~/scripts/switch-model.sh gemma-vllm

# Reiniciar OpenClaw después
openclaw gateway restart
```

### OpenClaw: `Permission denied` al abrir el Web UI

**Causa:** El túnel SSH está siendo ejecutado desde el Jetson en lugar de desde Windows.

```bash
# INCORRECTO (desde el Jetson):
ssh -N -L 18789:127.0.0.1:18789 localhost   # ← No hacer esto

# CORRECTO (desde Windows PowerShell):
ssh -N -L 18789:127.0.0.1:18789 jetson@192.168.1.100
```

### WhatsApp: Los mensajes no generan respuesta del agente

**Causa más común:** El perfil de herramientas está en `"default"` o `"coding"` en lugar de `"full"`.

```bash
# Verificar el perfil actual
grep '"profile"' ~/.openclaw/openclaw.json
# Si muestra "default" o "coding", cambiar a "full":

openclaw config set tools.profile full
openclaw gateway restart
```

### Open WebUI: Puerto 3000 no accesible desde Windows

```bash
# Verificar que el firewall permite el puerto 3000
sudo ufw status | grep 3000
# Si no aparece:
sudo ufw allow 3000/tcp comment "Open WebUI"

# Verificar que el contenedor está corriendo con red del host
docker inspect open-webui | grep '"NetworkMode"'
# Debe mostrar: "NetworkMode": "host"
```

### NemoClaw: Proxy no arranca después del reinicio

```bash
# Restaurar NemoClaw manualmente

# Paso 1: Verificar que el motor de inferencia está activo primero
curl -sf http://localhost:8000/v1/models > /dev/null || \
  curl -sf http://localhost:11434/api/tags > /dev/null
echo "Motor de inferencia: activo"

# Paso 2: Reiniciar el proxy
nemoclaw restart

# Paso 3: Verificar estado
nemoclaw status
```

---

## Resumen del Capítulo

En este capítulo configuramos el stack agéntico completo que convierte el Jetson AGX Orin 64GB en un asistente de IA autónomo, accesible desde WhatsApp, el navegador y la terminal:

- **OpenClaw** (puerto 18789) actúa como el agente central, conectando el modelo de lenguaje con el mundo exterior. La clave de la configuración es `"profile": "full"` y el ID correcto del modelo sin prefijo `vllm/`.
- **NemoClaw** agrega políticas de seguridad L7 entre el navegador y OpenClaw. Con JP 7.2, la instalación se reduce a un solo comando.
- **Jetson Agent Skills** (device-skills + bsp-skills) permiten al agente ejecutar tareas de hardware del Jetson directamente desde una interfaz de chat.
- **Open WebUI** (puerto 3000) proporciona una interfaz gráfica para interactuar con todos los motores de inferencia simultáneamente.

El siguiente capítulo (Capítulo 14) cubre el benchmarking detallado de los 10 modelos más importantes para el Jetson AGX Orin 64GB, con metodología de medición y guías de selección para cada caso de uso.
