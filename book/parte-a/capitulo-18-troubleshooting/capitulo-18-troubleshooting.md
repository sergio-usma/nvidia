# Capítulo 18 — Troubleshooting y Mejores Prácticas

## Introducción

Este capítulo documenta los errores más frecuentes al trabajar con el Jetson AGX Orin 64GB bajo JetPack 7.2, con sus causas exactas y soluciones verificadas. Si algo no funciona como se esperaba, este es el primer lugar donde buscar.

Los errores están organizados por área: Docker y contenedores, modelos LLM, audio y red, y sistema operativo. Cada entrada incluye el mensaje de error exacto que verá en el terminal, la causa raíz y la solución paso a paso.

---

## 16.1 Errores de Docker y Contenedores

### Error 16.1.1 — "docker: Error response from daemon: unknown or invalid runtime name: nvidia"

```
# Error completo
docker: Error response from daemon: unknown or invalid runtime name: nvidia.
See 'docker run --help'.
```

**Causa:** El NVIDIA Container Toolkit no está configurado como runtime en Docker, o Docker no ha sido reiniciado después de la configuración.

**Solución:**
```bash
# Verificar si el NCT está instalado
nvidia-ctk --version

# Si no está instalado:
sudo apt install -y nvidia-container-toolkit

# Configurar el runtime
sudo nvidia-ctk runtime configure --runtime=docker

# Reiniciar Docker (obligatorio)
sudo systemctl restart docker

# Verificar que el runtime aparece en la configuración
docker info | grep -i runtime
```

```
# Salida esperada
  Runtimes: io.containerd.runc.v2 nvidia runc
  Default Runtime: runc
```

---

### Error 16.1.2 — "docker: Error response from daemon: conflict: container name already in use"

```
# Error completo
docker: Error response from daemon: Conflict. The container name "/qwen35-35b" 
is already in use by container "<id>". You have to remove (or rename) that 
container to be able to reuse that name.
```

**Causa:** Un contenedor con ese nombre ya existe (activo o detenido). Esto ocurre cuando se intenta lanzar el mismo modelo dos veces, o cuando un alias `start-*` se ejecuta sin haber detenido el contenedor anterior.

**Solución:**
```bash
# Ver el estado del contenedor existente
docker ps -a | grep qwen35-35b

# Si está detenido, eliminarlo y volver a lanzar
docker rm qwen35-35b

# Si está activo, usar stop primero
docker stop qwen35-35b && docker rm qwen35-35b

# O usar el alias de kill que hace ambas cosas
kill-qwen35
```

---

### Error 16.1.3 — Out of Memory (OOM) al iniciar el contenedor del modelo

```
# Error en los logs del contenedor
torch.cuda.OutOfMemoryError: CUDA out of memory.
Attempted to allocate X GiB (GPU 0; 63.98 GiB total capacity)
```

**Causa:** El parámetro `--gpu-memory-utilization` es demasiado alto para el modelo actual, o hay otro contenedor activo que ocupa memoria GPU simultáneamente.

**Solución:**

```bash
# 1. Verificar qué contenedores están activos
docker ps
motors-status

# 2. Detener contenedores conflictivos
kill-qwen35 2>/dev/null
kill-nemotron 2>/dev/null
sudo systemctl stop ollama 2>/dev/null

# 3. Verificar RAM disponible
free -h

# 4. Reducir la utilización de GPU
# Cambiar 0.80 a 0.70 (o menos) en el comando docker run
# Para MoE y modelos >20B: usar 0.65–0.70
# Para modelos ≤9B: 0.80 es seguro
```

---

### Error 16.1.4 — "Error: pull access denied" o "manifest unknown"

```
# Error completo
docker: Error response from daemon: pull access denied for ghcr.io/nvidia-ai-iot/vllm,
repository does not exist or may require 'docker login'
```

**Causa:** El tag exacto del contenedor no existe en el registro. Los tags de los contenedores de NVIDIA cambian con nuevas versiones.

**Solución:**
```bash
# Verificar tags disponibles para vLLM oficial de NVIDIA
curl -s "https://ghcr.io/v2/nvidia-ai-iot/vllm/tags/list" \
  | python3 -m json.tool 2>/dev/null | grep '"' | head -20

# O buscar en la documentación de NVIDIA Jetson AI Lab
# la imagen correcta para JetPack 7.2

# Para ghcr.io (GitHub Container Registry), puede necesitar autenticarse:
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

---

### Error 16.1.5 — Contenedor se reinicia en bucle (restart loop)

```
# Al ejecutar: docker ps
CONTAINER ID   IMAGE          STATUS                      NAMES
abc123         ...            Restarting (1) 2 sec ago    qwen35-35b
```

**Causa:** El contenedor falla al arrancar y Docker lo reinicia automáticamente. Esto ocurre cuando `--restart unless-stopped` está activo (no debe usarse con contenedores de inferencia — usar `--restart no`).

**Solución:**
```bash
# 1. Ver por qué falla el contenedor
docker logs qwen35-35b --tail 50

# 2. Detener el ciclo
docker stop qwen35-35b && docker rm qwen35-35b

# 3. Relanzar con --restart no (OBLIGATORIO para contenedores de inferencia)
docker run ... --restart no ...
```

---

## 16.2 Errores de Modelos LLM

### Error 16.2.1 — La respuesta del modelo llega como "content: None"

```python
# Al hacer la petición en Python
respuesta = cliente.chat.completions.create(...)
print(respuesta.choices[0].message.content)
# Resultado: None
```

**Causa:** El parámetro `--reasoning-parser qwen3` redirige el contenido del pensamiento al campo `reasoning_content` en lugar de `content`. Clientes estándar compatibles con OpenAI no conocen este campo.

**Solución:**
```bash
# OPCIÓN 1 (recomendada): Eliminar --reasoning-parser del comando de inicio
# El modelo responde directamente en el campo content (compatible con todos los clientes)

# OPCIÓN 2: Si quiere usar el razonamiento, activarlo por petición
# (sin --reasoning-parser en el servidor)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35",
    "messages": [{"role": "user", "content": "Analiza..."}],
    "extra_body": {"enable_thinking": true}
  }'
```

---

### Error 16.2.2 — "404 Not Found: model 'Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16' not found"

```json
{
  "error": {
    "code": 404,
    "message": "model 'Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16' not found. Did you use --served-model-name?"
  }
}
```

**Causa:** Está usando el nombre completo del modelo de Hugging Face cuando en la API debe usar el alias configurado con `--served-model-name`.

**Solución:**
```python
# INCORRECTO — nombre completo del modelo HuggingFace
cliente.chat.completions.create(
    model="Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16",
    ...
)

# CORRECTO — usar el alias configurado con --served-model-name
cliente.chat.completions.create(
    model="qwen35",  # el alias que configuró
    ...
)

# Para saber qué modelos/aliases están activos:
curl http://localhost:8000/v1/models | python3 -m json.tool
```

---

### Error 16.2.3 — Ollama no responde después de un tiempo

```bash
# El comando curl queda colgado o da "Connection refused"
curl http://localhost:11434/api/version
# (sin respuesta, timeout)
```

**Causa:** Ollama se cayó (crash) o fue detenido por el OOM killer del kernel (cuando el sistema quedó sin RAM).

**Solución:**
```bash
# Verificar el estado del servicio
systemctl status ollama

# Ver el log de journald para encontrar la causa
journalctl -u ollama --since "30 min ago" | tail -30

# Si fue OOM, liberar memoria antes de reiniciar
clean-ai-containers 2>/dev/null
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
free -h

# Reiniciar Ollama
sudo systemctl restart ollama
sleep 5

# Verificar
curl -sf http://localhost:11434/api/version && echo "[OK] Ollama activo"
```

---

### Error 16.2.4 — Velocidad de tokens muy baja (<5 tok/s)

```
# Benchmark muestra velocidad inesperadamente baja
Velocidad: 3.2 tok/s (esperado: >25 tok/s)
```

**Causa posible 1:** El Jetson está en modo de baja potencia (15W) en lugar de MAXN.

```bash
# Verificar y corregir el modo de potencia
nvpmodel -q | grep "NV Power Mode"
pwr-maxn
```

**Causa posible 2:** jetson_clocks no está activo.

```bash
# Activar jetson_clocks
sudo jetson_clocks
# Verificar
sudo jetson_clocks --show | head -5
```

**Causa posible 3:** El modelo está siendo procesado en CPU en lugar de GPU.

```bash
# Verificar en los logs del contenedor que CUDA está siendo usado
docker logs nombre-contenedor | grep -i "cuda\|gpu\|device"

# Dentro del contenedor (si está activo):
docker exec -it nombre-contenedor \
  python3 -c "import torch; print(torch.cuda.is_available())"
```

---

### Error 16.2.5 — vLLM termina con "Segmentation Fault"

```
# En los logs del contenedor
Fatal Python error: Segmentation fault
...
/opt/venv/lib/python3.12/site-packages/vllm/...
```

**Causa:** Frecuentemente es un problema de `--shm-size` insuficiente. vLLM usa shared memory extensivamente para la comunicación entre procesos.

**Solución:**
```bash
# Incrementar el shm-size de 8g a 16g
docker run ... --shm-size 16g ...

# Si persiste, agregar también --ipc host
docker run ... --ipc host --shm-size 16g ...
```

---

## 16.3 Errores de Red y Acceso Remoto

### Error 16.3.1 — "Connection refused" desde otra máquina al Jetson

```bash
# Desde PC, intenta: curl http://192.168.1.100:8000/v1/models
# Resultado: curl: (7) Failed to connect to 192.168.1.100 port 8000: Connection refused
```

**Causa A:** El servidor no está escuchando en `0.0.0.0` — está limitado a `127.0.0.1` (localhost).

**Solución A:** Asegúrese de que todos los comandos de servidor incluyan `--host 0.0.0.0`:
```bash
vllm serve ... --host 0.0.0.0 --port 8000
llama-server ... --host 0.0.0.0 --port 8080
ollama serve  # Ollama por defecto ya escucha en 0.0.0.0
```

**Causa B:** UFW (firewall) está bloqueando el puerto.

**Solución B:**
```bash
# Ver estado del firewall
sudo ufw status

# Si está activo, permitir el puerto
sudo ufw allow 8000/tcp
sudo ufw allow 8080/tcp
sudo ufw reload
```

**Causa C:** El contenedor no usa `--network host` y el puerto no está publicado.

**Solución C:**
```bash
# Verificar cómo está expuesto el puerto
docker inspect nombre-contenedor | grep -A5 "Ports"

# Si no usa --network host, agregar -p 8000:8000
# O (preferido) usar --network host
```

---

### Error 16.3.2 — SSH se desconecta durante operaciones largas

```
# Durante una descarga o generación larga
packet_write_wait: Connection to X port 22: Broken pipe
```

**Causa:** El servidor SSH (en el Jetson) cierra sesiones inactivas por timeout. Aunque haya actividad, ciertas configuraciones de red o NAT hacen que la conexión se considere inactiva.

**Solución (en el cliente SSH — su PC):**
```bash
# En ~/.ssh/config (su PC)
Host jetson
    HostName 192.168.1.100
    User jetson
    ServerAliveInterval 60     # envía keepalive cada 60 segundos
    ServerAliveCountMax 5      # tolera hasta 5 fallos antes de desconectar
```

**Solución (en el Jetson — para sesiones muy largas):**
```bash
# Usar tmux o screen para que la sesión persista independientemente del SSH
sudo apt install -y tmux

# Iniciar sesión tmux
tmux new -s jetson_session

# Si se desconecta, reconectar con:
tmux attach -t jetson_session
```

---

### Error 16.3.3 — NoMachine muestra pantalla negra al conectar

```
# Al conectar con NoMachine desde Windows
La sesión se conecta pero la pantalla está negra
```

**Causa:** GNOME con Wayland activo no funciona en modo headless con pantalla virtual. El display manager Mutter requiere DRI3 que no está disponible con el driver dummy.

**Solución (ver Capítulo 7 §7.4 para detalles completos):**
```bash
# 1. Desactivar Wayland en GDM
sudo nano /etc/gdm3/custom.conf
# Descomentar: WaylandEnable=false

# 2. Instalar driver dummy y XFCE4
sudo apt install -y xserver-xorg-video-dummy xfce4 xfce4-goodies

# 3. Crear configuración de pantalla dummy
sudo tee /etc/X11/xorg.conf.d/30-headless-display.conf << 'EOF'
Section "Device"
    Identifier "DummyDevice"
    Driver "dummy"
    VideoRam 256000
EndSection
Section "Monitor"
    Identifier "DummyMonitor"
    HorizSync 28.0-80.0
    VertRefresh 48.0-75.0
EndSection
Section "Screen"
    Identifier "DummyScreen"
    Device "DummyDevice"
    Monitor "DummyMonitor"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Modes "1920x1080"
    EndSubSection
EndSection
EOF

# 4. Reiniciar GDM
sudo systemctl restart gdm3
```

---

## 16.4 Errores del Sistema Operativo

### Error 16.4.1 — El Jetson no arranca después de `apt upgrade`

```
# Al encender el Jetson, queda en la pantalla de NVIDIA o reinicia en bucle
```

**Por qué `apt dist-upgrade` es peligroso en Jetson:** El comando `dist-upgrade` puede reemplazar el kernel de NVIDIA Tegra por el kernel genérico de Ubuntu, lo que rompe el soporte GPU y puede dejar el sistema inoperable.

**Solución preventiva (para no llegar a este punto):**
```bash
# SIEMPRE usar solo:
sudo apt update && sudo apt upgrade -y
# NUNCA: sudo apt dist-upgrade
# NUNCA: sudo do-release-upgrade
```

**Si ya ocurrió** y tiene acceso a la UART serial o a la tarjeta SD de recuperación:

```bash
# Opción 1: Recovery mode (mantener Vol- durante el arranque)
# Luego usar NVIDIA SDK Manager desde el PC para re-flashear JP 7.2

# Opción 2: Si tiene acceso SSH residual
sudo apt install --reinstall linux-image-$(uname -r)
sudo update-initramfs -u
```

---

### Error 16.4.2 — "No space left on device" en `/`

```
# Error al instalar o descargar
E: Failed to fetch ... No space left on device
```

**Causa:** El sistema de archivos raíz (almacenamiento interno 64GB) está lleno.

**Solución:**
```bash
# 1. Identificar qué ocupa más espacio
du -sh /* 2>/dev/null | sort -h -r | head -15

# 2. Limpiar caché de apt
sudo apt clean
sudo apt autoremove -y

# 3. Limpiar Docker (imágenes no usadas)
docker image prune -a -f

# 4. Ver y limpiar caché de Hugging Face
hf-cache --list
hf-cache --clean-snapshots

# 5. Si tiene NVMe, mover el caché de HF al NVMe
ln -sfn /data/hf-cache ~/.cache/huggingface
```

---

### Error 16.4.3 — Alta temperatura y throttling

```bash
# jtop muestra temperatura >80°C y la velocidad de tokens cae a la mitad
```

**Causa:** El Jetson activa el throttling térmico automáticamente cuando supera el umbral de temperatura. En modo MAXN con modelos grandes, puede ocurrir si la ventilación es insuficiente.

**Diagnóstico:**
```bash
# Ver temperatura en tiempo real
watch -n 1 "cat /sys/class/thermal/thermal_zone0/temp | awk '{printf \"%.1f°C\n\", \$1/1000}'"

# Ver si hay throttling activo
cat /sys/kernel/debug/clk/emc/rate  2>/dev/null
```

**Solución:**
```bash
# 1. Verificar que el ventilador está funcionando
# (físicamente, escuchar/sentir el flujo de aire)

# 2. Reducir temporalmente el modo de potencia
pwr-30w  # reduce la carga térmica

# 3. Si el ambiente es muy caluroso, añadir ventilación forzada

# 4. Para cargas muy sostenidas, usar 30W en lugar de MAXN
# El rendimiento cae ~30% pero la temperatura se estabiliza
```

---

### Error 16.4.4 — Python 3.12 no encontrado o versión incorrecta

```bash
python3 --version
# Python 3.10.x  ← versión antigua de JP 6.2

# o:
python3 --version
# -bash: python3: command not found
```

**Causa:** En JP 7.2, Python 3.12 es el predeterminado, pero puede haber conflictos si tiene un sistema actualizado desde JP 6.2.

**Solución:**
```bash
# Verificar Python disponible
ls -la /usr/bin/python3*

# Si Python 3.12 está instalado pero no es el predeterminado
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
sudo update-alternatives --config python3

# Verificar
python3 --version
python3.12 --version
```

---

### Error 16.4.5 — `nvpmodel` o `jetson_clocks` no encontrados

```bash
nvpmodel -q
# -bash: nvpmodel: command not found
```

**Causa:** Las herramientas de NVIDIA para gestión de energía no están instaladas, o la instalación de JP 7.2 fue incompleta.

**Solución:**
```bash
# Instalar herramientas de NVIDIA Jetson
sudo apt update
sudo apt install -y nvidia-jetpack

# Alternativamente, instalar solo las herramientas de energía
sudo apt install -y nvpmodel jetson-clocks

# Verificar
which nvpmodel && nvpmodel -q
```

---

## 16.5 Errores de vLLM y llama.cpp

### Error 16.5.1 — "ValueError: max_model_len is too large"

```
# Al iniciar vLLM
ValueError: max_model_len (32768) is too large for this model.
The model's max sequence length (8192) is smaller than the requested max_model_len.
```

**Causa:** El parámetro `--max-model-len` es mayor que el máximo que soporta el modelo.

**Solución:**
```bash
# Reducir max-model-len al valor máximo del modelo
# Para modelos MoE grandes (35B+): 8192
# Para modelos 7B-14B: 16384
# Para modelos pequeños (2B-4B): 32768

# Agregar al comando:
vllm serve ... --max-model-len 8192
```

---

### Error 16.5.2 — llama.cpp no descarga el modelo de Hugging Face

```
# Al iniciar con --hf-repo
error: failed to load model: HTTP error 401 Unauthorized
```

**Causa:** El modelo requiere autenticación con Hugging Face (modelos "gated" como Llama 3, Gemma).

**Solución:**
```bash
# 1. Crear token en huggingface.co/settings/tokens
# 2. Configurar la variable de entorno en el contenedor
docker run ... \
  -e HF_TOKEN="hf_xxxxxxxxxxxx" \
  ...

# O aceptar las condiciones del modelo en huggingface.co
# y usar el token en el docker run
```

---

## 16.6 Mejores Prácticas — Resumen

### 16.6.1 Reglas de oro para el Jetson

| Práctica | Nunca | Siempre |
|---------|-------|---------|
| Actualizaciones | `apt dist-upgrade`, `do-release-upgrade` | `apt update && apt upgrade -y` |
| GPU en Docker | `--gpus all` | `--runtime nvidia` |
| Arranque automático de inferencia | `--restart unless-stopped` en contenedores LLM | `--restart no` para inferencia |
| `nvidia-smi` | ❌ No existe en Jetson | Usar `jtop`, `tegrastats`, `nvcc --version` |
| Modo de energía durante inferencia | 15W | `pwr-maxn` o `pwr-30w` |
| Antes de lanzar un modelo grande | Sin verificar RAM libre | `check-ready 20 "nombre"` |
| Temperatura máxima segura | >85°C sostenida | Configurar alertas en `jtop` |

### 16.6.2 Comandos de diagnóstico más útiles

```bash
# Estado completo del sistema
sys-status

# Ver qué consume más RAM
ps aux --sort=-%mem | head -15

# Ver logs del sistema (últimos 5 min)
journalctl --since "5 min ago" | grep -i "error\|warning\|oom" | tail -20

# Ver todos los contenedores y su estado
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Ver uso de disco por directorio
du -sh /var/* 2>/dev/null | sort -h -r | head -10
du -sh ~/.cache/* 2>/dev/null | sort -h -r | head -10

# Reinicio limpio del sistema de inferencia
clean-ai-containers && jetson-clean && pwr-15w && sleep 10 && sys-status
```

### 16.6.3 Checklist antes de reportar un problema

Antes de buscar ayuda en los foros de NVIDIA o abrir un issue, verifique:

```bash
# ╔═══════════════════════════════════════════════════════╗
# ║    CHECKLIST DE DIAGNÓSTICO JETSON AGX ORIN JP 7.2   ║
# ╚═══════════════════════════════════════════════════════╝

# 1. Versión del sistema
uname -r        # debe incluir "tegra"
lsb_release -a  # Ubuntu 24.04.x

# 2. Estado de Docker + NVIDIA
docker info | grep -E "Runtime|NVIDIA"

# 3. RAM disponible
free -h

# 4. Temperatura
cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "%.1f°C\n", $1/1000}'

# 5. Modo de energía actual
nvpmodel -q 2>/dev/null | grep "NV Power Mode"

# 6. Logs del contenedor que falla
docker logs nombre-contenedor --tail 100

# 7. Espacio en disco
df -h / /data 2>/dev/null
```

---

## 16.7 Recursos de Ayuda

**Comunidades oficiales:**
- NVIDIA Developer Forums — Jetson AGX Orin: `forums.developer.nvidia.com`
- NVIDIA Jetson AI Lab: `jetson-ai-lab.io`
- jetson-containers Issues: `github.com/dusty-nv/jetson-containers/issues`

**Documentación técnica:**
- JetPack 7.2 Release Notes: release notes oficiales de NVIDIA
- L4T r39.2 Documentation: developer.nvidia.com
- CUDA 13.2.1 Programming Guide: docs.nvidia.com

**Herramientas de diagnóstico instaladas:**
- `jtop` — monitor completo de Jetson (RAM, GPU, temperatura, energía)
- `tegrastats` — estadísticas en modo texto para scripts
- `nvcc --version` — verificar versión de CUDA dentro de contenedores
