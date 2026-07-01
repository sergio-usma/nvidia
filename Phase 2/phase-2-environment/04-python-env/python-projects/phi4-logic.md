# Phi-4 Mini Reasoning — Logic & Decision Engine

Microsoft's Phi-4 Mini Reasoning is a compact but surprisingly capable model for formal logic, deductive reasoning, and structured decision-making. At ~3.8B parameters it runs fast (~35 tok/s on Jetson) while delivering reasoning quality that rivals much larger models on logical tasks.

---

## What You'll Learn

- Formal logic types: deductive, inductive, abductive reasoning
- Building a logic-first CLI with structured prompts that force step-by-step thinking
- Decision support tools: option scoring, pros/cons, devil's advocate
- When a small specialized model beats a large general model

## Why Phi-4 Mini?

| Model | Params | Speed | Logic Score | Best For |
|-------|--------|-------|-------------|---------|
| tinyllama | 1.1B | ~60 tok/s | Basic | Speed |
| phi4-mini-reasoning | 3.8B | ~35 tok/s | Excellent | Logic tasks |
| qwen2.5:7b | 7B | ~22 tok/s | Very good | General |

Phi-4 Mini Reasoning punches above its weight on structured reasoning — Microsoft fine-tuned it specifically for step-by-step thinking.

## Prerequisites

```bash
# Pull the model (~2.5 GB)
docker exec ollama ollama pull phi4-mini-reasoning

# Verify
docker exec ollama ollama list | grep phi4
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/phi4_logic
cd ~/projects/phi4_logic
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Logic & Decision Engine

Save as `~/projects/phi4_logic/phi4_logic.py`:

```python
#!/usr/bin/env python3
"""
Phi-4 Mini Reasoning — Logic & Decision Engine
Compact model (3.8B) optimized for structured reasoning.

Reasoning types:
- Deductive: Given premises → derive conclusion (top-down, certain)
- Inductive: Given observations → infer general rule (bottom-up, probable)
- Abductive: Given observations → find best explanation (inference to best explanation)

Phi-4 excels at all three. Use temperature 0.1-0.3 for logical consistency.
"""
import time
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns

console = Console()
MODEL = "phi4-mini-reasoning"

# Temperature guide for logic:
# 0.1 — Maximum determinism, for formal logic proofs
# 0.3 — Good for structured reasoning with some variation
# 0.5 — For devil's advocate and creative argument generation
TEMP_LOGIC = 0.2
TEMP_DECISION = 0.3
TEMP_DEVILS = 0.5


def stream_response(prompt: str, system: str = "", temperature: float = TEMP_LOGIC,
                    max_tokens: int = 2048, label: str = "Phi-4") -> str:
    """Core streaming call — reused by all functions below."""
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


def deductive_reason(premises: list[str], conclusion: str) -> str:
    """
    Check if conclusion follows from premises via deductive logic.
    Deduction is certain: if premises are true, conclusion MUST be true.
    Example: "All humans die. Socrates is human. → Socrates will die."
    """
    premise_str = "\n".join(f"P{i+1}: {p}" for i, p in enumerate(premises))
    prompt = f"""Analyze this deductive argument for logical validity.

Premises:
{premise_str}

Proposed conclusion: {conclusion}

Steps:
1. List the logical form of each premise
2. Apply the appropriate rule of inference (modus ponens, hypothetical syllogism, etc.)
3. Determine if the conclusion is VALID (must follow) or INVALID (doesn't necessarily follow)
4. If valid, prove it. If invalid, provide a counterexample."""

    return stream_response(prompt, temperature=TEMP_LOGIC, label="Deductive Analysis")


def inductive_reason(observations: list[str], question: str) -> str:
    """
    Inductive reasoning: from specific cases to general rules.
    Induction is probable, not certain — observe patterns, infer rules.
    Example: "Sun rose yesterday, today, all week → Sun probably rises daily."
    """
    obs_str = "\n".join(f"- {o}" for o in observations)
    prompt = f"""Apply inductive reasoning to these observations.

Observations:
{obs_str}

Question: {question}

1. Identify patterns in the observations
2. Formulate the most likely general rule or explanation
3. Rate your confidence (low/medium/high) with justification
4. Describe what additional evidence would increase confidence
5. State the conclusion as a probability, not a certainty"""

    return stream_response(prompt, temperature=TEMP_LOGIC, label="Inductive Analysis")


def abductive_reason(observations: list[str]) -> str:
    """
    Abductive reasoning: inference to the best explanation.
    Given surprising facts, find the simplest explanation that fits all of them.
    Used in: diagnosis, detective work, scientific hypothesis.
    """
    obs_str = "\n".join(f"- {o}" for o in observations)
    prompt = f"""Apply abductive reasoning (inference to best explanation).

Observations to explain:
{obs_str}

1. Generate 3-4 possible explanations that could account for all observations
2. For each explanation, assess:
   - How well it explains ALL observations
   - Its simplicity (Occam's Razor)
   - Whether it makes testable predictions
3. Select the best explanation and justify why it beats the alternatives"""

    return stream_response(prompt, temperature=TEMP_LOGIC, label="Abductive Analysis")


def validate_argument(argument_text: str) -> str:
    """
    Check a natural-language argument for logical validity and fallacies.
    Returns a structured assessment.
    """
    prompt = f"""Analyze this argument for logical validity and identify any fallacies.

Argument: "{argument_text}"

Structure your analysis:
1. Formalize the argument (premise → conclusion format)
2. Logical validity: Is the conclusion properly supported?
3. Soundness: Are the premises actually true (if you can assess this)?
4. Fallacies: List any informal logical fallacies (with their names)
5. Verdict: STRONG / WEAK / FALLACIOUS

Common fallacies to check: ad hominem, strawman, false dichotomy, slippery slope,
appeal to authority, hasty generalization, circular reasoning, post hoc ergo propter hoc"""

    return stream_response(prompt, temperature=TEMP_LOGIC, label="Argument Validation")


def pros_cons(decision: str, options: list[str]) -> None:
    """
    Generate structured pros/cons for each option.
    Displays in a rich table format.
    """
    for option in options:
        prompt = f"""For this decision: {decision}

Analyze option: {option}

Give exactly:
PROS (3-5 specific advantages):
- [pro 1]
- [pro 2]
...

CONS (3-5 specific disadvantages):
- [con 1]
- [con 2]
...

VERDICT: Rate this option 1-10 for this specific decision and explain in 1 sentence."""

        stream_response(
            prompt,
            temperature=TEMP_DECISION,
            label=f"Option: {option}",
            max_tokens=800,
        )


def devils_advocate(position: str) -> str:
    """
    Generate the strongest possible counter-arguments to a position.
    Useful for stress-testing ideas before committing to them.
    """
    prompt = f"""You are playing devil's advocate against this position:

"{position}"

Your job: Generate the 5 STRONGEST counter-arguments possible. Be genuinely challenging.
Do NOT strawman — make the most compelling version of each counter-argument.

For each counter-argument:
- State it powerfully (1-2 sentences)
- Provide supporting evidence or reasoning
- Explain why this is hard to dismiss"""

    return stream_response(
        prompt,
        temperature=TEMP_DEVILS,
        label="Devil's Advocate",
        max_tokens=1500,
    )


def rate_claim(claim: str) -> str:
    """
    Rate a factual or logical claim on a structured scale.
    """
    prompt = f"""Evaluate this claim: "{claim}"

Rate it on:
1. Logical consistency (0-10): Does it contain internal contradictions?
2. Empirical support (0-10): How much evidence exists?
3. Falsifiability (0-10): Can it be tested/disproven?
4. Clarity (0-10): Is it precise and unambiguous?

Overall score: [average]/10
Verdict: STRONG CLAIM / WEAK CLAIM / UNFALSIFIABLE / CONTRADICTORY

Provide a 2-sentence justification for each score."""

    return stream_response(prompt, temperature=TEMP_LOGIC, label="Claim Rating")


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]Phi-4 Mini Reasoning — Logic Engine[/bold cyan]\n"
        f"[dim]Model: {MODEL} | ~35 tok/s | Structured logical analysis[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Modes:[/bold]")
    console.print("  [cyan]1[/cyan] — Deductive reasoning (premises → conclusion)")
    console.print("  [cyan]2[/cyan] — Inductive reasoning (observations → rules)")
    console.print("  [cyan]3[/cyan] — Abductive reasoning (best explanation)")
    console.print("  [cyan]4[/cyan] — Argument validation (check for fallacies)")
    console.print("  [cyan]5[/cyan] — Pros & Cons analysis")
    console.print("  [cyan]6[/cyan] — Devil's Advocate")
    console.print("  [cyan]7[/cyan] — Claim rating\n")

    mode = console.input("Select mode [1-7]: ").strip()

    if mode == "1":
        console.print("[dim]Enter premises then a conclusion to test[/dim]\n")
        premises = []
        console.print("Enter premises (blank line to finish):")
        while True:
            p = input("  Premise: ").strip()
            if not p:
                break
            premises.append(p)
        conclusion = console.input("Proposed conclusion: ").strip()
        if premises and conclusion:
            deductive_reason(premises, conclusion)

    elif mode == "2":
        console.print("[dim]Enter observations, then state what you want to infer[/dim]\n")
        observations = []
        console.print("Enter observations (blank line to finish):")
        while True:
            o = input("  Observation: ").strip()
            if not o:
                break
            observations.append(o)
        question = console.input("What rule or pattern are you trying to infer? ").strip()
        if observations and question:
            inductive_reason(observations, question)

    elif mode == "3":
        console.print("[dim]Enter observations that need explanation[/dim]\n")
        observations = []
        console.print("Enter observations to explain (blank line to finish):")
        while True:
            o = input("  Observation: ").strip()
            if not o:
                break
            observations.append(o)
        if observations:
            abductive_reason(observations)

    elif mode == "4":
        console.print("[dim]Paste an argument to check for logical validity and fallacies[/dim]\n")
        while True:
            argument = console.input("[green]Argument:[/green] ").strip()
            if argument.lower() in ("quit", "q"):
                break
            validate_argument(argument)

    elif mode == "5":
        decision = console.input("Decision to make: ").strip()
        options = []
        console.print("Enter options to compare (blank line to finish):")
        while True:
            opt = input("  Option: ").strip()
            if not opt:
                break
            options.append(opt)
        if options:
            pros_cons(decision, options)

    elif mode == "6":
        console.print("[dim]Enter a position to stress-test[/dim]\n")
        while True:
            position = console.input("[green]Position to challenge:[/green] ").strip()
            if position.lower() in ("quit", "q"):
                break
            devils_advocate(position)

    elif mode == "7":
        console.print("[dim]Rate claims for logical strength and evidence[/dim]\n")
        while True:
            claim = console.input("[green]Claim to evaluate:[/green] ").strip()
            if claim.lower() in ("quit", "q"):
                break
            rate_claim(claim)

    else:
        console.print("[yellow]Invalid mode[/yellow]")


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/phi4_logic
source venv/bin/activate
python3 phi4_logic.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Deductive Reasoning — Classic Syllogism

Select mode `1`:
```
Premise 1: All GPU-accelerated programs run faster than CPU-only programs
Premise 2: CUDA programs are GPU-accelerated programs
Premise 3: This TensorFlow model uses CUDA

Conclusion: This TensorFlow model runs faster than it would without CUDA
```

### Exercise 2: Inductive Reasoning — Pattern Recognition

Select mode `2`:
```
Observation: My llama3.2:3b model generates 45 tok/s at 8W power
Observation: My qwen2.5:7b model generates 22 tok/s at 15W power
Observation: My mistral:7b model generates 20 tok/s at 16W power
Observation: TinyLlama 1.1B generates 60 tok/s at 5W power

Question: What general rule relates model size to speed and power on Jetson?
```

### Exercise 3: Abductive Reasoning — Diagnose a System Problem

Select mode `3`:
```
Observation: My Python script that ran at 45 tok/s now runs at 8 tok/s
Observation: GPU memory usage is the same as before
Observation: jtop shows GPU utilization dropped from 95% to 20%
Observation: The slowdown happened after a Docker container restart
Observation: CPU usage increased significantly
```

What's the most likely explanation? (Answer: MAXN mode wasn't set after restart — model fell back to CPU or low-power GPU mode)

### Exercise 4: Validate a Common Fallacy

Select mode `4`:
```
Argument: "We should ban all AI research because a few AI researchers have raised safety concerns. If even the experts are worried, clearly AI will destroy humanity."
```

Expected: Appeal to authority fallacy, false dichotomy (concern ≠ certain doom), hasty generalization.

### Exercise 5: Devil's Advocate — Test Your Own Project

Select mode `6`:
```
Position: Running all AI models locally on Jetson is better than using cloud APIs
```

Use the counter-arguments to improve your thinking about when local vs cloud makes sense.

---

## Expected Output

```
Select mode: 1
Premise 1: If it rains, the ground gets wet
Premise 2: It is raining

Conclusion: The ground is wet

Phi-4:
1. Logical form:
   P1: Rain → Wet ground (conditional)
   P2: Rain (affirming the antecedent)

2. Rule of inference: Modus Ponens
   Form: If P then Q; P is true; therefore Q

3. VALID — The conclusion necessarily follows.

  1.4s
```

**Performance (MAXN, phi4-mini-reasoning):** ~30–38 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `phi4-mini-reasoning not found` | `docker exec ollama ollama pull phi4-mini-reasoning` |
| Inconsistent logic answers | Lower temperature to 0.1 for maximum determinism |
| Very long responses | Reduce `max_tokens`; add "Be concise" to the prompt |
| Model gets stuck in circular reasoning | Add `"repeat_penalty": 1.15` to options |

---

## Next Steps

- **[OpenThinker](openthinker.md)** — Visible chain-of-thought reasoning
- **[DeepSeek-R1](deepsr1-reasoning.md)** — Large-scale reasoning with `<think>` blocks
- **[DeepScaler Math](deepscaler-math.md)** — Apply reasoning to math problems
