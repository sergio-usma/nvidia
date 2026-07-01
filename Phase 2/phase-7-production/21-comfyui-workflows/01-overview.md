# ComfyUI + Ollama Workflow Overview

## What is ComfyUI

ComfyUI is a node-based GUI for Stable Diffusion that allows:
- Visual workflow creation
- Advanced image generation
- Video generation (with extensions)
- API access for automation

## Why Combine with Ollama

- **Automated Prompts**: Use Ollama to generate prompts
- **Image-to-Text**: Describe images with Ollama
- **Smart Routing**: Choose models based on task
- **Workflow Automation**: Complete pipelines

## Workflow Types

| Workflow | Description | Use Case |
|----------|-------------|----------|
| Prompt Generation | Ollama → ComfyUI | Automated image creation |
| Image Analysis | ComfyUI → Ollama | Describe generated images |
| Iterative | Ollama → ComfyUI → Ollama → ComfyUI | Refinement loops |
| Video Pipeline | Ollama → ComfyUI (frames) → Video | Automated video |

## Architecture

```
User Request → Ollama (prompt) → ComfyUI (image) → Output
     ↓              ↓               ↓
  Interface    Text Gen      Image Gen

Advanced:
User → Ollama → ComfyUI → Ollama (refine) → ComfyUI → Output
```

## Use Cases

1. **Automated Art Generation**: Text → Image without manual prompts
2. **Batch Processing**: Generate multiple images from text list
3. **Style Transfer**: Use Ollama to describe style → apply in ComfyUI
4. **Image-to-Story**: Generate images that match a story
5. **Video Generation**: Automated keyframe generation

## Next Steps

- [ComfyUI Setup](./02-comfyui-setup.md) - Install ComfyUI
- [Ollama Integration](./03-ollama-integration.md) - Connect Ollama
