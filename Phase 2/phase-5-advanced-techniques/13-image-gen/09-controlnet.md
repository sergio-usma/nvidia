# ControlNet on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding ControlNet](#understanding-controlnet)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [ControlNet Models](#controlnet-models)
8. [Advanced Techniques](#advanced-techniques)
9. [Practical Applications](#practical-applications)
10. [Troubleshooting](#troubleshooting)

## Introduction

ControlNet is a neural network structure to control diffusion models by adding extra conditions. It enables precise control over image generation through various input conditions like:

- Canny edge detection
- Depth maps
- Pose skeletons
- Scribbles
- Segmentation maps
- Normal maps
- Facial landmarks

**Important Note**: ControlNet is computationally demanding. On Jetson AGX Orin 64GB, you may need to use lighter models or optimizations. This guide covers practical deployment strategies.

## Understanding ControlNet

### How ControlNet Works

1. **Conditioning**: Extra input (edge map, pose, etc.) is processed
2. **Feature Injection**: ControlNet features are injected into the UNet
3. **Guided Generation**: The model generates while respecting the condition
4. **Output**: Image that matches both prompt and condition

### Architecture

```
Input Image → Preprocessor → ControlNet → Condition Features
                                                    ↓
Prompt → Text Encoder → Text Features → UNet → Latents → VAE → Output
```

### Jetson Considerations

| ControlNet Type | Memory | Feasibility on Jetson |
|----------------|--------|----------------------|
| Canny | ~5GB | ✅ Possible |
| Depth | ~5GB | ✅ Possible |
| Pose | ~5GB | ✅ Possible |
| Scribble | ~5GB | ✅ Possible |
| Seg | ~6GB | ⚠️ Requires optimization |
| Normal | ~5GB | ✅ Possible |
| Multiple | ~8GB | ⚠️ Challenging |

## Prerequisites

### System Setup

```bash
# Enable maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Configure adequate swap (16GB recommended)
sudo fallocate -l 16G /swapfile
sudo swapon /swapfile
```

### Python Dependencies

```bash
# Install controlnet dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

pip install diffusers transformers accelerate opencv-python
pip install controlnet-aux  # Preprocessors
pip install scipy
```

## Installation

### Install ControlNet Pipeline

```python
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
import torch

# Load ControlNet model
controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/sd-controlnet-canny",
    torch_dtype=torch.float16,
)

# Create pipeline
pipeline = StableDiffusionControlNetPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    controlnet=controlnet,
    torch_dtype=torch.float16,
)

pipeline.enable_attention_slicing()

if torch.cuda.is_available():
    pipeline = pipeline.to("cuda")
```

### Alternative: Using diffusers + controlnet-aux

```python
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
from controlnet_aux import CannyDetector, DepthDetector, OpenposeDetector

# Initialize preprocessors
canny = CannyDetector()
depth = DepthDetector()
openpose = OpenposeDetector()
```

## Configuration

### Recommended Settings for Jetson

```python
CONTROLNET_CONFIG = {
    "base_model": "runwayml/stable-diffusion-v1-5",
    
    # ControlNet models (choose based on need)
    "controlnet_models": {
        "canny": "lllyasviel/sd-controlnet-canny",
        "depth": "lllyasviel/sd-controlnet-depth",
        "pose": "lllyasviel/sd-controlnet-openpose",
        "scribble": "lllyasviel/sd-controlnet-scribble",
        "seg": "lllyasviel/sd-controlnet-seg",
        "normal": "lllyasviel/sd-controlnet-normal",
    },
    
    "generation": {
        "steps": 30,
        "guidance": 7.5,
        "controlnet_scale": 1.0,
        "controlnet_conditioning_scale": 1.0,
    },
    
    "optimization": {
        "attention_slicing": True,
        "vae_slicing": True,
        "enable_sequential_cpu_offload": False,
    },
}
```

## Basic Usage

### Canny Edge Control

```python
#!/usr/bin/env python3
"""
ControlNet on Jetson AGX Orin
Controlled image generation with various conditions
"""

import torch
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
from PIL import Image, ImageFilter
import numpy as np
import cv2
import os
import time

class ControlNetGenerator:
    """ControlNet generation on Jetson"""
    
    def __init__(self, controlnet_model="lllyasviel/sd-controlnet-canny"):
        self.controlnet_model = controlnet_model
        self.pipeline = None
        self.controlnet = None
        
    def load_model(self, base_model="runwayml/stable-diffusion-v1-5"):
        """Load ControlNet pipeline"""
        
        print(f"Loading ControlNet: {self.controlnet_model}")
        
        # Load ControlNet
        self.controlnet = ControlNetModel.from_pretrained(
            self.controlnet_model,
            torch_dtype=torch.float16,
        )
        
        # Create pipeline
        self.pipeline = StableDiffusionControlNetPipeline.from_pretrained(
            base_model,
            controlnet=self.controlnet,
            torch_dtype=torch.float16,
        )
        
        # Enable optimizations
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
            print("ControlNet loaded on CUDA")
        
        print("ControlNet model loaded!")
        return self.pipeline
    
    def preprocess_canny(self, image_path, low_threshold=100, high_threshold=200):
        """Generate canny edge map"""
        
        # Load image
        image = cv2.imread(image_path)
        image = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, low_threshold, high_threshold)
        
        # Convert to RGB (stack 3 times)
        edges_rgb = np.stack([edges] * 3, axis=-1)
        
        return Image.fromarray(edges_rgb)
    
    def preprocess_depth(self, image_path):
        """Generate depth map"""
        
        from controlnet_aux import DepthDetector
        
        # Initialize detector
        detector = DepthDetector.from_pretrained(
            "lllyasviel/control_v11f1e_sd21_tile"
        )
        
        # Load image
        image = Image.open(image_path)
        
        # Get depth map
        depth_map = detector(image)
        
        return depth_map
    
    def preprocess_pose(self, image_path):
        """Generate pose keypoints"""
        
        from controlnet_aux import OpenposeDetector
        
        # Initialize detector
        detector = OpenposeDetector.from_pretrained(
            "lllyasviel/control_v11p_sd15_openpose"
        )
        
        # Load image
        image = Image.open(image_path)
        
        # Get pose
        pose = detector(image)
        
        return pose
    
    def preprocess_scribble(self, image_path):
        """Generate scribble map from sketch"""
        
        # Load image
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Apply strong blur and threshold
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        _, scribble = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)
        
        # Dilate to connect lines
        kernel = np.ones((5, 5), np.uint8)
        scribble = cv2.dilate(scribble, kernel, iterations=2)
        
        # Convert to RGB
        scribble_rgb = np.stack([scribble] * 3, axis=-1)
        
        return Image.fromarray(scribble_rgb)
    
    def generate(
        self,
        control_image,
        prompt,
        negative_prompt=None,
        num_inference_steps=30,
        guidance_scale=7.5,
        controlnet_scale=1.0,
        seed=None
    ):
        """Generate with ControlNet conditioning"""
        
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
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator.manual_seed(seed)
        
        # Generate
        start_time = time.time()
        
        with torch.inference_mode():
            result = self.pipeline(
                prompt=prompt,
                image=control_image,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                controlnet_conditioning_scale=controlnet_scale,
                generator=generator,
            )
        
        elapsed = time.time() - start_time
        print(f"Generation completed in {elapsed:.2f}s")
        
        return result.images[0]
    
    def generate_from_image(
        self,
        image_path,
        prompt,
        control_type="canny",
        **kwargs
    ):
        """Generate ControlNet image from input"""
        
        # Generate control map based on type
        if control_type == "canny":
            control_image = self.preprocess_canny(image_path)
        elif control_type == "depth":
            control_image = self.preprocess_depth(image_path)
        elif control_type == "pose":
            control_image = self.preprocess_pose(image_path)
        elif control_type == "scribble":
            control_image = self.preprocess_scribble(image_path)
        else:
            raise ValueError(f"Unknown control type: {control_type}")
        
        # Generate
        return self.generate(control_image, prompt, **kwargs)


def main():
    """Demo of ControlNet capabilities"""
    
    # Initialize with Canny ControlNet
    generator = ControlNetGenerator("lllyasviel/sd-controlnet-canny")
    generator.load_model()
    
    # Create output directory
    os.makedirs("./output/controlnet", exist_ok=True)
    
    # Example: Generate from edge map
    # Note: Provide your own input image
    # input_path = "./input/photo.jpg"
    # if os.path.exists(input_path):
    #     result = generator.generate_from_image(
    #         input_path,
    #         prompt="a beautiful landscape with mountains",
    #         control_type="canny",
    #         seed=42
    #     )
    #     result.save("./output/controlnet/canny_result.png")
    
    print("ControlNet demo complete!")
    print("Add input images to test ControlNet features")


if __name__ == "__main__":
    main()
```

### Quick Start: Canny Edge Control

```python
# Quick Canny edge ControlNet
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
from PIL import Image
import cv2
import torch

# Load model
controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/sd-controlnet-canny",
    torch_dtype=torch.float16,
)

pipeline = StableDiffusionControlNetPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    controlnet=controlnet,
    torch_dtype=torch.float16,
)
pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda")

# Create canny edge map
image = cv2.imread("input.jpg")
edges = cv2.Canny(image, 100, 200)
edges_rgb = Image.fromarray(np.stack([edges]*3, axis=-1))

# Generate
result = pipeline(
    prompt="a beautiful landscape",
    image=edges_rgb,
    num_inference_steps=30,
).images[0]

result.save("output.png")
```

## ControlNet Models

### Available ControlNet Types

| Model | Control Type | Use Case | Memory |
|-------|--------------|----------|--------|
| Canny | Edge detection | Structure preservation | 5GB |
| Depth | Depth map | 3D structure | 5GB |
| OpenPose | Skeleton | Pose transfer | 5GB |
| Scribble | Hand-drawn | Sketch to image | 5GB |
| Seg | Segmentation | Semantic control | 6GB |
| Normal | Normal map | Surface normals | 5GB |
| Inpaint | Inpainting mask | Targeted editing | 5GB |

### Loading Different ControlNet Models

```python
# Depth ControlNet
controlnet_depth = ControlNetModel.from_pretrained(
    "lllyasviel/sd-controlnet-depth",
    torch_dtype=torch.float16,
)

# Pose ControlNet
controlnet_pose = ControlNetModel.from_pretrained(
    "lllyasviel/sd-controlnet-openpose",
    torch_dtype=torch.float16,
)

# Scribble ControlNet
controlnet_scribble = ControlNetModel.from_pretrained(
    "lllyasviel/sd-controlnet-scribble",
    torch_dtype=torch.float16,
)
```

### Multi-ControlNet

```python
# Using multiple ControlNets together
from diffusers import MultiControlNetModel

# Load multiple ControlNets
controlnets = [
    ControlNetModel.from_pretrained("lllyasviel/sd-controlnet-canny"),
    ControlNetModel.from_pretrained("lllyasviel/sd-controlnet-depth"),
]

# Create multi-control pipeline
controlnet = MultiControlNetModel(controlnets)

pipeline = StableDiffusionControlNetPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    controlnet=controlnet,
    torch_dtype=torch.float16,
)

# Generate with multiple conditions
result = pipeline(
    prompt="your prompt",
    image=[canny_image, depth_image],
    num_inference_steps=30,
)
```

## Advanced Techniques

### 1. ControlNet with Inpainting

```python
class ControlNetInpainter:
    """Combine ControlNet with inpainting"""
    
    def __init__(self, base_model, controlnet_model):
        from diffusers import StableDiffusionControlNetInpaintPipeline
        
        controlnet = ControlNetModel.from_pretrained(controlnet_model)
        
        self.pipeline = StableDiffusionControlNetInpaintPipeline.from_pretrained(
            base_model,
            controlnet=controlnet,
            torch_dtype=torch.float16,
        )
        
        self.pipeline.enable_attention_slicing()
        self.pipeline = self.pipeline.to("cuda")
    
    def inpaint_with_control(
        self,
        image,
        mask,
        control_image,
        prompt,
        **kwargs
    ):
        """Inpaint with ControlNet guidance"""
        
        result = self.pipeline(
            prompt=prompt,
            image=image,
            mask_image=mask,
            control_image=control_image,
            **kwargs
        )
        
        return result.images[0]
```

### 2. ControlNet with Reference Image

```python
class ControlNetReference:
    """Use reference image for style/content"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate_with_reference(
        self,
        control_image,
        reference_image,
        prompt,
        style_strength=0.5,
        **kwargs
    ):
        """Generate with reference image influence"""
        
        # Prepare reference (could be pose, depth, etc.)
        # This is a simplified version
        
        result = self.pipeline(
            prompt=prompt,
            image=control_image,
            num_inference_steps=30,
            guidance_scale=7.5,
            **kwargs
        )
        
        return result.images[0]
```

### 3. Weighted Control

```python
def generate_weighted_control(
    pipeline,
    prompt,
    control_images,
    weights,
    **kwargs
):
    """Apply weighted combination of controls"""
    
    if len(control_images) != len(weights):
        raise ValueError("Number of controls must match weights")
    
    # Normalize weights
    total = sum(weights)
    weights = [w/total for w in weights]
    
    # Generate
    result = pipeline(
        prompt=prompt,
        image=control_images[0],  # Use first as main
        num_inference_steps=kwargs.get("num_inference_steps", 30),
    )
    
    return result.images[0]
```

### 4. Progressive Control

```python
class ProgressiveControl:
    """Apply control progressively"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate_progressive(
        self,
        prompt,
        control_image,
        start_scale=0.0,
        end_scale=1.0,
        steps=10
    ):
        """Progressively increase control influence"""
        
        results = []
        
        for i in range(steps):
            scale = start_scale + (end_scale - start_scale) * (i / (steps - 1))
            
            result = self.pipeline(
                prompt=prompt,
                image=control_image,
                controlnet_conditioning_scale=scale,
                num_inference_steps=20,
            ).images[0]
            
            results.append(result)
        
        return results
```

## Practical Applications

### 1. Architecture Rendering

```python
def architecture_control(image_path, style="modern building", **kwargs):
    """Generate architectural render from sketch"""
    
    # Load ControlNet
    generator = ControlNetGenerator("lllyasviel/sd-controlnet-scribble")
    generator.load_model()
    
    # Generate
    return generator.generate_from_image(
        image_path,
        prompt=f"{style}, architectural rendering, detailed, professional",
        control_type="scribble",
        **kwargs
    )
```

### 2. Pose Transfer

```python
def pose_to_image(pose_image_path, character_description, **kwargs):
    """Generate character from pose"""
    
    generator = ControlNetGenerator("lllyasviel/sd-controlnet-openpose")
    generator.load_model()
    
    return generator.generate_from_image(
        pose_image_path,
        prompt=f"detailed character, {character_description}, high quality",
        control_type="pose",
        **kwargs
    )
```

### 3. Depth-to-3D Scene

```python
def depth_to_scene(depth_image_path, scene_description, **kwargs):
    """Generate scene from depth map"""
    
    generator = ControlNetGenerator("lllyasviel/sd-controlnet-depth")
    generator.load_model()
    
    return generator.generate_from_image(
        depth_image_path,
        prompt=f"beautiful {scene_description}, realistic, detailed",
        control_type="depth",
        **kwargs
    )
```

### 4. Sketch-to-Image

```python
def sketch_to_art(sketch_path, art_style="detailed illustration", **kwargs):
    """Convert sketch to detailed artwork"""
    
    generator = ControlNetGenerator("lllyasviel/sd-controlnet-scribble")
    generator.load_model()
    
    return generator.generate_from_image(
        sketch_path,
        prompt=f"{art_style}, professional, high quality",
        control_type="scribble",
        **kwargs
    )
```

### 5. Product Visualization

```python
def product_visualize(product_image_path, scene_description, **kwargs):
    """Generate product in scene"""
    
    # Use Canny for product outline
    generator = ControlNetGenerator("lllyasviel/sd-controlnet-canny")
    generator.load_model()
    
    return generator.generate_from_image(
        product_image_path,
        prompt=f"product photography, {scene_description}, professional",
        control_type="canny",
        **kwargs
    )
```

## Troubleshooting

### Common Issues

#### 1. Out of Memory

```python
# Solution 1: Enable CPU offload
pipeline.enable_sequential_cpu_offload()

# Solution 2: Use smaller base model
pipeline = StableDiffusionControlNetPipeline.from_pretrained(
    "stabilityai/stable-diffusion-1-5",  # Smaller than v1-5
    controlnet=controlnet,
    torch_dtype=torch.float16,
)

# Solution 3: Reduce resolution
image = image.resize((384, 384))
```

#### 2. Control Not Strong Enough

```python
# Increase controlnet scale
result = pipeline(
    prompt=prompt,
    image=control_image,
    controlnet_conditioning_scale=1.5,  # Stronger control
)
```

#### 3. Poor Quality Output

```python
# Increase steps and guidance
result = pipeline(
    prompt=prompt,
    image=control_image,
    num_inference_steps=50,  # More steps
    guidance_scale=8.0,       # Higher guidance
)
```

#### 4. Preprocessing Issues

```python
# For Canny - adjust thresholds
edges = cv2.Canny(gray, 50, 150)  # Lower = more edges

# For scribble - adjust threshold
_, scribble = cv2.threshold(blurred, 150, 255, cv2.THRESH_BINARY)  # Lower = more lines
```

### Performance Tips

```bash
# Monitor memory usage
python -c "import torch; print(torch.cuda.max_memory_allocated() / 1024**3, 'GB')"

# Check GPU stats
tegrastats --interval 1000
```

### Alternative: Lighter ControlNet

For Jetson, consider using T2I-Adapter which is lighter:

```python
# T2I-Adapter (lighter alternative)
from diffusers import T2IAdapter
from adapters import T2IAdapterRunner
```

## Next Steps

- Explore [Portrait Generation](./10-portrait-generation.md) for face control
- Learn about [Style Transfer](./11-style-transfer.md) for artistic control
- Check [Upscaling](./12-upscaling.md) for resolution enhancement

## Additional Resources

- [ControlNet Official](https://github.com/lllyasviel/ControlNet)
- [HuggingFace ControlNet](https://huggingface.co/lllyasviel)
- [ControlNet Preprocessors](https://github.com/lllyasviel/controlnet_aux)
