# System Monitoring with jtop

Monitor your Jetson's CPU, GPU, memory, and temperature in real-time.

## Install jtop

```bash
sudo pip install -U jetson-stats
sudo systemctl restart jtop
```

## Run jtop

```bash
jtop
```

## Navigation

- **Arrow keys**: Navigate between tabs
- **q**: Quit
- **1-5**: Jump to specific tab

## Tabs

| Tab | Shows |
|-----|-------|
| 1 | CPU, GPU, MEM summary |
| 2 | CPU details |
| 3 | GPU details |
| 4 | Memory details |
| 5 | System info |

## Understanding the Display

- **CPU**: 12 cores with frequency and usage
- **GPU**: GR3D frequency and utilization
- **MEM**: RAM and swap usage
- **Temperature**: Various sensors
- **Power**: Power consumption

## Monitor Specific Metrics

Quick check without interactive mode:

```bash
jtop -s
```

## Remote Monitoring

Run jtop in a specific mode:

```bash
jtop --fps 5  # 5 FPS refresh
```

## Using tegrastats

Alternative to jtop:

```bash
sudo tegrastats
```

Filter output:

```bash
sudo tegrastats | grep -E "RAM|GR3D_FREQ"
```

## Save Stats to File

```bash
sudo tegrastats --interval 500 --logfile stats.log
```

## Next Steps

- [LLM Monitoring](02-llm-monitoring.md)
- [Docker Cleanup](03-docker-cleanup.md)
