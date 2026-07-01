# Image Classification

This guide covers image classification on Jetson AGX Orin with various models.

## TorchVision Models

```python
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

# Load pretrained model
model = models.resnet50(pretrained=True)
model.eval()

# Preprocessing
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# Load and preprocess image
img = Image.open('image.jpg')
img_tensor = transform(img).unsqueeze(0)

# Classify
with torch.no_grad():
    output = model(img_tensor)
    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    top5_prob, top5_idx = torch.topk(probabilities, 5)

# Load labels
with open('imagenet_classes.txt') as f:
    classes = [line.strip() for line in f.readlines()]

# Print results
for idx in top5_idx:
    print(f"{classes[idx]}: {probabilities[idx].item():.4f}")
```

## MobileNet for Edge

```python
import torchvision.models as models

# Lightweight model for Jetson
model = models.mobilenet_v3_small(pretrained=True)
model.eval()

# Use with quantization for better performance
model_quantized = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)
```

## TensorFlow/Keras

```bash
pip install tensorflow
```

```python
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2

# Load model
model = MobileNetV2(weights='imagenet')

# Preprocess
img = tf.keras.preprocessing.image.load_img('image.jpg', target_size=(224, 224))
img_array = tf.keras.preprocessing.image.img_to_array(img)
img_array = tf.expand_dims(img_array, 0)
img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)

# Predict
predictions = model.predict(img_array)
decoded = tf.keras.applications.mobilenet_v2.decode_predictions(predictions)

print(decoded)
```

## Hugging Face Transformers

```bash
pip install transformers
```

```python
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image

processor = AutoImageProcessor.from_pretrained("microsoft/resnet-50")
model = AutoModelForImageClassification.from_pretrained("microsoft/resnet-50")

image = Image.open("image.jpg")
inputs = processor(images=image, return_tensors="pt")

with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predicted_class = logits.argmax(-1).item()

print(model.config.id2label[predicted_class])
```

## ONNX Runtime

```bash
pip install onnxruntime-gpu
```

```python
import onnxruntime as ort
import numpy as np
from PIL import Image

# Load model
session = ort.InferenceSession("model.onnx")

# Preprocess
img = Image.open("image.jpg").resize((224, 224))
img_array = np.array(img).transpose(2, 0, 1).astype(np.float32)
img_array = img_array / 255.0

# Predict
outputs = session.run(None, {"input": [img_array]})
print(outputs[0])
```

## Custom Classifier Training

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision.datasets as datasets
import torchvision.transforms as transforms

# Define model
class SimpleClassifier(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Linear(32*32*32, num_classes)
    
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)

# Train
model = SimpleClassifier()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

for epoch in range(10):
    for images, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
```

## TensorRT Optimization

```python
import torch
import tensorrt as trt

# Convert to ONNX first
torch.onnx.export(model, dummy_input, "model.onnx")

# Convert to TensorRT
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
builder = trt.Builder(TRT_LOGGER)
network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
parser = trt.OnnxParser(network, TRT_LOGGER)

with open("model.onnx", "rb") as f:
    parser.parse(f.read())

engine = builder.build_serialized_network(network, builder.build)
```

## API Server for Classification

```python
from flask import Flask, request, jsonify
import torch
from PIL import Image

app = Flask(__name__)
model = torch.jit.load("model.pt")
model.eval()

@app.route('/classify', methods=['POST'])
def classify():
    file = request.files['image']
    img = Image.open(file.stream)
    
    # Preprocess and predict
    result = model(preprocess(img))
    
    return jsonify({
        'class': int(result.argmax(1)),
        'probability': float(result.max(1))
    })
```

## Performance Benchmarking

```python
import time
import torch

def benchmark(model, input_tensor, iterations=100):
    # Warmup
    for _ in range(10):
        model(input_tensor)
    
    # Measure
    start = time.time()
    for _ in range(iterations):
        model(input_tensor)
    elapsed = time.time() - start
    
    print(f"Average: {elapsed/iterations*1000:.2f}ms")

benchmark(model, torch.randn(1, 3, 224, 224))
```
