# Troubleshooting

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Runtime Errors](#runtime-errors)
3. [Memory Issues](#memory-issues)
4. [Performance Issues](#performance-issues)

## Installation Issues

### pip Install Fails

```bash
# Try with specific versions
pip install langchain==0.1.0 langchain-community==0.0.10

# Or from source
git clone https://github.com/langchain-ai/langchain.git
cd langchain
pip install -e .
```

### Ollama Connection Errors

```bash
# Check if Ollama is running
systemctl status ollama
# or
ps aux | grep ollama

# Start Ollama
ollama serve

# Check port
curl http://localhost:11434
```

### Module Not Found

```bash
# Reinstall langchain-ollama
pip uninstall langchain-ollama -y
pip install langchain-ollama

# Check Python version
python3 --version  # Should be 3.10+
```

## Runtime Errors

### LangChain Import Errors

```python
# If langchain_ollama not available, use httpx directly
import httpx

def query_ollama(prompt: str, model: str = "llama3.2:3b"):
    response = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120
    )
    return response.json()["response"]
```

### Tool Execution Errors

```python
# Add error handling to tools
from langchain.tools import tool
import traceback

@tool
def safe_tool(input: str) -> str:
    try:
        # Tool logic
        return result
    except Exception as e:
        return f"Error: {str(e)}\n{traceback.format_exc()}"
```

### Agent Infinite Loop

```python
# Add max iterations
from langchain.agents import AgentExecutor

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=10,  # Limit iterations
    max_execution_time=60,  # Or time limit
    handle_parsing_errors="Error occurred, try again"
)
```

## Memory Issues

### Out of Memory Errors

```python
import gc
import torch

def clear_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

# Use in long-running agents
class MemorySafeAgent:
    def __init__(self):
        self.llm = ChatOllama(model="llama3.2:3b")
    
    def run(self, task: str):
        try:
            return self.llm.invoke(task)
        except RuntimeError as e:
            if "out of memory" in str(e):
                clear_memory()
                # Try with smaller model
                self.llm = ChatOllama(model="llama3.2:1b")
                return self.llm.invoke(task)
            raise
```

### Vector Store Memory

```python
# Use smaller embeddings
embeddings = OllamaEmbeddings(model="all-minilm:6v")

# Or limit chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,  # Smaller chunks
    chunk_overlap=20
)

# Limit search results
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 2}  # Fewer results
)
```

## Performance Issues

### Slow Inference

```python
# Use smaller model for speed
llm = ChatOllama(
    model="llama3.2:1b",  # Smaller/faster
    temperature=0.3
)

# Or use quantization
llm = ChatOllama(
    model="llama3.2:3b",
    options={"num_gpu": 1}
)
```

### Agent Too Slow

```python
# Optimize prompt length
prompt = PromptTemplate(
    template="Brief: {input}\nAnswer:",  # Shorter prompt
    input_variables=["input"]
)

# Cache results
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(query: str):
    return agent.run(query)
```

### n8n Performance

```bash
# Increase memory for n8n
docker run -m 4g ...

# Or use nginx caching
```

## Common Error Solutions

### Error: "model not found"

```bash
# Pull the model
ollama pull llama3.2:3b

# List available models
ollama list
```

### Error: "connection refused"

```bash
# Check Ollama is running
ollama serve

# Or start as service
sudo systemctl enable ollama
sudo systemctl start ollama
```

### Error: "port already in use"

```bash
# Find process using port
sudo lsof -i :11434

# Kill or use different port
OLLAMA_HOST=0.0.0.0:11435 ollama serve
```

### Error: "Import chainstream not found"

```bash
# Install missing dependencies
pip install langchain-core langchain-community
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Or set LangChain verbose
from langchain import verbose
verbose(True)
```

### Check System Resources

```bash
# CPU/Memory
htop

# GPU (if available)
tegrastats

# Disk
df -h
```

### Test Components Separately

```python
# Test Ollama first
import requests
resp = requests.post("http://localhost:11434/api/generate",
    json={"model": "llama3.2:3b", "prompt": "hi", "stream": False})
print(resp.json())

# Then test LangChain
from langchain_ollama import ChatOllama
llm = ChatOllama(model="llama3.2:3b")
print(llm.invoke("hi"))
```

## Hardware-Specific Issues

### Jetson Thermal Throttling

```bash
# Check temperature
tegrastats

# Improve cooling
sudo jetson_clocks

# Check power mode
sudo nvpmodel -q
```

### Limited VRAM

```python
# Use CPU fallback
llm = ChatOllama(
    model="llama3.2:1b",  # Smaller model
    options={"num_gpu": 0}  # CPU only
)
```

### Swap Usage

```bash
# Check swap
swapon -s

# Increase swap if needed
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Getting Help

- Check LangChain docs: https://python.langchain.com/
- Ollama docs: https://github.com/ollama/ollama
- Jetson forums: https://forums.developer.nvidia.com/
