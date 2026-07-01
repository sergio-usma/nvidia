# Documentation Standards

## README Structure

```markdown
# Project Name

Brief description of the project.

## Features

- Feature 1
- Feature 2

## Installation

```bash
pip install project-name
```

## Usage

```python
from project import Example

example = Example()
result = example.run()
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| model | str | "llama3.2:3b" | Model name |

## Requirements

- Python 3.10+
- Ollama running on localhost:11434

## License

MIT
```

## API Documentation

```python
"""
API Reference
=============

### generate(prompt: str, model: str) -> str

Generate text from prompt.

**Parameters:**
- `prompt` (str): Input prompt
- `model` (str): Model name

**Returns:**
- `str`: Generated text

**Example:**
```python
result = generate("Hello", model="llama3.2:3b")
```
"""
```

## Configuration Documentation

```markdown
# Configuration

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| OLLAMA_URL | No | http://localhost:11434 | Ollama URL |
| MODEL_NAME | No | llama3.2:3b | Default model |

## Config File

```yaml
model:
  name: llama3.2:3b
  temperature: 0.7
  max_tokens: 1000
```
```

## Next Steps

- [CI/CD](./08-ci-cd.md) - Set up CI/CD
- [Monitoring](./09-monitoring.md) - Add monitoring
