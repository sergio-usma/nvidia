# Monitor LLM Execution

Monitor resource usage while running LLMs.

## Monitor with jtop

Run jtop in one terminal:

```bash
jtop
```

Run your LLM in another terminal. Watch:
- Memory usage (should increase when model loads)
- GPU utilization (should be high during inference)
- CPU usage

## Monitor with tegrastats

```bash
sudo tegrastats --interval 1000
```

Watch for:
- RAM usage
- GR3D_FREQ (GPU frequency)
- CPU frequencies

## Python Monitoring Script

Create `monitor_llm.py`:

```python
import subprocess
import time
import re

def get_stats():
    result = subprocess.run(['sudo', 'tegrastats'], capture_output=True, text=True)
    output = result.stdout
    
    # Parse RAM
    ram_match = re.search(r'RAM (\d+)/(\d+)MB', output)
    if ram_match:
        ram_used = int(ram_match.group(1))
        ram_total = int(ram_match.group(2))
        print(f"RAM: {ram_used}/{ram_total} MB ({100*ram_used/ram_total:.1f}%)")
    
    # Parse GPU
    gpu_match = re.search(r'GR3D_FREQ (\d+)%', output)
    if gpu_match:
        gpu_usage = int(gpu_match.group(1))
        print(f"GPU: {gpu_usage}%")

if __name__ == "__main__":
    print("Monitoring LLM... Press Ctrl+C to stop")
    while True:
        get_stats()
        time.sleep(1)
```

Run:

```bash
python3 monitor_llm.py
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Low GPU usage | Model on CPU only | Use GPU offloading |
| High memory | Model too large | Use smaller model/quantization |
| OOM killed | Out of memory | Reduce context, add swap |

## Performance Optimization

- Use MAXN mode: `sudo nvpmodel -m 0`
- Lock clocks: `sudo jetson_clocks`
- Close unnecessary apps

## Next Steps

- [Docker Cleanup](03-docker-cleanup.md)
- [Firewall Setup](../part-10-security/01-firewall-setup.md)
