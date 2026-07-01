# Create a Large Swap File

Your Jetson has 64 GB of unified memory. That's enough for a 70B model at Q4_K_M (~40 GB), but leaves little room for the OS and other processes. A swap file on a fast NVMe SSD gives you a safe overflow zone without crashing.

---

## Swap Location Strategy

| Storage | Speed | Recommendation |
|---------|-------|----------------|
| NVMe SSD (e.g., Samsung 970 Evo) | ~2000 MB/s | ✅ Best — put swap here |
| eMMC (built-in 64 GB) | ~400 MB/s | ⚠️ OK if no NVMe |
| USB drive | ~100 MB/s | ❌ Too slow |

**If you have an NVMe SSD**, always create swap there. Using the eMMC for swap accelerates wear.

---

## Step 0: Check Where to Put the Swap

```bash
# See all block devices
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,ROTA

# Check free space on each
df -h
```

- **eMMC** appears as `mmcblk0` — mounted at `/`
- **NVMe** appears as `nvme0n1` — may be mounted at `/data` or similar

For this guide, use the best available location. Replace `/swapfile` with `/data/swapfile` if your NVMe is mounted at `/data`.

---

## Step 1: Verify Available Space

You need at least **55 GB free** on your target partition:

```bash
# Check the target partition (adjust path as needed)
df -h /          # eMMC root
df -h /data      # NVMe (if mounted)
```

---

## Step 2: Create the Swap File

A 50 GB swap file provides headroom for 70B+ models:

```bash
# Using fallocate (fast, preferred)
sudo fallocate -l 50G /swapfile

# If fallocate fails, fall back to dd (slower but always works)
# sudo dd if=/dev/zero of=/swapfile bs=1G count=50 status=progress
```

> If your NVMe is at `/data`, use `/data/swapfile` instead.

---

## Step 3: Secure and Format

```bash
# Restrict permissions (required by Linux — swap must be root-only)
sudo chmod 600 /swapfile

# Format as swap
sudo mkswap /swapfile
```

Expected output:
```
Setting up swapspace version 1, size = 50 GiB (53687087104 bytes)
no label, UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## Step 4: Enable Swap

```bash
sudo swapon /swapfile

# Verify it's active
sudo swapon --show
free -h
```

Expected (`free -h`):
```
               total        used        free
Mem:            61Gi       ...
Swap:           49Gi        0B         49Gi
```

---

## Step 5: Make It Permanent

```bash
# Add to fstab (survives reboots)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify the fstab entry
grep swap /etc/fstab
```

---

## Step 6: Tune Swappiness for LLM Workloads

Swappiness controls how eagerly Linux moves RAM pages to swap. For LLM inference you want to stay in RAM as long as possible:

```bash
# Apply immediately
sudo sysctl vm.swappiness=10

# Make permanent
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Also set these for better memory management under LLM load
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

| swappiness value | Behavior |
|-----------------|----------|
| 0 | Only swap when absolutely out of RAM |
| **10** | **Recommended for LLM workloads** |
| 60 | Linux default |
| 100 | Aggressive swapping |

---

## Step 7: Configure zram as a Second Layer (Optional)

`zram` creates a compressed RAM-based swap. It's faster than disk swap and helps when you have many small allocations alongside a large model:

```bash
# Install zram tools
sudo apt install zram-config -y

# Check status
sudo systemctl status zram-config

# Verify zram devices
swapon --show | grep zram
```

With zram + 50 GB NVMe swap, Linux prioritizes: RAM → zram (compressed RAM) → NVMe swap.

---

## Understanding Swap Performance Impact

| Model Size | Fits in RAM? | Inference Speed |
|-----------|-------------|----------------|
| 7B Q4_K_M (~4 GB) | Yes | 15–25 tok/s (no swap used) |
| 13B Q4_K_M (~8 GB) | Yes | 10–15 tok/s |
| 34B Q4_K_M (~20 GB) | Yes | 5–8 tok/s |
| 70B Q4_K_M (~40 GB) | Yes (64 GB) | 2–4 tok/s |
| 70B Q8_0 (~70 GB) | **No — uses swap** | 0.5–1 tok/s |

The 70B Q4_K_M fits in RAM — that's the recommended maximum for smooth inference.

---

## Remove Swap (If Needed)

```bash
sudo swapoff /swapfile
sudo rm /swapfile
# Remove the line from /etc/fstab
sudo sed -i '/swapfile/d' /etc/fstab
sudo sysctl -p
```

---

## Next Steps

- **[Install Essential Tools](04-essential-tools.md)** — Build toolchain and utilities
- **[Configure Shell](05-shell-configuration.md)** — Optimized `.bashrc` for AI development
