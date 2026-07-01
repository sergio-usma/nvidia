# Automation & Agents Overview on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [What is Automation?](#what-is-automation)
3. [LangChain](#langchain)
4. [n8n](#n8n)
5. [Agents](#agents)
6. [Jetson Implementation](#jetson-implementation)

## Introduction

Automation and agents allow AI systems to perform tasks autonomously. On Jetson AGX Orin, we can build:

- **Workflow Automation**: Automated sequences of tasks
- **AI Agents**: Autonomous systems that reason and act
- **RAG Systems**: Retrieval-augmented knowledge
- **Custom Tools**: Domain-specific capabilities

## What is Automation?

Automation uses AI to:

- Execute repetitive tasks
- Respond to triggers
- Make decisions
- Chain multiple operations

## LangChain

LangChain is a framework for building applications with LLMs:

```python
from langchain.llms import Ollama
from langchain.chains import LLMChain

llm = Ollama(model="llama2")
chain = LLMChain(llm=llm, prompt="Tell me about {topic}")
```

### LangChain Components

| Component | Purpose |
|-----------|---------|
| Chains | Sequence of operations |
| Agents | Autonomous decision-making |
| Memory | State persistence |
| Tools | External capabilities |
| Prompts | Input templates |

## n8n

n8n is a visual workflow automation tool:

- **No-code** workflow builder
- **300+ integrations**
- **Self-hosted** option
- **API-first** design

### n8n Features

- Trigger workflows on events
- Connect services
- Run code
- AI node integration

## Agents

AI agents are autonomous systems that:

1. **Perceive** their environment
2. **Reason** about actions
3. **Act** to achieve goals
4. **Learn** from feedback

### Agent Types

| Type | Description |
|------|-------------|
| ReAct | Reasoning + Action |
| Tool Use | Use external tools |
| Conversational | Chat-based |
| Plan-and-Execute | Planning first |

## Jetson Implementation

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    n8n     │────►│  LangChain │────►│   Ollama   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Tools    │
                    │ - Part 17  │
                    │ - Part 18  │
                    │ - Part 19  │
                    │ - Part 20  │
                    └─────────────┘
```

## Next Steps

- [Environment Setup](./02-environment-setup.md) - Install dependencies
- [LangChain Basics](./03-langchain-basics.md) - Learn LangChain
- [AI Agents](./05-agents.md) - Build agents
