# Pip Configuration and Package Management

This guide covers pip configuration and package management for Python on Jetson AGX Orin.

## Check Pip Version

```bash
pip3 --version
pip --version
```

## Upgrade Pip

```bash
pip install --upgrade pip
```

## Install Packages

```bash
pip install package_name
pip install package==version
pip install "package>=1.0"
```

## Requirements Files

### Create requirements.txt

```bash
pip freeze > requirements.txt
```

Or for specific packages:

```bash
pip freeze | grep -v "^##" > requirements.txt
```

### Install from requirements

```bash
pip install -r requirements.txt
```

## Pip Configuration Files

### Per-user config

```bash
mkdir -p ~/.config/pip
nano ~/.config/pip/pip.conf
```

```ini
[global]
timeout = 60
index-url = https://pypi.org/simple
trusted-host = pypi.org
```

### Project config

```bash
nano pyproject.toml
```

```toml
[tool.pip]
timeout = 60

[project]
dependencies = [
    "requests>=2.28.0",
    "numpy>=1.24.0",
]
```

## Mirror Configuration

Use PyPI mirror for faster downloads:

```bash
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
```

Or Tsinghua mirror:

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## Package Search

Search for packages:

```bash
pip search package  # deprecated
pip index versions package
```

## Package Information

Show package info:

```bash
pip show package_name
pip show -f package_name
```

List outdated packages:

```bash
pip list --outdated
```

Upgrade packages:

```bash
pip install --upgrade package_name
pip list --outdated | pip install -U
```

## Wheel Cache

Cache downloaded wheels:

```bash
pip cache list
pip cache info
```

Clear cache:

```bash
pip cache purge
```

## Wheels and Eggs

Force wheel installation:

```bash
pip install --only-binary :all: package
```

Force source installation:

```bash
pip install --no-binary :all: package
```

## Development Install

Editable install:

```bash
pip install -e .
pip install -e ".[dev]"
```

## UnInstall Packages

```bash
pip uninstall package_name
pip uninstall -r requirements.txt
```

## Verify Installations

```bash
python3 -c "import package; print(package.__version__)"
```

## Common AI/ML Packages

Install essential packages:

```bash
pip install numpy
pip install scipy
pip install pandas
pip install scikit-learn
pip install matplotlib
pip install pillow
pip install opencv-python
pip install torch
pip install transformers
```

## PyTorch for Jetson

```bash
# Using pip (CPU version)
pip install torch torchvision

# Or from source with Jetson-specific optimizations
# See part-3-python-environment/03-pytorch-installation.md
```

## TensorFlow for Jetson

```bash
pip install tensorflow
```

Verify:

```bash
python3 -c "import tensorflow as tf; print(tf.__version__)"
```

## Troubleshooting

### SSL Errors

```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org package
```

### Permission Errors

```bash
pip install --user package
```

### Version Conflicts

```bash
pip check
```

## Proxy Configuration

```bash
pip install --proxy http://proxy:port package
```

## Automatic Upgrades

Check for updates:

```bash
pip list -o
```

Upgrade all:

```bash
pip freeze | grep -v "^-e" | cut -d = -f 1 | xargs -n1 pip install -U
```

## CI/CD Pip Configuration

```bash
pip config list
export PIP_INDEX_URL=$PIP_INDEX_URL
export PIP_TRUSTED_HOST=$PIP_TRUSTED_HOST
```

## Pre-commit Hooks

Install pre-commit:

```bash
pip install pre-commit
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```
