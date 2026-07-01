# Creative Studio - LTX-2.3 Setup

## Overview

This guide covers setting up LTX-2.3 for video generation on your Jetson AGX Orin. Due to the model's size (22B parameters), we'll explore multiple deployment options.

## Deployment Options

### Option 1: Cloud API (Recommended for Jetson)

Since LTX-2.3 requires significant GPU resources, the most practical approach for Jetson is using the cloud API:

```python
# config/ltx_config.py

LTX_CONFIG = {
    "provider": "fal_ai",  # or "local", "comfyui"
    
    # FAL.ai API (recommended)
    "fal_ai": {
        "api_key": os.environ.get("FAL_API_KEY", ""),
        "endpoint": "ltx-2-3",
        "webhook_url": os.environ.get("FAL_WEBHOOK_URL", ""),
        "timeout": 300  # seconds
    },
    
    # Local execution (if sufficient VRAM)
    "local": {
        "model_path": "/opt/creative-studio/models/ltx-2.3",
        "model_size": "22b",
        "precision": "bf16",  # or "fp16", "int8"
        "device": "cuda",
        "max_batch_size": 1
    },
    
    # ComfyUI integration
    "comfyui": {
        "address": "http://localhost:8188",
        "workflow_dir": "/opt/creative-studio/workflows"
    },
    
    # Generation defaults
    "defaults": {
        "fps": 24,
        "duration": 5,
        "resolution": "1216x704",
        "aspect_ratio": "16:9",
        "quality": "high",  # or "fast"
        "seed": -1
    }
}
```

### Option 2: FAL.ai API

```python
#!/usr/bin/env python3
"""
FAL.ai LTX-2.3 API Client
"""

import os
import json
import logging
import time
import requests
from typing import Dict, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "api_key": os.environ.get("FAL_API_KEY", ""),
    "timeout": 300
}


class FALLTXClient:
    """FAL.ai LTX-2.3 API client"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or CONFIG["api_key"]
        self.base_url = "https://queue.fal.run/ltx-2-3"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_text2video(
        self,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704",
        quality: str = "high",
        seed: int = -1,
        webhook_url: str = None
    ) -> Dict:
        """Generate text-to-video"""
        
        width, height = map(int, resolution.split("x"))
        
        payload = {
            "prompt": prompt,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "quality": quality,
            "seed": seed
        }
        
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        logger.info(f"Starting text-to-video generation: {prompt[:50]}...")
        
        # Submit request
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
        
        result = response.json()
        
        # Get request ID
        request_id = result.get("request_id")
        
        # Poll for result
        return self.poll_result(request_id)
    
    def generate_image2video(
        self,
        image_url: str,
        prompt: str = "",
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704",
        quality: str = "high",
        seed: int = -1
    ) -> Dict:
        """Generate image-to-video"""
        
        width, height = map(int, resolution.split("x"))
        
        payload = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "quality": quality,
            "seed": seed
        }
        
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
        
        result = response.json()
        request_id = result.get("request_id")
        
        return self.poll_result(request_id)
    
    def generate_audio2video(
        self,
        audio_url: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704"
    ) -> Dict:
        """Generate audio-to-video"""
        
        width, height = map(int, resolution.split("x"))
        
        payload = {
            "audio_url": audio_url,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height
        }
        
        response = requests.post(
            self.base_url + "/audio-to-video",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        request_id = result.get("request_id")
        
        return self.poll_result(request_id)
    
    def extend_video(
        self,
        video_url: str,
        prompt: str,
        duration: int = 5
    ) -> Dict:
        """Extend existing video"""
        
        payload = {
            "video_url": video_url,
            "prompt": prompt,
            "duration": duration
        }
        
        response = requests.post(
            self.base_url + "/extend",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        request_id = result.get("request_id")
        
        return self.poll_result(request_id)
    
    def poll_result(self, request_id: str, max_wait: int = 300) -> Dict:
        """Poll for generation result"""
        
        status_url = f"https://queue.fal.run/ltx-2-3/requests/{request_id}/status"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(status_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                time.sleep(2)
                continue
            
            status = response.json()
            
            logger.info(f"Status: {status.get('status')}")
            
            if status.get("status") == "COMPLETED":
                return status.get("response")
            
            elif status.get("status") == "FAILED":
                raise Exception(f"Generation failed: {status.get('error')}")
            
            time.sleep(2)
        
        raise Exception("Timeout waiting for generation")


# Example Usage

if __name__ == "__main__":
    client = FALLTXClient()
    
    # Text-to-video
    result = client.generate_text2video(
        prompt="A serene lake at sunset with birds flying",
        duration=5,
        fps=24
    )
    
    print(f"Video URL: {result.get('video', {}).get('url')}")
    print(f"Audio URL: {result.get('audio', {}).get('url')}")
```

### Option 3: ComfyUI Integration

```python
#!/usr/bin/env python3
"""
LTX-2.3 ComfyUI Workflow
"""

import requests
import json
from pathlib import Path

COMFYUI_ADDRESS = "http://localhost:8188"
WORKFLOW_DIR = Path("/opt/creative-studio/workflows")


# LTX-2.3 Text-to-Video Workflow
TEXT2VIDEO_WORKFLOW = {
    "nodes": [
        {
            "id": 1,
            "type": "TextPrompt",
            "pos": [100, 100],
            "size": [300, 80],
            "flags": {},
            "order": 0,
            "mode": 0,
            "outputs": [
                {"name": "PROMPT", "type": "STRING", "links": [10]}
            ],
            "properties": {"Node name for S&R": "TextPrompt"},
            "widgets_values": ["A cinematic shot of a spaceship orbiting a planet"]
        },
        {
            "id": 2,
            "type": "LTXVideoLoader",
            "pos": [100, 200],
            "size": [300, 80],
            "flags": {},
            "order": 1,
            "mode": 0,
            "outputs": [
                {"name": "MODEL", "type": "MODEL", "links": [11]}
            ],
            "properties": {"Node name for S&R": "LTXVideoLoader"},
            "widgets_values": ["ltx-2.3-22b-dev"]
        },
        {
            "id": 3,
            "type": "LTXVideoGenerate",
            "pos": [500, 100],
            "size": [400, 300],
            "flags": {},
            "order": 2,
            "mode": 0,
            "inputs": [
                {"name": "model", "type": "MODEL", "link": 11},
                {"name": "prompt", "type": "STRING", "link": 10}
            ],
            "outputs": [
                {"name": "VIDEO", "type": "VIDEO", "links": [12]}
            ],
            "properties": {"Node name for S&R": "LTXVideoGenerate"},
            "widgets_values": [5, 24, 1216, 704, 1, 42]
        },
        {
            "id": 4,
            "type": "SaveVideo",
            "pos": [1000, 100],
            "size": [300, 80],
            "flags": {},
            "order": 3,
            "mode": 0,
            "inputs": [
                {"name": "video", "type": "VIDEO", "link": 12}
            ],
            "properties": {"Node name for S&R": "SaveVideo"},
            "widgets_values": ["/opt/creative-studio/outputs/video.mp4"]
        }
    ],
    "links": [
        [10, 1, 0, "STRING", "STRING"],
        [11, 2, 0, "MODEL", "MODEL"],
        [12, 3, 0, "VIDEO", "VIDEO"]
    ],
    "groups": [],
    "config": {},
    "extra": {"ds": {"scale": 1.0, "offset": [0, 0]}},
    "version": 0.4
}


class ComfyUIClient:
    """ComfyUI API client for LTX-2.3"""
    
    def __init__(self, address: str = COMFYUI_ADDRESS):
        self.address = address
    
    def queue_workflow(self, workflow: Dict) -> str:
        """Queue a workflow for execution"""
        
        response = requests.post(
            f"{self.address}/prompt",
            json={"prompt": workflow}
        )
        
        if response.status_code != 200:
            raise Exception(f"Queue error: {response.text}")
        
        result = response.json()
        return result.get("prompt_id")
    
    def get_status(self, prompt_id: str) -> Dict:
        """Get workflow status"""
        
        response = requests.get(f"{self.address}/history/{prompt_id}")
        
        if response.status_code == 200:
            return response.json()
        
        return {}
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704",
        seed: int = -1
    ) -> str:
        """Generate video via ComfyUI"""
        
        # Prepare workflow
        workflow = json.loads(json.dumps(TEXT2VIDEO_WORKFLOW))
        
        # Update prompt node
        for node in workflow["nodes"]:
            if node["type"] == "TextPrompt":
                node["widgets_values"][0] = prompt
            elif node["type"] == "LTXVideoGenerate":
                width, height = map(int, resolution.split("x"))
                node["widgets_values"] = [
                    duration,  # duration
                    fps,       # fps
                    width,     # width
                    height,    # height
                    1,         # cfg_scale
                    seed       # seed
                ]
        
        # Queue workflow
        prompt_id = self.queue_workflow(workflow)
        
        return prompt_id
```

### Option 4: Local Execution (High-end GPU only)

For systems with sufficient VRAM (48GB+):

```bash
# Install LTX-2.3 locally
git clone https://github.com/Lightricks/LTX-2.git
cd LTX-2
uv sync --frozen
source .venv/bin/activate

# Download model
huggingface-cli download Lightricks/LTX-2.3 ltx-2.3-22b-dev --local-dir /models/ltx-2.3

# Run inference
python -m ltx_v2.generate \
    --model ltx-2.3-22b-dev \
    --prompt "Your prompt here" \
    --duration 5 \
    --fps 24 \
    --output output.mp4
```

## Prompt Engineering

### Best Practices

```python
# Prompt templates for LTX-2.3

PROMPT_TEMPLATES = {
    "cinematic": """Cinematic {subject}, {action}, {setting}, 
                    film grain, 35mm, professional cinematography, 
                    dramatic lighting, {mood}""",
    
    "animation": """Animated style, {character}, {action}, 
                    {environment}, vibrant colors, 
                    smooth motion, {style}""",
    
    "realistic": """Photorealistic {subject}, {action}, 
                    {setting}, natural lighting, 
                    detailed textures, 8k quality""",
    
    "abstract": """Abstract {concept}, {style}, flowing motion, 
                   vibrant colors, mesmerizing patterns, 
                   {mood} atmosphere"""
}


def enhance_prompt(prompt: str, style: str = "cinematic") -> str:
    """Enhance prompt with style template"""
    
    template = PROMPT_TEMPLATES.get(style, PROMPT_TEMPLATES["cinematic"])
    
    # Use Ollama to expand prompt
    enhancement_prompt = f"""Expand this video prompt to be more detailed and effective:

Original: {prompt}

Create a detailed LTX-2.3 video generation prompt that includes:
- Main subject description
- Action/movement
- Setting/environment
- Lighting and mood
- Camera angles
- Technical quality

Return ONLY the enhanced prompt, no explanation."""

    # Call Ollama
    import requests
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5-coder:14b",
            "prompt": enhancement_prompt,
            "stream": False
        }
    )
    
    result = response.json()
    return result.get("response", prompt)
```

## Configuration

```python
# config/generators.py

GENERATOR_CONFIG = {
    # Primary generator (default)
    "primary": "fal_ai",  # or "comfyui", "local"
    
    # Fallback generators
    "fallbacks": ["comfyui", "fal_ai"],
    
    # Generation presets
    "presets": {
        "fast": {
            "quality": "fast",
            "duration": 3,
            "fps": 24
        },
        "quality": {
            "quality": "high",
            "duration": 5,
            "fps": 48
        },
        "portrait": {
            "resolution": "1080x1920",
            "duration": 5,
            "fps": 24
        }
    }
}
```

## Environment Variables

```bash
# Set in /opt/creative-studio/.env

# FAL.ai API (recommended)
export FAL_API_KEY="your_fal_api_key"
export FAL_WEBHOOK_URL="https://your-webhook.com/webhook"

# ComfyUI (optional)
export COMFYUI_ADDRESS="http://localhost:8188"

# Local model (optional)
export LTX_MODEL_PATH="/models/ltx-2.3"

# Output directory
export OUTPUT_DIR="/opt/creative-studio/outputs"
```

## Jetson AGX Orin Local Setup

Since LTX-2.3 requires significant resources, here's how to run it locally on your 64GB Orin:

### 1. Install Jetson-Optimized PyTorch

**Do NOT use standard pip install torch** - you need the NVIDIA-optimized build for aarch64:

```bash
# Update system
sudo apt-get update
sudo apt-get install -y libopenblas-dev python3-pip libjpeg-dev zlib1g-dev

# Install PyTorch for JetPack 6.2 (CUDA 12.6)
pip3 install --no-cache-dir torch torchvision torchaudio \
  --index-url https://pypi.jetson-ai-lab.io/jp6/cu126
```

### 2. Install LTX-2.3 Dependencies

```bash
# Core AI libraries
pip3 install diffusers transformers accelerate sentencepiece

# Optimization for FP8/BF16 efficiency
pip3 install optimum-quanto

# Video processing
sudo apt-get install -y ffmpeg
pip3 install av
```

### 3. Configure Unified Memory

Your Orin has 64GB shared memory. Add to ~/.bashrc:

```bash
export JETSON_MAX_ALLOC_PERCENT=90
source ~/.bashrc
```

### 4. Run Local Inference (Python)

Use the **distilled** model in **FP8** to stay under 28GB memory:

```python
import torch
from diffusers import LTXVideoPipeline
from diffusers.utils import export_to_video

# Use distilled version for Orin
model_id = "Lightricks/LTX-Video"

pipe = LTXVideoPipeline.from_pretrained(model_id, torch_dtype=torch.bfloat16)
pipe.to("cuda")

# Do NOT use pipe.enable_model_cpu_offload() on Orin

prompt = "A cinematic shot of a robotic hand assembling a circuit board, high detail, 4k."

video_frames = pipe(
    prompt=prompt,
    num_inference_steps=8,  # 8 for distilled, 25-50 for dev
    height=480,
    width=704,
    num_frames=81,  # Must be divisible by 8 + 1
    decode_chunk_size=8,  # Lower if OOM during VAE decode
).frames[0]

export_to_video(video_frames, "output.mp4", fps=24)
```

### 5. ComfyUI on Jetson

Create a dedicated environment:

```bash
# Create virtual environment
cd ~
python3 -m venv comfy-orin
source comfy-orin/bin/activate

# Install Jetson PyTorch
pip3 install --no-cache-dir torch torchvision torchaudio \
  --index-url https://pypi.jetson-ai-lab.io/jp6/cu126

# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Install LTXVideo custom nodes
cd custom_nodes
git clone https://github.com/Lightricks/ComfyUI-LTXVideo
cd ComfyUI-LTXVideo
pip install -r requirements.txt
```

### 6. ComfyUI Launch for Orin

```bash
# Set memory allocation
export JETSON_MAX_ALLOC_PERCENT=90

# Launch with Orin-optimized flags
python main.py --preview-method auto --use-pytorch-cross-attention --highvram
```

**Key flags:**
- `--highvram`: Don't offload to CPU (Orin shared memory is faster)
- `--use-pytorch-cross-attention`: Faster on ARM CPU

### 7. Model Files Location

| File Type | Folder | Recommended |
|-----------|--------|-------------|
| Checkpoint | models/checkpoints/ | ltx-2.3-22b-distilled.safetensors |
| Text Encoder | models/text_encoders/ | gemma-2-2b-it |
| VAE | models/vae/ | (usually bundled) |

### 8. Performance Tuning

```bash
# MAXN mode (highest performance)
sudo nvpmodel -m 0
sudo jetson_clocks

# Create swap space (20GB on NVMe)
sudo fallocate -l 20G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 9. VAE Tiling

If you get OOM during "Decoding" stage, use **VAE Decode (Tiled)** node in ComfyUI.

## Important LTX-2.3 Limitations

- Width & height must be divisible by 32
- Frame count must be divisible by 8 + 1
- If not divisible, pad with -1 then crop
- Model may not follow prompts perfectly
- Audio quality may vary without speech

## LTX-2 Official Repository

Full documentation at: https://github.com/Lightricks/LTX-2

### Clone Repository

```bash
git clone https://github.com/Lightricks/LTX-2.git
cd LTX-2
uv sync --frozen
source .venv/bin/activate
```

### Required Model Downloads

Download from HuggingFace: https://huggingface.co/Lightricks/LTX-2.3

**Main Checkpoints:**
| Model | Description | Size |
|-------|-------------|------|
| ltx-2.3-22b-dev | Full model, bf16 | ~44GB |
| ltx-2.3-22b-distilled | 8 steps, CFG=1 | ~22GB |

**Upscalers (for higher resolution):**
| Model | Description |
|-------|-------------|
| ltx-2.3-spatial-upscaler-x2-1.0 | x2 spatial upscaler |
| ltx-2.3-spatial-upscaler-x1.5-1.0 | x1.5 spatial upscaler |
| ltx-2.3-temporal-upscaler-x2-1.0 | x2 temporal upscaler (FPS) |

**LoRAs (for style/motion control):**
| LoRA | Description |
|------|-------------|
| ltx-2.3-22b-distilled-lora-384 | Distilled LoRA |
| LTX-2.3-22b-IC-LoRA-Union-Control | Control appearance |
| LTX-2.3-22b-IC-LoRA-Motion-Track-Control | Motion tracking |
| LTX-2-19b-IC-LoRA-Detailer | Detail enhancement |
| LTX-2-19b-IC-LoRA-Pose-Control | Pose control |
| LTX-2-19b-LoRA-Camera-Control-* | Camera movements (Dolly, Jib, Static) |

### Available Pipelines

```python
# Text-to-Video (Two-Stage - Recommended)
from ltx_pipelines import TI2VidTwoStagesPipeline

# High Quality (res_2s sampler)
from ltx_pipelines import TI2VidTwoStagesHQPipeline

# Single-Stage (Fast prototyping)
from ltx_pipelines import TI2VidOneStagePipeline

# Fastest (8 predefined sigmas)
from ltx_pipelines import DistilledPipeline

# Video-to-Video
from ltx_pipelines import ICLoraPipeline

# Keyframe Interpolation
from ltx_pipelines import KeyframeInterpolationPipeline

# Audio-to-Video
from ltx_pipelines import A2VidPipelineTwoStage

# Retake (Regenerate portion)
from ltx_pipelines import RetakePipeline
```

### Optimization Tips

```bash
# 1. Use DistilledPipeline - Fastest (8 steps)
# 2. Enable FP8 quantization
pipe = LTXVideoPipeline.from_pretrained(
    model_id, 
    quantization=QuantizationPolicy.fp8_cast()
)

# 3. Install xFormers for attention optimization
uv sync --extra xformers

# 4. Use gradient estimation (40 steps -> 20-30)
# 5. Skip memory cleanup between stages if sufficient VRAM
```

### Prompting Guide

Structure your prompts like a cinematographer's shot list:

1. **Start with main action** - Single sentence
2. **Add specific movements** - Gestures, movements
3. **Describe appearances** - Characters, objects
4. **Include background** - Environment details
5. **Specify camera** - Angles, movements
6. **Describe lighting** - Colors, atmosphere
7. **Note changes** - Sudden events

Example:
```
A robot walks through a futuristic corridor, camera follows behind, 
neon lights flicker on walls, metallic footsteps echo, 
suddenly robot stops and turns toward camera, surprised expression, 
cinematic wide shot
```

Use the `enhance_prompt=True` parameter for automatic enhancement!

## Next Steps

- [03-text2video](./03-text2video.md) - Text-to-video workflows
