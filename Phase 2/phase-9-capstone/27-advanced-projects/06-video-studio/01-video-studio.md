# AI Video Generation Studio

## Project Overview

This project creates a complete AI-powered video generation studio running on the Jetson AGX Orin, accessible remotely via web browser or API from any Windows or Mac computer on your local network.

### Features

- **Story-to-Video**: Convert text stories into animated video sequences
- **Frame-by-Frame Generation**: Generate individual frames using Stable Diffusion
- **AI Scene Processing**: Use Ollama to split stories into scenes and enhance prompts
- **Remote Access**: Access via nginx reverse proxy or direct IP
- **API Access**: REST API for programmatic video generation
- **Multiple Output Formats**: Support for MP4, GIF, and frame sequences

### Architecture

```
Windows/Mac Host → Local Network → Nginx (Jetson) → ComfyUI + Ollama → FFmpeg
                                                                        ↓
                                                                  Video Output
```

## Prerequisites

### Services Running

Ensure the following services are running:

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Check ComfyUI
curl http://localhost:8188/system_stats
```

### Install FFmpeg

```bash
sudo apt update
sudo apt install -y ffmpeg

# Verify installation
ffmpeg -version
```

### ComfyUI Setup

Make sure ComfyUI is set up with Stable Diffusion models as described in the Image Studio project.

## Project Setup

### Create Project Directory

```bash
mkdir -p ~/ai-projects/video-studio/{api,frames,output,logs}
cd ~/ai-projects/video-studio
```

### Create the Video Generation API

```python
#!/usr/bin/env python3
"""
AI Video Generation Studio API
Provides REST API for video generation from stories using ComfyUI and Ollama
"""

import os
import sys
import json
import time
import logging
import subprocess
import uuid
import requests
import shutil
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
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

CONFIG = {
    "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "comfyui_host": os.getenv("COMFYUI_HOST", "http://localhost:8188"),
    "frames_dir": os.path.expanduser("~/ai-projects/video-studio/frames"),
    "output_dir": os.path.expanduser("~/ai-projects/video-studio/output"),
    "default_ollama": os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.2:3b"),
    "default_sd_model": os.getenv("DEFAULT_SD_MODEL", "sd_xl_base_1.0.safetensors"),
    "default_fps": int(os.getenv("DEFAULT_FPS", "2")),
    "default_frames": int(os.getenv("DEFAULT_FRAMES", "8"))
}

os.makedirs(CONFIG["frames_dir"], exist_ok=True)
os.makedirs(CONFIG["output_dir"], exist_ok=True)
os.makedirs("logs", exist_ok=True)


class VideoGenerator:
    """Core video generation engine"""
    
    def __init__(self):
        self.ollama = CONFIG["ollama_host"]
        self.comfy = CONFIG["comfyui_host"]
        self.frames_dir = CONFIG["frames_dir"]
        self.output_dir = CONFIG["output_dir"]
    
    def split_story_into_scenes(self, story, num_scenes=None):
        """Use Ollama to split story into scenes"""
        
        if num_scenes is None:
            num_scenes = CONFIG["default_frames"]
        
        prompt = f"""Split this story into exactly {num_scenes} distinct scenes.
Each scene should be 1-2 sentences describing a visual moment.
Return ONLY the scenes, one per line, numbered or with bullet points.

Story:
{story}

Scenes:"""
        
        try:
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": CONFIG["default_ollama"],
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            
            scenes_text = response.json().get("response", "")
            
            # Parse scenes
            scenes = []
            for line in scenes_text.strip().split("\n"):
                line = line.strip()
                # Remove numbering/bullets
                line = line.lstrip("0123456789.-*). ").strip()
                if line and len(line) > 10:
                    scenes.append(line)
            
            # Limit to requested number
            scenes = scenes[:num_scenes]
            
            # If parsing failed, create simple scenes
            if len(scenes) < 2:
                story_sentences = story.replace("\n", " ").split(".")
                scenes = [s.strip() + "." for s in story_sentences if s.strip()][:num_scenes]
            
            logger.info(f"Split story into {len(scenes)} scenes")
            return scenes
            
        except Exception as e:
            logger.error(f"Scene splitting failed: {e}")
            # Fallback: split by sentences
            sentences = story.replace("\n", " ").split(".")
            return [s.strip() + "." for s in sentences if s.strip()][:num_scenes]
    
    def enhance_scene_prompt(self, scene):
        """Enhance scene into detailed image prompt"""
        
        prompt = f"""Create a detailed stable diffusion prompt for this scene.
Include: subject, setting, lighting, mood, style, composition.
Keep it under 100 words.

Scene: {scene}

Prompt:"""
        
        try:
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": CONFIG["default_ollama"],
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            enhanced = response.json().get("response", scene).strip()
            logger.info(f"Enhanced prompt: {enhanced[:80]}...")
            return enhanced
            
        except Exception as e:
            logger.warning(f"Prompt enhancement failed: {e}")
            return scene
    
    def generate_frame(self, prompt, frame_index, seed=None, 
                     negative_prompt=None, steps=20):
        """Generate single frame via ComfyUI"""
        
        if seed is None:
            seed = 1000 + frame_index
        
        if negative_prompt is None:
            negative_prompt = "low quality, blurry, deformed, ugly, bad anatomy, watermark, text"
        
        # Create workflow for this frame
        workflow = {
            "1": {
                "inputs": {"model_name": CONFIG["default_sd_model"]},
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {"text": prompt, "clip": ["1", 1]},
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
                    "cfg": 7.0,
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
                    "filename_prefix": f"frame_{frame_index:04d}"
                },
                "class_type": "SaveImage"
            }
        }
        
        # Submit job
        logger.info(f"Generating frame {frame_index} with seed {seed}")
        response = requests.post(
            f"{self.comfy}/prompt",
            json={"prompt": workflow},
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to submit frame job: {response.text}")
        
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
                        logger.info(f"Frame {frame_index} generated in {elapsed:.1f}s")
                        return {"job_id": job_id, "seed": seed, "elapsed": elapsed}
                    elif status.get("error"):
                        raise Exception(f"Frame error: {status['error']}")
            except Exception as e:
                logger.warning(f"Status check error: {e}")
            
            if time.time() - start_time > 600:
                raise Exception(f"Frame {frame_index} generation timeout")
    
    def get_generated_frame_path(self, frame_index):
        """Get path to generated frame"""
        # ComfyUI saves as frame_0001_00001.png
        possible_names = [
            f"frame_{frame_index:04d}_0001_.png",
            f"frame_{frame_index:04d}-0001.png",
        ]
        
        for name in possible_names:
            # Check ComfyUI output
            output_path = os.path.expanduser("~/ComfyUI/output")
            full_path = os.path.join(output_path, name)
            if os.path.exists(full_path):
                return full_path
        
        return None
    
    def combine_frames_to_video(self, frame_paths, output_file, fps=None):
        """Combine frames into video using FFmpeg"""
        
        if fps is None:
            fps = CONFIG["default_fps"]
        
        # Create temp directory for frame list
        list_file = os.path.join(self.output_dir, f"frames_{uuid.uuid4().hex}.txt")
        
        with open(list_file, "w") as f:
            for frame_path in frame_paths:
                # FFmpeg needs absolute paths
                abs_path = os.path.abspath(frame_path)
                f.write(f"file '{abs_path}'\n")
                f.write(f"duration {1/fps}\n")
        
        # Run FFmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-vsync", "vfr",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            output_file
        ]
        
        logger.info(f"Creating video: {output_file}")
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        
        # Cleanup
        os.remove(list_file)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr.decode()}")
        
        return output_file
    
    def generate_video(self, story, num_frames=None, fps=None, 
                      seed_start=None, enhance_prompts=True):
        """Generate complete video from story"""
        
        if num_frames is None:
            num_frames = CONFIG["default_frames"]
        
        if fps is None:
            fps = CONFIG["default_fps"]
        
        if seed_start is None:
            seed_start = int(time.time()) % 10000
        
        # Create unique session directory
        session_id = uuid.uuid4().hex[:8]
        session_dir = os.path.join(self.frames_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        logger.info(f"Starting video generation: session={session_id}, frames={num_frames}")
        start_time = time.time()
        
        # Step 1: Split story into scenes
        scenes = self.split_story_into_scenes(story, num_frames)
        
        # Step 2: Generate frames
        frame_paths = []
        
        for i, scene in enumerate(scenes):
            logger.info(f"Processing scene {i+1}/{len(scenes)}: {scene[:50]}...")
            
            # Enhance prompt
            if enhance_prompts:
                prompt = self.enhance_scene_prompt(scene)
            else:
                prompt = scene
            
            # Generate frame
            result = self.generate_frame(prompt, i, seed=seed_start + i)
            
            # Find generated frame
            frame_path = self.get_generated_frame_path(i)
            
            if frame_path:
                # Copy to session directory
                dest_path = os.path.join(session_dir, f"frame_{i:04d}.png")
                shutil.copy2(frame_path, dest_path)
                frame_paths.append(dest_path)
            else:
                logger.warning(f"Could not find frame {i}")
        
        # Step 3: Combine frames into video
        output_file = os.path.join(
            self.output_dir, 
            f"video_{session_id}_{int(time.time())}.mp4"
        )
        
        self.combine_frames_to_video(frame_paths, output_file, fps)
        
        elapsed = time.time() - start_time
        
        logger.info(f"Video generated: {output_file} in {elapsed:.1f}s")
        
        return {
            "session_id": session_id,
            "output_file": output_file,
            "num_frames": len(frame_paths),
            "fps": fps,
            "elapsed_seconds": elapsed,
            "scenes": scenes
        }
    
    def generate_animation(self, prompt, num_frames=16, fps=4, 
                          seed_start=1000, steps=20):
        """Generate animation from single prompt with seed variation"""
        
        session_id = uuid.uuid4().hex[:8]
        session_dir = os.path.join(self.frames_dir, f"anim_{session_id}")
        os.makedirs(session_dir, exist_ok=True)
        
        logger.info(f"Starting animation: {num_frames} frames")
        start_time = time.time()
        
        frame_paths = []
        
        for i in range(num_frames):
            # Slight seed variation for smooth animation
            seed = seed_start + i
            
            # Add slight prompt variation for animation
            variation = f"{prompt} (frame {i+1}/{num_frames})"
            
            result = self.generate_frame(variation, i, seed=seed, steps=steps)
            
            frame_path = self.get_generated_frame_path(i)
            
            if frame_path:
                dest_path = os.path.join(session_dir, f"frame_{i:04d}.png")
                shutil.copy2(frame_path, dest_path)
                frame_paths.append(dest_path)
        
        # Create video
        output_file = os.path.join(
            self.output_dir, 
            f"animation_{session_id}_{int(time.time())}.mp4"
        )
        
        self.combine_frames_to_video(frame_paths, output_file, fps)
        
        elapsed = time.time() - start_time
        
        return {
            "session_id": session_id,
            "output_file": output_file,
            "num_frames": len(frame_paths),
            "fps": fps,
            "elapsed_seconds": elapsed
        }


generator = VideoGenerator()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "video-studio"})


@app.route("/generate", methods=["POST"])
def generate():
    """Generate video from story"""
    data = request.get_json()
    
    if not data or "story" not in data:
        return jsonify({"error": "Missing 'story' parameter"}), 400
    
    try:
        result = generator.generate_video(
            story=data["story"],
            num_frames=data.get("num_frames"),
            fps=data.get("fps"),
            seed_start=data.get("seed_start"),
            enhance_prompts=data.get("enhance_prompts", True)
        )
        
        # Add download URL
        filename = os.path.basename(result["output_file"])
        result["download_url"] = f"/download/{filename}"
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/animation", methods=["POST"])
def animation():
    """Generate animation from single prompt"""
    data = request.get_json()
    
    if not data or "prompt" not in data:
        return jsonify({"error": "Missing 'prompt' parameter"}), 400
    
    try:
        result = generator.generate_animation(
            prompt=data["prompt"],
            num_frames=data.get("num_frames", 16),
            fps=data.get("fps", 4),
            seed_start=data.get("seed_start", 1000),
            steps=data.get("steps", 20)
        )
        
        filename = os.path.basename(result["output_file"])
        result["download_url"] = f"/download/{filename}"
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Animation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/preview-frames", methods=["POST"])
def preview_frames():
    """Preview frames without creating video"""
    data = request.get_json()
    
    if not data or "story" not in data:
        return jsonify({"error": "Missing 'story' parameter"}), 400
    
    try:
        scenes = generator.split_story_into_scenes(
            data["story"], 
            data.get("num_frames", 8)
        )
        
        enhanced_prompts = []
        for scene in scenes:
            if data.get("enhance_prompts", True):
                enhanced = generator.enhance_scene_prompt(scene)
                enhanced_prompts.append(enhanced)
            else:
                enhanced_prompts.append(scene)
        
        return jsonify({
            "scenes": scenes,
            "enhanced_prompts": enhanced_prompts
        })
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    """Download generated video"""
    filepath = os.path.join(CONFIG["output_dir"], secure_filename(filename))
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    @after_this_request
    def remove_file(response):
        return response
    
    return send_file(
        filepath,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=filename
    )


@app.route("/list", methods=["GET"])
def list_videos():
    """List generated videos"""
    videos = []
    for f in os.listdir(CONFIG["output_dir"]):
        if f.endswith((".mp4", ".gif")):
            filepath = os.path.join(CONFIG["output_dir"], f)
            videos.append({
                "filename": f,
                "size": os.path.getsize(filepath),
                "created": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                "download_url": f"/download/{f}"
            })
    
    return jsonify({"videos": sorted(videos, key=lambda x: x["created"], reverse=True)})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    app.run(host="0.0.0.0", port=port, debug=False)
```

### Create Service File

```bash
sudo tee /etc/systemd/system/video-studio.service << 'EOF'
[Unit]
Description=AI Video Generation Studio
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/home/sergiok/ai-projects/video-studio
ExecStart=/home/sergiok/comfyui_env/bin/python3 api/server.py 8082
Restart=always
Environment="OLLAMA_HOST=http://localhost:11434"
Environment="COMFYUI_HOST=http://localhost:8188"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable video-studio
```

## Nginx Reverse Proxy Configuration

```bash
sudo tee /etc/nginx/sites-available/video-studio << 'EOF'
upstream video_backend {
    server 127.0.0.1:8082;
}

server {
    listen 80;
    server_name video.yourhostname.local;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name video.yourhostname.local;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Video Studio API
    location / {
        proxy_pass http://video_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        client_max_body_size 50M;
        proxy_read_timeout 1800s;
        proxy_send_timeout 1800s;
    }

    # Health check
    location /health {
        proxy_pass http://video_backend/health;
        access_log off;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/video-studio /etc/nginx/sites-enabled/
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

# Start Video Studio API
source ~/comfyui_env/bin/activate
cd ~/ai-projects/video-studio
python3 api/server.py 8082 &

# Or use systemd
sudo systemctl start video-studio
```

### Test Locally

```bash
# Health check
curl http://localhost:8082/health

# Preview frames (no video generation)
curl -X POST http://localhost:8082/preview-frames \
  -H "Content-Type: application/json" \
  -d '{"story": "A dragon flies over mountains. It lands in a forest."}'

# List generated videos
curl http://localhost:8082/list
```

## Remote Access from Windows/Mac

### Option 1: Direct IP Access

```bash
# Find Jetson IP
hostname -I | awk '{print $1}'
```

On Windows/Mac, access:
- **Video API**: `http://<JETSON_IP>:8082`

### Option 2: Nginx with Custom Hostname

Edit `/etc/hosts`:
- **Windows**: `C:\Windows\System32\drivers\etc\hosts`
- **Mac**: `/etc/hosts`

```
192.168.1.100    video.yourhostname.local
```

Then access: `https://video.yourhostname.local/`

### Option 3: SSH Tunnel

```bash
ssh -L 8082:localhost:8082 sergiok@<JETSON_IP>
```

Then access: `http://localhost:8082`

## Client Examples

### Python Client

```python
import requests
import json

class VideoStudioClient:
    def __init__(self, base_url="http://<JETSON_IP>:8082"):
        self.base_url = base_url.rstrip("/")
    
    def generate(self, story, **kwargs):
        """Generate video from story"""
        response = requests.post(
            f"{self.base_url}/generate",
            json={"story": story, **kwargs},
            timeout=1800  # 30 minutes
        )
        response.raise_for_status()
        result = response.json()
        
        # Download video
        if "download_url" in result:
            video_url = f"{self.base_url}{result['download_url']}"
            video_data = requests.get(video_url).content
            
            filename = result["download_url"].split("/")[-1]
            with open(filename, "wb") as f:
                f.write(video_data)
            result["saved_to"] = filename
        
        return result
    
    def animate(self, prompt, **kwargs):
        """Generate animation from single prompt"""
        response = requests.post(
            f"{self.base_url}/animation",
            json={"prompt": prompt, **kwargs},
            timeout=1800
        )
        response.raise_for_status()
        return response.json()
    
    def preview(self, story, **kwargs):
        """Preview scenes without generating video"""
        response = requests.post(
            f"{self.base_url}/preview-frames",
            json={"story": story, **kwargs}
        )
        return response.json()
    
    def list_videos(self):
        """List generated videos"""
        response = requests.get(f"{self.base_url}/list")
        return response.json()


# Usage
client = VideoStudioClient("http://192.168.1.100:8082")

# Preview story scenes first
preview = client.preview("""
    A dragon flying over mountains at sunset
    The dragon lands in a mystical forest
    The dragon meets another dragon
    They fly together into the clouds
""")
print("Scenes:", preview["scenes"])

# Generate video
result = client.generate("""
    A dragon flying over mountains at sunset.
    The dragon lands in a mystical forest.
    The dragon meets another dragon.
    They fly together into the clouds.
    The dragons soar higher than the clouds.
    They discover a hidden castle in the sky.
""", num_frames=8, fps=2)
print(f"Video saved to: {result.get('saved_to')}")

# Generate animation
result = client.animate(
    "a flowing river with mountains in background, cinematic",
    num_frames=16,
    fps=4
)
print(f"Animation: {result['output_file']}")
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');
const fs = require('fs');

class VideoStudioClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async generate(story, options = {}) {
        const response = await axios.post(`${this.baseUrl}/generate`, {
            story,
            ...options
        }, {
            timeout: 1800000 // 30 min
        });
        
        const result = response.data;
        
        // Download video
        if (result.download_url) {
            const videoData = await axios.get(
                `${this.baseUrl}${result.download_url}`,
                { responseType: 'arraybuffer' }
            );
            
            const filename = result.download_url.split('/').pop();
            fs.writeFileSync(filename, videoData.data);
            result.saved_to = filename;
        }
        
        return result;
    }
    
    async preview(story) {
        const response = await axios.post(`${this.base_url}/preview-frames`, { story });
        return response.data;
    }
}

const client = new VideoStudioClient('http://192.168.1.100:8082');

// Generate video
const result = await client.generate(`
    A cat sitting on a windowsill.
    The cat sees a bird outside.
    The cat jumps after the bird.
    The cat lands safely on the ground.
`);
console.log('Video saved to:', result.saved_to);
```

### cURL Commands

```bash
# Generate video from story
curl -X POST http://192.168.1.100:8082/generate \
  -H "Content-Type: application/json" \
  -d '{
    "story": "A dragon flying over mountains. It lands in a forest.",
    "num_frames": 6,
    "fps": 2
  }' \
  -o video.mp4

# Preview scenes
curl -X POST http://192.168.1.100:8082/preview-frames \
  -H "Content-Type: application/json" \
  -d '{"story": "A sunset over ocean. Waves crashing on rocks."}'

# Generate animation
curl -X POST http://192.168.1.100:8082/animation \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a flowing river with mountains",
    "num_frames": 12,
    "fps": 4
  }'

# List videos
curl http://192.168.1.100:8082/list
```

## Testing Procedures

### 1. Local API Test

```bash
# Health check
curl http://localhost:8082/health
# Expected: {"status": "ok", "service": "video-studio"}

# Preview story
curl -X POST http://localhost:8082/preview-frames \
  -H "Content-Type: application/json" \
  -d '{"story": "A cat. A dog. A bird."}'

# List videos
curl http://localhost:8082/list
```

### 2. Generate Test Video

```bash
# Generate simple 4-frame video
curl -X POST http://localhost:8082/generate \
  -H "Content-Type: application/json" \
  -d '{
    "story": "A red ball. A blue ball. A green ball. A yellow ball.",
    "num_frames": 4,
    "fps": 1
  }'
```

### 3. Ollama Integration Test

```bash
# Test scene splitting
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "Split this into 4 scenes: A dragon flies over mountains. It sees a castle. It lands in the courtyard. The end.",
    "stream": false
  }'
```

### 4. Performance Test

```bash
# Time video generation
start=$(date +%s)
curl -X POST http://localhost:8082/generate \
  -H "Content-Type: application/json" \
  -d '{"story": "Frame one. Frame two. Frame three.", "num_frames": 3}' \
  -s > /dev/null
end=$(date +%s)
echo "Total time: $((end - start))s"
```

## Troubleshooting

### Frame Generation Fails

```bash
# Check ComfyUI is running
curl http://localhost:8188/system_stats

# Check model files
ls -la ~/ComfyUI/models/checkpoints/

# Check ComfyUI logs
tail -f ~/ComfyUI/comfyui.log
```

### Video Creation Fails

```bash
# Check FFmpeg
ffmpeg -version

# Check frames directory
ls -la ~/ai-projects/video-studio/frames/

# Check output permissions
ls -la ~/ai-projects/video-studio/output/
```

### Memory Issues

```bash
# Monitor GPU
tegrastats --interval 1000

# Monitor memory
free -h

# Reduce frame count or resolution
# In API call: num_frames: 4, steps: 15
```

### Timeout Issues

```bash
# Video generation can take 10+ minutes
# Check nginx timeout settings
# Increase: proxy_read_timeout 1800s;
```

## Advanced Options

### Higher Quality Video

```python
# Use more frames and steps
result = client.generate(
    story,
    num_frames=16,      # More frames = longer video
    fps=3,              # Higher fps = smoother
    enhance_prompts=True
)
```

### Animation Mode

```python
# Create animated loop from single concept
result = client.animate(
    "a flowing river at sunset, cinematic lighting",
    num_frames=24,      # More frames for animation
    fps=6,              # Higher fps = smoother
    steps=25            # More steps = better quality
)
```

## Next Steps

- [AI Image Generation Studio](./project-01-image-studio.md) - Image generation
- [AI Audio Generation Studio](./project-02-audio-studio.md) - Audio generation
