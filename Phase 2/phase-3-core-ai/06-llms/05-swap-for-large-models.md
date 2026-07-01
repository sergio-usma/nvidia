# Configure Swap for Large Models

Learn how to configure swap for running 70B+ models on your 64GB Jetson.

## Why Swap Is Needed

Even with 64GB RAM, some 70B+ models with quantization still require additional memory for:
- Loading all model weights
- Context processing
- KV cache

## Create Swap File

Follow the instructions in [Part 1: Swap File](../part-1-system-setup/03-swap-file.md) to create a 50GB swap file.

## Optimize Swappiness

Set swappiness lower to prefer RAM over swap:

```bash
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

## Running 70B Models

### With llama.cpp

```bash
./llama-cli \
    --model ~/models/70b-model-Q4_K_M.gguf \
    --ctx-size 8192 \
    --n-gpu-layers 40 \
    --flash-attn
```

Start with fewer GPU layers and increase if memory allows.

### Recommended Settings for 70B

| Parameter | Value | Notes |
|-----------|-------|-------|
| `--n-gpu-layers` | 30-50 | Adjust based on free memory |
| `--ctx-size` | 4096-8192 | Larger = more memory |
| `--batch-size` | 512 | Adjust for performance |

## Monitor Memory Usage

Use jtop to monitor:

```bash
jtop
```

Watch the RAM and GPU memory usage while loading the model.

## Troubleshooting OOM

If you get Out of Memory errors:

1. Reduce `--ctx-size` to 4096
2. Reduce `--n-gpu-layers`
3. Use more aggressive quantization (Q3 instead of Q4)
4. Close other applications

## When Swap Helps

Swap is useful for:
- Temporary memory spikes
- Loading multiple models
- Very large context sizes

Swap is slower than RAM but prevents crashes.

## Next Steps

- [Audio Setup](../part-6-speech-audio/01-audio-hdmi.md)
- [Whisper STT](../part-6-speech-audio/02-whisper-stt.md)
