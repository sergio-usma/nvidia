# Image-to-Video Animation on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Image Animation](#understanding-image-animation)
3. [Prerequisites](#prerequisites)
4. [Implementation](#implementation)
5. [Animation Techniques](#animation-techniques)
6. [Advanced Effects](#advanced-effects)
7. [Practical Examples](#practical-examples)

## Introduction

Image-to-video animation transforms static images into dynamic videos using AI. This is more practical on Jetson than full video generation, offering smooth motion effects at lower computational cost.

### Advantages

- **Efficient**: Only requires image generation once as base
- **Smooth**: Optical flow ensures coherent motion
- **Fast**: Much quicker than frame-by-frame generation
- **Control**: Precise control over motion type

## Understanding Image Animation

### Methods

| Method | Description | Quality | Speed |
|--------|-------------|---------|-------|
| Pan/Zoom | Simple transforms | Good | Fast |
| Warp | Grid-based deformation | Medium | Fast |
| Flow | Optical flow based | Excellent | Medium |
| AI | Diffusion-based | Best | Slow |

## Implementation

### Basic Image Animation

```python
#!/usr/bin/env python3
"""
Image-to-Video Animation
Transform static images into videos
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os
import torch

class ImageAnimator:
    """Animate static images into videos"""
    
    def __init__(self):
        self.pipeline = None
    
    def load_diffusion(self):
        """Load diffusion model for enhancement"""
        from diffusers import StableDiffusionImg2ImgPipeline
        
        self.pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
            "stabilityai/stable-diffusion-1-5",
            torch_dtype=torch.float16,
        )
        self.pipeline.enable_attention_slicing()
        self.pipeline = self.pipeline.to("cuda")
        
        return self.pipeline
    
    def animate_zoom(
        self,
        image_path,
        output_path,
        zoom_factor=1.1,
        duration=3,
        fps=24,
        direction='out'
    ):
        """Create zoom in/out animation"""
        
        # Load image
        img = Image.open(image_path)
        width, height = img.size
        
        # Calculate frames
        num_frames = duration * fps
        
        frames = []
        
        for i in range(num_frames):
            # Calculate zoom progress
            progress = i / num_frames
            
            if direction == 'out':
                scale = 1.0 + (zoom_factor - 1.0) * progress
            else:  # in
                scale = zoom_factor - (zoom_factor - 1.0) * progress
            
            # Calculate new dimensions
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Resize
            zoomed = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop back to original size (center)
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            cropped = zoomed.crop((left, top, left + width, top + height))
            
            frames.append(np.array(cropped))
        
        # Write video
        self._frames_to_video(frames, output_path, fps)
        
        return output_path
    
    def animate_pan(
        self,
        image_path,
        output_path,
        direction='left',
        duration=3,
        fps=24
    ):
        """Create pan animation"""
        
        img = Image.open(image_path)
        width, height = img.size
        
        num_frames = duration * fps
        frames = []
        
        # Calculate step
        step = width // num_frames if direction in ['left', 'right'] else height // num_frames
        
        for i in range(num_frames):
            if direction == 'left':
                offset = int(i * step)
                cropped = img.crop((offset, 0, width, height))
            elif direction == 'right':
                offset = int(i * step)
                cropped = img.crop((0, 0, width - offset, height))
            elif direction == 'up':
                offset = int(i * step)
                cropped = img.crop((0, offset, width, height))
            else:  # down
                offset = int(i * step)
                cropped = img.crop((0, 0, width, height - offset))
            
            # Resize to maintain size
            cropped = cropped.resize((width, height), Image.Resampling.LANCZOS)
            frames.append(np.array(cropped))
        
        self._frames_to_video(frames, output_path, fps)
        
        return output_path
    
    def _frames_to_video(self, frames, output_path, fps):
        """Save frames as video"""
        
        height, width = frames[0].shape[:2]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for frame in frames:
            if frame.shape[2] == 4:  # RGBA
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            writer.write(frame)
        
        writer.release()
```

### AI-Enhanced Animation

```python
class AIImageAnimator:
    """AI-powered image animation"""
    
    def __init__(self):
        self.pipeline = None
    
    def load_model(self):
        """Load animation model"""
        
        from diffusers import StableDiffusionImg2ImgPipeline
        
        self.pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
            "stabilityai/stable-diffusion-1-5",
            torch_dtype=torch.float16,
        )
        self.pipeline.enable_attention_slicing()
        self.pipeline = self.pipeline.to("cuda")
        
        return self.pipeline
    
    def animate_with_ai(
        self,
        base_image_path,
        output_path,
        num_frames=48,
        fps=24,
        prompt="",
        strength_range=(0.3, 0.6)
    ):
        """Create animation with AI enhancement"""
        
        # Load base image
        base_img = Image.open(base_image_path).convert('RGB')
        base_img = base_img.resize((512, 512))
        
        frames = []
        
        for i in range(num_frames):
            # Calculate strength (increasing)
            strength = strength_range[0] + (strength_range[1] - strength_range[0]) * (i / num_frames)
            
            # Generate enhanced frame
            enhanced = self.pipeline(
                prompt=prompt,
                image=base_img,
                strength=strength,
                num_inference_steps=15,
                guidance_scale=7.0,
            ).images[0]
            
            # Resize to original
            enhanced = enhanced.resize(base_img.size)
            frames.append(np.array(enhanced))
            
            # Progress
            if i % 10 == 0:
                print(f"Generated {i}/{num_frames} frames")
                torch.cuda.empty_cache()
        
        # Create video
        self._frames_to_video(frames, output_path, fps)
        
        return output_path
    
    def _frames_to_video(self, frames, output_path, fps):
        """Save frames as video"""
        
        height, width = frames[0].shape[:2]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for frame in frames:
            writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        
        writer.release()
```

## Animation Techniques

### 1. Ken Burns Effect

```python
class KenBurnsAnimator:
    """Classic Ken Burns zoom/pan effect"""
    
    def __init__(self):
        pass
    
    def apply(
        self,
        image_path,
        output_path,
        duration=5,
        fps=24,
        zoom_start=1.0,
        zoom_end=1.3,
        pan_start=(0, 0),
        pan_end=(50, 30)
    ):
        """Apply Ken Burns effect"""
        
        img = Image.open(image_path)
        width, height = img.size
        
        num_frames = duration * fps
        frames = []
        
        for i in range(num_frames):
            progress = i / num_frames
            
            # Interpolate zoom
            zoom = zoom_start + (zoom_end - zoom_start) * progress
            
            # Interpolate pan
            pan_x = pan_start[0] + (pan_end[0] - pan_start[0]) * progress
            pan_y = pan_start[1] + (pan_end[1] - pan_start[1]) * progress
            
            # Apply transformations
            frame = self._transform_frame(
                img, width, height, zoom, pan_x, pan_y
            )
            
            frames.append(frame)
        
        # Save video
        self._save_video(frames, output_path, fps)
        
        return output_path
    
    def _transform_frame(self, img, width, height, zoom, pan_x, pan_y):
        """Apply zoom and pan to frame"""
        
        # Scale
        new_width = int(width * zoom)
        new_height = int(height * zoom)
        
        scaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop with pan
        left = int(pan_x)
        top = int(pan_y)
        
        cropped = scaled.crop((
            left, top,
            left + width, top + height
        ))
        
        return np.array(cropped)
    
    def _save_video(self, frames, output_path, fps):
        """Save frames as video"""
        
        height, width = frames[0].shape[:2]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for frame in frames:
            writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        
        writer.release()
```

### 2. Rotation Animation

```python
def animate_rotation(
    image_path,
    output_path,
    angle_range=(-15, 15),
    duration=3,
    fps=24
):
    """Create rotation animation"""
    
    img = Image.open(image_path)
    width, height = img.size
    center = (width // 2, height // 2)
    
    num_frames = duration * fps
    frames = []
    
    for i in range(num_frames):
        progress = i / num_frames
        
        # Calculate angle
        angle = angle_range[0] + (angle_range[1] - angle_range[0]) * progress
        
        # Rotate
        rotated = img.rotate(angle, center=center, resample=Image.Resampling.BICUBIC)
        
        frames.append(np.array(rotated))
    
    # Save
    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    writer.release()
    
    return output_path
```

### 3. Color Animation

```python
def animate_colors(
    image_path,
    output_path,
    duration=5,
    fps=24
):
    """Animate colors - shift hue over time"""
    
    img = Image.open(image_path).convert('HSV')
    width, height = img.size
    
    num_frames = duration * fps
    frames = []
    
    for i in range(num_frames):
        # Shift hue
        hue_shift = int((i / num_frames) * 180) % 256
        
        # Create shifted image
        h, s, v = img.split()
        h = Image.fromarray((np.array(h) + hue_shift) % 256)
        shifted = Image.merge('HSV', (h, s, v)).convert('RGB')
        
        frames.append(np.array(shifted))
    
    # Save
    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    writer.release()
    
    return output_path
```

## Advanced Effects

### 1. Particle Effects

```python
def add_particle_effect(
    frames,
    num_particles=50,
    particle_color=(255, 255, 255)
):
    """Add floating particles to frames"""
    
    height, width = frames[0].shape[:2]
    
    # Initialize particles
    particles = np.random.rand(num_particles, 2)
    particles[:, 0] *= width
    particles[:, 1] *= height
    
    velocities = np.random.rand(num_particles, 2) - 0.5
    velocities *= 2
    
    result_frames = []
    
    for frame in frames:
        frame = frame.copy()
        
        # Update particles
        particles += velocities
        
        # Wrap around edges
        particles[:, 0] = particles[:, 0] % width
        particles[:, 1] = particles[:, 1] % height
        
        # Draw particles
        for px, py in particles:
            x, y = int(px), int(py)
            if 0 <= x < width and 0 <= y < height:
                frame[y, x] = particle_color
        
        result_frames.append(frame)
    
    return result_frames
```

### 2. Light Rays

```python
def add_light_rays(
    image_path,
    output_path,
    duration=5,
    fps=24,
    ray_color=(255, 255, 200)
):
    """Add animated light rays"""
    
    img = Image.open(image_path)
    width, height = img.size
    
    num_frames = duration * fps
    frames = []
    
    for i in range(num_frames):
        progress = i / num_frames
        
        # Create gradient
        angle = progress * 2 * np.pi
        gradient = np.zeros((height, width), dtype=np.float32)
        
        for y in range(height):
            for x in range(width):
                dx = x - width // 2
                dy = y - height // 2
                ray = np.sin(np.arctan2(dy, dx) + angle)
                gradient[y, x] = (ray + 1) / 2
        
        # Normalize
        gradient = (gradient * 255).astype(np.uint8)
        
        # Apply to image
        img_array = np.array(img)
        mask = np.stack([gradient] * 3, axis=2) / 255.0
        
        # Blend
        blended = (img_array * 0.7 + np.array(ray_color) * mask * 0.3).astype(np.uint8)
        
        frames.append(blended)
    
    # Save
    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    writer.release()
    
    return output_path
```

## Practical Examples

### Example 1: Product Showcase

```python
def create_product_showcase(
    product_image_path,
    output_path
):
    """Create animated product showcase"""
    
    animator = KenBurnsAnimator()
    
    # Multiple animations
    temp_files = []
    
    # Zoom in
    out1 = "/tmp/showcase1.mp4"
    animator.apply(
        product_image_path,
        out1,
        duration=3,
        zoom_start=1.0,
        zoom_end=1.5
    )
    temp_files.append(out1)
    
    # Zoom out
    out2 = "/tmp/showcase2.mp4"
    animator.apply(
        product_image_path,
        out2,
        duration=3,
        zoom_start=1.5,
        zoom_end=1.0
    )
    temp_files.append(out2)
    
    # Combine videos
    combine_videos(temp_files, output_path)
    
    # Cleanup
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)
    
    return output_path
```

### Example 2: Photo Gallery Slideshow

```python
def create_slideshow(
    image_paths,
    output_path,
    duration_per_image=3,
    transition_duration=1,
    fps=24
):
    """Create photo slideshow with transitions"""
    
    all_frames = []
    
    for img_path in image_paths:
        img = Image.open(img_path)
        img = img.resize((1920, 1080))
        
        num_static = int((duration_per_image - transition_duration) * fps)
        
        # Add static frames
        for _ in range(num_static):
            all_frames.append(np.array(img))
        
        # Add transition (crossfade with next)
        if img_path != image_paths[-1]:
            next_img = Image.open(image_paths[image_paths.index(img_path) + 1])
            next_img = next_img.resize((1920, 1080))
            
            for i in range(int(transition_duration * fps)):
                alpha = i / (transition_duration * fps)
                
                current = np.array(img)
                next_frame = np.array(next_img)
                
                blended = (current * (1 - alpha) + next_frame * alpha).astype(np.uint8)
                all_frames.append(blended)
    
    # Save
    height, width = all_frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in all_frames:
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    writer.release()
    
    return output_path
```

## Next Steps

- [Video Interpolation](./06-video-interpolation.md) - Create smooth slow-motion
- [Video Upscaling](./07-video-upscaling.md) - Enhance resolution
- [Video Effects](./09-video-effects.md) - Add visual effects
