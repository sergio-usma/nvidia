# Text-to-Speech on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [TTS Engines](#tts-engines)
3. [Implementation](#implementation)
4. [Piper TTS](#piper-tts)
5. [Coqui TTS](#coqui-tts)
6. [Voice Customization](#voice-customization)

## Introduction

Text-to-Speech (TTS) converts written text into spoken audio. On Jetson AGX Orin, we have several options:

- **Piper**: Fast, neural TTS - recommended for Jetson
- **Coqui**: High quality, heavier
- **Edge TTS**: Cloud-based (not local)

## TTS Engines

### Comparison

| Engine | Quality | Speed | Size | Jetson |
|--------|---------|-------|------|--------|
| Piper | Good | Very Fast | Small | ✅ |
| Coqui VITS | Medium | Medium | Medium | ✅ |
| Coqui XTTS | High | Slow | Large | ⚠️ |
| Edge TTS | High | Fast | Cloud | ❌ |

## Implementation

### Piper TTS (Recommended)

```python
#!/usr/bin/env python3
"""
Text-to-Speech using Piper
Optimized for Jetson AGX Orin
"""

import subprocess
import os
import wave

class TextToSpeech:
    """Text-to-Speech using Piper"""
    
    def __init__(self, voice="en_US-lessac"):
        self.voice = voice
        self.model_path = None
        self.onnx_path = None
        
    def download_voice(self, voice=None):
        """Download Piper voice model"""
        
        if voice:
            self.voice = voice
        
        # Voice models
        voices = {
            "en_US-lessac": "en_US-lessac-medium",
            "en_US-lessac-medium": "en_US-lessac-medium",
            "en_US-lessac-large": "en_US-lessac-large",
            "en_GB-lessac": "en_GB-lessac-medium",
        }
        
        model_name = voices.get(self.voice, "en_US-lessac-medium")
        
        # Download model
        url = f"https://rhasspy.github.io/piper-voices/{model_name}.onnx.json"
        model_url = f"https://rhasspy.github.io/piper-voices/{model_name}.onnx"
        
        os.makedirs("/tmp/piper", exist_ok=True)
        
        # Download if not exists
        self.onnx_path = f"/tmp/piper/{model_name}.onnx"
        
        if not os.path.exists(self.onnx_path):
            print(f"Downloading {model_name}...")
            subprocess.run([
                "wget", "-q", "-O", self.onnx_path, model_url
            ])
        
        return self.onnx_path
    
    def speak(self, text, output_file=None):
        """Convert text to speech"""
        
        if not self.onnx_path:
            self.download_voice()
        
        if output_file is None:
            output_file = "/tmp/tts_output.wav"
        
        # Run Piper
        subprocess.run([
            "piper",
            "--model", self.onnx_path,
            "--output_file", output_file
        ], input=text.encode(), check=True)
        
        return output_file
    
    def speak_file(self, text_file, output_file=None):
        """Convert text file to speech"""
        
        with open(text_file, 'r') as f:
            text = f.read()
        
        return self.speak(text, output_file)


def main():
    """Demo TTS"""
    
    tts = TextToSpeech()
    tts.download_voice()
    
    # Speak
    output = tts.speak("Hello! This is a test of text to speech on Jetson.")
    
    print(f"Audio saved to: {output}")


if __name__ == "__main__":
    main()
```

### Using Piper Python Bindings

```python
import piper_tts

def speak_with_piper(text, voice="en_US-lessac-medium"):
    """Speak using Piper Python API"""
    
    # Generate speech
    import io
    audio_buffer = io.BytesIO()
    
    piper_tts.tts(
        text,
        voice,
        audio_buffer.write
    )
    
    # Save to file
    with open("output.wav", "wb") as f:
        f.write(audio_buffer.getvalue())
    
    return "output.wav"
```

## Coqui TTS

### Install Coqui

```bash
pip install TTS
```

### Coqui TTS Usage

```python
from TTS.api import TTS

class CoquiTTS:
    """Coqui TTS wrapper"""
    
    def __init__(self, model="vits--ljspeech"):
        self.tts = TTS(model_path=None)
        self.tts.download_model(model)
    
    def speak(self, text, output_file="output.wav"):
        """Generate speech"""
        
        self.tts.tts_to_file(
            text=text,
            file_path=output_file
        )
        
        return output_file
```

## Voice Customization

### Voice Parameters

```python
def customize_voice(
    text,
    pitch=1.0,
    speed=1.0,
    volume=1.0
):
    """Customize voice parameters"""
    
    # Use piper with parameters
    cmd = [
        "piper",
        "--pitch", str(pitch),
        "--speed", str(speed),
        "--volume", str(volume),
    ]
    
    return cmd
```

## Next Steps

- [Piper TTS](./06-piper-tts.md) - Detailed Piper setup
- [Voice Cloning](./05-voice-cloning.md) - Clone voices
- [Integration](./08-integration.md) - Combine with STT
