# Qwen2.5-Coder — Python Debugger

Build a local AI debugging assistant that finds bugs, explains errors, suggests fixes, and generates unit tests — all running on your Jetson with zero internet required.

---

## What You'll Learn

- How to send code as context to a code-specialized LLM
- Temperature control for deterministic vs creative output
- Reading code from files vs stdin
- Saving fixed code back to disk automatically

## Prerequisites

```bash
# Pull the model (do this once, ~4.7 GB)
docker exec ollama ollama pull qwen2.5-coder:7b

# Verify it loaded
docker exec ollama ollama list | grep qwen2.5-coder
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/debugger
cd ~/projects/debugger
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Debugger

Save as `~/projects/debugger/debugger.py`:

```python
#!/usr/bin/env python3
"""
AI Python Debugger using Qwen2.5-Coder
Jetson AGX Orin 64GB — runs 100% locally
"""
import sys
import time
from pathlib import Path
import ollama
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# Use a low temperature for deterministic, precise bug fixes
MODEL = "qwen2.5-coder:7b"
TEMP_FIX = 0.1       # Very precise for bug fixes
TEMP_EXPLAIN = 0.4   # Slightly more natural for explanations


def fix_bugs(code: str) -> str:
    """
    Ask the model to find and fix all bugs.
    Low temperature (0.1) makes the output deterministic and precise.
    """
    prompt = f"""You are an expert Python developer. Find ALL bugs in the code below and return ONLY the corrected code.
Do not add explanations or markdown — just the fixed Python code.

```python
{code}
```"""

    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": TEMP_FIX, "num_predict": 2048},
    )
    return response["response"]


def explain_error(error_msg: str, code: str = "") -> str:
    """
    Explain a Python error in plain language.
    Context (the surrounding code) makes the explanation much more useful.
    """
    context = f"\n\nCode context:\n```python\n{code}\n```" if code else ""
    prompt = f"""Explain this Python error in simple terms and provide the fix:

Error: {error_msg}{context}

Format your response as:
1. What went wrong (1-2 sentences)
2. Why it happened
3. How to fix it (with code)"""

    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": TEMP_EXPLAIN, "num_predict": 1024},
    )
    return response["response"]


def generate_tests(code: str) -> str:
    """
    Generate pytest unit tests for the given code.
    Tests catch regressions — always generate them after a fix.
    """
    prompt = f"""Write comprehensive pytest unit tests for this Python code.
Cover: normal cases, edge cases, and error cases.

```python
{code}
```

Return only the test code."""

    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": 0.2, "num_predict": 2048},
    )
    return response["response"]


def review_code(code: str) -> str:
    """Code quality review: style, performance, and security issues."""
    prompt = f"""Review this Python code for:
1. Code quality and style (PEP 8)
2. Performance issues
3. Security vulnerabilities
4. Missing error handling

```python
{code}
```

Be concise and actionable."""

    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": 0.3, "num_predict": 1024},
    )
    return response["response"]


def read_code_input() -> str:
    """Read multi-line code from stdin until two blank lines."""
    console.print("[dim]Paste your code. Press Enter twice when done:[/dim]")
    lines = []
    blank_count = 0
    while True:
        try:
            line = input()
            if line == "":
                blank_count += 1
                if blank_count >= 2 and lines:
                    break
            else:
                blank_count = 0
                lines.append(line)
        except EOFError:
            break
    return "\n".join(lines)


def main():
    console.print(Panel.fit(
        "[bold cyan]Qwen2.5-Coder — Python Debugger[/bold cyan]\n"
        "[dim]Model: qwen2.5-coder:7b | Running locally on Jetson[/dim]",
        border_style="cyan",
    ))

    commands = {
        "fix":    "Find and fix all bugs",
        "error":  "Explain an error message",
        "tests":  "Generate pytest unit tests",
        "review": "Code quality review",
        "file":   "Debug a .py file directly",
        "quit":   "Exit",
    }

    console.print("\n[bold]Commands:[/bold]")
    for cmd, desc in commands.items():
        console.print(f"  [cyan]{cmd:<8}[/cyan] {desc}")

    while True:
        try:
            cmd = console.input("\n[bold blue]debugger>[/bold blue] ").strip().lower()

            if cmd in ("quit", "exit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break

            elif cmd == "fix":
                code = read_code_input()
                if not code:
                    continue
                with console.status("[bold green]Analyzing bugs...[/bold green]"):
                    start = time.time()
                    fixed = fix_bugs(code)
                    elapsed = time.time() - start
                syntax = Syntax(fixed, "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title=f"Fixed Code ({elapsed:.1f}s)"))

                save = console.input("Save to file? [y/N]: ").strip().lower()
                if save == "y":
                    path = console.input("Filename: ").strip()
                    Path(path).write_text(fixed)
                    console.print(f"[green]Saved to {path}[/green]")

            elif cmd == "error":
                error_msg = console.input("Error message: ")
                console.print("[dim]Paste relevant code (optional, Enter twice to skip):[/dim]")
                code = read_code_input()
                with console.status("[bold green]Analyzing error...[/bold green]"):
                    explanation = explain_error(error_msg, code)
                console.print(Panel(Markdown(explanation), title="Error Analysis"))

            elif cmd == "tests":
                code = read_code_input()
                if not code:
                    continue
                with console.status("[bold green]Generating tests...[/bold green]"):
                    tests = generate_tests(code)
                syntax = Syntax(tests, "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="Unit Tests (pytest)"))

            elif cmd == "review":
                code = read_code_input()
                if not code:
                    continue
                with console.status("[bold green]Reviewing code...[/bold green]"):
                    review = review_code(code)
                console.print(Panel(Markdown(review), title="Code Review"))

            elif cmd == "file":
                filepath = console.input("Path to .py file: ").strip()
                try:
                    code = Path(filepath).read_text()
                    console.print(f"[green]Loaded {len(code.splitlines())} lines[/green]")
                    action = console.input("Action [fix/review/tests]: ").strip().lower()
                    with console.status("[bold green]Processing...[/bold green]"):
                        if action == "fix":
                            result = fix_bugs(code)
                            syntax = Syntax(result, "python", theme="monokai", line_numbers=True)
                            console.print(Panel(syntax, title="Fixed Code"))
                        elif action == "review":
                            result = review_code(code)
                            console.print(Panel(Markdown(result), title="Review"))
                        elif action == "tests":
                            result = generate_tests(code)
                            syntax = Syntax(result, "python", theme="monokai", line_numbers=True)
                            console.print(Panel(syntax, title="Tests"))
                except FileNotFoundError:
                    console.print(f"[red]File not found: {filepath}[/red]")

            else:
                console.print("[yellow]Unknown command. Type 'quit' to exit.[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/debugger
source venv/bin/activate
python3 debugger.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Fix a Buggy Script

Create a file with intentional bugs:
```bash
cat > buggy.py << 'EOF'
def calculate_average(numbers):
    total = 0
    for n in numbers
        total += n
    return total / len(numbers)

scores = [85, 92, 78, 90, 88]
print(f"Average: {calculate_average()}")
EOF
```

Then in the debugger:
```
debugger> file
Path to .py file: buggy.py
Action: fix
```

The model should find: missing `:` after `for`, wrong function call (missing argument).

### Exercise 2: Explain a Real Error

Run this to get an error:
```bash
python3 -c "d = {'key': 1}; print(d['missing'])"
```

Copy the `KeyError` traceback and paste it with `error` command.

### Exercise 3: Generate Tests for Your Own Code

Take any Python function you've written recently and run `tests` on it. The model writes pytest cases you can actually run:
```bash
pip install pytest
pytest test_mycode.py -v
```

---

## Expected Output

```
debugger> fix
Paste your code...

Fixed Code (3.2s)
 1 def calculate_average(numbers):
 2     total = 0
 3     for n in numbers:
 4         total += n
 5     return total / len(numbers)
 6
 7 scores = [85, 92, 78, 90, 88]
 8 print(f"Average: {calculate_average(scores)}")
```

**Performance on Jetson AGX Orin 64GB (MAXN):** ~18–22 tok/s with qwen2.5-coder:7b

---

## Monitor GPU During Use

```bash
# In a second terminal
tegrastats --interval 1000 | grep -E "GR3D|RAM"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `model not found` | `docker exec ollama ollama pull qwen2.5-coder:7b` |
| Slow response (<10 tok/s) | `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| Fixed code not valid Python | Lower temperature to `0.05`, be more specific in code input |
| Rich not installed | `pip install rich` in your venv |

---

## Next Steps

- **[CodeQwen Assistant](codeqwen-assistant.md)** — Multi-command IDE-like interface
- **[Qwen3 Coder](qwen3coder-master.md)** — Newer, more capable coding model
- **[OpenCoder](opencoder.md)** — Specialized code completion
