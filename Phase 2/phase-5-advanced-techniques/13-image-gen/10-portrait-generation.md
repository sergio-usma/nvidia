# Portrait Generation on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Portrait Generation](#understanding-portrait-generation)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Portrait Prompt Engineering](#portrait-prompt-engineering)
8. [Advanced Techniques](#advanced-techniques)
9. [Face Editing and Enhancement](#face-editing-and-enhancement)
10. [Troubleshooting](#troubleshooting)

## Introduction

Portrait generation is one of the most popular applications of AI image generation. This guide covers creating professional-quality portraits on your Jetson AGX Orin 64GB, including:

- Photorealistic human faces
- Artistic portraits
- Character design
- Face editing and enhancement
- Professional headshots
- Creative transformations

### Key Features

- High-quality facial rendering
- Accurate skin textures
- Proper lighting and shadows
- Expression control
- Age and appearance modification

## Understanding Portrait Generation

### Best Models for Portraits on Jetson

| Model | VRAM | Quality | Speed | Notes |
|-------|------|---------|-------|-------|
| Realistic Vision | 5GB | Excellent | Medium | Best for photorealistic |
| Juggernaut XL | 6GB | Excellent | Slow | SDXL-based |
| Deliberate | 4GB | Good | Fast | Artistic portraits |
| SD 1.5 + VAE | 4GB | Good | Fast | General use |
| Protogen | 5GB | Good | Medium | Anime/realistic mix |

### Portrait-Specific Techniques

1. **Face Detail Enhancement**: Using specialized VAEs
2. **Prompt Engineering**: Face-specific terminology
3. **Negative Embeddings**: Avoiding common artifacts
4. **LoRA Adapters**: Style-specific fine-tuning

## Prerequisites

### System Setup

```bash
# Enable performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Check GPU
python -c "import torch; print(torch.cuda.get_device_name(0))"
```

### Python Dependencies

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install diffusers transformers accelerate safetensors
pip install pillow numpy opencv-python
```

## Installation

### Recommended Setup

```python
# Using Realistic Vision for best portraits
from diffusers import StableDiffusionPipeline
import torch

pipeline = StableDiffusionPipeline.from_pretrained(
    "SG161222/Realistic_Vision_V5.1_noVAE",
    torch_dtype=torch.float16,
    variant="fp16",
)

# Add custom VAE for better faces
from diffusers import AutoencoderKL
vae = AutoencoderKL.from_pretrained(
    "stabilityai/sd-vae-ft-mse",
    torch_dtype=torch.float16,
)
pipeline.vae = vae

pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda")
```

### Alternative: Portrait-Specific Models

```python
# Using Deliberate for artistic portraits
pipeline = StableDiffusionPipeline.from_pretrained(
    "XpucT/Deliberate_v2",
    torch_dtype=torch.float16,
)

# Using SDXL with Juggernaut (requires more VRAM)
pipeline = StableDiffusionPipeline.from_pretrained(
    "RunDiffusion/Juggernaut_XL_v2",
    torch_dtype=torch.float16,
)
```

## Configuration

### Portrait Configuration

```python
PORTRAIT_CONFIG = {
    "model": "SG161222/Realistic_Vision_V5.1_noVAE",
    "vae": "stabilityai/sd-vae-ft-mse",
    
    "generation": {
        "default_steps": 35,
        "default_guidance": 7.0,
        "default_height": 512,
        "default_width": 512,
    },
    
    "portrait_prompts": {
        "positive": "photorealistic portrait, sharp focus, detailed skin, realistic eyes",
        "negative": "blurry, low quality, deformed, ugly, bad anatomy, extra fingers"
    },
    
    "optimization": {
        "attention_slicing": True,
        "vae_slicing": True,
    }
}
```

## Basic Usage

### Portrait Generator

```python
#!/usr/bin/env python3
"""
Portrait Generation on Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
import time
import numpy as np

class PortraitGenerator:
    """Generate professional portraits on Jetson"""
    
    # Portrait-specific negative prompts
    NEGATIVE_PROMPT = (
        "blurry, low quality, deformed, ugly, bad anatomy, "
        "extra fingers, extra limbs, deformed face, "
        "mutation, mutated, watermark, signature, text, logo, "
        "artistic, painting, illustration, cartoon, anime, "
        "3d render, digital art, grain, noise"
    )
    
    def __init__(self, model_id="SG161222/Realistic_Vision_V5.1_noVAE"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self, use_vae=True):
        """Load portrait model with optimizations"""
        
        print(f"Loading model: {self.model_id}")
        
        # Load with custom VAE for better faces
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
        
        # Enable optimizations
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        # Configure Karras scheduler
        self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipeline.scheduler.config,
            algorithm_type="dpmsolver++",
            use_karras_sigmas=True,
        )
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
            print("Model loaded on CUDA")
        
        print("Portrait model loaded!")
        return self.pipeline
    
    def generate(
        self,
        prompt,
        negative_prompt=None,
        height=512,
        width=512,
        num_inference_steps=35,
        guidance_scale=7.0,
        seed=None
    ):
        """Generate portrait"""
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded")
        
        # Use default negative if not provided
        if negative_prompt is None:
            negative_prompt = self.NEGATIVE_PROMPT
        
        # Set seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
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
        print(f"Portrait generated in {elapsed:.2f}s")
        
        return result.images[0]
    
    def generate_headshot(
        self,
        subject_description,
        lighting="professional studio lighting",
        camera="85mm lens",
        background="solid color",
        **kwargs
    ):
        """Generate professional headshot"""
        
        prompt = (
            f"professional headshot of {subject_description}, "
            f"{lighting}, shot with {camera}, "
            f"{background} background, sharp focus, "
            f"detailed skin texture, realistic eyes, "
            f"professional photography, 4k"
        )
        
        return self.generate(prompt, **kwargs)
    
    def generate_full_portrait(
        self,
        subject_description,
        pose="standing",
        setting="indoor",
        clothing="casual",
        **kwargs
    ):
        """Generate full portrait"""
        
        prompt = (
            f"portrait of {subject_description}, {pose} pose, "
            f"in {setting}, wearing {clothing}, "
            f"professional photography, detailed, sharp focus"
        )
        
        return self.generate(prompt, **kwargs)
    
    def generate_creative_portrait(
        self,
        subject_description,
        style="artistic",
        mood="dramatic",
        **kwargs
    ):
        """Generate artistic/creative portrait"""
        
        style_prompts = {
            "artistic": "artistic portrait, painterly, expressive",
            "dramatic": "dramatic lighting, cinematic, moody",
            "vintage": "vintage photograph, retro, nostalgic, film grain",
            "fashion": "high fashion, editorial, magazine style",
            "cinematic": "cinematic portrait, film still, dramatic",
            "minimalist": "minimalist, simple, clean composition",
        }
        
        prompt = (
            f"{subject_description}, {style_prompts.get(style, style_prompts['artistic'])}, "
            f"{mood} mood, professional photography"
        )
        
        return self.generate(prompt, **kwargs)
    
    def generate_group_portrait(
        self,
        subjects,
        relationship="friends",
        setting="casual",
        **kwargs
    ):
        """Generate group portrait"""
        
        prompt = (
            f"group portrait of {len(subjects)} {relationship}, "
            f"{', '.join(subjects)}, in {setting}, "
            f"professional photography, everyone in focus"
        )
        
        return self.generate(prompt, **kwargs)
    
    def save_portrait(self, image, output_path):
        """Save portrait with quality"""
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, "PNG", quality=95)
        print(f"Saved to: {output_path}")


def main():
    """Demo of portrait generation"""
    
    # Initialize
    generator = PortraitGenerator()
    generator.load_model()
    
    # Create output
    os.makedirs("./output/portraits", exist_ok=True)
    
    # Generate examples
    examples = [
        ("professional headshot", {
            "subject_description": "professional businesswoman, 30s, friendly smile",
            "lighting": "soft studio lighting",
            "camera": "85mm portrait lens",
            "seed": 42,
        }),
        ("creative portrait", {
            "subject_description": "artist with creative expression",
            "style": "dramatic",
            "mood": "moody",
            "seed": 43,
        }),
    ]
    
    for name, params in examples:
        print(f"\n=== Generating {name} ===")
        
        if "subject_description" in params:
            image = generator.generate_headshot(**params)
        else:
            image = generator.generate_creative_portrait(**params)
        
        generator.save_portrait(image, f"./output/portraits/{name.replace(' ', '_')}.png")
    
    print("\nPortrait generation complete!")


if __name__ == "__main__":
    main()
```

### Quick Portrait Generation

```python
# Quick portrait generation
from diffusers import StableDiffusionPipeline
from PIL import Image
import torch

# Load model
pipeline = StableDiffusionPipeline.from_pretrained(
    "SG161222/Realistic_Vision_V5.1_noVAE",
    torch_dtype=torch.float16,
)
pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda")

# Generate portrait
prompt = (
    "professional portrait of a woman, 30s, natural beauty, "
    "soft studio lighting, sharp focus, detailed skin, "
    "realistic eyes, 4k, professional photography"
)

negative = (
    "blurry, low quality, deformed, ugly, bad anatomy, "
    "extra fingers, artistic, cartoon, anime"
)

result = pipeline(
    prompt=prompt,
    negative_prompt=negative,
    num_inference_steps=30,
    guidance_scale=7.0,
)

result.images[0].save("portrait.png")
```

## Portrait Prompt Engineering

### Essential Portrait Elements

```python
class PortraitPromptBuilder:
    """Build professional portrait prompts"""
    
    # Subject descriptions
    SUBJECT_TYPES = {
        "man": "male, masculine features",
        "woman": "female, feminine features", 
        "child": "child, youthful features",
        "elderly": "elderly, aged features",
        "neutral": "androgynous features",
    }
    
    # Age descriptions
    AGE_RANGES = {
        "child": "young child, 5-7 years old",
        "teen": "teenager, 15-17 years old",
        "young_adult": "young adult, 20-30 years old",
        "middle_aged": "middle-aged, 40-50 years old",
        "elderly": "elderly person, 70+ years old",
    }
    
    # Lighting types
    LIGHTING = {
        "studio": "professional studio lighting, soft boxes",
        "natural": "natural window lighting, soft",
        "golden": "golden hour lighting, warm",
        "rim": "rim lighting, dramatic",
        "butterfly": "butterfly lighting, glamour",
        "split": "split lighting, dramatic",
        "rembrandt": "rembrandt lighting, classic",
    }
    
    # Camera settings
    CAMERA = {
        "portrait": "85mm portrait lens, f/1.8",
        "wide": "35mm wide angle, environmental portrait",
        "standard": "50mm standard lens",
        "telephoto": "135mm telephoto, compression",
    }
    
    # Backgrounds
    BACKGROUNDS = {
        "studio": "solid studio background, seamless",
        "gradient": "gradient background, professional",
        "outdoor": "outdoor setting, natural",
        "urban": "urban environment, city",
        "minimal": "minimal background, clean",
    }
    
    # Expressions
    EXPRESSIONS = {
        "neutral": "neutral expression, calm",
        "smile": "friendly smile, natural",
        "serious": "serious expression, confident",
        "joy": "joyful expression, happy",
        "contemplative": "contemplative, thoughtful",
    }
    
    @classmethod
    def build_portrait_prompt(
        cls,
        gender="man",
        age="young_adult",
        lighting="studio",
        camera="portrait",
        background="studio",
        expression="neutral",
        quality="high quality, detailed, sharp focus, 4k"
    ):
        """Build complete portrait prompt"""
        
        parts = []
        
        # Subject
        if gender in cls.SUBJECT_TYPES:
            parts.append(cls.SUBJECT_TYPES[gender])
        
        if age in cls.AGE_RANGES:
            parts.append(cls.AGE_RANGES[age])
        
        # Expression
        if expression in cls.EXPRESSIONS:
            parts.append(cls.EXPRESSIONS[expression])
        
        # Lighting
        if lighting in cls.LIGHTING:
            parts.append(cls.LIGHTING[lighting])
        
        # Camera
        if camera in cls.CAMERA:
            parts.append("shot with " + cls.CAMERA[camera])
        
        # Background
        if background in cls.BACKGROUNDS:
            parts.append(cls.BACKGROUNDS[background])
        
        # Quality
        parts.append(quality)
        
        # Add photography terms
        parts.extend([
            "professional photography",
            "portrait",
            "sharp focus on eyes",
            "detailed skin texture",
            "realistic",
        ])
        
        return ", ".join(parts)
    
    @classmethod
    def get_negative_prompt(cls):
        """Get portrait-specific negative prompt"""
        
        return (
            "blurry, low quality, distorted, ugly, "
            "bad anatomy, deformed face, extra fingers, "
            "extra limbs, mutation, watermark, signature, "
            "text, logo, artistic, painting, illustration, "
            "cartoon, anime, manga, 3d render, cgi, "
            "digital art, grain, noise, oversaturated"
        )


# Usage examples
prompt = PortraitPromptBuilder.build_portrait_prompt(
    gender="woman",
    age="young_adult",
    lighting="golden",
    camera="portrait",
    background="outdoor",
    expression="smile"
)
# Result: "female, feminine features, young adult, 20-30 years old, 
# friendly smile, golden hour lighting, shot with 85mm portrait lens, 
# f/1.8, outdoor setting, natural, high quality, detailed, sharp focus, 4k, 
# professional photography, portrait, sharp focus on eyes, detailed skin 
# texture, realistic"
```

### Parameter Reference

| Parameter | Recommended | Range | Effect |
|-----------|-------------|-------|--------|
| Steps | 30-40 | 20-50 | Higher = smoother |
| Guidance | 6-8 | 4-12 | Higher = prompt adherence |
| Resolution | 512x512 | 384-768 | Higher = more detail |
| Seed | Fixed/None | Any | Fixed = reproducible |

## Advanced Techniques

### 1. Face Enhancement LoRA

```python
class EnhancedPortraitGenerator:
    """Portrait generation with face enhancement"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def load_face_lora(self, lora_path, scale=0.7):
        """Load face enhancement LoRA"""
        
        self.pipeline.load_lora_weights(lora_path)
        self.pipeline.set_adapters([lora_path], scales=[scale])
    
    def generate_with_face_enhancement(
        self,
        prompt,
        face_lora_path=None,
        **kwargs
    ):
        """Generate portrait with enhanced face details"""
        
        if face_lora_path:
            self.load_face_lora(face_lora_path)
        
        return self.pipeline(
            prompt=prompt,
            num_inference_steps=35,
            guidance_scale=7.0,
            **kwargs
        ).images[0]
```

### 2. Expression Control

```python
class ExpressionController:
    """Control facial expressions in portraits"""
    
    EXPRESSION_PROMPTS = {
        "happy": "happy, smiling, joyful, teeth showing",
        "serious": "serious, solemn, dignified, composed",
        "surprised": "surprised, wide-eyed, astonished",
        "angry": "angry, intense, fierce expression",
        "sad": "sad, melancholy, sorrowful, contemplative",
        "thoughtful": "thoughtful, pensive, reflective",
        "confident": "confident, powerful, commanding",
        "shy": "shy, timid, reserved, modest",
    }
    
    @classmethod
    def add_expression(cls, base_prompt, expression):
        """Add expression to prompt"""
        
        if expression in cls.EXPRESSION_PROMPTS:
            return base_prompt + ", " + cls.EXPRESSION_PROMPTS[expression]
        
        return base_prompt
```

### 3. Age Modification

```python
class AgeModifier:
    """Modify age in portraits"""
    
    AGE_PROMPTS = {
        "child": "child face, young, innocent, round features",
        "teen": "teenager, youthful, fresh, smooth skin",
        "young": "young adult, 20s, youthful, vibrant",
        "middle": "middle-aged, 40s, mature, distinguished",
        "elderly": "elderly, senior, aged, wrinkles, wisdom",
    }
    
    @classmethod
    def set_age(cls, base_prompt, age):
        """Set age in prompt"""
        
        if age in cls.AGE_PROMPTS:
            # Remove any existing age references
            for age_term in cls.AGE_PROMPTS.values():
                base_prompt = base_prompt.replace(age_term, "")
            
            return base_prompt + ", " + cls.AGE_PROMPTS[age]
        
        return base_prompt
```

### 4. Lighting Effects

```python
class LightingController:
    """Control lighting in portraits"""
    
    LIGHTING_SETUPS = {
        "butterfly": {
            "prompt": "butterfly lighting, glamour lighting, shadow under nose",
            "position": "above and in front of subject"
        },
        "rembrandt": {
            "prompt": "rembrandt lighting, triangle shadow on cheek",
            "position": "45 degrees to side and above"
        },
        "split": {
            "prompt": "split lighting, half face illuminated",
            "position": "90 degrees to side"
        },
        "loop": {
            "prompt": "loop lighting, small shadow beside nose",
            "position": "30-45 degrees to side"
        },
        "broad": {
            "prompt": "broad lighting, illuminated side facing camera",
            "position": "side facing camera"
        },
        "short": {
            "prompt": "short lighting, shadow side facing camera",
            "position": "opposite side from camera"
        },
    }
    
    @classmethod
    def set_lighting(cls, base_prompt, lighting_type):
        """Set lighting in prompt"""
        
        if lighting_type in cls.LIGHTING_SETUPS:
            return base_prompt + ", " + cls.LIGHTING_SETUPS[lighting_type]["prompt"]
        
        return base_prompt
```

## Face Editing and Enhancement

### 1. Face Enhancement

```python
class FaceEnhancer:
    """Enhance existing portrait faces"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def enhance_face(
        self,
        image_path,
        enhancement_type="detail",
        strength=0.3
    ):
        """Enhance face in image"""
        
        from diffusers import StableDiffusionImg2ImgPipeline
        
        # Convert to img2img
        img2img = StableDiffusionImg2ImgPipeline(
            vae=self.pipeline.vae,
            text_encoder=self.pipeline.text_encoder,
            tokenizer=self.pipeline.tokenizer,
            unet=self.pipeline.unet,
            scheduler=self.pipeline.scheduler,
            safety_checker=None,
            feature_extractor=None,
            requires_safety_checker=False,
        )
        img2img = img2img.to("cuda")
        
        # Load image
        image = Image.open(image_path).resize((512, 512))
        
        # Enhancement prompts
        prompts = {
            "detail": "enhanced details, sharper features, more detail",
            "smooth": "smoother skin, refined features, polished",
            "youthful": "youthful appearance, younger, fresh skin",
            "professional": "professional headshot, retouched, magazine quality",
        }
        
        result = img2img(
            prompt=prompts.get(enhancement_type, prompts["detail"]),
            image=image,
            strength=strength,
            num_inference_steps=25,
            guidance_scale=7.0,
        ).images[0]
        
        return result
```

### 2. Face Swap (Simplified)

```python
class FaceEditor:
    """Edit specific facial features"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def change_hair(
        self,
        image_path,
        hair_description,
        **kwargs
    ):
        """Change hair style/color"""
        
        # Use inpainting
        from diffusers import StableDiffusionInpaintPipeline
        
        inpaint = StableDiffusionInpaintPipeline.from_pretrained(
            "runwayml/stable-diffusion-inpainting",
            torch_dtype=torch.float16,
        )
        inpaint = inpaint.to("cuda")
        
        # Load image and create mask for hair area
        image = Image.open(image_path).resize((512, 512))
        
        # Simplified: mask center-upper portion
        mask = Image.new("L", image.size, 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.ellipse([50, 50, 462, 300], fill=255)
        
        # Generate
        prompt = f"realistic hair, {hair_description}, natural looking"
        
        result = inpaint(
            prompt=prompt,
            image=image,
            mask_image=mask,
            **kwargs
        ).images[0]
        
        return result
```

## Troubleshooting

### Common Issues

#### 1. Unrealistic Faces

```python
# Solution: Use better prompts and negative prompts
prompt = "photorealistic portrait, realistic face, detailed skin"
negative = "cartoon, anime, illustration, painting, deformed, ugly"
```

#### 2. Asymmetrical Features

```python
# Solution: Add symmetry-focused prompts
prompt += ", symmetrical face, balanced features, even features"
```

#### 3. Poor Skin Texture

```python
# Solution: Use custom VAE and add skin prompts
vae = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse")
pipeline.vae = vae

prompt += ", detailed skin texture, realistic pores, natural skin"
```

#### 4. Out of Memory

```python
# Solution: Enable optimizations
pipeline.enable_attention_slicing()
pipeline.enable_vae_slicing()
pipeline.enable_model_cpu_offload()

# Reduce resolution
height, width = 384, 384
```

### Quality Checklist

- [ ] Use dedicated portrait model (Realistic Vision)
- [ ] Include detailed face descriptions
- [ ] Add skin/eye detail prompts
- [ ] Use appropriate negative prompts
- [ ] Enable VAE slicing for memory
- [ ] Use 30+ inference steps
- [ ] Keep guidance scale 6-8

## Next Steps

- Learn about [Style Transfer](./11-style-transfer.md) for artistic portraits
- Explore [Upscaling](./12-upscaling.md) for resolution enhancement
- Check [Batch Processing](./13-batch-processing.md) for bulk generation

## Additional Resources

- [Realistic Vision Model](https://huggingface.co/SG161222/Realistic_Vision_V5.1_noVAE)
- [Portrait Prompt Guide](https://promptbase.com/)
- [Photography Lighting Guide](https://www.studiobinder.com/blog/photography-lighting-terms/)
