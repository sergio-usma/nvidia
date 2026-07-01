# AI Design Patterns

## 1. Model Wrapper Pattern

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseModel(ABC):
    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        pass

class OllamaModel(BaseModel):
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
    
    def predict(self, prompt: str) -> str:
        import requests
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model_name, "prompt": prompt}
        )
        return response.json()["response"]
    
    def load(self, path: str) -> None:
        pass  # Ollama loads models automatically
```

## 2. Pipeline Pattern

```python
from typing import List, Callable

class Pipeline:
    def __init__(self):
        self.steps: List[Callable] = []
    
    def add_step(self, step: Callable) -> "Pipeline":
        self.steps.append(step)
        return self
    
    def run(self, input_data):
        result = input_data
        for step in self.steps:
            result = step(result)
        return result

# Usage
pipeline = (
    Pipeline()
    .add_step(preprocess)
    .add_step(embed)
    .add_step(predict)
)
result = pipeline.run(data)
```

## 3. Adapter Pattern

```python
class OllamaAdapter:
    """Adapt Ollama API to standard interface"""
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.client = OllamaClient(base_url)
    
    def generate(self, prompt: str, **kwargs) -> str:
        return self.client.create_completion(prompt, **kwargs)
    
    def embed(self, text: str) -> List[float]:
        return self.client.create_embedding(text)
```

## 4. Factory Pattern

```python
class ModelFactory:
    @staticmethod
    def create(model_type: str, **kwargs):
        if model_type == "ollama":
            return OllamaModel(**kwargs)
        elif model_type == "openai":
            return OpenAIModel(**kwargs)
        elif model_type == "huggingface":
            return HuggingFaceModel(**kwargs)
        raise ValueError(f"Unknown model type: {model_type}")

# Usage
model = ModelFactory.create("ollama", model_name="llama3.2:3b")
```

## 5. Strategy Pattern

```python
class EmbeddingStrategy(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

class OllamaEmbedding(EmbeddingStrategy):
    def embed(self, text: str) -> List[float]:
        # Implementation
        pass

class SentenceTransformerEmbedding(EmbeddingStrategy):
    def embed(self, text: str) -> List[float]:
        # Implementation
        pass
```

## 6. Observer Pattern for Monitoring

```python
class ModelObserver:
    def on_prediction_start(self, input_data): pass
    def on_prediction_end(self, output_data): pass
    def on_error(self, error): pass

class LoggingObserver(ModelObserver):
    def on_prediction_start(self, input_data):
        logger.info(f"Starting prediction: {input_data[:50]}")
    
    def on_prediction_end(self, output_data):
        logger.info(f"Prediction complete: {output_data[:50]}")
```

## 7. Singleton for Model Cache

```python
class ModelCache:
    _instance = None
    _models = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get(self, key: str):
        return self._models.get(key)
    
    def set(self, key: str, model):
        self._models[key] = model
```

## Next Steps

- [Code Quality](./04-code-quality.md) - Quality guidelines
- [Linters](./05-linters.md) - Code linters
