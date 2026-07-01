# Video Generation Workflows

## Frame-by-Frame Generation

```python
import requests
import time
import os
import subprocess

class VideoGenerator:
    def __init__(self):
        self.ollama = "http://localhost:11434"
        self.comfy = "http://localhost:8188"
        self.frames_dir = "./frames"
    
    def generate_video(self, story, num_frames=10):
        """Generate video from story"""
        os.makedirs(self.frames_dir, exist_ok=True)
        
        # Break story into scenes
        scenes = self._split_into_scenes(story, num_frames)
        
        frames = []
        
        for i, scene in enumerate(scenes):
            print(f"Generating frame {i+1}/{len(scenes)}")
            
            # Generate prompt
            prompt = self._scene_to_prompt(scene)
            
            # Generate frame
            frame_path = self._generate_frame(prompt, i)
            frames.append(frame_path)
        
        # Combine into video
        video_path = self._create_video(frames)
        
        return video_path
    
    def _split_into_scenes(self, story, num_scenes):
        """Use Ollama to split story into scenes"""
        resp = requests.post(
            f"{self.ollama}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": f"Split this story into {num_scenes} distinct scenes: {story}. Return only the scenes, one per line."
            }
        )
        
        scenes = resp.json()["response"].strip().split("\n")
        return scenes[:num_scenes]
    
    def _scene_to_prompt(self, scene):
        """Enhance scene into image prompt"""
        resp = requests.post(
            f"{self.ollama}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": f"Create a detailed stable diffusion prompt for: {scene}"
            }
        )
        return resp.json()["response"]
    
    def _generate_frame(self, prompt, index):
        """Generate single frame"""
        # Simplified workflow
        workflow = {
            "1": {"inputs": {"model_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"},
            "2": {"inputs": {"text": prompt, "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
            "3": {"inputs": {"text": "blurry, low quality", "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
            "4": {"inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "seed": index * 100, "steps": 20, "cfg": 7.0}, "class_type": "KSampler"},
            "5": {"inputs": {"samples": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
            "6": {"inputs": {"images": ["5", 0], "filename_prefix": f"frame_{index}"}, "class_type": "SaveImage"}
        }
        
        resp = requests.post(f"{self.comfy}/prompt", json={"prompt": workflow})
        job_id = resp.json()["prompt_id"]
        
        # Wait for completion
        while True:
            time.sleep(1)
            hist = requests.get(f"{self.comfy}/history/{job_id}").json()
            if job_id in hist and hist[job_id].get("status", {}).get("completed"):
                break
        
        return f"{self.frames_dir}/frame_{index}_0001_.png"
    
    def _create_video(self, frames):
        """Combine frames to video using ffmpeg"""
        output = "./output_video.mp4"
        
        subprocess.run([
            "ffmpeg", "-framerate", "1", "-i",
            f"{self.frames_dir}/frame_%d_0001_.png",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", output
        ])
        
        return output

# Usage
generator = VideoGenerator()
story = """
A dragon flying over mountains at sunset
The dragon lands in a mystical forest
The dragon meets another dragon
They fly together into the clouds
"""

video = generator.generate_video(story, num_frames=5)
print(f"Video saved to: {video}")
```

## Animated Sequence

```python
def generate_animated_sequence(self, prompt, frames=30, start_seed=42):
    """Generate animation sequence with slight variations"""
    
    for i in range(frames):
        # Slight seed variation for smooth animation
        seed = start_seed + i
        
        # Generate frame
        self._generate_frame(prompt, i, seed)
    
    # Create video
    return self._create_video(frames)
```

## Next Steps

- [API Automation](./07-api-automation.md) - Automate workflows
- [Custom Nodes](./08-custom-nodes.md) - Create custom nodes
