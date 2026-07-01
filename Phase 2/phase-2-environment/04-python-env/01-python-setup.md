# Python Environment Setup

Set up Python with GPU support using venv and system packages.

## Understanding the Problem

When you create a virtual environment with `venv` or `pyenv`, it doesn't see the system-installed NVIDIA packages (CUDA, TensorRT, cuDNN, OpenCV). We need to use `--system-site-packages` to inherit these.

## Option A: venv with System Packages (Recommended)

### Create Environment

```bash
python3 -m venv --system-site-packages ~/envs/ai_env
```

### Activate Environment

```bash
source ~/envs/ai_env/bin/activate
```

### Add NVIDIA Bridge

Even with `--system-site-packages`, Python 3.12 might not find system packages. Add a bridge:

```bash
echo "/usr/lib/python3/dist-packages" > $(python -c "import site; print(site.getsitepackages()[0])")/nvidia_bridge.pth
```

### Verify Access

```bash
python -c "import tensorrt; print('TensorRT:', trt.__version__)"
python -c "import cv2; print('OpenCV:', cv2.__version__)"
```

## Option B: Using pyenv

### Install pyenv

```bash
curl https://pyenv.run | bash
```

Add to `.bashrc`:

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
eval "$(pyenv virtualenv-init -)"
```

### Install Python Version

```bash
pyenv install 3.12.2
pyenv virtualenv 3.12.2 ai_env
pyenv activate ai_env
```

> **Note**: When using pyenv, you won't automatically see system packages. You'll need to reinstall CUDA-dependent libraries.

## Deactivate Environment

```bash
deactivate
```

## Remove Environment (If Needed)

```bash
rm -rf ~/envs/ai_env
```

## When to Use Which Option

| Option | Use Case |
|--------|----------|
| venv + system-site-packages | Recommended for most users; keeps system CUDA access |
| pyenv | When you need multiple Python versions |

## Next Steps

- [Install PyTorch with CUDA](03-pytorch-installation.md)
- [Homebrew + Python](02-homebrew-python.md) - Alternative Python setup
