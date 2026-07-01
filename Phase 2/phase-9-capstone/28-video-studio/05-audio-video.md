# Creative Studio - Audio-to-Video Generation

## Overview

LTX-2.3 supports native audio-to-video generation, creating visual content that matches audio tracks. This is powerful for music videos, podcasts, and audio-reactive content.

## Audio-to-Video Generator

```python
#!/usr/bin/env python3
"""
Audio-to-Video Generation Module
"""

import os
import json
import logging
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_dir": "/opt/creative-studio/outputs",
    "input_dir": "/opt/creative-studio/inputs",
    "fal_api_key": os.environ.get("FAL_API_KEY", "")
}

for d in [CONFIG["output_dir"], CONFIG["input_dir"]]:
    os.makedirs(d, exist_ok=True)


class AudioToVideoGenerator:
    """Audio-to-video generation using LTX-2.3"""
    
    def __init__(self, provider: str = "fal_ai"):
        self.provider = provider
        self.output_dir = Path(CONFIG["output_dir"])
        self.input_dir = Path(CONFIG["input_dir"])
    
    def generate(
        self,
        audio: Union[str, Path],
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704",
        visual_style: str = "abstract",
        seed: int = -1,
        output_format: str = "mp4"
    ) -> Dict:
        """Generate video from audio"""
        
        # Prepare audio
        audio_path = self.prepare_audio(audio)
        
        # Upload to accessible URL
        audio_url = self.upload_audio(audio_path)
        
        logger.info(f"Generating video from audio: {audio_path.name}")
        
        # Call generation API
        if self.provider == "fal_ai":
            result = self.generate_fal(
                audio_url, duration, fps, resolution, visual_style, seed
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        # Save output
        output_file = self.save_output(result, output_format)
        
        return {
            "status": "success",
            "source_audio": str(audio_path),
            "visual_style": visual_style,
            "video_url": result.get("video_url"),
            "output_file": str(output_file),
            "metadata": {
                "duration": duration,
                "fps": fps,
                "resolution": resolution,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def prepare_audio(self, audio: Union[str, Path]) -> Path:
        """Validate and prepare audio file"""
        
        audio_path = Path(audio)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        
        # Convert if needed
        if audio_path.suffix.lower() not in ['.mp3', '.wav', '.ogg', '.m4a']:
            audio_path = self.convert_audio(audio_path)
        
        return audio_path
    
    def convert_audio(self, audio_path: Path) -> Path:
        """Convert audio to compatible format"""
        
        import subprocess
        
        output_path = audio_path.with_suffix('.wav')
        
        subprocess.run([
            'ffmpeg', '-i', str(audio_path),
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            '-y', str(output_path)
        ], capture_output=True)
        
        return output_path
    
    def upload_audio(self, audio_path: Path) -> str:
        """Upload audio to accessible URL"""
        
        with open(audio_path, "rb") as f:
            response = requests.post(
                "https://queue.fal.run/files/upload",
                files={"file": f},
                headers={"Authorization": f"Key {CONFIG['fal_api_key']}"},
                timeout=120
            )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("url")
        
        return f"file://{audio_path}"
    
    def generate_fal(
        self,
        audio_url: str,
        duration: int,
        fps: int,
        resolution: str,
        visual_style: str,
        seed: int
    ) -> Dict:
        """Generate via FAL.ai API"""
        
        width, height = map(int, resolution.split("x"))
        
        payload = {
            "audio_url": audio_url,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "visual_style": visual_style,
            "seed": seed
        }
        
        headers = {
            "Authorization": f"Key {CONFIG['fal_api_key']}",
            "Content-Type": "application/json"
        }
        
        # Submit request
        response = requests.post(
            "https://queue.fal.run/ltx-2-3/audio-to-video",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
        
        result = response.json()
        request_id = result.get("request_id")
        
        return self.poll_result(request_id, headers)
    
    def poll_result(self, request_id: str, headers: Dict) -> Dict:
        """Poll for result"""
        
        import time
        
        status_url = f"https://queue.fal.run/ltx-2-3/audio-to-video/requests/{request_id}/status"
        
        for _ in range(300):
            response = requests.get(status_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                status = response.json()
                
                if status.get("status") == "COMPLETED":
                    return status.get("response")
                elif status.get("status") == "FAILED":
                    raise Exception(f"Generation failed")
            
            time.sleep(2)
        
        raise Exception("Timeout")
    
    def save_output(self, result: Dict, output_format: str) -> Path:
        """Save generated video"""
        
        video_url = result.get("video_url", "")
        
        if not video_url:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audio2video_{timestamp}.{output_format}"
        output_file = self.output_dir / filename
        
        response = requests.get(video_url, timeout=300)
        
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        logger.info(f"Saved video: {output_file}")
        
        return output_file


# Visual Styles

VISUAL_STYLES = {
    "abstract": {
        "description": "Abstract shapes and colors responding to audio",
        "prompt": "Abstract flowing shapes, vibrant colors, audio-reactive patterns"
    },
    "particles": {
        "description": "Particle systems dancing to music",
        "prompt": "Floating particles, ethereal glow, musical visualization"
    },
    "waves": {
        "description": "Wave forms matching audio frequencies",
        "prompt": "Sine waves, equalizer visualization, flowing ribbons"
    },
    "nature": {
        "description": "Natural elements responding to audio",
        "prompt": "Nature scenes, trees swaying, water rippling"
    },
    "geometric": {
        "description": "Geometric shapes and patterns",
        "prompt": "Geometric shapes, rotating cubes, mathematical patterns"
    },
    "cinematic": {
        "description": "Cinematic visuals for dramatic audio",
        "prompt": "Cinematic atmosphere, dramatic lighting, film grain"
    }
}


# API Integration

def setup_a2v_api(app):
    """Setup Flask API routes"""
    
    generator = AudioToVideoGenerator()
    
    @app.route("/api/generate/audio2video", methods=["POST"])
    def audio2video():
        """Generate video from audio"""
        data = request.get_json()
        
        audio = data.get("audio")
        
        if not audio:
            return jsonify({"error": "No audio provided"}), 400
        
        # Handle base64
        if isinstance(audio, str) and audio.startswith("data:audio"):
            import re
            header, b64data = re.split(r',', audio, 1)
            audio_data = base64.b64decode(b64data)
            
            audio_path = CONFIG["input_dir"] / f"upload_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
            with open(audio_path, "wb") as f:
                f.write(audio_data)
            audio = audio_path
        
        result = generator.generate(
            audio=audio,
            duration=data.get("duration", 5),
            fps=data.get("fps", 24),
            resolution=data.get("resolution", "1216x704"),
            visual_style=data.get("visual_style", "abstract"),
            seed=data.get("seed", -1)
        )
        
        return jsonify(result)
    
    @app.route("/api/generate/visual-styles", methods=["GET"])
    def get_visual_styles():
        """Get available visual styles"""
        return jsonify(VISUAL_STYLES)
```

## Audio Generation with Ollama/Piper

For generating audio first, then video:

```python
#!/usr/bin/env python3
"""
Audio Generation + Video Creation Pipeline
"""

import requests
from pathlib import Path
from datetime import datetime


class AudioVideoPipeline:
    """Generate audio, then create matching video"""
    
    def __init__(self):
        self.output_dir = Path("/opt/creative-studio/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_audio(self, prompt: str, voice: str = "en_US-lessac") -> Path:
        """Generate audio using Piper TTS"""
        
        # Use Ollama to create script
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5-coder:14b",
                "prompt": f"Create a short 15-second narration script for: {prompt}",
                "stream": False
            }
        )
        
        script = response.json().get("response", "")[:200]
        
        # Use Piper TTS
        import subprocess
        
        output_path = self.output_dir / f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        
        subprocess.run([
            'piper',
            '--model', f'/opt/piper/voices/{voice}.onnx',
            '--output_file', str(output_path)
        ], input=script.encode(), capture_output=True)
        
        return output_path
    
    def create_video(
        self,
        audio_path: Path,
        visual_style: str = "cinematic",
        duration: int = 15
    ) -> Path:
        """Create video from audio"""
        
        from ltxx import AudioToVideoGenerator
        
        a2v = AudioToVideoGenerator()
        
        result = a2v.generate(
            audio=audio_path,
            duration=min(duration, 10),  # Max 10s for API
            visual_style=visual_style
        )
        
        return Path(result["output_file"])
    
    def pipeline(
        self,
        prompt: str,
        voice: str = "en_US-lessac",
        visual_style: str = "cinematic"
    ) -> Dict:
        """Complete audio-to-video pipeline"""
        
        # Step 1: Generate audio
        audio_path = self.generate_audio(prompt, voice)
        
        # Step 2: Create video
        video_path = self.create_video(audio_path, visual_style)
        
        return {
            "audio": str(audio_path),
            "video": str(video_path),
            "script": prompt
        }
```

## Music Video Workflow

```python
# Create music video from track

# 1. Get audio file
audio_file = Path("/music/track.mp3")

# 2. Generate video with abstract visuals
a2v = AudioToVideoGenerator()

video = a2v.generate(
    audio=audio_file,
    duration=30,
    visual_style="abstract",
    fps=30,
    resolution="1920x1080"
)

# 3. Enhance with FFmpeg
from ffmpeg import FFmpeg

# Add fade in/out
FFmpeg.trim(
    input=video["output_file"],
    start=0,
    duration=30
).output(
    "/music_video_final.mp4",
    **{"c:v": "libx264", "preset": "slow", "crf": 18}
).run()
```

## Next Steps

- [06-workflows](./06-workflows.md) - Complex workflows
