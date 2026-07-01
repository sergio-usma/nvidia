# Image-to-Image Generation on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Image-to-Image](#understanding-image-to-image)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Advanced Transformations](#advanced-transformations)
8. [Creative Applications](#creative-applications)
9. [Quality Control](#quality-control)
10. [Troubleshooting](#troubleshooting)

## Introduction

Image-to-Image (Img2Img) generation is a powerful technique that transforms an existing image according to a text prompt while preserving certain aspects of the original. This guide covers deploying img2img capabilities on your Jetson AGX Orin 64GB, enabling you to:

- Transform sketches into detailed artwork
- Apply artistic styles to photographs
- Enhance and modify existing images
- Create variations of existing images
- Convert between different visual styles

### How Image-to-Image Works

Img2Img uses a process called "diffusion" where:
1. The input image is encoded into latent space
2. Noise is gradually added while being conditioned on the prompt
3. The denoising process transforms the image according to the text guidance

The **strength** parameter controls how much the output differs from the input:
- 0.0 = No change (ignores prompt)
- 0.5 = Balanced transformation
- 1.0 = Complete transformation (ignores input)

## Prerequisites

### System Requirements

```bash
# Enable maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify GPU availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### Python Dependencies

```bash
# Core dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Diffusers and related
pip install diffusers transformers accelerate safetensors

# Image processing
pip install pillow numpy opencv-python scipy
```

## Installation

### Basic Installation

```bash
pip install diffusers transformers accelerate
```

### Recommended Models for Jetson

| Model | Quality | Speed | VRAM | Best For |
|-------|---------|-------|------|----------|
| SD 1.5 | Good | Fast | 4GB | General img2img |
| SD-Turbo | Good | Very Fast | 4GB | Quick iterations |
| SD 2.1 | Better | Medium | 6GB | Higher quality |
| Realistic Vision | Best for photos | Medium | 5GB | Photorealistic |

## Configuration

### Basic Configuration

```python
# Configuration for img2img on Jetson
IMG2IMG_CONFIG = {
    "default_model": "stabilityai/stable-diffusion-2-1-base",
    "optimized_model": "stabilityai/sd-turbo",
    
    # Default generation settings
    "default_steps": 30,
    "default_guidance": 7.5,
    "default_strength": 0.5,
    
    # Resolution limits for Jetson
    "max_width": 768,
    "max_height": 768,
    "default_size": 512,
    
    # Optimization settings
    "enable_attention_slicing": True,
    "enable_vae_slicing": True,
    "use_fp16": True,
}
```

## Basic Usage

### Basic Image Transformation

```python
#!/usr/bin/env python3
"""
Image-to-Image Generation on Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os
import time
import numpy as np

class ImageToImageGenerator:
    """Image-to-Image generation on Jetson"""
    
    def __init__(self, model_id="stabilityai/stable-diffusion-2-1-base"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self):
        """Load the img2img pipeline with optimizations"""
        
        print(f"Loading model: {self.model_id}")
        
        self.pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        # Enable memory optimizations
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        # Move to GPU
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
            print("Model loaded on CUDA")
        
        print("Model loaded successfully!")
        return self.pipeline
    
    def load_image(self, image_path):
        """Load and preprocess input image"""
        
        image = Image.open(image_path)
        
        # Convert to RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
    
    def preprocess_image(self, image, size=512):
        """Resize and prepare image for processing"""
        
        # Resize to square
        image = image.resize((size, size), Image.Resampling.LANCZOS)
        
        return image
    
    def transform(
        self,
        input_image,
        prompt,
        negative_prompt=None,
        strength=0.5,
        num_inference_steps=30,
        guidance_scale=7.5,
        seed=None
    ):
        """Transform image based on prompt"""
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded")
        
        # Set negative prompt
        if negative_prompt is None:
            negative_prompt = (
                "blurry, low quality, distorted, ugly, "
                "deformed, bad anatomy, extra limbs"
            )
        
        # Set seed
        generator = None
        if seed is not None:
            generator = torch.Generator(
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
            generator.manual_seed(seed)
        
        # Preprocess image
        input_image = self.preprocess_image(input_image)
        
        # Generate
        start_time = time.time()
        
        with torch.inference_mode():
            result = self.pipeline(
                prompt=prompt,
                image=input_image,
                negative_prompt=negative_prompt,
                strength=strength,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
        
        elapsed = time.time() - start_time
        print(f"Transformation completed in {elapsed:.2f}s")
        
        return result.images[0]
    
    def sketch_to_image(self, sketch_path, target_style, **kwargs):
        """Convert sketch to detailed image"""
        
        # Load sketch
        sketch = self.load_image(sketch_path)
        sketch = self.preprocess_image(sketch)
        
        # Build prompt for sketch-to-image
        prompt = f"detailed {target_style} illustration, sketch, clean lines, high quality"
        
        # Higher strength for complete transformation
        return self.transform(sketch, prompt, strength=0.7, **kwargs)
    
    def style_transfer(self, image_path, style, strength=0.5, **kwargs):
        """Apply artistic style to image"""
        
        image = self.load_image(image_path)
        image = self.preprocess_image(image)
        
        # Style prompts
        style_prompts = {
            "anime": "anime style, manga, vibrant colors, clean lines, cel shading",
            "oil_painting": "oil painting, brush strokes, classic art style, impasto",
            "watercolor": "watercolor painting, soft colors, flowing, artistic",
            "photorealistic": "photorealistic, realistic, high detail, photograph",
            "impressionist": "impressionist painting, loose brushwork, light and color",
            "cyberpunk": "cyberpunk, neon lights, futuristic, digital art",
            "fantasy": "fantasy art, magical, detailed, epic, fantasy illustration",
            "vintage": "vintage photograph, retro, nostalgic, film grain",
        }
        
        prompt = style_prompts.get(style, style_prompts["photorealistic"])
        
        return self.transform(image, prompt, strength=strength, **kwargs)
    
    def create_variation(self, image_path, seed=None, **kwargs):
        """Create variation of existing image"""
        
        image = self.load_image(image_path)
        image = self.preprocess_image(image)
        
        # Low strength for subtle variations
        prompt = "high quality, detailed, professional"
        
        return self.transform(
            image, 
            prompt, 
            strength=0.3, 
            seed=seed,
            **kwargs
        )


def main():
    """Demo of img2img capabilities"""
    
    # Initialize
    generator = ImageToImageGenerator("stabilityai/stable-diffusion-2-1-base")
    generator.load_model()
    
    # Create output directory
    os.makedirs("./output/img2img", exist_ok=True)
    
    # Example: Style transfer
    # Note: You'll need to provide your own input image
    sample_image_path = "./input/sample.jpg"
    
    if os.path.exists(sample_image_path):
        print("\n=== Style Transfer ===")
        
        # Apply different styles
        styles = ["anime", "oil_painting", "watercolor", "cyberpunk"]
        
        for style in styles:
            print(f"Applying {style} style...")
            
            result = generator.style_transfer(
                sample_image_path,
                style=style,
                strength=0.6,
                seed=42
            )
            
            result.save(f"./output/img2img/style_{style}.png")
            print(f"Saved: style_{style}.png")
    else:
        print(f"\nNote: Sample image not found at {sample_image_path}")
        print("Create an input folder with images to test img2img")


if __name__ == "__main__":
    main()
```

### Quick Transformation Script

```python
# Simple img2img transformation
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import torch

# Load pipeline
pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
    "stabilityai/stable-diffusion-2-1-base",
    torch_dtype=torch.float16,
)
pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda" if torch.cuda.is_available() else "cpu")

# Load and prepare image
image = Image.open("input.jpg").resize((512, 512))

# Transform
result = pipeline(
    prompt="make it an anime style, vibrant colors",
    image=image,
    strength=0.6,  # How much to transform (0-1)
    num_inference_steps=25,
    guidance_scale=7.5,
)

result.images[0].save("output.png")
```

## Advanced Transformations

### 1. Progressive Transformation

```python
class ProgressiveImg2Img:
    """Progressive image transformation with multiple passes"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def transform_progressive(
        self,
        image,
        prompt,
        stages=3,
        start_strength=0.3,
        end_strength=0.7
    ):
        """Apply transformation in progressive stages"""
        
        current_image = image.copy()
        
        for stage in range(stages):
            # Calculate strength for this stage
            strength = start_strength + (end_strength - start_strength) * (stage / (stages - 1))
            
            print(f"Stage {stage + 1}/{stages}, strength: {strength:.2f}")
            
            # Apply transformation
            result = self.pipeline(
                prompt=prompt,
                image=current_image,
                strength=strength,
                num_inference_steps=20,
                guidance_scale=7.5,
            )
            
            current_image = result.images[0]
        
        return current_image
```

### 2. Masked Transformation

```python
class MaskedImg2Img:
    """Transform specific areas of an image using masks"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def transform_masked(
        self,
        image,
        mask_image,
        prompt,
        strength=0.6,
        **kwargs
    ):
        """Transform only the masked area"""
        
        # Ensure mask is grayscale
        if mask_image.mode != 'L':
            mask_image = mask_image.convert('L')
        
        # Resize to match
        mask_image = mask_image.resize(image.size)
        
        result = self.pipeline(
            prompt=prompt,
            image=image,
            mask_image=mask_image,
            strength=strength,
            **kwargs
        )
        
        return result.images[0]
    
    def create_mask_from_color(self, image, target_color, tolerance=30):
        """Create mask based on color"""
        
        import numpy as np
        
        # Convert to numpy
        img_array = np.array(image)
        
        # Create mask based on color similarity
        if len(img_array.shape) == 3:
            # Calculate distance from target color
            color_diff = np.abs(img_array[:, :, :3] - target_color)
            mask = np.any(color_diff > tolerance, axis=-1)
            
            # Invert if needed
            mask = ~mask
            
            return Image.fromarray((mask * 255).astype(np.uint8))
        
        return None
```

### 3. Multi-Style Blending

```python
class StyleBlender:
    """Blend multiple styles together"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def blend_styles(
        self,
        image,
        styles_weights,
        num_inference_steps=30
    ):
        """
        Blend multiple styles
        
        styles_weights: dict of {style_name: weight}
        """
        
        # Build blended prompt
        prompt_parts = []
        for style, weight in styles_weights.items():
            style_prompts = {
                "anime": "anime style",
                "oil": "oil painting",
                "watercolor": "watercolor",
                "cyberpunk": "cyberpunk neon",
                "realistic": "photorealistic",
            }
            
            if style in style_prompts:
                prompt_parts.append(f"({style_prompts[style]}:{weight})")
        
        prompt = ", ".join(prompt_parts) if prompt_parts else "high quality"
        
        # Use intermediate strength for blending
        result = self.pipeline(
            prompt=prompt,
            image=image,
            strength=0.5,
            num_inference_steps=num_inference_steps,
            guidance_scale=7.5,
        )
        
        return result.images[0]
```

### 4. Resolution-Adaptive Processing

```python
class ResolutionAdaptiveImg2Img:
    """Process images at optimal resolution for quality/speed"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def process_at_resolution(
        self,
        image,
        prompt,
        target_resolution,
        strength=0.5,
        num_steps=25
    ):
        """Process at specified resolution"""
        
        # Resize to target
        original_size = image.size
        image = image.resize(target_resolution, Image.Resampling.LANCZOS)
        
        # Process
        result = self.pipeline(
            prompt=prompt,
            image=image,
            strength=strength,
            num_inference_steps=num_steps,
        )
        
        # Resize back
        result_image = result.images[0].resize(original_size)
        
        return result_image
    
    def multi_scale_process(
        self,
        image,
        prompt,
        scales=[0.5, 0.75, 1.0],
        strength=0.5
        ):
        """Process at multiple scales and blend"""
        
        from PIL import ImageDraw
        
        results = []
        
        for scale in scales:
            # Calculate scaled size
            w, h = int(image.width * scale), int(image.height * scale)
            
            # Process at this scale
            result = self.process_at_resolution(
                image,
                prompt,
                (w, h),
                strength=strength,
            )
            
            # Resize back to original
            result = result.resize(image.size)
            results.append(np.array(result))
        
        # Average results (simple blending)
        blended = np.mean(results, axis=0).astype(np.uint8)
        
        return Image.fromarray(blended)
```

## Creative Applications

### 1. Sketch to Art

```python
class SketchToArt:
    """Convert sketches to detailed artwork"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def convert_sketch(
        self,
        sketch_path,
        target_style="detailed digital art",
        line_weight=0.8
    ):
        """Convert sketch to detailed artwork"""
        
        # Load sketch
        sketch = Image.open(sketch_path).resize((512, 512))
        
        # Enhance lines
        if line_weight < 1.0:
            sketch = self._enhance_lines(sketch, line_weight)
        
        # Build prompt
        prompt = (
            f"detailed {target_style}, clean lines, "
            "professional illustration, high quality"
        )
        
        # Transform with high strength
        result = self.pipeline(
            prompt=prompt,
            image=sketch,
            strength=0.75,
            num_inference_steps=35,
            guidance_scale=8.0,
        )
        
        return result.images[0]
    
    def _enhance_lines(self, image, weight):
        """Enhance sketch lines"""
        # Simple line enhancement
        from PIL import ImageEnhance
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
        return image
```

### 2. Photo Enhancement

```python
class PhotoEnhancer:
    """Enhance and improve photographs"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def enhance_photo(
        self,
        photo_path,
        enhancement_type="detail"
    ):
        """Enhance photograph"""
        
        photo = Image.open(photo_path).resize((512, 512))
        
        prompts = {
            "detail": "enhance details, sharp, detailed, professional photography",
            "color": "vibrant colors, rich colors, saturated, beautiful color grading",
            "light": "beautiful lighting, cinematic, dramatic lighting, professional",
            "mood": "moody, atmospheric, emotional, cinematic",
            "portrait": "beautiful portrait, professional headshot, detailed skin",
        }
        
        prompt = prompts.get(enhancement_type, prompts["detail"])
        
        # Low strength for subtle enhancement
        result = self.pipeline(
            prompt=prompt,
            image=photo,
            strength=0.3,
            num_inference_steps=25,
            guidance_scale=7.0,
            negative_prompt="blurry, low quality, distorted, ugly",
        )
        
        return result.images[0]
    
    def restore_old_photo(self, photo_path):
        """Restore and enhance old photos"""
        
        photo = Image.open(photo_path).resize((512, 512))
        
        # Restoration prompt
        prompt = (
            "restored photo, high resolution, detailed, "
            "clean, professional restoration, vintage photo enhanced"
        )
        
        negative = (
            "damaged, torn, scratched, old, faded, "
            "blurry, low quality, distorted"
        )
        
        result = self.pipeline(
            prompt=prompt,
            image=photo,
            strength=0.5,
            num_inference_steps=30,
            guidance_scale=7.5,
            negative_prompt=negative,
        )
        
        return result.images[0]
```

### 3. Concept Art Generation

```python
class ConceptArtGenerator:
    """Generate concept art from rough ideas"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate_concept(
        self,
        base_image_path,
        concept_description,
        style="sci-fi concept art"
    ):
        """Generate concept art from base"""
        
        base = Image.open(base_image_path).resize((512, 512))
        
        prompt = f"{concept_description}, {style}, professional concept art, detailed"
        
        result = self.pipeline(
            prompt=prompt,
            image=base,
            strength=0.6,
            num_inference_steps=35,
            guidance_scale=7.5,
        )
        
        return result.images[0]
```

## Quality Control

### Strength vs Quality Guide

| Strength | Effect | Best For |
|----------|--------|----------|
| 0.1-0.2 | Very subtle | Light enhancement |
| 0.3-0.4 | Subtle changes | Variations |
| 0.5-0.6 | Balanced | Style transfer |
| 0.7-0.8 | Major changes | Art style conversion |
| 0.9-1.0 | Complete change | New creation from sketch |

### Best Practices

```python
# Optimal settings for different use cases
SETTINGS = {
    # Sketch to art
    "sketch_to_art": {
        "strength": 0.7,
        "steps": 35,
        "guidance": 8.0,
    },
    
    # Photo enhancement  
    "photo_enhance": {
        "strength": 0.3,
        "steps": 25,
        "guidance": 7.0,
    },
    
    # Style transfer
    "style_transfer": {
        "strength": 0.5,
        "steps": 30,
        "guidance": 7.5,
    },
    
    # Variation
    "variation": {
        "strength": 0.25,
        "steps": 20,
        "guidance": 6.0,
    },
}
```

### Resolution Guidelines

| Input Size | Output Size | Use Case |
|------------|-------------|----------|
| 256x256 | 256x256 | Quick preview |
| 512x512 | 512x512 | Standard use |
| 512x512 | 768x768 | High quality |
| 512x512 | 1024x1024 | Maximum detail |

## Troubleshooting

### Common Issues

#### 1. Output Too Different from Input

```python
# Solution: Reduce strength
result = pipeline(
    prompt=prompt,
    image=image,
    strength=0.3,  # Lower strength
)
```

#### 2. Output Looks Garbled

```python
# Solution: Increase steps and guidance
result = pipeline(
    prompt=prompt,
    image=image,
    strength=0.5,
    num_inference_steps=40,  # More steps
    guidance_scale=8.0,     # Higher guidance
)
```

#### 3. Out of Memory

```python
# Solution: Enable memory optimizations
pipeline.enable_sequential_cpu_offload()

# Or reduce resolution
image = image.resize((384, 384))
```

#### 4. Style Not Applied

```python
# Solution: Increase strength and add style to negative prompt
result = pipeline(
    prompt=f"{prompt}, {style}",
    image=image,
    strength=0.7,
    negative_prompt="realistic, photo, " + negative_prompt,
)
```

### Performance Tips

```bash
# Monitor GPU usage
tegrastats

# Check memory
python -c "import torch; print(torch.cuda.max_memory_allocated() / 1024**3, 'GB')"
```

## Next Steps

- Explore [Inpainting & Outpainting](./08-inpainting-outpainting.md) for targeted edits
- Learn about [ControlNet](./09-controlnet.md) for controlled transformations
- Check [Batch Processing](./13-batch-processing.md) for bulk img2img

## Additional Resources

- [HuggingFace Img2Img Guide](https://huggingface.co/docs/diffusers/api/pipelines/img2img)
- [Stable Diffusion Img2Img Tips](https://stable-diffusion-art.com/img2img/)
