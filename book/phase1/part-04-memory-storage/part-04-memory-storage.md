# Capítulo 4 — Memoria y Almacenamiento: Swap, ZRAM y NVMe

## Introducción

El Jetson AGX Orin 64GB tiene una ventaja enorme sobre cualquier GPU de escritorio: 64 GB de memoria unificada que la CPU y la GPU comparten. Un modelo de 26 GB cabe completamente en RAM con margen sobrante. Sin embargo, cuando el sistema operativo, los servicios activos y el modelo suman más de 64 GB, el kernel no tiene adónde poner el excedente y mata procesos o entra en pánico.

La solución es un sistema de overflow en dos capas: **ZRAM** (swap comprimido en RAM — más rápido, menor espacio real) y **swap en NVMe** (disco SSD — más lento, pero sin límite práctico). Con estas dos capas configuradas, el Jetson puede manejar modelos de hasta ~55 GB con fluidez y bordear los 60 GB sin colapsar.

**Prerequisito:** Capítulo 1 completada. NVMe SSD instalado recomendado (aunque la guía cubre también eMMC como alternativa).

**Tiempo estimado:** 15–20 minutos.

**Al final de esta parte tendrá:**
- ZRAM de 8 GB (swap comprimido en RAM)
- Swap de 16 GB en NVMe SSD (o eMMC si no hay NVMe)
- Swappiness optimizado para cargas de LLM
- Directorio de modelos en NVMe montado como `/data`
- Comprensión del impacto de swap en velocidad de inferencia

---

## 4.1 Arquitectura de Memoria del Jetson

<!-- INFOGRAFÍA: Arquitectura de Memoria Unificada del Jetson — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


Antes de configurar el swap, conviene entender la jerarquía de memoria que usará el sistema:

```
┌───────────────────────────────────────────────────────────────┐
│              JERARQUÍA DE MEMORIA — Jetson AGX Orin 64GB     │
├───────────────────────────────────────────────────────────────┤
│  1. LPDDR5 UNIFICADA: 64 GB                                   │
│     • CPU + GPU comparten el mismo banco físico              │
│     • Velocidad: 204.8 GB/s                                  │
│     • Latencia: ~100 ns                                      │
│     • Para modelos: ~50 GB disponibles (OS usa ~12-14 GB)    │
├───────────────────────────────────────────────────────────────┤
│  2. ZRAM (swap comprimido en RAM): 8 GB virtuales            │
│     • Ocupa ~4 GB de RAM real (ratio de compresión ~2:1)     │
│     • Velocidad: similar a RAM (sin I/O de disco)            │
│     • Para: páginas frías del kernel, buffers del sistema    │
├───────────────────────────────────────────────────────────────┤
│  3. SWAP EN NVMe SSD: 16 GB                                  │
│     • Velocidad: ~2000 MB/s (Samsung 970 Evo o similar)     │
│     • Latencia: ~0.1 ms (vs 100 ns de RAM = 1000× más lento)│
│     • Para: último recurso antes de OOM killer               │
│     • Modelos en swap NVMe: inferencia muy lenta (0.5 tok/s) │
└───────────────────────────────────────────────────────────────┘
```

> **IMPORTANTE:** El swap en NVMe NO hace que modelos más grandes sean "rápidos" — si un modelo de 60 GB no cabe en RAM, la inferencia caerá a 0.5–2 tok/s porque cada operación requiere leer y escribir al disco. El swap es un amortiguador de seguridad, no una extensión de capacidad de rendimiento.

---

## 4.2 Verificar el Almacenamiento Disponible

```bash
# Ver dispositivos de bloque
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
```

```
# Salida esperada en un sistema con NVMe
NAME         SIZE TYPE MOUNTPOINT  FSTYPE
mmcblk0    59.2G disk
└─mmcblk0p1 59.2G part /           ext4    ← eMMC (SO)
nvme0n1   931.5G disk
└─nvme0n1p1 931.5G part /data      ext4    ← NVMe SSD
```

```bash
# Ver espacio disponible
df -h
```

```
# Salida esperada
Filesystem      Size  Used Avail Use% Mounted on
/dev/mmcblk0p1   58G   12G   43G  21% /
/dev/nvme0n1p1  916G   1.2G  914G   1% /data
```

---

## 4.3 Montar el NVMe SSD (si no está montado)

Si el NVMe aparece en `lsblk` pero no tiene punto de montaje, es necesario formatearlo y montarlo:

```bash
# SOLO si el NVMe no tiene sistema de archivos — BORRA TODO SU CONTENIDO
# Verificar primero: lsblk -f nvme0n1
# Si muestra FSTYPE vacío, ejecutar:

# Crear partición y formato ext4
sudo parted /dev/nvme0n1 --script mklabel gpt
sudo parted /dev/nvme0n1 --script mkpart primary ext4 0% 100%
sudo mkfs.ext4 /dev/nvme0n1p1

# Crear punto de montaje y montar
sudo mkdir -p /data
sudo mount /dev/nvme0n1p1 /data
sudo chown jetson:jetson /data

# Montar automáticamente en boot
echo "/dev/nvme0n1p1  /data  ext4  defaults,noatime  0 2" | sudo tee -a /etc/fstab

# Verificar
df -h /data
```

```
# Salida esperada
Filesystem       Size  Used Avail Use% Mounted on
/dev/nvme0n1p1   916G  1.2G  914G   1% /data
```

---

## 4.4 Configurar ZRAM

ZRAM es un dispositivo de swap virtual que comprime las páginas de memoria antes de "escribirlas" — en realidad las mantiene en RAM comprimidas. Ocupa menos espacio real del que reporta y es mucho más rápido que el swap en disco.

Ubuntu 24.04 incluye `zram-config` pero necesita instalarse:

```bash
# Instalar y verificar ZRAM
sudo apt install -y zram-config

# Verificar que el servicio está activo
sudo systemctl status zram-config | grep -E "Active|Loaded"
```

```
# Salida esperada
     Loaded: loaded (/lib/systemd/system/zram-config.service; enabled; ...)
     Active: active (exited) since ...
```

```bash
# Verificar que ZRAM está activo como swap
swapon --show
```

```
# Salida esperada
NAME       TYPE      SIZE USED PRIO
/dev/zram0 partition 7.8G   0B  100
```

Por defecto, `zram-config` crea un dispositivo de aproximadamente la mitad de la RAM (8 GB en el caso del Jetson 64GB) con prioridad alta (`PRIO 100`), lo que significa que Linux lo llenará primero antes de tocar el swap en disco.

> **NOTA:** Si `zram-config` no crea automáticamente el dispositivo del tamaño esperado, puede configurarlo manualmente:
>
> ```bash
> # Configuración manual de ZRAM (si el automático da un tamaño incorrecto)
> sudo systemctl stop zram-config
> sudo tee /etc/default/zram-config > /dev/null << 'EOF'
> ZRAM_SIZE=8G
> EOF
> sudo systemctl start zram-config
> swapon --show
> ```

---

## 4.5 Crear Swap en NVMe

El swap en NVMe es el segundo nivel de overflow. 16 GB es suficiente para la mayoría de escenarios — si un modelo requiere más de 50 GB + 8 GB ZRAM + 16 GB NVMe swap = 74 GB, probablemente no debería ejecutarse en este sistema de todos modos.

```bash
# Verificar que hay espacio suficiente en NVMe
df -h /data | awk 'NR==2 {print "NVMe disponible:", $4}'
```

```bash
# Crear el archivo de swap en NVMe
sudo fallocate -l 16G /data/swapfile

# Si fallocate falla (sistema de archivos sin soporte):
# sudo dd if=/dev/zero of=/data/swapfile bs=1G count=16 status=progress

# Asegurar permisos — el swap DEBE ser solo de root
sudo chmod 600 /data/swapfile

# Formatear como área de swap
sudo mkswap /data/swapfile
```

```
# Salida esperada
Setting up swapspace version 1, size = 16 GiB (17179869184 bytes)
no label, UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

```bash
# Activar el swap
sudo swapon /data/swapfile

# Verificar que está activo (junto a ZRAM)
swapon --show
```

```
# Salida esperada — deben aparecer ZRAM y el swapfile
NAME            TYPE      SIZE USED PRIO
/dev/zram0      partition 7.8G   0B  100
/data/swapfile  file       16G   0B   -2
```

```bash
# Hacer el swap permanente (sobrevive reboots)
echo '/data/swapfile  none  swap  sw  0 0' | sudo tee -a /etc/fstab

# Verificar la entrada en fstab
grep swap /etc/fstab
```

```
# Salida esperada
/data/swapfile  none  swap  sw  0 0
```

---

## 4.6 Ajustar Swappiness y Parámetros de Memoria

`swappiness` controla con qué agresividad el kernel mueve páginas de RAM a swap. El valor por defecto (60) hace que Linux empiece a usar swap cuando la RAM aún está al 40% de uso. Para inferencia con LLMs, queremos que el kernel mantenga todo en RAM el mayor tiempo posible:

```bash
# Configurar parámetros de memoria para LLM
sudo tee /etc/sysctl.d/99-jetson-memory.conf > /dev/null << 'EOF'
# Usar swap solo cuando sea estrictamente necesario
vm.swappiness=10

# No liberar cache del filesystem agresivamente
# (50 = intermedio; útil cuando hay muchos modelos en disco)
vm.vfs_cache_pressure=50

# No entrar en pánico por OOM — dejar que el OOM killer actúe
vm.panic_on_oom=0

# Matar el proceso que causó el OOM, no uno aleatorio
vm.oom_kill_allocating_task=1
EOF

# Aplicar inmediatamente sin reboot
sudo sysctl -p /etc/sysctl.d/99-jetson-memory.conf
```

```
# Salida esperada
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.panic_on_oom = 0
vm.oom_kill_allocating_task = 1
```

| Parámetro | Valor por defecto | Valor Jetson | Por qué |
|-----------|-----------------|-------------|---------|
| `vm.swappiness` | 60 | 10 | Priorizar RAM para el modelo |
| `vm.vfs_cache_pressure` | 100 | 50 | Mantener cache de archivos más tiempo |
| `vm.panic_on_oom` | 0 | 0 | Dejar actuar el OOM killer, no reboot |
| `vm.oom_kill_allocating_task` | 0 | 1 | Matar al responsable, no a un proceso aleatorio |

---

## 4.7 Directorio de Modelos en NVMe

Si el NVMe tiene más de 200 GB libres, es conveniente configurar los cachés de modelos para que apunten al NVMe en lugar del eMMC (que tiene solo ~43 GB libres tras la instalación del sistema):

```bash
# Crear estructura de directorios de modelos en NVMe
mkdir -p /data/models/huggingface
mkdir -p /data/models/gguf
mkdir -p /data/models/ollama

# Crear enlace simbólico para que HuggingFace use NVMe automáticamente
# (el cache HF por defecto es ~/.cache/huggingface/)
mkdir -p ~/.cache
ln -sf /data/models/huggingface ~/.cache/huggingface

# Verificar
ls -la ~/.cache/huggingface
```

```
# Salida esperada
lrwxrwxrwx 1 jetson jetson 26 ... /home/jetson/.cache/huggingface -> /data/models/huggingface
```

```bash
# Agregar variable de entorno para vLLM también
echo 'export HF_HOME=/data/models/huggingface' >> ~/.bashrc
echo 'HF_HOME=/data/models/huggingface' | sudo tee -a /etc/environment
source ~/.bashrc
```

> **NOTA:** Si ya guardó tokens HuggingFace en `~/.cache/huggingface/token` en el Capítulo 2, ese archivo ahora apuntará automáticamente al nuevo directorio via el symlink. Los tokens siguen funcionando sin cambios.

---

## 4.8 Impacto del Swap en la Velocidad de Inferencia

Es fundamental entender qué ocurre con la velocidad de inferencia cuando un modelo excede la RAM disponible:

| Escenario | RAM usada | Swap usado | Velocidad |
|-----------|-----------|-----------|-----------|
| Modelo 7B Q4 (4 GB) | 4 GB | 0 | ~35–50 tok/s |
| Modelo 13B Q4 (8 GB) | 8 GB | 0 | ~25–35 tok/s |
| Modelo 35B MoE (26 GB) | 26 GB | 0 | ~28–32 tok/s |
| Modelo 35B Q4 completo (20 GB) | 20 GB | 0 | ~18–25 tok/s |
| Modelo 70B Q4 (40 GB) | 40 GB | 0 | ~8–12 tok/s |
| Modelo que excede RAM (usa ZRAM) | ~50 GB | 8 GB ZRAM | ~5–8 tok/s |
| Modelo que excede RAM+ZRAM (usa NVMe swap) | ~50 GB | 16 GB NVMe | ~0.5–2 tok/s |

La recomendación práctica: **mantenga sus modelos dentro del presupuesto de ~50 GB**. Para modelos de 35B+ MoE (que tienen muchos parámetros pero activan solo una fracción), el consumo real es mucho menor que el tamaño nominal.

---

## 4.9 Script de Liberación de Memoria

En ocasiones, tras ejecutar y detener un modelo, la RAM no se libera completamente porque el kernel mantiene cachés en memoria. Este script fuerza la limpieza:

```bash
# Agregar al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── Gestión de memoria ────────────────────────────────────────────
alias jetson-mem='free -h | awk "/^Mem:/{print \"RAM: \"\$3\" usados de \"\$2\", \"\$7\" libres\"}" && swapon --show'

alias mem-free='
  echo "Memoria antes:"
  free -h | grep Mem
  echo ""
  sudo sync
  sudo sh -c "echo 3 > /proc/sys/vm/drop_caches"
  sudo swapoff -a && sudo swapon -a 2>/dev/null
  echo ""
  echo "Memoria después:"
  free -h | grep Mem
'
EOF

source ~/.bashrc
```

```bash
# Uso — ver estado de memoria:
jetson-mem

# Limpiar cachés del kernel (usar tras detener un modelo):
mem-free
```

---

## 4.10 Verificación Final del Capítulo

```bash
# Verificación completa de memoria y swap
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     VERIFICACIÓN CAPÍTULO 4 — RESULTADO         ║"
echo "╚══════════════════════════════════════════════╝"

echo ""
echo "── Dispositivos de almacenamiento ──"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -v "^loop"

echo ""
echo "── Swap activo ──"
swapon --show
# Esperado: /dev/zram0 (ZRAM) + /data/swapfile (NVMe)

echo ""
echo "── Memoria total (RAM + swap) ──"
free -h

echo ""
echo "── Parámetros de kernel ──"
sysctl vm.swappiness vm.vfs_cache_pressure vm.panic_on_oom

echo ""
echo "── Directorio de modelos ──"
ls -la ~/.cache/huggingface 2>/dev/null && echo "[OK] Symlink HF → NVMe" || echo "[WARN]  Sin symlink HF"
df -h /data 2>/dev/null | awk 'NR==2{print "NVMe disponible:", $4}'
```

```
# Salida esperada
╔══════════════════════════════════════════════╗
║     VERIFICACIÓN CAPÍTULO 4 — RESULTADO         ║
╚══════════════════════════════════════════════╝

── Dispositivos de almacenamiento ──
NAME         SIZE TYPE MOUNTPOINT
mmcblk0    59.2G disk
└─mmcblk0p1 59.2G part /
nvme0n1   931.5G disk
└─nvme0n1p1 931.5G part /data

── Swap activo ──
NAME            TYPE      SIZE USED PRIO
/dev/zram0      partition 7.8G   0B  100
/data/swapfile  file       16G   0B   -2

── Memoria total (RAM + swap) ──
               total        used        free
Mem:            62Gi       12Gi        50Gi
Swap:           24Gi        0B         24Gi

── Parámetros de kernel ──
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.panic_on_oom = 0

── Directorio de modelos ──
lrwxrwxrwx ... /home/jetson/.cache/huggingface -> /data/models/huggingface
[OK] Symlink HF → NVMe
NVMe disponible: 898G
```

| Error | Causa | Solución |
|-------|-------|---------|
| ZRAM no aparece en `swapon` | `zram-config` no instalado | `sudo apt install zram-config && sudo systemctl restart zram-config` |
| `/data/swapfile` no aparece | `swapon` no ejecutado o fstab sin entrada | `sudo swapon /data/swapfile` |
| `/data` no disponible | NVMe sin montar | Verificar `lsblk` y ejecutar sección 4.3 |
| `vm.swappiness` sigue en 60 | `sysctl -p` no aplicado | `sudo sysctl -p /etc/sysctl.d/99-jetson-memory.conf` |

> **Próximo paso:** El Capítulo 5 configura el entorno de shell: alias de productividad, `.bashrc` organizado y las herramientas de desarrollo (Git, pipx, entornos virtuales Python).
