# LLaVA Vision Model

Run LLaVA for vision + language tasks.

## Using Ollama

```bash
ollama pull llava
```

## Query with Image

```bash
ollama run llava "Describe this image" --image /path/to/image.jpg
```

## Using API

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llava",
  "messages": [
    {
      "role": "user",
      "content": "What is in this image?",
      "images": ["base64_encoded_image"]
    }
  ]
}'
```

## Using jetson-containers

```bash
./run.sh $(./autotag nanollava)
```

## Image Input Methods

1. **File path**: `--image /path/to/image.jpg`
2. **Base64 encoded**: Use in API calls
3. **Camera capture**: Use jetson-utils

## Use Cases

- Image description
- Visual question answering
- Object detection in context
- Reading text from images (OCR)

## Model Variants

| Model | Size | Description |
|-------|------|-------------|
| llava | ~5GB | Default vision model |
| llava:7b | ~7GB | Higher quality |
| bakllava | ~6GB | Alternative |

## Next Steps

- [Object Detection](02-object-detection.md)
- [VS Code Setup](../part-8-development-tools/01-vscode-ssh.md)
