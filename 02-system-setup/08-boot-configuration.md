# Boot Configuration and Optimization

This guide covers Jetson AGX Orin boot configuration, including boot order, bootloader settings, and startup optimization.

## Boot Process Overview

1. BootROM (internal)
2. MB1 bootloader (T234)
3. MB2 bootloader
4. UEFI firmware
5. Linux kernel
6. init system (systemd)

## Enter Recovery Mode

For flashing or recovery:

1. Power off the device
2. Press and hold Force Recovery button
3. Press Power button
4. Release Force Recovery button

Verify:

```bash
lsusb | grep NVIDIA
```

## Boot Configuration

View current boot settings:

```bash
sudo efibootmgr -v
```

Set boot order:

```bash
sudo efibootmgr -o 0000,0001,0002
```

## Boot from External SSD

Flash to external SSD:

```bash
sudo ./flash.sh -d ./ bootloader/boot_config.cfg jetson-agx-orin-devkit-qspi-ssd external
```

Or use SDK Manager with "NVMe" target.

## Boot Optimization

### Disable unnecessary services

```bash
sudo systemctl disable bluetooth.service
sudo systemctl disable cups.service
sudo systemctl disable snapd.service
```

### Fast boot kernel parameters

Edit GRUB:

```bash
sudo nano /etc/default/grub
```

Add to `GRUB_CMDLINE_LINUX_DEFAULT`:

```
quiet splash loglevel=3 quiet
```

Update GRUB:

```bash
sudo update-grub
```

## Boot Time Measurement

```bash
systemd-analyze time
systemd-analyze plot > boot.svg
```

## Startup Services Analysis

```bash
systemd-analyze blame | head -20
```

Disable slow services:

```bash
sudo systemctl mask systemd-journal-flush
```

## UEFI Settings

Access UEFI setup:

```bash
sudo efibootmgr --bootnext 0
sudo systemctl reboot --firmware-setup
```

## NVMe Boot Setup

Create boot configuration:

```bash
sudo mke2fs -t ext4 /dev/nvme0n1p1
sudo mkdir /mnt/nvme
sudo mount /dev/nvme0n1p1 /mnt/nvme
```

Clone rootfs:

```bash
sudo rsync -axHAW --exclude='/proc' --exclude='/sys' --exclude='/dev' --exclude='/run' --exclude='/boot' / /mnt/nvme/
```

Update fstab:

```bash
sudo blkid /dev/nvme0n1p1
sudo nano /mnt/nvme/etc/fstab
```

## Boot Security

Disable unused boot options:

```bash
sudo efibootmgr -B -b 0001
```

Secure boot (if configured):

```bash
sudo sbctl status
```

## Troubleshooting Boot Issues

### Boot stuck at logo

```bash
# Add to kernel parameters
nvidia.no_powergating
```

### Kernel panic

```bash
# Boot to recovery
sudo ./flash.sh --rcm jetson-agx-orin-devkit recovery
```

### Disk full causing boot issues

```bash
journalctl --disk-usage
sudo journalctl --vacuum-size=100M
```
