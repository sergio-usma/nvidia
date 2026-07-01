# Part 21: n8n, LangChain, Automation & Agents

A comprehensive Guide to building AI automation workflows and agents on NVIDIA Jetson AGX Orin 64GB using n8n, LangChain, and related tools.

## Table of Contents

1. [Overview](./01-overview.md) - Introduction to automation & agents
2. [Environment Setup](./02-environment-setup.md) - Prerequisites and dependencies
3. [LangChain Basics](./03-langchain-basics.md) - LangChain fundamentals
4. [LangChain on Jetson](./04-langchain-jetson.md) - Jetson-specific implementation
5. [AI Agents](./05-agents.md) - Building autonomous agents
6. [Automation Workflows](./06-workflows.md) - Creating automated workflows
7. [n8n Setup](./07-n8n-setup.md) - n8n installation and configuration
8. [LangGraph](./08-langgraph.md) - Graph-based agent workflows
9. [RAG Automation](./09-rag-automation.md) - Retrieval-augmented generation
10. [Tools & Functions](./10-tools-functions.md) - Custom tools for agents
11. [Memory Management](./11-memory.md) - Agent memory and context
12. [Ollama Agents](./12-ollama-agents.md) - Ollama-powered agents
13. [Troubleshooting](./13-troubleshooting.md) - Common issues

## Quick Start

```bash
# Install LangChain
pip install langchain langchain-community

# Install n8n (via Docker or npm)
docker run -it --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
```

## What You'll Learn

- Build AI-powered automation workflows
- Create autonomous agents with LangChain
- Integrate n8n for visual automation
- Connect local LLMs to automation systems
- Implement RAG (Retrieval-Augmented Generation)
- Build custom tools and functions

## Prerequisites

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Python 3.10+
- Ollama (from Part 9-12)
- Docker (optional, for n8n)

## Architecture Overview

```
User Request → n8n Workflow → LangChain Agent → Ollama LLM
                                    ↓
                           Tools (Part 17-20)
                           - Image Generation
                           - Video Processing
                           - Speech AI
                           - MCP Tools
```

## Next Steps

Start with [Overview](./01-overview.md) to understand automation concepts, then proceed to [Environment Setup](./02-environment-setup.md).
