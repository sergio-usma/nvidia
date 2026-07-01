# Audio Playback and GStreamer

This guide covers audio playback and GStreamer pipelines for Jetson AGX Orin.

## Install GStreamer

```bash
sudo apt update
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-libav
```

## GStreamer Basics

```bash
# Play audio file
gst-play-1.0 audio.wav

# List available devices
gst-device-monitor-1.0 Audio/Sink

# Pipeline example
gst-launch-1.0 filesrc location=audio.wav ! decodebin ! audioconvert ! alsasink
```

## Python with GStreamer

Install:

```bash
pip install pygobject
```

Or use gi:

```python
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)
```

## Play Audio File

```python
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

# Create pipeline
pipeline = Gst.parse_launch("filesrc location=audio.wav ! decodebin ! audioconvert ! alsasink")

# Play
pipeline.set_state(Gst.State.PLAYING)

# Run loop
main_loop = GLib.MainLoop()
main_loop.run()

# Stop
pipeline.set_state(Gst.State.NULL)
```

## Play from URL

```python
pipeline = Gst.parse_launch(
    "uridecodebin uri=http://example.com/stream.mp3 ! "
    "audioconvert ! alsasink"
)
```

## Audio Pipeline Elements

```python
# Audio sources
filesrc location=audio.wav
pulsesrc device=0
alsasrc device=hw:0
autoaudiosrc

# Audio filters
audioconvert
volume volume=0.5
audioamplify amplification=1.5
audioresample

# Audio sinks
alsasink device=hw:0
pulsesink
autoaudiosink
filesink location=output.wav
```

## Real-time Audio Processing

```python
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Pipeline with processing
pipeline = Gst.parse_launch(
    "pulsesrc ! "
    "audioconvert ! "
    "volume volume=0.5 ! "
    "alsasink"
)

pipeline.set_state(Gst.State.PLAYING)
GLib.MainLoop().run()
```

## Audio Streaming with RTP

Sender:

```bash
gst-launch-1.0 filesrc location=audio.wav ! \
    decodebin ! \
    audioconvert ! \
    "audio/x-raw,rate=44100,channels=2" ! \
    rtpL16pay ! \
    udpsink host=192.168.1.100 port=5000
```

Receiver:

```bash
gst-launch-1.0 udpsrc port=5000 ! \
    "application/x-rtp, media=audio" ! \
    rtpL16depay ! \
    audioconvert ! \
    alsasink
```

## TTS to Audio Pipeline

```python
import subprocess
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

# First generate TTS audio
subprocess.run([
    'echo', 'Hello world', '|',
    'piper', '--model', 'en_US-lessac-medium.onnx',
    '--output_file', '/tmp/tts.wav'
])

# Then play
pipeline = Gst.parse_launch(
    "filesrc location=/tmp/tts.wav ! "
    "decodebin ! "
    "audioconvert ! "
    "alsasink"
)

pipeline.set_state(Gst.State.PLAYING)
```

## Audio Visualization

```python
# With wavescope
pipeline = Gst.parse_launch(
    "filesrc location=music.mp3 ! "
    "decodebin ! "
    "audioconvert ! "
    "wavescope style=1 ! "
    " videoconvert ! "
    "xvimagesink"
)
```

## Multi-channel Audio

```bash
# Convert to mono
gst-launch-1.0 filesrc location=stereo.wav ! decodebin ! \
    audioconvert ! "audio/x-raw,channels=1" ! \
    alsasink
```

## Audio Recording

```bash
gst-launch-1.0 -e \
    alsasrc ! \
    "audio/x-raw,rate=44100,channels=1" ! \
    wavenc ! \
    filesink location=recording.wav
```

## Video + Audio

```bash
gst-launch-1.0 playbin \
    uri=file:///path/to/video.mp4 \
    video-sink=xvimagesink \
    audio-sink=alsasink
```

## Python HTTP Audio Stream

```python
from flask import Response, request
import subprocess
import threading

def stream_audio():
    proc = subprocess.Popen([
        'gst-launch-1.0', '-q', '-e',
        'alsasrc', '!', 'audio/x-raw,rate=16000,channels=1',
        '!', 'wavenc', '!', 'filesink', 'location=/dev/stdout'
    ], stdout=subprocess.PIPE)
    
    def generate():
        while True:
            data = proc.stdout.read(4096)
            if not data:
                break
            yield data
    
    return Response(generate(), mimetype='audio/wav')

app = Flask(__name__)
app.add_url_rule('/stream', view_func=stream_audio)
```

## Troubleshooting

```bash
# List audio devices
pactl list short sinks
pactl list short sources

# Check GStreamer version
gst-inspect-1.0 --version

# Debug
GST_DEBUG=3 gst-launch-1.0 ...
```
