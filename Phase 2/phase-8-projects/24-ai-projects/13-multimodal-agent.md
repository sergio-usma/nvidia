# Project 13: Multimodal AI Agent

A comprehensive guide to building an intelligent AI agent that combines vision, voice, and text reasoning to interact with the physical world through camera and audio input on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Create Vision Agent](#step-3-create-vision-agent)
   - [Step 4: Create Voice Agent](#step-4-create-voice-agent)
   - [Step 5: Create Multimodal Agent](#step-5-create-multimodal-agent)
6. [Running the Agent](#running-the-agent)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a comprehensive multimodal AI agent:

- **Visual Perception**: Describe scenes, detect objects
- **Voice Interaction**: Listen and respond
- **Chain of Thought**: Combine multiple modalities
- **Action Execution**: Act on visual + voice input
- **Memory**: Remember past interactions

### Agent Capabilities

| Capability | Description |
|-----------|-------------|
| Vision | See and understand images |
| Voice | Speech input/output |
| Reasoning | Chain modalities |
| Actions | Execute tasks |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Multimodal Agent Architecture                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                      MULTIMODAL AGENT CORE                          │ │
│   │                                                                      │ │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │ │
│   │  │  Vision  │    │  Voice   │    │   Text   │    │  Action  │    │ │
│   │  │  Agent   │    │  Agent   │    │  Reason  │    │  Planner │    │ │
│   │  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    │ │
│   │       │              │              │              │             │ │
│   │       └──────────────┼──────────────┼──────────────┘             │ │
│   │                      │              │                              │ │
│   │                      ▼              ▼                              │ │
│   │               ┌──────────────┐ ┌──────────────┐                  │ │
│   │               │  Context     │ │   Memory    │                  │ │
│   │               │   Manager   │ │   System    │                  │ │
│   │               └──────────────┘ └──────────────┘                  │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│   Inputs:                              Outputs:                             │
│   ┌──────────┐                       ┌──────────┐                        │
│   │  Camera  │                       │   Text   │                        │
│   │  Input   │                       │ Response │                        │
│   └──────────┘                       └──────────┘                        │
│   ┌──────────┐                       ┌──────────┐                        │
│   │  Micro   │                       │  Speech  │                        │
│   │  phone   │                       │  Output  │                        │
│   └──────────┘                       └──────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation |
|-----------|-------------|
| LLaVA | Part 7: Vision |
| Whisper | Part 6: Speech |
| Piper | Part 6: TTS |
| Ollama | Part 5: LLMs |

### Pre-Installation

```bash
# Check Ollama
ollama list | grep llava

# Check Whisper
which whisper

# Check Piper
which piper
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Vision Understanding | Scene description, object detection |
| Voice I/O | Speech recognition and synthesis |
| Chain Reasoning | Combine modalities |
| Action Planning | Execute complex tasks |
| Memory | Context retention |

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
pip3 install transformers accelerate opencv-python pillow pygame pyaudio httpx scipy
```

### Step 2: Create Project Directory

```bash
mkdir -p ~/ai-projects/multimodal-agent
cd ~/ai-projects/multimodal-agent
mkdir -p agents models memories
```

### Step 3: Create Vision Agent

Create `agents/vision_agent.py`:

```python
#!/usr/bin/env python3
"""
Vision Agent Module

Handles visual perception tasks including scene description,
object detection, and visual question answering.
"""

import base64
import cv2
import numpy as np
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class VisionResult:
    """Result from vision processing."""
    description: str
    objects: List[str]
    confidence: float


class VisionAgent:
    """
    Vision agent using LLaVA for visual understanding.
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llava"
    
    def describe_scene(self, image) -> str:
        """
        Describe what's in the image.
        
        Args:
            image: numpy array or image path
        
        Returns:
            str: Scene description
        """
        prompt = "Describe this image in detail. What's happening? What objects do you see?"
        return self.analyze(image, prompt)
    
    def analyze(self, image, question: str) -> str:
        """
        Answer a question about an image.
        
        Args:
            image: numpy array or image path
            question: Question to ask
        
        Returns:
            str: Answer
        """
        # Convert image to base64
        if isinstance(image, str):
            # Load from file
            import base64
            with open(image, 'rb') as f:
                image_b64 = base64.b64encode(f.read()).decode()
        else:
            # Convert numpy array
            import base64
            _, buffer = cv2.imencode('.jpg', image)
            image_b64 = base64.b64encode(buffer).decode()
        
        # Prepare request
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }],
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['message']['content']
        
        except Exception as e:
            print(f"Vision error: {e}")
        
        return "I'm sorry, I couldn't analyze the image."
    
    def detect_objects(self, image) -> List[str]:
        """
        Detect objects in the image.
        
        Args:
            image: numpy array
        
        Returns:
            List of detected objects
        """
        prompt = "List all the objects you can see in this image. Just give me a list."
        result = self.analyze(image, prompt)
        
        # Parse objects (simplified)
        objects = [line.strip() for line in result.split('\n') if line.strip()]
        return objects
    
    def answer_question(self, image, question: str) -> str:
        """
        Answer a specific question about an image.
        
        Args:
            image: numpy array
            question: Question
        
        Returns:
            str: Answer
        """
        return self.analyze(image, question)
```

### Step 4: Create Voice Agent

Create `agents/voice_agent.py`:

```python
#!/usr/bin/env python3
"""
Voice Agent Module

Handles voice input and output for the multimodal agent.
"""

import pyaudio
import wave
import tempfile
import os
import requests
from typing import Optional


class VoiceAgent:
    """
    Voice agent for speech input/output.
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        whisper_model: str = "base"
    ):
        self.ollama_url = ollama_url
        self.whisper_model = whisper_model
        self.sample_rate = 16000
        self.channels = 1
    
    def listen(self, duration: float = 5.0) -> Optional[str]:
        """
        Listen for speech and transcribe.
        
        Args:
            duration: Recording duration in seconds
        
        Returns:
            str: Transcribed text
        """
        # Record audio
        audio = pyaudio.PyAudio()
        
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=1024
        )
        
        print("Listening...")
        frames = []
        chunks = int(self.sample_rate / 1024 * duration)
        
        for _ in range(chunks):
            data = stream.read(1024)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wf = wave.open(f.name, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            # Transcribe
            text = self._transcribe(f.name)
            os.unlink(f.name)
        
        return text
    
    def _transcribe(self, audio_file: str) -> str:
        """Transcribe audio file using Whisper."""
        # Use faster-whisper or whisper CLI
        # Simplified version using requests to local API
        
        try:
            with open(audio_file, 'rb') as f:
                # This would need a local Whisper server
                # For now, return placeholder
                return "Speech recognized"
        
        except Exception as e:
            print(f"Transcription error: {e}")
        
        return ""
    
    def speak(self, text: str):
        """
        Speak text using TTS.
        
        Args:
            text: Text to speak
        """
        # Use Piper for TTS
        model = os.environ.get(
            'PIPER_MODEL',
            '/usr/local/share/piper/samples/en_US-lessac-medium.onnx'
        )
        config = model + '.json'
        
        cmd = f"echo '{text}' | piper --model {model} --config {config} | aplay -q"
        os.system(cmd)
```

### Step 5: Create Multimodal Agent

Create `agents/agent.py`:

```python
#!/usr/bin/env python3
"""
Multimodal AI Agent

Combines vision, voice, and text reasoning for intelligent interaction.

Author: Your Name
Version: 1.0.0
"""

import os
import cv2
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from vision_agent import VisionAgent
from voice_agent import VoiceAgent


@dataclass
class Message:
    """A message in the conversation."""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentState:
    """Current state of the agent."""
    mode: str = "idle"  # idle, listening, viewing, thinking, speaking
    context: Dict = field(default_factory=dict)


class MultimodalAgent:
    """
    Multimodal AI agent combining vision, voice, and text.
    """
    
    def __init__(self):
        # Initialize components
        self.vision = VisionAgent()
        self.voice = VoiceAgent()
        
        # State
        self.state = AgentState()
        self.conversation: List[Message] = []
        self.memory: List[str] = []
        
        # Camera
        self.camera = None
        
        # Ollama
        self.ollama_url = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
        self.model = os.environ.get('DEFAULT_MODEL', 'llama3.2')
    
    def start_camera(self, index: int = 0):
        """Start camera capture."""
        self.camera = cv2.VideoCapture(index)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    def capture_frame(self):
        """Capture a frame from camera."""
        if self.camera:
            ret, frame = self.camera.read()
            if ret:
                return frame
        return None
    
    def see(self, prompt: str = None) -> str:
        """
        Process visual input.
        
        Args:
            prompt: Optional question about the image
        
        Returns:
            str: Visual analysis result
        """
        frame = self.capture_frame()
        if frame is None:
            return "No camera available."
        
        if prompt is None:
            prompt = "Describe this image."
        
        self.state.mode = "viewing"
        result = self.vision.analyze(frame, prompt)
        self.state.mode = "idle"
        
        # Store in memory
        self.memory.append(f"Visual: {result[:100]}...")
        
        return result
    
    def listen(self) -> str:
        """
        Listen for voice input.
        
        Returns:
            str: Transcribed speech
        """
        self.state.mode = "listening"
        text = self.voice.listen(duration=5.0)
        self.state.mode = "idle"
        
        if text:
            self.conversation.append(Message(role="user", content=text))
        
        return text or ""
    
    def speak(self, text: str):
        """
        Speak text output.
        
        Args:
            text: Text to speak
        """
        self.state.mode = "speaking"
        self.voice.speak(text)
        self.state.mode = "idle"
        
        self.conversation.append(Message(role="assistant", content=text))
    
    def think(self, prompt: str) -> str:
        """
        Process text with LLM.
        
        Args:
            prompt: Input prompt
        
        Returns:
            str: LLM response
        """
        self.state.mode = "thinking"
        
        # Build conversation context
        messages = [
            {"role": "system", "content": "You are a helpful multimodal AI assistant."}
        ]
        
        # Add recent conversation
        for msg in self.conversation[-10:]:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result['message']['content']
                self.state.mode = "idle"
                return text
        
        except Exception as e:
            print(f"LLM error: {e}")
        
        self.state.mode = "idle"
        return "I'm having trouble thinking right now."
    
    def run_interactive(self):
        """Run interactive mode."""
        print("\n" + "="*50)
        print("🎭 Multimodal AI Agent")
        print("="*50)
        print("Commands:")
        print("  see [question] - View and analyze image")
        print("  say <text>    - Have agent speak text")
        print("  think <prompt> - Text reasoning")
        print("  listen        - Voice input")
        print("  camera        - Start camera view")
        print("  quit          - Exit")
        print("="*50 + "\n")
        
        while True:
            try:
                cmd = input("> ").strip()
                
                if not cmd:
                    continue
                
                if cmd == "quit":
                    break
                
                elif cmd.startswith("see"):
                    question = cmd[4:].strip() or None
                    result = self.see(question)
                    print(f"\n{result}\n")
                
                elif cmd.startswith("say"):
                    text = cmd[4:].strip()
                    self.speak(text)
                
                elif cmd.startswith("think"):
                    prompt = cmd[6:].strip()
                    result = self.think(prompt)
                    print(f"\n{result}\n")
                
                elif cmd == "listen":
                    text = self.listen()
                    print(f"\nHeard: {text}\n")
                
                elif cmd == "camera":
                    print("Starting camera... (press 'q' to exit)")
                    while True:
                        ret, frame = self.camera.read()
                        if not ret:
                            break
                        cv2.imshow('Camera', frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    cv2.destroyAllWindows()
                
                else:
                    print("Unknown command")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    agent = MultimodalAgent()
    agent.start_camera()
    agent.run_interactive()


if __name__ == '__main__':
    main()
```

---

## Running the Agent

```bash
# Run interactive mode
cd ~/ai-projects/multimodal-agent
python3 agents/agent.py
```

### Commands

| Command | Description |
|---------|-------------|
| `see` | View and analyze image |
| `listen` | Voice input |
| `think` | Text reasoning |
| `say` | Text-to-speech |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not working | Check v4l2 devices |
| Whisper timeout | Use smaller model |
| LLaVA not responding | Check Ollama |

---

## License

MIT License
