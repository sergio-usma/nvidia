# Code Model Fine-Tuning

Fine-tuning LLMs specifically for code generation tasks.

## Table of Contents

- [Best Models for Code](#best-models-for-code)
- [Code Datasets](#code-datasets)
- [Training Script](#training-script)
- [Prompt Templates](#prompt-templates)
- [Testing](#testing)

## Best Models for Code

| Model | Strengths | VRAM |
|-------|-----------|------|
| Qwen3 Coder | General coding | 16GB |
| codeqwen | Code tasks | 16GB |
| StarCoder2 | Multi-language | 24GB |
| DeepSeek Coder | Code + Math | 24GB |

## Code Datasets

### Public Code Datasets

```python
from datasets import load_dataset

# CodeAlpaca
code_alpaca = load_dataset("sahil2801/CodeAlpaca-20k")

# Python datasets
python_ds = load_dataset("smangrul/python-code-50k-train")

# Multi-language
multi_code = load_dataset("codeparrot/code-20k")
```

### Your Own Code Data

```json
[
  {
    "instruction": "Write a Python function to calculate factorial",
    "input": "",
    "output": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"
  },
  {
    "instruction": "Create a REST API endpoint",
    "input": "Python with FastAPI",
    "output": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/items/{item_id}')\ndef read_item(item_id: int):\n    return {'item_id': item_id}"
  }
]
```

## Training Script

```python
#!/usr/bin/env python3
"""Fine-tune for code generation."""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from unsloth import FastLanguageModel
from datasets import Dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import json

# Configuration
model_name = "Qwen/Qwen2.5-7B-Instruct"  # Or use local GGUF
max_seq_length = 1024
dtype = None
load_in_4bit = True

# Load model
print("Loading model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
)

# Add LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=16,
    lora_dropout=0,
)

# Load code dataset
with open('code_data.json', 'r') as f:
    data = json.load(f)

dataset = Dataset.from_list(data)

# Format for code
def format_code(examples):
    texts = []
    for instruction, input_text, output in zip(
        examples['instruction'],
        examples.get('input', [''] * len(examples['instruction'])),
        examples['output']
    ):
        # Code-specific format
        text = f"""<|im_start|>system
You are an expert programmer. Write clean, efficient code.<|im_end>
<|im_start|>user
{instruction}
{input_text if input_text else ''}<|im_end>
<|im_start|>assistant
```{output.split('```')[0].split('```')[0] if '```' in output else output}
```<|im_end>"""
        texts.append(text)
    return {'text': texts}

dataset = dataset.map(format_code, batched=True, remove_columns=dataset.column_names)

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    training_arguments=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        output_dir="code_finetuned",
        save_strategy="epoch",
    ),
)

trainer.train()
model.save_pretrained("code_model")
tokenizer.save_pretrained("code_model")
```

## Prompt Templates

### Python

```python
PYTHON_TEMPLATE = """<|im_start|>system
You are a Python expert. Write clean, well-documented Python code.<|im_end>
<|im_start|>user
{instruction}

```python
```<|im_end>
<|im_start|>assistant
"""
```

### Multi-language

```python
CODE_TEMPLATE = """<|im_start|>system
You are a coding assistant proficient in multiple programming languages.<|im_end>
<|im_start|>user
{instruction}

Language: {language}<|im_end>
<|im_start|>assistant
"""
```

### Debug

```python
DEBUG_TEMPLATE = """<|im_start|>system
You are an expert debugging assistant.<|im_end>
<|im_start|>user
Find and fix bugs in this code:

```{language}
{code}
```<|im_end>
<|im_start|>assistant
"""
```

## Testing

### Test Script

```python
from unsloth import FastLanguageModel

# Load
model, tokenizer = FastLanguageModel.from_pretrained("code_model")
FastLanguageModel.for_inference(model)

# Test
test_prompt = """<|im_start|>system
You are a Python expert.<|im_end>
<|im_start|>user
Write a function to reverse a string.<|im_end>
<|im_start|>assistant
"""

inputs = tokenizer(test_prompt, return_tensors="pt").to(model.device)
outputs = model.generate(
    input_ids=inputs.input_ids,
    max_new_tokens=256,
    temperature=0.2,
)
print(tokenizer.decode(outputs[0]))
```

## Optimization Tips

1. **Use code-specific tokens**
2. **Include docstrings in training**
3. **Test with edge cases**
4. **Evaluate on multiple languages**

## Next Steps

- [Reasoning Fine-tuning](./09-reasoning-finetune.md) - For math/logic
- [Model Evaluation](./10-evaluation.md) - Test quality
