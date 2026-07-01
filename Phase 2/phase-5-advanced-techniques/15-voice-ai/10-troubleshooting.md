# Speech AI Troubleshooting on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [STT Issues](#stt-issues)
3. [TTS Issues](#tts-issues)
4. [Audio Issues](#audio-issues)
5. [Performance Issues](#performance-issues)

## Introduction

Common issues and solutions for speech AI on Jetson AGX Orin.

## STT Issues

### Whisper Loading Errors

```
Error: Model not found
```

**Solution:**
```python
# Download model explicitly
model = WhisperModel("base", download_root="/path/to/models")
```

### CUDA Out of Memory

```
Error: CUDA out of memory
```

**Solution:**
```python
# Use smaller model
model = WhisperModel("tiny")

# Use CPU
model = WhisperModel("base", device="cpu", compute_type="int8")
```

## TTS Issues

### Piper Not Found

```
Error: piper: command not found
```

**Solution:**
```bash
# Install Piper
wget https://github.com/rhasspy/piper/releases/download/2024.01.16/piper_1.2.0_linux_aarch64.tar.gz
tar -xzf piper_1.2.0_linux_aarch64.tar.gz
sudo cp piper /usr/local/bin/
```

### Voice Download Errors

```
Error: Failed to download voice
```

**Solution:**
```bash
# Download manually
wget -O /tmp/voice.onnx https://rhasspy.github.io/piper-voices/en_US-lessac-medium.onnx
```

## Audio Issues

### Microphone Not Detected

```
Error: No audio input device
```

**Solution:**
```bash
# List audio devices
arecord -l

# Set default device
pactl set-default-source alsa_input.usb-*
```

### Audio Playback Issues

```
Error: No audio output
```

**Solution:**
```bash
# Check audio devices
aplay -l

# Set default output
pactl set-default-sink alsa_output.*
```

## Performance Issues

### Slow Transcription

**Solution:**
- Use smaller model (tiny/base)
- Use CUDA if available
- Enable VAD filtering

### Audio Quality Issues

**Solution:**
- Check microphone quality
- Adjust sample rate
- Reduce background noise

## Next Steps

- [API Reference](./11-api-reference.md) - Full API
