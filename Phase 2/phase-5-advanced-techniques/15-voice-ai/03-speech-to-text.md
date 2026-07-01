# Speech-to-Text on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Whisper Models](#whisper-models)
3. [Implementation](#implementation)
4. [Audio Processing](#audio-processing)
5. [Real-Time STT](#real-time-stt)
6. [Batch Transcription](#batch-transcription)

## Introduction

Speech-to-Text (STT) converts spoken language into written text. On Jetson AGX Orin, we use Whisper - a state-of-the-art speech recognition model.

## Whisper Models

### Available Models

| Model | Parameters | Size | Accuracy | Speed |
|-------|------------|------|----------|-------|
| Tiny | 39M | 39MB | Good | Very Fast |
| Base | 74M | 74MB | Good | Fast |
| Small | 244M | 244MB | Better | Medium |
| Medium | 769M | 769MB | Best | Slow |

### Recommended for Jetson

- **Tiny**: Best for real-time, lower accuracy
- **Base**: Good balance for Jetson
- **Small**: Best accuracy, requires optimization

## Implementation

### Basic Whisper Transcription

```python
#!/usr/bin/env python3
"""
Speech-to-Text using Faster Whisper
Optimized for Jetson AGX Orin
"""

from faster_whisper import WhisperModel
import torch
import os

class SpeechToText:
    """Speech-to-Text using Whisper"""
    
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None
        
    def load_model(self, device="cuda"):
        """Load Whisper model"""
        
        print(f"Loading Whisper {self.model_size}...")
        
        # Use CUDA if available
        if device == "cuda" and torch.cuda.is_available():
            self.model = WhisperModel(
                self.model_size,
                device="cuda",
                compute_type="float16"
            )
        else:
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
        
        print(f"✅ Whisper {self.model_size} loaded!")
        return self.model
    
    def transcribe_file(self, audio_path, language=None):
        """Transcribe audio file"""
        
        if self.model is None:
            self.load_model()
        
        # Transcribe
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True
        )
        
        print(f"Detected language: {info.language} ({info.language_probability:.2f})")
        
        # Collect segments
        text = ""
        for segment in segments:
            text += segment.text + " "
        
        return text.strip()
    
    def transcribe_microphone(self, duration=5, language=None):
        """Transcribe from microphone"""
        
        import pyaudio
        import numpy as np
        import wave
        
        # Record audio
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        print("Recording...")
        frames = []
        
        for _ in range(int(16000 / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)
        
        print("Processing...")
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Save to temporary file
        with wave.open("/tmp/mic_input.wav", 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
        
        # Transcribe
        return self.transcribe_file("/tmp/mic_input.wav", language)


def main():
    """Demo transcription"""
    
    stt = SpeechToText("base")
    stt.load_model()
    
    # Transcribe file
    # result = stt.transcribe_file("audio.mp3")
    # print(f"Transcription: {result}")
    
    print("STT demo ready!")


if __name__ == "__main__":
    main()
```

## Audio Processing

### Audio Preprocessing

```python
import librosa
import numpy as np

def preprocess_audio(audio_path, target_sr=16000):
    """Preprocess audio for Whisper"""
    
    # Load audio
    y, sr = librosa.load(audio_path, sr=target_sr)
    
    # Normalize
    y = y / np.max(np.abs(y))
    
    return y

def trim_silence(audio, threshold=0.01):
    """Trim silence from audio"""
    
    import librosa
    
    # Trim
    trimmed, _ = librosa.effects.trim(audio, top_db=20)
    
    return trimmed
```

## Real-Time STT

### Streaming Transcription

```python
class RealtimeSTT:
    """Real-time speech-to-text"""
    
    def __init__(self, model_size="tiny"):
        self.stt = SpeechToText(model_size)
        self.stt.load_model()
    
    def stream_transcribe(self, chunk_duration=1.0):
        """Stream transcription from microphone"""
        
        import pyaudio
        import wave
        import threading
        
        self.running = True
        self.frames = []
        
        def record_audio():
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            while self.running:
                data = stream.read(1024)
                self.frames.append(data)
            
            stream.close()
            p.terminate()
        
        # Start recording thread
        thread = threading.Thread(target=record_audio)
        thread.start()
        
        # Process chunks
        while self.running:
            if len(self.frames) >= int(16000 / 1024 * chunk_duration):
                # Save chunk
                with wave.open("/tmp/chunk.wav", 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(self.frames[-int(16000/1024*chunk_duration):]))
                
                # Transcribe
                text = self.stt.transcribe_file("/tmp/chunk.wav")
                if text:
                    print(f"You: {text}")
        
        thread.join()
    
    def stop(self):
        """Stop streaming"""
        self.running = False
```

## Batch Transcription

### Process Multiple Files

```python
def batch_transcribe(audio_files, output_dir):
    """Transcribe multiple audio files"""
    
    stt = SpeechToText("base")
    stt.load_model()
    
    results = {}
    
    for audio_file in audio_files:
        print(f"Transcribing: {audio_file}")
        
        text = stt.transcribe_file(audio_file)
        
        # Save transcript
        output_file = os.path.join(
            output_dir,
            os.path.basename(audio_file) + ".txt"
        )
        
        with open(output_file, 'w') as f:
            f.write(text)
        
        results[audio_file] = text
    
    return results
```

## Next Steps

- [Faster Whisper](./07-faster-whisper.md) - Optimized inference
- [Text-to-Speech](./04-text-to-speech.md) - TTS systems
- [Integration](./08-integration.md) - Combine STT/TTS
