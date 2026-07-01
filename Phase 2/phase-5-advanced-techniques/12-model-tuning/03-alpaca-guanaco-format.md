# Alpaca and Guanaco Dataset Format Guide

This guide covers how to format your training data in Alpaca and Guanaco formats for fine-tuning LLMs on Jetson AGX Orin.

## Table of Contents

- [Alpaca Format](#alpaca-format)
- [Guanaco Format](#guanaco-format)
- [JSON vs CSV](#json-vs-csv)
- [Field Descriptions](#field-descriptions)
- [Examples](#examples)
- [Validation](#validation)
- [Conversion Tools](#conversion-tools)

## Alpaca Format

Alpaca format is the most widely used instruction-following dataset format, originally from Stanford's Alpaca project.

### JSON Format

```json
[
  {
    "instruction": "What is the capital of France?",
    "input": "",
    "output": "The capital of France is Paris."
  },
  {
    "instruction": "Translate the following to Spanish",
    "input": "Hello, how are you?",
    "output": "Hola, ¿cómo estás?"
  }
]
```

### Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `instruction` | Yes | The task instruction |
| `input` | No | Additional context/input |
| `output` | Yes | Expected response |

### CSV Format

```csv
instruction,input,output
"What is the capital of France?","","The capital of France is Paris."
"Translate to Spanish","Hello, how are you?","Hola, ¿cómo estás?"
"Explain photosynthesis","","Photosynthesis is the process by which plants convert sunlight into energy..."
```

## Guanaco Format

Guanaco format is similar to Alpaca but uses a conversational format with special tokens.

### JSON Format

```json
[
  {
    "conversations": [
      {"from": "human", "value": "What is machine learning?"},
      {"from": "gpt", "value": "Machine learning is a subset of artificial intelligence..."}
    ]
  },
  {
    "conversations": [
      {"from": "human", "input": "Explain this code"},
      {"from": "gpt", "value": "This Python code implements..."}
    ]
  }
]
```

### Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `conversations` | Yes | List of message objects |
| `from` | Yes | Speaker identity (human/gpt) |
| `value` | Yes | Message content |

## JSON vs CSV

### JSON Advantages
- Supports complex nested structures
- Better for multi-turn conversations
- Preserves special characters better
- Standard for most LLM frameworks

### CSV Advantages
- Simpler to create/edit manually
- Excel-compatible
- Smaller file size
- Easier to inspect

## Field Descriptions

### instruction

The prompt that tells the model what to do. Should be:
- Clear and specific
- In the language you want the model to respond
- Action-oriented

```json
{
  "instruction": "Summarize the following article"
}
```

### input

Additional context or data. Can be:
- Empty string for no input
- Text to process
- Code snippets
- Document excerpts

```json
{
  "instruction": "Translate",
  "input": "Good morning"
}
```

### output

The expected model response. Should be:
- Complete and accurate
- In the same language as instruction
- Properly formatted

```json
{
  "output": "Buenos días"
}
```

## Examples

### Simple Q&A

```json
{
  "instruction": "What is Python?",
  "input": "",
  "output": "Python is a high-level, interpreted programming language known for its readability and versatility."
}
```

### Code Generation

```json
{
  "instruction": "Write a Python function to calculate factorial",
  "input": "",
  "output": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"
}
```

### Text Transformation

```json
{
  "instruction": "Convert to uppercase",
  "input": "hello world",
  "output": "HELLO WORLD"
}
```

### Reasoning

```json
{
  "instruction": "If all roses are flowers and some flowers are red, what can we conclude?",
  "input": "",
  "output": "We can conclude that some roses could potentially be red, since roses are a subset of flowers."
}
```

## Validation

### Python Validation Script

```python
#!/usr/bin/env python3
"""Validate Alpaca format dataset."""

import json
import csv
import sys

def validate_json_file(filepath):
    """Validate JSON format."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("Error: Data must be a list")
            return False
        
        for i, item in enumerate(data):
            if 'instruction' not in item:
                print(f"Error: Item {i} missing 'instruction'")
                return False
            if 'output' not in item:
                print(f"Error: Item {i} missing 'output'")
                return False
            if not isinstance(item['instruction'], str):
                print(f"Error: Item {i} instruction must be string")
                return False
        
        print(f"✓ Valid: {len(data)} samples")
        return True
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def validate_csv_file(filepath):
    """Validate CSV format."""
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        required_fields = ['instruction', 'output']
        
        for i, row in enumerate(rows):
            for field in required_fields:
                if field not in row:
                    print(f"Error: Row {i} missing '{field}'")
                    return False
        
        print(f"✓ Valid: {len(rows)} samples")
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <file.json|csv>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if filepath.endswith('.json'):
        validate_json_file(filepath)
    elif filepath.endswith('.csv'):
        validate_csv_file(filepath)
    else:
        print("Error: Unsupported file format")
```

### Run Validation

```bash
python3 validate.py my_dataset.json
# Output: ✓ Valid: 100 samples

python3 validate.py my_dataset.csv  
# Output: ✓ Valid: 50 samples
```

## Conversion Tools

### CSV to JSON

```python
#!/usr/bin/env python3
"""Convert CSV to Alpaca JSON."""

import csv
import json
import sys

def csv_to_json(csv_file, json_file):
    """Convert CSV to JSON format."""
    data = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = {
                'instruction': row.get('instruction', ''),
                'input': row.get('input', ''),
                'output': row.get('output', '')
            }
            data.append(item)
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(data)} samples to {json_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python csv_to_json.py input.csv output.json")
        sys.exit(1)
    
    csv_to_json(sys.argv[1], sys.argv[2])
```

### JSON to CSV

```python
#!/usr/bin/env python3
"""Convert Alpaca JSON to CSV."""

import csv
import json
import sys

def json_to_csv(json_file, csv_file):
    """Convert JSON to CSV format."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['instruction', 'input', 'output'])
        writer.writeheader()
        for item in data:
            writer.writerow({
                'instruction': item.get('instruction', ''),
                'input': item.get('input', ''),
                'output': item.get('output', '')
            })
    
    print(f"Converted {len(data)} samples to {csv_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python json_to_csv.py input.json output.csv")
        sys.exit(1)
    
    json_to_csv(sys.argv[1], sys.argv[2])
```

### Usage

```bash
# Convert CSV to JSON
python3 csv_to_json.py train.csv train.json

# Convert JSON to CSV
python3 json_to_csv.py train.json train.csv

# Validate
python3 validate.py train.json
```

## Dataset Sources

### Public Datasets

| Dataset | Size | Use Case |
|---------|------|----------|
| Alpaca | 52K | General instruction |
| Alpaca-GPT4 | 52K | GPT-4 generated |
| Guanaco | 534K | Multilingual |
| CodeAlpaca | 20K | Code generation |
| MathInstruct | 62K | Math reasoning |

### Download Example

```bash
# Download Alpaca dataset
wget https://huggingface.co/datasets/tatsu-lab/alpaca/resolve/main/data/alpaca_data.json

# Download CodeAlpaca
wget https://huggingface.co/datasets/sahil2801/CodeAlpaca-20k/resolve/main/data/code_alpaca_20k.json
```

## Best Practices

1. **Quality over Quantity**: 1K high-quality samples > 100K low-quality
2. **Diverse Instructions**: Vary instruction phrasing
3. **Consistent Outputs**: Maintain format and style
4. **Balance Classes**: Even distribution of task types
5. **Validate First**: Always validate before training

## Next Steps

- Proceed to [Custom Datasets](./07-custom-datasets.md) to create your own dataset
- Or jump to [Unsloth Fine-tuning](./05-unsloth-finetune.md) to start training
