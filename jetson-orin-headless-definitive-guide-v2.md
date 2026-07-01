# 🚀 NVIDIA Jetson AGX Orin — Guía Definitiva Headless + LLM en Producción
## v2.0 — Consolidada con troubleshooting real | JetPack 6.2.2 | Windows 11

---

> **Hardware:** NVIDIA Jetson AGX Orin Developer Kit 64GB  
> **OS:** Ubuntu 22.04.5 LTS aarch64 | L4T 36.5.0 | JetPack 6.2.2  
> **CUDA:** 12.6 | cuDNN 9.3 | TensorRT 10.3  
> **Host:** Windows 11 (WiFi) → Jetson (Ethernet, misma red)  
> **Objetivo:** 100% headless, GUI remota, SSH, GitHub, JetBrains, vLLM, Ollama

---

## ⚠️ ERRORES CRÍTICOS A EVITAR (Lecciones Aprendidas)

Antes de empezar, lee esto. Son los errores que más tiempo cuestan:

| ❌ NO hagas esto | ✅ Haz esto en cambio |
|------------------|----------------------|
| `sudo apt dist-upgrade` | Solo `sudo apt upgrade` (dist-upgrade rompe JetPack) |
| `sudo systemctl disable gdm` sin arreglar red | Primero arregla `nmcli connection.permissions` |
| `--gpus all` en Docker | Usa `--runtime=nvidia` (Jetson usa GPU integrada) |
| `huggingface-cli download` | Usa `hf download` (CLI nuevo) |
| `google/gemma-4-4b-it` en HuggingFace | Es `google/gemma-4-E4B-it` |
| Instalar vLLM desde source (main branch) | Usa `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` |
| `pip install torch --index-url ...redist/jp/v62` | Usa el CDN `.cn` con v61 y filename exacto |
| `python -m build` desde `~/torchvision` | Funciona. Error: estabas en `~` en lugar de `~/torchvision` |
| `$Host` como variable en PowerShell | Es reservada. Usa `$OllamaHost` |
| Abrir vLLM con Ollama cargado en GPU | Primero `ollama stop <modelo>`, la VRAM es unificada |

---

## 📋 Tabla de Contenidos

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Prerequisitos Windows 11](#2-prerequisitos-windows-11)
3. [Fase 1 — Configuración Inicial Jetson](#3-fase-1--configuración-inicial-jetson)
4. [Fase 2 — Red y IP Estática](#4-fase-2--red-y-ip-estática)
5. [Fase 3 — SSH desde Windows](#5-fase-3--ssh-desde-windows)
6. [Fase 4 — Modo Headless](#6-fase-4--modo-headless)
7. [Fase 5 — XRDP (Remote Desktop)](#7-fase-5--xrdp-remote-desktop)
8. [Fase 6 — NoMachine](#8-fase-6--nomachine)
9. [Fase 7 — GitHub SSH](#9-fase-7--github-ssh)
10. [Fase 8 — JetBrains Gateway](#10-fase-8--jetbrains-gateway)
11. [Fase 9 — VS Code Remote SSH](#11-fase-9--vs-code-remote-ssh)
12. [Fase 10 — Ollama con GPU](#12-fase-10--ollama-con-gpu)
13. [Fase 11 — Docker + NVIDIA Container Toolkit](#13-fase-11--docker--nvidia-container-toolkit)
14. [Fase 12 — Open WebUI](#14-fase-12--open-webui)
15. [Fase 13 — PyTorch para JetPack 6.2](#15-fase-13--pytorch-para-jetpack-62)
16. [Fase 14 — torchvision desde Source](#16-fase-14--torchvision-desde-source)
17. [Fase 15 — vLLM en Producción (NVIDIA Container)](#17-fase-15--vllm-en-producción-nvidia-container)
18. [Fase 16 — Nginx API Gateway](#18-fase-16--nginx-api-gateway)
19. [Fase 17 — Gestión de Servicios](#19-fase-17--gestión-de-servicios)
20. [Referencia Rápida](#20-referencia-rápida)
21. [Guía de Troubleshooting](#21-guía-de-troubleshooting)

---

## 1. Arquitectura del Sistema

```
                    RED LOCAL (192.168.1.0/24)
    ┌──────────────────────────────────────────────────────┐
    │                                                      │
    │      Windows 11 (192.168.1.33) ←── WiFi             │
    │           │                                          │
    │           │  SSH :22 / XRDP :3389 / NX :4000        │
    │           │  Ollama :11434 / vLLM :8000              │
    │           │  Open WebUI :3000 / Jupyter :8888        │
    │           ▼                                          │
    │      Jetson AGX Orin (192.168.1.100) ←── Ethernet   │
    │      64GB RAM unificada / Ampere GPU / CUDA 12.6     │
    └──────────────────────────────────────────────────────┘
```

### Stack de Servicios

```
Puerto  Servicio              Protocolo    Acceso
──────  ───────────────────   ─────────    ────────────────────
22      SSH (OpenSSH)         TCP          Terminal remota
3389    XRDP                  RDP          Remote Desktop (mstsc)
4000    NoMachine             NX           GUI mejor rendimiento
11434   Ollama API            HTTP         7 modelos GGUF
3000    Open WebUI            HTTP         Chat browser
8000    vLLM API              HTTP         Producción / batch
8888    Jupyter Lab           HTTP         Notebooks
```

---

## 2. Prerequisitos Windows 11

### Instalar antes de empezar

```powershell
# Verificar OpenSSH instalado
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'

# Instalar si no está (como Administrador)
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0

# Habilitar SSH Agent (como Administrador)
Set-Service -Name ssh-agent -StartupType Automatic
Start-Service ssh-agent

# Verificar
ssh -V
```

**Herramientas adicionales:**

| Herramienta | Uso | Descarga |
|-------------|-----|---------|
| Windows Terminal | Terminal con perfiles | Microsoft Store |
| NoMachine | GUI remota (mejor rendimiento) | https://nomachine.com/download |
| JetBrains Gateway | Remote IDE | https://jetbrains.com/remote-development/gateway |
| VS Code | Editor + Remote SSH | https://code.visualstudio.com |
| WinSCP | Transferencia de archivos SFTP | https://winscp.net |
| Angry IP Scanner | Encontrar IP del Jetson | https://angryip.org |

---

## 3. Fase 1 — Configuración Inicial Jetson

> ⚠️ **Esta fase requiere monitor + teclado físicos. Es la ÚNICA vez.**

### 3.1 Completar el wizard OEM de primer boot

Conecta monitor, teclado y mouse al Jetson. Sigue el asistente `oem-config`:
- Idioma, zona horaria, teclado
- **Usuario y contraseña** (anótalos bien — los usarás para SSH)
- Acepta las licencias de JetPack

### 3.2 Actualizar el sistema

```bash
# CORRECTO — actualizar sin romper JetPack
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y

# ❌ NUNCA ejecutar en Jetson:
# sudo apt dist-upgrade  ← rompe paquetes L4T/JetPack
```

### 3.3 Instalar herramientas esenciales

```bash
sudo apt install -y \
  net-tools curl wget htop tmux tree \
  git nano vim unzip zip \
  build-essential python3-pip python3-venv \
  software-properties-common \
  apt-transport-https ca-certificates gnupg

# jtop — monitor del sistema específico para Jetson (IMPRESCINDIBLE)
sudo pip3 install -U jetson-stats
sudo systemctl restart jtop
# Uso: jtop
```

### 3.4 Habilitar SSH

```bash
sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl status ssh
# Debe mostrar: Active: active (running)
```

### 3.5 Configurar SSH (/etc/ssh/sshd_config)

```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.original
sudo nano /etc/ssh/sshd_config
```

Asegurar estas líneas (descomentar si es necesario):

```ini
Port 22
PubkeyAuthentication yes
PasswordAuthentication yes          # Cambiar a "no" DESPUÉS de configurar keys
PermitRootLogin prohibit-password
ClientAliveInterval 60
ClientAliveCountMax 10
TCPKeepAlive yes
X11Forwarding yes
MaxAuthTries 6
```

```bash
sudo systemctl restart ssh
```

### 3.6 Cambiar hostname

```bash
sudo hostnamectl set-hostname jetson-orin
sudo nano /etc/hosts
# Cambiar: 127.0.1.1 <nombre-anterior>
# A:       127.0.1.1 jetson-orin
```

---

## 4. Fase 2 — Red y IP Estática

### 4.1 Identificar la conexión Ethernet

```bash
ip addr show
nmcli device status
nmcli connection show
# Anotar: nombre de conexión (ej: "Wired connection 1"), IP actual, gateway
```

### 4.2 Asignar IP estática con NetworkManager

```bash
# CRÍTICO: Esto evita perder acceso de red en modo headless
# Quitar permissions para que la conexión suba sin login de usuario
CONN="Wired connection 1"   # ← reemplaza con tu nombre real

sudo nmcli connection modify "$CONN" \
  ipv4.method manual \
  ipv4.addresses "192.168.1.100/24" \
  ipv4.gateway "192.168.1.1" \
  ipv4.dns "8.8.8.8,1.1.1.1" \
  ipv4.ignore-auto-dns yes \
  connection.permissions "" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100

sudo nmcli connection down "$CONN" && sudo nmcli connection up "$CONN"

# Verificar
hostname -I
```

> 💡 `connection.permissions ""` es el fix crítico que permite que la red suba en boot sin necesitar login gráfico.

### 4.3 Configurar Windows para acceder por hostname

**PowerShell como Administrador:**

```powershell
# Agregar Jetson al archivo hosts de Windows
Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" `
  -Value "`n192.168.1.100  jetson-orin  jetson"

# Vaciar caché DNS
ipconfig /flushdns

# Verificar
ping jetson-orin
```

### 4.4 Alternativa: Reserva DHCP en el router

1. Obtener MAC del Jetson: `ip link show eth0 | grep "link/ether"`
2. Entrar al panel del router (http://192.168.1.1)
3. DHCP → Reserva de dirección → agregar MAC → 192.168.1.100
4. `sudo reboot` y verificar que mantiene la IP

---

## 5. Fase 3 — SSH desde Windows

### 5.1 Primer acceso (con contraseña)

```powershell
ssh jetson@192.168.1.100
# Primera vez: acepta el fingerprint con "yes"
# Introduce tu contraseña de Jetson
```

### 5.2 Generar par de claves SSH en Windows

```powershell
# Generar clave Ed25519 dedicada al Jetson
ssh-keygen -t ed25519 -C "win11-jetson-orin" -f "$env:USERPROFILE\.ssh\jetson_orin"
# Passphrase: opcional (recomendada para seguridad)

# Desplegar clave pública al Jetson
type "$env:USERPROFILE\.ssh\jetson_orin.pub" | `
  ssh jetson@192.168.1.100 `
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### 5.3 Crear archivo SSH config en Windows

```powershell
notepad "$env:USERPROFILE\.ssh\config"
```

Contenido completo del config:

```ini
# ─────────────────────────────────────────
#  Jetson AGX Orin — SSH estándar
# ─────────────────────────────────────────
Host jetson
    HostName 192.168.1.100
    User jetson
    IdentityFile ~/.ssh/jetson_orin
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 10
    TCPKeepAlive yes
    Compression yes

# ─────────────────────────────────────────
#  Jetson — Con todos los túneles de servicios
# ─────────────────────────────────────────
Host jetson-tunnels
    HostName 192.168.1.100
    User jetson
    IdentityFile ~/.ssh/jetson_orin
    IdentitiesOnly yes
    LocalForward 11434 localhost:11434    # Ollama API
    LocalForward 8000  localhost:8000     # vLLM API
    LocalForward 8888  localhost:8888     # Jupyter Lab
    LocalForward 3000  localhost:3000     # Open WebUI
    ServerAliveInterval 30
    ServerAliveCountMax 6
    ExitOnForwardFailure yes

# ─────────────────────────────────────────
#  GitHub (configurado en Fase 7)
# ─────────────────────────────────────────
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_key
    IdentitiesOnly yes
```

### 5.4 Agregar clave al agente SSH de Windows

```powershell
ssh-add "$env:USERPROFILE\.ssh\jetson_orin"
ssh-add -l    # Verificar que está cargada
```

### 5.5 Probar acceso sin contraseña

```powershell
ssh jetson
# Debe conectar SIN pedir contraseña
```

### 5.6 Deshabilitar autenticación por contraseña (después de confirmar que las keys funcionan)

```bash
# En el Jetson
sudo nano /etc/ssh/sshd_config
# Cambiar:
PasswordAuthentication no
ChallengeResponseAuthentication no

sudo systemctl restart ssh
```

### 5.7 Configurar tmux para sesiones persistentes

```bash
# Instalar tmux
sudo apt install tmux -y

# Crear configuración
cat > ~/.tmux.conf << 'EOF'
set -g prefix C-a
unbind C-b
bind C-a send-prefix
set -g mouse on
set -g default-terminal "screen-256color"
set -g base-index 1
setw -g pane-base-index 1
set -g history-limit 50000
set -g status-bg colour234
set -g status-fg colour137
set -g status-left "#[fg=green][#S] "
set -g status-right "#[fg=yellow]%Y-%m-%d %H:%M"
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
bind -n M-Left  select-pane -L
bind -n M-Right select-pane -R
bind -n M-Up    select-pane -U
bind -n M-Down  select-pane -D
bind r source-file ~/.tmux.conf \; display "Reloaded!"
EOF

# Crear sesiones persistentes
tmux new-session -d -s main
tmux new-session -d -s llm

# Comandos esenciales:
# Ctrl+A d     → detach (sesión sigue corriendo)
# tmux attach -t main  → reconectar
# tmux ls      → listar sesiones
```

---

## 6. Fase 4 — Modo Headless

### 6.1 Estrategia correcta (lección aprendida)

**NO** deshabilites GDM sin antes arreglar NetworkManager (Fase 2).  
**SÍ** usa `graphical.target` con display virtual — es más estable.

### 6.2 Forzar X11 (deshabilitar Wayland)

Wayland es incompatible con XRDP y la mayoría de herramientas de escritorio remoto.

```bash
# Deshabilitar Wayland en GDM3
sudo nano /etc/gdm3/custom.conf
```

```ini
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=jetson
WaylandEnable=false

[security]
[xdmcp]
[chooser]
[debug]
```

```bash
# Variables de entorno globales para X11
sudo nano /etc/environment
```

Agregar al final de `/etc/environment`:
```bash
QT_QPA_PLATFORM=xcb
GDK_BACKEND=x11
XDG_SESSION_TYPE=x11
```

### 6.3 Instalar driver Xorg Dummy (display virtual)

El Jetson sin monitor conectado genera un framebuffer de 640x480 que hace que XRDP y NoMachine funcionen mal.

```bash
sudo apt install xserver-xorg-video-dummy -y

sudo nano /etc/X11/xorg.conf.d/30-tegra-headless.conf
```

```
Section "Device"
    Identifier  "Tegra"
    Driver      "nvidia"
    Option      "AllowEmptyInitialConfiguration" "true"
    Option      "UseDisplayDevice" "none"
EndSection

Section "Monitor"
    Identifier  "Monitor0"
    HorizSync   28.0-80.0
    VertRefresh 48.0-75.0
    Modeline    "1920x1080" 148.50 1920 2008 2052 2200 1080 1084 1089 1125 +hsync +vsync
EndSection

Section "Screen"
    Identifier  "Screen0"
    Device      "Tegra"
    Monitor     "Monitor0"
    DefaultDepth 24
    SubSection "Display"
        Depth    24
        Virtual  1920 1080
    EndSubSection
EndSection
```

### 6.4 Desactivar screensaver y power management

```bash
# Ejecutar vía SSH como tu usuario
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0
gsettings set org.gnome.settings-daemon.plugins.power idle-dim false
gsettings set org.gnome.settings-daemon.plugins.power power-button-action 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power ambient-enabled false
```

### 6.5 Configurar boot headless permanente

```bash
sudo systemctl set-default graphical.target
sudo systemctl restart gdm3

# Verificar
systemctl get-default
# Debe mostrar: graphical.target
```

### 6.6 Deshabilitar servicio de snapd que interfiere

```bash
sudo snap stop snapd-desktop-integration
sudo snap disable snapd-desktop-integration
```

### 6.7 Desactivar servicio de espera de red en boot

```bash
sudo systemctl disable NetworkManager-wait-online.service
sudo systemctl mask NetworkManager-wait-online.service
```

---

## 7. Fase 5 — XRDP (Remote Desktop)

### 7.1 Instalar XRDP

```bash
sudo apt install xrdp -y
sudo adduser xrdp ssl-cert    # Fix de permisos de certificado SSL
```

### 7.2 Configurar inicio de sesión GNOME en XRDP

**Fix principal del black screen** — este archivo es el más importante:

```bash
sudo nano /etc/xrdp/startwm.sh
```

Reemplazar el contenido completo con:

```bash
#!/bin/sh
# xrdp session startup — Ubuntu 22.04 GNOME — Jetson AGX Orin

if test -r /etc/profile; then
    . /etc/profile
fi

# CRÍTICO: estas tres variables resuelven el black screen en Ubuntu 22.04
export DESKTOP_SESSION=ubuntu
export GNOME_SHELL_SESSION_MODE=ubuntu
export XDG_CURRENT_DESKTOP=ubuntu:GNOME

# Limpiar variables que causan conflictos entre sesiones
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR

test -x /etc/X11/Xsession && exec /etc/X11/Xsession
exec /bin/sh /etc/X11/Xsession
```

```bash
sudo chmod +x /etc/xrdp/startwm.sh
```

### 7.3 Crear archivos de sesión de usuario

```bash
cat > ~/.xsessionrc << 'EOF'
export XDG_SESSION_TYPE=x11
export GNOME_SHELL_SESSION_MODE=ubuntu
export XDG_CURRENT_DESKTOP=ubuntu:GNOME
export XDG_CONFIG_DIRS=/etc/xdg/xdg-ubuntu:/etc/xdg
export DESKTOP_SESSION=ubuntu
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR
EOF

cat > ~/.xsession << 'EOF'
#!/bin/bash
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR
export GNOME_SHELL_SESSION_MODE=ubuntu
export XDG_CURRENT_DESKTOP=ubuntu:GNOME
export XDG_CONFIG_DIRS=/etc/xdg/xdg-ubuntu:/etc/xdg
export DESKTOP_SESSION=ubuntu
export XDG_SESSION_TYPE=x11
exec /usr/bin/gnome-session --session=ubuntu
EOF
chmod +x ~/.xsession
```

### 7.4 Fix de PolicyKit / colord (causa frecuente de black screen secundario)

```bash
sudo mkdir -p /etc/polkit-1/localauthority/50-local.d/

sudo tee /etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla << 'EOF'
[Allow Colord all Users]
Identity=unix-user:*
Action=org.freedesktop.color-manager.create-device;org.freedesktop.color-manager.create-profile;org.freedesktop.color-manager.delete-device;org.freedesktop.color-manager.delete-profile;org.freedesktop.color-manager.modify-device;org.freedesktop.color-manager.modify-profile
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF
```

### 7.5 Habilitar y arrancar XRDP

```bash
sudo systemctl enable xrdp
sudo systemctl restart xrdp
sudo systemctl status xrdp

# Verificar que escucha en puerto 3389
sudo ss -tlnp | grep 3389
# Debe mostrar: 0.0.0.0:3389

# Abrir firewall
sudo ufw allow 3389/tcp comment "XRDP Remote Desktop"
sudo ufw reload
```

### 7.6 Conectar desde Windows

1. `Win+R` → `mstsc` → Enter
2. Computer: `192.168.1.100`
3. Click **Show Options** → configurar:
   - **Display**: 1920x1080, 32-bit color
   - **Experience**: LAN (10 Mbps+), Persistent bitmap caching
   - **Local Resources**: Clipboard checked, Audio "Do not play"
4. Click **Connect** → aceptar certificado → usuario + contraseña del Jetson

**Si aparece pantalla negra:**
```bash
# Desde otra terminal SSH, matar sesiones huérfanas
ps aux | grep gnome-session
# Matar los PIDs de sesiones anteriores (no los de gdm):
kill <PID1> <PID2>
sudo systemctl restart xrdp
# Reconectar RDP
```

**Si GNOME sigue dando problemas, instalar XFCE4 (más compatible):**
```bash
sudo apt install xfce4 xfce4-goodies -y
echo 'exec startxfce4' > ~/.xsession
chmod +x ~/.xsession
sudo systemctl restart xrdp
```

---

## 8. Fase 6 — NoMachine

> **NoMachine es la mejor opción de escritorio remoto para Jetson** — mejor rendimiento que XRDP, especialmente para trabajo prolongado.

### 8.1 Instalar NoMachine en el Jetson

```bash
# IMPORTANTE: Usar el CDN correcto y la versión actual
# Versión actual (Jun 2026): 9.7.3
# NO usar: download.nomachine.com/download/8.14/... (versión antigua, URL errónea)

cd ~/Downloads
wget "https://web9001.nomachine.com/download/9.7/Arm/nomachine_9.7.3_1_arm64.deb"

# Verificar tamaño (~74MB)
ls -lh nomachine_9.7.3_1_arm64.deb

# Instalar
sudo dpkg -i nomachine_9.7.3_1_arm64.deb
sudo apt --fix-broken install -y

# Las advertencias de CUPS son normales (impresoras) — no es un error

# Verificar que arrancó
sudo /usr/NX/bin/nxserver --status
# Debe mostrar: Running server at port: 4000

# Abrir firewall
sudo ufw allow 4000/tcp comment "NoMachine NX"
```

> 💡 Si 9.7.3 ya no está disponible, obtén el link actual desde:
> https://downloads.nomachine.com/download/?id=30&platform=linux&distro=arm
> (busca el DEB arm64 para Ubuntu/Debian)

### 8.2 Fix headless para NoMachine — display virtual

Cuando no hay monitor físico, NoMachine puede conectar al display de GDM pero sin entrada de mouse/teclado. Fix permanente:

```bash
# Opción A: La más limpia — dejar que GDM corra con el Xorg dummy de la Fase 4
# El driver "nvidia" con AllowEmptyInitialConfiguration crea un framebuffer virtual
# NoMachine detecta el X server activo y conecta correctamente
sudo systemctl restart gdm3
sudo /usr/NX/bin/nxserver --restart

# Opción B: Si sigue sin funcionar — forzar display virtual propio de NoMachine
sudo systemctl stop gdm3
sudo /usr/NX/bin/nxserver --restart
# NoMachine creará su propio X server virtual
```

### 8.3 Configurar resolución en NoMachine

```bash
sudo nano /usr/NX/etc/node.cfg
```

Buscar y modificar (descomentar quitando `#`):
```
DisplayGeometry 1920x1080
AllowDesktopResize 1
```

```bash
sudo /usr/NX/bin/nxserver --restart
```

### 8.4 Instalar NoMachine en Windows 11

Descargar de: https://www.nomachine.com/download (versión Windows x64)

### 8.5 Conectar desde Windows

1. Abrir **NoMachine**
2. **Add** → Protocol: **NX** → Host: `192.168.1.100` → Port: `4000`
3. Authentication: **Password**
4. Click **Connect** → aceptar fingerprint
5. Usuario + contraseña del Jetson
6. Seleccionar **"Connect to the physical desktop"** o crear nueva sesión virtual

**Si no hay entrada de mouse/teclado:**
- Asegúrate de que el display virtual de Xorg está activo (Fase 4)
- Reconectar seleccionando "Create a new virtual display" en lugar de "physical desktop"

### 8.6 Autostart NoMachine en boot

```bash
sudo systemctl enable nxserver 2>/dev/null || \
  sudo /usr/NX/bin/nxserver --startup
```

---

## 9. Fase 7 — GitHub SSH

### 9.1 Generar clave SSH en el Jetson para GitHub

```bash
# SSH into Jetson desde Windows
ssh jetson

# Generar clave dedicada a GitHub
ssh-keygen -t ed25519 \
  -C "jetson-orin-$(date +%Y%m%d)" \
  -f ~/.ssh/github_ed25519
# Passphrase: recomendada

# Configurar SSH agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/github_ed25519

# Agregar al shell para inicio automático
cat >> ~/.bashrc << 'EOF'
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval "$(ssh-agent -s)" > /dev/null
  ssh-add ~/.ssh/github_ed25519 2>/dev/null
fi
EOF
```

### 9.2 Agregar clave a GitHub

```bash
# Mostrar la clave pública
cat ~/.ssh/github_ed25519.pub
```

1. Copiar el output completo
2. Ir a https://github.com/settings/keys
3. **New SSH key** → Title: "Jetson AGX Orin" → Key type: Authentication Key
4. Pegar la clave → **Add SSH key**

### 9.3 Configurar SSH config en el Jetson

```bash
nano ~/.ssh/config
```

```ini
# GitHub
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
```

### 9.4 Verificar conexión

```bash
ssh -T git@github.com
# Esperado: "Hi username! You've successfully authenticated..."
```

### 9.5 Configurar Git global

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
git config --global core.editor "nano"
git config --global init.defaultBranch main
git config --global pull.rebase false

# Usar SSH en lugar de HTTPS para GitHub
git config --global url."git@github.com:".insteadOf "https://github.com/"

# Aliases útiles
git config --global alias.st status
git config --global alias.lg "log --oneline --graph --decorate --all"
```

---

## 10. Fase 8 — JetBrains Gateway

### 10.1 Instalar JetBrains Gateway en Windows

Descargar de: https://www.jetbrains.com/remote-development/gateway/

### 10.2 Configurar conexión SSH en Gateway

1. Abrir **JetBrains Gateway**
2. **New Connection** → SSH
3. Configurar:
   - Host: `192.168.1.100`
   - Port: `22`
   - Username: `jetson`
   - Authentication: Key pair
   - Private key: `C:\Users\TuUsuario\.ssh\jetson_orin`
4. **Check Connection and Continue**
5. Seleccionar IDE (ej: PyCharm 2026.1)
6. Seleccionar directorio de proyecto en el Jetson
7. **Download IDE and Connect** (~600MB, primera vez)

### 10.3 Optimizar JVM del backend (ubicación correcta)

```bash
# Encontrar el archivo vmoptions real del backend instalado
find ~/.cache/JetBrains -name "*.vmoptions" 2>/dev/null
# Ejemplo: ~/.cache/JetBrains/RemoteDev/dist/4c879fee91167_pycharm-2026.1.3-aarch64/bin/pycharm64.vmoptions

# IMPORTANTE: Editar pycharm64.vmoptions (no jetbrains_client64.vmoptions)
VMOPTIONS="$HOME/.cache/JetBrains/RemoteDev/dist/$(ls ~/.cache/JetBrains/RemoteDev/dist/ | head -1)/bin/pycharm64.vmoptions"
nano "$VMOPTIONS"
```

Modificar SOLO estas líneas (mantener el resto intacto):
```
-Xms512m          ← (era -Xms256m)
-Xmx8192m         ← (era -Xmx2048m)
-XX:CICompilerCount=4   ← (era -XX:CICompilerCount=2)
```

```bash
# Guardar override persistente (sobrevive actualizaciones)
mkdir -p ~/.config/JetBrains/RemoteDev-PY

cp "$VMOPTIONS" ~/.config/JetBrains/RemoteDev-PY/pycharm64.vmoptions

# Verificar cambios
grep -E "^-Xms|^-Xmx|^-XX:CICompilerCount" ~/.config/JetBrains/RemoteDev-PY/pycharm64.vmoptions
```

### 10.4 Si Gateway muestra "Host has no projects"

Es normal — Gateway conectó bien pero no tiene proyectos recientes.

```bash
# Crear estructura de proyectos
mkdir -p ~/projects/llm-test

cat > ~/projects/llm-test/main.py << 'EOF'
import torch
print(f"CUDA: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
EOF
```

En Gateway: Click **Open Project** → seleccionar `/home/jetson/projects/llm-test`

### 10.5 Si Gateway se cuelga al conectar

```bash
# Limpiar procesos y locks
pkill -9 -f "pycharm\|RemoteDev\|idea" 2>/dev/null
find ~/.cache/JetBrains -name "port" -delete 2>/dev/null
find ~/.cache/JetBrains -name "*.lock" -delete 2>/dev/null

# Para reinstalar backend desde cero
rm -rf ~/.cache/JetBrains/RemoteDev
rm -rf ~/.cache/JetBrains/RemoteDev-PY
rm -rf ~/.config/JetBrains/RemoteDev-PY
```
Luego reconectar desde Gateway — descargará el backend de nuevo.

---

## 11. Fase 9 — VS Code Remote SSH

### 11.1 Instalar extensión Remote-SSH en Windows

1. VS Code → `Ctrl+Shift+X`
2. Buscar: **Remote - SSH** (by Microsoft)
3. Instalar también: **Remote - SSH: Editing Configuration Files**

### 11.2 Conectar al Jetson

`Ctrl+Shift+P` → **Remote-SSH: Connect to Host** → seleccionar `jetson`

VS Code instalará el servidor automáticamente en el Jetson (primera vez ~30 segundos).

### 11.3 Extensiones para instalar en remoto (Jetson)

Con la ventana remota abierta, instalar:
- Python, Pylance, Jupyter
- GitLens, Docker
- CUDA C++ (nvidia.nsight-vscode-edition)

### 11.4 Settings remotos recomendados

`.vscode/settings.json` en tu proyecto:

```json
{
    "python.defaultInterpreterPath": "/home/jetson/venvs/llm/bin/python3",
    "python.linting.enabled": true,
    "editor.formatOnSave": true,
    "terminal.integrated.defaultProfile.linux": "bash",
    "jupyter.jupyterServerType": "local",
    "git.autofetch": true
}
```

---

## 12. Fase 10 — Ollama con GPU

### 12.1 Verificar GPU antes de instalar

```bash
nvidia-smi
nvcc --version
# Esperado: CUDA 12.6
```

### 12.2 Instalar Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
sudo systemctl status ollama
```

### 12.3 Configurar Ollama para acceso desde red

**Este es el paso que más se olvida** — por defecto Ollama solo escucha en localhost.

```bash
# Crear override de systemd para Ollama
sudo mkdir -p /etc/systemd/system/ollama.service.d/

sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF

# Aplicar
sudo systemctl daemon-reload
sudo systemctl restart ollama
sleep 3

# Verificar que ahora escucha en 0.0.0.0 (no 127.0.0.1)
sudo ss -tlnp | grep 11434
# Debe mostrar: *:11434 (no 127.0.0.1:11434)

# Abrir firewall
sudo ufw allow 11434/tcp comment "Ollama API"
```

### 12.4 Descargar modelos

```bash
# Modelos recomendados para Jetson AGX Orin 64GB
ollama pull gemma4:latest          # ~9.6GB — rápido y capaz
ollama pull gemma4:26b             # ~17GB — máxima calidad Gemma4
ollama pull ministral-3:latest     # ~6GB  — muy rápido
ollama pull qwen2.5:7b             # ~4.7GB — excelente general

# Modelos de código
ollama pull qwen2.5-coder:7b       # ~4.7GB

# Modelos de embedding (para RAG)
ollama pull nomic-embed-text       # ~0.3GB

# Ver modelos instalados
ollama list

# Test rápido
ollama run gemma4:latest "Hola, ¿qué puedes hacer?"
```

### 12.5 Probar desde Windows

```powershell
# Ver modelos disponibles
(Invoke-RestMethod -Uri "http://192.168.1.100:11434/api/tags").models |
    ForEach-Object {
        [PSCustomObject]@{
            Name       = $_.name
            "Size(GB)" = [math]::Round($_.size / 1GB, 1)
        }
    } | Format-Table -AutoSize

# Función de chat reutilizable (IMPORTANTE: no usar $Host, es reservada en PowerShell)
function Invoke-Ollama {
    param(
        [string]$Model = "gemma4:latest",
        [string]$Prompt,
        [string]$OllamaHost = "192.168.1.100"   # ← OllamaHost, no Host
    )
    $body = @{
        model  = $Model
        prompt = $Prompt
        stream = $false
    } | ConvertTo-Json

    Write-Host "[$Model] Thinking..." -ForegroundColor Cyan
    $start = Get-Date
    $response = Invoke-RestMethod `
        -Uri "http://${OllamaHost}:11434/api/generate" `
        -Method Post -ContentType "application/json" -Body $body
    $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    Write-Host "[$Model] ${elapsed}s" -ForegroundColor Green
    Write-Host $response.response
}

# Uso
Invoke-Ollama -Model "gemma4:latest" -Prompt "Hello from Windows!"
```

### 12.6 Guardar función en perfil PowerShell

```powershell
# Agregar función al perfil permanente
notepad $PROFILE
# (Si no existe: New-Item -Path $PROFILE -ItemType File -Force)
# Pegar la función Invoke-Ollama y guardar
```

---

## 13. Fase 11 — Docker + NVIDIA Container Toolkit

### 13.1 Instalar Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verificar
docker run hello-world
```

### 13.2 Instalar NVIDIA Container Toolkit

```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
# NOTA: Si aparece "will be DOWNGRADED", NO confirmar. Saltar con Ctrl+C
# Solo instalar si no hay conflictos de versión
sudo apt install -y nvidia-container-toolkit --allow-downgrades 2>/dev/null || \
  echo "Usando versión existente del toolkit"
```

### 13.3 Configurar Docker con runtime NVIDIA

```bash
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker

# Verificar
docker info | grep -i "Default Runtime"
# Debe mostrar: Default Runtime: nvidia
```

### 13.4 Test GPU en Docker (Jetson-specific)

```bash
# ❌ ESTO NO FUNCIONA EN JETSON:
# docker run --rm --gpus all ubuntu nvidia-smi
# Error: "nvidia-smi not found" — es normal, Jetson usa GPU integrada

# ✅ ESTO SÍ FUNCIONA EN JETSON:
docker run --rm --runtime=nvidia ubuntu:22.04 \
  bash -c "ls /dev/ | grep -E 'nvhost|nvmap|tegra' | head -5"
# Debe listar: nvhost-ctrl, nvhost-gpu, nvmap, etc.
```

---

## 14. Fase 12 — Open WebUI

Open WebUI provee una interfaz de chat tipo ChatGPT para tus modelos de Ollama.

### 14.1 Ejecutar Open WebUI con Docker

```bash
docker run -d \
  --name open-webui \
  --restart always \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  ghcr.io/open-webui/open-webui:main

sudo ufw allow 3000/tcp comment "Open WebUI"

# Esperar ~60-90 segundos (primera vez hace migraciones de DB)
docker logs open-webui --follow
# Esperar hasta ver: "Application startup complete."
```

### 14.2 Acceder desde Windows

Navegar a: `http://192.168.1.100:3000`

Primera visita:
1. Click **Get Started**
2. Crear cuenta de administrador (email + contraseña, son locales)
3. Seleccionar modelo desde el dropdown en la esquina superior izquierda
4. ¡Chatear!

### 14.3 Verificar conexión Open WebUI → Ollama

```bash
docker exec open-webui \
  curl -s http://host.docker.internal:11434/api/tags \
  | python3 -m json.tool | grep "name" | head -5
# Debe listar tus modelos de Ollama
```

---

## 15. Fase 13 — PyTorch para JetPack 6.2

> PyTorch en Jetson NO se instala con `pip install torch` estándar. Requiere wheels especiales de NVIDIA.

### 15.1 Instalar prerequisitos

```bash
sudo apt-get install -y python3-pip libopenblas-dev libjpeg-dev libpng-dev cmake ninja-build

# Crear entorno virtual
python3 -m venv ~/venvs/llm
source ~/venvs/llm/bin/activate

# Actualizar pip
pip install --upgrade pip
```

### 15.2 Instalar cuSPARSELt (OBLIGATORIO antes de PyTorch 2.5+)

```bash
source ~/venvs/llm/bin/activate

# Verificar si ya está instalado
ls /usr/local/cuda/lib64/libcusparseLt.so 2>/dev/null && echo "Ya instalado" || echo "Necesita instalación"

# Si no está, instalar
cd ~/Downloads
wget https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-sbsa/libcusparse_lt-linux-sbsa-0.7.0.0-archive.tar.xz

tar xf libcusparse_lt-linux-sbsa-0.7.0.0-archive.tar.xz

sudo cp -a libcusparse_lt-linux-sbsa-0.7.0.0-archive/include/* /usr/local/cuda/include/
sudo cp -a libcusparse_lt-linux-sbsa-0.7.0.0-archive/lib/* /usr/local/cuda/lib64/

# Verificar
ls /usr/local/cuda/lib64/libcusparseLt.so
```

### 15.3 Instalar NumPy (versión requerida)

```bash
pip install numpy==1.26.1
```

### 15.4 Instalar PyTorch con el wheel correcto

```bash
source ~/venvs/llm/bin/activate

# ATENCIÓN: URL EXACTA — cada parte del nombre es crítica
# ✅ Correcto: nvidia.CN (no .com), v61 (no v62), nv24.08 (no nv24.09)
pip install --no-cache-dir \
  https://developer.download.nvidia.cn/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl
```

Si el URL anterior da error 404, buscar el wheel disponible:
```bash
curl -s https://developer.download.nvidia.cn/compute/redist/jp/v61/pytorch/ \
  | grep -o 'torch-[^"]*aarch64\.whl' | sort
```

### 15.5 Verificar PyTorch + CUDA

```bash
cd ~    # ← IMPORTANTE: salir del directorio de source si estuvieras en uno
source ~/venvs/llm/bin/activate

python3 -c "
import torch
print('PyTorch  :', torch.__version__)
print('CUDA     :', torch.cuda.is_available())
print('CUDA ver :', torch.version.cuda)
if torch.cuda.is_available():
    print('GPU      :', torch.cuda.get_device_name(0))
    print('GPU mem  :', torch.cuda.get_device_properties(0).total_memory // (1024**3), 'GB')
    x = torch.randn(3,3).cuda()
    print('GPU test :', x.shape, 'on', x.device)
"
# Esperado: CUDA: True, GPU: Orin, 61 GB
```

---

## 16. Fase 14 — torchvision desde Source

> torchvision no tiene wheel precompilado para Jetson JetPack 6.2 — hay que compilarlo.

### 16.1 Clonar el repo

```bash
cd ~
git clone --branch v0.20.0 --depth 1 https://github.com/pytorch/vision torchvision
cd torchvision
```

### 16.2 Compilar con el fix de FFmpeg

```bash
source ~/venvs/llm/bin/activate

# Instalar wheel backend
pip install wheel setuptools build

export BUILD_VERSION=0.20.0
export TORCH_CUDA_ARCH_LIST="8.7"
export MAX_JOBS=4
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH

# CRÍTICO: TORCHVISION_USE_FFMPEG=0 evita el error:
# "'AVFrame' has no member named 'key_frame'"
FORCE_CUDA=1 \
TORCHVISION_USE_FFMPEG=0 \
python setup.py bdist_wheel 2>&1 | tail -10
```

Si muestra `removing build/bdist.linux-aarch64/wheel` al final → compilación exitosa.

### 16.3 Instalar y verificar

```bash
pip install dist/torchvision-0.20.0-cp310-cp310-linux_aarch64.whl

# IMPORTANTE: Verificar desde ~, NO desde ~/torchvision
cd ~
python3 -c "
import torch, torchvision
print('PyTorch     :', torch.__version__)
print('TorchVision :', torchvision.__version__)
print('CUDA        :', torch.cuda.is_available())

# Test NMS op (verifica que las extensiones CUDA compilaron bien)
boxes  = torch.tensor([[0,0,10,10],[1,1,11,11]], dtype=torch.float32).cuda()
scores = torch.tensor([0.9, 0.8]).cuda()
result = torchvision.ops.nms(boxes, scores, 0.5)
print('NMS op      :', result)
print('Stack OK para vLLM')
"
```

---

## 17. Fase 15 — vLLM en Producción (NVIDIA Container)

> **NO intentes compilar vLLM desde source con el main branch** — requiere PyTorch 2.6+ (`torch/csrc/stable/library.h`). Usa el container oficial de NVIDIA.

### 17.1 Por qué el container oficial

- vLLM main branch: requiere `torch/csrc/stable/library.h` → solo en PyTorch 2.6+
- JetPack 6.2 tiene PyTorch 2.5 máximo en wheels precompilados
- NVIDIA mantiene containers optimizados para Jetson con vLLM 0.19.0

### 17.2 Pull del container

```bash
docker pull ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin

# Verificar versión de vLLM incluida
docker run --rm ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  python3 -c "import vllm; print('vLLM:', vllm.__version__)"
# vLLM: 0.19.0
```

### 17.3 Descargar modelo desde HuggingFace

```bash
source ~/venvs/llm/bin/activate

# Nuevo CLI: "hf" (no "huggingface-cli" — está deprecado)
hf auth login
# Token desde: https://huggingface.co/settings/tokens
# Acepta la licencia de Gemma en: https://huggingface.co/google/gemma-4-E4B-it

mkdir -p ~/models/hf

# Modelo Gemma4 E4B (4B denso — eficiente, ~15GB)
# NOMBRE CORRECTO: google/gemma-4-E4B-it (NO google/gemma-4-4b-it)
hf download google/gemma-4-E4B-it \
  --local-dir ~/models/hf/gemma-4-E4B-it

# Verificar
ls -lh ~/models/hf/gemma-4-E4B-it/
du -sh ~/models/hf/gemma-4-E4B-it/
```

### 17.4 Lanzar vLLM (comando completo con todos los fixes)

```bash
# ANTES DE LANZAR: liberar GPU de Ollama (la VRAM es unificada)
ollama stop $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}') 2>/dev/null
sleep 2

# Verificar memoria disponible
nvidia-smi --query-gpu=memory.free,memory.total --format=csv,noheader

# COMANDO COMPLETO DE PRODUCCIÓN — con todos los fixes para Jetson:
# - --runtime=nvidia: runtime correcto para Jetson (no --gpus all)
# - LD_LIBRARY_PATH: apunta a librerías tegra reales (no el stub)
# - Montar /tegra y /cuda del host para acceso GPU
# - gpu-memory-utilization 0.70: deja margen (0.85 falla si Ollama tiene modelos)
docker run --rm \
  --runtime=nvidia \
  --network host \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:/usr/local/cuda/lib64 \
  -v /usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra:ro \
  -v /usr/local/cuda:/usr/local/cuda:ro \
  -v ~/models/hf:/models \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  vllm serve /models/gemma-4-E4B-it \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.70 \
    --dtype bfloat16
```

Tiempo de arranque: ~3 minutos (torch.compile + CUDA graph capture)

Cuando veas `Application startup complete` → está listo.

### 17.5 Abrir firewall para vLLM

```bash
sudo ufw allow 8000/tcp comment "vLLM API"
sudo ufw reload
```

### 17.6 Verificar desde el Jetson (otra terminal SSH)

```bash
curl -s http://localhost:8000/health
# Respuesta: (vacío o "OK")

curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/models/gemma-4-E4B-it",
    "messages": [{"role": "user", "content": "¿Qué es el Jetson AGX Orin?"}],
    "max_tokens": 100
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(r['choices'][0]['message']['content'])
print(f'Tokens: {r[\"usage\"][\"completion_tokens\"]}')
"
```

### 17.7 Verificar desde Windows

```powershell
# Test TCP
Test-NetConnection -ComputerName 192.168.1.100 -Port 8000
# TcpTestSucceeded : True

# Chat con vLLM
$body = @{
    model       = "/models/gemma-4-E4B-it"
    messages    = @(@{role="user"; content="Explain edge AI in 3 bullet points."})
    max_tokens  = 200
    temperature = 0.7
} | ConvertTo-Json -Depth 3

$start = Get-Date
$r = Invoke-RestMethod `
    -Uri "http://192.168.1.100:8000/v1/chat/completions" `
    -Method Post -ContentType "application/json" -Body $body
$elapsed = [math]::Round(((Get-Date)-$start).TotalSeconds, 1)

Write-Host $r.choices[0].message.content -ForegroundColor Green
Write-Host "[$($r.usage.completion_tokens) tokens en ${elapsed}s]" -ForegroundColor Cyan
```

### 17.8 Alias permanentes para modo producción/desarrollo

```bash
cat >> ~/.bashrc << 'EOF'

# ─────────────────────────────────────────
#  Modos de operación GPU
# ─────────────────────────────────────────

# Modo vLLM (producción) — libera Ollama y lanza vLLM
alias mode-vllm='
  echo "Liberando GPU de Ollama..."
  for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
    ollama stop $m 2>/dev/null
  done
  sleep 2
  echo "GPU libre:"
  nvidia-smi --query-gpu=memory.free --format=csv,noheader
  echo "Lanzando vLLM..."
  docker run --rm \
    --runtime=nvidia --network host \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:/usr/local/cuda/lib64 \
    -v /usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra:ro \
    -v /usr/local/cuda:/usr/local/cuda:ro \
    -v $HOME/models/hf:/models \
    ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
    vllm serve /models/gemma-4-E4B-it \
      --host 0.0.0.0 --port 8000 \
      --max-model-len 8192 \
      --gpu-memory-utilization 0.70 \
      --dtype bfloat16'

# Modo Ollama (desarrollo) — para Ollama después de parar vLLM
alias mode-ollama='
  docker stop $(docker ps -q --filter ancestor=ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin) 2>/dev/null || true
  echo "vLLM parado. Ollama disponible."
  ollama ps'

# Estado rápido
alias gpu-status='nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader'
alias vllm-health='curl -s http://localhost:8000/health && echo "vLLM OK"'
alias ollama-models='ollama list'
EOF
source ~/.bashrc
```

---

## 18. Fase 16 — Nginx API Gateway

### 18.1 Instalar y configurar Nginx

```bash
sudo apt install nginx -y

sudo tee /etc/nginx/sites-available/llm-api << 'EOF'
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

upstream vllm_backend { server 127.0.0.1:8000; keepalive 32; }
upstream ollama_backend { server 127.0.0.1:11434; keepalive 32; }

server {
    listen 80;
    server_name 192.168.1.100;

    access_log /var/log/nginx/llm-access.log;
    error_log  /var/log/nginx/llm-error.log;
    proxy_read_timeout 300s;
    proxy_connect_timeout 10s;

    location /v1/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://vllm_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
    }

    location /ollama/ {
        proxy_pass http://ollama_backend/;
        proxy_http_version 1.1;
        proxy_buffering off;
    }

    location /health {
        proxy_pass http://vllm_backend/health;
        access_log off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/llm-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl restart nginx
sudo ufw allow 80/tcp comment "Nginx API Gateway"
```

Ahora puedes usar `http://192.168.1.100/v1/...` en lugar de `:8000`.

---

## 19. Fase 17 — Gestión de Servicios

### 19.1 Máximo rendimiento del Jetson

```bash
# Modo máxima potencia
sudo nvpmodel -m 0
sudo jetson_clocks

# Guardar configuración de clocks
sudo jetson_clocks --store /etc/jetson-clocks.conf

# Servicio systemd para max clocks en boot
sudo tee /etc/systemd/system/jetson-max-performance.service << 'EOF'
[Unit]
Description=Jetson AGX Orin Maximum Performance
After=nvpmodel.service multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nvpmodel -m 0
ExecStartPost=/usr/bin/jetson_clocks --restore /etc/jetson-clocks.conf

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jetson-max-performance
sudo systemctl start jetson-max-performance
```

### 19.2 Script de estado del sistema

```bash
cat > ~/scripts/status.sh << 'SCRIPT'
#!/bin/bash
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

clear
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      Jetson AGX Orin — System Status             ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo "  $(date) | $(uptime -p)"
echo "  IP: $(hostname -I | awk '{print $1}')"
echo ""

echo -e "${YELLOW}── GPU ──────────────────────────────────────────────${NC}"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
  --format=csv,noheader,nounits | \
  awk -F', ' '{printf "  Util: %s%% | VRAM: %s/%s MiB | Temp: %s°C\n",$1,$2,$3,$4}'
echo ""

echo -e "${YELLOW}── RAM ──────────────────────────────────────────────${NC}"
free -h | grep Mem | awk '{printf "  Used: %s / %s (Free: %s)\n",$3,$2,$4}'
echo ""

echo -e "${YELLOW}── Services ─────────────────────────────────────────${NC}"
for svc in ssh xrdp ollama docker nginx; do
    status=$(systemctl is-active $svc 2>/dev/null || echo "N/A")
    [ "$status" = "active" ] && \
        echo -e "  ${GREEN}✅ $svc${NC}" || \
        echo -e "  ${RED}❌ $svc: $status${NC}"
done
echo ""

echo -e "${YELLOW}── API Endpoints ────────────────────────────────────${NC}"
for url in "http://localhost:11434/api/tags" "http://localhost:8000/health"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$url" 2>/dev/null)
    [ "$code" = "200" ] && \
        echo -e "  ${GREEN}✅ $url${NC}" || \
        echo -e "  ${RED}❌ $url ($code)${NC}"
done
echo ""

echo -e "${YELLOW}── Ollama Models ────────────────────────────────────${NC}"
ollama list 2>/dev/null | tail -n +2 | awk '{printf "  %s (%s)\n",$1,$4}' || echo "  Ollama not running"
SCRIPT

mkdir -p ~/scripts
chmod +x ~/scripts/status.sh
echo "alias jstatus='~/scripts/status.sh'" >> ~/.bashrc
source ~/.bashrc
```

### 19.3 Reglas de firewall completas

```bash
# Aplicar todas las reglas de una vez
sudo ufw allow 22/tcp    comment "SSH"
sudo ufw allow 3389/tcp  comment "XRDP Remote Desktop"
sudo ufw allow 4000/tcp  comment "NoMachine NX"
sudo ufw allow 11434/tcp comment "Ollama API"
sudo ufw allow 8000/tcp  comment "vLLM API"
sudo ufw allow 8888/tcp  comment "Jupyter Lab"
sudo ufw allow 3000/tcp  comment "Open WebUI"
sudo ufw allow 80/tcp    comment "Nginx Gateway"

sudo ufw enable
sudo ufw status numbered
```

---

## 20. Referencia Rápida

### Puertos y URLs

| Servicio | Puerto | URL desde Windows |
|---------|--------|-------------------|
| SSH | 22 | `ssh jetson` |
| XRDP | 3389 | `mstsc /v:192.168.1.100` |
| NoMachine | 4000 | App NoMachine |
| Ollama API | 11434 | `http://192.168.1.100:11434` |
| Open WebUI | 3000 | `http://192.168.1.100:3000` |
| vLLM API | 8000 | `http://192.168.1.100:8000` |
| Jupyter Lab | 8888 | `http://192.168.1.100:8888` |
| Nginx GW | 80 | `http://192.168.1.100/v1/` |

### Comandos Frecuentes en Jetson

```bash
# Sistema
jstatus             # Dashboard completo del sistema
jtop                # Monitor gráfico interactivo
gpu-status          # Estado GPU rápido
sudo nvpmodel -q    # Ver modo de potencia actual

# Modos GPU
mode-vllm           # Cambiar a modo producción (vLLM)
mode-ollama         # Cambiar a modo desarrollo (Ollama)

# Servicios
sudo systemctl restart ollama
sudo systemctl restart xrdp
sudo /usr/NX/bin/nxserver --restart
docker restart open-webui

# Ollama
ollama list         # Ver modelos
ollama ps           # Ver modelos en GPU
ollama stop <modelo> # Liberar GPU
ollama run <modelo>  # Chat interactivo

# tmux
tmux new -s work    # Nueva sesión
tmux attach -t main # Reconectar
tmux ls             # Listar sesiones
# Ctrl+A d = detach

# LLM venv
source ~/venvs/llm/bin/activate
deactivate
```

### Diagnóstico de Conectividad desde Windows

```powershell
# Verificar puertos
@(22, 3389, 4000, 11434, 8000, 3000, 8888, 80) | ForEach-Object {
    $result = Test-NetConnection -ComputerName 192.168.1.100 -Port $_ -WarningAction SilentlyContinue
    $status = if ($result.TcpTestSucceeded) { "✅" } else { "❌" }
    Write-Host "$status Port $_"
}
```

### Modelos Gemma4 en HuggingFace (nombres correctos)

| Ollama | HuggingFace | Parámetros | VRAM |
|--------|------------|-----------|------|
| `gemma4:latest` | `google/gemma-4-E4B-it` | 4B denso | ~16GB |
| `gemma4:26b` | `google/gemma-4-26B-A4B-it` | MoE 26B/4B activos | ~50GB |
| — | `google/gemma-4-12B-it` | 12B denso | ~24GB |
| — | `google/gemma-4-31B-it` | 31B denso | ~62GB |

---

## 21. Guía de Troubleshooting

### 🔴 SSH: Connection timed out (ping responde)

```bash
# El Jetson está vivo pero SSH no corre o UFW lo bloquea
# Solución 1: Acceder vía NoMachine → abrir terminal → arreglar SSH
sudo systemctl start ssh
sudo ufw allow 22/tcp

# Solución 2: Verificar puerto
sudo ss -tlnp | grep :22
# Si no aparece → SSH no está corriendo
```

### 🔴 SSH: Connection refused (ping no responde)

```bash
# Jetson no tiene red — probablemente NetworkManager no subió sin GDM
# Acceder con monitor+teclado físico → login de consola → arreglar red:
sudo systemctl start NetworkManager
sudo nmcli connection up "Wired connection 1"
hostname -I  # Verificar IP
```

### 🔴 XRDP: Pantalla negra después de login

Aplicar en orden hasta que funcione:

```bash
# Fix 1: Matar sesiones huérfanas (soluciona el 80% de los casos)
ps aux | grep gnome-session | grep -v grep
kill <PIDs de sesiones anteriores>
sudo systemctl restart xrdp
# Reconectar RDP

# Fix 2: Verificar startwm.sh (las 3 exports CRÍTICAS)
grep -E "DESKTOP_SESSION|GNOME_SHELL|XDG_CURRENT" /etc/xrdp/startwm.sh
# Deben estar las tres líneas

# Fix 3: Verificar Wayland deshabilitado
grep WaylandEnable /etc/gdm3/custom.conf
# Debe mostrar: WaylandEnable=false

# Fix 4: Cambiar a XFCE4
sudo apt install xfce4 -y
echo 'exec startxfce4' > ~/.xsession
chmod +x ~/.xsession
sudo systemctl restart xrdp
```

### 🔴 NoMachine: Mouse/teclado no funcionan

```bash
# El problema es que NoMachine está compartiendo el framebuffer de GDM
# sin GPU activa (display virtual no inicializado)

# Fix: Reiniciar GDM y NoMachine
sudo systemctl restart gdm3
sleep 5
sudo /usr/NX/bin/nxserver --restart

# Reconectar desde Windows → seleccionar "Create a new virtual display"
```

### 🔴 Ollama: Rechaza conexión desde Windows

```bash
# Verificar binding
sudo ss -tlnp | grep 11434
# ❌ Mal:  127.0.0.1:11434
# ✅ Bien: *:11434 o 0.0.0.0:11434

# Si es 127.0.0.1, el override no se aplicó
cat /etc/systemd/system/ollama.service.d/override.conf
# Debe mostrar: Environment="OLLAMA_HOST=0.0.0.0"

# Si no existe:
sudo mkdir -p /etc/systemd/system/ollama.service.d/
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 🔴 vLLM: "Free memory less than desired GPU memory utilization"

```bash
# Ollama tiene modelos cargados en la VRAM unificada
ollama ps
# Descargar todos los modelos
ollama stop $(ollama ps | tail -n +2 | awk '{print $1}')
sleep 3

# Relanzar vLLM con utilización reducida
# Cambiar --gpu-memory-utilization 0.85 a 0.70
```

### 🔴 vLLM: "libcuda.so.1: file too short"

```bash
# El container encuentra el stub de libcuda, no la real
# Fix: montar las librerías de tegra y el LD_LIBRARY_PATH correcto
# Usar EXACTAMENTE el comando de la Fase 15.4 (con -v tegra y LD_LIBRARY_PATH)
```

### 🔴 Docker: `--gpus all` falla en Jetson

```bash
# ❌ No funciona en Jetson:
docker run --gpus all ubuntu nvidia-smi

# ✅ Sí funciona:
docker run --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all ubuntu bash

# El Jetson usa GPU integrada (tegra), no PCIe discreta
# nvidia-smi no existe en containers Ubuntu estándar en Jetson
```

### 🔴 PyTorch: "No matching distribution found"

```bash
# El URL del CDN .com no tiene el wheel para v62
# Solución: usar CDN chino (.cn) con v61 y el nombre EXACTO del archivo

pip install --no-cache-dir \
  https://developer.download.nvidia.cn/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl
#                                                       ^^^^                          ^^^^^
#                          Usar: developer.download.nvidia.CN          Usar: nv24.08 (no nv24.09)
```

### 🔴 torchvision: "AVFrame has no member named 'key_frame'"

```bash
# Incompatibilidad con versión de FFmpeg del sistema
# Fix: deshabilitar el decoder de video de FFmpeg en la compilación
FORCE_CUDA=1 TORCHVISION_USE_FFMPEG=0 python setup.py bdist_wheel
```

### 🔴 torchvision: "operator torchvision::nms does not exist"

```bash
# Estás ejecutando Python desde ~/torchvision/
# Python carga el source en lugar del wheel instalado

# Fix: siempre ejecutar desde ~
cd ~
python3 -c "import torchvision; print(torchvision.__version__)"
```

### 🔴 HuggingFace: "huggingface-cli is deprecated"

```bash
# CLI nuevo: "hf" en lugar de "huggingface-cli"
hf auth login           # (no huggingface-cli login)
hf download <repo>      # (no huggingface-cli download)
hf auth whoami          # verificar login
```

### 🔴 UFW BLOCK: PROTO=2 DST=224.0.0.1 en logs

```
[UFW BLOCK] SRC=192.168.1.1 DST=224.0.0.1 PROTO=2
```

**No es un error.** Es tráfico IGMP multicast del router siendo bloqueado correctamente por UFW. Es completamente normal y no afecta ninguna funcionalidad.

### 🔴 PowerShell: "Cannot overwrite variable Host"

```powershell
# $Host es una variable reservada en PowerShell
# ❌ Mal:
param([string]$Host = "192.168.1.100")

# ✅ Bien:
param([string]$OllamaHost = "192.168.1.100")
```

---

## Checklist de Reinstalación

Si reformateas o instalas en nuevo hardware, sigue este orden exacto:

```
□ Fase 1:  apt update && apt upgrade (NO dist-upgrade)
□ Fase 1:  Instalar SSH, herramientas, jtop
□ Fase 2:  IP estática + connection.permissions="" en nmcli
□ Fase 2:  Hostname → jetson-orin
□ Fase 3:  SSH keys desde Windows + SSH config
□ Fase 3:  Deshabilitar PasswordAuthentication después de keys
□ Fase 3:  tmux config
□ Fase 4:  WaylandEnable=false en gdm3/custom.conf
□ Fase 4:  /etc/environment con X11 vars
□ Fase 4:  xserver-xorg-video-dummy + 30-tegra-headless.conf
□ Fase 4:  Desactivar screensaver/power via gsettings
□ Fase 4:  systemctl set-default graphical.target
□ Fase 4:  snap stop snapd-desktop-integration
□ Fase 5:  XRDP + startwm.sh fix + polkit fix
□ Fase 6:  NoMachine 9.7.x DEB desde web9001.nomachine.com
□ Fase 7:  GitHub SSH key + hf.co/settings/keys
□ Fase 8:  JetBrains Gateway Windows + proyecto en ~/projects
□ Fase 9:  VS Code + Remote-SSH extension
□ Fase 10: Ollama + override OLLAMA_HOST=0.0.0.0
□ Fase 10: ollama pull de modelos deseados
□ Fase 11: Docker + nvidia-ctk + default-runtime=nvidia
□ Fase 12: Open WebUI Docker container
□ Fase 13: cuSPARSELt + PyTorch wheel .cn/v61/nv24.08
□ Fase 14: torchvision v0.20.0 con TORCHVISION_USE_FFMPEG=0
□ Fase 15: docker pull ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin
□ Fase 15: hf download google/gemma-4-E4B-it
□ Fase 16: Nginx API gateway
□ Fase 17: jetson-max-performance systemd service
□ Fase 17: UFW rules completas
□ Fase 17: ~/scripts/status.sh + aliases en ~/.bashrc
```

---

*Guía v2.0 — Consolidada con troubleshooting real de implementación completa*  
*Hardware: NVIDIA Jetson AGX Orin Developer Kit 64GB | JetPack 6.2.2 | L4T 36.5.0*  
*CUDA 12.6 | cuDNN 9.3 | TensorRT 10.3 | vLLM 0.19.0 | PyTorch 2.5.0 | Ollama 0.x*
