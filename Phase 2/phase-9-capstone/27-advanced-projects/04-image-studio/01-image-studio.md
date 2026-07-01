# AI Image Generation Studio

## Project Overview

This project creates a complete AI-powered image generation studio running on the Jetson AGX Orin, accessible remotely via web browser from any Windows or Mac computer on your local network.

### Features

- **Text-to-Image**: Generate images from text prompts using Stable Diffusion via ComfyUI
- **AI Prompt Enhancement**: Use Ollama to enhance prompts before generation
- **Remote Access**: Access via nginx reverse proxy from any network device
- **API Access**: REST API for programmatic image generation
- **Multiple Models**: Support for SDXL, SD 1.5, and custom models

### Architecture

```
Windows/Mac Host → Local Network → Nginx (Jetson) → ComfyUI + Ollama
                                                    ↓
                                              Generated Images
```

## Prerequisites

### Services Running

Ensure the following services are running on your Jetson:

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Check ComfyUI
curl http://localhost:8188/system_stats
```

### Install ComfyUI (if not already installed)

```bash
# Create virtual environment
python3 -m venv ~/comfyui_env
source ~/comfyui_env/bin/activate

# Clone ComfyUI
cd ~
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Install additional dependencies for image processing
pip install pillow requests
```

### Download Stable Diffusion Models

```bash
# Create models directory
mkdir -p ~/ComfyUI/models/checkpoints
mkdir -p ~/ComfyUI/models/vae
mkdir -p ~/ComfyUI/models/loras

# Download SDXL Base (recommended for quality)
# Place your .safetensors files in ~/ComfyUI/models/checkpoints/
# Example models:
# - sd_xl_base_1.0.safetensors
# - sd_xl_refiner_1.0.safetensors
# - dreamshaper_8.safetensors (SD 1.5)

# Verify models
ls -la ~/ComfyUI/models/checkpoints/
```

## Project Setup

### Create Project Directory

```bash
mkdir -p ~/ai-projects/image-studio/{api,workflows,output,logs}
cd ~/ai-projects/image-studio
```

### Create the Image Generation API

```python
#!/usr/bin/env python3
"""
AI Image Generation Studio API
Provides REST API for image generation with Ollama prompt enhancement
"""

import os
import sys
import json
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "comfyui_host": os.getenv("COMFYUI_HOST", "http://localhost:8188"),
    "output_dir": os.path.expanduser("~/ai-projects/image-studio/output"),
    "default_model": os.getenv("DEFAULT_SD_MODEL", "sd_xl_base_1.0.safetensors"),
    "default_ollama": os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.2:3b"),
    "enhance_prompts": os.getenv("ENHANCE_PROMPTS", "true").lower() == "true"
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)
os.makedirs("logs", exist_ok=True)


class ImageGenerator:
    """Core image generation engine"""
    
    def __init__(self):
        self.ollama = CONFIG["ollama_host"]
        self.comfy = CONFIG["comfyui_host"]
    
    def enhance_prompt(self, prompt):
        """Use Ollama to enhance the prompt"""
        if not CONFIG["enhance_prompts"]:
            return prompt
            
        try:
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": CONFIG["default_ollama"],
                    "prompt": f"""Enhance this prompt for AI image generation. 
Add details about:
- Style (artistic period, technique)
- Lighting (time of day, mood)
- Composition (framing, depth)
- Quality modifiers (8k, detailed, masterpiece)

Original prompt: {prompt}

Enhanced prompt:""",
                    "stream": False
                },
                timeout=60
            )
            enhanced = response.json().get("response", prompt)
            logger.info(f"Enhanced prompt: {enhanced[:100]}...")
            return enhanced
        except Exception as e:
            logger.warning(f"Prompt enhancement failed: {e}, using original")
            return prompt
    
    def generate_image(self, prompt, negative_prompt=None, 
                      steps=25, cfg=7.0, seed=None, model=None):
        """Generate image via ComfyUI"""
        
        # Enhance prompt if enabled
        enhanced_prompt = self.enhance_prompt(prompt)
        
        if negative_prompt is None:
            negative_prompt = "low quality, blurry, deformed, ugly, bad anatomy"
        
        if seed is None:
            seed = int(time.time()) % 1000000
        
        if model is None:
            model = CONFIG["default_model"]
        
        # Create workflow
        workflow = {
            "1": {
                "inputs": {"model_name": model},
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {"text": enhanced_prompt, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {"text": negative_prompt, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal"
                },
                "class_type": "KSampler"
            },
            "5": {
                "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
                "class_type": "VAEDecode"
            },
            "6": {
                "inputs": {
                    "images": ["5", 0],
                    "filename_prefix": f"img_{seed}"
                },
                "class_type": "SaveImage"
            }
        }
        
        # Submit job
        logger.info(f"Submitting image generation job: seed={seed}, steps={steps}")
        response = requests.post(
            f"{self.comfy}/prompt",
            json={"prompt": workflow},
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to submit job: {response.text}")
        
        job_id = response.json()["prompt_id"]
        
        # Wait for completion
        start_time = time.time()
        while True:
            time.sleep(2)
            try:
                hist_response = requests.get(
                    f"{self.comfy}/history/{job_id}",
                    timeout=10
                )
                hist = hist_response.json()
                
                if job_id in hist:
                    status = hist[job_id].get("status", {})
                    if status.get("completed"):
                        elapsed = time.time() - start_time
                        logger.info(f"Image generated in {elapsed:.1f}s")
                        return {
                            "job_id": job_id,
                            "seed": seed,
                            "elapsed_seconds": elapsed,
                            "prompt": enhanced_prompt
                        }
                    elif status.get("error"):
                        raise Exception(f"Generation error: {status['error']}")
            except Exception as e:
                logger.warning(f"Status check error: {e}")
            
            # Timeout after 10 minutes
            if time.time() - start_time > 600:
                raise Exception("Generation timeout")
    
    def get_output_images(self, job_id):
        """Get generated image paths"""
        try:
            response = requests.get(f"{self.comfy}/history/{job_id}", timeout=10)
            data = response.json()
            
            if job_id not in data:
                return []
            
            outputs = data[job_id].get("outputs", {})
            images = []
            
            for node_id, node_data in outputs.items():
                if "images" in node_data:
                    for img in node_data["images"]:
                        images.append({
                            "filename": img["filename"],
                            "subfolder": img.get("subfolder", ""),
                            "type": img.get("type", "output")
                        })
            
            return images
        except Exception as e:
            logger.error(f"Failed to get output images: {e}")
            return []
    
    def download_image(self, filename, subfolder="", image_type="output"):
        """Download image from ComfyUI"""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": image_type
        }
        response = requests.get(f"{self.comfy}/view", params=params, timeout=60)
        return response.content


generator = ImageGenerator()


class APIHandler(BaseHTTPRequestHandler):
    """HTTP API Handler"""
    
    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/health":
            self.send_json(200, {"status": "ok", "service": "image-studio"})
        
        elif parsed.path == "/models":
            # Get available SD models
            try:
                response = requests.get(f"{self.comfy}/object_info/CheckpointLoaderSimple")
                models = response.json().get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("model_name", [{}])[0].get("default", [])
                self.send_json(200, {"models": models})
            except:
                self.send_json(200, {"models": [CONFIG["default_model"]]})
        
        elif parsed.path.startswith("/output/"):
            # Download generated image
            filename = parsed.path.split("/")[-1]
            try:
                img_data = generator.download_image(filename)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Disposition", f"attachment; filename={filename}")
                self.end_headers()
                self.wfile.write(img_data)
            except Exception as e:
                self.send_json(404, {"error": str(e)})
        
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body) if body else {}
        except:
            self.send_json(400, {"error": "Invalid JSON"})
            return
        
        if parsed.path == "/generate":
            try:
                result = generator.generate_image(
                    prompt=data.get("prompt", ""),
                    negative_prompt=data.get("negative_prompt"),
                    steps=data.get("steps", 25),
                    cfg=data.get("cfg", 7.0),
                    seed=data.get("seed"),
                    model=data.get("model")
                )
                
                images = generator.get_output_images(result["job_id"])
                result["images"] = images
                
                self.send_json(200, result)
            except Exception as e:
                logger.error(f"Generation error: {e}")
                self.send_json(500, {"error": str(e)})
        
        elif parsed.path == "/batch":
            prompts = data.get("prompts", [])
            results = []
            
            for i, prompt in enumerate(prompts):
                logger.info(f"Batch {i+1}/{len(prompts)}: {prompt}")
                try:
                    result = generator.generate_image(prompt)
                    images = generator.get_output_images(result["job_id"])
                    result["images"] = images
                    results.append(result)
                except Exception as e:
                    results.append({"prompt": prompt, "error": str(e)})
            
            self.send_json(200, {"results": results})
        
        else:
            self.send_json(404, {"error": "Not found"})


def run_server(port=8080):
    """Run the API server"""
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    logger.info(f"Image Studio API running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
```

### Create Service File

```bash
sudo tee /etc/systemd/system/image-studio.service << 'EOF'
[Unit]
Description=AI Image Generation Studio
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/home/sergiok/ai-projects/image-studio
ExecStart=/home/sergiok/comfyui_env/bin/python3 api/server.py 8080
Restart=always
Environment="OLLAMA_HOST=http://localhost:11434"
Environment="COMFYUI_HOST=http://localhost:8188"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable image-studio
```

## Nginx Reverse Proxy Configuration

### Create Nginx Configuration

```bash
sudo tee /etc/nginx/sites-available/image-studio << 'EOF'
upstream image_backend {
    server 127.0.0.1:8080;
}

upstream comfyui_backend {
    server 127.0.0.1:8188;
}

server {
    listen 80;
    server_name image.yourhostname.local;

    # Redirect to HTTPS (or use HTTP for local-only)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name image.yourhostname.local;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Image Studio API
    location /api/ {
        proxy_pass http://image_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        client_max_body_size 50M;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    # ComfyUI Web Interface (for direct access)
    location /comfy/ {
        proxy_pass http://comfyui_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        client_max_body_size 100M;
    }

    # Generated images
    location /images/ {
        alias /home/sergiok/ai-projects/image-studio/output/;
        autoindex on;
    }

    # Health check
    location /health {
        proxy_pass http://image_backend/health;
        access_log off;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/image-studio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Running Locally

### Start Services

```bash
# Start ComfyUI (if not running)
source ~/comfyui_env/bin/activate
cd ~/ComfyUI
python3 main.py --listen 0.0.0.0 --port 8188 --enable-api &

# Start Image Studio API
source ~/comfyui_env/bin/activate
cd ~/ai-projects/image-studio
python3 api/server.py 8080 &

# Or use systemd
sudo systemctl start image-studio
```

### Test Locally

```bash
# Health check
curl http://localhost:8080/health

# Generate single image
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a beautiful sunset over mountains"}'

# Get available models
curl http://localhost:8080/models
```

## Remote Access from Windows/Mac

### Option 1: Direct IP Access

Find your Jetson's IP address:

```bash
hostname -I | awk '{print $1}'
```

On Windows/Mac, access:
- **API**: `http://<JETSON_IP>:8080`
- **ComfyUI**: `http://<JETSON_IP>:8188`

### Option 2: Nginx with Custom Hostname

Edit `/etc/hosts` on Windows:

```
# Windows: C:\Windows\System32\drivers\etc\hosts
192.168.1.100    image.yourhostname.local
```

On Mac:
```bash
sudo sh -c 'echo "192.168.1.100 image.yourhostname.local" >> /etc/hosts'
```

Then access:
- **API**: `https://image.yourhostname.local/api/`
- **ComfyUI**: `https://image.yourhostname.local/comfy/`

### Option 3: SSH Tunnel (No Nginx)

From Windows/Mac:

```bash
# SSH tunnel (using Putty on Windows or terminal on Mac)
ssh -L 8188:localhost:8188 -L 8080:localhost:8080 sergiok@<JETSON_IP>
```

Then access:
- **API**: `http://localhost:8080`
- **ComfyUI**: `http://localhost:8188`

## Client Examples

### Python Client

```python
import requests
import time

class ImageStudioClient:
    def __init__(self, base_url="http://<JETSON_IP>:8080"):
        self.base_url = base_url.rstrip("/")
    
    def generate(self, prompt, **kwargs):
        response = requests.post(
            f"{self.base_url}/generate",
            json={"prompt": prompt, **kwargs}
        )
        response.raise_for_status()
        return response.json()
    
    def download(self, filename):
        response = requests.get(f"{self.base_url}/output/{filename}")
        return response.content


# Usage
client = ImageStudioClient("http://192.168.1.100:8080")

# Generate image
result = client.generate("a futuristic city at night")
print(f"Generated: {result['job_id']}, seed: {result['seed']}")

# Download image
img_data = client.download(result['images'][0]['filename'])
with open("output.png", "wb") as f:
    f.write(img_data)
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

class ImageStudioClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async generate(prompt, options = {}) {
        const response = await axios.post(`${this.baseUrl}/generate`, {
            prompt,
            ...options
        });
        return response.data;
    }
    
    async downloadImage(filename) {
        const response = await axios.get(`${this.baseUrl}/output/${filename}`, {
            responseType: 'arraybuffer'
        });
        return response.data;
    }
}

const client = new ImageStudioClient('http://192.168.1.100:8080');

const result = await client.generate('a dragon flying over mountains');
console.log('Generated:', result.jobId);
```

### cURL Commands

```bash
# Generate image
curl -X POST http://192.168.1.100:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cat sitting on a windowsill",
    "steps": 25,
    "cfg": 7.0,
    "seed": 42
  }'

# Batch generation
curl -X POST http://192.168.1.100:8080/batch \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": [
      "a sunset over ocean",
      "a futuristic car",
      "a fantasy castle"
    ]
  }'
```

## Testing Procedures

### 1. Local API Test

```bash
# Test health endpoint
curl http://localhost:8080/health
# Expected: {"status": "ok", "service": "image-studio"}

# Test image generation
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a red rose", "steps": 20}'
```

### 2. Network Test

```bash
# From another machine on network
curl http://<JETSON_IP>:8080/health

# With nginx
curl https://image.yourhostname.local/health
```

### 3. Performance Test

```bash
# Generate 5 images and measure time
for i in {1..5}; do
    start=$(date +%s)
    curl -X POST http://localhost:8080/generate \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"test image $i\"}" \
        -s > /dev/null
    end=$(date +%s)
    echo "Image $i: $((end - start))s"
done
```

### 4. Ollama Integration Test

```bash
# Test Ollama prompt enhancement
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "Enhance this: a cat",
    "stream": false
  }'
```

## Troubleshooting

### ComfyUI Not Responding

```bash
# Check if ComfyUI is running
curl http://localhost:8188/system_stats

# Check ComfyUI logs
tail -f ~/ComfyUI/comfyui.log
```

### Image Generation Fails

```bash
# Check model files
ls -la ~/ComfyUI/models/checkpoints/

# Verify model is accessible
curl http://localhost:8188/object_info/CheckpointLoaderSimple
```

### Memory Issues

```bash
# Check GPU memory
tegrastats --interval 1000

# Monitor memory usage
free -h
```

### Network Access Issues

```bash
# Check firewall
sudo ufw status

# Allow ports if needed
sudo ufw allow 8080/tcp
sudo ufw allow 8188/tcp
```

## Next Steps

- [AI Audio Generation Studio](./project-02-audio-studio.md) - Text-to-speech
- [AI Video Generation Studio](./project-03-video-studio.md) - Video generation
