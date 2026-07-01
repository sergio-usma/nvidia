# Creative Studio - Text-to-Video Generation

## Overview

Text-to-video generation creates videos from text prompts using LTX-2.3. This guide covers prompt engineering, generation options, and workflow automation.

## Basic Text-to-Video

```python
#!/usr/bin/env python3
"""
Text-to-Video Generation Module
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_dir": "/opt/creative-studio/outputs",
    "api_url": "http://localhost:8083",
    "fal_api_key": os.environ.get("FAL_API_KEY", "")
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)


class TextToVideoGenerator:
    """Text-to-video generation using LTX-2.3"""
    
    def __init__(self, provider: str = "fal_ai"):
        self.provider = provider
        self.output_dir = Path(CONFIG["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704",
        quality: str = "high",
        seed: int = -1,
        enhance_prompt: bool = True,
        output_format: str = "mp4"
    ) -> Dict:
        """Generate video from text prompt"""
        
        # Enhance prompt if enabled
        if enhance_prompt:
            prompt = self.enhance_prompt(prompt)
        
        logger.info(f"Generating video: {prompt[:50]}...")
        
        # Call generation API
        if self.provider == "fal_ai":
            result = self.generate_fal(
                prompt, duration, fps, resolution, quality, seed
            )
        elif self.provider == "comfyui":
            result = self.generate_comfyui(
                prompt, duration, fps, resolution, seed
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        # Save output
        output_file = self.save_output(result, output_format)
        
        return {
            "status": "success",
            "prompt": prompt,
            "video_url": result.get("video_url"),
            "audio_url": result.get("audio_url"),
            "output_file": str(output_file),
            "metadata": {
                "duration": duration,
                "fps": fps,
                "resolution": resolution,
                "seed": seed,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def enhance_prompt(self, prompt: str) -> str:
        """Enhance prompt using Ollama"""
        
        enhancement_prompt = f"""Create a detailed, cinematic LTX-2.3 video generation prompt:

Base concept: {prompt}

Expand to include:
- Subject details and characteristics
- Action or movement description
- Environment and setting
- Lighting (time of day, artificial, natural)
- Camera movement and angle
- Mood and atmosphere
- Technical quality descriptors

Return ONLY the enhanced prompt, no explanations."""

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:14b",
                    "prompt": enhancement_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                enhanced = result.get("response", "").strip()
                
                if enhanced:
                    logger.info(f"Enhanced prompt: {enhanced[:100]}...")
                    return enhanced
                    
        except Exception as e:
            logger.warning(f"Prompt enhancement failed: {e}")
        
        return prompt
    
    def generate_fal(
        self,
        prompt: str,
        duration: int,
        fps: int,
        resolution: str,
        quality: str,
        seed: int
    ) -> Dict:
        """Generate via FAL.ai API"""
        
        width, height = map(int, resolution.split("x"))
        
        payload = {
            "prompt": prompt,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "quality": quality,
            "seed": seed
        }
        
        headers = {
            "Authorization": f"Key {CONFIG['fal_api_key']}",
            "Content-Type": "application/json"
        }
        
        # Submit request
        response = requests.post(
            "https://queue.fal.run/ltx-2-3",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
        
        result = response.json()
        request_id = result.get("request_id")
        
        # Poll for result
        return self.poll_fal_result(request_id, headers)
    
    def poll_fal_result(self, request_id: str, headers: Dict) -> Dict:
        """Poll FAL.ai for result"""
        
        import time
        
        status_url = f"https://queue.fal.run/ltx-2-3/requests/{request_id}/status"
        
        for _ in range(300):  # 5 minutes max
            response = requests.get(status_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                status = response.json()
                
                if status.get("status") == "COMPLETED":
                    return status.get("response")
                elif status.get("status") == "FAILED":
                    raise Exception(f"Generation failed: {status.get('error')}")
            
            time.sleep(2)
        
        raise Exception("Timeout waiting for generation")
    
    def generate_comfyui(
        self,
        prompt: str,
        duration: int,
        fps: int,
        resolution: str,
        seed: int
    ) -> Dict:
        """Generate via ComfyUI"""
        
        width, height = map(int, resolution.split("x"))
        
        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "TextPrompt",
                    "widgets_values": [prompt]
                },
                {
                    "id": 2,
                    "type": "LTXVideoGenerate",
                    "widgets_values": [duration, fps, width, height, 1, seed]
                },
                {
                    "id": 3,
                    "type": "SaveVideo",
                    "widgets_values": [str(self.output_dir / "temp.mp4")]
                }
            ]
        }
        
        response = requests.post(
            "http://localhost:8188/prompt",
            json={"prompt": workflow},
            timeout=60
        )
        
        result = response.json()
        
        return {
            "video_url": str(self.output_dir / "output.mp4")
        }
    
    def save_output(self, result: Dict, output_format: str) -> Path:
        """Save generated video"""
        
        video_url = result.get("video_url", "")
        
        if not video_url:
            return None
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"text2video_{timestamp}.{output_format}"
        output_file = self.output_dir / filename
        
        # Download video
        response = requests.get(video_url, timeout=300)
        
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        logger.info(f"Saved video: {output_file}")
        
        return output_file


# Batch Generation

class BatchGenerator:
    """Generate multiple videos in batch"""
    
    def __init__(self):
        self.generator = TextToVideoGenerator()
    
    def generate_batch(
        self,
        prompts: List[Dict],
        parallel: int = 3
    ) -> List[Dict]:
        """Generate multiple videos"""
        
        results = []
        
        for i, prompt_data in enumerate(prompts):
            logger.info(f"Generating {i+1}/{len(prompts)}: {prompt_data.get('prompt', '')[:30]}...")
            
            try:
                result = self.generator.generate(
                    prompt=prompt_data.get("prompt"),
                    duration=prompt_data.get("duration", 5),
                    fps=prompt_data.get("fps", 24),
                    resolution=prompt_data.get("resolution", "1216x704"),
                    quality=prompt_data.get("quality", "high"),
                    seed=prompt_data.get("seed", -1)
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                results.append({
                    "status": "failed",
                    "error": str(e),
                    "prompt": prompt_data.get("prompt")
                })
        
        return results


# API Integration

def setup_t2v_api(app):
    """Setup Flask API routes"""
    
    generator = TextToVideoGenerator()
    batch = BatchGenerator()
    
    @app.route("/api/generate/text2video", methods=["POST"])
    def text2video():
        """Generate text-to-video"""
        data = request.get_json()
        
        result = generator.generate(
            prompt=data.get("prompt", ""),
            duration=data.get("duration", 5),
            fps=data.get("fps", 24),
            resolution=data.get("resolution", "1216x704"),
            quality=data.get("quality", "high"),
            seed=data.get("seed", -1),
            enhance_prompt=data.get("enhance_prompt", True)
        )
        
        return jsonify(result)
    
    @app.route("/api/generate/text2video/batch", methods=["POST"])
    def text2video_batch():
        """Generate multiple videos"""
        data = request.get_json()
        prompts = data.get("prompts", [])
        
        results = batch.generate_batch(prompts)
        
        return jsonify({
            "count": len(results),
            "results": results
        })
    
    @app.route("/api/generate/presets", methods=["GET"])
    def get_presets():
        """Get generation presets"""
        return jsonify({
            "cinematic": {
                "resolution": "1216x704",
                "fps": 24,
                "duration": 5,
                "quality": "high"
            },
            "fast": {
                "resolution": "704x576",
                "fps": 24,
                "duration": 3,
                "quality": "fast"
            },
            "portrait": {
                "resolution": "1080x1920",
                "fps": 24,
                "duration": 5,
                "quality": "high"
            },
            "slowmo": {
                "resolution": "1216x704",
                "fps": 48,
                "duration": 5,
                "quality": "high"
            }
        })
```

## Prompt Examples

### Cinematic Scenes

```python
PROMPTS = {
    "space": "Cinematic wide shot of a massive spaceship emerging from clouds above an alien planet at sunset, golden hour lighting, volumetric rays, sci-fi atmosphere, 35mm film, detailed textures",
    
    "ocean": "Aerial drone view of turquoise waves crashing against rocky coastline, sunset colors, spray mist, dynamic movement, nature documentary style, 8k resolution",
    
    "city": "Cyberpunk city street at night, neon lights reflecting on wet pavement, rain droplets, people walking with umbrellas, cinematic lighting, Blade Runner atmosphere",
    
    "forest": "Sunbeams filtering through dense forest canopy, morning mist, deer walking through tall grass, magical atmosphere, fantasy movie quality",
    
    "abstract": "Flowing abstract colors morphing and swirling, vibrant gradient background, hypnotic patterns, mesmerizing motion, art installation style"
}
```

## Resolution & Duration Guide

| Use Case | Resolution | FPS | Duration | Best For |
|----------|------------|-----|----------|----------|
| Social Media | 1080x1920 | 24 | 3-5s | Instagram/TikTok |
| YouTube Shorts | 1080x1920 | 30 | 5-10s | Short videos |
| Web Content | 1216x704 | 24 | 5-10s | Website backgrounds |
| Preview/Draft | 704x576 | 24 | 3s | Quick iterations |
| Cinematic | 1216x704 | 48 | 5s | High-quality output |

## Workflow Templates

```yaml
# workflows/text2video_cinematic.yaml
name: Cinematic Text-to-Video
description: Generate high-quality cinematic video

steps:
  - name: enhance_prompt
    type: ollama
    model: qwen2.5-coder:14b
    prompt: "Enhance: {input.prompt}"
    
  - name: generate_video
    type: ltx2video
    provider: fal_ai
    prompt: "{steps.enhance_prompt.output}"
    duration: 5
    fps: 24
    resolution: 1216x704
    quality: high
    
  - name: enhance_audio
    type: audio_generate
    prompt: "{steps.enhance_prompt.output}"
    duration: 5
    
  - name: combine
    type: ffmpeg
    video: "{steps.generate_video.output}"
    audio: "{steps.enhance_audio.output}"
    output: "{config.output_dir}/final.mp4"
```

## Next Steps

- [04-image2video](./04-image2video.md) - Image-to-video workflows
