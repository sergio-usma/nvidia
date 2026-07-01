# Project 5: Math Teaching Agent with Visualizations

A comprehensive guide to building an AI-powered math tutor that teaches calculus step-by-step with interactive visualizations using matplotlib on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
6. [Running the Tutor](#running-the-tutor)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates an interactive math tutoring system:

- **Step-by-Step Solutions**: Problem breakdown
- **Visualizations**: Interactive graphs
- **Explanations**: AI-generated teaching
- **Web Interface**: Problem input/output
- **Multiple Topics**: Derivatives, integrals, limits

### Supported Topics

| Topic | Description |
|-------|-------------|
| Derivatives | Rate of change |
| Integrals | Area under curve |
| Limits | Approach behavior |
| Functions | Graph analysis |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Math Tutor Architecture                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        MATH ENGINE                                   │   │
│   │                                                                      │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│   │  │  SymPy  │  │ NumPy    │  │ Matplotlib│  │  Ollama  │        │   │
│   │  │(Symbolic)│  │ (Numeric)│  │ (Plots)  │  │  (AI)   │        │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      TUTORIAL LOGIC                                │   │
│   │                                                                      │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│   │  │ Problem  │  │  Step    │  │   Plot   │  │Explain  │        │   │
│   │  │  Parser  │  │ Solver   │  │ Generator│  │  Gen    │        │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        WEB INTERFACE                               │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │   │
│   │  │ Input   │  │ Solution │  │  Plot   │                     │   │
│   │  │  Form   │  │ Display  │  │ Viewer  │                     │   │
│   │  └──────────┘  └──────────┘  └──────────┘                     │   │
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
| Python | Part 3 |
| SymPy | pip install |
| Matplotlib | pip install |

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Problem Solver | Solve math problems |
| Step-by-Step | Show work |
| Visualizations | Graph functions |
| AI Explanations | Teaching via LLM |

---

## Implementation

### Math Engine

```python
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

def derivative(f, var):
    """Compute derivative."""
    x = sp.symbols(var)
    return sp.diff(f, x)

def plot_function(f, x_range=(-10, 10)):
    """Plot function."""
    x = np.linspace(*x_range, 100)
    y = eval(f)
    plt.plot(x, y)
    plt.savefig('plot.png')
```

### Web Interface

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/solve', methods=['POST'])
def solve():
    problem = request.json['problem']
    solution = solve_problem(problem)
    return jsonify(solution)
```

---

## Running the Tutor

```bash
# Install dependencies
pip3 install flask matplotlib sympy numpy

# Run the tutor
python3 app.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Plot not showing | Check matplotlib backend |
| SymPy error | Verify problem syntax |
| LLM slow | Use smaller model |

---

## License

MIT License
