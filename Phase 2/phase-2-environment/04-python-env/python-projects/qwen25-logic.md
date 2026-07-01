# Qwen2.5 Logic Engine — Structured Reasoning and Decision Analysis

Build a command-line logic and decision-making tool powered by Qwen2.5:7b running in the Ollama Docker container. This project teaches you to harness a capable instruction-tuned model for structured reasoning tasks: deductive logic, pros/cons analysis, decision trees, syllogism validation, and multi-scenario planning — all with real-time streaming output.

---

## What You'll Learn

- How to call the Ollama Python SDK against a Dockerized Ollama service
- Streaming responses token-by-token with live tok/s display using `rich`
- Designing multi-mode CLI tools that route prompts to specialized system prompts
- Structured output techniques: forcing the model to produce numbered steps, trees, and scored lists
- Prompt engineering for logical deduction and argument validation
- Managing conversation history for multi-turn reasoning sessions

## Prerequisites

```bash
# Ensure Ollama container is running
docker ps | grep ollama

# Pull the model (Ollama runs in Docker — always use docker exec)
docker exec ollama ollama pull qwen2.5:7b

# Verify it loaded
docker exec ollama ollama list
```

```bash
# Set MAXN performance mode before any inference session
sudo nvpmodel -m 0
sudo jetson_clocks
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/qwen25-logic
cd ~/projects/qwen25-logic
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Logic Engine

Save as `~/projects/qwen25-logic/logic_engine.py`:

```python
#!/usr/bin/env python3
"""
Qwen2.5 Logic Engine
Structured reasoning and decision-analysis tool for Jetson AGX Orin.
Uses Ollama Docker container (port 11434) with streaming output.
"""

import time
import sys
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

console = Console()

MODEL = "qwen2.5:7b"
OLLAMA_HOST = "http://localhost:11434"

# ── System prompts for each reasoning mode ──────────────────────────────────

SYSTEM_DEDUCE = """You are a precise logical reasoning engine. When given a problem:
1. Identify all given premises clearly (label them P1, P2, ...).
2. Apply logical rules step by step (label each inference step).
3. State the conclusion explicitly.
4. Rate your confidence (High / Medium / Low) and explain why.
Always be explicit about which premises support each inference step."""

SYSTEM_PROS_CONS = """You are a balanced decision analyst. When given a decision or topic:
1. List PROS — number each one, estimate impact (High/Medium/Low).
2. List CONS — number each one, estimate impact (High/Medium/Low).
3. Provide a weighted RECOMMENDATION with a score out of 10.
4. Name the single biggest risk and the single biggest opportunity.
Be concrete and practical, not vague."""

SYSTEM_DECISION_TREE = """You are a decision-tree architect. When given a scenario:
1. Identify the root decision node.
2. List 2–4 main branches (choices or events).
3. For each branch list 2–3 sub-outcomes.
4. Mark each leaf as GOOD / NEUTRAL / BAD with a brief reason.
Format the tree using indented ASCII art with → arrows."""

SYSTEM_SYLLOGISM = """You are a formal logic validator. When given an argument:
1. Extract the major premise, minor premise, and conclusion.
2. Identify the logical form (e.g., Modus Ponens, Modus Tollens, Syllogism).
3. Check for fallacies (affirming the consequent, undistributed middle, etc.).
4. Verdict: VALID or INVALID, with a one-sentence explanation.
5. If invalid, rewrite it as a corrected valid argument."""

SYSTEM_SCENARIO = """You are a strategic foresight analyst. When given a situation:
1. Define the current state clearly.
2. Describe BEST CASE scenario (optimistic, realistic probability %).
3. Describe BASE CASE scenario (most likely, probability %).
4. Describe WORST CASE scenario (pessimistic, probability %).
5. For each scenario: list 2 key drivers and 1 recommended action.
Keep probabilities summing to ~100%."""

SYSTEM_CHAT = """You are a helpful logical reasoning assistant. Think carefully before
answering. When appropriate, use numbered steps, structured lists, and clear conclusions.
Acknowledge uncertainty when you are unsure."""


# ── Core streaming function ──────────────────────────────────────────────────

def stream_response(
    prompt: str,
    system: str,
    history: Optional[list] = None,
    title: str = "Response",
) -> str:
    """Stream a response from Qwen2.5 via Ollama, printing tokens live."""
    client = ollama.Client(host=OLLAMA_HOST)

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    console.print(Rule(f"[bold cyan]{title}[/bold cyan]"))

    full_text = ""
    token_count = 0
    start = time.time()

    try:
        stream = client.chat(
            model=MODEL,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk["message"]["content"]
            full_text += delta
            token_count += 1
            console.print(delta, end="", markup=False)

    except ollama.ResponseError as e:
        console.print(f"\n[red]Ollama error: {e}[/red]")
        console.print("[yellow]Is the model pulled? Run:[/yellow]")
        console.print("  docker exec ollama ollama pull qwen2.5:7b")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Connection error: {e}[/red]")
        console.print("[yellow]Is the Ollama container running?[/yellow]")
        console.print("  docker ps | grep ollama")
        sys.exit(1)

    elapsed = time.time() - start
    toks_per_sec = token_count / elapsed if elapsed > 0 else 0

    console.print()
    console.print(
        Rule(
            f"[dim]{token_count} tokens · {elapsed:.1f}s · "
            f"[bold green]{toks_per_sec:.1f} tok/s[/bold green][/dim]"
        )
    )
    return full_text


# ── Mode functions ────────────────────────────────────────────────────────────

def run_deduction(problem: str) -> str:
    console.print(
        Panel(
            f"[bold]{problem}[/bold]",
            title="[cyan]Logical Deduction Problem[/cyan]",
            border_style="cyan",
        )
    )
    return stream_response(problem, SYSTEM_DEDUCE, title="Step-by-Step Deduction")


def run_pros_cons(topic: str) -> str:
    console.print(
        Panel(
            f"[bold]{topic}[/bold]",
            title="[green]Pros / Cons Analysis[/green]",
            border_style="green",
        )
    )
    return stream_response(topic, SYSTEM_PROS_CONS, title="Pros & Cons")


def run_decision_tree(scenario: str) -> str:
    console.print(
        Panel(
            f"[bold]{scenario}[/bold]",
            title="[yellow]Decision Tree Builder[/yellow]",
            border_style="yellow",
        )
    )
    return stream_response(scenario, SYSTEM_DECISION_TREE, title="Decision Tree")


def run_syllogism(argument: str) -> str:
    console.print(
        Panel(
            f"[bold]{argument}[/bold]",
            title="[magenta]Syllogism Validator[/magenta]",
            border_style="magenta",
        )
    )
    return stream_response(argument, SYSTEM_SYLLOGISM, title="Validity Check")


def run_scenario_planning(situation: str) -> str:
    console.print(
        Panel(
            f"[bold]{situation}[/bold]",
            title="[blue]Scenario Planning[/blue]",
            border_style="blue",
        )
    )
    return stream_response(situation, SYSTEM_SCENARIO, title="Scenario Analysis")


def run_chat_mode() -> None:
    """Interactive multi-turn chat with conversation history."""
    history: list = []

    console.print(
        Panel(
            "[bold cyan]Logic Assistant Chat[/bold cyan]\n"
            "[dim]Multi-turn conversation with reasoning focus.\n"
            "Commands: [bold]/clear[/bold] reset history · [bold]/quit[/bold] exit[/dim]",
            border_style="cyan",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold green]You>[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting chat.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if user_input.lower() == "/clear":
            history.clear()
            console.print("[yellow]History cleared.[/yellow]")
            continue

        response = stream_response(
            user_input,
            SYSTEM_CHAT,
            history=history,
            title="Assistant",
        )
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})

        # Keep last 10 exchanges (20 messages) to avoid context overflow
        if len(history) > 20:
            history = history[-20:]


# ── Help / menu ───────────────────────────────────────────────────────────────

def print_menu() -> None:
    table = Table(
        title="Qwen2.5 Logic Engine — Modes",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Mode", style="bold")
    table.add_column("Flag", style="green")
    table.add_column("Description")

    table.add_row("Deduction",       "--deduce",   "Step-by-step logical deduction from premises")
    table.add_row("Pros & Cons",     "--pros",     "Weighted pros/cons with recommendation score")
    table.add_row("Decision Tree",   "--tree",     "ASCII decision tree with outcome ratings")
    table.add_row("Syllogism Check", "--syllogism","Formal validity check with fallacy detection")
    table.add_row("Scenario Plan",   "--scenario", "Best/base/worst case scenario planning")
    table.add_row("Chat",            "--chat",     "Multi-turn reasoning conversation")

    console.print(table)
    console.print()
    console.print(
        "Usage examples:\n"
        "  [cyan]python3 logic_engine.py --deduce[/cyan]\n"
        "  [cyan]python3 logic_engine.py --pros[/cyan]\n"
        "  [cyan]python3 logic_engine.py --tree[/cyan]\n"
        "  [cyan]python3 logic_engine.py --syllogism[/cyan]\n"
        "  [cyan]python3 logic_engine.py --scenario[/cyan]\n"
        "  [cyan]python3 logic_engine.py --chat[/cyan]"
    )


# ── Prompts for demo mode ─────────────────────────────────────────────────────

DEMO_PROMPTS = {
    "deduce": (
        "All mammals are warm-blooded. All whales are mammals. "
        "Whales live in the ocean. Therefore, what can we conclude "
        "about whales and warm-bloodedness? Is this a valid chain of reasoning?"
    ),
    "pros": (
        "Should I migrate my application from a monolithic architecture "
        "to microservices? The app currently handles 10k requests/day "
        "and has a team of 4 developers."
    ),
    "tree": (
        "I am deciding whether to start a new SaaS product. "
        "I have limited funding (6 months runway), some technical skills, "
        "and an unvalidated idea. Build a decision tree for this scenario."
    ),
    "syllogism": (
        "Premise 1: If it rains, the ground gets wet. "
        "Premise 2: The ground is wet. "
        "Conclusion: Therefore it rained. "
        "Is this argument valid?"
    ),
    "scenario": (
        "My startup is launching a hardware product in 3 months. "
        "We have a manufacturer but no pre-orders yet. "
        "Plan out best, base, and worst case scenarios for launch."
    ),
}


# ── Main entry point ──────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Qwen2.5 Logic Engine — structured reasoning on Jetson"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--deduce",    action="store_true", help="Logical deduction mode")
    group.add_argument("--pros",      action="store_true", help="Pros/cons analysis mode")
    group.add_argument("--tree",      action="store_true", help="Decision tree mode")
    group.add_argument("--syllogism", action="store_true", help="Syllogism validation mode")
    group.add_argument("--scenario",  action="store_true", help="Scenario planning mode")
    group.add_argument("--chat",      action="store_true", help="Interactive chat mode")
    group.add_argument("--demo",      action="store_true", help="Run all demo prompts")
    args = parser.parse_args()

    console.print(
        Panel(
            "[bold cyan]Qwen2.5 Logic Engine[/bold cyan]\n"
            "[dim]Model: qwen2.5:7b via Ollama (Docker) · Jetson AGX Orin 64GB[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )

    if args.deduce:
        prompt = console.input("[bold]Enter logical problem:[/bold] ").strip()
        if not prompt:
            prompt = DEMO_PROMPTS["deduce"]
        run_deduction(prompt)

    elif args.pros:
        prompt = console.input("[bold]Enter decision/topic for pros-cons:[/bold] ").strip()
        if not prompt:
            prompt = DEMO_PROMPTS["pros"]
        run_pros_cons(prompt)

    elif args.tree:
        prompt = console.input("[bold]Enter scenario for decision tree:[/bold] ").strip()
        if not prompt:
            prompt = DEMO_PROMPTS["tree"]
        run_decision_tree(prompt)

    elif args.syllogism:
        prompt = console.input("[bold]Enter argument to validate:[/bold] ").strip()
        if not prompt:
            prompt = DEMO_PROMPTS["syllogism"]
        run_syllogism(prompt)

    elif args.scenario:
        prompt = console.input("[bold]Enter situation for scenario planning:[/bold] ").strip()
        if not prompt:
            prompt = DEMO_PROMPTS["scenario"]
        run_scenario_planning(prompt)

    elif args.chat:
        run_chat_mode()

    elif args.demo:
        console.print("[bold yellow]Running all demo prompts...[/bold yellow]\n")
        run_deduction(DEMO_PROMPTS["deduce"])
        console.print()
        run_pros_cons(DEMO_PROMPTS["pros"])
        console.print()
        run_syllogism(DEMO_PROMPTS["syllogism"])

    else:
        print_menu()


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/qwen25-logic
source venv/bin/activate

# Show available modes
python3 logic_engine.py

# Logical deduction (enter a problem when prompted, or press Enter for demo)
python3 logic_engine.py --deduce

# Pros/cons analysis
python3 logic_engine.py --pros

# Decision tree
python3 logic_engine.py --tree

# Syllogism validation
python3 logic_engine.py --syllogism

# Scenario planning
python3 logic_engine.py --scenario

# Interactive multi-turn chat
python3 logic_engine.py --chat

# Run all demos at once
python3 logic_engine.py --demo
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Chain of deduction
Run `--deduce` and enter this problem:

```
All programmers who know CUDA can write GPU kernels.
Sergi knows CUDA. Maria does not know CUDA but knows PyTorch.
Can either of them write GPU kernels?
```

Expected: the model should produce labelled premises P1/P2/P3, draw conclusions for Sergi (yes) and Maria (no/uncertain), and explain the logical chain.

### Exercise 2: Real decision analysis
Run `--pros` and enter a decision you actually face — for example:

```
Should I use Ollama or llama.cpp directly as my inference backend
for a local AI assistant project on Jetson?
```

Observe how the model weights impacts and produces a scored recommendation. Compare its score to your own intuition.

### Exercise 3: Spot the fallacy
Run `--syllogism` and test this deliberately invalid argument:

```
Premise 1: All fast cars are red.
Premise 2: My car is red.
Conclusion: Therefore my car is fast.
```

The model should identify this as "Affirming the Consequent" (invalid) and rewrite it as a valid form.

Then test a valid one:
```
Premise 1: All Python scripts end in .py.
Premise 2: main.py is a Python script.
Conclusion: Therefore main.py ends in .py.
```

### Exercise 4: Scenario planning for a Jetson project
Run `--scenario` and enter:

```
I am building an edge AI product using Jetson AGX Orin.
The device costs $500 per unit. My target market is industrial
inspection. I plan to sell 50 units in the first year.
```

Note how the model assigns probabilities and identifies key drivers per scenario.

### Exercise 5: Multi-turn reasoning session
Run `--chat` and have a three-turn exchange:

- Turn 1: "What is the frame problem in AI planning?"
- Turn 2: "How does modern deep learning handle this compared to classical AI?"
- Turn 3: "Give me a concrete example from robotics."

Observe that the model maintains context across all three turns, building on each previous answer.

---

## Expected Output

```
╭─────────────────────────────────────────────────────────╮
│           Qwen2.5 Logic Engine                          │
│   Model: qwen2.5:7b via Ollama (Docker) · Jetson AGX   │
╰─────────────────────────────────────────────────────────╯

╭─ Logical Deduction Problem ─────────────────────────────╮
│  All mammals are warm-blooded. All whales are mammals.  │
╰─────────────────────────────────────────────────────────╯
──────────────────── Step-by-Step Deduction ─────────────────────
P1: All mammals are warm-blooded.
P2: All whales are mammals.

Step 1: From P2, whales belong to the set of mammals.
Step 2: From P1, all members of the mammal set are warm-blooded.
Step 3: By transitivity (universal instantiation), whales are warm-blooded.

Conclusion: Whales are warm-blooded.
Form: Universal Syllogism (Barbara form) — VALID.
Confidence: High — both premises are well-established biological facts.
──────────── 187 tokens · 11.4s · 16.4 tok/s ────────────
```

**Performance (MAXN, qwen2.5:7b):** ~15–18 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection refused` on port 11434 | `docker ps | grep ollama` — start container if missing |
| `model not found: qwen2.5:7b` | `docker exec ollama ollama pull qwen2.5:7b` |
| Very slow output (<5 tok/s) | `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| `ModuleNotFoundError: ollama` | `source venv/bin/activate && pip install ollama rich` |
| Output cuts off mid-sentence | Model hit token limit; the demo prompts are sized to fit |
| Docker container not starting | `docker start ollama` or check `docker logs ollama` |

---

## Next Steps

- `glm-flash.md` — ultra-fast inference with GLM-4.7 Flash for rapid-fire queries
- `gpt-oss.md` — scale up to a 20B model for more complex reasoning tasks
- `qwen3-rag.md` — combine embeddings with a reasoning LLM for document Q&A
- `../../../phase-3-services/ollama-docker.md` — Ollama container management
- `../../../../experiment_llm_nvidia.md` — full voice + vision + LLM Docker stack
