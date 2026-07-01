# System Updates and Package Management

This guide covers system updates, package management, and keeping your Jetson AGX Orin up to date with JetPack 6.2.2.

## Update Package Lists

```bash
sudo apt update
```

## Upgrade Installed Packages

```bash
sudo apt upgrade -y
```

## Full System Upgrade

```bash
sudo apt update && sudo apt full-upgrade -y
```

## Check JetPack Version

```bash
cat /etc/nv_tegra_release
```

Or:

```bash
nvcc --version
```

## NVIDIA Package Management

### List installed NVIDIA packages

```bash
dpkg -l | grep nvidia
```

### Reinstall NVIDIA packages

```bash
sudo apt install --reinstall nvidia-jetpack
```

### Update CUDA

```bash
sudo apt update
sudo apt install cuda-toolkit-12-6
```

## Kernel Updates

### Check current kernel

```bash
uname -r
```

### List available kernels

```bash
apt search linux-image | grep jetson
```

### Install new kernel

```bash
sudo apt install linux-image-unsigned-nvidia
sudo apt install linux-headers-nvidia
```

## Snap Package Management

### List snaps

```bash
snap list
```

### Refresh snaps

```bash
sudo snap refresh
```

### Remove unused snaps

```bash
snap list --all
sudo snap remove <package> --revision=<revision>
```

## Python Package Updates

### Upgrade pip

```bash
python3 -m pip install --upgrade pip
```

### List outdated packages

```bash
pip list --outdated
```

### Upgrade all packages

```bash
pip list --outdated | grep -v "^Package" | awk '{print $1}' | xargs -I {} pip install --upgrade {}
```

## Container Updates

### Update Docker images

```bash
docker images
docker pull nvcr.io/nvidia/l4t-pytorch:r36.2.0-pytorch2.1.0-py3
```

### Clean up old images

```bash
docker image prune -a
```

## Block Map Updates

### Update block map

```bash
sudo apt update
sudo apt install nvidia-l4t-kernel
```

## Update Device Tree

```bash
sudo apt install device-tree-compiler
sudo dtc -I dtb -O dts -o extracted.dts /boot/dtb/nvidia/*.dtb
```

## Create Update Script

```bash
#!/bin/bash
echo "Updating Jetson AGX Orin..."

# Update package lists
sudo apt update

# Upgrade packages
sudo apt upgrade -y

# Clean up
sudo apt autoremove -y
sudo apt autoclean

# Update Python packages
python3 -m pip install --upgrade pip setuptools wheel

# Show current versions
echo "=== System Versions ==="
cat /etc/nv_tegra_release
uname -r
nvcc --version 2>/dev/null || echo "CUDA not in PATH"

echo "Update complete!"
```

## Automatic Updates

Install unattended-upgrades:

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Troubleshooting Updates

### Package conflicts

```bash
sudo apt -f install
sudo dpkg --configure -a
```

### Hold specific packages

```bash
sudo apt-mark hold nvidia-l4t-kernel
```

### Release upgrades

```bash
sudo do-release-upgrade
```

## Backup Before Updates

Create system snapshot:

```bash
sudo apt install timeshift
sudo timeshift --create --comments "Before updates"
```

## Verify Installation

After updates, verify:

```bash
# NVIDIA components
dpkg -l | grep -E "nvidia|cuda"

# Kernel modules
lsmod | grep nvidia

# CUDA
nvcc --version
```
