# Workflow Basics

## Basic Text-to-Image Workflow

```python
import requests
import json
import time

class ComfyWorkflow:
    def __init__(self):
        self.url = "http://localhost:8188"
    
    def get_models(self):
        """Get available models"""
        resp = requests.get(f"{self.url}/object_info/CheckpointLoaderSimple")
        return resp.json()
    
    def simple_txt2img(self, prompt, model="sd_xl_base_1.0.safetensors"):
        """Simple text to image workflow"""
        
        workflow = {
            "1": {
                "inputs": {"model_name": model},
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {"text": prompt, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {"text": "low quality, worst quality", "clip": ["1", 1]},
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "seed": 42,
                    "steps": 20,
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
                "inputs": {"images": ["5", 0]},
                "class_type": "SaveImage"
            }
        }
        
        resp = requests.post(f"{self.url}/prompt", json={"prompt": workflow})
        return resp.json()
    
    def wait_for_completion(self, prompt_id):
        """Wait for workflow to complete"""
        while True:
            resp = requests.get(f"{self.url}/history/{prompt_id}")
            data = resp.json()
            
            if prompt_id in data:
                status = data[prompt_id].get("status", {})
                if status.get("completed"):
                    return True
                if status.get("err_message"):
                    return False
            
            time.sleep(1)
    
    def get_output(self, prompt_id):
        """Get generated images"""
        resp = requests.get(f"{self.url}/history/{prompt_id}")
        data = resp.json()
        
        images = []
        for node_id, node_data in data[prompt_id]["outputs"].items():
            if "images" in node_data:
                for img in node_data["images"]:
                    images.append({
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", "")
                    })
        
        return images

# Usage
wf = ComfyWorkflow()
result = wf.simple_txt2img("a beautiful sunset over mountains")
prompt_id = result["prompt_id"]

wf.wait_for_completion(prompt_id)
images = wf.get_output(prompt_id)
print(f"Generated {len(images)} images")
```

## Workflow with Ollama Prompt

```python
def generate_with_ollama_prompt(concept):
    # 1. Generate prompt with Ollama
    ollama = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2:3b",
            "prompt": f"Create a stable diffusion prompt: {concept}"
        }
    )
    
    prompt = ollama.json()["response"]
    
    # 2. Generate image
    wf = ComfyWorkflow()
    result = wf.simple_txt2img(prompt)
    
    return result["prompt_id"]

# Run
prompt_id = generate_with_ollama_prompt("cyberpunk city")
```

## Image-to-Image Workflow

```python
def img2img(self, prompt, input_image, strength=0.7):
    """Image to image workflow"""
    
    workflow = {
        "1": {"inputs": {"image": input_image}, "class_type": "LoadImage"},
        "2": {"inputs": {"model_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"},
        "3": {"inputs": {"text": prompt, "clip": ["2", 1]}, "class_type": "CLIPTextEncode"},
        "4": {"inputs": {"text": "low quality", "clip": ["2", 1]}, "class_type": "CLIPTextEncode"},
        "5": {"inputs": {"image": ["1", 0]}, "class_type": "VAEEncodeForInpaint"},
        "6": {
            "inputs": {
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent": ["5", 0],
                "seed": 42,
                "steps": 20,
                "cfg": 7.0,
                "denoise": strength
            },
            "class_type": "KSampler"
        },
        "7": {"inputs": {"samples": ["6", 0], "vae": ["2", 2]}, "class_type": "VAEDecode"},
        "8": {"inputs": {"images": ["7", 0]}, "class_type": "SaveImage"}
    }
    
    return requests.post(f"{self.url}/prompt", json={"prompt": workflow})
```

## Next Steps

- [Image Generation](./05-image-generation.md) - Automated image workflows
- [Video Generation](./06-video-generation.md) - Video workflows
