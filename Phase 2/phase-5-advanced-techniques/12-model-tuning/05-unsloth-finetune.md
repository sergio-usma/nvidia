# Unsloth Fine-Tuning

Fast and memory-efficient fine-tuning using Unsloth on Jetson AGX Orin.

## Table of Contents

- [What is Unsloth?](#what-is-unsloth)
- [Installation](#installation)
- [Dataset Preparation](#dataset-preparation)
- [Fine-Tuning Script](#fine-tuning-script)
- [Training Parameters](#training-parameters)
- [Monitoring](#monitoring)
- [Saving and Exporting](#saving-and-exporting)

## What is Unsloth?

Unsloth is a fast fine-tuning library that provides:
- **2x faster training** than standard methods
- **60% less memory** usage
- **No quality loss** compared to full fine-tuning
- Supports LoRA, QLoRA, and full fine-tuning

## Installation

### Install Dependencies

```bash
# Create virtual environment
python3 -m venv finetune_env
source finetune_env/bin/activate

# Install PyTorch (CUDA 12.x)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Unsloth
pip3 install unsloth

# Install other dependencies
pip3 install \
    transformers \
    datasets \
    peft \
    accelerate \
    bitsandbytes \
    trl \
    scipy \
    sentencepiece \
    protobuf
```

### Verify Installation

```bash
python3 << 'EOF'
import unsloth
print(f"Unsloth version: {unsloth.__version__}")

# Check GPU
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
EOF
```

## Dataset Preparation

### Load from JSON

```python
from datasets import Dataset
import json

# Load from JSON
with open('data.json', 'r') as f:
    data = json.load(f)

# Convert to Dataset
dataset = Dataset.from_list(data)
print(f"Dataset size: {len(dataset)}")

# Preview
print(dataset[0])
```

### Load from CSV

```python
from datasets import Dataset

# Load from CSV
dataset = Dataset.from_csv('data.csv')
print(f"Dataset size: {len(dataset)}")
```

### Format for Training

```python
def format_prompts(examples):
    """Format prompts for instruction tuning."""
    
    texts = []
    for instruction, input_text, output in zip(
        examples['instruction'],
        examples.get('input', [''] * len(examples['instruction'])),
        examples['output']
    ):
        # Alpaca format
        if input_text:
            text = f"""Below is an instruction that describes a task, paired with an input. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Input:
{input_text}

### Response:
{output}"""
        else:
            text = f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Response:
{output}"""
        
        texts.append(text)
    
    return {'text': texts}

# Apply formatting
dataset = dataset.map(format_prompts, batched=True)
```

## Fine-Tuning Script

### Basic Script

```python
#!/usr/bin/env python3
"""Fine-tune using Unsloth."""

from unsloth import FastLanguageModel
import torch
from datasets import Dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import json

# Configuration
max_seq_length = 2048
dtype = None
load_in_4bit = True

# Load model and tokenizer
print("Loading model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/mistral-7b-bf16",
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
)

# Add LoRA adapters
print("Adding LoRA adapters...")
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing=True,
)

# Load dataset
print("Loading dataset...")
with open('train_data.json', 'r') as f:
    data = json.load(f)

dataset = Dataset.from_list(data)

def format_prompts(examples):
    texts = []
    for instruction, input_text, output in zip(
        examples['instruction'],
        examples.get('input', [''] * len(examples['instruction'])),
        examples['output']
    ):
        if input_text:
            text = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Response:
{output}"""
        else:
            text = f"""### Instruction:
{instruction}

### Response:
{output}"""
        texts.append(text)
    return {'text': texts}

dataset = dataset.map(format_prompts, batched=True)

# Trainer
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    training_arguments=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        save_strategy="epoch",
        save_total_limit=2,
        output_dir="output",
        optim="adamw_torch",
    ),
)

# Train
print("Starting training...")
trainer.train()

# Save
print("Saving model...")
model.save_pretrained("finetuned_model")
tokenizer.save_pretrained("finetuned_model")
print("Done!")
```

### Run Training

```bash
# Set CUDA device
export CUDA_VISIBLE_DEVICES=0

# Run script
python3 finetune.py
```

## Training Parameters

### Key Parameters

| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `r` | LoRA rank | 8-64 |
| `lora_alpha` | LoRA scaling | 2x rank |
| `lora_dropout` | Regularization | 0-0.1 |
| `learning_rate` | Training LR | 1e-4 to 5e-4 |
| `num_train_epochs` | Epochs | 3-5 |
| `per_device_batch_size` | Batch size | 1-4 |
| `gradient_accumulation_steps` | Accumulation | 4-8 |

### Memory Optimization

```python
# For Jetson AGX Orin 64GB
training_arguments = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    gradient_checkpointing=True,
    fp16=True,
    max_seq_length=2048,
)

# For Jetson AGX Orin 32GB
training_arguments = TrainingArguments(
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    gradient_checkpointing=True,
    fp16=True,
    max_seq_length=1024,
    load_in_4bit=True,
)
```

## Monitoring

### During Training

```bash
# Terminal 1: Monitor GPU
tegrastats

# Terminal 2: Training logs
tail -f output/trainer_state.json
```

### Checkpoint Interruption

```python
# Resume from checkpoint
trainer.train(resume_from_checkpoint=True)

# Or from specific checkpoint
trainer.train(resume_from_checkpoint="output/checkpoint-1000")
```

## Saving and Exporting

### Save LoRA Adapters

```python
# Save adapters only (small, ~100MB)
model.save_pretrained("lora_adapters")
tokenizer.save_pretrained("lora_adapters")

# Load later
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/mistral-7b-bf16",
    adapter_name="lora_adapters"
)
```

### Merge and Export to GGUF

```python
# Merge adapters with base model
merged_model = model.merge_and_unload()

# Save as HF format
merged_model.save_pretrained("merged_model")
tokenizer.save_pretrained("merged_model")

# Convert to GGUF (using llama.cpp)
# First, export to safetensors
merged_model.save_pretrained("model", safe_serialization=True)

# Then convert with llama.cpp
# ./convert-hf-to-gguf model/
```

### Export to Ollama

```python
# Save in GGUF format
# Then create Modelfile

# Create Modelfile
with open('Modelfile', 'w') as f:
    f.write(f"FROM ./finetuned_model.gguf\n")
    f.write("TEMPLATE \"\"\"{{.System}}\n\n### Instruction:\n{{.Instruction}}\n\n### Response:\n{{.Response}}\n\"\"\"")

# Import to Ollama
import subprocess
subprocess.run(['ollama', 'create', 'my-model', '-f', 'Modelfile'])
```

## Using Your Fine-Tuned Model

### Python Inference

```python
from unsloth import FastLanguageModel

# Load model
model, tokenizer = FastLanguageModel.from_pretrained(
    "finetuned_model",
    load_in_4bit=False,
)

FastLanguageModel.for_inference(model)

# Generate
messages = [{"role": "user", "content": "Your instruction here"}]
inputs = tokenizer.apply_chat_template(messages, tokenize=True, return_tensors="pt").cuda()

outputs = model.generate(
    input_ids=inputs,
    max_new_tokens=512,
    temperature=0.7,
)

print(tokenizer.decode(outputs[0]))
```

### llama.cpp Server

```bash
# Convert to GGUF and run
llama-cli -m finetuned_model.gguf -ngl 99 -c 2048 --server --port 8080
```

## Troubleshooting

### Out of Memory

```python
# Reduce batch size
per_device_train_batch_size=1

# Reduce sequence length
max_seq_length=1024

# Enable gradient checkpointing
gradient_checkpointing=True
```

### Slow Training

```bash
# Check GPU utilization
nvtop

# Increase batch size if VRAM allows
per_device_train_batch_size=4
```

### Training Doesn't Converge

```python
# Adjust learning rate
learning_rate=1e-4

# More epochs
num_train_epochs=5

# Check data quality
print(dataset[0])
```

## Next Steps

- [QLoRA Fine-tuning](./06-qlora-finetune.md) for even more memory efficiency
- [Custom Datasets](./07-custom-datasets.md) for advanced dataset handling
