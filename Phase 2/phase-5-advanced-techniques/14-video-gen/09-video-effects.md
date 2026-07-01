# Video Effects on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Effects](#basic-effects)
3. [Filters](#filters)
4. [AI Effects](#ai-effects)

## Introduction

Add visual effects to videos including filters, color grading, blur, and AI-powered effects.

## Basic Effects

```python
#!/usr/bin/env python3
"""
Video Effects
"""

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

class VideoEffects:
    """Apply effects to video frames"""
    
    def __init__(self):
        pass
    
    def apply_blur(self, frame, kernel_size=15):
        """Apply blur"""
        return cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
    
    def apply_sharpen(self, frame):
        """Apply sharpen"""
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        return cv2.filter2D(frame, -1, kernel)
    
    def apply_edge_detection(self, frame):
        """Apply edge detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    def apply_sepia(self, frame):
        """Apply sepia tone"""
        kernel = np.array([
            [0.272, 0.534, 0.131],
            [0.349, 0.686, 0.168],
            [0.393, 0.769, 0.189]
        ])
        return cv2.transform(frame, kernel)
    
    def adjust_brightness(self, frame, factor=1.5):
        """Adjust brightness"""
        return cv2.convertScaleAbs(frame, alpha=factor, beta=0)
    
    def adjust_contrast(self, frame, factor=1.5):
        """Adjust contrast"""
        return cv2.convertScaleAbs(frame, alpha=factor, beta=0)
    
    def apply_vignette(self, frame, intensity=0.5):
        """Apply vignette effect"""
        rows, cols = frame.shape[:2]
        kernel_x = cv2.getGaussianKernel(cols, cols/2)
        kernel_y = cv2.getGaussianKernel(rows, rows/2)
        kernel = kernel_y * kernel_x.T
        mask = kernel / kernel.max()
        
        vignette = frame * mask[:, :, np.newaxis] * intensity
        return vignette.astype(np.uint8)
```

## Filters

```python
def apply_filter(frame, filter_name):
    """Apply named filter"""
    
    effects = {
        'blur': lambda f: cv2.GaussianBlur(f, (15, 15), 0),
        'sharpen': lambda f: VideoEffects().apply_sharpen(f),
        'edge': lambda f: VideoEffects().apply_edge_detection(f),
        'sepia': lambda f: VideoEffects().apply_sepia(f),
        'vignette': lambda f: VideoEffects().apply_vignette(f),
        'grayscale': lambda f: cv2.cvtColor(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR),
        'invert': lambda f: cv2.bitwise_not(f),
    }
    
    return effects.get(filter_name, lambda f: f)(frame)
```

## AI Effects

```python
def apply_ai_style(frame, pipeline):
    """Apply AI style transfer to frame"""
    
    pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    styled = pipeline(
        prompt="artistic style, painting, vibrant colors",
        image=pil_frame,
        strength=0.5,
        num_inference_steps=10,
    ).images[0]
    
    return cv2.cvtColor(np.array(styled), cv2.COLOR_RGB2BGR)
```

## Next Steps

- [Batch Video](./10-batch-video.md) - Process multiple
- [Video Analysis](./11-video-analysis.md) - Analyze
- [Optimization](./12-optimization.md) - Tune performance
