# Video Basics on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Video File Handling](#video-file-handling)
3. [Reading Videos](#reading-videos)
4. [Writing Videos](#writing-videos)
5. [Frame Operations](#frame-operations)
6. [Video Properties](#video-properties)
7. [Batch Frame Processing](#batch-frame-processing)
8. [Video Conversion](#video-conversion)

## Introduction

This guide covers fundamental video handling operations using OpenCV on Jetson AGX Orin. These basics are essential for all video AI processing tasks.

## Video File Handling

### VideoReader Class

```python
#!/usr/bin/env python3
"""
Video Basics - Reading, Writing, and Processing
Optimized for Jetson AGX Orin
"""

import cv2
import numpy as np
from PIL import Image
import os
import time
from tqdm import tqdm

class VideoReader:
    """Read and process video files"""
    
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = None
        self.properties = {}
        
    def open(self):
        """Open video file"""
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")
        
        # Read properties
        self.properties = {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "frame_count": int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "duration": int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) / 
                       self.cap.get(cv2.CAP_PROP_FPS),
            "codec": int(self.cap.get(cv2.CAP_PROP_FOURCC)),
        }
        
        return self.cap
    
    def read_frame(self):
        """Read single frame"""
        ret, frame = self.cap.read()
        return ret, frame
    
    def read_frames(self, max_frames=None):
        """Read all frames"""
        frames = []
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            frames.append(frame)
            
            if max_frames and len(frames) >= max_frames:
                break
        
        return frames
    
    def read_frame_at(self, position):
        """Read frame at specific position"""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
        return self.cap.read()
    
    def get_frame_at_time(self, time_seconds):
        """Read frame at specific time"""
        self.cap.set(cv2.CAP_PROP_POS_MSEC, time_seconds * 1000)
        return self.cap.read()
    
    def release(self):
        """Release video capture"""
        if self.cap:
            self.cap.release()
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *args):
        self.release()
    
    def print_info(self):
        """Print video information"""
        print("="*50)
        print(f"Video: {self.video_path}")
        print(f"Resolution: {self.properties['width']}x{self.properties['height']}")
        print(f"FPS: {self.properties['fps']:.2f}")
        print(f"Frames: {self.properties['frame_count']}")
        print(f"Duration: {self.properties['duration']:.2f}s")
        print("="*50)


class VideoWriter:
    """Write video files"""
    
    def __init__(self, output_path, fps, width, height, codec='mp4v'):
        self.output_path = output_path
        self.fps = fps
        self.width = width
        self.height = height
        
        # Convert codec
        fourcc = cv2.VideoWriter_fourcc(*codec)
        
        # Create writer
        self.writer = cv2.VideoWriter(
            output_path,
            fourcc,
            fps,
            (width, height)
        )
        
        if not self.writer.isOpened():
            raise ValueError(f"Cannot create video writer: {output_path}")
    
    def write_frame(self, frame):
        """Write single frame"""
        # Resize if needed
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        
        self.writer.write(frame)
    
    def write_frames(self, frames):
        """Write multiple frames"""
        for frame in tqdm(frames, desc="Writing frames"):
            self.write_frame(frame)
    
    def release(self):
        """Release video writer"""
        self.writer.release()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.release()


class VideoProcessor:
    """Process video frames"""
    
    def __init__(self):
        self.cap = None
    
    def process_video(
        self,
        input_path,
        output_path,
        process_func,
        max_frames=None
    ):
        """
        Process video with custom function
        
        Args:
            input_path: Input video path
            output_path: Output video path
            process_func: Function to process each frame
            max_frames: Maximum frames to process
        """
        
        # Open input
        cap = cv2.VideoCapture(input_path)
        
        # Get properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create output
        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            fps,
            (width, height)
        )
        
        frame_count = 0
        
        print(f"Processing video: {input_path}")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            processed = process_func(frame)
            
            # Write frame
            writer.write(processed)
            
            frame_count += 1
            
            if max_frames and frame_count >= max_frames:
                break
            
            # Progress
            if frame_count % 30 == 0:
                print(f"Processed {frame_count} frames...")
        
        cap.release()
        writer.release()
        
        print(f"Complete! Processed {frame_count} frames")
        
        return frame_count


def process_grayscale(frame):
    """Example: Convert to grayscale"""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

def process_blur(frame):
    """Example: Apply blur"""
    return cv2.GaussianBlur(frame, (15, 15), 0)

def process_edge(frame):
    """Example: Edge detection"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def main():
    """Demo video processing"""
    
    # Create test video
    test_input = "/tmp/test_input.mp4"
    test_output = "/tmp/test_output.mp4"
    
    print("Creating test video...")
    
    # Generate test video
    width, height = 640, 480
    fps = 30
    duration = 2  # seconds
    
    writer = cv2.VideoWriter(
        test_input,
        cv2.VideoWriter_fourcc(*'mp4v'),
        fps,
        (width, height)
    )
    
    for i in range(fps * duration):
        # Create colorful frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = (i * 10) % 256  # Blue channel
        frame[:, :, 1] = (i * 5) % 256   # Green
        frame[:, :, 2] = (i * 15) % 256  # Red
        
        # Add some shapes
        cv2.circle(frame, (width//2, height//2), 50, (255, 255, 255), -1)
        
        writer.write(frame)
    
    writer.release()
    print(f"Created test video: {test_input}")
    
    # Process with VideoReader
    print("\n=== Using VideoReader ===")
    with VideoReader(test_input) as reader:
        reader.print_info()
        
        # Read first 10 frames
        frames = reader.read_frames(max_frames=10)
        print(f"Read {len(frames)} frames")
    
    # Process video
    print("\n=== Processing Video ===")
    processor = VideoProcessor()
    processor.process_video(
        test_input,
        test_output,
        process_blur,
        max_frames=30
    )
    
    print(f"Output saved to: {test_output}")
    
    # Cleanup
    if os.path.exists(test_input):
        os.remove(test_input)
    if os.path.exists(test_output):
        os.remove(test_output)
    
    print("\nDemo complete!")


if __name__ == "__main__":
    main()
```

## Reading Videos

### Basic Video Reading

```python
import cv2

# Open video
cap = cv2.VideoCapture('video.mp4')

# Check if opened
if not cap.isOpened():
    print("Error opening video")
    exit()

# Read frames
while True:
    ret, frame = cap.read()
    
    if not ret:
        break
    
    # Process frame
    cv2.imshow('Frame', frame)
    
    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### Reading with Properties

```python
cap = cv2.VideoCapture('video.mp4')

# Get properties
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
codec = int(cap.get(cv2.CAP_PROP_FOURCC))

print(f"Resolution: {width}x{height}")
print(f"FPS: {fps}")
print(f"Frames: {frame_count}")
print(f"Duration: {frame_count/fps:.2f}s")
```

## Writing Videos

### Basic Video Writing

```python
import cv2
import numpy as np

# Create video writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (640, 480))

# Write frames
for i in range(100):
    # Create frame (replace with actual frame)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out.write(frame)

out.release()
```

### Different Codecs

```python
# Common codecs
codecs = {
    'mp4v': 'MP4V (MPEG-4)',
    'avc1': 'H.264/AVC',
    'H264': 'H.264',
    'XVID': 'Xvid',
    'MJPG': 'Motion-JPEG',
}

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
```

## Frame Operations

### Frame Manipulation

```python
def process_frame(frame):
    """Example frame processing"""
    
    # Resize
    resized = cv2.resize(frame, (512, 512))
    
    # Convert color
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Adjust brightness
    brightness = 30
    bright = cv2.add(frame, np.full(frame.shape, brightness, dtype=np.uint8))
    
    # Adjust contrast
    contrast = 1.5
    contrasted = cv2.convertScaleAbs(frame, alpha=contrast, beta=0)
    
    # Blur
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    
    # Sharpen
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(frame, -1, kernel)
    
    return resized
```

### Frame Extraction

```python
# Extract frames to images
cap = cv2.VideoCapture('video.mp4')
frame_num = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Save every 30th frame
    if frame_num % 30 == 0:
        cv2.imwrite(f'frame_{frame_num:04d}.jpg', frame)
    
    frame_num += 1

cap.release()
```

## Video Properties

### Get Video Information

```python
class VideoInfo:
    """Get comprehensive video information"""
    
    @staticmethod
    def get_info(video_path):
        """Get video information"""
        
        cap = cv2.VideoCapture(video_path)
        
        info = {
            "path": video_path,
            "opened": cap.isOpened(),
        }
        
        if cap.isOpened():
            props = [
                ("frame_width", cv2.CAP_PROP_FRAME_WIDTH),
                ("frame_height", cv2.CAP_PROP_FRAME_HEIGHT),
                ("fps", cv2.CAP_PROP_FPS),
                ("frame_count", cv2.CAP_PROP_FRAME_COUNT),
                ("format", cv2.CAP_PROP_FORMAT),
                ("mode", cv2.CAP_PROP_MODE),
                ("brightness", cv2.CAP_PROP_BRIGHTNESS),
                ("contrast", cv2.CAP_PROP_CONTRAST),
                ("saturation", cv2.CAP_PROP_SATURATION),
                ("hue", cv2.CAP_PROP_HUE),
                ("gain", cv2.CAP_PROP_GAIN),
                ("exposure", cv2.CAP_PROP_EXPOSURE),
            ]
            
            for name, prop in props:
                info[name] = cap.get(prop)
            
            info["duration"] = info["frame_count"] / info["fps"]
        
        cap.release()
        
        return info
    
    @staticmethod
    def print_info(video_path):
        """Print video information"""
        
        info = VideoInfo.get_info(video_path)
        
        print("="*50)
        print(f"Video: {info['path']}")
        print(f"Status: {'Open' if info['opened'] else 'Failed'}")
        
        if info['opened']:
            print(f"Resolution: {int(info['frame_width'])}x{int(info['frame_height'])}")
            print(f"FPS: {info['fps']:.2f}")
            print(f"Frames: {int(info['frame_count'])}")
            print(f"Duration: {info['duration']:.2f}s")
        
        print("="*50)


# Usage
VideoInfo.print_info('video.mp4')
```

## Batch Frame Processing

### Process Frame Batches

```python
def process_batch(frames, process_func, batch_size=8):
    """Process frames in batches"""
    
    results = []
    
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i+batch_size]
        
        for frame in batch:
            result = process_func(frame)
            results.append(result)
        
        # Clear memory
        if i % 100 == 0:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    return results
```

### Chunk Processing

```python
def process_video_chunks(input_path, output_path, process_func, chunk_size=300):
    """Process video in chunks to save memory"""
    
    cap = cv2.VideoCapture(input_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    writer = None
    chunk_num = 0
    frame_count = 0
    
    while True:
        # Read chunk
        chunk_frames = []
        
        for _ in range(chunk_size):
            ret, frame = cap.read()
            if not ret:
                break
            chunk_frames.append(frame)
        
        if not chunk_frames:
            break
        
        # Process chunk
        processed = [process_func(f) for f in chunk_frames]
        
        # Write chunk
        if writer is None:
            writer = cv2.VideoWriter(
                f"{output_path}.part{chunk_num}",
                cv2.VideoWriter_fourcc(*'mp4v'),
                fps,
                (width, height)
            )
        
        for pf in processed:
            writer.write(pf)
        
        frame_count += len(processed)
        print(f"Processed {frame_count} frames...")
        
        # Clear memory
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        chunk_num += 1
    
    cap.release()
    writer.release()
    
    print(f"Complete! {frame_count} frames processed")
```

## Video Conversion

### Convert Video Format

```python
import subprocess

def convert_video(input_path, output_path, codec='libx264', crf=23):
    """Convert video using ffmpeg"""
    
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-c:v', codec,
        '-crf', str(crf),
        '-preset', 'fast',
        output_path
    ]
    
    subprocess.run(cmd)

# Usage
convert_video('input.avi', 'output.mp4')
```

### Resolution Conversion

```python
def resize_video(input_path, output_path, scale=0.5):
    """Resize video by scale factor"""
    
    cap = cv2.VideoCapture(input_path)
    
    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    new_width = int(orig_width * scale)
    new_height = int(orig_height * scale)
    
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*'mp4v'),
        fps,
        (new_width, new_height)
    )
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        resized = cv2.resize(frame, (new_width, new_height))
        writer.write(resized)
    
    cap.release()
    writer.release()
```

## Next Steps

- [Frame Generation](./04-frame-generation.md) - Generate video frames with AI
- [Image-to-Video](./05-image-to-video.md) - Animate static images
- [Video Interpolation](./06-video-interpolation.md) - Create smooth slow-motion
