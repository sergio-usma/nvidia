# Frame-by-Frame Generation on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Frame Generation](#understanding-frame-generation)
3. [Prerequisites](#prerequisites)
4. [Basic Implementation](#basic-implementation)
5. [Advanced Techniques](#advanced-techniques)
6. [Video Assembly](#video-assembly)
7. [Optimization](#optimization)
8. [Practical Examples](#practical-examples)

## Introduction

Frame-by-frame generation is the most practical approach for AI video generation on Jetson AGX Orin. Instead of full video models (which require too much VRAM), we generate individual frames using text-to-image models and assemble them into videos.

### Why Frame Generation?

- **Memory efficient**: Process one frame at a time
- **Flexible**: Each frame can have different seeds
- **Control**: Fine-grained control over each frame
- **Jetson-friendly**: Works within 64GB constraints

## Understanding Frame Generation

### Basic Concept

```
Prompt: "mountain landscape" 
├── Frame 1 (seed=1) ──┐
├── Frame 2 (seed=2) ──┼──→ Video
├── Frame 3 (seed=3) ──┤
└── ...              ──┘
```

### Motion Strategies

| Strategy | Description | Pros | Cons |
|----------|-------------|------|------|
| Seed Increment | Increment seed each frame | Simple | Can be jittery |
| Interpolation | Smooth seed transition | Smooth | More complex |
| Prompt Evolution | Gradually change prompt | Dynamic | Planning needed |
| Style Keyframes | Keyframes + interpolation | Creative | Manual work |

## Prerequisites

```python
# Import required libraries
import torch
from diffusers import StableDiffusionPipeline
import cv2
import numpy as np
from PIL import Image
import os
```

## Basic Implementation

### Frame Generator Class

```python
#!/usr/bin/env python3
"""
Frame-by-Frame Video Generation
Optimized for Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import cv2
import numpy as np
import os
import time
from tqdm import tqdm

class FrameGenerator:
    """Generate video frames using AI"""
    
    def __init__(self, model_id="stabilityai/stable-diffusion-1-5"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self):
        """Load Stable Diffusion model"""
        
        print(f"Loading model: {self.model_id}")
        
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        # Enable optimizations for Jetson
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        # Use fast scheduler
        self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipeline.scheduler.config,
            algorithm_type="dpmsolver++",
        )
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
        
        print("Model loaded!")
        return self.pipeline
    
    def generate_frame(
        self,
        prompt,
        negative_prompt="",
        height=512,
        width=512,
        num_inference_steps=25,
        guidance_scale=7.5,
        seed=None
    ):
        """Generate single frame"""
        
        # Set seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator.manual_seed(seed)
        
        # Generate
        with torch.inference_mode():
            result = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                height=height,
                width=width,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
        
        return result.images[0]
    
    def generate_sequence(
        self,
        prompts,
        output_dir,
        height=512,
        width=512,
        num_inference_steps=25,
        guidance_scale=7.5,
        start_seed=42,
        clear_memory_interval=5
    ):
        """Generate sequence of frames"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        frames = []
        start_time = time.time()
        
        print(f"Generating {len(prompts)} frames...")
        
        for i, prompt in enumerate(tqdm(prompts)):
            try:
                # Generate frame with incrementing seed
                seed = start_seed + i
                
                frame = self.generate_frame(
                    prompt=prompt,
                    height=height,
                    width=width,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    seed=seed
                )
                
                # Save frame
                frame_path = os.path.join(output_dir, f"frame_{i:04d}.png")
                frame.save(frame_path)
                
                frames.append(frame_path)
                
                # Clear memory periodically
                if i > 0 and i % clear_memory_interval == 0:
                    torch.cuda.empty_cache()
                    
            except Exception as e:
                print(f"Error generating frame {i}: {e}")
                continue
        
        elapsed = time.time() - start_time
        
        print(f"Generated {len(frames)} frames in {elapsed:.2f}s")
        print(f"Average: {elapsed/len(frames):.2f}s per frame")
        
        return frames


class VideoAssembler:
    """Assemble frames into video"""
    
    def __init__(self):
        pass
    
    def frames_to_video(
        self,
        frame_paths,
        output_path,
        fps=24,
        codec='mp4v'
    ):
        """Convert frame images to video"""
        
        if not frame_paths:
            raise ValueError("No frames provided")
        
        # Load first frame to get dimensions
        first_frame = Image.open(frame_paths[0])
        width, height = first_frame.size
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Write frames
        for frame_path in tqdm(frame_paths, desc="Creating video"):
            frame = cv2.imread(frame_path)
            writer.write(frame)
        
        writer.release()
        
        print(f"Video saved to: {output_path}")
        
        return output_path
    
    def create_video_from_generator(
        self,
        generator,
        prompt,
        num_frames,
        output_path,
        fps=24,
        **generation_kwargs
    ):
        """Generate frames and create video directly"""
        
        # Create temp directory
        temp_dir = "/tmp/video_frames"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate frames
        frame_paths = []
        
        for i in tqdm(range(num_frames), desc="Generating frames"):
            # Generate frame
            frame = generator.generate_frame(
                prompt=prompt,
                seed=generation_kwargs.get('start_seed', 42) + i,
                height=generation_kwargs.get('height', 512),
                width=generation_kwargs.get('width', 512),
                num_inference_steps=generation_kwargs.get('num_inference_steps', 20),
                guidance_scale=generation_kwargs.get('guidance_scale', 7.5),
            )
            
            # Save frame
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            frame.save(frame_path)
            frame_paths.append(frame_path)
            
            # Clear memory
            if i % 3 == 0:
                torch.cuda.empty_cache()
        
        # Create video
        self.frames_to_video(frame_paths, output_path, fps)
        
        # Cleanup
        for f in frame_paths:
            os.remove(f)
        
        print(f"Video complete: {output_path}")
        
        return output_path
```

### Basic Usage

```python
# Initialize
generator = FrameGenerator()
generator.load_model()

# Simple video: same prompt, different seeds
prompts = ["mountain landscape at sunset"] * 30

# Generate frames
frames = generator.generate_sequence(
    prompts=prompts,
    output_dir="./output/frames",
    num_inference_steps=20,
    start_seed=42
)

# Assemble video
assembler = VideoAssembler()
assembler.frames_to_video(frames, "./output/video.mp4", fps=24)
```

## Advanced Techniques

### 1. Prompt Evolution

```python
class EvolvingPromptGenerator:
    """Generate video with evolving prompts"""
    
    def __init__(self, frame_generator):
        self.generator = frame_generator
    
    def generate_evolution(
        self,
        start_prompt,
        end_prompt,
        num_frames,
        output_path,
        fps=24
    ):
        """Gradually evolve prompt from start to end"""
        
        # Create interpolated prompts
        prompts = self._interpolate_prompts(
            start_prompt, end_prompt, num_frames
        )
        
        # Generate frames
        frame_paths = []
        temp_dir = "/tmp/evolution_frames"
        os.makedirs(temp_dir, exist_ok=True)
        
        for i, prompt in enumerate(tqdm(prompts, desc="Generating")):
            frame = self.generator.generate_frame(
                prompt=prompt,
                seed=42 + i,
                num_inference_steps=20
            )
            
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            frame.save(frame_path)
            frame_paths.append(frame_path)
            
            if i % 5 == 0:
                torch.cuda.empty_cache()
        
        # Create video
        assembler = VideoAssembler()
        assembler.frames_to_video(frame_paths, output_path, fps)
        
        # Cleanup
        for f in frame_paths:
            os.remove(f)
        
        return output_path
    
    def _interpolate_prompts(self, start, end, num_steps):
        """Interpolate between prompts"""
        
        prompts = []
        
        for i in range(num_steps):
            ratio = i / (num_steps - 1) if num_steps > 1 else 0
            
            # Simple approach: blend prompts
            # For more complex cases, use prompt weighting
            prompt = f"{start}, frame {i+1}/{num_steps}"
            
            prompts.append(prompt)
        
        return prompts
```

### 2. Keyframe-Based Generation

```python
class KeyframeGenerator:
    """Generate video from keyframes"""
    
    def __init__(self, frame_generator):
        self.generator = frame_generator
    
    def generate_from_keyframes(
        self,
        keyframes,  # List of (prompt, seed) tuples
        frames_per_keyframe,
        output_path,
        fps=24
    ):
        """Generate video with keyframe transitions"""
        
        prompts = []
        
        for i in range(len(keyframes) - 1):
            start_prompt, start_seed = keyframes[i]
            end_prompt, end_seed = keyframes[i + 1]
            
            # Interpolate between keyframes
            for j in range(frames_per_keyframe):
                ratio = j / frames_per_keyframe
                
                # Use same prompt with evolved seed
                prompt = start_prompt
                seed = int(start_seed + (end_seed - start_seed) * ratio)
                
                prompts.append((prompt, seed))
        
        # Generate all frames
        temp_dir = "/tmp/keyframe_frames"
        os.makedirs(temp_dir, exist_ok=True)
        
        frame_paths = []
        
        for i, (prompt, seed) in enumerate(tqdm(prompts, desc="Generating")):
            frame = self.generator.generate_frame(
                prompt=prompt,
                seed=seed,
                num_inference_steps=20
            )
            
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            frame.save(frame_path)
            frame_paths.append(frame_path)
            
            if i % 5 == 0:
                torch.cuda.empty_cache()
        
        # Create video
        assembler = VideoAssembler()
        assembler.frames_to_video(frame_paths, output_path, fps)
        
        return output_path
```

### 3. Scene-Based Generation

```python
class SceneVideoGenerator:
    """Generate video with multiple scenes"""
    
    def __init__(self, frame_generator):
        self.generator = frame_generator
    
    def generate_scene_video(
        self,
        scenes,  # List of {"prompt": str, "duration": int, "seed": int}
        output_path,
        fps=24,
        transition_frames=5
    ):
        """Generate video with multiple scenes"""
        
        all_frames = []
        temp_dir = "/tmp/scene_frames"
        os.makedirs(temp_dir, exist_ok=True)
        
        for scene_idx, scene in enumerate(scenes):
            prompt = scene["prompt"]
            duration_frames = scene["duration"] * fps
            seed = scene.get("seed", 42 + scene_idx * 100)
            
            print(f"Generating scene {scene_idx + 1}/{len(scenes)}: {prompt}")
            
            # Generate frames for this scene
            for i in range(duration_frames):
                frame = self.generator.generate_frame(
                    prompt=prompt,
                    seed=seed + i,
                    num_inference_steps=20
                )
                
                frame_path = os.path.join(temp_dir, f"frame_{len(all_frames):04d}.png")
                frame.save(frame_path)
                all_frames.append(frame_path)
                
                if i % 10 == 0:
                    torch.cuda.empty_cache()
        
        # Create video
        assembler = VideoAssembler()
        assembler.frames_to_video(all_frames, output_path, fps)
        
        return output_path
```

## Video Assembly

### Assembly Options

```python
# Using MoviePy (alternative to OpenCV)
from moviepy.editor import ImageSequenceClip

# Create clip from image sequence
clip = ImageSequenceClip(frame_paths, fps=24)
clip.write_videofile("output.mp4", codec='libx264')

# Add audio
# clip = clip.set_audio(audio_clip)

# Add effects
# clip = clip.fadein(1).fadeout(1)
```

### Video Properties

```python
def create_video_with_metadata(
    frame_paths,
    output_path,
    fps=24,
    title="AI Generated Video",
    artist="Jetson AGX Orin"
):
    """Create video with metadata"""
    
    from moviepy.editor import ImageSequenceClip
    
    # Create clip
    clip = ImageSequenceClip(frame_paths, fps=fps)
    
    # Set metadata
    clip = clip.set_duration(clip.duration)
    
    # Write with metadata
    clip.write_videofile(
        output_path,
        codec='libx264',
        audio=False,
        verbose=False,
        logger=None
    )
    
    return output_path
```

## Optimization

### Jetson-Specific Optimizations

```python
# Optimize for Jetson
class OptimizedFrameGenerator:
    """Frame generator with Jetson optimizations"""
    
    def __init__(self):
        self.pipeline = None
        
    def load_optimized(self):
        """Load with maximum optimizations"""
        
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-1-5",
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        # Memory optimizations
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        # Use SD Turbo for speed
        # (Trade-off: lower quality but faster)
        
        self.pipeline = self.pipeline.to("cuda")
        
        return self.pipeline
    
    def generate_optimized(
        self,
        prompt,
        height=384,  # Smaller for speed
        width=384,
        num_inference_steps=15,  # Fewer steps
        guidance_scale=1.0,  # Lower guidance
    ):
        """Generate with optimized settings"""
        
        result = self.pipeline(
            prompt=prompt,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        
        torch.cuda.empty_cache()
        
        return result.images[0]
```

### Performance Tips

| Setting | Default | Optimized | Speed Gain |
|---------|---------|-----------|------------|
| Resolution | 512x512 | 384x384 | 2x |
| Steps | 30 | 15 | 2x |
| Guidance | 7.5 | 1.0 | 1.3x |
| Model | SD 1.5 | SD Turbo | 3x |

## Practical Examples

### Example 1: Landscape Animation

```python
# Generate landscape changing time of day
generator = FrameGenerator()
generator.load_model()

scenes = [
    {"prompt": "mountain landscape at sunrise", "duration": 3, "seed": 100},
    {"prompt": "mountain landscape at noon", "duration": 3, "seed": 200},
    {"prompt": "mountain landscape at sunset", "duration": 3, "seed": 300},
    {"prompt": "mountain landscape at night", "duration": 3, "seed": 400},
]

scene_gen = SceneVideoGenerator(generator)
scene_gen.generate_scene_video(scenes, "landscape.mp4", fps=24)
```

### Example 2: Character Animation

```python
# Animate a character with different expressions
generator = FrameGenerator()
generator.load_model()

expressions = [
    "portrait of a woman, happy smile",
    "portrait of a woman, laughing",
    "portrait of a woman, surprised",
    "portrait of a woman, thoughtful",
]

# Generate frames
frames = generator.generate_sequence(
    prompts=expressions * 8,
    output_dir="./character_frames",
    num_inference_steps=25,
    start_seed=42
)

# Create video
assembler = VideoAssembler()
assembler.frames_to_video(frames, "character.mp4", fps=12)
```

## Next Steps

- [Image-to-Video](./05-image-to-video.md) - Animate static images
- [Video Interpolation](./06-video-interpolation.md) - Smooth video
- [Video Upscaling](./07-video-upscaling.md) - Enhance resolution
