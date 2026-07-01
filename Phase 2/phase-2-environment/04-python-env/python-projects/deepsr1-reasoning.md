# DeepSeek-R1 — Chain-of-Thought Reasoning Engine

DeepSeek-R1 is one of the most capable open-source reasoning models. Like OpenThinker, it exposes `<think>` blocks showing its internal reasoning — but it goes deeper, often producing hundreds of tokens of multi-step thought before a final answer. Excellent for complex math, code analysis, and nuanced problem solving.

---

## What You'll Learn

- How DeepSeek-R1's `<think>` blocks differ from standard CoT prompting
- Streaming reasoning in real time as the model "thinks"
- Multi-mode interface: reason, decompose, verify, compare solutions
- When to use reasoning models vs standard models (cost/quality tradeoff)

## DeepSeek-R1 Model Sizes on Jetson

| Variant | Size | Speed (MAXN) | Use When |
|---------|------|-------------|---------|
| deepseek-r1:1.5b | 1.0 GB | ~50 tok/s | Quick reasoning, limited RAM |
| deepseek-r1:7b | 4.7 GB | ~20 tok/s | Balanced quality/speed |
| deepseek-r1:8b | 5.2 GB | ~18 tok/s | Best 8B reasoning quality |
| deepseek-r1:14b | 9.0 GB | ~10 tok/s | Complex problems |

Start with `:8b` for this tutorial.

## Prerequisites

```bash
# Pull the 8B variant (~5.2 GB)
docker exec ollama ollama pull deepseek-r1:8b

# Verify
docker exec ollama ollama list | grep deepseek-r1
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/deepseek_r1
cd ~/projects/deepseek_r1
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Reasoning Engine

Save as `~/projects/deepseek_r1/cot_reasoner.py`:

```python
#!/usr/bin/env python3
"""
DeepSeek-R1 Chain-of-Thought Reasoning Engine
Deep reasoning with visible <think> blocks.

What R1 does differently:
- Generates extended internal reasoning (often 200-500+ tokens of thought)
- <think>...</think> shows the scratchpad process
- Final answer is more accurate because of this extended reasoning
- Particularly strong at: math, code analysis, logical proofs, planning

When NOT to use R1:
- Simple factual questions (overkill, use mistral:7b)
- Fast responses needed (use phi4-mini or tinyllama)
- Creative writing (use mistral:7b with temp 0.8+)
"""
import re
import time
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

console = Console()

# Default model — change to :7b or :14b if needed
MODEL = "deepseek-r1:8b"

TEMP_REASONING = 0.3    # Low for logical problems
TEMP_PLANNING = 0.4     # Slightly higher for planning tasks
TEMP_ANALYSIS = 0.3     # Low for code/argument analysis


def stream_with_thinking(prompt: str, system: str = "",
                         temperature: float = TEMP_REASONING,
                         max_tokens: int = 4096,
                         show_thinking: bool = True) -> tuple[str, str]:
    """
    Stream model output, separating <think> blocks from the final answer.

    DeepSeek-R1 output structure:
    <think>
    [internal reasoning — often hundreds of tokens]
    </think>
    [final answer]

    Returns (thinking_text, answer_text).
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    start = time.time()
    full_text = ""
    in_think = False
    thinking_done = False

    if show_thinking:
        console.print(Rule("[dim]Reasoning...[/dim]", style="dim"))

    for chunk in ollama.chat(
        model=MODEL,
        messages=messages,
        stream=True,
        options={"temperature": temperature, "num_predict": max_tokens},
    ):
        token = chunk["message"]["content"]
        full_text += token

        if show_thinking:
            # Track think block state for visual differentiation
            if not in_think and not thinking_done and "<think>" in full_text:
                in_think = True
            if in_think and "</think>" in full_text:
                in_think = False
                thinking_done = True
                if thinking_done:
                    print()
                    console.print(Rule("[bold green]Answer[/bold green]", style="green"))

            # Dim color for thinking, normal for answer
            if in_think:
                print(f"\033[2m{token}\033[0m", end="", flush=True)
            else:
                print(token, end="", flush=True)
        else:
            # Show only answer portion
            if "</think>" in full_text and not in_think:
                # We're past the think block
                _, after = full_text.split("</think>", 1)
                if len(after) <= len(token) + 5:
                    # Just crossed the boundary
                    console.print(Rule("[bold green]Answer[/bold green]", style="green"))
                print(token, end="", flush=True)
            elif "<think>" not in full_text:
                print(token, end="", flush=True)

    print()
    elapsed = time.time() - start

    # Parse think blocks
    think_match = re.search(r"<think>(.*?)</think>", full_text, re.DOTALL)
    thinking = think_match.group(1).strip() if think_match else ""
    answer = re.sub(r"<think>.*?</think>", "", full_text, flags=re.DOTALL).strip()

    think_words = len(thinking.split()) if thinking else 0
    ans_words = len(answer.split())
    console.print(f"[dim]  {elapsed:.1f}s | {think_words} words of reasoning → {ans_words} word answer[/dim]")

    return thinking, answer


def reason(problem: str, show_thinking: bool = True) -> str:
    """
    General chain-of-thought reasoning for any problem.
    Returns the final answer.
    """
    prompt = f"""Think through this problem carefully and thoroughly. Consider all relevant factors and edge cases.

Problem: {problem}"""

    _, answer = stream_with_thinking(
        prompt,
        temperature=TEMP_REASONING,
        show_thinking=show_thinking,
    )
    return answer


def decompose_problem(problem: str) -> str:
    """
    Break a complex problem into independent sub-problems.
    Returns a structured breakdown with dependencies.
    """
    prompt = f"""Decompose this complex problem into manageable sub-problems.

Problem: {problem}

Provide:
1. Problem understanding — what makes this complex?
2. Independent sub-problems — list each with clear boundaries
3. Dependencies — which sub-problems must be solved first?
4. Solution strategy — recommended order and approach
5. Potential pitfalls — what could go wrong?"""

    _, answer = stream_with_thinking(
        prompt,
        temperature=TEMP_PLANNING,
        show_thinking=True,
    )
    return answer


def verify_solution(problem: str, proposed_solution: str) -> str:
    """
    Critically verify a proposed solution. Check for errors, edge cases, assumptions.
    """
    prompt = f"""Critically verify this solution. Be thorough and skeptical.

Original problem:
{problem}

Proposed solution:
{proposed_solution}

Check:
1. Correctness — does it solve the problem? Show with an example.
2. Edge cases — what inputs could break it?
3. Hidden assumptions — what does it assume that might not hold?
4. Alternative approaches — is there a better solution?
5. Verdict — CORRECT / PARTIALLY CORRECT / INCORRECT with explanation"""

    _, answer = stream_with_thinking(
        prompt,
        temperature=TEMP_ANALYSIS,
        show_thinking=True,
    )
    return answer


def compare_solutions(problem: str, solutions: list[str]) -> str:
    """
    Compare multiple solutions to the same problem.
    Evaluates correctness, efficiency, readability, and maintainability.
    """
    sols_str = "\n\n".join(
        f"Solution {i+1}:\n{sol}"
        for i, sol in enumerate(solutions)
    )

    prompt = f"""Compare these solutions to the same problem. Evaluate each rigorously.

Problem: {problem}

{sols_str}

For each solution:
- Correctness (does it work?)
- Time/space complexity
- Readability and maintainability
- Edge case handling

Final recommendation: which solution to use and why?"""

    _, answer = stream_with_thinking(
        prompt,
        temperature=TEMP_ANALYSIS,
        show_thinking=True,
    )
    return answer


def analyze_code_logic(code: str, question: str = "Is this code correct?") -> str:
    """
    Deep analysis of code logic — find bugs, prove correctness, or explain behavior.
    R1's extended reasoning makes it much better at this than standard models.
    """
    prompt = f"""Analyze this code deeply. Use careful step-by-step reasoning.

Question: {question}

Code:
```
{code}
```

Trace through the execution for at least one example. Check all branches. Identify any bugs or logic errors."""

    _, answer = stream_with_thinking(
        prompt,
        temperature=TEMP_ANALYSIS,
        max_tokens=3000,
        show_thinking=True,
    )
    return answer


def plan_implementation(task: str, constraints: str = "") -> str:
    """
    Create a detailed implementation plan with R1's reasoning.
    Better than standard models at anticipating problems.
    """
    constraint_note = f"\n\nConstraints: {constraints}" if constraints else ""
    prompt = f"""Create a detailed implementation plan for this task.{constraint_note}

Task: {task}

Include:
1. Architecture overview — key components and how they interact
2. Implementation order — what to build first and why
3. Data structures and algorithms — specific choices with justification
4. Error handling strategy
5. Testing approach
6. Estimated complexity and potential bottlenecks"""

    _, answer = stream_with_thinking(
        prompt,
        temperature=TEMP_PLANNING,
        max_tokens=3000,
        show_thinking=True,
    )
    return answer


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]DeepSeek-R1 — Chain-of-Thought Reasoner[/bold cyan]\n"
        f"[dim]Model: {MODEL} | Extended reasoning | <think> blocks visible[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Modes:[/bold]")
    console.print("  [cyan]1[/cyan] — General reasoning (any complex problem)")
    console.print("  [cyan]2[/cyan] — Decompose a complex problem into sub-tasks")
    console.print("  [cyan]3[/cyan] — Verify a proposed solution")
    console.print("  [cyan]4[/cyan] — Compare multiple solutions")
    console.print("  [cyan]5[/cyan] — Analyze code logic")
    console.print("  [cyan]6[/cyan] — Plan an implementation\n")

    mode = console.input("Select mode [1-6]: ").strip()

    if mode == "1":
        console.print("[dim]General reasoning. /quit to exit[/dim]\n")
        while True:
            problem = console.input("[green]Problem:[/green] ").strip()
            if problem.lower() in ("/quit", "quit", "q"):
                break
            show = console.input("Show thinking? [Y/n]: ").strip().lower() != "n"
            reason(problem, show_thinking=show)

    elif mode == "2":
        problem = console.input("Complex problem to decompose: ").strip()
        decompose_problem(problem)

    elif mode == "3":
        problem = console.input("Problem statement: ").strip()
        console.print("Paste proposed solution (blank line to finish):")
        lines = []
        while True:
            line = input()
            if not line and lines:
                break
            lines.append(line)
        if lines:
            verify_solution(problem, "\n".join(lines))

    elif mode == "4":
        problem = console.input("Problem statement: ").strip()
        solutions = []
        n = int(console.input("How many solutions to compare? ").strip() or "2")
        for i in range(n):
            console.print(f"Paste solution {i+1} (blank line to finish):")
            lines = []
            while True:
                line = input()
                if not line and lines:
                    break
                lines.append(line)
            solutions.append("\n".join(lines))
        compare_solutions(problem, solutions)

    elif mode == "5":
        question = console.input("Question about the code (e.g. 'Is this correct?'): ").strip() or "Is this code correct?"
        console.print("Paste code (blank line to finish):")
        lines = []
        while True:
            line = input()
            if not line and lines:
                break
            lines.append(line)
        if lines:
            analyze_code_logic("\n".join(lines), question)

    elif mode == "6":
        task = console.input("Task to implement: ").strip()
        constraints = console.input("Constraints (optional): ").strip()
        plan_implementation(task, constraints)

    else:
        console.print("[yellow]Invalid mode, using general reasoning[/yellow]\n")
        problem = console.input("[green]Problem:[/green] ").strip()
        reason(problem, show_thinking=True)


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/deepseek_r1
source venv/bin/activate
python3 cot_reasoner.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Complex Reasoning vs Simple Model

Select mode `1`:
```
Problem: I have a 10-liter jug and a 7-liter jug with no markings. How do I measure exactly 4 liters of water?
```

Watch the `<think>` block — R1 will trace through the water-pouring steps systematically. Then ask the same question to TinyLlama and compare depth.

### Exercise 2: Decompose a Software Architecture Problem

Select mode `2`:
```
Problem: Design a real-time video analytics system that processes 4 camera streams simultaneously on Jetson, detects objects using YOLO, tracks them across frames, and alerts when a person enters a restricted zone — with a web dashboard showing live status
```

### Exercise 3: Verify a Flawed Solution

Select mode `3`:
```
Problem: Find all prime numbers up to N

Proposed solution:
def primes_up_to(n):
    primes = []
    for num in range(2, n):
        is_prime = True
        for i in range(2, num):
            if num % i == 0:
                is_prime = False
        if is_prime:
            primes.append(num)
    return primes
```

Expected findings: Off-by-one (should be `range(2, n+1)`), O(n²) complexity, no early termination, no sqrt optimization.

### Exercise 4: Compare Algorithm Implementations

Select mode `4`:
```
Problem: Sort a list of 1 million integers as fast as possible in Python

Solution 1:
def sort_it(lst):
    return sorted(lst)

Solution 2:
import numpy as np
def sort_it(lst):
    return np.sort(np.array(lst)).tolist()

Solution 3:
def quicksort(lst):
    if len(lst) <= 1: return lst
    pivot = lst[len(lst)//2]
    left = [x for x in lst if x < pivot]
    mid = [x for x in lst if x == pivot]
    right = [x for x in lst if x > pivot]
    return quicksort(left) + mid + quicksort(right)
```

### Exercise 5: Plan a Real Project

Select mode `6`:
```
Task: Build a home security camera system on Jetson that: records 24/7 at 1080p, runs YOLO object detection, sends notifications when a person is detected at night, stores clips for 7 days, and provides a web interface to view live feed and recordings

Constraints: Must run entirely on Jetson AGX Orin with no cloud services. Under 30W power during idle. Storage limited to 1TB SSD.
```

---

## Expected Output

```
Select mode: 1
Problem: What is the probability of getting at least one 6 in 4 dice rolls?

──────────── Reasoning... ──────────────
[dim]Let me calculate this using complementary probability.
P(at least one 6) = 1 - P(no 6 in 4 rolls)
P(no 6 in single roll) = 5/6
P(no 6 in 4 rolls) = (5/6)^4 = 625/1296 ≈ 0.482
P(at least one 6) = 1 - 625/1296 = 671/1296 ≈ 0.518[/dim]
──────────── Answer ─────────────────────

The probability of getting at least one 6 in 4 dice rolls is approximately **51.8%**.

  3.4s | 89 words of reasoning → 32 word answer
```

**Performance (MAXN, deepseek-r1:8b):** ~16–20 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `deepseek-r1:8b not found` | `docker exec ollama ollama pull deepseek-r1:8b` |
| Very slow (~5 tok/s) | Check MAXN mode: `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| No `<think>` blocks in output | Some variants don't use XML tags; reduce model size to `:1.5b` which always uses them |
| OOM error | Switch to `:7b` or `:1.5b`; or reduce `num_predict` to 1024 |

---

## Next Steps

- **[OpenThinker](openthinker.md)** — Another visible CoT reasoning model
- **[Phi-4 Logic](phi4-logic.md)** — Faster, compact reasoning model
- **[DeepScaler Math](deepscaler-math.md)** — R1-style reasoning for math + SymPy exact solver
