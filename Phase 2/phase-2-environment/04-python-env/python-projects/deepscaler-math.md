# DeepScaler — Step-by-Step Math Solver

Build a math problem solver that combines exact symbolic computation (SymPy) with chain-of-thought AI reasoning (DeepSeek-R1). SymPy handles calculus instantly; the LLM handles word problems, proofs, and anything else.

---

## What You'll Learn

- Why low temperature (0.1–0.3) is critical for math accuracy
- Combining two systems: SymPy (exact) + LLM (reasoning)
- Routing problems to the right solver automatically
- Streaming chain-of-thought reasoning in real time

## Prerequisites

```bash
# Pull model (~5 GB — chain-of-thought reasoning)
docker exec ollama ollama pull deepseek-r1:8b

# Verify
docker exec ollama ollama list | grep deepseek-r1
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/math_solver
cd ~/projects/math_solver
python3 -m venv venv
source venv/bin/activate
pip install ollama sympy rich
```

---

## Step 2 — Create the Math Solver

Save as `~/projects/math_solver/math_solver.py`:

```python
#!/usr/bin/env python3
"""
Math Solver: SymPy (exact) + DeepSeek-R1 (reasoning)

Routing logic:
- derivative/integral/solve equation → SymPy (instant, exact)
- word problems / stats / proofs    → LLM (chain-of-thought)
"""
import re
import time
import ollama
import sympy as sp
from sympy import symbols, diff, integrate, solve, simplify, Eq
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# SymPy variables
x, y, z, t, a, b, n = symbols("x y z t a b n")

MODEL = "deepseek-r1:8b"
# Critical: low temperature for math (deterministic, no hallucination)
TEMP = 0.2


# ── Exact Symbolic Solvers (SymPy) ─────────────────────────────────────────

def sym_derivative(expr_str: str) -> dict:
    """Differentiate expression with respect to x."""
    expr = sp.sympify(expr_str)
    result = sp.simplify(sp.diff(expr, x))
    return {
        "method": "SymPy (exact)",
        "result": str(result),
        "steps": [
            f"f(x) = {expr}",
            f"f'(x) = {result}",
        ],
    }


def sym_integral(expr_str: str) -> dict:
    """Compute indefinite integral."""
    expr = sp.sympify(expr_str)
    result = sp.integrate(expr, x)
    return {
        "method": "SymPy (exact)",
        "result": f"{result} + C",
    }


def sym_solve_eq(equation_str: str) -> dict:
    """Solve equation for x."""
    if "=" in equation_str:
        lhs, rhs = equation_str.split("=", 1)
        eq = Eq(sp.sympify(lhs.strip()), sp.sympify(rhs.strip()))
    else:
        eq = Eq(sp.sympify(equation_str), 0)
    solutions = sp.solve(eq, x)
    return {
        "method": "SymPy (exact)",
        "result": f"x = {solutions}",
    }


# ── LLM Chain-of-Thought Solver ────────────────────────────────────────────

def llm_solve(problem: str) -> None:
    """
    Solve with DeepSeek-R1 chain-of-thought reasoning.
    Streams token by token so you see the reasoning as it happens.
    """
    prompt = f"""You are an expert math tutor. Solve this step by step.
Show every step. Explain the reasoning at each stage.

Problem: {problem}

Format:
## Solution Steps
[numbered steps]

## Final Answer
[clear answer]

## Concepts Used
[list of mathematical concepts applied]"""

    console.print("\n[bold cyan]Reasoning (streaming):[/bold cyan]")
    start = time.time()
    tokens = 0

    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": TEMP, "num_predict": 2048},
        stream=True,
    ):
        print(chunk["response"], end="", flush=True)
        tokens += 1

    elapsed = time.time() - start
    print()
    console.print(f"\n[dim]{tokens} tokens in {elapsed:.1f}s ({tokens/elapsed:.1f} tok/s)[/dim]")


# ── Smart Router ─────────────────────────────────────────────────────────

def solve_problem(problem: str) -> None:
    """Route to SymPy for pure math expressions, LLM for everything else."""
    p = problem.lower()

    try:
        if any(kw in p for kw in ["derivative", "d/dx", "differentiate"]):
            # Strip the keyword, keep the expression
            expr = re.sub(r"(derivative of|d/dx|differentiate)", "", p, flags=re.I).strip()
            result = sym_derivative(expr)
            _show_symbolic_result(result, problem)

        elif any(kw in p for kw in ["integral", "integrate", "antiderivative"]):
            expr = re.sub(r"(integral of|integrate|antiderivative of)", "", p, flags=re.I).strip()
            result = sym_integral(expr)
            _show_symbolic_result(result, problem)

        elif "solve" in p and "=" in problem:
            eq = re.sub(r"(solve for x:?|solve:?)", "", problem, flags=re.I).strip()
            result = sym_solve_eq(eq)
            _show_symbolic_result(result, problem)

        else:
            # Word problems, statistics, proofs → LLM
            llm_solve(problem)

    except Exception as e:
        console.print(f"[yellow]SymPy parse error ({e}) — using LLM[/yellow]")
        llm_solve(problem)


def _show_symbolic_result(result: dict, problem: str) -> None:
    console.print(Panel(
        f"[bold]Method:[/bold] {result['method']}\n"
        f"[bold]Result:[/bold] [green]{result['result']}[/green]",
        title="Exact Symbolic Answer",
        border_style="green",
    ))
    if result.get("steps"):
        for step in result["steps"]:
            console.print(f"  {step}")

    if console.input("\nWant LLM explanation? [y/N]: ").strip().lower() == "y":
        llm_solve(problem)


# ── Practice & Verify ──────────────────────────────────────────────────────

def generate_practice(topic: str, difficulty: str = "medium") -> None:
    prompt = f"Generate a {difficulty} practice problem about {topic}. Include the solution."
    response = ollama.generate(model=MODEL, prompt=prompt,
                               options={"temperature": 0.7, "num_predict": 512})
    console.print(Panel(Markdown(response["response"]), title="Practice Problem"))


def verify_solution(problem: str, answer: str) -> None:
    prompt = f"Is this solution correct?\nProblem: {problem}\nAnswer: {answer}\nExplain any errors."
    response = ollama.generate(model=MODEL, prompt=prompt,
                               options={"temperature": 0.1, "num_predict": 512})
    console.print(Panel(Markdown(response["response"]), title="Verification"))


# ── Main CLI ──────────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]Math Solver — SymPy + DeepSeek-R1[/bold cyan]\n"
        "[dim]Exact computation for calculus | LLM reasoning for word problems[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]  solve | practice | verify | quit")
    console.print("[dim]Or just type any math problem directly[/dim]\n")

    while True:
        try:
            cmd = console.input("[bold blue]math>[/bold blue] ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("quit", "exit"):
                break
            elif cmd.lower() == "practice":
                topic = console.input("Topic: ")
                diff = console.input("Difficulty [easy/medium/hard]: ") or "medium"
                generate_practice(topic, diff)
            elif cmd.lower() == "verify":
                problem = console.input("Problem: ")
                answer = console.input("Your answer: ")
                verify_solution(problem, answer)
            elif cmd.lower() == "solve":
                problem = console.input("Problem: ")
                solve_problem(problem)
            else:
                # Treat direct input as a problem
                solve_problem(cmd)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/math_solver
source venv/bin/activate
python3 math_solver.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Calculus — Exact (SymPy, instant)
```
math> derivative of x**3 + 5*x**2 - 3*x + 7
```
Expected: `3*x**2 + 10*x - 3` — returns in milliseconds, no GPU needed.

### Exercise 2: Equation Solving
```
math> solve 2*x**2 - 5*x - 3 = 0
```
Expected: `x = [-1/2, 3]`

### Exercise 3: Word Problem (LLM reasoning — watch it stream)
```
math> A train leaves at 60 mph. A second train leaves the same station 2 hours later at 90 mph. When does the second train catch up?
```

### Exercise 4: Statistics
```
math> A dataset has mean=75, std=10, n=50. Calculate the 95% confidence interval.
```

### Exercise 5: Generate + Solve Practice
```
math> practice
Topic: integration by parts
Difficulty: hard
```
Then copy the problem and solve it yourself. Use `verify` to check your work.

---

## Expected Output

```
math> derivative of x**3 + 2*x

Exact Symbolic Answer
 Method: SymPy (exact)
 Result: 3*x**2 + 2

  f(x) = x**3 + 2*x
  f'(x) = 3*x**2 + 2
```

**Performance (MAXN, deepseek-r1:8b):**
- SymPy: instant (< 10ms)
- LLM word problems: ~15–20 tok/s, ~30–60s for detailed solutions

---

## Monitor GPU

```bash
# Watch GPU during LLM reasoning
tegrastats --interval 500 | grep GR3D
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `x^2` gives wrong result | Use Python syntax: `x**2`, not `x^2` |
| `deepseek-r1:8b not found` | `docker exec ollama ollama pull deepseek-r1:8b` |
| SymPy parse error | Type expression more explicitly, e.g. `3*x` not `3x` |
| Very slow reasoning | Normal for complex problems — DeepSeek-R1 reasons thoroughly |

---

## Next Steps

- **[MathStral Tutor](mathstral-tutor.md)** — Full STEM tutor with practice problem history
- **[DeepSeek R1 Reasoning](deepsr1-reasoning.md)** — Use chain-of-thought for logic/analysis
- **[Phi4 Logic](phi4-logic.md)** — Logic puzzles and deductive reasoning
