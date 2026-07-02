# Capítulo 8 — IDE Remoto y Transferencia de Archivos: VSCode, PyCharm y SSH

## Introducción

Con el Jetson funcionando en modo headless (Capítulo 2), SSH activo y NoMachine configurado, el siguiente paso natural es establecer un entorno de desarrollo productivo desde su PC con Windows. Este capítulo cubre tres herramientas fundamentales:

1. **VSCode Remote SSH** — el editor de código más popular del mundo, ejecutando código directamente en el Jetson desde su PC sin copiar archivos
2. **PyCharm via JetBrains Gateway** — IDE profesional para Python con depurador remoto completo
3. **SCP y SSH Tunnels** — transferencia de archivos y acceso a servicios del Jetson desde Windows

**Por qué ejecutar el IDE en el Jetson y no en su PC:** Los scripts de Python que usa este libro (inferencia LLM, visión por computadora, TTS/STT) dependen de CUDA 13.2.1, PyTorch ARM64 y bibliotecas compiladas para sm_87. Si ejecuta el código en su PC y lo transfiere al Jetson, pierde el autocompletado, los errores de tipo y el debugger. Con Remote SSH, el editor corre en su PC pero **todo el código, las dependencias y la ejecución ocurren en el Jetson**.

**Prerequisito:** Capítulo 2 completado — SSH activo con alias `ssh jetson` configurado en `~/.ssh/config` de Windows.

**Tiempo estimado:** 20–30 minutos.

---

## 7.1 Verificar Conectividad SSH desde Windows

Antes de configurar los IDEs, confirme que la conexión SSH base funciona correctamente:

```bash
# Desde Windows PowerShell o Terminal:
# (si ssh jetson ya estaba configurado en el Capitulo 2)
ssh jetson
```

```bash
# Salida esperada
jetson@jetson-orin:~$
```

### 7.1.1 Configurar `ssh jetson` si no existe

Si el alias `ssh jetson` no está configurado, créelo ahora en Windows:

```bash
# En Windows PowerShell — crear o editar C:\Users\SU_USUARIO\.ssh\config
# IMPORTANTE: reemplaza TU_IP con la IP del Jetson (ej: 192.168.1.100)
# y TU_USUARIO con su nombre de usuario de Windows
notepad C:\Users\TU_USUARIO\.ssh\config
```

Contenido del archivo `~/.ssh/config` en Windows:

```bash
Host jetson
    HostName 192.168.1.100
    User jetson
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

```bash
# Probar conexion simplificada [EN WINDOWS POWERSHELL]:
ssh jetson
# Debe conectar directamente sin pedir contrasena
```

> **NOTA:** `ssh jetson` funciona porque `~/.ssh/config` en Windows define un bloque `Host jetson` con la IP, usuario y ruta a la clave privada. No es un alias de shell sino una configuración del cliente SSH. Esto se explica en detalle en el Capítulo 2 (§2.1).

---

## 7.2 VSCode Remote SSH

VSCode Remote SSH es la forma más eficiente de desarrollar en el Jetson. El editor corre en Windows con toda la UI familiar, pero el servidor de lenguaje, el terminal integrado, las extensiones de Python y la ejecución de código ocurren 100% en el Jetson.

### 7.2.1 Instalar la Extensión Remote SSH

1. Abra VSCode en Windows
2. Presione `Ctrl+Shift+X` (Extensiones)
3. Busque `Remote - SSH` (publicada por Microsoft)
4. Clic en **Install**

También instale estas extensiones relacionadas:
- **Remote - SSH: Editing Configuration Files** (para editar `~/.ssh/config` desde VSCode)
- **Python** (publicada por Microsoft) — se instalará también en el Jetson automáticamente

### 7.2.2 Conectar VSCode al Jetson

1. Presione `Ctrl+Shift+P` → escriba `Remote-SSH: Connect to Host...`
2. Seleccione `jetson` (aparecerá desde su `~/.ssh/config`)
3. Se abrirá una nueva ventana de VSCode. En la esquina inferior izquierda verá `SSH: jetson`
4. Primera conexión: VSCode instalará el servidor remoto en el Jetson (~100 MB, tarda 1–2 min)

```bash
# Salida en el panel Output de VSCode durante la conexion:
[11:23:15.891] Installing VS Code Server for host linux
[11:23:20.012] Downloading server...
[11:23:45.233] Installing server...
[11:23:48.001] Connected!
```

### 7.2.3 Abrir la carpeta de trabajo en el Jetson

Una vez conectado:

1. `Ctrl+K Ctrl+O` → **Open Folder**
2. Escriba la ruta del Jetson: `/home/jetson/` (o `/data/proyectos/`)
3. Clic en **OK**

Ahora puede crear, editar y ejecutar archivos directamente en el Jetson. El terminal integrado (`Ctrl+\``) abre una terminal en el Jetson.

### 7.2.4 Instalar extensiones Python en el Jetson

Con la conexión activa, instale las extensiones en el **servidor remoto** (el Jetson):

```bash
# En VSCode conectado al Jetson:
# Ctrl+Shift+X -> buscar "Python" -> Install on SSH: jetson
```

Las extensiones marcadas con `(SSH: jetson)` corren en el Jetson y tienen acceso a CUDA, PyTorch y todas las bibliotecas instaladas.

### 7.2.5 Seleccionar el intérprete Python

```bash
# Ctrl+Shift+P -> "Python: Select Interpreter"
# Seleccione el venv correcto segun el proyecto:
# - Para inferencia LLM:  ~/venvs/llm/bin/python3
# - Para desarrollo:      ~/venvs/dev/bin/python3
# - Para proyectos:       ~/projects/<nombre>/venv/bin/python3
```

> **CONSEJO:** Cree un archivo `.vscode/settings.json` en cada proyecto del Jetson con `"python.defaultInterpreterPath"` apuntando al venv correcto. VSCode lo recuerda por proyecto.

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python3",
    "python.terminal.activateEnvironment": true,
    "editor.formatOnSave": true
}
```

### 7.2.6 Ejecutar y depurar código en el Jetson

Con VSCode remoto, el botón "Run" (`F5`) ejecuta el script directamente en el Jetson con acceso a la GPU. El depurador funciona igual que localmente — puntos de interrupción, inspección de variables, call stack.

```python
# test_gpu.py -- crear en el Jetson desde VSCode
import torch
print(f"CUDA disponible: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

```bash
# Salida esperada al presionar F5 o "Run Python File":
CUDA disponible: True
GPU: Orin (Ampere)
VRAM: 62.8 GB
```

---

## 7.3 PyCharm via JetBrains Gateway

PyCharm Professional ofrece el depurador más completo para Python, con soporte de Django, Flask, profiling y análisis de memoria. JetBrains Gateway permite conectarlo al Jetson sin instalar PyCharm en el dispositivo.

> **IMPORTANTE:** JetBrains Gateway requiere una suscripción a PyCharm Professional (a partir de ~8 USD/mes). Existe un **período de prueba gratuito de 30 días** — suficiente para seguir los capítulos de proyectos avanzados de este libro antes de decidir si continuar.

### 7.3.1 Instalar JetBrains Gateway en Windows

1. Descargue JetBrains Gateway desde `jetbrains.com/remote-development/gateway`
2. Instale y abra Gateway
3. En la pantalla principal, seleccione **SSH**

### 7.3.2 Crear una conexión SSH al Jetson

1. Clic en **New Connection**
2. Host: `192.168.1.100` (su IP estática del Capítulo 2) | Puerto: `22` | Usuario: `jetson`
3. Autenticación: **Private Key** → seleccione `C:\Users\TU_USUARIO\.ssh\id_ed25519`
4. Clic en **Check Connection and Continue**

```bash
# Gateway verificara la conexion y mostrara:
Connection test successful.
SSH fingerprint: SHA256:... (accept once)
```

### 7.3.3 Seleccionar IDE y carpeta remota

1. En la siguiente pantalla, seleccione **PyCharm** como IDE
2. Gateway descargará e instalará el servidor de PyCharm en el Jetson (~300 MB, una sola vez)
3. Seleccione la carpeta del proyecto: `/home/jetson/` o la ruta de su proyecto
4. Clic en **Download and Start IDE**

Después de 1–2 minutos, PyCharm se abrirá en su PC conectado al Jetson.

### 7.3.4 Configurar el intérprete Python en PyCharm

1. `File → Settings → Project → Python Interpreter`
2. Clic en el engranaje → **Add Interpreter → On SSH**
3. Seleccione **Existing environment** → ruta: `/home/jetson/venvs/llm/bin/python3`

```bash
# Verificar que PyCharm ve la GPU desde el Jetson:
# Run -> Python Console:
import torch
print(torch.cuda.get_device_name(0))
```

```bash
# Salida esperada:
Orin (Ampere)
```

---

## 7.4 Transferencia de Archivos: SCP y rsync

SCP (Secure Copy) y rsync transfieren archivos entre su PC Windows y el Jetson sin software adicional — usan el mismo canal SSH ya configurado en el Capítulo 2.

### 7.4.1 Copiar archivos desde Windows al Jetson

```bash
# [EN WINDOWS POWERSHELL] Copiar un archivo al Jetson
scp C:\Users\sergi\Downloads\mi_modelo.gguf jetson:~/data/models/gguf/

# Copiar un directorio completo (-r = recursivo)
scp -r C:\Users\sergi\Documents\proyecto\ jetson:~/projects/

# Copiar preservando timestamps y permisos
scp -p C:\Users\sergi\scripts\setup.sh jetson:~/scripts/
```

### 7.4.2 Descargar archivos del Jetson a Windows

```bash
# [EN WINDOWS POWERSHELL] Descargar un archivo del Jetson
scp jetson:~/logs/analytics_20260629.txt C:\Users\sergi\Desktop\

# Descargar resultados de un experimento completo
scp -r jetson:~/experiments/run_001/ C:\Users\sergi\Documents\resultados\

# Verificar el tamano antes de descargar (para archivos grandes)
ssh jetson du -sh ~/data/models/gguf/
```

```bash
# Salida de du:
8.1G    /home/jetson/data/models/gguf/
```

### 7.4.3 Sincronización eficiente con rsync

Para transferencias frecuentes o directorios grandes, rsync es más eficiente que scp — solo transfiere los cambios:

```bash
# [EN GIT BASH o WSL en Windows] rsync desde Windows al Jetson
rsync -avz --progress /c/Users/sergi/proyectos/mi_app/ jetson:~/projects/mi_app/
```

```bash
# Salida esperada (solo transfiere archivos modificados):
sending incremental file list
./
main.py
requirements.txt
sent 1,247 bytes  received 62 bytes  1,309.00 bytes/sec
```

> **CONSEJO:** Para modelos grandes (>4 GB), use `aria2c` en el Jetson para descargas directas desde HuggingFace o NGC — es mucho más rápido que SCP (ver Capítulo 6, §6.4).

---

## 7.5 SSH Tunnels — Acceso a Servicios del Jetson desde Windows

Los SSH tunnels permiten acceder desde su PC Windows a servicios que corren en el Jetson (APIs, interfaces web, Jupyter) sin exponer puertos directamente a internet.

### 7.5.1 ¿Para qué sirven?

| Servicio en el Jetson | Puerto | Acceso desde Windows con tunnel |
|-----------------------|--------|---------------------------------|
| Open WebUI | 3000 | `http://localhost:3000` en el navegador de Windows |
| vLLM API | 8000 | `http://localhost:8000/v1` desde scripts de Windows |
| llama.cpp | 8080 | `http://localhost:8080` |
| Ollama API | 11434 | `http://localhost:11434` |
| JupyterLab | 8888 | `http://localhost:8888` en navegador de Windows |
| N8N | 5678 | `http://localhost:5678` |
| FastAPI (proyectos) | 5000 | `http://localhost:5000` |

### 7.5.2 Tunnel simple (un solo puerto)

```bash
# [EN WINDOWS POWERSHELL] Abrir tunnel para Open WebUI
# Sintaxis: ssh -L LOCAL_PORT:localhost:REMOTE_PORT jetson -N
ssh -L 3000:localhost:3000 jetson -N

# En otra terminal: abrir navegador en Windows y visitar:
# http://localhost:3000
# Vera el Open WebUI corriendo en el Jetson
```

```bash
# Tunnel para JupyterLab
ssh -L 8888:localhost:8888 jetson -N

# Primero en el Jetson, iniciar Jupyter:
# jupyter lab --no-browser --port=8888
# Luego abrir en Windows: http://localhost:8888
```

> **NOTA:** El flag `-N` indica que no se abre shell — la conexión solo mantiene el tunnel activo. Para cerrar el tunnel, presione `Ctrl+C` en esa terminal.

### 7.5.3 Tunnel multi-puerto (todos los servicios a la vez)

```bash
# [EN WINDOWS POWERSHELL] Abrir tunnels para todos los servicios principales
# (mantener esta terminal abierta mientras trabaja)
ssh -L 3000:localhost:3000 \
    -L 8000:localhost:8000 \
    -L 8080:localhost:8080 \
    -L 11434:localhost:11434 \
    -L 8888:localhost:8888 \
    -L 5678:localhost:5678 \
    jetson -N
```

### 7.5.4 Tunnel permanente con ~/.ssh/config

Para no escribir el comando cada vez, agregue los tunnels al archivo `~/.ssh/config` de Windows:

```bash
# Agregar a C:\Users\TU_USUARIO\.ssh\config
Host jetson-tunnels
    HostName 192.168.1.100
    User jetson
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    LocalForward 3000 localhost:3000
    LocalForward 8000 localhost:8000
    LocalForward 8080 localhost:8080
    LocalForward 11434 localhost:11434
    LocalForward 8888 localhost:8888
    LocalForward 5678 localhost:5678
```

```bash
# [EN WINDOWS POWERSHELL] Activar todos los tunnels con un solo comando:
ssh -N jetson-tunnels
```

### 7.5.5 JupyterLab via SSH tunnel

JupyterLab es ideal para experimentos con PyTorch, exploración de datos y prototipos rápidos en el Jetson:

```bash
# En el Jetson (via terminal de VSCode o SSH):
# Activar el venv llm
source ~/venvs/llm/bin/activate

# Instalar Jupyter si no esta instalado
pip install jupyterlab

# Iniciar JupyterLab sin abrir navegador
jupyter lab --no-browser --port=8888 --ip=127.0.0.1
```

```bash
# Salida esperada -- copie el token (o URL completa):
[I 2026-06-29 11:30:15.123 ServerApp] JupyterLab extension loaded
[I 2026-06-29 11:30:15.456 ServerApp] Jupyter Server is running at:
[I 2026-06-29 11:30:15.457 ServerApp] http://127.0.0.1:8888/lab?token=abc123xyz...
```

```bash
# [EN WINDOWS POWERSHELL] Abrir el tunnel (en otra terminal):
ssh -L 8888:localhost:8888 jetson -N

# Abrir en el navegador de Windows:
# http://localhost:8888/lab?token=abc123xyz... (use el token de la salida anterior)
```

---

## 7.6 Flujo de Trabajo Típico con IDE Remoto

### Caso A — Desarrollo con VSCode (más común)

```bash
1. [Windows] Abrir PowerShell -> ssh jetson (verificar conectividad)
2. [Windows] Abrir VSCode -> Ctrl+Shift+P -> "Remote-SSH: Connect to Host" -> jetson
3. [VSCode remoto] Abrir carpeta del proyecto en el Jetson
4. [VSCode terminal] source ~/venvs/llm/bin/activate
5. [VSCode terminal] start-ollama  (o el alias del motor que necesite)
6. Desarrollar, depurar, iterar -- todo en el Jetson desde la UI de Windows
7. [VSCode terminal] stop-ollama && jetson-clean
```

### Caso B — Tunnel + Navegador para Open WebUI

```bash
1. [Windows PowerShell 1] ssh -L 3000:localhost:3000 jetson -N
2. [Windows PowerShell 2] ssh jetson "start-webui"
3. [Windows Navegador] http://localhost:3000
4. Usar Open WebUI normalmente desde el navegador de Windows
5. [Windows PowerShell 2] ssh jetson "stop-webui"
6. Ctrl+C en PowerShell 1 para cerrar el tunnel
```

---

## 7.7 Aliases para Desarrollo Remoto

Agregue estos aliases en el Jetson para facilitar el flujo de trabajo:

```bash
# Agregar a ~/.bash_aliases en el Jetson
# -------------------------------------------------
# Desarrollo remoto

# Iniciar JupyterLab (el tunnel SSH desde Windows lo hace accesible en :8888)
alias start-jupyter='source ~/venvs/llm/bin/activate && \
  jupyter lab --no-browser --port=8888 --ip=127.0.0.1 2>&1 | \
  grep -E "token=|http://127" | head -3'

alias stop-jupyter='pkill -f "jupyter lab" && echo "JupyterLab detenido"'

# Ver procesos de desarrollo activos
alias dev-status='echo "=== Procesos de desarrollo ===" && \
  pgrep -la "jupyter\|code-server\|python" 2>/dev/null || echo "(ninguno)"'
```

```bash
# Recargar aliases
source ~/.bash_aliases || source ~/.bashrc
```

---

## 7.8 Errores Frecuentes

### [ERROR] "Could not establish connection to jetson" en VSCode

```bash
# Causa: el servidor SSH del Jetson no esta activo, o la IP cambio

# Desde Windows PowerShell, verificar conectividad basica:
ping 192.168.1.100

# Si hay respuesta, intentar SSH directo:
ssh jetson@192.168.1.100

# Si la IP cambio, actualizar ~/.ssh/config en Windows con la nueva IP
```

### [ERROR] "Permission denied (publickey)" al conectar

```bash
# Causa: la clave SSH no esta autorizada en el Jetson

# Verificar que la clave publica esta en el Jetson:
ssh jetson@192.168.1.100 "cat ~/.ssh/authorized_keys"

# Si no esta, agregarla desde Windows PowerShell:
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh jetson@192.168.1.100 "cat >> ~/.ssh/authorized_keys"
```

### [ERROR] "Connection closed by remote host" en el tunnel

```bash
# Causa: el servicio en el Jetson no esta corriendo en el puerto del tunnel

# Verificar que puertos estan activos en el Jetson:
ssh jetson "ss -tlnp | grep -E '3000|8000|8080|11434|8888'"

# Solo puede hacer tunnel a puertos que esten ESCUCHANDO
```

### [ERROR] VSCode Remote tarda 5+ minutos en conectar

```bash
# Causa: el servidor VS Code tiene cache corrupta

# En el Jetson, eliminar el servidor VS Code y reinstalar:
ssh jetson "rm -rf ~/.vscode-server/"
# Reconectar desde VSCode -- se reinstalara automaticamente (~2 min)
```

---

## 7.9 Verificación Final del Capítulo

```bash
# Ejecutar desde Windows PowerShell para verificar todo:
Write-Host "=== Verificacion IDE Remoto ===" -ForegroundColor Cyan

# 1. SSH conectividad
Write-Host "Probando SSH..."
ssh jetson "echo '[OK] SSH activo - $(hostname)'"

# 2. Python version
Write-Host "Python en el Jetson..."
ssh jetson "python3 --version"

# 3. CUDA disponible
Write-Host "CUDA en el Jetson..."
ssh jetson "python3 -c 'import torch; print(\"[OK] CUDA=\"+str(torch.cuda.is_available())+\" GPU=\"+torch.cuda.get_device_name(0)) if torch.cuda.is_available() else print(\"[WARN] CUDA no disponible\")'"
```

```bash
# Salida esperada:
=== Verificacion IDE Remoto ===
Probando SSH...
[OK] SSH activo - jetson-orin
Python en el Jetson...
Python 3.12.3
CUDA en el Jetson...
[OK] CUDA=True GPU=Orin (Ampere)
```

> **CONSEJO:** VSCode Remote SSH guarda el estado de sus conexiones y ventanas abiertas entre sesiones. La próxima vez que abra VSCode, puede reconectar con un clic desde la sección **Remote Explorer** en la barra lateral.
