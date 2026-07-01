# TinyLlama — Edge Chat & Benchmarking Lab

TinyLlama is a 1.1B parameter model — the fastest LLM you can run on Jetson. This project uses it as a speed benchmark baseline and shows you how to build a memory-constrained chat loop suited for IoT and edge deployments.

---

## What You'll Learn

- Why TinyLlama is useful: ~60 tok/s on Jetson = real-time conversational feel
- How to implement a sliding window history (important for constrained memory)
- Benchmarking: measuring and comparing inference speed across models
- When to use small models vs large ones

## Why TinyLlama?

| Model | Size | Speed (Jetson) | Quality |
|-------|------|----------------|---------|
| tinyllama:1.1b | 0.6 GB | ~55–65 tok/s | Basic |
| llama3.2:3b | 2.0 GB | ~35–45 tok/s | Good |
| qwen2.5:7b | 4.4 GB | ~18–22 tok/s | Excellent |

TinyLlama is ideal when you need **instant responses** and quality is less critical — dashboards, status alerts, simple Q&A chatbots.

## Prerequisites

```bash
# Only 637 MB — downloads in seconds
docker exec ollama ollama pull tinyllama
docker exec ollama ollama list | grep tiny
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/tinyllama
cd ~/projects/tinyllama
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Edge Chat

Save as `~/projects/tinyllama/edge_chat.py`:

```python
#!/usr/bin/env python3
"""
TinyLlama Edge Chat + Benchmark Tool
Fastest local chat on Jetson — 55-65 tok/s at 0.6 GB RAM usage.

Use cases:
- Real-time chatbots where latency matters
- IoT / kiosk applications with limited memory
- Benchmarking baseline for comparing larger models
- Fast prototyping before switching to a larger model
"""
import time
import sys
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

MODEL = "tinyllama"
# TinyLlama has a 2048 token context — small! Keep history short.
MAX_HISTORY = 6   # 3 user + 3 assistant messages
SYSTEM = "You are a concise, helpful assistant. Keep responses short and clear."


class EdgeChat:
    """
    Sliding window chat for memory-constrained deployments.

    The sliding window works like this:
    - We only keep the last MAX_HISTORY messages
    - When the window fills up, the oldest message pair is dropped
    - This limits memory usage but means the model forgets older context
    - Perfect for TinyLlama's small 2048-token context window
    """

    def __init__(self, model: str = MODEL, system: str = SYSTEM,
                 max_history: int = MAX_HISTORY):
        self.model = model
        self.max_history = max_history
        self.history = [{"role": "system", "content": system}]
        self.total_tokens = 0
        self.total_time = 0.0

    def chat(self, message: str) -> tuple[str, float]:
        """Send message and return (response, tok_per_sec)."""
        self.history.append({"role": "user", "content": message})

        # Sliding window: keep system + last max_history messages
        system_msg = self.history[0]
        recent = self.history[1:][-self.max_history:]
        trimmed_messages = [system_msg] + recent

        start = time.time()
        tokens = 0
        response_text = ""

        # Stream tokens
        print("\n\033[94mTinyLlama:\033[0m ", end="", flush=True)
        for chunk in ollama.chat(
            model=self.model,
            messages=trimmed_messages,
            stream=True,
            options={"temperature": 0.7, "num_ctx": 2048},
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            response_text += token
            tokens += 1

        print()
        elapsed = time.time() - start
        tok_per_sec = tokens / elapsed if elapsed > 0 else 0

        self.history.append({"role": "assistant", "content": response_text})
        self.total_tokens += tokens
        self.total_time += elapsed

        return response_text, tok_per_sec

    def reset(self) -> None:
        system_msg = self.history[0]
        self.history = [system_msg]
        self.total_tokens = 0
        self.total_time = 0.0

    def show_stats(self) -> None:
        t = Table(title="Session Stats")
        t.add_column("Metric", style="cyan")
        t.add_column("Value")
        t.add_row("Model", self.model)
        t.add_row("History messages", str(len(self.history) - 1))
        t.add_row("Total tokens generated", str(self.total_tokens))
        avg = self.total_tokens / self.total_time if self.total_time > 0 else 0
        t.add_row("Average speed", f"{avg:.1f} tok/s")
        console.print(t)


def benchmark(models: list[str], prompt: str, runs: int = 3) -> None:
    """
    Benchmark multiple models on the same prompt.
    Useful for deciding which model to use for a given use case.
    """
    console.print(Panel(f"[bold]Benchmarking {len(models)} models[/bold]\nPrompt: {prompt[:80]}"))
    results = []

    for model in models:
        times = []
        tok_counts = []
        for run in range(1, runs + 1):
            console.print(f"  [{run}/{runs}] {model}...", end="")
            start = time.time()
            tokens = 0
            response = ""
            try:
                for chunk in ollama.generate(
                    model=model,
                    prompt=prompt,
                    stream=True,
                    options={"temperature": 0.7, "num_predict": 100},
                ):
                    response += chunk["response"]
                    tokens += 1
                elapsed = time.time() - start
                console.print(f" {tokens/elapsed:.1f} tok/s")
                times.append(elapsed)
                tok_counts.append(tokens)
            except Exception as e:
                console.print(f" [red]ERROR: {e}[/red]")
                break

        if times:
            avg_tok_s = sum(t / e for t, e in zip(tok_counts, times)) / len(times)
            results.append((model, avg_tok_s, sum(tok_counts) // len(tok_counts)))

    # Results table
    t = Table(title="Benchmark Results")
    t.add_column("Model", style="cyan")
    t.add_column("Avg tok/s", justify="right")
    t.add_column("Avg tokens", justify="right")
    for model, avg_tps, avg_tok in sorted(results, key=lambda x: -x[1]):
        t.add_row(model, f"{avg_tps:.1f}", str(avg_tok))
    console.print(t)


def main():
    console.print(Panel.fit(
        "[bold cyan]TinyLlama Edge Chat[/bold cyan]\n"
        "[dim]Fastest local LLM on Jetson (~60 tok/s) | 0.6 GB RAM[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]/reset[/cyan]     Clear conversation history")
    console.print("  [cyan]/stats[/cyan]     Show session statistics")
    console.print("  [cyan]/bench[/cyan]     Benchmark TinyLlama vs other models")
    console.print("  [cyan]/quit[/cyan]      Exit\n")

    chat = EdgeChat()

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                cmd = user_input[1:].lower()
                if cmd in ("quit", "exit", "q"):
                    break
                elif cmd == "reset":
                    chat.reset()
                    console.print("[yellow]History cleared[/yellow]")
                elif cmd == "stats":
                    chat.show_stats()
                elif cmd == "bench":
                    prompt = console.input("Benchmark prompt: ")
                    models_input = console.input(
                        "Models to compare (comma-separated, e.g. tinyllama,llama3.2,qwen2.5:7b): "
                    )
                    models = [m.strip() for m in models_input.split(",")]
                    benchmark(models, prompt)
                continue

            _, tok_s = chat.chat(user_input)
            console.print(f"[dim]  {tok_s:.1f} tok/s[/dim]")

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/tinyllama
source venv/bin/activate
python3 edge_chat.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Speed Test — Feel the Difference

Ask a short question:
```
You: What is a neural network?
```
Notice: the response appears almost instantly. Check the `tok/s` counter.

### Exercise 2: Benchmark vs Larger Models

```
/bench
Benchmark prompt: Explain the difference between RAM and storage in 2 sentences
Models: tinyllama,llama3.2,qwen2.5:7b
```

Expected results (MAXN mode):
```
Model          Avg tok/s
tinyllama      ~60
llama3.2       ~40
qwen2.5:7b     ~22
```

### Exercise 3: Context Limit Test

Send 10+ messages and watch what happens. After `max_history=6` messages, the model will start forgetting the first messages — this is intentional for edge deployments.

### Exercise 4: Quality Comparison

Ask the same complex question to TinyLlama vs a 7B model:
```
You: Design a REST API for a blog platform with authentication
```

Compare the output quality. TinyLlama gives shorter, simpler answers — choose the right model for your quality requirements.

---

## Expected Output

```
You: What is CUDA?

TinyLlama: CUDA (Compute Unified Device Architecture) is NVIDIA's parallel
computing platform that lets you run code on the GPU. It's used by AI
frameworks like PyTorch to accelerate matrix operations in neural networks.

  62.3 tok/s
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `tinyllama not found` | `docker exec ollama ollama pull tinyllama` |
| Response cuts off early | TinyLlama has a 2048-token context — keep prompts short |
| Benchmark other model fails | Pull it first: `docker exec ollama ollama pull <model>` |
| Speed under 40 tok/s | Enable MAXN: `sudo nvpmodel -m 0 && sudo jetson_clocks` |

---

## Next Steps

- **[Mistral Chat](mistral-chat.md)** — Better quality, same speed pattern
- **[Nemotron Nano](nemotron-nano.md)** — Another fast small model
- **[GLM Flash](glm-flash.md)** — Fast generation with llama.cpp backend
