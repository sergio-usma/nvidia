# Verify Your System

Before starting any setup, run a complete health-check of your Jetson AGX Orin. This page gives you exact expected outputs for JetPack 6.2.2 and a one-shot script that catches mismatches.

---

## 1. OS and Kernel

```bash
cat /etc/os-release | grep -E "^(NAME|VERSION)="
uname -srm
```

Expected:
```
NAME="Ubuntu"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
Linux 5.15.185-tegra aarch64
```

---

## 2. JetPack Version

```bash
apt show nvidia-jetpack 2>/dev/null | grep -E "^(Package|Version)"
```

Expected:
```
Package: nvidia-jetpack
Version: 6.2.2+b24
```

---

## 3. L4T (Linux for Tegra)

```bash
cat /etc/nv_tegra_release
```

Expected:
```
# R36 (release), REVISION: 5.0, GCID: 40478484 ...
```

The `R36` line maps to JetPack 6.x. `REVISION: 5.0` = JetPack 6.2.

---

## 4. CUDA Compiler

```bash
nvcc --version
```

Expected:
```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on ...
Cuda compilation tools, release 12.6, V12.6.68
Build cuda_12.6.r12.6/compiler.34714021_0
```

---

## 5. cuDNN

```bash
dpkg -l libcudnn9 2>/dev/null | grep ^ii | awk '{print $2, $3}'
```

Expected:
```
libcudnn9-cuda-12  9.3.0.75-1+cuda12.6
```

Alternative (header check):
```bash
cat /usr/include/aarch64-linux-gnu/cudnn_version.h 2>/dev/null \
  | grep -E "CUDNN_(MAJOR|MINOR|PATCHLEVEL)" | head -3
```

Expected:
```
#define CUDNN_MAJOR 9
#define CUDNN_MINOR 3
#define CUDNN_PATCHLEVEL 0
```

---

## 6. TensorRT

```bash
dpkg -l | grep -E "^ii.*tensorrt " | awk '{print $2, $3}'
```

Expected:
```
tensorrt  10.3.0.30-1+cuda12.5
```

---

## 7. OpenCV

```bash
pkg-config --modversion opencv4 2>/dev/null || python3 -c "import cv2; print(cv2.__version__)"
```

Expected: `4.8.0`

---

## 8. GPU Visibility

```bash
ls /dev/nvhost-* 2>/dev/null | head -5
cat /sys/class/nvhost/nvhost-gpu/reload_notifier 2>/dev/null && echo "GPU accessible"
```

For a quick GPU compute check (if llama.cpp or PyTorch is installed):
```bash
# Quick CUDA presence check without Python
nvidia-smi 2>/dev/null || \
  cat /sys/bus/platform/devices/17000000.gpu/power/runtime_status 2>/dev/null || \
  echo "Use jtop or tegrastats to verify GPU"
```

> **Note:** `nvidia-smi` is not available on Jetson — the GPU is integrated. Use `jtop` or `tegrastats` instead.

---

## 9. Memory

```bash
free -h
```

Expected:
```
               total        used        free      shared  buff/cache   available
Mem:            61Gi       7.3Gi        20Gi       ...
```

Total should show ~62 GB. The ~2 GB difference from the 64 GB spec is reserved by the firmware.

---

## 10. Storage

```bash
df -h /
lsblk
```

Check that eMMC (`mmcblk0p1`) shows ~57 GB usable (64 GB eMMC minus partitions). If you have an NVMe SSD, it will appear as `nvme0n1`.

---

## 11. Install Monitoring Tools

These are not installed by default — install them now, you'll use them constantly:

```bash
# jtop: the essential Jetson dashboard
sudo pip3 install jetson-stats
sudo systemctl restart jtop.service 2>/dev/null || true

# Launch jtop
jtop
```

`jtop` shows CPU, GPU, memory, power, and temperature in one interactive view. Press `q` to quit.

```bash
# tegrastats: lightweight, pipe-friendly
tegrastats --interval 1000
# Ctrl+C to stop
```

---

## One-Shot Verification Script

Save this as `~/verify_system.sh` and run it any time you want a full health report:

```bash
cat > ~/verify_system.sh << 'EOF'
#!/bin/bash
set -euo pipefail

PASS="\e[32m✓\e[0m"
FAIL="\e[31m✗\e[0m"
WARN="\e[33m⚠\e[0m"

check() {
    local label="$1"
    local cmd="$2"
    local expected="$3"
    local actual
    actual=$(eval "$cmd" 2>/dev/null | tr -d '\n')
    if echo "$actual" | grep -q "$expected"; then
        echo -e "$PASS $label: $actual"
    else
        echo -e "$FAIL $label: got '$actual', expected '$expected'"
    fi
}

echo "=========================================="
echo " Jetson AGX Orin — System Verification"
echo " $(date)"
echo "=========================================="
echo ""

check "OS"        "cat /etc/os-release | grep VERSION_ID | cut -d= -f2 | tr -d '\"'" "22.04"
check "Kernel"    "uname -r"                                                            "tegra"
check "JetPack"   "apt show nvidia-jetpack 2>/dev/null | grep ^Version | awk '{print \$2}'" "6.2"
check "CUDA"      "nvcc --version | grep 'release' | awk '{print \$5}' | tr -d ','"    "12.6"
check "cuDNN"     "dpkg -l libcudnn9 2>/dev/null | grep ^ii | awk '{print \$3}'"       "9.3"
check "TensorRT"  "dpkg -l | grep '^ii.*tensorrt ' | awk '{print \$3}' | head -1"      "10.3"
check "OpenCV"    "pkg-config --modversion opencv4 2>/dev/null || echo 'not_found'"    "4.8"

echo ""
echo "--- Memory ---"
free -h | grep -E "^Mem"

echo ""
echo "--- Storage ---"
df -h / | tail -1

echo ""
echo "--- CPU ---"
echo "Cores: $(nproc)"
echo "Arch:  $(uname -m)"

echo ""
echo "--- Jetson Stats (tegrastats snapshot) ---"
timeout 2 tegrastats 2>/dev/null | head -1 || echo "tegrastats not available"

echo ""
echo "=========================================="
echo " Run 'jtop' for live GPU/power monitoring"
echo "=========================================="
EOF

chmod +x ~/verify_system.sh
~/verify_system.sh
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `nvcc: command not found` | `export PATH=/usr/local/cuda/bin:$PATH` (then add to `.bashrc`) |
| `pkg-config: opencv4 not found` | `sudo apt install libopencv-dev` |
| `libcudnn9` not found | `sudo apt install libcudnn9-cuda-12` |
| jtop shows `N/A` everywhere | Run `sudo systemctl restart jtop.service` |
| JetPack shows wrong version | Flash with SDK Manager to get JetPack 6.2.2 |

---

## Next Steps

Once all checks pass, proceed to **[Enable Maximum Performance](02-maximum-performance.md)** to unlock your Jetson's full 275 TOPS.
