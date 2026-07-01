# Speech AI Integration on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Pipeline Overview](#pipeline-overview)
3. [Speech-to-Speech](#speech-to-speech)
4. [Voice Assistant](#voice-assistant)
5. [Examples](#examples)

## Introduction

Integrate Speech-to-Text, Text-to-Speech, and LLMs for complete voice interaction systems.

## Pipeline Overview

```
Microphone → STT → Text → LLM → TTS → Speaker
                    ↓
              Intent Recognition
```

## Speech-to-Speech

### Complete Pipeline

```python
#!/usr/bin/env python3
"""
Speech-to-Speech Pipeline
Combine STT and TTS for voice interaction
"""

from faster_whisper import WhisperModel
import subprocess
import os

class SpeechPipeline:
    """Complete speech pipeline"""
    
    def __init__(self):
        self.stt = None
        self.tts_model = None
        
    def init_stt(self, model_size="base"):
        """Initialize speech-to-text"""
        self.stt = WhisperModel(model_size, device="cuda", compute_type="float16")
        
    def init_tts(self, voice="en_US-lessac-medium"):
        """Initialize text-to-speech"""
        self.tts_voice = voice
        
        # Download voice if needed
        self.tts_model = f"/tmp/{voice}.onnx"
        if not os.path.exists(self.tts_model):
            # Download voice
            pass
    
    def speech_to_speech(self, audio_input, llm_response):
        """Process audio through pipeline"""
        
        # STT: Audio to text
        segments, info = self.stt.transcribe(audio_input)
        text = " ".join([s.text for s in segments])
        
        # Process with LLM
        # (See Part 9-12 for LLM integration)
        response = llm_response(text)
        
        # TTS: Text to audio
        output_audio = self.speak(response)
        
        return output_audio
    
    def speak(self, text):
        """Convert text to speech"""
        
        output = "/tmp/response.wav"
        
        subprocess.run([
            "piper",
            "--model", self.tts_model,
            "--output_file", output
        ], input=text.encode())
        
        return output


class VoiceAssistant:
    """Voice assistant with LLM"""
    
    def __init__(self):
        self.pipeline = SpeechPipeline()
        
    def start(self):
        """Start voice assistant"""
        
        print("Initializing voice assistant...")
        
        # Load models
        self.pipeline.init_stt("base")
        self.pipeline.init_tts("en_US-lessac-medium")
        
        print("Ready! Say something...")
        
        # Main loop
        while True:
            # Record audio
            # (See real-time STT)
            
            # Process
            response = self.respond("Hello, how can I help you?")
            
            # Speak response
            self.pipeline.speak(response)
```

## Voice Assistant

### Basic Voice Assistant

```python
class SimpleVoiceAssistant:
    """Simple voice assistant"""
    
    def __init__(self):
        self.stt = None
        self.tts = None
        
    def setup(self):
        """Setup components"""
        
        # STT
        self.stt = WhisperModel("tiny", device="cuda")
        
        # TTS voice
        self.tts_voice = "/tmp/en_US-lessac-medium.onnx"
    
    def listen(self, duration=3):
        """Listen for speech"""
        
        # Record audio
        # Returns audio path
        return "/tmp/input.wav"
    
    def think(self, text):
        """Process text (placeholder for LLM)"""
        
        # Here you would integrate with Ollama
        # See Part 9-12
        responses = {
            "hello": "Hello! How can I help you?",
            "time": "The current time is...",
            "default": "I understand. Let me think about that."
        }
        
        text_lower = text.lower()
        
        for key, response in responses.items():
            if key in text_lower:
                return response
        
        return responses["default"]
    
    def speak(self, text):
        """Speak response"""
        
        output = "/tmp/output.wav"
        
        subprocess.run([
            "piper",
            "--model", self.tts_voice,
            "--output_file", output
        ], input=text.encode())
        
        # Play audio
        subprocess.run(["aplay", output])
    
    def run(self):
        """Run assistant"""
        
        self.setup()
        
        while True:
            audio = self.listen()
            text = self.stt.transcribe(audio)
            response = self.think(text)
            self.speak(response)
```

## Examples

### Voice-Controlled LED

```python
def control_led(command):
    """Control LED based on voice command"""
    
    if "on" in command.lower():
        # Turn on LED
        pass
    elif "off" in command.lower():
        # Turn off LED
        pass
```

### Voice Notes

```python
def voice_notes():
    """Voice note taking"""
    
    # Record
    audio = listen()
    
    # Transcribe
    text = stt.transcribe(audio)
    
    # Save
    with open("notes.txt", "a") as f:
        f.write(text + "\n")
```

## Next Steps

- [Speech-to-Text](./03-speech-to-text.md) - STT
- [Text-to-Speech](./04-text-to-speech.md) - TTS
- [Optimization](./09-optimization.md) - Performance
