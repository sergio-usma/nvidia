# Text-to-Speech Alternatives

This guide covers alternative TTS solutions for Jetson AGX Orin beyond Piper.

## Coqui TTS

Install:

```bash
pip install tts
```

Usage:

```python
from TTS.api import TTS

tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", gpu=False)

# Generate speech
tts.tts_to_file(text="Hello world", file_path="output.wav")
```

## Edge TTS (Microsoft)

Install:

```bash
pip install edge-tts
```

Usage:

```python
import asyncio
import edge_tts

async def generate_speech():
    communicate = edge_tts.Communicate(
        "Hello from Edge TTS",
        voice="en-US-AriaNeural"
    )
    await communicate.save("output.mp3")

asyncio.run(generate_speech())
```

## Google Cloud TTS

Install:

```bash
pip install google-cloud-texttospeech
```

Usage:

```python
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

synthesis_input = texttospeech.SynthesisInput(text="Hello")

voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

response = client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

with open("output.mp3", "wb") as f:
    f.write(response.audio_content)
```

## Amazon Polly

Install:

```bash
pip install boto3
```

## Festival TTS

Install:

```bash
sudo apt install festival festvox-kenan
```

Usage:

```bash
echo "Hello world" | festival --tts
```

## espeak-ng

Install:

```bash
sudo apt install espeak-ng
```

Usage:

```bash
espeak-ng "Hello world"
espeak-ng -w output.wav "Hello world"
```

## Mimic3 (Mycroft)

Install:

```bash
pip install mimic3
mimic3 --voice en_US/male/low
```

## Comparison

| TTS | Quality | Latency | Offline | License |
|-----|---------|---------|---------|---------|
| Piper | Good | Fast | Yes | Apache 2.0 |
| Coqui | Good | Medium | Yes | MPL 2.0 |
| Edge TTS | Excellent | Fast | No | Proprietary |
| Google Cloud | Excellent | Fast | No | Proprietary |
| espeak-ng | Low | Very Fast | Yes | GPL |

## Offline TTS for Jetson

Best offline options:

```python
# Piper (recommended)
from piper_train import PiperVoice

voice = PiperVoice.from_pretrained("en_US-lessac-medium.onnx")
voice.say_text("Hello world", "output.wav")

# Coqui
from TTS.api import TTS
tts = TTS(model_path="model.pth", config_path="config.json")
tts.tts("Hello world")
```

## FastSpeech2

Install:

```bash
pip install espnet
```

## Custom Voice Models

```python
# Using Coqui
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts.train import XttsTrainer

# Train custom voice (requires dataset)
config = XttsConfig()
model = XttsTrainer.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="models/xtts")
model.synthesize(
    text="Custom voice recording",
    speaker_wav="speaker_reference.wav",
    language="en"
)
```

## Streaming TTS

```python
import edge_tts
import asyncio

async def stream_audio():
    communicate = edge_tts.Communicate("Hello world", voice="en-US-AriaNeural")
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]

# Use with Flask
from flask import Response

@app.route("/tts")
def tts_stream():
    return Response(stream_audio(), mimetype="audio/mpeg")
```

## Voice Cloning

```python
# Using Coqui XTTS (requires consent)
from TTS.api import TTS

tts = TTS("xtts_v2", gpu=True)
tts.tts_to_file(
    text="Hello this is my voice",
    speaker_wav="my_voice_sample.wav",
    language="en",
    file_path="cloned_voice.wav"
)
```
