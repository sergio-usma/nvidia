# Face Detection and Recognition

This guide covers face detection and recognition on Jetson AGX Orin.

## Install Dependencies

```bash
pip install opencv-python face_recognition dlib
```

## Haar Cascade Face Detection

```python
import cv2

# Load cascade
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# Detect faces
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
faces = face_cascade.detectMultiScale(
    gray,
    scaleFactor=1.1,
    minNeighbors=5,
    minSize=(30, 30)
)

# Draw rectangles
for (x, y, w, h) in faces:
    cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)

cv2.imwrite('faces_detected.jpg', image)
```

## DNN Face Detection

```python
import cv2

# Load model
prototxt = "deploy.prototxt"
caffemodel = "res10_300x300_ssd_iter_140000.caffemodel"
net = cv2.dnn.readNetFromCaffe(prototxt, caffemodel)

# Preprocess
blob = cv2.dnn.blobFromImage(
    cv2.resize(image, (300, 300)),
    1.0, (300, 300), (104.0, 177.0, 123.0)
)
net.setInput(blob)
detections = net.forward()

# Draw detections
for i in range(detections.shape[2]):
    confidence = detections[0, 0, i, 2]
    if confidence > 0.5:
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        (x, y, xE, yE) = box.astype("int")
        cv2.rectangle(image, (x, y), (xE, yE), (0, 255, 0), 2)
```

## Face Recognition with face_recognition

```python
import face_recognition
import cv2

# Load known faces
known_encodings = []
known_names = []

# Load and encode known images
for name, image_path in known_faces.items():
    image = face_recognition.load_image_file(image_path)
    encoding = face_recognition.face_encodings(image)[0]
    known_encodings.append(encoding)
    known_names.append(name)

# Process frame
unknown_image = face_recognition.load_image_file("test.jpg")
unknown_encodings = face_recognition.face_encodings(unknown_image)

for unknown_encoding in unknown_encodings:
    matches = face_recognition.compare_faces(known_encodings, unknown_encoding)
    name = "Unknown"
    
    if True in matches:
        matched_idx = matches.index(True)
        name = known_names[matched_idx]
    
    print(f"Found: {name}")
```

## Face Recognition with DeepFace

```bash
pip install deepface
```

```python
from deepface import DeepFace

# Find identity
result = DeepFace.find(
    img_path="test.jpg",
    db_path="faces_db/",
    model_name="VGG-Face"
)

# Verify faces
result = DeepFace.verify(
    img1_path="person1.jpg",
    img2_path="person2.jpg",
    model_name="Facenet"
)
```

## Face Landmark Detection

```python
import dlib
import numpy as np
import cv2

# Load detector and predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# Detect
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
faces = detector(gray)

for face in faces:
    landmarks = predictor(gray, face)
    
    # Draw landmarks
    for n in range(68):
        x = landmarks.part(n).x
        y = landmarks.part(n).y
        cv2.circle(image, (x, y), 2, (0, 255, 0), -1)
```

## Real-time Face Detection

```python
import cv2

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
    
    cv2.imshow('Face Detection', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## NVIDIA DeepStream

```bash
# Install DeepStream
sudo apt install deepstream-6.2

# Run face detection pipeline
deepstream-app -c config_face_detection.txt
```

## Performance Comparison

| Method | Speed | Accuracy | GPU |
|--------|-------|----------|-----|
| Haar Cascade | Very Fast | Low | No |
| DNN | Medium | High | Yes |
| face_recognition | Slow | Medium | No |
| DeepFace | Slow | Very High | Optional |

## Liveness Detection

```python
import cv2
import numpy as np

def detect_blink(eye_points, facial_landmarks):
    # Check eye aspect ratio
    left_eye = facial_landmarks[eye_points[0]:eye_points[1]]
    right_eye = facial_landmarks[eye_points[2]:eye_points[3]]
    
    def eye_aspect_ratio(eye):
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        return (A + B) / (2.0 * C)
    
    return eye_aspect_ratio(left_eye), eye_aspect_ratio(right_eye)
```

## Mask Detection

```python
# Using pretrained model
import cv2

net = cv2.dnn.readNet("mask_detector.model", "mask_detector.xml")

blob = cv2.dnn.blobFromImage(img, 1/255, (224, 224))
net.setInput(blob)
preds = net.forward()

# 0 = with mask, 1 = without mask
label = "Mask" if preds[0][0] > preds[0][1] else "No Mask"
```
