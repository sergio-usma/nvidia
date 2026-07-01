# Edge AI Deployment

This guide covers deploying AI models at the edge on Jetson AGX Orin.

## TensorRT Optimization

```python
import torch
import tensorrt as trt
import numpy as np

# Convert PyTorch to ONNX
model = MyModel()
model.eval()
dummy_input = torch.randn(1, 3, 224, 224)

torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    export_params=True,
    opset_version=11,
    do_constant_folding=True,
    input_names=['input'],
    output_names=['output']
)

# Convert ONNX to TensorRT
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
builder = trt.Builder(TRT_LOGGER)
network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
parser = trt.OnnxParser(network, TRT_LOGGER)

with open("model.onnx", "rb") as f:
    parser.parse(f.read())

config = builder.create_builder_config()
config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)

engine = builder.build_serialized_network(network, config)

with open("model.trt", "wb") as f:
    f.write(engine)
```

## TensorRT Inference

```python
import tensorrt as trt
import numpy as np
import pycuda.driver as cuda
import pycuda.autoinit

def allocate_buffers(engine):
    h_input = cuda.pagelocked_empty(engine.get_binding_size(0), dtype=np.float32)
    h_output = cuda.pagelocked_empty(engine.get_binding_size(1), dtype=np.float32)
    d_input = cuda.mem_alloc(h_input.nbytes)
    d_output = cuda.mem_alloc(h_output.nbytes)
    return h_input, h_output, d_input, d_output

def inference(engine, input_data):
    h_input, h_output, d_input, d_output = allocate_buffers(engine)
    stream = cuda.Stream()
    
    # Copy input
    np.copyto(h_input, input_data)
    cuda.memcpy_htod_async(d_input, h_input, stream)
    
    # Inference
    context = engine.create_execution_context()
    context.execute_async_v2(bindings=[int(d_input), int(d_output)], stream_handle=stream.handle)
    
    # Copy output
    cuda.memcpy_dtoh_async(h_output, d_output, stream)
    stream.synchronize()
    
    return h_output

# Load and run
with open("model.trt", "rb") as f:
    engine = trt.Runtime(trt.Logger()).deserialize_cuda_engine(f.read())

output = inference(engine, input_data)
```

## ONNX Runtime

```bash
pip install onnxruntime-gpu
```

```python
import onnxruntime as ort
import numpy as np

session = ort.InferenceSession(
    "model.onnx",
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)

input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

result = session.run([output_name], {input_name: input_data})
```

## TorchScript

```python
import torch

model = MyModel()
model.eval()

# Trace
example = torch.randn(1, 3, 224, 224)
traced = torch.jit.trace(model, example)
traced.save("model.pt")

# Or script
scripted = torch.jit.script(model)
scripted.save("model.pt")

# Load and run
loaded = torch.jit.load("model.pt")
output = loaded(input_data)
```

## Quantization

```python
import torch

# Dynamic quantization
model = torch.nn.Linear(1024, 512)
quantized = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)

# Static quantization
model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
torch.quantization.prepare(model, inplace=True)
torch.quantization.convert(model, inplace=True)
```

## Model Optimization for Jetson

```python
# Use TorchVision's pretrained models with optimizations
import torchvision.models as models

# MobileNetV3
model = models.mobilenet_v3_large(pretrained=True)
model.eval()

# Apply optimizations
with torch.no_grad():
    model = torch.jit.script(model)
    model = model.eval()

# Save
model.save("mobilenet_traced.pt")
```

## DeepStream

```bash
sudo apt install deepstream-6.2
```

Config file (dstest1_pgie_config.txt):

```ini
[property]
gpu-id=0
net-scale-factor=0.0039215697906911373
model-color-format=1
custom-network-config=/path/to/model.onnx
model-engine-file=/path/to/model.onnx.engine
labelfile-path=/path/to/labels.txt
batch-size=1
network-mode=2
num-detected-classes=80
interval=0
gie-unique-id=1
process-mode=1
network-type=0
cluster-mode=2
maintain-aspect-ratio=1
parse-bbox-func-name=NvDsInferParseYolo
custom-lib-path=/path/to/libnvdsinfer_custom_impl_yolo.so

[class-attrs-all]
pre-cluster-threshold=0.25
eps=0.25
group-threshold=1
```

Run:

```bash
deepstream-app -c config.txt
```

## Flask API for Inference

```python
from flask import Flask, request
import torch
import torchvision.transforms as T
from PIL import Image

app = Flask(__name__)
model = torch.jit.load("model.pt")
model.eval()

transform = T.Compose([
    T.Resize(256),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

@app.route('/predict', methods=['POST'])
def predict():
    file = request.files['image']
    img = Image.open(file.stream).convert('RGB')
    img_tensor = transform(img).unsqueeze(0)
    
    with torch.no_grad():
        output = model(img_tensor)
    
    return {'prediction': output.argmax(1).item()}

app.run(host='0.0.0.0', port=5000)
```

## Performance Monitoring

```python
import time
import torch

def benchmark(model, input_data, iterations=100):
    # Warmup
    for _ in range(10):
        _ = model(input_data)
    
    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.time()
        _ = model(input_data)
        times.append(time.time() - start)
    
    avg = sum(times) / len(times)
    print(f"Average inference time: {avg*1000:.2f}ms")
    print(f"FPS: {1/avg:.1f}")

benchmark(model, torch.randn(1, 3, 224, 224))
```

## Multi-Model Pipeline

```python
class Pipeline:
    def __init__(self):
        self.detector = load_detector()
        self.classifier = load_classifier()
        self.tracker = load_tracker()
    
    def process(self, frame):
        # Detect
        detections = self.detector(frame)
        
        # Track
        tracks = self.tracker.update(detections)
        
        # Classify
        results = []
        for track in tracks:
            crop = frame[track.bbox]
            cls = self.classifier(crop)
            results.append({'track': track, 'class': cls})
        
        return results
```
