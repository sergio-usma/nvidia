# Project 2: Multi-Agent Academic Writing Platform

A comprehensive guide to building a collaborative multi-agent system that writes academic articles and scientific publications using local LLM on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
6. [Running the System](#running-the-system)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a multi-agent academic writing system:

- **Research Agent**: Gather information
- **Outline Agent**: Create structure
- **Writing Agent**: Generate content
- **Review Agent**: Edit and improve
- **Citation Agent**: Manage references
- **Web UI**: Monitor process

### Agent Collaboration

| Agent | Role |
|-------|------|
| Research | Find information |
| Outline | Structure content |
| Writing | Generate text |
| Review | Edit quality |
| Citation | Manage sources |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Multi-Agent Writing Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      ORCHESTRATOR                                   │   │
│   │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │
│   │  │ Research │  │ Outline  │  │  Write  │  │  Review │      │   │
│   │  │ Manager  │  │ Manager  │  │ Manager  │  │ Manager  │      │   │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │   │
│   └───────┼──────────────┼──────────────┼──────────────┼───────────────┘   │
│           │              │              │              │                     │
│           ▼              ▼              ▼              ▼                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         LLM (Ollama)                                 │   │
│   │                                                                      │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│   │  │ Researcher│  │ Outliner │  │  Writer  │  │ Reviewer │        │   │
│   │  │   Agent   │  │  Agent   │  │   Agent  │  │   Agent  │        │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   Outputs:                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│   │  Document   │  │   Web UI    │  │   Export    │                   │
│   │  Output     │  │  (Progress) │  │   (PDF/MD)  │                   │
│   └──────────────┘  └──────────────┘  └──────────────┘                   │
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

---

## What You'll Build

### Agents

| Agent | Function |
|-------|----------|
| Research | Find topics |
| Outline | Structure |
| Writing | Generate |
| Review | Edit |
| Citation | References |

---

## Implementation

### Agent System

```python
class Agent:
    """Base agent class."""
    
    def __init__(self, name, role, model):
        self.name = name
        self.role = role
        self.model = model
    
    def run(self, task):
        """Execute task."""
        pass

class ResearchAgent(Agent):
    """Research agent."""
    
    def run(self, topic):
        # Gather information
        return research_data

class WritingAgent(Agent):
    """Writing agent."""
    
    def run(self, outline):
        # Generate content
        return content
```

### Orchestration

```python
class WritingOrchestrator:
    """Coordinates agents."""
    
    def __init__(self):
        self.agents = {
            'research': ResearchAgent(),
            'outline': OutlineAgent(),
            'writing': WritingAgent(),
            'review': ReviewAgent()
        }
    
    def write_article(self, topic):
        # Run pipeline
        research = self.agents['research'].run(topic)
        outline = self.agents['outline'].run(research)
        content = self.agents['writing'].run(outline)
        final = self.agents['review'].run(content)
        return final
```

---

## Running the System

```bash
# Install dependencies
pip3 install flask langchain

# Run the system
python3 app.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| LLM slow | Use smaller model |
| Content poor | Adjust prompts |
| Memory error | Reduce batch size |

---

## License

MIT License
