# Video Editing on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Editing](#basic-editing)
3. [Trimming and Cutting](#trimming-and-cutting)
4. [Merging Videos](#merging-videos)
5. [Adding Transitions](#adding-transitions)

## Introduction

Video editing on Jetson using OpenCV and MoviePy for trimming, merging, transitions, and more.

## Basic Editing

```python
#!/usr/bin/env python3
"""
Video Editing
"""

import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips
import os

class VideoEditor:
    """Video editing operations"""
    
    def __init__(self):
        pass
    
    def trim_video(self, input_path, output_path, start=0, end=None):
        """Trim video"""
        
        clip = VideoFileClip(input_path)
        
        if end:
            clip = clip.subclip(start, end)
        else:
            clip = clip.subclip(start)
        
        clip.write_videofile(output_path, codec='libx264')
        
        return output_path
    
    def merge_videos(self, input_paths, output_path):
        """Merge multiple videos"""
        
        clips = [VideoFileClip(p) for p in input_paths]
        final = concatenate_videoclips(clips)
        
        final.write_videofile(output_path, codec='libx264')
        
        return output_path
    
    def add_fade(self, input_path, output_path, duration=1):
        """Add fade in/out"""
        
        clip = VideoFileClip(input_path)
        clip = clip.fadein(duration).fadeout(duration)
        
        clip.write_videofile(output_path, codec='libx264')
        
        return output_path
```

## Next Steps

- [Video Effects](./09-video-effects.md) - Visual effects
- [Batch Video](./10-batch-video.md) - Process multiple
- [Video Analysis](./11-video-analysis.md) - Analyze videos
