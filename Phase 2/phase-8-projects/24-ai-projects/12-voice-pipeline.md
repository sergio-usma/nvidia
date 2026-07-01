# Project 12: End-to-End Voice AI Pipeline

A comprehensive guide to building a complete voice AI system with wake word detection, speech recognition, LLM reasoning, and text-to-speech synthesis, all optimized for Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Create Wake Word Detector](#step-3-create-wake-word-detector)
   - [Step 4: Create Speech Recognition](#step-4-create-speech-recognition)
   - [Step 5: Create Voice Pipeline](#step-5-create-voice-pipeline)
   - [Step 6: Run the System](#step-6-run-the-system)
6. [Advanced Configuration](#advanced-configuration)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a complete voice AI pipeline:

- **Wake Word**: "Hey Jarvis" activation
- **Speech Recognition**: Whisper for accurate STT
- **LLM Reasoning**: Ollama for intelligent responses
- **Speech Synthesis**: Piper for natural TTS
- **Conversation History**: Context-aware dialogue
- **Audio Feedback**: Sound effects and status

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Voice AI Pipeline Flow                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Microphone ──▶ Wake ──▶ Record ──▶ Whisper ──▶ Ollama ──▶ Piper ──▶│
│   Input       Word  Trigger   ASR       LLM        TTS      Speaker      │
│                                                                             │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ ┌───────┐ ┌───────┐ │
│   │ Porcupine│ │ Audio   │ │ Streaming│ │Llama3.2│ │Response│ │  Audio │ │
│   │  Wake   │ │ Buffer  │ │  ASR    │ │        │ │       │ │ Output │ │
│   └─────────┘ └─────────┘ └─────────┘ └────────┘ └───────┘ └───────┘ │
│                                                                             │
│   States:                                                                  │
│   LISTENING → WAKE_DETECTED → RECORDING → PROCESSING → SPEAKING → LISTENING│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation |
|-----------|-------------|
| Whisper | Part 6: Whisper STT |
| Piper | Part 6: Piper TTS |
| Ollama | Part 5: Ollama |
| Porcupine | Wake word |

### Pre-Installation

```bash
# Check Whisper
which whisper

# Check Piper
which piper

# Check Ollama
ollama --version
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Wake Word | "Hey Jarvis" detection |
| Streaming ASR | Real-time speech recognition |
| LLM Integration | Contextual responses |
| Natural TTS | Voice output |
| Conversation | History management |

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Install voice processing packages
pip3 install pvporcupine scipy pyaudio soundfile webrtcvad
pip3 install flask flask-socketio numpy queue threading
pip3 install faster-whisper
```

### Step 2: Create Project Directory

```bash
mkdir -p ~/ai-projects/voice-pipeline
cd ~/ai-projects/voice-pipeline
mkdir -p audio config models
```

### Step 3: Create Wake Word Detector

Create `wakeword.py`:

```python
#!/usr/bin/env python3
"""
Wake Word Detection Module

Uses Picovoice Porcupine for efficient wake word detection.
"""

import pvporcupine
import pyaudio
import struct
import os
from typing import Callable, Optional


class WakeWordDetector:
    """
    Wake word detector using Porcupine.
    
    Args:
        access_key: Picovoice access key
        keywords: List of wake words
        sensitivity: Detection sensitivity (0-1)
    """
    
    def __init__(
        self,
        access_key: str,
        keywords: list = None,
        sensitivity: float = 0.5
    ):
        self.access_key = access_key
        self.keywords = keywords or ['jarvis']
        self.sensitivity = sensitivity
        
        # Initialize Porcupine
        self.porcupine = None
        self._init_porcupine()
        
        # Audio stream
        self.audio = None
        self.stream = None
    
    def _init_porcupine(self):
        """Initialize Porcupine engine."""
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=self.keywords,
                sensitivities=[self.sensitivity]
            )
            print(f"Wake word: {self.keywords[0]}")
        except Exception as e:
            print(f"Porcupine error: {e}")
            self.porcupine = None
    
    def start(self, callback: Callable):
        """Start listening for wake word."""
        if not self.porcupine:
            print("Warning: Porcupine not initialized")
            return
        
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.porcupine.sample_rate,
            input=True,
            frames_per_buffer=self.porcupine.frame_length,
            stream_callback=self._audio_callback(callback)
        )
        
        print("Listening for wake word...")
        self.stream.start_stream()
    
    def _audio_callback(self, callback: Callable):
        """Audio stream callback."""
        def callback_wrapper(in_data, frame_count, time_info, status):
            if status:
                print(f"Audio status: {status}")
            
            # Convert to numpy array
            pcm = struct.unpack_from("h" * frame_count, in_data)
            
            # Check for wake word
            try:
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    callback()
            except:
                pass
            
            return None, pyaudio.paContinue
        
        return callback_wrapper
    
    def stop(self):
        """Stop listening."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        if self.porcupine:
            self.porcupine.delete()
```

### Step 4: Create Speech Recognition

Create `speech_recognition.py`:

```python
#!/usr/bin/env python3
"""
Speech Recognition Module

Streaming ASR using faster-whisper.
"""

import numpy as np
import pyaudio
import wave
import tempfile
from faster_whisper import WhisperModel
from typing import Optional


class SpeechRecognizer:
    """
    Speech recognition using faster-whisper.
    
    Args:
        model: Whisper model size (tiny, base, small, medium, large)
        device: Device (cuda, cpu)
    """
    
    def __init__(
        self,
        model: str = "base",
        device: str = "cuda"
    ):
        self.model_name = model
        self.device = device
        
        # Load model
        print(f"Loading Whisper model: {model}")
        self.model = WhisperModel(
            model,
            device=device,
            compute_type="int8" if device == "cuda" else "float32"
        )
        
        # Audio settings
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
    
    def recognize(self, audio_file: str) -> str:
        """Recognize speech from audio file."""
        segments, info = self.model.transcribe(audio_file)
        
        text = ""
        for segment in segments:
            text += segment.text
        
        return text.strip()
    
    def recognize_from_microphone(
        self,
        duration: float = 10.0,
        silence_threshold: float = 0.01
    ) -> str:
        """Recognize speech from microphone."""
        # Record audio
        audio_data = self._record_audio(duration, silence_threshold)
        
        if not audio_data:
            return ""
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            self._save_wav(f.name, audio_data)
            result = self.recognize(f.name)
            os.unlink(f.name)
        
        return result
    
    def _record_audio(
        self,
        duration: float,
        silence_threshold: float
    ) -> Optional[np.ndarray]:
        """Record audio from microphone."""
        audio = pyaudio.PyAudio()
        
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        chunks = int(self.sample_rate / self.chunk_size * duration)
        
        for _ in range(chunks):
            data = stream.read(self.chunk_size)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        # Convert to numpy
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        
        return audio_data
    
    def _save_wav(self, filename: str, audio_data: np.ndarray):
        """Save audio to WAV file."""
        audio = pyaudio.PyAudio()
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        
        audio.terminate()
```

### Step 5: Create Voice Pipeline

Create `voice_pipeline.py`:

```python
#!/usr/bin/env python3
"""
End-to-End Voice AI Pipeline

Complete voice assistant combining wake word, ASR, LLM, and TTS.

Author: Your Name
Version: 1.0.0
"""

import os
import sys
import time
import queue
import threading
import requests
from typing import List, Dict, Optional

# Import modules
from wakeword import WakeWordDetector
from speech_recognition import SpeechRecognizer


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Pipeline configuration."""
    
    # Porcupine
    PICOVOICE_KEY = os.environ.get('PICOVOICE_KEY', '')
    WAKE_WORD = os.environ.get('WAKE_WORD', 'jarvis')
    WAKE_SENSITIVITY = float(os.environ.get('WAKE_SENSITIVITY', '0.5'))
    
    # Whisper
    WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base')
    WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE', 'cuda')
    
    # Ollama
    OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')
    
    # Piper
    PIPER_MODEL = os.environ.get(
        'PIPER_MODEL',
        '/usr/local/share/piper/samples/en_US-lessac-medium.onnx'
    )
    PIPER_CONFIG = os.environ.get(
        'PIPER_CONFIG',
        '/usr/local/share/piper/samples/en_US-lessac-medium.onnx.json'
    )
    
    # Recording
    RECORD_DURATION = int(os.environ.get('RECORD_DURATION', '10'))
    SAMPLE_RATE = 16000


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """Ollama LLM client."""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.history: List[Dict] = []
    
    def generate(self, prompt: str) -> str:
        """Generate response from prompt."""
        # Add to history
        self.history.append({'role': 'user', 'content': prompt})
        
        # Build messages
        messages = [
            {'role': 'system', 'content': 'You are a helpful voice assistant.'}
        ] + self.history[-10:]  # Last 10 messages
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    'model': self.model,
                    'messages': messages,
                    'stream': False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result['message']['content']
                
                # Add to history
                self.history.append({'role': 'assistant', 'content': text})
                return text
        
        except Exception as e:
            print(f"LLM error: {e}")
        
        return "I'm sorry, I couldn't generate a response."
    
    def clear_history(self):
        """Clear conversation history."""
        self.history = []


# ============================================================================
# TTS CLIENT
# ============================================================================

class TTSClient:
    """Piper TTS client."""
    
    def __init__(self, model: str, config: str):
        self.model = model
        self.config = config
    
    def speak(self, text: str):
        """Speak text using Piper."""
        # Generate speech
        cmd = f"echo '{text}' | piper --model {self.model} --config {self.config} | aplay -q"
        os.system(cmd)
    
    def speak_async(self, text: str, queue: queue.Queue):
        """Speak text in background thread."""
        def speak():
            self.speak(text)
            queue.put('done')
        
        thread = threading.Thread(target=speak)
        thread.start()


# ============================================================================
# VOICE PIPELINE
# ============================================================================

class VoicePipeline:
    """
    Complete voice AI pipeline.
    
    States:
        LISTENING: Waiting for wake word
        WAKE_DETECTED: Wake word heard
        RECORDING: Recording speech
        PROCESSING: Processing with ASR/LLM
        SPEAKING: Outputting TTS
    """
    
    STATE_LISTENING = 'listening'
    STATE_RECORDING = 'recording'
    STATE_PROCESSING = 'processing'
    STATE_SPEAKING = 'speaking'
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        
        # State
        self.state = self.STATE_LISTENING
        
        # Components
        self.wake_word = None
        self.asr = None
        self.llm = None
        self.tts = None
        
        # Queues
        self.audio_queue = queue.Queue()
        
        # Initialize
        self._init_components()
    
    def _init_components(self):
        """Initialize pipeline components."""
        # Wake word
        if self.config.PICOVOICE_KEY:
            self.wake_word = WakeWordDetector(
                access_key=self.config.PICOVOICE_KEY,
                keywords=[self.config.WAKE_WORD],
                sensitivity=self.config.WAKE_SENSITIVITY
            )
        
        # ASR
        self.asr = SpeechRecognizer(
            model=self.config.WHISPER_MODEL,
            device=self.config.WHISPER_DEVICE
        )
        
        # LLM
        self.llm = LLMClient(
            base_url=self.config.OLLAMA_BASE,
            model=self.config.OLLAMA_MODEL
        )
        
        # TTS
        self.tts = TTSClient(
            model=self.config.PIPER_MODEL,
            config=self.config.PIPER_CONFIG
        )
        
        print("Voice pipeline initialized")
    
    def start(self):
        """Start the voice pipeline."""
        print("\n" + "="*50)
        print("🎙️  Voice AI Pipeline Ready!")
        print(f"   Say '{self.config.WAKE_WORD}' to activate")
        print("   Press Ctrl+C to exit")
        print("="*50 + "\n")
        
        if self.wake_word:
            # Start wake word detection
            self.wake_word.start(self.on_wake_word)
            
            # Keep main thread alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
        else:
            # Manual mode
            self.run_manual()
    
    def on_wake_word(self):
        """Callback when wake word is detected."""
        print("\n[WAKE WORD DETECTED]")
        
        # Play activation sound
        os.system('paplay /usr/share/sounds/gtk-events/click.wav 2>/dev/null &')
        
        # Change state
        self.state = self.STATE_RECORDING
        
        # Start recording in background
        threading.Thread(target=self.process_voice_input).start()
    
    def process_voice_input(self):
        """Process voice input."""
        try:
            # Record speech
            print("[RECORDING] Speak now...")
            self.state = self.STATE_RECORDING
            
            text = self.asr.recognize_from_microphone(
                duration=self.config.RECORD_DURATION
            )
            
            if not text:
                print("[ERROR] No speech detected")
                self.state = self.STATE_LISTENING
                return
            
            print(f"[UNDERSTOOD] {text}")
            
            # Process with LLM
            self.state = self.STATE_PROCESSING
            print("[THINKING]...")
            
            response = self.llm.generate(text)
            print(f"[RESPONSE] {response}")
            
            # Speak response
            self.state = self.STATE_SPEAKING
            print("[SPEAKING]...")
            
            self.tts.speak(response)
            
            # Return to listening
            self.state = self.STATE_LISTENING
            
        except Exception as e:
            print(f"[ERROR] {e}")
            self.state = self.STATE_LISTENING
    
    def run_manual(self):
        """Run in manual mode (no wake word)."""
        print("\nManual mode - press Enter to start recording")
        
        try:
            while True:
                input()
                self.process_voice_input()
        
        except KeyboardInterrupt:
            print("\nShutting down...")
    
    def stop(self):
        """Stop the pipeline."""
        if self.wake_word:
            self.wake_word.stop()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    pipeline = VoicePipeline()
    pipeline.start()


if __name__ == '__main__':
    main()
```

---

## Running the System

```bash
# Set Picovoice key
export PICOVOICE_KEY="your-key"

# Run pipeline
cd ~/ai-projects/voice-pipeline
python3 voice_pipeline.py
```

---

## Configuration

### Environment Variables

```bash
# Wake word
export WAKE_WORD="jarvis"
export WAKE_SENSITIVITY=0.5

# Whisper
export WHISPER_MODEL="base"
export WHISPER_DEVICE="cuda"

# Ollama
export OLLAMA_MODEL="llama3.2"

# Piper
export PIPER_MODEL="/path/to/voice.onnx"
export PIPER_CONFIG="/path/to/voice.onnx.json"
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Wake word not detected | Adjust sensitivity |
| Whisper timeout | Use smaller model |
| Ollama slow | Use smaller model |
| TTS not working | Check Piper installation |

---

## License

MIT License
