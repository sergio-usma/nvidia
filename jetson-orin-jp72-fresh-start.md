# 🚀 Jetson AGX Orin — Fresh Start JetPack 7.2
## Solo Jetson | El host Windows 11 ya está configurado

---

> **Hardware:** NVIDIA Jetson AGX Orin Developer Kit 64GB  
> **Target:** Ubuntu 24.04 LTS | L4T r39.2 | JetPack 7.2  
> **CUDA:** 13.2.1 | TensorRT 10.16.2 | Python 3.12  
> **Asumido como listo en Windows:** SSH keys, config, NoMachine client, JetBrains Gateway, VS Code Remote SSH, PowerShell functions, hosts file con `192.168.1.100 jetson-orin`

---

## ⚡ Qué cambia en JP 7.2 vs 6.2 (resumen rápido)

| Componente | JP 6.2.2 | JP 7.2 | Impacto |
|------------|---------|--------|---------|
| Ubuntu | 22.04 | **24.04** | Paquetes distintos, pip con venv obligatorio |
| CUDA | 12.6 | **13.2.1** | Wheels PyTorch distintos |
| Python | 3.10 | **3.12** | `cp312` en wheels, no `cp310` |
| L4T | r36.5 | **r39.2** | BSP nuevo, reflash obligatorio |
| Kernel | 5.15 | **6.8** | Drivers actualizados |
| NemoClaw | ❌ | **1 comando** | Stack agéntico listo |
| Agent Skills | ❌ | **Integrado** | Automatización de workflows |
| GPU (sm_87) | sm_87 | **sm_87 igual** | TORCH_CUDA_ARCH_LIST no cambia |
| Instalación | SDK Manager | **ISO unificado** | Nuevo método de flash |

**Lo que NO cambia en el proceso:**
NetworkManager, SSH, XRDP (mismo fix), NoMachine server, Docker, Ollama, GitHub SSH, tmux, aliases.

---

## 📋 Orden de Ejecución

```
PASO 0  → Pre-flash: guardar lo necesario del Jetson actual
PASO 1  → Flashear JetPack 7.2 con ISO
PASO 2  → Primer boot + wizard OEM
PASO 3  → Sistema base Ubuntu 24.04
PASO 4  → Red + IP estática (192.168.1.100)
PASO 5  → SSH server → reconectar desde Windows
PASO 6  → Headless mode (disable Wayland)
PASO 7  → XRDP + fix black screen
PASO 8  → NoMachine server
PASO 9  → GitHub SSH key
PASO 10 → Docker + NVIDIA Container Toolkit
PASO 11 → Ollama + modelos
PASO 12 → Open WebUI
PASO 13 → Python venv + PyTorch JP 7.2
PASO 14 → torchvision
PASO 15 → vLLM (NVIDIA container)
PASO 16 → NemoClaw ← NUEVO
PASO 17 → Jetson Agent Skills ← NUEVO
PASO 18 → Rendimiento máximo + servicios
PASO 19 → Verificación final de conexiones Windows ↔ Jetson
```

---

## PASO 0 — Pre-Flash: Guardar lo Necesario

Antes de formatear, ejecuta en el Jetson actual (JP 6.2.2):

```bash
# Crear directorio de backup
mkdir -p ~/jp62_backup

# 1. Exportar lista de modelos Ollama
ollama list > ~/jp62_backup/ollama_models.txt
cat ~/jp62_backup/ollama_models.txt  # Anota para re-descargar

# 2. Guardar aliases y funciones personalizadas del bashrc
grep -A 200 "Modos de operación" ~/.bashrc > ~/jp62_backup/aliases.txt 2>/dev/null || \
  cp ~/.bashrc ~/jp62_backup/bashrc_backup.txt

# 3. Guardar configuración tmux
cp ~/.tmux.conf ~/jp62_backup/tmux.conf 2>/dev/null

# 4. Guardar clave SSH privada de GitHub (opcional — puedes generar nueva)
cp ~/.ssh/github_ed25519 ~/jp62_backup/github_ed25519 2>/dev/null
cp ~/.ssh/github_ed25519.pub ~/jp62_backup/github_ed25519.pub 2>/dev/null

# 5. Copiar backup a Windows desde PowerShell (no desde Jetson)
# En Windows PowerShell:
# scp -r jetson:~/jp62_backup/ C:\Users\sergi\jetson_backup\
```

> 💡 Los modelos de HuggingFace en `~/models/hf/` son ~15GB. Si tienes un SSD externo, cópialos para no re-descargarlos.

---

## PASO 1 — Flashear JetPack 7.2 con ISO

JetPack 7.2 introduce un método de instalación basado en ISO unificado — ya no necesitas una máquina Linux con SDK Manager.

### 1.1 Descargar la imagen ISO

Ir a: **https://developer.nvidia.com/embedded/jetpack/downloads**  
Seleccionar: **JetPack 7.2 → Jetson AGX Orin Developer Kit → Download JetPack ISO Image**

### 1.2 Crear USB booteable desde Windows 11

1. Descargar **Rufus** → https://rufus.ie
2. Insertar USB de mínimo **16GB** (se borrará todo)
3. En Rufus:
   - Device: tu USB
   - Boot selection: seleccionar la ISO de JetPack 7.2
   - Partition scheme: **GPT**
   - Target system: **UEFI (non CSM)**
   - File system: **FAT32**
   - Click **START** → confirmar advertencia de borrado

### 1.3 Poner el Jetson en Force Recovery Mode

1. Apagar el Jetson completamente
2. Conectar el USB con la ISO al Jetson
3. Mantener presionado el botón **FORCE RECOVERY** (centro de los 3 botones)
4. Sin soltar FORCE RECOVERY, conectar el cable de alimentación
5. Mantener 2-3 segundos más → soltar

> **Referencia oficial:** https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/quick_start.html

### 1.4 Iniciar el flash

El Jetson arrancará desde el USB y comenzará el proceso de flash automáticamente. Sigue las instrucciones en pantalla. El proceso toma 10-20 minutos.

---

## PASO 2 — Primer Boot + Wizard OEM

Conecta monitor + teclado + mouse al Jetson. **Esta es la ÚNICA vez que necesitarás hardware físico.**

En el wizard `oem-config`:
- **Username:** `jetson` (mantener igual para compatibilidad con rutas del tutorial)
- **Password:** la que elijas (anótala bien)
- Zona horaria: tu zona
- Teclado: tu layout
- Acepta todas las licencias de JetPack

Cuando aparezca el escritorio de Ubuntu 24.04 → abre una terminal (`Ctrl+Alt+T`).

---

## PASO 3 — Sistema Base Ubuntu 24.04

### 3.1 Actualización del sistema

```bash
# ❌ NUNCA en Jetson (rompe JetPack):
# sudo apt dist-upgrade

# ✅ Correcto:
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
```

### 3.2 Instalar herramientas esenciales

```bash
sudo apt install -y \
  net-tools curl wget htop tmux tree \
  git nano vim unzip zip \
  build-essential \
  python3-pip python3-venv python3-dev \
  software-properties-common pipx \
  apt-transport-https ca-certificates gnupg lsb-release \
  libopenblas-dev libjpeg-dev libpng-dev cmake ninja-build
```

### 3.3 Instalar jtop (monitor de Jetson)

```bash
# Ubuntu 24.04 — usar pipx para herramientas globales
pipx install jetson-stats
pipx ensurepath
source ~/.bashrc

sudo systemctl restart jtop 2>/dev/null || true

# Verificar
jtop --version
```

### 3.4 Hostname

```bash
sudo hostnamectl set-hostname jetson-orin

sudo nano /etc/hosts
# Cambiar la línea con 127.0.1.1 a:
# 127.0.1.1  jetson-orin
```

---

## PASO 4 — Red + IP Estática (192.168.1.100)

### 4.1 Identificar la conexión Ethernet

```bash
ip addr show
nmcli connection show
nmcli device status
# Anotar el nombre de conexión Ethernet (ej: "Wired connection 1")
```

### 4.2 Asignar IP estática

```bash
CONN="Wired connection 1"   # ← reemplazar con el nombre real

# CRÍTICO: connection.permissions="" hace que la red suba sin login gráfico
# Esto es lo que previene quedarse sin acceso SSH en modo headless
sudo nmcli connection modify "$CONN" \
  ipv4.method manual \
  ipv4.addresses "192.168.1.100/24" \
  ipv4.gateway "192.168.1.1" \
  ipv4.dns "8.8.8.8,1.1.1.1" \
  ipv4.ignore-auto-dns yes \
  connection.permissions "" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100

# Aplicar
sudo nmcli connection down "$CONN" && sudo nmcli connection up "$CONN"

# Verificar
hostname -I
# Debe mostrar: 192.168.1.100
```

### 4.3 Deshabilitar espera de red en boot

```bash
sudo systemctl disable NetworkManager-wait-online.service
sudo systemctl mask NetworkManager-wait-online.service
```

---

## PASO 5 — SSH Server → Primera Reconexión desde Windows

### 5.1 Instalar y habilitar SSH

```bash
sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh

# Configurar sshd_config
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.original
sudo nano /etc/ssh/sshd_config
```

Asegurar estas líneas (descomentar o agregar):

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
sudo systemctl status ssh
# Debe mostrar: Active: active (running)
```

### 5.2 Instalar la clave pública de Windows en el Jetson

Desde **Windows PowerShell** (usando la clave que ya existe de JP 6.2):

```powershell
# La clave ya existe en Windows de la sesión anterior
# Solo copiarla al nuevo Jetson

type "$env:USERPROFILE\.ssh\jetson_orin.pub" | `
  ssh jetson@192.168.1.100 `
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### 5.3 Verificar conexión sin contraseña

```powershell
# Desde Windows — el SSH config ya tiene la entrada "Host jetson"
ssh jetson
# Debe conectar sin pedir contraseña
```

**A partir de aquí, trabaja desde la terminal SSH de Windows. Ya no necesitas el monitor del Jetson.**

### 5.4 Deshabilitar autenticación por contraseña (después de confirmar keys)

```bash
# En el Jetson via SSH
sudo nano /etc/ssh/sshd_config
# Cambiar:
# PasswordAuthentication no

sudo systemctl restart ssh
```

### 5.5 Configurar tmux

```bash
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
bind r source-file ~/.tmux.conf \; display "Config recargado"
EOF

# Crear sesiones base
tmux new-session -d -s main
tmux new-session -d -s llm
```

---

## PASO 6 — Headless Mode (Deshabilitar Wayland)

Ubuntu 24.04 usa Wayland por defecto. Hay que forzar X11 para XRDP y NoMachine.

### 6.1 Deshabilitar Wayland en GDM3

```bash
sudo nano /etc/gdm3/custom.conf
```

Contenido completo:

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

### 6.2 Variables de entorno globales X11

```bash
sudo nano /etc/environment
```

Agregar al final:
```bash
QT_QPA_PLATFORM=xcb
GDK_BACKEND=x11
XDG_SESSION_TYPE=x11
```

### 6.3 Driver de display virtual (Xorg Dummy)

Sin monitor físico, el Jetson crea un framebuffer de solo 640x480. El driver dummy crea un display virtual de 1920x1080.

```bash
sudo apt install xserver-xorg-video-dummy -y

sudo mkdir -p /etc/X11/xorg.conf.d/

sudo tee /etc/X11/xorg.conf.d/30-tegra-headless.conf << 'EOF'
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
EOF
```

### 6.4 Desactivar screensaver y power management

```bash
# Estos settings se aplican al usuario actual
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0
gsettings set org.gnome.settings-daemon.plugins.power idle-dim false
gsettings set org.gnome.settings-daemon.plugins.power power-button-action 'nothing'
```

### 6.5 Establecer boot gráfico y reiniciar

```bash
sudo systemctl set-default graphical.target
sudo systemctl restart gdm3

# Verificar
systemctl get-default
# graphical.target
```

**Reboot de prueba headless:**

```bash
sudo reboot
```

Espera 30 segundos, luego desde Windows:

```powershell
ping 192.168.1.100    # debe responder
ssh jetson            # debe conectar
```

Si ambos funcionan → el Jetson corre headless correctamente.

---

## PASO 7 — XRDP (Remote Desktop)

### 7.1 Instalar y configurar

```bash
sudo apt install xrdp -y

# Fix de certificado SSL
sudo adduser xrdp ssl-cert
```

### 7.2 Fix principal del black screen — startwm.sh

```bash
sudo tee /etc/xrdp/startwm.sh << 'EOF'
#!/bin/sh
# xrdp session startup — Ubuntu 24.04 / Jetson AGX Orin JP 7.2

if test -r /etc/profile; then
    . /etc/profile
fi

# Las tres variables críticas que resuelven el black screen
export DESKTOP_SESSION=ubuntu
export GNOME_SHELL_SESSION_MODE=ubuntu
export XDG_CURRENT_DESKTOP=ubuntu:GNOME

# Limpiar variables conflictivas entre sesiones
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR

test -x /etc/X11/Xsession && exec /etc/X11/Xsession
exec /bin/sh /etc/X11/Xsession
EOF

sudo chmod +x /etc/xrdp/startwm.sh
```

### 7.3 Archivos de sesión del usuario

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

### 7.4 Fix PolicyKit / colord

```bash
sudo mkdir -p /etc/polkit-1/rules.d/

sudo tee /etc/polkit-1/rules.d/45-allow-colord.rules << 'EOF'
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.color-manager.") === 0) {
        return polkit.Result.YES;
    }
});
EOF
```

> 📝 Ubuntu 24.04 usa el formato `.rules` (JavaScript) en lugar del `.pkla` (INI) de 22.04.

### 7.5 Habilitar XRDP

```bash
sudo systemctl enable xrdp
sudo systemctl restart xrdp
sudo systemctl status xrdp

# Verificar que escucha en 3389
sudo ss -tlnp | grep 3389

# Firewall
sudo ufw allow 3389/tcp comment "XRDP Remote Desktop"
sudo ufw reload
```

### 7.6 Conectar desde Windows

El cliente ya está configurado. Solo abrir `mstsc` → `192.168.1.100` → usuario `jetson`.

**Si aparece pantalla negra:**
```bash
# Abrir nueva terminal SSH y matar sesiones huérfanas
ps aux | grep gnome-session | grep -v grep
# Matar los PIDs problemáticos
sudo pkill -u jetson gnome-session 2>/dev/null
sudo systemctl restart xrdp
# Reconectar RDP
```

**Alternativa más estable — XFCE4:**
```bash
sudo apt install xfce4 xfce4-goodies -y
echo 'exec startxfce4' > ~/.xsession
chmod +x ~/.xsession
sudo systemctl restart xrdp
```

---

## PASO 8 — NoMachine Server

```bash
# Verificar la versión actual en:
# https://downloads.nomachine.com/download/?id=30&platform=linux&distro=arm
# Al momento de JP 7.2: versión 9.x para arm64

cd ~/Downloads
wget "https://web9001.nomachine.com/download/9.7/Arm/nomachine_9.7.3_1_arm64.deb"

# Si la versión cambió, descargar desde el navegador de Windows
# y subir al Jetson: scp <archivo.deb> jetson:~/Downloads/

sudo dpkg -i ~/Downloads/nomachine_*.deb
sudo apt --fix-broken install -y

# Iniciar
sudo /usr/NX/bin/nxserver --start
sudo /usr/NX/bin/nxserver --status
# Debe mostrar: Running server at port: 4000

# Autostart
sudo systemctl enable nxserver 2>/dev/null || \
  sudo /usr/NX/bin/nxserver --startup

# Firewall
sudo ufw allow 4000/tcp comment "NoMachine NX"
```

**Conectar desde Windows:** El cliente NoMachine ya está instalado. Solo conectar a `192.168.1.100:4000` con usuario `jetson`.

---

## PASO 9 — GitHub SSH

### 9.1 Opción A: Reutilizar la clave de JP 6.2 (si la guardaste)

```bash
# Si copiaste el backup desde Windows:
# scp C:\Users\sergi\jetson_backup\github_ed25519 jetson:~/.ssh/
# scp C:\Users\sergi\jetson_backup\github_ed25519.pub jetson:~/.ssh/

# Ajustar permisos
chmod 600 ~/.ssh/github_ed25519
chmod 644 ~/.ssh/github_ed25519.pub

# Verificar — si la clave no cambió en GitHub, debería funcionar directamente
ssh -T git@github.com
```

### 9.2 Opción B: Generar nueva clave (recomendado para fresh start)

```bash
ssh-keygen -t ed25519 \
  -C "jetson-orin-jp72-$(date +%Y%m%d)" \
  -f ~/.ssh/github_ed25519

# Mostrar clave pública para agregar en GitHub
cat ~/.ssh/github_ed25519.pub
```

Ir a https://github.com/settings/keys → **New SSH key** → pegar la clave.

### 9.3 Configurar SSH config del Jetson

```bash
cat > ~/.ssh/config << 'EOF'
# GitHub
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
EOF
chmod 600 ~/.ssh/config

# Test
ssh -T git@github.com
# "Hi username! You've successfully authenticated..."
```

### 9.4 Git global

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
git config --global core.editor "nano"
git config --global init.defaultBranch main
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

---

## PASO 10 — Docker + NVIDIA Container Toolkit

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Test básico
docker run hello-world

# NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

# Configurar Docker con runtime NVIDIA como default
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker

# Verificar
docker info | grep "Default Runtime"
# Default Runtime: nvidia

# Test GPU en Jetson (NO usar --gpus all — es para GPU discreta, no Tegra)
docker run --rm --runtime=nvidia ubuntu:24.04 \
  bash -c "ls /dev/ | grep -E 'nvhost|nvmap|tegra' | head -5"
# Debe listar dispositivos tegra
```

---

## PASO 11 — Ollama con GPU

```bash
# Instalar
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
sudo systemctl status ollama

# CRÍTICO: habilitar acceso desde red (por defecto solo localhost)
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
sleep 3

# Verificar binding correcto
sudo ss -tlnp | grep 11434
# DEBE mostrar: *:11434 (no 127.0.0.1:11434)

# Firewall
sudo ufw allow 11434/tcp comment "Ollama API"
```

### Re-descargar modelos

```bash
# Ver la lista que guardaste en el PASO 0
cat ~/jp62_backup/ollama_models.txt 2>/dev/null

# Re-descargar los que usabas
ollama pull gemma4:latest        # ~9.6GB
ollama pull gemma4:26b           # ~17GB
ollama pull ministral-3:latest   # ~6GB
# ... añadir los que tenías

# Verificar
ollama list
```

### Test desde Windows (PowerShell ya configurado)

```powershell
# Las funciones ya están en el perfil de PowerShell de Windows
# Solo verificar que conecta:
Invoke-RestMethod -Uri "http://192.168.1.100:11434/api/tags" |
    Select-Object -ExpandProperty models |
    Select-Object name | Format-Table
```

---

## PASO 12 — Open WebUI

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

# Seguir logs hasta ver "Application startup complete."
docker logs open-webui --follow
```

Acceder desde Windows: `http://192.168.1.100:3000` → crear cuenta admin → chatear.

---

## PASO 13 — Python venv + PyTorch para JP 7.2

### 13.1 Crear entorno virtual Python 3.12

```bash
python3 --version   # Debe ser 3.12.x

python3 -m venv ~/venvs/llm
source ~/venvs/llm/bin/activate

pip install --upgrade pip
pip install numpy   # Ubuntu 24.04 usa numpy 2.x por defecto
```

### 13.2 Instalar cuSPARSELt para CUDA 13

```bash
# Verificar si ya viene con JP 7.2
ls /usr/local/cuda/lib64/libcusparseLt.so 2>/dev/null && echo "Ya instalado" || echo "Instalar"

# Si no está:
cd ~/Downloads
# Verificar la versión más reciente en:
# https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-sbsa/

wget "https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-sbsa/libcusparse_lt-linux-sbsa-0.7.1.0-archive.tar.xz"

tar xf libcusparse_lt-linux-sbsa-0.7.1.0-archive.tar.xz
sudo cp -a libcusparse_lt-linux-sbsa-0.7.1.0-archive/include/* /usr/local/cuda/include/
sudo cp -a libcusparse_lt-linux-sbsa-0.7.1.0-archive/lib/* /usr/local/cuda/lib64/

ls /usr/local/cuda/lib64/libcusparseLt.so
# Debe existir
```

### 13.3 Instalar PyTorch para JP 7.2

Las URLs cambian respecto a JP 6.2: `v72` en lugar de `v61`, Python `cp312` en lugar de `cp310`.

```bash
source ~/venvs/llm/bin/activate

# Paso 1: Ver qué wheels están disponibles para JP 7.2
curl -s "https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/" 2>/dev/null | \
  grep -o 'torch-[^"]*aarch64\.whl' | sort

# Paso 2: Instalar el wheel encontrado (ajustar el nombre exacto)
# Patrón esperado: torch-2.X.X...-cp312-cp312-linux_aarch64.whl
pip install --no-cache-dir \
  "https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/<NOMBRE-EXACTO-DEL-WHEEL>"
```

**Si el CDN de NVIDIA no tiene JP 7.2 aún**, usar Jetson AI Lab:

```bash
# Buscar versión disponible para JP7 / CUDA 13
pip install --no-cache-dir \
  --index-url https://pypi.jetson-ai-lab.io/jp7/cu130/ \
  torch

# O buscar el wheel directo
curl -s "https://pypi.jetson-ai-lab.io/jp7/cu130/" 2>/dev/null | \
  grep -o 'href="[^"]*torch-[^"]*cp312[^"]*aarch64[^"]*\.whl"' | head -3
```

### 13.4 Verificar PyTorch + CUDA 13

```bash
cd ~    # ← Siempre verificar desde ~, no desde un directorio de source
source ~/venvs/llm/bin/activate

python3 -c "
import torch
print('PyTorch   :', torch.__version__)
print('CUDA avail:', torch.cuda.is_available())
print('CUDA ver  :', torch.version.cuda)
if torch.cuda.is_available():
    print('GPU       :', torch.cuda.get_device_name(0))
    print('GPU mem   :', torch.cuda.get_device_properties(0).total_memory // (1024**3), 'GB')
    x = torch.randn(3,3).cuda()
    print('GPU tensor:', x.shape, 'on', x.device)
"
# Esperado: CUDA ver: 13.x, GPU: Orin, 61 GB
```

---

## PASO 14 — torchvision desde Source

```bash
source ~/venvs/llm/bin/activate

pip install wheel setuptools build

# Clonar versión compatible con tu PyTorch (0.21 para torch 2.x)
cd ~
git clone --branch v0.21.0 --depth 1 https://github.com/pytorch/vision torchvision
cd torchvision

export BUILD_VERSION=0.21.0
export TORCH_CUDA_ARCH_LIST="8.7"    # Orin = Ampere sm_87, igual que JP 6.2
export MAX_JOBS=4
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH

# TORCHVISION_USE_FFMPEG=0 evita el error de key_frame en FFmpeg moderno
FORCE_CUDA=1 TORCHVISION_USE_FFMPEG=0 python setup.py bdist_wheel 2>&1 | tail -10
# Debe terminar con: "removing build/bdist.linux-aarch64/wheel"

pip install dist/torchvision-0.21.0*.whl

# Verificar DESDE ~ (no desde ~/torchvision)
cd ~
python3 -c "
import torch, torchvision
print('TorchVision :', torchvision.__version__)
boxes = torch.tensor([[0,0,10,10],[1,1,11,11]], dtype=torch.float32).cuda()
scores = torch.tensor([0.9, 0.8]).cuda()
result = torchvision.ops.nms(boxes, scores, 0.5)
print('NMS op OK   :', result)
"
```

---

## PASO 15 — vLLM (NVIDIA Container)

> NO compilar vLLM desde el main branch de GitHub — requiere PyTorch 2.6+ que no existe para JP 7.2 aún. Usar el container oficial NVIDIA.

### 15.1 Verificar tags disponibles para JP 7.2

```bash
# Ver página oficial de containers:
# https://github.com/orgs/NVIDIA-AI-IOT/packages/container/package/vllm

# Pull del container apropiado para JP 7.2
# Posibles tags (verificar en la página):
docker pull ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin

# O buscar el tag específico de r39.2
docker pull ghcr.io/nvidia-ai-iot/vllm:r39.2.tegra-aarch64-cu130-24.04
```

### 15.2 Descargar modelo Gemma4 desde HuggingFace

```bash
source ~/venvs/llm/bin/activate
pip install huggingface-hub

# CLI nuevo: "hf" (huggingface-cli está deprecado)
hf auth login
# Token desde: https://huggingface.co/settings/tokens
# Acepta la licencia de Gemma4 en: https://huggingface.co/google/gemma-4-E4B-it

mkdir -p ~/models/hf

# Modelo correcto: google/gemma-4-E4B-it (NO google/gemma-4-4b-it)
hf download google/gemma-4-E4B-it \
  --local-dir ~/models/hf/gemma-4-E4B-it

du -sh ~/models/hf/gemma-4-E4B-it/
# ~15GB
```

### 15.3 Lanzar vLLM

```bash
# Liberar GPU de Ollama primero (memoria unificada — no pueden coexistir modelos grandes)
for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
    ollama stop "$m"
done
sleep 2

# Verificar memoria libre
nvidia-smi --query-gpu=memory.free,memory.total --format=csv,noheader

# Lanzar con todos los fixes para Jetson Tegra
docker run --rm \
  --runtime=nvidia \
  --network host \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:/usr/local/cuda/lib64 \
  -v /usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra:ro \
  -v /usr/local/cuda:/usr/local/cuda:ro \
  -v ~/models/hf:/models \
  ghcr.io/nvidia-ai-iot/vllm:<TAG-JP7> \
  vllm serve /models/gemma-4-E4B-it \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.70 \
    --dtype bfloat16

sudo ufw allow 8000/tcp comment "vLLM API"
```

Cuando aparezca `Application startup complete.`, probar desde Windows:

```powershell
Test-NetConnection -ComputerName 192.168.1.100 -Port 8000

$body = @{
    model    = "/models/gemma-4-E4B-it"
    messages = @(@{role="user"; content="Test JP 7.2 vLLM!"})
    max_tokens = 100
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://192.168.1.100:8000/v1/chat/completions" `
    -Method Post -ContentType "application/json" -Body $body |
    Select-Object -ExpandProperty choices | ForEach-Object { $_.message.content }
```

---

## PASO 16 — NemoClaw (Nuevo en JP 7.2)

JetPack 7.2 viene preconfigurado con las dependencias de NemoClaw — solo ejecutar un comando.

```bash
# Un solo comando instala todo el stack NemoClaw
curl -fsSL nvidia.com/nemoclaw.sh | bash

# Verificar instalación
nemoclaw --version 2>/dev/null || \
  python3 -c "import nemoclaw; print('NemoClaw instalado')" 2>/dev/null

# Primer test: pipeline básico con modelo local
python3 << 'EOF'
"""
Test básico de NemoClaw usando Ollama local.
Adaptar imports según la API real post-instalación.
Ref: https://github.com/nvidia/nemoclaw
"""

# Pipeline sin NemoClaw (siempre funciona con Ollama activo)
import requests

OLLAMA = "http://localhost:11434"

def run(prompt, model="gemma4:latest", system="You are an edge AI agent on Jetson."):
    r = requests.post(f"{OLLAMA}/api/generate", json={
        "model": model, "prompt": prompt,
        "system": system, "stream": False
    })
    return r.json()["response"]

# Agentic pipeline de 3 pasos
steps = [
    "What hardware platform are you running on? Be specific about CUDA and memory.",
    "Given JetPack 7.2 with CUDA 13, what new AI capabilities are available?",
    "Suggest a concrete agentic workflow using NemoClaw for edge robotics."
]

context = ""
for i, step in enumerate(steps, 1):
    print(f"\n{'='*50}")
    print(f"Step {i}: {step}")
    print('='*50)
    prompt = f"Context so far: {context}\n\nQuestion: {step}" if context else step
    response = run(prompt)
    print(response)
    context += f"\nStep {i}: {response[:200]}"
EOF
```

---

## PASO 17 — Jetson Agent Skills (Nuevo en JP 7.2)

Tres categorías de skills para automatizar el desarrollo en Jetson: Linux Customization (automatiza configuración BSP), Memory Optimization (optimiza uso de memoria en todo el stack), y Model Benchmarking (identifica la mejor configuración de modelo).

```bash
# Clonar Jetson Device Skills
git clone https://github.com/NVIDIA-AI-IOT/jetson-device-skills.git ~/projects/jetson-device-skills
cd ~/projects/jetson-device-skills

# Instalar dependencias dentro del venv
source ~/venvs/llm/bin/activate
pip install -r requirements.txt 2>/dev/null || \
  pip install openai requests pydantic fastapi uvicorn

# Ver skills disponibles
ls skills/ 2>/dev/null || echo "Ver README para estructura actual"

# Memory Optimization Skill
python3 run_skill.py \
  --skill memory_optimization \
  --backend ollama \
  --model gemma4:latest 2>/dev/null || \
  echo "Revisar README del repo para sintaxis exacta"
```

```bash
# Clonar Jetson BSP Skills
git clone https://github.com/NVIDIA-AI-IOT/jetson-bsp-skills.git ~/projects/jetson-bsp-skills
cd ~/projects/jetson-bsp-skills

source ~/venvs/llm/bin/activate
pip install -r requirements.txt 2>/dev/null

# Ver skills disponibles
cat README.md | head -50
```

> 📚 Documentación live: https://github.com/NVIDIA-AI-IOT/jetson-device-skills

---

## PASO 18 — Rendimiento Máximo + Servicios

### 18.1 Máxima potencia del Jetson

```bash
# Verificar modos disponibles en JP 7.2
sudo nvpmodel --verbose -q

# Modo MAXN (máxima potencia)
sudo nvpmodel -m 0
sudo jetson_clocks

# Guardar configuración
sudo jetson_clocks --store /etc/jetson-clocks.conf

# Servicio para max performance en boot
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

### 18.2 UFW — todas las reglas en un bloque

```bash
sudo ufw allow 22/tcp    comment "SSH"
sudo ufw allow 3389/tcp  comment "XRDP Remote Desktop"
sudo ufw allow 4000/tcp  comment "NoMachine NX"
sudo ufw allow 11434/tcp comment "Ollama API"
sudo ufw allow 8000/tcp  comment "vLLM API"
sudo ufw allow 8888/tcp  comment "Jupyter Lab"
sudo ufw allow 3000/tcp  comment "Open WebUI"
sudo ufw allow 80/tcp    comment "Nginx Gateway (opcional)"
sudo ufw allow 9000/tcp  comment "Edge Agent API (opcional)"

sudo ufw enable
sudo ufw status numbered
```

### 18.3 Aliases y funciones en ~/.bashrc

```bash
cat >> ~/.bashrc << 'EOF'

# ─── Jetson AGX Orin — JP 7.2 ──────────────────────────────

# Status
alias jstatus='~/scripts/status.sh'
alias gpu='nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader'

# LLM venv
alias llmenv='source ~/venvs/llm/bin/activate'

# tmux
alias tm='tmux attach -t main 2>/dev/null || tmux new -s main'

# Ollama
alias ollist='ollama list'
alias olps='ollama ps'
alias olstop='ollama stop'

# Modo vLLM producción (libera Ollama y lanza vLLM)
alias mode-vllm='
  echo "Liberando GPU de Ollama..."
  for m in $(ollama ps 2>/dev/null | tail -n +2 | awk "{print \$1}"); do
    ollama stop "$m" 2>/dev/null
  done
  sleep 2
  echo "GPU libre: $(nvidia-smi --query-gpu=memory.free --format=csv,noheader)"
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

# Modo Ollama desarrollo
alias mode-ollama='
  docker stop $(docker ps -q --filter name=vllm) 2>/dev/null || true
  echo "Modo Ollama activo."
  ollama ps'

# NemoClaw
alias nemoclaw-test='python3 ~/projects/agentic/pipeline_test.py'
EOF

source ~/.bashrc
```

### 18.4 Script de status JP 7.2

```bash
mkdir -p ~/scripts

cat > ~/scripts/status.sh << 'SCRIPT'
#!/bin/bash
CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Jetson AGX Orin 64GB — JetPack 7.2 | $(date '+%H:%M:%S')    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo "  IP: $(hostname -I | awk '{print $1}')  |  $(uptime -p)"
echo ""

echo -e "${YELLOW}── GPU / CUDA 13 ───────────────────────────────────────────${NC}"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw \
  --format=csv,noheader,nounits 2>/dev/null | \
  awk -F', ' '{printf "  Util: %s%% | VRAM: %s/%s MiB | Temp: %s°C | Power: %s W\n",$1,$2,$3,$4,$5}'
CUDA_VER=$(nvcc --version 2>/dev/null | grep "release" | awk '{print $5}' | tr -d ',')
echo "  CUDA: ${CUDA_VER:-N/A} | JetPack 7.2 | L4T r39.2"
echo ""

echo -e "${YELLOW}── RAM ─────────────────────────────────────────────────────${NC}"
free -h | grep Mem | awk '{printf "  Used: %s / %s  (Free: %s)\n",$3,$2,$4}'
echo ""

echo -e "${YELLOW}── Servicios ───────────────────────────────────────────────${NC}"
for svc in ssh xrdp ollama docker; do
    st=$(systemctl is-active $svc 2>/dev/null || echo "N/A")
    [ "$st" = "active" ] && echo -e "  ${GREEN}✅ $svc${NC}" || echo -e "  ${RED}❌ $svc: $st${NC}"
done
st=$(sudo /usr/NX/bin/nxserver --status 2>/dev/null | grep -c "Running" || echo 0)
[ "$st" -gt 0 ] && echo -e "  ${GREEN}✅ NoMachine${NC}" || echo -e "  ${RED}❌ NoMachine${NC}"
echo ""

echo -e "${YELLOW}── APIs ────────────────────────────────────────────────────${NC}"
declare -A APIS=(
    ["Ollama"]="http://localhost:11434/api/tags"
    ["vLLM"]="http://localhost:8000/health"
    ["OpenWebUI"]="http://localhost:3000"
)
for name in "${!APIS[@]}"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "${APIS[$name]}" 2>/dev/null)
    [ "$code" = "200" ] && echo -e "  ${GREEN}✅ $name${NC}" || echo -e "  ${RED}❌ $name (HTTP $code)${NC}"
done
echo ""

echo -e "${YELLOW}── Ollama Models ───────────────────────────────────────────${NC}"
ollama list 2>/dev/null | tail -n +2 | awk '{printf "  %-30s %s\n",$1,$4}' || echo "  Ollama no disponible"
SCRIPT

chmod +x ~/scripts/status.sh
```

---

## PASO 19 — Verificación Final Windows ↔ Jetson

Desde **Windows PowerShell**, verificar que todo conecta:

```powershell
# ─── Test completo de conectividad ───

$IP = "192.168.1.100"

Write-Host "=== Jetson AGX Orin JP 7.2 — Connectivity Check ===" -ForegroundColor Cyan

# Ping
$ping = Test-Connection -ComputerName $IP -Count 1 -Quiet
Write-Host "Ping          : $(if($ping){'✅ OK'}else{'❌ FAIL'})"

# Puertos
@(22,3389,4000,11434,8000,3000) | ForEach-Object {
    $port = $_
    $r = Test-NetConnection -ComputerName $IP -Port $port -WarningAction SilentlyContinue
    $label = switch($port) {
        22    {"SSH"}; 3389 {"XRDP"}; 4000 {"NoMachine"}
        11434 {"Ollama"}; 8000 {"vLLM"}; 3000 {"OpenWebUI"}
    }
    Write-Host "Port $port ($label)$(if($port -lt 1000){' '}): $(if($r.TcpTestSucceeded){'✅ Open'}else{'❌ Closed'})"
}

# Ollama API
try {
    $models = (Invoke-RestMethod -Uri "http://${IP}:11434/api/tags").models
    Write-Host "Ollama models : ✅ $($models.Count) models loaded"
} catch { Write-Host "Ollama models : ❌ API not responding" }

Write-Host ""
Write-Host "Run 'ssh jetson' for terminal access" -ForegroundColor Green
Write-Host "Run 'mstsc /v:$IP' for Remote Desktop" -ForegroundColor Green
Write-Host "Open NoMachine -> $IP`:4000 for best GUI" -ForegroundColor Green
Write-Host "Browse http://$IP`:3000 for Open WebUI" -ForegroundColor Green
```

---

## Troubleshooting Específico JP 7.2

### 🔴 pip da "externally-managed-environment"

```bash
# Ubuntu 24.04 protege el Python del sistema
# SIEMPRE usar venv:
source ~/venvs/llm/bin/activate
pip install <paquete>  # dentro del venv no hay problema

# Para herramientas globales usar pipx:
pipx install <herramienta>
```

### 🔴 PyTorch wheel no encontrado para JP 7.2

```bash
# Verificar qué hay disponible en el CDN
curl -s "https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/" | \
  grep -o 'torch-[^"]*aarch64\.whl' | sort

# Si no hay nada, probar Jetson AI Lab JP7:
pip install --index-url https://pypi.jetson-ai-lab.io/jp7/cu130/ torch

# Último recurso: container NVIDIA con PyTorch ya incluido
docker run --rm --runtime=nvidia \
  nvcr.io/nvidia/l4t-pytorch:r39.2-cu130 \
  python3 -c "import torch; print(torch.cuda.is_available())"
```

### 🔴 XRDP black screen en Ubuntu 24.04

```bash
# Fix inmediato: matar sesiones huérfanas
sudo pkill -u jetson gnome-session 2>/dev/null
sudo systemctl restart xrdp
# Reconectar

# Si persiste, cambiar a XFCE4 (más estable):
sudo apt install xfce4 -y
echo 'exec startxfce4' > ~/.xsession
chmod +x ~/.xsession
sudo systemctl restart xrdp
```

### 🔴 GPU OOM al lanzar vLLM

```bash
# Verificar qué tiene cargado Ollama en GPU
ollama ps
# Descargar todo
for m in $(ollama ps | tail -n +2 | awk '{print $1}'); do ollama stop "$m"; done
sleep 3

# Reducir utilización de GPU
# Cambiar --gpu-memory-utilization 0.70 a 0.60 en el docker run
```

### 🔴 NemoClaw: script de instalación falla

```bash
# Debug
curl -fsSL nvidia.com/nemoclaw.sh -o /tmp/nemoclaw_install.sh
bash -x /tmp/nemoclaw_install.sh 2>&1 | head -50

# Prerequisitos
sudo apt install -y python3-pip python3-venv git curl build-essential
source ~/venvs/llm/bin/activate
bash /tmp/nemoclaw_install.sh
```

### 🔴 libcuda.so.1: file too short en Docker

```bash
# Verificar las librerías del host
ls -lh /usr/lib/aarch64-linux-gnu/tegra/libcuda.so*
# Debe ser ~40MB

# Si el path cambió en JP 7.2, buscar:
find /usr -name "libcuda.so*" -size +1M 2>/dev/null

# Ajustar el LD_LIBRARY_PATH y -v mount en el docker run según lo que encuentres
```

---

## Checklist de Reinstalación JP 7.2

```
PRE-FLASH (Jetson JP 6.2):
□ Guardar lista de modelos Ollama en ~/jp62_backup/
□ Copiar ~/jp62_backup/ a Windows via scp
□ Guardar clave GitHub si quieres reutilizarla

FLASH:
□ Descargar ISO JetPack 7.2 desde developer.nvidia.com/embedded/jetpack
□ Crear USB booteable con Rufus (GPT + UEFI + FAT32)
□ Force Recovery Mode → Flash via USB
□ Wizard OEM: usuario jetson, contraseña, zona horaria

JETSON (post-flash, en orden):
□ apt update && apt upgrade -y (NO dist-upgrade)
□ Instalar paquetes esenciales (incluido pipx)
□ pipx install jetson-stats → jtop funcional
□ SSH server: enable + start + sshd_config configurado
□ hostname: jetson-orin
□ nmcli IP estática + connection.permissions="" + autoconnect
□ Deshabilitar NetworkManager-wait-online.service
□ WaylandEnable=false en /etc/gdm3/custom.conf
□ AutomaticLoginEnable=true en gdm3
□ /etc/environment con X11 vars (QT_QPA_PLATFORM, GDK_BACKEND, XDG_SESSION_TYPE)
□ xserver-xorg-video-dummy + 30-tegra-headless.conf
□ gsettings: desactivar screensaver y power management
□ systemctl set-default graphical.target
□ REBOOT → Verificar SSH desde Windows funciona headless
□ XRDP + startwm.sh fix (3 exports: DESKTOP_SESSION, GNOME_SHELL_SESSION_MODE, XDG_CURRENT_DESKTOP)
□ polkit rules para colord (formato .rules en Ubuntu 24.04)
□ NoMachine DEB arm64 desde web9001.nomachine.com
□ GitHub SSH key (nueva o reutilizada) → agregar en github.com/settings/keys
□ Restaurar clave pública Windows en ~/.ssh/authorized_keys
□ Git global config (user.name, user.email, url SSH)
□ tmux config en ~/.tmux.conf
□ Docker + nvidia-ctk + default-runtime=nvidia
□ Ollama + override.conf con OLLAMA_HOST=0.0.0.0
□ Re-descargar modelos Ollama (ver lista guardada)
□ Open WebUI Docker container
□ UFW: habilitar + todas las reglas de puertos
□ python3 -m venv ~/venvs/llm
□ cuSPARSELt para CUDA 13
□ PyTorch JP 7.2 (cp312, v72, CUDA 13)
□ torchvision desde source (TORCHVISION_USE_FFMPEG=0, cd ~ antes de verificar)
□ docker pull ghcr.io/nvidia-ai-iot/vllm:<TAG-JP7>
□ hf auth login + hf download google/gemma-4-E4B-it
□ NemoClaw: curl -fsSL nvidia.com/nemoclaw.sh | bash
□ Jetson Device Skills: git clone NVIDIA-AI-IOT/jetson-device-skills
□ jetson-max-performance systemd service
□ ~/scripts/status.sh + aliases en ~/.bashrc
□ JetBrains Gateway: reconectar desde Windows → re-descargar backend
□ VERIFICACIÓN FINAL: correr el PowerShell check desde Windows
```

---

## Recursos Clave JP 7.2

```
Flash Guide:
  https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/quick_start.html

JetPack 7.2 Downloads:
  https://developer.nvidia.com/embedded/jetpack/downloads

NemoClaw:
  https://www.nvidia.com/en-us/ai/nemoclaw/
  curl -fsSL nvidia.com/nemoclaw.sh | bash

Jetson Device Skills:
  https://github.com/NVIDIA-AI-IOT/jetson-device-skills

Jetson BSP Skills:
  https://github.com/NVIDIA-AI-IOT/jetson-bsp-skills

vLLM containers (buscar tag JP7):
  https://github.com/orgs/NVIDIA-AI-IOT/packages/container/package/vllm

PyTorch para Jetson:
  https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/
  https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/

Jetson AI Lab (modelos, containers, recursos):
  https://www.jetson-ai-lab.com/
```

---

*Fresh start guide — JetPack 7.2 | Jetson AGX Orin 64GB | Ubuntu 24.04 | CUDA 13.2.1*  
*Windows 11 host ya configurado — solo pasos de la Jetson*
