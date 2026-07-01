# Image Generation

This guide covers image generation on Jetson AGX Orin using diffusion models.

## Stable Diffusion with Diffusers

```bash
pip install diffusers transformers accelerate
```

```python
from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
)
pipe = pipe.to("cuda")

prompt = "a photo of an astronaut riding a horse on mars"
image = pipe(prompt).images[0]
image.save("output.png")
```

## Stable Diffusion WebGPU (CPU)

```bash
pip install huggingface_hub
```

```python
from diffusers import DiffusionPipeline
import torch

# Use CPU
pipe = DiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float32
)
pipe = pipe.to("cpu")

prompt = "a beautiful landscape"
image = pipe(prompt, num_inference_steps=10).images[0]
```

## Lightweight Models for Jetson

```python
# Using smaller model
pipe = DiffusionPipeline.from_pretrained(
    "CompVis/stable-diffusion-v1-4",
    torch_dtype=torch.float16,
    variant="fp16"
)

# Or use TinySD
# https://huggingface.co/segmind/tiny-sd
pipe = DiffusionPipeline.from_pretrained("segmind/tiny-sd")
```

## Image-to-Image

```python
from diffusers import StableDiffusionImg2ImgPipeline
import torch
from PIL import Image

pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")

init_image = Image.open("input.jpg").resize((512, 512))
prompt = "oil painting style"

result = pipe(prompt, image=init_image, strength=0.75).images[0]
result.save("output.jpg")
```

## Inpainting

```python
from diffusers import StableDiffusionInpaintPipeline

pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float16
).to("cuda")

init_image = Image.open("image.jpg").resize((512, 512))
mask_image = Image.open("mask.jpg").resize((512, 512))
prompt = "a cat sitting on a couch"

result = pipe(prompt=prompt, image=init_image, mask_image=mask_image).images[0]
```

## ControlNet

```bash
pip install controlnet-aux
```

```python
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
from PIL import Image
import torch

controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/sd-controlnet-canny",
    torch_dtype=torch.float16
)

pipe = StableDiffusionControlNetPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    controlnet=controlnet,
    torch_dtype=torch.float16
).to("cuda")

control_image = Image.open("canny_edge.jpg").resize((512, 512))
prompt = "a modern living room"

result = pipe(prompt, image=control_image).images[0]
```

## Text-to-Image with Optimizations

```python
# Enable optimizations
pipe.enable_attention_slicing()
pipe.enable_vae_slicing()
pipe.enable_vae_tiling()

# Reduce memory usage
pipe.enable_model_cpu_offload()

prompt = "high quality photo"
image = pipe(prompt, height=512, width=512).images[0]
```

## Lora Weights

```python
from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")

# Load LoRA
pipe.load_lora_weights("path/to/lora")
image = pipe("prompt with lora style").images[0]
```

## API Server

```python
from flask import Flask, request, jsonify
from diffusers import StableDiffusionPipeline
import torch

app = Flask(__name__)
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json['prompt']
    image = pipe(prompt).images[0]
    image.save('/tmp/output.png')
    return jsonify({'url': '/tmp/output.png'})
```

## Performance on Jetson

```python
# Use smaller resolution
image = pipe(prompt, height=256, width=256).images[0]

# Reduce steps
image = pipe(prompt, num_inference_steps=15).images[0]

# Use quantization
pipe = DiffusionPipeline.from_pretrained(
    "segmind/tiny-sd",
    torch_dtype=torch.int8
)
```

## Comparison

| Model | VRAM | Speed | Quality |
|-------|------|-------|---------|
| SD 1.5 | 8GB+ | Slow | High |
| Tiny SD | 2GB | Fast | Medium |
| LCM | 4GB | Fast | High |

## Running with Ollama (LLM)

```python
import requests

def generate_with_llm(prompt):
    # Get description from LLM
    response = requests.post('http://localhost:11434/api/generate', json={
        'model': 'llama2',
        'prompt': f'Describe in detail: {prompt}',
        'stream': False
    })
    description = response.json()['response']
    
    # Generate image
    image = pipe(description).images[0]
    return image
```
