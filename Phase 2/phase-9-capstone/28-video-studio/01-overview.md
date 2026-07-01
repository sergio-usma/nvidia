# Creative Studio - LTX-2.3 Video Generation Platform

## Project Overview

Creative Studio is a comprehensive AI-powered video generation platform built on LTX-2.3, the state-of-the-art open-source video generation model from Lightricks. This platform enables text-to-video, image-to-video, and audio-to-video generation with professional quality outputs.

This platform combines and extends all previous projects:
- **Project 6 (Video Studio)**: Story-to-video pipeline → Enhanced with LTX-2.3
- **Project 7 (INNOVALABS)**: Multi-agent storytelling → Script-to-video workflows
- **Project 8 (Funding Finder)**: Document processing → Video proposal generation
- **Project 9 (AI Office)**: Agent management → Video generation orchestration
- **Project 10 (Tourism Intel)**: Data visualization → Video reports
- **Project 11 (Freelance Hunter)**: Job matching → Video presentations

### What It Does

1. **Text-to-Video Generation**: Create videos from text prompts
2. **Image-to-Video**: Animate static images into dynamic videos
3. **Audio-to-Video**: Generate video from audio tracks
4. **Video Extension**: Extend existing videos
5. **Video Retake**: Regenerate specific portions
6. **Multi-Scene Workflows**: Create complex video narratives
7. **Storyboard Generation**: Auto-generate storyboards from scripts
8. **Video Editing**: Professional video editing capabilities

### Features

- **LTX-2.3 Integration**: State-of-the-art video generation
- **Multiple Modes**: Text-to-video, image-to-video, audio-to-video, extend, retake
- **Professional Quality**: 24/48 FPS, 9:16 portrait support
- **Native Audio**: Synchronized audio generation
- **REST API**: Full API for programmatic access
- **Web Interface**: User-friendly browser interface
- **Ollama Integration**: AI-powered prompt enhancement
- **ComfyUI Workflows**: Custom node integration
- **Batch Processing**: Generate multiple videos
- **Project Templates**: Pre-built video templates

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CREATIVE STUDIO PLATFORM                                │
│                   LTX-2.3 Video Generation Suite                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    INPUT LAYER                                        │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │   TEXT      │ │   IMAGE     │ │   AUDIO     │ │   VIDEO     │    │  │
│  │  │   INPUT     │ │   INPUT     │ │   INPUT     │ │   INPUT     │    │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘    │  │
│  │         │               │               │               │            │  │
│  │  ┌──────┴───────────────┴───────────────┴───────────────┴──────┐   │  │
│  │  │              PROMPT ENHANCER (Ollama)                        │   │  │
│  │  │        AI-powered prompt optimization                        │   │  │
│  │  └──────────────────────────┬───────────────────────────────────┘   │  │
│  └─────────────────────────────┼───────────────────────────────────────┘  │
│                                │                                           │
│  ┌─────────────────────────────┴───────────────────────────────────────┐  │
│  │                    GENERATION LAYER                                 │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │  │
│  │  │   TEXT 2    │ │   IMAGE 2    │ │   AUDIO 2    │ │   VIDEO   │ │  │
│  │  │   VIDEO     │ │   VIDEO     │ │   VIDEO      │ │  EXTEND   │ │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │              LTX-2.3 ENGINE                                │   │  │
│  │  │    (Local / Cloud API / ComfyUI)                          │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                │                                           │
│  ┌─────────────────────────────┴───────────────────────────────────────┐  │
│  │                    PROCESSING LAYER                                 │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │  │
│  │  │   FFmpeg    │ │   Upscaling  │ │   Effects    │ │   Audio   │ │  │
│  │  │  Processing │ │   (Optional) │ │   Overlay    │ │   Mix     │ │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                │                                           │
│  ┌─────────────────────────────┴───────────────────────────────────────┐  │
│  │                    OUTPUT LAYER                                     │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │  │
│  │  │   REST API  │ │    WEB UI   │ │   STORAGE   │ │  DISCORD    │  │  │
│  │  │    (8083)   │ │    (8083)   │ │   Local     │ │   BOT       │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## LTX-2.3 Models

### Available Models

| Model | Description | VRAM Required | Use Case |
|-------|-------------|---------------|----------|
| ltx-2.3-22b-dev | Full model, bf16 | 48GB+ | Best quality |
| ltx-2.3-22b-distilled | 8-step distilled | 24GB+ | Balanced |
| ltx-2.3-spatial-upscaler-x2 | Resolution upscaler | 16GB+ | HD output |
| Fast variants | Speed-optimized | 16GB+ | Quick preview |

### Generation Modes

| Mode | Description | Input | Output |
|------|-------------|-------|--------|
| Text-to-Video | Generate from prompt | Text | Video |
| Image-to-Video | Animate image | Image | Video |
| Audio-to-Video | Match audio | Audio | Video |
| Extend | Continue video | Video | Longer Video |
| Retake | Regenerate section | Video | Fixed Video |

## Supported Resolutions & Frame Rates

- **Resolutions**: 512×512, 704×576, 1216×704, 1080×1920 (portrait)
- **Frame Rates**: 24 FPS, 30 FPS, 48 FPS
- **Duration**: 2-10 seconds per generation
- **Aspect Ratios**: 1:1, 16:9, 9:16

## Integration Features

### From Previous Projects

- **Ollama**: Prompt enhancement and optimization
- **ComfyUI**: Custom workflow integration
- **FFmpeg**: Video processing and encoding
- **Discord Bot**: Generation control
- **REST API**: Full programmatic access
- **Web Interface**: User-friendly UI

## Quick Start

```bash
# Start the platform
cd /opt/creative-studio
python server/main.py

# Access web interface
# http://jetson:8083

# Or use API
curl -X POST http://localhost:8083/api/generate/text2video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A sunset over the ocean", "duration": 5}'
```

## Next Steps

- [02-setup](./02-setup.md) - LTX-2.3 installation and setup
- [03-text2video](./03-text2video.md) - Text-to-video workflows
- [04-image2video](./04-image2video.md) - Image-to-video workflows
- [05-audio-video](./05-audio-video.md) - Audio-to-video generation
- [06-workflows](./06-workflows.md) - Complex workflows
- [07-api](./07-api.md) - REST API reference
- [08-web-interface](./08-web-interface.md) - Web UI guide
- [09-integration](./09-integration.md) - Project integration
- [10-installation](./10-installation.md) - Complete setup guide
