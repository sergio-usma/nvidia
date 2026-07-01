# Faster Whisper on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Model Selection](#model-selection)
4. [Implementation](#implementation)
5. [Optimization](#optimization)

## Introduction

Faster Whisper is an optimized implementation of Whisper that runs significantly faster on CUDA-enabled devices like Jetson AGX Orin.

## Installation

```bash
pip install faster-whisper
```

## Model Selection

### Recommended Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| Tiny | 39MB | Very Fast | Good |
| Base | 74MB | Fast | Good |
| Small | 244MB | Medium | Better |

## Implementation

### CUDA-Accelerated Whisper

```python
#!/usr/bin/env python3
"""
Faster Whisper - Optimized STT for Jetson
"""

from faster_whisper import WhisperModel
import torch

class FastWhisper:
    """Optimized Whisper for Jetson"""
    
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None
        
    def load(self, device="cuda"):
        """Load model with optimization"""
        
        # Use CUDA if available
        if device == "cuda" and torch.cuda.is_available():
            self.model = WhisperModel(
                self.model_size,
                device="cuda",
                compute_type="float16"
            )
            print("Using CUDA acceleration")
        else:
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
        
        return self.model
    
    def transcribe(
        self,
        audio_path,
        language=None,
        beam_size=5
    ):
        """Transcribe audio"""
        
        if self.model is None:
            self.load()
        
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            vad_filter=True
        )
        
        # Print info
        print(f"Language: {info.language} ({info.language_probability:.2f})")
        
        # Collect results
        text = ""
        for segment in segments:
            text += segment.text + " "
        
        return text.strip()
    
    def transcribe_segments(self, audio_path):
        """Get segment-level transcription"""
        
        segments, info = self.model.transcribe(
            audio_path,
            vad_filter=True
        )
        
        results = []
        for segment in segments:
            results.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
        
        return results
```

## Optimization

### Performance Tips

```python
# Use float16 for faster inference
model = WhisperModel("base", compute_type="float16")

# Enable VAD filter
segments, info = model.transcribe(audio, vad_filter=True)

# Use larger beam size for accuracy
segments = model.transcribe(audio, beam_size=5)
```

## Next Steps

- [Speech-to-Text](./03-speech-to-text.md) - Overview
- [Integration](./08-integration.md) - Full pipeline
