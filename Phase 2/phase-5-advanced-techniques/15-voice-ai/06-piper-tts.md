# Piper TTS on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Voice Models](#voice-models)
4. [Implementation](#implementation)
5. [Advanced Usage](#advanced-usage)

## Introduction

Piper is a fast, neural text-to-speech system. It's the recommended TTS solution for Jetson AGX Orin due to its low resource requirements.

## Installation

### Install Piper

```bash
# Install Piper binary
wget https://github.com/rhasspy/piper/releases/download/2024.01.16/piper_1.2.0_linux_aarch64.tar.gz
tar -xzf piper_1.2.0_linux_aarch64.tar.gz

# Copy to PATH
sudo cp piper /usr/local/bin/
sudo chmod +x /usr/local/bin/piper
```

### Install Python Bindings

```bash
pip install piper-tts
```

## Voice Models

### Available English Voices

| Voice | Size | Quality | Speed |
|-------|------|---------|-------|
| en_US-lessac | 39MB | Good | Fast |
| en_US-lessac-medium | 77MB | Better | Medium |
| en_US-lessac-large | 317MB | Best | Slow |

### Download Voices

```python
import subprocess

voices = [
    "en_US-lessac",
    "en_US-lessac-medium", 
    "en_US-lessac-large",
    "en_GB-lessac-medium",
]

for voice in voices:
    url = f"https://rhasspy.github.io/piper-voices/{voice}.onnx"
    subprocess.run(["wget", "-q", "-O", f"/tmp/{voice}.onnx", url])
```

## Implementation

### Basic Piper TTS

```python
#!/usr/bin/env python3
"""
Piper TTS Implementation
"""

import subprocess
import os

class PiperTTS:
    """Fast neural TTS using Piper"""
    
    def __init__(self, voice="en_US-lessac-medium"):
        self.voice = voice
        self.model_path = None
        
    def download_voice(self):
        """Download voice model"""
        
        model_name = self.voice
        base_url = "https://rhasspy.github.io/piper-voices"
        
        # Download onnx model
        onnx_url = f"{base_url}/{model_name}.onnx"
        self.model_path = f"/tmp/{model_name}.onnx"
        
        if not os.path.exists(self.model_path):
            print(f"Downloading voice: {model_name}")
            subprocess.run([
                "wget", "-q", "-O", self.model_path, onnx_url
            ])
        
        return self.model_path
    
    def speak(self, text, output_file=None):
        """Convert text to speech"""
        
        if not self.model_path:
            self.download_voice()
        
        if output_file is None:
            output_file = "/tmp/piper_output.wav"
        
        # Run piper
        result = subprocess.run(
            ["piper", "--model", self.model_path, "--output_file", output_file],
            input=text.encode(),
            capture_output=True
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr.decode()}")
            return None
        
        return output_file
    
    def speak_to_file(self, text_file, output_file=None):
        """Convert text file to speech"""
        
        with open(text_file, 'r') as f:
            text = f.read()
        
        return self.speak(text, output_file)


def main():
    """Demo Piper TTS"""
    
    tts = PiperTTS("en_US-lessac-medium")
    tts.download_voice()
    
    # Speak
    output = tts.speak("Hello! This is Piper text to speech on Jetson.")
    
    print(f"Audio: {output}")


if __name__ == "__main__":
    main()
```

### Stream Audio

```python
def speak_stream(text):
    """Stream audio output"""
    
    cmd = [
        "piper",
        "--model", "/tmp/en_US-lessac-medium.onnx",
        "--output_file", "-"
    ]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    
    # Send text
    proc.stdin.write(text.encode())
    proc.stdin.close()
    
    # Play audio
    import pyaudio
    
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=22050,
        output=True
    )
    
    # Stream audio
    while True:
        data = proc.stdout.read(1024)
        if not data:
            break
        stream.write(data)
    
    stream.close()
    p.terminate()
```

## Advanced Usage

### Voice Parameters

```python
def speak_with_params(text, pitch=0, speed=1.0, noise=0.0):
    """Customize voice parameters"""
    
    cmd = [
        "piper",
        "--model", "/tmp/en_US-lessac-medium.onnx",
        "--pitch", str(pitch),
        "--speed", str(speed),
        "--noise", str(noise),
        "--output_file", "/tmp/output.wav"
    ]
    
    subprocess.run(cmd, input=text.encode())


def speak_ssml(text):
    """Use SSML for advanced control"""
    
    # Piper supports SSML
    ssml = f"<speak>{text}</speak>"
    
    cmd = [
        "piper",
        "--model", "/tmp/en_US-lessac-medium.onnx",
        "--output_file", "/tmp/output.wav"
    ]
    
    subprocess.run(cmd, input=ssml.encode())
```

## Next Steps

- [Text-to-Speech](./04-text-to-speech.md) - Overview
- [Integration](./08-integration.md) - Combine with STT
- [Optimization](./09-optimization.md) - Performance tuning
