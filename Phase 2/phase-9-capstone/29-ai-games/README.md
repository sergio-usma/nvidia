# Part 15: Bonus Projects - AI Plays Games

This section contains fun bonus projects where local AI models play classic games on your Jetson AGX Orin!

## Overview

Watch your local LLMs play classic games while monitoring system stats in real-time. A fun way to test model capabilities and see AI "thinking" in action.

## Projects

### 1. Tetris - AI Block Stacking
- [tetris-ai.md](tetris-ai.md) - Complete Tetris game with AI player
- Connect to Ollama, llama.cpp, LMStudio, or MLC-LLM
- Real-time GPU/CPU monitoring
- Custom AI prompts for different strategies

### 2. Snake - AI Serpent Game
- [snake-ai.md](snake-ai.md) - Complete Snake game with AI player
- Multiple AI backends supported
- Live performance metrics
- Configurable AI thinking time

## Supported AI Backends

| Backend | Port | Description |
|---------|------|-------------|
| Ollama | 11434 | Local LLM server |
| llama.cpp | 8080 | GGUF model server |
| LMStudio | 1234 | Local model server |
| MLC-LLM | 8000 | WebGPU/CUDA inference |

## Features

- **Real-time Stats**: GPU usage, memory, temperature monitoring
- **Multiple Backends**: Switch between Ollama, llama.cpp, LMStudio
- **Custom Prompts**: Configure AI behavior and strategy
- **Streaming Responses**: Watch AI think in real-time

## Prerequisites

- One of the AI backends installed and running
- Python 3.8+ with required libraries
- Jetson in MAXN mode for best performance

## Quick Start

1. Start your preferred AI backend
2. Choose a game (Tetris or Snake)
3. Run the game script
4. Watch AI play!

## System Requirements

- Jetson AGX Orin 64GB (recommended)
- 32GB also works with smaller models
- MAXN power mode for optimal performance
