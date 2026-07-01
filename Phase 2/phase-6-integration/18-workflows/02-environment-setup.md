# Environment Setup for Automation on Jetson AGX Orin

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Python Dependencies](#python-dependencies)
3. [LangChain Installation](#langchain-installation)
4. [n8n Installation](#n8n-installation)
5. [Verification](#verification)

## System Requirements

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Python 3.10+
- Ollama (from Part 9-12)

## Python Dependencies

```bash
# Core LangChain
pip install langchain langchain-community

# For agents
pip install langchain-core langchain-ollama

# For RAG
pip install faiss-cpu sentence-transformers

# For tools
pip install requests duckduckgo-search

# For memory
pip install redis sqlalchemy

# For n8n integration
pip install pydantic httpx
```

## LangChain Installation

```bash
# Install specific versions compatible with ARM64
pip install langchain==0.1.0 langchain-community==0.0.10
pip install langchain-ollama  # If available
```

## n8n Installation

### Option 1: Docker

```bash
# Install Docker
sudo apt install docker.io

# Run n8n
docker run -it --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
```

### Option 2: npm

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install n8n
npm install -g n8n

# Run n8n
n8n start
```

## Verification

```python
# Test LangChain
from langchain.llms import Ollama
print("✅ LangChain OK")

# Test Ollama integration
from langchain_ollama import ChatOllama
print("✅ Ollama integration OK")
```

## Next Steps

- [LangChain Basics](./03-langchain-basics.md)
- [LangChain on Jetson](./04-langchain-jetson.md)
