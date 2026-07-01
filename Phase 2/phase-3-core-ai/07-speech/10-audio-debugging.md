# Audio Debugging and Troubleshooting

This guide covers debugging and troubleshooting audio issues on Jetson AGX Orin.

## Check Audio Devices

```bash
# List playback devices
aplay -l
aplay -L

# List recording devices
arecord -l
arecord -L

# Test with speaker
speaker-test -t sine -f 440

# Test microphone
arecord -d 3 test.wav
aplay test.wav
```

## ALSA Configuration

```bash
# Create ~/.asoundrc
nano ~/.asoundrc
```

```bash
pcm.!default {
    type hw
    card 0
}

ctl.!default {
    type hw
    card 0
}
```

## PulseAudio

```bash
# Check PulseAudio
pactl list short sinks
pactl list short sources

# Set default
pactl set-default-sink alsa_output.platform-sound:analog-stereo
pactl set-default-source alsa_input.platform-sound:analog-mono

# Volume control
pactl set-sink-volume 0 +10%
pactl set-source-volume 0 -10%
```

## Microphone Issues

```bash
# Check microphone permissions
ls -la /dev/audio
groups | grep audio

# Add user to audio group
sudo usermod -a -G audio $USER

# Test microphone
arecord -D plughw:0 -d 5 test.wav
```

## Audio Cracks/Pops

```bash
# Check for buffer underruns
dmesg | grep -i audio

# Increase buffer size
# In ALSA:
pcm.default {
    type plug
    slave.pcm "hw:0"
    buffer_size 4096
    period_size 1024
}
```

## Sample Rate Issues

```bash
# Check current rate
cat /proc/asound/card0/stream0

# Force sample rate
arecord -r 44100 -f S16_LE test.wav
aplay -r 44100 test.wav
```

## HDMI Audio

```bash
# List HDMI outputs
cat /proc/asound/card0/eld#0.0

# Check if HDMI audio is detected
aplay -l | grep HDMI

# Switch to HDMI audio
pactl set-default-sink alsa_output.platform-hdmi-sound:analog-stereo
```

## GStreamer Debug

```bash
# Enable debug
GST_DEBUG=3 gst-launch-1.0 ...

# Check available plugins
gst-inspect-1.0 | grep -i alsa
gst-inspect-1.0 | grep -i pulse

# List devices
gst-device-monitor-1.0 Audio
```

## Python Audio Issues

```sounddevice:

```python
import sounddevice as sd

# List devices
print(sd.query_devices())

# Check default
print(sd.query_default_devices())

# Test
sd.play(test_data, 44100)
sd.wait()
```

## Common Error Solutions

### "No such file or directory"

```bash
# Install ALSA utilities
sudo apt install alsa-utils libasound2-dev
```

### "Device not found"

```python
# Use different device index
sd.query_devices()
sd.default.device = 1  # Change index
```

### "Permission denied"

```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Or run with sudo (not recommended)
```

### "Input overflow"

```python
# Increase blocksize
with sd.InputStream(blocksize=4096) as stream:
    pass
```

## Testing STT Pipeline

```python
import sounddevice as sd
import numpy as np

# Record test audio
print("Recording...")
audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1)
sd.wait()
print("Recording done")

# Save
import scipy.io.wavfile as wav
wav.write("test_audio.wav", 16000, audio)

# Transcribe
from faster_whisper import WhisperModel
model = WhisperModel("small.en", device="cuda")
segments, info = model.transcribe("test_audio.wav")
print("Transcription:", " ".join([s.text for s in segments]))
```

## Testing TTS Pipeline

```python
import subprocess

# Test Piper
subprocess.run([
    'echo', 'Testing the audio pipeline',
    '|', 'piper',
    '--model', 'en_US-lessac-medium.onnx',
    '--output_file', 'test_output.wav'
])

# Play
subprocess.run(['aplay', 'test_output.wav'])
```

## Monitoring Audio Performance

```python
import time
import psutil

def monitor_audio_system():
    while True:
        # CPU usage
        print(f"CPU: {psutil.cpu_percent()}%")
        
        # Memory
        print(f"Memory: {psutil.virtual_memory().percent}%")
        
        time.sleep(1)
```

## System Logs

```bash
# Check system logs
dmesg | grep -i audio
journalctl -u pulseaudio

# ALSA info
cat /proc/asound/cards
cat /proc/asound/card0/stream0
```

## Rebuild Audio Stack

```bash
# Reinstall ALSA
sudo apt install --reinstall alsa-base alsa-utils libasound2

# Reinstall PulseAudio
sudo apt install --reinstall pulseaudio

# Restart services
sudo systemctl restart alsa-state
sudo systemctl restart pulseaudio
```
