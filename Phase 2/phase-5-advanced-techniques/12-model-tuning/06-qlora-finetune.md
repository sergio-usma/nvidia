# QLoRA Fine-Tuning

Memory-efficient fine-tuning using Quantized LoRA on Jetson AGX Orin.

## Table of Contents

- [What is QLoRA?](#what-is-qlora)
- [Why QLoRA on Jetson?](#why-qlora-on-jetson)
- [Setup](#setup)
- [Training Script](#training-script)
- [Configuration](#configuration)
- [Inference](#inference)

## What is QLoRA?

QLoRA combines:
- **Quantization**: Compresses base model to 4-bit
- **LoRA**: Trains small adapter matrices
- **Backpropagation**: Through quantized weights

This allows fine-tuning models that wouldn't normally fit in GPU memory.

## Why QLoRA on Jetson?

| Method | VRAM Required | Jetson Compatible |
|--------|---------------|-------------------|
| Full Fine-tuning | 64GB+ | No |
| LoRA | 24GB+ | Orin 64GB |
| QLoRA | 16GB+ | Orin 32GB+ |

## Setup

```bash
# Install required packages
pip3 install \
    transformers \
    peft \
    bitsandbytes \
    accelerate \
    datasets \
    trl \
    scipy
```

## Training Script

```python
#!/usr/bin/env python3
"""QLoRA Fine-tuning on Jetson."""

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
from trl import SFTTrainer
import json

# Model configuration - Using 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# Load model
print("Loading model with 4-bit quantization...")
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    trust_remote_code=True,
)
tokenizer.pad_token = tokenizer.eos_token

# Configure LoRA
lora_config = LoraConfig(
    r=16,  # LoRA rank
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

# Apply LoRA
print("Applying LoRA adapters...")
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Load dataset
with open('train_data.json', 'r') as f:
    data = json.load(f)

dataset = Dataset.from_list(data)

# Format prompts
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

# Training arguments
training_args = TrainingArguments(
    output_dir="qlora_output",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    save_total_limit=2,
    optim="adamw_torch",
    max_grad_norm=0.3,
    warmup_ratio=0.1,
    lr_scheduler_type="cosine",
)

# Trainer
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    args=training_args,
)

# Train
print("Starting QLoRA training...")
trainer.train()

# Save
print("Saving model...")
model.save_pretrained("qlora_finetuned")
tokenizer.save_pretrained("qlora_finetuned")
```

## Configuration

### 4-bit vs 8-bit

```python
# 4-bit (recommended for Jetson)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

# 8-bit (more accurate, more memory)
bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
)
```

### LoRA Rank

| Rank | Memory | Quality |
|------|--------|---------|
| 8 | Low | Good |
| 16 | Medium | Better |
| 32 | Higher | Best |

```python
# Small model on Jetson
lora_config = LoraConfig(r=8, lora_alpha=16)

# Larger model
lora_config = LoraConfig(r=16, lora_alpha=32)
```

### Target Modules

```python
# For Llama/Mistral
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]

# For Qwen
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

# For all linear layers
target_modules = "all-linear"
```

## Inference

### Load Fine-tuned Model

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load base model with quantization
base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=BitsAndBytesConfig(load_in_4bit=True),
    device_map="auto",
)

# Load LoRA adapters
model = PeftModel.from_pretrained(
    base_model,
    "qlora_finetuned",
    device_map="auto",
)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("qlora_finetuned")

# Generate
inputs = tokenizer("Your prompt here", return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=512)
print(tokenizer.decode(outputs[0]))
```

### Merge and Save

```python
# Merge adapters
merged_model = model.merge_and_unload()

# Save merged model
merged_model.save_pretrained("merged_model")
tokenizer.save_pretrained("merged_model")
```

## Jetson AGX Orin Optimizations

### Memory Management

```python
# Add to training script
import gc

# Clear cache periodically
gc.collect()
torch.cuda.empty_cache()

# Gradient checkpointing
model.gradient_checkpointing_enable()
```

### Mixed Precision

```python
# Use FP16
training_args = TrainingArguments(
    fp16=True,
    bf16=False,
)

# Or BF16 (if supported)
training_args = TrainingArguments(
    bf16=True,
)
```

### Batch Size Optimization

```python
# For 64GB Orin
training_args = TrainingArguments(
    per_device_train_batch_size=4,
    gradient_accumulation_steps=2,
)

# For 32GB Orin
training_args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
)
```

## Complete Example with Your Models

```python
#!/usr/bin/env python3
"""Fine-tune Qwen3 Coder with QLoRA."""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import json

# QLoRA config for code model
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# Load Qwen model
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    quantization_config=bnb_config,
    device_map="auto",
)

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")

# LoRA for coding
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Load your code dataset
with open('code_data.json', 'r') as f:
    data = json.load(f)

dataset = Dataset.from_list(data)

# Format for code
def format_code(examples):
    texts = []
    for instruction, output in zip(examples['instruction'], examples['output']):
        text = f"""<|im_start|>system
You are a code expert.<|im_end>
<|im_start|>user
{instruction}<|im_end>
<|im_start|>assistant
{output}<|im_end>"""
        texts.append(text)
    return {'text': texts}

dataset = dataset.map(format_code, batched=True)

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=1024,
    args=TrainingArguments(
        output_dir="qwen_coder_qlora",
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=True,
    ),
)

trainer.train()
model.save_pretrained("qwen_coder_finetuned")
```

## Next Steps

- [Custom Datasets](./07-custom-datasets.md) - Create your training data
- [Model Evaluation](./10-evaluation.md) - Test your fine-tuned model
