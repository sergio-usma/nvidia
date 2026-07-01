# Capítulo 13B — NemoClaw: Capa de Seguridad L7 sobre OpenClaw

## Introducción

NemoClaw es el proxy de políticas que envuelve a OpenClaw con tres capas de protección indispensables cuando da acceso al bot de Telegram a terceros: políticas L7 REST (bloqueo selectivo de rutas de API), aislamiento del sistema de archivos (el agente solo accede a directorios explícitamente permitidos) y control de red (puede prohibir que el agente haga solicitudes hacia internet o hacia servicios internos que no debe tocar).

Sin NemoClaw, cualquier usuario del bot de Telegram podría pedirle al agente que borre archivos, ejecute comandos del sistema o filtre datos privados. NemoClaw actúa como un guardia que revisa cada solicitud antes de que llegue al modelo.

Este capítulo cubre únicamente NemoClaw. Para OpenClaw (gateway principal) consulte el Capítulo 13A.

**Modo energético:** NemoClaw es un proxy liviano — 30W es suficiente. El modo de energía lo controla el motor de inferencia, no NemoClaw.

> **Prerrequisito:** OpenClaw instalado, configurado y con el bot de Telegram activo (Capítulo 13A). NemoClaw envuelve a OpenClaw — sin OpenClaw, NemoClaw no tiene nada que proteger.

---

## 13B.1 Arquitectura de NemoClaw

<!-- INFOGRAFÍA: Arquitectura de NemoClaw — Seguridad sobre OpenClaw — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


```
Arquitectura NemoClaw — JetPack 7.2
═════════════════════════════════════

Navegador / WhatsApp
       │
       ▼  puerto 18789 (loopback)
┌──────────────────────┐
│   NemoClaw Proxy     │   ← Capa de seguridad
│   ─────────────────  │
│   • Políticas L7 REST│   Bloquea rutas de API específicas
│   • Aislamiento FS   │   El agente solo ve directorios permitidos
│   • Control de red   │   Puede prohibir salidas a internet
└──────────────────────┘
       │
       ▼  puerto 18788 (interno)
┌──────────────────────┐
│   OpenClaw Gateway   │   ← Agente central (Capítulo 13A)
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│  vLLM :8000          │
│  llama.cpp :8080     │
│  Ollama :11434       │
└──────────────────────┘
```

NemoClaw intercepta todas las solicitudes antes de que lleguen al gateway OpenClaw. Actúa como un firewall de aplicación: puede aprobar, rechazar o modificar cada solicitud basándose en las políticas configuradas.

---

## 13B.2 Instalación

JetPack 7.2 incluye todas las dependencias necesarias. La instalación se reduce a un solo comando:

```bash
# Instalación oficial NVIDIA
# Tarda 3-5 minutos — descarga el proxy y configura los servicios
curl -fsSL nvidia.com/nemoclaw.sh | bash
```

```
# Salida esperada:
[OK] NemoClaw installed
[OK] Dependencies satisfied (JetPack 7.2 detected)
[OK] Proxy service configured
→ Run 'nemoclaw start' to activate the security proxy
```

```bash
# Verificar instalación
nemoclaw --version
# Esperado: NemoClaw 2026.x.x
```

> **ADVERTENCIA — Repositorio incorrecto:** El repositorio `github.com/jetsonhacks/NemoClaw-Orin` no existe. Cualquier guía que indique clonarlo está desactualizada. Use exclusivamente el instalador oficial `curl -fsSL nvidia.com/nemoclaw.sh | bash`.

> **IMPORTANTE — Boot limpio:** El instalador configura el servicio pero **NO lo habilita en boot** automáticamente. Esto es correcto para la arquitectura clean-start. Active NemoClaw bajo demanda con `nemoclaw start`.

---

## 13B.3 Gestión del Proxy

```bash
# Verificar estado
nemoclaw status
```

```
# Salida esperada:
NemoClaw proxy: running on :18789
OpenClaw gateway: connected (via :18788)
Inference backend: connected
Active policies: 3
```

```bash
# Detener el proxy
nemoclaw stop

# Iniciar el proxy
nemoclaw start

# Reiniciar (útil tras cambio de modelo de inferencia)
nemoclaw restart

# Verificar endpoint de salud del gateway
curl -sf http://localhost:18789/health && echo "[OK] Gateway en :18789 activo"
```

---

## 13B.4 Configuración de Inferencia Local (Modo Offline)

Para un despliegue completamente offline y privado, apunte NemoClaw al servidor local activo. El flujo correcto es: **primero iniciar el motor de inferencia**, luego NemoClaw.

**Ejemplo concreto — configuracion con vLLM + Gemma 4 E2B:**

```bash
# PASO 1: Iniciar el motor de inferencia (del Capitulo 12)
mode-vllm
# Espera a que vLLM este listo (~3 min) antes de continuar

# PASO 2: Verificar que vLLM responde
curl -s http://localhost:8000/v1/models | python3 -m json.tool | grep '"id"'
# Salida: "id": "google/gemma-3-4b-it"
```

```bash
# PASO 3: Configurar NemoClaw para usar vLLM local
nemoclaw config set \
  --inference-provider local \
  --base-url http://localhost:8000/v1 \
  --model gemma4-e2b

# PASO 4: Iniciar NemoClaw
nemoclaw start
sleep 3

# PASO 5: Verificar la cadena completa (OpenClaw -> NemoClaw -> vLLM)
nemoclaw status
```

```
# Salida esperada:
NemoClaw Proxy: running on :18788
OpenClaw Gateway: connected via proxy
Inference: local @ http://localhost:8000/v1 [OK]
Model: gemma4-e2b (connected)
Policies: 3 active
```

```bash
# Probar que el agente responde a traves de NemoClaw:
curl -s http://localhost:18789/api/health
# Salida: {"status":"ok","proxy":"nemoclaw","backend":"vllm"}
```

**Otras configuraciones de backend:**

```bash
# Cambiar a Ollama (sin Docker, mas rapido de iniciar):
mode-ollama
nemoclaw config set \
  --inference-provider local \
  --base-url http://localhost:11434/v1 \
  --model qwen3:8b
nemoclaw restart

# Cambiar a llama.cpp (bajo consumo):
mode-lite
nemoclaw config set \
  --inference-provider local \
  --base-url http://localhost:8080/v1 \
  --model gemma4-e2b-gguf
nemoclaw restart

# Verificar backend activo tras cualquier cambio:
nemoclaw config show
```

```
# Salida de nemoclaw config show:
inference.provider: local
inference.base-url: http://localhost:8000/v1
inference.model: qwen3:8b
status: connected [OK]
policies: 3 reglas activas
filesystem.sandbox: /home/jetson/data/agent-sandbox
network.mode: allowlist
```

---

## 13B.5 Configuración de Políticas de Seguridad

### 13B.5.1 Políticas L7 REST — Bloquear Rutas de API

NemoClaw puede bloquear que el agente llame a rutas específicas de la API del sistema:

```bash
# Ver políticas activas
nemoclaw policies list

# Bloquear comandos sensibles de sistema de archivos
nemoclaw policies add \
  --rule block-fs-delete \
  --match "POST /api/files/delete" \
  --action deny \
  --reason "El agente no puede borrar archivos del sistema"

# Bloquear acceso a la cámara
nemoclaw policies add \
  --rule block-camera \
  --match "POST /api/camera/*" \
  --action deny

# Bloquear envío de SMS desde el agente
nemoclaw policies add \
  --rule block-sms \
  --match "POST /api/sms/send" \
  --action deny

# Ver las reglas configuradas
nemoclaw policies list --verbose
```

### 13B.5.2 Control de Red

```bash
# Modo offline total: el agente no puede hacer solicitudes a internet
nemoclaw config set network.outbound.mode offline

# Modo allowlist: el agente solo puede contactar hosts específicos
nemoclaw config set network.outbound.mode allowlist
nemoclaw config set network.outbound.allowlist '["localhost","192.168.1.0/24"]'

# Modo por defecto (permisivo): el agente puede contactar cualquier host
nemoclaw config set network.outbound.mode permissive

# Verificar modo activo
nemoclaw config get network.outbound.mode
```

### 13B.5.3 Aislamiento del Sistema de Archivos

```bash
# Definir directorios que el agente puede leer/escribir
nemoclaw config set \
  filesystem.allowedPaths '["/home/jetson/.openclaw/workspace","/tmp/agent-sandbox"]'

# Crear el directorio sandbox si no existe
mkdir -p /tmp/agent-sandbox

# Verificar configuración
nemoclaw config get filesystem.allowedPaths
```

---

## 13B.6 Recuperación Post-Reinicio

NemoClaw no persiste entre reinicios — correcto para la arquitectura clean-start. Tras cada reinicio, la secuencia es siempre: motor de inferencia → OpenClaw → NemoClaw.

**Ejemplo concreto — restaurar el stack con vLLM + Gemma 4 E2B:**

```bash
# PASO 1: Iniciar motor de inferencia (script del Capitulo 13A)
mode-vllm
# Espera internamente hasta que vLLM responda en :8000 (~3 min primer modelo)
```

```bash
# PASO 2: Verificar que el motor esta listo antes de continuar
curl -sf http://localhost:8000/v1/models > /dev/null && \
  echo "[OK] vLLM activo" || echo "[ERROR] vLLM no responde"
```

```bash
# PASO 3: Iniciar OpenClaw gateway
openclaw gateway start
sleep 5
openclaw doctor | grep -E "Model:|Gateway:"
# Salida: [OK] Gateway: running | [OK] Model: vllm/gemma4-e2b (connected)
```

```bash
# PASO 4: Iniciar NemoClaw proxy
nemoclaw start
sleep 3
nemoclaw status
# Salida: NemoClaw Proxy: running on :18788
#         OpenClaw Gateway: connected via proxy
#         Inference: local @ http://localhost:8000/v1 [OK]
```

```bash
# PASO 5: Verificacion final del stack completo
curl -sf http://localhost:18789/health && echo "[OK] Stack agéntico activo en :18789"
```

**Script de restauracion rapida (guarda los 5 pasos en un alias):**

```bash
cat > ~/scripts/start-agent-stack.sh << 'EOF'
#!/usr/bin/env bash
# start-agent-stack.sh -- Restaura el stack agéntico (OpenClaw + NemoClaw)
# Uso: start-agent-stack.sh [vllm-gemma|lite-gemma|longdoc|ollama]
set -euo pipefail

MODE=${1:-"vllm-gemma"}

echo "=== Iniciando stack agéntico (modo: $MODE) ==="

# 1. Motor de inferencia via switch-model.sh
~/scripts/switch-model.sh "$MODE"

# 2. OpenClaw gateway
echo "Iniciando OpenClaw..."
openclaw gateway start
sleep 5
openclaw doctor | grep -E "Model:|Gateway:|Error:" || true

# 3. NemoClaw proxy
echo "Iniciando NemoClaw..."
nemoclaw start
sleep 3
nemoclaw status

# 4. Verificacion
curl -sf http://localhost:18789/health && echo "[OK] Stack completo en :18789" || \
  echo "[WARN] Gateway no responde -- revisar logs con: openclaw logs --tail 20"
EOF

chmod +x ~/scripts/start-agent-stack.sh
```

```bash
# Agregar alias a ~/.bash_aliases
alias start-stack='~/scripts/start-agent-stack.sh'
alias start-stack-lite='~/scripts/start-agent-stack.sh lite-gemma'
alias stop-stack='~/scripts/switch-model.sh stop && nemoclaw stop 2>/dev/null; echo "[OK] Stack detenido"'

source ~/.bash_aliases || source ~/.bashrc

# Uso tras reinicio:
start-stack           # Stack con vLLM + Gemma 4 E2B (defecto)
start-stack-lite      # Stack con llama.cpp + Gemma GGUF (bajo consumo)
stop-stack            # Detener todo, volver a 15W idle
```

---

## 13B.7 Monitoreo en Tiempo Real

```bash
# Ver logs del proxy en tiempo real
nemoclaw logs --follow

# Filtrar solo solicitudes rechazadas por políticas
nemoclaw logs --follow | grep -i "denied\|blocked\|policy"

# Ver estadísticas de tráfico
nemoclaw stats

# Ver conexiones activas al proxy
ss -tlnp | grep 18789

# Verificar que el proxy está interceptando correctamente
curl -sf http://localhost:18789/health | python3 -m json.tool
```

---

## 13B.8 Aliases para el Día a Día

```bash
# Agregar al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── NemoClaw ────────────────────────────────────────────────────────────
alias nemoclaw-start='nemoclaw start && sleep 3 && nemoclaw status'
alias nemoclaw-stop='nemoclaw stop && echo "NemoClaw proxy detenido"'
alias nemoclaw-restart='nemoclaw restart && sleep 3 && nemoclaw status'
alias nemoclaw-status='nemoclaw status'
alias nemoclaw-logs='nemoclaw logs --follow'
alias nemoclaw-policies='nemoclaw policies list --verbose'
EOF

source ~/.bashrc
```

---

## 13B.9 Solución de Problemas

### NemoClaw no arranca después del reinicio

```bash
# Causa más común: el motor de inferencia no está activo
curl -sf http://localhost:8000/v1/models > /dev/null \
  && echo "[OK] vLLM activo" \
  || echo "[ERROR] vLLM inactivo — ejecute start-qwen35 primero"

# Después de confirmar el motor, reiniciar
nemoclaw restart
nemoclaw status
```

### El proxy arranca pero OpenClaw no conecta

```bash
# Verificar que el gateway interno de OpenClaw está en el puerto correcto
openclaw gateway status | grep -E "port|running"
# Esperado: running on port 18788 (interno) o 18789 (si NemoClaw no está activo)

# Si OpenClaw muestra puerto 18789 y NemoClaw también intenta tomar 18789:
# solo uno puede estar en ese puerto — detenga el gateway y reinicie el stack
openclaw gateway stop
nemoclaw restart  # NemoClaw tomará 18789 y conectará a OpenClaw en 18788
```

### Las políticas no se aplican

```bash
# Verificar que las políticas están cargadas
nemoclaw policies list

# Recargar políticas sin reiniciar el proxy
nemoclaw policies reload

# Si el problema persiste, reiniciar completamente
nemoclaw restart
```

---

## Resumen del Capítulo 13B

NemoClaw añade tres capas de seguridad sobre el bot de Telegram del Capítulo 13A:

- **Políticas L7 REST** — bloquea rutas de API específicas antes de que lleguen al agente
- **Aislamiento de sistema de archivos** — el agente solo accede a directorios explícitamente permitidos
- **Control de red** — modo offline, allowlist, o permisivo para las solicitudes salientes

El flujo post-reinicio es siempre: `mode-vllm` (o el motor elegido) → `openclaw gateway start` → `nemoclaw start`. El script `~/scripts/start-agent-stack.sh` automatiza esta secuencia.

El capítulo siguiente (13C) cubre Open WebUI con SSL local — necesario para habilitar el microfono en el navegador y construir el proyecto de aprendizaje de inglés con Nemotron Omni multimodal.
