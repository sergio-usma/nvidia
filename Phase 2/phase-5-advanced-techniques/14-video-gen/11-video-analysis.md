# Video Analysis on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Analysis](#basic-analysis)
3. [Motion Detection](#motion-detection)
4. [Statistics](#statistics)

## Introduction

Basic video analysis including frame statistics, motion detection, and video metadata.

## Basic Analysis

```python
#!/usr/bin/env python3
"""
Video Analysis
"""

import cv2
import numpy as np
from collections import defaultdict

class VideoAnalyzer:
    """Analyze video content"""
    
    def __init__(self):
        pass
    
    def get_info(self, video_path):
        """Get video information"""
        
        cap = cv2.VideoCapture(video_path)
        
        info = {
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS),
            'codec': int(cap.get(cv2.CAP_PROP_FOURCC)),
        }
        
        cap.release()
        
        return info
    
    def analyze_frames(self, video_path, sample_rate=30):
        """Analyze frame statistics"""
        
        cap = cv2.VideoCapture(video_path)
        
        stats = {
            'brightness': [],
            'contrast': [],
            'motion': [],
        }
        
        prev_frame = None
        frame_num = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_num % sample_rate == 0:
                # Brightness
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                stats['brightness'].append(gray.mean())
                
                # Contrast (std dev)
                stats['contrast'].append(gray.std())
                
                # Motion
                if prev_frame is not None:
                    diff = cv2.absdiff(gray, prev_frame)
                    stats['motion'].append(diff.mean())
                
                prev_frame = gray
            
            frame_num += 1
        
        cap.release()
        
        # Summary
        summary = {
            'avg_brightness': np.mean(stats['brightness']),
            'avg_contrast': np.mean(stats['contrast']),
            'avg_motion': np.mean(stats['motion']),
            'max_motion': np.max(stats['motion']),
        }
        
        return summary
```

## Motion Detection

```python
def detect_motion(video_path, threshold=25):
    """Detect motion in video"""
    
    cap = cv2.VideoCapture(video_path)
    
    ret, frame1 = cap.read()
    frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    frame1 = cv2.GaussianBlur(frame1, (21, 21), 0)
    
    motion_frames = []
    
    while True:
        ret, frame2 = cap.read()
        if not ret:
            break
        
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        frame2 = cv2.GaussianBlur(frame2, (21, 21), 0)
        
        diff = cv2.absdiff(frame1, frame2)
        thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)[2]
        
        if thresh.sum() > 50000:  # Motion threshold
            motion_frames.append(True)
        else:
            motion_frames.append(False)
        
        frame1 = frame2
    
    cap.release()
    
    return motion_frames
```

## Statistics

```python
def get_video_stats(video_path):
    """Get comprehensive video statistics"""
    
    cap = cv2.VideoCapture(video_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Sample frames
    sample_interval = max(1, frame_count // 100)
    
    brightness_values = []
    color_values = {'R': [], 'G': [], 'B': []}
    
    frame_num = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_num % sample_interval == 0:
            # Brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness_values.append(gray.mean())
            
            # Colors
            color_values['B'].append(frame[:, :, 0].mean())
            color_values['G'].append(frame[:, :, 1].mean())
            color_values['R'].append(frame[:, :, 2].mean())
        
        frame_num += 1
    
    cap.release()
    
    return {
        'fps': fps,
        'frame_count': frame_count,
        'duration': frame_count / fps,
        'avg_brightness': np.mean(brightness_values),
        'avg_colors': {k: np.mean(v) for k, v in color_values.items()},
    }
```

## Next Steps

- [Optimization](./12-optimization.md) - Tune performance
- [Troubleshooting](./13-troubleshooting.md) - Fix issues
