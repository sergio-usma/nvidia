# Enable Maximum Performance Mode

Your Jetson AGX Orin 64GB is rated at **275 TOPS** — but it only reaches that number in MAXN mode with clocks locked. This guide gets you there and verifies it.

---

## Why This Matters for AI

Without MAXN + jetson_clocks:
- GPU runs at ~600 MHz (thermal-safe default)
- LLM inference: ~8 tokens/sec on a 7B model

With MAXN + jetson_clocks:
- GPU runs at 1300 MHz (maximum)
- LLM inference: ~18-25 tokens/sec on the same model
- **~3x performance difference**

---

## Step 1: Check Current Mode

```bash
sudo nvpmodel -q
```

Sample output:
```
NVPM WARN: ...
NV Power Mode: MAXN
0
```

The number at the bottom is the active mode ID.

---

## Step 2: View All Available Modes

```bash
sudo nvpmodel -q --verbose | grep -A1 "MODE_NAME"
```

Full power mode table for Jetson AGX Orin 64GB (JetPack 6.2):

| Mode ID | Name | TDP | CPU Cores Active | GPU Max Freq |
|---------|------|-----|-----------------|--------------|
| **0** | **MAXN** | **No limit (~60W)** | **12** | **1300 MHz** |
| 1 | MODE_50W | 50 W | 12 | 1100 MHz |
| 2 | MODE_30W | 30 W | 8 | 854 MHz |
| 3 | MODE_15W | 15 W | 4 | 612 MHz |

> **Use Mode 0 (MAXN)** for all AI workloads in this tutorial.

---

## Step 3: Switch to MAXN

```bash
sudo nvpmodel -m 0
```

This change **survives reboots** — it writes to `/etc/nvpmodel.conf`.

---

## Step 4: Lock Clocks at Maximum

```bash
sudo jetson_clocks
```

This sets every clock (CPU, GPU, EMC memory bus) to its maximum frequency. The change is **temporary** — it resets after reboot.

---

## Step 5: Verify Settings

```bash
# Confirm power mode
sudo nvpmodel -q

# Check GPU and CPU frequencies
sudo jetson_clocks --show
```

`jetson_clocks --show` output includes lines like:
```
CPU Cluster Switching: Disabled
cpu0: Online=1 Governor=schedutil MinFreq=729600 MaxFreq=2201600 CurrentFreq=2201600 ...
GPU MinFreq=306000000 MaxFreq=1300500000 CurrentFreq=1300500000
EMC MinFreq=204000000 MaxFreq=3199000000 CurrentFreq=3199000000
```

`CurrentFreq` should equal `MaxFreq` on all lines.

---

## Step 6: Make jetson_clocks Permanent

The `jetson_clocks` systemd service runs it at boot. Enable it once:

```bash
sudo systemctl enable nvargus-daemon 2>/dev/null || true
sudo systemctl enable jetson_clocks 2>/dev/null || echo "Service not found, creating..."
```

If the service doesn't exist (some JetPack versions), create it:

```bash
sudo tee /etc/systemd/system/jetson_clocks.service > /dev/null << 'EOF'
[Unit]
Description=Lock Jetson clocks at maximum frequency
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/jetson_clocks
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jetson_clocks
sudo systemctl start jetson_clocks
sudo systemctl status jetson_clocks
```

---

## Verify Performance: Quick Benchmark

After enabling MAXN, run this to confirm real-world AI throughput:

```bash
# Requires Ollama container running (covered in Phase 3)
# If you haven't set up Ollama yet, come back to this after Phase 3-06

# Benchmark: time to generate 100 tokens with a 3B model
docker exec ollama ollama run llama3.2 \
  --verbose \
  "Write a 100-word story about a robot" 2>&1 | grep -E "eval rate|tokens/s"
```

Expected in MAXN mode: **25–40 tokens/sec** for llama3.2 (3B Q4_K_M).

---

## Monitor Power and Temperature During Inference

Open a second terminal and run while a model is working:

```bash
# Option A: tegrastats (every second)
tegrastats --interval 1000

# Option B: jtop (interactive dashboard)
jtop
```

In `tegrastats` output, look for:
- `GPU@XXX°C` — GPU temperature (should stay below 85°C)
- `POM_5V_GPU Xm/Ym` — GPU power draw in milliwatts
- `Tboard@XXX` — board temperature

---

## Performance vs Power: When to Use Each Mode

| Situation | Recommended Mode | Command |
|-----------|-----------------|---------|
| LLM inference (7B–70B) | MAXN (0) | `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| Vision/video processing | MAXN (0) | same |
| Compiling code (llama.cpp etc.) | MAXN (0) | same |
| Idle / light development | MODE_30W (2) | `sudo nvpmodel -m 2` |
| Power-saving background tasks | MODE_15W (3) | `sudo nvpmodel -m 3` |

---

## Thermal Safety

MAXN mode is designed for the AGX Orin's cooling solution. The active fan will spin up automatically. Normal operating temperatures under sustained AI load:

| Component | Normal | Throttle Starts | Emergency |
|-----------|--------|----------------|-----------|
| GPU | 50–75°C | ~85°C | ~95°C |
| CPU | 45–70°C | ~85°C | ~95°C |
| Board | 40–60°C | — | — |

If you see throttling (`throttle=1` in `tegrastats`), ensure the ventilation vents on the AGX module are not blocked.

---

## Next Steps

- **[Create Swap File](03-swap-file.md)** — Required before loading 70B models
- **[Install Essential Tools](04-essential-tools.md)** — Build tools and utilities
