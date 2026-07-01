# Inpainting & Outpainting on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Inpainting & Outpainting](#understanding-inpainting--outpainting)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Mask Creation](#mask-creation)
8. [Advanced Techniques](#advanced-techniques)
9. [Creative Applications](#creative-applications)
10. [Troubleshooting](#troubleshooting)

## Introduction

Inpainting and outpainting are powerful image editing techniques that allow you to:

- **Inpainting**: Remove unwanted objects, fill missing areas, or replace specific regions
- **Outpainting**: Extend an image beyond its original boundaries to create larger scenes

This guide covers deploying these capabilities on your Jetson AGX Orin 64GB, enabling precise image editing and creative extensions.

### Use Cases

| Technique | Applications |
|-----------|--------------|
| Inpainting | Object removal, face editing, text removal, product replacement |
| Outpainting | Scene extension, panoramic creation, background expansion |

## Understanding Inpainting & Outpainting

### How Inpainting Works

1. A mask defines the region to be modified
2. The model generates new content for the masked area
3. Content is conditioned on both the prompt and unmasked regions
4. The result blends seamlessly with the original

### How Outpainting Works

1. The original image defines the content to extend
2. The model generates content extending from edges
3. Multiple passes can expand the scene progressively
4. Consistent lighting and perspective are maintained

### Jetson Considerations

| Feature | Memory Usage | Recommended |
|---------|--------------|-------------|
| Inpainting | ~4GB VRAM | SD 1.5 models |
| Outpainting | ~5GB VRAM | SD 1.5 with tiling |
| Combined | ~6GB VRAM | Optimized pipeline |

## Prerequisites

### System Setup

```bash
# Enable performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Python Dependencies

```bash
# Install dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

pip install diffusers transformers accelerate safetensors
pip install pillow numpy opencv-python
```

## Installation

### Install Inpainting Model

```python
# Using Stable Diffusion Inpainting
from diffusers import StableDiffusionInpaintPipeline

pipeline = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float16,
)
```

### Alternative: Use SD 1.5 with Mask

```python
# Use standard SD 1.5 with inpainting pipeline
# This works better on Jetson due to smaller size

from diffusers import StableDiffusionInpaintPipeline

pipeline = StableDiffusionInpaintPipeline.from_pretrained(
    "stabilityai/stable-diffusion-1-5-inpainting",
    torch_dtype=torch.float16,
)
```

## Configuration

### Recommended Settings

```python
INPAINT_CONFIG = {
    "model": "runwayml/stable-diffusion-inpainting",
    "alt_model": "stabilityai/stable-diffusion-1-5-inpainting",
    
    "generation": {
        "steps": 30,
        "guidance": 7.5,
        "mask_blur": 8,
        "inpainting_fill": 0,
    },
    
    "optimization": {
        "attention_slicing": True,
        "vae_slicing": True,
    },
}
```

## Basic Usage

### Inpainting Implementation

```python
#!/usr/bin/env python3
"""
Inpainting and Outpainting on Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionInpaintPipeline
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os
import time

class InpaintingEditor:
    """Inpainting editor for Jetson"""
    
    def __init__(self, model_id="runwayml/stable-diffusion-inpainting"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self):
        """Load inpainting model"""
        
        print(f"Loading model: {self.model_id}")
        
        self.pipeline = StableDiffusionInpaintPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        # Enable optimizations
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
            print("Model loaded on CUDA")
        
        print("Inpainting model loaded!")
        return self.pipeline
    
    def load_image(self, image_path):
        """Load and prepare image"""
        
        image = Image.open(image_path).convert("RGB")
        return image.resize((512, 512), Image.Resampling.LANCZOS)
    
    def create_mask(
        self,
        image,
        mask_type="manual",
        bounds=None,
        brush_size=20
    ):
        """Create inpainting mask"""
        
        if mask_type == "manual":
            return self._create_manual_mask(image, bounds)
        elif mask_type == "brush":
            return self._create_brush_mask(image, brush_size)
        elif mask_type == "auto":
            return self._create_auto_mask(image)
        else:
            raise ValueError(f"Unknown mask type: {mask_type}")
    
    def _create_manual_mask(self, image, bounds):
        """Create mask from bounds [x1, y1, x2, y2]"""
        
        # Create white image
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        
        # Draw rectangle
        if bounds:
            draw.rectangle(bounds, fill=255)
        
        return mask
    
    def _create_brush_mask(self, image, brush_size):
        """Interactive brush mask creation"""
        
        # For now, create a simple circular mask in center
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        
        # Center circle
        cx, cy = image.size[0] // 2, image.size[1] // 2
        r = min(image.size) // 4
        
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=255)
        
        return mask
    
    def _create_auto_mask(self, image):
        """Auto-detect areas to inpaint"""
        
        # Simple edge detection approach
        img_array = np.array(image.convert("L"))
        
        # Find edges
        from scipy import ndimage
        edges = ndimage.sobel(img_array)
        
        # Create mask from edges
        mask = (np.abs(edges) > 50).astype(np.uint8) * 255
        
        # Expand regions
        from scipy.ndimage import binary_dilation
        mask = binary_dilation(mask, iterations=10)
        mask = (mask * 255).astype(np.uint8)
        
        return Image.fromarray(mask, "L")
    
    def inpaint(
        self,
        image,
        mask,
        prompt,
        negative_prompt=None,
        num_inference_steps=30,
        guidance_scale=7.5,
        seed=None
    ):
        """Inpaint the masked area"""
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded")
        
        # Set negative prompt
        if negative_prompt is None:
            negative_prompt = (
                "blurry, low quality, distorted, ugly, "
                "deformed, bad anatomy, extra limbs, watermark"
            )
        
        # Set seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator.manual_seed(seed)
        
        # Inpaint
        start_time = time.time()
        
        with torch.inference_mode():
            result = self.pipeline(
                prompt=prompt,
                image=image,
                mask_image=mask,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
        
        elapsed = time.time() - start_time
        print(f"Inpainting completed in {elapsed:.2f}s")
        
        return result.images[0]
    
    def remove_object(self, image_path, bounds, prompt="clean background", **kwargs):
        """Remove object from image"""
        
        # Load image and create mask
        image = self.load_image(image_path)
        mask = self.create_mask(image, bounds=bounds)
        
        # Inpaint with generic prompt
        return self.inpaint(image, mask, prompt, **kwargs)
    
    def replace_object(
        self,
        image_path,
        bounds,
        replacement_description,
        **kwargs
    ):
        """Replace object with something else"""
        
        image = self.load_image(image_path)
        mask = self.create_mask(image, bounds=bounds)
        
        prompt = f"{replacement_description}, high quality, detailed"
        
        return self.inpaint(image, mask, prompt, **kwargs)


class OutpaintingEditor:
    """Outpainting for extending images"""
    
    def __init__(self, model_id="runwayml/stable-diffusion-inpainting"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self):
        """Load model for outpainting"""
        
        self.pipeline = StableDiffusionInpaintPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
        )
        
        self.pipeline.enable_attention_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
        
        return self.pipeline
    
    def extend_image(
        self,
        image_path,
        direction="right",
        extension_size=128,
        prompt="continuation of scene, seamless",
        num_inference_steps=30,
        **kwargs
    ):
        """Extend image in specified direction"""
        
        # Load image
        image = Image.open(image_path).convert("RGB")
        original_size = image.size
        
        # Create extended canvas
        if direction in ["left", "right"]:
            new_width = original_size[0] + extension_size
            new_height = original_size[1]
            new_image = Image.new("RGB", (new_width, new_height), (0, 0, 0))
            
            if direction == "right":
                new_image.paste(image, (0, 0))
                paste_x = original_size[0]
            else:
                new_image.paste(image, (extension_size, 0))
                paste_x = 0
                
            # Create mask for new area
            mask = Image.new("L", (new_width, new_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            
            if direction == "right":
                mask_draw.rectangle(
                    [original_size[0], 0, new_width, new_height],
                    fill=255
                )
            else:
                mask_draw.rectangle(
                    [0, 0, extension_size, new_height],
                    fill=255
                )
        
        else:  # top or bottom
            new_width = original_size[0]
            new_height = original_size[1] + extension_size
            new_image = Image.new("RGB", (new_width, new_height), (0, 0, 0))
            
            if direction == "bottom":
                new_image.paste(image, (0, 0))
                paste_y = original_size[1]
            else:
                new_image.paste(image, (0, extension_size))
                paste_y = 0
            
            # Create mask
            mask = Image.new("L", (new_width, new_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            
            if direction == "bottom":
                mask_draw.rectangle(
                    [0, original_size[1], new_width, new_height],
                    fill=255
                )
            else:
                mask_draw.rectangle(
                    [0, 0, new_width, extension_size],
                    fill=255
                )
        
        # Resize for model
        new_image = new_image.resize((512, 512), Image.Resampling.LANCZOS)
        mask = mask.resize((512, 512), Image.Resampling.LANCZOS)
        
        # Inpaint
        result = self.pipeline(
            prompt=prompt,
            image=new_image,
            mask_image=mask,
            num_inference_steps=num_inference_steps,
            **kwargs
        ).images[0]
        
        # Resize back
        result = result.resize((new_width, new_height))
        
        return result
    
    def extend_panoramic(
        self,
        image_path,
        num_extensions=3,
        direction="right",
        prompt="beautiful landscape, continuation",
        **kwargs
    ):
        """Create panoramic by extending multiple times"""
        
        current_image = Image.open(image_path).convert("RGB")
        current_image = current_image.resize((512, 512))
        
        for i in range(num_extensions):
            print(f"Extension {i+1}/{num_extensions}")
            
            # Extend
            current_image = self.extend_image(
                current_image,
                direction=direction,
                extension_size=128,
                prompt=prompt,
                **kwargs
            )
        
        return current_image


def main():
    """Demo of inpainting capabilities"""
    
    # Initialize inpainter
    inpainter = InpaintingEditor()
    inpainter.load_model()
    
    # Create output directory
    os.makedirs("./output/inpainting", exist_ok=True)
    
    # Example: Remove object (requires input image)
    # image_path = "./input/photo.jpg"
    # if os.path.exists(image_path):
    #     result = inpainter.remove_object(
    #         image_path,
    #         bounds=[100, 100, 300, 300],
    #         prompt="smooth background",
    #         seed=42
    #     )
    #     result.save("./output/inpainting/removed.png")
    
    print("Inpainting demo complete!")
    print("Add input images to test inpainting features")


if __name__ == "__main__":
    main()
```

### Quick Inpainting Example

```python
from diffusers import StableDiffusionInpaintPipeline
from PIL import Image
import torch

# Load pipeline
pipeline = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float16,
)
pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda")

# Load image and create mask
image = Image.open("input.jpg").resize((512, 512))
mask = Image.open("mask.png").resize((512, 512))

# Inpaint
result = pipeline(
    prompt="a beautiful garden",
    image=image,
    mask_image=mask,
    num_inference_steps=30,
    guidance_scale=7.5,
)

result.images[0].save("output.png")
```

## Mask Creation

### 1. Rectangle Mask

```python
def create_rectangle_mask(size, bounds):
    """Create rectangular mask [x1, y1, x2, y2]"""
    
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle(bounds, fill=255)
    
    return mask
```

### 2. Circle/Ellipse Mask

```python
def create_circle_mask(size, center, radius):
    """Create circular mask"""
    
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    
    x, y = center
    bbox = [x - radius, y - radius, x + radius, y + radius]
    draw.ellipse(bbox, fill=255)
    
    return mask
```

### 3. Freehand Mask

```python
def create_freehand_mask(size, points):
    """Create freeform polygon mask"""
    
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    
    draw.polygon(points, fill=255)
    
    return mask

# Usage
points = [(100, 100), (200, 100), (200, 200), (100, 200)]
mask = create_freehand_mask((512, 512), points)
```

### 4. Brush Stroke Mask

```python
def create_brush_mask(size, stroke_points, brush_width=20):
    """Create brush stroke mask"""
    
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Draw lines between points
    for i in range(len(stroke_points) - 1):
        draw.line(
            [stroke_points[i], stroke_points[i+1]],
            fill=255,
            width=brush_width
        )
    
    return mask

# Usage
points = [(50, 50), (100, 80), (150, 60), (200, 100)]
mask = create_brush_mask((512, 512), points)
```

### 5. Auto-Detection Mask

```python
def auto_detect_mask(image_path):
    """Automatically detect areas to inpaint"""
    
    import cv2
    
    # Load image
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Create mask
    mask = np.zeros(gray.shape, dtype=np.uint8)
    
    for contour in contours:
        if cv2.contourArea(contour) > 500:  # Filter small areas
            cv2.drawContours(mask, [contour], -1, 255, -1)
    
    # Dilate for better coverage
    kernel = np.ones((10, 10), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    
    return Image.fromarray(mask)
```

### 6. Text/Logo Mask

```python
def create_text_mask(size, text, font_size=60):
    """Create mask from text"""
    
    from PIL import ImageFont
    
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Try to load font, use default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Draw text
    draw.text((size[0]//4, size[1]//2), text, fill=255, font=font)
    
    return mask
```

## Advanced Techniques

### 1. Edge-Aware Inpainting

```python
class EdgeAwareInpainter:
    """Inpaint while preserving edges"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def inpaint_preserve_edges(
        self,
        image,
        mask,
        prompt,
        edge_blur=10
    ):
        """Inpaint with edge preservation"""
        
        # Blur mask edges
        mask_array = np.array(mask)
        mask_blurred = Image.fromarray(
            cv2.GaussianBlur(mask_array, (edge_blur, edge_blur), 0)
        )
        
        # Inpaint
        result = self.pipeline(
            prompt=prompt,
            image=image,
            mask_image=mask_blurred,
        )
        
        return result.images[0]
```

### 2. Multi-Pass Inpainting

```python
class MultiPassInpainter:
    """Inpaint in multiple passes for better quality"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def inpaint_progressive(
        self,
        image,
        mask,
        prompt,
        passes=2
    ):
        """Progressive inpainting"""
        
        current_image = image.copy()
        current_mask = mask.copy()
        
        for p in range(passes):
            # Reduce mask strength
            if p > 0:
                current_mask = self._reduce_mask(current_mask)
            
            # Inpaint
            result = self.pipeline(
                prompt=prompt,
                image=current_image,
                mask_image=current_mask,
            )
            
            current_image = result.images[0]
        
        return current_image
    
    def _reduce_mask(self, mask):
        """Reduce mask area for next pass"""
        
        import cv2
        
        mask_array = np.array(mask)
        kernel = np.ones((5, 5), np.uint8)
        mask_reduced = cv2.erode(mask_array, kernel, iterations=1)
        
        return Image.fromarray(mask_reduced)
```

### 3. Guidance Mask

```python
class GuidanceInpainter:
    """Inpaint with color/intensity guidance"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def inpaint_with_guidance(
        self,
        image,
        mask,
        prompt,
        guidance_image=None,
        guidance_strength=0.5
    ):
        """Inpaint with guidance image"""
        
        # Use img2img + inpaint combination
        from diffusers import StableDiffusionImg2ImgPipeline
        
        # First inpaint
        inpaint_result = self.pipeline(
            prompt=prompt,
            image=image,
            mask_image=mask,
            strength=0.8,
        ).images[0]
        
        # Then enhance with guidance if provided
        if guidance_image:
            img2img = StableDiffusionImg2ImgPipeline.from_pretrained(
                "stabilityai/stable-diffusion-1-5",
                torch_dtype=torch.float16,
            )
            img2img = img2img.to("cuda")
            
            result = img2img(
                prompt=prompt,
                image=inpaint_result,
                strength=guidance_strength,
            ).images[0]
            
            return result
        
        return inpaint_result
```

## Creative Applications

### 1. Object Removal

```python
def remove_object(image_path, mask_bounds, **kwargs):
    """Remove object from image"""
    
    pipeline = load_inpainting_pipeline()
    
    image = Image.open(image_path).resize((512, 512))
    mask = create_rectangle_mask(image.size, mask_bounds)
    
    result = pipeline(
        prompt="smooth background, clean, natural",
        image=image,
        mask_image=mask,
        **kwargs
    )
    
    return result.images[0]
```

### 2. Face Editing

```python
def edit_face(image_path, face_bounds, edit_type="smile", **kwargs):
    """Edit facial features"""
    
    prompts = {
        "smile": "happy smile, cheerful expression, natural smile",
        "older": "older appearance, aged face, wrinkles",
        "younger": "younger appearance, youthful face, smooth skin",
        "glasses": "wearing stylish glasses",
        "makeup": "professional makeup, natural look",
    }
    
    pipeline = load_inpainting_pipeline()
    
    image = Image.open(image_path).resize((512, 512))
    mask = create_ellipse_mask(image.size, face_bounds)
    
    result = pipeline(
        prompt=prompts.get(edit_type, "natural face"),
        image=image,
        mask_image=mask,
        **kwargs
    )
    
    return result.images[0]
```

### 3. Product Placement

```python
def add_product(base_path, product_path, position, product_description, **kwargs):
    """Add product to scene"""
    
    pipeline = load_inpainting_pipeline()
    
    # Load images
    base = Image.open(base_path).resize((512, 512))
    mask = create_rectangle_mask(base.size, position)
    
    prompt = f"realistic {product_description} in scene, proper lighting, natural"
    
    result = pipeline(
        prompt=prompt,
        image=base,
        mask_image=mask,
        **kwargs
    )
    
    return result.images[0]
```

### 4. Scene Extension

```python
def extend_scene(image_path, direction="right", num_passes=2, **kwargs):
    """Extend scene beyond original boundaries"""
    
    outpainter = OutpaintingEditor()
    outpainter.load_model()
    
    return outpainter.extend_panoramic(
        image_path,
        num_extensions=num_passes,
        direction=direction,
        **kwargs
    )
```

## Troubleshooting

### Common Issues

#### 1. Incomplete Fill

```python
# Increase steps and guidance
result = pipeline(
    prompt=prompt,
    image=image,
    mask_image=mask,
    num_inference_steps=50,  # More steps
    guidance_scale=9.0,     # Higher guidance
)
```

#### 2. Visible Edges

```python
# Blur mask edges
mask = mask.filter(ImageFilter.GaussianBlur(10))

# Or use feathered mask
mask = create_feathered_mask(bounds, feather=20)
```

#### 3. Inconsistent Content

```python
# Add more context to prompt
prompt = f"{prompt}, consistent with surrounding, seamless, matching lighting"

# Use lower strength
result = pipeline(
    prompt=prompt,
    image=image,
    mask_image=mask,
    strength=0.7,
)
```

#### 4. Out of Memory

```python
# Enable CPU offload
pipeline.enable_sequential_cpu_offload()

# Or reduce resolution
image = image.resize((384, 384))
mask = mask.resize((384, 384))
```

## Next Steps

- Learn about [ControlNet](./09-controlnet.md) for controlled edits
- Explore [Portrait Generation](./10-portrait-generation.md) for face editing
- Check [Upscaling](./12-upscaling.md) for final enhancement

## Additional Resources

- [Stable Diffusion Inpainting](https://huggingface.co/runwayml/stable-diffusion-inpainting)
- [Inpainting Techniques](https://stable-diffusion-art.com/inpainting/)
