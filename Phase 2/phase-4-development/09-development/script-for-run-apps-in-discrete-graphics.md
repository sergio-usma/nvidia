# GPU Automation Scripts and Docker Configuration

This guide provides automation scripts and Docker configuration for GPU-accelerated applications on your Jetson AGX Orin.

## Python Script: Set GPU Apps

This script automatically configures multiple applications to use GPU acceleration.

### Save the Script

```python
import os
import shutil

# ==========================================================
# MODIFY THE APPS LIST HERE
# Use the .desktop filename (without path)
# ==========================================================
APPS_FOR_GPU = [
    "firefox.desktop",
    "code.desktop",
    "brave-browser.desktop",
    "chromium-browser.desktop"
]

# Standard Linux paths
SYSTEM_PATH = "/usr/share/applications/"
USER_PATH = os.path.expanduser("~/.local/share/applications/")

def configure_gpu():
    # Ensure user directory exists
    if not os.path.exists(USER_PATH):
        os.makedirs(USER_PATH)
        print(f"[+] Created directory: {USER_PATH}")

    for app in APPS_FOR_GPU:
        src = os.path.join(SYSTEM_PATH, app)
        dst = os.path.join(USER_PATH, app)

        if os.path.exists(src):
            # Copy original file to user space
            shutil.copy2(src, dst)
            
            with open(dst, "r") as f:
                lines = f.readlines()

            # Remove previous entries to avoid duplicates
            new_lines = [l for l in lines if "PrefersNonDefaultGPU" not in l and "X-KDE-RunOnDiscreteGpu" not in l]
            
            # Insert directives under [Desktop Entry]
            final_content = []
            for line in new_lines:
                final_content.append(line)
                if "[Desktop Entry]" in line:
                    final_content.append("PrefersNonDefaultGPU=true\n")
                    final_content.append("X-KDE-RunOnDiscreteGpu=true\n")

            with open(dst, "w") as f:
                f.writelines(final_content)
            
            print(f"[OK] Configured: {app} (Will prefer GPU)")
        else:
            print(f"[ERROR] Not found: {app} in {SYSTEM_PATH}")

if __name__ == "__main__":
    configure_gpu()
    print("\n[!] Log out and back in for changes to take effect.")
```

### Run the Script

```bash
python3 set_gpu_apps.py
```

### After Running

Log out and log back in. Applications will now prioritize GPU acceleration.

---

## Docker GPU Configuration

For Docker containers to use the Jetson's GPU, use the NVIDIA Container Runtime.

### Basic Docker Command

```bash
docker run -it --rm \
    --runtime nvidia \
    --network host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    image-name
```

### Docker Compose Template

```yaml
services:
  gpu-app:
    image: nvcr.io/nvidia/l4t-base:r36.5.0
    runtime: nvidia
    environment:
      - DISPLAY=${DISPLAY}
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=all
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### Set Default GPU Runtime

Make all containers use GPU by default:

1. Edit Docker daemon config:

```bash
sudo nano /etc/docker/daemon.json
```

2. Add configuration:

```json
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
```

3. Restart Docker:

```bash
sudo systemctl restart docker
```

## Verify GPU in Docker

Test GPU access in containers:

```bash
docker run --rm --runtime nvidia nvcr.io/nvidia/l4t-base:r36.5.0 nvidia-smi
```

## Jetson Memory Tip

With 64GB unified memory, use this flag to prevent memory limits:

```bash
docker run --memlock=-1 ...
```

## Next Steps

- Configure [individual apps](run-apps-in-discrete-graphics.md) manually
- Set up development environment with GPU support
