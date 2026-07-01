# USB Device Configuration

This guide covers USB device configuration for Jetson AGX Orin, including peripheral setup, power management, and device troubleshooting.

## USB Ports Overview

The Jetson AGX Orin Developer Kit provides multiple USB ports:
- 2x USB 3.2 Gen 2 (10 Gbps) - Type-A
- 2x USB Type-C (with USB Power Delivery)
- 1x Micro-USB (recovery mode)

## Checking USB Devices

```bash
lsusb
lsusb -t
```

## USB Power Management

Disable USB autosuspend for stable operation:

```bash
echo -1 | sudo tee /sys/bus/usb/devices/*/power/autosuspend_delay_ms
echo on | sudo tee /sys/bus/usb/devices/*/power/control
```

Make persistent:

```bash
sudo bash -c 'cat > /etc/udev/rules.d/99-usb-power.rules << EOF
ACTION=="add", SUBSYSTEM=="usb", RUN+="/bin/sh -c 'echo on > /sys$DEVPATH/power/control'"
EOF'
```

## USB Device Permissions

Create udev rules for device access:

```bash
sudo bash -c 'cat > /etc/udev/rules.d/50-myusb.rules << EOF
# Camera devices
SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", MODE="0666"
# Arduino/Serial devices
SUBSYSTEM=="usb", ATTR{idVendor}=="2341", MODE="0666"
# FTDI devices
SUBSYSTEM=="usb", ATTR{idVendor=="0403", MODE="0666"
EOF'
```

Reload rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## USB Camera Setup

Check available video devices:

```bash
v4l2-ctl --list-devices
```

Test camera:

```bash
 Cheese or
guvcview
```

## USB Storage

Mount USB drive:

```bash
sudo mkdir /mnt/usb
sudo mount /dev/sda1 /mnt/usb
```

Add to fstab for auto-mount:

```bash
UUID=xxx /mnt/usb ext4 defaults,nofail 0 2
```

## Troubleshooting

### Device not recognized

```bash
dmesg | grep -i usb
ls /dev/ttyUSB*
```

### USB bandwidth issues

```bash
lsusb -v 2>/dev/null | grep -i bandwidth
```

### Reset USB hub

```bash
echo "0" | sudo tee /sys/bus/usb/devices/usb1/authorized
sleep 2
echo "1" | sudo tee /sys/bus/usb/devices/usb1/authorized
```
