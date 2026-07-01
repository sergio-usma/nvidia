# Style Transfer on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Style Transfer](#understanding-style-transfer)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Artistic Styles](#artistic-styles)
8. [Advanced Techniques](#advanced-techniques)
9. [Practical Applications](#practical-applications)
10. [Troubleshooting](#troubleshooting)

## Introduction

Style transfer transforms images using artistic styles, combining the content of one image with the visual appearance of another. This guide covers deploying style transfer on your Jetson AGX Orin 64GB, enabling:

- Artistic rendering of photos
- Style application from reference images
- Custom artistic effects
- Creative transformations

### Types of Style Transfer

| Method | Description | Best For |
|--------|-------------|----------|
| Img2Img | AI-based style transfer | General use |
| Neural Style | Perceptual loss-based | Artistic effects |
| LoRA | Lightweight style adapters | Specific styles |
| ControlNet | Controlled style application | Precise control |

## Understanding Style Transfer

### How It Works

1. **Content Preservation**: Maintains original image structure
2. **Style Extraction**: Captures artistic characteristics
3. **Blending**: Combines content + style
4. **Output**: Stylized image

### Jetson Considerations

- Img2Img is most feasible for Jetson
- LoRA provides lightweight style options
- Neural Style requires more memory

## Prerequisites

### System Setup

```bash
sudo nvpmodel -m 0
sudo jetson_clocks

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install diffusers transformers accelerate safetensors
pip install pillow numpy opencv-python
```

## Installation

### Basic Installation

```bash
pip install diffusers transformers accelerate
```

### Install Style LoRAs

```python
# Style LoRAs can be downloaded from CivitAI
# Popular styles: anime, painterly, comic, etc.
```

## Configuration

### Style Transfer Config

```python
STYLE_TRANSFER_CONFIG = {
    "base_model": "stabilityai/stable-diffusion-1-5",
    "img2img_model": "stabilityai/stable-diffusion-1-5",
    
    "default_settings": {
        "strength": 0.5,
        "steps": 30,
        "guidance": 7.5,
    },
    
    "optimization": {
        "attention_slicing": True,
        "vae_slicing": True,
    }
}
```

## Basic Usage

### Style Transfer Implementation

```python
#!/usr/bin/env python3
"""
Style Transfer on Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os
import time

class StyleTransfer:
    """Style transfer on Jetson"""
    
    # Comprehensive style definitions
    STYLES = {
        "anime": {
            "prompt": "anime style, manga, vibrant colors, clean lines, cel shading, anime art",
            "negative": "realistic, photo, photorealistic, 3d render, blurry, low quality"
        },
        "oil_painting": {
            "prompt": "oil painting, brush strokes, classic art, impasto, traditional painting",
            "negative": "anime, cartoon, digital art, photo, blurry"
        },
        "watercolor": {
            "prompt": "watercolor painting, soft colors, flowing, artistic, watercolor effect",
            "negative": "sharp lines, digital, photo, blurry"
        },
        "impressionist": {
            "prompt": "impressionist painting, loose brushwork, light and color, Monet style",
            "negative": "detailed, realistic, photo, sharp"
        },
        "photorealistic": {
            "prompt": "photorealistic, realistic, high detail, professional photograph",
            "negative": "artistic, painting, illustration, cartoon, anime"
        },
        "cyberpunk": {
            "prompt": "cyberpunk, neon lights, futuristic, digital art, synthwave",
            "negative": "natural, vintage, traditional, blurry"
        },
        "fantasy": {
            "prompt": "fantasy art, magical, epic, detailed fantasy illustration, concept art",
            "negative": "realistic, photo, modern, mundane"
        },
        "vintage": {
            "prompt": "vintage photograph, retro, nostalgic, film grain, old photo style",
            "negative": "modern, digital, high tech, sharp"
        },
        "comic": {
            "prompt": "comic book art, vibrant, bold outlines, Marvel style, comic illustration",
            "negative": "photorealistic, realistic, blurry, low quality"
        },
        "pixar": {
            "prompt": "Pixar style, 3D animation, CGI character, Disney, cute",
            "negative": "2D, anime, realistic photo, blurry"
        },
        "steampunk": {
            "prompt": "steampunk, Victorian, brass gears, retro-futuristic, vintage sci-fi",
            "negative": "modern, sleek, digital, natural"
        },
        "noir": {
            "prompt": "film noir, black and white, dramatic lighting, 1940s, detective",
            "negative": "color, modern, bright, cheerful"
        },
        "watercolor": {
            "prompt": "watercolor, soft pastel colors, artistic, flowing paint",
            "negative": "sharp, digital, photo, realistic"
        },
        "gothic": {
            "prompt": "gothic art, dark, dramatic, medieval, eerie",
            "negative": "bright, happy, modern, cheerful"
        },
        "art_deco": {
            "prompt": "Art Deco, geometric patterns, elegant, 1920s, decorative",
            "negative": "random, messy, modern, organic"
        },
    }
    
    def __init__(self, model_id="stabilityai/stable-diffusion-1-5"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self):
        """Load style transfer model"""
        
        print(f"Loading model: {self.model_id}")
        
        self.pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
            print("Model loaded on CUDA")
        
        print("Style transfer model loaded!")
        return self.pipeline
    
    def load_image(self, image_path):
        """Load and prepare image"""
        
        image = Image.open(image_path).convert("RGB")
        return image.resize((512, 512), Image.Resampling.LANCZOS)
    
    def apply_style(
        self,
        image_path,
        style,
        strength=0.5,
        num_inference_steps=30,
        guidance_scale=7.5,
        seed=None
    ):
        """Apply style to image"""
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded")
        
        # Get style prompts
        style_info = self.STYLES.get(style, self.STYLES["photorealistic"])
        
        # Load image
        image = self.load_image(image_path)
        
        # Set seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator.manual_seed(seed)
        
        # Generate
        start_time = time.time()
        
        with torch.inference_mode():
            result = self.pipeline(
                prompt=style_info["prompt"],
                image=image,
                negative_prompt=style_info["negative"],
                strength=strength,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
        
        elapsed = time.time() - start_time
        print(f"Style transfer completed in {elapsed:.2f}s")
        
        return result.images[0]
    
    def apply_custom_style(
        self,
        image_path,
        style_prompt,
        negative_prompt="",
        strength=0.5,
        **kwargs
    ):
        """Apply custom style prompt"""
        
        # Load image
        image = self.load_image(image_path)
        
        # Use default negatives if not provided
        if not negative_prompt:
            negative_prompt = "blurry, low quality, distorted, ugly, deformed"
        
        result = self.pipeline(
            prompt=style_prompt,
            image=image,
            negative_prompt=negative_prompt,
            strength=strength,
            **kwargs
        ).images[0]
        
        return result
    
    def blend_styles(
        self,
        image_path,
        styles_weights,
        strength=0.5,
        **kwargs
    ):
        """Blend multiple styles"""
        
        # Build blended prompt
        prompt_parts = []
        for style, weight in styles_weights.items():
            if style in self.STYLES:
                style_prompt = self.STYLES[style]["prompt"]
                if weight != 1.0:
                    prompt_parts.append(f"({style_prompt}:{weight})")
                else:
                    prompt_parts.append(style_prompt)
        
        prompt = ", ".join(prompt_parts)
        
        return self.apply_custom_style(
            image_path,
            prompt,
            strength=strength,
            **kwargs
        )


def main():
    """Demo of style transfer"""
    
    # Initialize
    transfer = StyleTransfer()
    transfer.load_model()
    
    # Create output directory
    os.makedirs("./output/style_transfer", exist_ok=True)
    
    # Available styles
    styles = ["anime", "oil_painting", "watercolor", "cyberpunk", "fantasy"]
    
    # Example: Apply styles (requires input image)
    # input_path = "./input/photo.jpg"
    # if os.path.exists(input_path):
    #     for style in styles:
    #         print(f"\nApplying {style} style...")
    #         result = transfer.apply_style(
    #             input_path,
    #             style=style,
    #             strength=0.6,
    #             seed=42
    #         )
    #         result.save(f"./output/style_transfer/{style}.png")
    
    print("Style transfer demo complete!")


if __name__ == "__main__":
    main()
```

### Quick Style Transfer

```python
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import torch

# Load pipeline
pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
    "stabilityai/stable-diffusion-1-5",
    torch_dtype=torch.float16,
)
pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda")

# Load image
image = Image.open("input.jpg").resize((512, 512))

# Apply style
result = pipeline(
    prompt="anime style, manga, vibrant colors",
    image=image,
    strength=0.6,
    num_inference_steps=25,
).images[0]

result.save("styled.png")
```

## Artistic Styles

### Style Reference

| Style | Strength | Steps | Effect |
|-------|----------|-------|--------|
| Anime | 0.5-0.7 | 25 | Cartoon-like |
| Oil Painting | 0.5-0.6 | 30 | Classic art |
| Watercolor | 0.4-0.5 | 25 | Soft, flowing |
| Cyberpunk | 0.6-0.8 | 30 | Futuristic neon |
| Vintage | 0.3-0.5 | 20 | Retro look |
| Comic | 0.6-0.7 | 25 | Bold colors |

### Custom Style Creation

```python
class StyleCreator:
    """Create custom styles"""
    
    @staticmethod
    def create_style(
        name,
        positive_keywords,
        negative_keywords="",
        category="artistic"
    ):
        """Create custom style definition"""
        
        return {
            "name": name,
            "prompt": ", ".join(positive_keywords),
            "negative": negative_keywords,
            "category": category,
        }
    
    @staticmethod
    def anime_style():
        """Anime/manga style definition"""
        return {
            "prompt": (
                "anime style, manga art, cel shaded, clean lines, "
                "vibrant colors, japanese animation style"
            ),
            "negative": (
                "photorealistic, realistic, 3d render, blurry, "
                "low quality, traditional art"
            )
        }
    
    @staticmethod
    def painterly_style():
        """Painterly style definition"""
        return {
            "prompt": (
                "oil painting style, brush strokes visible, "
                "traditional media, artistic, classic art technique"
            ),
            "negative": (
                "digital, photo, anime, cartoon, sharp edges"
            )
        }


# Usage
custom_style = StyleCreator.create_style(
    name="my_style",
    positive_keywords=["unique art style", "distinctive look", "professional"],
    negative_keywords="common, generic, low quality"
)
```

## Advanced Techniques

### 1. Style Strength Control

```python
class StyleStrengthController:
    """Control style intensity"""
    
    @staticmethod
    def apply_with_strength(image_path, style, strength_range=(0.2, 0.8)):
        """Apply style at different strengths"""
        
        results = []
        
        for strength in range(
            int(strength_range[0] * 10),
            int(strength_range[1] * 10) + 1,
            2
        ):
            strength = strength / 10
            
            result = style_transfer.apply_style(
                image_path,
                style,
                strength=strength
            )
            results.append((strength, result))
        
        return results
```

### 2. Progressive Styling

```python
class ProgressiveStyler:
    """Apply style progressively"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def stylize_progressive(
        self,
        image,
        style_prompt,
        stages=3
    ):
        """Apply style in progressive stages"""
        
        current = image.copy()
        
        for i in range(stages):
            # Increase strength each stage
            strength = (i + 1) / stages * 0.5
            
            result = self.pipeline(
                prompt=style_prompt,
                image=current,
                strength=strength,
                num_inference_steps=20,
            )
            
            current = result.images[0]
        
        return current
```

### 3. Reference Image Style Transfer

```python
class ReferenceStyleTransfer:
    """Transfer style from reference image"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def extract_style_from_reference(self, reference_path):
        """Analyze reference image for style"""
        
        # Simple approach: use reference in img2img
        reference = Image.open(reference_path).resize((512, 512))
        
        # Extract dominant colors (simplified)
        import numpy as np
        ref_array = np.array(reference)
        
        # Get average color as style indicator
        avg_color = ref_array.mean(axis=(0, 1))
        
        return {
            "reference": reference,
            "avg_color": avg_color,
        }
    
    def apply_with_reference(
        self,
        content_path,
        reference_path,
        style_strength=0.5
    ):
        """Apply reference image style"""
        
        content = Image.open(content_path).resize((512, 512))
        
        # Analyze reference
        style_info = self.extract_style_from_reference(reference_path)
        
        # Simple approach: blend in img2img
        result = self.pipeline(
            prompt="high quality, detailed, professional",
            image=content,
            strength=style_strength,
            num_inference_steps=30,
        ).images[0]
        
        return result
```

## Practical Applications

### 1. Photo Artification

```python
def photofy(image_path, target_style="oil_painting"):
    """Convert photo to artwork"""
    
    transfer = StyleTransfer()
    transfer.load_model()
    
    return transfer.apply_style(
        image_path,
        style=target_style,
        strength=0.6,
        num_inference_steps=30
    )
```

### 2. Character Art

```python
def create_character_art(character_photo, style="anime"):
    """Create character art from photo"""
    
    styles = {
        "anime": "anime character, manga style, vibrant",
        "comic": "comic book character, bold, dynamic",
        "fantasy": "fantasy character, epic, detailed",
    }
    
    prompt = f"character portrait, {styles.get(style, styles['anime'])}"
    
    return transfer.apply_custom_style(
        character_photo,
        style_prompt=prompt,
        strength=0.7
    )
```

### 3. Product Styling

```python
def style_product_image(product_path, style="minimalist"):
    """Apply style to product image"""
    
    styles = {
        "minimalist": "clean, white background, studio product photography",
        "luxury": "luxury product, elegant, premium, rich colors",
        "vintage": "vintage product photo, nostalgic, warm tones",
    }
    
    return transfer.apply_custom_style(
        product_path,
        style_prompt=styles.get(style, styles["minimalist"]),
        strength=0.4
    )
```

### 4. Social Media Content

```python
def create_social_media_style(photo, platform="instagram"):
    """Apply platform-specific style"""
    
    styles = {
        "instagram": "aesthetic, trendy, vibrant, popular",
        "vintage": "retro, nostalgic, vintage filter effect",
        "minimal": "minimalist, clean, modern, simple",
    }
    
    return transfer.apply_custom_style(
        photo,
        style_prompt=styles.get(platform, styles["instagram"]),
        strength=0.5
    )
```

## Troubleshooting

### Common Issues

#### 1. Style Not Visible

```python
# Solution: Increase strength
result = pipeline(
    prompt=style_prompt,
    image=image,
    strength=0.7,  # Higher strength
)
```

#### 2. Content Lost

```python
# Solution: Reduce strength
result = pipeline(
    prompt=style_prompt,
    image=image,
    strength=0.3,  # Lower strength
)
```

#### 3. Artifacts

```python
# Solution: Increase steps
result = pipeline(
    prompt=style_prompt,
    image=image,
    strength=0.5,
    num_inference_steps=40,  # More steps
)
```

#### 4. Memory Issues

```python
# Enable optimizations
pipeline.enable_attention_slicing()
pipeline.enable_vae_slicing()
pipeline.enable_model_cpu_offload()

# Reduce size
image = image.resize((384, 384))
```

## Next Steps

- Explore [Upscaling](./12-upscaling.md) for enhancing styled images
- Learn [Batch Processing](./13-batch-processing.md) for bulk styling
- Check [Image-to-Image](./07-image-to-image.md) for more techniques

## Additional Resources

- [Stable Diffusion Art](https://stable-diffusion-art.com/)
- [CivitAI Styles](https://civitai.com/)
- [HuggingFace Styles](https://huggingface.co/models?pipeline_tag=image-to-image)
