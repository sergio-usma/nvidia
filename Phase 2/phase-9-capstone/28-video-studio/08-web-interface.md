# Creative Studio - Web Interface

## Overview

The Creative Studio web interface provides a user-friendly browser-based interface for video generation. Running on port 8083.

## Interface Features

- **Dashboard**: Overview of projects, recent generations
- **Text-to-Video**: Generate from prompts
- **Image-to-Video**: Animate images
- **Audio-to-Video**: Visualize audio
- **Projects**: Manage video projects
- **Gallery**: View generated videos
- **Settings**: Configure API keys, preferences

## Web Server Implementation

```python
#!/usr/bin/env python3
"""
Creative Studio Web Server
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

CONFIG = {
    "host": "0.0.0.0",
    "port": 8083,
    "output_dir": "/opt/creative-studio/outputs",
    "input_dir": "/opt/creative-studio/inputs",
    "templates_dir": "/opt/creative-studio/web/templates"
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)
os.makedirs(CONFIG["input_dir"], exist_ok=True)


# ==================== ROUTES ====================

@app.route("/")
def index():
    """Main dashboard"""
    return render_template("index.html")


@app.route("/text2video")
def text2video():
    """Text-to-video page"""
    return render_template("text2video.html")


@app.route("/image2video")
def image2video():
    """Image-to-video page"""
    return render_template("image2video.html")


@app.route("/audio2video")
def audio2video():
    """Audio-to-video page"""
    return render_template("audio2video.html")


@app.route("/projects")
def projects():
    """Projects page"""
    return render_template("projects.html")


@app.route("/gallery")
def gallery():
    """Gallery page"""
    return render_template("gallery.html")


@app.route("/settings")
def settings():
    """Settings page"""
    return render_template("settings.html")


# ==================== API PROXY ====================

@app.route("/api/generate/text2video", methods=["POST"])
def generate_text2video():
    """Proxy to generation API"""
    from text2video import TextToVideoGenerator
    
    data = request.get_json()
    
    generator = TextToVideoGenerator()
    
    try:
        result = generator.generate(
            prompt=data.get("prompt", ""),
            duration=data.get("duration", 5),
            fps=data.get("fps", 24),
            resolution=data.get("resolution", "1216x704"),
            quality=data.get("quality", "high"),
            seed=data.get("seed", -1)
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate/image2video", methods=["POST"])
def generate_image2video():
    """Proxy to image2video API"""
    from image2video import ImageToVideoGenerator
    
    data = request.get_json()
    
    generator = ImageToVideoGenerator()
    
    try:
        result = generator.generate(
            image=data.get("image"),
            prompt=data.get("prompt", ""),
            duration=data.get("duration", 5)
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/gallery")
def get_gallery():
    """Get generated videos"""
    output_dir = Path(CONFIG["output_dir"])
    
    videos = []
    for f in sorted(output_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
        videos.append({
            "name": f.name,
            "path": f"/outputs/{f.name}",
            "size": f.stat().st_size,
            "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    
    return jsonify(videos)


@app.route("/outputs/<path:filename>")
def serve_output(filename):
    """Serve output files"""
    return send_from_directory(CONFIG["output_dir"], filename)


@app.route("/api/presets")
def get_presets():
    """Get generation presets"""
    return jsonify({
        "text2video": {
            "cinematic": {"duration": 5, "fps": 24, "resolution": "1216x704"},
            "fast": {"duration": 3, "fps": 24, "resolution": "704x576"},
            "portrait": {"duration": 5, "fps": 24, "resolution": "1080x1920"}
        },
        "motion": {
            "gentle": {"strength": 0.3},
            "moderate": {"strength": 0.5},
            "dynamic": {"strength": 0.7}
        }
    })


# ==================== MAIN ====================

if __name__ == "__main__":
    logger.info(f"Starting Creative Studio on port {CONFIG['port']}")
    app.run(host=CONFIG["host"], port=CONFIG["port"], debug=False)
```

## HTML Templates

### Base Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Creative Studio{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }
    </style>
    {% block styles %}{% endblock %}
</head>
<body class="gradient-bg min-h-screen text-white">
    <nav class="bg-gray-900/80 backdrop-blur-sm border-b border-gray-800">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center space-x-8">
                    <a href="/" class="text-xl font-bold text-purple-400">🎬 Creative Studio</a>
                    <div class="flex space-x-4">
                        <a href="/text2video" class="hover:text-purple-400 transition">Text→Video</a>
                        <a href="/image2video" class="hover:text-purple-400 transition">Image→Video</a>
                        <a href="/audio2video" class="hover:text-purple-400 transition">Audio→Video</a>
                        <a href="/projects" class="hover:text-purple-400 transition">Projects</a>
                        <a href="/gallery" class="hover:text-purple-400 transition">Gallery</a>
                    </div>
                </div>
                <a href="/settings" class="hover:text-purple-400 transition">⚙️</a>
            </div>
        </div>
    </nav>
    
    <main class="max-w-7xl mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Text-to-Video Page

```html
{% extends "base.html" %}

{% block title %}Text to Video - Creative Studio{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto">
    <h1 class="text-3xl font-bold mb-8">Text to Video</h1>
    
    <form id="generate-form" class="space-y-6">
        <div>
            <label class="block text-sm font-medium mb-2">Prompt</label>
            <textarea 
                id="prompt" 
                rows="4"
                class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Describe your video... (e.g., A serene lake at sunset with birds flying)"
            ></textarea>
        </div>
        
        <div class="grid grid-cols-3 gap-4">
            <div>
                <label class="block text-sm font-medium mb-2">Duration</label>
                <select id="duration" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg">
                    <option value="3">3 seconds</option>
                    <option value="5" selected>5 seconds</option>
                    <option value="10">10 seconds</option>
                </select>
            </div>
            
            <div>
                <label class="block text-sm font-medium mb-2">FPS</label>
                <select id="fps" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg">
                    <option value="24" selected>24 fps</option>
                    <option value="30">30 fps</option>
                    <option value="48">48 fps</option>
                </select>
            </div>
            
            <div>
                <label class="block text-sm font-medium mb-2">Resolution</label>
                <select id="resolution" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg">
                    <option value="704x576">704×576</option>
                    <option value="1216x704" selected>1216×704</option>
                    <option value="1920x1080">1920×1080</option>
                    <option value="1080x1920">1080×1920 (Portrait)</option>
                </select>
            </div>
        </div>
        
        <button 
            type="submit" 
            class="w-full py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold transition"
        >
            Generate Video
        </button>
    </form>
    
    <div id="result" class="mt-8 hidden">
        <h2 class="text-xl font-semibold mb-4">Result</h2>
        <video id="video-player" controls class="w-full rounded-lg"></video>
        <a id="download-link" href="#" class="inline-block mt-4 px-6 py-2 bg-green-600 rounded-lg hover:bg-green-700">
            Download
        </a>
    </div>
    
    <div id="loading" class="mt-8 hidden">
        <div class="flex items-center justify-center space-x-4">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            <span>Generating video...</span>
        </div>
    </div>
</div>

{% block scripts %}
<script>
const form = document.getElementById('generate-form');
const loading = document.getElementById('loading');
const result = document.getElementById('result');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const prompt = document.getElementById('prompt').value;
    const duration = parseInt(document.getElementById('duration').value);
    const fps = parseInt(document.getElementById('fps').value);
    const resolution = document.getElementById('resolution').value;
    
    form.classList.add('hidden');
    loading.classList.remove('hidden');
    
    try {
        const response = await fetch('/api/generate/text2video', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt, duration, fps, resolution})
        });
        
        const data = await response.json();
        
        loading.classList.add('hidden');
        result.classList.remove('hidden');
        
        document.getElementById('video-player').src = data.output_file;
        document.getElementById('download-link').href = data.output_file;
        
    } catch (error) {
        loading.classList.add('hidden');
        form.classList.remove('hidden');
        alert('Error: ' + error.message);
    }
});
</script>
{% endblock %}
```

### Gallery Page

```html
{% extends "base.html" %}

{% block title %}Gallery - Creative Studio{% endblock %}

{% block content %}
<h1 class="text-3xl font-bold mb-8">Generated Videos</h1>

<div id="gallery" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    <div class="animate-pulse">Loading...</div>
</div>

<script>
async function loadGallery() {
    const response = await fetch('/api/gallery');
    const videos = await response.json();
    
    const gallery = document.getElementById('gallery');
    gallery.innerHTML = videos.map(video => `
        <div class="bg-gray-800 rounded-lg overflow-hidden">
            <video src="${video.path}" class="w-full" controls></video>
            <div class="p-4">
                <p class="text-sm text-gray-400">${new Date(video.created).toLocaleString()}</p>
                <p class="text-sm">${(video.size / 1024 / 1024).toFixed(1)} MB</p>
            </div>
        </div>
    `).join('');
}

loadGallery();
</script>
{% endblock %}
```

## Accessing the Interface

```bash
# Start server
python /opt/creative-studio/web/main.py

# Access
http://jetson:8083
```

## Features

| Feature | Description |
|---------|-------------|
| Text-to-Video | Generate videos from text prompts |
| Image-to-Video | Animate static images |
| Audio-to-Video | Visualize audio tracks |
| Project Management | Organize video projects |
| Gallery | Browse generated videos |
| Presets | Quick generation settings |
| Download | Save generated videos |

## Next Steps

- [09-integration](./09-integration.md) - Project integration
