# Project 11: Real-Time Object Tracking System

A comprehensive guide to building an advanced multi-object tracking system using DeepSort and YOLO for real-time tracking of people and vehicles with trajectory analysis on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Hardware Optimization](#hardware-optimization)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [What You'll Build](#what-youll-build)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Create DeepSort Tracker](#step-3-create-deepsort-tracker)
   - [Step 4: Create Tracking Application](#step-4-create-tracking-application)
   - [Step 5: Create Web Visualization](#step-5-create-web-visualization)
7. [Running the System](#running-the-system)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates an advanced object tracking system:

- **Multi-Object Tracking**: Track multiple objects simultaneously
- **Unique IDs**: Each object gets a persistent ID
- **Trajectory Visualization**: Draw movement paths
- **Re-Identification**: Maintain identity across frames
- **Motion Prediction**: Kalman filter smoothing
- **Zone Analytics**: Count objects in regions
- **Web Interface**: Real-time visualization

### Why DeepSort?

| Feature | Benefit |
|---------|---------|
| Kalman Filtering | Smooth tracking |
| Hungarian Algorithm | Optimal assignment |
| Appearance Features | Re-ID capability |
| IoU Matching | Robust association |
| Real-time | 30+ FPS possible |

---

## Hardware Optimization

### Jetson AGX Orin

| Component | Specification |
|-----------|---------------|
| GPU | NVIDIA Ampere 64 cores |
| Memory | 64GB Unified |
| CUDA | 12.6 |
| TensorRT | 10.3 |

### Optimization Settings

```bash
# Maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Real-Time Tracking Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │   Video     │─────▶│    YOLO      │─────▶│   Feature   │           │
│   │   Frame     │      │   Detector   │      │  Extractor  │           │
│   └──────────────┘      └──────────────┘      └──────┬───────┘           │
│                                                       │                    │
│                                                       ▼                    │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                         DEEP SORT TRACKER                          │ │
│   │                                                                      │ │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │ │
│   │  │  Kalman  │───▶│ Hungarian│───▶│   Track │───▶│   ID    │      │ │
│   │  │  Filter  │    │Matching  │    │ Management│   │ Assign  │      │ │
│   │  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │ │
│   │                                                                      │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                               │                                            │
│                               ▼                                            │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │ Trajectories │      │   Analytics  │      │  Web Server  │           │
│   │   Storage    │      │   Engine     │      │  (SocketIO)  │           │
│   └──────────────┘      └──────────────┘      └──────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation |
|-----------|-------------|
| PyTorch | With CUDA support |
| YOLO | Ultralytics |
| OpenCV | Computer vision |
| Flask | Web server |

### Pre-Installation

```bash
# Check CUDA
python3 -c "import torch; print(torch.cuda.is_available())"

# Check YOLO
python3 -c "import ultralytics; print('YOLO ready')"
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Multi-Object | Track multiple objects |
| Unique IDs | Persistent tracking |
| Trajectories | Movement paths |
| Motion Prediction | Kalman filtering |
| Zone Counting | Region analytics |
| Real-time UI | Web dashboard |

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Install PyTorch with CUDA
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Install tracking dependencies
pip3 install ultralytics opencv-python
pip3 install filterpy scipy scikit-learn
pip3 install flask flask-socketio numpy pandas
```

### Step 2: Create Project Directory

```bash
mkdir -p ~/ai-projects/tracking-system
cd ~/ai-projects/tracking-system
mkdir -p tracker models static templates data
```

### Step 3: Create DeepSort Tracker

Create `tracker/deepsort.py`:

```python
#!/usr/bin/env python3
"""
DeepSort Tracker Implementation

Implementation of the DeepSort multi-object tracking algorithm
with Kalman filtering and appearance features.

Author: Your Name
Version: 1.0.0
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from scipy.optimize import linear_sum_assignment


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Detection:
    """Object detection from YOLO."""
    bbox: np.ndarray  # [x1, y1, x2, y2]
    confidence: float
    class_id: int
    class_name: str
    feature: Optional[np.ndarray] = None
    
    @property
    def xyxy(self) -> np.ndarray:
        return self.bbox
    
    @property
    def xywh(self) -> np.ndarray:
        """Convert to center x, center y, width, height format."""
        x1, y1, x2, y2 = self.bbox
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w / 2
        cy = y1 + h / 2
        return np.array([cx, cy, w, h])


@dataclass
class Track:
    """Tracked object."""
    track_id: int
    class_id: int
    class_name: str
    hits: int = 0
    age: int = 0
    time_since_update: int = 0
    state: str = 'confirmed'
    features: List[np.ndarray] = field(default_factory=list)
    bbox: np.ndarray = field(default_factory=lambda: np.zeros(4))
    
    # Kalman state
    mean: np.ndarray = field(default_factory=lambda: np.zeros(8))
    covariance: np.ndarray = field(default_factory=lambda: np.eye(8))


# ============================================================================
# KALMAN FILTER
# ============================================================================

class KalmanFilter:
    """
    Kalman filter for tracking bounding boxes.
    
    State: [cx, cy, w, h, vx, vy, vw, vh]
    """
    
    def __init__(self):
        ndim = 4  # bbox dimensions
        dt = 1.0  # time step
        
        # Motion model transition matrix
        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt
        
        # Measurement matrix
        self._update_mat = np.eye(ndim, 2 * ndim)
        
        # Motion and observation uncertainty
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160
    
    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create initial track state from unassociated detection."""
        mean_pos = measurement
        mean_vel = np.zeros_like(measurement)
        mean = np.r_[mean_pos, mean_vel]
        
        std = [
            2 * self._std_weight_position * measurement[2],
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[2],
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[2],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[2],
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        
        return mean, covariance
    
    def predict(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict next state using motion model."""
        std_pos = [
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[2],
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[2],
            self._std_weight_velocity * mean[3],
        ]
        
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))
        
        mean = np.dot(self._motion_mat, mean)
        covariance = np.linalg.multi_dot([
            self._motion_mat, covariance, self._motion_mat.T
        ]) + motion_cov
        
        return mean, covariance
    
    def project(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Project state distribution to measurement space."""
        std = [
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))
        
        mean = np.dot(self._update_mat, mean)
        covariance = np.linalg.multi_dot([
            self._update_mat, covariance, self._update_mat.T
        ])
        
        return mean, covariance + innovation_cov
    
    def update(self, mean: np.ndarray, covariance: np.ndarray, 
               measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Update state with new measurement."""
        projected_mean, projected_cov = self.project(mean, covariance)
        
        # Kalman gain
        chol_factor, lower = torch.linalg.cho_factor(
            torch.from_numpy(projected_cov), lower=True
        )
        kalman_gain = torch.linalg.cho_solve(
            chol_factor,
            torch.from_numpy(np.linalg.multi_dot([
                covariance, self._update_mat.T
            ])),
            upper=False
        ).numpy()
        
        # Innovation
        innovation = measurement - projected_mean
        
        # Update
        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_cov = covariance - np.linalg.multi_dot([
            kalman_gain, projected_cov, kalman_gain.T
        ])
        
        return new_mean, new_cov


# ============================================================================
# DEEP SORT TRACKER
# ============================================================================

class DeepSortTracker:
    """
    DeepSort multi-object tracker.
    
    Args:
        max_age: Maximum frames to keep lost tracks
        n_init: Frames to confirm track
        max_iou_distance: Maximum IoU for matching
        max_age: Frames until track is deleted
    """
    
    def __init__(
        self,
        max_iou_distance: float = 0.7,
        max_age: int = 30,
        n_init: int = 3,
        metric_name: str = 'cosine'
    ):
        self.max_iou_distance = max_iou_distance
        self.max_age = max_age
        self.n_init = n_init
        
        self.kf = KalmanFilter()
        self.tracks: List[Track] = []
        self._next_id = 1
        
        # Metric for appearance matching
        self.metric = None  # Would use cosine similarity
    
    def predict(self):
        """Propagate track state forward."""
        for track in self.tracks:
            if track.state == 'confirmed':
                track.time_since_update += 1
            
            # Kalman prediction
            track.mean, track.covariance = self.kf.predict(
                track.mean, track.covariance
            )
            
            # Age the track
            track.age += 1
    
    def update(self, detections: List[Detection]):
        """Update tracks with new detections."""
        # Run matching
        matched, unmatched_dets, unmatched_trks = self._match(detections)
        
        # Update matched tracks
        for det_idx, trk_idx in matched:
            det = detections[det_idx]
            trk = self.tracks[trk_idx]
            self._update_track(trk, det)
        
        # Initialize new tracks for unmatched detections
        for det_idx in unmatched_dets:
            det = detections[det_idx]
            self._initiate_track(det)
        
        # Mark unmatched tracks as lost
        for trk_idx in unmatched_trks:
            self.tracks[trk_idx].state = 'lost'
        
        # Remove old tracks
        self._remove_aged_tracks()
    
    def _match(self, detections: List[Detection]) -> Tuple[List, List, List]:
        """Match detections to tracks using IoU and appearance."""
        
        # Separate confirmed and unconfirmed tracks
        confirmed_tracks = [
            (i, t) for i, t in enumerate(self.tracks)
            if t.state == 'confirmed'
        ]
        
        if not confirmed_tracks or not detections:
            return [], list(range(len(detections))), [i for i, _ in confirmed_tracks]
        
        # Compute IoU distance matrix
        iou_matrix = self._compute_iou_matrix(detections, [t for _, t in confirmed_tracks])
        
        # Hungarian matching
        row_ind, col_ind = linear_sum_assignment(-iou_matrix)
        
        matched = []
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(range(len(confirmed_tracks)))
        
        for r, c in zip(row_ind, col_ind):
            if iou_matrix[r, c] < self.max_iou_distance:
                matched.append((r, c))
                unmatched_detections.remove(r)
                unmatched_tracks.remove(c)
        
        return matched, unmatched_detections, [confirmed_tracks[i][0] for i in unmatched_tracks]
    
    def _compute_iou_matrix(self, detections: List[Detection], 
                           tracks: List[Track]) -> np.ndarray:
        """Compute IoU between detections and tracks."""
        iou_matrix = np.zeros((len(detections), len(tracks)))
        
        for d, det in enumerate(detections):
            for t, track in enumerate(tracks):
                iou_matrix[d, t] = self._compute_iou(det.bbox, track.bbox)
        
        return iou_matrix
    
    def _compute_iou(self, bbox1: np.ndarray, bbox2: np.ndarray) -> float:
        """Compute IoU between two bounding boxes."""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0
    
    def _update_track(self, track: Track, detection: Detection):
        """Update track with detection."""
        # Kalman update
        measurement = detection.xywh
        track.mean, track.covariance = self.kf.update(
            track.mean, track.covariance, measurement
        )
        
        track.bbox = detection.bbox
        track.hits += 1
        track.time_since_update = 0
        track.state = 'confirmed'
        
        # Store appearance feature
        if detection.feature is not None:
            track.features.append(detection.feature)
            if len(track.features) > 100:
                track.features = track.features[-100:]
    
    def _initiate_track(self, detection: Detection):
        """Create new track from detection."""
        mean, covariance = self.kf.initiate(detection.xywh)
        
        track = Track(
            track_id=self._next_id,
            class_id=detection.class_id,
            class_name=detection.class_name,
            mean=mean,
            covariance=covariance,
            bbox=detection.bbox
        )
        
        self.tracks.append(track)
        self._next_id += 1
    
    def _remove_aged_tracks(self):
        """Remove tracks that have been lost for too long."""
        self.tracks = [
            t for t in self.tracks
            if t.time_since_update < self.max_age
        ]
    
    def get_active_tracks(self) -> List[Track]:
        """Get confirmed and active tracks."""
        return [t for t in self.tracks if t.state == 'confirmed']


# ============================================================================
# TRACKING UTILITIES
# ============================================================================

def draw_tracks(frame: np.ndarray, tracks: List[Track]) -> np.ndarray:
    """Draw tracking visualization on frame."""
    import cv2
    
    # Define colors for different classes
    colors = {
        'person': (255, 0, 0),
        'car': (0, 255, 0),
        'truck': (0, 0, 255),
        'bus': (255, 255, 0),
    }
    
    for track in tracks:
        bbox = track.bbox.astype(int)
        color = colors.get(track.class_name, (128, 128, 128))
        
        # Draw rectangle
        cv2.rectangle(
            frame,
            (bbox[0], bbox[1]),
            (bbox[2], bbox[3]),
            color,
            2
        )
        
        # Draw ID
        label = f"ID:{track.track_id} {track.class_name}"
        cv2.putText(
            frame, label,
            (bbox[0], bbox[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, color, 2
        )
    
    return frame
```

### Step 4: Create Tracking Application

Create `tracking_app.py`:

```python
#!/usr/bin/env python3
"""
Real-Time Object Tracking Application

Main application for multi-object tracking with YOLO and DeepSort.
Features real-time visualization, trajectory storage, and analytics.

Author: Your Name
Version: 1.0.0
"""

import cv2
import numpy as np
import torch
import time
import json
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

from ultralytics import YOLO
from tracker.deepsort import DeepSortTracker, Detection, draw_tracks

# Configuration
MODEL_NAME = 'yolov8n.pt'
TRACK_CLASSES = ['person', 'car', 'truck', 'bus', 'bicycle', 'motorcycle']
MAX_AGE = 30
N_INIT = 3

# ============================================================================
# TRACKING APPLICATION
# ============================================================================

class TrackingApp:
    """Main tracking application."""
    
    def __init__(self, camera_index: int = 0, camera_url: str = ''):
        # Initialize YOLO
        print(f"Loading YOLO model: {MODEL_NAME}")
        self.model = YOLO(MODEL_NAME)
        
        # Move to GPU if available
        if torch.cuda.is_available():
            self.model.to('cuda')
        
        # Initialize tracker
        self.tracker = DeepSortTracker(
            max_iou_distance=0.7,
            max_age=MAX_AGE,
            n_init=N_INIT
        )
        
        # Camera
        self.camera_index = camera_index
        self.camera_url = camera_url
        self.cap = None
        
        # Analytics
        self.track_history = defaultdict(list)
        self.class_counts = defaultdict(int)
        
        # Open camera
        self._open_camera()
    
    def _open_camera(self):
        """Open video capture."""
        if self.camera_url:
            self.cap = cv2.VideoCapture(self.camera_url)
        else:
            self.cap = cv2.VideoCapture(self.camera_index)
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print(f"Camera opened: {self.cap.isOpened()}")
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLO detection on frame."""
        results = self.model(frame, verbose=False)[0]
        
        detections = []
        for r in results.boxes:
            class_id = int(r.cls[0])
            class_name = self.model.names[class_id]
            
            # Filter by class
            if class_name not in TRACK_CLASSES:
                continue
            
            bbox = r.xyxy[0].cpu().numpy()
            confidence = float(r.conf[0])
            
            detection = Detection(
                bbox=bbox,
                confidence=confidence,
                class_id=class_id,
                class_name=class_name
            )
            detections.append(detection)
        
        return detections
    
    def process_frame(self, frame: np.ndarray) -> List:
        """Process single frame."""
        # Detect
        detections = self.detect(frame)
        
        # Update tracker
        self.tracker.predict()
        self.tracker.update(detections)
        
        # Get active tracks
        tracks = self.tracker.get_active_tracks()
        
        # Update analytics
        for track in tracks:
            center = [
                (track.bbox[0] + track.bbox[2]) / 2,
                (track.bbox[1] + track.bbox[3]) / 2
            ]
            self.track_history[track.track_id].append(center)
            
            # Limit history length
            if len(self.track_history[track.track_id]) > 100:
                self.track_history[track.track_id] = \
                    self.track_history[track.track_id][-100:]
            
            self.class_counts[track.class_name] += 1
        
        return tracks
    
    def draw_visualization(self, frame: np.ndarray, tracks: List) -> np.ndarray:
        """Draw tracking visualization."""
        # Draw tracks
        frame = draw_tracks(frame, tracks)
        
        # Draw trajectory
        for track_id, trajectory in self.track_history.items():
            if len(trajectory) < 2:
                continue
            
            # Draw line
            for i in range(1, len(trajectory)):
                pt1 = (int(trajectory[i-1][0]), int(trajectory[i-1][1]))
                pt2 = (int(trajectory[i][0]), int(trajectory[i][1]))
                cv2.line(frame, pt1, pt2, (0, 255, 255), 2)
        
        # Draw stats
        y_offset = 30
        cv2.putText(
            frame, f"Tracks: {len(tracks)}",
            (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (0, 255, 0), 2
        )
        
        return frame
    
    def run(self):
        """Main loop."""
        print("Starting tracking...")
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Process
                start_time = time.time()
                tracks = self.process_frame(frame)
                process_time = time.time() - start_time
                
                # Visualize
                frame = self.draw_visualization(frame, tracks)
                
                # Show FPS
                fps = 1 / process_time if process_time > 0 else 0
                cv2.putText(
                    frame, f"FPS: {fps:.1f}",
                    (frame.shape[1] - 150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )
                
                # Display
                cv2.imshow('Tracking', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        except KeyboardInterrupt:
            print("Interrupted")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        
        # Save analytics
        print("\nTracking Statistics:")
        print(f"Total tracks: {len(self.track_history)}")
        print(f"Class counts: {dict(self.class_counts)}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Object Tracking')
    parser.add_argument('--camera', type=int, default=0, help='Camera index')
    parser.add_argument('--url', type=str, default='', help='RTSP URL')
    parser.add_argument('--model', type=str, default='yolov8n.pt', help='YOLO model')
    
    args = parser.parse_args()
    
    app = TrackingApp(args.camera, args.url)
    app.run()
```

### Step 5: Create Web Visualization

Create `templates/tracking.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Real-Time Tracking</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <style>
        body { font-family: Arial; margin: 20px; background: #1a1a2e; color: white; }
        #video { max-width: 100%; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat { background: #16213e; padding: 20px; border-radius: 10px; }
    </style>
</head>
<body>
    <h1>🎯 Real-Time Object Tracking</h1>
    
    <div class="stats">
        <div class="stat">
            <h3>Active Tracks</h3>
            <div id="track-count" style="font-size: 2em;">0</div>
        </div>
        <div class="stat">
            <h3>FPS</h3>
            <div id="fps" style="font-size: 2em;">0</div>
        </div>
    </div>
    
    <img id="video" />
    
    <script>
        const socket = io();
        
        socket.on('frame', (data) => {
            document.getElementById('video').src = 'data:image/jpeg;base64,' + data.image;
            document.getElementById('track-count').textContent = data.tracks;
            document.getElementById('fps').textContent = data.fps.toFixed(1);
        });
    </script>
</body>
</html>
```

---

## Running the System

```bash
# Run tracking
python3 tracking_app.py

# Or with specific camera
python3 tracking_app.py --camera 0
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No detections | Check YOLO model |
| Low FPS | Use smaller model (yolov8n) |
| ID switching | Tune max_age and n_init |

---

## License

MIT License
