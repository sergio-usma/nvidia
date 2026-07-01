# Thermal Management

This guide covers thermal management for Jetson AGX Orin, including monitoring, cooling solutions, and thermal throttling prevention.

## Understanding Thermal Behavior

Jetson AGX Orin thermal zones:
- CPU (0-4)
- GPU
- DDR
- PMIC
- Tboard

View temperatures:

```bash
cat /sys/class/thermal/thermal_zone*/temp
```

Or use:

```bash
tegrastats --interval 1000
```

## Thermal Zones and Thresholds

| Zone | Warning | Critical | Thermal Throttling |
|------|---------|----------|-------------------|
| CPU | 80°C | 85°C | Yes at 85°C |
| GPU | 80°C | 85°C | Yes at 85°C |
| DDR | 80°C | 85°C | No |
| PMIC | 90°C | 95°C | No |

## Cooling Solutions

### Stock fan control

```bash
# Manual fan control
sudo bash -c 'echo 255 > /sys/devices/pwm-fan/target_pwm'

# Auto mode
sudo bash -c 'echo 0 > /sys/devices/pwm-fan/target_pwm'
```

### PWM fan curve

Create thermal configuration:

```bash
sudo nano /etc/thermal.conf
```

```ini
[Thermals]
zone0=CPU
zone1=GPU
zone2=DDR

[FanCurve]
pwm0=0
temp0=40000
pwm1=50
temp1=50000
pwm2=100
temp2=70000
pwm3=200
temp3=80000
```

## Performance Mode Impact

MAXN mode generates more heat:

```bash
sudo nvpmodel -m 0    # 15W, 6 cores
sudo nvpmodel -m 1    # 15W, 4 cores
sudo nvpmodel -m 2    # 10W, 2 cores
sudo nvpmodel -m 3    # 10W, 2 cores
sudo nvpmodel -m 4    # 7W,  1 core
```

Monitor during workloads:

```bash
watch -n 1tegrastats
```

## Thermal Throttling Prevention

### Airflow optimization

- Position device with clearance
- Use vertical stand
- Avoid enclosed spaces

### External cooling

```bash
# Install 120mm fan
# Connect to 5V PWM fan
# Control via GPIO
```

### Heatsink upgrade

Consider:
- Larger heatsink
- Active cooling with PWM fan
- Water cooling (advanced)

## Temperature Monitoring Script

```python
#!/usr/bin/env python3
import os
import time

def get_temps():
    zones = {}
    for zone in os.listdir('/sys/class/thermal'):
        if zone.startswith('thermal_zone'):
            temp = int(open(f'/sys/class/thermal/{zone}/temp').read())
            type_name = open(f'/sys/class/thermal/{zone}/type').read().strip()
            zones[type_name] = temp / 1000
    return zones

while True:
    temps = get_temps()
    print(f"CPU: {temps.get('CPU-therm', 0):.1f}°C | GPU: {temps.get('GPU-therm', 0):.1f}°C | DDR: {temps.get('DDR-therm', 0):.1f}°C")
    time.sleep(2)
```

## Kernel Thermal Settings

View current settings:

```bash
cat /sys/devices/virtual/thermal/thermal_zone*/trip_point_*_temp
```

Adjust trip points (not recommended):

```bash
sudo echo 85000 > /sys/devices/virtual/thermal/thermal_zone0/trip_point_1_temp
```

## Thermal Logs

Check for throttling events:

```bash
dmesg | grep -i thermal
journalctl -k | grep -i thermal
```

## Cooling for AI Workloads

For LLM inference, prioritize GPU cooling:

```bash
# Monitor GPU specifically
tegrastats --interval 100 | grep -i gpu
```

Add cooling during AI tasks:

```bash
# Run with fans at max
sudo bash -c 'echo 255 > /sys/devices/pwm-fan/target_pwm'

# Script to auto-adjust
while true; do
    TEMP=$(cat /sys/class/thermal/thermal_zone1/temp)
    if [ $TEMP -gt 75000 ]; then
        echo 255 > /sys/devices/pwm-fan/target_pwm
    elif [ $TEMP -gt 60000 ]; then
        echo 150 > /sys/devices/pwm-fan/target_pwm
    else
        echo 50 > /sys/devices/pwm-fan/target_pwm
    fi
    sleep 5
done
```

## Temperature-Based Performance Scaling

```python
#!/usr/bin/env python3
import subprocess
import time
import threading

FAN_PATH = '/sys/devices/pwm-fan/target_pwm'
TEMP_THRESHOLDS = [
    (45000, 30),
    (55000, 80),
    (65000, 150),
    (75000, 200),
    (85000, 255),
]

def get_gpu_temp():
    result = subprocess.run(
        ['tegrastats', '--interval', '100'],
        capture_output=True, text=True
    )
    for line in result.stdout.split('\n'):
        if 'GPU' in line:
            temp = int(line.split('GPU ')[1].split('C')[0])
            return temp * 1000
    return 45000

def set_fan(speed):
    with open(FAN_PATH, 'w') as f:
        f.write(str(speed))

def adjust_fan():
    temp = get_gpu_temp()
    for threshold, speed in TEMP_THRESHOLDS:
        if temp >= threshold:
            set_fan(speed)

while True:
    adjust_fan()
    time.sleep(5)
```
