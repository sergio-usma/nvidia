# 🚀 Jetson AGX Orin — Tutorial JetPack 7.2 | Headless + Agentic AI
## Versión adaptada desde setup JetPack 6.2.2 → 7.2 | Windows 11 Host

---

> **Hardware:** NVIDIA Jetson AGX Orin Developer Kit 64GB  
> **Target OS:** Ubuntu 24.04 LTS aarch64 | L4T r39.2 | JetPack 7.2  
> **CUDA:** 13.2.1 | TensorRT 10.16.2 | Python 3.12  
> **Host:** Windows 11 (WiFi) → Jetson (Ethernet, misma red)  
> **Nuevo en JP 7.2:** NemoClaw, OpenClaw, Jetson Agent Skills, CUDA 13

---

## ⚡ Lo Que Cambió en JetPack 7.2 vs 6.2

Esta tabla es la referencia más importante del documento:

| Componente | JetPack 6.2.2 | JetPack 7.2 | Impacto en Tutorial |
|------------|--------------|-------------|---------------------|
| **Ubuntu** | 22.04 LTS | **24.04 LTS** | Alto — paquetes distintos |
| **Kernel Linux** | 5.15.185-tegra | **6.8.x-tegra** | Medio |
| **L4T** | r36.5 | **r39.2** | Alto — BSP nuevo |
| **CUDA** | 12.6 | **13.2.1** | Alto — wheels PyTorch cambian |
| **cuDNN** | 9.3 | **TBD (9.x+)** | Medio |
| **TensorRT** | 10.3 | **10.16.2** | Bajo |
| **Python default** | 3.10 | **3.12** | Alto — venv paths cambian |
| **Display server** | X11 (forzado) | **Wayland default** | Alto — mismo fix requerido |
| **Instalación** | SDK Manager / flash | **ISO unificado** | Alto — proceso nuevo |
| **NemoClaw** | No disponible | **1 comando** | ¡NUEVO! |
| **OpenClaw** | No disponible | **Via NemoClaw** | ¡NUEVO! |
| **Agent Skills** | No disponible | **Integrado** | ¡NUEVO! |
| **vLLM container** | gemma4-jetson-orin | **Nueva tag JP7** | Verificar al instalar |
| **Ollama** | Funciona (arm64) | **Funciona (arm64)** | Sin cambios |
| **Docker** | Mismo proceso | **Mismo proceso** | Sin cambios |
| **SSH/XRDP/NoMachine** | Configurado | **Mismo proceso** | Sin cambios |

### Lo que NO cambia

- Hardware: mismo GPU Ampere **sm_87** → `TORCH_CUDA_ARCH_LIST="8.7"` igual
- NetworkManager para red estática → mismo proceso
- SSH keys y configuración → mismos archivos
- NoMachine DEB ARM64 → mismo proceso de instalación
- Ollama → mismo proceso, mismos modelos
- Docker + nvidia-ctk → mismo proceso
- GitHub SSH → mismo proceso
- JetBrains Gateway / VS Code → mismos
- Aliases en ~/.bashrc → mismos

---

## 📋 Tabla de Contenidos

1. [Pre-Flash: Guardar lo que puedes antes de formatear](#1-pre-flash-guardar-lo-que-puedes)
2. [Flashear JetPack 7.2 con ISO](#2-flashear-jetpack-72-con-iso)
3. [Post-Flash: Configuración base Ubuntu 24.04](#3-post-flash-configuración-base-ubuntu-2404)
4. [Red y IP Estática](#4-red-y-ip-estática)
5. [SSH desde Windows](#5-ssh-desde-windows)
6. [Headless Mode en Ubuntu 24.04](#6-headless-mode-en-ubuntu-2404)
7. [XRDP en Ubuntu 24.04](#7-xrdp-en-ubuntu-2404)
8. [NoMachine](#8-nomachine)
9. [Docker + NVIDIA Container Toolkit](#9-docker--nvidia-container-toolkit)
10. [Ollama con GPU](#10-ollama-con-gpu)
11. [Open WebUI](#11-open-webui)
12. [PyTorch para JetPack 7.2 (CUDA 13 / Python 3.12)](#12-pytorch-para-jetpack-72)
13. [vLLM para JetPack 7.2](#13-vllm-para-jetpack-72)
14. [NemoClaw — Instalación con 1 Comando](#14-nemoclaw--instalación-con-1-comando)
15. [Jetson Agent Skills](#15-jetson-agent-skills)
16. [Agentic AI con OpenClaw + NemoClaw](#16-agentic-ai-con-openclaw--nemoclaw)
17. [Gestión de Servicios](#17-gestión-de-servicios)
18. [Referencia Rápida JP 7.2](#18-referencia-rápida-jp-72)
19. [Troubleshooting Específico JP 7.2](#19-troubleshooting-específico-jp-72)

---

## 1. Pre-Flash: Guardar lo que puedes

Antes de flashear, guarda en Windows o en una USB:

```bash
# En el Jetson (antes de flashear)

# 1. Exportar configuración SSH
cp -r ~/.ssh ~/ssh_backup/
cat ~/.ssh/authorized_keys           # Copia esto a Windows

# 2. Guardar configuración tmux
cp ~/.tmux.conf ~/tmux_conf_backup.txt

# 3. Exportar aliases y funciones de ~/.bashrc
grep -A 100 "# ─────" ~/.bashrc > ~/bashrc_aliases_backup.txt

# 4. Guardar lista de modelos Ollama descargados
ollama list > ~/ollama_models_list.txt

# 5. Guardar el directorio de modelos HuggingFace en disco externo (si tienes)
# Los modelos HF no se pueden mover fácilmente — los tendrás que re-descargar
# A menos que tengas un SSD externo

# 6. Ver qué modelos de Ollama tienes (para recordar re-descargar)
cat ~/ollama_models_list.txt

# 7. Exportar tu clave SSH pública de GitHub
cat ~/.ssh/github_ed25519.pub > ~/github_key_public_backup.txt
# OJO: La clave privada (~/.ssh/github_ed25519) también guárdala
cp ~/.ssh/github_ed25519 ~/github_private_key_backup

# Copiar todo a Windows con SCP desde PowerShell
# scp -r jetson:~/ssh_backup/ C:\Users\TuUsuario\jetson_backup\
```

> 💡 Los modelos de HuggingFace (~/models/hf/) son ~15GB. Si tienes espacio en un disco externo, cópialos ahí para no re-descargarlos.

---

## 2. Flashear JetPack 7.2 con ISO

### 2.1 Diferencia clave: JetPack 7.2 usa ISO, no SDK Manager (para AGX Orin)

JetPack 7.2 introduce un método de instalación unificado basado en ISO para Jetson Orin y Jetson Thor developer kits.

### 2.2 Proceso de flash con ISO

1. **Descargar la imagen ISO de JetPack 7.2** desde:
   https://developer.nvidia.com/embedded/jetpack/downloads

2. **Crear USB booteable** desde Windows:
   - Descargar **Rufus** (https://rufus.ie)
   - USB de mínimo 16GB
   - Scheme: GPT | Target system: UEFI
   - File system: FAT32
   - Seleccionar la ISO de JetPack 7.2
   - Click START

3. **Poner el Jetson en Recovery Mode**:
   - Apagar el Jetson
   - Mantener presionado el botón **FORCE RECOVERY** (el del medio)
   - Conectar USB-C de la Jetson a tu PC Windows
   - Encender el Jetson
   - Mantener FORCE RECOVERY por 2 segundos más
   - Soltar

4. **Verificar modo recovery desde Windows** (Device Manager):
   - Debe aparecer "NVIDIA APX" o "NVIDIA USB Recovery Mode"

5. **Seguir el proceso del Quick Start Guide**:
   https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/quick_start.html

### 2.3 Alternativa: Usar SDK Manager desde Linux

Si tienes un PC con Ubuntu 20.04 o 22.04:

```bash
# Instalar SDK Manager
# Descargar .deb desde: https://developer.nvidia.com/sdk-manager
sudo dpkg -i sdkmanager_*.deb

# Lanzar
sdkmanager
# Seleccionar: JetPack 7.2 → Jetson AGX Orin → Flash
```

### 2.4 Post-flash: Primer boot

Conecta monitor + teclado + mouse al Jetson (última vez necesaria).  
Completa el asistente OEM:
- Usuario: `jetson` (o el que prefieras)
- Contraseña: fuerte y memorable
- Zona horaria, idioma, teclado

---

## 3. Post-Flash: Configuración Base Ubuntu 24.04

### 3.1 Diferencias Ubuntu 24.04 vs 22.04 en el proceso

```bash
# Ubuntu 24.04 usa Python 3.12 por defecto (no 3.10)
python3 --version
# Python 3.12.x

# pip ya viene instalado diferente en 24.04
# Usar pipx o venv en lugar de pip directo al sistema
sudo apt install python3-pip python3-venv pipx -y

# El sistema usa systemd-networkd también disponible (además de NetworkManager)
# Nos quedamos con NetworkManager como antes
```

### 3.2 Actualizar sistema (misma regla que JP 6.2)

```bash
# ❌ NUNCA en Jetson:
# sudo apt dist-upgrade

# ✅ Correcto:
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
```

### 3.3 Instalar herramientas esenciales para Ubuntu 24.04

```bash
sudo apt install -y \
  net-tools curl wget htop tmux tree \
  git nano vim unzip zip \
  build-essential python3-pip python3-venv python3-dev \
  software-properties-common \
  apt-transport-https ca-certificates gnupg lsb-release \
  libopenblas-dev libjpeg-dev libpng-dev cmake ninja-build

# jtop para Ubuntu 24.04 — mismo proceso
sudo pip3 install -U jetson-stats --break-system-packages
# En Ubuntu 24.04, pip3 al sistema requiere --break-system-packages
# O mejor: usar pipx
pipx install jetson-stats

sudo systemctl restart jtop
jtop  # Test
```

### 3.4 SSH — mismo proceso que JP 6.2

```bash
sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl status ssh

# Configurar sshd_config — exactamente igual que en JP 6.2
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.original
sudo nano /etc/ssh/sshd_config
```

```ini
Port 22
PubkeyAuthentication yes
PasswordAuthentication yes
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

### 3.5 Hostname

```bash
sudo hostnamectl set-hostname jetson-orin
sudo nano /etc/hosts
# 127.0.1.1  jetson-orin
```

---

## 4. Red y IP Estática

### Sin cambios respecto a JP 6.2

El proceso con `nmcli` es idéntico. La clave crítica es `connection.permissions ""`.

```bash
# Identificar conexión Ethernet
nmcli connection show
nmcli device status

CONN="Wired connection 1"  # ← ajustar al nombre real

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
hostname -I

# Deshabilitar wait-online para boot más rápido
sudo systemctl disable NetworkManager-wait-online.service
sudo systemctl mask NetworkManager-wait-online.service
```

---

## 5. SSH desde Windows

### Sin cambios respecto a JP 6.2

Si guardaste tus claves SSH antes del flash, puedes reutilizarlas directamente:

```powershell
# En Windows — la clave ya existe de JP 6.2, solo copiarla de nuevo
type "$env:USERPROFILE\.ssh\jetson_orin.pub" | `
  ssh jetson@192.168.1.100 `
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# El ~/.ssh/config de Windows no cambia
# ssh jetson  → conecta igual que antes
```

### Restaurar tmux config

```bash
# En el Jetson (via SSH)
sudo apt install tmux -y

# Pegar el contenido de tu backup ~/.tmux.conf
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
```

---

## 6. Headless Mode en Ubuntu 24.04

### 6.1 Ubuntu 24.04 y Wayland — mismo problema, mismo fix

En JetPack 7 / Ubuntu 24.04, el display server por defecto cambió de Xorg a Wayland, lo que afecta al escritorio remoto y a cualquier aplicación que use la variable DISPLAY.

El fix es **exactamente el mismo** que en JP 6.2:

```bash
# Deshabilitar Wayland en GDM
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
# Variables de entorno globales
sudo nano /etc/environment
```

Agregar:
```bash
QT_QPA_PLATFORM=xcb
GDK_BACKEND=x11
XDG_SESSION_TYPE=x11
```

### 6.2 Xorg Dummy driver

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

### 6.3 Desactivar screensaver (Ubuntu 24.04 — mismo proceso, nueva ubicación gsettings)

```bash
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0
gsettings set org.gnome.settings-daemon.plugins.power idle-dim false
gsettings set org.gnome.settings-daemon.plugins.power power-button-action 'nothing'
```

```bash
sudo systemctl set-default graphical.target
sudo systemctl restart gdm3
```

---

## 7. XRDP en Ubuntu 24.04

### 7.1 Instalar XRDP

```bash
sudo apt install xrdp -y
sudo adduser xrdp ssl-cert
```

### 7.2 Fix startwm.sh — igual que JP 6.2 pero con ajuste para GNOME 46

Ubuntu 24.04 usa GNOME 46. El fix del startwm.sh sigue siendo el mismo:

```bash
sudo nano /etc/xrdp/startwm.sh
```

```bash
#!/bin/sh
# xrdp session startup — Ubuntu 24.04 / GNOME 46 / Jetson AGX Orin

if test -r /etc/profile; then
    . /etc/profile
fi

# Estas tres líneas resuelven el black screen en Ubuntu 24.04 también
export DESKTOP_SESSION=ubuntu
export GNOME_SHELL_SESSION_MODE=ubuntu
export XDG_CURRENT_DESKTOP=ubuntu:GNOME

# Limpiar variables conflictivas
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR

test -x /etc/X11/Xsession && exec /etc/X11/Xsession
exec /bin/sh /etc/X11/Xsession
```

### 7.3 Archivos de sesión de usuario

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
export DESKTOP_SESSION=ubuntu
export XDG_SESSION_TYPE=x11
exec /usr/bin/gnome-session --session=ubuntu
EOF
chmod +x ~/.xsession
```

### 7.4 Fix PolicyKit

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

> 💡 **Nota Ubuntu 24.04:** Si PolicyKit da errores con el formato `.pkla`, prueba el formato nuevo `.rules`:

```bash
sudo nano /etc/polkit-1/rules.d/45-allow-colord.rules
```

```javascript
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.color-manager.") === 0) {
        return polkit.Result.YES;
    }
});
```

### 7.5 Habilitar y arrancar XRDP

```bash
sudo systemctl enable xrdp
sudo systemctl restart xrdp
sudo systemctl status xrdp
sudo ss -tlnp | grep 3389

sudo ufw allow 3389/tcp comment "XRDP Remote Desktop"
sudo ufw reload
```

### 7.6 Alternativa: XFCE4 (más estable con XRDP en Ubuntu 24.04)

```bash
sudo apt install xfce4 xfce4-goodies -y
echo 'exec startxfce4' > ~/.xsession
chmod +x ~/.xsession
sudo systemctl restart xrdp
```

---

## 8. NoMachine

### Sin cambios respecto a JP 6.2

El DEB ARM64 para Ubuntu/Debian sigue siendo el mismo:

```bash
cd ~/Downloads

# Verificar versión actual en: https://downloads.nomachine.com/download/?id=30&platform=linux&distro=arm
# Al momento de escribir esto: 9.7.3
wget "https://web9001.nomachine.com/download/9.7/Arm/nomachine_9.7.3_1_arm64.deb"

sudo dpkg -i nomachine_9.7.3_1_arm64.deb
sudo apt --fix-broken install -y

sudo /usr/NX/bin/nxserver --start
sudo /usr/NX/bin/nxserver --status

sudo ufw allow 4000/tcp comment "NoMachine NX"

# Autostart
sudo systemctl enable nxserver 2>/dev/null || \
  sudo /usr/NX/bin/nxserver --startup
```

---

## 9. Docker + NVIDIA Container Toolkit

### Sin cambios respecto a JP 6.2

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker

# Verificar
docker info | grep "Default Runtime"
# Default Runtime: nvidia
```

### Test GPU en Docker (Jetson — igual que JP 6.2)

```bash
# ❌ NO usar --gpus all en Jetson
# ✅ Usar --runtime=nvidia
docker run --rm --runtime=nvidia ubuntu:24.04 \
  bash -c "ls /dev/ | grep -E 'nvhost|nvmap|tegra' | head -5"
```

---

## 10. Ollama con GPU

### Sin cambios — mismo proceso que JP 6.2

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Override para red — CRÍTICO como siempre
sudo mkdir -p /etc/systemd/system/ollama.service.d/

sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama

# Verificar binding
sudo ss -tlnp | grep 11434
# Debe mostrar: *:11434

sudo ufw allow 11434/tcp comment "Ollama API"

# Re-descargar los modelos que tenías en JP 6.2
ollama pull gemma4:latest
ollama pull gemma4:26b
ollama pull ministral-3:latest
# ... etc según tu lista guardada

# Verificar desde Windows (mismo PowerShell que antes)
# Invoke-RestMethod -Uri "http://192.168.1.100:11434/api/tags"
```

---

## 11. Open WebUI

### Sin cambios — mismo Docker run

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

# Esperar ~90 segundos
docker logs open-webui --follow
# Esperar: "Application startup complete."
```

---

## 12. PyTorch para JetPack 7.2

### ⚠️ CAMBIOS IMPORTANTES vs JP 6.2

- Python: **3.12** (no 3.10) → `cp312` en los wheel filenames
- CUDA: **13.2.1** (no 12.6) → diferente URL de NVIDIA CDN
- URL JetPack index: **v72** (no v61)
- cuSPARSELt: versión más nueva requerida

### 12.1 Crear entorno virtual con Python 3.12

```bash
python3 --version
# Python 3.12.x

python3 -m venv ~/venvs/llm
source ~/venvs/llm/bin/activate
pip install --upgrade pip
```

### 12.2 Instalar cuSPARSELt para CUDA 13

```bash
# Verificar si ya está (JetPack 7.2 puede incluirlo)
ls /usr/local/cuda/lib64/libcusparseLt.so 2>/dev/null && echo "OK" || echo "Instalar"

# Si no está, instalar versión compatible con CUDA 13
cd ~/Downloads

# Buscar la versión más reciente en:
# https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-sbsa/
wget https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-sbsa/libcusparse_lt-linux-sbsa-0.7.1.0-archive.tar.xz

tar xf libcusparse_lt-linux-sbsa-0.7.1.0-archive.tar.xz

sudo cp -a libcusparse_lt-linux-sbsa-0.7.1.0-archive/include/* /usr/local/cuda/include/
sudo cp -a libcusparse_lt-linux-sbsa-0.7.1.0-archive/lib/* /usr/local/cuda/lib64/

ls /usr/local/cuda/lib64/libcusparseLt.so
```

### 12.3 Instalar PyTorch para JP 7.2

El wheel correcto para JP 7.2 sigue el patrón:
```
https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/torch-X.X.X...-cp312-cp312-linux_aarch64.whl
```

```bash
source ~/venvs/llm/bin/activate

# Primero, ver qué wheels hay disponibles para JP 7.2
curl -s https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/ \
  | grep -o 'torch-[^"]*aarch64\.whl' | sort
```

Si el índice v72 está disponible, instalar el wheel encontrado:

```bash
# Patrón esperado (ajustar al nombre real que aparezca):
pip install --no-cache-dir numpy==2.0.0    # Ubuntu 24.04 usa numpy 2.x

pip install --no-cache-dir \
  "https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/torch-X.X.X-cp312-cp312-linux_aarch64.whl"
```

Si el CDN NVIDIA no tiene wheels todavía, usar el Jetson AI Lab:

```bash
# Buscar en el índice JP7 de Jetson AI Lab
pip install --no-cache-dir \
  --index-url https://pypi.jetson-ai-lab.io/jp7/cu130/ \
  torch

# O buscar wheel directo
curl -s "https://pypi.jetson-ai-lab.io/jp7/cu130/" 2>/dev/null | \
  grep -o 'torch-[^"]*cp312[^"]*aarch64[^"]*\.whl' | head -5
```

### 12.4 Verificar PyTorch + CUDA 13

```bash
cd ~    # ← IMPORTANTE: siempre desde ~
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
    print('CUDA 13 OK')
"
# Esperado: CUDA ver: 13.x, GPU: Orin, 61 GB
```

### 12.5 torchvision para JP 7.2

```bash
source ~/venvs/llm/bin/activate

# Buscar versión compatible con tu versión de PyTorch
# PyTorch 2.x → TorchVision 0.2x

# Intentar desde Jetson AI Lab primero
pip install --no-cache-dir \
  --index-url https://pypi.jetson-ai-lab.io/jp7/cu130/ \
  torchvision

# Si no está disponible, compilar desde source (mismo proceso que JP 6.2
# pero con version apropiada y TORCH_CUDA_ARCH_LIST="8.7" igual)
cd ~
git clone --branch v0.21.0 --depth 1 https://github.com/pytorch/vision torchvision
cd torchvision

export BUILD_VERSION=0.21.0
export TORCH_CUDA_ARCH_LIST="8.7"    # ← Orin sigue siendo sm_87
export MAX_JOBS=4
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH

FORCE_CUDA=1 TORCHVISION_USE_FFMPEG=0 python setup.py bdist_wheel
pip install dist/torchvision-0.21.0*.whl

cd ~    # ← salir antes de verificar
python3 -c "import torchvision; print('torchvision:', torchvision.__version__)"
```

---

## 13. vLLM para JetPack 7.2

### 13.1 Verificar disponibilidad de nuevo container

NVIDIA actualiza los containers de vLLM con cada JetPack. Verificar qué tags están disponibles:

```bash
# Ver los tags disponibles para JP 7.2
# Página oficial: https://github.com/orgs/NVIDIA-AI-IOT/packages/container/package/vllm

# Posibles tags para JP 7.2 (verificar en la página):
docker pull ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin  # puede apuntar a JP7
docker pull ghcr.io/nvidia-ai-iot/vllm:r39.2.tegra-aarch64-cu130-24.04  # patrón esperado
```

### 13.2 Descargar modelo (si no lo guardaste)

```bash
source ~/venvs/llm/bin/activate

# Instalar hf CLI
pip install huggingface-hub
hf auth login

mkdir -p ~/models/hf

hf download google/gemma-4-E4B-it \
  --local-dir ~/models/hf/gemma-4-E4B-it
```

### 13.3 Lanzar vLLM con JP 7.2

El comando base es el mismo. Solo cambia el tag del container:

```bash
# Liberar GPU de Ollama primero
ollama stop $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}') 2>/dev/null
sleep 2

# Con nuevo tag JP 7.2 (ajustar según lo que encuentres)
docker run --rm \
  --runtime=nvidia \
  --network host \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:/usr/local/cuda/lib64 \
  -v /usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra:ro \
  -v /usr/local/cuda:/usr/local/cuda:ro \
  -v ~/models/hf:/models \
  ghcr.io/nvidia-ai-iot/vllm:<TAG-JP7-AQUI> \
  vllm serve /models/gemma-4-E4B-it \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.70 \
    --dtype bfloat16

sudo ufw allow 8000/tcp comment "vLLM API"
```

> 📌 Verificar el tag correcto en: https://github.com/orgs/NVIDIA-AI-IOT/packages/container/package/vllm

---

## 14. NemoClaw — Instalación con 1 Comando

### ¡Esta es la gran novedad de JetPack 7.2!

Con JetPack 7.2, el Jetson está listo para NemoClaw desde el primer momento. JetPack 7.2 viene preconfigurado con las dependencias y el software stack requeridos para desplegar y ejecutar workflows basados en NemoClaw sin configuración manual del entorno.

```bash
# En el Jetson — comando único para instalar NemoClaw
curl -fsSL nvidia.com/nemoclaw.sh | bash
```

### 14.1 ¿Qué es NemoClaw?

```
OpenClaw (open source)
    └── Base framework para AI agents
    └── Orquestación de modelos locales + cloud
    └── Tool calling, memoria, planning

NemoClaw (NVIDIA, sobre OpenClaw)
    └── Adds: Privacy controls
    └── Adds: Security layers
    └── Adds: Governance
    └── Adds: Optimizado para Jetson hardware
```

NemoClaw es un stack open source que añade controles de privacidad y seguridad a OpenClaw, habilitando la construcción de aplicaciones de IA agéntica en robótica, automatización industrial, agentes de visión y sistemas de edge AI.

### 14.2 Verificar instalación de NemoClaw

```bash
# Verificar que NemoClaw está instalado
nemoclaw --version 2>/dev/null || \
  python3 -c "import nemoclaw; print('NemoClaw OK')" 2>/dev/null || \
  echo "Verificar log de instalación"

# Ver directorio de instalación
ls ~/nemoclaw/ 2>/dev/null || ls /opt/nemoclaw/ 2>/dev/null
```

### 14.3 Primer test de NemoClaw

```bash
# Test básico con un LLM local (Ollama debe estar corriendo)
python3 << 'EOF'
# Ejemplo básico de NemoClaw con modelo local
# (Ajustar imports según la documentación actual de NemoClaw)
from nemoclaw import Agent, LocalLLM

# Conectar al LLM local via Ollama
llm = LocalLLM(
    base_url="http://localhost:11434",
    model="gemma4:latest"
)

agent = Agent(
    name="JetsonAgent",
    llm=llm,
    system_prompt="You are a helpful assistant running on NVIDIA Jetson AGX Orin."
)

response = agent.run("What is your hardware platform?")
print(response)
EOF
```

> 📚 Documentación oficial NemoClaw: https://www.nvidia.com/en-us/ai/nemoclaw/

---

## 15. Jetson Agent Skills

JetPack 7.2 introduce tres categorías de skills para Jetson: Linux Customization Skills (automatizan configuración BSP), Memory Optimization Skills (optimizan uso de memoria en todo el stack), y Model Benchmarking Skills (identifican la mejor configuración de modelo para cada caso de uso).

### 15.1 Instalar Jetson Device Skills

```bash
# Clonar el repositorio oficial de Jetson Device Skills
git clone https://github.com/NVIDIA-AI-IOT/jetson-device-skills.git
cd jetson-device-skills

# Instalar dependencias
pip install -r requirements.txt

# Ver skills disponibles
ls skills/
```

### 15.2 Instalar Jetson BSP Skills

```bash
git clone https://github.com/NVIDIA-AI-IOT/jetson-bsp-skills.git
cd jetson-bsp-skills

pip install -r requirements.txt
```

### 15.3 Usar Memory Optimization Skill

Las Memory Optimization Skills pueden optimizar el uso de memoria en todo el stack, desde los carveouts del bootloader, hasta la reserva de memoria del kernel, procesos redundantes en espacio de usuario, y ayudar a construir la configuración de software más eficiente en memoria para una carga de trabajo dada.

```bash
cd jetson-device-skills

# Ejecutar skill de optimización de memoria
python3 run_skill.py --skill memory_optimization \
  --agent-backend ollama \
  --model gemma4:latest

# Ver métricas antes/después
free -h
sudo tegrastats --interval 1000
```

### 15.4 Usar Model Benchmarking Skill

```bash
# Benchmarking de modelos con el skill oficial
python3 run_skill.py --skill model_benchmarking \
  --model gemma4:latest \
  --backend ollama \
  --output benchmarks.json

cat benchmarks.json | python3 -m json.tool
```

---

## 16. Agentic AI con OpenClaw + NemoClaw

### 16.1 Arquitectura de sistema agéntico en Jetson

```
Windows 11 (192.168.1.33)
    │
    │  SSH / API calls
    ▼
Jetson AGX Orin (192.168.1.100)
    │
    ├── NemoClaw Agent Runtime
    │   ├── Local LLM (Ollama / vLLM)
    │   │   ├── gemma4:latest → razonamiento
    │   │   └── nomic-embed-text → embeddings / RAG
    │   │
    │   ├── Memory Layer
    │   │   ├── Short-term: context window
    │   │   └── Long-term: vector DB (local)
    │   │
    │   ├── Tool Layer
    │   │   ├── Vision tools (cámara, RTSP)
    │   │   ├── System tools (bash, filesystem)
    │   │   └── API tools (HTTP, REST)
    │   │
    │   └── Privacy/Security Layer (NemoClaw)
    │       ├── Data stays on device
    │       └── No cloud calls unless configured
    │
    └── Jetson Agent Skills
        ├── Memory Optimization
        ├── Model Benchmarking
        └── Linux Customization
```

### 16.2 Setup básico de agente con NemoClaw + Ollama

```python
# ~/projects/agentic/jetson_agent.py

"""
Agente básico con NemoClaw en Jetson AGX Orin
Usa Ollama como backend local (sin cloud)
"""

import os

# Configuración para modo 100% offline
os.environ["NEMOCLAW_OFFLINE"] = "true"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

# Adaptar imports a la API real de NemoClaw post-instalación
# Referencia: https://github.com/nvidia/nemoclaw

def create_local_agent():
    """Crea un agente que corre completamente en el Jetson."""
    try:
        from nemoclaw import Agent, OllamaLLM, MemoryStore
        
        # LLM local
        llm = OllamaLLM(
            model="gemma4:latest",
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # Memoria persistente local
        memory = MemoryStore(
            path="~/.jetson_agent_memory",
            embedding_model="nomic-embed-text"
        )
        
        # Agente completo
        agent = Agent(
            name="JetsonEdgeAgent",
            llm=llm,
            memory=memory,
            system_prompt="""
            You are an intelligent agent running on NVIDIA Jetson AGX Orin 64GB.
            You operate completely offline for privacy.
            You have access to the local system and can perform edge AI tasks.
            """,
            privacy_mode=True    # NemoClaw privacy layer
        )
        
        return agent
        
    except ImportError:
        print("NemoClaw not installed. Run: curl -fsSL nvidia.com/nemoclaw.sh | bash")
        return None


def simple_pipeline():
    """Pipeline agéntico simple sin dependencias."""
    import requests
    
    OLLAMA_URL = "http://localhost:11434"
    
    def call_llm(prompt, model="gemma4:latest", system=""):
        response = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False
        })
        return response.json()["response"]
    
    # Pipeline multi-step
    print("=== Jetson AGX Orin Agentic Pipeline ===\n")
    
    # Step 1: Analizar
    context = "System: Jetson AGX Orin 64GB, CUDA 13, JetPack 7.2"
    analysis = call_llm(
        f"Given this context: {context}\nWhat are the top 3 AI tasks this hardware is ideal for?",
        system="You are an edge AI expert. Be concise."
    )
    print(f"Analysis:\n{analysis}\n")
    
    # Step 2: Planear
    plan = call_llm(
        f"Based on: {analysis}\nCreate a concrete implementation plan with 3 steps.",
        system="You are a project planner. Output numbered steps."
    )
    print(f"Plan:\n{plan}\n")
    
    # Step 3: Código
    code = call_llm(
        f"For step 1 of: {plan}\nWrite a Python code snippet.",
        system="You are a Python expert. Output only code."
    )
    print(f"Code:\n{code}\n")
    
    return {"analysis": analysis, "plan": plan, "code": code}


if __name__ == "__main__":
    # Intentar con NemoClaw
    agent = create_local_agent()
    
    if agent:
        # Modo NemoClaw completo
        response = agent.run(
            "Analyze the current system memory usage and suggest optimizations for running LLMs"
        )
        print(response)
    else:
        # Fallback a pipeline manual
        simple_pipeline()
```

### 16.3 Exponer el agente como API

```python
# ~/projects/agentic/agent_api.py

from fastapi import FastAPI
from pydantic import BaseModel
import requests
import uvicorn

app = FastAPI(title="Jetson AGX Orin Edge Agent API")

OLLAMA_URL = "http://localhost:11434"

class AgentRequest(BaseModel):
    prompt: str
    model: str = "gemma4:latest"
    system: str = "You are a helpful edge AI assistant on NVIDIA Jetson."
    max_tokens: int = 500

class AgentResponse(BaseModel):
    response: str
    model: str
    tokens: int

@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    r = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": request.model,
        "prompt": request.prompt,
        "system": request.system,
        "stream": False,
        "options": {"num_predict": request.max_tokens}
    })
    data = r.json()
    return AgentResponse(
        response=data["response"],
        model=request.model,
        tokens=data.get("eval_count", 0)
    )

@app.get("/agent/models")
async def list_models():
    r = requests.get(f"{OLLAMA_URL}/api/tags")
    return r.json()

@app.get("/health")
async def health():
    return {"status": "ok", "platform": "Jetson AGX Orin", "jetpack": "7.2"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
```

```bash
# Instalar dependencias e iniciar
pip install fastapi uvicorn
sudo ufw allow 9000/tcp comment "Edge Agent API"
python3 ~/projects/agentic/agent_api.py
```

Desde Windows:
```powershell
# Test del agente
$body = @{prompt="What is running on this edge device?"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://192.168.1.100:9000/agent/run" `
  -Method Post -ContentType "application/json" -Body $body
```

### 16.4 Instalar DeepStream para Vision Agents (opcional)

JetPack 7.2 también introduce skills que ayudan a los agentes a construir pipelines de visión usando NVIDIA DeepStream y NVIDIA Metropolis Blueprint para Video Search and Summarization.

```bash
# DeepStream para pipelines de video/visión en el agente
sudo apt install deepstream-7.0 -y 2>/dev/null || \
  echo "Instalar vía SDK Manager o repositorio NVIDIA"

# O via Docker (más limpio)
docker pull nvcr.io/nvidia/deepstream:7.0-gc-triton-devel
```

---

## 17. Gestión de Servicios

### 17.1 Máximo rendimiento — mismo proceso que JP 6.2

```bash
# Verificar modo actual
sudo nvpmodel -q

# Modo MAXN
sudo nvpmodel -m 0
sudo jetson_clocks

# Guardar configuración
sudo jetson_clocks --store /etc/jetson-clocks.conf
```

### 17.2 GitHub SSH — restaurar desde backup

```bash
# Si guardaste las claves antes del flash:
# Copiar desde Windows:
# scp C:\Users\TuUsuario\jetson_backup\github_ed25519 jetson:~/.ssh/

# Si no las guardaste, generar nuevas:
ssh-keygen -t ed25519 \
  -C "jetson-orin-jp72-$(date +%Y%m%d)" \
  -f ~/.ssh/github_ed25519

cat ~/.ssh/github_ed25519.pub
# Agregar en: https://github.com/settings/keys

# Test
ssh -T git@github.com
```

### 17.3 Reglas UFW completas para JP 7.2

```bash
sudo ufw allow 22/tcp    comment "SSH"
sudo ufw allow 3389/tcp  comment "XRDP Remote Desktop"
sudo ufw allow 4000/tcp  comment "NoMachine NX"
sudo ufw allow 11434/tcp comment "Ollama API"
sudo ufw allow 8000/tcp  comment "vLLM API"
sudo ufw allow 8888/tcp  comment "Jupyter Lab"
sudo ufw allow 3000/tcp  comment "Open WebUI"
sudo ufw allow 80/tcp    comment "Nginx Gateway"
sudo ufw allow 9000/tcp  comment "Edge Agent API"

sudo ufw enable
sudo ufw status numbered
```

### 17.4 Script de status actualizado para JP 7.2

```bash
mkdir -p ~/scripts

cat > ~/scripts/status.sh << 'SCRIPT'
#!/bin/bash
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

clear
echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Jetson AGX Orin 64GB — JetPack 7.2 Status         ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo "  $(date) | $(uptime -p)"
echo "  IP: $(hostname -I | awk '{print $1}')"
echo ""

echo -e "${YELLOW}── GPU / CUDA 13 ──────────────────────────────────────${NC}"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
  --format=csv,noheader,nounits | \
  awk -F', ' '{printf "  Util: %s%% | VRAM: %s/%s MiB | Temp: %s°C\n",$1,$2,$3,$4}'
echo "  CUDA: $(nvcc --version 2>/dev/null | grep release | awk '{print $5}' | tr -d ',')"
echo ""

echo -e "${YELLOW}── Sistema ──────────────────────────────────────────────${NC}"
free -h | grep Mem | awk '{printf "  RAM: %s / %s\n",$3,$2}'
sudo nvpmodel -q 2>/dev/null | grep "NV Power Mode" | head -1 | sed 's/^/  /'
echo ""

echo -e "${YELLOW}── Servicios ────────────────────────────────────────────${NC}"
for svc in ssh xrdp ollama docker nginx; do
    status=$(systemctl is-active $svc 2>/dev/null || echo "N/A")
    [ "$status" = "active" ] && \
        echo -e "  ${GREEN}✅ $svc${NC}" || \
        echo -e "  ${RED}❌ $svc: $status${NC}"
done
echo ""

echo -e "${YELLOW}── APIs ──────────────────────────────────────────────────${NC}"
for url in \
    "http://localhost:11434/api/tags:Ollama" \
    "http://localhost:8000/health:vLLM" \
    "http://localhost:3000:OpenWebUI" \
    "http://localhost:9000/health:EdgeAgent"; do
    url_only=$(echo $url | cut -d: -f1-2)
    label=$(echo $url | cut -d: -f3)
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$url_only" 2>/dev/null)
    [ "$code" = "200" ] && \
        echo -e "  ${GREEN}✅ $label${NC}" || \
        echo -e "  ${RED}❌ $label (HTTP $code)${NC}"
done
echo ""

echo -e "${YELLOW}── NemoClaw ─────────────────────────────────────────────${NC}"
nemoclaw --version 2>/dev/null && echo "  NemoClaw: installed" || \
  echo "  NemoClaw: curl -fsSL nvidia.com/nemoclaw.sh | bash"
SCRIPT

chmod +x ~/scripts/status.sh
echo "alias jstatus='~/scripts/status.sh'" >> ~/.bashrc

# Aliases para modo GPU (igual que JP 6.2)
cat >> ~/.bashrc << 'EOF'

# Modo vLLM producción
alias mode-vllm='
  for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
    ollama stop $m 2>/dev/null
  done
  sleep 2
  docker run --rm \
    --runtime=nvidia --network host \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:/usr/local/cuda/lib64 \
    -v /usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra:ro \
    -v /usr/local/cuda:/usr/local/cuda:ro \
    -v $HOME/models/hf:/models \
    ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
    vllm serve /models/gemma-4-E4B-it \
      --host 0.0.0.0 --port 8000 \
      --max-model-len 8192 \
      --gpu-memory-utilization 0.70 \
      --dtype bfloat16'

alias mode-ollama='
  docker stop $(docker ps -q --filter name=vllm) 2>/dev/null || true
  echo "Modo Ollama. GPU libre."
  ollama ps'

# Activar venv LLM
alias llmenv='source ~/venvs/llm/bin/activate'

# Status
alias jstatus='~/scripts/status.sh'
alias gpu-status='nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader'
EOF

source ~/.bashrc
```

---

## 18. Referencia Rápida JP 7.2

### Diferencias clave de comandos vs JP 6.2

| Tarea | JP 6.2 | JP 7.2 |
|-------|--------|--------|
| Python por defecto | `python3.10` | `python3.12` |
| pip al sistema | `pip3 install X` | `pip3 install X --break-system-packages` o usar venv |
| Wheel PyTorch | `...jp/v61/...cp310...` | `...jp/v72/...cp312...` |
| CUDA arch | sm_87 | **sm_87 (igual)** |
| NemoClaw | No disponible | `curl -fsSL nvidia.com/nemoclaw.sh \| bash` |
| vLLM tag | `gemma4-jetson-orin` | Ver tags nuevos en ghcr.io/nvidia-ai-iot/vllm |

### Puertos y URLs — sin cambios

| Servicio | Puerto | URL |
|---------|--------|-----|
| SSH | 22 | `ssh jetson` |
| XRDP | 3389 | `mstsc /v:192.168.1.100` |
| NoMachine | 4000 | NoMachine client |
| Ollama | 11434 | `http://192.168.1.100:11434` |
| Open WebUI | 3000 | `http://192.168.1.100:3000` |
| vLLM | 8000 | `http://192.168.1.100:8000` |
| Edge Agent | 9000 | `http://192.168.1.100:9000` |

---

## 19. Troubleshooting Específico JP 7.2

### 🔴 XRDP pantalla negra en Ubuntu 24.04

```bash
# Ubuntu 24.04 + GNOME 46 puede tener problemas adicionales con XRDP
# Fix principal: instalar xfce4 (más fiable)
sudo apt install xfce4 xfce4-goodies -y
echo 'exec startxfce4' > ~/.xsession
chmod +x ~/.xsession
sudo systemctl restart xrdp

# O probar con gnome-session directamente:
# Verificar que gnome-session está en Ubuntu 24.04
which gnome-session
dpkg -l | grep gnome-session
```

### 🔴 pip3 falla con "externally-managed-environment"

```bash
# Ubuntu 24.04 protege el Python del sistema
# Solución 1: siempre usar venv (recomendado)
python3 -m venv ~/venvs/llm
source ~/venvs/llm/bin/activate
pip install X  # dentro del venv, no necesita flags

# Solución 2: flag para instalación global (no recomendado)
pip3 install X --break-system-packages

# Solución 3: usar pipx para herramientas globales
pipx install jetson-stats
pipx install huggingface-hub  # para el CLI 'hf'
```

### 🔴 PyTorch wheel no encontrado para JP 7.2

```bash
# Verificar qué está disponible en el CDN de NVIDIA para v72
curl -s "https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/" 2>/dev/null | \
  grep -o 'torch-[^"]*aarch64\.whl' | sort

# Si el índice v72 no existe todavía en el CDN:
# Opción A: Jetson AI Lab (puede tener builds comunitarios para JP7)
pip install --index-url https://pypi.jetson-ai-lab.io/jp7/cu130/ torch

# Opción B: Compilar desde source (tarda 2-3 horas pero garantiza compatibilidad)
# Ver: https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/

# Opción C: Usar el container de NVIDIA que ya incluye PyTorch
docker run --rm --runtime=nvidia \
  nvcr.io/nvidia/l4t-pytorch:r39.2-cu130 \
  python3 -c "import torch; print(torch.cuda.is_available())"
```

### 🔴 NemoClaw: el script de instalación falla

```bash
# Debug del script de instalación
curl -fsSL nvidia.com/nemoclaw.sh -o /tmp/nemoclaw_install.sh
cat /tmp/nemoclaw_install.sh  # revisar el contenido

# Si falla por dependencias:
sudo apt update
sudo apt install -y python3-pip python3-venv git curl

# Intentar de nuevo
bash /tmp/nemoclaw_install.sh
```

### 🔴 nvpmodel muestra modos diferentes en JP 7.2

```bash
# JetPack 7.2 puede tener nuevos power modes para AGX Orin 64GB
sudo nvpmodel --verbose -q

# Verificar los modos disponibles
sudo nvpmodel -p --verbose

# Mode 0 sigue siendo MAXN (máxima potencia)
sudo nvpmodel -m 0
sudo jetson_clocks
```

### 🔴 Docker: cambio en libcuda path en Ubuntu 24.04

```bash
# Verificar ubicación de libcuda en JP 7.2
find /usr -name "libcuda.so*" 2>/dev/null

# Puede ser que en JP 7.2 la ruta cambie
# Ajustar el LD_LIBRARY_PATH en el comando de vLLM si es necesario
# Patrón: verificar con:
ls -la /usr/lib/aarch64-linux-gnu/tegra/libcuda.so* 2>/dev/null
ls -la /usr/lib/aarch64-linux-gnu/nvidia/libcuda.so* 2>/dev/null

# Si ninguna existe, buscar:
find /usr -name "libcuda.so*" -size +1M 2>/dev/null
```

---

## Checklist de Reinstalación para JetPack 7.2

```
PRE-FLASH:
□ Guardar ~/.ssh/ en Windows
□ Guardar ~/.tmux.conf
□ Guardar lista de modelos Ollama
□ Guardar aliases de ~/.bashrc
□ Opcional: copiar ~/models/hf/ a disco externo

FLASH:
□ Descargar ISO JetPack 7.2 desde developer.nvidia.com/embedded/jetpack
□ Crear USB con Rufus (GPT, UEFI, FAT32)
□ Flash via USB booteable (Quick Start Guide oficial)
□ Completar wizard OEM: usuario jetson, contraseña, zona horaria

POST-FLASH (en orden):
□ apt update && apt upgrade (NO dist-upgrade)
□ Instalar: net-tools curl wget htop tmux tree git build-essential python3-venv cmake ninja-build
□ pipx install jetson-stats → jtop
□ SSH server: enable + start + sshd_config
□ hostname: jetson-orin en /etc/hostname + /etc/hosts
□ NetworkManager IP estática + connection.permissions="" (crítico para headless)
□ Deshabilitar NetworkManager-wait-online.service
□ WaylandEnable=false en /etc/gdm3/custom.conf
□ AutomaticLoginEnable=true, AutomaticLogin=jetson
□ /etc/environment con QT_QPA_PLATFORM=xcb, GDK_BACKEND=x11, XDG_SESSION_TYPE=x11
□ xserver-xorg-video-dummy + 30-tegra-headless.conf
□ Desactivar screensaver via gsettings
□ systemctl set-default graphical.target
□ XRDP + startwm.sh fix + polkit fix
□ NoMachine DEB ARM64 desde web9001.nomachine.com
□ GitHub SSH key + agregar en github.com/settings/keys
□ Restaurar ~/.ssh/config en Jetson
□ Instalar Docker + nvidia-ctk (default-runtime=nvidia)
□ Ollama + override OLLAMA_HOST=0.0.0.0
□ ollama pull de los modelos guardados
□ Open WebUI Docker container
□ python3 -m venv ~/venvs/llm
□ cuSPARSELt para CUDA 13
□ PyTorch wheel para JP 7.2 (cp312, CUDA 13, v72)
□ torchvision (precompilado o desde source con TORCHVISION_USE_FFMPEG=0)
□ NemoClaw: curl -fsSL nvidia.com/nemoclaw.sh | bash
□ Jetson Agent Skills: clonar repos nvidia-ai-iot
□ vLLM: docker pull ghcr.io/nvidia-ai-iot/vllm:<TAG-JP7>
□ hf download google/gemma-4-E4B-it
□ UFW rules completas (22, 3389, 4000, 11434, 8000, 3000, 9000)
□ jetson-max-performance systemd service
□ ~/scripts/status.sh + aliases en ~/.bashrc
□ JetBrains Gateway: reconectar y re-descargar backend
□ VS Code Remote SSH: reconectar
```

---

## Recursos Oficiales para JetPack 7.2

```
Quick Start Guide AGX Orin:
  https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/quick_start.html

JetPack 7.2 Downloads:
  https://developer.nvidia.com/embedded/jetpack/downloads

Blog post JetPack 7.2:
  https://developer.nvidia.com/blog/deploy-agentic-ready-ai-at-the-edge-with-memory-efficiency-in-nvidia-jetpack-7-2/

Jetson Device Skills (GitHub):
  https://github.com/NVIDIA-AI-IOT/jetson-device-skills

Jetson BSP Skills (GitHub):
  https://github.com/NVIDIA-AI-IOT/jetson-bsp-skills

NemoClaw:
  https://www.nvidia.com/en-us/ai/nemoclaw/

OpenClaw:
  https://github.com/nvidia/openclaw

PyTorch para Jetson:
  https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/

vLLM containers NVIDIA:
  https://github.com/orgs/NVIDIA-AI-IOT/packages/container/package/vllm

Jetson AI Lab (modelos y containers):
  https://www.jetson-ai-lab.com/
```

---

*Tutorial adaptado para JetPack 7.2 — basado en experiencia real con JetPack 6.2.2*  
*Hardware: NVIDIA Jetson AGX Orin Developer Kit 64GB | JetPack 7.2 | L4T r39.2*  
*Ubuntu 24.04 LTS | CUDA 13.2.1 | Python 3.12 | NemoClaw | Jetson Agent Skills*
