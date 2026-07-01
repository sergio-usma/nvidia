# Object Detection

Run real-time object detection using jetson-inference.

## Using jetson-containers

```bash
./run.sh $(./autotag jetson-inference)
```

## Inside the Container

```bash
cd /usr/local/bin/jetson-inference/examples
./detectnet --network=ssd-mobilenet-v2 /dev/video0
```

This opens a window showing detected objects.

## Headless Mode

Save output to file instead of display:

```bash
./detectnet --network=ssd-mobilenet-v2 /dev/video0 output.jpg
```

## Available Networks

| Network | Description |
|---------|-------------|
| ssd-mobilenet-v2 | Fast, COCO objects |
| pednet | People detection |
| facenet | Face detection |
| segnet | Semantic segmentation |

## Camera Sources

- USB Camera: `/dev/video0`
- CSI Camera: `csi://0`

## Python Integration

Use jetson-utils for Python:

```python
import jetson_inference
import jetson_utils

# Load network
net = jetson_inference.detectNet("ssd-mobilenet-v2", threshold=0.5)

# Capture from camera
camera = jetson_utils.videoSource("csi://0")

while True:
    img = camera.Capture()
    detections = net.Detect(img)
    print(f"Detected {len(detections)} objects")
```

## Next Steps

- [VS Code SSH Setup](../part-8-development-tools/01-vscode-ssh.md)
- [GitHub Setup](../part-8-development-tools/02-github-setup.md)
