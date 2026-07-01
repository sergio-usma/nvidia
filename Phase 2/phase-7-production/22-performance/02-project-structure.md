# AI Project Structure

## Recommended Structure

```
ai_project/
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration
│   ├── main.py           # Entry point
│   ├── models/           # AI models
│   │   ├── __init__.py
│   │   ├── base.py       # Base model class
│   │   ├── llm.py       # LLM wrapper
│   │   └── embed.py      # Embeddings
│   ├── pipelines/       # Processing pipelines
│   │   ├── __init__.py
│   │   ├── rag.py        # RAG pipeline
│   │   └── preprocess.py # Data preprocessing
│   ├── api/              # API endpoints
│   │   ├── __init__.py
│   │   └── routes.py     # FastAPI routes
│   └── utils/           # Utilities
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── config/
│   ├── default.yaml
│   └── production.yaml
├── notebooks/
├── scripts/
├── data/
├── models/               # Saved models
├── requirements.txt
├── setup.py
├── pyproject.toml
├── Makefile
└── README.md
```

## Core Files

### pyproject.toml
```toml
[project]
name = "ai-project"
version = "0.1.0"

[tool.ruff]
line-length = 100

[tool.mypy]
python_version = "3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Makefile
```makefile
.PHONY: install test lint format

install:
	pip install -e .

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

quality: lint test
```

## Model Organization

```
models/
├── llms/
│   ├── llama3.2-3b/
│   └── qwen2.5-coder/
├── embeddings/
│   └── nomic-embed-text/
└── checkpoints/
```

## Next Steps

- [Design Patterns](./03-design-patterns.md) - Common patterns
- [Code Quality](./04-code-quality.md) - Quality guidelines
