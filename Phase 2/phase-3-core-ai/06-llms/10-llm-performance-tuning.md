# LLM Performance Tuning

This guide covers performance tuning for LLM inference on Jetson AGX Orin.

## Quantization Levels

| Level | Bits | Memory | Quality | Speed |
|-------|------|--------|---------|-------|
| Q2_K | 2 | ~4GB/1B | Low | Fastest |
| Q3_K | 3 | ~5GB/1B | Medium | Fast |
| Q4_0 | 4 | ~6GB/1B | Good | Medium |
| Q4_K | 4 | ~6GB/1B | Better | Medium |
| Q5_0 | 5 | ~7GB/1B | Great | Slower |
| Q5_K | 5 | ~7GB/1B | Best | Slower |
| Q6_K | 6 | ~8GB/1B | Very Good | Slow |
| Q8_0 | 8 | ~10GB/1B | Near Full | Slowest |

## Context Window Optimization

```bash
# Smaller context for faster inference
ollama run llama2 "prompt" --ctx 2048

# llama.cpp
llama-cli -c 2048 -m model.gguf
```

## GPU Layer Optimization

```bash
# llama.cpp - offload more layers to GPU
llama-cli -ngl 35 -m model.gguf

# Check GPU layers
llama-cli -ngl 99 -m model.gguf --verbose
```

## Batch Processing

```python
# Process multiple prompts
import asyncio

async def batch_generate(prompts, model="llama2"):
    async with httpx.AsyncClient() as client:
        tasks = [
            client.post("http://localhost:11434/api/generate", 
                       json={"model": model, "prompt": p})
            for p in prompts
        ]
        responses = await asyncio.gather(*tasks)
        return [r.json()["response"] for r in responses]
```

## Prompt Engineering

```python
# System prompt for better performance
SYSTEM_PROMPT = """You are a helpful AI assistant. 
Be concise and accurate in your responses."""

# Structured prompts
def create_prompt(task, context=""):
    return f"""Task: {task}
Context: {context}
Answer:"""
```

## Caching

```python
# Cache embeddings
import hashlib

cache = {}

def get_embedding(text):
    cache_key = hashlib.md5(text.encode()).hexdigest()
    
    if cache_key in cache:
        return cache[cache_key]
    
    embedding = compute_embedding(text)
    cache[cache_key] = embedding
    return embedding
```

## Model Selection Guide

| Use Case | Recommended Model | Quantization |
|----------|------------------|--------------|
| Chat | Mistral | Q4_K |
| Code | CodeQwen | Q4_K |
| Math | MathStral | Q5_K |
| Reasoning | DeepSeek R1 | Q4_K |
| Embeddings | Nomic | Q4_0 |

## Performance Monitoring

```python
import time
import psutil

def monitor_inference():
    start = time.time()
    
    # Run inference
    result = generate(prompt)
    
    elapsed = time.time() - start
    tokens = len(result.split())
    
    print(f"Time: {elapsed:.2f}s")
    print(f"Tokens: {tokens}")
    print(f"Tokens/sec: {tokens/elapsed:.2f}")
    print(f"Memory: {psutil.virtual_memory().percent}%")
```

## Resource Management

```bash
# Limit Ollama memory
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_GPU_MEMORY=16GB
```

## Async Inference

```python
# Async for better throughput
async def stream_generate(prompt):
    async with httpx.AsyncClient() as client:
        async with client.stream_post(
            "http://localhost:11434/api/generate",
            json={"model": "llama2", "prompt": prompt}
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)
```

## Batching Strategies

```python
# Queue-based batching
from queue import Queue
import threading

class BatchProcessor:
    def __init__(self, batch_size=4, interval=0.1):
        self.queue = Queue()
        self.batch_size = batch_size
        self.interval = interval
        self.running = True
        self.thread = threading.Thread(target=self.process_batch)
    
    def add(self, prompt):
        future = Future()
        self.queue.put((prompt, future))
        return future.result()
    
    def process_batch(self):
        while self.running:
            batch = []
            futures = []
            
            while len(batch) < self.batch_size:
                try:
                    item = self.queue.get(timeout=self.interval)
                    batch.append(item[0])
                    futures.append(item[1])
                except:
                    break
            
            if batch:
                results = self.batch_inference(batch)
                for future, result in zip(futures, results):
                    future.set_result(result)
```

## Model Warm-up

```python
# Warm up model before production
def warmup():
    prompts = [
        "Hello, how are you?",
        "What is 2+2?",
        "Describe the sun."
    ]
    
    for prompt in prompts:
        generate(prompt)

# Run at startup
warmup()
```

## Streaming for Better UX

```python
# Stream tokens for perceived faster response
@app.route('/generate')
def generate():
    def generate_tokens():
        for chunk in stream_generate(prompt):
            yield f"data: {chunk}\n\n"
    
    return Response(generate_tokens(), 
                   mimetype='text/event-stream')
```
