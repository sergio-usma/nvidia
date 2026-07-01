# Custom ComfyUI Nodes

## Creating Custom Node

```python
# custom_nodes/OllamaPromptNode.py

import requests
import server
from nodes import NODE_CLASS_MAPPINGS
from PIL import Image
import io
import base64

class OllamaPromptGenerator:
    """Use Ollama to generate prompts"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "concept": ("STRING", {"multiline": True}),
                "model": ("STRING", {"default": "llama3.2:3b"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "generate"
    CATEGORY = "Ollama"
    
    def generate(self, concept, model):
        resp = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": f"Create detailed stable diffusion prompt: {concept}",
                "stream": False
            }
        )
        
        prompt = resp.json()["response"]
        return (prompt,)

NODE_CLASS_MAPPINGS = {
    "OllamaPromptGenerator": OllamaPromptGenerator
}
```

## Image Analysis Node

```python
class OllamaImageAnalyzer:
    """Analyze image with Ollama"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "question": ("STRING", {"default": "Describe this image"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "analyze"
    CATEGORY = "Ollama"
    
    def analyze(self, image, question):
        # Convert to base64
        img = Image.fromarray((image[0].cpu().numpy() * 255).astype("uint8"))
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Use vision model
        resp = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": "llama3.2:vision",  # or compatible
                "prompt": f"Question: {question}\nImage: (base64)",
                "stream": False
            }
        )
        
        return (resp.json()["response"],)

NODE_CLASS_MAPPINGS["OllamaImageAnalyzer"] = OllamaImageAnalyzer
```

## Installation

```bash
cd ~/ComfyUI/custom_nodes
mkdir MyCustomNodes
# Add your node files here
# Restart ComfyUI
```

## Next Steps

- [Performance](./09-performance.md) - Jetson optimization
- [Troubleshooting](./10-troubleshooting.md) - Common issues
