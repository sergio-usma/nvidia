# OpenCV Installation and Basics

This guide covers OpenCV installation and computer vision basics for Jetson AGX Orin with JetPack 6.2.2.

## Install OpenCV

### From pip (CPU only)

```bash
pip install opencv-python
pip install opencv-contrib-python
```

### With CUDA support (Jetson optimized)

```bash
# Install from NVIDIA repo
sudo apt update
sudo apt install libopencv-python

# Or build from source with CUDA
# See advanced section below
```

## Verify Installation

```python
import cv2
print(cv2.__version__)

# Check CUDA support
print(cv2.cuda.getCudaEnabledDeviceCount())
```

## Reading Images

```python
import cv2
import numpy as np
from PIL import Image

# Read image
img = cv2.imread('image.jpg')

# Read as grayscale
gray = cv2.imread('image.jpg', cv2.IMREAD_GRAYSCALE)

# Read with PIL and convert
pil_img = Image.open('image.jpg')
img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
```

## Display Images

```python
import cv2

img = cv2.imread('image.jpg')

# Show image
cv2.imshow('Image', img)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Save image
cv2.imwrite('output.jpg', img)
```

## Basic Operations

```python
import cv2
import numpy as np

# Get image properties
height, width, channels = img.shape
size = img.size
dtype = img.dtype

# Resize
resized = cv2.resize(img, (width//2, height//2))
resized = cv2.resize(img, (800, 600))

# Crop
cropped = img[y:y+h, x:x+w]

# Rotate
(h, w) = img.shape[:2]
center = (w // 2, h // 2)
M = cv2.getRotationMatrix2D(center, 45, 1.0)
rotated = cv2.warpAffine(img, M, (w, h))

# Flip
flipped = cv2.flip(img, 0)  # vertical
flipped = cv2.flip(img, 1)  # horizontal
```

## Color Spaces

```python
# Convert color spaces
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Convert back
bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
```

## Drawing

```python
import cv2
import numpy as np

# Blank image
canvas = np.zeros((500, 500, 3), dtype=np.uint8)

# Line
cv2.line(canvas, (0, 0), (500, 500), (0, 255, 0), 2)

# Rectangle
cv2.rectangle(canvas, (100, 100), (400, 400), (255, 0, 0), 2)

# Circle
cv2.circle(canvas, (250, 250), 100, (0, 0, 255), -1)

# Text
cv2.putText(canvas, 'Hello', (50, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
```

## Image Processing

```python
# Blur
blur = cv2.GaussianBlur(img, (5, 5), 0)
blur = cv2.medianBlur(img, 5)
blur = cv2.bilateralFilter(img, 9, 75, 75)

# Thresholding
_, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 11, 2)

# Edge detection
edges = cv2.Canny(gray, 50, 150)

# Morphological
kernel = np.ones((5, 5), np.uint8)
erosion = cv2.erode(img, kernel, iterations=1)
dilation = cv2.dilate(img, kernel, iterations=1)
opening = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
closing = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
```

## Contours

```python
# Find contours
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, 
                                        cv2.CHAIN_APPROX_SIMPLE)

# Draw contours
cv2.drawContours(img, contours, -1, (0, 255, 0), 2)

# Largest contour
largest = max(contours, key=cv2.contourArea)

# Bounding box
x, y, w, h = cv2.boundingRect(largest)
cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
```

## Video Capture

```python
import cv2

# Open camera
cap = cv2.VideoCapture(0)
cap = cv2.VideoCapture('/dev/video0')

# Set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    cv2.imshow('Frame', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## CUDA Acceleration

```python
import cv2

# Check CUDA
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    # Upload to GPU
    gpu_frame = cv2.cuda_GpuMat()
    gpu_frame.upload(frame)
    
    # Process on GPU
    gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2GRAY)
    
    # Download result
    gray = gpu_gray.download()
```

## Object Detection Template

```python
import cv2

# Initialize camera
cap = cv2.VideoCapture(0)

# Load pre-trained models (example with Haar Cascade)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Detect faces
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    # Draw rectangles
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
    
    cv2.imshow('Face Detection', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## Performance Optimization

```python
# Use GPU if available
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    # CUDA processing
    pass

# Use NumPy optimizations
img_float = np.float32(img) / 255.0

# Resize with INTER_AREA for downscaling
resized = cv2.resize(img, (w//2, h//2), interpolation=cv2.INTER_AREA)

# Grayscale conversion once
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
```
