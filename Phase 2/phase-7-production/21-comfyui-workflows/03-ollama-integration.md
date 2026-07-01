# Ollama Integration with ComfyUI

## Method 1: Using Ollama API Node

### Install ComfyUI-Ollama

```bash
cd ~/ComfyUI/custom_nodes
git clone https://github.com/hydfac/ComfyUI-Ollama.git
cd ComfyUI-Ollama
pip install -r requirements.txt
```

### Use in Workflow

1. Restart ComfyUI
2. Search for "Ollama" in nodes
3. Connect Ollama node to prompt input

## Method 2: Python Script Integration

```python
import requests
import json

class OllamaComfy:
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        self.comfy_url = "http://localhost:8188"
    
    def generate_prompt(self, concept, model="llama3.2:3b"):
        """Use Ollama to generate image prompt"""
        prompt = f"""Create a detailed stable diffusion prompt for: {concept}

Include: subject, setting, lighting, style, mood"""
        
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        
        # Extract and clean prompt
        raw = response.json()["response"]
        # Process to get clean SD prompt
        return self._process_prompt(raw)
    
    def _process_prompt(self, raw):
        # Clean up prompt for Stable Diffusion
        # Remove analysis text, keep key terms
        lines = raw.split("\n")
        prompt_parts = []
        for line in lines:
            if ":" in line and len(line) < 200:
                prompt_parts.append(line.split(":", 1)[1].strip())
        
        return ", ".join(prompt_parts[:8])
    
    def queue_comfy_workflow(self, prompt, workflow_type="txt2img"):
        """Send prompt to ComfyUI"""
        
        if workflow_type == "txt2img":
            workflow = self._get_txt2img_workflow(prompt)
        
        response = requests.post(
            f"{self.comfy_url}/prompt",
            json={"prompt": workflow}
        )
        
        return response.json()
    
    def _get_txt2img_workflow(self, prompt):
        # Basic workflow structure
        return {
            "3": {"inputs": {"text": prompt, "clip": ["4", 0]}, "class_type": "CLIPTextEncode"},
            "5": {"inputs": {"samples": ["6", 0]}, "class_type": "VAEDecode"},
            "6": {"inputs": {"model": ["7", 0], "noise": ["8", 0]}, "class_type": "KSampler"},
            # ... more nodes
        }

# Usage
ollama_comfy = OllamaComfy()
prompt = ollama_comfy.generate_prompt("a futuristic city at sunset")
ollama_comfy.queue_comfy_workflow(prompt)
```

## Method 3: External API Server

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    concept = data.get("concept")
    
    # 1. Generate prompt with Ollama
    ollama_resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2:3b",
            "prompt": f"Create a detailed art prompt: {concept}"
        }
    )
    
    prompt = ollama_resp.json()["response"]
    
    # 2. Send to ComfyUI
    comfy_resp = requests.post(
        "http://localhost:8188/prompt",
        json={"prompt": {"inputs": {"prompt": prompt}}}
    )
    
    return jsonify({"prompt": prompt, "job_id": comfy_resp.json()["prompt_id"]})

if __name__ == "__main__":
    app.run(port=5000)
```

## Advanced: Image-to-Prompt

```python
def image_to_prompt(self, image_path):
    """Describe image with Ollama, use for variation"""
    
    # Convert image to base64
    import base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    # Use vision model if available
    response = requests.post(
        f"{self.ollama_url}/api/generate",
        json={
            "model": "llama3.2:3b",  # Or vision model
            "prompt": "Describe this image in detail for AI generation"
        }
    )
    
    return response.json()["response"]
```

## Next Steps

- [Workflow Basics](./04-workflow-basics.md) - Create workflows
- [Image Generation](./05-image-generation.md) - Automated image generation
