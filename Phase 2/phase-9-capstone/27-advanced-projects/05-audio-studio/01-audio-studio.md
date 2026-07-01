# AI Audio Generation Studio

## Project Overview

This project creates a complete AI-powered audio generation studio running on the Jetson AGX Orin, accessible remotely via web browser or API from any Windows or Mac computer on your local network.

### Features

- **Text-to-Speech**: Convert text to speech using Piper TTS
- **AI-Powered Text Processing**: Use Ollama to process/enhance text before TTS
- **Voice Selection**: Multiple voice models available
- **Remote Access**: Access via nginx reverse proxy or direct IP
- **API Access**: REST API for programmatic audio generation
- **Audio Playback**: Stream audio directly or download

### Architecture

```
Windows/Mac Host → Local Network → Nginx (Jetson) → Audio API + Piper
                                                    ↓
                                              Generated Audio
```

## Prerequisites

### Services Running

Ensure Ollama is running:

```bash
# Check Ollama
curl http://localhost:11434/api/tags
```

### Install Piper TTS

```bash
# Install Piper
sudo apt update
sudo apt install -y piper

# Download a voice model
mkdir -p ~/.local/share/piper/voices
cd ~/.local/share/piper/voices

# Download English voice
wget https://rhasspy.github.io/piper-voices/v1/en_US-lessac-medium.onnx
wget https://rhasspy.github.io/piper-voices/v1/en_US-lessac-medium.onnx.json

# Test Piper
echo "Hello world" | piper --model ~/.local/share/piper/voices/en_US-lessac-medium.onnx --output_file /tmp/test.wav
aplay /tmp/test.wav
```

### Install Additional Dependencies

```bash
# Install Python dependencies
pip install flask requests pydub

# For audio processing
sudo apt install -y ffmpeg libavcodec-extra
```

## Project Setup

### Create Project Directory

```bash
mkdir -p ~/ai-projects/audio-studio/{api,output,logs,temp}
cd ~/ai-projects/audio-studio
```

### Create the Audio Generation API

```python
#!/usr/bin/env python3
"""
AI Audio Generation Studio API
Provides REST API for text-to-speech with Ollama text processing
"""

import os
import sys
import json
import time
import logging
import subprocess
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

CONFIG = {
    "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "output_dir": os.path.expanduser("~/ai-projects/audio-studio/output"),
    "temp_dir": os.path.expanduser("~/ai-projects/audio-studio/temp"),
    "default_voice": os.getenv("DEFAULT_VOICE", "en_US-lessac-medium"),
    "voices_dir": os.path.expanduser("~/.local/share/piper/voices"),
    "default_ollama": os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.2:3b"),
    "sample_rate": 22050
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)
os.makedirs(CONFIG["temp_dir"], exist_ok=True)
os.makedirs("logs", exist_ok=True)


AVAILABLE_VOICES = {
    "en_US-lessac-medium": {
        "file": "en_US-lessac-medium.onnx",
        "description": "American English, medium quality, fast"
    },
    "en_US-lessac-large": {
        "file": "en_US-lessac-large.onnx",
        "description": "American English, high quality"
    },
    "en_GB-lessac-medium": {
        "file": "en_GB-lessac-medium.onnx",
        "description": "British English, medium quality"
    },
    "en_US-lessac": {
        "file": "en_US-lessac-medium.onnx",
        "description": "American English, medium (alias)"
    }
}


class AudioGenerator:
    """Core audio generation engine using Piper"""
    
    def __init__(self):
        self.ollama = CONFIG["ollama_host"]
        self.voices_dir = CONFIG["voices_dir"]
    
    def process_text_with_ollama(self, text, instruction=None):
        """Use Ollama to process/enhance text for TTS"""
        if instruction is None:
            instruction = "Convert this text into natural, speakable text for text-to-speech. Remove any special characters, fix grammar, and make it flow naturally."
        
        try:
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": CONFIG["default_ollama"],
                    "prompt": f"{instruction}\n\nText: {text}\n\nProcessed:",
                    "stream": False
                },
                timeout=60
            )
            processed = response.json().get("response", text).strip()
            logger.info(f"Processed text: {processed[:100]}...")
            return processed
        except Exception as e:
            logger.warning(f"Ollama processing failed: {e}, using original")
            return text
    
    def generate_speech(self, text, voice=None, output_file=None, 
                       processing="default", pitch=0.0, speed=1.0):
        """Generate speech using Piper"""
        
        if voice is None:
            voice = CONFIG["default_voice"]
        
        # Resolve voice alias
        voice_file = AVAILABLE_VOICES.get(voice, AVAILABLE_VOICES[CONFIG["default_voice"]])["file"]
        voice_path = os.path.join(self.voices_dir, voice_file)
        
        if not os.path.exists(voice_path):
            raise Exception(f"Voice model not found: {voice_path}")
        
        if output_file is None:
            output_file = os.path.join(
                CONFIG["output_dir"], 
                f"speech_{int(time.time())}_{uuid.uuid4().hex[:8]}.wav"
            )
        
        # Process text with Ollama based on processing mode
        if processing == "expand":
            # Expand abbreviations, fix pronunciation
            text = self.process_text_with_ollama(text, 
                "Expand any abbreviations and make text speakable for TTS. Example: 'Dr.' -> 'Doctor', 'etc.' -> 'etcetera'")
        elif processing == "narrate":
            # Convert to narration style
            text = self.process_text_with_ollama(text,
                "Convert this into engaging narration text. Add dramatic pauses with '...' where appropriate.")
        elif processing == "summary":
            # Summarize then speak
            text = self.process_text_with_ollama(text,
                "Summarize this text into a brief, concise version suitable for speaking aloud.")
        
        # Generate speech with Piper
        cmd = [
            "piper",
            "--model", voice_path,
            "--output_file", output_file,
            "--sample_rate", str(CONFIG["sample_rate"])
        ]
        
        if pitch != 0.0:
            cmd.extend(["--pitch", str(pitch)])
        
        if speed != 1.0:
            cmd.extend(["--speed", str(speed)])
        
        logger.info(f"Generating speech with voice: {voice}")
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            input=text.encode(),
            capture_output=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise Exception(f"Piper error: {result.stderr.decode()}")
        
        elapsed = time.time() - start_time
        logger.info(f"Speech generated in {elapsed:.2f}s: {output_file}")
        
        return {
            "output_file": output_file,
            "voice": voice,
            "processing": processing,
            "elapsed_seconds": elapsed,
            "text_length": len(text)
        }
    
    def text_to_ssml(self, text):
        """Convert text to SSML-like format for better control"""
        # Simple SSML-like tags
        text = text.replace("<break>", "...")
        text = text.replace("<emphasis>", "")
        return text
    
    def batch_generate(self, texts, voice=None, processing="default"):
        """Generate multiple audio files from list of texts"""
        results = []
        
        for i, text in enumerate(texts):
            logger.info(f"Processing {i+1}/{len(texts)}")
            try:
                result = self.generate_speech(
                    text, 
                    voice=voice,
                    processing=processing
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing text {i+1}: {e}")
                results.append({"error": str(e), "text": text[:50]})
        
        return results
    
    def get_available_voices(self):
        """Get list of available voices"""
        voices = {}
        for name, info in AVAILABLE_VOICES.items():
            voice_path = os.path.join(self.voices_dir, info["file"])
            voices[name] = {
                "description": info["description"],
                "installed": os.path.exists(voice_path)
            }
        return voices


generator = AudioGenerator()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "audio-studio"})


@app.route("/voices", methods=["GET"])
def voices():
    return jsonify(generator.get_available_voices())


@app.route("/generate", methods=["POST"])
def generate():
    """Generate speech from text"""
    data = request.get_json()
    
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    try:
        result = generator.generate_speech(
            text=data["text"],
            voice=data.get("voice"),
            processing=data.get("processing", "default"),
            pitch=data.get("pitch", 0.0),
            speed=data.get("speed", 1.0)
        )
        
        # Return download URL
        filename = os.path.basename(result["output_file"])
        result["download_url"] = f"/download/{filename}"
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/batch", methods=["POST"])
def batch():
    """Generate multiple audio files"""
    data = request.get_json()
    
    if not data or "texts" not in data:
        return jsonify({"error": "Missing 'texts' parameter"}), 400
    
    try:
        results = generator.batch_generate(
            texts=data["texts"],
            voice=data.get("voice"),
            processing=data.get("processing", "default")
        )
        
        # Add download URLs
        for result in results:
            if "output_file" in result:
                filename = os.path.basename(result["output_file"])
                result["download_url"] = f"/download/{filename}"
        
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Batch error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/narrate", methods=["POST"])
def narrate():
    """Generate narration from longer text (with Ollama processing)"""
    data = request.get_json()
    
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    try:
        result = generator.generate_speech(
            text=data["text"],
            voice=data.get("voice"),
            processing="narrate"
        )
        
        filename = os.path.basename(result["output_file"])
        result["download_url"] = f"/download/{filename}"
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Narration error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    """Download generated audio file"""
    filepath = os.path.join(CONFIG["output_dir"], secure_filename(filename))
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    @after_this_request
    def remove_file(response):
        try:
            # Optional: cleanup after sending
            pass
        except:
            pass
        return response
    
    return send_file(
        filepath,
        mimetype="audio/wav",
        as_attachment=True,
        download_name=filename
    )


@app.route("/stream", methods=["POST"])
def stream():
    """Generate and stream audio (returns URL for now)"""
    data = request.get_json()
    
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    try:
        result = generator.generate_speech(
            text=data["text"],
            voice=data.get("voice")
        )
        
        filename = os.path.basename(result["output_file"])
        
        return jsonify({
            "status": "ready",
            "url": f"/download/{filename}",
            "elapsed": result["elapsed_seconds"]
        })
    except Exception as e:
        logger.error(f"Stream error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/ollama/process", methods=["POST"])
def ollama_process():
    """Process text with Ollama without generating speech"""
    data = request.get_json()
    
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    try:
        processed = generator.process_text_with_ollama(
            text=data["text"],
            instruction=data.get("instruction")
        )
        
        return jsonify({
            "original": data["text"],
            "processed": processed
        })
    except Exception as e:
        logger.error(f"Ollama processing error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    app.run(host="0.0.0.0", port=port, debug=False)
```

### Create Service File

```bash
sudo tee /etc/systemd/system/audio-studio.service << 'EOF'
[Unit]
Description=AI Audio Generation Studio
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/home/sergiok/ai-projects/audio-studio
ExecStart=/home/sergiok/comfyui_env/bin/python3 api/server.py 8081
Restart=always
Environment="OLLAMA_HOST=http://localhost:11434"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable audio-studio
```

## Nginx Reverse Proxy Configuration

```bash
sudo tee /etc/nginx/sites-available/audio-studio << 'EOF'
upstream audio_backend {
    server 127.0.0.1:8081;
}

server {
    listen 80;
    server_name audio.yourhostname.local;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name audio.yourhostname.local;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Audio Studio API
    location / {
        proxy_pass http://audio_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        client_max_body_size 10M;
        proxy_read_timeout 300s;
    }

    # Health check
    location /health {
        proxy_pass http://audio_backend/health;
        access_log off;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/audio-studio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Running Locally

### Start Services

```bash
# Start Audio Studio API
source ~/comfyui_env/bin/activate
cd ~/ai-projects/audio-studio
python3 api/server.py 8081 &

# Or use systemd
sudo systemctl start audio-studio
```

### Test Locally

```bash
# Health check
curl http://localhost:8081/health

# List available voices
curl http://localhost:8081/voices

# Generate speech
curl -X POST http://localhost:8081/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test of text to speech on the Jetson."}'

# Process text with Ollama
curl -X POST http://localhost:8081/ollama/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Dr. Smith works at the MIT and has a PhD. Call him at 555-1234."}'
```

## Remote Access from Windows/Mac

### Option 1: Direct IP Access

```bash
# Find Jetson IP
hostname -I | awk '{print $1}'
```

On Windows/Mac, access:
- **Audio API**: `http://<JETSON_IP>:8081`

### Option 2: Nginx with Custom Hostname

Edit `/etc/hosts` on Windows:
```
192.168.1.100    audio.yourhostname.local
```

On Mac:
```bash
sudo sh -c 'echo "192.168.1.100 audio.yourhostname.local" >> /etc/hosts'
```

Then access: `https://audio.yourhostname.local/`

### Option 3: SSH Tunnel

From Windows/Mac:
```bash
ssh -L 8081:localhost:8081 sergiok@<JETSON_IP>
```

Then access: `http://localhost:8081`

## Client Examples

### Python Client

```python
import requests
import json
import os

class AudioStudioClient:
    def __init__(self, base_url="http://<JETSON_IP>:8081"):
        self.base_url = base_url.rstrip("/")
    
    def generate(self, text, voice=None, **kwargs):
        response = requests.post(
            f"{self.base_url}/generate",
            json={"text": text, "voice": voice, **kwargs}
        )
        response.raise_for_status()
        result = response.json()
        
        # Download audio
        if "download_url" in result:
            audio_url = f"{self.base_url}{result['download_url']}"
            audio_data = requests.get(audio_url).content
            
            filename = result["download_url"].split("/")[-1]
            with open(filename, "wb") as f:
                f.write(audio_data)
            result["saved_to"] = filename
        
        return result
    
    def narrate(self, text, voice=None):
        """Generate narration (with Ollama processing)"""
        response = requests.post(
            f"{self.base_url}/narrate",
            json={"text": text, "voice": voice}
        )
        response.raise_for_status()
        return response.json()
    
    def batch_generate(self, texts, voice=None):
        """Generate multiple audio files"""
        response = requests.post(
            f"{self.base_url}/batch",
            json={"texts": texts, "voice": voice}
        )
        return response.json()


# Usage
client = AudioStudioClient("http://192.168.1.100:8081")

# Simple generation
result = client.generate("Hello world!")
print(f"Saved to: {result.get('saved_to')}")

# Generate narration
result = client.narrate("""
    Once upon a time, in a land far away, there lived a brave knight.
    He traveled across mountains and valleys, seeking adventure.
    Every day brought new challenges and new friends.
""")
print(f"Generated: {result['output_file']}")
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');
const fs = require('fs');

class AudioStudioClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async generate(text, options = {}) {
        const response = await axios.post(`${this.baseUrl}/generate`, {
            text,
            ...options
        });
        
        const result = response.data;
        
        // Download audio
        if (result.download_url) {
            const audioData = await axios.get(
                `${this.baseUrl}${result.download_url}`,
                { responseType: 'arraybuffer' }
            );
            
            const filename = result.download_url.split('/').pop();
            fs.writeFileSync(filename, audioData.data);
            result.saved_to = filename;
        }
        
        return result;
    }
    
    async narrate(text, voice) {
        const response = await axios.post(`${this.base_url}/narrate`, {
            text, voice
        });
        return response.data;
    }
}

const client = new AudioStudioClient('http://192.168.1.100:8081');

const result = await client.generate('Hello from the Jetson!');
console.log('Audio saved to:', result.saved_to);
```

### cURL Commands

```bash
# Generate speech
curl -X POST http://192.168.1.100:8081/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to the AI Audio Studio on Jetson",
    "voice": "en_US-lessac-medium"
  }' \
  -o speech.wav

# Generate narration (with Ollama processing)
curl -X POST http://192.168.1.100:8081/narrate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The hero stood before the ancient castle. Darkness loomed within its walls."
  }'

# Batch generation
curl -X POST http://192.168.1.100:8081/batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["First sentence", "Second sentence", "Third sentence"]
  }'
```

## Testing Procedures

### 1. Local API Test

```bash
# Health check
curl http://localhost:8081/health
# Expected: {"status": "ok", "service": "audio-studio"}

# Check available voices
curl http://localhost:8081/voices

# Generate test audio
curl -X POST http://localhost:8081/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Testing the audio studio"}'
```

### 2. Network Test

```bash
# From another machine on network
curl http://<JETSON_IP>:8081/health

# With nginx
curl https://audio.yourhostname.local/health
```

### 3. Ollama Integration Test

```bash
# Test text processing
curl -X POST http://localhost:8081/ollama/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Dr. Jane Smith MD works at St. Mary Hospital"}'

# Direct Ollama test
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "Make this speakable: The CEO announced Q4 profits rose by 15%",
    "stream": false
  }'
```

### 4. Performance Test

```bash
# Generate multiple audio files and measure time
for i in {1..5}; do
    start=$(date +%s.%N)
    curl -X POST http://localhost:8081/generate \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"Test message number $i\"}" \
        -s > /dev/null
    end=$(date +%s.%N)
    echo "Audio $i: $(echo "$end - $start" | bc)s"
done
```

## Additional Voice Models

### Download More Voices

```bash
cd ~/.local/share/piper/voices

# Download additional voices
# American English - high quality
wget https://rhasspy.github.io/piper-voices/v1/en_US-lessac-large.onnx
wget https://rhasspy.github.io/piper-voices/v1/en_US-lessac-large.onnx.json

# British English
wget https://rhasspy.github.io/piper-voices/v1/en_GB-lessac-medium.onnx
wget https://rhasspy.github.io/piper-voices/v1/en_GB-lessac-medium.onnx.json

# Scottish English
wget https://rhasspy.github.io/piper-voices/v1/en_GB-scottish-medium.onnx
wget https://rhasspy.github.io/piper-voices/v1/en_GB-scottish-medium.onnx.json
```

## Troubleshooting

### Piper Not Found

```bash
# Check Piper installation
which piper
piper --help

# If not installed, install
sudo apt install piper
```

### Voice Model Not Found

```bash
# Check voice files
ls -la ~/.local/share/piper/voices/

# Download if missing
mkdir -p ~/.local/share/piper/voices
cd ~/.local/share/piper/voices
wget https://rhasspy.github.io/piper-voices/v1/en_US-lessac-medium.onnx
wget https://rhasspy.github.io/piper-voices/v1/en_US-lessac-medium.onnx.json
```

### Audio Playback Issues

```bash
# Check audio output
aplay -l

# Test audio file
aplay /tmp/test.wav

# Install audio tools if needed
sudo apt install alsa-utils
```

### Memory Issues

```bash
# Monitor memory
free -h
tegrastats --interval 1000
```

## Next Steps

- [AI Image Generation Studio](./project-01-image-studio.md) - Image generation
- [AI Video Generation Studio](./project-03-video-studio.md) - Video generation
