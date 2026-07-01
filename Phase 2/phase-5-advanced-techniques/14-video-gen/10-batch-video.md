# Batch Video Processing on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Implementation](#implementation)
3. [Queue Processing](#queue-processing)
4. [Examples](#examples)

## Introduction

Process multiple videos efficiently with batch processing.

## Implementation

```python
#!/usr/bin/env python3
"""
Batch Video Processing
"""

import cv2
import os
from glob import glob
from tqdm import tqdm
import torch

class BatchVideoProcessor:
    """Process multiple videos"""
    
    def __init__(self):
        self.tasks = []
        self.results = []
    
    def add_task(self, input_path, output_path, process_func):
        """Add processing task"""
        self.tasks.append({
            'input': input_path,
            'output': output_path,
            'func': process_func
        })
    
    def process_all(self, clear_memory_every=5):
        """Process all tasks"""
        
        for i, task in enumerate(tqdm(self.tasks)):
            try:
                # Process video
                process_func = task['func']
                process_func(task['input'], task['output'])
                
                self.results.append({
                    'input': task['input'],
                    'output': task['output'],
                    'success': True
                })
                
                # Clear memory
                if i > 0 and i % clear_memory_every == 0:
                    torch.cuda.empty_cache()
                    
            except Exception as e:
                self.results.append({
                    'input': task['input'],
                    'output': task['output'],
                    'success': False,
                    'error': str(e)
                })
        
        return self.results
    
    def get_failed(self):
        """Get failed tasks"""
        return [r for r in self.results if not r['success']]
```

## Examples

```python
# Process folder of videos
def process_video(input_path, output_path):
    """Example processing function"""
    cap = cv2.VideoCapture(input_path)
    # ... process
    cap.release()

processor = BatchVideoProcessor()

# Add all videos in folder
for video in glob("input/*.mp4"):
    output = video.replace("input/", "output/")
    processor.add_task(video, output, process_video)

# Process
results = processor.process_all()
```

## Next Steps

- [Video Analysis](./11-video-analysis.md) - Analyze
- [Optimization](./12-optimization.md) - Tune
- [Troubleshooting](./13-troubleshooting.md) - Fix issues
