# Capítulo 7 — Optimización de Red

## Introducción

La red es el cuello de botella más subestimado en un sistema de inferencia local. Descargar un modelo de 26 GB con la configuración por defecto de Ubuntu puede tomar 2 horas en una conexión de 100 Mbps por limitaciones del buffer TCP. Optimizado correctamente, el mismo sistema puede saturar el enlace y descargar en 30 minutos. Esta parte aplica todas las optimizaciones de red relevantes para el Jetson: parámetros TCP, algoritmo de congestión BBR, APT paralelo y aria2 para descargas de modelos.

**Prerequisito:** Capítulo 1 completada — red con IP estática 192.168.1.100.

**Tiempo estimado:** 15 minutos.

**Al final de esta parte tendrá:**
- Buffers TCP ampliados (de 128 KB a 16 MB por conexión)
- Algoritmo de congestión TCP BBR activado (mejor rendimiento en conexiones de alta latencia)
- IPv6 desactivado en la interfaz de red (reduce latencia en resolución DNS)
- APT configurado para descargas paralelas y retry automático
- `aria2` configurado para descargas de modelos a máxima velocidad (16 hilos)
- Verificación de velocidad de red efectiva

---

## 7.1 Optimización de Parámetros TCP del Kernel

El kernel Linux gestiona las conexiones TCP con un conjunto de parámetros de tamaño de buffer que por defecto están calibrados para consumo de energía y equipos de gama baja. En el Jetson, que tiene 64 GB de RAM, puede ampliar estos buffers significativamente para mejorar el throughput en descargas de archivos grandes.

```bash
# Crear archivo de configuración de red optimizada
sudo tee /etc/sysctl.d/99-jetson-network.conf > /dev/null << 'EOF'
# ── Buffers TCP ampliados ─────────────────────────────────────────
# Aumentar de 128KB a 16MB por conexión (mejora descargas de modelos grandes)
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# ── TCP BBR — algoritmo de congestión moderno ────────────────────
# BBR estima el ancho de banda real y la RTT para no sobrecargar la red
# Mejora significativamente la velocidad en conexiones con algo de latencia
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# ── Rendimiento general TCP ───────────────────────────────────────
# No reiniciar el slow-start TCP en conexiones idle (mejora transfers largos)
net.ipv4.tcp_slow_start_after_idle = 0
# Escala de ventana TCP (obligatorio con buffers grandes)
net.ipv4.tcp_window_scaling = 1
# Reutilizar TIME_WAIT sockets (mejora muchas conexiones simultáneas)
net.ipv4.tcp_tw_reuse = 1
# Fast open — reduce latencia en conexiones repetidas al mismo servidor
net.ipv4.tcp_fastopen = 3

# ── IPv6 ──────────────────────────────────────────────────────────
# Deshabilitar IPv6 en la interfaz de red (evita timeouts de resolución DNS
# cuando el router no tiene IPv6 configurado — reduce latencia de descarga)
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1

# ── Backlog de conexiones ─────────────────────────────────────────
# Permite más conexiones en cola (útil cuando Docker y vLLM reciben requests)
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
EOF

# Aplicar sin reboot
sudo sysctl -p /etc/sysctl.d/99-jetson-network.conf
```

```bash
# Salida esperada
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fastopen = 3
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
```

### 7.1.1 Verificar TCP BBR activo

```bash
# Verificar que BBR está activo
sysctl net.ipv4.tcp_congestion_control
```

```bash
# Salida esperada
net.ipv4.tcp_congestion_control = bbr
```

```bash
# Verificar que BBR está disponible como módulo del kernel
lsmod | grep bbr
# Si no aparece nada, el kernel lo tiene compilado estáticamente (normal en JP 7.2)
# Verificar alternativamente:
sysctl net.ipv4.tcp_available_congestion_control | grep bbr
```

```bash
# Salida esperada
net.ipv4.tcp_available_congestion_control = reno cubic bbr
```

---

## 7.2 Ajuste de MTU

El MTU (Maximum Transmission Unit) define el tamaño máximo de cada paquete de red. El valor por defecto (1500 bytes para Ethernet) es correcto para la mayoría de redes. Sin embargo, si su red local usa VLANs, PPPoE o VPN, un MTU más pequeño puede mejorar la estabilidad:

```bash
# Ver el MTU actual
ip link show | grep -E "eth|enp" | grep mtu
```

```bash
# Salida esperada (ejemplo)
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP ...
```

En la mayoría de redes domésticas con router directo a internet (sin PPPoE), 1500 bytes es el valor correcto. Solo cambie el MTU si tiene problemas de conectividad específicos con paquetes grandes:

```bash
# Solo si necesita ajustar MTU (reemplazar eth0 con su interfaz real):
# sudo ip link set dev eth0 mtu 1450
# Para hacerlo permanente via NetworkManager:
# sudo nmcli connection modify "Wired connection 1" 802-3-ethernet.mtu 1450
```

---

## 7.3 Optimización de APT para Descargas Paralelas

Cada vez que instala paquetes con `apt`, Ubuntu descarga múltiples archivos de forma secuencial por defecto. Esta configuración habilita descargas paralelas y retry automático:

```bash
# Configuración de APT optimizada
sudo tee /etc/apt/apt.conf.d/99jetson-performance > /dev/null << 'EOF'
# No descargar traducciones (ahorra tiempo y banda)
Acquire::Languages "none";

# Descargas en paralelo (hasta 5 simultáneas)
Acquire::Queue-Mode "access";
Acquire::http::Pipeline-Depth "5";

# Reintentos automáticos ante fallos de red
Acquire::Retries "3";

# Timeout más largo para conexiones lentas
Acquire::http::Timeout "120";

# Preferir IPv4 (evita problemas si IPv6 está desactivado en el kernel pero no en APT)
Acquire::ForceIPv4 "true";
EOF

echo "[OK] APT optimizado"
```

```bash
# Verificar que APT funciona con la nueva configuración
sudo apt update 2>&1 | tail -5
```

---

## 7.4 aria2 — Descargas Multi-Hilo para Modelos Grandes

`aria2` es un gestor de descargas que abre múltiples conexiones simultáneas al mismo servidor, multiplicando la velocidad de descarga efectiva. Es especialmente útil para descargar modelos de HuggingFace o NVIDIA NGC.

### 7.4.1 Instalar y Configurar aria2

```bash
# Instalar aria2
sudo apt install -y aria2
aria2c --version | head -1
# Salida esperada: aria2 version 1.37.0
```

```bash
# Crear configuración permanente de aria2
mkdir -p ~/.config/aria2

cat > ~/.config/aria2/aria2.conf << 'EOF'
# Número de conexiones paralelas por descarga
max-connection-per-server=16
split=16

# Buffer de descarga
min-split-size=10M
piece-length=4M

# Reintentos
max-tries=5
retry-wait=3

# Progreso
show-console-readout=true
human-readable=true

# Destino por defecto
dir=/data/models/gguf
EOF

echo "[OK] aria2 configurado"
```

### 7.4.2 Aliases para Descargas de Modelos

```bash
# Agregar aliases a ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── Descargas de modelos ───────────────────────────────────────────
# Descarga un archivo GGUF con aria2 a maxima velocidad (16 hilos)
# Uso: dl-gguf https://huggingface.co/.../model.gguf
alias dl-gguf='aria2c --conf-path=$HOME/.config/aria2/aria2.conf \
  --max-connection-per-server=16 --split=16 --dir=$HOME/data/models/gguf'

# Descarga un repositorio completo de HuggingFace (requiere huggingface-hub)
# Uso: hf-clone org/modelo [subdirectorio-destino]
alias hf-clone='huggingface-cli download --local-dir-use-symlinks false'

# Ver el estado de descarga de aria2 (en una segunda terminal)
alias dl-status='watch -n2 "aria2c --show-files 2>/dev/null || ls -lh ~/data/models/gguf/*.gguf 2>/dev/null | tail -5"'
EOF

source ~/.bash_aliases || source ~/.bashrc
```

### 7.4.3 Ejemplo de Descarga Directa de Archivo GGUF

```bash
# Ejemplo: descargar Gemma4 E2B GGUF para llama.cpp (Capitulo 12)
# Crear directorio de destino si no existe
mkdir -p ~/data/models/gguf

# Descarga directa con aria2 (sin autenticacion — modelo publico)
aria2c --conf-path=$HOME/.config/aria2/aria2.conf \
  --max-connection-per-server=16 \
  --split=16 \
  --dir=$HOME/data/models/gguf \
  "https://huggingface.co/unsloth/gemma-4-E2B-GGUF/resolve/main/gemma-4-E2B-Q4_K_M.gguf"
```

```bash
# Salida esperada durante descarga:
[DL:45.2MiB/s][#1 56%] gemma-4-E2B-Q4_K_M.gguf       2.1GiB/3.8GiB
```

```bash
# Verificar descarga completa
ls -lh ~/data/models/gguf/
# Salida esperada: -rw-r--r-- 1 jetson jetson 3.8G gemma-4-E2B-Q4_K_M.gguf
```

### 7.4.4 Script dl-model.sh — Descargas con Autenticacion HuggingFace

Los modelos "gated" (como Gemma 4 E4B, Llama 3, Mistral) requieren un token de HuggingFace. Este script gestiona la autenticacion automaticamente.

> **NOTA:** Si configuró el entorno de shell en el Capítulo 5, es posible que `HF_TOKEN` ya esté definido en su `~/.bash_aliases`. Verifique antes de duplicar la variable:
> ```bash
> grep "HF_TOKEN" ~/.bash_aliases ~/.bashrc 2>/dev/null
> ```
> Si aparece una línea con su token, salte el bloque de configuración siguiente y pase directamente a instalar `huggingface-hub`.

```bash
# Solo si HF_TOKEN NO está en ~/.bash_aliases todavía:
# Obtener token gratuito en: huggingface.co/settings/tokens
# Crear token de tipo "Read" y copiarlo

echo 'export HF_TOKEN="hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"' >> ~/.bash_aliases
# ⚠ Reemplaza hf_XXXX... con tu token real de HuggingFace
source ~/.bash_aliases
```

```bash
# Instalar huggingface-hub CLI
source ~/venvs/llm/bin/activate
pip install huggingface-hub
huggingface-cli --version
# Salida esperada: huggingface-cli 0.x.x
```

```bash
# Crear el script de descarga
cat > ~/scripts/dl-model.sh << 'EOF'
#!/usr/bin/env bash
# dl-model.sh — Descarga modelos con soporte HF_TOKEN y aria2
# Uso:
#   dl-model.sh <url|hf:org/modelo> [archivo] [directorio-destino]
#
#   dl-model.sh https://hf.co/.../model.gguf            archivo GGUF (aria2)
#   dl-model.sh hf:org/modelo                            repo completo (huggingface-cli)
#   dl-model.sh hf:org/modelo archivo.gguf               archivo especifico del repo
#   dl-model.sh hf:org/modelo "" /data/models/custom    destino personalizado
set -euo pipefail

URL="${1:-}"
ARCHIVO="${2:-}"
DESTINO="${3:-${DESTINO:-$HOME/data/models/gguf}}"
mkdir -p "$DESTINO"

LOG_FILE="$DESTINO/downloads.log"
log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

if [[ -z "$URL" ]]; then
    echo "Uso: dl-model.sh <url|hf:org/modelo> [archivo] [directorio-destino]"
    echo "  Ejemplos:"
    echo "    dl-model.sh https://huggingface.co/.../model.gguf"
    echo "    dl-model.sh hf:unsloth/gemma-4-E2B-GGUF gemma-4-E2B-Q4_K_M.gguf"
    echo "    dl-model.sh hf:google/gemma-4-E4B-it  (repo completo)"
    echo "    dl-model.sh https://hf.co/.../model.gguf \"\" /data/models/custom"
    exit 1
fi

log_msg "Iniciando descarga: $URL ${ARCHIVO:+(archivo: $ARCHIVO)} → $DESTINO"

# ── Descarga de repositorio HF completo ──────────────────────────
if [[ "$URL" == hf:* ]]; then
    REPO="${URL#hf:}"
    log_msg "=== Descargando repo HuggingFace: $REPO ==="
    source ~/venvs/llm/bin/activate 2>/dev/null || true
    HF_ARGS=(--local-dir-use-symlinks false)
    [ -n "${HF_TOKEN:-}" ] && HF_ARGS+=(--token "$HF_TOKEN")
    if [[ -n "$ARCHIVO" ]]; then
        log_msg "  Archivo: $ARCHIVO"
        huggingface-cli download "$REPO" "$ARCHIVO" \
            --local-dir "$DESTINO" "${HF_ARGS[@]}"
    else
        NOMBRE_REPO=$(echo "$REPO" | tr '/' '_')
        huggingface-cli download "$REPO" \
            --local-dir "$DESTINO/$NOMBRE_REPO" "${HF_ARGS[@]}"
    fi
    log_msg "[OK] Descarga completada en: $DESTINO"
    ls -lh "$DESTINO"/*.gguf 2>/dev/null || ls -lh "$DESTINO/" | tail -5
    exit 0
fi

# ── Descarga directa de archivo (URL HTTP) ───────────────────────
log_msg "=== Descargando archivo: $(basename "$URL") ==="
ARIA_ARGS=(
    --conf-path="$HOME/.config/aria2/aria2.conf"
    --max-connection-per-server=16
    --split=16
    --dir="$DESTINO"
    --continue=true
    --summary-interval=5
)

# Anadir header de autenticacion si HF_TOKEN esta disponible
if [[ -n "${HF_TOKEN:-}" ]]; then
    ARIA_ARGS+=(--header="Authorization: Bearer $HF_TOKEN")
    log_msg "  Usando HF_TOKEN para autenticacion"
fi

aria2c "${ARIA_ARGS[@]}" "$URL"
log_msg "[OK] Archivo guardado en: $DESTINO/$(basename "$URL") — $(ls -lh "$DESTINO/$(basename "$URL")" | awk '{print $5}')"
ls -lh "$DESTINO/$(basename "$URL")"
EOF

chmod +x ~/scripts/dl-model.sh
echo "[OK] ~/scripts/dl-model.sh listo"
```

```bash
# Agregar alias de acceso rapido
cat >> ~/.bash_aliases << 'EOF'
alias dl-model='~/scripts/dl-model.sh'
alias dl-model-hf='DESTINO=$HOME/data/models/gguf ~/scripts/dl-model.sh'
EOF
source ~/.bash_aliases || source ~/.bashrc

# Prueba: descargar Qwen3.5-4B GGUF (modelo publico, ~2.7 GB)
dl-model "https://huggingface.co/Qwen/Qwen2.5-4B-Instruct-GGUF/resolve/main/qwen2.5-4b-instruct-q4_k_m.gguf"
```

```bash
# Ejemplo con modelo gated (requiere HF_TOKEN y aceptar terminos en huggingface.co):
# dl-model hf:google/gemma-3-4b-it
# dl-model hf:unsloth/gemma-4-E4B-GGUF gemma-4-E4B-Q4_K_M.gguf
```

> **CONSEJO:** Si la descarga se interrumpe, vuelva a ejecutar el mismo comando. `aria2` reanuda desde donde se detuvo (`--continue=true`). Para ver el progreso en tiempo real desde otra terminal use `dl-status`.

---

### 7.4.5 aria2 para Descargas Generales

`aria2` no es solo para modelos de IA — es un gestor de descargas de propósito general. Con múltiples conexiones simultáneas acelera cualquier descarga grande: imágenes ISO de Linux, datasets, videos, firmware, etc.

```bash
# Agregar aliases de descarga general a ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── Descargas generales con aria2 ─────────────────────────────────
# Descarga cualquier archivo con 16 hilos y reanudación automática
# Uso: dl <url> [directorio-destino]
dl() {
    local url="${1:-}"
    local dest="${2:-$HOME/Downloads}"
    if [[ -z "$url" ]]; then
        echo "Uso: dl <url> [directorio-destino]"
        return 1
    fi
    mkdir -p "$dest"
    aria2c \
        --max-connection-per-server=16 \
        --split=16 \
        --continue=true \
        --dir="$dest" \
        --summary-interval=5 \
        "$url"
}

# Descarga una imagen ISO (destino: ~/iso/)
# Uso: dl-iso https://ubuntu.com/...iso
alias dl-iso='dl_iso() { dl "$1" "$HOME/iso"; }; dl_iso'

# Descarga un dataset (destino: /data/datasets/)
# Uso: dl-dataset https://example.com/dataset.zip
alias dl-dataset='dl_ds() { dl "$1" "/data/datasets"; }; dl_ds'

# Descarga múltiples URLs desde un archivo de texto (un URL por línea)
# Uso: dl-list lista.txt [directorio-destino]
dl-list() {
    local lista="${1:-}"
    local dest="${2:-$HOME/Downloads}"
    if [[ -z "$lista" || ! -f "$lista" ]]; then
        echo "Uso: dl-list <archivo-con-urls.txt> [directorio-destino]"
        return 1
    fi
    mkdir -p "$dest"
    aria2c \
        --input-file="$lista" \
        --max-connection-per-server=8 \
        --split=8 \
        --continue=true \
        --dir="$dest" \
        --summary-interval=10
}
EOF

source ~/.bash_aliases || source ~/.bashrc
echo "[OK] Aliases de descarga general disponibles: dl, dl-iso, dl-dataset, dl-list"
```

**Ejemplos de uso:**

```bash
# Descargar una imagen ISO de Ubuntu 24.04 (~2.6 GB)
dl-iso "https://releases.ubuntu.com/24.04/ubuntu-24.04.2-desktop-amd64.iso"

# Descargar un dataset público de Kaggle (tras exportar su URL de descarga)
dl-dataset "https://storage.googleapis.com/download.tensorflow.org/data/mnist.npz"

# Descargar múltiples modelos GGUF desde un archivo de lista
cat > /tmp/modelos.txt << 'EOF'
https://huggingface.co/Qwen/Qwen2.5-4B-Instruct-GGUF/resolve/main/qwen2.5-4b-instruct-q4_k_m.gguf
https://huggingface.co/lmstudio-community/Phi-4-mini-instruct-GGUF/resolve/main/Phi-4-mini-instruct-Q4_K_M.gguf
EOF
dl-list /tmp/modelos.txt ~/data/models/gguf
```

```bash
# Salida esperada (dl-list con 2 archivos):
[#1 28%][#2 12%] 2 archivos en paralelo
[DL:38.2MiB/s] ETA: 3m12s
```

> **NOTA:** Para descargas de video (YouTube, Vimeo, etc.) instale `yt-dlp` (`pip install yt-dlp`) — `aria2` solo descarga URLs directas, no páginas con reproductores JavaScript.

---

## 7.5 Verificación de Velocidad de Red

Antes de descargar los modelos de los Capítulos 12–14, verifique que la red funciona correctamente y mida la velocidad base:

```bash
# Verificar conectividad básica
ping -c 5 8.8.8.8
```

```bash
# Salida esperada
PING 8.8.8.8 (8.8.8.8): 56 data bytes
64 bytes from 8.8.8.8: seq=0 ttl=55 time=12.3 ms
...
5 packets transmitted, 5 received, 0% packet loss
round-trip min/avg/max = 11.2/12.5/14.1 ms
```

```bash
# Verificar resolución DNS (sin IPv6, solo IPv4)
nslookup huggingface.co
```

```bash
# Salida esperada (solo entradas IPv4 — confirma que IPv6 está desactivado)
Server:         8.8.8.8
Address:        8.8.8.8#53

Non-authoritative answer:
Name:    huggingface.co
Address: 18.x.x.x
```

```bash
# Prueba de velocidad de descarga con un archivo de HuggingFace
# Descarga un archivo pequeño (~30MB) y mide la velocidad
time curl -L --progress-bar \
  "https://huggingface.co/spaces/huggingface/README/resolve/main/thumbnail.png" \
  -o /tmp/hf_test.png && \
  echo "Tamaño descargado: $(du -h /tmp/hf_test.png | cut -f1)" && \
  rm /tmp/hf_test.png
```

```bash
# Verificar configuración TCP activa
echo "=== Configuración TCP activa ==="
sysctl net.ipv4.tcp_congestion_control
sysctl net.core.rmem_max
sysctl net.ipv4.tcp_slow_start_after_idle
sysctl net.ipv6.conf.all.disable_ipv6
```

```bash
# Salida esperada
=== Configuración TCP activa ===
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 16777216
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv6.conf.all.disable_ipv6 = 1
```

---

## 7.6 Verificación Final del Capítulo

```bash
# Verificación completa de red
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   VERIFICACIÓN CAPÍTULO 6 — RESULTADO        ║"
echo "╚══════════════════════════════════════════════╝"

echo ""
echo "── Conectividad ──"
ping -c 2 -W 2 8.8.8.8 &>/dev/null \
  && echo "[OK] Internet accesible (8.8.8.8)" \
  || echo "[ERROR] Sin acceso a internet"

echo ""
echo "── TCP BBR ──"
BBR=$(sysctl -n net.ipv4.tcp_congestion_control)
[ "$BBR" = "bbr" ] \
  && echo "[OK] TCP BBR activo" \
  || echo "[WARN]  TCP usa $BBR (BBR no activo)"

echo ""
echo "── Buffers TCP ──"
RMAX=$(sysctl -n net.core.rmem_max)
[ "$RMAX" -ge 16777216 ] \
  && echo "[OK] rmem_max: ${RMAX} bytes (16MB)" \
  || echo "[WARN]  rmem_max: ${RMAX} (esperado ≥16777216)"

echo ""
echo "── IPv6 ──"
IPV6=$(sysctl -n net.ipv6.conf.all.disable_ipv6)
[ "$IPV6" = "1" ] \
  && echo "[OK] IPv6 desactivado en interfaz" \
  || echo "[WARN]  IPv6 activo (puede causar lentitud en DNS)"

echo ""
echo "── Herramientas de descarga ──"
which aria2c &>/dev/null \
  && echo "[OK] aria2c disponible: $(aria2c --version | head -1)" \
  || echo "[ERROR] aria2 no instalado"

[ -f ~/.config/aria2/aria2.conf ] \
  && echo "[OK] Configuración aria2 presente" \
  || echo "[WARN]  Sin configuración aria2 (~/.config/aria2/aria2.conf)"

echo ""
echo "── APT optimizado ──"
[ -f /etc/apt/apt.conf.d/99jetson-performance ] \
  && echo "[OK] APT performance config presente" \
  || echo "[WARN]  Sin configuración APT personalizada"

echo ""
echo "── IP del Jetson ──"
hostname -I | awk '{print "  IP:", $1}'
ip route | grep "^default" | awk '{print "  Gateway:", $3}'
```

```bash
# Salida esperada
╔══════════════════════════════════════════════╗
║   VERIFICACIÓN CAPÍTULO 6 — RESULTADO        ║
╚══════════════════════════════════════════════╝

── Conectividad ──
[OK] Internet accesible (8.8.8.8)

── TCP BBR ──
[OK] TCP BBR activo

── Buffers TCP ──
[OK] rmem_max: 16777216 bytes (16MB)

── IPv6 ──
[OK] IPv6 desactivado en interfaz

── Herramientas de descarga ──
[OK] aria2c disponible: aria2 version 1.37.0
[OK] Configuración aria2 presente

── APT optimizado ──
[OK] APT performance config presente

── IP del Jetson ──
  IP: 192.168.1.100
  Gateway: 192.168.1.1
```

| Error | Causa | Solución |
|-------|-------|---------|
| BBR no activo | Kernel sin soporte BBR | Verificar: `sysctl net.ipv4.tcp_available_congestion_control` |
| IPv6 sigue activo tras reboot | Reglas de sysctl no persistidas | Verificar que el archivo está en `/etc/sysctl.d/`, no en `/etc/sysctl.conf` |
| ping falla | IP estática mal configurada | Verificar Capítulo 1, Sección 1.5 |
| APT update lento | `ForceIPv4` no activo | Re-ejecutar sección 6.3 |

> **Próximo paso:** El Capítulo 7 configura el entorno de desarrollo remoto completo — VSCode Remote SSH, JetBrains Gateway via SSH, tunnels para acceder a servicios del Jetson desde Windows, y transferencia de archivos con SCP y rsync.

---

## Apéndice 6-A: Velocidades de Descarga Esperadas por Tamaño de Modelo

Con la red optimizada (buffers TCP + BBR + aria2 multi-hilo), las velocidades de descarga en una conexión doméstica típica son:

| Velocidad de conexión | Modelo 4 GB | Modelo 16 GB | Modelo 26 GB |
|----------------------|-------------|--------------|--------------|
| 100 Mbps (12.5 MB/s) | ~6 min | ~22 min | ~35 min |
| 200 Mbps (25 MB/s) | ~3 min | ~11 min | ~18 min |
| 500 Mbps (62 MB/s) | ~1 min | ~4 min | ~7 min |
| 1 Gbps (125 MB/s) | <1 min | ~2 min | ~3.5 min |

> **CONSEJO:** Si tiene conexión simétrica de fibra, use `aria2c` con `--split=16` y `--max-connection-per-server=16` para modelos grandes. HuggingFace tiene CDN distribuido y aguanta bien las 16 conexiones paralelas.
