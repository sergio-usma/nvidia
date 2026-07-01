# Creative Studio - Image-to-Video Generation

## Overview

Image-to-video generation animates static images into dynamic videos using LTX-2.3. This is ideal for creating motion from photos, artwork, or AI-generated images.

## Image-to-Video Generator

```python
#!/usr/bin/env python3
"""
Image-to-Video Generation Module
"""

import os
import json
import logging
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import requests
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_dir": "/opt/creative-studio/outputs",
    "input_dir": "/opt/creative-studio/inputs",
    "api_url": "http://localhost:8083",
    "fal_api_key": os.environ.get("FAL_API_KEY", "")
}

for d in [CONFIG["output_dir"], CONFIG["input_dir"]]:
    os.makedirs(d, exist_ok=True)


class ImageToVideoGenerator:
    """Image-to-video generation using LTX-2.3"""
    
    def __init__(self, provider: str = "fal_ai"):
        self.provider = provider
        self.output_dir = Path(CONFIG["output_dir"])
        self.input_dir = Path(CONFIG["input_dir"])
    
    def generate(
        self,
        image: Union[str, Path, Image.Image],
        prompt: str = "",
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704",
        quality: str = "high",
        seed: int = -1,
        motion_strength: float = 0.5,
        output_format: str = "mp4"
    ) -> Dict:
        """Generate video from image"""
        
        # Prepare image
        image_path = self.prepare_image(image)
        
        # Upload to accessible URL
        image_url = self.upload_image(image_path)
        
        logger.info(f"Generating video from image: {image_path.name}")
        
        # Call generation API
        if self.provider == "fal_ai":
            result = self.generate_fal(
                image_url, prompt, duration, fps, resolution, quality, seed
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        # Save output
        output_file = self.save_output(result, output_format)
        
        return {
            "status": "success",
            "source_image": str(image_path),
            "prompt": prompt,
            "video_url": result.get("video_url"),
            "audio_url": result.get("audio_url"),
            "output_file": str(output_file),
            "metadata": {
                "duration": duration,
                "fps": fps,
                "resolution": resolution,
                "motion_strength": motion_strength,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def prepare_image(self, image: Union[str, Path, Image.Image]) -> Path:
        """Prepare and validate image"""
        
        if isinstance(image, Image.Image):
            # Convert PIL Image to file
            image_path = self.input_dir / f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            image.save(image_path)
            return image_path
        elif isinstance(image, (str, Path)):
            image_path = Path(image)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            return image_path
        else:
            raise ValueError("Image must be file path or PIL Image")
    
    def upload_image(self, image_path: Path) -> str:
        """Upload image to accessible URL"""
        
        # Option 1: Upload to FAL.ai
        with open(image_path, "rb") as f:
            response = requests.post(
                "https://queue.fal.run/files/upload",
                files={"file": f},
                headers={"Authorization": f"Key {CONFIG['fal_api_key']}"},
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("url")
        
        # Option 2: Use local server (if accessible)
        return f"file://{image_path}"
    
    def generate_fal(
        self,
        image_url: str,
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
            "image_url": image_url,
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
            "https://queue.fal.run/ltx-2-3/image-to-video",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
        
        result = response.json()
        request_id = result.get("request_id")
        
        # Poll for result
        return self.poll_result(request_id, headers)
    
    def poll_result(self, request_id: str, headers: Dict) -> Dict:
        """Poll for generation result"""
        
        import time
        
        status_url = f"https://queue.fal.run/ltx-2-3/image-to-video/requests/{request_id}/status"
        
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
        filename = f"image2video_{timestamp}.{output_format}"
        output_file = self.output_dir / filename
        
        response = requests.get(video_url, timeout=300)
        
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        logger.info(f"Saved video: {output_file}")
        
        return output_file


# Motion Presets

MOTION_PRESETS = {
    "gentle": {
        "description": "Subtle, natural movement",
        "motion_strength": 0.3
    },
    "moderate": {
        "description": "Balanced movement",
        "motion_strength": 0.5
    },
    "dynamic": {
        "description": "Strong, dramatic movement",
        "motion_strength": 0.7
    },
    "cinematic": {
        "description": "Camera-like motion with cinematic feel",
        "motion_strength": 0.6
    },
    "loop": {
        "description": "Smooth, seamless looping motion",
        "motion_strength": 0.4
    }
}


# Prompt Enhancements for Image-to-Video

I2V_PROMPT_TEMPLATES = {
    "pan_left": "Camera slowly pans to the left, revealing more of the scene",
    "pan_right": "Camera smoothly pans to the right, showing new angles",
    "zoom_in": "Camera gradually zooms in, creating depth",
    "zoom_out": "Camera pulls back, expanding the view",
    "drone": "Aerial drone perspective, sweeping overhead movement",
    "float": "Gentle floating sensation, dreamlike atmosphere",
    "wave": "Wave-like undulating motion flowing through scene",
    "breathing": "Subtle expansion and contraction, living quality"
}


def enhance_motion_prompt(base_prompt: str, motion_type: str = "moderate") -> str:
    """Enhance prompt with motion description"""
    
    template = I2V_PROMPT_TEMPLATES.get(motion_type, I2V_PROMPT_TEMPLATES["moderate"])
    
    if base_prompt:
        return f"{base_prompt}. {template}"
    
    return template


# API Integration

def setup_i2v_api(app):
    """Setup Flask API routes"""
    
    generator = ImageToVideoGenerator()
    
    @app.route("/api/generate/image2video", methods=["POST"])
    def image2video():
        """Generate video from image"""
        data = request.get_json()
        
        # Get image (base64 or URL or path)
        image = data.get("image")
        
        if not image:
            return jsonify({"error": "No image provided"}), 400
        
        # Handle base64
        if isinstance(image, str) and image.startswith("data:image"):
            # Decode base64
            import re
            header, b64data = re.split(r',', image, 1)
            image_data = base64.b64decode(b64data)
            
            image_path = CONFIG["input_dir"] / f"upload_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            with open(image_path, "wb") as f:
                f.write(image_data)
            image = image_path
        
        result = generator.generate(
            image=image,
            prompt=data.get("prompt", ""),
            duration=data.get("duration", 5),
            fps=data.get("fps", 24),
            resolution=data.get("resolution", "1216x704"),
            quality=data.get("quality", "high"),
            seed=data.get("seed", -1)
        )
        
        return jsonify(result)
    
    @app.route("/api/generate/motion-presets", methods=["GET"])
    def get_motion_presets():
        """Get available motion presets"""
        return jsonify(MOTION_PRESETS)
```

## Use Cases

### From ComfyUI Images

```python
# Generate from ComfyUI output
from comfyui import ComfyUIClient

comfy = ComfyUIClient()

# Generate image first
image_path = comfy.generate_image(
    prompt="A serene lake at sunset with mountains in background"
)

# Then animate
i2v = ImageToVideoGenerator()

video = i2v.generate(
    image=image_path,
    prompt="Camera slowly pans across the landscape, revealing reflections on water",
    motion_strength=0.5
)
```

### From Stable Diffusion Images

```python
# Generate from Stable Diffusion
from stable_diffusion import ImageGenerator

sd = ImageGenerator()
image = sd.generate(
    prompt="Portrait of a woman, artistic, dramatic lighting"
)

# Animate
i2v = ImageToVideoGenerator()
video = i2v.generate(
    image=image,
    prompt="Gentle blinking, subtle head movement",
    motion_strength=0.3
)
```

### Batch Image-to-Video

```python
# Process multiple images
from pathlib import Path

image_dir = Path("/opt/creative-studio/inputs/batch")
images = list(image_dir.glob("*.png"))

i2v = ImageToVideoGenerator()

for img in images:
    result = i2v.generate(
        image=img,
        prompt="Subtle natural movement",
        duration=3,
        output_format="mp4"
    )
    
    print(f"Generated: {result['output_file']}")
```

## Image Requirements

| Aspect | Specification |
|--------|---------------|
| Formats | PNG, JPG, WebP |
| Max Size | 10MB |
| Min Resolution | 512×512 |
| Aspect Ratios | 1:1, 16:9, 9:16, 4:3 |

## Tips for Best Results

1. **High Quality Source**: Use clear, detailed images
2. **Consistent Lighting**: Avoid harsh shadows in source
3. **Simple Compositions**: Less busy images animate better
4. **Motion Prompts**: Add camera movement descriptions
5. **Start Frames**: First frame should have clear subject

## Workflow: AI Art to Video

```python
# Complete workflow: Generate image → Animate
from stable_diffusion import ImageGenerator
from ltxx import ImageToVideoGenerator

# Step 1: Generate artistic image
sd = ImageGenerator()
image = sd.generate(
    prompt="Abstract colorful flowing paint, mesmerizing patterns, 4k"
)

# Step 2: Animate with motion
i2v = ImageToVideoGenerator()
video = i2v.generate(
    image=image,
    prompt="Flowing, wave-like motion, colors morphing gently",
    motion_strength=0.6,
    duration=5
)

# Step 3: Add audio
audio = AudioGenerator().generate(
    prompt="Mesmerizing ambient soundscape"
)

# Step 4: Combine
FFmpeg.combine_video_audio(
    video=video["output_file"],
    audio=audio["output_file"],
    output="final_art.mp4"
)
```

## Next Steps

- [05-audio-video](./05-audio-video.md) - Audio-to-video generation
