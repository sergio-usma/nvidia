# Creative Studio - Complex Workflows

## Overview

This guide covers complex video generation workflows combining multiple LTX-2.3 capabilities: video extension, retake, multi-scene narratives, and integration with other AI tools.

## Video Extension

```python
#!/usr/bin/env python3
"""
Video Extension Module
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_dir": "/opt/creative-studio/outputs",
    "fal_api_key": os.environ.get("FAL_API_KEY", "")
}


class VideoExtender:
    """Extend existing videos using LTX-2.3"""
    
    def __init__(self):
        self.output_dir = Path(CONFIG["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extend_forward(
        self,
        video_path: str,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        resolution: str = "1216x704"
    ) -> Dict:
        """Extend video forward in time"""
        
        video_url = self.upload_video(video_path)
        
        payload = {
            "video_url": video_url,
            "prompt": prompt,
            "duration": duration,
            "fps": fps,
            "width": int(resolution.split("x")[0]),
            "height": int(resolution.split("x")[1]),
            "direction": "forward"
        }
        
        headers = {
            "Authorization": f"Key {CONFIG['fal_api_key']}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://queue.fal.run/ltx-2-3/extend",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        result = response.json()
        request_id = result.get("request_id")
        
        # Poll and return
        return self.poll_result(request_id, headers)
    
    def extend_backward(
        self,
        video_path: str,
        prompt: str,
        duration: int = 5
    ) -> Dict:
        """Extend video backward (prequel)"""
        
        video_url = self.upload_video(video_path)
        
        payload = {
            "video_url": video_url,
            "prompt": prompt,
            "duration": duration,
            "direction": "backward"
        }
        
        # Similar to forward...
        return self.extend_forward(video_path, prompt, duration)
    
    def upload_video(self, video_path: str) -> str:
        """Upload video for processing"""
        
        with open(video_path, "rb") as f:
            response = requests.post(
                "https://queue.fal.run/files/upload",
                files={"file": f},
                headers={"Authorization": f"Key {CONFIG['fal_api_key']}"},
                timeout=300
            )
        
        return response.json().get("url")
    
    def poll_result(self, request_id: str, headers: Dict) -> Dict:
        """Poll for result"""
        import time
        
        for _ in range(300):
            response = requests.get(
                f"https://queue.fal.run/ltx-2-3/extend/requests/{request_id}/status",
                headers=headers
            )
            
            if response.status_code == 200:
                status = response.json()
                if status.get("status") == "COMPLETED":
                    return status.get("response")
            
            time.sleep(2)
        
        raise Exception("Timeout")


# Video Retake

class VideoRetaker:
    """Regenerate specific portions of video"""
    
    def retake(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        prompt: str
    ) -> Dict:
        """Retake specific segment of video"""
        
        video_url = self.upload_video(video_path)
        
        payload = {
            "video_url": video_url,
            "start_time": start_time,
            "end_time": end_time,
            "prompt": prompt
        }
        
        # Submit and poll...
        return {"status": "processing"}
```

## Multi-Scene Workflow

```python
#!/usr/env python3
"""
Multi-Scene Video Workflow
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime


class Scene:
    """Video scene definition"""
    
    def __init__(
        self,
        prompt: str,
        duration: int = 5,
        transition: str = "fade"  # fade, dissolve, cut
    ):
        self.prompt = prompt
        self.duration = duration
        self.transition = transition
        self.video_path = None


class MultiSceneWorkflow:
    """Create multi-scene video narratives"""
    
    def __init__(self, generator):
        self.generator = generator
        self.scenes: List[Scene] = []
        self.output_dir = Path("/opt/creative-studio/outputs/multi_scene")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def add_scene(self, prompt: str, duration: int = 5, transition: str = "fade"):
        """Add scene to workflow"""
        
        scene = Scene(prompt, duration, transition)
        self.scenes.append(scene)
        
        return scene
    
    def generate(self) -> Dict:
        """Generate all scenes and combine"""
        
        scene_files = []
        
        # Generate each scene
        for i, scene in enumerate(self.scenes):
            logger.info(f"Generating scene {i+1}/{len(self.scenes)}")
            
            result = self.generator.generate(
                prompt=scene.prompt,
                duration=scene.duration
            )
            
            scene.video_path = Path(result["output_file"])
            scene_files.append(scene.video_path)
        
        # Combine scenes with transitions
        final_video = self.combine_scenes(scene_files)
        
        return {
            "status": "success",
            "scenes": len(self.scenes),
            "output": str(final_video)
        }
    
    def combine_scenes(self, scene_files: List[Path]) -> Path:
        """Combine scenes with FFmpeg"""
        
        import subprocess
        
        output = self.output_dir / f"multiscene_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
        
        # Create concat file
        concat_file = self.output_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for sf in scene_files:
                f.write(f"file '{sf}'\n")
        
        # Combine
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            "-y", str(output)
        ], capture_output=True)
        
        return output


# Example: Story-to-Video

class StoryToVideo:
    """Convert story/script to video"""
    
    def __init__(self):
        self.t2v_generator = None  # TextToVideoGenerator
        self.multi_scene = None
    
    def generate_from_script(
        self,
        script: str,
        scenes_count: int = 5
    ) -> Dict:
        """Generate video from script"""
        
        # Use Ollama to split into scenes
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5-coder:14b",
                "prompt": f"""Split this script into {scenes_count} distinct visual scenes.
For each scene, provide a brief visual description suitable for AI video generation.

Script:
{script}

Return as JSON array of scene descriptions.""",
                "stream": False
            }
        )
        
        # Parse scene descriptions (simplified)
        # In production, parse actual JSON
        
        # Generate scenes
        from text2video import TextToVideoGenerator
        
        t2v = TextToVideoGenerator()
        multi = MultiSceneWorkflow(t2v)
        
        # Add scenes from script (example)
        multi.add_scene("Opening shot: A vast landscape at dawn, misty mountains", duration=5)
        multi.add_scene("Camera moves to reveal an ancient castle", duration=5)
        multi.add_scene("Inside the castle, torchlight flickers on stone walls", duration=5)
        multi.add_scene("A hero emerges, walking through corridors", duration=5)
        multi.add_scene("Final shot: Hero exits into sunlight", duration=5)
        
        return multi.generate()
```

## Storyboard Generation

```python
#!/usr/bin/env python3
"""
Storyboard Generator
"""

import requests
from typing import List, Dict


class StoryboardGenerator:
    """Generate storyboards from scripts"""
    
    def generate(
        self,
        script: str,
        panels: int = 8
    ) -> List[Dict]:
        """Generate storyboard panels"""
        
        # Use Ollama to generate panel descriptions
        prompt = f"""Create a {panels}-panel storyboard for this script.

For each panel provide:
1. Panel number
2. Visual description (for image generation)
3. Camera angle
4. Action/dialogue

Script:
{script}

Return as JSON array."""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5-coder:14b",
                "prompt": prompt,
                "stream": False
            }
        )
        
        # Parse response
        storyboard = self.parse_storyboard(response.json().get("response", ""))
        
        return storyboard
    
    def generate_images(self, storyboard: List[Dict]) -> List[Path]:
        """Generate images for each panel"""
        
        from stable_diffusion import ImageGenerator
        
        sd = ImageGenerator()
        images = []
        
        for panel in storyboard:
            img = sd.generate(
                prompt=panel["description"],
                size="1024x1024"
            )
            images.append(img)
        
        return images
    
    def create_video(
        self,
        images: List[Path],
        duration_per_panel: int = 3
    ) -> Path:
        """Create video from storyboard images"""
        
        from image2video import ImageToVideoGenerator
        
        i2v = ImageToVideoGenerator()
        
        video_clips = []
        
        for img in images:
            clip = i2v.generate(
                image=img,
                duration=duration_per_panel
            )
            video_clips.append(Path(clip["output_file"]))
        
        # Combine into final video
        from ffmmpeg import FFmpeg
        return FFmpeg.concatenate(video_clips)
```

## Complete Workflow Examples

### Example 1: Product Commercial

```python
# Generate product commercial

# 1. Generate audio narration
pipeline = AudioVideoPipeline()
audio = pipeline.generate_audio(
    prompt="Introducing our revolutionary new product..."
)

# 2. Generate visuals
t2v = TextToVideoGenerator()

scenes = [
    ("Product on clean white background, studio lighting", 3),
    ("Close-up product rotating, 360 view", 3),
    ("Product in use, lifestyle setting", 4),
    ("Happy users interacting with product", 3),
    ("Logo animation, final shot", 2)
]

multi = MultiSceneWorkflow(t2v)
for prompt, duration in scenes:
    multi.add_scene(prompt, duration)

result = multi.generate()

# 3. Combine audio + video
from ffmpeg import FFmpeg
FFmpeg.combine_video_audio(
    video=result["output"],
    audio=audio,
    output="commercial.mp4"
)
```

### Example 2: Music Video

```python
# Generate music video from audio track

audio_file = Path("/music/song.mp3")

# Generate abstract visuals
a2v = AudioToVideoGenerator()
video = a2v.generate(
    audio=audio_file,
    duration=180,  # Full song
    visual_style="abstract",
    resolution="1920x1080"
)

# Enhance with effects
from ffmpeg import FFmpeg

FFmpeg(video["output_file"]) \
    .filter("eq", saturation=1.2) \
    .output("music_video_enhanced.mp4", crf=18) \
    .run()
```

### Example 3: Educational Content

```python
# Generate educational video from topic

topic = "How Photosynthesis Works"

# Generate script
script_response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5-coder:14b",
        "prompt": f"""Create an educational video script about {topic}.
Include 5 scenes with visual descriptions.""",
        "stream": False
    }
)

# Generate storyboard
storyboard = StoryboardGenerator()
panels = storyboard.generate(script_response.text, panels=5)

# Generate images
images = storyboard.generate_images(panels)

# Create video
video = storyboard.create_video(images, duration_per_panel=5)

# Add narration
narration = pipeline.generate_audio(topic)

# Combine
FFmpeg.combine_video_audio(video, narration, "educational.mp4")
```

## Workflow YAML Templates

```yaml
# workflows/story_video.yaml
name: Story to Video
description: Convert narrative to video

config:
  output_dir: /opt/creative-studio/outputs
  resolution: 1216x704
  fps: 24

steps:
  - name: parse_script
    type: llm
    model: qwen2.5-coder:14b
    prompt: "Extract 5 key scenes from: {input.script}"
    output: scenes

  - name: generate_scenes
    type: batch_t2v
    prompts: "{steps.parse_script.scenes}"
    parallel: 3

  - name: combine
    type: ffmpeg_concat
    inputs: "{steps.generate_scenes.outputs}"

  - name: add_audio
    type: piper_tts
    script: "{input.script}"
    
  - name: merge
    type: ffmpeg_merge
    video: "{steps.combine.output}"
    audio: "{steps.add_audio.output}"
    output: "{config.output_dir}/final.mp4"
```

## Next Steps

- [07-api](./07-api.md) - REST API reference
