# Batch Processing on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Batch Processing](#understanding-batch-processing)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Basic Usage](#basic-usage)
7. [Batch Generation Strategies](#batch-generation-strategies)
8. [Advanced Techniques](#advanced-techniques)
9. [Practical Applications](#practical-applications)
10. [Troubleshooting](#troubleshooting)

## Introduction

Batch processing enables efficient generation of multiple images simultaneously. This guide covers deploying batch processing workflows on your Jetson AGX Orin 64GB, enabling:

- Bulk image generation
- Prompt variations
- Parallel processing
- Automated workflows
- Queue management
- Progress tracking

### Why Batch Processing?

- **Efficiency**: Process multiple images in one run
- **Variations**: Generate multiple versions quickly
- **Automation**: Create hands-free workflows
- **Production**: Scale image generation

## Understanding Batch Processing

### Types of Batch Processing

| Method | Description | Use Case |
|--------|-------------|----------|
| Sequential | One after another | Simple workflows |
| Parallel | Multiple at once | Speed |
| Queued | Background processing | Large batches |
| Distributed | Multiple workers | Production |

### Jetson Considerations

- Sequential is most stable on Jetson
- Clear memory between generations
- Use smaller batches to avoid OOM
- Monitor temperature

## Prerequisites

### System Setup

```bash
sudo nvpmodel -m 0
sudo jetson_clocks

# Check available memory
free -h
```

### Python Dependencies

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install diffusers transformers accelerate safetensors
pip install pillow numpy opencv-python tqdm
```

## Installation

### Basic Installation

```bash
# Core dependencies already installed
pip install tqdm  # Progress bars
```

## Configuration

### Batch Processing Config

```python
BATCH_CONFIG = {
    "batch_size": 1,  # Keep at 1 for Jetson
    "max_queue_size": 10,
    "memory_cleanup": True,
    "checkpoint_interval": 5,
    
    "generation": {
        "default_steps": 25,
        "default_guidance": 7.0,
        "default_height": 512,
        "default_width": 512,
    },
    
    "output": {
        "save_directory": "./output",
        "naming_pattern": "{prompt}_{index}",
        "format": "png",
        "quality": 95,
    },
    
    "memory": {
        "clear_cache_interval": 1,
        "enable_cpu_offload": False,
    }
}
```

## Basic Usage

### Batch Image Generation

```python
#!/usr/bin/env python3
"""
Batch Processing on Jetson AGX Orin
"""

import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import os
import time
import glob
from tqdm import tqdm
import json

class BatchGenerator:
    """Batch image generation on Jetson"""
    
    def __init__(self, model_id="stabilityai/stable-diffusion-1-5"):
        self.model_id = model_id
        self.pipeline = None
        
    def load_model(self):
        """Load generation model"""
        
        print(f"Loading model: {self.model_id}")
        
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        
        self.pipeline.enable_attention_slicing()
        self.pipeline.enable_vae_slicing()
        
        if torch.cuda.is_available():
            self.pipeline = self.pipeline.to("cuda")
        
        print("Model loaded!")
        return self.pipeline
    
    def clear_memory(self):
        """Clear GPU memory between generations"""
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    
    def generate_batch(
        self,
        prompts,
        negative_prompt="",
        output_dir="./output/batch",
        num_inference_steps=25,
        guidance_scale=7.0,
        seeds=None,
        save_metadata=True
    ):
        """Generate batch of images"""
        
        if self.pipeline is None:
            raise RuntimeError("Model not loaded")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize seeds if not provided
        if seeds is None:
            seeds = [None] * len(prompts)
        
        # Generate
        results = []
        start_time = time.time()
        
        print(f"Generating {len(prompts)} images...")
        
        for i, (prompt, seed) in enumerate(tqdm(zip(prompts, seeds), total=len(prompts))):
            try:
                # Set seed
                generator = None
                if seed is not None:
                    generator = torch.Generator(device="cuda")
                    generator.manual_seed(seed)
                
                # Generate
                with torch.inference_mode():
                    result = self.pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        height=512,
                        width=512,
                        generator=generator,
                    )
                
                image = result.images[0]
                
                # Save
                output_path = os.path.join(
                    output_dir,
                    f"image_{i:04d}.png"
                )
                image.save(output_path)
                
                results.append({
                    "index": i,
                    "prompt": prompt,
                    "seed": seed,
                    "output_path": output_path,
                    "success": True,
                })
                
                # Clear memory
                if i % 2 == 0:
                    self.clear_memory()
                    
            except Exception as e:
                print(f"Error generating image {i}: {e}")
                results.append({
                    "index": i,
                    "prompt": prompt,
                    "seed": seed,
                    "error": str(e),
                    "success": False,
                })
        
        # Save metadata
        if save_metadata:
            metadata_path = os.path.join(output_dir, "metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump({
                    "prompts": prompts,
                    "negative_prompt": negative_prompt,
                    "results": results,
                    "total_time": time.time() - start_time,
                    "settings": {
                        "num_inference_steps": num_inference_steps,
                        "guidance_scale": guidance_scale,
                    }
                }, f, indent=2)
        
        elapsed = time.time() - start_time
        print(f"Batch complete! Generated {len(results)} images in {elapsed:.2f}s")
        
        return results
    
    def generate_variations(
        self,
        base_prompt,
        num_variations=4,
        **kwargs
    ):
        """Generate variations of the same prompt"""
        
        prompts = [base_prompt] * num_variations
        seeds = list(range(num_variations))
        
        return self.generate_batch(
            prompts,
            seeds=seeds,
            **kwargs
        )


class PromptVariationGenerator:
    """Generate prompt variations automatically"""
    
    @staticmethod
    def vary_adjectives(base_prompt, adjectives):
        """Vary adjectives in prompt"""
        
        prompts = []
        
        for adj in adjectives:
            prompt = base_prompt.replace("{adjective}", adj)
            prompt = prompt.replace("{adj}", adj)
            prompts.append(prompt)
        
        # If no placeholder, append adjectives
        if prompts == []:
            for adj in adjectives:
                prompts.append(f"{base_prompt}, {adj}")
        
        return prompts
    
    @staticmethod
    def vary_subject(base_prompt, subjects):
        """Vary subject in prompt"""
        
        prompts = []
        
        for subject in subjects:
            prompt = base_prompt.replace("{subject}", subject)
            prompt = prompt.replace("{subj}", subject)
            prompts.append(prompt)
        
        if prompts == []:
            for subject in subjects:
                prompts.append(f"{subject}, {base_prompt}")
        
        return prompts
    
    @staticmethod
    def vary_settings(base_prompt, settings):
        """Vary settings in prompt"""
        
        prompts = []
        
        for setting in settings:
            prompts.append(f"{base_prompt}, {setting}")
        
        return prompts
    
    @staticmethod
    def generate_combinations(
        subjects,
        styles,
        environments,
        lighting
    ):
        """Generate all combinations"""
        
        prompts = []
        
        for subject in subjects:
            for style in styles:
                for env in environments:
                    for light in lighting:
                        prompt = f"{subject}, {style}, {env}, {light}"
                        prompts.append(prompt)
        
        return prompts


def main():
    """Demo of batch processing"""
    
    # Initialize
    generator = BatchGenerator()
    generator.load_model()
    
    # Example prompts
    prompts = [
        "a beautiful mountain landscape",
        "a futuristic city at night",
        "a serene beach at sunset",
        "an ancient forest",
        "a modern interior design",
    ]
    
    # Generate batch
    # results = generator.generate_batch(prompts, output_dir="./output/batch")
    
    print("Batch processing demo complete!")


if __name__ == "__main__":
    main()
```

### Quick Batch Generation

```python
from diffusers import StableDiffusionPipeline
import torch

# Load model
pipeline = StableDiffusionPipeline.from_pretrained(
    "stabilityai/stable-diffusion-1-5",
    torch_dtype=torch.float16,
)
pipeline.enable_attention_slicing()
pipeline = pipeline.to("cuda")

# Batch prompts
prompts = [
    "a cat",
    "a dog", 
    "a bird",
    "a fish",
]

# Generate
for i, prompt in enumerate(prompts):
    result = pipeline(prompt, num_inference_steps=20)
    result.images[0].save(f"output_{i}.png")
    
    # Clear memory
    torch.cuda.empty_cache()
```

## Batch Generation Strategies

### 1. Sequential Generation

```python
class SequentialBatch:
    """Sequential batch generation"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate(
        self,
        prompts,
        clear_memory=True,
        **kwargs
    ):
        """Generate images one by one"""
        
        results = []
        
        for i, prompt in enumerate(prompts):
            print(f"Generating {i+1}/{len(prompts)}: {prompt}")
            
            result = self.pipeline(
                prompt=prompt,
                **kwargs
            )
            
            results.append(result.images[0])
            
            # Clear memory
            if clear_memory and torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        return results
```

### 2. Variation Generation

```python
class VariationGenerator:
    """Generate variations of images"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate_with_seeds(
        self,
        prompt,
        num_variations=4,
        seeds=None,
        **kwargs
    ):
        """Generate multiple variations"""
        
        if seeds is None:
            seeds = list(range(num_variations))
        
        results = []
        
        for i, seed in enumerate(seeds):
            generator = torch.Generator(device="cuda")
            generator.manual_seed(seed)
            
            result = self.pipeline(
                prompt=prompt,
                generator=generator,
                **kwargs
            )
            
            results.append(result.images[0])
        
        return results
    
    def generate_with_guidance(
        self,
        prompt,
        guidance_values=[5, 7, 9, 11],
        **kwargs
    ):
        """Generate with different guidance scales"""
        
        results = []
        
        for guidance in guidance_values:
            result = self.pipeline(
                prompt=prompt,
                guidance_scale=guidance,
                **kwargs
            )
            
            results.append(result.images[0])
        
        return results
    
    def generate_with_steps(
        self,
        prompt,
        step_values=[10, 20, 30, 50],
        **kwargs
    ):
        """Generate with different step counts"""
        
        results = []
        
        for steps in step_values:
            result = self.pipeline(
                prompt=prompt,
                num_inference_steps=steps,
                **kwargs
            )
            
            results.append(result.images[0])
        
        return results
```

### 3. Parallel Prompt Generation

```python
class ParallelPromptGenerator:
    """Generate from multiple prompts in parallel"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate_batch(
        self,
        prompts,
        batch_size=1,  # Keep small for Jetson
        **kwargs
    ):
        """Generate batch of prompts"""
        
        # Note: True parallel requires more memory
        # This simulates batch with small chunks
        
        all_results = []
        
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i+batch_size]
            
            # Generate
            results = self.pipeline(
                batch,
                **kwargs
            )
            
            all_results.extend(results.images)
        
        return all_results
```

### 4. Queued Processing

```python
import queue
import threading
import time

class QueuedBatchProcessor:
    """Process prompts from a queue"""
    
    def __init__(self, pipeline, max_queue=100):
        self.pipeline = pipeline
        self.queue = queue.Queue(maxsize=max_queue)
        self.results = []
        self.processing = True
    
    def add_prompt(self, prompt):
        """Add prompt to queue"""
        self.queue.put(prompt)
    
    def process_queue(self):
        """Process prompts from queue"""
        
        while self.processing or not self.queue.empty():
            try:
                prompt = self.queue.get(timeout=1)
                
                result = self.pipeline(prompt, num_inference_steps=20)
                self.results.append(result.images[0])
                
                self.queue.task_done()
                
                # Clear memory
                torch.cuda.empty_cache()
                
            except queue.Empty:
                continue
    
    def start(self, num_workers=1):
        """Start processing"""
        
        self.processing = True
        
        for _ in range(num_workers):
            thread = threading.Thread(target=self.process_queue)
            thread.start()
    
    def stop(self):
        """Stop processing"""
        
        self.processing = False
        self.queue.join()
    
    def get_results(self):
        """Get all results"""
        return self.results
```

## Advanced Techniques

### 1. Smart Memory Management

```python
class SmartBatchGenerator:
    """Batch generation with smart memory management"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate_with_monitoring(
        self,
        prompts,
        memory_threshold=0.9,
        **kwargs
    ):
        """Generate with memory monitoring"""
        
        results = []
        
        for i, prompt in enumerate(prompts):
            # Check memory before generation
            if torch.cuda.is_available():
                memory_used = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()
                
                if memory_used > memory_threshold:
                    print(f"Memory high ({memory_used:.1%}), clearing cache")
                    torch.cuda.empty_cache()
            
            # Generate
            result = self.pipeline(prompt, **kwargs)
            results.append(result.images[0])
            
            # Check after generation
            if torch.cuda.is_available():
                memory_used = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()
                print(f"Memory after generation: {memory_used:.1%}")
        
        return results
```

### 2. Checkpoint System

```python
class CheckpointBatchGenerator:
    """Batch generation with checkpointing"""
    
    def __init__(self, pipeline, checkpoint_file="checkpoint.json"):
        self.pipeline = pipeline
        self.checkpoint_file = checkpoint_file
        self.completed = self.load_checkpoint()
    
    def load_checkpoint(self):
        """Load completed indices"""
        
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
                return set(data.get("completed", []))
        
        return set()
    
    def save_checkpoint(self, index):
        """Save checkpoint"""
        
        self.completed.add(index)
        
        data = {"completed": list(self.completed)}
        
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f)
    
    def generate_with_checkpoint(
        self,
        prompts,
        output_dir,
        **kwargs
    ):
        """Generate with checkpoint support"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        
        for i, prompt in enumerate(prompts):
            # Skip if already completed
            if i in self.completed:
                print(f"Skipping {i+1}/{len(prompts)} (already completed)")
                continue
            
            print(f"Generating {i+1}/{len(prompts)}")
            
            result = self.pipeline(prompt, **kwargs)
            image = result.images[0]
            
            # Save
            output_path = os.path.join(output_dir, f"image_{i:04d}.png")
            image.save(output_path)
            
            # Save checkpoint
            self.save_checkpoint(i)
            
            results.append(image)
        
        return results
```

### 3. Template-Based Generation

```python
class TemplateBatchGenerator:
    """Generate from templates"""
    
    TEMPLATES = {
        "portrait": "{subject}, {lighting}, {background}, professional photography",
        "landscape": "{location}, {time}, {weather}, landscape photography",
        "product": "{product}, {style}, {background}, product photography",
    }
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def generate_from_template(
        self,
        template_name,
        variables,
        **kwargs
    ):
        """Generate from template with variables"""
        
        template = self.TEMPLATES.get(template_name, "{subject}")
        
        # Generate all combinations
        prompts = []
        
        keys = list(variables.keys())
        values = list(variables.values())
        
        # Generate all combinations
        import itertools
        for combination in itertools.product(*values):
            prompt = template
            for key, value in zip(keys, combination):
                prompt = prompt.replace(f"{{{key}}}", value)
            
            prompts.append(prompt)
        
        # Generate
        results = []
        
        for prompt in prompts:
            result = self.pipeline(prompt, **kwargs)
            results.append(result.images[0])
        
        return results
```

### 4. Progress Tracking

```python
class TrackedBatchGenerator:
    """Batch generation with progress tracking"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "total_time": 0,
        }
    
    def generate_with_tracking(
        self,
        prompts,
        **kwargs
    ):
        """Generate with statistics tracking"""
        
        self.stats["total"] = len(prompts)
        results = []
        
        for i, prompt in enumerate(prompts):
            start_time = time.time()
            
            try:
                result = self.pipeline(prompt, **kwargs)
                results.append(result.images[0])
                self.stats["completed"] += 1
                
            except Exception as e:
                print(f"Error: {e}")
                self.stats["failed"] += 1
            
            self.stats["total_time"] += time.time() - start_time
            
            # Print progress
            print(f"Progress: {i+1}/{len(prompts)} "
                  f"({self.stats['completed']} ok, {self.stats['failed']} failed) "
                  f"Avg time: {self.stats['total_time']/(i+1):.2f}s")
        
        return results
    
    def get_stats(self):
        """Get generation statistics"""
        
        return {
            **self.stats,
            "success_rate": self.stats["completed"] / max(1, self.stats["total"]),
            "avg_time": self.stats["total_time"] / max(1, self.stats["completed"]),
        }
```

## Practical Applications

### 1. Product Photography Batch

```python
def generate_product_batch(products, backgrounds, styles):
    """Generate product photos in bulk"""
    
    prompts = []
    
    for product in products:
        for background in backgrounds:
            for style in styles:
                prompt = f"{product} on {background}, {style}, product photography"
                prompts.append(prompt)
    
    # Generate
    generator = BatchGenerator()
    generator.load_model()
    
    return generator.generate_batch(prompts, output_dir="./output/products")
```

### 2. Asset Generation

```python
def generate_game_assets(categories, num_per_category):
    """Generate game assets in bulk"""
    
    prompts = {
        "characters": ["warrior mage rogue", "elf dwarf orc"],
        "items": ["sword shield potion", "armor helmet boots"],
        "environment": ["forest dungeon castle", "cave temple ruins"],
    }
    
    all_prompts = []
    
    for category in categories:
        for prompt in prompts.get(category, []):
            all_prompts.extend([prompt] * num_per_category)
    
    # Generate
    return BatchGenerator().generate_batch(all_prompts)
```

### 3. A/B Testing

```python
def ab_test_prompts(prompt_variants, num_samples=4):
    """Generate A/B test variants"""
    
    prompts = []
    
    for prompt in prompt_variants:
        prompts.extend([prompt] * num_samples)
    
    return BatchGenerator().generate_batch(prompts)
```

### 4. Dataset Generation

```python
def generate_dataset(subjects, attributes, output_dir):
    """Generate training dataset"""
    
    prompts = []
    
    for subject in subjects:
        for attr in attributes:
            prompts.append(f"{subject}, {attr}")
    
    results = BatchGenerator().generate_batch(
        prompts,
        output_dir=output_dir,
        save_metadata=True
    )
    
    return results
```

## Troubleshooting

### Common Issues

#### 1. Out of Memory

```python
# Solution: Reduce batch size
batch_size = 1

# Clear memory more frequently
if i % 1 == 0:
    torch.cuda.empty_cache()

# Use CPU offload
pipeline.enable_sequential_cpu_offload()
```

#### 2. Slow Generation

```bash
# Check performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Monitor
tegrastats
```

#### 3. Inconsistent Results

```python
# Solution: Use fixed seeds
seeds = [42, 43, 44, 45]
results = generate_batch(prompts, seeds=seeds)
```

#### 4. Crashes

```python
# Solution: Add error handling
try:
    result = pipeline(prompt)
except Exception as e:
    print(f"Error: {e}")
    continue
```

### Performance Tips

| Setting | Value | Effect |
|---------|-------|--------|
| Batch size | 1 | Most stable |
| Steps | 20-25 | Good speed |
| Resolution | 512x512 | Fastest |
| Clear interval | 1-2 | Memory stable |

## Next Steps

- All Part 17 tutorials are now complete!
- Explore [Fine-tuning (Part 16)](../part-16-finetuning/README.md) for custom models
- Check [Overview](../part-17-image-processing-generation/01-overview.md) to start fresh

## Additional Resources

- [Diffusers Batching](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/text2img)
- [Performance Optimization](../part-17-image-processing-generation/04-stable-diffusion-xl.md)
