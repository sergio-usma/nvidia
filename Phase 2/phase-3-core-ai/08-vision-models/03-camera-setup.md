# Camera Setup for Jetson

This guide covers camera setup for Jetson AGX Orin with libcamera and GStreamer.

## Check Camera Support

```bash
# List video devices
ls /dev/video*

# Check libcamera
libcamera-hello

# List available cameras
libcamera-kmd
```

## Install Camera Tools

```bash
sudo apt update
sudo apt install libcamera-apps libcamera-utils
```

## Test Camera

```bash
# Preview camera
libcamera-hello

# Capture image
libcamera-still -o test.jpg

# Record video
libcamera-vid -o video.h264 --duration 5
```

## GStreamer Pipeline

```bash
# View camera with GStreamer
gst-launch-1.0 nvarguscamerasrc ! \
    "video/x-raw(memory:NVMM),width=1920,height=1080,format=NV12" ! \
    nvvidconv ! \
    xvimagesink

# Record to file
gst-launch-1.0 nvarguscamerasrc ! \
    "video/x-raw(memory:NVMM),width=1920,height=1080" ! \
    nvvidconv ! \
    filesink location=video.mp4
```

## Python with OpenCV

```python
import cv2

# Open default camera
cap = cv2.VideoCapture(0)

# Set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Read frame
ret, frame = cap.read()
cv2.imwrite('capture.jpg', frame)

cap.release()
```

## Python with GStreamer

```python
import cv2
import numpy as np

def gstreamer_pipeline(
    capture_width=1920,
    capture_height=1080,
    display_width=640,
    display_height=480,
    framerate=30,
    flip=0
):
    return (
        f"nvarguscamerasrc ! "
        f"video/x-raw(memory:NVMM),"
        f"width=(int){capture_width},height=(int){capture_height},"
        f"format=(string)NV12,framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip} ! "
        f"video/x-raw,width=(int){display_width},height=(int){display_height},"
        f"format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw,format=(string)BGR ! appsink"
    )

# Use pipeline
cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow('Camera', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## Multiple Cameras

```python
# CSI Camera 0
cap0 = cv2.VideoCapture(
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM),format=NV12 ! "
    "nvvidconv ! appsink"
)

# CSI Camera 1
cap1 = cv2.VideoCapture(
    "nvarguscamerasrc sensor-id=1 ! "
    "video/x-raw(memory:NVMM),format=NV12 ! "
    "nvvidconv ! appsink"
)
```

## USB Camera

```bash
# List USB cameras
v4l2-ctl --list-devices

# Test
guvcview
```

## USB Camera in Python

```python
import cv2

# Try different indices
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Camera found at index {i}")
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f'camera_{i}.jpg', frame)
        cap.release()
        break
```

## Camera Calibration

```python
import cv2
import numpy as np
import glob

# Prepare object points
objp = np.zeros((6*9, 3), np.float32)
objp[:,:2] = np.mgrid[0:9,0:6].T.reshape(-1,2)

objpoints = []
imgpoints = []

images = glob.glob('calib/*.jpg')

for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    ret, corners = cv2.findChessboardCorners(gray, (9,6), None)
    
    if ret:
        objpoints.append(objp)
        imgpoints.append(corners)

# Calibrate
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

print("Camera matrix:", mtx)
print("Distortion:", dist)

# Save
np.save('camera_matrix.npy', mtx)
np.save('distortion_coeffs.npy', dist)
```

## Camera Performance Tips

```python
# Use NVMM memory for better performance
pipeline = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM),width=1280,height=720,format=NV12 ! "
    "nvvidconv ! appsink drop=true"
)
```

## Troubleshooting

```bash
# Check camera status
cat /proc/camera

# Check device
v4l2-ctl --device=/dev/video0 --info

# Kill processes using camera
fuser -v /dev/video0

# Rebind camera
echo 0 > /sys/bus/platform/devices/tegra-camrtc-caam/bind
echo tegra-camrtc-caam > /sys/bus/platform/drivers/tegra-camrtc-caam/bind
```
