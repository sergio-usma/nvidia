# Linters Setup

## Installation

```bash
pip install ruff black pylint mypy pyright
```

## ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

## black Configuration

```toml
[tool.black]
line-length = 100
target-version = ["py310"]
```

## mypy Configuration

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false

[tool.mypy.overrides]
module = ["numpy.*"]
ignore_missing_imports = true
```

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
      - id: ruff-format
  
  - repo: https://github.com/psf/black
    rev: 23.10.0
    hooks:
      - id: black
```

## Run Linters

```bash
# Run ruff
ruff check src/

# Run black
black --check src/

# Run mypy
mypy src/

# Run all
make lint
```

## GitHub Actions

```yaml
name: Quality

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
```

## Next Steps

- [Testing](./06-testing.md) - Test your AI code
- [CI/CD](./08-ci-cd.md) - Set up CI/CD
