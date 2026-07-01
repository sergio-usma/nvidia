# Video Analysis

This guide covers video analysis and processing on Jetson AGX Orin.

## Video Capture

```python
import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FPS, 30)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## Video Writer

```python
import cv2

cap = cv2.VideoCapture(0)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (640, 480))

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    out.write(frame)
    cv2.imshow('Recording', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
```

## Frame-by-Frame Processing

```python
import cv2
import numpy as np

cap = cv2.VideoCapture('video.mp4')
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

frame_idx = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # Process frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    frame_idx += 1
    
cap.release()
```

## Motion Detection

```python
import cv2
import numpy as np

cap = cv2.VideoCapture(0)
ret, frame1 = cap.read()
gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)

while True:
    ret, frame2 = cap.read()
    if not ret:
        break
    
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
    
    diff = cv2.absdiff(gray1, gray2)
    thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, 
                                    cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        if cv2.contourArea(contour) > 500:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame2, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    cv2.imshow('Motion', frame2)
    gray1 = gray2
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## Object Tracking

```python
import cv2

cap = cv2.VideoCapture(0)
tracker = cv2.TrackerCSRT_create()

ret, frame = cap.read()
bbox = cv2.selectROI(frame, False)
tracker.init(frame, bbox)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    success, bbox = tracker.update(frame)
    
    if success:
        x, y, w, h = [int(v) for v in bbox]
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    cv2.imshow('Tracking', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## Optical Flow

```python
import cv2
import numpy as np

cap = cv2.VideoCapture(0)
ret, old_frame = cap.read()
old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    flow = cv2.calcOpticalFlowFarneback(
        old_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
    )
    
    h, w = gray.shape
    hsv = np.zeros_like(frame)
    hsv[..., 1] = 255
    
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    hsv[..., 0] = ang * 180 / np.pi / 2
    hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    cv2.imshow('Optical Flow', rgb)
    
    old_gray = gray.copy()
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## Video Stabilization

```python
import cv2

cap = cv2.VideoCapture('video.mp4')
ret, frame = cap.read()
prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('stabilized.mp4', fourcc, 30, 
                      (frame.shape[1], frame.shape[0]))

transforms = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    pts = cv2.goodFeaturesToTrack(prev_gray, maxCorners=200,
                                   qualityLevel=0.01, minDistance=30)
    
    if pts is not None:
        pts_next, status, err = cv2.calcOpticalFlowPyrLK(
            prev_gray, gray, pts, None
        )
        
        if pts_next is not None:
            transform = cv2.estimateRigidTransform(pts, pts_next, False)
            if transform is not None:
                transforms.append(transform)
                
                stabilized = cv2.warpAffine(frame, transform, 
                                           (frame.shape[1], frame.shape[0]))
                out.write(stabilized)
    
    prev_gray = gray

cap.release()
out.release()
```

## Video Summarization

```python
import cv2
import numpy as np

def extract_frames(video_path, sample_rate=30):
    """Extract key frames from video"""
    cap = cv2.VideoCapture(video_path)
    frames = []
    
    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % sample_rate == 0:
            frames.append(frame)
        
        frame_idx += 1
    
    cap.release()
    return frames

def compute_frame_diff(frames):
    """Find frames with significant changes"""
    diffs = []
    for i in range(1, len(frames)):
        diff = np.sum(np.abs(frames[i] - frames[i-1]))
        diffs.append(diff)
    
    # Return top N diverse frames
    top_indices = np.argsort(diffs)[-10:]
    return [frames[i] for i in top_indices]
```

## Background Subtraction

```python
import cv2

fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    fgmask = fgbg.apply(frame)
    
    # Remove shadows (optional)
    fgmask[fgmask == 127] = 0
    
    cv2.imshow('Foreground', fgmask)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## FPS Counter

```python
import cv2
import time

cap = cv2.VideoCapture(0)
fps = 0
frame_count = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    elapsed = time.time() - start_time
    
    if elapsed >= 1:
        fps = frame_count / elapsed
        frame_count = 0
        start_time = time.time()
    
    cv2.putText(frame, f'FPS: {fps:.1f}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow('FPS', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```
