# Export and Deploy

Exporting and deploying your fine-tuned models.

## Export Formats

| Format | Use | Size |
|--------|-----|------|
| GGUF | llama.cpp | Small |
| Ollama | Ollama | Medium |
| HF | HuggingFace | Large |

## Export to GGUF

### Using llama.cpp

```bash
# First export model to HF
model.save_pretrained("hf_model")
tokenizer.save_pretrained("hf_model")

# Then convert to GGUF
./convert-hf-to-gguf ./hf_model ./model.gguf
```

### Quantize

```bash
./llama-quantize model.gguf model-q4.gguf Q4_K_M
```

## Deploy with llama.cpp

```bash
# Start server
llama-cli -m model-q4.gguf -ngl 99 -c 2048 --server --port 8080
```

## Export to Ollama

```python
# Create Modelfile
with open('Modelfile', 'w') as f:
    f.write("FROM ./model.gguf\n")
    f.write('TEMPLATE """{{.System}}\n\n### Instruction:\n{{.Instruction}}\n\n### Response:\n{{.Response}}\n"""\n')

# Import
subprocess.run(['ollama', 'create', 'my-model', '-f', 'Modelfile'])
```

## Docker Deployment

```dockerfile
FROM nvidia/cuda:12.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /app
COPY model.gguf /app/
COPY server.py /app/

RUN pip3 install llama-cpp-python

EXPOSE 8080
CMD ["python3", "server.py"]
```

## API Service

```python
from flask import Flask, request, jsonify
from llama_cpp import Llama

app = Flask(__name__)
llm = Llama(model_path="model.gguf", n_gpu_layers=99)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    output = llm(
        data['prompt'],
        max_tokens=data.get('max_tokens', 512),
        temperature=data.get('temperature', 0.7),
    )
    return jsonify({'response': output['choices'][0]['text']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Next Steps

- [Troubleshooting](./12-troubleshooting.md)
