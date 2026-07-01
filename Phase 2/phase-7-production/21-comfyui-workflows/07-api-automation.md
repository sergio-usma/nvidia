# API Automation

## Flask API Server

```python
from flask import Flask, request, jsonify
import requests
import threading

app = Flask(__name__)

# Start Ollama and ComfyUI clients
OLLAMA_URL = "http://localhost:11434"
COMFY_URL = "http://localhost:8188"

@app.route("/generate", methods=["POST"])
def generate():
    """Generate image from concept"""
    data = request.json
    concept = data.get("concept")
    
    # 1. Generate prompt with Ollama
    ollama_resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "llama3.2:3b",
            "prompt": f"Create a detailed stable diffusion prompt: {concept}"
        }
    )
    
    prompt = ollama_resp.json()["response"]
    
    # 2. Generate image with ComfyUI
    workflow = _create_workflow(prompt)
    comfy_resp = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow})
    
    job_id = comfy_resp.json()["prompt_id"]
    
    return jsonify({
        "job_id": job_id,
        "prompt": prompt,
        "status": "queued"
    })

@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    """Check job status"""
    resp = requests.get(f"{COMFY_URL}/history/{job_id}")
    
    if job_id in resp.json():
        data = resp.json()[job_id]
        if data.get("status", {}).get("completed"):
            return jsonify({"status": "completed"})
    
    return jsonify({"status": "processing"})

def _create_workflow(prompt):
    return {
        "1": {"inputs": {"model_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"},
        "2": {"inputs": {"text": prompt, "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
        "3": {"inputs": {"text": "low quality", "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
        "4": {"inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "seed": 42, "steps": 20, "cfg": 7.0}, "class_type": "KSampler"},
        "5": {"inputs": {"samples": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
        "6": {"inputs": {"images": ["5", 0]}, "class_type": "SaveImage"}
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

## Webhook Integration

```python
@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive webhook to trigger generation"""
    data = request.json
    
    # Trigger async generation
    thread = threading.Thread(target=async_generate, args=(data,))
    thread.start()
    
    return jsonify({"status": "accepted"})

def async_generate(data):
    concept = data.get("concept")
    webhook_url = data.get("webhook_url")
    
    # Generate
    job_id = generate_image(concept)
    
    # Wait
    wait_for_completion(job_id)
    
    # Send result webhook
    requests.post(webhook_url, json={"job_id": job_id, "status": "completed"})
```

## Usage

```bash
# Trigger generation
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"concept": "a futuristic city"}'

# Check status
curl http://localhost:5000/status/job_id
```

## Next Steps

- [Custom Nodes](./08-custom-nodes.md) - Create custom ComfyUI nodes
- [Performance](./09-performance.md) - Optimize for Jetson
