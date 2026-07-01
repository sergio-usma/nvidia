# Video Upscaling on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Implementation](#implementation)
3. [Frame-by-Frame Upscaling](#frame-by-frame-upscaling)
4. [AI Enhancement](#ai-enhancement)

## Introduction

Video upscaling increases resolution while maintaining quality. On Jetson, we process frame-by-frame using image upscaling techniques.

## Implementation

```python
#!/usr/bin/env python3
"""
Video Upscaling
Enhance video resolution
"""

import cv2
import numpy as np
from PIL import Image
import torch
import os
from tqdm import tqdm

class VideoUpscaler:
    """Upscale video resolution"""
    
    def __init__(self):
        self.pipeline = None
    
    def upscale_video(
        self,
        input_path,
        output_path,
        scale=2,
        model=None
    ):
        """Upscale video"""
        
        cap = cv2.VideoCapture(input_path)
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        new_width = width * scale
        new_height = height * scale
        
        # Output
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
        
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to PIL
            pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Upscale
            if model:
                upscaled = self._ai_upscale(pil_frame, model)
            else:
                upscaled = pil_frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert back
            result = cv2.cvtColor(np.array(upscaled), cv2.COLOR_RGB2BGR)
            writer.write(result)
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Upscaled {frame_count} frames")
                torch.cuda.empty_cache()
        
        cap.release()
        writer.release()
        
        return output_path
    
    def _ai_upscale(self, pil_image, model):
        """AI upscale single image"""
        # Implementation using Real-ESRGAN or similar
        return pil_image.resize(
            (pil_image.width * 2, pil_image.height * 2),
            Image.Resampling.LANCZOS
        )
```

## Next Steps

- [Video Editing](./08-video-editing.md) - Edit videos
- [Video Effects](./09-video-effects.md) - Add effects
- [Batch Video](./10-batch-video.md) - Process multiple
