# Project 15: Real-Time Video Streaming with AI Overlays

A comprehensive guide to building a complete video streaming system with real-time AI annotations, web-based viewer, and multi-user support on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Create Video Capture](#step-3-create-video-capture)
   - [Step 4: Create Streaming Server](#step-4-create-streaming-server)
   - [Step 5: Create Web Viewer](#step-5-create-web-viewer)
6. [Running the System](#running-the-system)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a comprehensive video streaming system:

- **Real-time Capture**: Camera input with AI processing
- **Object Detection**: YOLO overlays on video
- **Web Streaming**: HLS/DASH delivery
- **Multi-Viewer**: Multiple simultaneous viewers
- **Recording**: On-demand and motion-triggered

### Streaming Features

| Feature | Description |
|---------|-------------|
| AI Overlays | Object detection boxes |
| HLS Streaming | Adaptive bitrate |
| WebSocket | Real-time updates |
| Recording | Clip storage |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Video Streaming Architecture                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │   Camera     │─────▶│    AI        │─────▶│   Video      │           │
│   │   Input      │      │   Detector   │      │   Encoder   │           │
│   └──────────────┘      └──────────────┘      └──────┬───────┘           │
│                                                       │                    │
│                                                       ▼                    │
│   ┌────────────────────────────────────────────────────────────────────┐   │
│   │                         STREAMING PIPELINE                          │   │
│   │                                                                     │   │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │   │
│   │  │  HLS     │───▶│  M3U8   │───▶│  nginx  │───▶│  Browser │  │   │
│   │  │ Segments │    │ Playlist │    │  Server │    │  Player  │  │   │
│   │  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │   │
│   │                                                                     │   │
│   │  ┌──────────────────────────────────────────────────────────────┐ │   │
│   │  │                    WebSocket for Updates                      │ │   │
│   │  └──────────────────────────────────────────────────────────────┘ │   │
│   └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │   Recording  │      │   Motion     │      │    Web       │           │
│   │   Manager   │      │   Trigger    │      │   Dashboard  │           │
│   └──────────────┘      └──────────────┘      └──────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation |
|-----------|-------------|
| OpenCV | Part 7 |
| YOLO | Part 7 |
| FFmpeg | System package |
| Flask | Python package |

### Pre-Installation

```bash
# Check OpenCV
python3 -c "import cv2; print(cv2.__version__)"

# Check FFmpeg
ffmpeg -version
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| AI Detection | YOLO object detection |
| Video Encoding | Hardware H.264 |
| HLS Streaming | Adaptive streaming |
| Web Viewer | Browser playback |
| Recording | Clip storage |

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y nginx ffmpeg

# Install Python packages
pip3 install flask flask-socketio opencv-python numpy imutils
```

### Step 2: Create Project Directory

```bash
mkdir -p ~/ai-projects/video-streaming
cd ~/ai-projects/video-streaming
mkdir -p capture static templates recordings streams
```

### Step 3: Create Video Capture

Create `capture/ai_capture.py`:

```python
#!/usr/bin/env python3
"""
AI Video Capture Module

Captures video with real-time AI object detection overlays.
"""

import cv2
import numpy as np
import time
import threading
from ultralytics import YOLO
from typing import Optional, Callable


class AICapture:
    """
    Video capture with AI detection overlays.
    """
    
    def __init__(
        self,
        camera_index: int = 0,
        model_name: str = 'yolov8n.pt',
        detection_classes: list = None
    ):
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        
        # Load YOLO model
        print(f"Loading model: {model_name}")
        self.model = YOLO(model_name)
        
        # Detection classes
        self.detection_classes = detection_classes or ['person', 'car', 'truck']
        
        # Frame buffer
        self.current_frame = None
        self.running = False
        self.lock = threading.Lock()
        
        # Statistics
        self.fps = 0
        self.frame_count = 0
        
        # Open camera
        self._open_camera()
    
    def _open_camera(self):
        """Open video capture."""
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if self.cap.isOpened():
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            print(f"Camera opened: {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
        else:
            print("Failed to open camera")
    
    def start(self):
        """Start capture loop in background."""
        self.running = True
        thread = threading.Thread(target=self._capture_loop, daemon=True)
        thread.start()
    
    def _capture_loop(self):
        """Background capture loop."""
        fps_start = time.time()
        
        while self.running:
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            # Run detection
            results = self.model(frame, verbose=False)
            
            # Draw detections
            frame = self._draw_detections(frame, results)
            
            # Update frame
            with self.lock:
                self.current_frame = frame.copy()
                self.frame_count += 1
            
            # Calculate FPS
            if time.time() - fps_start >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                fps_start = time.time()
    
    def _draw_detections(self, frame, results):
        """Draw detection boxes on frame."""
        for r in results:
            boxes = r.boxes
            
            for box in boxes:
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Get class
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                
                # Filter classes
                if class_name not in self.detection_classes:
                    continue
                
                # Get confidence
                confidence = float(box.conf[0])
                
                # Draw box
                color = (0, 255, 0)  # Green
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label
                label = f"{class_name}: {confidence:.2f}"
                cv2.putText(
                    frame, label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 2
                )
        
        # Draw FPS
        cv2.putText(
            frame, f"FPS: {self.fps}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1, (0, 255, 0), 2
        )
        
        return frame
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame."""
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def stop(self):
        """Stop capture."""
        self.running = False
        if self.cap:
            self.cap.release()


# ============================================================================
# RECORDING
# ============================================================================

class VideoRecorder:
    """Record video segments."""
    
    def __init__(self, output_dir: str = 'recordings'):
        self.output_dir = output_dir
        self.writer = None
        self.recording = False
    
    def start_recording(self, frame):
        """Start recording a video segment."""
        if self.recording:
            return
        
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"{self.output_dir}/clip_{timestamp}.mp4"
        
        # Get frame dimensions
        h, w = frame.shape[:2]
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            output_path, fourcc, 30, (w, h)
        )
        
        self.recording = True
        self.output_path = output_path
        print(f"Started recording: {output_path}")
    
    def write_frame(self, frame):
        """Write frame to recording."""
        if self.recording and self.writer:
            self.writer.write(frame)
    
    def stop_recording(self):
        """Stop recording."""
        if self.recording:
            self.writer.release()
            self.writer = None
            self.recording = False
            print(f"Stopped recording: {self.output_path}")
```

### Step 4: Create Streaming Server

Create `streaming/server.py`:

```python
#!/usr/bin/env python3
"""
Streaming Server

Provides HLS streaming with Flask and FFmpeg.
"""

import os
import ffmpeg
import subprocess
from flask import Flask, Response, render_template
from flask_socketio import SocketIO


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
STREAM_DIR = 'streams'
os.makedirs(STREAM_DIR, exist_ok=True)


def generate_hls(pipe):
    """
    Generate HLS stream from FFmpeg pipe.
    
    Args:
        pipe: FFmpeg output pipe
    
    Yields:
        bytes: HLS segments
    """
    while True:
        data = pipe.stdout.read(4096)
        if not data:
            break
        yield data


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/stream.m3u8')
def stream_playlist():
    """
    Serve HLS playlist.
    """
    playlist_path = f"{STREAM_DIR}/playlist.m3u8"
    
    if not os.path.exists(playlist_path):
        return "Stream not available", 404
    
    with open(playlist_path, 'rb') as f:
        content = f.read()
    
    return Response(
        content,
        mimetype='application/vnd.apple.mpegurl'
    )


@app.route('/segment/<name>')
def segment(name):
    """
    Serve HLS segment.
    """
    segment_path = f"{STREAM_DIR}/{name}"
    
    if not os.path.exists(segment_path):
        return "Segment not found", 404
    
    with open(segment_path, 'rb') as f:
        content = f.read()
    
    return Response(
        content,
        mimetype='video/mp2ts'
    )


@app.route('/mjpeg')
def mjpeg_stream():
    """
    Serve MJPEG stream.
    """
    from capture.ai_capture import AICapture
    
    capture = AICapture()
    capture.start()
    
    def generate():
        while True:
            frame = capture.get_frame()
            if frame is not None:
                # Encode as JPEG
                _, jpeg = cv2.imencode('.jpg', frame)
                frame_bytes = jpeg.tobytes()
                
                yield b'--frame\r\n'
                yield b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ============================================================================
# BROADCAST FRAMES VIA SOCKETIO
# ============================================================================

def broadcast_frames(capture):
    """Broadcast frames to connected clients."""
    import cv2
    
    while True:
        frame = capture.get_frame()
        if frame is not None:
            # Encode as JPEG
            _, jpeg = cv2.imencode('.jpg', frame)
            frame_bytes = jpeg.tobytes()
            
            # Broadcast to all clients
            socketio.emit('frame', {'image': frame_bytes})
        
        socketio.sleep(0.033)  # ~30 FPS


@app.route('/video_feed')
def video_feed():
    """Video feed route for Socket.IO."""
    return render_template('video.html')


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Start server
    print("Starting streaming server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

### Step 5: Create Web Viewer

Create `templates/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Video Streaming</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a2e;
            color: white;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #e94560; }
        
        .video-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .video-card {
            background: #16213e;
            border-radius: 10px;
            padding: 10px;
        }
        
        video {
            width: 100%;
            border-radius: 8px;
        }
        
        .stats {
            margin-top: 10px;
            padding: 10px;
            background: #0f3460;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📹 AI Video Streaming</h1>
        
        <div class="video-container">
            <div class="video-card">
                <h3>HLS Stream</h3>
                <video id="hls-video" controls></video>
            </div>
            
            <div class="video-card">
                <h3>MJPEG Stream</h3>
                <img id="mjpeg-image" style="width:100%">
            </div>
        </div>
        
        <div class="stats">
            <div id="status">Connecting...</div>
        </div>
    </div>
    
    <script>
        // HLS Player
        var video = document.getElementById('hls-video');
        var hls = new Hls();
        hls.loadSource('/stream.m3u8');
        hls.attachMedia(video);
        
        // MJPEG Player
        function updateMJPEG() {
            fetch('/mjpeg')
                .then(response => {
                    document.getElementById('mjpeg-image').src = '/mjpeg';
                })
                .catch(err => console.error(err));
        }
        
        // Update every 100ms
        setInterval(updateMJPEG, 100);
        
        // Socket.IO connection
        var socket = io();
        
        socket.on('connect', function() {
            document.getElementById('status').innerHTML = 'Connected';
        });
        
        socket.on('disconnect', function() {
            document.getElementById('status').innerHTML = 'Disconnected';
        });
    </script>
</body>
</html>
```

---

## Running the System

```bash
# Start capture
python3 capture/ai_capture.py &

# Start streaming server
python3 streaming/server.py
```

### Access Streams

- **HLS**: `http://localhost:5000/`
- **MJPEG**: `http://localhost:5000/mjpeg`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Stream not available | Check FFmpeg |
| High latency | Reduce resolution |
| No detections | Check YOLO model |

---

## License

MIT License
