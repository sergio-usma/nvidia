# Video Interpolation on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Interpolation](#understanding-interpolation)
3. [Implementation](#implementation)
4. [Slow Motion Effects](#slow-motion-effects)
5. [Advanced Techniques](#advanced-techniques)
6. [Practical Examples](#practical-examples)

## Introduction

Video interpolation creates new frames between existing ones to produce smooth slow-motion or convert frame rates. This is one of the most practical AI video enhancements for Jetson.

### Applications

- **Slow motion**: Convert 30fps to 120fps
- **Frame rate conversion**: 24fps to 60fps
- **Smooth playback**: Reduce jitter in low-fps video

## Implementation

### Optical Flow Interpolation

```python
#!/usr/bin/env python3
"""
Video Interpolation - Create smooth video
"""

import cv2
import numpy as np
from PIL import Image
import os

class VideoInterpolator:
    """Interpolate video frames for smooth motion"""
    
    def __init__(self):
        pass
    
    def create_slow_motion(
        self,
        input_path,
        output_path,
        speed_factor=4
    ):
        """Create slow motion video"""
        
        # Read video
        cap = cv2.VideoCapture(input_path)
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Output fps
        output_fps = fps * speed_factor
        
        # Create writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, output_fps, (width, height))
        
        prev_frame = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if prev_frame is not None:
                # Interpolate frames
                interpolated = self._interpolate_frames(
                    prev_frame, frame, speed_factor
                )
                
                # Write interpolated frames
                for f in interpolated:
                    writer.write(f)
            
            prev_frame = frame
        
        cap.release()
        writer.release()
        
        return output_path
    
    def _interpolate_frames(self, frame1, frame2, num_interpolated):
        """Interpolate between two frames"""
        
        frames = []
        
        for i in range(1, num_interpolated):
            alpha = i / num_interpolated
            
            # Linear interpolation
            interpolated = cv2.addWeighted(
                frame1, 1 - alpha,
                frame2, alpha,
                0
            )
            
            frames.append(interpolated)
        
        return frames
```

### Advanced Interpolation

```python
class OpticalFlowInterpolator:
    """Optical flow-based interpolation"""
    
    def __init__(self):
        self.fgbg = None
    
    def interpolate_with_flow(
        self,
        frame1,
        frame2,
        num_interpolated
    ):
        """Create smooth interpolated frames"""
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow
        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        
        frames = []
        
        for i in range(1, num_interpolated):
            alpha = i / num_interpolated
            
            # Create warped frame
            h, w = gray1.shape
            y, x = np.mgrid[0:h, 0:w].astype(float)
            
            # Shift by flow
            x_new = x + flow[..., 0] * alpha
            y_new = y + flow[..., 1] * alpha
            
            # Remap
            map_x = x_new.astype(np.float32)
            map_y = y_new.astype(np.float32)
            
            warped = cv2.remap(frame1, map_x, map_y, cv2.INTER_LINEAR)
            
            # Blend
            interpolated = cv2.addWeighted(
                warped, 1 - alpha,
                frame2, alpha,
                0
            )
            
            frames.append(interpolated)
        
        return frames
```

## Slow Motion Effects

### Frame Doubling

```python
def create_smooth_slow_motion(input_path, output_path, factor=2):
    """Create smooth slow motion"""
    
    cap = cv2.VideoCapture(input_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Optical flow interpolator
    interpolator = OpticalFlowInterpolator()
    
    # Output
    output_fps = fps * factor
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, output_fps, (width, height))
    
    prev_frame = None
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if prev_frame is not None:
            # Interpolate
            if factor == 2:
                # Simple blend for 2x
                mid = cv2.addWeighted(prev_frame, 0.5, frame, 0.5, 0)
                writer.write(mid)
            else:
                # Flow-based for higher factors
                interpolated = interpolator.interpolate_with_flow(
                    prev_frame, frame, factor
                )
                for f in interpolated:
                    writer.write(f)
        
        writer.write(frame)
        prev_frame = frame
        frame_count += 1
        
        if frame_count % 30 == 0:
            print(f"Processed {frame_count} frames...")
    
    cap.release()
    writer.release()
    
    return output_path
```

## Practical Examples

### Example: 24fps to 60fps

```python
# Convert 24fps film to 60fps for smooth playback
create_smooth_slow_motion(
    "input.mp4",
    "output_60fps.mp4",
    factor=2  # Creates 48fps, blend to 60
)
```

## Next Steps

- [Video Upscaling](./07-video-upscaling.md) - Enhance resolution
- [Video Editing](./08-video-editing.md) - Edit videos
- [Video Effects](./09-video-effects.md) - Add effects
