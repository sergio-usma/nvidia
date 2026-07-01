# Reasoning Model Fine-Tuning

Fine-tuning LLMs for mathematical reasoning and logical thinking tasks.

## Table of Contents

- [Models for Reasoning](#models-for-reasoning)
- [Reasoning Datasets](#reasoning-datasets)
- [Training for Chain-of-Thought](#training-for-chain-of-thought)
- [Testing Reasoning](#testing-reasoning)

## Models for Reasoning

| Model | Type | Best For |
|-------|------|----------|
| deepseek-r1:8b |蒸馏 | Chain-of-thought |
| mathstral | Math | STEM tasks |
| phi4-mini-reasoning | Logic | Quick decisions |
| Qwen2.5-Math | Math | Complex math |

## Reasoning Datasets

```python
from datasets import load_dataset

# Math
math_ds = load_dataset("meta-math/MetaMathQA")

# Logic
logic_ds = load_dataset("openai/gsm8k")

# STEM
stem_ds = load_dataset("reasoning-machines/chain-of-thought")
```

### Format

```json
[
  {
    "instruction": "Solve: 2x + 5 = 15",
    "output": "Step 1: Subtract 5 from both sides\n2x = 10\nStep 2: Divide by 2\nx = 5\nAnswer: x = 5"
  }
]
```

## Training for Chain-of-Thought

```python
#!/usr/bin/env python3
"""Fine-tune for reasoning."""

import torch
from unsloth import FastLanguageModel
from datasets import Dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import json

# Load model - prefer math-capable model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-7B-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,
)

# LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)

# Load reasoning data
with open('reasoning_data.json', 'r') as f:
    data = json.load(f)

dataset = Dataset.from_list(data)

# Format with reasoning steps
def format_reasoning(examples):
    texts = []
    for instruction, output in zip(examples['instruction'], examples['output']):
        # Emphasize step-by-step
        text = f"""<|im_start|>system
You are a math and reasoning expert. Show your work step by step.<|im_end>
<|im_start|>user
{instruction}<|im_end>
<|im_start|>assistant
Let's think step by step:

{output}

Therefore, the answer is: {extract_answer(output)}<|im_end>"""
        texts.append(text)
    return {'text': texts}

def extract_answer(output):
    # Extract final answer
    lines = output.split('\n')
    for line in reversed(lines):
        if any(c.isdigit() for c in line):
            return line.strip()
    return "the above"

dataset = dataset.map(format_reasoning, batched=True)

# Train with lower temperature
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    training_arguments=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=1e-4,  # Lower LR for reasoning
        fp16=True,
        output_dir="reasoning_model",
    ),
)

trainer.train()
model.save_pretrained("reasoning_model")
```

## Testing Reasoning

```python
# Test
test_prompt = """<|im_start|>system
You are a math expert.<|im_end>
<|im_start|>user
If a train travels 60 mph for 2 hours, how far does it go?<|im_end>
<|im_start|>assistant
"""

inputs = tokenizer(test_prompt, return_tensors="pt").to(model.device)
outputs = model.generate(
    input_ids=inputs.input_ids,
    max_new_tokens=512,
    temperature=0.3,  # Lower for reasoning
)

print(tokenizer.decode(outputs[0]))
```

## Next Steps

- [Model Evaluation](./10-evaluation.md)
- [Export and Deploy](./11-export-deploy.md)
