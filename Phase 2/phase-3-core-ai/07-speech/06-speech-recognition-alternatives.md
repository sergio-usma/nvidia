# Speech Recognition Alternatives

This guide covers alternative speech recognition solutions for Jetson AGX Orin beyond Whisper.

## Vosk

Install:

```bash
pip install vosk
```

Download model:

```bash
# Small model (50MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-us-0.15.zip

# Larger model (1GB)
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
```

Usage:

```python
import vosk
import pyaudio
import json

model = vosk.Model('vosk-model-small-en-us-0.15')
rec = vosk.KaldiRecognizer(model, 16000)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000,
                input=True, frames_per_buffer=8000)

while True:
    data = stream.read(4000)
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        print(result.get('text', ''))
```

## Coqui STT

Install:

```bash
pip install coqui-stt
```

Download models:

```bash
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v0.9.3/model.pbmm
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v0.9.3/model.scorer
```

Usage:

```python
from coqui_stt import Model

model = Model('model.pbmm')
model.enableDecoderWithLM('model.scorer', 0.5, 0.5)

audio = read_audio('audio.wav')
text = model.stt(audio)
print(text)
```

## AssemblyAI

Install:

```bash
pip install assemblyai
```

Usage:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

config = aai.TranscriptionConfig(
    speaker_labels=True,
    auto_chapters=True
)

transcriber = aai.Transcriber()
transcript = transcriber.transcribe("https://example.com/audio.wav")

for utterance in transcript.utterances:
    print(f"Speaker {utterance.speaker}: {utterance.text}")
```

## Google Cloud Speech

Install:

```bash
pip install google-cloud-speech
```

Usage:

```python
from google.cloud import speech

client = speech.SpeechClient()

audio = speech.RecognitionAudio(uri="gs://your-bucket/audio.wav")
config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000,
    language_code="en-US"
)

operation = client.long_running_recognize(config=config, audio=audio)
response = operation.result(timeout=600)

for result in response.results:
    print(result.alternatives[0].transcript)
```

## Amazon Transcribe

Install:

```bash
pip install boto3
```

## Microsoft Azure Speech

Install:

```bash
pip install azure-cognitiveservices-speech
```

## Comparison

| Model | Accuracy | Speed | Offline | Size |
|-------|----------|-------|---------|------|
| Whisper | High | Medium | Yes | Large |
| Vosk | Medium | Fast | Yes | Small |
| Coqui | Medium | Fast | Yes | Medium |
| Cloud APIs | High | Fast | No | N/A |

## Offline with Vosk

Best for offline, low-resource scenarios:

```python
# Optimized for Jetson
from vosk import Model, KaldiRecognizer
import pyaudio

model = Model('vosk-model-small-en-us-0.15')
recognizer = KaldiRecognizer(model, 16000)

# Real-time recognition
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000,
                input=True, frames_per_buffer=4096)

while True:
    data = stream.read(4096)
    if recognizer.AcceptWaveform(data):
        result = recognizer.Result()
        print(result)
```

## Hybrid Approach

```python
import subprocess

def transcribe_with_vosk(audio_file):
    """Use Vosk for local transcription"""
    # Run vosk-transcriber
    result = subprocess.run(
        ['vosk-transcriber', '-i', audio_file, '-o', '/tmp/result.json'],
        capture_output=True
    )
    return result.stdout
```

## Benchmarking

```python
import time
import whisper

def benchmark_models():
    audio_path = "test_audio.wav"
    results = {}
    
    # Whisper tiny
    model = whisper.load_model("tiny")
    start = time.time()
    result = model.transcribe(audio_path)
    results["whisper-tiny"] = time.time() - start
    
    # Whisper base
    model = whisper.load_model("base")
    start = time.time()
    result = model.transcribe(audio_path)
    results["whisper-base"] = time.time() - start
    
    return results
```

## Model Selection Guide

- **Whisper**: Best overall accuracy, good for diverse audio
- **Vosk**: Fastest, smallest models, good for real-time
- **Coqui**: Balance between accuracy and speed
- **Cloud APIs**: Best accuracy, requires internet
