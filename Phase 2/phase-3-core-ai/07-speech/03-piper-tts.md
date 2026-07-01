# Piper Text-to-Speech

Run Piper for high-quality text-to-speech synthesis.

## Using jetson-containers

```bash
cd ~/jetson-containers
./run.sh $(./autotag piper)
```

## Inside the Container

Synthesize speech:

```bash
echo "Hello from your Jetson!" | piper --model en_US-lessac-medium --output_file hello.wav
```

## Play Audio

```bash
aplay hello.wav
```

Install alsa-utils if needed:

```bash
sudo apt install alsa-utils
```

## Model Options

Available voices:
- `en_US-lessac-medium` - American English, medium quality
- `en_US-lessac-large` - American English, high quality
- `en_GB-lessac-medium` - British English

## Using Ollama

Ollama doesn't include TTS, but you can use Piper API:

```bash
curl "http://localhost:8002/api/tts?text=Hello%20world" --output hello.wav
```

Run piper server first (port 8002).

## Next Steps

- [Build Voice Assistant](04-voice-assistant.md)
- [Vision Models](../part-7-vision/01-llava.md)
