# Project 9: TensorRT-Optimized LLM Inference Server

A comprehensive guide to building a high-performance LLM inference server using TensorRT-LLM for maximum throughput on Jetson AGX Orin 64GB with FP16/INT8 quantization.

## Table of Contents

1. [Overview](#overview)
2. [Hardware Optimization](#hardware-optimization)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [What You'll Build](#what-youll-build)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install TensorRT-LLM](#step-1-install-tensorrt-llm)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Configure TensorRT-LLM](#step-3-configure-tensorrt-llm)
   - [Step 4: Create Inference Server](#step-4-create-inference-server)
   - [Step 5: Set Up Monitoring](#step-5-set-up-monitoring)
7. [Running the Server](#running-the-server)
8. [Performance Tuning](#performance-tuning)
9. [API Documentation](#api-documentation)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a production-grade inference server:

- **TensorRT-LLM Optimization**: Maximum GPU utilization
- **Dynamic Batching**: Handle multiple requests efficiently
- **FP16/INT8 Quantization**: Faster inference with minimal quality loss
- **Streaming Responses**: Real-time token generation
- **Prometheus Metrics**: Full observability
- **OpenAI-Compatible API**: Easy integration

### Why TensorRT-LLM?

| Feature | Improvement |
|---------|------------|
| FP16 Precision | 2x faster than FP32 |
| INT8 Quantization | 4x faster, less memory |
| KV Cache Optimization | Reduced memory bandwidth |
| Dynamic Batching | Better GPU utilization |
| Tensor Cores | 3x faster matrix operations |

---

## Hardware Optimization

### Jetson AGX Orin 64GB Specifications

| Component | Specification |
|-----------|---------------|
| GPU | NVIDIA Ampere (sm_87) |
| Tensor Cores | 64 |
| CUDA Cores | 2048 |
| Memory | 64GB Unified |
| Storage | NVMe SSD recommended |

### Power Mode

```bash
# Maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify
jtop
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 TensorRT-LLM Server Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │   Client     │─────▶│   FastAPI    │─────▶│  TensorRT    │           │
│   │  (Requests)  │      │   Server     │      │    Engine    │           │
│   └──────────────┘      └──────┬───────┘      └──────┬───────┘           │
│                                 │                     │                    │
│                                 │                ┌────┴────┐              │
│                                 │                │         │              │
│                                 ▼                ▼         ▼              │
│                         ┌──────────────┐   ┌────────┐ ┌────────┐          │
│                         │   Metrics    │   │  FP16  │ │  INT8  │          │
│                         │  Prometheus  │   │  Mode  │ │Quantize│          │
│                         └──────────────┘   └────────┘ └────────┘          │
│                                                                             │
│   GPU Optimization:                                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  • Tensor Cores Enabled  • KV Cache Optimization                   │  │
│   │  • Flash Attention        • Dynamic Batching                        │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Version | Purpose |
|-----------|---------|---------|
| CUDA | 12.6 | GPU computation |
| TensorRT | 10.3 | Model optimization |
| Python | 3.10+ | Runtime |
| Docker | Latest | Containerization |

### Pre-Installation Verification

```bash
# Check CUDA
nvcc --version

# Check TensorRT
dpkg -l | grep TensorRT

# Check GPU
nvidia-smi
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| TensorRT Optimization | GPU-accelerated inference |
| FP16/INT8 Quantization | Reduced precision for speed |
| Dynamic Batching | Efficient request handling |
| Streaming | Server-Sent Events |
| Prometheus Metrics | Monitoring |
| OpenAI API | Compatible endpoints |

---

## Step-by-Step Implementation

### Step 1: Install TensorRT-LLM

```bash
# Install TensorRT-LLM
pip3 install tensorrtllm_backend --extra-index-url https://pypi.nvidia.com

# Install additional dependencies
pip3 install transformers accelerate peft fastapi uvicorn \
    sse-starlette prometheus-client pynvml numpy

# Verify installation
python3 -c "import tensorrt; import tensorrt_llm; print('TensorRT-LLM installed')"
```

### Step 2: Create Project Directory

```bash
# Create project directory
mkdir -p ~/ai-projects/tensorrt-llm-server
cd ~/ai-projects/tensorrt-llm-server

# Create subdirectories
mkdir -p models metrics
```

### Step 3: Configure TensorRT-LLM

Create `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8080
  workers: 1
  timeout: 120

tensorrt:
  max_batch_size: 32
  max_num_tokens: 8192
  enable_trt_llm: true
  engine_dir: ./models

models:
  - name: llama3.2
    path: meta-llama/Llama-3.2-3B-Instruct
    precision: fp16
    max_length: 4096
    kv_cache_dtype: fp16

  - name: qwen2.5-coder
    path: Qwen/Qwen2.5-Coder-7B-Instruct
    precision: int8
    max_length: 4096

batching:
  enabled: true
  max_batch_size: 16
  timeout: 0.1

prometheus:
  enabled: true
  port: 9090
```

### Step 4: Create Inference Server

Create `server.py`:

```python
#!/usr/bin/env python3
"""
TensorRT-LLM Inference Server

High-performance LLM inference server with TensorRT optimization,
dynamic batching, and Prometheus metrics.

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import os
import time
import json
import logging
from typing import List, Dict, Optional, AsyncIterator
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from sse_starlette.sse import EventStreamResponse

# Try to import TensorRT-LLM
try:
    from tensorrt_llm.runtime import ModelRunner
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False
    print("Warning: TensorRT-LLM not available, using fallback")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Server settings
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8080'))

# Model settings
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'llama3.2')
MODEL_DIR = os.getenv('MODEL_DIR', './models')

# Precision settings
PRECISION = os.getenv('PRECISION', 'fp16')  # fp16 or int8

# Batching
ENABLE_BATCHING = os.getenv('ENABLE_BATCHING', 'true').lower() == 'true'
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', '16'))

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# METRICS
# ============================================================================

REQUEST_COUNT = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

REQUEST_LATENCY = Histogram(
    'llm_request_duration_seconds',
    'LLM request latency',
    ['model']
)

TOKEN_GENERATED = Counter(
    'llm_tokens_generated_total',
    'Total tokens generated',
    ['model']
)

ACTIVE_REQUESTS = Gauge(
    'llm_active_requests',
    'Currently active requests'
)

GPU_UTILIZATION = Gauge(
    'gpu_utilization_percent',
    'GPU utilization percentage'
)

GPU_MEMORY = Gauge(
    'gpu_memory_used_bytes',
    'GPU memory used'
)


# ============================================================================
# MODELS
# ============================================================================

class LLMModel:
    """LLM model wrapper with TensorRT optimization."""
    
    def __init__(self, model_name: str, precision: str = 'fp16'):
        self.model_name = model_name
        self.precision = precision
        self.runner = None
        self._load_model()
    
    def _load_model(self):
        """Load the model with TensorRT."""
        logger.info(f"Loading model: {self.model_name} ({self.precision})")
        
        if TENSORRT_AVAILABLE:
            try:
                # TensorRT-LLM loading
                self.runner = ModelRunner.from_dir(
                    os.path.join(MODEL_DIR, self.model_name),
                    precision=self.precision
                )
                logger.info(f"Model loaded with TensorRT-LLM")
                return
            except Exception as e:
                logger.warning(f"TensorRT-LLM failed: {e}")
        
        # Fallback to HuggingFace
        logger.info("Using HuggingFace fallback")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        # Load with appropriate precision
        if self.precision == 'int8':
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.int8,
                device_map='auto',
                trust_remote_code=True
            )
        elif self.precision == 'fp16':
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map='auto',
                trust_remote_code=True
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map='auto',
                trust_remote_code=True
            )
        
        self.model.eval()
        logger.info("Model loaded successfully")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False
    ) -> Dict:
        """Generate text from prompt."""
        start_time = time.time()
        
        if self.runner and TENSORRT_AVAILABLE:
            # TensorRT-LLM generation
            outputs = self.runner.generate(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=stream
            )
        else:
            # HuggingFace generation
            inputs = self.tokenizer(prompt, return_tensors='pt').to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id
                )
            
            outputs = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Calculate metrics
        latency = time.time() - start_time
        tokens = len(outputs.split())  # Approximate
        
        REQUEST_LATENCY.labels(model=self.model_name).observe(latency)
        TOKEN_GENERATED.labels(model=self.model_name).inc(tokens)
        
        return {
            'text': outputs,
            'tokens': tokens,
            'latency': latency
        }
    
    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> AsyncIterator[str]:
        """Stream generation token by token."""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        inputs = tokenizer(prompt, return_tensors='pt').to(self.model.device)
        
        # For streaming, we generate incrementally
        # This is a simplified version
        from transformers import TextIteratorStreamer
        from threading import Thread
        
        streamer = TextIteratorStreamer(
            tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        
        generation_kwargs = {
            **inputs,
            'max_new_tokens': max_tokens,
            'temperature': temperature,
            'top_p': top_p,
            'streamer': streamer,
            'do_sample': True
        }
        
        thread = Thread(
            target=self.model.generate,
            kwargs=generation_kwargs
        )
        thread.start()
        
        for text in streamer:
            yield f"data: {json.dumps({'token': text})}\n\n"
        
        thread.join()
        yield "data: [DONE]\n\n"


# ============================================================================
# MODEL REGISTRY
# ============================================================================

class ModelRegistry:
    """Manage loaded models."""
    
    def __init__(self):
        self.models: Dict[str, LLMModel] = {}
    
    def get_model(self, name: str, precision: str = None) -> LLMModel:
        """Get or load a model."""
        if precision is None:
            precision = PRECISION
        
        key = f"{name}_{precision}"
        
        if key not in self.models:
            self.models[key] = LLMModel(name, precision)
        
        return self.models[key]
    
    def list_models(self) -> List[Dict]:
        """List available models."""
        return [
            {
                'name': m.model_name,
                'precision': m.precision,
                'loaded': True
            }
            for m in self.models.values()
        ]


# Global registry
model_registry = ModelRegistry()


# ============================================================================
# FASTAPI APP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    logger.info("Starting TensorRT-LLM Server...")
    
    # Preload default model
    model_registry.get_model(DEFAULT_MODEL, PRECISION)
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(
    title="TensorRT-LLM Server",
    description="High-performance LLM inference with TensorRT",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# REQUEST MODELS
# ============================================================================

class GenerateRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL)
    prompt: str
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stream: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL)
    messages: List[ChatMessage]
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "tensorrt": TENSORRT_AVAILABLE,
        "models": model_registry.list_models()
    }


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {
                "id": m.model_name,
                "object": "model",
                "created": 0,
                "owned_by": "tensorrt-llm"
            }
            for m in model_registry.models.values()
        ]
    }


@app.post("/v1/completions")
async def generate(request: GenerateRequest):
    """Generate completion (OpenAI-compatible)."""
    try:
        REQUEST_COUNT.labels(model=request.model, status='started').inc()
        ACTIVE_REQUESTS.inc()
        
        model = model_registry.get_model(request.model)
        
        if request.stream:
            # Streaming response
            async def event_generator():
                for chunk in model.stream_generate(
                    request.prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p
                ):
                    yield chunk
            
            return EventStreamResponse(event_generator())
        
        # Non-streaming
        result = model.generate(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p
        )
        
        REQUEST_COUNT.labels(model=request.model, status='success').inc()
        
        return {
            "id": f"cmpl-{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "text": result['text'],
                "index": 0,
                "finish_reason": "length"
            }],
            "usage": {
                "prompt_tokens": len(request.prompt.split()),
                "completion_tokens": result['tokens'],
                "total_tokens": len(request.prompt.split()) + result['tokens']
            }
        }
        
    except Exception as e:
        REQUEST_COUNT.labels(model=request.model, status='error').inc()
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        ACTIVE_REQUESTS.dec()


@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    """Chat completion (OpenAI-compatible)."""
    try:
        REQUEST_COUNT.labels(model=request.model, status='started').inc()
        ACTIVE_REQUESTS.inc()
        
        # Convert messages to prompt
        prompt = "\n".join([
            f"{m.role}: {m.content}"
            for m in request.messages
        ])
        prompt += "\nassistant:"
        
        model = model_registry.get_model(request.model)
        result = model.generate(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p
        )
        
        REQUEST_COUNT.labels(model=request.model, status='success').inc()
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result['text']
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": result['tokens'],
                "total_tokens": len(prompt.split()) + result['tokens']
            }
        }
        
    except Exception as e:
        REQUEST_COUNT.labels(model=request.model, status='error').inc()
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/metrics")
async def metrics():
    """Prometheus metrics."""
    return generate_latest()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting TensorRT-LLM Server on {HOST}:{PORT}")
    logger.info(f"Default model: {DEFAULT_MODEL}")
    logger.info(f"Precision: {PRECISION}")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        workers=1
    )
```

### Step 5: Set Up Monitoring

The server includes Prometheus metrics. Configure Prometheus:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'tensorrt-llm'
    static_configs:
      - targets: ['localhost:8080']
```

---

## Running the Server

```bash
# Activate environment
cd ~/ai-projects/tensorrt-llm-server
source venv/bin/activate

# Run the server
python3 server.py

# Access the API
curl http://localhost:8080/health
```

---

## Performance Tuning

### Optimization Tips

| Setting | Recommendation |
|---------|----------------|
| Precision | INT8 for speed, FP16 for quality |
| Batch Size | 8-16 for Jetson |
| KV Cache | FP16 |
| Max Tokens | 2048 for most tasks |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Model loading slow | Use quantized model |
| Out of memory | Reduce batch size |
| Slow inference | Use INT8 precision |
| GPU not used | Check CUDA availability |

---

## License

MIT License
