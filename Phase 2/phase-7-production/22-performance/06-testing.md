# Testing AI Components

## Pytest Setup

```bash
pip install pytest pytest-cov pytest-mock
```

## Unit Tests

```python
# tests/unit/test_ollama.py
import pytest
from unittest.mock import Mock, patch

class TestOllamaClient:
    @pytest.fixture
    def client(self):
        from src.models.ollama import OllamaClient
        return OllamaClient(base_url="http://localhost:11434")
    
    def test_generate(self, client):
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "response": "Hello!"
            }
            result = client.generate("Hi")
            assert result == "Hello!"
    
    def test_generate_error(self, client):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = ConnectionError("Failed")
            with pytest.raises(ConnectionError):
                client.generate("Hi")
```

## Integration Tests

```python
# tests/integration/test_pipeline.py
import pytest

@pytest.fixture
def ollama_running():
    """Skip if Ollama not running"""
    import requests
    try:
        requests.get("http://localhost:11434/api/tags")
    except:
        pytest.skip("Ollama not running")

def test_ollama_generation(ollama_running):
    from src.models.ollama import OllamaClient
    client = OllamaClient()
    result = client.generate("Say hello")
    assert len(result) > 0
```

## Mocking External Services

```python
@pytest.fixture
def mock_ollama():
    with patch("src.models.ollama.OllamaClient.generate") as mock:
        mock.return_value = "Mocked response"
        yield mock
```

## Fixtures

```python
# tests/fixtures/__init__.py
import pytest
import tempfile
import shutil

@pytest.fixture
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)

@pytest.fixture
def sample_prompts():
    return [
        "Hello, world!",
        "What is AI?",
        "Explain machine learning"
    ]
```

## Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific
pytest tests/unit/test_ollama.py -v
```

## Test Organization

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_models.py
│   └── test_pipelines.py
├── integration/
│   ├── __init__.py
│   ├── test_ollama.py
│   └── test_pipeline.py
└── fixtures/
    └── __init__.py
```

## Next Steps

- [Documentation](./07-documentation.md) - Document your code
- [CI/CD](./08-ci-cd.md) - Set up CI/CD
