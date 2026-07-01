# Nemotron Super 120B — NVIDIA's Largest Reasoning Model

NVIDIA's Nemotron Super 120B is a Mixture-of-Experts model with 120B total parameters but only 12B active per token — meaning it delivers 70B-class reasoning quality at closer to 7B inference speed. On Jetson AGX Orin 64GB with a 50GB NVMe swap, you can run the Q4_K_XL quantization at ~2–3 tok/s. This is your local GPT-4 class model.

---

## What You'll Learn

- Why 120B MoE models fit on 64GB when dense 120B models don't
- Setting up llama.cpp HTTP server for large models
- Streaming responses via HTTP SSE from Python
- Using swap memory effectively for large inference
- When to use a 120B model vs a 7B model

## Memory Math for 120B MoE

```
Nemotron Super 120B Q4_K_XL:
- Total weights: ~60 GB on disk
- Active weights per token: ~12B → ~6 GB in working set
- KV cache (8192 ctx): ~8 GB
- Runtime overhead: ~2 GB
- Total needed: ~60 GB load + ~10 GB active = fits in 64GB unified + 50GB swap
```

The key: unified memory on Jetson means GPU and CPU share the same 64GB pool. The model layers you don't use stay in swap; active layers stay in VRAM.

## Prerequisites

### Hardware Check

```bash
# Confirm you have 64GB unified memory
free -h
# Should show ~60GB total

# Check NVMe storage (needs 80+ GB free)
df -h /
df -h /data 2>/dev/null || echo "Consider mounting NVMe at /data"

# Enable 50GB swap (REQUIRED for this model)
# See: ~/Desktop/JETSON-CONFIG/jetson-getting-started/phase-2-environment/02-system-setup/03-swap-file.md
swapon --show
# Should show at least 50GB swap

# Set MAXN performance mode
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Build llama.cpp (if not already done)

```bash
# Check if already built
which llama-server && echo "Already installed" || echo "Need to build"

# If not built:
cd ~/
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build && cd build

# Build for Jetson (sm_87 = Ampere/Orin)
cmake .. \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_F16=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DGGML_CUDA_ARCH=sm_87
make -j12
sudo make install

# Verify
llama-server --version
```

### Download the Model

```bash
mkdir -p ~/models/nemotron-super
cd ~/models/nemotron-super

# Install huggingface-cli for downloading
pip install huggingface_hub

# Download the Q4_K_XL GGUF (split into multiple files)
# WARNING: ~60GB total download — use aria2 for resume support
pip install huggingface_hub[cli]

huggingface-cli download \
  nvidia/Nemotron-Super-49B-v1-GGUF \
  --repo-type model \
  --local-dir ~/models/nemotron-super \
  --include "*.gguf"

# Alternative: use wget directly
# wget -c "https://huggingface.co/..."

ls -la ~/models/nemotron-super/
```

> **Note:** The exact model path depends on what GGUF files are available on HuggingFace. Search for "Nemotron Super GGUF Q4_K_M" for the best quality/size tradeoff.

---

## Step 1 — Start llama.cpp Server

```bash
# Set MAXN before starting
sudo nvpmodel -m 0 && sudo jetson_clocks

# Start server (adjust model path to match your download)
llama-server \
  -m ~/models/nemotron-super/nemotron-super-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -n 2048 \
  --n-gpu-layers 999 \
  --ctx-size 8192 \
  --threads 8 \
  --log-disable

# Or with first file of a split model:
# llama-server -m ~/models/nemotron-super/nemotron-super-00001-of-00004.gguf ...
```

Expected output: `llama server listening at http://0.0.0.0:8080`

```bash
# Verify server is running in another terminal
curl -s http://localhost:8080/health | python3 -m json.tool
```

---

## Step 2 — Project Setup

```bash
mkdir -p ~/projects/nemotron_super
cd ~/projects/nemotron_super
python3 -m venv venv
source venv/bin/activate
pip install requests rich
```

---

## Step 3 — Create the Client

Save as `~/projects/nemotron_super/nemotron_super.py`:

```python
#!/usr/bin/env python3
"""
Nemotron Super 120B — Python Client for llama.cpp HTTP Server

At 2-3 tok/s, Nemotron Super is slow — but it's your local GPT-4.
Use it when you need maximum reasoning capability and can wait.

When to use 120B vs 7B:
- 7B: quick answers, code snippets, chat — use daily
- 120B: complex reasoning, nuanced analysis, difficult code — use selectively

Architecture note: This uses llama.cpp's HTTP API, NOT Ollama.
llama.cpp gives more control: custom sampling, stop tokens, raw logits.
The API is OpenAI-compatible: /v1/chat/completions and /v1/completions.
"""
import json
import time
import sys
from typing import Optional, Generator
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

console = Console()
SERVER_URL = "http://localhost:8080"

# These settings are tuned for 120B models on Jetson
DEFAULT_CONFIG = {
    "temperature": 0.5,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "n_predict": 2048,
}


def check_server() -> bool:
    """Check if llama.cpp server is running."""
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def stream_generate(prompt: str, system: str = "",
                    max_tokens: int = 2048,
                    temperature: float = 0.5,
                    stop_sequences: Optional[list[str]] = None) -> Generator[str, None, None]:
    """
    Stream tokens from llama.cpp server via Server-Sent Events.

    llama.cpp's /completion endpoint supports streaming via SSE:
    Each line is: data: {"content": "...", "stop": false}
    When stop=true, generation is complete.
    """
    # Format prompt with system if using completion endpoint
    if system:
        full_prompt = f"<|system|>\n{system}\n<|user|>\n{prompt}\n<|assistant|>\n"
    else:
        full_prompt = prompt

    payload = {
        "prompt": full_prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "top_p": DEFAULT_CONFIG["top_p"],
        "top_k": DEFAULT_CONFIG["top_k"],
        "repeat_penalty": DEFAULT_CONFIG["repeat_penalty"],
        "stream": True,
    }
    if stop_sequences:
        payload["stop"] = stop_sequences

    response = requests.post(
        f"{SERVER_URL}/completion",
        json=payload,
        stream=True,
        timeout=300,  # 5 minutes for long responses
    )
    response.raise_for_status()

    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_str = line_str[6:]  # Remove "data: " prefix
                try:
                    data = json.loads(data_str)
                    token = data.get("content", "")
                    if token:
                        yield token
                    if data.get("stop", False):
                        break
                except json.JSONDecodeError:
                    continue


def chat_completion(messages: list[dict],
                    temperature: float = 0.5,
                    max_tokens: int = 2048) -> Generator[str, None, None]:
    """
    Use the OpenAI-compatible /v1/chat/completions endpoint.
    This is cleaner for multi-turn conversations.
    """
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    response = requests.post(
        f"{SERVER_URL}/v1/chat/completions",
        json=payload,
        stream=True,
        timeout=300,
    )
    response.raise_for_status()

    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: ") and line_str != "data: [DONE]":
                try:
                    data = json.loads(line_str[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue


def ask(question: str, system: str = "", temperature: float = 0.5,
        max_tokens: int = 2048, label: str = "Nemotron 120B") -> str:
    """Single-turn question with streaming output."""
    if not check_server():
        console.print("[red]Server not running. Start llama-server first.[/red]")
        return ""

    start = time.time()
    response_text = ""
    tokens = 0

    print(f"\n\033[94m{label}:\033[0m ", end="", flush=True)

    try:
        for token in stream_generate(question, system, max_tokens, temperature):
            print(token, end="", flush=True)
            response_text += token
            tokens += 1

    except requests.RequestException as e:
        console.print(f"\n[red]Connection error: {e}[/red]")
        return response_text

    print()
    elapsed = time.time() - start
    tok_s = tokens / elapsed if elapsed > 0 else 0
    console.print(f"[dim]  {elapsed:.1f}s | {tok_s:.2f} tok/s | {tokens} tokens[/dim]")
    return response_text


# ── Task-Specific Functions ─────────────────────────────────────────────────

def deep_analysis(topic: str) -> str:
    """
    Comprehensive deep-dive analysis. Use 120B for complex topics
    where a 7B model would give shallow or incorrect analysis.
    """
    system = (
        "You are a world-class expert analyst. Provide thorough, nuanced, "
        "multi-perspective analysis. Cover depth that a 7B model would miss."
    )
    prompt = f"""Provide a comprehensive analysis of: {topic}

Structure your analysis:
1. Core concepts and mechanisms
2. Historical context and evolution
3. Multiple stakeholder perspectives
4. Trade-offs and tensions
5. Current state and controversies
6. Future trajectory and implications

Be specific, cite concrete examples, and don't shy from nuance."""

    return ask(prompt, system, temperature=0.6, max_tokens=3000, label="Deep Analysis")


def complex_reasoning(problem: str) -> str:
    """
    Multi-step reasoning for hard problems.
    120B models dramatically outperform 7B on complex chains of reasoning.
    """
    system = (
        "You are an expert problem solver. Work through complex problems "
        "step by step, considering all constraints, edge cases, and alternatives."
    )
    return ask(problem, system, temperature=0.3, max_tokens=3000,
               label="Complex Reasoning")


def write_long_form(task: str, style: str = "technical") -> str:
    """
    Generate long-form content (1000+ words).
    120B models maintain coherence over much longer outputs.
    """
    styles = {
        "technical": "clear, precise technical prose",
        "essay": "analytical essay format with clear argument structure",
        "report": "formal report with executive summary and sections",
    }
    style_desc = styles.get(style, style)

    prompt = (
        f"Write a comprehensive {style_desc} about: {task}\n\n"
        f"This should be detailed, well-structured, and thorough — "
        f"at least 800 words. Don't rush."
    )
    return ask(prompt, temperature=0.6, max_tokens=4096, label="Long-Form Writing")


def generate_code(description: str, language: str = "python") -> str:
    """
    Generate complex, production-quality code.
    120B models handle architectural patterns that stump smaller models.
    """
    system = (
        f"You are a senior software architect. Write production-quality {language} code "
        f"with proper error handling, documentation, and design patterns."
    )
    prompt = (
        f"Implement the following in {language}:\n{description}\n\n"
        f"Requirements: complete implementation, type hints (Python), docstrings, "
        f"error handling, and inline comments for complex logic."
    )
    return ask(prompt, system, temperature=0.2, max_tokens=4096, label="Code Generation")


class ConversationSession:
    """Multi-turn conversation using OpenAI-compatible chat endpoint."""

    def __init__(self, system: str = "You are a helpful, knowledgeable assistant. "
                                    "Provide thorough, accurate responses."):
        self.messages = [{"role": "system", "content": system}]
        self.turn = 0

    def chat(self, user_message: str, temperature: float = 0.5) -> str:
        if not check_server():
            return "Server not running."

        self.messages.append({"role": "user", "content": user_message})
        self.turn += 1

        start = time.time()
        response = ""
        tokens = 0

        print(f"\n\033[94m[Turn {self.turn}] Nemotron:\033[0m ", end="", flush=True)

        try:
            for token in chat_completion(self.messages, temperature):
                print(token, end="", flush=True)
                response += token
                tokens += 1
        except requests.RequestException as e:
            console.print(f"\n[red]Error: {e}[/red]")
            return response

        print()
        elapsed = time.time() - start
        tok_s = tokens / elapsed if elapsed > 0 else 0
        console.print(f"[dim]  {elapsed:.1f}s | {tok_s:.2f} tok/s[/dim]")

        self.messages.append({"role": "assistant", "content": response})
        return response

    def reset(self) -> None:
        system_msg = self.messages[0]
        self.messages = [system_msg]
        self.turn = 0
        console.print("[yellow]Conversation cleared[/yellow]")


def show_server_status() -> None:
    """Display server status and model info."""
    if not check_server():
        console.print(Panel("[red]Server OFFLINE[/red]\nStart with: llama-server -m <model.gguf> --port 8080",
                           border_style="red"))
        return

    try:
        r = requests.get(f"{SERVER_URL}/props", timeout=5)
        props = r.json() if r.status_code == 200 else {}
    except Exception:
        props = {}

    t = Table(title="Nemotron Super Server Status")
    t.add_column("Property", style="cyan")
    t.add_column("Value")
    t.add_row("Server", f"[green]ONLINE[/green] at {SERVER_URL}")
    t.add_row("Model", props.get("model_alias", props.get("model", "Unknown")))
    t.add_row("Context length", str(props.get("n_ctx", "Unknown")))
    console.print(t)


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]Nemotron Super 120B — NVIDIA's Flagship Model[/bold cyan]\n"
        "[dim]llama.cpp HTTP backend | 2-3 tok/s | GPT-4 class reasoning[/dim]",
        border_style="cyan",
    ))

    show_server_status()

    if not check_server():
        console.print("\n[yellow]Start the server first (see Prerequisites above)[/yellow]")
        return

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]chat[/cyan]      Multi-turn conversation")
    console.print("  [cyan]reason[/cyan]    Complex multi-step reasoning")
    console.print("  [cyan]analyze[/cyan]   Deep topic analysis")
    console.print("  [cyan]code[/cyan]      Generate production code")
    console.print("  [cyan]write[/cyan]     Long-form content generation")
    console.print("  [cyan]status[/cyan]    Server status")
    console.print("  [cyan]quit[/cyan]      Exit\n")

    session = ConversationSession()

    while True:
        try:
            cmd = console.input("[bold blue]nemotron>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "chat":
                console.print("[dim]Conversation mode. /reset, /quit[/dim]\n")
                while True:
                    msg = console.input("[green]You:[/green] ").strip()
                    if not msg:
                        continue
                    if msg.startswith("/"):
                        if msg[1:] in ("quit", "q"):
                            break
                        elif msg[1:] == "reset":
                            session.reset()
                        continue
                    session.chat(msg)

            elif cmd == "reason":
                problem = console.input("Complex problem: ").strip()
                complex_reasoning(problem)

            elif cmd == "analyze":
                topic = console.input("Topic for deep analysis: ").strip()
                deep_analysis(topic)

            elif cmd == "code":
                lang = console.input("Language [python/javascript/go/bash]: ").strip() or "python"
                desc = console.input("What to implement: ").strip()
                result = generate_code(desc, lang)
                save = console.input("Save to file? [filename or Enter]: ").strip()
                if save:
                    from pathlib import Path
                    Path(save).write_text(result)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "write":
                task = console.input("What to write: ").strip()
                style = console.input("Style [technical/essay/report]: ").strip() or "technical"
                result = write_long_form(task, style)
                save = console.input("Save to file? [filename or Enter]: ").strip()
                if save:
                    from pathlib import Path
                    Path(save).write_text(result)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "status":
                show_server_status()

            else:
                # Treat as direct question
                ask(cmd)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
```

---

## Step 4 — Run It

```bash
# Terminal 1: start server
llama-server \
  -m ~/models/nemotron-super/nemotron-super-q4_k_m.gguf \
  --host 0.0.0.0 --port 8080 \
  --n-gpu-layers 999 --ctx-size 8192

# Terminal 2: run client
cd ~/projects/nemotron_super
source venv/bin/activate
python3 nemotron_super.py
```

---

## Step 5 — Hands-On Exercises

### Exercise 1: Feel the Difference vs 7B Models

Ask the same question to Nemotron Super and then to a 7B model. Compare depth:

```
nemotron> reason
Problem: Design a distributed system to handle 1 million real-time sensor readings per second from IoT devices. Sensors report temperature, humidity, and pressure. The system must: process data in real-time, detect anomalies within 100ms, store 30 days of history, and provide a REST API. What architecture would you use and why?
```

Then ask the same question to `mistral:7b` via Ollama. Compare architectural depth, consideration of trade-offs, and practical details.

### Exercise 2: Complex Technical Analysis

```
nemotron> analyze
Topic: The trade-offs between quantization levels (Q4_K_M vs Q8_0 vs FP16) for running LLMs on edge devices with limited memory bandwidth
```

At 120B, the model has absorbed much more nuanced knowledge about this topic than a 7B model.

### Exercise 3: Generate Complex Production Code

```
nemotron> code
Language: python
What: A complete async REST API server using FastAPI that: accepts sensor readings, stores them in SQLite with time-series indexing, detects anomalies using a rolling Z-score, sends email alerts via SMTP, and provides a WebSocket endpoint for real-time streaming
```

This is a complex multi-component system. Note how 120B handles the architecture much more coherently than smaller models.

### Exercise 4: Multi-Turn Technical Discussion

```
nemotron> chat
You: I'm designing a RAG system for a company with 50,000 documents
You: What embedding model would you recommend?
You: How should I chunk the documents?
You: What retrieval strategy should I use for questions that span multiple documents?
You: How do I evaluate if my RAG system is working well?
```

The 120B model maintains context across a long technical conversation much better than smaller models.

### Exercise 5: Monitor Performance

In another terminal while the model is running:
```bash
# Watch GPU utilization
watch -n 1 "tegrastats | grep -o 'GR3D_FREQ [0-9]*%'"

# Or use jtop
jtop
```

Note the GPU utilization pattern during generation: it won't be 100% because the model is too large to fully fit in the active GPU working set — it has to load/unload layers.

---

## Expected Output

```
nemotron> reason
Complex problem: Why does sorting 1 million random integers take much longer in practice than O(n log n) theory predicts?

[Turn 1] Nemotron:
The theoretical O(n log n) analysis makes several assumptions that don't hold in practice...

[Extended reasoning about cache effects, branch prediction, memory bandwidth...]

  47.3s | 2.41 tok/s | 114 tokens
```

**Performance (MAXN):** 2–3 tok/s for 120B Q4_K_XL. Patience required.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Server won't start | Check model path; check available memory with `free -h`; ensure 50GB swap is active |
| `cuda error: out of memory` | Reduce `--ctx-size` to 4096 or even 2048 |
| Very slow (< 1 tok/s) | Check MAXN mode: `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| Model not found on HuggingFace | Search "Nemotron Super GGUF" on HuggingFace; use smaller variant like nemotron-mini instead |
| `nvidia-smi` not found | Use `tegrastats` or `jtop` instead (Jetson doesn't have nvidia-smi) |
| Server crashes mid-generation | Context too long; reduce `--ctx-size`; restart server |

---

## Performance Optimization

```bash
# Maximize throughput:
sudo nvpmodel -m 0        # MAXN mode
sudo jetson_clocks         # Lock clocks

# Check swap usage during generation
watch -n 2 "free -h | grep Swap"

# Reduce swap usage: smaller context window
llama-server -m model.gguf --ctx-size 4096 ...  # Instead of 8192

# Use 4-bit vs 8-bit quantization:
# Q4_K_M: ~60GB, 2-3 tok/s
# Q4_K_XL: slightly better quality, same size
```

---

## Next Steps

- **[Qwen3 Dev](qwen3-dev.md)** — Qwen3 Coder via llama.cpp (also HTTP server)
- **[DeepSeek-R1 Reasoning](deepsr1-reasoning.md)** — Reasoning model via Ollama (simpler setup)
- **[Qwen2.5 Logic](qwen25-logic.md)** — Logical reasoning with a faster 7B model
