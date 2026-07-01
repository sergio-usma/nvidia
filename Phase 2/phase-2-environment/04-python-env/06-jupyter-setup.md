# Jupyter Notebook Setup

This guide covers Jupyter Notebook setup for AI development on Jetson AGX Orin.

## Install Jupyter

```bash
pip install jupyter
pip install notebook
```

Or with all dependencies:

```bash
pip install "jupyter[all]"
```

## Install JupyterLab

```bash
pip install jupyterlab
```

## Install JupyterHub

```bash
pip install jupyterhub
npm install -g configurable-http-proxy
```

## Start Jupyter Notebook

```bash
jupyter notebook
```

Start on specific port:

```bash
jupyter notebook --port=8888
```

Start without browser:

```bash
jupyter notebook --no-browser
```

## Start JupyterLab

```bash
jupyter lab
jupyter lab --port=8889
```

## Configuration

Generate config:

```bash
jupyter notebook --generate-config
```

Edit config:

```bash
nano ~/.jupyter/jupyter_notebook_config.py
```

Common settings:

```python
c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = 8888
c.NotebookApp.open_browser = False
c.NotebookApp.password = 'sha1:hash:here'
c.NotebookApp.allow_root = True
```

## Password Protection

Generate password:

```bash
jupyter notebook password
```

Or manually:

```python
from jupyter_server.auth import passwd
passwd('your_password')
```

Copy hash to config.

## Access from Remote

Access via SSH tunnel:

```bash
ssh -L 8888:localhost:8888 jetson@192.168.1.x
```

Then open http://localhost:8888 in browser.

## Install Kernels

### Python Kernel

```bash
python3 -m ipykernel install --user
```

### PyTorch Kernel

```bash
pip install ipykernel
python3 -m ipykernel install --user --name=pytorch --display-name="PyTorch"
```

### Environment-Specific Kernels

```bash
source myenv/bin/activate
python3 -m ipykernel install --user --name=myenv --display-name="My Environment"
```

List kernels:

```bash
jupyter kernelspec list
```

Remove kernel:

```bash
jupyter kernelspec remove kernel_name
```

## Jupyter Extensions

Install extensions:

```bash
pip install jupyter_contrib_nbextensions
jupyter contrib nbextension install --user
```

Useful extensions:
- Table of Contents
- Variable Inspector
- ExecuteTime
- Collapsible Headings

## JupyterLab Extensions

```bash
jupyter labextension install @jupyterlab/toc
jupyter labextension install @jupyter-widgets/jupyterlab-manager
```

## Connect to Ollama from Jupyter

```python
from llama import Llama

generator = Llama(
    model_path="./models/7b/ggml-model.bin",
    n_ctx=2048,
)

response = generator("Explain quantum computing in simple terms")
print(response)
```

## Connect to Ollama API

```python
import requests

def generate(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama2", "prompt": prompt}
    )
    return response.json()["response"]

print(generate("Hello!"))
```

## GPU in Jupyter

Check GPU availability:

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
```

## Jupyter with TensorFlow

```python
import tensorflow as tf
print(f"TensorFlow version: {tf.__version__}")
print(f"GPU: {tf.config.list_physical_devices('GPU')}")
```

## Data Science Packages

```bash
pip install pandas numpy matplotlib seaborn plotly
```

## Image/Video in Jupyter

```python
from IPython.display import Image, display

# Display image
display(Image(filename='image.png'))

# Display video
from IPython.display import HTML
HTML('<video src="video.mp4" controls/>')
```

## Widgets

```bash
pip install ipywidgets
jupyter nbextension enable --py widgetsnbextension
```

Example:

```python
import ipywidgets as widgets
from IPython.display import display

slider = widgets.IntSlider(value=50, min=0, max=100)
display(slider)
```

## JupyterHub on Jetson

Create systemd service:

```bash
sudo nano /etc/systemd/system/jupyterhub.service
```

```ini
[Unit]
Description=JupyterHub
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson
ExecStart=/home/jetson/.local/bin/jupyterhub
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl enable jupyterhub
sudo systemctl start jupyterhub
```

## Security Considerations

1. Always use password
2. Enable SSL/TLS
3. Limit network access
4. Use authentication tokens
5. Regularly update Jupyter

## Running as Service

```bash
sudo nano /etc/systemd/system/jupyter.service
```

```ini
[Unit]
Description=Jupyter Notebook
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson/jupyter
ExecStart=/home/jetson/.local/bin/jupyter notebook --config=/home/jetson/.jupyter/jupyter_notebook_config.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable jupyter
sudo systemctl start jupyter
```
