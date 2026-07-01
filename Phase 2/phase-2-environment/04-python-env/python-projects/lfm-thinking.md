# LFM2.5 Thinking — Structured Reasoning Assistant

LFM2.5 Thinking is the reasoning-enhanced variant of Liquid AI's LFM2 model. It uses chain-of-thought reasoning to tackle complex problems — science questions, logic puzzles, multi-step analysis, and comparative studies. Compared to LFM2's creative focus, LFM2.5-Thinking prioritizes accuracy and structured thinking.

---

## What You'll Learn

- How thinking models build reasoning chains before answering
- Multi-perspective analysis: examining issues from different angles
- Socratic tutoring: teaching through guided questions
- Structured comparison with explicit criteria

## LFM2 vs LFM2.5-Thinking

| Feature | LFM2 | LFM2.5-Thinking |
|---------|-------|----------------|
| Strength | Creative writing | Complex reasoning |
| Temperature | 0.7–0.9 | 0.3–0.5 |
| Best for | Stories, articles | Analysis, explanation |
| Approach | Intuitive flow | Step-by-step logic |

## Prerequisites

```bash
# Pull the model
docker exec ollama ollama pull lfm2.5-thinking

# Check availability — if not listed, try variants:
docker exec ollama ollama list | grep -i lfm
# Alternative: docker exec ollama ollama pull lfm2.5
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/lfm_thinking
cd ~/projects/lfm_thinking
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Thinking Assistant

Save as `~/projects/lfm_thinking/lfm_thinking.py`:

```python
#!/usr/bin/env python3
"""
LFM2.5 Thinking — Structured Reasoning Assistant
Enhanced reasoning for complex explanations, analysis, and problem solving.

When to use thinking mode:
- Science/math explanations where accuracy matters
- Multi-step logic problems
- Comparative analysis of multiple options
- Understanding complex systems

Temperature 0.3–0.5 for consistent, logical output.
Higher temperatures create more varied but less reliable reasoning.
"""
import time
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

console = Console()
MODEL = "lfm2.5-thinking"

TEMP_REASONING = 0.35
TEMP_EXPLANATION = 0.45
TEMP_COMPARE = 0.35


def stream_think(prompt: str, system: str = "",
                 temperature: float = TEMP_REASONING,
                 max_tokens: int = 2048,
                 label: str = "Thinking") -> str:
    """Streaming generation with a thinking label."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    start = time.time()
    response = ""

    print(f"\n\033[94m{label}:\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=messages,
        stream=True,
        options={"temperature": temperature, "num_predict": max_tokens},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        response += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return response


def think_through(problem: str, show_steps: bool = True) -> str:
    """
    General chain-of-thought reasoning for any problem.
    Forces step-by-step breakdown before concluding.
    """
    step_instruction = (
        "Work through this step by step, numbering each step. "
        "Show your reasoning at each stage before giving the final answer."
        if show_steps else ""
    )

    prompt = f"""{step_instruction}

Problem: {problem}"""

    return stream_think(prompt, temperature=TEMP_REASONING, label="Step-by-Step")


def explain_deeply(concept: str, audience: str = "curious person",
                   use_analogies: bool = True) -> str:
    """
    Build a deep, layered explanation using the Feynman technique:
    1. Simple definition
    2. How it works mechanically
    3. Why it matters
    4. Analogies to familiar concepts
    5. Edge cases and limitations
    """
    analogy_note = " Use an analogy to something familiar." if use_analogies else ""
    prompt = f"""Explain '{concept}' to {audience} using the Feynman technique.

Structure your explanation:
1. Simple one-sentence definition
2. How it actually works (the mechanism)
3. Why it matters and where it's used
4. {analogy_note}A concrete example
5. What it does NOT do (common misconceptions)"""

    return stream_think(
        prompt,
        system="You are an expert teacher who excels at clear, deep explanations.",
        temperature=TEMP_EXPLANATION,
        label=f"Explaining: {concept}",
    )


def analyze_multifaceted(topic: str, perspectives: list[str]) -> None:
    """
    Analyze a topic from multiple specified perspectives.
    Useful for understanding complex issues with no single "right" answer.
    """
    perspectives_str = "\n".join(f"- {p}" for p in perspectives)
    prompt = f"""Analyze '{topic}' from each of these perspectives:

{perspectives_str}

For each perspective:
1. State the key concerns or priorities from that viewpoint
2. What would this perspective recommend or conclude?
3. What would this perspective consider the main risks?"""

    stream_think(
        prompt,
        temperature=TEMP_REASONING,
        max_tokens=2000,
        label=f"Multi-Perspective: {topic}",
    )


def compare_deeply(item1: str, item2: str,
                   criteria: Optional[list[str]] = None,
                   context: str = "") -> None:
    """
    Deep comparison with explicit scoring on each criterion.
    Better than a simple pros/cons because it forces evaluation per dimension.
    """
    default_criteria = ["Performance", "Ease of use", "Cost", "Reliability", "Scalability"]
    eval_criteria = criteria or default_criteria

    criteria_str = "\n".join(f"- {c}" for c in eval_criteria)
    context_note = f"\nContext: {context}" if context else ""
    prompt = f"""Compare {item1} vs {item2}.{context_note}

Evaluate each criterion on a 1–10 scale with justification:
{criteria_str}

Present results as:
CRITERION | {item1.upper()} | {item2.upper()} | WINNER
[score]      [score]          [reasoning]

Then give an overall recommendation."""

    stream_think(
        prompt,
        temperature=TEMP_COMPARE,
        max_tokens=2000,
        label=f"Comparison: {item1} vs {item2}",
    )


def socratic_tutor(subject: str) -> None:
    """
    Interactive Socratic tutoring session.
    The model teaches by asking guiding questions rather than lecturing.
    This forces active learning — you must engage to get answers.
    """
    console.print(Panel.fit(
        f"[bold]Socratic Tutoring: {subject}[/bold]\n"
        "[dim]The tutor will guide you with questions. Answer them to learn.[/dim]",
        border_style="cyan",
    ))

    history = [{
        "role": "system",
        "content": (
            f"You are a Socratic tutor teaching {subject}. "
            "Ask one guiding question at a time. "
            "When the student answers correctly, affirm them and deepen the question. "
            "When they answer incorrectly, ask a simpler clarifying question. "
            "Never give the answer directly — guide them to discover it."
        ),
    }]

    # Start with an opening question
    history.append({
        "role": "user",
        "content": f"Please teach me about {subject} using the Socratic method."
    })

    response = ollama.chat(
        model=MODEL,
        messages=history,
        options={"temperature": 0.6, "num_predict": 512},
    )
    opening = response["message"]["content"]
    console.print(f"\n[bold cyan]Tutor:[/bold cyan] {opening}\n")
    history.append({"role": "assistant", "content": opening})

    while True:
        student_answer = console.input("[green]You:[/green] ").strip()
        if student_answer.lower() in ("quit", "q", "/quit"):
            break

        history.append({"role": "user", "content": student_answer})

        print("\n\033[94mTutor:\033[0m ", end="", flush=True)
        reply = ""
        for chunk in ollama.chat(
            model=MODEL,
            messages=history,
            stream=True,
            options={"temperature": 0.6, "num_predict": 512},
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            reply += token
        print()
        history.append({"role": "assistant", "content": reply})


def system_explainer(system_name: str) -> None:
    """
    Explain a complex system from multiple levels of abstraction:
    Bird's eye view → functional components → detailed mechanisms.
    """
    prompt = f"""Explain the {system_name} system using three levels of abstraction:

LEVEL 1 — Big Picture (2-3 sentences for a manager)
What it is and what problem it solves.

LEVEL 2 — Functional Components (for a developer)
List and explain the main components and how they interact.

LEVEL 3 — Deep Mechanics (for an engineer)
How the key algorithms/mechanisms actually work internally.

After each level, note: "If you understand this level, you can [do X]"."""

    stream_think(
        prompt,
        temperature=TEMP_EXPLANATION,
        max_tokens=2000,
        label=f"System: {system_name}",
    )


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]LFM2.5 Thinking — Structured Reasoning[/bold cyan]\n"
        f"[dim]Model: {MODEL} | Deep explanation | Multi-perspective analysis[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Modes:[/bold]")
    console.print("  [cyan]1[/cyan] — Step-by-step reasoning")
    console.print("  [cyan]2[/cyan] — Deep concept explanation (Feynman technique)")
    console.print("  [cyan]3[/cyan] — Multi-perspective analysis")
    console.print("  [cyan]4[/cyan] — Structured comparison")
    console.print("  [cyan]5[/cyan] — Socratic tutoring session")
    console.print("  [cyan]6[/cyan] — System architecture explainer\n")

    mode = console.input("Select mode [1-6]: ").strip()

    if mode == "1":
        console.print("[dim]Step-by-step reasoning. /quit to exit[/dim]\n")
        while True:
            problem = console.input("[green]Problem:[/green] ").strip()
            if problem.lower() in ("/quit", "quit", "q"):
                break
            steps = console.input("Show numbered steps? [Y/n]: ").strip().lower() != "n"
            think_through(problem, steps)

    elif mode == "2":
        console.print("[dim]Deep Feynman-style explanation. /quit to exit[/dim]\n")
        while True:
            concept = console.input("[green]Concept to explain:[/green] ").strip()
            if concept.lower() in ("/quit", "quit", "q"):
                break
            audience = console.input("Target audience [curious person/student/expert]: ").strip() or "curious person"
            analogies = console.input("Use analogies? [Y/n]: ").strip().lower() != "n"
            explain_deeply(concept, audience, analogies)

    elif mode == "3":
        topic = console.input("Topic to analyze: ").strip()
        perspectives = []
        console.print("Enter perspectives (blank line to finish):")
        while True:
            p = input("  Perspective: ").strip()
            if not p:
                break
            perspectives.append(p)
        if not perspectives:
            perspectives = ["technical", "business", "user experience", "ethical"]
            console.print(f"[dim]Using default perspectives: {', '.join(perspectives)}[/dim]")
        analyze_multifaceted(topic, perspectives)

    elif mode == "4":
        item1 = console.input("First item to compare: ").strip()
        item2 = console.input("Second item to compare: ").strip()
        criteria = []
        console.print("Enter comparison criteria (blank line to use defaults):")
        while True:
            c = input("  Criterion: ").strip()
            if not c:
                break
            criteria.append(c)
        context = console.input("Context/use case (optional): ").strip()
        compare_deeply(item1, item2, criteria or None, context)

    elif mode == "5":
        subject = console.input("Subject to learn via Socratic method: ").strip()
        socratic_tutor(subject)

    elif mode == "6":
        system_name = console.input("System to explain (e.g. 'Docker', 'Transformer architecture'): ").strip()
        system_explainer(system_name)

    else:
        console.print("[yellow]Invalid mode, using step-by-step reasoning[/yellow]\n")
        problem = console.input("[green]Problem:[/green] ").strip()
        think_through(problem, True)


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/lfm_thinking
source venv/bin/activate
python3 lfm_thinking.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Step-by-Step Problem Solving

Select mode `1`:
```
Problem: I want to run a 70B parameter model on my Jetson AGX Orin 64GB. The model is available in Q4_K_M GGUF format at 42GB. How much memory will I actually need, and will it fit?
```

Watch the reasoning: model size, context window overhead, OS + runtime overhead, swap usage.

### Exercise 2: Feynman Explanation

Select mode `2`:
```
Concept: Transformer attention mechanism
Audience: developer who knows Python but is new to AI
Analogies: Y
```

Then try the same concept for a different audience:
```
Concept: Transformer attention mechanism
Audience: expert machine learning researcher
```

Compare: same concept, very different depth and vocabulary.

### Exercise 3: Multi-Perspective Analysis

Select mode `3`:
```
Topic: Should we run AI models locally on Jetson or use cloud APIs?

Perspectives:
- Cost (operational expenses over 2 years)
- Privacy and data security
- Performance and latency
- Developer productivity
- Environmental impact
```

### Exercise 4: Structured Comparison

Select mode `4`:
```
Item 1: ollama (Docker-based)
Item 2: llama.cpp (local build)
Context: Serving multiple LLM models to a small team of 5 developers

Criteria:
- Setup time
- GPU utilization
- Model switching speed
- API compatibility
- Memory efficiency
```

### Exercise 5: Learn by Socratic Method

Select mode `5`:
```
Subject: How CUDA parallel computing works
```

The tutor will ask you questions. Try answering even if you're unsure — see how it guides you toward the right understanding. Don't just type "I don't know" — guess!

---

## Expected Output

```
Select mode: 2
Concept: Gradient descent
Audience: curious person
Analogies: Y

Explaining: Gradient descent:

1. Simple definition
Gradient descent is an optimization algorithm that finds the minimum of a function by taking small steps in the direction of steepest descent.

2. How it works
Starting at a random point, we compute the gradient (slope) of the loss function...

3. Analogy
Imagine you're blindfolded on a hilly landscape and want to find the lowest valley...

  6.3s
```

**Performance (MAXN):** ~15–20 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `lfm2.5-thinking not found` | `docker exec ollama ollama pull lfm2.5-thinking` — check available variants with `ollama list` |
| Responses too brief | Increase `max_tokens`; add "explain in detail" to prompt |
| Socratic tutor just lectures | Remind it: "Please only ask me a question, don't give me the answer" |
| Very slow | `lfm2.5-thinking` is larger; enable MAXN mode or use `lfm2` as fallback |

---

## Next Steps

- **[OpenThinker](openthinker.md)** — Another reasoning model with `<think>` blocks
- **[DeepSeek-R1](deepsr1-reasoning.md)** — Deepest chain-of-thought reasoning
- **[LFM2 Studio](lfm2.md)** — Creative writing with the base LFM2 model
