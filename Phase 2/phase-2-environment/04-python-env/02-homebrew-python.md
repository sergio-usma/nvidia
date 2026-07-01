# Install Python via Homebrew

Homebrew (Linuxbrew) provides up-to-date Python versions for ARM64.

## Install Homebrew Dependencies

```bash
sudo apt update
sudo apt install build-essential procps curl file git
```

## Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Add Homebrew to PATH

```bash
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

## Verify Homebrew

```bash
brew doctor
```

## Install Python 3.12

```bash
brew install python@3.12
```

## Verify Installation

```bash
which python3.12
python3.12 --version
```

## Create Virtual Environment with Homebrew Python

```bash
python3.12 -m venv --system-site-packages ~/jetson_ai_env
source ~/jetson_ai_env/bin/activate
```

## Add NVIDIA Bridge

```bash
echo "/usr/lib/python3/dist-packages" > $(python -c "import site; print(site.getsitepackages()[0])")/nvidia_bridge.pth
```

## Install Node.js (Optional)

```bash
brew install node
node -v
npm -v
```

## Next Steps

- [Install PyTorch](03-pytorch-installation.md)
- [Set Up Node.js via NVM](../part-4-nodejs/01-nodejs-nvm.md)
