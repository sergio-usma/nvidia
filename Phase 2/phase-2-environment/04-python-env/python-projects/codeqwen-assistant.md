# CodeQwen — Multi-Model Code Assistant

Build a local GitHub Copilot-style assistant supporting multiple code models. Switch between CodeQwen (fast), Qwen2.5-Coder (balanced), and Granite (enterprise review) — all from a single interactive interface, all running locally.

---

## What You'll Learn

- How to build a model-agnostic code tool that works with any Ollama model
- The difference between `ollama.generate()` (completion) vs `ollama.chat()` (conversation)
- Syntax-highlighted code output with `rich.syntax`
- Practical code workflows: generate → explain → test in one session

## Model Comparison

| Model | Speed | Code Quality | Best For |
|-------|-------|-------------|---------|
| codeqwen | ~25 tok/s | Good | Quick generation |
| qwen2.5-coder:7b | ~22 tok/s | Excellent | Balanced tasks |
| granite3.3 | ~18 tok/s | Enterprise | Code review |

## Prerequisites

```bash
# Pull the primary model (~4.7 GB)
docker exec ollama ollama pull codeqwen

# Optional: additional models for comparison
docker exec ollama ollama pull qwen2.5-coder:7b

# Verify
docker exec ollama ollama list | grep -E "codeqwen|qwen.*coder|granite"
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/codeqwen_assistant
cd ~/projects/codeqwen_assistant
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Multi-Model Assistant

Save as `~/projects/codeqwen_assistant/code_assistant.py`:

```python
#!/usr/bin/env python3
"""
CodeQwen Multi-Model Code Assistant
Switch between code models mid-session. All local, no internet.

Key learning: ollama.generate() vs ollama.chat()
- generate(): single-turn, completion-style, no history
- chat(): multi-turn, conversation-style, with history
Both are used here — generate() for code tasks, chat() for explanation Q&A.
"""
import sys
import time
from pathlib import Path
import ollama
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table

console = Console()

MODELS = {
    "1": ("codeqwen", "CodeQwen — fast code generation, ~25 tok/s"),
    "2": ("qwen2.5-coder:7b", "Qwen2.5-Coder 7B — excellent quality, ~22 tok/s"),
    "3": ("granite3.3", "Granite 3.3 — enterprise code review, ~18 tok/s"),
}


def generate_code(prompt: str, model: str, language: str = "python") -> str:
    """
    Generate code from a natural language description.
    Uses generate() (completion style) — no conversation history.
    """
    system_prompt = f"""You are an expert {language} programmer. Generate clean, production-quality code.
Requirements:
- Complete, runnable implementation
- Proper error handling
- Type hints for Python
- No placeholder code
Return ONLY the code, no markdown fences or explanation."""

    full_prompt = f"{system_prompt}\n\nTask: {prompt}"

    start = time.time()
    code = ""

    print(f"\n\033[94mGenerating {language} code...\033[0m\n", flush=True)
    for chunk in ollama.generate(
        model=model,
        prompt=full_prompt,
        stream=True,
        options={"temperature": 0.25, "num_predict": 2048},
    ):
        token = chunk["response"]
        print(token, end="", flush=True)
        code += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")

    # Strip accidental markdown fences
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return code


def explain_code(code: str, model: str, level: str = "developer") -> str:
    """
    Explain code in natural language.
    Uses chat() so follow-up questions work.
    """
    levels = {
        "beginner": "a student who is learning to code",
        "developer": "an experienced developer unfamiliar with this code",
        "expert": "a senior architect reviewing the design",
    }
    audience = levels.get(level, levels["developer"])

    messages = [{
        "role": "user",
        "content": f"Explain this code to {audience}. Cover: what it does, how it works, and any notable design decisions.\n\n```\n{code}\n```"
    }]

    start = time.time()
    explanation = ""

    print(f"\n\033[94mExplanation ({level}):\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=model,
        messages=messages,
        stream=True,
        options={"temperature": 0.4, "num_predict": 1024},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        explanation += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return explanation


def fix_bugs(code: str, error: str, model: str) -> str:
    """Find and fix bugs in code. Error message optional but helps."""
    error_section = f"\nError observed:\n```\n{error}\n```" if error else ""
    prompt = f"""Debug this code and return the fixed version.{error_section}

Buggy code:
```
{code}
```

Return ONLY the corrected code. Make minimal changes to fix the bugs."""

    start = time.time()
    fixed = ""

    print(f"\n\033[91mDebugging...\033[0m\n", flush=True)
    for chunk in ollama.generate(
        model=model,
        prompt=prompt,
        stream=True,
        options={"temperature": 0.1, "num_predict": 2048},
    ):
        token = chunk["response"]
        print(token, end="", flush=True)
        fixed += token

    print()
    console.print(f"[dim]  {time.time() - start:.1f}s[/dim]")
    return fixed.strip()


def generate_tests(code: str, model: str, framework: str = "pytest") -> str:
    """Generate a test suite for the given code."""
    prompt = f"""Write a {framework} test suite for this code.
Include: happy path, edge cases, error conditions. At least 5 tests.
Return ONLY the test code.

Code to test:
```
{code}
```"""

    start = time.time()
    tests = ""

    print(f"\n\033[92mGenerating {framework} tests...\033[0m\n", flush=True)
    for chunk in ollama.generate(
        model=model,
        prompt=prompt,
        stream=True,
        options={"temperature": 0.2, "num_predict": 2048},
    ):
        token = chunk["response"]
        print(token, end="", flush=True)
        tests += token

    print()
    console.print(f"[dim]  {time.time() - start:.1f}s[/dim]")
    return tests.strip()


def show_model_comparison() -> None:
    """Display available models in a table."""
    t = Table(title="Available Models")
    t.add_column("Key", style="cyan")
    t.add_column("Model")
    t.add_column("Description")
    for key, (model, desc) in MODELS.items():
        t.add_row(key, model, desc)
    console.print(t)


def main():
    console.print(Panel.fit(
        "[bold cyan]CodeQwen Multi-Model Code Assistant[/bold cyan]\n"
        "[dim]Local AI code tools | Switch models anytime | No internet[/dim]",
        border_style="cyan",
    ))

    show_model_comparison()
    choice = console.input("\nSelect model [1/2/3] (default 1): ").strip()
    model_name = MODELS.get(choice, MODELS["1"])[0]
    console.print(f"\n[green]Using: {model_name}[/green]")
    console.print("[dim]Commands: generate | explain | fix | test | model | quit[/dim]\n")

    last_code = ""  # Remember last generated/pasted code

    while True:
        try:
            cmd = console.input("[bold blue]codeqwen>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "generate":
                lang = console.input("Language [python/javascript/bash/go]: ").strip() or "python"
                desc = console.input("Describe the code to generate: ").strip()
                last_code = generate_code(desc, model_name, lang)
                syntax = Syntax(last_code, lang, theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title=f"Generated {lang} code"))

                save = console.input("Save to file? [filename or Enter to skip]: ").strip()
                if save:
                    Path(save).write_text(last_code)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "explain":
                if not last_code:
                    console.print("Paste code (blank line to finish):")
                    lines = []
                    while True:
                        line = input()
                        if not line and lines:
                            break
                        lines.append(line)
                    last_code = "\n".join(lines)
                else:
                    use_last = console.input(f"Use last generated code? [Y/n]: ").strip().lower()
                    if use_last == "n":
                        console.print("Paste code (blank line to finish):")
                        lines = []
                        while True:
                            line = input()
                            if not line and lines:
                                break
                            lines.append(line)
                        last_code = "\n".join(lines)

                level = console.input("Explain for [beginner/developer/expert]: ").strip() or "developer"
                explain_code(last_code, model_name, level)

            elif cmd == "fix":
                if not last_code:
                    console.print("Paste buggy code (blank line to finish):")
                    lines = []
                    while True:
                        line = input()
                        if not line and lines:
                            break
                        lines.append(line)
                    last_code = "\n".join(lines)
                error = console.input("Error message (optional): ").strip()
                fixed = fix_bugs(last_code, error, model_name)
                last_code = fixed
                syntax = Syntax(fixed, "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="Fixed Code"))

            elif cmd == "test":
                if not last_code:
                    console.print("Paste code to test (blank line to finish):")
                    lines = []
                    while True:
                        line = input()
                        if not line and lines:
                            break
                        lines.append(line)
                    last_code = "\n".join(lines)
                framework = console.input("Framework [pytest/unittest/jest]: ").strip() or "pytest"
                tests = generate_tests(last_code, model_name, framework)
                syntax = Syntax(tests, "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title=f"{framework} Tests"))

                save = console.input("Save tests? [filename or Enter to skip]: ").strip()
                if save:
                    Path(save).write_text(tests)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "model":
                show_model_comparison()
                choice = console.input("Switch to model [1/2/3]: ").strip()
                model_name = MODELS.get(choice, (model_name, ""))[0]
                console.print(f"[green]Switched to {model_name}[/green]")

            else:
                console.print("[yellow]Unknown command. Try: generate | explain | fix | test | model | quit[/yellow]")

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
cd ~/projects/codeqwen_assistant
source venv/bin/activate
python3 code_assistant.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Generate a Data Processing Pipeline

```
codeqwen> generate
Language: python
Describe: Read a CSV file, filter rows where a "status" column equals "active", compute the mean of a "score" column, and save results to a new CSV
```

Run `test` on the generated code immediately to see if it works.

### Exercise 2: Fix a Broken Function

```
codeqwen> fix
[paste this code]

def merge_sorted_lists(list1, list2):
    result = []
    i = j = 0
    while i <= len(list1) and j <= len(list2):
        if list1[i] < list2[j]:
            result.append(list1[i])
            i += 1
        else:
            result.append(list2[j])
            j += 1
    result.extend(list1[i:])
    result.extend(list2[j:])
    return result

Error: IndexError: list index out of range
```

Expected fix: `while i < len(list1) and j < len(list2)` (off-by-one error).

### Exercise 3: Compare Model Quality

Generate the same function with different models:

```
codeqwen> generate
Language: python
Describe: Implement a LRU (Least Recently Used) cache with get and put operations, O(1) time complexity

[note the output quality]

codeqwen> model
Switch to: 2 (qwen2.5-coder:7b)

codeqwen> generate
[same description]
```

Compare: Which model generates cleaner code? Which adds better error handling?

### Exercise 4: Chain Operations — Generate, Explain, Test

```
codeqwen> generate
Language: python
Describe: A binary search tree with insert, search, and in-order traversal

[output is saved as last_code]

codeqwen> explain
[uses last generated code]
Level: beginner

codeqwen> test
Framework: pytest

[test suite for the BST]
```

This is a real AI-assisted workflow: generate → understand → validate.

### Exercise 5: Generate Bash Tooling

```
codeqwen> generate
Language: bash
Describe: A script to monitor GPU temperature via tegrastats, alert if it exceeds 80°C, and log readings to a CSV file with timestamps
```

---

## Expected Output

```
codeqwen> generate
Language: python
Describe: fibonacci with memoization

Generating python code...

from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

  1.2s
```

**Performance (MAXN, codeqwen):** ~22–28 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `codeqwen not found` | `docker exec ollama ollama pull codeqwen` |
| Code wrapped in markdown fences | The script strips them; if still an issue, check the stripping logic |
| Model generates wrong language | Specify language explicitly in both the prompt and the `lang` field |
| `fix` generates entirely new code | Lower temperature to 0.05; emphasize "minimal changes" in prompt |

---

## Next Steps

- **[Qwen3 Coder Master](qwen3coder-master.md)** — More advanced multi-mode coding assistant
- **[Granite Dev](granite-dev.md)** — Enterprise code review with security scanning
- **[OpenCoder](opencoder.md)** — Fill-in-the-Middle code completion
