# Semantic Segmentation

This guide covers semantic segmentation on Jetson AGX Orin.

## What is Semantic Segmentation?

Semantic segmentation assigns a class label to each pixel in an image, enabling pixel-level understanding.

## TorchVision Segmentation Models

```python
import torch
import torchvision.models.segmentation as segmentation
import cv2
import numpy as np

# Load DeepLabV3 model
model = segmentation.deeplabv3_resnet50(pretrained=True)
model.eval()

# Load and preprocess image
img = cv2.imread('image.jpg')
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

transform = torchvision.transforms.Compose([
    torchvision.transforms.ToTensor(),
    torchvision.transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                     std=[0.229, 0.224, 0.225])
])

input_tensor = transform(img_rgb).unsqueeze(0)

# Predict
with torch.no_grad():
    output = model(input_tensor)['out'][0]
    mask = output.argmax(0).numpy()

# Colorize mask
colors = np.array([
    [0, 0, 0],       # background
    [255, 0, 0],     # person
    [0, 255, 0],     # car
    [0, 0, 255],     # etc
], dtype=np.uint8)

colored_mask = colors[mask]
result = cv2.addWeighted(img_rgb, 0.5, colored_mask, 0.5, 0)
cv2.imwrite('segmentation.jpg', result)
```

## MobileNetV3 for Segmentation

```python
# Lightweight model for Jetson
model = segmentation.lraspp_mobilenet_v3_large(pretrained=True)
model.eval()
```

## Segmentation with OpenCV

```python
import cv2
import numpy as np

# Using GrabCut algorithm
img = cv2.imread('image.jpg')
mask = np.zeros(img.shape[:2], np.uint8)

bgdModel = np.zeros((1, 65), np.float64)
fgdModel = np.zeros((1, 65), np.float64)

rect = (50, 50, 400, 500)
cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)

mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
result = img * mask2[:, :, np.newaxis]
```

## Cityscapes Dataset Classes

```python
CITYSCAPES_CLASSES = [
    'road', 'sidewalk', 'building', 'wall', 'fence',
    'pole', 'traffic light', 'traffic sign', 'vegetation',
    'terrain', 'sky', 'person', 'rider', 'car', 'truck',
    'bus', 'train', 'motorcycle', 'bicycle'
]
```

## U-Net Implementation

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class UNet(nn.Module):
    def __init__(self, in_channels=3, out_channels=1):
        super().__init__()
        
        self.enc1 = self._conv_block(in_channels, 64)
        self.enc2 = self._conv_block(64, 128)
        self.enc3 = self._conv_block(128, 256)
        self.enc4 = self._conv_block(256, 512)
        
        self.bottleneck = self._conv_block(512, 1024)
        
        self.up4 = nn.ConvTranspose2d(1024, 512, 2, 2)
        self.dec4 = self._conv_block(1024, 512)
        
        self.up3 = nn.ConvTranspose2d(512, 256, 2, 2)
        self.dec3 = self._conv_block(512, 256)
        
        self.up2 = nn.ConvTranspose2d(256, 128, 2, 2)
        self.dec2 = self._conv_block(256, 128)
        
        self.up1 = nn.ConvTranspose2d(128, 64, 2, 2)
        self.dec1 = self._conv_block(192, 64)
        
        self.out = nn.Conv2d(64, out_channels, 1)
        
    def _conv_block(self, in_ch, out_ch):
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        # Encoder
        e1 = self.enc1(x)
        e2 = self.enc2(F.max_pool2d(e1, 2))
        e3 = self.enc3(F.max_pool2d(e2, 2))
        e4 = self.enc4(F.max_pool2d(e3, 2))
        
        # Bottleneck
        b = self.bottleneck(F.max_pool2d(e4, 2))
        
        # Decoder
        d4 = self.up4(b)
        d4 = torch.cat([d4, e4], dim=1)
        d4 = self.dec4(d4)
        
        d3 = self.up3(d4)
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)
        
        d2 = self.up2(d3)
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)
        
        d1 = self.up1(d2)
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)
        
        return self.out(d1)
```

## Instance Segmentation

```python
import torchvision.models.detection as detection

# Mask R-CNN
model = detection.maskrcnn_resnet50_fpn(pretrained=True)
model.eval()

# Get predictions
with torch.no_grad():
    predictions = model([input_tensor])

# Masks
masks = predictions[0]['masks']
scores = predictions[0]['scores']
```

## Real-time Segmentation

```python
import cv2
import torch
import torchvision.transforms as T

model = segmentation.deeplabv3_resnet50(pretrained=True)
model.eval()

transform = T.Compose([
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    img = transform(frame).unsqueeze(0)
    
    with torch.no_grad():
        output = model(img)['out'][0].argmax(0).numpy()
    
    # Apply colormap
    colored = cv2.applyColorMap(
        (output * 20).astype(np.uint8), 
        cv2.COLORMAP_JET
    )
    
    result = cv2.addWeighted(frame, 0.6, colored, 0.4, 0)
    cv2.imshow('Segmentation', result)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

## Performance Optimization

```python
# Use TorchScript for faster inference
model = segmentation.deeplabv3_resnet50(pretrained=True)
model.eval()

# Trace
example_input = torch.randn(1, 3, 512, 512)
traced_model = torch.jit.trace(model, example_input)
traced_model.save('segmentation_traced.pt')
```
