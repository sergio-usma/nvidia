# jetson-containers

Use pre-built optimized containers for AI frameworks.

## Install jetson-containers

```bash
git clone https://github.com/dusty-nv/jetson-containers
cd jetson-containers
pip3 install -r requirements.txt
```

## Using autotag

The `autotag` script automatically selects the correct container tag for your JetPack version:

```bash
./autotag ollama
```

This returns something like `dustynv/ollama:r36.5.0`.

## Run Containers

### Ollama

```bash
./run.sh $(./autotag ollama)
```

### PyTorch

```bash
./run.sh $(./autotag pytorch)
```

### Whisper (Speech-to-Text)

```bash
./run.sh $(./autotag whisper)
```

### Piper (Text-to-Speech)

```bash
./run.sh $(./autotag piper)
```

### LLaVA (Vision)

```bash
./run.sh $(./autotag nanollava)
```

## List Available Packages

```bash
jetson-containers build --list-packages
```

## Build Custom Container

```bash
jetson-containers build --package pytorch
```

## Using Docker Directly

You can also use Docker directly with the tags:

```bash
docker run --runtime nvidia -it dustynv/ollama:r36.5.0
```

## Persist Data with Volumes

```bash
docker run --runtime nvidia -v ~/ollama_models:/root/.ollama -p 11434:11434 dustynv/ollama:r36.5.0
```

This mounts your models folder so models persist after container removal.

## Common Container Tags

| Package | Tag | Description |
|--------|-----|-------------|
| Ollama | r36.5.0 | LLM runtime |
| PyTorch | r36.5.0 | Deep learning |
| Whisper | r36.5.0 | Speech-to-text |
| Piper | r36.5.0 | Text-to-speech |
| L4T Base | r36.5.0 | Base container |

## Next Steps

Now that you understand containers, proceed to:
- [Python Environment Setup](../part-3-python-environment/01-python-setup.md)
- [Ollama Setup](../part-5-llms/01-ollama-setup.md)
