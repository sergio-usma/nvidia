# Speech AI API Reference

## Table of Contents

1. [Speech-to-Text API](#speech-to-text-api)
2. [Text-to-Speech API](#text-to-speech-api)
3. [Pipeline API](#pipeline-api)

## Speech-to-Text API

### SpeechToText

```python
class SpeechToText:
    def __init__(self, model_size="base"):
        """Initialize STT
        
        Args:
            model_size: Model size (tiny, base, small, medium)
        """
        
    def load_model(self, device="cuda"):
        """Load Whisper model
        
        Args:
            device: Device (cuda, cpu)
        """
        
    def transcribe_file(self, audio_path, language=None):
        """Transcribe audio file
        
        Args:
            audio_path: Path to audio file
            language: Language code (None for auto-detect)
            
        Returns:
            str: Transcribed text
        """
        
    def transcribe_microphone(self, duration=5, language=None):
        """Transcribe from microphone
        
        Args:
            duration: Recording duration in seconds
            language: Language code (None for auto-detect)
            
        Returns:
            str: Transcribed text
        """
```

### FastWhisper

```python
class FastWhisper:
    def __init__(self, model_size="base"):
        """Initialize faster-whisper"""
        
    def load(self, device="cuda"):
        """Load optimized model"""
        
    def transcribe(self, audio_path, language=None, beam_size=5):
        """Transcribe audio
        
        Returns:
            str: Transcribed text
        """
        
    def transcribe_segments(self, audio_path):
        """Get segment-level transcription
        
        Returns:
            list: List of segments with start, end, text
        """
```

## Text-to-Speech API

### TextToSpeech

```python
class TextToSpeech:
    def __init__(self, voice="en_US-lessac"):
        """Initialize TTS
        
        Args:
            voice: Voice model name
        """
        
    def download_voice(self, voice=None):
        """Download voice model
        
        Args:
            voice: Voice name (optional)
        """
        
    def speak(self, text, output_file=None):
        """Convert text to speech
        
        Args:
            text: Text to speak
            output_file: Output audio file path
            
        Returns:
            str: Path to output file
        """
        
    def speak_file(self, text_file, output_file=None):
        """Convert text file to speech
        
        Args:
            text_file: Path to text file
            output_file: Output audio file path
        """
```

### PiperTTS

```python
class PiperTTS:
    def __init__(self, voice="en_US-lessac-medium"):
        """Initialize Piper TTS"""
        
    def download_voice(self):
        """Download voice model"""
        
    def speak(self, text, output_file=None):
        """Generate speech
        
        Returns:
            str: Path to audio file
        """
```

## Pipeline API

### SpeechPipeline

```python
class SpeechPipeline:
    def __init__(self):
        """Initialize speech pipeline"""
        
    def init_stt(self, model_size="base"):
        """Initialize STT"""
        
    def init_tts(self, voice="en_US-lessac-medium"):
        """Initialize TTS"""
        
    def speech_to_speech(self, audio_input, llm_response):
        """Process audio through full pipeline
        
        Args:
            audio_input: Input audio
            llm_response: LLM response function
            
        Returns:
            str: Path to output audio
        """
        
    def speak(self, text):
        """Convert text to speech"""
```

### VoiceAssistant

```python
class VoiceAssistant:
    def __init__(self):
        """Initialize voice assistant"""
        
    def start(self):
        """Start voice assistant"""
        
    def listen(self, duration=3):
        """Listen for speech
        
        Returns:
            str: Path to recorded audio
        """
        
    def think(self, text):
        """Process text with LLM
        
        Returns:
            str: Response text
        """
        
    def speak(self, text):
        """Speak response"""
        
    def run(self):
        """Run assistant loop"""
```

## Audio Processing

### Preprocessing Functions

```python
def preprocess_audio(audio_path, target_sr=16000):
    """Preprocess audio for Whisper"""
    
def trim_silence(audio, threshold=0.01):
    """Trim silence from audio"""
```

## Configuration

### Model Sizes

| Size | Parameters | Speed | Accuracy |
|------|------------|-------|----------|
| tiny | 39M | Fastest | Good |
| base | 74M | Fast | Good |
| small | 244M | Medium | Better |
| medium | 769M | Slow | Best |

### Compute Types

| Type | Device | Speed | Memory |
|------|--------|-------|--------|
| float16 | CUDA | Fast | Medium |
| int8 | CPU | Medium | Low |
| float32 | CPU | Slow | High |

## Next Steps

This concludes Part 19. For more information, see:

- [Overview](./01-overview.md)
- [Environment Setup](./02-environment-setup.md)
- [Speech-to-Text](./03-speech-to-text.md)
- [Text-to-Speech](./04-text-to-speech.md)
- [Integration](./08-integration.md)
