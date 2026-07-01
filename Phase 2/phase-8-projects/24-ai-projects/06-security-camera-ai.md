# Project 6: AI-Powered Security Camera

A comprehensive guide to building an intelligent security camera system that detects people, objects, and sends real-time alerts using YOLO object detection and local AI models.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Hardware](#hardware)
5. [What You'll Build](#what-youll-build)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Install YOLO Model](#step-3-install-yolo-model)
   - [Step 4: Create Security Camera Application](#step-4-create-security-camera-application)
   - [Step 5: Configure Notifications](#step-5-configure-notifications)
   - [Step 6: Run the System](#step-6-run-the-system)
7. [Advanced Configuration](#advanced-configuration)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)
10. [Next Steps](#next-steps)

---

## Overview

This project creates an AI-powered security camera system:

- **Real-time Detection**: Detect people, vehicles, and objects
- **Motion-triggered Recording**: Save clips when activity detected
- **Alert Notifications**: Telegram or email alerts
- **24/7 Operation**: Runs as a system service
- **Local Processing**: No cloud dependencies

### Why AI-Powered Security?

| Feature | Benefit |
|---------|---------|
| Object Detection | Know WHAT triggered the alarm |
| Privacy | All processing local |
| Cost | No cloud subscription |
| Customizable | Detect specific objects |
| Fast | Real-time inference |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   AI Security Camera Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │   Camera     │─────▶│   OpenCV     │─────▶│    YOLO      │           │
│   │ (USB/IP)     │      │   Capture    │      │   Detector   │           │
│   └──────────────┘      └──────────────┘      └──────┬───────┘           │
│                                                       │                    │
│                                                       ▼                    │
│                                              ┌──────────────┐             │
│                                              │   Analysis   │             │
│                                              │   Engine     │             │
│                                              └──────┬───────┘             │
│                                                     │                     │
│                      ┌──────────────────────────────┼──────────────────┐  │
│                      │                              │                  │  │
│                      ▼                              ▼                  ▼  │
│              ┌──────────────┐            ┌──────────────┐    ┌─────────┐ │
│              │  Recording   │            │  Telegram    │    │  Email  │ │
│              │   (Clips)    │            │   Alerts     │    │ Alerts  │ │
│              └──────────────┘            └──────────────┘    └─────────┘ │
│                                                                             │
│   Detection Classes:                                                        │
│   • person    • car        • dog       • bicycle                         │
│   • cat       • truck      • motorcycle                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation Guide |
|-----------|-------------------|
| Python | [Part 3: Python Setup](../part-3-python-environment/01-python-setup.md) |
| OpenCV | [Part 7: OpenCV](../part-7-vision/02-opencv.md) |
| YOLO | [Part 7: Object Detection](../part-7-vision/02-object-detection.md) |
| Docker | [Part 2: Docker Basics](../part-2-docker/01-docker-basics.md) |

### Pre-Installation Verification

```bash
# Check Python
python3 --version

# Check OpenCV
python3 -c "import cv2; print(cv2.__version__)"

# Check PyTorch
python3 -c "import torch; print(torch.__version__)"
```

---

## Hardware

### Camera Options

| Type | Pros | Cons |
|------|------|------|
| USB Webcam | Cheap, easy | Limited range |
| IP Camera | Network accessible | Requires network |
| RTSP Camera | Low latency | More setup |
| CSI Camera | Native Jetson | Limited models |

### Recommended Setup

- **Jetson AGX Orin**: 64GB recommended
- **Camera**: Logitech C920 or similar
- **Storage**: 32GB+ SD card or SSD

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Person Detection | Alert when people detected |
| Object Detection | Vehicles, animals, packages |
| Motion Recording | Save clips on detection |
| Telegram Alerts | Instant notifications |
| Email Alerts | Detailed reports |
| Web Dashboard | Live view and playback |

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Update package lists
sudo apt update
sudo apt install -y python3-pip libopencv-dev ffmpeg libopencv-python

# Install Python packages
pip install --upgrade pip
pip install opencv-python torch torchvision
pip install ultralytics
pip install python-telegram-bot requests
```

### Step 2: Create Project Directory

```bash
# Create project directory
mkdir -p ~/ai-projects/security-camera
cd ~/ai-projects/security-camera

# Create subdirectories
mkdir -p recordings logs models
```

### Step 3: Install YOLO Model

```bash
# The YOLO model will be downloaded automatically
# But we can pre-download for offline use
python3 -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt')"
```

### Step 4: Create Security Camera Application

Create `security_camera.py`:

```python
#!/usr/bin/env python3
"""
AI-Powered Security Camera System

A comprehensive security camera system with AI object detection,
motion-triggered recording, and alert notifications.

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import cv2
import torch
import time
import os
import json
import logging
import requests
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from queue import Queue

# ============================================================================
# CONFIGURATION
# ============================================================================

# Detection Settings
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.5'))
DETECTION_CLASSES = os.environ.get('DETECTION_CLASSES', 'person,car,truck').split(',')
DETECTION_INTERVAL = int(os.environ.get('DETECTION_INTERVAL', '1'))  # Frames to skip

# Recording Settings
RECORD_ON_DETECTION = os.environ.get('RECORD_ON_DETECTION', 'true').lower() == 'true'
RECORD_DURATION = int(os.environ.get('RECORD_DURATION', '10'))  # Seconds after detection
RECORDING_DIR = os.environ.get('RECORDING_DIR', 'recordings')
MOTION_COOLDOWN = int(os.environ.get('MOTION_COOLDOWN', '30'))  # Seconds between alerts

# Camera Settings
CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', '0'))
CAMERA_URL = os.environ.get('CAMERA_URL', '')  # For IP cameras
FRAME_WIDTH = int(os.environ.get('FRAME_WIDTH', '1280'))
FRAME_HEIGHT = int(os.environ.get('FRAME_HEIGHT', '720'))
FPS = int(os.environ.get('FPS', '30'))

# Alert Settings
TELEGRAM_ENABLED = os.environ.get('TELEGRAM_ENABLED', 'false').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
EMAIL_SMTP = os.environ.get('EMAIL_SMTP', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')
EMAIL_TO = os.environ.get('EMAIL_TO', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

# Logging
LOG_DIR = os.environ.get('LOG_DIR', 'logs')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure logging."""
    Path(LOG_DIR).mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{LOG_DIR}/security.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============================================================================
# NOTIFICATION HANDLERS
# ============================================================================

class AlertManager:
    """Manage alert notifications."""
    
    def __init__(self):
        self.last_alert_time = {}
        self.alert_queue = Queue()
        self.alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.alert_thread.start()
    
    def _process_alerts(self):
        """Process alerts in background."""
        while True:
            alert = self.alert_queue.get()
            if alert is None:
                break
            self._send_alert(alert)
            self.alert_queue.task_done()
    
    def queue_alert(self, alert_type: str, message: str, image_path: str = None):
        """Queue an alert for processing."""
        # Check cooldown
        now = time.time()
        last_time = self.last_alert_time.get(alert_type, 0)
        
        if now - last_time < MOTION_COOLDOWN:
            logger.debug(f"Alert {alert_type} on cooldown")
            return
        
        self.last_alert_time[alert_type] = now
        self.alert_queue.put({
            'type': alert_type,
            'message': message,
            'image': image_path,
            'timestamp': now
        })
    
    def _send_alert(self, alert: Dict):
        """Send alert via configured channels."""
        if TELEGRAM_ENABLED and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            self._send_telegram(alert)
        
        if EMAIL_ENABLED and EMAIL_FROM and EMAIL_TO:
            self._send_email(alert)
    
    def _send_telegram(self, alert: Dict):
        """Send Telegram message."""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': f"🚨 Security Alert\n\n{alert['message']}",
                'parse_mode': 'Markdown'
            }
            requests.post(url, json=data, timeout=10)
            logger.info("Telegram alert sent")
            
            # Send image if available
            if alert.get('image') and os.path.exists(alert['image']):
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                with open(alert['image'], 'rb') as f:
                    files = {'photo': f}
                    data = {'chat_id': TELEGRAM_CHAT_ID}
                    requests.post(url, files=files, data=data, timeout=30)
                    
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")
    
    def _send_email(self, alert: Dict):
        """Send email notification."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.image import MIMEImage
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_TO
            msg['Subject'] = f"Security Alert - {alert['type']}"
            
            body = f"""
Security Alert

{alert['message']}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach image if available
            if alert.get('image') and os.path.exists(alert['image']):
                with open(alert['image'], 'rb') as f:
                    img = MIMEImage(f.read())
                    msg.attach(img)
            
            server = smtplib.SMTP(EMAIL_SMTP, EMAIL_PORT)
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            logger.info("Email alert sent")
            
        except Exception as e:
            logger.error(f"Email alert failed: {e}")


# ============================================================================
# DETECTION ENGINE
# ============================================================================

class DetectionEngine:
    """YOLO-based object detection."""
    
    def __init__(self, model_name: str = 'yolov8n.pt'):
        logger.info(f"Loading YOLO model: {model_name}")
        self.model = torch.hub.load('ultralytics/yolov8', model_name)
        self.model.conf = CONFIDENCE_THRESHOLD
        self.classes = [c.strip().lower() for c in DETECTION_CLASSES]
        logger.info(f"Detection classes: {self.classes}")
    
    def detect(self, frame) -> List[Dict]:
        """Detect objects in frame."""
        try:
            results = self.model(frame, verbose=False)
            detections = []
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    # Get class name
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id].lower()
                    
                    # Check if we care about this class
                    if class_name not in self.classes:
                        continue
                    
                    # Get confidence
                    confidence = float(box.conf[0])
                    
                    # Get bounding box
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    detections.append({
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2]
                    })
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []


# ============================================================================
# VIDEO CAPTURE
# ============================================================================

class VideoCapture:
    """Handle video capture from camera."""
    
    def __init__(self, camera_index: int = 0, camera_url: str = ''):
        self.camera_index = camera_index
        self.camera_url = camera_url
        self.cap = None
        self._open()
    
    def _open(self):
        """Open video capture."""
        if self.camera_url:
            # IP camera or RTSP stream
            self.cap = cv2.VideoCapture(self.camera_url)
        else:
            # Local camera
            self.cap = cv2.VideoCapture(self.camera_index)
        
        if self.cap.isOpened():
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, FPS)
            logger.info(f"Camera opened: {FRAME_WIDTH}x{FRAME_HEIGHT} @ {FPS}fps")
        else:
            logger.error("Failed to open camera")
    
    def read(self):
        """Read frame."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            return ret, frame
        return False, None
    
    def release(self):
        """Release camera."""
        if self.cap:
            self.cap.release()


# ============================================================================
# VIDEO RECORDER
# ============================================================================

class VideoRecorder:
    """Record video clips."""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.writer = None
        self.recording = False
        self.start_time = None
    
    def start_recording(self, frame):
        """Start recording a clip."""
        if self.recording:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"clip_{timestamp}.mp4"
        
        # Get frame dimensions
        h, w = frame.shape[:2]
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            FPS,
            (w, h)
        )
        
        self.recording = True
        self.start_time = time.time()
        self.current_path = output_path
        logger.info(f"Started recording: {output_path}")
    
    def write_frame(self, frame):
        """Write frame to recording."""
        if self.recording and self.writer:
            self.writer.write(frame)
    
    def stop_recording(self):
        """Stop recording."""
        if self.recording and self.writer:
            self.writer.release()
            self.writer = None
            duration = time.time() - self.start_time
            logger.info(f"Stopped recording: {self.current_path} ({duration:.1f}s)")
            self.recording = False
            return str(self.current_path)
        return None
    
    def should_keep_recording(self):
        """Check if should keep recording."""
        if not self.recording:
            return False
        return (time.time() - self.start_time) < RECORD_DURATION


# ============================================================================
# SECURITY CAMERA MAIN
# ============================================================================

class SecurityCamera:
    """Main security camera system."""
    
    def __init__(self):
        # Initialize components
        self.capture = VideoCapture(CAMERA_INDEX, CAMERA_URL)
        self.detector = DetectionEngine()
        self.recorder = VideoRecorder(RECORDING_DIR)
        self.alerts = AlertManager()
        
        # State
        self.running = False
        self.frame_count = 0
        self.last_detection = None
        
        logger.info("Security Camera initialized")
    
    def process_frame(self, frame) -> List[Dict]:
        """Process a single frame."""
        self.frame_count += 1
        
        # Skip frames for performance
        if self.frame_count % DETECTION_INTERVAL != 0:
            return []
        
        # Detect objects
        detections = self.detector.detect(frame)
        
        # Draw bounding boxes
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            label = f"{det['class']} {det['confidence']:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1)-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Handle detections
        if detections:
            self.handle_detections(frame, detections)
        
        # Draw info overlay
        self.draw_overlay(frame)
        
        return detections
    
    def handle_detections(self, frame, detections: List[Dict]):
        """Handle detected objects."""
        # Get unique classes detected
        classes = set(d['class'] for d in detections)
        
        # Save snapshot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_path = Path(LOG_DIR) / f"alert_{timestamp}.jpg"
        cv2.imwrite(str(snapshot_path), frame)
        
        # Queue alert
        message = f"Detected: {', '.join(classes)}"
        self.alerts.queue_alert('detection', message, str(snapshot_path))
        
        # Start recording
        if RECORD_ON_DETECTION:
            self.recorder.start_recording(frame)
        
        self.last_detection = time.time()
    
    def draw_overlay(self, frame):
        """Draw info overlay on frame."""
        # Timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Recording indicator
        if self.recorder.recording:
            cv2.circle(frame, (FRAME_WIDTH-30, 30), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (FRAME_WIDTH-70, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Detection indicator
        if self.last_detection and (time.time() - self.last_detection) < 5:
            cv2.putText(frame, "MOTION DETECTED", (10, FRAME_HEIGHT-20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    def run(self):
        """Main loop."""
        self.running = True
        logger.info("Starting security camera...")
        
        try:
            while self.running:
                ret, frame = self.capture.read()
                
                if not ret:
                    logger.warning("Failed to read frame")
                    time.sleep(1)
                    continue
                
                # Process frame
                detections = self.process_frame(frame)
                
                # Write to recording if active
                if self.recorder.recording:
                    self.recorder.write_frame(frame)
                    if not self.recorder.should_keep_recording():
                        self.recorder.stop_recording()
                
                # Display (optional)
                cv2.imshow('Security Camera', frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self.running = False
        self.capture.release()
        self.recorder.stop_recording()
        cv2.destroyAllWindows()
        logger.info("Security camera stopped")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("="*60)
    print("AI-Powered Security Camera")
    print("="*60)
    
    camera = SecurityCamera()
    camera.run()
```

### Step 5: Configure Notifications

Create `.env` file:

```bash
# Detection
DETECTION_CLASSES=person,car,truck,dog,cat
CONFIDENCE_THRESHOLD=0.5

# Telegram Alerts
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email Alerts
EMAIL_ENABLED=false
EMAIL_SMTP=smtp.gmail.com
EMAIL_PORT=587
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=destination@example.com
EMAIL_PASSWORD=your_app_password

# Recording
RECORD_ON_DETECTION=true
RECORD_DURATION=10
```

### Step 6: Run the System

```bash
# Run the security camera
cd ~/ai-projects/security-camera
python3 security_camera.py
```

---

## Advanced Configuration

### Telegram Setup

1. Start a chat with @BotFather
2. Create a new bot
3. Get the bot token
4. Start a chat with your bot
5. Get your chat ID from @userinfobot

### Custom Detection Classes

```bash
# Available YOLO classes:
# person, bicycle, car, motorcycle, airplane, bus, train, truck, boat
# traffic light, fire hydrant, stop sign, parking meter, bench
# bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe
# backpack, umbrella, handbag, tie, suitcase, frisbee, skis, snowboard
# sports ball, kite, baseball bat, baseball glove, skateboard
# surfboard, tennis racket, bottle, wine glass, cup, fork, knife, spoon
# bowl, banana, apple, sandwich, orange, broccoli, carrot, hot dog
# pizza, donut, cake, chair, couch, potted plant, bed, dining table
# toilet, tv, laptop, mouse, remote, keyboard, cell phone, microwave
# oven, toaster, sink, refrigerator, book, clock, vase, scissors
# teddy bear, hair drier, toothbrush
```

---

## Deployment

### Systemd Service

```ini
# /etc/systemd/system/security-camera.service
[Unit]
Description=AI Security Camera
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ai-projects/security-camera
ExecStart=/usr/bin/python3 /home/ubuntu/ai-projects/security-camera/security_camera.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable security-camera
sudo systemctl start security-camera
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not opening | Check camera index or URL |
| Low FPS | Reduce resolution or skip frames |
| Too many alerts | Increase confidence threshold |
| Telegram not working | Check bot token and chat ID |

---

## Next Steps

| Enhancement | Description |
|-------------|-------------|
| [Multi-camera](10-multi-camera-analytics.md) | Multiple camera streams |
| [Real-time Tracking](11-realtime-tracking.md) | Object tracking |

---

## License

MIT License
