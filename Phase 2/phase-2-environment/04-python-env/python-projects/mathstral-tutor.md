# MathStral — STEM Tutor with Exact + AI Solvers

MathStral is Mistral's math-specialized model. This project combines **exact symbolic math** (SymPy — always correct) with **MathStral's step-by-step explanations and word problem solving** (AI — natural language). The two complement each other: SymPy for precision, MathStral for understanding.

---

## What You'll Learn

- When to use symbolic math (SymPy) vs AI (LLM) for different problem types
- Building a smart routing system that selects the right solver automatically
- Visualizing mathematical functions with matplotlib
- Generating and solving practice problems on demand

## Solver Selection Guide

| Problem Type | Use | Why |
|-------------|-----|-----|
| Derivative/Integral | SymPy | Exact, always correct |
| Solve equations | SymPy | Algebraic solutions |
| Word problems | MathStral | Requires language understanding |
| Statistics/probability | MathStral | Contextual reasoning |
| Proofs/explanations | MathStral | Natural language output |

## Prerequisites

```bash
# Pull the model (~4.1 GB)
docker exec ollama ollama pull mathstral

# Verify
docker exec ollama ollama list | grep mathstral
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/mathstral_tutor
cd ~/projects/mathstral_tutor
python3 -m venv venv
source venv/bin/activate
pip install ollama sympy matplotlib rich
```

---

## Step 2 — Create the STEM Tutor

Save as `~/projects/mathstral_tutor/math_tutor.py`:

```python
#!/usr/bin/env python3
"""
MathStral STEM Tutor — Exact + AI Math Solver

Two-solver architecture:
1. SymPy (symbolic math library): always correct for calculus/algebra
   - Derivatives, integrals, limits, equation solving
   - Returns LaTeX-ready exact results

2. MathStral (LLM): handles what SymPy can't
   - Word problems, statistics, proofs, explanations
   - Step-by-step reasoning in natural language

Smart router selects the appropriate solver based on problem type.
"""
import re
import time
import os
from typing import Optional
import sympy as sp
from sympy import symbols, diff, integrate, limit, solve, oo, simplify
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

console = Console()
MODEL = "mathstral"

# SymPy symbols — add more as needed
x, y, z, n, t, a, b, c = symbols("x y z n t a b c")

# Keywords for automatic solver routing
SYMPY_KEYWORDS = [
    "derivative", "differentiate", "d/dx", "dy/dx",
    "integral", "integrate", "antiderivative",
    "limit", "lim ",
    "solve for", "find x", "equation",
    "simplify", "expand", "factor",
]

MATHSTRAL_KEYWORDS = [
    "probability", "statistics", "mean", "variance",
    "word problem", "how many", "how much",
    "prove", "proof", "theorem",
    "what is", "explain", "why",
]


def route_problem(problem: str) -> str:
    """
    Determine which solver to use based on problem keywords.
    Returns 'sympy' or 'mathstral'.
    """
    problem_lower = problem.lower()

    sympy_score = sum(1 for kw in SYMPY_KEYWORDS if kw in problem_lower)
    mathstral_score = sum(1 for kw in MATHSTRAL_KEYWORDS if kw in problem_lower)

    if sympy_score > mathstral_score:
        return "sympy"
    elif mathstral_score > 0:
        return "mathstral"
    else:
        # Default: try SymPy, fall back to MathStral
        return "auto"


# ── SymPy Solvers ───────────────────────────────────────────────────────────

def parse_expression(expr_str: str) -> Optional[sp.Expr]:
    """Safely parse a SymPy expression from string."""
    try:
        # Replace ^ with ** for power (common math notation)
        expr_str = expr_str.replace("^", "**")
        return sp.sympify(expr_str, locals={
            "x": x, "y": y, "z": z, "n": n, "t": t,
            "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
            "exp": sp.exp, "log": sp.log, "ln": sp.ln,
            "sqrt": sp.sqrt, "pi": sp.pi, "e": sp.E,
        })
    except Exception as e:
        return None


def solve_derivative(problem: str) -> dict:
    """Compute derivatives using SymPy. Handles d/dx f(x) = ... notation."""
    # Extract expression from various notations
    patterns = [
        r"(?:d/dx|derivative of|differentiate)\s+(.+)",
        r"f\(x\)\s*=\s*(.+)",
        r"y\s*=\s*(.+)",
    ]
    expr_str = None
    for pat in patterns:
        m = re.search(pat, problem, re.IGNORECASE)
        if m:
            expr_str = m.group(1).strip()
            break

    if not expr_str:
        return {"error": "Could not extract expression. Try: 'derivative of x^2 + 3x'"}

    expr = parse_expression(expr_str)
    if expr is None:
        return {"error": f"Could not parse: {expr_str}"}

    deriv = sp.diff(expr, x)
    simplified = sp.simplify(deriv)

    return {
        "input": str(expr),
        "result": str(simplified),
        "latex": sp.latex(simplified),
        "steps": [
            f"f(x) = {expr}",
            f"Apply differentiation rules",
            f"f'(x) = {simplified}",
        ],
        "solver": "SymPy (exact)",
    }


def solve_integral(problem: str) -> dict:
    """Compute indefinite or definite integrals using SymPy."""
    # Check for definite integral: integral from a to b of f(x)
    definite_match = re.search(
        r"(?:from|∫)\s*([^,\s]+)\s*(?:to|,)\s*([^,\s]+).*?(?:of)?\s*(.+?)(?:\s*dx)?$",
        problem, re.IGNORECASE
    )

    indefinite_match = re.search(
        r"(?:integral of|∫|integrate)\s+(.+?)(?:\s*dx)?$",
        problem, re.IGNORECASE
    )

    if definite_match:
        lower_str, upper_str, expr_str = definite_match.groups()
        expr = parse_expression(expr_str.strip())
        lower = parse_expression(lower_str)
        upper = parse_expression(upper_str)

        if expr is None:
            return {"error": f"Could not parse expression"}

        result = sp.integrate(expr, (x, lower, upper))
        result = sp.simplify(result)

        return {
            "input": str(expr),
            "result": str(result),
            "latex": sp.latex(result),
            "type": "definite",
            "bounds": f"{lower} to {upper}",
            "solver": "SymPy (exact)",
        }

    elif indefinite_match:
        expr_str = indefinite_match.group(1).strip()
        expr = parse_expression(expr_str)

        if expr is None:
            return {"error": f"Could not parse: {expr_str}"}

        result = sp.integrate(expr, x)
        result = sp.simplify(result)

        return {
            "input": str(expr),
            "result": f"{result} + C",
            "latex": sp.latex(result) + " + C",
            "type": "indefinite",
            "steps": [
                f"∫ {expr} dx",
                f"Apply integration rules",
                f"= {result} + C",
            ],
            "solver": "SymPy (exact)",
        }

    return {"error": "Could not parse integral. Try: 'integral of x^2 + 3x'"}


def solve_equation(problem: str) -> dict:
    """Solve algebraic equations symbolically."""
    # Look for equation with = sign
    if "=" in problem:
        # Extract only the equation part
        eq_match = re.search(r"([\w\s\+\-\*\/\^\(\)\.]+)=([\w\s\+\-\*\/\^\(\)\.]+)", problem)
        if eq_match:
            left_str = eq_match.group(1).strip()
            right_str = eq_match.group(2).strip()
            left = parse_expression(left_str)
            right = parse_expression(right_str)

            if left is None or right is None:
                return {"error": "Could not parse equation"}

            equation = sp.Eq(left, right)
            solutions = sp.solve(equation, x)

            return {
                "equation": str(equation),
                "solutions": [str(s) for s in solutions],
                "latex": [sp.latex(s) for s in solutions],
                "solver": "SymPy (exact)",
            }

    return {"error": "Could not find equation. Include '=' sign."}


def solve_limit_sympy(problem: str) -> dict:
    """Compute limits using SymPy."""
    # Match: "lim x -> 0 of sin(x)/x" or "limit as x approaches 2 of..."
    patterns = [
        r"lim.*?x\s*(?:->|→|approaches?)\s*([^\s]+)\s*(?:of\s+)?(.+)",
        r"limit.*?x\s*(?:->|→|approaches?)\s*([^\s]+)\s*(?:of\s+)?(.+)",
    ]

    for pat in patterns:
        m = re.search(pat, problem, re.IGNORECASE)
        if m:
            approach_str, expr_str = m.groups()
            expr = parse_expression(expr_str.strip())

            approach_map = {"inf": sp.oo, "infinity": sp.oo,
                           "-inf": -sp.oo, "0": 0}
            approach = approach_map.get(approach_str.lower(),
                                        parse_expression(approach_str))

            if expr is None or approach is None:
                return {"error": "Could not parse limit"}

            result = sp.limit(expr, x, approach)

            return {
                "expression": str(expr),
                "approach": str(approach),
                "result": str(result),
                "latex": sp.latex(result),
                "solver": "SymPy (exact)",
            }

    return {"error": "Could not parse limit. Try: 'lim x -> 0 of sin(x)/x'"}


# ── MathStral AI Solver ─────────────────────────────────────────────────────

def mathstral_solve(problem: str, stream: bool = True) -> str:
    """
    Use MathStral for problems SymPy can't handle:
    word problems, statistics, proofs, and explanations.
    """
    system = (
        "You are MathStral, an expert math tutor. "
        "Show step-by-step work for all solutions. "
        "Box or clearly mark the final answer. "
        "Use LaTeX notation when writing math expressions."
    )

    prompt = f"""Solve this math problem step by step:

{problem}

Show all work. If this is a word problem, first define variables and set up equations, then solve."""

    start = time.time()
    response = ""

    print(f"\n\033[94mMathStral:\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        stream=True,
        options={"temperature": 0.2, "num_predict": 2048},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        response += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return response


def explain_concept(concept: str, depth: str = "student") -> None:
    """Explain a math concept with examples."""
    depth_map = {
        "student": "a high school student",
        "undergrad": "a first-year university student",
        "advanced": "someone with a math degree",
    }
    audience = depth_map.get(depth, depth_map["student"])

    prompt = f"""Explain '{concept}' to {audience}.

Include:
1. What it is (clear definition)
2. Why it matters / where it's used
3. Intuitive explanation (use an analogy if helpful)
4. One concrete worked example
5. Common mistakes to avoid"""

    print(f"\n\033[94mExplanation of {concept}:\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": 0.4, "num_predict": 1500},
    ):
        print(chunk["message"]["content"], end="", flush=True)
    print()


def generate_practice(topic: str, difficulty: str = "medium",
                      n: int = 3) -> None:
    """Generate practice problems with solutions."""
    prompt = f"""Generate {n} {difficulty} practice problems about {topic}.

For each problem:
1. State the problem clearly
2. Provide the complete solution with steps
3. State the final answer clearly"""

    print(f"\n\033[92mPractice Problems ({topic}, {difficulty}):\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": 0.6, "num_predict": 2000},
    ):
        print(chunk["message"]["content"], end="", flush=True)
    print()


def plot_function(expr_str: str, x_range: tuple = (-10, 10)) -> None:
    """Plot a function using matplotlib (saved to file)."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np

        expr = parse_expression(expr_str)
        if expr is None:
            console.print(f"[red]Could not parse: {expr_str}[/red]")
            return

        f = sp.lambdify(x, expr, "numpy")
        xs = np.linspace(x_range[0], x_range[1], 500)
        ys = f(xs)

        plt.figure(figsize=(10, 6))
        plt.plot(xs, ys, "b-", linewidth=2)
        plt.grid(True, alpha=0.3)
        plt.axhline(y=0, color="k", linewidth=0.5)
        plt.axvline(x=0, color="k", linewidth=0.5)
        plt.title(f"f(x) = {expr}")
        plt.xlabel("x")
        plt.ylabel("f(x)")

        out = "plot.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        console.print(f"[green]Plot saved to {out}[/green]")

    except ImportError:
        console.print("[yellow]matplotlib not available. Install: pip install matplotlib[/yellow]")
    except Exception as e:
        console.print(f"[red]Plot error: {e}[/red]")


def display_result(result: dict) -> None:
    """Display a SymPy result with rich formatting."""
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        return

    t = Table(title="Solution")
    t.add_column("Field", style="cyan")
    t.add_column("Value")

    for key, val in result.items():
        if key in ("steps", "latex"):
            continue
        if isinstance(val, list):
            t.add_row(key.capitalize(), ", ".join(str(v) for v in val))
        else:
            t.add_row(key.capitalize(), str(val))

    console.print(t)

    if "steps" in result:
        console.print("\n[bold]Steps:[/bold]")
        for step in result["steps"]:
            console.print(f"  {step}")

    if "latex" in result:
        console.print(f"\n[dim]LaTeX: {result['latex']}[/dim]")


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]MathStral STEM Tutor[/bold cyan]\n"
        "[dim]SymPy exact solver + MathStral AI | Calculus, Algebra, Word Problems[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]solve[/cyan]      Auto-route to best solver")
    console.print("  [cyan]deriv[/cyan]      Derivative (SymPy exact)")
    console.print("  [cyan]integral[/cyan]   Integral (SymPy exact)")
    console.print("  [cyan]limit[/cyan]      Limit (SymPy exact)")
    console.print("  [cyan]equation[/cyan]   Solve equation (SymPy)")
    console.print("  [cyan]explain[/cyan]    Explain a concept")
    console.print("  [cyan]practice[/cyan]   Generate practice problems")
    console.print("  [cyan]plot[/cyan]       Plot a function")
    console.print("  [cyan]quit[/cyan]       Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]math>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "solve":
                problem = console.input("Problem: ").strip()
                solver = route_problem(problem)
                console.print(f"[dim]Routing to: {solver}[/dim]")

                if solver == "sympy":
                    # Try each SymPy solver
                    p_lower = problem.lower()
                    if any(k in p_lower for k in ["derivative", "d/dx", "differentiate"]):
                        display_result(solve_derivative(problem))
                    elif any(k in p_lower for k in ["integral", "integrate", "∫"]):
                        display_result(solve_integral(problem))
                    elif "limit" in p_lower or "lim " in p_lower:
                        display_result(solve_limit_sympy(problem))
                    elif "=" in problem:
                        display_result(solve_equation(problem))
                    else:
                        mathstral_solve(problem)
                else:
                    mathstral_solve(problem)

            elif cmd == "deriv":
                problem = console.input("Derivative problem (e.g. 'derivative of x^3 + sin(x)'): ").strip()
                display_result(solve_derivative(problem))

            elif cmd == "integral":
                problem = console.input("Integral problem (e.g. 'integral of x^2 + 3x'): ").strip()
                display_result(solve_integral(problem))

            elif cmd == "limit":
                problem = console.input("Limit problem (e.g. 'lim x -> 0 of sin(x)/x'): ").strip()
                display_result(solve_limit_sympy(problem))

            elif cmd == "equation":
                problem = console.input("Equation to solve (e.g. 'x^2 - 5x + 6 = 0'): ").strip()
                display_result(solve_equation(problem))

            elif cmd == "explain":
                concept = console.input("Concept to explain: ").strip()
                depth = console.input("Level [student/undergrad/advanced]: ").strip() or "student"
                explain_concept(concept, depth)

            elif cmd == "practice":
                topic = console.input("Topic: ").strip()
                difficulty = console.input("Difficulty [easy/medium/hard]: ").strip() or "medium"
                n = int(console.input("Number of problems [3]: ").strip() or "3")
                generate_practice(topic, difficulty, n)

            elif cmd == "plot":
                expr = console.input("Function f(x) = ").strip()
                x_min = float(console.input("x min [-10]: ").strip() or "-10")
                x_max = float(console.input("x max [10]: ").strip() or "10")
                plot_function(expr, (x_min, x_max))

            else:
                console.print("[yellow]Unknown command[/yellow]")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/mathstral_tutor
source venv/bin/activate
python3 math_tutor.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Exact Derivatives (SymPy)

```
math> deriv
Problem: derivative of x^4 - 3*x^2 + 2*x - 7

math> deriv
Problem: derivative of sin(x) * exp(x)

math> deriv
Problem: derivative of ln(x^2 + 1)
```

Compare SymPy's output (instant, exact) to what you'd get from MathStral alone.

### Exercise 2: Definite Integral

```
math> integral
Problem: integral from 0 to pi of sin(x) dx

math> integral
Problem: integral of x^2 * exp(-x)
```

Expected first answer: exactly `2` (SymPy gives the exact rational/symbolic result).

### Exercise 3: Limits at Infinity

```
math> limit
Problem: lim x -> inf of (x^2 + 1) / (3*x^2 - 2)

math> limit
Problem: lim x -> 0 of sin(x)/x
```

Expected: `1/3` and `1` respectively.

### Exercise 4: Word Problem (MathStral)

```
math> solve
Problem: A train leaves station A at 60 km/h. Another train leaves station B (300 km away) toward station A at 90 km/h. How long until they meet, and at what distance from A?
```

This routes to MathStral. Watch it set up the distance equations and solve.

### Exercise 5: Generate Practice Problems

```
math> practice
Topic: integration by parts
Difficulty: medium
Number: 3
```

Then solve one of the generated problems with `integral`:
```
math> integral
Problem: integral of x * sin(x)
```

### Exercise 6: Plot and Verify

```
math> plot
f(x) = x^3 - 3*x
x min: -3
x max: 3
```

Then take the derivative and verify the critical points match the zeros in the plot:
```
math> deriv
Problem: derivative of x^3 - 3*x
```

The derivative `3*x^2 - 3 = 0` gives `x = ±1` — verify these are the turning points in the plot.

---

## Expected Output

```
math> deriv
Problem: derivative of sin(x) * exp(x)

Solution:
Field      | Value
Input      | sin(x)*exp(x)
Result     | (sin(x) + cos(x))*exp(x)
Latex      | \left(\sin{\left(x \right)} + \cos{\left(x \right)}\right) e^{x}
Solver     | SymPy (exact)

Steps:
  f(x) = sin(x)*exp(x)
  Apply differentiation rules (product rule)
  f'(x) = (sin(x) + cos(x))*exp(x)
```

**Performance:** SymPy results are instant (<0.1s). MathStral: ~15–20 tok/s on Jetson MAXN.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mathstral not found` | `docker exec ollama ollama pull mathstral` |
| SymPy parse error | Use Python-style syntax: `x**2` not `x^2`, `*` for multiplication |
| `matplotlib not found` | `pip install matplotlib` (optional, only for plot command) |
| Word problem routes to SymPy | It found a math keyword; prefix with "word problem:" to force MathStral |

---

## Next Steps

- **[DeepScaler Math](deepscaler-math.md)** — DeepSeek-R1 reasoning + SymPy for advanced math
- **[DeepSeek-R1 Reasoning](deepsr1-reasoning.md)** — Chain-of-thought for math proofs
- **[Phi-4 Logic](phi4-logic.md)** — Compact reasoning for logical problems
