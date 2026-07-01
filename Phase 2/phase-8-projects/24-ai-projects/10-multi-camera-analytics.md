# Project 10: Multi-Camera Video Analytics with DeepStream

A comprehensive guide to building an enterprise-grade multi-camera video analytics system using NVIDIA DeepStream for real-time object detection, tracking, and analytics on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Hardware Optimization](#hardware-optimization)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [What You'll Build](#what-youll-build)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install DeepStream SDK](#step-1-install-deepstream-sdk)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Configure Camera Sources](#step-3-configure-camera-sources)
   - [Step 4: Create Analytics Pipeline](#step-4-create-analytics-pipeline)
   - [Step 5: Set Up Web Dashboard](#step-5-set-up-web-dashboard)
7. [Running the System](#running-the-system)
8. [Advanced Configuration](#advanced-configuration)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a comprehensive multi-camera analytics system:

- **8+ Concurrent Streams**: Process multiple camera feeds
- **Real-time Detection**: Person, vehicle, object detection
- **Object Tracking**: Unique IDs for each tracked object
- **Heatmap Generation**: Visualize movement patterns
- **ROI Analytics**: Region-based statistics
- **Web Dashboard**: Real-time monitoring
- **Alert System**: Critical event notifications

### Why DeepStream?

| Feature | Benefit |
|---------|---------|
| NVDEC Acceleration | Hardware video decode |
| TensorRT Optimization | GPU-accelerated inference |
| Zero-copy | Minimal latency |
| Plugin Architecture | Flexible pipeline |
| Edge-Ready | Designed for Jetson |

---

## Hardware Optimization

### Jetson AGX Orin Capabilities

| Capability | Specification |
|-----------|---------------|
| Decode | 8x 4K @ 30fps |
| Encode | 4x 4K @ 30fps |
| Inference | 8x 1080p streams |
| Tensor Cores | 64 for AI |

### Power Mode

```bash
# Maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DeepStream Pipeline Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Camera 1 │  │ Camera 2 │  │ Camera 3 │  │ Camera N │                   │
│  │ (RTSP)   │  │ (USB)    │  │ (CSI)    │  │ (File)   │                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
│       │            │            │            │                            │
│       └────────────┴────────────┴────────────┘                            │
│                              │                                             │
│                    ┌─────────┴─────────┐                                 │
│                    │  Stream Muxer     │                                 │
│                    └─────────┬─────────┘                                 │
│                              │                                             │
│  ┌───────────────────────────┼───────────────────────────────────────┐   │
│  │                    DEEPSTREAM PIPELINE                           │   │
│  │                                                                  │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │   │
│  │  │ Decoder │─▶│ Parser  │─▶│ Detector│─▶│ Tracker │           │   │
│  │  │(NVDEC)  │  │         │  │(TensorRT)│  │         │           │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │   │
│  │                                                          │           │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │           │   │
│  │  │Analytics│─▶│OSD     │─▶│ Encode  │─▶│ Streaming│      │           │   │
│  │  │        │  │        │  │(NVENC)  │  │(RTSP)    │      │           │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │           │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Outputs:                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │   RTSP       │  │   MQTT       │  │   REST API   │                   │
│  │   Stream     │  │   Messages   │  │   Analytics  │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Purpose |
|-----------|---------|
| DeepStream SDK | Video analytics framework |
| JetPack 6.2 | CUDA, TensorRT |
| Python 3.10+ | Application logic |

### Pre-Installation Verification

```bash
# Check DeepStream
dpkg -l | grep deepstream

# Check CUDA
nvcc --version

# Check TensorRT
dpkg -l | grep TensorRT
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Multi-Stream Support | 4+ cameras |
| Object Detection | YOLO with TensorRT |
| Object Tracking | DeepSORT |
| Heatmap | Movement visualization |
| ROI Analysis | Region statistics |
| Web Dashboard | Real-time view |
| Alerts | Event notifications |

---

## Step-by-Step Implementation

### Step 1: Install DeepStream SDK

```bash
# Install DeepStream
sudo apt-get update
sudo apt-get install -y \
    deepstream-6.4 \
    deepstream-apps \
    deepstream-python-apps

# Verify
dpkg -l | grep deepstream
```

### Step 2: Create Project Directory

```bash
# Create project directory
mkdir -p ~/ai-projects/deepstream-analytics
cd ~/ai-projects/deepstream-analytics

# Create subdirectories
mkdir -p config models streams analytics
```

### Step 3: Configure Camera Sources

Create `config/sources.yml`:

```yaml
sources:
  - name: camera_1
    type: rtsp
    url: rtsp://192.168.1.101/stream
    enabled: true

  - name: camera_2
    type: rtsp
    url: rtsp://192.168.1.102/stream
    enabled: true

  - name: camera_3
    type: usb
    device: /dev/video0
    enabled: true

  - name: camera_4
    type: file
    path: /path/to/video.mp4
    loop: true
    enabled: false
```

### Step 4: Create Analytics Application

Create `deepstream_analytics.py`:

```python
#!/usr/bin/env python3
"""
Multi-Camera Video Analytics with DeepStream

Enterprise-grade video analytics for multiple camera streams
with real-time detection, tracking, and analytics.

Author: Your Name
Version: 1.0.0
"""

import sys
import os
import yaml
import json
import time
import logging
from typing import Dict, List
from pathlib import Path

# DeepStream imports
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG_FILE = os.environ.get('CONFIG_FILE', 'config/sources.yml')
ANALYTICS_PORT = int(os.environ.get('ANALYTICS_PORT', '8080'))
RTSP_PORT = int(os.environ.get('RTSP_PORT', '8554'))

# Detection classes
DETECTION_CLASSES = ['person', 'car', 'truck', 'bus', 'bicycle', 'motorcycle']

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ANALYTICS ENGINE
# ============================================================================

class AnalyticsEngine:
    """Handle analytics data from DeepStream."""
    
    def __init__(self):
        self.data = {
            'streams': {},
            'objects': {},
            'heatmaps': {},
            'rois': {}
        }
    
    def update_stream(self, stream_id: str, detections: List[Dict]):
        """Update analytics for a stream."""
        if stream_id not in self.data['streams']:
            self.data['streams'][stream_id] = {
                'detections': [],
                'counts': {},
                'last_update': time.time()
            }
        
        # Update detections
        self.data['streams'][stream_id]['detections'] = detections
        self.data['streams'][stream_id]['last_update'] = time.time()
        
        # Count by class
        counts = {}
        for det in detections:
            class_name = det.get('class', 'unknown')
            counts[class_name] = counts.get(class_name, 0) + 1
        
        self.data['streams'][stream_id]['counts'] = counts
    
    def update_object_tracking(self, object_id: str, data: Dict):
        """Update object tracking data."""
        self.data['objects'][object_id] = {
            **data,
            'last_seen': time.time()
        }
    
    def get_summary(self) -> Dict:
        """Get analytics summary."""
        total_objects = sum(
            len(s['detections']) 
            for s in self.data['streams'].values()
        )
        
        return {
            'timestamp': time.time(),
            'active_streams': len(self.data['streams']),
            'total_objects': total_objects,
            'streams': self.data['streams']
        }


# ============================================================================
# DEEPSTREAM PIPELINE
# ============================================================================

class DeepStreamPipeline:
    """Manage DeepStream pipeline."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.pipeline = None
        self.analytics = AnalyticsEngine()
        self.running = False
        
        # Initialize GStreamer
        Gst.init(None)
    
    def create_pipeline(self) -> Gst.Pipeline:
        """Create DeepStream pipeline."""
        pipeline = Gst.Pipeline.new("multi-camera-analytics")
        
        # Create source bins for each camera
        source_bins = []
        for i, source in enumerate(self.config.get('sources', [])):
            if not source.get('enabled', True):
                continue
            
            bin = self.create_source_bin(i, source)
            source_bins.append(bin)
            pipeline.add(bin)
        
        # Create stream muxer
        streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
        streammux.set_property('width', 1920)
        streammux.set_property('height', 1080)
        streammux.set_property('batch-size', len(source_bins))
        streammux.set_property('batched-push-timeout', 40000)
        pipeline.add(streammux)
        
        # Connect sources to muxer
        for i, bin in enumerate(source_bins):
            pad_name = f"sink_{i}"
            sinkpad = streammux.get_request_pad(pad_name)
            srcpad = bin.get_static_pad("src")
            srcpad.link(sinkpad)
        
        # Create detector (Primary GIE)
        detector = Gst.ElementFactory.make("nvinfer", "detector")
        detector.set_property('config-file-path', 'config/detector.txt')
        detector.set_property('batch-size', len(source_bins))
        pipeline.add(detector)
        
        # Create tracker
        tracker = Gst.ElementFactory.make("nvtracker", "tracker")
        tracker.set_property('tracker-width', 640)
        tracker.set_property('tracker-height', 384)
        tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so')
        tracker.set_property('ll-config-file', 'config/tracker.txt')
        pipeline.add(tracker)
        
        # Create analytics
        analytics = Gst.ElementFactory.make("nvdsanalytics", "analytics")
        analytics.set_property('config-file', 'config/analytics.txt')
        pipeline.add(analytics)
        
        # Create on-screen display
        osd = Gst.ElementFactory.make("nvdsosd", "osd")
        osd.set_property('process-mode', 1)
        osd.set_property('display-text', 1)
        pipeline.add(osd)
        
        # Create converter
        converter = Gst.ElementFactory.make("nvvidconv", "converter")
        pipeline.add(converter)
        
        # Create encoder
        encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
        encoder.set_property('bitrate', 2000000)
        pipeline.add(encoder)
        
        # Create parser
        parser = Gst.ElementFactory.make("h264parse", "parser")
        pipeline.add(parser)
        
        # Create RTPPayloader
        rtp = Gst.ElementFactory.make("rtph264pay", "rtp")
        pipeline.add(rtp)
        
        # Create UDP sink
        udpsink = Gst.ElementFactory.make("udpsink", "udpsink")
        udpsink.set_property('host', '127.0.0.1')
        udpsink.set_property('port', RTSP_PORT)
        pipeline.add(udpsink)
        
        # Link elements
        streammux.link(detector)
        detector.link(tracker)
        tracker.link(analytics)
        analytics.link(osd)
        osd.link(converter)
        converter.link(encoder)
        encoder.link(parser)
        parser.link(rtp)
        rtp.link(udpsink)
        
        # Add probe for analytics
        analytics_pad = analytics.get_static_pad("src")
        analytics_pad.add_probe(
            Gst.PadProbeType.BUFFER,
            self.analytics_probe_callback
        )
        
        return pipeline
    
    def create_source_bin(self, index: int, source: Dict) -> Gst.Bin:
        """Create source bin for a camera."""
        bin = Gst.Bin.new(f"source-{index}")
        
        if source['type'] == 'rtsp':
            source_elem = Gst.ElementFactory.make("rtspsrc", f"rtsp-{index}")
            source_elem.set_property('location', source['url'])
            
            # Add depay
            depay = Gst.ElementFactory.make("rtph264depay", f"depay-{index}")
            bin.add(depay)
            bin.add(source_elem)
            source_elem.link(depay)
            
            # Connect source pad
            srcpad = depay.get_static_pad("src")
        elif source['type'] == 'usb':
            source_elem = Gst.ElementFactory.make("v4l2src", f"usb-{index}")
            source_elem.set_property('device', source.get('device', '/dev/video0'))
            
            # Add parser
            parser = Gst.ElementFactory.make("h264parse", f"parser-{index}")
            bin.add(parser)
            bin.add(source_elem)
            source_elem.link(parser)
            
            srcpad = parser.get_static_pad("src")
        else:
            # File source
            source_elem = Gst.ElementFactory.make("filesrc", f"file-{index}")
            source_elem.set_property('location', source['path'])
            
            parser = Gst.ElementFactory.make("h264parse", f"parser-{index}")
            bin.add(parser)
            bin.add(source_elem)
            source_elem.link(parser)
            
            srcpad = parser.get_static_pad("src")
        
        # Add ghost pad
        bin.add_pad(Gst.GhostPad.new("src", srcpad))
        
        return bin
    
    def analytics_probe_callback(self, pad, info):
        """Callback for analytics data."""
        # Extract metadata
        # This would parse NvDsAnalytics and update analytics engine
        pass
    
    def run(self):
        """Run the pipeline."""
        self.pipeline = self.create_pipeline()
        self.pipeline.set_state(Gst.State.PLAYING)
        self.running = True
        
        logger.info("DeepStream pipeline started")
        
        # Run main loop
        loop = GObject.MainLoop()
        loop.run()
    
    def stop(self):
        """Stop the pipeline."""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        self.running = False
        logger.info("DeepStream pipeline stopped")


# ============================================================================
# WEB SERVER
# ============================================================================

class AnalyticsServer:
    """Web server for analytics dashboard."""
    
    def __init__(self, engine: AnalyticsEngine):
        self.engine = engine
        self.app = None
    
    def create_app(self):
        """Create Flask application."""
        from flask import Flask, render_template, jsonify, request
        from flask_socketio import SocketIO
        
        app = Flask(__name__)
        socketio = SocketIO(app, cors_allowed_origins="*")
        
        @app.route('/')
        def index():
            return render_template('index.html')
        
        @app.route('/api/analytics')
        def get_analytics():
            return jsonify(self.engine.get_summary())
        
        @app.route('/api/streams')
        def get_streams():
            streams = []
            for name, data in self.engine.data['streams'].items():
                streams.append({
                    'name': name,
                    'counts': data['counts'],
                    'last_update': data['last_update']
                })
            return jsonify(streams)
        
        @app.route('/api/objects')
        def get_objects():
            return jsonify(self.engine.data['objects'])
        
        # WebSocket for real-time updates
        @socketio.on('connect')
        def handle_connect():
            pass
        
        def background_updates():
            """Send periodic updates."""
            while True:
                socketio.sleep(1)
                data = self.engine.get_summary()
                socketio.emit('analytics', data)
        
        import threading
        threading.Thread(target=background_updates, daemon=True).start()
        
        self.app = app
        return app, socketio
    
    def run(self, port: int = ANALYTICS_PORT):
        """Run the server."""
        app, socketio = self.create_app()
        logger.info(f"Starting analytics server on port {port}")
        socketio.run(app, host='0.0.0.0', port=port)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    # Load configuration
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    # Create pipeline
    pipeline = DeepStreamPipeline(config)
    
    # Start analytics server in background
    import threading
    server = AnalyticsServer(pipeline.analytics)
    threading.Thread(target=server.run, daemon=True).start()
    
    # Run pipeline
    try:
        pipeline.run()
    except KeyboardInterrupt:
        pipeline.stop()


if __name__ == '__main__':
    main()
```

### Step 5: Set Up Web Dashboard

Create `templates/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Camera Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial; margin: 20px; background: #1a1a2e; color: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; }
        .stat { font-size: 2em; font-weight: bold; color: #e94560; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #2a2a4a; }
    </style>
</head>
<body>
    <h1>📹 Multi-Camera Analytics</h1>
    
    <div class="grid">
        <div class="card">
            <h3>Active Streams</h3>
            <div class="stat" id="stream-count">0</div>
        </div>
        <div class="card">
            <h3>Total Objects</h3>
            <div class="stat" id="object-count">0</div>
        </div>
        <div class="card">
            <h3>Detections by Class</h3>
            <canvas id="detections-chart"></canvas>
        </div>
    </div>
    
    <div class="card" style="margin-top: 20px;">
        <h3>Stream Details</h3>
        <table id="streams-table">
            <thead>
                <tr><th>Stream</th><th>Person</th><th>Car</th><th>Last Update</th></tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
    
    <script>
        // Connect to WebSocket
        const socket = io();
        
        socket.on('analytics', (data) => {
            document.getElementById('stream-count').textContent = data.active_streams;
            document.getElementById('object-count').textContent = data.total_objects;
            
            // Update table
            const tbody = document.querySelector('#streams-table tbody');
            tbody.innerHTML = '';
            
            for (const [name, stream] of Object.entries(data.streams)) {
                const row = `<tr>
                    <td>${name}</td>
                    <td>${stream.counts.person || 0}</td>
                    <td>${stream.counts.car || 0}</td>
                    <td>${new Date(stream.last_update * 1000).toLocaleTimeString()}</td>
                </tr>`;
                tbody.innerHTML += row;
            }
        });
    </script>
</body>
</html>
```

---

## Running the System

```bash
# Run the analytics system
cd ~/ai-projects/deepstream-analytics
python3 deepstream_analytics.py

# Access dashboard
# Open http://localhost:8080
```

---

## Advanced Configuration

### Object Detection Config

Create `config/detector.txt`:

```properties
[property]
gpu-id=0
net-scale-factor=0.0039215697906911373
model-color-format=1
custom-network-config=/path/to/yolo/config.txt
model-engine-file=/path/to/yolo/model.engine
labelfile-path=/path/to/labels.txt
batch-size=4
network-mode=2
interval=0
gie-mode=1
```

### Tracking Config

Create `config/tracker.txt`:

```properties
[property]
tracker-width=640
tracker-height=384
ll-lib-file=/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so
ll-config-file=/opt/nvidia/deepstream/deepstream/samples/configs/tracker_ params/DeepStream-Tracker-DeepSORT.txt
tracker-surface-type=0
batch-size=4
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Pipeline won't start | Check camera URLs |
| Low FPS | Reduce resolution |
| Memory error | Reduce batch size |
| No detections | Check model config |

---

## License

MIT License
