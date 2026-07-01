# Project 3: Multimodal Vision System

A comprehensive guide to building an AI system that can see, understand, and describe images and video in real-time using LLaVA and Ollama.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Hardware Setup](#hardware-setup)
5. [What You'll Build](#what-youll-build)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Test Camera](#step-2-test-camera)
   - [Step 3: Install LLaVA Model](#step-3-install-llava-model)
   - [Step 4: Create Image Captioning Script](#step-4-create-image-captioning-script)
   - [Step 5: Create Video Stream Analyzer](#step-5-create-video-stream-analyzer)
   - [Step 6: Create VQA Interface](#step-6-create-vqa-interface)
7. [Running the Vision System](#running-the-vision-system)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)
10. [Next Steps](#next-steps)

---

## Overview

This project creates a complete multimodal vision AI system:

- **Image Captioning**: Describe what's in any image
- **Visual Question Answering**: Answer questions about images
- **Real-time Video Analysis**: Process video streams with AI
- **Object Detection**: Identify objects in scenes
- **Face Detection**: Recognize faces (optional)

### Why Multimodal AI?

| Capability | Use Case |
|------------|----------|
| Image Understanding | Accessibility tools, content moderation |
| Visual Q&A | Educational assistants, product support |
| Video Analysis | Security, wildlife monitoring |
| Object Tracking | Robotics, autonomous vehicles |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Multimodal Vision System Architecture                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐              │
│   │   Camera    │─────▶│   OpenCV    │─────▶│   LLaVA     │              │
│   │   (CSI/USB) │      │  Processing │      │   (Vision)  │              │
│   └─────────────┘      └─────────────┘      └──────┬──────┘              │
│                                                     │                     │
│                                                     ▼                     │
│                                              ┌─────────────┐              │
│                                              │   Ollama    │              │
│                                              │   (LLM)     │              │
│                                              └──────┬──────┘              │
│                                                     │                     │
│                                                     ▼                     │
│                                              ┌─────────────┐              │
│                                              │   Output    │              │
│                                              │ Display/API │              │
│                                              └─────────────┘              │
│                                                                             │
│   Components:                                                               │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │ Image        │  │ Video        │  │ VQA          │                  │
│   │ Captioning   │  │ Streaming    │  │ Interface    │                  │
│   └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation Guide |
|-----------|-------------------|
| LLaVA | [Part 7: LLaVA Setup](../part-7-vision/01-llava.md) |
| Ollama | [Part 5: Ollama Setup](../part-5-llms/01-ollama-setup.md) |
| OpenCV | [Part 7: OpenCV](../part-7-vision/02-opencv.md) |
| Python | [Part 3: Python Setup](../part-3-python-environment/01-python-setup.md) |

### Pre-Installation Verification

```bash
# 1. Verify Ollama is running
curl http://localhost:11434/api/tags

# 2. Check if LLaVA is available
ollama list | grep llava

# 3. Verify OpenCV
python3 -c "import cv2; print(cv2.__version__)"

# 4. Test camera
v4l2-ctl --list-devices
```

---

## Hardware Setup

### Camera Types

| Camera Type | Device | Driver |
|-------------|--------|--------|
| CSI Camera | /dev/video0 | v4l2 |
| USB Camera | /dev/video1+ | uvcvideo |
| IP Camera | rtsp://... | ffmpeg |

### Camera Setup Commands

```bash
# List all video devices
v4l2-ctl --list-devices

# Check specific device
v4l2-ctl --device /dev/video0 --all

# Set resolution
v4l2-ctl --device /dev/video0 --set-fmt-video=width=1280,height=720

# Test capture
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Image Captioning | Generate descriptions for images |
| Visual Q&A | Answer questions about images |
| Video Analysis | Process video streams in real-time |
| Batch Processing | Process multiple images |
| REST API | Programmatic access |

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Install system dependencies
sudo apt update
sudo apt install -y v4l-utils ffmpeg libgl1-mesa-glx libglib2.0-0

# Install Python packages
pip install --upgrade pip
pip install opencv-python numpy requests pillow

# For Jetson specific
pip install jetson-utils 2>/dev/null || true
```

### Step 2: Test Camera

```bash
# List available cameras
v4l2-ctl --list-devices

# For USB camera
v4l2-ctl --device /dev/video0 --all

# For CSI camera (Jetson)
# Should auto-detect as /dev/video0

# Test capture with ffmpeg
ffmpeg -f v4l2 -input_format yuyv422 -i /dev/video0 -frames:v 1 capture.jpg

# Or use OpenCV test
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    cv2.imwrite('test.jpg', frame)
    print('Camera working!')
else:
    print('Camera not detected')
cap.release()
"
```

### Step 3: Install LLaVA Model

```bash
# Pull LLaVA model
ollama pull llava

# Or use llava:7b for more accurate but larger
ollama pull llava:7b

# Verify
ollama list | grep llava
```

### Step 4: Create Image Captioning Script

Create `vision_caption.py`:

```python
#!/usr/bin/env python3
"""
Image Captioning with LLaVA

A script that uses LLaVA to generate descriptions for images.
Supports single image, batch processing, and custom prompts.

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import requests
import base64
import os
import sys
import json
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# Ollama configuration
OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llava')

# API endpoint
CHAT_API = f"{OLLAMA_BASE}/api/chat"
GENERATE_API = f"{OLLAMA_BASE}/api/generate"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def encode_image_to_base64(image_path):
    """
    Encode an image file to base64 string.
    
    Args:
        image_path: Path to image file
    
    Returns:
        str: Base64 encoded image
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def check_ollama_connection():
    """
    Verify Ollama is running and accessible.
    
    Returns:
        bool: True if connected
    """
    try:
        response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_available_models():
    """
    Get list of available Ollama models.
    
    Returns:
        list: Model names
    """
    try:
        response = requests.get(f"{OLLAMA_BASE}/api/tags")
        if response.status_code == 200:
            data = response.json()
            return [m['name'] for m in data.get('models', [])]
    except Exception as e:
        print(f"Error getting models: {e}")
    return []


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def describe_image(image_path, prompt="Describe this image in detail.", model=None):
    """
    Generate a description of an image using LLaVA.
    
    Args:
        image_path: Path to the image file
        prompt: Question/prompt about the image
        model: Model name (default: DEFAULT_MODEL)
    
    Returns:
        str: AI-generated description
    """
    if model is None:
        model = DEFAULT_MODEL
    
    # Encode image
    image_b64 = encode_image_to_base64(image_path)
    
    # Prepare request
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        }],
        "stream": False
    }
    
    try:
        response = requests.post(CHAT_API, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('message', {}).get('content', '')
        else:
            return f"Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "Error: Request timed out"
    except Exception as e:
        return f"Error: {str(e)}"


def ask_about_image(image_path, question, model=None):
    """
    Ask a specific question about an image.
    
    Args:
        image_path: Path to the image file
        question: Question about the image
        model: Model name
    
    Returns:
        str: Answer to the question
    """
    return describe_image(image_path, question, model)


def describe_multiple_images(image_paths, prompt="Describe these images.", model=None):
    """
    Describe multiple images at once.
    
    Args:
        image_paths: List of image paths
        prompt: Overall prompt
        model: Model name
    
    Returns:
        str: Combined description
    """
    if model is None:
        model = DEFAULT_MODEL
    
    # Encode all images
    images_b64 = []
    for path in image_paths:
        images_b64.append(encode_image_to_base64(path))
    
    # Build message with multiple images
    content = [{"type": "text", "text": prompt}]
    for img_b64 in images_b64:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "stream": False
    }
    
    try:
        response = requests.post(CHAT_API, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('message', {}).get('content', '')
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================================
# ADVANCED FUNCTIONS
# ============================================================================

def generate_image_tags(image_path, model=None):
    """
    Generate tags/labels for an image.
    
    Args:
        image_path: Path to image
        model: Model name
    
    Returns:
        list: List of tags
    """
    prompt = "List 5-10 keywords that describe this image. Format as comma-separated list."
    result = describe_image(image_path, prompt, model)
    return [tag.strip() for tag in result.split(',')]


def detect_image_content(image_path, model=None):
    """
    Analyze image for various content types.
    
    Args:
        image_path: Path to image
        model: Model name
    
    Returns:
        dict: Analysis results
    """
    questions = [
        "What objects are in this image?",
        "What is the setting/location?",
        "What colors dominate?",
        "Are there any people?",
        "What is the mood/atmosphere?"
    ]
    
    results = {}
    for question in questions:
        answer = ask_about_image(image_path, question, model)
        results[question] = answer
    
    return results


def compare_images(image_path1, image_path2, model=None):
    """
    Compare two images and describe differences.
    
    Args:
        image_path1: First image
        image_path2: Second image
        model: Model name
    
    Returns:
        str: Comparison description
    """
    prompt = "Compare these two images. What are the similarities and differences?"
    return describe_multiple_images([image_path1, image_path2], prompt, model)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Image Captioning with LLaVA',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Describe an image
  python vision_caption.py image.jpg

  # Ask a question
  python vision_caption.py image.jpg "What colors are in this image?"

  # Generate tags
  python vision_caption.py image.jpg --tags

  # Batch process
  python vision_caption.py *.jpg --batch
        """
    )
    
    parser.add_argument('image', help='Image file or directory')
    parser.add_argument('prompt', nargs='?', default='Describe this image in detail.')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='Model to use')
    parser.add_argument('--tags', action='store_true', help='Generate tags')
    parser.add_argument('--analyze', action='store_true', help='Full analysis')
    parser.add_argument('--batch', action='store_true', help='Batch process directory')
    parser.add_argument('--output', '-o', help='Output file')
    
    args = parser.parse_args()
    
    # Check connection
    if not check_ollama_connection():
        print("ERROR: Cannot connect to Ollama. Is it running?")
        sys.exit(1)
    
    # Check model
    models = get_available_models()
    if args.model not in models:
        print(f"Warning: Model '{args.model}' not found. Using default.")
        args.model = DEFAULT_MODEL
    
    # Process
    if args.batch:
        # Batch processing
        image_dir = Path(args.image)
        if not image_dir.is_dir():
            print(f"Error: {args.image} is not a directory")
            sys.exit(1)
        
        images = list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.png'))
        
        for img in images:
            print(f"\n{'='*50}")
            print(f"Image: {img.name}")
            print('='*50)
            result = describe_image(str(img), args.prompt, args.model)
            print(result)
            
    elif args.tags:
        # Generate tags
        result = generate_image_tags(args.image, args.model)
        print("Tags:", ', '.join(result))
        
    elif args.analyze:
        # Full analysis
        results = detect_image_content(args.image, args.model)
        for question, answer in results.items():
            print(f"\n{question}")
            print(f"  {answer}")
            
    else:
        # Single image
        result = describe_image(args.image, args.prompt, args.model)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(result)
            print(f"Result saved to {args.output}")
        else:
            print(result)


if __name__ == '__main__':
    main()
```

### Step 5: Create Video Stream Analyzer

Create `vision_video.py`:

```python
#!/usr/bin/env python3
"""
Real-time Video Analysis with LLaVA

Analyzes video frames in real-time using LLaVA for vision understanding.
Can be used for surveillance, monitoring, or interactive applications.

Author: Your Name
Version: 1.0.0
"""

import cv2
import requests
import base64
import os
import time
import json
from datetime import datetime

# Configuration
OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llava')
FRAME_SKIP = 10  # Process every N frames
DISPLAY = True

def encode_frame(frame):
    """Encode video frame to base64."""
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')

def analyze_frame(frame, prompt="Describe what's happening in this frame."):
    """Analyze a single frame with LLaVA."""
    frame_b64 = encode_frame(frame)
    
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}}
            ]
        }],
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('message', {}).get('content', '')
    except Exception as e:
        return f"Error: {e}"
    return None

def process_video_stream(camera_index=0, output_file=None):
    """
    Process video stream from camera.
    
    Args:
        camera_index: Camera device index
        output_file: Optional output video file
    """
    # Open camera
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"Error: Cannot open camera {camera_index}")
        return
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Video writer
    writer = None
    if output_file:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_file, fourcc, 30, (1280, 720))
    
    frame_count = 0
    last_analysis = "No analysis yet"
    start_time = time.time()
    
    print("Starting video analysis...")
    print("Press 'q' to quit")
    print("Press 'a' to trigger immediate analysis")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame")
                break
            
            frame_count += 1
            
            # Display frame info
            info_text = f"Frame: {frame_count} | FPS: {frame_count/(time.time()-start_time):.1f}"
            cv2.putText(frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display last analysis
            y_offset = 60
            for i, line in enumerate(last_analysis.split('\n')[:3]):
                cv2.putText(frame, line[:80], (10, y_offset + i*30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame
            if DISPLAY:
                cv2.imshow('Video Analysis', frame)
            
            # Write to output
            if writer:
                writer.write(frame)
            
            # Process frame periodically
            if frame_count % FRAME_SKIP == 0:
                print(f"\nAnalyzing frame {frame_count}...")
                last_analysis = analyze_frame(
                    frame, 
                    "Briefly describe what's in this image. Keep it concise."
                )
                print(f"Analysis: {last_analysis[:100]}...")
            
            # Check for key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('a'):
                # Manual trigger
                print("Manual analysis triggered...")
                last_analysis = analyze_frame(frame)
                
    except KeyboardInterrupt:
        print("\nInterrupted")
        
    finally:
        cap.release()
        if writer:
            writer.release()
        if DISPLAY:
            cv2.destroyAllWindows()
        
        print(f"\nProcessed {frame_count} frames")
        print(f"Duration: {time.time() - start_time:.1f} seconds")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Video Analysis with LLaVA')
    parser.add_argument('--camera', '-c', type=int, default=0, help='Camera index')
    parser.add_argument('--output', '-o', help='Output video file')
    parser.add_argument('--skip', type=int, default=10, help='Frame skip interval')
    parser.add_argument('--no-display', action='store_true', help='No display window')
    
    args = parser.parse_args()
    
    global DISPLAY, FRAME_SKIP
    DISPLAY = not args.no_display
    FRAME_SKIP = args.skip
    
    process_video_stream(args.camera, args.output)


if __name__ == '__main__':
    main()
```

---

## Running the Vision System

### Image Captioning

```bash
# Basic captioning
python3 vision_caption.py your_image.jpg

# Ask specific question
python3 vision_caption.py your_image.jpg "What colors are in this image?"

# Generate tags
python3 vision_caption.py your_image.jpg --tags

# Full analysis
python3 vision_caption.py your_image.jpg --analyze

# Batch processing
python3 vision_caption.py ./photos/ --batch
```

### Video Analysis

```bash
# Live camera analysis
python3 vision_video.py

# Record analysis
python3 vision_video.py --output analysis.mp4

# Analyze at 5 fps (process every 6 frames at 30fps)
python3 vision_video.py --skip 6

# Headless mode (no display)
python3 vision_video.py --no-display
```

---

## Advanced Features

### Custom Prompts

```python
# Object detection style
prompt = "List all the objects you can see, be specific."

# OCR style
prompt = "What text do you see in this image?"

# Safety/moderation
prompt = "Does this image contain any inappropriate content?"

# Educational
prompt = "What could be learned from this image?"
```

### Real-time API Server

```python
# Create a Flask API
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    # Get image from request
    image_data = request.json.get('image')
    prompt = request.json.get('prompt', 'Describe this image.')
    
    # Decode and process
    # ... (use the functions above)
    
    return jsonify({'result': result})
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not detected | Check `v4l2-ctl --list-devices` |
| LLaVA model not found | Run `ollama pull llava` |
| Slow processing | Increase FRAME_SKIP, use smaller model |
| Memory error | Reduce resolution, use quantized model |

---

## Next Steps

| Enhancement | Description |
|-------------|-------------|
| [Multi-camera](10-multi-camera-analytics.md) | Multiple camera streams |
| [Real-time Tracking](11-realtime-tracking.md) | Object tracking |
| [Security Camera](06-security-camera-ai.md) | AI security system |

---

## Related Documentation

- [LLaVA Model](https://llava-vl.github.io/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Ollama API](https://github.com/ollama/ollama)

---

## License

MIT License
