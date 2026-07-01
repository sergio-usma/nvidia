# Python Virtual Environments

This guide covers Python virtual environments for Jetson AGX Orin with JetPack 6.2.2.

## Why Virtual Environments

- Isolate project dependencies
- Avoid version conflicts
- Reproducible environments

## Using venv

### Create virtual environment

```bash
python3 -m venv myenv
```

### Activate

```bash
source myenv/bin/activate
```

### Deactivate

```bash
deactivate
```

## Using Virtualenvwrapper

Install:

```bash
pip install virtualenvwrapper
```

Configure:

```bash
echo 'export WORKON_HOME=$HOME/.virtualenvs' >> ~/.bashrc
echo 'source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
source ~/.bashrc
```

Commands:

```bash
mkvirtualenv myenv
workon myenv
deactivate
rmvirtualenv myenv
```

## Using Poetry

Install:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Initialize project:

```bash
poetry new myproject
cd myproject
poetry add requests
```

Activate environment:

```bash
poetry shell
```

Install dependencies:

```bash
poetry install
```

## Using Pipenv

Install:

```bash
pip install pipenv
```

Initialize:

```bash
pipenv install requests
pipenv shell
```

## Virtual Environment Best Practices

### Directory structure

```
projects/
├── project1/
│   ├── env/
│   ├── src/
│   └── requirements.txt
└── project2/
    ├── env/
    └── ...
```

### requirements.txt

Generate:

```bash
pip freeze > requirements.txt
```

Install from file:

```bash
pip install -r requirements.txt
```

## Docker with Virtual Environments

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
```

## Using Conda (Alternative)

Install Miniforge:

```bash
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh
```

Create environment:

```bash
conda create -n myenv python=3.12
conda activate myenv
```

## Multiple Python Versions

Check Python versions:

```bash
ls /usr/bin/python*
ls /usr/local/bin/python*
```

Using pyenv:

```bash
curl https://pyenv.run | bash
pyenv install 3.12.0
pyenv global 3.12.0
```

## Environment Management Scripts

Create environment:

```bash
#!/bin/bash
# create-env.sh

ENV_NAME=${1:-myenv}
echo "Creating environment: $ENV_NAME"

python3 -m venv ~/$ENV_NAME
source ~/$ENV_NAME/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "Environment $ENV_NAME created!"
```

Switch environment:

```bash
#!/bin/bash
# switch-env.sh

ENV_NAME=$1
if [ -z "$ENV_NAME" ]; then
    echo "Usage: $0 <environment-name>"
    return 1
fi

source ~/$ENV_NAME/bin/activate
echo "Activated: $VIRTUAL_ENV"
```

## Cleanup

Remove virtual environment:

```bash
rm -rf myenv/
```

Or with virtualenvwrapper:

```bash
rmvirtualenv myenv
```
