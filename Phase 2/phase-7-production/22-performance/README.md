# Part 26: Vibe Engineering & AI Patterns

## Overview

This section covers engineering best practices, design patterns, linters, and quality guidelines specifically for AI projects on your Jetson AGX Orin. Build production-ready AI applications with proper architecture and code quality.

## Available Guides

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | Vibe engineering introduction |
| [02-project-structure.md](./02-project-structure.md) | AI project folder structure |
| [03-design-patterns.md](./03-design-patterns.md) | AI design patterns |
| [04-code-quality.md](./04-code-quality.md) | Code quality guidelines |
| [05-linters.md](./05-linters.md) | Python linters for AI |
| [06-testing.md](./06-testing.md) | Testing AI components |
| [07-documentation.md](./07-documentation.md) | Documentation standards |
| [08-ci-cd.md](./08-ci-cd.md) | CI/CD for AI projects |
| [09-monitoring.md](./09-monitoring.md) | Observability |
| [10-best-practices.md](./10-best-practices.md) | Jetson-specific best practices |

## Quick Start

```bash
# Install linters
pip install ruff black pylint mypy

# Set up project
python -m ai_project init

# Run quality checks
make quality
```

## Architecture

```
ai_project/
├── src/
│   ├── models/          # AI models
│   ├── pipelines/       # Data pipelines
│   ├── api/            # API endpoints
│   └── utils/          # Utilities
├── tests/              # Test suite
├── config/             # Configuration
├── notebooks/          # Jupyter notebooks
└── Makefile           # Build automation
```

## Next Steps

Start with [01-overview.md](./01-overview.md) to understand vibe engineering.
