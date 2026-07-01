# Build a Voice Assistant

Combine STT (Whisper), LLM (Ollama), and TTS (Piper) for a complete voice assistant.

## Prerequisites

- Ollama running with a model
- Whisper for STT
- Piper for TTS

## Install Dependencies

```bash
sudo apt install -y python3-pip python3-pyaudio portaudio19-dev
pip install requests
```

## Voice Assistant Script

Create `voice_assistant.py`:

```python
#!/usr/bin/env python3
import requests
import os
import wave
import pyaudio

# Configuration
ORIN_IP = "localhost"
WHISPER_URL = f"http://{ORIN_IP}:8001/transcribe"
OLLAMA_URL = f"http://{ORIN_IP}:11434/api/generate"
PIPER_URL = f"http://{ORIN_IP}:8002/api/tts"

def record_audio(duration=5, filename="query.wav"):
    """Record audio from microphone."""
    print(f"Recording {duration} seconds...")
    os.system(f"arecord -d {duration} -f S16_LE -r 16000 {filename}")
    return filename

def transcribe(audio_path):
    """Transcribe audio using Whisper."""
    with open(audio_path, "rb") as f:
        files = {"audio": f}
        resp = requests.post(WHISPER_URL, files=files)
    return resp.json().get("text", "")

def generate(prompt):
    """Generate response using Ollama."""
    resp = requests.post(OLLAMA_URL, json={
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    })
    return resp.json().get("response", "")

def speak(text):
    """Convert text to speech using Piper."""
    print(f"Speaking: {text}")
    resp = requests.get(PIPER_URL, params={"text": text})
    with open("response.wav", "wb") as f:
        f.write(resp.content)
    os.system("aplay response.wav")

def main():
    print("Voice Assistant ready. Press Enter to start...")
    input()
    
    while True:
        # Record
        audio = record_audio()
        
        # Transcribe
        text = transcribe(audio)
        print(f"You said: {text}")
        
        if not text:
            continue
            
        # Generate
        response = generate(text)
        
        # Speak
        speak(response)

if __name__ == "__main__":
    main()
```

## Run the Assistant

```bash
python3 voice_assistant.py
```

## Services Required

Start these services before running:

- Ollama on port 11434
- Whisper API on port 8001
- Piper API on port 8002

## Next Steps

- [LLaVA Vision](01-llava.md)
- [Object Detection](02-object-detection.md)
