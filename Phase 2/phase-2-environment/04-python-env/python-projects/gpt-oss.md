# gpt-oss:20b Versatile Assistant — Large-Model General-Purpose AI on Jetson

Build a full-featured assistant powered by `gpt-oss:20b` running in the Ollama Docker container. At 20 billion parameters this is a significantly more capable model than the 7B options — it produces richer analysis, more coherent long-form text, and higher-quality code. On Jetson AGX Orin in MAXN mode it sustains ~10–12 tok/s, a comfortable speed for interactive use. This project builds a streaming assistant with persistent conversation history, a dedicated code generation mode, a research/analysis mode, and a task-planning mode.

---

## What You'll Learn

- How to work with a large (20B) model's slower but higher-quality output via streaming
- Building a multi-mode CLI that routes to specialized prompting strategies
- Implementing persistent conversation history saved to disk between sessions
- Code generation with automatic language detection and syntax-highlighted output
- Research/analysis mode that structures responses as structured reports
- Task decomposition and project planning with an AI planner

## Prerequisites

```bash
# Ensure Ollama container is running
docker ps | grep ollama

# Pull gpt-oss:20b (this is a large model — ~12GB download, takes several minutes)
docker exec ollama ollama pull gpt-oss:20b

# Verify
docker exec ollama ollama list
```

```bash
# CRITICAL: Set MAXN before running the 20B model
sudo nvpmodel -m 0
sudo jetson_clocks

# Confirm MAXN is active
sudo nvpmodel -q
```

> **Memory note:** gpt-oss:20b at Q4_K_M quantization uses approximately 12–13GB of the Jetson's
> unified memory. With JetPack 6.2.2's unified memory architecture this is fine on the 64GB model.
> Monitor with `jtop` if you experience slowdowns.

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/gpt-oss
cd ~/projects/gpt-oss
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Versatile Assistant

Save as `~/projects/gpt-oss/assistant.py`:

```python
#!/usr/bin/env python3
"""
gpt-oss:20b Versatile Assistant
Multi-mode AI assistant with streaming chat, code generation, research analysis,
and task planning. Uses Ollama Docker container (port 11434).
Jetson AGX Orin 64GB · JetPack 6.2.2 · CUDA 12.6
Target: ~10-12 tok/s on MAXN mode.
"""

import time
import sys
import json
import argparse
from pathlib import Path
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.rule import Rule
from rich.markdown import Markdown
from rich import box

console = Console()

MODEL = "gpt-oss:20b"
OLLAMA_HOST = "http://localhost:11434"
HISTORY_FILE = Path.home() / ".gpt_oss_history.json"

# ── System prompts ────────────────────────────────────────────────────────────

SYSTEM_CHAT = """You are a knowledgeable, thoughtful AI assistant. You give accurate,
well-reasoned answers. When you are uncertain, you say so. You adapt your communication
style to the user — technical when they are technical, accessible when they are not.
For complex topics, use structured responses with headers and bullet points."""

SYSTEM_CODE = """You are an expert software engineer. When asked to write code:
1. Write complete, runnable code — no placeholders or stubs.
2. Include brief inline comments for non-obvious logic.
3. Start with the language identifier on the first line (e.g., ```python).
4. After the code block, add a short explanation of how it works.
5. Note any dependencies the user needs to install.
For Jetson/CUDA code, use sm_87 architecture and CUDA 12.6 conventions."""

SYSTEM_RESEARCH = """You are a research analyst. When given a topic:
1. Write a structured analysis with these sections:
   ## Overview — 2-3 sentence summary
   ## Key Concepts — bullet list of the most important ideas
   ## Current State — what is the state of the art / current situation
   ## Tradeoffs & Considerations — pros, cons, important nuances
   ## Practical Implications — what should someone actually do with this knowledge
2. Be precise with technical details. Cite well-known sources by name when relevant.
3. Flag anything where your knowledge may be outdated (cutoff: early 2025)."""

SYSTEM_PLANNER = """You are a project planning expert. When given a goal or project:
1. Break it into phases (Phase 1, Phase 2, ...).
2. Within each phase list concrete, actionable tasks (numbered).
3. For each task estimate effort: S (< 2h), M (2-8h), L (1-3d), XL (> 3d).
4. Identify dependencies between tasks.
5. Flag the top 3 risks with mitigation strategies.
6. Estimate total timeline (realistic, not optimistic).
Keep the plan practical and specific to what was described."""


# ── History management ────────────────────────────────────────────────────────

def load_history() -> list:
    """Load conversation history from disk."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history: list) -> None:
    """Save conversation history to disk."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except IOError as e:
        console.print(f"[yellow]Warning: could not save history: {e}[/yellow]")


def clear_history() -> None:
    """Delete saved history file."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()


# ── Core streaming function ───────────────────────────────────────────────────

def stream_response(
    prompt: str,
    system: str,
    history: Optional[list] = None,
    title: str = "gpt-oss:20b",
    color: str = "cyan",
    max_tokens: int = 2048,
) -> tuple[str, float]:
    """
    Stream a response from gpt-oss:20b via Ollama.
    Returns (full_text, tok_per_sec).
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
        stream = client.chat(
            model=MODEL,
            messages=messages,
            stream=True,
            options={"num_predict": max_tokens},
        )
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
        console.print("[yellow]Check:[/yellow] docker ps | grep ollama")
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


# ── Mode 1: Streaming chat with persistent history ───────────────────────────

def run_chat(resume: bool = False) -> None:
    """
    Interactive multi-turn chat with optional disk-persisted history.
    """
    history: list = load_history() if resume else []

    if resume and history:
        console.print(
            f"[dim]Resumed session with {len(history) // 2} previous exchanges.[/dim]"
        )
    elif resume:
        console.print("[dim]No previous session found. Starting fresh.[/dim]")

    console.print(
        Panel(
            "[bold cyan]gpt-oss:20b Chat[/bold cyan]\n"
            "[dim]20B parameter model — richer, more nuanced responses (~10-12 tok/s)\n\n"
            "Commands: [bold]/save[/bold] save history · [bold]/load[/bold] load saved session · "
            "[bold]/clear[/bold] clear history · [bold]/history[/bold] show session · "
            "[bold]/quit[/bold] exit[/dim]",
            border_style="cyan",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold cyan]You>[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            _offer_save(history)
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            _offer_save(history)
            break

        if user_input.lower() == "/clear":
            history.clear()
            clear_history()
            console.print("[yellow]History cleared and deleted from disk.[/yellow]")
            continue

        if user_input.lower() == "/save":
            save_history(history)
            console.print(f"[green]History saved to {HISTORY_FILE}[/green]")
            continue

        if user_input.lower() == "/load":
            loaded = load_history()
            if loaded:
                history = loaded
                console.print(f"[green]Loaded {len(history) // 2} exchanges from disk.[/green]")
            else:
                console.print("[yellow]No saved history found.[/yellow]")
            continue

        if user_input.lower() == "/history":
            _print_history_summary(history)
            continue

        response, _ = stream_response(
            user_input,
            SYSTEM_CHAT,
            history=history,
            title="Assistant",
            color="cyan",
        )

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})

        # Keep last 20 messages to manage context size
        if len(history) > 20:
            history = history[-20:]


def _offer_save(history: list) -> None:
    if not history:
        return
    try:
        answer = console.input(
            f"\n[dim]Save {len(history) // 2} exchanges to disk? (y/N) [/dim]"
        ).strip().lower()
        if answer == "y":
            save_history(history)
            console.print(f"[green]Saved to {HISTORY_FILE}[/green]")
    except (KeyboardInterrupt, EOFError):
        pass


def _print_history_summary(history: list) -> None:
    if not history:
        console.print("[dim]No history in current session.[/dim]")
        return
    table = Table(title="Session History", box=box.SIMPLE_HEAD, border_style="dim")
    table.add_column("#", style="dim", width=3)
    table.add_column("Role", width=12)
    table.add_column("Content (truncated)", max_width=60)
    for i, msg in enumerate(history, 1):
        content_short = msg["content"][:80].replace("\n", " ")
        table.add_row(str(i), msg["role"], content_short)
    console.print(table)


# ── Mode 2: Code generation ───────────────────────────────────────────────────

LANG_EXTENSIONS = {
    "python": "py", "javascript": "js", "typescript": "ts",
    "bash": "sh", "go": "go", "rust": "rs", "c": "c",
    "cpp": "cpp", "java": "java", "sql": "sql",
}


def run_code_generation() -> None:
    """Interactive code generation with syntax-highlighted output."""
    console.print(
        Panel(
            "[bold green]Code Generation Mode[/bold green]\n"
            "[dim]Describe what you want to build. Specify language (optional).\n"
            "Examples:\n"
            "  'Write a Python async HTTP client with retry logic'\n"
            "  'Bash script to monitor GPU memory and alert at 80%'\n"
            "  'C++ function to compute cosine similarity of float vectors'\n\n"
            "Commands: [bold]/quit[/bold] exit[/dim]",
            border_style="green",
        )
    )

    while True:
        try:
            task = console.input("\n[bold green]Task>[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting code mode.[/dim]")
            break

        if not task:
            continue
        if task.lower() in ("/quit", "/exit", "quit", "exit"):
            break

        response, tps = stream_response(
            task,
            SYSTEM_CODE,
            title="Code Generator",
            color="green",
            max_tokens=2048,
        )

        # Extract and syntax-highlight code blocks
        _highlight_code_blocks(response)

        console.print(f"[dim]Throughput: {tps:.1f} tok/s[/dim]")


def _highlight_code_blocks(text: str) -> None:
    """Find ```lang ... ``` blocks and re-render them with rich Syntax."""
    import re
    pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    matches = list(pattern.finditer(text))

    if not matches:
        return  # Already printed raw; nothing extra to do

    console.print()
    console.print(Rule("[green]Highlighted Code[/green]"))
    for match in matches:
        lang = match.group(1) or "text"
        code = match.group(2)
        try:
            syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
            console.print(syntax)
        except Exception:
            console.print(code)


# ── Mode 3: Research / analysis ──────────────────────────────────────────────

def run_research() -> None:
    """Research mode: structured analysis reports with markdown rendering."""
    console.print(
        Panel(
            "[bold yellow]Research & Analysis Mode[/bold yellow]\n"
            "[dim]Enter any topic. Get a structured analysis report.\n"
            "Examples:\n"
            "  'Quantization techniques for large language models'\n"
            "  'Edge AI vs cloud AI: tradeoffs for IoT deployments'\n"
            "  'CUDA unified memory on Jetson AGX Orin'\n\n"
            "Commands: [bold]/quit[/bold] exit[/dim]",
            border_style="yellow",
        )
    )

    while True:
        try:
            topic = console.input("\n[bold yellow]Topic>[/bold yellow] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting research mode.[/dim]")
            break

        if not topic:
            continue
        if topic.lower() in ("/quit", "/exit", "quit", "exit"):
            break

        response, tps = stream_response(
            f"Research topic: {topic}",
            SYSTEM_RESEARCH,
            title="Research Analysis",
            color="yellow",
            max_tokens=1500,
        )

        # Re-render as markdown for clean formatting
        console.print()
        console.print(Rule("[yellow]Formatted Report[/yellow]"))
        try:
            console.print(Markdown(response))
        except Exception:
            pass  # Already printed raw above

        console.print(f"[dim]Throughput: {tps:.1f} tok/s[/dim]")


# ── Mode 4: Task planning ─────────────────────────────────────────────────────

def run_planner() -> None:
    """Task decomposition and project planning mode."""
    console.print(
        Panel(
            "[bold blue]Task Planning Mode[/bold blue]\n"
            "[dim]Describe a project or goal. Get a phased plan with effort estimates.\n"
            "Examples:\n"
            "  'Build a RAG chatbot for company documentation'\n"
            "  'Set up a Jetson Orin as an edge AI inference server'\n"
            "  'Learn Rust from scratch, I know Python'\n\n"
            "Commands: [bold]/quit[/bold] exit[/dim]",
            border_style="blue",
        )
    )

    while True:
        try:
            goal = console.input("\n[bold blue]Goal>[/bold blue] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting planner.[/dim]")
            break

        if not goal:
            continue
        if goal.lower() in ("/quit", "/exit", "quit", "exit"):
            break

        response, tps = stream_response(
            f"Create a project plan for: {goal}",
            SYSTEM_PLANNER,
            title="Project Planner",
            color="blue",
            max_tokens=1500,
        )

        # Re-render as markdown
        console.print()
        console.print(Rule("[blue]Project Plan[/blue]"))
        try:
            console.print(Markdown(response))
        except Exception:
            pass

        console.print(f"[dim]Throughput: {tps:.1f} tok/s[/dim]")


# ── Mode 5: Single-shot quick query ──────────────────────────────────────────

def run_ask(query: str) -> None:
    """Non-interactive single query — useful for scripting."""
    response, tps = stream_response(
        query,
        SYSTEM_CHAT,
        title="gpt-oss:20b",
        color="cyan",
    )
    console.print(f"\n[dim]Throughput: {tps:.1f} tok/s[/dim]")


# ── Help display ──────────────────────────────────────────────────────────────

def print_menu() -> None:
    table = Table(
        title=f"gpt-oss:20b Versatile Assistant",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Mode", style="bold")
    table.add_column("Flag", style="green")
    table.add_column("Description")

    table.add_row("Chat",     "--chat",         "Streaming chat with persistent history (~10-12 tok/s)")
    table.add_row("Resume",   "--resume",       "Load previous session and continue")
    table.add_row("Code",     "--code",         "Code generation with syntax highlighting")
    table.add_row("Research", "--research",     "Structured research & analysis reports")
    table.add_row("Plan",     "--plan",         "Project/task planning with effort estimates")
    table.add_row("Ask",      "--ask 'query'",  "Single non-interactive query")

    console.print(table)
    console.print(
        f"\n[dim]Model: {MODEL} · ~10-12 tok/s on Jetson AGX Orin MAXN[/dim]\n"
        f"[dim]History file: {HISTORY_FILE}[/dim]"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="gpt-oss:20b versatile assistant")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--chat",     action="store_true", help="Interactive streaming chat")
    group.add_argument("--resume",   action="store_true", help="Resume saved chat session")
    group.add_argument("--code",     action="store_true", help="Code generation mode")
    group.add_argument("--research", action="store_true", help="Research & analysis mode")
    group.add_argument("--plan",     action="store_true", help="Task/project planning mode")
    group.add_argument("--ask",      metavar="QUERY",     help="Single query (non-interactive)")
    args = parser.parse_args()

    console.print(
        Panel(
            "[bold cyan]gpt-oss:20b Versatile Assistant[/bold cyan]\n"
            "[dim]20B parameters · Ollama Docker container · Jetson AGX Orin 64GB[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )

    if args.chat:
        run_chat(resume=False)
    elif args.resume:
        run_chat(resume=True)
    elif args.code:
        run_code_generation()
    elif args.research:
        run_research()
    elif args.plan:
        run_planner()
    elif args.ask:
        run_ask(args.ask)
    else:
        print_menu()


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/gpt-oss
source venv/bin/activate

# Show all modes
python3 assistant.py

# Start a new chat session
python3 assistant.py --chat

# Resume a previously saved session
python3 assistant.py --resume

# Code generation mode
python3 assistant.py --code

# Research/analysis mode
python3 assistant.py --research

# Project planning mode
python3 assistant.py --plan

# Quick single query (useful in scripts)
python3 assistant.py --ask "What are the tradeoffs of INT8 vs FP16 quantization?"
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Persistent conversation across sessions
Start a chat, build a multi-turn conversation, then save it:

```bash
python3 assistant.py --chat
```

Ask 3 follow-up questions about one topic. Then type `/save`. Exit and run:

```bash
python3 assistant.py --resume
```

Confirm that the model remembers all previous exchanges and can continue the thread.

### Exercise 2: Compare 20B vs 7B output quality
Run the same complex prompt on gpt-oss:20b and on qwen2.5:7b (from the `qwen25-logic` project). Use this prompt for both:

```
Explain the vanishing gradient problem in deep learning, why it occurs,
and describe three techniques used to mitigate it with their tradeoffs.
```

Compare the depth and accuracy of the two responses. The 20B model should produce noticeably more comprehensive coverage.

### Exercise 3: Code generation for a Jetson-specific task
Run `--code` and enter:

```
Write a Python script that monitors Jetson GPU memory using tegrastats,
logs readings every 5 seconds to a CSV file, and prints an alert to the
terminal if usage exceeds 80%.
```

The 20B model should produce a complete, runnable script. Test it by actually running it.

### Exercise 4: Research mode deep dive
Run `--research` and query:

```
TensorRT optimization for transformer models on Jetson AGX Orin
```

Observe the structured report format (Overview, Key Concepts, Current State, Tradeoffs, Implications). Save the output to a markdown file:

```bash
python3 assistant.py --ask "TensorRT optimization for transformer models on Jetson" > tensorrt_research.md
```

### Exercise 5: Plan a real project
Run `--plan` and enter a project you actually want to do:

```
Build a local voice assistant on Jetson that uses Whisper for speech-to-text,
an LLM for responses, and Piper TTS for speech output. I have Docker installed
and the Jetson is already set up with JetPack 6.2.2.
```

Compare the model's plan to the guide in `experiment_llm_nvidia.md`. How accurate is it?

---

## Expected Output

```
╭─────────────────────────────────────────────────────────╮
│  gpt-oss:20b Versatile Assistant                        │
│  20B parameters · Ollama Docker · Jetson AGX Orin 64GB  │
╰─────────────────────────────────────────────────────────╯

You> What is the difference between CUDA streams and CUDA graphs?

──────────────────── Assistant ──────────────────────────────
**CUDA Streams** and **CUDA Graphs** are both mechanisms for managing
GPU execution, but they operate at different levels of abstraction:

**CUDA Streams**
A stream is a queue of GPU operations that execute in order...
[continues for ~400 tokens]

──────── 418 tokens · 39.2s · 10.7 tok/s ───────────────────
```

**Performance (MAXN, gpt-oss:20b):** ~10–12 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `model "gpt-oss:20b" not found` | `docker exec ollama ollama pull gpt-oss:20b` |
| Pull takes very long | Normal — 20B model is ~12GB; check progress with `docker logs -f ollama` |
| `Connection refused localhost:11434` | `docker start ollama` |
| Very slow output (<5 tok/s) | `sudo nvpmodel -m 0 && sudo jetson_clocks` — verify with `sudo nvpmodel -q` |
| OOM / model crash | `jtop` to check RAM; close other processes; ensure 50GB swap is enabled |
| History file corrupt | `rm ~/.gpt_oss_history.json` |
| Code blocks not highlighted | Normal on first print; highlighted version appears after |
| `ModuleNotFoundError: rich` | `source venv/bin/activate && pip install ollama rich` |

---

## Next Steps

- `qwen25-logic.md` — focused logical reasoning with a leaner 7B model
- `glm-flash.md` — switch to GLM Flash when you need speed over depth
- `qwen3-rag.md` — augment the 20B model with a document knowledge base via RAG
- `../../../../expand_swap_file.md` — set up 50GB swap if running 120B+ models
- `../../../../use_jetson_as_local_ai_server.md` — expose this assistant over the network
