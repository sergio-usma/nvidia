# Part 19: Speech-to-Text, TTS, and Voice Cloning

A comprehensive guide to speech AI on NVIDIA Jetson AGX Orin 64GB, covering speech recognition, text-to-speech synthesis, and voice cloning technologies.

## Table of Contents

1. [Overview](./01-overview.md) - Introduction to speech AI
2. [Environment Setup](./02-environment-setup.md) - Prerequisites and dependencies
3. [Speech-to-Text](./03-speech-to-text.md) - Whisper and STT models
4. [Text-to-Speech](./04-text-to-speech.md) - TTS engines and synthesis
5. [Voice Cloning](./05-voice-cloning.md) - Voice cloning techniques
6. [Piper TTS](./06-piper-tts.md) - Fast neural TTS for Jetson
7. [Faster Whisper](./07-faster-whisper.md) - Optimized Whisper inference
8. [Integration](./08-integration.md) - Combine STT and TTS
9. [Optimization](./09-optimization.md) - Jetson performance tuning
10. [Troubleshooting](./10-troubleshooting.md) - Common issues and solutions
11. [API Reference](./11-api-reference.md) - Complete API documentation

## Quick Start

```bash
# Install faster-whisper (recommended for Jetson)
pip install faster-whisper

# Install Piper TTS
pip install piper-tts

# Test Whisper
python -c "from faster_whisper import WhisperModel; print('Whisper OK')"

# Test Piper
python -c "import piper_tts; print('Piper OK')"
```

## Available Technologies

| Technology | Feasibility | Quality | Speed |
|------------|-------------|---------|-------|
| Faster Whisper | ✅ Excellent | High | Fast |
| Piper TTS | ✅ Excellent | Good | Very Fast |
| Coqui TTS | ⚠️ Limited | High | Slow |
| Voice Cloning | ⚠️ Basic | Medium | Slow |

## Prerequisites

- Jetson AGX Orin 64GB (recommended)
- JetPack 6.2.2
- Python 3.10+
- USB Microphone (for STT)
- Speakers (for TTS)

## Next Steps

Start with [Overview](./01-overview.md) to understand speech AI on Jetson, then proceed to [Environment Setup](./02-environment-setup.md).
