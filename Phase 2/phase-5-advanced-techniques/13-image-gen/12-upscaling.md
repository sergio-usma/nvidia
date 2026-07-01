# Image Upscaling on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Upscaling](#understanding-upscaling)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Upscaling Models](#upscaling-models)
8. [Advanced Techniques](#advanced-techniques)
9. [Practical Applications](#practical-applications)
10. [Troubleshooting](#troubleshooting)

## Introduction

Image upscaling increases image resolution while maintaining or enhancing quality. This guide covers deploying upscaling on your Jetson AGX Orin 64GB, enabling:

- 2x, 4x, or 8x image enlargement
- AI-enhanced detail reconstruction
- Noise reduction
- Artifact removal
- Photo enhancement

### Why Upscaling?

- **Generated images** are typically 512x512
- **Upscaling** can bring them to 1024x1024 or higher
- **AI upscaling** adds realistic details
- **Better than bicubic** interpolation

## Understanding Upscaling

### Types of Upscaling

| Method | Quality | Speed | Best For |
|--------|---------|-------|----------|
| Bicubic | Low | Fast | Quick preview |
| Lanczos | Low | Fast | General use |
| ESRGAN | High | Medium | AI enhancement |
| Real-ESRGAN | High | Medium | Universal |
| SwinIR | High | Slow | High quality |
| SD Upscale | High | Slow | Generation |

### Jetson Considerations

- Real-ESRGAN is most practical for Jetson
- TensorRT optimization available
- 4x upscaling is memory-intensive

## Prerequisites

### System Setup

```bash
sudo nvpmodel -m 0
sudo jetson_clocks

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install pillow numpy opencv-python scipy
```

## Installation

### Install Real-ESRGAN

```bash
# Option 1: Using pip
pip install realesrgan-ncnn-vulkan

# Option 2: For Python
pip install realesrgan
```

### Alternative: Using diffusers

```python
# For TensorRT-based upscaling
pip install tensorrt
```

## Configuration

### Upscaling Configuration

```python
UPSCALE_CONFIG = {
    "models": {
        "RealESRGAN_x2": "RealESRGAN_x2plus",
        "RealESRGAN_x4": "RealESRGAN_x4plus",
        "RealESRGAN_x8": "RealESRGAN_x8plus",
    },
    
    "default_settings": {
        "scale": 2,
        "tile_size": 256,
        "tile_pad": 10,
        "pre_pad": 0,
    },
    
    "optimization": {
        "gpu_id": 0,
        "num_threads": 4,
    }
}
```

## Basic Usage

### Real-ESRGAN Upscaling

```python
#!/usr/bin/env python3
"""
Image Upscaling on Jetson AGX Orin
"""

import torch
from PIL import Image
import os
import numpy as np

class ImageUpscaler:
    """AI-powered image upscaling for Jetson"""
    
    def __init__(self, model_name="RealESRGAN_x2plus"):
        self.model_name = model_name
        self.model = None
        
    def load_model(self):
        """Load upscaling model"""
        
        try:
            from realesrgan_ncnn_vulkan import RealESRGAN
            from realesrgan_ncnn_vulkan import RealESRGAN_vulkan
            
            # Initialize with Vulkan/NCNN
            self.model = RealESRGAN(gpu_id=0, scale=2)
            
            print(f"Loaded Real-ESRGAN model")
            return self.model
            
        except ImportError:
            print("Real-ESRGAN not available, using alternative method")
            return None
    
    def upscale_pillow(self, image, scale=2):
        """Upscale using PIL (fallback)"""
        
        new_size = (image.width * scale, image.height * scale)
        return image.resize(new_size, Image.Resampling.LANCZOS)
    
    def upscale_bicubic(self, image, scale=2):
        """Simple bicubic upscaling"""
        
        new_size = (image.width * scale, image.height * scale)
        return image.resize(new_size, Image.Resampling.BICUBIC)
    
    def upscale_lanczos(self, image, scale=2):
        """Lanczos upscaling"""
        
        new_size = (image.width * scale, image.height * scale)
        return image.resize(new_size, Image.Resampling.LANCZOS)
    
    def upscale_with_model(
        self,
        image_path,
        output_path=None,
        scale=2,
        denoise_strength=0
    ):
        """Upscale using AI model"""
        
        if self.model is None:
            # Fallback to PIL
            image = Image.open(image_path)
            result = self.upscale_lanczos(image, scale)
            
            if output_path:
                result.save(output_path)
            return result
        
        # Use Real-ESRGAN
        img = cv2.imread(image_path)
        result = self.model.process(img)
        
        result_img = Image.fromarray(result)
        
        if output_path:
            result_img.save(output_path)
        
        return result_img
    
    def enhance_image(
        self,
        image_path,
        scale=2,
        sharpness=1.0,
        denoise=True
    ):
        """Enhance and upscale image"""
        
        # Load image
        image = Image.open(image_path)
        
        # Upscale first
        upscaled = self.upscale_lanczos(image, scale)
        
        # Apply sharpening if requested
        if sharpness != 1.0:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Sharpness(upscaled)
            upscaled = enhancer.enhance(sharpness)
        
        return upscaled


# Alternative: Using PyTorch-based upscaling
class PyTorchUpscaler:
    """PyTorch-based upscaling models"""
    
    def __init__(self):
        self.pipeline = None
        
    def load_rrdb(self):
        """Load RRDB model"""
        
        # This is a simplified version
        # For production, use pre-trained models from torch.hub
        
        import torch.nn as nn
        
        class SimpleUpsampler(nn.Module):
            def __init__(self, scale):
                super().__init__()
                self.scale = scale
                
                self.conv1 = nn.Conv2d(3, 64, 3, padding=1)
                self.conv2 = nn.Conv2d(64, 64, 3, padding=1)
                self.conv3 = nn.Conv2d(64, 3 * (scale ** 2), 3, padding=1)
                self.pixel_shuffle = nn.PixelShuffle(scale)
                self.relu = nn.ReLU()
                
            def forward(self, x):
                x = self.relu(self.conv1(x))
                x = self.relu(self.conv2(x))
                x = self.conv3(x)
                x = self.pixel_shuffle(x)
                return x
        
        self.model = SimpleUpsampler(scale=2)
        return self.model
    
    def upscale(self, image, scale=2):
        """Upscale image using model"""
        
        if self.model is None:
            self.load_rrdb()
        
        # Convert to tensor
        img_array = np.array(image).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).unsqueeze(0)
        
        # Upscale
        with torch.no_grad():
            output = self.model(img_tensor)
        
        # Convert back to PIL
        output = output.squeeze(0).permute(1, 2, 0).numpy()
        output = (output * 255).clip(0, 255).astype(np.uint8)
        
        return Image.fromarray(output)


def main():
    """Demo of upscaling capabilities"""
    
    upscaler = ImageUpscaler()
    
    # Create output directory
    os.makedirs("./output/upscaling", exist_ok=True)
    
    print("Upscaling demo complete!")
    print("Add images to test upscaling")


if __name__ == "__main__":
    main()
```

### Using Real-ESRGAN CLI

```bash
# Install Real-ESRGAN
git clone https://github.com/xinntao/Real-ESRGAN.git
cd Real-ESRGAN
pip install -e .

# Upscale image
python realesrgan_ncnn_vulkan.py -i input.png -o output.png -s 2

# Parameters
# -i: input path
# -o: output path  
# -s: scale (2, 4, 8)
# -n: model name
```

### Using with diffusers

```python
# Stable Diffusion Upscale
from diffusers import StableDiffusionUpscalePipeline
import torch

pipeline = StableDiffusionUpscalePipeline.from_pretrained(
    "stabilityai/stable-diffusion-x4-upscaler",
    torch_dtype=torch.float16,
)

pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda")

# Load low-res image
low_res_image = Image.open("low_res.png").convert("RGB")
low_res_image = low_res_image.resize((512, 512))

# Upscale
upscaled_image = pipeline(
    prompt="high quality, detailed",
    image=low_res_image,
    num_inference_steps=30,
).images[0]

upscaled_image.save("upscaled.png")
```

## Upscaling Models

### Available Models

| Model | Scale | VRAM | Speed | Quality |
|-------|-------|------|-------|---------|
| Real-ESRGAN x2 | 2x | 2GB | Fast | Good |
| Real-ESRGAN x4 | 4x | 3GB | Medium | Very Good |
| Real-ESRGAN x8 | 8x | 4GB | Slow | Good |
| ESRGAN | 4x | 3GB | Medium | Good |
| SwinIR | 4x | 4GB | Slow | Excellent |
| SD Upscale | 4x | 6GB | Very Slow | Best |

### Model Selection Guide

```python
UPSCALING_MODELS = {
    "anime": {
        "model": "RealESRGAN_x2plus-anime",
        "scale": 2,
        "description": "Best for anime/artwork"
    },
    "photographic": {
        "model": "RealESRGAN_x4plus",
        "scale": 4,
        "description": "Best for photos"
    },
    "universal": {
        "model": "RealESRGAN_x4plus",
        "scale": 4,
        "description": "General purpose"
    },
}
```

## Advanced Techniques

### 1. Tile-Based Upscaling

```python
class TiledUpscaler:
    """Upscale large images in tiles"""
    
    def __init__(self, tile_size=256, tile_overlap=16):
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
    
    def upscale_tiled(self, image, scale=2, upscaler=None):
        """Upscale in tiles to save memory"""
        
        img_array = np.array(image)
        h, w = img_array.shape[:2]
        
        # Calculate output size
        out_h, out_w = h * scale, w * scale
        
        # Initialize output
        output = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        
        # Process tiles
        for y in range(0, h, self.tile_size - self.tile_overlap):
            for x in range(0, w, self.tile_size - self.tile_overlap):
                # Extract tile
                y_end = min(y + self.tile_size, h)
                x_end = min(x + self.tile_size, w)
                
                tile = image.crop((x, y, x_end, y_end))
                
                # Upscale tile
                if upscaler:
                    tile_up = upscaler.upscale_lanczos(tile, scale)
                else:
                    tile_up = tile.resize(
                        (tile.width * scale, tile.height * scale),
                        Image.Resampling.LANCZOS
                    )
                
                # Place in output
                out_y = y * scale
                out_x = x * scale
                out_y_end = y_end * scale
                out_x_end = x_end * scale
                
                output[out_y:out_y_end, out_x:out_x_end] = np.array(tile_up)
        
        return Image.fromarray(output)
```

### 2. Progressive Upscaling

```python
class ProgressiveUpscaler:
    """Upscale in multiple passes"""
    
    def __init__(self):
        self.upscaler = ImageUpscaler()
    
    def upscale_progressive(self, image, target_scale=4):
        """Upscale progressively (2x -> 2x -> etc)"""
        
        current = image
        current_scale = 1
        
        while current_scale < target_scale:
            # Double scale each pass
            next_scale = min(current_scale * 2, target_scale)
            scale_factor = next_scale / current_scale
            
            # Upscale
            new_size = (
                current.width * scale_factor,
                current.height * scale_factor
            )
            current = current.resize(new_size, Image.Resampling.LANCZOS)
            
            current_scale = next_scale
            
            print(f"Upscaled to {current_scale}x")
        
        return current
```

### 3. Enhancement Pipeline

```python
class EnhancementPipeline:
    """Complete enhancement pipeline"""
    
    def __init__(self):
        self.upscaler = ImageUpscaler()
    
    def enhance_full(
        self,
        image_path,
        upscale_scale=2,
        denoise=True,
        sharpen=True,
        color_correct=True
    ):
        """Full enhancement pipeline"""
        
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # 1. Upscale
        print("Upscaling...")
        upscaled = self.upscaler.upscale_lanczos(image, upscale_scale)
        
        # 2. Denoise if requested
        if denoise:
            print("Denoising...")
            upscaled = upscaled.filter(ImageFilter.MedianFilter(size=3))
        
        # 3. Sharpen if requested
        if sharpen:
            print("Sharpening...")
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Sharpness(upscaled)
            upscaled = enhancer.enhance(1.3)
        
        # 4. Color correction if requested
        if color_correct:
            print("Color correcting...")
            upscaled = self._auto_color_correct(upscaled)
        
        return upscaled
    
    def _auto_color_correct(self, image):
        """Simple auto color correction"""
        
        from PIL import ImageOps
        
        # Auto contrast
        image = ImageOps.autocontrast(image)
        
        return image
```

## Practical Applications

### 1. Upscale AI Art

```python
def upscale_ai_art(art_path, output_path=None, scale=4):
    """Upscale AI-generated artwork"""
    
    upscaler = ImageUpscaler()
    
    # For AI art, Real-ESRGAN is recommended
    result = upscaler.enhance_image(
        art_path,
        scale=scale,
        sharpness=1.2  # Slightly sharper for AI art
    )
    
    if output_path:
        result.save(output_path)
    
    return result
```

### 2. Upscale Photos

```python
def upscale_photo(photo_path, output_path=None, scale=2):
    """Upscale photographs"""
    
    upscaler = ImageUpscaler()
    
    # For photos, preserve natural look
    result = upscaler.enhance_image(
        photo_path,
        scale=scale,
        sharpness=1.0,
        denoise=True
    )
    
    if output_path:
        result.save(output_path, quality=95)
    
    return result
```

### 3. Batch Upscaling

```python
def batch_upscale(input_dir, output_dir, scale=2):
    """Upscale multiple images"""
    
    upscaler = ImageUpscaler()
    
    # Get all images
    import glob
    image_files = glob.glob(os.path.join(input_dir, "*.png"))
    image_files.extend(glob.glob(os.path.join(input_dir, "*.jpg")))
    
    os.makedirs(output_dir, exist_ok=True)
    
    for img_file in image_files:
        print(f"Upscaling: {img_file}")
        
        filename = os.path.basename(img_file)
        output_path = os.path.join(output_dir, filename)
        
        result = upscaler.enhance_image(img_file, scale=scale)
        result.save(output_path)
    
    print(f"Upscaled {len(image_files)} images")
```

### 4. Before/After Comparison

```python
def create_comparison(original_path, upscaled_path, output_path):
    """Create side-by-side comparison"""
    
    original = Image.open(original_path)
    upscaled = Image.open(upscaled_path)
    
    # Match sizes for comparison
    if original.size != upscaled.size:
        original = original.resize(upscaled.size, Image.Resampling.LANCZOS)
    
    # Create comparison image
    comparison = Image.new('RGB', (upscaled.width * 2 + 10, upscaled.height))
    
    comparison.paste(original, (0, 0))
    comparison.paste(upscaled, (upscaled.width + 10, 0))
    
    # Add labels
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(comparison)
    
    # Try to use a font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    draw.text((10, 10), "Original", fill="white", font=font)
    draw.text((upscaled.width + 20, 10), "Upscaled", fill="white", font=font)
    
    comparison.save(output_path)
```

## Troubleshooting

### Common Issues

#### 1. Out of Memory

```python
# Solution: Use smaller tile size
tile_size = 128  # Instead of 256

# Or use progressive upscaling
progressive = ProgressiveUpscaler()
result = progressive.upscale_progressive(image, target_scale=4)
```

#### 2. Artifacts

```python
# Solution: Add post-processing
result = result.filter(ImageFilter.SMOOTH)
result = result.filter(ImageFilter.MedianFilter(size=3))
```

#### 3. Wrong Colors

```python
# Solution: Color correction
result = ImageOps.autocontrast(result)
result = ImageOps.equalize(result)
```

#### 4. Slow Processing

```bash
# Solution: Use lower scale
# 2x is much faster than 4x

# Or use simpler method
result = upscaler.upscale_bicubic(image, scale=2)
```

### Performance Tips

```bash
# Monitor GPU
tegrastats

# Check memory
python -c "import torch; print(torch.cuda.max_memory_allocated() / 1024**3, 'GB')"
```

### Quality Settings

| Scale | Quality | Speed | Use Case |
|-------|---------|-------|----------|
| 2x | Good | Fast | Quick upscale |
| 4x | Very Good | Medium | Standard use |
| 8x | Good | Slow | Maximum size |

## Next Steps

- Explore [Batch Processing](./13-batch-processing.md) for bulk upscaling
- Check [Image-to-Image](./07-image-to-image.md) for enhancement
- Learn [Portrait Generation](./10-portrait-generation.md) for face enhancement

## Additional Resources

- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- [Upscaling Models](https://upscale.media/)
- [AI Upscaling Guide](https://magazine.sebastraschke.com/p/ai-upscaling-explained)
