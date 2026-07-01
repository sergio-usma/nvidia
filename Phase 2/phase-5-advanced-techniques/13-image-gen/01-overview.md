# Image Generation Overview

## What is AI Image Generation?

AI image generation uses deep learning models to create images from text descriptions (prompts) or transform existing images.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                   Image Generation Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Text Input ──► 2. Tokenization ──► 3. Encoding      │
│                                                              │
│         Prompt              Words → IDs              Latent    │
│                                                              │
│  4. Diffusion ──► 5. Denoising ──► 6. Decoding         │
│                                                              │
│    Process          Iterations            Image Output       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Types of Image Generation

### 1. Text-to-Image (T2I)
Generate images from text descriptions.

```python
prompt = "A sunset over the ocean"
image = model.generate(prompt)
```

### 2. Image-to-Image (I2I)
Transform existing images using a prompt.

```python
input_image = load_image("photo.jpg")
prompt = "Transform to oil painting style"
output = model.transform(input_image, prompt)
```

### 3. Inpainting
Edit specific parts of an image.

```python
mask = create_mask(region_to_edit)
result = model.inpaint(image, mask, "new content")
```

### 4. ControlNet
Generate with controlled structure (pose, edge, depth).

```python
pose_image = detect_pose(person.jpg)
result = model.generate_with_control(prompt, pose_image)
```

## Key Concepts

### Prompts
The text description that guides image generation.

| Element | Example |
|---------|---------|
| Subject | "A cat" |
| Action | "sitting on a wall" |
| Style | "oil painting" |
| Quality | "highly detailed" |

### Parameters

| Parameter | Description | Range |
|-----------|-------------|-------|
| Steps | Number of denoising steps | 1-150 |
| CFG Scale | Prompt adherence | 1-30 |
| Seed | Random seed | -1 (random) |
| Size | Output dimensions | 256-2048 |

### Negative Prompts
Things to avoid in the generated image.

```python
negative_prompt = "blurry, low quality, distorted"
```

## Model Types

### Diffusion Models
- **Stable Diffusion**: Open source, efficient
- **DALL-E**: OpenAI's model
- **Midjourney**: High-quality artistic

### Architecture

```
Latent Diffusion Model (LDM)

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Text      │    │  VAE       │    │  UNet      │
│  Encoder   │───►│  (compress)│───►│  (diffuse) │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
                                    ┌─────────────┐
                                    │  Decoder   │
                                    │ (reconstruct)│
                                    └─────────────┘
```

## Jetson AGX Orin Optimization

### VRAM Requirements

| Model | Min VRAM | Recommended |
|-------|----------|--------------|
| SD 1.5 | 4GB | 8GB |
| SDXL | 8GB | 16GB |
| SDXL + ControlNet | 12GB | 16GB+ |

### Optimization Techniques

1. **Quantization**: Use INT8/FP16
2. **Tile-based**: Process in small chunks
3. **CPU offload**: Move model to CPU when not in use
4. **Attention slicing**: Reduce memory during attention

## Use Cases

| Application | Description |
|-------------|-------------|
| Art Creation | Digital artwork, illustrations |
| Photo Editing | Enhancement, restoration |
| Design | UI mockups, logos |
| Gaming | Asset generation |
| Marketing | Ad creative |
| Education | Visual aids |

## Next Steps

Proceed to [Environment Setup](./02-environment-setup.md) to install required dependencies.
