# GLM-4.7 Flash Fast Chat — High-Speed Conversational AI on Jetson

Build an interactive fast-chat tool powered by GLM-4.7 Flash running in the Ollama Docker container. GLM-4.7 Flash is a highly efficient model optimized for low-latency responses — on Jetson AGX Orin in MAXN mode it sustains 22–28 tok/s, making it ideal for real-time conversation, rapid summarization, and domain-expert mode switching. This project demonstrates conversation mode, batch summarization, and live tok/s telemetry.

---

## What You'll Learn

- How to build a multi-mode interactive CLI with `rich` panels and live streaming
- Displaying real-time tok/s performance telemetry during inference
- Implementing domain-expert personas via system prompt switching at runtime
- Batch document summarization with a progress display
- Managing conversation history with a token-budget cutoff
- Benchmarking model speed directly from Python

## Prerequisites

```bash
# Ensure Ollama container is running
docker ps | grep ollama

# Pull GLM-4.7 Flash (Ollama runs in Docker — always use docker exec)
docker exec ollama ollama pull glm4:flash

# Verify
docker exec ollama ollama list
```

```bash
# Set MAXN performance mode before inference
sudo nvpmodel -m 0
sudo jetson_clocks
```

> **Note on model tag:** GLM-4.7 Flash is available in the Ollama registry as `glm4:flash`.
> Check `docker exec ollama ollama list` for the exact tag after pulling.

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/glm-flash
cd ~/projects/glm-flash
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Fast Chat Tool

Save as `~/projects/glm-flash/glm_chat.py`:

```python
#!/usr/bin/env python3
"""
GLM-4.7 Flash Fast Chat Tool
Interactive high-speed chat, batch summarization, and domain-expert mode.
Uses Ollama Docker container (port 11434) with live tok/s display.
Jetson AGX Orin 64GB · JetPack 6.2.2 · CUDA 12.6
"""

import time
import sys
import argparse
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.rule import Rule
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

console = Console()

MODEL = "glm4:flash"
OLLAMA_HOST = "http://localhost:11434"

# ── Expert personas ───────────────────────────────────────────────────────────

EXPERTS = {
    "default": {
        "name": "General Assistant",
        "system": (
            "You are a fast, helpful assistant. Give clear, direct answers. "
            "Be concise unless the user asks for detail."
        ),
        "color": "cyan",
    },
    "devops": {
        "name": "DevOps Engineer",
        "system": (
            "You are a senior DevOps engineer specializing in containers, CI/CD, "
            "Kubernetes, and Linux systems. Give practical, battle-tested advice. "
            "Include commands where relevant. Assume the user is technical."
        ),
        "color": "green",
    },
    "ml": {
        "name": "ML Engineer",
        "system": (
            "You are a machine learning engineer with deep expertise in PyTorch, "
            "model optimization, quantization, and edge deployment (including NVIDIA Jetson). "
            "Explain tradeoffs clearly. Use equations only when they add clarity."
        ),
        "color": "magenta",
    },
    "writer": {
        "name": "Technical Writer",
        "system": (
            "You are an expert technical writer. Produce clear, well-structured "
            "documentation, summaries, and explanations. Use Markdown formatting. "
            "Be precise with terminology."
        ),
        "color": "yellow",
    },
    "analyst": {
        "name": "Data Analyst",
        "system": (
            "You are a data analyst skilled in Python (pandas, numpy, matplotlib), "
            "SQL, and statistical reasoning. Help interpret data, suggest analyses, "
            "and write clean analytical code."
        ),
        "color": "blue",
    },
}


# ── Core streaming helper ────────────────────────────────────────────────────

def stream_chat(
    prompt: str,
    system: str,
    history: Optional[list] = None,
    title: str = "GLM-4.7 Flash",
    color: str = "cyan",
) -> tuple[str, float]:
    """
    Stream a chat response and return (full_text, tok_per_sec).
    Prints tokens live to the terminal as they arrive.
    """
    client = ollama.Client(host=OLLAMA_HOST)

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    console.print(Rule(f"[bold {color}]{title}[/bold {color}]"))

    full_text = ""
    token_count = 0
    start = time.time()

    try:
        stream = client.chat(model=MODEL, messages=messages, stream=True)
        for chunk in stream:
            delta = chunk["message"]["content"]
            full_text += delta
            token_count += 1
            console.print(delta, end="", markup=False)

    except ollama.ResponseError as e:
        console.print(f"\n[red]Ollama error: {e}[/red]")
        if "not found" in str(e).lower():
            console.print(f"[yellow]Pull the model:[/yellow] docker exec ollama ollama pull {MODEL}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Connection error: {e}[/red]")
        console.print("[yellow]Check container:[/yellow] docker ps | grep ollama")
        sys.exit(1)

    elapsed = time.time() - start
    tps = token_count / elapsed if elapsed > 0 else 0.0

    console.print()
    console.print(
        Rule(
            f"[dim]{token_count} tokens · {elapsed:.1f}s · "
            f"[bold green]{tps:.1f} tok/s[/bold green][/dim]"
        )
    )
    return full_text, tps


# ── Mode 1: Interactive conversation ─────────────────────────────────────────

def run_conversation(expert_key: str = "default") -> None:
    """Multi-turn chat with selectable expert persona."""
    expert = EXPERTS.get(expert_key, EXPERTS["default"])
    color = expert["color"]

    console.print(
        Panel(
            f"[bold {color}]{expert['name']}[/bold {color}]\n"
            f"[dim]{expert['system'][:120]}...[/dim]\n\n"
            "[dim]Commands: [bold]/expert <name>[/bold] switch persona · "
            "[bold]/clear[/bold] reset history · "
            "[bold]/speed[/bold] show last tok/s · "
            "[bold]/quit[/bold] exit[/dim]",
            title="[bold]GLM-4.7 Flash Chat[/bold]",
            border_style=color,
        )
    )

    history: list = []
    last_tps: float = 0.0
    current_expert = expert

    while True:
        try:
            user_input = console.input(f"\n[bold {color}]You>[/bold {color}] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting.[/dim]")
            break

        if not user_input:
            continue

        # Commands
        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.lower() == "/clear":
            history.clear()
            console.print("[yellow]Conversation history cleared.[/yellow]")
            continue

        if user_input.lower() == "/speed":
            console.print(f"[green]Last response: {last_tps:.1f} tok/s[/green]")
            continue

        if user_input.lower().startswith("/expert "):
            key = user_input.split(None, 1)[1].strip().lower()
            if key in EXPERTS:
                current_expert = EXPERTS[key]
                color = current_expert["color"]
                history.clear()
                console.print(
                    f"[{color}]Switched to: {current_expert['name']}. History cleared.[/{color}]"
                )
            else:
                available = ", ".join(EXPERTS.keys())
                console.print(f"[red]Unknown expert. Available: {available}[/red]")
            continue

        if user_input.lower() == "/experts":
            _print_experts_table()
            continue

        # Generate response
        response, tps = stream_chat(
            user_input,
            current_expert["system"],
            history=history,
            title=current_expert["name"],
            color=current_expert["color"],
        )
        last_tps = tps

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})

        # Cap history at 16 messages to avoid context overflow
        if len(history) > 16:
            history = history[-16:]


def _print_experts_table() -> None:
    table = Table(title="Available Expert Personas", box=box.ROUNDED, border_style="cyan")
    table.add_column("Key", style="bold green")
    table.add_column("Name")
    table.add_column("Focus")
    table.add_row("default",  "General Assistant",   "General Q&A, explanations")
    table.add_row("devops",   "DevOps Engineer",      "Docker, Linux, CI/CD, Kubernetes")
    table.add_row("ml",       "ML Engineer",          "PyTorch, quantization, Jetson edge AI")
    table.add_row("writer",   "Technical Writer",     "Docs, summaries, structured writing")
    table.add_row("analyst",  "Data Analyst",         "Python data analysis, SQL, statistics")
    console.print(table)


# ── Mode 2: Batch summarization ───────────────────────────────────────────────

SUMMARIZE_SYSTEM = (
    "You are a precise summarizer. Produce a concise summary in 3–5 sentences. "
    "Preserve the key facts. Do not add opinions or information not in the source."
)

SAMPLE_DOCS = [
    {
        "title": "NVIDIA Jetson AGX Orin Overview",
        "text": (
            "The NVIDIA Jetson AGX Orin is NVIDIA's most powerful Jetson module, "
            "delivering up to 275 TOPS of AI performance. It features a 12-core "
            "ARM Cortex-A78AE CPU, an Ampere GPU with 2048 CUDA cores and 64 Tensor Cores, "
            "and up to 64GB of unified LPDDR5 memory. It supports JetPack 6.x with CUDA 12.6, "
            "TensorRT 10, and cuDNN 9. The module is designed for robotics, autonomous machines, "
            "edge AI inference, and industrial IoT applications requiring real-time AI."
        ),
    },
    {
        "title": "Retrieval-Augmented Generation (RAG) Explained",
        "text": (
            "Retrieval-Augmented Generation (RAG) is a technique that enhances large language "
            "models by retrieving relevant documents from an external knowledge base before "
            "generating a response. The process has two phases: indexing (encoding documents "
            "into vector embeddings and storing them in a vector database) and querying "
            "(encoding the user's question, finding the closest document embeddings via "
            "cosine similarity, and passing those documents as context to the LLM). "
            "RAG allows models to answer questions about private or up-to-date data "
            "without retraining, reduces hallucination by grounding answers in retrieved facts, "
            "and provides source citations for transparency."
        ),
    },
    {
        "title": "Transformer Architecture",
        "text": (
            "The Transformer architecture, introduced in the 2017 paper 'Attention Is All You Need', "
            "replaced recurrent networks with a self-attention mechanism that processes all tokens "
            "in parallel. The encoder stack maps input tokens to contextual representations; "
            "the decoder stack generates output tokens autoregressively. Multi-head attention "
            "allows the model to attend to different positions simultaneously, capturing both "
            "local and long-range dependencies. Positional encodings inject sequence order "
            "information since attention itself is permutation-invariant. Transformers became the "
            "foundation for GPT, BERT, T5, and virtually all modern LLMs."
        ),
    },
]


def run_batch_summarization(docs: Optional[list] = None) -> None:
    """Summarize multiple documents with a progress display."""
    if docs is None:
        docs = SAMPLE_DOCS

    console.print(
        Panel(
            f"[bold]Batch Summarization[/bold]\n"
            f"[dim]{len(docs)} documents to process with {MODEL}[/dim]",
            border_style="yellow",
        )
    )

    client = ollama.Client(host=OLLAMA_HOST)
    results = []

    for i, doc in enumerate(docs, 1):
        console.print(f"\n[bold yellow][{i}/{len(docs)}][/bold yellow] {doc['title']}")
        prompt = f"Summarize this text:\n\n{doc['text']}"

        messages = [
            {"role": "system", "content": SUMMARIZE_SYSTEM},
            {"role": "user", "content": prompt},
        ]

        full_text = ""
        token_count = 0
        start = time.time()

        try:
            stream = client.chat(model=MODEL, messages=messages, stream=True)
            console.print("[dim italic]", end="")
            for chunk in stream:
                delta = chunk["message"]["content"]
                full_text += delta
                token_count += 1
                console.print(delta, end="", markup=False)
            console.print("[/dim italic]", end="")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            continue

        elapsed = time.time() - start
        tps = token_count / elapsed if elapsed > 0 else 0.0
        console.print(f"\n[dim]  {token_count} tokens · {tps:.1f} tok/s[/dim]")
        results.append({"title": doc["title"], "summary": full_text, "tps": tps})

    # Print summary table
    console.print()
    table = Table(
        title="Summarization Results",
        box=box.SIMPLE_HEAD,
        border_style="yellow",
    )
    table.add_column("Document", style="bold", max_width=30)
    table.add_column("Summary (truncated)", max_width=55)
    table.add_column("tok/s", justify="right", style="green")

    for r in results:
        short_summary = r["summary"][:120].replace("\n", " ") + "..."
        table.add_row(r["title"][:28], short_summary, f"{r['tps']:.1f}")

    console.print(table)


# ── Mode 3: Speed benchmark ───────────────────────────────────────────────────

BENCHMARK_PROMPTS = [
    ("Short", "What is CUDA?", 80),
    ("Medium", "Explain the difference between supervised and unsupervised learning.", 200),
    ("Long", "Write a detailed explanation of how transformer attention works, including the math.", 400),
]


def run_benchmark() -> None:
    """Measure tok/s for short, medium, and long responses."""
    console.print(
        Panel(
            f"[bold]Speed Benchmark[/bold]\n"
            f"[dim]Model: {MODEL} · Measuring tok/s for 3 response lengths[/dim]",
            border_style="green",
        )
    )

    client = ollama.Client(host=OLLAMA_HOST)
    bench_results = []

    for label, prompt, max_tokens in BENCHMARK_PROMPTS:
        console.print(f"\n[bold green]{label} response[/bold green] — {prompt}")

        messages = [
            {"role": "system", "content": "Answer concisely."},
            {"role": "user", "content": prompt},
        ]

        token_count = 0
        start = time.time()

        try:
            stream = client.chat(
                model=MODEL,
                messages=messages,
                stream=True,
                options={"num_predict": max_tokens},
            )
            for chunk in stream:
                console.print(chunk["message"]["content"], end="", markup=False)
                token_count += 1
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            continue

        elapsed = time.time() - start
        tps = token_count / elapsed if elapsed > 0 else 0.0
        bench_results.append((label, token_count, elapsed, tps))
        console.print(f"\n[dim]{token_count} tokens · {elapsed:.1f}s · {tps:.1f} tok/s[/dim]")

    # Results table
    console.print()
    table = Table(title="Benchmark Results", box=box.ROUNDED, border_style="green")
    table.add_column("Response Length", style="bold")
    table.add_column("Tokens", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("tok/s", justify="right", style="bold green")

    for label, tokens, elapsed, tps in bench_results:
        table.add_row(label, str(tokens), f"{elapsed:.1f}", f"{tps:.1f}")

    console.print(table)
    console.print(
        "[dim]Expected on Jetson AGX Orin MAXN: 22–28 tok/s for glm4:flash[/dim]"
    )


# ── CLI entry point ───────────────────────────────────────────────────────────

def print_usage() -> None:
    table = Table(
        title="GLM-4.7 Flash Chat Tool",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Mode", style="bold")
    table.add_column("Flag", style="green")
    table.add_column("Description")

    table.add_row("Conversation",  "--chat",          "Interactive multi-turn chat")
    table.add_row("Expert Mode",   "--expert <name>", "Chat as devops/ml/writer/analyst")
    table.add_row("Summarize",     "--summarize",     "Batch summarize 3 sample documents")
    table.add_row("Benchmark",     "--benchmark",     "Measure tok/s performance")
    table.add_row("List Experts",  "--experts",       "Show available expert personas")

    console.print(table)
    console.print(
        "\n[dim]Expert keys: default, devops, ml, writer, analyst[/dim]\n"
        "[dim]Example: python3 glm_chat.py --expert ml[/dim]"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="GLM-4.7 Flash fast chat tool")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--chat",      action="store_true", help="Interactive chat (default expert)")
    group.add_argument("--expert",    metavar="NAME",      help="Chat with a specific expert persona")
    group.add_argument("--summarize", action="store_true", help="Batch document summarization")
    group.add_argument("--benchmark", action="store_true", help="Speed benchmark (tok/s test)")
    group.add_argument("--experts",   action="store_true", help="List available expert personas")
    args = parser.parse_args()

    console.print(
        Panel(
            "[bold cyan]GLM-4.7 Flash Fast Chat[/bold cyan]\n"
            f"[dim]Model: {MODEL} via Ollama (Docker) · Jetson AGX Orin 64GB[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )

    if args.chat:
        run_conversation("default")
    elif args.expert:
        key = args.expert.lower()
        if key not in EXPERTS:
            console.print(f"[red]Unknown expert '{key}'. Available: {', '.join(EXPERTS)}[/red]")
            sys.exit(1)
        run_conversation(key)
    elif args.summarize:
        run_batch_summarization()
    elif args.benchmark:
        run_benchmark()
    elif args.experts:
        _print_experts_table()
    else:
        print_usage()


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/glm-flash
source venv/bin/activate

# Show all modes
python3 glm_chat.py

# Default interactive chat
python3 glm_chat.py --chat

# Start as ML expert directly
python3 glm_chat.py --expert ml

# Start as DevOps expert
python3 glm_chat.py --expert devops

# Batch summarization of 3 sample documents
python3 glm_chat.py --summarize

# Speed benchmark (measures tok/s for short/medium/long responses)
python3 glm_chat.py --benchmark

# List all expert personas
python3 glm_chat.py --experts
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Switch experts mid-session
Start a chat session and use the `/expert` command at runtime:

```bash
python3 glm_chat.py --chat
```

Then type these in sequence:
1. "What is Docker?" — answered by the default assistant
2. `/expert devops`  — switches to DevOps engineer persona
3. "What is Docker?" — now answered with practitioner-level detail
4. `/expert ml`      — switches to ML engineer
5. "How do I run PyTorch on Jetson?"

Notice how the same question gets meaningfully different answers from each persona.

### Exercise 2: Benchmark and compare
Run the benchmark, note the tok/s for each response length:

```bash
python3 glm_chat.py --benchmark
```

Then open `jtop` in another terminal and watch the GPU utilization during generation. Expected: GPU should hit 90–95% during inference on MAXN mode.

### Exercise 3: Add your own document to batch summarization
Edit `glm_chat.py` and add a 4th entry to `SAMPLE_DOCS`:

```python
{
    "title": "Your Document Title",
    "text": "Paste a long article or README here (500+ words for a good test)...",
},
```

Run `--summarize` and measure how long it takes per document.

### Exercise 4: Measure context window impact on speed
In `--chat` mode, have a long conversation (10+ exchanges). Watch how tok/s may slow slightly as the context grows. The 16-message cap in the code prevents runaway context growth — try changing it to 4 and 32 to observe the difference.

### Exercise 5: Custom expert persona
Add a new expert to the `EXPERTS` dict at the top of the script:

```python
"security": {
    "name": "Security Engineer",
    "system": (
        "You are a cybersecurity engineer specializing in Linux hardening, "
        "network security, and secure coding practices. Give actionable advice, "
        "reference CVEs when relevant, and always consider threat models."
    ),
    "color": "red",
},
```

Then test it with: `python3 glm_chat.py --expert security` and ask "How do I harden an Ubuntu server?"

---

## Expected Output

```
╭──────────────────────────────────────────────────╮
│  GLM-4.7 Flash Fast Chat                         │
│  Model: glm4:flash via Ollama (Docker)           │
╰──────────────────────────────────────────────────╯

╭─ ML Engineer ────────────────────────────────────╮
│  You are a machine learning engineer with deep   │
│  expertise in PyTorch, model optimization...     │
│  Commands: /expert <name> · /clear · /speed      │
╰──────────────────────────────────────────────────╯

You> How do I quantize a model for Jetson?

─────────────────── ML Engineer ────────────────────
For Jetson deployment, you have two main quantization
paths depending on your framework:

**1. TensorRT INT8/FP16 (native Jetson path)**
...
──────────── 312 tokens · 12.8s · 24.4 tok/s ───────
```

**Performance (MAXN, glm4:flash):** ~22–28 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `model "glm4:flash" not found` | `docker exec ollama ollama pull glm4:flash` |
| `Connection refused localhost:11434` | `docker start ollama` or check `docker ps` |
| Slow performance (<10 tok/s) | `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| `ModuleNotFoundError: rich` | `pip install ollama rich` inside venv |
| `/expert` command not recognized | Type exactly `/expert ml` with a space, not `--expert` |
| High memory usage | `docker stats ollama` — GLM Flash uses ~5GB VRAM |
| Model response is empty | Check `docker logs ollama` for OOM errors |

---

## Next Steps

- `qwen25-logic.md` — structured reasoning and decision analysis with Qwen2.5
- `gpt-oss.md` — step up to a 20B model for deeper, more nuanced responses
- `qwen3-rag.md` — add a knowledge base so the model answers from your documents
- `../../../phase-3-services/ollama-docker.md` — Ollama container management and model lifecycle
- `../../../../trucos-optimizacion-jetson.txt` — hardware tuning tips for maximum throughput
