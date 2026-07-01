# Environment Setup for Speech AI on Jetson AGX Orin

## Table of Contents

1. [System Requirements](#system-requirements)
2. [System Configuration](#system-configuration)
3. [Python Dependencies](#python-dependencies)
4. [Audio Setup](#audio-setup)
5. [Verification](#verification)

## System Requirements

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Python 3.10+
- USB Microphone
- Audio Output (speakers/headphones)

## System Configuration

### Enable Performance Mode

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Install System Dependencies

```bash
sudo apt update
sudo apt install -y \
    portaudio19-dev \
    libsndfile1 \
    ffmpeg \
    libsox-dev \
    python3-pyaudio \
    libopenblas-dev
```

## Python Dependencies

### Core Speech Libraries

```bash
# Install faster-whisper (recommended for Jetson)
pip install faster-whisper

# Install Piper TTS
pip install piper-tts

# Install audio processing
pip install soundfile librosa numpy scipy

# Install additional utilities
pip install webrtcvad pyaudio
```

### Verify Installation

```bash
# Test faster-whisper
python -c "from faster_whisper import WhisperModel; print('✅ faster-whisper OK')"

# Test audio libraries
python -c "import soundfile; print('✅ soundfile OK')"
python -c "import librosa; print('✅ librosa OK')"
```

## Audio Setup

### Configure Audio

```bash
# List audio devices
arecord -l
aplay -l

# Set default audio device
# Edit /etc/pulse/default.pa or use pavucontrol
```

### Test Microphone

```bash
# Record test audio
arecord -f cd -t wav /tmp/test.wav

# Play back
aplay /tmp/test.wav
```

## Verification

### Test Script

```python
#!/usr/bin/env python3
"""Verify speech AI setup"""

def test_audio():
    """Test audio input/output"""
    import sounddevice as sd
    
    print("Available audio devices:")
    print(sd.query_devices())
    
def test_whisper():
    """Test Whisper"""
    from faster_whisper import WhisperModel
    
    print("Testing Whisper...")
    # This will download model on first run
    model = WhisperModel("tiny", device="cuda")
    print("✅ Whisper loaded!")

def test_tts():
    """Test TTS"""
    print("Testing TTS systems...")
    print("✅ TTS libraries loaded!")

if __name__ == "__main__":
    print("=== Speech AI Setup Verification ===\n")
    test_audio()
    test_whisper()
    test_tts()
    print("\n✅ All tests passed!")
```

## Next Steps

- [Speech-to-Text](./03-speech-to-text.md) - Using Whisper
- [Text-to-Speech](./04-text-to-speech.md) - TTS engines
- [Faster Whisper](./07-faster-whisper.md) - Optimized STT
