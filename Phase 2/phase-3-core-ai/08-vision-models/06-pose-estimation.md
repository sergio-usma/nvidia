# Pose Estimation

This guide covers pose estimation on Jetson AGX Orin.

## OpenPose

```bash
# Install OpenPose
git clone https://github.com/CMU-Perceptual-Computing-Lab/openpose
cd openpose
mkdir build && cd build
cmake .. -DCUDA_ARCH_BIN=8.7
make -j$(nproc)
```

## MediaPipe

```bash
pip install mediapipe
```

```python
import mediapipe as mp
import cv2

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=True
)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    
    if results.pose_landmarks:
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )
    
    cv2.imshow('Pose', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## TorchVision Pose Estimation

```python
import torch
import torchvision.models.detection as detection
import torchvision.transforms as T

# Load model
model = detection.keypointrcnn_resnet50_fpn(pretrained=True)
model.eval()

# Transform
transform = T.Compose([T.ToTensor()])

# Detect
img = cv2.imread('person.jpg')
img_tensor = transform(img)

with torch.no_grad():
    predictions = model([img_tensor])

# Get keypoints
keypoints = predictions[0]['keypoints']
scores = predictions[0]['scores']

# Draw
for kp in keypoints:
    if kp[2] > 0.5:  # confidence threshold
        x, y = kp[0].int().tolist(), kp[1].int().tolist()
        cv2.circle(img, (x, y), 3, (0, 255, 0), -1)
```

## MoveNet

```bash
pip install tensorflow
```

```python
import tensorflow as tf
import cv2
import numpy as np

# Load MoveNet
interpreter = tf.lite.Interpreter(model_path="movenet_single_pose_lightning_3.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Resize and normalize
    img = cv2.resize(frame, (192, 192))
    img = np.expand_dims(img, axis=0)
    img = img.astype(np.float32) / 127.5 - 1
    
    interpreter.set_tensor(input_details[0]['index'], img)
    interpreter.invoke()
    
    keypoints = interpreter.get_tensor(output_details[0]['index'])
    # Process keypoints
    
    cv2.imshow('MoveNet', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
```

## BodyPix

```python
from pixellib.torchbackend.instance import instanceSegmentation

ins = instanceSegmentation()
ins.load_model("pointrend_resnet50.pkl")

# Segment person
target_classes = ins.select_target_classes(person=True)
result_image, segmap = ins.segmentImage(
    "input.jpg",
    segment_target_classes=target_classes
)
```

## Pose Classification

```python
import numpy as np

def calculate_angle(a, b, c):
    """Calculate angle between three points"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    ba = a - b
    bc = c - b
    
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine, -1, 1))
    return np.degrees(angle)

# Example: Detect squat
def detect_squat(landmarks):
    hip = landmarks[24]
    knee = landmarks[26]
    ankle = landmarks[28]
    
    angle = calculate_angle(hip, knee, ankle)
    
    if angle < 90:
        return "squat"
    elif angle < 160:
        return "standing"
    return "walking"
```

## Real-time Pose Analysis

```python
import cv2
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)
    
    if results.pose_landmarks:
        # Get specific landmarks
        left_shoulder = results.pose_landmarks.landmark[11]
        right_shoulder = results.pose_landmarks.landmark[12]
        
        # Draw
        h, w, _ = frame.shape
        cv2.circle(frame, (int(left_shoulder.x*w), int(left_shoulder.y*h)), 
                   5, (0, 255, 0), -1)
    
    cv2.imshow('Pose', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
```

## TensorRT Pose Model

```python
import tensorrt as trt

# Convert to TensorRT for faster inference
# Use trtexe:
# trtexec --onnx=pose_model.onnx --saveEngine=pose_model.trt
```

## Gesture Recognition

```python
import mediapipe as mp

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7
)

def get_gesture(landmarks):
    # Simple gesture detection
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    
    distance = ((thumb_tip.x - index_tip.x)**2 + 
                (thumb_tip.y - index_tip.y)**2)**0.5
    
    if distance < 0.05:
        return "pinch"
    return "open"
```
