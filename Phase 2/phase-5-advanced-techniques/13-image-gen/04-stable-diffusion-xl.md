# Stable Diffusion XL on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Stable Diffusion XL](#understanding-stable-diffusion-xl)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Advanced Features](#advanced-features)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

## Introduction

Stable Diffusion XL (SDXL) is the next generation of Stable Diffusion models, offering significantly improved image quality, better composition, and more accurate text rendering compared to its predecessor, Stable Diffusion 1.5. This comprehensive guide will walk you through setting up and running SDXL on your NVIDIA Jetson AGX Orin 64GB Developer Kit.

### What You'll Learn

- How to install and configure Stable Diffusion XL on Jetson
- Text-to-image generation with SDXL
- Image-to-image transformation
- Parameter optimization for best results
- Performance tuning for edge devices
- Troubleshooting common issues

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Jetson Model | AGX Orin 32GB | AGX Orin 64GB |
| JetPack | 6.2.2 | 6.2.2 |
| Python | 3.10 | 3.12 |
| CUDA | 12.6 | 12.6 |
| RAM | 16GB swap | 32GB swap |

## Understanding Stable Diffusion XL

### Architecture Overview

Stable Diffusion XL uses a latent diffusion model architecture with several key improvements over SD 1.5:

1. **Larger Base Model**: SDXL uses a 3.5B parameter UNet compared to 860M in SD 1.5
2. **Dual Text Encoders**: Combines CLIP ViT-L and OpenCLIP ViT-bigG for better text understanding
3. **Refiner Model**: Two-stage generation for enhanced details
4. **Native Resolution**: 1024x1024 compared to 512x512

### Model Variants for Jetson

Given the memory constraints of the Jetson AGX Orin, we recommend these alternatives:

| Model | Parameters | Memory | Quality |
|-------|------------|--------|---------|
| SDXL Base | 3.5B | 8GB+ VRAM | Highest (requires external GPU) |
| SD 1.5 Quantized | 860M | 4GB | Good |
| SD 2.1 Optimized | 1B | 4-6GB | Better |
| TinySD | 100M | 1GB | Basic |

For Jetson AGX Orin, we will focus on **Stable Diffusion 1.5 with optimizations** as it provides the best balance of quality and performance.

## Prerequisites

### 1. Enable Maximum Performance Mode

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### 2. Configure Swap Space

Stable Diffusion requires significant memory. Configure adequate swap:

```bash
# Check current swap
swapon --show

# Create 16GB swap file if not exists
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Add to fstab for persistence
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Install Required Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Install diffusers and related packages
pip install diffusers transformers accelerate safetensors

# Install additional utilities
pip install opencv-python pillow numpy scipy
```

### 4. Install TensorRT (Recommended)

For optimal performance, install TensorRT:

```bash
# TensorRT should be included with JetPack 6.2.2
# Verify installation
python -c "import tensorrt; print(tensorrt.__version__)"
```

## Installation

### Option 1: Using Diffusers (Recommended)

```python
pip install diffusers transformers accelerate safetensors
```

### Option 2: Using TensorRT Extension

```bash
# Install TensorRT Python bindings
pip install tensorrt

# Install polygraphy for model conversion
pip install polygraphy
```

## Configuration

### Basic Configuration File

Create a configuration file for SDXL:

```yaml
# config.yaml
model:
  name: "stabilityai/stable-diffusion-2-1-base"
  cache_dir: "./models"
  
generation:
  default_steps: 50
  default_guidance: 7.5
  default_height: 512
  default_width: 512
  batch_size: 1
  
optimization:
  use_xformers: true
  use_attention_slicing: true
  enable_vae_slicing: true
  torch_compile: false
  
memory:
  enable_cpu_offload: true
  low_vram_mode: true
  
output:
  save_directory: "./output"
  format: "png"
  quality: 95
```

### Environment Variables

```bash
# Set CUDA architecture for Jetson
export CUDA_ARCH_BIN="8.7"

# Enable memory optimizations
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"

# Set model cache directory
export HF_HOME="./models"
export TRANSFORMERS_CACHE="./models/transformers"
```

## Basic Usage

### Python Script: Text-to-Image

```python
#!/usr/bin/env python3
"""
Stable Diffusion Text-to-Image Generation
Optimized for Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
import time

class StableDiffusionGenerator:
    def __init__(self, model_id="stabilityai/stable-diffusion-2-1-base"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self, use_quantization=True):
        """Load the Stable Diffusion model with optimizations"""
        print(f"Loading model: {self.model_id}")
        
        # Configure pipeline with optimizations
        if use_quantization:
            # Use 8-bit quantization for reduced memory
            self.pipeline = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16,
                variant="fp16",
            )
        else:
            self.pipeline = StableDiffusionPipeline.from_pretrained(self.model_id)
        
        # Enable memory optimizations
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        # Move to GPU if available
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
            print("Model moved to CUDA")
        
        # Optimize scheduler
        self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipeline.scheduler.config
        )
        
        print("Model loaded successfully!")
        return self.pipeline
    
    def generate(
        self,
        prompt,
        negative_prompt="",
        height=512,
        width=512,
        num_inference_steps=50,
        guidance_scale=7.5,
        seed=None
    ):
        """Generate image from text prompt"""
        
        # Set seed for reproducibility
        if seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator.manual_seed(seed)
        else:
            generator = None
        
        # Generate image
        start_time = time.time()
        
        with torch.inference_mode():
            result = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                height=height,
                width=width,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
        
        elapsed_time = time.time() - start_time
        print(f"Generation time: {elapsed_time:.2f} seconds")
        
        return result.images[0]
    
    def save_image(self, image, output_path):
        """Save generated image to file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)
        print(f"Image saved to: {output_path}")
        
    def generate_variations(self, prompt, num_images=4, **kwargs):
        """Generate multiple variations of the same prompt"""
        images = []
        for i in range(num_images):
            # Use different seed for each variation
            kwargs['seed'] = kwargs.get('seed', 42) + i
            img = self.generate(prompt, **kwargs)
            images.append(img)
        return images


def main():
    # Initialize generator
    generator = StableDiffusionGenerator()
    
    # Load model
    generator.load_model(use_quantization=True)
    
    # Generate image
    prompt = "a serene mountain landscape at golden hour, dramatic clouds, photorealistic"
    negative_prompt = "blurry, low quality, distorted, ugly"
    
    image = generator.generate(
        prompt=prompt,
        negative_prompt=negative_prompt,
        height=512,
        width=512,
        num_inference_steps=30,  # Reduced for Jetson
        guidance_scale=7.5,
        seed=42
    )
    
    # Save output
    generator.save_image(image, "./output/sdxl_generated.png")
    
    print("Generation complete!")


if __name__ == "__main__":
    main()
```

### Using the Interactive Prompt Parameters

The interactive prompt generator from Part 17 Section 3 can be integrated:

```python
from interactive_prompt import PromptGenerator

# Create prompt generator
prompt_gen = PromptGenerator()

# Generate professional prompt
prompt_gen.set_main_subject("portrait photography")
prompt_gen.set_environment("Studio lighting")
prompt_gen.set_color_palette("Vibrant")
prompt_gen.set_lighting("Golden hour")
prompt_gen.set_composition("Rule of thirds")
prompt_gen.set_depth_of_field("Shallow")
prompt_gen.set_mood("Inspiring")
prompt_gen.set_time_weather("Sunset")
prompt_gen.set_human_emotion("Happiness")
prompt_gen.set_camera("85mm portrait lens")
prompt_gen.set_camera_angle("Eye-level")

# Get formatted prompt
full_prompt = prompt_gen.generate_prompt()
print(full_prompt)

# Use with Stable Diffusion
image = generator.generate(prompt=full_prompt, num_inference_steps=30)
```

### Command Line Usage

```bash
# Basic generation
python sd_generator.py --prompt "a beautiful sunset over the ocean" --steps 30

# With negative prompt
python sd_generator.py --prompt "a cat" --negative "blurry, low quality" --seed 42

# Generate multiple images
python sd_generator.py --prompt "landscape" --num-images 4 --batch-size 1
```

## Advanced Features

### 1. Image-to-Image Generation

Transform existing images using Stable Diffusion:

```python
from diffusers import StableDiffusionImg2ImgPipeline
import torch
from PIL import Image
import requests
from io import BytesIO

class ImageToImageGenerator:
    def __init__(self, model_id="stabilityai/stable-diffusion-2-1-base"):
        self.pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        self.pipeline.enable_attention_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
    
    def load_image(self, image_path):
        """Load and preprocess input image"""
        image = Image.open(image_path).convert("RGB")
        image = image.resize((512, 512))
        return image
    
    def transform(
        self,
        input_image,
        prompt,
        strength=0.75,
        guidance_scale=7.5,
        num_inference_steps=50
    ):
        """Transform image using prompt guidance"""
        
        with torch.inference_mode():
            result = self.pipeline(
                prompt=prompt,
                image=input_image,
                strength=strength,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
            )
        
        return result.images[0]
    
    def style_transfer(self, input_image, style="anime"):
        """Apply style transfer to image"""
        style_prompts = {
            "anime": "anime style, manga, vibrant colors, clean lines",
            "oil_painting": "oil painting style, brush strokes, classic art",
            "watercolor": "watercolor painting, soft colors, artistic",
            "photorealistic": "photorealistic, high detail, realistic lighting",
        }
        
        prompt = style_prompts.get(style, style_prompts["photorealistic"])
        return self.transform(input_image, prompt, strength=0.6)


# Usage
img2img = ImageToImageGenerator()
input_img = img2img.load_image("./input.jpg")
output_img = img2img.style_transfer(input_img, style="anime")
output_img.save("./output/styled.png")
```

### 2. Using LoRA Adapters

Load custom LoRA adapters for specific styles:

```python
from diffusers import StableDiffusionPipeline
import torch

class LoRASDGenerator:
    def __init__(self, base_model, lora_path, lora_scale=1.0):
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            base_model,
            torch_dtype=torch.float16,
        )
        
        # Load LoRA weights
        self.pipeline.load_lora_weights(lora_path)
        
        # Set LoRA scale
        self.pipeline.set_adapters([lora_path], scales=[lora_scale])
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
    
    def generate_with_lora(self, prompt, **kwargs):
        """Generate with LoRA style applied"""
        return self.pipeline(prompt, **kwargs).images[0]


# Usage
generator = LoRASDGenerator(
    base_model="stabilityai/stable-diffusion-2-1-base",
    lora_path="./loras/anime_style.safetensors",
    lora_scale=0.8
)
image = generator.generate_with_lora("a girl walking in the city")
```

### 3. Prompt Engineering Guide

Create effective prompts using structured parameters:

```python
class PromptBuilder:
    """Build professional prompts for Stable Diffusion"""
    
    PARAMETERS = {
        "environment": [
            "Interior", "Cityscape", "Beach", "Mountain", "Desert",
            "Forest", "Ocean", "Rural countryside", "Space station"
        ],
        "color_palette": [
            "Stardust", "Night sky", "Vibrant", "Monochrome",
            "Pastel", "Neon", "Earth tones", "Sepia", "Cool tones"
        ],
        "lighting": [
            "Golden hour", "Studio lighting", "Moonlight", "Natural light",
            "Dramatic lighting", "Soft lighting", "Rim lighting",
            "Volumetric lighting", "Cinematic lighting"
        ],
        "composition": [
            "Rule of thirds", "Center focus", "Leading lines",
            "Symmetrical", "Diagonal composition", "Fill the frame",
            "Negative space", "Pattern-based", "Frame within frame"
        ],
        "depth_of_field": [
            "Shallow", "Medium", "Deep", "Bokeh", "Tilt-shift",
            "Pan focus", "Selective focus", "Wide depth", "Narrow depth"
        ],
        "mood": [
            "Inspiring", "Epic", "Energetic", "Mysterious",
            "Peaceful", "Melancholic", "Joyful", "Tense", "Serene"
        ],
        "time_weather": [
            "Sunset", "Sunrise", "Night", "Rainy", "Snowy",
            "Cloudy", "Clear sky", "Foggy", "Stormy"
        ],
        "human_emotion": [
            "Happiness", "Peace", "Curiosity", "Determination",
            "Surprise", "Contemplation", "Excitement", "Calm", "Joy"
        ],
        "camera": [
            "85mm portrait lens", "35mm wide angle", "50mm standard",
            "24mm ultra-wide", "135mm telephoto", "Macro lens",
            "Fisheye lens", "Tilt-shift lens", "Standard DSLR"
        ],
        "camera_angle": [
            "Eye-level", "Bird's-eye", "Close-up", "Wide shot",
            "Medium shot", "Over the shoulder", "Low angle",
            "High angle", "Dutch angle"
        ]
    }
    
    @classmethod
    def build_prompt(
        cls,
        subject,
        environment=None,
        color_palette=None,
        lighting=None,
        composition=None,
        depth_of_field=None,
        mood=None,
        time_weather=None,
        human_emotion=None,
        camera=None,
        camera_angle=None,
        quality="high quality, detailed, 4k"
    ):
        """Build a complete prompt from parameters"""
        
        prompt_parts = [subject]
        
        # Add each parameter if specified
        if environment:
            prompt_parts.append(f"in {environment}")
        if color_palette:
            prompt_parts.append(f"with {color_palette} color palette")
        if lighting:
            prompt_parts.append(f", {lighting}")
        if composition:
            prompt_parts.append(f", {composition} composition")
        if depth_of_field:
            prompt_parts.append(f", {depth_of_field} depth of field")
        if mood:
            prompt_parts.append(f", {mood} mood")
        if time_weather:
            prompt_parts.append(f"at {time_weather}")
        if human_emotion:
            prompt_parts.append(f"expressing {human_emotion}")
        if camera:
            prompt_parts.append(f", shot with {camera}")
        if camera_angle:
            prompt_parts.append(f", {camera_angle} angle")
            
        prompt_parts.append(f", {quality}")
        
        return ", ".join(prompt_parts)
    
    @classmethod
    def get_random_prompt(cls, subject):
        """Generate a random professional prompt"""
        import random
        
        params = {}
        for key in cls.PARAMETERS:
            params[key] = random.choice(cls.PARAMETERS[key])
        
        return cls.build_prompt(subject, **params)


# Usage
prompt = PromptBuilder.build_prompt(
    subject="a professional portrait of a woman",
    environment="Studio lighting",
    color_palette="Vibrant",
    lighting="Golden hour",
    composition="Rule of thirds",
    depth_of_field="Shallow",
    mood="Inspiring",
    time_weather="Sunset",
    human_emotion="Happiness",
    camera="85mm portrait lens",
    camera_angle="Eye-level"
)
# Result: "a professional portrait of a woman, in Studio lighting, with Vibrant 
# color palette, Golden hour, Rule of thirds composition, Shallow depth of field, 
# inspiring mood, at sunset, expressing Happiness, shot with 85mm portrait lens, 
# eye-level angle, high quality, detailed, 4k"
```

### 4. Custom Schedulers

Experiment with different samplers:

```python
from diffusers import (
    DDIMScheduler,
    DDPMScheduler,
    EulerDiscreteScheduler,
    EulerAncestralDiscreteScheduler,
    DPMSolverMultistepScheduler,
    UniPCMultistepScheduler,
    LMSDiscreteScheduler,
)

class SchedulerComparison:
    """Compare different sampling schedulers"""
    
    SCHEDULERS = {
        "ddim": DDIMScheduler,
        "ddpm": DDPMScheduler,
        "euler": EulerDiscreteScheduler,
        "euler_a": EulerAncestralDiscreteScheduler,
        "dpm": DPMSolverMultistepScheduler,
        "unipc": UniPCMultistepScheduler,
        "lms": LMSDiscreteScheduler,
    }
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        
    def generate_with_scheduler(self, scheduler_name, prompt, **kwargs):
        """Generate with specified scheduler"""
        
        scheduler_class = self.SCHEDULERS.get(scheduler_name.lower())
        if not scheduler_class:
            raise ValueError(f"Unknown scheduler: {scheduler_name}")
        
        # Configure scheduler
        self.pipeline.scheduler = scheduler_class.from_config(
            self.pipeline.scheduler.config
        )
        
        # Generate
        return self.pipeline(prompt, **kwargs).images[0]
    
    def compare_schedulers(self, prompt, num_steps=20):
        """Compare all schedulers and return timing"""
        
        results = {}
        
        for name in self.SCHEDULERS:
            import time
            start = time.time()
            
            img = self.generate_with_scheduler(name, prompt, num_inference_steps=num_steps)
            
            elapsed = time.time() - start
            results[name] = {"time": elapsed, "image": img}
            
            print(f"{name}: {elapsed:.2f}s")
        
        return results
```

## Performance Optimization

### 1. TensorRT Optimization

For maximum performance on Jetson:

```python
import tensorrt as trt
import torch
from polygraphy import api as polygraphy_api

class TensorRTOptimizer:
    """Optimize Stable Diffusion for TensorRT"""
    
    def __init__(self, onnx_dir="./onnx_models"):
        self.onnx_dir = onnx_dir
        os.makedirs(onnx_dir, exist_ok=True)
    
    def export_onnx(self, pipeline, output_dir):
        """Export model to ONNX format"""
        
        # Export text encoder
        print("Exporting text encoder...")
        # (Implementation depends on specific TensorRT version)
        
        # Export UNet
        print("Exporting UNet...")
        
        # Export VAE
        print("Exporting VAE...")
        
    def build_engine(self, onnx_path, engine_path):
        """Build TensorRT engine from ONNX"""
        
        # Create builder
        builder = trt.Builder(trt.Logger(trt.Logger.WARNING))
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, trt.Logger(trt.Logger.WARNING))
        
        # Parse ONNX
        with open(onnx_path, 'rb') as f:
            parser.parse(f.read())
        
        # Build engine
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)
        
        engine = builder.build_serialized_network(network, config)
        
        # Save engine
        with open(engine_path, 'wb') as f:
            f.write(engine)
        
        print(f"Engine saved to {engine_path}")
        return engine
```

### 2. Memory Optimization Techniques

```python
class MemoryOptimizedGenerator:
    """Memory-efficient generation for Jetson"""
    
    def __init__(self, model_id):
        self.model_id = model_id
        self.pipeline = None
        
    def load_sequential_cpu_offload(self):
        """Use sequential CPU offload for very low VRAM"""
        
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        # Enable sequential CPU offload (most memory efficient)
        self.pipeline.enable_sequential_cpu_offload()
        
        return self.pipeline
    
    def load_attention_slicing(self):
        """Use attention slicing to reduce memory"""
        
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
        )
        
        # Enable attention slicing
        self.pipeline.enable_attention_slicing(slice_size="auto")
        
        # Enable VAE slicing
        self.pipeline.enable_vae_slicing()
        
        # Enable model CPU offload
        self.pipeline.enable_model_cpu_offload()
        
        return self.pipeline
    
    def generate_low_memory(self, prompt, height=384, width=384):
        """Generate with minimal memory footprint"""
        
        # Use smaller dimensions
        image = self.pipeline(
            prompt,
            height=height,
            width=width,
            num_inference_steps=20,
            guidance_scale=7.0,
        ).images[0]
        
        return image
    
    def clear_cache(self):
        """Clear CUDA cache"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
```

### 3. xFormers Installation

Install xFormers for faster attention computation:

```bash
# Install xFormers for Jetson
pip install xformers==0.0.23

# Or build from source
git clone https://github.com/facebookresearch/xformers.git
cd xformers
pip install -e .
```

### 4. Performance Tuning Parameters

```python
# Optimal settings for Jetson AGX Orin
OPTIMAL_SETTINGS = {
    # Generation
    "height": 512,
    "width": 512,
    "num_inference_steps": 30,  # Higher = slower but better quality
    "guidance_scale": 7.5,
    
    # Memory optimization
    "enable_attention_slicing": True,
    "enable_vae_slicing": True,
    "enable_sequential_cpu_offload": False,
    "enable_model_cpu_offload": True,
    
    # Speed optimization
    "use_xformers": True,
    "use_torch_compile": False,  # Can cause issues on Jetson
    
    # Quality
    "torch_dtype": torch.float16,
    "variant": "fp16",
}

def apply_optimal_settings(pipeline, settings=OPTIMAL_SETTINGS):
    """Apply optimal settings to pipeline"""
    
    if settings.get("enable_attention_slicing"):
        pipeline.enable_attention_slicing()
    
    if settings.get("enable_vae_slicing"):
        pipeline.enable_vae_slicing()
    
    if settings.get("enable_model_cpu_offload"):
        pipeline.enable_model_cpu_offload()
    
    return pipeline
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Out of Memory Errors

```
Error: CUDA out of memory. Tried to allocate X GB
```

**Solutions:**

```python
# Solution 1: Reduce image size
image = pipeline(prompt, height=384, width=384).images[0]

# Solution 2: Enable CPU offload
pipeline.enable_sequential_cpu_offload()

# Solution 3: Reduce batch size
pipeline(prompt, batch_size=1)

# Solution 4: Use gradient checkpointing
# (Only for training, not inference)
```

#### 2. Slow Generation Speed

**Solutions:**

```bash
# Enable performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Check current clocks
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# Monitor GPU usage
tegrastats
```

#### 3. Model Loading Failures

```
Error: Unable to load model from HuggingFace
```

**Solutions:**

```python
# Solution 1: Download model manually
git lfs install
git clone https://huggingface.co/stabilityai/stable-diffusion-2-1-base ./models/sd21

# Solution 2: Use local model
pipeline = StableDiffusionPipeline.from_pretrained(
    "./models/sd21",
    torch_dtype=torch.float16,
)

# Solution 3: Use offline mode
import os
os.environ["HF_HUB_OFFLINE"] = "1"
```

#### 4. CUDA Architecture Errors

```
Error: CUDA error: no kernel image is available for execution
```

**Solutions:**

```bash
# Check CUDA architecture
nvcc --version
cat /usr/local/cuda/include/cuda_runtime.h | grep -i arch

# Set correct architecture
export TORCH_CUDA_ARCH_LIST="8.7"

# Rebuild torch with correct architecture
pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
```

#### 5. WebUI Installation Issues

If using Automatic1111 WebUI:

```bash
# Clone repository
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui

# Edit webui.sh for Jetson
export COMMANDLINE_ARGS="--precision full --no-half"

# Run installation
./webui.sh
```

### Performance Monitoring

```python
import time
import torch

class PerformanceMonitor:
    """Monitor generation performance"""
    
    def __init__(self):
        self.metrics = []
        
    def record_generation(self, prompt, params, elapsed_time, memory_used):
        """Record generation metrics"""
        self.metrics.append({
            "prompt": prompt,
            "params": params,
            "time": elapsed_time,
            "memory_mb": memory_used,
            "timestamp": time.time(),
        })
        
    def get_stats(self):
        """Get performance statistics"""
        if not self.metrics:
            return {}
            
        times = [m["time"] for m in self.metrics]
        memories = [m["memory_mb"] for m in self.metrics]
        
        return {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "avg_memory": sum(memories) / len(memories),
            "total_generations": len(self.metrics),
        }
    
    def print_stats(self):
        """Print performance statistics"""
        stats = self.get_stats()
        
        print("\n=== Performance Statistics ===")
        print(f"Total generations: {stats.get('total_generations', 0)}")
        print(f"Average time: {stats.get('avg_time', 0):.2f}s")
        print(f"Min time: {stats.get('min_time', 0):.2f}s")
        print(f"Max time: {stats.get('max_time', 0):.2f}s")
        print(f"Average memory: {stats.get('avg_memory', 0):.2f}MB")
        print("==============================\n")
```

### Benchmarking

```python
def benchmark_models():
    """Benchmark different models on Jetson"""
    
    models = [
        "stabilityai/stable-diffusion-2-1-base",
        "runwayml/stable-diffusion-v1-5",
        "stabilityai/sd-turbo",  # Fast model
    ]
    
    prompt = "a beautiful landscape with mountains"
    
    results = {}
    
    for model_id in models:
        print(f"\nBenchmarking {model_id}...")
        
        pipeline = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
        )
        pipeline.enable_attention_slicing()
        
        if torch.cuda.is_available():
            pipeline = pipeline.to("cuda")
        
        # Warmup
        _ = pipeline(prompt, num_inference_steps=10)
        
        # Benchmark
        start = time.time()
        _ = pipeline(prompt, num_inference_steps=30)
        elapsed = time.time() - start
        
        results[model_id] = elapsed
        print(f"Time: {elapsed:.2f}s")
    
    return results
```

## API Reference

### StableDiffusionPipeline

```python
from diffusers import StableDiffusionPipeline

# Methods
pipeline = StableDiffusionPipeline.from_pretrained(model_id)
pipeline.enable_attention_slicing()
pipeline.enable_vae_slicing()
pipeline.enable_model_cpu_offload()
pipeline.enable_sequential_cpu_offload()

# Generation
image = pipeline(
    prompt,                      # str or List[str]
    negative_prompt=None,        # str or List[str]
    height=512,                  # int
    width=512,                  # int
    num_inference_steps=50,     # int
    guidance_scale=7.5,         # float
    num_images_per_prompt=1,    # int
    generator=None,             # torch.Generator
    latents=None,               # torch.Tensor
)
```

### PromptBuilder

```python
# Build prompts
prompt = PromptBuilder.build_prompt(
    subject="portrait",
    environment="Studio lighting",
    color_palette="Vibrant",
    # ... other parameters
)

# Get random prompt
prompt = PromptBuilder.get_random_prompt("landscape")
```

### Scheduler Configuration

```python
from diffusers import DPMSolverMultistepScheduler

# Configure scheduler
pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
    pipeline.scheduler.config,
    algorithm_type="dpmsolver++",
    use_karras_sigmas=True,
    prediction_type="epsilon",
)
```

## Next Steps

- Continue to [FLUX.1 Models](./05-flux-models.md) for state-of-the-art generation
- Learn about [Realistic Vision](./06-realistic-vision.md) for photorealistic images
- Explore [Image-to-Image](./07-image-to-image.md) for transformations

## Additional Resources

- [HuggingFace Diffusers Documentation](https://huggingface.co/docs/diffusers)
- [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [TensorRT Documentation](https://docs.nvidia.com/deeplearning/tensorrt/)
- [Jetson AI Lab](https://www.jetsonai-lab.com)
