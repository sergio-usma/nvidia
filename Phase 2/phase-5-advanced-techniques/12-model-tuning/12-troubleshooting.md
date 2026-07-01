# Troubleshooting Guide

Common issues and solutions for fine-tuning on Jetson AGX Orin.

## Out of Memory (OOM)

### Symptoms
- `CUDA out of memory` error
- Training crashes randomly

### Solutions

```python
# 1. Reduce batch size
per_device_train_batch_size=1

# 2. Reduce sequence length
max_seq_length=512

# 3. Enable gradient checkpointing
gradient_checkpointing=True

# 4. Use more quantization
load_in_4bit=True

# 5. Clear cache
import gc
gc.collect()
torch.cuda.empty_cache()
```

### Commands
```bash
# Check memory
tegrastats | grep RAM

# Monitor
watch -n 1 nvidia-smi
```

## CUDA Not Available

### Symptoms
- `CUDA not available` error

### Solutions

```bash
# Check CUDA
python3 -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch with CUDA
pip3 uninstall torch
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify
nvidia-smi
```

## Slow Training

### Symptoms
- Training takes very long

### Solutions

```bash
# Increase batch size
per_device_train_batch_size=4

# Use mixed precision
fp16=True

# Enable TF32
with torch.cuda.amp.autocast():
    # training code

# Use gradient checkpointing
gradient_checkpointing=True
```

## Model Not Learning

### Symptoms
- Loss doesn't decrease
- No improvement in outputs

### Solutions

```python
# Increase learning rate
learning_rate=1e-4

# More epochs
num_train_epochs=5

# Check data format
print(dataset[0])

# Verify tokenizer
print(tokenizer.decode(outputs[0]))
```

## Checkpoint Saving Issues

```python
# Save more frequently
save_strategy="steps"
save_steps=100

# Limit saved checkpoints
save_total_limit=2
```

## Data Format Errors

```python
# Validate dataset
print(dataset[0])
print(dataset.features)

# Check for nulls
dataset.filter(lambda x: x['instruction'] is not None)
```

## Hardware Issues

```bash
# Check GPU
nvidia-smi

# Jetson-specific
sudo nvpmodel -m 0
sudo jetson_clocks

# Check thermals
tegrastats
```

## Getting Help

1. Check [Unsloth docs](https://unsloth.ai)
2. Check [llama.cpp docs](https://github.com/ggerganov/llama.cpp)
3. Check NVIDIA forums for Jetson-specific issues
