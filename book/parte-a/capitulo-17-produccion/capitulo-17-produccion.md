# Capítulo 17 — Despliegue en Producción: Endurecimiento, Watchdogs, Firewall y Automatización

## Introducción

Poner el Jetson AGX Orin en producción va mucho más allá de tener los modelos funcionando correctamente. Un sistema de producción debe sobrevivir reinicios imprevistos, gestionar la memoria de forma proactiva, protegerse contra accesos no autorizados y recuperarse automáticamente de fallos sin intervención humana.

Este capítulo cubre las cinco áreas críticas del despliegue en producción:

1. **Endurecimiento del sistema** — restricciones de arranque automático, protección OOM, configuración de swap y políticas de Docker
2. **Firewall UFW** — reglas de red para exponer solo los puertos necesarios
3. **Scripts de arranque inteligente** — secuencia de inicio post-reinicio que recupera el stack sin intervención manual
4. **Watchdogs y monitoreo** — detección y recuperación automática de fallos en los servicios
5. **Troubleshooting** — 22 errores comunes en producción con causas raíz y soluciones paso a paso

> **NOTA:** Este capítulo asume que los componentes del stack (Capítulo 12 — motores de inferencia, Capítulo 13 — OpenClaw, NemoClaw) están instalados y funcionando correctamente en modo interactivo. El objetivo aquí es automatizar y proteger esa instalación para uso continuo.

---

## 15.0 Arquitectura de Arranque Limpio

El problema más frecuente al poner el Jetson en producción no es técnico sino operativo: el sistema arranca con demasiados servicios activos. Ollama instala por defecto un servicio systemd con `Restart=always`. Los contenedores Docker creados sin `--restart no` se reinician solos. Scripts en `~/.bashrc` pueden lanzar modelos al iniciar sesión. El resultado es que al encender el Jetson ya hay 20–30 GB de RAM comprometidos antes de que el usuario elija qué modelo quiere ejecutar.

La arquitectura de arranque limpio resuelve esto con un principio simple: **el Jetson no inicia ningún motor de inferencia por sí solo**. Al arrancar solo están activos SSH y los componentes necesarios para NoMachine. Todo lo demás se activa explícitamente mediante scripts del usuario.

### 15.0.1 Estado Objetivo del Sistema tras el Boot

<!-- INFOGRAFÍA: Estado Objetivo del Sistema tras Boot Limpio — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


```
┌─────────────────────────────────────────────────────────┐
│              JETSON — ESTADO TRAS REBOOT LIMPIO          │
├─────────────────────────────────────────────────────────┤
│  multi-user.target (modo texto, sin GUI local)           │
│                                                         │
│  SERVICIOS ACTIVOS:                                     │
│    [OK] ssh.service         — administración remota        │
│    [OK] nxserver.service    — NoMachine (GUI remota)       │
│    [OK] NetworkManager      — red                          │
│                                                         │
│  SERVICIOS DESACTIVADOS:                                │
│    [ERROR] ollama.service      — eliminado completamente      │
│    [ERROR] docker.service      — desactivado en boot          │
│    [ERROR] vllm / llama.cpp   — sin systemd units            │
│    [ERROR] Contenedores        — todos con restart=no         │
│                                                         │
│  MEMORIA DISPONIBLE TRAS BOOT: ~50-52 GB               │
└─────────────────────────────────────────────────────────┘
```

Con esta base, el usuario elige qué motor activar:

```
Usuario conecta por SSH
        │
        ├─→ alias vllm-start   → lanza docker run (vLLM)
        ├─→ alias llama-start  → lanza docker run (llama.cpp)
        ├─→ alias ollama-start → sudo systemctl start ollama
        └─→ combinación        → switch-model.sh (Capítulo 12)
```

### 15.0.2 Procedimiento: Configurar el Arranque Limpio

Ejecute estos pasos **una sola vez** después de instalar todos los componentes del stack.

**Paso 1 — Arrancar en modo texto (sin GUI local):**

```bash
sudo systemctl set-default multi-user.target
```

```
# Salida esperada
Created symlink /etc/systemd/system/default.target → /lib/systemd/system/multi-user.target
```

> **IMPORTANTE:** Esto NO desactiva NoMachine. La sesión gráfica de NoMachine se genera virtualmente en el servidor y se envía a su PC mediante el protocolo NX. El Jetson no necesita un entorno gráfico local para que NoMachine funcione. SSH seguirá funcionando con total normalidad. El acceso local por teclado y monitor entrará en modo consola, que es exactamente lo que se busca: un sistema base liviano.

**Paso 2 — Eliminar completamente el servicio Ollama:**

Ollama documenta explícitamente que su instalador crea `ollama.service` con `Restart=always`. Si lo deja habilitado, Ollama arrancará en cada reboot y cargará el último modelo usado, consumiendo entre 4 y 26 GB de RAM antes de que abra una terminal.

```bash
# Detener, deshabilitar y eliminar el servicio Ollama
sudo systemctl stop ollama 2>/dev/null || true
sudo systemctl disable ollama 2>/dev/null || true
sudo rm -f /etc/systemd/system/ollama.service
sudo rm -f /etc/systemd/system/ollama.service.d/production.conf
sudo systemctl daemon-reload
echo "[OK] ollama.service eliminado"
```

```
# Verificación
systemctl is-enabled ollama 2>&1
# Salida esperada: Failed to get unit file state for ollama.service: No such file or directory
```

> **NOTA:** El binario `ollama` sigue instalado en `/usr/local/bin/ollama`. Solo se elimina el servicio de arranque automático. Puede seguir usando Ollama con `sudo systemctl start ollama` o directamente con `ollama serve &` cuando lo necesite.

**Paso 3 — Desactivar Docker en el arranque:**

```bash
# Desactivar Docker en boot
sudo systemctl disable docker
sudo systemctl disable docker.socket 2>/dev/null || true
echo "[OK] Docker desactivado en boot"
```

```
# Verificación
systemctl is-enabled docker
# Salida esperada: disabled
```

> **CONSEJO:** Cuando quiera usar Docker, simplemente ejecute `sudo systemctl start docker`. También puede crear un alias:
> ```bash
> echo 'alias docker-start="sudo systemctl start docker && echo Docker activo"' >> ~/.bashrc
> ```

**Paso 4 — Neutralizar políticas de reinicio en contenedores existentes:**

```bash
# Cambiar restart=always / unless-stopped a restart=no en todos los contenedores LLM
#
if docker ps -a -q 2>/dev/null | grep -q .; then
    docker update --restart=no $(docker ps -a -q) 2>/dev/null
    # Excepción: Open WebUI puede mantenerse con unless-stopped (usa ~200MB RAM)
    docker update --restart=unless-stopped open-webui 2>/dev/null || true
    echo "[OK] Todos los contenedores LLM → restart=no"
else
    echo "No hay contenedores todavía (se crearán con --restart no por defecto)"
fi
```

**Paso 5 — Auditar y limpiar scripts de sesión:**

```bash
# Verificar que ~/.bashrc no lanza procesos de inferencia al iniciar sesión
#
grep -n -E "(ollama|vllm|llama\.cpp|docker run)" ~/.bashrc && \
    echo "[WARN]  ATENCIÓN: encontrados comandos de inferencia en ~/.bashrc — revíselos" || \
    echo "[OK] ~/.bashrc limpio de autoarranque de inferencia"

# Verificar servicios de usuario
ls ~/.config/systemd/user/ 2>/dev/null && \
    echo "[WARN]  Revisar: hay unidades systemd de usuario" || \
    echo "[OK] Sin unidades systemd de usuario"
```

**Paso 6 — Reiniciar y verificar:**

```bash
sudo reboot now
```

Tras el reboot, conéctese por SSH y verifique:

```bash
# Verificación completa del arranque limpio
echo "=== TARGET DE ARRANQUE ==="
systemctl get-default

echo ""
echo "=== SERVICIOS DE INFERENCIA (deben estar inactivos) ==="
systemctl is-active ollama 2>&1 || echo "ollama → inactivo [OK]"
systemctl is-active docker 2>&1 || echo "docker → inactivo [OK]"

echo ""
echo "=== CONTENEDORES ACTIVOS (deben ser 0) ==="
docker ps 2>/dev/null || echo "(Docker no está corriendo — correcto)"

echo ""
echo "=== MEMORIA DISPONIBLE ==="
free -h | grep Mem
```

```
# Salida esperada tras arranque limpio
=== TARGET DE ARRANQUE ===
multi-user.target

=== SERVICIOS DE INFERENCIA (deben estar inactivos) ===
inactive
ollama → inactivo [OK]
inactive
docker → inactivo [OK]

=== CONTENEDORES ACTIVOS (deben ser 0) ===
(Docker no está corriendo — correcto)

=== MEMORIA DISPONIBLE ===
Mem:            62Gi       10Gi       50Gi      ...
```

Con ~50 GB libres tras el boot, el sistema está listo para recibir el modelo que el usuario elija.

### 15.0.3 Regla de Operación

> **REGLA FUNDAMENTAL:** El Jetson no inicia ningún motor de inferencia por sí solo. La activación de vLLM, Ollama o llama.cpp ocurre **solo mediante comandos explícitos del usuario**, nunca por arranque del sistema. Los scripts de activación (`vllm-start`, `llama-start`, `ollama-start`) y el script de limpieza (`jetson-clean`) son el mecanismo de control. El sistema debe comportarse como base limpia de ejecución, no como servidor persistente de LLM.

---

## 15.1 Endurecimiento del Sistema

El "hardening" (endurecimiento) en el contexto del Jetson consiste principalmente en prevenir tres categorías de problemas:

1. **Contenedores LLM que arrancan automáticamente** — consumiendo toda la RAM antes de que el usuario elija un modo de trabajo
2. **Fallos por falta de memoria (OOM)** — que pueden bloquear el sistema o matar procesos críticos
3. **Configuraciones de Ollama subóptimas** — que mantienen modelos cargados en GPU consumiendo RAM sin ser usados

### 15.1.1 Política de Restart para Contenedores LLM

La regla más importante del Jetson en producción: **todos los contenedores LLM deben tener `restart=no`**. Si un contenedor LLM arranca automáticamente en el boot, puede pre-alocar toda la memoria GPU/RAM y bloquear el sistema antes de que el usuario tenga oportunidad de elegir qué modelo cargar.

```bash
# Verificar las políticas de restart de todos los contenedores
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
  for c in json.load(sys.stdin):
    n = c['Name'].lstrip('/')
    p = c['HostConfig']['RestartPolicy']['Name']
    flag = '[WARN]  PELIGRO' if p in ['always', 'unless-stopped'] else '[OK] seguro'
    print(f'  {flag}  {n}: restart={p}')
except:
  print('  Sin contenedores')
" 2>/dev/null || echo "No hay contenedores"
```

```bash
# Aplicar restart=no a todos los contenedores LLM — detección dinámica
# No se usan nombres fijos: los contenedores tienen nombres variables según cómo se crean.
LLM_CONTAINERS=$(docker ps -a --format '{{.Names}}' \
  | grep -E "vllm|llama|qwen|gemma|nemotron|cosmos|gpt|openclaw")

if [ -n "$LLM_CONTAINERS" ]; then
    for c in $LLM_CONTAINERS; do
        docker update --restart=no "$c" 2>/dev/null && \
            echo "[OK] $c → restart=no"
    done
else
    echo "ℹ Sin contenedores LLM activos todavía"
fi

# Open WebUI puede tener restart=unless-stopped (usa solo ~200MB RAM)
docker update --restart=unless-stopped open-webui 2>/dev/null || true
echo "[OK] Open WebUI → restart=unless-stopped (se reinicia automáticamente)"
```

> **IMPORTANTE:** `--restart no` NO significa que el contenedor se detenga cuando falla. Solo significa que no se reinicia automáticamente cuando Docker (o el sistema) arrancan. Un contenedor con `--restart no` puede seguir corriendo indefinidamente si no lo detiene manualmente o si el sistema no se reinicia.

### 15.1.2 Configuración de Ollama para Producción

Ollama por defecto mantiene los modelos cargados en GPU durante 5 minutos después del último uso. En producción esto es peligroso porque consume RAM que otros procesos podrían necesitar.

```bash
# Configurar Ollama con políticas de producción
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/production.conf << 'EOF'
[Service]
# Escuchar en todas las interfaces (necesario para acceso desde red local)
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"

# Máximo 2 requests en paralelo (evita OOM)
Environment="OLLAMA_NUM_PARALLEL=2"

# Solo un modelo cargado a la vez (memoria unificada del Jetson)
Environment="OLLAMA_MAX_LOADED_MODELS=1"

# Descargar el modelo inmediatamente después de cada uso (0 = sin timeout)
Environment="OLLAMA_KEEP_ALIVE=0"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama 2>/dev/null || true
echo "[OK] Ollama configurado: keep_alive=0, max_loaded=1"
```

```bash
# Verificar que las variables de entorno se aplicaron
systemctl show ollama --property=Environment
# Salida esperada:
# Environment=OLLAMA_HOST=0.0.0.0 OLLAMA_ORIGINS=* OLLAMA_NUM_PARALLEL=2 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=0
```

### 15.1.3 Protección OOM del Kernel

El kernel Linux tiene un mecanismo llamado OOM Killer que termina procesos cuando la memoria se agota. En el Jetson, es preferible que el OOM Killer actúe antes de que el sistema entre en pánico:

```bash
# Configurar protección OOM
sudo tee /etc/sysctl.d/99-jetson-oom.conf << 'EOF'
# Preferir matar procesos antes de que el kernel entre en pánico
vm.panic_on_oom = 0

# El OOM Killer mata el proceso que causó la asignación (no el proceso aleatorio)
vm.oom_kill_allocating_task = 1

# Mínimo uso de swap — solo cuando es absolutamente necesario
vm.swappiness = 1

# Presión alta sobre el caché VFS para liberar memoria rápidamente cuando escasea
vm.vfs_cache_pressure = 200
EOF

sudo sysctl -p /etc/sysctl.d/99-jetson-oom.conf
echo "[OK] Protección OOM configurada"
```

```bash
# Verificar que las configuraciones se aplicaron correctamente
sysctl vm.panic_on_oom vm.oom_kill_allocating_task vm.swappiness vm.vfs_cache_pressure
# Salida esperada:
# vm.panic_on_oom = 0
# vm.oom_kill_allocating_task = 1
# vm.swappiness = 1
# vm.vfs_cache_pressure = 200
```

### 15.1.4 Script de Hardening Completo (Ejecutar una Vez)

```bash
# Crear y ejecutar el script de hardening completo
cat > ~/scripts/harden.sh << 'HARDEN'
#!/bin/bash
echo "╔══════════════════════════════════════════════╗"
echo "║   HARDENING JETSON AGX ORIN — JetPack 7.2   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Arranque limpio: target mínimo (modo texto, sin GUI local)
echo "→ [1/7] Configurando multi-user.target..."
sudo systemctl set-default multi-user.target
echo "  [OK] Boot target → multi-user.target (modo texto)"

# 2. Eliminar servicio Ollama (Restart=always por defecto — peligroso en Jetson)
echo ""
echo "→ [2/7] Eliminando servicio ollama..."
sudo systemctl stop ollama 2>/dev/null || true
sudo systemctl disable ollama 2>/dev/null || true
sudo rm -f /etc/systemd/system/ollama.service
sudo rm -f /etc/systemd/system/ollama.service.d/production.conf
sudo rmdir /etc/systemd/system/ollama.service.d 2>/dev/null || true
sudo systemctl daemon-reload
echo "  [OK] ollama.service eliminado (binario /usr/local/bin/ollama intacto)"
echo "  ℹ  Para usar Ollama: 'sudo systemctl start ollama' o 'ollama serve &'"

# 3. Desactivar Docker en boot (se inicia manualmente con docker-start)
echo ""
echo "→ [3/7] Desactivando Docker en boot..."
sudo systemctl disable docker 2>/dev/null || true
sudo systemctl disable docker.socket 2>/dev/null || true
echo "  [OK] Docker desactivado en boot (actívelo con: sudo systemctl start docker)"

# 4. Políticas de restart: detección dinámica por palabras clave
echo ""
echo "→ [4/7] Fijando políticas de restart (detección dinámica)..."
if sudo systemctl start docker 2>/dev/null && docker ps -a -q 2>/dev/null | grep -q .; then
    # Todos los contenedores LLM a restart=no
    LLM_CONTAINERS=$(docker ps -a --format '{{.Names}}' \
      | grep -E "vllm|llama|qwen|gemma|nemotron|cosmos|gpt|openclaw")
    for c in $LLM_CONTAINERS; do
        docker update --restart=no "$c" 2>/dev/null && \
            echo "  [OK] $c → restart=no" || true
    done
    # Open WebUI: puede quedar en unless-stopped (~200MB RAM es aceptable)
    docker update --restart=unless-stopped open-webui 2>/dev/null && \
        echo "  [OK] open-webui → restart=unless-stopped" || true
    # Desactivar Docker nuevamente en boot (lo activamos solo para la operación)
    sudo systemctl disable docker 2>/dev/null || true
else
    echo "  ℹ  Sin contenedores todavía — créelos con --restart no por defecto"
fi

# 5. Configurar protección OOM del kernel
echo ""
echo "→ [5/7] Configurando protección OOM..."
sudo tee /etc/sysctl.d/99-jetson-oom.conf > /dev/null << 'EOF'
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1
vm.swappiness = 1
vm.vfs_cache_pressure = 200
EOF
sudo sysctl -p /etc/sysctl.d/99-jetson-oom.conf > /dev/null
echo "  [OK] OOM killer configurado (panic_on_oom=0, kill_allocating_task=1)"

# 6. Caché Node.js para OpenClaw
echo ""
echo "→ [6/7] Creando caché Node.js para OpenClaw..."
mkdir -p /var/tmp/openclaw-compile-cache
echo "  [OK] Cache creada en /var/tmp/openclaw-compile-cache"

# 7. Verificación final
echo ""
echo "→ [7/7] Verificación..."
echo "  Boot target:        $(systemctl get-default)"
echo "  ollama.service:     $(systemctl is-enabled ollama 2>&1 | head -1)"
echo "  docker.service:     $(systemctl is-enabled docker 2>&1 | head -1)"
echo ""
echo "  Políticas de restart activas:"
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
  for c in json.load(sys.stdin):
    n = c['Name'].lstrip('/')
    p = c['HostConfig']['RestartPolicy']['Name']
    flag = '  [WARN]  REVISAR' if p in ['always', 'unless-stopped'] and 'webui' not in n else '  [OK]'
    print(f'{flag} {n}: restart={p}')
except:
  print('  Sin contenedores activos')
" 2>/dev/null || echo "  (Docker no está corriendo)"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Hardening completado."
echo "  Reinicie con 'sudo reboot' para aplicar multi-user.target."
echo "  Para re-aplicar después de crear contenedores: ~/scripts/harden.sh"
echo "═══════════════════════════════════════════════"
HARDEN

chmod +x ~/scripts/harden.sh
alias jetson-harden='~/scripts/harden.sh'
echo 'alias jetson-harden="~/scripts/harden.sh"' >> ~/.bashrc

# Ejecutar el hardening
~/scripts/harden.sh
```

### 15.1.5 Cómo Revertir el Hardening (para usuarios que prefieren autostart)

Si decide que prefiere que los servicios arranquen automáticamente en lugar de on-demand, estos son los pasos para revertir cada acción del hardening:

```bash
# Revertir Paso 1: volver a graphical.target (entorno gráfico en pantalla local)
sudo systemctl set-default graphical.target
# Aplicar sin reboot:
sudo systemctl isolate graphical.target

# Revertir Paso 2: reinstalar el servicio de Ollama con arranque automatico
# (el binario ollama sigue en /usr/local/bin/)
sudo tee /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0"

[Install]
WantedBy=default.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
systemctl is-active ollama  # Salida: active

# Revertir Paso 3: habilitar Docker en arranque automatico
sudo systemctl enable docker
sudo systemctl enable docker.socket
systemctl is-enabled docker  # Salida: enabled

# Revertir contenedores: cambiar restart=no a restart=unless-stopped
# Reemplazar "open-webui" con el nombre del contenedor a restaurar:
docker update --restart unless-stopped open-webui
```

> **NOTA:** Reactivar el arranque automatico de Ollama o Docker incrementa el uso de RAM en reposo. En el Jetson AGX Orin 64GB esto puede no ser critico, pero si ejecuta modelos grandes (35B+) puede quedar con menos RAM disponible tras el boot. La arquitectura clean-start garantiza siempre los maximos 64 GB disponibles al iniciar un modelo.

---

## 15.2 Firewall UFW — Control de Acceso a la Red

UFW (Uncomplicated Firewall) controla qué puertos son accesibles desde la red local. Por defecto en Ubuntu 24.04, UFW está deshabilitado. En producción debe activarse con reglas específicas para el Jetson.

### 15.2.1 Activación y Reglas Base

```bash
# Verificar estado actual de UFW
sudo ufw status verbose
# Si dice "Status: inactive", proceder con la configuración
```

```bash
# ATENCIÓN: Configurar SSH PRIMERO antes de habilitar UFW.
# Si habilita UFW sin permitir SSH, perderá el acceso remoto.

# Paso 1: Asegurarse de que SSH está permitido
sudo ufw allow ssh
# O equivalentemente:
sudo ufw allow 22/tcp comment "SSH"

# Paso 2: Permitir los servicios del stack de IA
sudo ufw allow 3000/tcp comment "Open WebUI"
sudo ufw allow 4000/tcp comment "NoMachine"
sudo ufw allow 8000/tcp comment "vLLM API"
sudo ufw allow 8080/tcp comment "llama.cpp API"
sudo ufw allow 11434/tcp comment "Ollama API"

# Puerto 18789 (OpenClaw Gateway) — NO abrir a la red local
# Está enlazado a loopback (127.0.0.1) por diseño de seguridad
# Acceso solo via túnel SSH

# Paso 3: Activar UFW (confirmación requerida)
sudo ufw enable
# Escribir "y" cuando pregunte "Command may disrupt existing ssh connections"

# Paso 4: Verificar reglas
sudo ufw status numbered
```

```
# Salida esperada de 'ufw status numbered':
# Status: active
#
#      To                         Action      From
#      --                         ------      ----
# [ 1] 22/tcp                     ALLOW IN    Anywhere   # SSH
# [ 2] 3000/tcp                   ALLOW IN    Anywhere   # Open WebUI
# [ 3] 4000/tcp                   ALLOW IN    Anywhere   # NoMachine
# [ 4] 8000/tcp                   ALLOW IN    Anywhere   # vLLM API
# [ 5] 8080/tcp                   ALLOW IN    Anywhere   # llama.cpp API
# [ 6] 11434/tcp                  ALLOW IN    Anywhere   # Ollama API
```

> **CONSEJO:** Si solo desea acceso desde su red local (no desde internet), restrinja cada regla a la subred local: `sudo ufw allow from 192.168.1.0/24 to any port 8000 comment "vLLM solo red local"`. Adapte `192.168.1.0/24` a su rango de red.

### 15.2.2 Restricción a Red Local Únicamente (Más Seguro)

```bash
# Configuración más restrictiva: solo permitir acceso desde la red local
# (Reemplazar 192.168.1.0/24 con su rango de red local)
LOCAL_SUBNET="192.168.1.0/24"

sudo ufw delete allow 8000/tcp 2>/dev/null || true
sudo ufw delete allow 8080/tcp 2>/dev/null || true
sudo ufw delete allow 11434/tcp 2>/dev/null || true

sudo ufw allow from $LOCAL_SUBNET to any port 8000 comment "vLLM - solo red local"
sudo ufw allow from $LOCAL_SUBNET to any port 8080 comment "llama.cpp - solo red local"
sudo ufw allow from $LOCAL_SUBNET to any port 11434 comment "Ollama - solo red local"

sudo ufw reload
sudo ufw status numbered
```

### 15.2.3 Gestión de UFW en el Día a Día

```bash
# Ver estado completo
sudo ufw status verbose

# Agregar una regla nueva (ejemplo: puerto personalizado para API propia)
sudo ufw allow 9000/tcp comment "API personalizada"

# Eliminar una regla por número (usar 'ufw status numbered' primero)
sudo ufw delete 5

# Recargar UFW sin reiniciar
sudo ufw reload

# Deshabilitar UFW temporalmente (por ejemplo, para depuración de red)
sudo ufw disable
# Volver a habilitar
sudo ufw enable
```

---

## 15.3 Script de Arranque Inteligente (Startup)

Después de un reinicio del Jetson, el stack de IA no vuelve a su estado anterior automáticamente (esto es intencionado — los contenedores LLM tienen `restart=no`). Sin embargo, los servicios base (SSH, XRDP, NoMachine, Ollama, OpenClaw) sí deben arrancar automáticamente.

El script de startup verifica el estado del sistema y restaura solo lo que es seguro restaurar automáticamente:

```bash
# Crear script de arranque
cat > ~/scripts/startup.sh << 'STARTUP'
#!/bin/bash
# startup.sh — Se ejecuta manual o vía cron después de cada reinicio
# NO inicia contenedores LLM automáticamente (por diseño)

LOG="$HOME/jetson-ai-data/startup.log"
mkdir -p "$HOME/jetson-ai-data"

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"; }

log "═══ STARTUP JETSON AGX ORIN — $(date '+%d/%m/%Y') ═══"

# 1. Verificar servicios básicos del sistema (solo SSH — ollama.service fue eliminado)
log "→ Verificando servicios del sistema..."
for svc in ssh; do
  if systemctl is-active --quiet $svc; then
    log "  [OK] $svc activo"
  else
    log "  [WARN]  $svc inactivo — intentando iniciar..."
    sudo systemctl start $svc && log "  [OK] $svc iniciado" || log "  [ERROR] $svc falló"
  fi
done
# NOTA: Ollama no se inicia aquí — el unit file fue eliminado en §15.0.2.
# Use 'ollama serve &' o el alias 'ollama-start' cuando necesite Ollama bajo demanda.

# 2. Verificar OpenClaw Gateway (servicio de usuario systemd)
log "→ Verificando OpenClaw Gateway..."
if openclaw gateway status 2>/dev/null | grep -q "running"; then
  log "  [OK] OpenClaw Gateway activo"
else
  log "  [WARN]  OpenClaw Gateway inactivo — iniciando..."
  openclaw gateway start 2>/dev/null && log "  [OK] OpenClaw Gateway iniciado" || \
    log "  [ERROR] OpenClaw Gateway falló — verificar: openclaw doctor"
fi

# 3. Verificar Open WebUI (puede tener restart=unless-stopped)
log "→ Verificando Open WebUI..."
if docker ps --filter name=open-webui --filter status=running -q 2>/dev/null | grep -q .; then
  log "  [OK] Open WebUI activo"
else
  log "  [WARN]  Open WebUI no está corriendo"
  log "  Para iniciarlo: docker start open-webui"
fi

# 4. Estado de memoria
FREE_GB=$(free -g | awk '/^Mem:/{print $7}')
log "→ Memoria disponible: ${FREE_GB}GB"

# 5. Modo de energía actual
POWER=$(sudo nvpmodel --query 2>/dev/null | grep "Power Model" | head -1)
log "→ Modo de energía: $POWER"

# 6. Resumen — qué NO arrancó automáticamente (por diseño)
log ""
log "  ── No arrancados automáticamente (por diseño) ──"
log "  • vLLM, llama.cpp, Ollama: iniciar con 'mode-openclaw', 'mode-lite', etc."
log "  • Para ver opciones: ~/scripts/switch-model.sh"
log ""
log "  ── Para iniciar el modo de trabajo preferido ──"
log "  mode-openclaw  → Gemma 4 E2B / vLLM (agente WhatsApp, 30W)"
log "  mode-lite      → Gemma 4 E2B / llama.cpp (bajo consumo, 30W)"
log "  mode-longdoc   → Nemotron3 30B / vLLM (documentos largos, MAXN)"
log ""
log "═══ Startup completado — $(date '+%H:%M:%S') ═══"
STARTUP

chmod +x ~/scripts/startup.sh
alias jetson-startup='~/scripts/startup.sh'
echo 'alias jetson-startup="~/scripts/startup.sh"' >> ~/.bashrc
```

### 15.3.1 Ejecutar Startup Automáticamente al Arrancar (cron)

Para ejecutar el script de startup automáticamente al reiniciar, use `@reboot` en el cron del usuario:

```bash
# Agregar el startup al cron del usuario para ejecutarse al reiniciar
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && $HOME/scripts/startup.sh >> $HOME/jetson-ai-data/startup.log 2>&1") | crontab -

# Verificar que se agregó correctamente
crontab -l | grep startup
# Salida esperada:
# @reboot sleep 30 && /home/jetson/scripts/startup.sh >> /home/jetson/jetson-ai-data/startup.log 2>&1
```

El `sleep 30` permite que los servicios del sistema (Docker, systemd) terminen de inicializarse antes de que el script de startup comience a verificar su estado.

---

## 15.4 Watchdog — Monitoreo y Recuperación Automática

Un watchdog verifica periódicamente el estado de los servicios críticos y los reinicia si detecta fallos. En el Jetson, el OpenClaw Gateway es el servicio más crítico en producción porque sin él, el agente WhatsApp no responde.

### 15.4.1 Watchdog del Gateway OpenClaw

```bash
# Crear script watchdog
cat > ~/scripts/watchdog-openclaw.sh << 'WATCHDOG'
#!/bin/bash
# watchdog-openclaw.sh — Verifica y recupera el gateway OpenClaw
# Ejecutar via cron cada 5 minutos

LOG="$HOME/jetson-ai-data/watchdog.log"
mkdir -p "$HOME/jetson-ai-data"

log() { echo "[$(date '+%H:%M:%S')] $1" >> "$LOG"; }

# Verificar si el gateway responde en el puerto 18789
if ! curl -sf http://localhost:18789/health > /dev/null 2>&1; then
  # El health check puede no existir — verificar con openclaw
  if ! openclaw gateway status 2>/dev/null | grep -q "running"; then
    log "ALERTA: OpenClaw Gateway inactivo — reiniciando..."
    openclaw gateway restart 2>/dev/null
    sleep 5
    if openclaw gateway status 2>/dev/null | grep -q "running"; then
      log "RECUPERADO: OpenClaw Gateway reiniciado exitosamente"
    else
      log "FALLO: No se pudo recuperar el gateway. Verificar: openclaw doctor"
    fi
  fi
else
  log "OK: Gateway activo"
fi

# Rotar log si supera 1MB
if [ -f "$LOG" ] && [ $(wc -c < "$LOG") -gt 1048576 ]; then
  mv "$LOG" "${LOG}.bak"
  log "Log rotado"
fi
WATCHDOG

chmod +x ~/scripts/watchdog-openclaw.sh

# Registrar en cron para ejecutarse cada 5 minutos
(crontab -l 2>/dev/null; echo "*/5 * * * * $HOME/scripts/watchdog-openclaw.sh") | crontab -

# Verificar
crontab -l | grep watchdog
echo "[OK] Watchdog de OpenClaw: verificación cada 5 minutos"
```

### 15.4.2 Script de Verificación del Stack Completo

```bash
# Crear script de verificación completa del stack
cat > ~/scripts/verify-stack.sh << 'VERIFY'
#!/bin/bash
pass=0; fail=0; warn=0

check_ok() { echo "  [OK] $1"; pass=$((pass+1)); }
check_fail() { echo "  [ERROR] $1"; fail=$((fail+1)); }
check_warn() { echo "  [WARN]  $1"; warn=$((warn+1)); }

echo "══════════════════════════════════════════════════"
echo "  VERIFICACIÓN DEL STACK — $(date '+%H:%M %d/%m/%Y')"
echo "══════════════════════════════════════════════════"
echo ""

# 1. Sistema operativo y kernel
echo "─── Sistema ───"
OS=$(lsb_release -ds 2>/dev/null || echo "desconocido")
KERNEL=$(uname -r)
echo "  OS: $OS"
echo "  Kernel: $KERNEL"
[[ "$KERNEL" == *tegra* ]] && check_ok "Kernel Tegra verificado" || check_warn "Kernel no reconocido como Tegra"

# 2. Docker
echo ""
echo "─── Docker ───"
if docker info &>/dev/null; then
  check_ok "Docker disponible"
  RT=$(docker info --format '{{.Runtimes}}' 2>/dev/null)
  [[ "$RT" == *"nvidia"* ]] && check_ok "Runtime NVIDIA registrado" || check_fail "Runtime NVIDIA no encontrado"
else
  check_fail "Docker no disponible"
fi

# 3. OpenClaw Gateway
echo ""
echo "─── OpenClaw ───"
if openclaw gateway status 2>/dev/null | grep -q "running"; then
  check_ok "Gateway activo en :18789"
else
  check_fail "Gateway inactivo (ejecutar: openclaw gateway start)"
fi

# 4. Motores de inferencia
echo ""
echo "─── Motores de Inferencia ───"
if curl -sf http://localhost:8000/v1/models > /dev/null 2>&1; then
  MODEL=$(curl -s http://localhost:8000/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null)
  check_ok "vLLM activo en :8000 → $MODEL"
else
  echo "  — vLLM: offline (normal — activar con mode-openclaw)"
fi

if curl -sf http://localhost:8080/v1/models > /dev/null 2>&1; then
  MODEL=$(curl -s http://localhost:8080/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null)
  check_ok "llama.cpp activo en :8080 → $MODEL"
else
  echo "  — llama.cpp: offline (normal — activar con mode-lite o mode-multimodal)"
fi

if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
  check_ok "Ollama activo en :11434"
else
  echo "  — Ollama: offline (normal cuando hay otro motor activo)"
fi

# 5. Políticas de restart
echo ""
echo "─── Políticas de Restart (contenedores LLM) ───"
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
  containers = json.load(sys.stdin)
  for c in containers:
    n = c['Name'].lstrip('/')
    p = c['HostConfig']['RestartPolicy']['Name']
    is_llm = any(x in n for x in ['vllm', 'llama', 'gemma', 'qwen', 'nemotron', 'cosmos', 'gpt'])
    if is_llm and p in ['always', 'unless-stopped']:
      print(f'  [WARN]  PELIGRO: {n} tiene restart={p} — cambiar a restart=no')
    elif is_llm:
      print(f'  [OK] {n}: restart={p}')
except:
  print('  Sin contenedores para verificar')
" 2>/dev/null

# 6. Memoria
echo ""
echo "─── Memoria ───"
FREE_GB=$(free -g | awk '/^Mem:/{print $7}')
TOTAL_GB=$(free -g | awk '/^Mem:/{print $2}')
echo "  Disponible: ${FREE_GB}GB de ${TOTAL_GB}GB"
[ "$FREE_GB" -gt 10 ] && check_ok "Memoria suficiente" || check_warn "Memoria baja — considere jetson-clean"

# 7. UFW
echo ""
echo "─── Firewall UFW ───"
if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
  check_ok "UFW habilitado"
else
  check_warn "UFW deshabilitado (expuesto a red local sin restricciones)"
fi

# Resumen
echo ""
echo "══════════════════════════════════════════════════"
echo "  RESULTADO: [OK] $pass OK | [WARN]  $warn advertencias | [ERROR] $fail errores"
echo "══════════════════════════════════════════════════"
VERIFY

chmod +x ~/scripts/verify-stack.sh
alias jetson-verify='~/scripts/verify-stack.sh'
echo 'alias jetson-verify="~/scripts/verify-stack.sh"' >> ~/.bashrc
```

---

## 15.5 Operación Diaria en Producción

### 15.5.1 Rutina de Conexión SSH Diaria

> **NOTA:** Los aliases usados en esta rutina están definidos en este mismo capítulo:
> - `jetson-verify` → definido en §15.4.2 (Script de Verificación del Stack)
> - `motors-status` → definido en §15.8.1 (Lanzamiento bajo Demanda)
> - `mode-vllm` → definido en §15.5.3 (Modos de Trabajo)
> - `claw-status` → definido en §15.5.3

```bash
# Secuencia recomendada al conectarse cada dia

# Paso 1: Verificar el estado completo del stack
ssh jetson
jetson-verify

# Paso 2: Si el modelo no esta activo, elegir el modo apropiado
motors-status               # ver que esta corriendo (definido en §15.8.1)
mode-vllm                   # o el modo que necesite (ver switch-model.sh)

# Paso 3 (opcional): Abrir Open WebUI desde Windows via SSH tunnel
# [EN WINDOWS POWERSHELL]:  ssh -L 3000:localhost:3000 jetson -N
# Abrir en navegador:        http://localhost:3000

# Paso 4: Verificar bot de Telegram esta conectado
claw-status
openclaw channels status --probe
# Salida esperada: Telegram default: enabled, configured, linked, running, connected [OK]
```

### 15.5.2 Rutina Pre-Carga Pesada

Para trabajos intensivos (PDFs de 100MB, audio largo, múltiples requests en paralelo), ejecutar antes:

```bash
# Alias de diagnóstico rápido (agregar a ~/.bash_aliases si no existen)
# jetson-audit: muestra memoria, contenedores y procesos GPU en una pantalla
alias jetson-audit='echo "=== MEM ==="; free -h; echo "=== DOCKER ==="; docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}"; echo "=== OLLAMA ==="; ollama ps 2>/dev/null || echo "(Ollama no activo)"'

# jetson-mem: muestra solo la memoria libre en GB (útil para decisiones rápidas)
alias jetson-mem='free -h | awk "/^Mem:/{print \"Libre:\", \$7, \"/ Total:\", \$2}"'

source ~/.bash_aliases || source ~/.bashrc
```

```bash
# Rutina pre-workload pesado
jetson-audit    # ver memoria, contenedores y GPU en una línea (definido arriba)
jetson-clean    # limpiar todos los modelos activos (definido en §14.1)
# Elegir el modo apropiado según la tarea:
mode-longdoc    # para PDFs de 100+ páginas (Nemotron3 30B, 256K contexto)
mode-multimodal # para audio o video (Nemotron Omni, multimodal)
jetson-mem      # verificar que hay >50GB libres antes de continuar
```

### 15.5.3 Modos de Trabajo y sus Aliases

```bash
# Agregar aliases al ~/.bashrc
cat >> ~/.bashrc << 'ALIASES'

# ── Modos de trabajo ──────────────────────────────────────────────
alias mode-idle='~/scripts/switch-model.sh stop'
alias mode-openclaw='~/scripts/switch-model.sh gemma-vllm'
alias mode-lite='~/scripts/switch-model.sh gemma-llama'
alias mode-longdoc='~/scripts/switch-model.sh nemotron-text'
alias mode-multimodal='~/scripts/switch-model.sh nemotron-omni'
alias mode-ollama='
  jetson-clean;
  sudo systemctl start docker 2>/dev/null;
  sudo systemctl start ollama;
  sudo nvpmodel -m 2 && sudo jetson_clocks;
  echo "[OK] Ollama activo — libre: $(free -h | awk \"/^Mem:/{print \$7}\")";
  echo "Uso: ollama run <modelo>"
'

# ── OpenClaw shortcuts ────────────────────────────────────────────
alias claw-status='openclaw gateway status && openclaw channels status --probe'
alias claw-restart='openclaw gateway restart && sleep 3 && openclaw gateway status'
alias claw-logs='openclaw logs --follow'
alias claw-wa='openclaw logs --follow | grep -i whatsapp'
alias claw-errors='openclaw logs --follow | grep -i error'
alias claw-token='openclaw config get gateway.auth.token'
alias claw-pair='openclaw pairing list whatsapp'
alias claw-tui='openclaw tui'

# ── Poder ─────────────────────────────────────────────────────────
alias pwr-idle='sudo nvpmodel -m 3 && sudo jetson_clocks --restore && sudo nvpmodel -q'
alias pwr-30w='sudo nvpmodel -m 2 && sudo jetson_clocks && sudo nvpmodel -q'
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && sudo nvpmodel -q'

# ── Estado del sistema ────────────────────────────────────────────
alias model-status='
  echo "── vLLM :8000 ──";
  curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -c \
    "import sys,json; [print(\"  \",m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" \
    2>/dev/null || echo "  offline";
  echo "── llama.cpp :8080 ──";
  curl -s http://localhost:8080/v1/models 2>/dev/null | python3 -c \
    "import sys,json; [print(\"  \",m[\"id\"]) for m in json.load(sys.stdin)[\"data\"]]" \
    2>/dev/null || echo "  offline";
  echo "── Ollama :11434 ──";
  ollama ps 2>/dev/null | tail -n +2 || echo "  offline/vacío"
'
ALIASES

source ~/.bashrc
```

---

## 15.6 Mapa de Puertos y Servicios del Sistema en Producción

La siguiente tabla describe todos los puertos del stack agéntico completo en producción:

| Puerto | Servicio | Administrado por | Auto-arranca | Acceso desde red local |
|--------|---------|-----------------|-------------|------------------------|
| 22 | SSH | systemd (sshd) | **Sí** | Sí |
| 3000 | Open WebUI | Docker (unless-stopped) | Solo si Docker está activo | Sí |
| 3389 | XRDP | systemd (xrdp) | Sí (si instalado) | Sí |
| 4000 | NoMachine | NX daemon | **Sí** | Sí |
| 8000 | vLLM API | Docker (restart=no) | **No** | Sí (UFW permitido) |
| 8080 | llama.cpp API | Docker (restart=no) | **No** | Sí (UFW permitido) |
| 11434 | Ollama API | Manual (`ollama serve`) | **No** (servicio eliminado) | Sí (UFW permitido) |
| 18789 | OpenClaw Gateway | systemd user | **No** (bajo demanda) | Solo via túnel SSH |

> **IMPORTANTE:** El puerto 18789 (OpenClaw Gateway) está enlazado a `127.0.0.1` (loopback) por diseño y NO debe abrirse en UFW. El acceso desde Windows se hace exclusivamente via túnel SSH.
>
> Con la arquitectura de arranque limpio (Sección 15.0), solo SSH y NoMachine arrancan automáticamente. Docker y Ollama se activan bajo demanda mediante aliases o scripts del usuario.

---

## 15.7 22 Errores Comunes en Producción — Causas y Soluciones

Estos son los errores más frecuentes que encontrará al configurar y operar el stack completo del Jetson AGX Orin con JetPack 7.2. Para cada uno se indica el componente afectado, la causa raíz y la solución verificada:

| # | Componente | Síntoma / Error | Causa raíz | Solución |
|---|-----------|-------|-----------|---------------------|
| P1 | hf download | Descarga incorrecta de archivos | `--exclude "a" "b"` trata "b" como archivo a descargar | Usar un `--exclude` por cada patrón |
| P2 | HF_TOKEN | Vacío en Docker/systemd | Token definido después de `case $- in *i*)` en bashrc | Mover todos los `export` al inicio del `.bashrc` |
| P3 | HF CLI | `huggingface-cli: not found` | Comando `huggingface-cli` deprecado en venv | Usar `hf` (instalado con `pip install huggingface_hub`) |
| P4 | OpenShell | `npm 404 @openshell/cli` | Paquete no existe en npm con ese nombre | `curl -fsSL NVIDIA/OpenShell/install.sh \| sh` |
| P5 | OpenClaw | `npm 404 @openclaw/cli` | Paquete no existe en npm con ese prefijo | `curl -fsSL https://openclaw.ai/install.sh \| bash` |
| P6 | vLLM | Puerto 8000 nunca abre | Imagen x86 `vllm/vllm-openai` no corre en arm64 | Usar `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` |
| P7 | vLLM | `exec: "--model": not found` | Imagen nvidia-ai-iot no tiene entrypoint de servidor | `bash -c "cd /opt && source venv/bin/activate && vllm serve ..."` |
| P8 | vLLM | `sleep 10` insuficiente | Modelos tardan 3-10 minutos en cargar | Usar loop de polling con `curl` hasta que responda |
| P9 | vLLM | OOM al iniciar | `gpu_mem_util 0.75` excede la RAM libre | Ejecutar `jetson-clean` antes de iniciar cualquier modelo |
| P10 | OpenClaw config | Unknown model error | `models.providers["qwen"]` como proveedor incorrecto | El proveedor debe llamarse `vllm`, no `qwen` o `gemma` |
| P11 | OpenClaw config | ID con prefijo incorrecto | `"id": "vllm/google/..."` | `"id": "google/..."` (sin el prefijo del proveedor) |
| P12 | OpenClaw config | apiKey literal como nombre de variable | `"apiKey": "VLLM_API_KEY"` | `"apiKey": "vllm-local"` (el valor, no el nombre) |
| P13 | OpenClaw config | Typo en nombre del modelo | `"primary": "...gemma4-E2B-it"` (sin guión en gemma) | `"primary": "vllm/google/gemma-4-E2B-it"` (con guión) |
| P14 | OpenClaw config | Context window overflow | `maxTokens = contextWindow` deja 0 tokens para input | `maxTokens: 4096`, `contextWindow: 65536` |
| P15 | OpenClaw config | WhatsApp recibe pero no responde | `"profile": "coding"` elimina la herramienta de respuesta | `"profile": "full"` es obligatorio para WhatsApp |
| P16 | OpenClaw config | Profile inválido silencioso | `"profile": "default"` no existe como perfil válido | Perfiles válidos: `minimal`, `coding`, `messaging`, `full` |
| P17 | OpenClaw config | Error silencioso en memory search | `memorySearch.enabled: true` requiere API key de OpenAI | `"memorySearch": {"enabled": false}` |
| P18 | NemoClaw | Repositorio no existe | `jetsonhacks/NemoClaw-Orin` no existe en GitHub | `curl -fsSL https://nvidia.com/nemoclaw.sh \| bash` |
| P19 | NemoClaw | Parches iptables innecesarios | Solo JP 6.x (kernel 5.15) los necesita | JP 7.2 con kernel 6.8 no requiere parches de iptables |
| P20 | SSH túnel | `Permission denied (publickey)` | Túnel ejecutado desde el Jetson hacia sí mismo | Ejecutar el túnel SSH desde Windows PowerShell |
| P21 | Recursos | Modelo "fantasma" en RAM tras reinicio | `--restart unless-stopped` + vLLM pre-aloca memoria en el boot | `--restart no` en TODOS los contenedores LLM |
| P22 | docker-compose | Imagen x86 en arm64 | `vllm/vllm-openai:v0.22.0-ubuntu2404` solo es x86 | `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` |

---

## 15.7.5 Script de Variables de Entorno LLM (`llm-env.sh`)

Los motores de inferencia necesitan varias variables de entorno para funcionar correctamente: el token de HuggingFace para modelos privados (Gemma 4 E4B, GPT OSS 20B), la clave de API de vLLM si se configura seguridad, y las rutas CUDA. En lugar de definirlas en `.bashrc` directamente (donde podrían ser leídas por otros procesos), se concentran en un script dedicado que se activa solo cuando se va a lanzar un motor.

```bash
# Crear directorio y script de entorno LLM
mkdir -p ~/scripts/llm/env

cat > ~/scripts/llm/env/llm-env.sh << 'ENVEOF'
#!/bin/bash
# llm-env.sh — Variables de entorno para motores de inferencia LLM
# Fuente: source ~/scripts/llm/env/llm-env.sh

# ── Token de HuggingFace (requerido para modelos gated: Gemma 4 E4B, GPT OSS 20B)
# Genere su token en: huggingface.co/settings/tokens
export HF_TOKEN="hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXX"      # ← REEMPLAZAR

# ── Clave de API de vLLM (opcional — activa autenticación en vLLM)
# Si se define, TODOS los clientes deben enviar Authorization: Bearer <clave>
# Dejar vacío ("") para modo sin autenticación (recomendado en red local)
export VLLM_API_KEY=""

# ── Rutas CUDA (confirma la versión correcta de CUDA 13 para JP 7.2)
export CUDA_HOME="/usr/local/cuda-13.2"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"

# ── Caché de Tiktoken (requerido para GPT OSS 20B)
export TIKTOKEN_ENCODINGS_BASE="$HOME/.cache/tiktoken"

# ── Directorio de modelos en NVMe (opcional — para modelos descargados manualmente)
export MODELS_DIR="/data/models"

echo "[OK] Entorno LLM activado (HF_TOKEN: ${HF_TOKEN:0:10}...)"
ENVEOF

chmod +x ~/scripts/llm/env/llm-env.sh
echo "[OK] llm-env.sh creado en ~/scripts/llm/env/"
```

```bash
# Editar el token con el editor nano antes de usarlo
nano ~/scripts/llm/env/llm-env.sh
# Reemplazar hf_XXXXX... con su token real de HuggingFace
```

> **IMPORTANTE — Seguridad del token:** El archivo `llm-env.sh` contiene su token de HuggingFace en texto plano. Asegúrese de que el archivo tenga permisos restrictivos y nunca lo comparta ni lo incluya en un repositorio Git:
>
> ```bash
> chmod 600 ~/scripts/llm/env/llm-env.sh
> echo "scripts/llm/env/llm-env.sh" >> ~/.gitignore
> ```

Para usar el entorno antes de lanzar un motor con modelo gated:

```bash
# Activar entorno LLM manualmente
source ~/scripts/llm/env/llm-env.sh
# Salida: [OK] Entorno LLM activado (HF_TOKEN: hf_XXXXXXXX...)

# Ahora lanzar el modelo que requiere el token:
docker run --runtime nvidia -d \
  --name gemma4-e4b-vllm \
  --restart no \
  --network host \
  -e HF_TOKEN=$HF_TOKEN \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve google/gemma-4-E4B-it \
      --dtype bfloat16 \
      --gpu-memory-utilization 0.50 \
      --host 0.0.0.0 --port 8000"
```

Adicionalmente, añada el alias `llm-vars` al `.bashrc` para activar el entorno con un solo comando (el alias `llm-env` está reservado para la activación del venv Python — ver §12.0):

```bash
echo "alias llm-vars='source ~/scripts/llm/env/llm-env.sh'" >> ~/.bashrc
source ~/.bashrc
```

---

## 15.8 Lanzamiento bajo Demanda — Aliases para los Motores de Inferencia

La arquitectura de arranque limpio (§15.0) establece que ningún motor de inferencia arranca automáticamente. El complemento indispensable de esta política es disponer de aliases de lanzamiento que permitan activar cada motor con un solo comando, sin tener que recordar las decenas de parámetros del `docker run`.

Los aliases que se presentan a continuación siguen un patrón consistente: `start-<motor>` para lanzar, `stop-<motor>` para detener (sin borrar el contenedor), y `kill-<motor>` para detener y eliminar. Los contenedores de inferencia se crean siempre con `--restart no`; Open WebUI (que no carga modelos en GPU) puede usar `--restart unless-stopped`.

### 15.8.1 Alias de Lanzamiento bajo Demanda

```bash
# Agregar todos los aliases al ~/.bashrc
cat >> ~/.bashrc << 'ALIASES_EOF'

# ══ Lanzamiento bajo demanda — Motores de inferencia ══════════════════

# ── vLLM: Qwen3.5 35B-A3B ─────────────────────────────────────────────
alias start-qwen35='
  echo "Iniciando Qwen3.5 35B-A3B (MoE)..."
  sudo systemctl start docker 2>/dev/null || true
  pwr-maxn
  sudo docker run -d \
    --name qwen35-35b --restart no \
    --runtime=nvidia --network host \
    --ipc host --shm-size 8g \
    ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
    bash -c "cd /opt && source venv/bin/activate && \
      vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
        --gpu-memory-utilization 0.70 \
        --enable-prefix-caching \
        --enable-auto-tool-choice \
        --tool-call-parser qwen3_coder \
        --served-model-name qwen35 \
        --max-model-len 8192 \
        --host 0.0.0.0 --port 8000"
  echo -n "Esperando qwen35 (primera vez ~10 min, sucesivas ~2 min)"
  until curl -sf http://localhost:8000/v1/models > /dev/null; do echo -n "."; sleep 20; done
  echo " [OK] qwen35 en puerto 8000"
'
alias stop-qwen35='docker stop qwen35-35b && echo "qwen35-35b detenido (contenedor conservado)"'
alias kill-qwen35='docker stop qwen35-35b && docker rm qwen35-35b && echo "qwen35-35b eliminado"'

# ── llama.cpp: Nemotron 3 Nano Omni ───────────────────────────────────
alias start-nemotron='
  echo "Iniciando Nemotron 3 Nano Omni (multimodal)..."
  sudo systemctl start docker 2>/dev/null || true
  pwr-maxn
  sudo docker run -d \
    --name nemotron-omni --restart no \
    --runtime=nvidia --network host \
    -v $HOME/.cache/huggingface:/root/.cache/huggingface \
    ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
    llama-server \
      --hf-repo ggml-org/NVIDIA-Nemotron-3-Nano-Omni \
      --hf-file nemotron-3-nano-omni-ga_v1.0-Q4_K_M.gguf \
      --ctx-size 8192 --n-gpu-layers 999 \
      --alias nemotron-omni \
      --host 0.0.0.0 --port 8080
  echo -n "Esperando nemotron-omni"
  until curl -sf http://localhost:8080/v1/models > /dev/null; do echo -n "."; sleep 10; done
  echo " [OK] nemotron-omni en puerto 8080"
'
alias stop-nemotron='docker stop nemotron-omni && echo "nemotron-omni detenido"'
alias kill-nemotron='docker stop nemotron-omni && docker rm nemotron-omni'

# ── vLLM: Qwen3.5 4B (modelo rápido y ligero) ─────────────────────────
alias start-qwen4b='
  echo "Iniciando Qwen3.5 4B (50 tok/s)..."
  sudo systemctl start docker 2>/dev/null || true
  pwr-30w
  sudo docker run -d \
    --name qwen35-4b --restart no \
    --runtime=nvidia --network host \
    --ipc host --shm-size 8g \
    ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
    bash -c "cd /opt && source venv/bin/activate && \
      vllm serve cyankiwi/Qwen3.5-4B-AWQ-4bit \
        --gpu-memory-utilization 0.80 \
        --enable-prefix-caching \
        --enable-auto-tool-choice \
        --tool-call-parser qwen3_coder \
        --served-model-name qwen4b \
        --max-model-len 16384 \
        --host 0.0.0.0 --port 8000"
  until curl -sf http://localhost:8000/v1/models > /dev/null; do sleep 10; done
  echo "[OK] qwen4b en puerto 8000"
'
alias stop-qwen4b='docker stop qwen35-4b && echo "qwen35-4b detenido"'
alias kill-qwen4b='docker stop qwen35-4b && docker rm qwen35-4b'

# ── Open WebUI (interfaz web — sin GPU) ────────────────────────────────
alias start-webui='
  JETSON_IP=$(hostname -I | awk "{print \$1}")
  echo "Iniciando Open WebUI en http://${JETSON_IP}:3000 ..."
  docker-on 2>/dev/null || true
  if docker inspect open-webui > /dev/null 2>&1; then
    docker start open-webui
  else
    docker run -d \
      --name open-webui \
      --restart no \
      --network host \
      -p 3000:8080 \
      -v open-webui-data:/app/backend/data \
      -e OLLAMA_BASE_URL=http://localhost:11434 \
      ghcr.io/open-webui/open-webui:main
  fi
  echo -n "Esperando Open WebUI"
  until curl -sf http://localhost:3000 > /dev/null 2>&1; do sleep 3; echo -n "."; done
  echo " [OK]"
  echo "  URL local:   http://${JETSON_IP}:3000"
  echo "  URL tunnel:  http://localhost:3000  (desde Windows con: ssh -L 3000:localhost:3000 jetson -N)"
  echo "  SSL:         https://${JETSON_IP}:3000 (si mkcert esta configurado — ver Capitulo 13C)"
  echo "  RAM usada:   $(docker stats open-webui --no-stream --format \"{{.MemUsage}}\" 2>/dev/null)"
'
alias stop-webui='docker stop open-webui && echo "[OK] Open WebUI detenido — datos conservados en volumen open-webui-data"'
alias kill-webui='docker stop open-webui 2>/dev/null; docker rm open-webui 2>/dev/null; echo "[OK] Contenedor eliminado (volumen de datos preservado)"'

# ── Verificar qué motores están activos ────────────────────────────────
alias motors-status='
  echo "═══ Estado de motores de inferencia ═══"
  curl -sf http://localhost:8000/v1/models 2>/dev/null \
    && echo "(vLLM activo en :8000)" \
    || echo "  vLLM :8000 → offline"
  curl -sf http://localhost:8080/v1/models 2>/dev/null \
    && echo "(llama.cpp activo en :8080)" \
    || echo "  llama.cpp :8080 → offline"
  curl -sf http://localhost:11434/api/version 2>/dev/null \
    && echo "  Ollama :11434 → activo" \
    || echo "  Ollama :11434 → offline"
  curl -sf http://localhost:3000 2>/dev/null \
    && echo "  Open WebUI :3000 → activo" \
    || echo "  Open WebUI :3000 → offline"
  echo "════════════════════════════════════════"
  free -h | awk "/^Mem:/{print \"RAM: \"\$3\" usada de \"\$2\", \"\$7\" libres\"}"
'
ALIASES_EOF

source ~/.bashrc
echo "[OK] Aliases de lanzamiento instalados"
```

```
# Verificar aliases disponibles
alias | grep -E "^alias (start-|stop-|kill-|motors-)"
```

```
# Salida esperada
alias kill-nemotron='...'
alias kill-qwen35='...'
alias kill-qwen4b='...'
alias kill-webui='...'
alias motors-status='...'
alias start-nemotron='...'
alias start-qwen35='...'
alias start-qwen4b='...'
alias start-webui='...'
alias stop-nemotron='...'
alias stop-qwen35='...'
alias stop-qwen4b='...'
alias stop-webui='...'
```

### 15.8.2 Flujo Típico de Trabajo

**Ejemplo A — Sesion de trabajo con modelo grande desde Windows:**
```bash
# [WINDOWS POWERSHELL] Conectar al Jetson
ssh jetson

# Verificar estado al arrancar (siempre offline tras boot limpio)
motors-status
check-ready        # confirmar 50+ GB disponibles

# Lanzar el motor (espera automaticamente hasta que este listo)
mode-vllm          # o start-qwen35 para el modelo 35B

# Iniciar Open WebUI y acceder desde el navegador de Windows
start-webui
# [WINDOWS POWERSHELL 2] ssh -L 3000:localhost:3000 jetson -N
# Navegador Windows: http://localhost:3000

# Al terminar la sesion:
stop-webui
mode-stop          # detiene el motor y vuelve a 15W
```

**Ejemplo B — Pipeline avanzado con dos motores:**
```bash
# Nota: 35B (26GB) + Nemotron Omni (24GB) = ~50GB al limite, monitorear con jtop
start-qwen35      # vLLM en :8000 (razonamiento)
start-nemotron    # llama.cpp en :8080 (vision/audio)

# Verificar ambos activos
motors-status

# Usar en pipeline: vLLM para razonamiento, llama.cpp para vision/audio
# ...

kill-qwen35
kill-nemotron
```

> **ATENCIÓN:** Dos modelos grandes (>20B cada uno) simultáneos consumen >48 GB combinados. Antes de lanzarlos ejecute `check-ready` y confirme >50 GB libres. Si hay dudas, use `start-qwen4b` + `start-nemotron` en lugar de `start-qwen35` + `start-nemotron`.

---

## 15.9 Verificación Final del Sistema en Producción

Ejecute este script como verificación final antes de dar el sistema por "listo para producción":

```bash
# Verificación completa de producción
echo "═══ CHECKLIST DE PRODUCCIÓN — Jetson AGX Orin JP 7.2 ═══"
echo ""

# 1. Kernel correcto
KERNEL=$(uname -r)
[[ "$KERNEL" == *"tegra"* ]] && echo "[OK] Kernel Tegra: $KERNEL" || echo "[WARN]  Kernel: $KERNEL (verificar)"

# 2. Políticas de restart
echo ""
echo "── Políticas de restart (NINGÚN LLM debe tener restart automático) ──"
docker inspect $(docker ps -aq 2>/dev/null) 2>/dev/null | python3 -c "
import sys, json
try:
  for c in json.load(sys.stdin):
    n = c['Name'].lstrip('/')
    p = c['HostConfig']['RestartPolicy']['Name']
    llm = any(x in n for x in ['vllm', 'llama', 'gemma', 'qwen', 'nemotron', 'cosmos', 'gpt', 'openclaw'])
    if llm and p in ['always', 'unless-stopped']:
      print(f'  [ERROR] CORREGIR: {n} restart={p}  → docker update --restart=no {n}')
    elif llm:
      print(f'  [OK] {n}: restart={p}')
except: pass
" 2>/dev/null || echo "  Sin contenedores LLM (correcto en idle)"

# 3. OpenClaw
echo ""
echo "── OpenClaw ──"
openclaw gateway status 2>/dev/null | grep -E "running|stopped|error" | head -3 || echo "  Estado desconocido"

# 4. UFW
echo ""
echo "── Firewall UFW ──"
sudo ufw status 2>/dev/null | head -3

# 5. Watchdog
echo ""
echo "── Watchdog (cron) ──"
crontab -l 2>/dev/null | grep -E "watchdog|startup" || echo "  No configurado (ver Sección 15.4)"

# 6. OOM protection
echo ""
echo "── Protección OOM ──"
sysctl vm.panic_on_oom 2>/dev/null | grep -q "= 0" && echo "  [OK] OOM configurado correctamente" || echo "  [WARN]  OOM no configurado"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Sistema listo para producción cuando todos los [OK]"
echo "═══════════════════════════════════════════════════════"
```

---

## Resumen del Capítulo

Este capítulo preparó el Jetson AGX Orin para operación continua en producción:

- **Hardening**: La regla critica es `--restart no` en todos los contenedores LLM. El servicio de Ollama se elimina (no solo desactiva) para evitar el autostart. Se puede revertir con los pasos de §15.1.5.
- **UFW**: El firewall protege los puertos de inferencia (8000, 8080, 11434) y la interfaz web (3000, 4000). El puerto 18789 de OpenClaw nunca se abre — acceso solo via tunel SSH.
- **Startup y watchdog**: El cron ejecuta el startup post-reinicio y verifica el gateway OpenClaw cada 5 minutos.
- **Operacion diaria**: `ssh jetson` → `motors-status` → `mode-vllm` (o el modo elegido) → trabajar → `mode-stop`. El alias `start-webui` muestra la URL local, el comando de tunnel SSH para Windows y el estado de RAM.
- **Reversibilidad**: Todo el hardening puede deshacerse. Los pasos exactos estan en §15.1.5 para usuarios que prefieran autostart.
