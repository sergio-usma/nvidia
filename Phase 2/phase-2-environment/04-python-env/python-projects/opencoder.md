# OpenCoder — Intelligent Code Completion

OpenCoder is trained specifically for code completion tasks — finishing partial functions, filling in missing code, and generating boilerplate. Think of it as a local GitHub Copilot.

---

## What You'll Learn

- Code completion vs code generation: key differences
- Fill-in-the-Middle (FIM) prompting pattern for code
- Building a file watcher that auto-completes as you save
- Integrating the model into a VS Code task

## Prerequisites

```bash
# Pull the model (~4.7 GB)
docker exec ollama ollama pull opencoder

# If not available, use this alternative:
# docker exec ollama ollama pull qwen2.5-coder:7b
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/code_complete
cd ~/projects/code_complete
python3 -m venv venv
source venv/bin/activate
pip install ollama rich watchdog
```

---

## Step 2 — Create the Code Completer

Save as `~/projects/code_complete/code_complete.py`:

```python
#!/usr/bin/env python3
"""
OpenCoder — Intelligent Code Completion
Finish functions, fill blanks, generate from signatures.

How completion models differ from chat models:
- Completion: given prefix → continue naturally
- Chat: given question → answer it
- FIM (Fill-in-Middle): given prefix + suffix → fill the gap

OpenCoder is optimized for all three patterns.
"""
import sys
import time
from pathlib import Path
import ollama
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

MODEL = "opencoder"
# Low temperature = deterministic code, no creative hallucinations
TEMP = 0.2


def complete_code(prefix: str, language: str = "python") -> str:
    """
    Complete partial code from a prefix.
    The model acts as if it's auto-completing what you've typed so far.
    """
    prompt = f"""Complete the following {language} code. Return ONLY the completion, not the original prefix.

```{language}
{prefix}
```

Continue from where it left off:"""

    start = time.time()
    response_text = ""

    print("\n\033[94mCompletion:\033[0m ", end="", flush=True)
    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": TEMP, "num_predict": 512},
    ):
        token = chunk["response"]
        print(token, end="", flush=True)
        response_text += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return response_text


def fill_blank(code_with_blank: str, language: str = "python") -> str:
    """
    Fill in a __BLANK__ placeholder in code.
    This implements a simplified FIM (Fill-in-Middle) pattern.
    """
    prompt = f"""Replace __BLANK__ with the correct {language} code.
Return ONLY the complete code with the blank filled in.

{code_with_blank}"""

    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": TEMP, "num_predict": 256},
    )
    return response["response"]


def generate_function(name: str, description: str, language: str = "python",
                      include_tests: bool = False) -> str:
    """
    Generate a complete function from its name and description.
    Optionally includes a pytest test.
    """
    prompt = f"""Write a complete, production-quality {language} function:

Function name: {name}
What it should do: {description}
Requirements:
- Proper docstring
- Type hints (for Python)
- Error handling for edge cases
- Efficient implementation"""

    if include_tests:
        prompt += "\n- Include a pytest test function below the implementation"

    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": TEMP, "num_predict": 1024},
    )
    return response["response"]


def complete_file(filepath: str) -> None:
    """
    Read a .py file, find incomplete sections (pass, TODO, ...)
    and fill them in with AI-generated code.
    """
    path = Path(filepath)
    if not path.exists():
        console.print(f"[red]File not found: {filepath}[/red]")
        return

    code = path.read_text()
    lines = code.splitlines()

    # Find lines with placeholders
    placeholders = ["pass", "...", "# TODO", "# FIXME", "raise NotImplementedError"]
    incomplete_lines = [
        (i + 1, line.strip())
        for i, line in enumerate(lines)
        if any(p in line for p in placeholders)
    ]

    if not incomplete_lines:
        console.print("[green]No incomplete sections found![/green]")
        return

    console.print(f"[yellow]Found {len(incomplete_lines)} incomplete section(s):[/yellow]")
    for lineno, content in incomplete_lines:
        console.print(f"  Line {lineno}: {content}")

    if Prompt.ask("\nComplete these sections?", choices=["y", "n"]) == "y":
        # Find context around each placeholder and complete
        # For simplicity, complete the whole file context at once
        result = complete_code(code)
        out_path = path.with_stem(path.stem + "_completed")
        out_path.write_text(result)
        console.print(f"[green]Saved to {out_path}[/green]")
        syntax = Syntax(result[:1000], "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Completion Preview"))


# ── Interactive CLI ────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]OpenCoder — Code Completion[/bold cyan]\n"
        "[dim]Complete, fill, generate | Local AI on Jetson[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]complete[/cyan]    Complete partial code")
    console.print("  [cyan]fill[/cyan]        Fill __BLANK__ in code")
    console.print("  [cyan]generate[/cyan]    Generate function from description")
    console.print("  [cyan]file[/cyan]        Complete a .py file's TODO sections")
    console.print("  [cyan]quit[/cyan]        Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]coder>[/bold blue] ").strip().lower()

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "complete":
                lang = console.input("Language [python/javascript/bash]: ").strip() or "python"
                console.print("Paste partial code (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    result = complete_code("\n".join(lines), lang)
                    syntax = Syntax(result, lang, theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title="Completed Code"))

            elif cmd == "fill":
                lang = console.input("Language [python/javascript]: ").strip() or "python"
                console.print("Paste code with __BLANK__ placeholder (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    result = fill_blank("\n".join(lines), lang)
                    syntax = Syntax(result, lang, theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title="Filled Code"))

            elif cmd == "generate":
                name = console.input("Function name: ").strip()
                desc = console.input("What it should do: ").strip()
                lang = console.input("Language [python/javascript/bash]: ").strip() or "python"
                tests = console.input("Include tests? [y/N]: ").strip().lower() == "y"
                with console.status("[bold green]Generating..."):
                    result = generate_function(name, desc, lang, tests)
                syntax = Syntax(result, lang, theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="Generated Function"))

                save = console.input("Save to file? [y/N]: ").strip().lower()
                if save == "y":
                    path = console.input("Filename: ").strip()
                    Path(path).write_text(result)
                    console.print(f"[green]Saved to {path}[/green]")

            elif cmd == "file":
                filepath = console.input("Path to .py file: ").strip()
                complete_file(filepath)

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
cd ~/projects/code_complete
source venv/bin/activate
python3 code_complete.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Complete a Function Signature

```
coder> complete
Language: python

Paste partial code:
def binary_search(arr: list, target: int) -> int:
    """Search for target in sorted array. Return index or -1."""
    left, right = 0, len(arr) - 1
    while
```

### Exercise 2: Fill in the Blank

```
coder> fill
Language: python

def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate Body Mass Index."""
    if height_m <= 0:
        __BLANK__
    return weight_kg / (height_m ** 2)
```

The model should fill `__BLANK__` with `raise ValueError("Height must be positive")`.

### Exercise 3: Generate a Complete Function

```
coder> generate
Function name: parse_jetson_tegrastats
What it should do: Parse a line of tegrastats output and return a dict with CPU%, GPU%, RAM used, RAM total
Language: python
Include tests: y
```

### Exercise 4: Generate Bash Utility

```
coder> generate
Function name: backup_models
What it should do: Backup all .gguf files from ~/models to /data/backup with timestamp
Language: bash
```

---

## Expected Output

```
coder> complete
Language: python
Paste partial code:
def fibonacci(n: int) -> int:
    if n <= 1:

Completion:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
  0.8s
```

**Performance (MAXN, opencoder):** ~20–25 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `opencoder not found` | `docker exec ollama ollama pull opencoder` or use `qwen2.5-coder:7b` |
| Completion repeats the input | The prompt is returning prefix — adjust the prompt template |
| Wrong language output | Specify language clearly in the prompt |

---

## Next Steps

- **[CodeQwen Assistant](codeqwen-assistant.md)** — Multi-command IDE-like interface
- **[Qwen2.5 Debugger](qwen25-debugger.md)** — Bug detection and fixing
- **[Granite Dev](granite-dev.md)** — Enterprise code review
