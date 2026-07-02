# Capítulo 3 — Configuración Base del Sistema

## Introducción

Este capítulo configura el Jetson para trabajo completamente remoto y sin monitor: modo headless, acceso gráfico de alta calidad vía NoMachine y autenticación SSH para GitHub. Al final, el Jetson nunca más necesitará un monitor físico — todo se administra desde Windows vía `ssh jetson` o NoMachine.

> **NOTA sobre XRDP:** Ubuntu 24.04 presenta problemas de compatibilidad con el cliente de escritorio remoto nativo de Windows (`mstsc`). Por esa razón, este capítulo no incluye la configuración de XRDP. **NoMachine es la alternativa verificada y recomendada** — ofrece mejor rendimiento, soporte de audio y es completamente gratuita para uso personal.

**Prerequisito:** Capítulo 1 completado — Ubuntu 24.04 instalado, SSH funcionando.

**Tiempo estimado:** 25–35 minutos.

**Al final de este capítulo tendrá:**
- Modo headless activo (arranque sin GUI local, ~1.5 GB RAM libre)
- Display virtual 1920×1080 para sesiones gráficas remotas
- Acceso gráfico completo vía NoMachine (puerto 4000, escritorio XFCE4)
- Clave SSH de GitHub configurada en el Jetson
- Variables de entorno críticas (`HF_TOKEN`, `CUDA_HOME`, `TORCH_CUDA_ARCH_LIST`) disponibles para Docker y systemd

---

## 2.1 Modo Headless — Arranque sin Entorno Gráfico Local

Por defecto, Ubuntu 24.04 arranca en `graphical.target`, lo que inicia el servidor gráfico GDM3, el entorno de escritorio GNOME y Wayland. Esto consume aproximadamente 1.5–2 GB de RAM innecesariamente cuando el Jetson opera sin monitor físico. El modo headless elimina esa carga y arranca en `multi-user.target` (solo servicios de red y consola).

> **IMPORTANTE:** El Capítulo 15 (Sección 15.0) documenta `multi-user.target` como la arquitectura de arranque limpio recomendada para producción. Este paso lo establece desde el principio. NoMachine sigue funcionando perfectamente en modo headless — genera su sesión gráfica virtualmente en el servidor y la envía a su PC.

### 2.1.1 Deshabilitar Wayland y configurar GDM3

Ubuntu 24.04 usa Wayland por defecto, pero NoMachine necesita X11 para las sesiones gráficas remotas. Antes de pasar a `multi-user.target` completamente, configure GDM3 para que cuando lo inicie manualmente use X11:

```bash
# Deshabilitar Wayland en GDM3
sudo tee /etc/gdm3/custom.conf > /dev/null << 'EOF'
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=jetson
WaylandEnable=false

[security]

[xdmcp]

[chooser]

[debug]
EOF
```

```bash
# Establecer variables globales de sesión X11
# Agregar al final de /etc/environment
sudo tee -a /etc/environment << 'EOF'
QT_QPA_PLATFORM=xcb
GDK_BACKEND=x11
XDG_SESSION_TYPE=x11
EOF
```

### 2.1.2 Display virtual 1920×1080 (Xorg Dummy)

Sin monitor físico conectado, el framebuffer del Jetson se limita a 640×480. El driver `dummy` crea un display virtual de 1920×1080 en RAM que NoMachine puede usar para renderizar la sesión gráfica remota:

```bash
# Instalar driver Xorg dummy
sudo apt install -y xserver-xorg-video-dummy
sudo mkdir -p /etc/X11/xorg.conf.d/

# Crear configuración de display virtual
sudo tee /etc/X11/xorg.conf.d/30-tegra-headless.conf > /dev/null << 'EOF'
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

### 2.1.3 Establecer multi-user.target como target de arranque

```bash
# Arrancar en modo texto (sin GUI local)
sudo systemctl set-default multi-user.target
```

```
# Salida esperada
Created symlink /etc/systemd/system/default.target → /lib/systemd/system/multi-user.target
```

```bash
# Reiniciar para aplicar
sudo reboot now
```

Espere 30 segundos y verifique desde Windows:

```powershell
# En Windows PowerShell
ping 192.168.1.100    # debe responder
ssh jetson            # debe conectar sin contraseña
```

```bash
# Confirmar que el target es correcto
systemctl get-default
```

```
# Salida esperada
multi-user.target
```

---

## 2.2 Acceso Remoto — Resumen de Opciones

| Método | Puerto | Cliente en Windows | Veredicto |
|--------|--------|--------------------|-----------|
| SSH | 22 | PowerShell / Terminal | [OK] Para comandos y transferencia de archivos |
| NoMachine | 4000 | NoMachine Client (gratuito) | [OK] Recomendado para escritorio gráfico |
| XRDP | 3389 | mstsc (nativo Windows) | [ERROR] Problemas de pantalla negra en Ubuntu 24.04 / JP 7.2 |

> **¿Por qué no XRDP?** En la práctica, XRDP con Ubuntu 24.04 y el cliente `mstsc` nativo de Windows presenta un problema de pantalla negra que afecta a casi todas las instalaciones. Las configuraciones de `startwm.sh` y PolicyKit que aparecen en tutoriales para Ubuntu 22.04 (JP 6.2) no resuelven el problema de forma confiable en Ubuntu 24.04. **Use NoMachine** — es más rápido, más estable y completamente gratuito para uso personal y comercial.



---

## 2.3 NoMachine — Acceso Gráfico Remoto de Alta Calidad

NoMachine es la solución de escritorio remoto recomendada para el Jetson. Ofrece compresión de video de alta calidad, soporte de audio, transferencia de archivos integrada y excelente rendimiento incluso con conexiones de red lentas. Es gratuita para uso personal y comercial hasta 10 usuarios simultáneos.

### 2.3.1 Instalar NoMachine Server

```bash
# Verificar la última versión disponible para arm64 en:
# downloads.nomachine.com/download/?id=30&platform=linux&distro=arm
# Al momento de JP 7.2: versión 9.7.x para arm64

cd ~/Downloads

# Descargar directamente si hay conexión desde el Jetson:
wget -q --show-progress \
  "https://web9001.nomachine.com/download/9.7/Arm/nomachine_9.7.3_1_arm64.deb" \
  -O nomachine_arm64.deb

# O bien, descargar en Windows y subir al Jetson via scp:
# [En Windows PowerShell]: scp C:\Users\TuUsuario\Downloads\nomachine_9.7.3_1_arm64.deb jetson:~/Downloads/

# Instalar
sudo dpkg -i ~/Downloads/nomachine_*.deb
sudo apt --fix-broken install -y
```

```
# Salida esperada
Selecting previously unselected package nomachine.
(Reading database ... )
Preparing to unpack nomachine_9.7.3_1_arm64.deb ...
Unpacking nomachine (9.7.3-1) ...
Setting up nomachine (9.7.3-1) ...
```

### 2.3.2 Iniciar y verificar el servidor NoMachine

```bash
# Iniciar el servidor NX
sudo /usr/NX/bin/nxserver --start

# Verificar que está corriendo en el puerto 4000
sudo /usr/NX/bin/nxserver --status
```

```
# Salida esperada
NX> 111 New connections to NoMachine server are enabled.
NX> 161 Enabled service: nxserver.
NX> 162 Disabled service: nxnode.
NX> 161 Enabled service: nxd.
```

```bash
# Habilitar arranque automático
sudo systemctl enable nxserver 2>/dev/null || \
  sudo /usr/NX/bin/nxserver --startup
```

### 2.3.3 Configurar sesión XFCE4 virtual para NoMachine

NoMachine en modo headless necesita un entorno gráfico virtual. XFCE4 es la opción recomendada: consume ~200 MB de RAM (vs ~1.5 GB de GNOME), es estable para uso remoto y responde bien con conexiones de red limitadas.

```bash
# Instalar XFCE4
sudo apt install -y xfce4 xfce4-goodies

# Configurar NoMachine para usar XFCE4 como escritorio virtual
sudo mkdir -p /usr/NX/etc/node.cfg.d/
sudo tee /usr/NX/etc/node.cfg.d/virtual-desktop.cfg > /dev/null << 'EOF'
# Escritorio virtual para sesiones headless
VirtualDesktop 1
DefaultDesktopCommand "startxfce4"
EOF

# (Opcional) Regla PolicyKit para evitar advertencias de color management en GNOME/XFCE4
# Ubuntu 24.04 usa formato .rules (JavaScript), no .pkla como JP 6.2
sudo mkdir -p /etc/polkit-1/rules.d/
sudo tee /etc/polkit-1/rules.d/45-allow-colord.rules > /dev/null << 'EOF'
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.color-manager.") === 0) {
        return polkit.Result.YES;
    }
});
EOF

# Reiniciar NoMachine para aplicar la configuración
sudo /usr/NX/bin/nxserver --restart
```

> **Resultado:** XFCE4 proporciona un escritorio completo (gestor de archivos, terminal, navegador ligero) con solo 200 MB de RAM adicionales. Perfecto para administrar el Jetson gráficamente sin comprometer la memoria disponible para los modelos de IA.

### 2.3.4 Conectar desde Windows

Descargue e instale el cliente NoMachine desde [nomachine.com](https://www.nomachine.com/download):

1. Abra NoMachine Client → clic en **Add**
2. Tipo de conexión: **NX** | Host: `192.168.1.100` (su IP estática) | Puerto: `4000`
3. Usuario: `jetson` | Contraseña: la configurada en el wizard OEM
4. En la primera conexión seleccione **"Create a new virtual desktop"**

```bash
# Verificar que NoMachine está activo desde el Jetson
sudo /usr/NX/bin/nxserver --status
```

```
# Salida esperada
NX> 111 New connections to NoMachine server are enabled.
NX> 161 Enabled service: nxserver.
NX> 162 Disabled service: nxnode.
NX> 161 Enabled service: nxd.
```

> **Si la sesión no abre escritorio:** Ejecute `startxfce4` desde una terminal SSH mientras el cliente NoMachine está conectado. Esto inicia XFCE4 en la sesión virtual ya creada.

---

## 2.4 GitHub SSH — Clave para el Jetson

Si trabaja con repositorios de GitHub desde el Jetson (código, modelos privados, configuraciones), necesita una clave SSH específica del Jetson en su cuenta de GitHub.

### 2.4.1 Generar la clave SSH

```bash
# Generar clave SSH Ed25519 para GitHub
ssh-keygen -t ed25519 \
  -C "jetson-orin-jp72-$(date +%Y%m%d)" \
  -f ~/.ssh/github_ed25519
# Presione Enter cuando pregunte por passphrase (sin contraseña = acceso automático en scripts)

# Mostrar la clave pública para agregarla en GitHub
cat ~/.ssh/github_ed25519.pub
```

```
# Salida esperada — copie esta línea completa
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... jetson-orin-jp72-20260628
```

Agregue esa clave en **github.com/settings/keys** → **New SSH key** → pegue la clave pública.

### 2.4.2 Configurar el cliente SSH del Jetson

```bash
# Crear/actualizar ~/.ssh/config en el Jetson
cat >> ~/.ssh/config << 'EOF'

# GitHub — clave específica del Jetson
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
EOF
chmod 600 ~/.ssh/config

# Verificar conexión
ssh -T git@github.com
```

```
# Salida esperada
Hi tu-usuario! You've successfully authenticated, but GitHub does not provide shell access.
```

### 2.4.3 Configuración global de Git

```bash
# Configurar identidad de commits
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
git config --global core.editor "nano"
git config --global init.defaultBranch main

# Usar SSH en lugar de HTTPS automáticamente
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

---

## 2.5 Variables de Entorno Críticas

Ubuntu 24.04 tiene una restricción importante en `~/.bashrc` que afecta a Docker, systemd y todos los scripts no interactivos: el archivo contiene un bloque `case $- in` que hace `return` anticipado cuando el shell no es interactivo. Cualquier `export` colocado **después** de ese bloque es invisible para Docker, systemd y los scripts.

```bash
# El problema — este bloque existe en ~/.bashrc por defecto
# case $- in
#     *i*) ;;
#       *) return;;   ← TODO lo que esté después de aquí NO se ejecuta
# esac               ← en Docker, systemd, scripts no interactivos
```

La solución es colocar las variables críticas **antes** de ese bloque, al inicio de `~/.bashrc`.

### 2.5.1 Configurar variables al inicio de ~/.bashrc

> **[IMPORTANTE — Leer antes de continuar]** Estas variables se configuran **ahora**, aunque algunos servicios (HuggingFace, vLLM, OpenClaw) no se instalen hasta capítulos posteriores. El motivo es que Docker, systemd y los scripts automatizados solo leen variables definidas **antes** del bloque `case $-` del `~/.bashrc`. Configurarlas aquí garantiza que estén disponibles globalmente desde el primer día. Si al ejecutar un capítulo posterior no tiene aún la variable activa, recargue el shell: `source ~/.bashrc`.

```bash
# Hacer backup del bashrc actual
cp ~/.bashrc ~/.bashrc.backup

# Crear un bloque de exports al inicio del bashrc
# (este comando inserta las líneas AL PRINCIPIO del archivo)
cat > /tmp/bashrc_header.txt << 'HEADER'
# ══════════════════════════════════════════════════════════════════
# EXPORTS GLOBALES — AL INICIO (antes del bloque case $- in)
# Visibles en: shells interactivos, SSH, Docker, systemd, scripts
# ══════════════════════════════════════════════════════════════════

# HuggingFace — IMPORTANTE: reemplaza hf_SU_TOKEN_AQUI con tu token real
# Obtén tu token en: huggingface.co/settings/tokens (tipo "read")
export HF_TOKEN="hf_SU_TOKEN_AQUI"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"

# vLLM API key local (valor fijo, no es un token de cuenta)
export VLLM_API_KEY="vllm-local"

# CUDA
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Python / pipx / npm global
export PATH="$HOME/.npm-global/bin:$PATH"
export PATH="$PATH:$HOME/.local/bin"

# Node.js cache para OpenClaw (reduce tiempo de inicio)
export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache

# PyTorch — arquitectura GPU del Jetson AGX Orin (Ampere sm_87)
export TORCH_CUDA_ARCH_LIST="8.7"

# ══════════════════════════════════════════════════════════════════
HEADER

# Insertar el header al principio del bashrc existente
cat /tmp/bashrc_header.txt ~/.bashrc > /tmp/bashrc_new.txt
mv /tmp/bashrc_new.txt ~/.bashrc
rm /tmp/bashrc_header.txt

source ~/.bashrc
echo "[OK] Variables configuradas. HF_TOKEN: ${HF_TOKEN:0:10}..."
```

> **IMPORTANTE:** Reemplace `hf_SU_TOKEN_AQUI` con su token real de HuggingFace. Si aún no tiene un token, puede dejarlo vacío por ahora — es necesario en el Capítulo 11 (descarga de modelos con acceso controlado como Llama o Gemma). Obtenga el token gratis en **huggingface.co/settings/tokens**.

### 2.5.2 Propagar variables a Docker y systemd

Docker y systemd no leen `~/.bashrc`. Necesitan las variables en `/etc/environment`:

```bash
# Propagar HF_TOKEN a Docker y systemd
# (reemplazar hf_SU_TOKEN_AQUI con el token real antes de ejecutar)

sudo tee -a /etc/environment << 'EOF'
HF_TOKEN=hf_SU_TOKEN_AQUI
HUGGING_FACE_HUB_TOKEN=hf_SU_TOKEN_AQUI
VLLM_API_KEY=vllm-local
CUDA_HOME=/usr/local/cuda
TORCH_CUDA_ARCH_LIST=8.7
EOF

# Verificar que no haya duplicados
grep -E "HF_TOKEN|VLLM_API_KEY|CUDA_HOME" /etc/environment
```

```bash
# Guardar también el token en la caché de HuggingFace
# Esto evita que hf CLI pida autenticación interactiva en scripts
mkdir -p ~/.cache/huggingface
echo "hf_SU_TOKEN_AQUI" > ~/.cache/huggingface/token
chmod 600 ~/.cache/huggingface/token
echo "[OK] Token HuggingFace cacheado"
```

### 2.5.3 Verificación de variables

```bash
# Verificar que las variables están disponibles
echo "HF_TOKEN:            ${HF_TOKEN:0:15}..."
echo "VLLM_API_KEY:        $VLLM_API_KEY"
echo "CUDA_HOME:           $CUDA_HOME"
echo "TORCH_CUDA_ARCH:     $TORCH_CUDA_ARCH_LIST"

# Verificar que nvcc está en PATH
nvcc --version | grep "release"

# Verificar que Docker puede ver las variables de sistema
# (esto se comprueba plenamente en la Capítulo 8, cuando Docker esté instalado)
```

```
# Salida esperada
HF_TOKEN:            hf_oauth_xxxxxxx...
VLLM_API_KEY:        vllm-local
CUDA_HOME:           /usr/local/cuda
TORCH_CUDA_ARCH:     8.7
Cuda compilation tools, release 13.2, V13.2.1
```

---

## 2.6 Herramientas de Monitoreo del Sistema

Antes de continuar con la instalación de software adicional, instale las herramientas de monitoreo que se usarán a lo largo de toda la guía. La más importante es `jtop`, diseñada específicamente para el hardware Jetson.

### 2.6.1 jtop — Monitor de GPU/CPU/Memoria en Tiempo Real

`jtop` es parte del paquete `jetson-stats` y proporciona una vista en tiempo real de CPU, GPU, memoria unificada, temperatura y modo de energía activo. Es la herramienta de diagnóstico principal para el Jetson.

```bash
# Instalar jetson-stats
sudo pip3 install jetson-stats

# Si pip3 no está disponible:
sudo apt install -y python3-pip
sudo pip3 install jetson-stats

# Verificar instalación
jtop --version
```

Salida esperada:
```
jtop 4.2.x
```

```bash
# Lanzar jtop (interfaz interactiva — presione 'q' para salir)
jtop
```

`jtop` muestra en tiempo real:
- **Pestaña ALL**: uso de CPU por núcleo, GPU, memoria RAM unificada, temperatura, modo nvpmodel activo
- **Pestaña GPU**: frecuencia GPU, utilización, consumo de energía
- **Pestaña MEM**: desglose de memoria por componente (CPU, GPU, compartida)
- **Pestaña CTRL**: cambio interactivo de modo de energía y `jetson_clocks`

> **NOTA:** `jtop` requiere ser ejecutado como usuario normal (no como root). Si ve el error "Permission denied", asegúrese de no estar usando `sudo jtop`.

### 2.6.2 tegrastats — Monitor de Línea de Comandos

`tegrastats` viene preinstalado con JetPack 7.2. Es útil para scripting y logging porque su salida es parseable:

```bash
# Ver métricas cada segundo durante 10 segundos
tegrastats --interval 1000 &
sleep 10
kill %1

# Capturar métricas en un log durante una inferencia:
tegrastats --interval 500 --logfile ~/logs/tegra_$(date +%Y%m%d_%H%M).log &
TEGRA_PID=$!
# ... ejecutar inferencia ...
kill $TEGRA_PID
```

---

## 2.7 SSH desde Windows y Transferencia de Archivos (SCP)

Esta sección configura el cliente SSH de Windows para conectar al Jetson con el alias `ssh jetson`, y cubre los comandos básicos de transferencia de archivos con SCP.

### 2.7.1 Configurar `~/.ssh/config` en Windows

El archivo `~/.ssh/config` en Windows define hosts nombrados con sus configuraciones. En lugar de escribir `ssh jetson@192.168.1.100 -i ~/.ssh/jetson_orin` cada vez, basta con `ssh jetson`.

A continuación, el archivo de configuración completo recomendado. Incluye tres perfiles para el Jetson (conexión estándar, reenvío gráfico X11 y tunnels de servicios) y el perfil de GitHub:

```
# [EN WINDOWS] Abrir con bloc de notas:
# notepad $HOME\.ssh\config
# O en PowerShell: code $HOME\.ssh\config
# IMPORTANTE: reemplace 192.168.1.100 con la IP estática de su Jetson

# ─────────────────────────────────────────────
#  Jetson AGX Orin — Conexión SSH estándar
# ─────────────────────────────────────────────
Host jetson
    HostName 192.168.1.100
    User jetson
    IdentityFile ~/.ssh/jetson_orin
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 10
    TCPKeepAlive yes
    Compression yes

# ─────────────────────────────────────────────
#  Jetson — Con reenvío gráfico X11 via SSH
# ─────────────────────────────────────────────
Host jetson-x11
    HostName 192.168.1.100
    User jetson
    IdentityFile ~/.ssh/jetson_orin
    IdentitiesOnly yes
    ForwardX11 yes
    ForwardX11Trusted yes
    ServerAliveInterval 60
    ServerAliveCountMax 10

# ─────────────────────────────────────────────
#  Jetson — Con tunnels para todos los servicios
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
#  GitHub (configurado en el Capítulo 2, §2.4)
# ─────────────────────────────────────────────
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_key
    IdentitiesOnly yes
```

> **NOTA:** Si aún no tiene el par de claves `jetson_orin` en Windows, genérelo con `ssh-keygen -t ed25519 -f $HOME\.ssh\jetson_orin` en PowerShell y copie la clave pública al Jetson con `ssh-copy-id -i ~/.ssh/jetson_orin.pub jetson@192.168.1.100`. Luego podrá conectar con `ssh jetson` sin contraseña.

> **NOTA sobre GitHub:** El archivo de clave para GitHub (`github_key`) se configura en la sección 2.4 de este mismo capítulo. Si todavía no lo ha creado, aparecerá como error al hacer `ssh -T git@github.com` — es normal en este punto.

```bash
# [EN WINDOWS POWERSHELL] Probar conexion con alias:
ssh jetson
```

```
# Salida esperada:
jetson@jetson-orin:~$
```

### 2.7.2 Transferencia de archivos con SCP

SCP usa el canal SSH — no requiere configuración adicional:

```bash
# [EN WINDOWS POWERSHELL] Copiar archivo de Windows al Jetson
# Reemplace "TuUsuario" con su usuario de Windows
scp C:\Users\TuUsuario\Downloads\modelo.gguf jetson:~/data/models/

# Copiar directorio completo
scp -r C:\Users\TuUsuario\proyecto\ jetson:~/projects/

# Descargar archivo del Jetson a Windows
scp jetson:~/logs/resultado.txt C:\Users\TuUsuario\Desktop\

# Ver tamaño de un directorio en el Jetson antes de descargar
ssh jetson "du -sh ~/data/models/"
```

> **CONSEJO:** Para modelos grandes (>4 GB), use `aria2c` en el Jetson para descargas directas desde HuggingFace — es significativamente más rápido que SCP desde Windows (ver Capítulo 6, §6.4).

### 2.7.3 SSH Tunnels — acceso a servicios del Jetson desde Windows

Los SSH tunnels redirigen un puerto local de Windows hacia un puerto en el Jetson:

```bash
# [EN WINDOWS POWERSHELL] Acceder a Open WebUI del Jetson desde el navegador de Windows:
# (Open WebUI corre en el Jetson en el puerto 3000)
ssh -L 3000:localhost:3000 jetson -N
# Abrir navegador: http://localhost:3000
```

```bash
# Tunnel para multiples servicios a la vez:
ssh -L 3000:localhost:3000 \
    -L 8000:localhost:8000 \
    -L 11434:localhost:11434 \
    jetson -N
# Ctrl+C para cerrar todos los tunnels
```

> **NOTA:** El flag `-N` mantiene el tunnel sin abrir un shell interactivo. Los tunnels se explican con más detalle en el Capítulo 7 (§7.5), donde se integran con VSCode Remote y JupyterLab.

---

## 2.8 Verificación Final del Capítulo

```bash
# Verificacion completa del estado tras Capitulo 2
echo ""
echo "=== VERIFICACION CAPITULO 2 ==="

echo ""
echo "-- Boot target --"
systemctl get-default
# Esperado: multi-user.target

echo ""
echo "-- Servicios de acceso remoto --"
sudo systemctl is-active nxserver 2>/dev/null \
  && echo "[OK] NoMachine activo (:4000)" \
  || sudo /usr/NX/bin/nxserver --status 2>/dev/null | grep "Running" \
  || echo "[WARN] NoMachine: verificar con /usr/NX/bin/nxserver --status"

echo ""
echo "── Display virtual ──"
ls /etc/X11/xorg.conf.d/30-tegra-headless.conf && echo "[OK] Config headless presente" || echo "[ERROR] Falta config headless"

echo ""
echo "── GitHub SSH ──"
ssh -T git@github.com 2>&1 | grep -E "success|Hi" && echo "[OK] GitHub SSH funciona" || echo "[WARN]  GitHub SSH: agregar clave en github.com/settings/keys"

echo ""
echo "── Variables de entorno ──"
[ -n "$HF_TOKEN" ]          && echo "[OK] HF_TOKEN configurado"  || echo "[WARN]  HF_TOKEN vacío (necesario en Capítulo 11)"
[ -n "$VLLM_API_KEY" ]      && echo "[OK] VLLM_API_KEY: $VLLM_API_KEY" || echo "[ERROR] VLLM_API_KEY no configurado"
[ -n "$TORCH_CUDA_ARCH_LIST" ] && echo "[OK] TORCH_CUDA_ARCH_LIST: $TORCH_CUDA_ARCH_LIST" || echo "[ERROR] TORCH_CUDA_ARCH_LIST no configurado"
nvcc --version 2>/dev/null | grep "release" && echo "[OK] nvcc en PATH" || echo "[ERROR] nvcc no en PATH"
```

```
# Salida esperada al completar el Capítulo 2 correctamente:
=== VERIFICACION CAPITULO 2 ===

-- Boot target --
multi-user.target

-- Servicios de acceso remoto --
[sudo] password for jetson:
active
[OK] NoMachine activo (:4000)

── Display virtual ──
/etc/X11/xorg.conf.d/30-tegra-headless.conf
[OK] Config headless presente

── GitHub SSH ──
Hi <tu_usuario>! You've successfully authenticated, but GitHub does not provide shell access.
[OK] GitHub SSH funciona

── Variables de entorno ──
[OK] HF_TOKEN configurado
[OK] VLLM_API_KEY: vllm-local
[ERROR] TORCH_CUDA_ARCH_LIST no configurado
Cuda compilation tools, release 13.2, V13.2.78
[OK] nvcc en PATH
```

> **NOTA sobre `[ERROR] TORCH_CUDA_ARCH_LIST`:** Este error es **esperado y normal** en este punto del libro. La variable `TORCH_CUDA_ARCH_LIST` se configura en el Capítulo 17 (entorno Python con PyTorch). No se preocupe por este mensaje — todo lo demás debe mostrar `[OK]`.

| Error | Causa probable | Solución |
|-------|---------------|---------|
| `multi-user.target` no aparece | Reboot no realizado | `sudo reboot now` y esperar |
| NoMachine no conecta | Puerto 4000 bloqueado | Verificar con `sudo ss -tlnp \| grep 4000` |
| NoMachine pantalla negra | XFCE4 no configurado | Revisar sección 2.3.3 |
| `HF_TOKEN` vacío | No colocado antes del bloque `case` | Revisar sección 2.5.1 |
| `nvcc not found` | PATH no propagado | `source ~/.bashrc` o verificar el bloque EXPORTS |
| `ssh jetson` rechaza la clave | Clave pública no en `authorized_keys` | Ver sección 2.7.1 |

> **Próximo paso:** El Capítulo 3 cubre el ajuste de rendimiento — modos de energía con `nvpmodel` y bloqueo de frecuencias con `jetson_clocks`. Sin este paso, el Jetson corre a un tercio de su velocidad máxima de inferencia.
