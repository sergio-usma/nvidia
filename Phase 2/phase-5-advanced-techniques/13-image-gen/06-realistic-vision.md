# Realistic Vision on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Realistic Vision Models](#understanding-realistic-vision-models)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Photorealistic Prompt Engineering](#photorealistic-prompt-engineering)
8. [Advanced Features](#advanced-features)
9. [Quality Optimization](#quality-optimization)
10. [Troubleshooting](#troubleshooting)

## Introduction

Realistic Vision is a specialized branch of AI image generation focused on producing photorealistic images that resemble real photographs. Unlike stylized or artistic generation, realistic vision models are trained on photographic datasets to accurately render:

- Human faces and portraits
- Natural landscapes
- Product photography
- Architectural interiors
- Food and still life
- Wildlife and nature

This guide covers deploying photorealistic image generation on your Jetson AGX Orin 64GB, with emphasis on producing high-quality realistic images within the device's memory constraints.

### Key Features

- Photorealistic human rendering
- Natural lighting simulation
- Accurate texture reproduction
- Proper depth and perspective
- Realistic color accuracy

## Understanding Realistic Vision Models

### Available Models for Jetson

| Model | Size | VRAM | Quality | Best For |
|-------|------|------|---------|----------|
| Realistic Vision V5.1 | 4GB | 6GB | Excellent | General photorealistic |
| Juggernaut XL | 6GB | 8GB | Excellent | Portraits, fashion |
| Deliberate V2 | 3.5GB | 5GB | Good | Artistic realism |
| Photography | 4GB | 5GB | Good | Camera-like output |
| SD 1.5 + Realism LoRA | 4GB | 5GB | Good | Enhanced realism |

### Model Architecture

Realistic vision models use the same underlying architecture as Stable Diffusion but are fine-tuned on photographic datasets:

1. **Enhanced VAE**: Better latent space for photorealistic decoding
2. **Photographic Text Encoder**: Understanding of photography terms
3. **Realism LoRA**: Lightweight adapters for enhanced realism
4. **Negative Embeddings**: Anti-artistic signatures for realism

## Prerequisites

### System Setup

```bash
# Enable maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify CUDA availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0)}')"

# Check available memory
free -h
```

### Python Dependencies

```bash
# Core dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Diffusers and related
pip install diffusers transformers accelerate safetensors

# Image processing
pip install pillow numpy opencv-python pillow-heif

# Additional utilities
pip install scipy torchvision
```

## Installation

### Option 1: Using Diffusers (Recommended)

```python
from diffusers import StableDiffusionPipeline
import torch

# Load Realistic Vision model
pipeline = StableDiffusionPipeline.from_pretrained(
    "SG161222/Realistic_Vision_V5.1_noVAE",
    torch_dtype=torch.float16,
    variant="fp16",
)

# Enable optimizations
pipeline.enable_attention_slicing()
pipeline.enable_vae_slicing()

# Move to GPU
if torch.cuda.is_available():
    pipeline = pipeline.to("cuda")
```

### Option 2: With Custom VAE

```python
from diffusers import StableDiffusionPipeline, AutoencoderKL

# Load with dedicated VAE for better photorealism
vae = AutoencoderKL.from_pretrained(
    "stabilityai/sd-vae-ft-mse",
    torch_dtype=torch.float16,
)

pipeline = StableDiffusionPipeline.from_pretrained(
    "SG161222/Realistic_Vision_V5.1_noVAE",
    vae=vae,
    torch_dtype=torch.float16,
)
```

### Option 3: Using WebUI with Realistic Models

```bash
# Clone Automatic1111 WebUI
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui

# Download Realistic Vision model
# Place in models/Stable-diffusion/Realistic_Vision_V5.1.safetensors

# Run with optimizations
export COMMANDLINE_ARGS="--precision full --no-half --opt-sdp-attention"

./webui.sh
```

## Configuration

### Recommended Settings for Photorealism

```yaml
# realistic_vision_config.yaml
model:
  base_model: "SG161222/Realistic_Vision_V5.1_noVAE"
  vae: "stabilityai/sd-vae-ft-mse"
  
generation:
  default_resolution: [512, 512]
  max_resolution: [768, 768]
  default_steps: 30
  guidance_scale: 7.0
  sampler: "DPM++ 2M Karras"
  
negative_prompt:
  base: "artistic, painting, illustration, cartoon, anime, 3d render, digital art, fantasy, deformed, ugly, bad anatomy, extra limbs, close up, b&w, monochrome"
  
optimization:
  use_fp16: true
  attention_slicing: true
  vae_slicing: true
  enable_sequential_cpu_offload: false
```

### Environment Variables

```bash
# Memory optimization
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"

# Model paths
export HF_HOME="./models"
export TRANSFORMERS_CACHE="./models"
```

## Basic Usage

### Photorealistic Image Generation

```python
#!/usr/bin/env python3
"""
Realistic Vision Image Generator
Optimized for Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
import time

class RealisticVisionGenerator:
    """Generate photorealistic images on Jetson"""
    
    # Comprehensive negative prompts for realism
    NEGATIVE_PROMPT = (
        "artistic, painting, illustration, cartoon, anime, manga, "
        "3d render, digital art, fantasy, deformed, ugly, bad anatomy, "
        "extra limbs, close up, b&w, monochrome, saturated, oversaturated, "
        "high contrast, low contrast, noise, grain, blurry, blur, "
        " watermark, signature, text, logo, frame"
    )
    
    # Photography-specific negative prompts
    PHOTO_NEGATIVE = (
        "render, cgi, illustration, painting, drawing, art, artwork, "
        "plastic, synthetic, doll, toy, artificial, fake, cartoon, "
        "anime, comic, graphic"
    )
    
    def __init__(self, model_id="SG161222/Realistic_Vision_V5.1_noVAE"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self, use_vae=True, use_xformers=False):
        """Load Realistic Vision model with optimizations"""
        
        print(f"Loading model: {self.model_id}")
        
        # Load with optional custom VAE
        if use_vae:
            from diffusers import AutoencoderKL
            vae = AutoencoderKL.from_pretrained(
                "stabilityai/sd-vae-ft-mse",
                torch_dtype=torch.float16,
            )
        else:
            vae = None
        
        # Create pipeline
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.model_id,
            vae=vae,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        # Enable memory optimizations
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        # Use Karras scheduler for better quality
        self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipeline.scheduler.config,
            algorithm_type="dpmsolver++",
            use_karras_sigmas=True,
        )
        
        # Move to GPU
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
            print("Model loaded on CUDA")
        else:
            print("Warning: CUDA not available, using CPU")
        
        print("Model loaded successfully!")
        return self.pipeline
    
    def generate(
        self,
        prompt,
        negative_prompt=None,
        height=512,
        width=512,
        num_inference_steps=30,
        guidance_scale=7.0,
        seed=None
    ):
        """Generate photorealistic image"""
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Combine negative prompts
        if negative_prompt is None:
            negative_prompt = self.NEGATIVE_PROMPT
        
        # Set random seed
        generator = None
        if seed is not None:
            generator = torch.Generator(
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
            generator.manual_seed(seed)
        
        # Generate
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
        
        elapsed = time.time() - start_time
        print(f"Generated in {elapsed:.2f}s")
        
        return result.images[0]
    
    def generate_portrait(
        self,
        subject_description,
        lighting="natural daylight",
        camera="85mm",
        **kwargs
    ):
        """Generate realistic portrait"""
        
        # Build portrait-specific prompt
        prompt = (
            f"photorealistic portrait of {subject_description}, "
            f"{lighting}, professional photography, "
            f"shot with {camera} lens, sharp focus, "
            f"detailed skin texture, realistic eyes, "
            f"beautiful lighting, high detail, 4k"
        )
        
        # Add portrait-specific negatives
        portrait_negative = (
            self.NEGATIVE_PROMPT + ", " +
            "cartoon, illustration, painting, watermark, signature"
        )
        
        return self.generate(
            prompt,
            negative_prompt=portrait_negative,
            **kwargs
        )
    
    def generate_landscape(
        self,
        scene_description,
        time_of_day="golden hour",
        weather="clear",
        **kwargs
    ):
        """Generate realistic landscape"""
        
        # Build landscape-specific prompt
        prompt = (
            f"photorealistic landscape of {scene_description}, "
            f"{time_of_day}, {weather}, "
            f"professional nature photography, "
            f"high detail, sharp, 8k resolution"
        )
        
        return self.generate(
            prompt,
            negative_prompt=self.NEGATIVE_PROMPT,
            **kwargs
        )
    
    def generate_product(
        self,
        product_name,
        product_type,
        background="white",
        lighting="studio lighting",
        **kwargs
    ):
        """Generate product photography"""
        
        prompt = (
            f"professional product photography of {product_name}, "
            f"{product_type}, {background} background, "
            f"{lighting}, commercial photography, "
            f"sharp focus, detailed, high resolution, "
            f"ecommerce, clean, professional"
        )
        
        product_negative = (
            self.NEGATIVE_PROMPT + ", "
            "shadow, reflection, glare"
        )
        
        return self.generate(
            prompt,
            negative_prompt=product_negative,
            **kwargs
        )
    
    def generate_variations(
        self,
        prompt,
        num_variations=4,
        **kwargs
    ):
        """Generate multiple variations"""
        
        images = []
        for i in range(num_variations):
            # Use different seed for each
            kwargs['seed'] = kwargs.get('seed', 42) + i
            img = self.generate(prompt, **kwargs)
            images.append(img)
        
        return images
    
    def save_image(self, image, output_path, quality=95):
        """Save image with quality settings"""
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save as PNG for quality or JPEG for size
        if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
            image.save(output_path, 'JPEG', quality=quality)
        else:
            image.save(output_path, 'PNG')
        
        print(f"Image saved to: {output_path}")


def main():
    # Initialize generator
    generator = RealisticVisionGenerator()
    
    # Load model
    generator.load_model(use_vae=True)
    
    # Create output directory
    os.makedirs("./output/realistic_vision", exist_ok=True)
    
    # Example 1: Portrait
    print("\n=== Generating Portrait ===")
    portrait = generator.generate_portrait(
        "young woman, 25 years old, friendly smile",
        lighting="soft natural daylight",
        seed=42
    )
    generator.save_image(portrait, "./output/realistic_vision/portrait_01.png")
    
    # Example 2: Landscape
    print("\n=== Generating Landscape ===")
    landscape = generator.generate_landscape(
        "mountain range with lake",
        time_of_day="golden hour",
        weather="clear sky",
        seed=43
    )
    generator.save_image(landscape, "./output/realistic_vision/landscape_01.png")
    
    # Example 3: Product
    print("\n=== Generating Product ===")
    product = generator.generate_product(
        "perfume bottle",
        "luxury cosmetic",
        background="soft gray",
        lighting="professional studio lighting",
        seed=44
    )
    generator.save_image(product, "./output/realistic_vision/product_01.png")
    
    print("\nAll generations complete!")


if __name__ == "__main__":
    main()
```

### Using with Interactive Prompt Generator

```python
# Integrate with the professional prompt system
from interactive_prompt import PromptGenerator

# Create photorealistic prompts
prompt_gen = PromptGenerator()

# Configure for photorealism
prompt_gen.set_main_subject("professional portrait of a person")
prompt_gen.set_environment("Studio lighting")
prompt_gen.set_color_palette("Natural")
prompt_gen.set_lighting("Golden hour")
prompt_gen.set_composition("Rule of thirds")
prompt_gen.set_depth_of_field("Shallow")
prompt_gen.set_mood("Peaceful")
prompt_gen.set_time_weather("Daytime")
prompt_gen.set_human_emotion("Serenity")
prompt_gen.set_camera("85mm portrait lens")
prompt_gen.set_camera_angle("Eye-level")

full_prompt = prompt_gen.generate_prompt() + ", photorealistic, realistic, photograph, photo realistic"

# Generate
generator = RealisticVisionGenerator()
generator.load_model()
image = generator.generate(full_prompt)
```

## Photorealistic Prompt Engineering

### Essential Prompt Elements

```python
class PhotorealisticPromptBuilder:
    """Build prompts specifically for photorealistic output"""
    
    # Photography-specific quality terms
    QUALITY_TERMS = [
        "photorealistic", "realistic", "photo realistic",
        "high resolution", "4k", "8k", "ultra detailed",
        "sharp focus", "professional photography",
        "detailed texture", "accurate colors"
    ]
    
    # Lighting terms for realism
    LIGHTING_TERMS = [
        "natural lighting", "soft lighting", "golden hour",
        "blue hour", "studio lighting", "key light",
        "rim lighting", "fill light", "ambient occlusion"
    ]
    
    # Camera terms
    CAMERA_TERMS = [
        "DSLR", "mirrorless camera", "full frame sensor",
        "85mm lens", "50mm lens", "35mm lens",
        "f/1.8", "f/2.8", "shallow depth of field"
    ]
    
    # Negative prompts for realism
    NEGATIVE_PRESET = (
        "cartoon, illustration, painting, drawing, art, "
        "anime, manga, comic, 3d render, cgi, digital art, "
        "deformed, ugly, bad anatomy, extra fingers, watermark"
    )
    
    @classmethod
    def build_portrait_prompt(
        cls,
        subject,
        age=None,
        gender="unspecified",
        expression="natural",
        lighting="natural",
        camera="85mm",
        background="gradient"
    ):
        """Build portrait-specific prompt"""
        
        parts = [
            f"photorealistic portrait of {gender} {subject}",
        ]
        
        if age:
            parts.append(f"{age} years old")
        
        parts.extend([
            f"with {expression} expression",
            f"professional photography",
            f"{lighting}",
            f"shot with {camera} lens",
            f"sharp focus on eyes",
            f"detailed skin texture",
            f"{background} background",
            "high detail",
            "realistic"
        ])
        
        return ", ".join(parts)
    
    @classmethod
    def build_landscape_prompt(
        cls,
        location,
        time_of_day="golden hour",
        weather="clear",
        season="spring"
    ):
        """Build landscape-specific prompt"""
        
        return (
            f"photorealistic landscape of {location}, "
            f"{time_of_day}, {weather}, {season}, "
            "professional nature photography, "
            "high resolution, sharp, detailed, 8k"
        )
    
    @classmethod
    def build_interior_prompt(
        cls,
        room_type,
        style="modern",
        lighting="natural",
        materials="realistic"
    ):
        """Build interior design prompt"""
        
        return (
            f"photorealistic interior design of {room_type}, "
            f"{style} style, {lighting}, "
            f"{materials} materials, "
            "architectural photography, "
            "wide angle lens, sharp, detailed"
        )
    
    @classmethod
    def build_product_prompt(
        cls,
        product,
        category,
        lighting="studio",
        background="white"
    ):
        """Build product photography prompt"""
        
        return (
            f"professional product photography of {product}, "
            f"{category}, {background} background, "
            f"{lighting}, commercial photography, "
            "sharp focus, detailed, high resolution"
        )


# Usage examples
portrait_prompt = PhotorealisticPromptBuilder.build_portrait_prompt(
    subject="woman",
    age="30",
    expression="friendly smile",
    lighting="soft natural daylight",
    camera="85mm"
)
# Result: "photorealistic portrait of unspecified gender woman, 30 years old, 
# with friendly expression, professional photography, soft natural daylight, 
# shot with 85mm lens, sharp focus on eyes, detailed skin texture, 
# gradient background, high detail, realistic"

landscape_prompt = PhotorealisticPromptBuilder.build_landscape_prompt(
    location="beach at sunset",
    time_of_day="golden hour",
    weather="clear sky"
)
```

### Parameter Reference

| Parameter | Recommended Value | Effect |
|-----------|-----------------|--------|
| Guidance Scale | 6.0 - 8.0 | Higher = more prompt adherence |
| Inference Steps | 25-40 | Higher = smoother, slower |
| Resolution | 512x512 or 768x768 | Higher = more detail, slower |
| Seed | Random or fixed | Fixed = reproducible |

## Advanced Features

### 1. Using Realism LoRAs

```python
class LoRAEnhancedGenerator:
    """Add realism LoRAs for enhanced photorealism"""
    
    def __init__(self, base_model):
        self.base_model = base_model
        self.pipeline = None
        
    def load_with_realism_lora(self, lora_path, scale=0.8):
        """Load base model with realism LoRA"""
        
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.base_model,
            torch_dtype=torch.float16,
        )
        
        # Load realism LoRA
        self.pipeline.load_lora_weights(lora_path)
        self.pipeline.set_adapters([lora_path], scales=[scale])
        
        # Enable optimizations
        self.pipeline.enable_attention_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
        
        return self.pipeline


# Popular realism LoRAs to use:
# - "https://civitai.com/api/download/models/RealisticVision" (VAE)
# - "photorealism" LoRAs from CivitAI
```

### 2. Multiple Prompt Weighting

```python
def weighted_prompt(base_subject, *modifiers, weights=None):
    """Create weighted prompts for detail control"""
    
    if weights is None:
        weights = [1.0] * len(modifiers)
    
    prompt_parts = [base_subject]
    for modifier, weight in zip(modifiers, weights):
        if weight > 1.0:
            prompt_parts.append(f"({modifier}:{weight})")
        else:
            prompt_parts.append(modifier)
    
    return ", ".join(prompt_parts)


# Example
prompt = weighted_prompt(
    "woman portrait",
    "detailed skin", "realistic eyes", "natural hair",
    weights=[1.2, 1.3, 1.1]
)
```

### 3. Image-to-Image for Realism

```python
class RealisticImg2Img:
    """Transform images with photorealistic model"""
    
    def __init__(self, model_id="SG161222/Realistic_Vision_V5.1_noVAE"):
        from diffusers import StableDiffusionImg2ImgPipeline
        
        self.pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        self.pipeline.enable_attention_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
    
    def enhance_realism(
        self,
        input_image,
        prompt,
        strength=0.5,
        num_steps=30
    ):
        """Enhance image realism"""
        
        # Resize
        input_image = input_image.resize((512, 512))
        
        negative = (
            "artistic, painting, cartoon, anime, 3d render, "
            "deformed, ugly, bad anatomy"
        )
        
        result = self.pipeline(
            prompt=prompt,
            image=input_image,
            strength=strength,
            num_inference_steps=num_steps,
            guidance_scale=7.0,
            negative_prompt=negative,
        )
        
        return result.images[0]
```

## Quality Optimization

### Settings for Best Quality

```python
# Optimal settings for photorealistic generation
QUALITY_SETTINGS = {
    # Higher steps = better quality (slower)
    "num_inference_steps": 35,
    
    # Moderate guidance
    "guidance_scale": 7.0,
    
    # Resolution (higher = more memory)
    "height": 512,
    "width": 512,
    
    # Sampler choice
    "scheduler": "DPM++ 2M Karras",
}

def apply_quality_settings(pipeline, settings=QUALITY_SETTINGS):
    """Configure pipeline for quality"""
    
    # Apply Karras scheduler
    pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
        pipeline.scheduler.config,
        algorithm_type="dpmsolver++",
        use_karras_sigmas=True,
    )
    
    return pipeline
```

### Speed vs Quality Tradeoff

| Steps | Time (approx) | Quality | Use Case |
|-------|---------------|---------|----------|
| 15 | ~20s | Draft | Quick preview |
| 25 | ~35s | Good | Standard use |
| 35 | ~50s | Excellent | Final output |
| 50 | ~70s | Maximum | Print quality |

## Troubleshooting

### Common Issues

#### 1. Not Photorealistic Enough

```python
# Increase quality terms in prompt
prompt = "photorealistic, realistic, photo realistic, " + prompt

# Use negative prompt
negative = "cartoon, painting, illustration, 3d render, digital art"

# Increase guidance scale
guidance_scale=8.0

# Increase steps
num_inference_steps=40
```

#### 2. Artifacts and Glitches

```python
# Add to negative prompt
negative = "deformed, ugly, bad anatomy, extra limbs, " + negative

# Reduce guidance scale
guidance_scale=6.0

# Use VAE
vae = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse")
```

#### 3. Memory Issues

```python
# Enable memory optimizations
pipeline.enable_attention_slicing()
pipeline.enable_vae_slicing()
pipeline.enable_model_cpu_offload()

# Reduce resolution
height=384
width=384
```

#### 4. Slow Generation

```bash
# Check Jetson performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Monitor
tegrastats
```

### Performance Monitoring

```python
import time
import torch

class RealismPerformanceMonitor:
    """Track generation performance"""
    
    def __init__(self):
        self.history = []
        
    def measure_generation(self, pipeline, prompt, **kwargs):
        """Measure generation time and memory"""
        
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        
        start = time.time()
        result = pipeline(prompt, **kwargs)
        elapsed = time.time() - start
        
        memory_used = 0
        if torch.cuda.is_available():
            memory_used = torch.cuda.max_memory_allocated() / 1024**2
        
        self.history.append({
            "time": elapsed,
            "memory_mb": memory_used,
            "prompt": prompt[:50],
        })
        
        return result.images[0], elapsed, memory_used
```

## Next Steps

- Explore [Portrait Generation](./10-portrait-generation.md) for specialized face generation
- Learn about [Upscaling](./12-upscaling.md) for enhancing generated images
- Check [Batch Processing](./13-batch-processing.md) for bulk generation

## Additional Resources

- [Realistic Vision Model](https://huggingface.co/SG161222/Realistic_Vision_V5.1_noVAE)
- [VAE Models](https://huggingface.co/stabilityai/sd-vae)
- [Photography Prompt Guide](https://prompthero.com/)
- [CivitAI Realism LoRAs](https://civitai.com/)
