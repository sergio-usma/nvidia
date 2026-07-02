# Capítulo 5 — Ajuste de Rendimiento: nvpmodel y jetson_clocks

## Introducción

El Jetson AGX Orin 64GB es capaz de alcanzar 275 TOPS y velocidades de inferencia de 30–58 tokens por segundo, pero solo cuando opera en el modo de energía correcto con las frecuencias bloqueadas al máximo. Sin este ajuste, el sistema funciona en un modo conservador que reduce la velocidad de inferencia en un factor de 3× respecto al máximo.

Esta parte explica los dos mecanismos de control de rendimiento del Jetson, cuándo usar cada uno y cómo verificar que están aplicados correctamente.

**Prerequisito:** Capítulo 1 completada — Ubuntu 24.04 con SSH.

**Tiempo estimado:** 10 minutos.

**Al final de esta parte tendrá:**
- Comprensión de los 4 modos de energía del Jetson
- Aliases de teclado para cambiar modo al instante (`pwr-maxn`, `pwr-30w`, `pwr-15w`)
- `jetson_clocks` aplicado en el modo de trabajo activo
- Script de arranque de rendimiento para activar antes de cargar modelos

---

## 3.1 Dos Mecanismos de Control Independientes

<!-- INFOGRAFÍA: Los Dos Mecanismos de Control de Rendimiento — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


El rendimiento del Jetson se controla con dos herramientas complementarias:

```
nvpmodel  →  define el LÍMITE de consumo energético (TDP)
              y cuántos núcleos están activos
              ↑ sobrevive reboots (escribe en /etc/nvpmodel.conf)

jetson_clocks →  dentro del TDP permitido, MAXIMIZA todas las frecuencias
                 (CPU, GPU, bus de memoria EMC)
                 ↑ temporal — se resetea en cada reboot
```

Ambos son necesarios. Solo `nvpmodel -m 0` (MAXN) sin `jetson_clocks` puede dejar la GPU corriendo a 600 MHz en lugar de 1300 MHz.

---

## 3.2 Modos de Energía — nvpmodel

### 3.2.1 Tabla de modos disponibles

El Jetson AGX Orin 64GB con JetPack 7.2 tiene los siguientes modos de energía:

| ID | Nombre | TDP | Núcleos CPU | Frec. GPU máx. | Cuándo usar |
|----|--------|-----|-------------|----------------|------------|
| **0** | **MAXN** | Sin límite (~50W) | **12** | **1300 MHz** | Inferencia LLM, compilación |
| 1 | MODE_50W | 50 W | 12 | 1100 MHz | Alternativa balanceada |
| 2 | MODE_30W | 30 W | 8 | 854 MHz | Modelos pequeños, uso general |
| 3 | MODE_15W | 15 W | 4 | 612 MHz | Espera, tareas livianas |

> **NOTA sobre consumo real:** "MAXN" no tiene un límite de TDP fijo — el sistema usa lo que necesite. En inferencia activa con modelos de 30B, el consumo suele ser de 45–55W. En espera, cae a 8–12W independientemente del modo.

### 3.2.2 Verificar el modo actual

```bash
# Ver el modo de energía activo
sudo nvpmodel -q
```

```
# Salida esperada
NVPM WARN: fan mode is not set to cool
NV Power Mode: MODE_30W_2CORE
2
```

El número final (aquí `2`) es el ID del modo activo.

```bash
# Ver todos los modos disponibles con detalle
sudo nvpmodel -q --verbose | grep -E "MODE_NAME|TDP"
```

### 3.2.3 Cambiar de modo

```bash
# Cambiar a MAXN (máximo rendimiento)
sudo nvpmodel -m 0
```

> **ATENCIÓN — Diálogo de reinicio:** Al cambiar de modo de energía, el Jetson mostrará un diálogo interactivo solicitando confirmación de reinicio. Este es el comportamiento esperado:
>
> ```
> jetson@jetson-orin:~$ sudo nvpmodel -m 0
> [sudo] password for jetson:
> NVPM WARN: Golden image context is already created
> NVPM WARN: Reboot required for changing to this power mode: 0
> NVPM WARN: DO YOU WANT TO REBOOT NOW? enter YES/yes to confirm:
> yes
> ```
>
> Escriba `yes` y presione Enter para confirmar el reinicio. El Jetson arrancará en el nuevo modo de energía automáticamente.

```bash
# Verificar cambio (tras el reinicio)
sudo nvpmodel -q
```

```
# Salida esperada
NVPM WARN: fan mode is not set to cool
NV Power Mode: MAXN
0
```

> **IMPORTANTE:** El cambio de `nvpmodel` **sobrevive reboots** — se guarda en `/etc/nvpmodel.conf`. Si cambia a MAXN ahora, el próximo reboot arrancará en MAXN. Esto es lo deseado para un sistema de inferencia.

---

## 3.3 Bloqueo de Frecuencias — jetson_clocks

### 3.3.1 Qué hace jetson_clocks

`nvpmodel` define el límite de energía pero el sistema puede no usar todas las frecuencias disponibles dentro de ese límite (por temperatura, carga detectada o políticas de governor). `jetson_clocks` fuerza todas las frecuencias (CPU, GPU y bus de memoria EMC) a su valor máximo permitido por el modo activo:

```bash
# Bloquear todas las frecuencias al máximo
sudo jetson_clocks
```

```bash
# Verificar que las frecuencias se bloquearon
sudo jetson_clocks --show
```

```
# Salida esperada (extracto clave)
CPU Cluster Switching: Disabled
cpu0: Online=1 Governor=schedutil MinFreq=729600 MaxFreq=2201600 CurrentFreq=2201600 ...
cpu4: Online=1 Governor=schedutil MinFreq=729600 MaxFreq=2201600 CurrentFreq=2201600 ...
GPU MinFreq=306000000 MaxFreq=1300500000 CurrentFreq=1300500000
EMC MinFreq=204000000 MaxFreq=3199000000 CurrentFreq=3199000000
```

La columna `CurrentFreq` debe ser igual a `MaxFreq` en todos los componentes.

### 3.3.2 Impacto real en inferencia

| Configuración | GPU Frec. | Velocidad (modelo 7B Q4) |
|---------------|-----------|--------------------------|
| nvpmodel modo 2 (30W), sin jetson_clocks | ~600 MHz | ~8–10 tok/s |
| nvpmodel modo 0 (MAXN), sin jetson_clocks | ~900 MHz | ~14–18 tok/s |
| nvpmodel modo 0 (MAXN) + jetson_clocks | **1300 MHz** | **~25–40 tok/s** |

La combinación `nvpmodel -m 0` + `jetson_clocks` entrega la mejora de rendimiento más significativa posible sin modificar el hardware.

---

## 3.4 Aliases de Energía — Control Rápido desde la Terminal

Configure estos aliases en `~/.bashrc` para cambiar modos al instante:

```bash
# Agregar aliases de energía al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── Modos de energía del Jetson ───────────────────────────────────
alias pwr-maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "MAXN: 50W activo, frecuencias bloqueadas"'
alias pwr-30w='sudo nvpmodel -m 2 && sudo jetson_clocks && echo "30W activo"'
alias pwr-15w='sudo nvpmodel -m 3 && sudo jetson_clocks --restore && echo "15W (bajo consumo)"'
alias pwr-status='sudo nvpmodel -q && echo "" && sudo jetson_clocks --show | grep -E "GPU|EMC|cpu0" | head -5'
EOF

source ~/.bashrc
```

**Uso diario:**

```bash
# Antes de cargar un modelo grande:
pwr-maxn    # MAXN + frecuencias al máximo

# Para trabajo de desarrollo ligero (editar código, git, etc.):
pwr-30w     # 8 núcleos, GPU a 854 MHz — suficiente para tareas de texto

# Con el sistema en espera sin modelos activos:
pwr-15w     # 4 núcleos, mínima frecuencia, bajo consumo

# Ver el estado actual:
pwr-status
```

---

## 3.5 Hacer jetson_clocks Permanente (Opcional)

`jetson_clocks` se resetea en cada reboot. Si siempre trabaja en MAXN, puede crear un servicio systemd que lo aplique automáticamente al arrancar:

```bash
# Crear servicio systemd para jetson_clocks
sudo tee /etc/systemd/system/jetson-clocks-lock.service > /dev/null << 'EOF'
[Unit]
Description=Lock Jetson clocks at maximum frequency
After=multi-user.target
Wants=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/jetson_clocks
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jetson-clocks-lock
sudo systemctl start jetson-clocks-lock

# Verificar
sudo systemctl status jetson-clocks-lock
```

```
# Salida esperada
● jetson-clocks-lock.service - Lock Jetson clocks at maximum frequency
     Loaded: loaded (/etc/systemd/system/jetson-clocks-lock.service; enabled; ...)
     Active: active (exited) since ...
```

> **CONSEJO:** Si implementa la arquitectura de arranque limpio de el Capítulo 15 (Sección 15.0), que inicia en `multi-user.target` sin cargar inferencia automáticamente, puede activar este servicio tranquilamente — bloquear frecuencias al máximo en boot no carga modelos, solo establece la configuración de hardware lista para cuando el usuario la necesite.

---

## 3.6 Monitoreo de Temperatura y Consumo

En MAXN con inferencia activa, el ventilador del Jetson se acelera automáticamente. El sistema de refrigeración del Developer Kit está diseñado para esta carga, pero es útil monitorear la temperatura durante los primeros usos intensivos.

### 3.6.1 jtop — monitor integrado

```bash
# Abrir el monitor de recursos del Jetson
sudo jtop
```

Navegue con las teclas numéricas:
- **1** — INFO: versiones, JetPack, modo de energía actual
- **2** — CTRL: control interactivo de frecuencias y modo de energía
- **3** — GPU: uso de GPU y temperatura en tiempo real
- **4** — CPU: uso por núcleo y frecuencias
- **5** — MEM: memoria unificada, swap, ZRAM

### 3.6.2 tegrastats — monitoreo en terminal

```bash
# Monitoreo continuo cada segundo (Ctrl+C para salir)
tegrastats --interval 1000
```

```
# Salida esperada (extracto)
RAM 12519/65536MB (lfb 1x4MB) SWAP 0/16384MB ...
CPU [45%@2201,32%@2201,...] EMC_FREQ 85%@3199 GPC_FREQ 80%@1300
GPU@62C cpu@58C Tboard@45C Tdiode@58C ...
```

Valores de referencia durante inferencia activa:

| Componente | Normal | Precaución | Crítico |
|------------|--------|-----------|---------|
| GPU | 50–75°C | 80–84°C | ≥85°C (throttle) |
| CPU | 45–70°C | 75–84°C | ≥85°C |
| Board | 35–55°C | 60°C | 70°C |

> **ADVERTENCIA:** Si ve `throttle=1` en `tegrastats`, el sistema está reduciendo frecuencias por temperatura. Causas más comunes: ventilador bloqueado o vents de ventilación cubiertos. Verifique que el Jetson tiene ventilación libre en los 4 costados.

### 3.6.3 Script de diagnóstico rápido

```bash
# Agregar al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── Diagnóstico rápido de rendimiento ────────────────────────────
alias perf-status='
  echo "── Modo de energía ──"
  sudo nvpmodel -q 2>/dev/null | grep -v WARN
  echo ""
  echo "── Frecuencias clave ──"
  sudo jetson_clocks --show 2>/dev/null | grep -E "GPU Min|GPU Max|GPU Cur|EMC Max|EMC Cur|cpu0.*Cur" | head -8
  echo ""
  echo "── Temperatura ──"
  cat /sys/class/thermal/thermal_zone*/type 2>/dev/null | paste - <(cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | awk "{printf \"%.1f°C\n\", \$1/1000}")
  echo ""
  echo "── Memoria ──"
  free -h | awk "/^Mem:/{print \"RAM: \"\$3\" usados de \"\$2\", \"\$7\" libres\"}"
'
EOF

source ~/.bashrc
```

```bash
# Uso:
perf-status
```

---

## 3.7 Cuándo Usar Cada Modo

| Situación | Modo recomendado | Comando |
|-----------|-----------------|---------|
| Ejecutar modelos LLM (cualquier tamaño) | MAXN | `pwr-maxn` |
| Compilar llama.cpp o torchvision | MAXN | `pwr-maxn` |
| Procesar video o audio con modelos | MAXN | `pwr-maxn` |
| Desarrollo: editar código, git, shell | 30W | `pwr-30w` |
| Sistema en espera sin modelos activos | 15W | `pwr-15w` |
| Ahorro de energía máximo (USB/batería externa) | 15W | `pwr-15w` |

---

## 3.8 Verificación Final del Capítulo

```bash
# Aplicar MAXN + jetson_clocks y verificar
pwr-maxn

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     VERIFICACIÓN CAPÍTULO 3 — RESULTADO         ║"
echo "╚══════════════════════════════════════════════╝"

echo ""
echo "── Modo de energía ──"
sudo nvpmodel -q 2>/dev/null | grep -E "Power Mode|^[0-9]"

echo ""
echo "── Frecuencia GPU ──"
GPU_FREQ=$(sudo jetson_clocks --show 2>/dev/null | grep "GPU.*CurrentFreq" | awk -F= '{print $NF}')
[ -n "$GPU_FREQ" ] \
  && echo "GPU CurrentFreq: ${GPU_FREQ} Hz (máx: 1300000000 Hz)" \
  || echo "[WARN]  No se pudo leer frecuencia de GPU"

echo ""
echo "── Aliases disponibles ──"
alias pwr-maxn  2>/dev/null && echo "[OK] pwr-maxn" || echo "[ERROR] pwr-maxn no configurado"
alias pwr-30w   2>/dev/null && echo "[OK] pwr-30w"  || echo "[ERROR] pwr-30w no configurado"
alias pwr-15w   2>/dev/null && echo "[OK] pwr-15w"  || echo "[ERROR] pwr-15w no configurado"
```

```
# Salida esperada
── Modo de energía ──
NV Power Mode: MAXN
0

── Frecuencia GPU ──
GPU CurrentFreq: 1300500000 Hz (máx: 1300000000 Hz)

── Aliases disponibles ──
[OK] pwr-maxn
[OK] pwr-30w
[OK] pwr-15w
```

> **Próximo paso:** El Capítulo 4 configura la memoria swap y ZRAM — el sistema de overflow de memoria que permite al Jetson manejar modelos cercanos a los 60 GB sin pánico del kernel.
