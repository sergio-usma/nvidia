# Custom Datasets Guide

Creating and preparing custom datasets for fine-tuning from CSV, JSON, and other sources.

## Table of Contents

- [Data Sources](#data-sources)
- [CSV Datasets](#csv-datasets)
- [JSON Datasets](#json-datasets)
- [Data Cleaning](#data-cleaning)
- [Data Augmentation](#data-augmentation)
- [Validation](#validation)

## Data Sources

### Collecting Your Own Data

| Source | Format | Tools |
|--------|---------|-------|
| Conversations | Text/JSON | Export from chat apps |
| Q&A Pairs | CSV/JSON | Custom scripts |
| Code Repos | JSON | Parse GitHub, GitLab |
| Documents | PDF/DOCX | OCR, text extraction |

### Public Datasets

```bash
# Download from HuggingFace
from datasets import load_dataset

# Code datasets
code_ds = load_dataset("codebudo/codeforces-problems", split="train")
python_ds = load_dataset("openai/openai_python", split="train")

# Math datasets
math_ds = load_dataset("meta-math/MetaMathQA", split="train")

# General datasets
alpaca_ds = load_dataset("tatsu-lab/alpaca", split="train")
```

## CSV Datasets

### Structure

```csv
instruction,input,output
"What is Python?","","Python is a high-level programming language..."
"Translate to Spanish","Hello","Hola"
"Debug this code","def foo(): pass","The code is missing return value..."
```

### Loading

```python
from datasets import Dataset
import pandas as pd

# Method 1: Using pandas
df = pd.read_csv('data.csv')
dataset = Dataset.from_pandas(df)

# Method 2: Direct
dataset = Dataset.from_csv('data.csv')

print(dataset[0])
```

### Creating from Scratch

```python
import csv
import json

# Create CSV from list
data = [
    {"instruction": "What is AI?", "input": "", "output": "AI is..."},
    {"instruction": "Write code", "input": "Hello world", "output": "print('Hello world')"},
]

with open('train.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['instruction', 'input', 'output'])
    writer.writeheader()
    writer.writerows(data)
```

## JSON Datasets

### Alpaca Format

```json
[
  {
    "instruction": "What is machine learning?",
    "input": "",
    "output": "Machine learning is a subset of artificial intelligence..."
  }
]
```

### Loading

```python
import json
from datasets import Dataset

# Load JSON
with open('data.json', 'r') as f:
    data = json.load(f)

dataset = Dataset.from_list(data)

# Or directly
dataset = Dataset.from_json('data.json')
```

### Multi-turn Conversations

```json
[
  {
    "conversations": [
      {"from": "human", "value": "What is Python?"},
      {"from": "gpt", "value": "Python is..."},
      {"from": "human", "value": "Tell me more"},
      {"from": "gpt", "value": "Additionally..."}
    ]
  }
]
```

## Data Cleaning

### Basic Cleaning

```python
def clean_text(text):
    """Clean and normalize text."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Remove special characters (optional)
    # text = re.sub(r'[^\w\s.,!?]', '', text)
    
    return text.strip()

def clean_dataset(examples):
    return {
        'instruction': [clean_text(i) for i in examples['instruction']],
        'output': [clean_text(o) for o in examples['output']],
        'input': [clean_text(i) if i else "" for i in examples.get('input', [])]
    }

dataset = dataset.map(clean_dataset, batched=True)
```

### Filter Invalid Entries

```python
def is_valid(example):
    """Check if entry is valid."""
    # Must have instruction and output
    if not example.get('instruction') or not example.get('output'):
        return False
    
    # Minimum length
    if len(example['instruction']) < 3:
        return False
    
    if len(example['output']) < 3:
        return False
    
    return True

dataset = dataset.filter(is_valid)
```

### Deduplication

```python
# Remove duplicates based on instruction
dataset = dataset.unique('instruction')

# Or custom
def deduplicate(examples):
    seen = set()
    unique_instructions = []
    unique_outputs = []
    unique_inputs = []
    
    for instr, outp in zip(examples['instruction'], examples['output']):
        if instr not in seen:
            seen.add(instr)
            unique_instructions.append(instr)
            unique_outputs.append(outp)
    
    return {
        'instruction': unique_instructions,
        'output': unique_outputs
    }

dataset = dataset.map(deduplicate, batched=True)
```

## Data Augmentation

### Paraphrasing

```python
# Using a small model for paraphrase
def paraphrase(text, model, tokenizer):
    prompt = f"Paraphrase: {text}"
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=100)
    return tokenizer.decode(outputs[0])
```

### Back-translation

```python
# Translate to another language and back
# This creates paraphrased versions
```

### Instruction Variations

```python
# Generate multiple phrasings
instruction_variations = {
    "What is X?": [
        "What is X?",
        "Define X",
        "Explain what X is",
        "What do you know about X?"
    ]
}
```

## Validation

### Quality Checks

```python
def validate_quality(example, idx):
    issues = []
    
    # Check length
    if len(example['instruction']) > 500:
        issues.append("Instruction too long")
    
    if len(example['output']) > 2000:
        issues.append("Output too long")
    
    # Check for placeholders
    if '[TODO]' in example['output'] or '...' in example['output']:
        issues.append("Contains incomplete content")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues
    }

# Apply validation
validated = dataset.map(validate_quality, with_indices=True)

# Filter valid only
valid_dataset = validated.filter(lambda x: x['valid'])
```

### Split Dataset

```python
# Train/val/test split
train_val = dataset.train_test_split(test_size=0.1)
train_dataset = train_val['train']
val_dataset = train_val['test']

# Or more granular
splits = dataset.train_test_split(test_size=0.2, seed=42)
train_ds = splits['train']
test_ds = splits['test']

val_test = test_ds.train_test_split(test_size=0.5)
val_dataset = val_test['train']
test_dataset = val_test['test']
```

## Complete Pipeline Example

```python
#!/usr/bin/env python3
"""Complete dataset preparation pipeline."""

import json
import csv
from datasets import Dataset
from transformers import AutoTokenizer
import random

def load_raw_data(source):
    """Load data from various sources."""
    if source.endswith('.json'):
        with open(source, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    
    elif source.endswith('.csv'):
        import pandas as df
        df = pd.read_csv(source)
        return df.to_dict('records')
    
    else:
        raise ValueError(f"Unsupported format: {source}")

def clean_data(examples):
    """Clean and normalize data."""
    cleaned = []
    for item in examples:
        # Extract fields
        instr = item.get('instruction', item.get('prompt', ''))
        outp = item.get('output', item.get('response', ''))
        inp = item.get('input', '')
        
        # Clean
        if isinstance(instr, str) and isinstance(outp, str):
            if len(instr) > 2 and len(outp) > 2:
                cleaned.append({
                    'instruction': instr.strip(),
                    'output': outp.strip(),
                    'input': inp.strip() if inp else ''
                })
    
    return cleaned

def augment_data(data, num_augmentations=2):
    """Augment with variations."""
    augmented = []
    
    templates = [
        "{}",
        "Please {}",
        "Can you {}?",
        "I need you to {}",
        "Help me {}"
    ]
    
    for item in data:
        augmented.append(item)
        
        # Add variations
        if random.random() < 0.3:
            template = random.choice(templates)
            new_item = item.copy()
            new_item['instruction'] = template.format(item['instruction'])
            augmented.append(new_item)
    
    return augmented

def prepare_dataset(source_file, output_file, augment=False):
    """Full pipeline."""
    print(f"Loading {source_file}...")
    raw_data = load_raw_data(source_file)
    
    print("Cleaning data...")
    cleaned = clean_data({'instruction': [d['instruction'] for d in raw_data],
                          'output': [d['output'] for d in raw_data],
                          'input': [d.get('input', '') for d in raw_data]})
    
    if augment:
        print("Augmenting data...")
        cleaned = augment_data(cleaned)
    
    print(f"Saving to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(cleaned, f, indent=2)
    
    print(f"Done! {len(cleaned)} samples prepared.")

if __name__ == "__main__":
    prepare_dataset("raw_data.csv", "train_data.json", augment=True)
```

## Dataset Sizes

| Dataset Size | Training Time | Use Case |
|-------------|---------------|----------|
| 100-1K | Minutes | Quick experiments |
| 1K-10K | Hours | Specific tasks |
| 10K-100K | Day(s) | Domain adaptation |
| 100K+ | Days/Week | Full fine-tuning |

## Next Steps

- [Code Fine-tuning](./08-code-finetune.md) - Fine-tune for code
- [Reasoning Fine-tuning](./09-reasoning-finetune.md) - Fine-tune for math/logic
