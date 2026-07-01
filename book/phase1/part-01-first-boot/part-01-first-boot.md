# Capítulo 1 — Configuración Inicial y Primer Arranque

## Introducción

Esta parte cubre los pasos que van desde un Jetson AGX Orin recién sacado de la caja hasta un sistema Ubuntu 24.04 actualizado, con SSH funcionando y accesible desde su PC Windows. Es el único momento en que necesitará un monitor, teclado y mouse físicos conectados al Jetson — a partir del Paso 5 (SSH), todo el trabajo se realiza de forma remota.

**Tiempo estimado:** 45–90 minutos (principalmente tiempo de espera durante el flash y las actualizaciones)

**Al final de esta parte tendrá:**
- JetPack 7.2 instalado y actualizado
- Ubuntu 24.04.4 LTS en funcionamiento
- Nombre de usuario `jetson`, hostname `jetson-orin`
- Herramientas esenciales de desarrollo instaladas
- `jtop` (monitor especializado del Jetson)
- `tmux` configurado para sesiones persistentes

> **NOTA:** Esta parte asume que parte de un Jetson sin sistema operativo o con JetPack 6.x que quiere actualizar. JetPack 7.2 es una actualización **mayor** (cambia el kernel, Ubuntu, CUDA y Python) que requiere reflash completo — no es una actualización de paquetes. No se puede hacer `apt upgrade` desde JP 6.x.

---

## 1.1 Paso 0 — Respaldar el Sistema Anterior (si aplica)

Si su Jetson tiene JetPack 6.x instalado con configuraciones que quiere conservar, respalde lo necesario antes de flashear. El proceso de flash borra completamente el almacenamiento interno.

```bash
# Ejecutar en el Jetson con JP 6.x ANTES de flashear 
mkdir -p ~/jp62_backup

# 1. Configuración SSH (claves, authorized_keys)
cp -r ~/.ssh ~/jp62_backup/ssh_backup 2>/dev/null || echo "Sin .ssh"

# 2. Aliases y funciones personalizadas del bashrc
cp ~/.bashrc ~/jp62_backup/bashrc_backup.txt

# 3. Configuración tmux
cp ~/.tmux.conf ~/jp62_backup/tmux.conf 2>/dev/null || echo "Sin .tmux.conf"

# 4. Lista de modelos Ollama descargados (para re-descargar después)
ollama list > ~/jp62_backup/ollama_models.txt 2>/dev/null || echo "Ollama no instalado"

# 5. Verificar qué hay en el backup
ls -la ~/jp62_backup/
```

```bash
# Copiar el backup a Windows desde PowerShell
# Ejecute este comando en Windows PowerShell, NO en el Jetson:
# Reemplace "TuUsuario" con su nombre de usuario de Windows
scp -r jetson@192.168.1.100:~/jp62_backup/ C:\Users\TuUsuario\jetson_backup\
```

> **ADVERTENCIA:** Los modelos de HuggingFace en `~/.cache/huggingface/` y los modelos GGUF en `~/models/` pueden ocupar 15–100 GB. Si tiene un SSD USB externo, cópielos antes de flashear para evitar re-descargarlos. Si no tiene SSD externo, deberá descargarlos nuevamente desde internet.

---

## 1.2 Paso 1 — Flashear JetPack 7.2 con ISO

JetPack 7.2 introduce un método de instalación basado en **imagen ISO unificada** — a diferencia de versiones anteriores, no necesita una máquina Linux auxiliar ni el SDK Manager. El proceso es equivalente a instalar Ubuntu desde un USB: crea el USB en Windows, lo inserta en el Jetson y arranca desde él.

### 1.2.1 Descargar la imagen ISO

Vaya a la página oficial de descargas de NVIDIA JetPack:

**developer.nvidia.com/embedded/jetpack/downloads**

Seleccione:
- **JetPack 7.2**
- **Jetson AGX Orin Developer Kit**
- **Download JetPack ISO Image**

El archivo descargado tendrá un nombre similar a `jetpack_7.2_agx_orin.iso` y ocupa aproximadamente 5–8 GB.

### 1.2.2 Crear el USB booteable desde Windows

La herramienta **recomendada oficialmente por NVIDIA** es **Balena Etcher** (etcher.balena.io), disponible gratuitamente para Windows, macOS y Linux:

1. Descargue e instale Balena Etcher.
2. **Importante:** Ejecútelo como administrador en Windows (clic derecho → "Ejecutar como administrador") para evitar errores al escribir en el USB.
3. Inserte un USB de mínimo **16 GB** (se borrará todo su contenido).
4. En Balena Etcher:
   - Haga clic en **"Flash from file"** y seleccione la ISO descargada de JetPack 7.2.
   - Si Etcher no muestra la ISO al navegar, seleccione "All files (*.*)" en el filtro del explorador.
   - En **"Select target"**, elija su USB.
   - Haga clic en **"Flash!"** y confirme.
5. Espere a que Etcher termine y valide el USB (5–8 minutos).

> **ALTERNATIVA — Rufus:** Si prefiere usar Rufus (rufus.ie), configure: Device = su USB, Boot selection = ISO de JetPack 7.2, Partition scheme = GPT, Target system = UEFI (non CSM), File system = FAT32, y haga clic en START. Ambas herramientas producen un resultado equivalente.

### 1.2.3 Poner el Jetson en modo Force Recovery

<!-- INFOGRAFÍA: Pasos para Poner el Jetson en Modo Force Recovery — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


El Jetson debe estar en modo especial de recuperación para arrancar desde USB:

1. **Apague** el Jetson completamente (desconecte la alimentación si es necesario).
2. Conecte el USB con la ISO al Jetson (use el puerto USB tipo A).
3. Localice los **3 botones** en la parte frontal del Developer Kit:
   - Izquierda: **POWER** (encendido)
   - Centro: **FORCE RECOVERY**
   - Derecha: **RESET**
4. **Mantenga presionado FORCE RECOVERY**.
5. Sin soltar FORCE RECOVERY, **conecte el cable de alimentación** (o presione POWER si ya está conectado).
6. Mantenga presionado 2–3 segundos más, luego **suelte**.

```
Posición de los botones en el Developer Kit:
┌─────────────────────────────────────────┐
│  [POWER]  [FORCE REC]  [RESET]          │
│    ←           ↑           →            │
│           Mantener        .             │
│           presionado                    │
│           al encender                   │
└─────────────────────────────────────────┘
```

> **ADVERTENCIA:** Si suelta FORCE RECOVERY antes de que el sistema detecte el USB, el Jetson arrancará normalmente desde el sistema interno. Repita el proceso si no ve la pantalla de instalación.

#### Método alternativo — Boot por menú UEFI

Si el método de Force Recovery no le funciona o no está seguro de qué puerto USB detecta, puede iniciar el Jetson normalmente y seleccionar el USB desde el menú de arranque:

1. Conecte el USB con la ISO al Jetson.
2. Encienda el Jetson normalmente (sin mantener ningún botón).
3. Inmediatamente, presione la tecla **`Esc`** repetidamente en el teclado conectado.
4. Se abrirá el menú de opciones de arranque UEFI.
5. Seleccione su USB como dispositivo de inicio.
6. El instalador de JetPack 7.2 cargará normalmente.

> **NOTA:** Este método alternativo puede funcionar mejor en algunos kits de desarrollo. Consulte también la guía oficial del fabricante en `docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/quick_start.html` si tiene dudas sobre el procedimiento específico de su hardware.

### 1.2.4 Proceso de flash

El Jetson arrancará desde el USB y mostrará una interfaz gráfica de instalación de JetPack. Siga las instrucciones en pantalla:

- Seleccione idioma y distribución de teclado
- Cuando pregunte dónde instalar, seleccione el **eMMC interno** (aparece como el disco de ~59 GB)
- Acepte las licencias de NVIDIA JetPack
- El proceso de flash tarda **15–25 minutos**

> **CONSEJO:** Durante el flash, el Jetson mostrará una barra de progreso. No desconecte la alimentación ni el USB durante este proceso. Si el proceso se detiene más de 10 minutos sin progreso, es probable que el USB no fue creado correctamente — rehágalo con Rufus.

Al terminar, el Jetson se reiniciará automáticamente. Retire el USB cuando vea que arranca desde el disco interno.

---

## 1.3 Paso 2 — Primer Boot y Wizard OEM

Cuando el Jetson arranque por primera vez tras el flash, mostrará el **asistente de configuración inicial** (oem-config). Necesitará monitor, teclado y mouse para este paso. Es la única vez.

### 1.3.1 Configuración durante el wizard

Complete el wizard con los siguientes valores. Algunos son sugeridos — puede cambiarlos si lo prefiere, pero las rutas en este tutorial asumen `jetson` como nombre de usuario:

| Campo | Valor recomendado | Por qué |
|-------|-------------------|---------|
| Nombre de usuario | `jetson` | Los scripts y rutas del tutorial usan `/home/jetson/` |
| Contraseña | (la que elija, anótela) | Se usará para `sudo` en todos los pasos siguientes |
| Nombre de equipo (hostname) | `jetson-orin` | Para identificación en la red y en SSH config |
| Zona horaria | La suya | Necesario para logs con timestamp correcto |
| Teclado | El suyo | Importante para no tener errores al escribir contraseñas |
| Licencias NVIDIA | Aceptar | Requerido para usar CUDA y TensorRT |

Cuando el wizard termine, verá el escritorio de Ubuntu 24.04. Abra una terminal con `Ctrl+Alt+T`.

### 1.3.2 Verificación inmediata del sistema

Lo primero que debe hacer tras el wizard es confirmar que JetPack 7.2 se instaló correctamente:

```bash
# Verificar versión del sistema
cat /etc/os-release | grep -E "^(NAME|VERSION)="
uname -r
cat /etc/nv_tegra_release | head -2
```

```
# Salida esperada
NAME="Ubuntu"
VERSION="24.04.4 LTS (Noble Numbat)"
6.8.12-1021-tegra
# R39 (release), REVISION: 2.0, GCID: ...
```

```bash
# Verificar CUDA (puede no estar en PATH aún — lo corregiremos en Paso 3)
ls /usr/local/cuda/bin/nvcc && echo "nvcc encontrado" || echo "nvcc: se configura el PATH en Paso 3"
```

---

## 1.4 Paso 3 — Configuración Base del Sistema

Este paso configura el sistema operativo Ubuntu 24.04 para uso con el Jetson: actualización, herramientas esenciales, `jtop` (el monitor especializado del Jetson), hostname y path de CUDA.

### 1.4.1 Actualización del sistema

```bash
# Actualizar lista de paquetes e instalar actualizaciones
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
```

```
# Salida esperada (parcial)
Get:1 http://ports.ubuntu.com/ubuntu-ports noble InRelease [256 kB]
...
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
```

**Tiempo estimado:** 5–15 minutos dependiendo de la velocidad de internet.

> **IMPORTANTE:** En el Jetson, NUNCA use `sudo apt dist-upgrade` ni `sudo apt full-upgrade`. Estos comandos pueden actualizar el kernel o los paquetes de JetPack a versiones incompatibles con los drivers de NVIDIA, dejando el sistema sin GPU. Use únicamente `sudo apt upgrade -y`.

### 1.4.2 Instalar herramientas esenciales

```bash
# Instalar herramientas de desarrollo y administración
sudo apt install -y \
  net-tools curl wget htop tmux tree \
  git nano vim unzip zip \
  build-essential \
  python3-pip python3-venv python3-dev \
  software-properties-common pipx \
  apt-transport-https ca-certificates gnupg lsb-release \
  libopenblas-dev libjpeg-dev libpng-dev \
  cmake ninja-build
```

```
# Salida esperada (parcial)
Reading package lists... Done
Building dependency tree... Done
...
Setting up build-essential (12.10ubuntu1) ...
```

**Tiempo estimado:** 3–5 minutos.

**Por qué cada grupo de paquetes:**

| Paquetes | Para qué |
|----------|---------|
| `net-tools curl wget` | Diagnóstico de red, descargas desde terminal |
| `tmux` | Sesiones persistentes que sobreviven desconexiones SSH |
| `git cmake ninja-build` | Compilar llama.cpp y torchvision desde fuente |
| `python3-venv pipx` | Ubuntu 24.04 requiere entornos virtuales para pip |
| `libopenblas-dev` | Dependencia de compilación para PyTorch y llama.cpp |

### 1.4.3 Configurar PATH de CUDA

En JetPack 7.2, el compilador CUDA (`nvcc`) está instalado en `/usr/local/cuda/bin/` pero esa ruta no está en el PATH por defecto. Este es el "fix requerido" que aparece en las especificaciones del sistema:

```bash
# Agregar CUDA al PATH permanentemente
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verificar
nvcc --version
```

```
# Salida esperada
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on ...
Cuda compilation tools, release 13.2, V13.2.1
Build cuda_13.2.r13.2/compiler.xxxxx_0
```

### 1.4.4 Instalar jtop (monitor especializado del Jetson)

`jtop` es el equivalente de `htop` para el Jetson: muestra el uso de CPU, GPU, temperatura, frecuencias, modo de energía y consumo en tiempo real. Es la herramienta de diagnóstico más importante para este sistema.

```bash
# Instalar jetson-stats con pipx (Ubuntu 24.04)
# pipx instala herramientas Python globales sin contaminar el sistema
pipx install jetson-stats
pipx ensurepath
source ~/.bashrc

# Activar el servicio jtop
sudo systemctl restart jtop 2>/dev/null || true

# Verificar instalación
jtop --version
```

```
# Salida esperada (versión 4.x.x o superior)
jetson@jetson-orin:~$ jtop --version
jtop 4.3.2
```

```bash
# Iniciar jtop para ver el estado del sistema
sudo jtop
```

`jtop` abre una interfaz de terminal con varias pestañas (use las teclas numéricas o flechas para navegar):
- **1 — INFO:** versiones de JetPack, CUDA, kernel
- **2 — CTRL:** control de frecuencias y modo de energía
- **3 — GPU:** uso de GPU en tiempo real
- **4 — CPU:** uso por núcleo
- **5 — MEM:** memoria unificada, swap, ZRAM

Presione `q` para salir de jtop.

> **NOTA:** Si `jtop` dice `Service not running` al primer inicio, ejecute `sudo systemctl start jtop` y luego vuelva a lanzarlo.

### 1.4.5 Configurar hostname

El hostname `jetson-orin` identifica el equipo en la red y aparece en el prompt de la terminal:

```bash
# Establecer hostname
sudo hostnamectl set-hostname jetson-orin

# Actualizar /etc/hosts para que el hostname resuelva localmente
sudo sed -i 's/127.0.1.1.*/127.0.1.1\tjetson-orin/' /etc/hosts
# Verificar que el cambio quedó bien:
grep "127.0.1.1" /etc/hosts
```

```
# Salida esperada
127.0.1.1	jetson-orin
```

```bash
# Abrir una nueva terminal para que el cambio de hostname sea visible
bash
# El prompt debe mostrar: jetson@jetson-orin:~$
```

### 1.4.6 Configurar tmux para trabajo headless

`tmux` es un multiplexor de terminal que permite mantener sesiones activas aunque se desconecte de SSH. Es imprescindible para tareas largas como compilaciones (que tardan 30–60 minutos) o descargas de modelos (que pueden tomar horas).

```bash
# Crear configuración de tmux
cat > ~/.tmux.conf << 'EOF'
# Cambiar prefijo de Ctrl+B a Ctrl+A (más ergonómico)
set -g prefix C-a
unbind C-b
bind C-a send-prefix

# Habilitar mouse para redimensionar paneles y hacer scroll
set -g mouse on

# Terminal con colores
set -g default-terminal "screen-256color"

# Numeración desde 1 (más intuitivo en teclado)
set -g base-index 1
setw -g pane-base-index 1

# Historial largo (útil para ver logs completos)
set -g history-limit 50000

# Barra de estado informativa
set -g status-bg colour234
set -g status-fg colour137
set -g status-left "#[fg=green][#S] "
set -g status-right "#[fg=yellow]%Y-%m-%d %H:%M"

# Atajos de teclado para dividir paneles
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"

# Moverse entre paneles con Alt+Flechas
bind -n M-Left  select-pane -L
bind -n M-Right select-pane -R
bind -n M-Up    select-pane -U
bind -n M-Down  select-pane -D

# Recargar configuración con Ctrl+A r
bind r source-file ~/.tmux.conf \; display "Config recargada"
EOF

# Crear sesiones base para uso futuro
tmux new-session -d -s main   # sesión principal de trabajo
tmux new-session -d -s llm    # sesión para modelos de inferencia

# Verificar
tmux ls
```

```
# Salida esperada
llm: 1 windows (created ...)
main: 1 windows (created ...)
```

**Comandos tmux esenciales** (prefijo es `Ctrl+A`):

| Combinación | Acción |
|-------------|--------|
| `Ctrl+A d` | Detach — desconectar de la sesión sin matarla |
| `tmux attach -t main` | Reconectar a la sesión 'main' |
| `Ctrl+A |` | Dividir panel verticalmente |
| `Ctrl+A -` | Dividir panel horizontalmente |
| `Alt+←/→/↑/↓` | Moverse entre paneles |
| `Ctrl+A [` | Modo scroll (salir con `q`) |

---

## 1.5 Paso 4 — Red y Dirección IP Estática

Asignar una IP estática al Jetson es fundamental para que SSH siempre conecte a la misma dirección. Sin IP estática, el router puede asignar una IP diferente tras cada reinicio y perdería el acceso.

### 1.5.1 Identificar la conexión Ethernet

```bash
# Ver conexiones de red disponibles
nmcli device status
nmcli connection show
```

```
# Salida esperada (ejemplo)
DEVICE    TYPE      STATE      CONNECTION
eth0      ethernet  connected  Wired connection 1
lo        loopback  unmanaged  --
```

```bash
# Anotar el nombre exacto de la conexión Ethernet (el que aparece en CONNECTION)
# En el ejemplo: "Wired connection 1"
ip addr show eth0 | grep "inet "
```

### 1.5.2 Asignar IP estática con NetworkManager

```bash
# Reemplazar "Wired connection 1" con el nombre real de su conexión
CONN="Wired connection 1"

sudo nmcli connection modify "$CONN" \
  ipv4.method manual \
  ipv4.addresses "192.168.1.100/24" \
  ipv4.gateway "192.168.1.1" \
  ipv4.dns "8.8.8.8,1.1.1.1" \
  ipv4.ignore-auto-dns yes \
  connection.permissions "" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100

# Aplicar los cambios
sudo nmcli connection down "$CONN" && sudo nmcli connection up "$CONN"
```

> **CONSEJO:** La línea `connection.permissions ""` es crítica. Sin ella, NetworkManager puede no levantar la conexión automáticamente en modo headless (sin sesión gráfica). El `""` vacío indica que la conexión está disponible para todos los usuarios, incluido el sistema en el arranque.

```bash
# Verificar la nueva IP
hostname -I
```

```
# Salida esperada
192.168.1.100
```

> **IMPORTANTE:** Si la IP de su red local no es `192.168.1.x`, ajuste la dirección, gateway y DNS según corresponda. Las partes avanzadas del tutorial (Capítulo 13 — OpenClaw) referencias esta IP. Si cambia la IP, también deberá actualizar los archivos de configuración SSH en Windows.

### 1.5.3 Deshabilitar la espera de red en el arranque

Por defecto, Ubuntu espera hasta 2 minutos a que la red esté disponible antes de completar el boot. Esto ralentiza innecesariamente el inicio del sistema:

```bash
# Deshabilitar la espera de red en boot
sudo systemctl disable NetworkManager-wait-online.service
sudo systemctl mask NetworkManager-wait-online.service
echo "[OK] Espera de red en boot deshabilitada"
```

---

## 1.6 Paso 5 — SSH: Primera Conexión desde Windows

A partir de este paso, todo el trabajo se realiza desde Windows vía SSH. Puede desconectar el monitor del Jetson.

### 1.6.1 Instalar y configurar SSH server en el Jetson

```bash
# Instalar SSH server
sudo apt install -y openssh-server

# Hacer backup de la configuración original
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.original
```

```bash
# Aplicar configuración de producción para SSH
sudo tee /etc/ssh/sshd_config > /dev/null << 'EOF'
Port 22
Protocol 2

# Autenticación
PubkeyAuthentication yes
PasswordAuthentication yes
PermitRootLogin prohibit-password
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 6

# Mantener la sesión viva durante trabajo largo (compilaciones, descargas)
ClientAliveInterval 60
ClientAliveCountMax 10
TCPKeepAlive yes

# X11 para aplicaciones gráficas por SSH (opcional)
X11Forwarding yes
X11UseLocalhost yes

# Logging
LogLevel INFO
SyslogFacility AUTH
EOF

sudo systemctl enable ssh
sudo systemctl restart ssh

# Verificar que está corriendo
sudo systemctl status ssh | grep -E "Active|Loaded"
```

```
# Salida esperada
     Loaded: loaded (/lib/systemd/system/ssh.service; enabled; ...)
     Active: active (running) since ...
```

### 1.6.2 Configurar SSH en Windows

**En Windows PowerShell** (no en el Jetson), genere una clave SSH y cópiela al Jetson:

```powershell
# Generar clave SSH para el Jetson (si no tiene una) [EN WINDOWS POWERSHELL]
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\jetson_orin" -C "windows-to-jetson"
# Presione Enter cuando pregunte por passphrase (sin contraseña para acceso automático)
```

```powershell
# Copiar la clave pública al Jetson [EN WINDOWS POWERSHELL]
# Reemplazar 192.168.1.100 con la IP de su Jetson si es diferente
type "$env:USERPROFILE\.ssh\jetson_orin.pub" | `
  ssh jetson `
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
# Le pedirá la contraseña del Jetson una última vez
```

```powershell
# Configurar el cliente SSH de Windows para acceso por alias [EN WINDOWS POWERSHELL]
$config = @"

Host jetson
    HostName 192.168.1.100
    User jetson
    IdentityFile ~/.ssh/jetson_orin
    ServerAliveInterval 60
    ServerAliveCountMax 10
"@

# Agregar al SSH config de Windows
Add-Content "$env:USERPROFILE\.ssh\config" $config
```

```powershell
# Probar conexión sin contraseña [EN WINDOWS POWERSHELL]
ssh jetson
# Debe conectar directamente sin pedir contraseña
# El prompt debe mostrar: jetson@jetson-orin:~$
```

```
# Salida esperada al conectar
Welcome to Ubuntu 24.04.4 LTS (GNU/Linux 6.8.12-1021-tegra aarch64)
jetson@jetson-orin:~$
```

**A partir de este momento, todas las operaciones se realizan desde la terminal SSH en Windows.** Puede desconectar el monitor, teclado y mouse del Jetson.

### 1.6.3 Agregar el Jetson al archivo hosts de Windows (opcional pero recomendado)

```powershell
# Ejecutar como Administrador en Windows PowerShell [EN WINDOWS POWERSHELL]
Add-Content "C:\Windows\System32\drivers\etc\hosts" "192.168.1.100`tjetson-orin"
# Verificar
ping jetson-orin
```

### 1.6.4 Deshabilitar autenticación por contraseña (después de confirmar las claves)

Una vez que SSH funciona sin contraseña, desactive la autenticación por contraseña para mayor seguridad:

```bash
# En el Jetson via SSH
sudo sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
echo "[OK] Autenticación por contraseña deshabilitada"

# Verificar desde otra terminal de Windows — debe conectar sin contraseña
# Si por error queda bloqueado, conecte monitor+teclado al Jetson para restaurar
```

---

## 1.7 Verificación Final del Capítulo

Al final de esta parte, ejecute la verificación completa desde SSH en Windows:

```bash
# Verificación completa del estado tras Capítulo 1
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     VERIFICACIÓN CAPÍTULO 1 — RESULTADO         ║"
echo "╚══════════════════════════════════════════════╝"

echo ""
echo "── Sistema operativo ──"
lsb_release -d | cut -f2
uname -r

echo ""
echo "── JetPack y L4T ──"
dpkg -l | grep 'nvidia-jetpack ' | awk '{print "JetPack:", $3}' 2>/dev/null || echo "JetPack: (verificar con dpkg -l | grep jetpack)"
cat /etc/nv_tegra_release | head -1

echo ""
echo "── CUDA en PATH ──"
nvcc --version 2>/dev/null | grep "release" || echo "[WARN]  nvcc no en PATH — revisar Paso 3.3"

echo ""
echo "── Red ──"
hostname -I
hostname

echo ""
echo "── SSH ──"
sudo systemctl is-active ssh && echo "[OK] SSH activo" || echo "[ERROR] SSH inactivo"

echo ""
echo "── Herramientas ──"
which tmux && tmux -V
which git && git --version
jtop --version 2>/dev/null && echo "[OK] jtop instalado" || echo "[WARN]  jtop: re-ejecutar pipx install jetson-stats"

echo ""
echo "── Memoria disponible ──"
free -h | awk '/^Mem:/{print "Total:", $2, "| Libre:", $7}'
```

```
# Salida esperada
╔══════════════════════════════════════════════╗
║     VERIFICACIÓN CAPÍTULO 1 — RESULTADO         ║
╚══════════════════════════════════════════════╝

── Sistema operativo ──
Ubuntu 24.04.4 LTS
6.8.12-1021-tegra

── JetPack y L4T ──
JetPack: 7.2-b187
# R39 (release), REVISION: 2.0, ...

── CUDA en PATH ──
Cuda compilation tools, release 13.2, V13.2.1

── Red ──
192.168.1.100
jetson-orin

── SSH ──
active
[OK] SSH activo

── Herramientas ──
/usr/bin/tmux
tmux 3.3a
/usr/bin/git
git version 2.43.0
7.x.x
[OK] jtop instalado

── Memoria disponible ──
Total: 62Gi | Libre: 58Gi
```

Si alguna verificación falla, consulte la siguiente tabla de errores comunes:

| Error | Causa probable | Solución |
|-------|---------------|---------|
| `nvcc: command not found` | PATH de CUDA no configurado | Re-ejecutar el Paso 3.3 y `source ~/.bashrc` |
| IP diferente a 192.168.1.100 | Configuración de red no aplicada | Repetir el Paso 4.2 con el nombre correcto de conexión |
| `jtop: command not found` | pipx no en PATH | Ejecutar `pipx ensurepath && source ~/.bashrc` |
| `JetPack: (verificar...)`  | dpkg aún actualizando índices | Esperar 1 min y re-ejecutar |
| SSH pide contraseña | Clave pública no copiada correctamente | Repetir el Paso 5.2 desde Windows |

---

> **Próximo paso:** El Capítulo 2 cubre la configuración base del sistema: modo headless (sin GUI local), IP estática verificada, GitHub SSH, variables de entorno permanentes y optimización del arranque.
