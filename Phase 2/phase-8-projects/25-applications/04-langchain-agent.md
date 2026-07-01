# Project 4: LangChain Local Chat Agent

A comprehensive guide to building a conversational AI agent using LangChain with local Ollama/LMStudio/llama.cpp/MLC-LLM backends on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
6. [Running the Agent](#running-the-agent)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a LangChain-powered chat agent:

- **Multiple Backends**: Ollama, LMStudio, llama.cpp
- **Custom Tools**: Calculator, search, file ops
- **Memory**: Conversation history
- **Web UI**: Chat interface

### Supported Backends

| Backend | Description |
|---------|-------------|
| Ollama | Local LLM server |
| LMStudio | Desktop LLM app |
| llama.cpp | Pure C++ inference |
| MLC-LLM | WebGPU/CUDA |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LangChain Agent Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      LANGCHAIN ORCHESTRATOR                        │   │
│   │                                                                      │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│   │  │  Prompt │  │  Memory  │  │  Tools   │  │   LLM    │        │   │
│   │  │Template │  │ (History)│  │ Registry │  │  (Ollama)│        │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         TOOLS                                       │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│   │  │Calculator│  │   Web    │  │  File    │  │  Custom  │       │   │
│   │  │         │  │  Search  │  │  Ops     │  │  Tool   │       │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation |
|-----------|-------------|
| Ollama | Part 5 |
| Python | Part 3 |
| LangChain | pip install |

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Chat Interface | Conversational UI |
| Tool Use | External actions |
| Memory | History retention |
| Multi-backend | Flexible LLM choice |

---

## Implementation

### Agent Setup

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_ollama import ChatOllama
from langchain.tools import Tool

# Initialize LLM
llm = ChatOllama(model="llama3.2")

# Define tools
def calculator(expression):
    """Evaluate math expression."""
    return str(eval(expression))

tools = [
    Tool(
        name="Calculator",
        func=calculator,
        description="Calculate math expressions"
    )
]

# Create agent
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
```

### Web Interface

```python
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/chat', methods=['POST'])
def chat():
    message = request.json['message']
    response = agent_executor.invoke(message)
    return jsonify(response)
```

---

## Running the Agent

```bash
# Install dependencies
pip3 install langchain langchain-ollama flask

# Run the agent
python3 app.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| LLM not connecting | Check backend URL |
| Tool fails | Verify tool implementation |
| Memory error | Adjust history length |

---

## License

MIT License
