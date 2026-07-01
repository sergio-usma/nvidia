# OpenThinker — Visible Chain-of-Thought Reasoning

OpenThinker is an open-source reasoning model that "thinks out loud" — it exposes its chain-of-thought process before giving a final answer. This makes it ideal for complex logical puzzles, strategic decisions, and problems that require multi-step reasoning. You can watch it reason in real time.

---

## What You'll Learn

- What chain-of-thought (CoT) prompting is and why it improves accuracy
- How reasoning models differ from standard chat models
- Extracting the `<think>...</think>` reasoning block from model output
- Building a structured debate tool: argue both sides of an issue

## Why Chain-of-Thought Matters

Standard model: `Input → Answer`
CoT model: `Input → [Reasoning steps...] → Answer`

The reasoning step forces the model to "work through" the problem rather than guessing, dramatically improving accuracy on:
- Logic puzzles and math word problems
- Multi-step decision making
- Argument analysis and debate

## Prerequisites

```bash
# Pull the model (~4.5 GB for 7b variant)
docker exec ollama ollama pull openthinker:7b

# Check what's available
docker exec ollama ollama list | grep thinker
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/openthinker
cd ~/projects/openthinker
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Reasoning Engine

Save as `~/projects/openthinker/openthinker.py`:

```python
#!/usr/bin/env python3
"""
OpenThinker — Visible Chain-of-Thought Reasoning Engine
Watch the model think through complex problems step by step.

What makes this special:
- <think>...</think> blocks show internal reasoning
- Final answer is distilled from the reasoning chain
- Two-phase output: thinking (internal) + answer (for user)
- Useful for problems where the reasoning is as important as the answer
"""
import time
import re
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

console = Console()

# Use openthinker:7b, or fall back to a model with CoT capabilities
MODEL = "openthinker:7b"

# Temperature settings for reasoning tasks
TEMP_LOGIC = 0.3      # Low for deterministic logical reasoning
TEMP_DEBATE = 0.6     # Higher for creative argument generation
TEMP_ANALYSIS = 0.4   # Medium for analytical tasks


def split_thinking(text: str) -> tuple[str, str]:
    """
    Split model output into thinking block and final answer.
    Models like OpenThinker wrap internal reasoning in <think>...</think>.
    Returns (thinking, answer) — either may be empty.
    """
    think_match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
    if think_match:
        thinking = think_match.group(1).strip()
        answer = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return thinking, answer
    return "", text.strip()


def reason(problem: str, show_thinking: bool = True,
           temperature: float = TEMP_LOGIC) -> tuple[str, str]:
    """
    Apply chain-of-thought reasoning to a problem.
    Returns (thinking, final_answer).
    """
    prompt = f"""Think through this problem carefully before answering.
Use step-by-step reasoning. Consider all possibilities and edge cases.

Problem: {problem}"""

    start = time.time()
    full_response = ""
    in_think_block = False
    thinking_printed = False

    if show_thinking:
        console.print(Rule("[dim]Thinking...[/dim]", style="dim"))

    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": temperature, "num_predict": 3000},
    ):
        token = chunk["response"]
        full_response += token

        if show_thinking:
            # Detect and visually distinguish thinking vs answer
            if "<think>" in full_response and not in_think_block:
                in_think_block = True
                thinking_printed = True
                console.print("[dim cyan]", end="")  # Dim color for thinking

            if "</think>" in full_response and in_think_block:
                in_think_block = False
                console.print("[/dim cyan]", end="")
                console.print(Rule("[bold]Answer[/bold]", style="green"))

            print(token, end="", flush=True)

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")

    thinking, answer = split_thinking(full_response)
    return thinking, answer


def logic_puzzle(puzzle: str) -> str:
    """
    Solve a logic puzzle with full step-by-step reasoning.
    These are problems like knights/knaves, syllogisms, and deductions.
    """
    prompt = f"""This is a logic puzzle. Think carefully through every possible scenario.

{puzzle}

Work through it systematically:
1. List all given facts
2. Apply logical deductions
3. Check for contradictions
4. State your conclusion"""

    _, answer = reason(prompt, show_thinking=True, temperature=TEMP_LOGIC)
    return answer


def debate(topic: str, stance: str = "both") -> None:
    """
    Generate a structured debate with arguments for and against a topic.
    stance: 'for' | 'against' | 'both'
    """
    if stance in ("for", "both"):
        console.print(Panel.fit(
            f"[bold green]Arguments FOR: {topic}[/bold green]",
            border_style="green"
        ))
        prompt = f"""You are a skilled debater. Provide the 5 strongest arguments IN FAVOR of:
"{topic}"

For each argument:
- State it clearly (1 sentence)
- Support with evidence or reasoning (2-3 sentences)
- Anticipate and answer the most obvious counter-argument"""

        for chunk in ollama.generate(
            model=MODEL,
            prompt=prompt,
            stream=True,
            options={"temperature": TEMP_DEBATE, "num_predict": 1500},
        ):
            print(chunk["response"], end="", flush=True)
        print()

    if stance in ("against", "both"):
        console.print(Panel.fit(
            f"[bold red]Arguments AGAINST: {topic}[/bold red]",
            border_style="red"
        ))
        prompt = f"""You are a skilled debater. Provide the 5 strongest arguments AGAINST:
"{topic}"

For each argument:
- State it clearly (1 sentence)
- Support with evidence or reasoning (2-3 sentences)
- Anticipate and answer the most obvious counter-argument"""

        for chunk in ollama.generate(
            model=MODEL,
            prompt=prompt,
            stream=True,
            options={"temperature": TEMP_DEBATE, "num_predict": 1500},
        ):
            print(chunk["response"], end="", flush=True)
        print()


def analyze_argument(argument: str) -> None:
    """
    Analyze an argument for logical validity, fallacies, and strength.
    """
    prompt = f"""Analyze this argument for logical soundness:

"{argument}"

Evaluate:
1. Logical structure: Is the conclusion properly supported by the premises?
2. Logical fallacies: Identify any (ad hominem, strawman, false dichotomy, etc.)
3. Missing evidence: What evidence would be needed to strengthen this?
4. Counter-arguments: What are the strongest objections?
5. Overall verdict: Sound, valid but unsound, or invalid — with explanation"""

    console.print("\n[bold]Argument Analysis:[/bold]\n")
    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": TEMP_ANALYSIS, "num_predict": 2000},
    ):
        print(chunk["response"], end="", flush=True)
    print()


def decision_matrix(scenario: str, options: list[str],
                    criteria: list[str]) -> None:
    """
    Structured decision-making using a weighted matrix.
    The model reasons about each option against each criterion.
    """
    opts_str = "\n".join(f"- {o}" for o in options)
    crit_str = "\n".join(f"- {c}" for c in criteria)

    prompt = f"""You are a strategic decision analyst. Evaluate this decision.

Scenario: {scenario}

Options to evaluate:
{opts_str}

Criteria (equally weighted):
{crit_str}

For each option, score it 1-10 on each criterion with brief reasoning.
Then calculate total scores and give a final recommendation with justification."""

    console.print("\n[bold]Decision Analysis:[/bold]\n")
    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": TEMP_ANALYSIS, "num_predict": 2000},
    ):
        print(chunk["response"], end="", flush=True)
    print()


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]OpenThinker — Chain-of-Thought Reasoning[/bold cyan]\n"
        f"[dim]Model: {MODEL} | Visible reasoning | Complex problem solving[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Modes:[/bold]")
    console.print("  [cyan]1[/cyan] — Logic puzzles and deduction")
    console.print("  [cyan]2[/cyan] — Debate both sides of a topic")
    console.print("  [cyan]3[/cyan] — Argument analysis (check for fallacies)")
    console.print("  [cyan]4[/cyan] — Decision matrix (compare options)")
    console.print("  [cyan]5[/cyan] — Free reasoning (any complex problem)\n")

    mode = console.input("Select mode [1/2/3/4/5]: ").strip()

    if mode == "1":
        console.print("[dim]Logic puzzle mode — paste your puzzle[/dim]\n")
        while True:
            puzzle = console.input("[green]Puzzle:[/green] ").strip()
            if puzzle.lower() in ("quit", "q"):
                break
            logic_puzzle(puzzle)

    elif mode == "2":
        console.print("[dim]Debate mode — state a proposition and see arguments for/against[/dim]\n")
        while True:
            topic = console.input("[green]Topic:[/green] ").strip()
            if topic.lower() in ("quit", "q"):
                break
            stance = console.input("Show [for/against/both]: ").strip() or "both"
            debate(topic, stance)

    elif mode == "3":
        console.print("[dim]Argument analysis — paste an argument to evaluate[/dim]\n")
        while True:
            argument = console.input("[green]Argument:[/green] ").strip()
            if argument.lower() in ("quit", "q"):
                break
            analyze_argument(argument)

    elif mode == "4":
        console.print("[dim]Decision matrix — structured comparison of options[/dim]\n")
        scenario = console.input("Decision scenario: ").strip()

        options = []
        console.print("Enter options (blank line to finish):")
        while True:
            opt = input("  Option: ").strip()
            if not opt:
                break
            options.append(opt)

        criteria = []
        console.print("Enter evaluation criteria (blank line to finish):")
        while True:
            crit = input("  Criterion: ").strip()
            if not crit:
                break
            criteria.append(crit)

        if options and criteria:
            decision_matrix(scenario, options, criteria)

    elif mode == "5":
        console.print("[dim]Free reasoning mode — any complex problem. /quit to exit[/dim]\n")
        while True:
            problem = console.input("[green]Problem:[/green] ").strip()
            if problem.lower() in ("/quit", "quit", "q"):
                break
            show = console.input("Show thinking process? [Y/n]: ").strip().lower() != "n"
            thinking, answer = reason(problem, show_thinking=show)
            if thinking and not show:
                # Show thinking summary even if not shown in-stream
                console.print(f"[dim]Thinking: {len(thinking.split())} words of reasoning used[/dim]")

    else:
        console.print("[yellow]Invalid mode, defaulting to free reasoning[/yellow]\n")
        problem = console.input("[green]Problem:[/green] ").strip()
        reason(problem, show_thinking=True)


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/openthinker
source venv/bin/activate
python3 openthinker.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Classic Logic Puzzle

Select mode `1`:
```
Puzzle: There are three boxes labeled "Apples", "Oranges", and "Mixed". All three labels are wrong. You can pick one fruit from one box without looking. Which box do you pick from to correctly label all three boxes?
```

Watch the model reason through it step-by-step in the `<think>` block.

### Exercise 2: Debate — AI in Education

Select mode `2`:
```
Topic: Artificial intelligence should replace human teachers in K-12 education
Show: both
```

Compare the quality of arguments for/against. Notice how the model considers evidence and counter-arguments for each point.

### Exercise 3: Analyze a Flawed Argument

Select mode `3`:
```
Argument: "We should not invest in renewable energy because my neighbor installed solar panels and his electricity bill didn't go down. Therefore, solar energy doesn't work and is a waste of money."
```

Expected: The model should identify the hasty generalization fallacy and anecdotal evidence problem.

### Exercise 4: Decision Matrix — Choose a Database

Select mode `4`:
```
Scenario: Choose a database for a new IoT sensor data logging application on the Jetson
Options: PostgreSQL, InfluxDB, SQLite, TimescaleDB
Criteria: Write performance, Query flexibility, Memory usage, Ease of setup
```

### Exercise 5: Complex Reasoning Problem

Select mode `5`:
```
Problem: I have a Python service that processes 1000 requests per minute. Each request makes 3 database queries taking 10ms each. The service uses 2GB of RAM and I need to scale it to handle 10x the load. What are my options and what are the tradeoffs of each?
```

Turn off thinking display (`n`) and compare the answer. Then run it again with thinking on (`Y`) — notice how the visible reasoning leads to a more thorough answer.

---

## Expected Output

```
Select mode: 1
Puzzle: If all Bloops are Razzles, and all Razzles are Lazzles, are all Bloops definitely Lazzles?

──────────── Thinking... ────────────────
[dim]Let me think through this systematically...
Given: All Bloops → Razzles
Given: All Razzles → Lazzles
By transitivity: All Bloops → Lazzles
This is a valid syllogism...[/dim]
──────────── Answer ─────────────────────

Yes, all Bloops are definitely Lazzles. This follows from transitive logic:
If A⊆B and B⊆C, then A⊆C.

  1.8s
```

**Performance (MAXN, openthinker:7b):** ~18–22 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `openthinker:7b not found` | `docker exec ollama ollama pull openthinker:7b` |
| No `<think>` blocks visible | Some model versions don't use XML tags; the reasoning is still happening, just not tagged |
| Slow for complex problems | Reasoning models generate more tokens — this is expected; reduce `num_predict` for faster (shallower) reasoning |
| Repetitive reasoning loops | Lower `temperature` to 0.2; add `"repeat_penalty": 1.1` to options |

---

## Next Steps

- **[DeepSeek-R1 Reasoning](deepsr1-reasoning.md)** — Another powerful reasoning model
- **[Phi4 Logic](phi4-logic.md)** — Microsoft's small but capable reasoning model
- **[DeepScaler Math](deepscaler-math.md)** — Math-specialized reasoning with SymPy
