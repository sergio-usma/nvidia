# Install PyTorch with CUDA Support

Install PyTorch optimized for your Jetson's CUDA version.

## Install System Dependencies

```bash
sudo apt install -y libopenblas-dev libopenmpi-dev libomp-dev
```

## Activate Your Environment

```bash
source ~/envs/ai_env/bin/activate
```

## Install PyTorch for Jetson

NVIDIA provides pre-compiled wheels for JetPack 6.2 (CUDA 12.6):

```bash
pip install numpy
pip install --index-url https://pypi.jetson-ai-lab.io/jp6/cu126 torch torchvision torchaudio
```

## Verify Installation

```bash
python -c "
import torch
print('PyTorch version:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
"
```

## Test GPU Access

Create a test script:

```python
import torch

# Create tensor on GPU
x = torch.randn(3, 3).cuda()
print('Tensor on GPU:', x)

# Check memory
print('GPU Memory:', torch.cuda.get_device_properties(0).total_memory / 1024**3, 'GB')
```

Run:

```bash
python test_gpu.py
```

## Troubleshooting

### ImportError: numpy not found

```bash
pip install numpy
```

### Illegal instruction error

If you get an illegal instruction error, downgrade NumPy:

```bash
pip install 'numpy<2'
```

### CUDA not available

Verify CUDA is in your path:

```bash
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
source ~/.bashrc
```

## Install Additional ML Libraries

```bash
# Transformers for LLMs
pip install transformers

# Computer vision
pip install opencv-python

# Scientific computing
pip install scipy pandas matplotlib
```

## Next Steps

Now that PyTorch is installed, proceed to:
- [Ollama Setup](../part-5-llms/01-ollama-setup.md)
- [llama.cpp Setup](../part-5-llms/02-llama-cpp.md)
