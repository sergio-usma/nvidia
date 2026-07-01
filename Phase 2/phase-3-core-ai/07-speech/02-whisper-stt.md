# Whisper Speech-to-Text

Run Whisper for speech recognition using jetson-containers.

## Using jetson-containers

```bash
cd ~/jetson-containers
./run.sh $(./autotag whisper)
```

## Inside the Container

Transcribe an audio file:

```bash
whisper audio.wav --model tiny --language en
```

## Model Options

| Model | Size | Speed |
|-------|------|-------|
| tiny | ~75MB | Fastest |
| base | ~150MB | Fast |
| small | ~500MB | Medium |
| medium | ~1.5GB | Slow |
| large | ~3GB | Slowest |

## Using API Server

The container can run as a server. See [jetson-containers whisper documentation](https://github.com/dusty-nv/jetson-containers/tree/master/packages/audio/whisper).

## Using Ollama

Ollama includes Whisper-based models:

```bash
ollama pull whisper
```

## Recording Audio

Record audio with arecord:

```bash
arecord -d 5 -f S16_LE -r 16000 recording.wav
```

Then transcribe.

## Next Steps

- [Piper TTS](03-piper-tts.md)
- [Build Voice Assistant](04-voice-assistant.md)
