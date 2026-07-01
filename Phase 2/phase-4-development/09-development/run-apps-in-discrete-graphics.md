# Run Applications with Discrete GPU

This guide explains how to configure applications to use the full GPU capabilities on your Jetson AGX Orin.

## Understanding Discrete GPU on Jetson

The Jetson AGX Orin is a SoC (System on a Chip) where CPU and GPU share the same silicon and unified memory. However, you can still configure applications to prioritize GPU acceleration.

## What is "Run with Discrete Graphics"?

In Ubuntu and GNOME, this option appears when the system detects multiple GPU drivers or powerful GPU architecture. On your Jetson:

1. **No weak integrated GPU**: You only have the Ampere GPU
2. **Power saving**: The system sometimes tries to render basic UI using fewer GPU resources
3. **Full acceleration**: Using discrete GPU mode forces maximum hardware acceleration

## Configure Desktop Files

Linux applications use `.desktop` files to define how they launch. Add `PrefersNonDefaultGPU` to force GPU acceleration.

### 1. Locate Application Files

Most desktop files are in `/usr/share/applications/`:

| Application | Desktop File |
|-------------|--------------|
| Firefox | `firefox.desktop` |
| VS Code | `code.desktop` |
| Brave | `brave-browser.desktop` |
| Chromium | `chromium-browser.desktop` |

### 2. Edit the Desktop File (Example: VS Code)

Copy to your local folder to avoid breaking system files:

```bash
cp /usr/share/applications/code.desktop ~/.local/share/applications/
nano ~/.local/share/applications/code.desktop
```

### 3. Add GPU Configuration

Find the `[Desktop Entry]` section and add:

```text
X-KDE-RunOnDiscreteGpu=true
PrefersNonDefaultGPU=true
```

## Browser-Specific Configuration

Even with GPU forced, browsers may need additional settings for hardware acceleration on ARM64:

### Brave/Chrome
1. Go to `chrome://flags`
2. Search for **"Override software rendering list"**
3. Enable it

### VS Code
If experiencing lag, launch with:

```bash
code --enable-gpu-rasterization --password-store=basic
```

## Verify GPU Usage

Monitor GPU usage in real-time:

```bash
# NVIDIA GPU stats
nvidia-smi

# Jetson-specific monitoring
jtop
```

Install jtop if not available:

```bash
sudo pip install jetson-stats
```

## Next Steps

- Use the [automation script](script-for-run-apps-in-discrete-graphics.md) to configure multiple apps
- Set up Docker GPU access for containers
