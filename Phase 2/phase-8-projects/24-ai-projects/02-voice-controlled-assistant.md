# Project 2: Voice-Controlled AI Assistant

A comprehensive guide to building a hands-free AI assistant that listens for a wake word, records your voice, processes it with AI (Whisper + Ollama), and speaks the response using Piper TTS.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Hardware Requirements](#hardware-requirements)
5. [What You'll Build](#what-youll-build)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install System Dependencies](#step-1-install-system-dependencies)
   - [Step 2: Get Wake Word Access Key](#step-2-get-wake-word-access-key)
   - [Step 3: Install Python Dependencies](#step-3-install-python-dependencies)
   - [Step 4: Create Voice Assistant Application](#step-4-create-voice-assistant-application)
   - [Step 5: Configure Audio Settings](#step-5-configure-audio-settings)
   - [Step 6: Test the System](#step-6-test-the-system)
7. [Running the Voice Assistant](#running-the-voice-assistant)
8. [Customization](#customization)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Configuration](#advanced-configuration)
11. [Next Steps](#next-steps)

---

## Overview

This project creates a complete voice-controlled AI assistant with:

- **Wake Word Detection**: "Jarvis" activation keyword
- **Speech-to-Text**: Whisper for accurate transcription
- **AI Processing**: Ollama for intelligent responses
- **Text-to-Speech**: Piper for natural voice output
- **Continuous Listening**: Always-ready voice assistant

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Voice Assistant Data Flow                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Microphone ──▶ Wake Word ──▶ Recording ──▶ Whisper ──▶ Ollama ──▶ Piper  │
│                Detection     Trigger      STT        LLM        TTS       │
│                                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  ┌────────┐ ┌───────┐│
│  │ Audio   │  │Porcupine│  │  Audio  │  │ Whisper│  │ Ollama │ │Piper  ││
│  │ Stream  │─▶│  Wake   │─▶│ Buffer  │─▶│  API   │─▶│  API   │─▶│  API  ││
│  │         │  │ Detector│  │         │  │        │  │        │  │       ││
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └────────┘ └───────┘│
│                                                                             │
│  States: LISTENING → DETECTED → RECORDING → PROCESSING → SPEAKING → LISTENING│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software Installations

| Component | Installation Guide |
|-----------|-------------------|
| Ollama | [Part 5: Ollama Setup](../part-5-llms/01-ollama-setup.md) |
| Whisper STT | [Part 6: Whisper STT](../part-6-speech-audio/02-whisper-stt.md) |
| Piper TTS | [Part 6: Piper TTS](../part-6-speech-audio/03-piper-tts.md) |
| Audio Setup | [Part 6: Audio HDMI](../part-6-speech-audio/01-audio-hdmi.md) |

### Pre-Installation Verification

Run these commands to verify all prerequisites:

```bash
# 1. Verify Ollama is running
curl http://localhost:11434/api/tags

# 2. Verify Whisper is installed
which whisper
whisper --help

# 3. Verify Piper is installed
which piper
piper --help

# 4. Check audio devices
arecord -l
aplay -l
```

---

## Hardware Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Microphone | USB microphone or 3.5mm jack |
| Speaker | 3.5mm or HDMI audio |
| RAM | 8GB (16GB recommended) |
| Storage | 10GB free space |

### Recommended Setup

- **Microphone**: USB microphone with noise cancellation
- **Speaker**: Active speakers via 3.5mm or HDMI
- **Jetson AGX Orin**: 64GB for best performance

### Audio Device Detection

```bash
# List recording devices
arecord -l

# List playback devices
aplay -l

# Test microphone
arecord -D plughw:0 -f S16_LE -r 16000 -d 3 test.wav
aplay test.wav

# Check audio levels
alsamixer
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Wake Word | Say "Jarvis" to activate |
| Voice Recording | Records your question |
| Speech Recognition | Converts speech to text |
| AI Response | Generates intelligent response |
| Voice Output | Speaks the response aloud |
| Continuous Mode | Stays listening after response |

### Voice Assistant States

```
┌─────────────────────────────────────────┐
│           STATE MACHINE                │
├─────────────────────────────────────────┤
│                                         │
│    ┌──────────┐    ┌──────────┐         │
│    │ LISTENING│───▶│DETECTED │         │
│    │ (Idle)   │    │ (Wake)   │         │
│    └──────────┘    └────┬─────┘         │
│                         │               │
│                         ▼               │
│                  ┌──────────┐           │
│                  │RECORDING │           │
│                  │ (Active) │           │
│                  └────┬─────┘           │
│                       │                 │
│                       ▼                 │
│                  ┌──────────┐           │
│                  │PROCESSING│           │
│                  │ (Think)  │           │
│                  └────┬─────┘           │
│                       │                 │
│                       ▼                 │
│                  ┌──────────┐    ┌──────────┐
│                  │ SPEAKING │───▶│ LISTENING │
│                  │ (Output) │    │ (Loop)   │
│                  └──────────┘    └──────────┘
│                                         │
└─────────────────────────────────────────┘
```

---

## Step-by-Step Implementation

### Step 1: Install System Dependencies

```bash
# Update package lists
sudo apt update

# Install PortAudio development files (required for PyAudio)
sudo apt install -y portaudio19-dev

# Install audio utilities
sudo apt install -y alsa-utils sox ffmpeg

# Verify installation
pkg-config --modversion portaudio-2.0
```

### Step 2: Get Wake Word Access Key

Picovoice Porcupine provides the wake word detection engine:

1. **Create Account**: Visit [Picovoice Console](https://console.picovoice.ai/)
2. **Create New Application**: Give it a name (e.g., "VoiceAssistant")
3. **Get Access Key**: Copy the access key from the dashboard
4. **Save It**: You'll need it for configuration

> **Note**: The free tier includes 1000 detections/day, sufficient for personal use.

### Step 3: Install Python Dependencies

```bash
# Create virtual environment (if not already)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install required packages
pip install --upgrade pip
pip install pvporcupine pyaudio requests numpy

# Verify installations
python3 -c "import pvporcupine; print('Porcupine:', pvporcupine.__version__)"
python3 -c "import pyaudio; print('PyAudio installed')"
```

### Step 4: Create Voice Assistant Application

Create `voice_assistant.py`:

```python
#!/usr/bin/env python3
"""
Voice-Controlled AI Assistant

A hands-free AI assistant that:
1. Listens for wake word "Jarvis"
2. Records your voice command
3. Transcribes speech to text using Whisper
4. Gets AI response from Ollama
5. Speaks response using Piper

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import pvporcupine
import pyaudio
import struct
import requests
import wave
import os
import sys
import json
import tempfile
import threading
import time
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Picovoice Access Key (get from https://console.picovoice.ai/)
PICOVOICE_ACCESS_KEY = os.environ.get('PICOVOICE_ACCESS_KEY', 'YOUR_ACCESS_KEY_HERE')

# Wake word
WAKE_WORD = 'jarvis'

# Ollama Configuration
OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llama3.2')

# Whisper Configuration
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base')
WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE', 'cuda')

# Piper Configuration
PIPER_MODEL = os.environ.get(
    'PIPER_MODEL',
    '/usr/local/share/piper/samples/en_US-lessac-medium.onnx'
)
PIPER_CONFIG = os.environ.get(
    'PIPER_CONFIG',
    '/usr/local/share/piper/samples/en_US-lessac-medium.onnx.json'
)

# Audio Configuration
AUDIO_FORMAT = pyaudio.paInt16
AUDIO_CHANNELS = 1
AUDIO_RATE = 16000
AUDIO_CHUNK = 512
SILENCE_THRESHOLD = 500
MAX_RECORDING_SECONDS = 30

# ============================================================================
# GLOBAL STATE
# ============================================================================

class VoiceAssistantState:
    """Manages the state of the voice assistant."""
    
    STATE_LISTENING = 'listening'
    STATE_DETECTED = 'detected'
    STATE_RECORDING = 'recording'
    STATE_PROCESSING = 'processing'
    STATE_SPEAKING = 'speaking'
    
    def __init__(self):
        self.current_state = self.STATE_LISTENING
        self.is_running = False
        self.audio = None
        self.porcupine = None
        self.stream = None
        
    def set_state(self, new_state):
        """Update state and log the change."""
        if new_state != self.current_state:
            print(f"[STATE] {self.current_state} → {new_state}")
            self.current_state = new_state

# Global state instance
state = VoiceAssistantState()


# ============================================================================
# AUDIO HELPER FUNCTIONS
# ============================================================================

def get_audio_device_index():
    """
    Find the default audio input device.
    
    Returns:
        int: Device index, or None for default
    """
    audio = pyaudio.PyAudio()
    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:
            print(f"Input device {i}: {device_info['name']}")
    audio.terminate()
    return None  # Use default


def record_audio(filename, duration=10):
    """
    Record audio to a WAV file.
    
    Args:
        filename: Output WAV file path
        duration: Maximum recording duration in seconds
    """
    audio = pyaudio.PyAudio()
    
    # Open stream
    stream = audio.open(
        format=AUDIO_FORMAT,
        channels=AUDIO_CHANNELS,
        rate=AUDIO_RATE,
        input=True,
        frames_per_buffer=AUDIO_CHUNK
    )
    
    print(f"[AUDIO] Recording for up to {duration} seconds...")
    frames = []
    
    # Record audio
    for _ in range(0, int(AUDIO_RATE / AUDIO_CHUNK * duration)):
        data = stream.read(AUDIO_CHUNK)
        frames.append(data)
        
        # Check for silence (optional: stop early if silence detected)
        # You can add silence detection here
    
    # Stop and save
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    # Write to WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(audio.get_sample_size(AUDIO_FORMAT))
        wf.setframerate(AUDIO_RATE)
        wf.writeframes(b''.join(frames))
    
    print(f"[AUDIO] Recording saved to {filename}")


def play_audio(filename):
    """
    Play audio file using Piper TTS output.
    
    Args:
        filename: Audio file to play
    """
    print(f"[AUDIO] Playing {filename}")
    os.system(f"aplay -q {filename}")


# ============================================================================
# SPEECH PROCESSING
# ============================================================================

def speech_to_text(audio_file):
    """
    Convert speech audio to text using Whisper.
    
    Args:
        audio_file: Path to audio file
    
    Returns:
        str: Transcribed text
    """
    print("[WHISPER] Transcribing audio...")
    
    try:
        # Try using faster-whisper if available
        from faster_whisper import WhisperModel
        
        model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type="int8")
        segments, info = model.transcribe(audio_file)
        
        transcription = ""
        for segment in segments:
            transcription += segment.text
        
        print(f"[WHISPER] Transcription: {transcription}")
        return transcription.strip()
        
    except ImportError:
        # Fallback to whisper CLI
        print("[WHISPER] Using whisper CLI...")
        import subprocess
        
        result = subprocess.run(
            ['whisper', audio_file, '--model', WHISPER_MODEL, '--device', WHISPER_DEVICE],
            capture_output=True,
            text=True
        )
        
        # Parse output (whisper saves to .txt file)
        txt_file = audio_file.replace('.wav', '.txt')
        if os.path.exists(txt_file):
            with open(txt_file, 'r') as f:
                return f.read().strip()
        
        return result.stdout


def text_to_speech(text, output_file):
    """
    Convert text to speech using Piper.
    
    Args:
        text: Text to speak
        output_file: Output audio file path
    """
    print(f"[PIPER] Synthesizing: {text[:50]}...")
    
    # Use Piper to convert text to speech
    cmd = f"echo '{text}' | piper --model {PIPER_MODEL} --config {PIPER_CONFIG} --output_file {output_file}"
    os.system(cmd)
    
    print(f"[PIPER] Audio saved to {output_file}")


def get_ai_response(prompt):
    """
    Get AI response from Ollama.
    
    Args:
        prompt: User input text
    
    Returns:
        str: AI response
    """
    print(f"[OLLAMA] Generating response...")
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                'model': DEFAULT_MODEL,
                'prompt': f"You are a helpful AI assistant. Respond to: {prompt}",
                'stream': False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            return f"Error: Ollama returned status {response.status_code}"
            
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}"


# ============================================================================
# WAKE WORD DETECTION
# ============================================================================

def init_wake_word():
    """
    Initialize Picovoice Porcupine wake word detection.
    
    Returns:
        Porcupine instance
    """
    print("[PORCUPINE] Initializing wake word detection...")
    
    # Get paths to keyword files
    keyword_path = pvporcupine.KEYWORD_PATHS[WAKE_WORD]
    
    # Check if keyword file exists, if not use default
    if not os.path.exists(keyword_path):
        print(f"[PORCUPINE] Using default keyword for '{WAKE_WORD}'")
    
    try:
        porcupine = pvporcupine.create(
            access_key=PICOVOICE_ACCESS_KEY,
            keywords=[WAKE_WORD]
        )
        print(f"[PORCUPINE] Ready - say '{WAKE_WORD}' to activate")
        return porcupine
    except Exception as e:
        print(f"[PORCUPINE] Error: {e}")
        print("[PORCUPINE] Falling back to manual activation mode")
        return None


# ============================================================================
# MAIN APPLICATION LOOP
# ============================================================================

def process_voice_command():
    """
    Process a voice command: record, transcribe, get response, speak.
    """
    state.set_state(state.STATE_RECORDING)
    
    # Create temporary file for recording
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        audio_file = tmp.name
    
    try:
        # Record audio
        record_audio(audio_file, duration=MAX_RECORDING_SECONDS)
        
        # Transcribe
        state.set_state(state.STATE_PROCESSING)
        text = speech_to_text(audio_file)
        
        if not text:
            print("[ERROR] No speech detected")
            return
        
        print(f"[UNDERSTOOD] {text}")
        
        # Get AI response
        response = get_ai_response(text)
        print(f"[RESPONSE] {response}")
        
        # Convert to speech
        state.set_state(state.STATE_SPEAKING)
        
        output_file = '/tmp/response.wav'
        text_to_speech(response, output_file)
        
        if os.path.exists(output_file):
            play_audio(output_file)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        
    finally:
        # Cleanup
        if os.path.exists(audio_file):
            os.remove(audio_file)
        
        state.set_state(state.STATE_LISTENING)


def run_voice_assistant():
    """
    Main loop: listen for wake word, process commands.
    """
    # Initialize components
    state.audio = pyaudio.PyAudio()
    state.porcupine = init_wake_word()
    state.is_running = True
    
    if state.porcupine:
        # Wake word mode
        state.stream = state.audio.open(
            format=AUDIO_FORMAT,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            input=True,
            frames_per_buffer=state.porcupine.frame_length
        )
        
        print("\n" + "="*50)
        print("🎙️  Voice Assistant Ready!")
        print(f"   Say '{WAKE_WORD}' to activate")
        print("   Press Ctrl+C to exit")
        print("="*50 + "\n")
        
        state.set_state(state.STATE_LISTENING)
        
        try:
            while state.is_running:
                # Read audio chunk
                pcm = state.stream.read(state.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * state.porcupine.frame_length, pcm)
                
                # Check for wake word
                keyword_index = state.porcupine.process(pcm)
                
                if keyword_index >= 0:
                    print("\n[WAKE WORD DETECTED!]")
                    state.set_state(state.STATE_DETECTED)
                    
                    # Play activation sound (optional)
                    # os.system('paplay /usr/share/sounds/gtk-events/click.wav &')
                    
                    # Process command in separate thread
                    threading.Thread(target=process_voice_command).start()
                    
        except KeyboardInterrupt:
            print("\n[EXIT] Shutting down...")
            
    else:
        # Manual mode (no wake word)
        print("\n" + "="*50)
        print("🎙️  Voice Assistant Ready (Manual Mode)!")
        print("   Press Enter to start recording")
        print("   Press Ctrl+C to exit")
        print("="*50 + "\n")
        
        try:
            while state.is_running:
                input("Press Enter to record...")
                process_voice_command()
                
        except KeyboardInterrupt:
            print("\n[EXIT] Shutting down...")
    
    # Cleanup
    cleanup()


def cleanup():
    """Clean up resources."""
    print("[CLEANUP] Closing audio resources...")
    
    if state.stream:
        state.stream.close()
    
    if state.porcupine:
        state.porcupine.delete()
    
    if state.audio:
        state.audio.terminate()
    
    print("[CLEANUP] Done")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Check for access key
    if PICOVOICE_ACCESS_KEY == 'YOUR_ACCESS_KEY_HERE':
        print("ERROR: Please set PICOVOICE_ACCESS_KEY environment variable")
        print("Get your free key at: https://console.picovoice.ai/")
        sys.exit(1)
    
    # Check for Ollama
    try:
        response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if response.status_code != 200:
            print("ERROR: Ollama is not running")
            print("Start Ollama with: ollama serve")
            sys.exit(1)
    except:
        print("ERROR: Cannot connect to Ollama")
        print("Start Ollama with: ollama serve")
        sys.exit(1)
    
    # Run the assistant
    run_voice_assistant()
```

---

## Running the Voice Assistant

### Quick Start

```bash
# Activate environment
source venv/bin/activate

# Set your Picovoice access key
export PICOVOICE_ACCESS_KEY="your-key-from-picovoice-console"

# Run the assistant
python3 voice_assistant.py
```

### Expected Output

```
[PORCUPINE] Initializing wake word detection...
[PORCUPINE] Ready - say 'jarvis' to activate

==================================================
🎙️  Voice Assistant Ready!
   Say 'jarvis' to activate
   Press Ctrl+C to exit
==================================================

[STATE] listening → detected
[AUDIO] Recording for up to 30 seconds...
[WHISPER] Transcribing audio...
[UNDERSTOOD] What is the capital of France?
[OLLAMA] Generating response...
[RESPONSE] The capital of France is Paris...
[PIPER] Synthesizing...
[AUDIO] Playing /tmp/response.wav
[STATE] speaking → listening
```

---

## Customization

### Changing the Wake Word

```python
# Change to a different wake word
WAKE_WORD = 'alexa'  # or 'computer', 'hey siri', etc.

# You'll need to update the Porcupine initialization
porcupine = pvporcupine.create(
    access_key=PICOVOICE_ACCESS_KEY,
    keywords=[WAKE_WORD]
)
```

### Using Different AI Models

```bash
# Use a different model
export DEFAULT_MODEL="mistral"

# Or change in code
DEFAULT_MODEL = "mistral"
```

### Custom Voice

```bash
# Download a different Piper voice
# See: https://github.com/rhasspy/piper/blob/master/README.md#voices

PIPER_MODEL = "/path/to/your/voice-model.onnx"
PIPER_CONFIG = "/path/to/your/voice-model.onnx.json"
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Access key invalid" | Wrong Picovoice key | Get key from console.picovoice.ai |
| "No audio device" | Microphone not detected | Check `arecord -l` |
| "Whisper not found" | Not installed | `pip install faster-whisper` |
| "Ollama timeout" | Model loading slow | Use smaller model |
| "Audio playback failed" | No speaker | Check `aplay -l` |

### Debug Mode

```python
# Add debug prints
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Components Separately

```bash
# Test microphone
arecord -d 5 test.wav && aplay test.wav

# Test Whisper
whisper --model base test.wav

# Test Ollama
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.2", "prompt": "Hello"}'

# Test Piper
echo "Hello world" | piper --model $PIPER_MODEL --config $PIPER_CONFIG | aplay
```

---

## Advanced Configuration

### Continuous Mode

Modify to stay in recording mode after each response:

```python
def process_voice_command(self):
    # ... existing code ...
    
    # Continue listening
    if state.porcupine:
        state.set_state(state.STATE_LISTENING)
```

### Multiple Wake Words

```python
porcupine = pvporcupine.create(
    access_key=PICOVOICE_ACCESS_KEY,
    keywords=['jarvis', 'computer', 'alexa']
)

# Check which was detected
keyword_index = state.porcupine.process(pcm)
if keyword_index == 0:  # 'jarvis'
    # ...
elif keyword_index == 1:  # 'computer'
    # ...
```

### Voice Activity Detection

Add VAD to start recording only when speech is detected:

```python
# Use webrtcvad for voice activity detection
import webrtcvad

vad = webrtcvad.Vad(2)  # Aggressiveness 0-3

# In recording loop
if vad.is_speech(frame_bytes, SAMPLE_RATE):
    frames.append(frame)
```

---

## Next Steps

Now that you have a voice assistant, try these enhancements:

| Enhancement | Description |
|-------------|-------------|
| [Voice Pipeline](12-voice-pipeline.md) | Complete end-to-end voice system |
| [RAG Integration](07-knowledge-base-rag.md) | Chat with your documents |
| [Home Automation](05-home-automation-bridge.md) | Control smart home devices |
| [Multi-modal](03-multimodal-vision-system.md) | Add vision capabilities |

---

## Related Documentation

- [Picovoice Porcupine](https://picovoice.ai/docs/)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [Piper TTS](https://github.com/rhasspy/piper)

---

## License

MIT License
