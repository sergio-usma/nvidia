# Qwen3 Coder — AI Pair Programmer

Qwen3-Coder is Alibaba's latest code-specialized model with strong performance across 40+ programming languages. This project builds a full AI pair programming environment: generate, explain, debug, test, and document code — all locally on your Jetson.

---

## What You'll Learn

- How code models differ from general models (training data, temperature tuning)
- Building a multi-mode coding assistant (generate, explain, debug, test)
- Streaming code output with syntax highlighting
- Saving generated code and running it immediately

## Prerequisites

```bash
# Pull the model (~5.2 GB for 8b variant)
docker exec ollama ollama pull qwen2.5-coder:7b

# Check if qwen3-coder is available (newer, larger)
docker exec ollama ollama pull qwen3-coder 2>/dev/null || echo "Using qwen2.5-coder:7b"

docker exec ollama ollama list | grep -i coder
```

> **Note:** `qwen2.5-coder:7b` and `qwen3-coder` use the same API. The `MODEL` variable in the script lets you switch between them.

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/qwen3_coder
cd ~/projects/qwen3_coder
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the AI Pair Programmer

Save as `~/projects/qwen3_coder/qwen3_coder.py`:

```python
#!/usr/bin/env python3
"""
Qwen3 Coder — AI Pair Programming Assistant
Code-specialized model for generation, explanation, debugging, and testing.

Key insight: code models use lower temperature (0.1–0.3) for deterministic,
correct output. General chat models use 0.7+ for creative responses.
This script shows how to tune parameters per task type.
"""
import sys
import time
import subprocess
import tempfile
import os
from pathlib import Path
import ollama
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table

console = Console()

# Change to qwen3-coder if you pulled it
MODEL = "qwen2.5-coder:7b"

# Temperature guide:
# 0.05–0.1: Very deterministic — use for bug fixing, exact completions
# 0.2–0.3: Deterministic with variety — use for generation
# 0.5+:    Creative — use for documentation prose
TEMP_GENERATE = 0.2
TEMP_DEBUG = 0.1
TEMP_EXPLAIN = 0.4
TEMP_TEST = 0.15


def generate_code(description: str, language: str = "python",
                  include_comments: bool = True) -> str:
    """
    Generate complete, production-ready code from a natural language description.
    The model writes the full implementation with proper structure.
    """
    comment_note = "Add inline comments for non-obvious logic." if include_comments else "No comments needed."
    prompt = f"""Write production-quality {language} code for the following task.

Task: {description}

Requirements:
- Complete, runnable implementation
- Proper error handling for edge cases
- Type hints (for Python/TypeScript)
- {comment_note}
- No placeholder code (no 'pass', '# TODO', etc.)

Return ONLY the code, no explanation before or after."""

    start = time.time()
    code = ""

    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": TEMP_GENERATE, "num_predict": 2048},
    ):
        token = chunk["response"]
        code += token

    elapsed = time.time() - start
    # Strip markdown code fences if present
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    console.print(f"[dim]  Generated in {elapsed:.1f}s[/dim]")
    return code


def explain_code(code: str, language: str = "python", level: str = "developer") -> None:
    """
    Explain what code does, line by line for complex sections.
    Level can be 'beginner', 'developer', or 'expert'.
    """
    level_desc = {
        "beginner": "someone learning to code for the first time",
        "developer": "an experienced developer unfamiliar with this specific code",
        "expert": "a senior engineer who wants architectural insight",
    }
    prompt = f"""Explain this {language} code to {level_desc.get(level, level_desc['developer'])}.

Cover:
1. What the code does overall (1-2 sentences)
2. Key design decisions and why they were made
3. Any tricky or non-obvious parts
4. What happens in edge cases

Code:
```{language}
{code}
```"""

    print(f"\n\033[94mExplanation ({level}):\033[0m\n", flush=True)
    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": TEMP_EXPLAIN, "num_predict": 1024},
    ):
        print(chunk["response"], end="", flush=True)
    print()


def debug_code(code: str, error_message: str = "", language: str = "python") -> str:
    """
    Find and fix bugs. If error_message is provided, uses it as context.
    Returns the fixed code.
    """
    error_section = f"\nError message:\n```\n{error_message}\n```" if error_message else ""
    prompt = f"""Debug this {language} code and fix all bugs.{error_section}

Buggy code:
```{language}
{code}
```

Return the FIXED code only, no explanation. Make minimal changes to fix the bugs."""

    start = time.time()
    fixed = ""

    print("\n\033[91mDebugging...\033[0m\n", flush=True)
    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": TEMP_DEBUG, "num_predict": 2048},
    ):
        token = chunk["response"]
        print(token, end="", flush=True)
        fixed += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  Fixed in {elapsed:.1f}s[/dim]")
    return fixed.strip()


def generate_tests(code: str, language: str = "python",
                   framework: str = "pytest") -> str:
    """
    Generate a complete test suite for the given code.
    Tests cover: happy path, edge cases, error conditions.
    """
    prompt = f"""Write a comprehensive {framework} test suite for this {language} code.

Cover:
- Happy path (normal usage)
- Edge cases (empty input, zero, None, boundary values)
- Error conditions (invalid input, exceptions)
- At least 5 different test functions

Code to test:
```{language}
{code}
```

Return ONLY the test code. Use descriptive test names that explain what's being tested."""

    start = time.time()
    tests = ""

    print(f"\n\033[92mGenerating {framework} tests...\033[0m\n", flush=True)
    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": TEMP_TEST, "num_predict": 2048},
    ):
        token = chunk["response"]
        print(token, end="", flush=True)
        tests += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  Tests generated in {elapsed:.1f}s[/dim]")
    return tests.strip()


def run_code(code: str, language: str = "python") -> None:
    """Execute the generated code and show output."""
    if language != "python":
        console.print("[yellow]Auto-run only supported for Python[/yellow]")
        return

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        fname = f.name

    try:
        console.print(f"[dim]Running {fname}...[/dim]")
        result = subprocess.run(
            ["python3", fname],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.stdout:
            console.print(Panel(result.stdout, title="Output", border_style="green"))
        if result.stderr:
            console.print(Panel(result.stderr, title="Errors", border_style="red"))
        if result.returncode == 0:
            console.print("[green]Ran successfully[/green]")
        else:
            console.print(f"[red]Exit code: {result.returncode}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Execution timed out (30s)[/red]")
    finally:
        os.unlink(fname)


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        f"[bold cyan]Qwen3 Coder — AI Pair Programmer[/bold cyan]\n"
        f"[dim]Model: {MODEL} | Code generation, debugging, testing[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]generate[/cyan]   Generate code from description")
    console.print("  [cyan]explain[/cyan]    Explain what code does")
    console.print("  [cyan]debug[/cyan]      Find and fix bugs")
    console.print("  [cyan]test[/cyan]       Generate test suite")
    console.print("  [cyan]file[/cyan]       Work on a file from disk")
    console.print("  [cyan]quit[/cyan]       Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]coder>[/bold blue] ").strip().lower()

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "generate":
                desc = console.input("Describe what to build: ").strip()
                lang = console.input("Language [python/javascript/bash/go]: ").strip() or "python"
                comments = console.input("Add inline comments? [Y/n]: ").strip().lower() != "n"

                with console.status("[bold green]Generating code..."):
                    code = generate_code(desc, lang, comments)

                syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="Generated Code"))

                action = console.input("Options: [s]ave / [r]un / [t]est / [Enter] to skip: ").strip().lower()
                if action == "s":
                    fname = console.input("Filename: ").strip()
                    Path(fname).write_text(code)
                    console.print(f"[green]Saved to {fname}[/green]")
                elif action == "r":
                    run_code(code, lang)
                elif action == "t":
                    framework = console.input("Test framework [pytest/unittest]: ").strip() or "pytest"
                    tests = generate_tests(code, lang, framework)
                    syntax = Syntax(tests, lang, theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title="Test Suite"))
                    save_tests = console.input("Save tests? [y/N]: ").strip().lower()
                    if save_tests == "y":
                        fname = console.input("Filename: ").strip()
                        Path(fname).write_text(tests)
                        console.print(f"[green]Saved to {fname}[/green]")

            elif cmd == "explain":
                lang = console.input("Language [python/javascript/go]: ").strip() or "python"
                level = console.input("Explain for [beginner/developer/expert]: ").strip() or "developer"
                console.print("Paste code (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    explain_code("\n".join(lines), lang, level)

            elif cmd == "debug":
                lang = console.input("Language [python/javascript/go]: ").strip() or "python"
                console.print("Paste buggy code (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if not lines:
                    continue
                error = console.input("Error message (optional): ").strip()
                debug_code("\n".join(lines), error, lang)

            elif cmd == "test":
                lang = console.input("Language [python/javascript]: ").strip() or "python"
                framework = console.input("Framework [pytest/unittest/jest]: ").strip() or "pytest"
                console.print("Paste code to test (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    tests = generate_tests("\n".join(lines), lang, framework)
                    syntax = Syntax(tests, lang, theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title="Test Suite"))

            elif cmd == "file":
                filepath = console.input("Path to file: ").strip()
                path = Path(filepath)
                if not path.exists():
                    console.print("[red]File not found[/red]")
                    continue
                code = path.read_text()
                ext_map = {"py": "python", "js": "javascript", "ts": "typescript",
                           "go": "go", "sh": "bash"}
                lang = ext_map.get(path.suffix.lstrip("."), "python")
                action = console.input("Action: [e]xplain / [d]ebug / [t]est: ").strip().lower()
                if action == "e":
                    level = console.input("Level [beginner/developer/expert]: ").strip() or "developer"
                    explain_code(code, lang, level)
                elif action == "d":
                    error = console.input("Error message (optional): ").strip()
                    debug_code(code, error, lang)
                elif action == "t":
                    framework = console.input("Framework [pytest/jest]: ").strip() or "pytest"
                    generate_tests(code, lang, framework)

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
cd ~/projects/qwen3_coder
source venv/bin/activate
python3 qwen3_coder.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Generate a Complete Utility

```
coder> generate
Describe: A rate limiter class that limits function calls to N calls per second using a token bucket algorithm
Language: python
Comments: Y
```

Watch the model generate a complete, production-ready implementation. Then:
```
Options: r   (run it immediately)
```

### Exercise 2: Explain Unfamiliar Code

```
coder> explain
Language: python
Level: developer

Paste code:
from functools import lru_cache
from typing import Iterator

def sieve(limit: int) -> Iterator[int]:
    composites = set()
    for n in range(2, limit + 1):
        if n not in composites:
            yield n
            composites.update(range(n*n, limit + 1, n))
```

### Exercise 3: Debug a Broken Script

```
coder> debug
Language: python
Error: TypeError: 'NoneType' object is not subscriptable

Paste buggy code:
def find_max_subarray(arr):
    max_sum = None
    current_sum = 0
    for num in arr:
        current_sum += num
        if current_sum > max_sum:
            max_sum = current_sum
        if current_sum < 0:
            current_sum = 0
    return max_sum

print(find_max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]))
```

The bug: comparing `current_sum > max_sum` when `max_sum` is `None` fails.

### Exercise 4: Generate a Test Suite

```
coder> generate
Describe: A function that validates email addresses using regex and returns True/False
Language: python
```

Then from the output, type `t` to generate tests. The suite should cover valid emails, invalid formats, edge cases like empty string, None, and special characters.

### Exercise 5: Work on a Real File

```
coder> file
Path: ~/projects/nemotron_nano/nemotron_chat.py
Action: e (explain)
Level: expert
```

---

## Expected Output

```
coder> generate
Describe: Parse a CSV file and return aggregated statistics per column
Language: python

Generating code...

import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import statistics

def analyze_csv(filepath: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse a CSV file and compute per-column statistics.
    ...
    """
    ...

  3.2s
```

**Performance (MAXN, qwen2.5-coder:7b):** ~20–25 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `qwen2.5-coder:7b not found` | `docker exec ollama ollama pull qwen2.5-coder:7b` |
| Code contains markdown fences | The script strips them automatically; if not, check the `generate_code` stripping logic |
| Generated code has `# TODO` | Ask again with "No placeholder code" in the description |

---

## Next Steps

- **[CodeQwen Assistant](codeqwen-assistant.md)** — Multi-command IDE-like interface
- **[Granite Dev](granite-dev.md)** — Enterprise code review
- **[OpenCoder](opencoder.md)** — Fill-in-the-Middle code completion
