# Code Quality Guidelines

## Type Hints

Always use type hints:
```python
from typing import List, Dict, Optional

def generate(
    prompt: str,
    model: str = "llama3.2:3b",
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    ...
```

## Error Handling

```python
class AIError(Exception):
    """Base exception for AI errors"""
    pass

class ModelError(AIError):
    """Model-related errors"""
    pass

class TimeoutError(AIError):
    """Timeout errors"""
    pass

def safe_generate(prompt: str) -> str:
    try:
        return model.generate(prompt)
    except TimeoutError:
        logger.warning("Timeout, retrying...")
        return model.generate(prompt)
    except ModelError as e:
        logger.error(f"Model error: {e}")
        raise
```

## Configuration

```python
from dataclasses import dataclass

@dataclass
class ModelConfig:
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 60

# Use
config = ModelConfig(model_name="llama3.2:3b")
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

def generate(prompt: str) -> str:
    logger.info(f"Generating response for prompt: {prompt[:50]}...")
    try:
        result = model.generate(prompt)
        logger.info(f"Generated {len(result)} chars")
        return result
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise
```

## Docstrings

```python
def generate(
    prompt: str,
    model: str = "llama3.2:3b",
    temperature: float = 0.7
) -> str:
    """Generate text using local LLM.
    
    Args:
        prompt: Input prompt for generation.
        model: Model name to use.
        temperature: Sampling temperature (0.0 to 1.0).
    
    Returns:
        Generated text string.
    
    Raises:
        AIError: If generation fails.
    
    Example:
        >>> generate("Hello, world!", temperature=0.5)
        "Hello to you too!"
    """
    ...
```

## Constants

```python
# Good
MAX_TOKENS = 4096
DEFAULT_MODEL = "llama3.2:3b"
OLLAMA_BASE_URL = "http://localhost:11434"

# Bad
max = 4096
model = "llama3.2:3b"
url = "http://localhost:11434"
```

## Next Steps

- [Linters](./05-linters.md) - Set up linters
- [Testing](./06-testing.md) - Test your AI code
