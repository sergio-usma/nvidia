# Model Evaluation

Testing and evaluating your fine-tuned models.

## Basic Evaluation

```python
#!/usr/bin/env python3
"""Evaluate fine-tuned model."""

from unsloth import FastLanguageModel
import json

# Load model
model, tokenizer = FastLanguageModel.from_pretrained("finetuned_model")
FastLanguageModel.for_inference(model)

# Test cases
test_cases = [
    {"instruction": "What is Python?", "expected": "programming language"},
    {"instruction": "Write hello world", "expected": "print"},
]

results = []
for test in test_cases:
    prompt = f"### Instruction:\n{test['instruction']}\n\n### Response:\n"
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(input_ids=inputs.input_ids, max_new_tokens=256)
    response = tokenizer.decode(outputs[0])
    
    # Simple check
    matches = any(word in response.lower() for word in test['expected'].lower().split())
    results.append({"passed": matches, "response": response})

print(f"Passed: {sum(1 for r in results if r['passed'])}/{len(results)}")
```

## Metrics

| Metric | Description |
|--------|-------------|
| Accuracy | Exact match |
| BLEU | Text similarity |
| ROUGE | N-gram overlap |
| Perplexity | Language quality |

## Human Evaluation

1. Test with diverse prompts
2. Compare to base model
3. Check for overfitting

## Next Steps

- [Export and Deploy](./11-export-deploy.md)
