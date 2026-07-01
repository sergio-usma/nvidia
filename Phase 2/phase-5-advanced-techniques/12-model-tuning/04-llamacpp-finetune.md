# llama.cpp Fine-Tuning

Fine-tuning LLMs using llama.cpp's built-in training capabilities on Jetson AGX Orin.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Build llama.cpp with Training Support](#build-llamacpp-with-training-support)
- [Prepare Training Data](#prepare-training-data)
- [Fine-Tuning Process](#fine-tuning-process)
- [Model Conversion](#model-conversion)
- [Deployment](#deployment)

## Overview

llama.cpp supports fine-tuning through its `llama-train` tool. This method is ideal for:
- GGUF format base models
- Memory-efficient training
- Local experimentation

## Prerequisites

```bash
# Check current llama.cpp
llama-cli --version

# If not installed, clone and build
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build && cd build
cmake .. -DCMAKE_CUDA_ARCHITECTURES=87 -DGGML_CUDA=on -DLLAMA_BUILD_TRAINING=on
make -j$(nproc)
```

## Build llama.cpp with Training Support

```bash
# Clone with training support
cd llama.cpp
git pull

# Build with CUDA and training
mkdir build && cd build
cmake .. \
    -DCMAKE_CUDA_ARCHITECTURES=87 \
    -DGGML_CUDA=on \
    -DLLAMA_BUILD_TRAINING=on \
    -DLLAMA_BUILD_EXAMPLES=on

make -j$(nproc)

# Verify training binary
ls -la bin/llama-train*
```

## Prepare Training Data

### Training Data Format

llama.cpp training uses a simple text format:

```text
<prompt> Your prompt here
<answer> Your expected response here
<prompt> Another prompt
<answer> Another response
```

### Convert Alpaca to Training Format

```python
#!/usr/bin/env python3
"""Convert Alpaca JSON to llama.cpp training format."""

import json
import sys

def convert_to_llama_format(input_file, output_file):
    """Convert Alpaca JSON to llama.cpp training format."""
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    with open(output_file, 'w') as f:
        for item in data:
            instruction = item.get('instruction', '')
            input_text = item.get('input', '')
            output = item.get('output', '')
            
            # Combine instruction and input
            if input_text:
                prompt = f"{instruction}\n{input_text}"
            else:
                prompt = instruction
            
            # Write in llama.cpp format
            f.write(f"<prompt> {prompt}\n")
            f.write(f"<answer> {output}\n")
    
    print(f"Converted {len(data)} samples to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert.py input.json output.txt")
        sys.exit(1)
    
    convert_to_llama_format(sys.argv[1], sys.argv[2])
```

### Usage

```bash
python3 convert.py my_data.json train.txt
wc -l train.txt
```

## Fine-Tuning Process

### Basic Fine-Tuning Command

```bash
# Set CUDA device
export CUDA_VISIBLE_DEVICES=0

# Run training
./bin/llama-train \
    --model ~/models/mistral-7b-v0.1.gguf \
    --train-file train.txt \
    --val-file val.txt \
    --epochs 3 \
    --batch-size 4 \
    --learning-rate 0.0001 \
    --context-length 2048 \
    --threads 8 \
    --gpu-layers 99
```

### Training Parameters

| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `--model` | Base model path | GGUF file |
| `--train-file` | Training data | .txt file |
| `--val-file` | Validation data | Optional |
| `--epochs` | Training iterations | 3-5 |
| `--batch-size` | Samples per batch | 1-4 |
| `--learning-rate` | LR for optimizer | 1e-4 to 1e-5 |
| `--context-length` | Max context | 512-2048 |
| `--threads` | CPU threads | 8 |
| `--gpu-layers` | GPU layers | 99 |

### Advanced Options

```bash
# LoRA training
./bin/llama-train \
    --model ~/models/mistral-7b-v0.1.gguf \
    --train-file train.txt \
    --lora-r 16 \
    --lora-alpha 32 \
    --lora-dropout 0.05 \
    --epochs 3 \
    --batch-size 2

# Mixed precision (faster)
./bin/llama-train \
    --model ~/models/mistral-7b-v0.1.gguf \
    --train-file train.txt \
    --f16 \
    --epochs 3
```

### Monitoring Training

```bash
# Training progress
# Check loss values in output

# GPU usage
tegrastats

# CPU usage
htop
```

## Model Conversion

### After Training

llama.cpp training produces a checkpoint that needs conversion:

```bash
# Convert checkpoint to GGUF
./bin/llama-quantize \
    output/llama-model-*.gguf \
    output/llama-model-finetuned.q4_k_m \
    Q4_K_M
```

### Full Pipeline

```bash
# 1. Train
./bin/llama-train --model base.gguf --train-file data.txt

# 2. Convert
./bin/llama-export-gguf checkpoint.pt output.gguf

# 3. Quantize
./bin/llama-quantize output.gguf output-q4.gguf Q4_K_M
```

## Deployment

### Using llama.cpp Server

```bash
# Start server with fine-tuned model
llama-cli \
    -m output/llama-model-finetuned.q4_k_m.gguf \
    -ngl 99 \
    -c 2048 \
    --server \
    --port 8080

# Test
curl -X POST http://localhost:8080/completion \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Your instruction here", "n_predict": 256}'
```

### As API Service

```python
#!/usr/bin/env python3
"""Simple API using fine-tuned model."""

import subprocess
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Start llama.cpp server in background
# llama-cli -m model.gguf -ngl 99 --server --port 8080

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    prompt = data.get('prompt', '')
    
    # Call llama.cpp
    response = requests.post(
        'http://localhost:8080/completion',
        json={
            'prompt': prompt,
            'n_predict': 512,
            'temperature': 0.7
        }
    )
    
    return jsonify({'response': response.json()['content']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Troubleshooting

### Out of Memory

```bash
# Reduce batch size
--batch-size 1

# Reduce context length
--context-length 512

# Reduce GPU layers
--gpu-layers 40
```

### Slow Training

```bash
# Increase threads
--threads 16

# Use f16
--f16

# Check GPU utilization
nvtop
```

### Training Doesn't Converge

```bash
# Adjust learning rate
--learning-rate 0.00005

# More epochs
--epochs 5

# Check data format
head train.txt
```

## Alternative: Using Python Bindings

For more control, use Python with llama.cpp bindings:

```bash
pip3 install llama-cpp-python
```

```python
from llama_cpp import Llama

# Load fine-tuned model
llm = Llama(
    model_path="output/model.gguf",
    n_gpu_layers=99,
    n_ctx=2048
)

# Generate
output = llm(
    "Your prompt here",
    max_tokens=512,
    temperature=0.7
)

print(output['choices'][0]['text'])
```

## Next Steps

- [Unsloth Fine-tuning](./05-unsloth-finetune.md) for more efficient training
- [Model Evaluation](./10-evaluation.md) to test your fine-tuned model
