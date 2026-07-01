# Automated Image Generation

## Batch Generation from Text List

```python
import requests
import time
import os

class BatchImageGenerator:
    def __init__(self):
        self.ollama = "http://localhost:11434"
        self.comfy = "http://localhost:8188"
    
    def generate_batch(self, concepts, output_dir="./output"):
        """Generate images from list of concepts"""
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        
        for i, concept in enumerate(concepts):
            print(f"Generating {i+1}/{len(concepts)}: {concept}")
            
            # Enhance prompt with Ollama
            prompt = self._enhance_prompt(concept)
            
            # Generate image
            job_id = self._generate_image(prompt)
            
            # Wait and save
            self._wait_for_job(job_id)
            self._save_output(job_id, output_dir, f"image_{i}")
            
            results.append({
                "concept": concept,
                "prompt": prompt,
                "job_id": job_id
            })
            
            time.sleep(2)  # Pause between generations
        
        return results
    
    def _enhance_prompt(self, concept):
        """Use Ollama to enhance prompt"""
        resp = requests.post(
            f"{self.ollama}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": f"Enhance this for stable diffusion: {concept}. Add details about style, lighting, mood."
            }
        )
        return resp.json()["response"]
    
    def _generate_image(self, prompt):
        """Send to ComfyUI"""
        # Simplified workflow
        workflow = self._create_workflow(prompt)
        resp = requests.post(f"{self.comfy}/prompt", json={"prompt": workflow})
        return resp.json()["prompt_id"]
    
    def _create_workflow(self, prompt):
        return {
            "1": {"inputs": {"model_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"},
            "2": {"inputs": {"text": prompt, "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
            "3": {"inputs": {"text": "low quality, blurry", "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
            "4": {"inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "seed": 42, "steps": 25, "cfg": 7.0}, "class_type": "KSampler"},
            "5": {"inputs": {"samples": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
            "6": {"inputs": {"images": ["5", 0]}, "class_type": "SaveImage", "widgets_values": ["image"]}
        }
    
    def _wait_for_job(self, job_id):
        while True:
            resp = requests.get(f"{self.comfy}/history/{job_id}")
            data = resp.json()
            if job_id in data and data[job_id].get("status", {}).get("completed"):
                break
            time.sleep(1)
    
    def _save_output(self, job_id, output_dir, prefix):
        resp = requests.get(f"{self.comfy}/history/{job_id}")
        data = resp.json()
        # Save images locally
        print(f"Saved to {output_dir}/{prefix}")

# Usage
generator = BatchImageGenerator()
results = generator.generate_batch([
    "a cat sitting on a windowsill",
    "a futuristic motorcycle",
    "ancient temple in jungle"
])
```

## Style Transfer

```python
def style_transfer(self, content_image, style_prompt):
    """Use Ollama to create style description"""
    
    # Generate style description
    style_desc = requests.post(
        f"{self.ollama}/api/generate",
        json={
            "model": "llama3.2:3b",
            "prompt": f"Describe {style_prompt} style in detail for AI art generation"
        }
    ).json()["response"]
    
    # Combine with content
    combined_prompt = f"{content_image}, {style_desc}"
    
    # Generate
    return self._generate_image(combined_prompt)
```

## Next Steps

- [Video Generation](./06-video-generation.md) - Generate videos
- [API Automation](./07-api-automation.md) - API workflows
