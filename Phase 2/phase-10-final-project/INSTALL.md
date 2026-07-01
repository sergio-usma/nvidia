# INNOVALABS Studio — Guía de Instalación Completa

## Autonomous Literature Factory v1.0

---

### Hardware certificado

```
Dispositivo:     NVIDIA Jetson AGX Orin Developer Kit 64GB
CPU:             ARMv8 rev 1 (v8l) — 12 cores @ 2.201 GHz
RAM:             62,827 MiB (unificada CPU/GPU)
GPU:             Ampere (2048 CUDA cores, 64 Tensor cores)
Almacenamiento:  NVMe recomendado (mínimo 256 GB libres)
```

### Software base certificado

```
OS:              Ubuntu 22.04.5 LTS (aarch64)
Kernel:          5.15.185-tegra
JetPack:         6.2.2 (nvidia-jetpack 6.2.2+b24)
L4T:             nvidia-l4t-core 36.5.0-20260115194252
CUDA:            12.6 (V12.6.68)
cuDNN:           9.3.0
TensorRT:        10.3.0.30-1+cuda12.5
OpenCV:          4.8.0
```

---

## Índice de la instalación

```
 1. Preparación del sistema operativo
 2. Verificación de JetPack y CUDA
 3. Docker y NVIDIA Container Toolkit
 4. Ollama (servidor de inferencia)
 5. llama.cpp (compilación nativa con CUDA)
 6. Modelos de IA (descarga y verificación)
 7. Python y dependencias del Scout
 8. Node.js y n8n
 9. Google Sheets API (credenciales)
10. Estructura de directorios
11. Docker Compose (stack containerizado)
12. Importación del workflow en n8n
13. Verificación completa del sistema
14. Optimizaciones de rendimiento
15. Mantenimiento y respaldos
16. Modo headless (sin monitor)
17. Dashboard y control remoto (acceso desde Windows)
18. Firewall y seguridad de red local
```

---

## 1. Preparación del sistema operativo

### 1.1. Actualizar paquetes base

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  build-essential \
  cmake \
  git \
  curl \
  wget \
  unzip \
  jq \
  htop \
  tmux \
  tree \
  openssl \
  ca-certificates \
  gnupg \
  lsb-release \
  software-properties-common \
  apt-transport-https
```

### 1.2. Configurar timezone

```bash
sudo timedatectl set-timezone America/Bogota
timedatectl
# Verificar: Time zone: America/Bogota (COT, UTC-5)
```

### 1.3. Configurar swap (recomendado)

El pipeline del Escritor consume ~18 GB de RAM. Aunque la Orin tiene 64 GB,
un swap de respaldo previene OOM kills durante picos inesperados.

```bash
# Crear swap de 16 GB en NVMe (no en eMMC)
sudo fallocate -l 16G /mnt/swapfile
sudo chmod 600 /mnt/swapfile
sudo mkswap /mnt/swapfile
sudo swapon /mnt/swapfile

# Persistir entre reinicios
echo '/mnt/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Reducir swappiness (preferir RAM, swap solo en emergencia)
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.d/99-innovalabs.conf
sudo sysctl -p /etc/sysctl.d/99-innovalabs.conf

# Verificar
free -h
# Swap: 16 GB
```

### 1.4. Configurar límites de archivos abiertos

n8n y Ollama pueden necesitar más file descriptors de los que el default permite.

```bash
cat << 'EOF' | sudo tee -a /etc/security/limits.conf
# INNOVALABS — Límites de procesos
*  soft  nofile  65535
*  hard  nofile  65535
*  soft  nproc   32768
*  hard  nproc   32768
EOF

# Aplicar sin reiniciar
sudo sysctl -w fs.file-max=262144
echo 'fs.file-max=262144' | sudo tee -a /etc/sysctl.d/99-innovalabs.conf
```

---

## 2. Verificación de JetPack y CUDA

Estos componentes ya deben estar instalados con JetPack 6.2.2. Esta sección
solo verifica que todo está operativo.

### 2.1. JetPack

```bash
# Verificar versión
sudo apt list --installed 2>/dev/null | grep nvidia-jetpack
# Esperado: nvidia-jetpack/stable,now 6.2.2+b24 arm64

# Información completa del sistema
jetson_release
# o alternativamente:
cat /etc/nv_tegra_release
```

### 2.2. CUDA Toolkit

```bash
# Verificar nvcc
nvcc --version
# Esperado: Cuda compilation tools, release 12.6, V12.6.68

# Verificar las bibliotecas
ls /usr/local/cuda/lib64/libcudart*
# Esperado: libcudart.so.12.6.68

# Verificar variables de entorno
echo $PATH | tr ':' '\n' | grep cuda
# Esperado: /usr/local/cuda/bin

echo $LD_LIBRARY_PATH | tr ':' '\n' | grep cuda
# Esperado: /usr/local/cuda/lib64
```

Si CUDA no está en el PATH, agregar a `~/.bashrc`:

```bash
cat << 'EOF' >> ~/.bashrc

# ── CUDA (JetPack 6.2.2) ──
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export CUDA_HOME=/usr/local/cuda
EOF
source ~/.bashrc
```

### 2.3. cuDNN

```bash
# Verificar instalación
dpkg -l | grep cudnn
# Esperado: libcudnn9-cuda-12  9.3.0...

# Verificar headers
ls /usr/include/cudnn_version.h
cat /usr/include/cudnn_version.h | grep CUDNN_MAJOR -A2
# Esperado: CUDNN_MAJOR 9, CUDNN_MINOR 3
```

### 2.4. TensorRT

```bash
dpkg -l | grep tensorrt
# Esperado: tensorrt 10.3.0.30-1+cuda12.5

# Verificar binario
trtexec --help 2>&1 | head -3
```

### 2.5. Test rápido de GPU

```bash
# Dispositivos CUDA visibles
/usr/local/cuda/extras/demo_suite/deviceQuery
# Esperado: Device 0: "Orin" ... Result = PASS

# Monitoreo en tiempo real
sudo tegrastats
# Ctrl+C para salir
```

---

## 3. Docker y NVIDIA Container Toolkit

### 3.1. Instalar Docker

```bash
# Si Docker no está instalado
sudo apt install -y docker.io docker-compose-plugin

# Agregar usuario actual al grupo docker (evita usar sudo)
sudo usermod -aG docker $USER

# IMPORTANTE: cerrar sesión y volver a entrar para que tome efecto
# o ejecutar temporalmente:
newgrp docker

# Verificar
docker --version
# Esperado: Docker version 24.x+

docker compose version
# Esperado: Docker Compose version v2.x+
```

### 3.2. Instalar NVIDIA Container Toolkit

JetPack 6.2.2 debería incluirlo, pero verificar y reinstalar si es necesario:

```bash
# Verificar si ya está instalado
dpkg -l | grep nvidia-container
# Si aparece nvidia-container-toolkit → ya está instalado

# Si NO está instalado:
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
```

### 3.3. Configurar Docker para usar el runtime NVIDIA

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verificar que el runtime está registrado
docker info | grep -i runtime
# Esperado: Runtimes: nvidia runc
```

### 3.4. Test de GPU en Docker

```bash
docker run --rm --runtime=nvidia nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
# Esperado: tabla con la GPU Orin y CUDA 12.6
```

Si el test falla con un error de arquitectura (la imagen oficial de CUDA
puede no tener build para aarch64), usar esta alternativa:

```bash
docker run --rm --runtime=nvidia \
  --device /dev/nvhost-ctrl \
  --device /dev/nvhost-ctrl-gpu \
  --device /dev/nvmap \
  ubuntu:22.04 bash -c "
    apt-get update && apt-get install -y nvidia-utils-535 2>/dev/null
    nvidia-smi 2>/dev/null || echo 'GPU accessible via /dev/nv*'
    ls /dev/nv* 2>/dev/null
  "
```

### 3.5. Configurar Docker daemon para la Orin

```bash
cat << 'EOF' | sudo tee /etc/docker/daemon.json
{
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "args": []
    }
  },
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "default-address-pools": [
    { "base": "172.20.0.0/16", "size": 24 }
  ]
}
EOF

sudo systemctl restart docker
```

---

## 4. Ollama (servidor de inferencia)

### 4.1. Instalar Ollama

Opción A — Instalación nativa (recomendada para la Orin):

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Verificar
ollama --version
# Esperado: ollama version 0.x.x

# El servicio se inicia automáticamente
sudo systemctl status ollama
```

Opción B — Vía Docker (usado por el docker-compose.yml):

```bash
# Se levanta automáticamente con docker compose up
# El compose ya incluye la configuración completa
docker pull ollama/ollama:latest
```

### 4.2. Configurar Ollama para carga secuencial

Crear el archivo de configuración del servicio:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d/

cat << 'EOF' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
# Máximo 1 modelo en VRAM simultáneamente
Environment="OLLAMA_MAX_LOADED_MODELS=1"

# Descargar modelo de VRAM tras 2 minutos sin uso
Environment="OLLAMA_KEEP_ALIVE=2m"

# Escuchar en todas las interfaces (para acceso desde Docker)
Environment="OLLAMA_HOST=0.0.0.0:11434"

# No purgear modelos no usados automáticamente
Environment="OLLAMA_NOPRUNE=true"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 4.3. Verificar la API

```bash
curl -s http://localhost:11434/api/tags | jq .
# Esperado: JSON con lista de modelos (vacía si no hay modelos descargados)
```

---

## 5. llama.cpp (compilación nativa con CUDA)

El agente Escritor (Qwen3.5-27B) se ejecuta via llama-cli porque necesita
control fino sobre parámetros de generación que la API de Ollama no expone.

### 5.1. Clonar y compilar

```bash
cd ~
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Compilar con soporte CUDA para aarch64
cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES="87" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA_F16=ON

# -DCMAKE_CUDA_ARCHITECTURES="87" → Ampere (Orin)
# -DGGML_CUDA_F16=ON → Habilitar FP16 nativo en Orin

cmake --build build --config Release -j$(nproc)
```

NOTA: La compilación en la Orin tarda ~10-15 minutos con los 12 cores.

### 5.2. Instalar el binario

```bash
# Copiar a un directorio en el PATH
sudo cp build/bin/llama-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/llama-cli

# Verificar
llama-cli --version
# Esperado: version: XXXX (build hash)

# Verificar soporte CUDA
llama-cli --help 2>&1 | grep -i "ngl\|gpu\|cuda"
# Debe mostrar la opción -ngl (number of GPU layers)
```

### 5.3. CMAKE_CUDA_ARCHITECTURES de referencia

| Dispositivo | Arquitectura | Valor |
|-------------|-------------|-------|
| Jetson AGX Orin | Ampere | `87` |
| Jetson Orin Nano | Ampere | `87` |
| Jetson AGX Xavier | Volta | `72` |
| RTX 3090 | Ampere | `86` |
| RTX 4090 | Ada Lovelace | `89` |

---

## 6. Modelos de IA (descarga y verificación)

### 6.1. Modelos de Ollama (3 agentes)

```bash
# Agente Estratega — síntesis tema/moraleja (~4 GB)
ollama pull glm-4.7-flash:latest

# Agente Arquitecto — blueprint 12 pasos (~6 GB)
ollama pull deepseek-r1:8b

# Agente Editor — corrección gramatical (~5 GB)
ollama pull nemotron-3-nano:latest

# Verificar todos los modelos descargados
ollama list
```

Salida esperada:

```
NAME                       ID            SIZE     MODIFIED
glm-4.7-flash:latest       xxxxxxxxxxxx  2.8 GB   ...
deepseek-r1:8b             xxxxxxxxxxxx  4.9 GB   ...
nemotron-3-nano:latest     xxxxxxxxxxxx  3.1 GB   ...
```

### 6.2. Test funcional de cada modelo

```bash
# Estratega
curl -s http://localhost:11434/api/generate -d '{
  "model": "glm-4.7-flash:latest",
  "prompt": "Responde solo con un JSON: {\"test\": \"ok\"}",
  "stream": false
}' | jq -r '.response'

# Arquitecto
curl -s http://localhost:11434/api/generate -d '{
  "model": "deepseek-r1:8b",
  "prompt": "Responde solo con un JSON: {\"test\": \"ok\"}",
  "stream": false
}' | jq -r '.response'

# Editor
curl -s http://localhost:11434/api/generate -d '{
  "model": "nemotron-3-nano:latest",
  "prompt": "Responde solo con un JSON: {\"test\": \"ok\"}",
  "stream": false
}' | jq -r '.response'
```

NOTA: La primera invocación de cada modelo tarda 30-60 segundos mientras
se cargan los tensores en la VRAM. Las siguientes son rápidas.

### 6.3. Modelo GGUF — Qwen3.5-27B (agente Escritor)

```bash
# Crear directorio de modelos
mkdir -p ~/.cache/llama.cpp

# Instalar el CLI de Hugging Face
pip install huggingface-hub

# Descargar el modelo cuantizado Q4 (~16 GB)
huggingface-cli download \
  unsloth/Qwen3.5-27B-GGUF \
  Qwen3.5-27B-UD-Q4_K_XL.gguf \
  --local-dir ~/.cache/llama.cpp \
  --local-dir-use-symlinks False
```

NOTA: La descarga de ~16 GB puede tardar 20-60 minutos según la conexión.

### 6.4. Verificar el modelo GGUF

```bash
# Verificar que el archivo existe y tiene el tamaño correcto
ls -lh ~/.cache/llama.cpp/Qwen3.5-27B-UD-Q4_K_XL.gguf
# Esperado: ~16-17 GB

# Renombrar al nombre que espera el workflow
cd ~/.cache/llama.cpp
mv Qwen3.5-27B-UD-Q4_K_XL.gguf \
   unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf

# Test rápido (genera solo 50 tokens para verificar que funciona)
llama-cli \
  -m ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf \
  -ngl 999 \
  -c 512 \
  -n 50 \
  -p "Hola, soy un test. Responde brevemente: /no_think" \
  2>/dev/null

# Si ves texto generado → el modelo y CUDA funcionan correctamente
```

### 6.5. Resumen de espacio en disco

| Componente | Tamaño | Ubicación |
|------------|--------|-----------|
| Modelos Ollama (3) | ~11 GB | `~/.ollama/models/` |
| Qwen3.5-27B GGUF | ~16 GB | `~/.cache/llama.cpp/` |
| llama.cpp (compilado) | ~500 MB | `~/llama.cpp/build/` |
| Docker images | ~5 GB | `/var/lib/docker/` |
| **Total estimado** | **~33 GB** | |

---

## 7. Python y dependencias del Scout

### 7.1. Verificar Python

```bash
python3 --version
# Esperado: Python 3.10.x (incluido en Ubuntu 22.04)
```

### 7.2. Instalar pip si no está presente

```bash
sudo apt install -y python3-pip python3-venv
```

### 7.3. Crear entorno virtual dedicado

```bash
python3 -m venv /opt/innovalabs/venv

# Activar
source /opt/innovalabs/venv/bin/activate

# Instalar dependencias del Scout
pip install --upgrade pip
pip install \
  pytrends==4.9.2 \
  requests>=2.28.0 \
  pandas>=1.5.0

# Verificar
python3 -c "from pytrends.request import TrendReq; print('pytrends OK')"

# Desactivar
deactivate
```

### 7.4. Script de activación rápida

```bash
cat << 'EOF' > /opt/innovalabs/scripts/activate_env.sh
#!/bin/bash
# Activar el entorno virtual de INNOVALABS
source /opt/innovalabs/venv/bin/activate
EOF
chmod +x /opt/innovalabs/scripts/activate_env.sh
```

El nodo Execute Command de n8n debe invocar el Scout así:

```bash
source /opt/innovalabs/venv/bin/activate && python3 /opt/innovalabs/scripts/scout_trends.py
```

---

## 8. Node.js y n8n

### 8.1. Instalar Node.js 20 LTS (aarch64)

```bash
# Repositorio oficial de NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar
node --version
# Esperado: v20.x.x

npm --version
# Esperado: 10.x.x
```

### 8.2. Instalar n8n globalmente

```bash
npm install -g n8n

# Verificar
n8n --version
# Esperado: 1.x.x
```

### 8.3. Configurar n8n como servicio systemd

```bash
cat << 'EOF' | sudo tee /etc/systemd/system/n8n.service
[Unit]
Description=INNOVALABS n8n Workflow Orchestrator
After=network.target ollama.service docker.service
Wants=ollama.service

[Service]
Type=simple
User=USER_ACTUAL
Group=USER_ACTUAL

# Directorio de trabajo
WorkingDirectory=/opt/innovalabs

# Variables de entorno
Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=http"
Environment="GENERIC_TIMEZONE=America/Bogota"
Environment="TZ=America/Bogota"
Environment="N8N_DEFAULT_BINARY_DATA_MODE=filesystem"
Environment="N8N_DEFAULT_EXECUTION_TIMEOUT=1800"
Environment="N8N_MAX_EXECUTION_TIMEOUT=3600"
Environment="N8N_BASIC_AUTH_ACTIVE=true"
Environment="N8N_BASIC_AUTH_USER=admin"
Environment="N8N_BASIC_AUTH_PASSWORD=CAMBIAR_ESTA_CONTRASEÑA"
Environment="N8N_ENCRYPTION_KEY=GENERAR_CON_openssl_rand_hex_32"

# PATH incluye node, python, llama-cli, docker
Environment="PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/cuda/bin"
Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64"

ExecStart=/usr/bin/n8n start
Restart=always
RestartSec=10

# Límites de recursos
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

# IMPORTANTE: reemplazar USER_ACTUAL con tu nombre de usuario
sudo sed -i "s/USER_ACTUAL/$USER/g" /etc/systemd/system/n8n.service

# Generar encryption key
N8N_KEY=$(openssl rand -hex 32)
sudo sed -i "s/GENERAR_CON_openssl_rand_hex_32/$N8N_KEY/" /etc/systemd/system/n8n.service
echo "Encryption key generada. Guardar en un lugar seguro: $N8N_KEY"

# Habilitar y arrancar
sudo systemctl daemon-reload
sudo systemctl enable n8n
sudo systemctl start n8n

# Verificar
sudo systemctl status n8n
# Esperado: active (running)

# Logs
journalctl -u n8n -f --no-pager
```

### 8.4. Verificar acceso web

```bash
curl -s http://localhost:5678/healthz
# Esperado: {"status":"ok"}
```

Abrir en el navegador: `http://<IP_DE_TU_JETSON>:5678`

---

## 9. Google Sheets API (credenciales)

### 9.1. Crear proyecto en Google Cloud Console

1. Ir a https://console.cloud.google.com/
2. Crear un nuevo proyecto: `INNOVALABS-Factory`
3. Habilitar la API: **Google Sheets API**
4. Habilitar la API: **Google Drive API** (requerida por n8n para listar archivos)

### 9.2. Crear credenciales OAuth2

1. En APIs & Services → Credentials → Create Credentials → OAuth Client ID
2. Tipo: **Web application**
3. Nombre: `n8n-innovalabs`
4. Authorized redirect URIs:
   - `http://localhost:5678/rest/oauth2-credential/callback`
   - `http://<IP_JETSON>:5678/rest/oauth2-credential/callback`
5. Descargar el JSON de credenciales

### 9.3. Crear el Spreadsheet

1. Crear un nuevo Google Spreadsheet
2. Renombrar la primera hoja a exactamente: `Queue_Historias`
3. En la fila 1, escribir los headers (uno por celda):

```
ID | Fecha | Tema | Contexto | Estado | Path_Archivo | Moraleja | Blueprint_JSON | Error_Log
```

4. Copiar el **Spreadsheet ID** de la URL:
   `https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit`

### 9.4. Configurar credenciales en n8n

1. Abrir n8n: `http://localhost:5678`
2. Ir a Settings → Credentials → Add Credential
3. Seleccionar: **Google Sheets OAuth2 API**
4. Pegar el Client ID y Client Secret del paso 9.2
5. Hacer clic en **Connect** y autorizar el acceso
6. Guardar la credencial

---

## 10. Estructura de directorios

### 10.1. Crear la estructura completa

```bash
# Directorio raíz del proyecto
sudo mkdir -p /opt/innovalabs/{scripts,config,logs}

# Directorio de salida de historias
sudo mkdir -p /var/opt/innovalabs/historias

# Directorio de trabajo temporal
sudo mkdir -p /tmp/innovalabs

# Asignar permisos al usuario actual
sudo chown -R $USER:$USER /opt/innovalabs
sudo chown -R $USER:$USER /var/opt/innovalabs
```

### 10.2. Árbol de archivos esperado

```
/opt/innovalabs/
├── scripts/
│   ├── scout_trends.py          ← Extractor de tendencias (Fase 1)
│   ├── writer_bridge.sh         ← Puente n8n → llama-cli (Fase 3)
│   └── activate_env.sh          ← Activar venv de Python
├── config/
│   ├── docker-compose.yml       ← Stack Docker (si se usa)
│   ├── .env                     ← Variables de entorno
│   └── .env.example             ← Plantilla de referencia
├── logs/                        ← Logs de operación
└── venv/                        ← Entorno virtual Python

/var/opt/innovalabs/
└── historias/
    ├── Historia_H-1710432000000.md
    ├── Historia_H-1710453600000.md
    └── ...

~/.cache/llama.cpp/
└── unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf

~/.ollama/
└── models/
    ├── manifests/
    └── blobs/
```

### 10.3. Copiar los archivos del proyecto

```bash
# Copiar scripts
cp scout_trends.py /opt/innovalabs/scripts/
cp writer_bridge.sh /opt/innovalabs/scripts/
chmod +x /opt/innovalabs/scripts/*.sh

# Copiar configuración Docker (si se usa el modo containerizado)
cp docker-compose.yml /opt/innovalabs/config/
cp .env.example /opt/innovalabs/config/
cp .env.example /opt/innovalabs/config/.env
cp setup.sh /opt/innovalabs/config/
chmod +x /opt/innovalabs/config/setup.sh

# Copiar verificador del sistema
cp verify_system.sh /opt/innovalabs/scripts/
chmod +x /opt/innovalabs/scripts/verify_system.sh
```

---

## 11. Docker Compose (stack containerizado)

Esta sección es OPCIONAL. Si prefieres correr n8n y Ollama de forma nativa
(secciones 4 y 8), puedes omitir este paso.

### 11.1. Preparar el archivo .env

```bash
cd /opt/innovalabs/config

# Ejecutar el script de setup que valida el entorno y genera .env
./setup.sh

# O si prefieres configurar manualmente:
nano .env
```

Variables críticas a configurar:

```bash
# Copiar el ID de tu Google Spreadsheet
GSHEETS_SPREADSHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz_1234567890

# Verificar que las rutas existen
ls -la $(grep LLAMA_CLI_PATH .env | cut -d= -f2)
ls -la $(grep LLAMA_MODELS_DIR .env | cut -d= -f2)

# Generar encryption key para n8n
openssl rand -hex 32
# Pegar el resultado en N8N_ENCRYPTION_KEY

# Cambiar la contraseña por defecto
# N8N_BASIC_AUTH_PASSWORD=tu_contraseña_segura
```

### 11.2. Levantar el stack

```bash
cd /opt/innovalabs/config

# Primer arranque (descarga imágenes)
docker compose up -d

# Monitorear el arranque
docker compose logs -f
# Ctrl+C cuando los 3 servicios estén healthy

# Verificar estado
docker compose ps
```

Salida esperada:

```
NAME                  STATUS                   PORTS
innovalabs-ollama     Up (healthy)             0.0.0.0:11434->11434/tcp
innovalabs-writer     Up                       
innovalabs-n8n        Up (healthy)             0.0.0.0:5678->5678/tcp
```

### 11.3. Test de conectividad entre servicios

```bash
# n8n puede llegar a Ollama
docker exec innovalabs-n8n wget -qO- http://ollama:11434/api/tags

# n8n puede hacer exec al Writer
docker exec innovalabs-n8n docker exec innovalabs-writer echo "Bridge OK"

# Writer tiene acceso a GPU
docker exec innovalabs-writer ls /usr/local/cuda/lib64/libcudart*

# Writer tiene acceso al modelo
docker exec innovalabs-writer ls -lh /models/*.gguf

# Volumen compartido funciona
docker exec innovalabs-writer touch /shared/test_file
docker exec innovalabs-n8n ls /shared/test_file
docker exec innovalabs-writer rm /shared/test_file
```

---

## 12. Importación del workflow en n8n

### 12.1. Importar el JSON

1. Abrir n8n: `http://localhost:5678`
2. Menú lateral → Workflows → Import from File
3. Seleccionar: `INNOVALABS_Literature_Factory_v1.0.json`

### 12.2. Configurar el Spreadsheet ID

Dentro del workflow importado, hay 6 nodos de Google Sheets.
En cada uno, reemplazar el Spreadsheet ID:

Nodos a editar:
- `📋 Sheets — Append Queue`
- `📖 Sheets — Leer PENDING`
- `🔒 Sheets — Lock PROCESSING`
- `✅ Sheets — COMPLETED`
- `❌ Sheets — FAILED`

En cada nodo: abrir → campo Document → pegar tu Spreadsheet ID.

### 12.3. Asignar credenciales

Cada nodo de Google Sheets necesita la credencial OAuth2 configurada
en la sección 9. Seleccionarla en el dropdown "Credential" de cada nodo.

### 12.4. Ajustar rutas del Scout

Nodo `🔍 Scout — Extraer Tendencias`:
- Si usas venv:
  ```
  source /opt/innovalabs/venv/bin/activate && python3 /opt/innovalabs/scripts/scout_trends.py
  ```
- Si usas Docker:
  ```
  docker exec innovalabs-writer python3 /opt/innovalabs/scripts/scout_trends.py
  ```

### 12.5. Configurar concurrencia global

En el workflow → Settings (icono de engranaje) → verificar:
- **Error Workflow:** seleccionar el sub-flujo de errores
- **Timezone:** America/Bogota
- **Max Concurrency:** 1 (CRÍTICO — evita colisiones de VRAM)

### 12.6. Activar el workflow

Toggle "Active" en la esquina superior derecha del editor de n8n.
El Cron disparará la primera ejecución a la siguiente hora múltiplo de 6
(00:00, 06:00, 12:00 o 18:00 COT).

### 12.7. Test manual

Antes de esperar al Cron, ejecutar manualmente:
1. Hacer clic en "Execute Workflow" en el editor de n8n
2. Observar el progreso nodo por nodo
3. Verificar que Google Sheets se actualiza
4. Verificar que el archivo .md se genera en `/var/opt/innovalabs/historias/`

---

## 13. Verificación completa del sistema

Ejecutar esta lista de verificación después de completar la instalación.

### 13.1. Script de verificación automatizada

```bash
#!/bin/bash
echo "═══ INNOVALABS — Verificación del sistema ═══"

PASS=0; FAIL=0
check() {
  if eval "$2" > /dev/null 2>&1; then
    echo "  ✓ $1"; ((PASS++))
  else
    echo "  ✗ $1"; ((FAIL++))
  fi
}

echo ""
echo "── Hardware y OS ──"
check "Arquitectura aarch64"         '[[ "$(uname -m)" == "aarch64" ]]'
check "Ubuntu 22.04"                 'lsb_release -d | grep -q "22.04"'
check "Kernel tegra"                 'uname -r | grep -q tegra'
check "RAM >= 60GB"                  '[[ $(free -m | awk "/Mem:/{print \$2}") -ge 60000 ]]'
check "Swap configurado"            '[[ $(free -m | awk "/Swap:/{print \$2}") -ge 1000 ]]'

echo ""
echo "── NVIDIA / CUDA ──"
check "JetPack 6.2.2"               'dpkg -l | grep -q "nvidia-jetpack.*6.2.2"'
check "CUDA 12.6"                    'nvcc --version 2>&1 | grep -q "12.6"'
check "cuDNN 9.3"                    'cat /usr/include/cudnn_version.h 2>/dev/null | grep -q "CUDNN_MAJOR 9"'
check "/usr/local/cuda existe"       'test -d /usr/local/cuda'
check "CUDA en PATH"                 'which nvcc'

echo ""
echo "── Docker ──"
check "Docker instalado"             'docker --version'
check "Docker Compose V2"            'docker compose version'
check "NVIDIA runtime"               'docker info 2>/dev/null | grep -q nvidia'
check "Docker socket accesible"      'test -S /var/run/docker.sock'

echo ""
echo "── Ollama ──"
check "Ollama instalado"             'which ollama || docker inspect innovalabs-ollama'
check "API respondiendo"             'curl -sf http://localhost:11434/api/tags'
check "glm-4.7-flash descargado"     'ollama list 2>/dev/null | grep -q "glm-4.7-flash"'
check "deepseek-r1:8b descargado"    'ollama list 2>/dev/null | grep -q "deepseek-r1"'
check "nemotron-3-nano descargado"   'ollama list 2>/dev/null | grep -q "nemotron-3-nano"'

echo ""
echo "── llama.cpp ──"
check "llama-cli en PATH"            'which llama-cli'
check "Modelo GGUF presente"         'test -f ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf'

echo ""
echo "── Python ──"
check "Python 3.10+"                 'python3 --version 2>&1 | grep -qE "3\.(1[0-9]|[2-9][0-9])"'
check "pytrends instalado"           'python3 -c "import pytrends" 2>/dev/null || source /opt/innovalabs/venv/bin/activate && python3 -c "import pytrends"'

echo ""
echo "── n8n ──"
check "n8n instalado"                'which n8n || docker inspect innovalabs-n8n'
check "n8n respondiendo"             'curl -sf http://localhost:5678/healthz'

echo ""
echo "── Estructura de archivos ──"
check "scout_trends.py"              'test -f /opt/innovalabs/scripts/scout_trends.py'
check "Directorio de historias"      'test -d /var/opt/innovalabs/historias'
check "Permisos correctos"           'test -w /var/opt/innovalabs/historias'

echo ""
echo "═══════════════════════════════════"
echo "  Resultado: $PASS pasaron, $FAIL fallaron"
echo "═══════════════════════════════════"
```

Guardar como `/opt/innovalabs/scripts/verify_system.sh` y ejecutar:

```bash
chmod +x /opt/innovalabs/scripts/verify_system.sh
bash /opt/innovalabs/scripts/verify_system.sh
```

---

## 14. Optimizaciones de rendimiento

### 14.1. Modo de potencia MAXN

La Orin tiene varios perfiles de energía. Para máximo rendimiento:

```bash
# Ver modo actual
sudo nvpmodel -q

# Establecer modo MAXN (máxima potencia)
sudo nvpmodel -m 0

# Maximizar frecuencias de todos los cores
sudo jetson_clocks

# Verificar frecuencias
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
# Todos deberían marcar ~2201600 (2.2 GHz)
```

Persistir entre reinicios:

```bash
cat << 'EOF' | sudo tee /etc/systemd/system/jetson-maxperf.service
[Unit]
Description=Set Jetson to maximum performance mode
After=nvpmodel.service

[Service]
Type=oneshot
ExecStart=/usr/bin/nvpmodel -m 0
ExecStartPost=/usr/bin/jetson_clocks
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable jetson-maxperf
```

### 14.2. Configuración de memoria de GPU

Verificar que la partición GPU/CPU de la memoria unificada
está configurada para maximizar la disponibilidad para inferencia:

```bash
# Ver asignación actual de memoria de GPU
cat /sys/devices/platform/bus@0/17000000.gpu/devfreq/17000000.gpu/cur_freq

# Ver memoria utilizable
cat /proc/meminfo | grep -E "MemTotal|MemAvailable|SwapTotal"
```

### 14.3. Desactivar servicios innecesarios

```bash
# Desactivar escritorio gráfico si la Orin se usa headless
sudo systemctl set-default multi-user.target
sudo systemctl disable gdm3 2>/dev/null

# Desactivar Bluetooth si no se necesita
sudo systemctl disable bluetooth

# Desactivar servicios de impresión
sudo systemctl disable cups cups-browsed 2>/dev/null

# Libera ~800 MB - 1.5 GB de RAM
```

### 14.4. Parámetros de kernel para inferencia

```bash
cat << 'EOF' | sudo tee -a /etc/sysctl.d/99-innovalabs.conf

# Preferir mantener datos de aplicaciones en RAM (no caché de filesystem)
vm.vfs_cache_pressure=50

# No matar procesos OOM hasta agotar swap
vm.overcommit_memory=0
vm.overcommit_ratio=95

# Permitir más memoria mapeada (necesario para modelos grandes)
vm.max_map_count=262144
EOF

sudo sysctl -p /etc/sysctl.d/99-innovalabs.conf
```

---

## 15. Mantenimiento y respaldos

### 15.1. Respaldo de credenciales y configuración

```bash
# Crear respaldo
BACKUP_DIR="/opt/innovalabs/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Credenciales de n8n (encriptadas)
cp -r ~/.n8n "$BACKUP_DIR/n8n_data"

# Configuración
cp /opt/innovalabs/config/.env "$BACKUP_DIR/"
cp /etc/systemd/system/n8n.service "$BACKUP_DIR/"
cp /etc/systemd/system/ollama.service.d/override.conf "$BACKUP_DIR/"

# Listar
echo "Respaldo creado en: $BACKUP_DIR"
ls -la "$BACKUP_DIR"
```

### 15.2. Respaldo de historias generadas

```bash
# Comprimir historias semanalmente
cd /var/opt/innovalabs/historias
tar -czf "/opt/innovalabs/backups/historias_$(date +%Y%m%d).tar.gz" *.md

# Cron para respaldo automático (domingos a las 3 AM)
(crontab -l 2>/dev/null; echo '0 3 * * 0 cd /var/opt/innovalabs/historias && tar -czf /opt/innovalabs/backups/historias_$(date +\%Y\%m\%d).tar.gz *.md') | crontab -
```

### 15.3. Limpieza de archivos temporales

```bash
# Limpiar archivos temporales del Writer (mayores a 7 días)
find /tmp/innovalabs -type f -mtime +7 -delete 2>/dev/null
find /tmp/historia_* -type f -mtime +7 -delete 2>/dev/null

# Limpiar logs de Docker
docker system prune -f --volumes 2>/dev/null
```

### 15.4. Actualización de modelos

```bash
# Actualizar modelos de Ollama (cuando haya nuevas versiones)
ollama pull glm-4.7-flash:latest
ollama pull deepseek-r1:8b
ollama pull nemotron-3-nano:latest

# Limpiar versiones antiguas
ollama rm glm-4.7-flash:versión_antigua  # si aplica
```

### 15.5. Monitoreo de salud del sistema

```bash
# Agregar al crontab — verificación cada hora
cat << 'CRONEOF' >> /tmp/innovalabs_cron
# INNOVALABS — Health check cada hora
0 * * * * curl -sf http://localhost:11434/api/tags > /dev/null || sudo systemctl restart ollama
0 * * * * curl -sf http://localhost:5678/healthz > /dev/null || sudo systemctl restart n8n
CRONEOF
crontab /tmp/innovalabs_cron
rm /tmp/innovalabs_cron
```

---

## Resumen de puertos y servicios

| Servicio | Puerto | Protocolo | Acceso |
|----------|--------|-----------|--------|
| n8n (UI + API) | 5678 | HTTP | `http://localhost:5678` |
| Ollama API | 11434 | HTTP | `http://localhost:11434` |
| Writer | — | docker exec | Interno (sin puerto) |

---

## Resumen de consumo de recursos por ciclo

| Fase | Modelo | RAM Pico | GPU | Duración |
|------|--------|----------|-----|----------|
| Scout | pytrends (Python) | < 100 MB | No | 10-30s |
| Estratega | glm-4.7-flash | ~4 GB | Sí | 30-120s |
| Arquitecto | deepseek-r1:8b | ~6 GB | Sí | 60-180s |
| Escritor | Qwen3.5-27B Q4 | ~18 GB | Sí | 15-30 min |
| Editor | nemotron-3-nano | ~5 GB | Sí | 60-180s |
| **Total** | | **~18 GB pico** | | **~20-35 min** |

RAM libre estimada durante ejecución: ~44 GB (62 - 18 pico del Escritor).

---

## Orden de arranque recomendado

```
1.  Jetson AGX Orin (boot)
2.  jetson-maxperf.service          → Modo MAXN + jetson_clocks
3.  Docker daemon                   → Automático
4.  Ollama (nativo o Docker)        → Carga modelos bajo demanda
5.  n8n (nativo o Docker)           → Espera a que Ollama esté healthy
6.  innovalabs-dashboard.service    → Dashboard web en :8080
7.  Cron 6h → Pipeline automático
```

Con systemd y `depends_on` (Docker) o `After=` (nativo), este orden
se mantiene automáticamente entre reinicios.

---

## 16. Modo headless (sin monitor)

La Jetson operará 24/7 sin monitor, teclado ni mouse conectados.
Todo el acceso será vía red desde tu PC con Windows.

### 16.1. Desactivar el escritorio gráfico

```bash
# Cambiar el target de arranque de gráfico a solo texto
sudo systemctl set-default multi-user.target

# Desactivar GDM (display manager)
sudo systemctl disable gdm3 2>/dev/null
sudo systemctl disable lightdm 2>/dev/null

# Detener el escritorio inmediatamente (sin reiniciar)
sudo systemctl stop gdm3 2>/dev/null
sudo systemctl stop lightdm 2>/dev/null

# Verificar
systemctl get-default
# Esperado: multi-user.target
```

Esto libera ~800 MB - 1.5 GB de RAM que estaba consumiendo
el entorno gráfico (GNOME/Ubuntu Desktop).

Para restaurar el escritorio temporalmente (ej: si conectas monitor):

```bash
sudo systemctl start gdm3
```

### 16.2. Configurar SSH

```bash
# Instalar OpenSSH server (si no está instalado)
sudo apt install -y openssh-server

# Habilitar y arrancar
sudo systemctl enable ssh
sudo systemctl start ssh

# Verificar
sudo systemctl status ssh
# Esperado: active (running)

# Ver la IP de la Jetson
hostname -I
# Ejemplo: 192.168.1.50
```

### 16.3. Conexión SSH desde Windows

Opción A — Terminal integrada de Windows (PowerShell o CMD):

```powershell
ssh usuario@192.168.1.50
```

Opción B — Windows Terminal (recomendado):

Instalar desde Microsoft Store → "Windows Terminal".
Abrir PowerShell y conectar con:

```powershell
ssh usuario@192.168.1.50
```

Opción C — PuTTY (interfaz gráfica):

Descargar de https://www.putty.org/ → Ingresar IP → Connect.

### 16.4. Configurar clave SSH (sin contraseña)

Desde tu PC Windows (PowerShell):

```powershell
# Generar clave SSH (si no tienes una)
ssh-keygen -t ed25519 -C "innovalabs-jetson"

# Copiar la clave pública a la Jetson
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh usuario@192.168.1.50 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Verificar que la conexión funciona sin contraseña:

```powershell
ssh usuario@192.168.1.50 "echo 'Conexión sin contraseña OK'"
```

### 16.5. Asignar IP fija en la red local

Para que la IP de la Jetson no cambie entre reinicios:

Opción A — Reserva DHCP en el router (recomendado):

1. Abrir la configuración de tu router (usualmente `192.168.1.1`)
2. Buscar "DHCP Reservations" o "Address Reservation"
3. Agregar la MAC de la Jetson con la IP deseada (ej: `192.168.1.50`)
4. La MAC se obtiene con: `ip link show eth0 | grep ether`

Opción B — IP estática en la Jetson via Netplan:

```bash
# Identificar la interfaz de red
ip addr show
# Buscar la interfaz activa (eth0, enp1s0, etc.)

# Crear configuración de Netplan
sudo nano /etc/netplan/01-static-ip.yaml
```

Contenido del archivo (ajustar según tu red):

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:                          # Cambiar por tu interfaz real
      dhcp4: no
      addresses:
        - 192.168.1.50/24          # IP deseada para la Jetson
      routes:
        - to: default
          via: 192.168.1.1         # IP de tu router
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

```bash
# Aplicar
sudo netplan apply

# Verificar
ip addr show eth0
ping -c 3 8.8.8.8
```

### 16.6. Configurar hostname descriptivo

```bash
sudo hostnamectl set-hostname innovalabs-jetson

# Agregar al /etc/hosts
echo "127.0.0.1 innovalabs-jetson" | sudo tee -a /etc/hosts

# Verificar
hostname
# Esperado: innovalabs-jetson
```

Desde Windows podrás conectar con:

```powershell
ssh usuario@innovalabs-jetson.local
```

(Funciona si tu red soporta mDNS. Si no, usar la IP directamente.)

### 16.7. Acceso a consola serie (fallback de emergencia)

Si la red falla y necesitas acceso de emergencia, la Orin Dev Kit tiene
un puerto micro-USB para consola serie:

1. Conectar cable micro-USB del puerto Debug de la Orin a tu Windows
2. Instalar driver FTDI: https://ftdichip.com/drivers/vcp-drivers/
3. Abrir PuTTY → Serial → COM port detectado → Baud: 115200
4. Tendrás una terminal de login directa

### 16.8. Wake-on-LAN (opcional)

Si quieres encender la Jetson remotamente desde Windows:

```bash
# En la Jetson — habilitar WoL
sudo ethtool -s eth0 wol g
# Persistir en /etc/network/interfaces o via script de arranque
```

Desde Windows (PowerShell):

```powershell
# Instalar herramienta WoL
# Usando la MAC de la Jetson (ejemplo: aa:bb:cc:dd:ee:ff)
# Hay varias herramientas gratuitas de WoL para Windows (WakeMeOnLan, etc.)
```

---

## 17. Dashboard y control remoto (acceso desde Windows)

Un servidor web ligero (FastAPI) que corre en la Jetson y permite
monitorear y controlar todo el sistema desde el navegador de Windows.

### 17.1. Instalar dependencias del dashboard

```bash
# Activar el entorno virtual
source /opt/innovalabs/venv/bin/activate

# Instalar FastAPI + Uvicorn
pip install \
  fastapi==0.115.0 \
  uvicorn[standard]==0.30.0 \
  pydantic>=2.0

# Verificar
python3 -c "import fastapi; print('FastAPI', fastapi.__version__)"
# Esperado: FastAPI 0.115.0

deactivate
```

### 17.2. Copiar archivos del dashboard

```bash
# Crear directorio del dashboard
sudo mkdir -p /opt/innovalabs/dashboard/templates

# Copiar archivos
cp dashboard/server.py /opt/innovalabs/dashboard/
cp dashboard/templates/index.html /opt/innovalabs/dashboard/templates/
cp dashboard/templates/factory.html /opt/innovalabs/dashboard/templates/

# Verificar estructura
tree /opt/innovalabs/dashboard/
# /opt/innovalabs/dashboard/
# ├── server.py
# └── templates/
#     ├── factory.html    ← Vista pixel-art de la fábrica
#     └── index.html      ← Dashboard técnico de métricas
```

### 17.3. Test rápido manual

```bash
source /opt/innovalabs/venv/bin/activate
cd /opt/innovalabs/dashboard
python3 server.py --port 8080
```

Desde tu PC Windows, abrir el navegador en:

```
http://192.168.1.50:8080
```

(Reemplazar `192.168.1.50` con la IP real de tu Jetson.)

Deberías ver el dashboard con métricas de CPU, RAM, GPU, temperaturas,
estado del pipeline, historias generadas y controles remotos.

Ctrl+C para detener el test.

### 17.4. Instalar como servicio systemd

```bash
# Copiar el archivo de servicio
sudo cp dashboard/innovalabs-dashboard.service /etc/systemd/system/

# Reemplazar el usuario
sudo sed -i "s/USER_ACTUAL/$USER/g" /etc/systemd/system/innovalabs-dashboard.service

# Habilitar y arrancar
sudo systemctl daemon-reload
sudo systemctl enable innovalabs-dashboard
sudo systemctl start innovalabs-dashboard

# Verificar
sudo systemctl status innovalabs-dashboard
# Esperado: active (running)

# Verificar desde la red
curl -s http://localhost:8080/api/system | python3 -m json.tool | head -10
```

### 17.5. Funcionalidades del dashboard

Acceder desde Windows en: `http://<IP_JETSON>:8080`

**Panel de monitoreo (auto-refresh cada 5s):**

- CPU: uso %, frecuencia, load average
- Memoria: usada/disponible/swap con barras de progreso
- GPU Orin: carga %, frecuencia, temperaturas por zona
- Disco: espacio usado/libre, tamaño de historias
- Pipeline: fase actual (idle/scouting/inferencing/writing)
- Servicios: estado de Ollama y n8n (online/offline)
- Modelos: lista de modelos de Ollama con tamaños
- Historias: últimas 15 generadas, click para leer completa

**Control remoto (6 acciones):**

| Botón | Acción | Cuándo usar |
|-------|--------|-------------|
| Reiniciar Ollama | Reinicia el servicio | Modelos no responden |
| Reiniciar n8n | Reinicia el orquestador | Workflow atascado |
| Disparar pipeline | Ejecuta un ciclo manualmente | Probar sin esperar el cron |
| Liberar VRAM | Reinicia Ollama para limpiar VRAM | Antes del Escritor si hay OOM |
| Max performance | Ejecuta jetson_clocks | Después de reiniciar la Jetson |
| Detener escritor | Kill del proceso llama-cli | Generación atascada o demasiado larga |

**Visor de logs (4 fuentes):**

- Sistema: logs generales del journal
- n8n: logs del orquestador
- Ollama: logs del servidor de inferencia
- Writer: logs del contenedor sidecar

**Visor de historias:**

- Click en cualquier historia para leer el contenido completo
- Botón de descarga para obtener el archivo .md
- Metadata: tema, moraleja, conteo de palabras

### 17.6. API REST del dashboard

Todos los datos del dashboard están disponibles como JSON para
automatización o integración con otras herramientas:

```powershell
# Desde PowerShell en Windows:

# Métricas del sistema
Invoke-RestMethod http://192.168.1.50:8080/api/system

# Estado del pipeline
Invoke-RestMethod http://192.168.1.50:8080/api/pipeline

# Lista de historias
Invoke-RestMethod http://192.168.1.50:8080/api/stories

# Descargar una historia
Invoke-WebRequest http://192.168.1.50:8080/api/stories/H-1710432000000/download -OutFile historia.md

# Ejecutar acción remota
Invoke-RestMethod -Method POST -Uri http://192.168.1.50:8080/api/control `
  -ContentType "application/json" `
  -Body '{"action":"restart_ollama","confirm":true}'
```

### 17.7. Accesos directos desde Windows

Crear un bookmark en el navegador o un acceso directo en el escritorio:

```
Nombre:     INNOVALABS Factory Floor (pixel-art)
URL:        http://192.168.1.50:8080/factory
```

```
Nombre:     INNOVALABS Dashboard (métricas)
URL:        http://192.168.1.50:8080
```

```
Nombre:     INNOVALABS n8n
URL:        http://192.168.1.50:5678
```

También puedes crear un atajo .bat para conectar por SSH rápidamente:

```batch
@echo off
title INNOVALABS - Jetson SSH
ssh usuario@192.168.1.50
pause
```

Guardar como `jetson-ssh.bat` en el escritorio.

---

## 18. Firewall y seguridad de red local

Aunque la Jetson solo es accesible desde la red local,
es buena práctica configurar un firewall básico.

### 18.1. Instalar y configurar UFW

```bash
sudo apt install -y ufw

# Política por defecto: bloquear entrada, permitir salida
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH (crítico — no bloquear antes de habilitar)
sudo ufw allow ssh

# Permitir el dashboard (solo desde red local)
sudo ufw allow from 192.168.1.0/24 to any port 8080 proto tcp comment "INNOVALABS Dashboard"

# Permitir n8n (solo desde red local)
sudo ufw allow from 192.168.1.0/24 to any port 5678 proto tcp comment "n8n UI"

# Permitir Ollama API (solo desde red local, opcional)
sudo ufw allow from 192.168.1.0/24 to any port 11434 proto tcp comment "Ollama API"

# Habilitar el firewall
sudo ufw enable
# Confirmar con 'y'

# Verificar reglas
sudo ufw status verbose
```

NOTA: Ajustar `192.168.1.0/24` al rango real de tu red local.
Si tu red usa `192.168.0.x`, cambiar a `192.168.0.0/24`.

### 18.2. Resumen de puertos expuestos

| Puerto | Servicio | Acceso | Propósito |
|--------|----------|--------|-----------|
| 22 | SSH | Red local + externo | Administración remota |
| 5678 | n8n | Solo red local | Editor de workflows |
| 8080 | Dashboard | Solo red local | Monitoreo y control |
| 11434 | Ollama | Solo red local | API de inferencia |

### 18.3. Seguridad adicional recomendada

```bash
# Desactivar login root por SSH
sudo sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Cambiar contraseña del usuario por una segura
passwd

# Instalar fail2ban (protección contra fuerza bruta SSH)
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Resumen de puertos y servicios (actualizado)

| Servicio | Puerto | Protocolo | Acceso |
|----------|--------|-----------|--------|
| SSH | 22 | TCP | `ssh usuario@<IP>` |
| n8n (UI + API) | 5678 | HTTP | `http://<IP>:5678` |
| Dashboard | 8080 | HTTP | `http://<IP>:8080` |
| Ollama API | 11434 | HTTP | `http://<IP>:11434` |
| Writer | — | docker exec | Interno (sin puerto) |

---

## Orden de arranque recomendado (actualizado)

```
1.  Jetson AGX Orin (boot — modo headless, multi-user.target)
2.  SSH daemon                      → Acceso remoto inmediato
3.  jetson-maxperf.service          → Modo MAXN + jetson_clocks
4.  Docker daemon                   → Automático
5.  Ollama (nativo o Docker)        → Carga modelos bajo demanda
6.  n8n (nativo o Docker)           → Espera a que Ollama esté healthy
7.  innovalabs-dashboard.service    → Dashboard web en :8080
8.  UFW firewall                    → Protección de red
9.  Cron 6h → Pipeline automático
```

Después del arranque, desde tu PC Windows:

1. Abrir `http://192.168.1.50:8080/factory` → Vista pixel-art de la fábrica
2. Abrir `http://192.168.1.50:8080` → Dashboard técnico de métricas
3. Abrir `http://192.168.1.50:5678` → n8n para editar workflows
4. SSH `ssh usuario@192.168.1.50` → Terminal completa
