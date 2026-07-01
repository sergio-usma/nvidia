# Qwen3 Coder — AI Pair Programmer via llama.cpp

Qwen3 Coder is Alibaba's state-of-the-art code-specialized model. This project runs it **directly via llama.cpp** (no Docker, no Ollama) — giving you full control over context size, GPU layers, and inference flags. You'll build an interactive pair programmer with streaming output, FIM completion, and multi-language support.

---

## What You'll Learn

- Running a GGUF model with the llama.cpp HTTP server on Jetson
- Streaming SSE (Server-Sent Events) from the `/completion` endpoint
- Fill-in-the-Middle (FIM) prompting for code completion
- Structuring a multi-mode interactive coding assistant
- Difference between llama.cpp direct vs Ollama for large models

## llama.cpp vs Ollama for Qwen3 Coder

| Feature | llama.cpp (this guide) | Ollama |
|---------|------------------------|--------|
| Context window | Set freely (`--ctx-size`) | Limited by Ollama preset |
| FIM prompting | Direct control | Not exposed |
| Startup time | ~10–30s | ~5–10s |
| API | Custom HTTP `/completion` | OpenAI-compatible |
| Best for | Large GGUF + fine control | Quick experiments |
| GPU layers | `--n-gpu-layers 999` | Automatic |

Use llama.cpp when you need the full 32k context window or FIM prompting.

## Prerequisites

### 1 — Set MAXN Mode

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
jtop   # Confirm GPU clock is locked at maximum
```

### 2 — Build llama.cpp with CUDA

```bash
git clone https://github.com/ggerganov/llama.cpp.git ~/llama.cpp
cd ~/llama.cpp
mkdir build && cd build

cmake .. \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_F16=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DGGML_CUDA_ARCH=sm_87

make -j12
# Binaries land in ~/llama.cpp/build/bin/
```

### 3 — Download Qwen3 Coder GGUF

```bash
mkdir -p ~/models/qwen3-coder
cd ~/models/qwen3-coder

# Qwen2.5-Coder 7B — recommended starting point (~4.7 GB)
wget -O qwen2.5-coder-7b-q4_k_m.gguf \
  "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf"

# Verify download
ls -lh ~/models/qwen3-coder/
```

> **Qwen3-Coder 32B (if available):** Requires ~20 GB. Use `Q4_K_M` quantization.
> Download from `Qwen/Qwen3-Coder-32B-Instruct-GGUF` on HuggingFace when released.

### 4 — Start the llama.cpp Server

```bash
~/llama.cpp/build/bin/llama-server \
  -m ~/models/qwen3-coder/qwen2.5-coder-7b-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --n-gpu-layers 999 \
  --ctx-size 16384 \
  --threads 8 \
  --parallel 2 \
  --log-disable
```

Confirm it's running:
```bash
curl -s http://localhost:8080/health
# {"status":"ok"}
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/qwen3_coder
cd ~/projects/qwen3_coder
python3 -m venv venv
source venv/bin/activate
pip install requests rich
```

---

## Step 2 — Create the Pair Programmer

Save as `~/projects/qwen3_coder/qwen3_coder.py`:

```python
#!/usr/bin/env python3
"""
Qwen3 Coder — AI Pair Programmer via llama.cpp HTTP Server
Streaming code generation, FIM completion, explanation, debugging.

llama.cpp HTTP API overview:
  POST /completion          — single-turn generation (streaming or not)
  POST /v1/chat/completions — OpenAI-compatible chat (with history)
  GET  /health              — server status
  GET  /props               — model info

Temperature guide for coding:
  0.05–0.1  — deterministic: tests, docstrings, formatting
  0.15–0.25 — balanced: code generation, refactoring
  0.4–0.6   — creative: architecture brainstorm, explanations
"""
import json
import time
import subprocess
import sys
import requests
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.rule import Rule

console = Console()

SERVER_URL = "http://localhost:8080"

TEMP_CODE    = 0.1   # Deterministic output for code gen
TEMP_DEBUG   = 0.2   # Slightly more flexible for debugging
TEMP_EXPLAIN = 0.45  # More natural language explanation
TEMP_TEST    = 0.1   # Tests must be precise

# Qwen2.5-Coder chat template tokens
CHAT_PREFIX = "<|im_start|>system\nYou are Qwen, a helpful coding assistant.<|im_end|>\n<|im_start|>user\n"
CHAT_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n"

# FIM tokens for Qwen2.5-Coder
FIM_PREFIX = "<|fim_prefix|>"
FIM_SUFFIX = "<|fim_suffix|>"
FIM_MIDDLE = "<|fim_middle|>"


def check_server() -> bool:
    """Return True if llama.cpp server is reachable."""
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=3)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def stream_completion(prompt: str, temperature: float = TEMP_CODE,
                      max_tokens: int = 1024, label: str = "Output") -> str:
    """
    POST to /completion with stream=True.
    llama.cpp sends SSE lines:  data: {"content": "...", "stop": false}
    Prints tokens as they arrive; returns the full response.
    """
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "repeat_penalty": 1.1,
        "stream": True,
        "stop": ["<|im_end|>", "<|endoftext|>"],
    }

    start = time.time()
    full_response = ""

    console.print(f"\n[bold cyan]{label}:[/bold cyan]\n")
    try:
        with requests.post(
            f"{SERVER_URL}/completion",
            json=payload,
            stream=True,
            timeout=120,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8")
                if text.startswith("data: "):
                    try:
                        obj = json.loads(text[6:])
                        token = obj.get("content", "")
                        print(token, end="", flush=True)
                        full_response += token
                        if obj.get("stop", False):
                            break
                    except json.JSONDecodeError:
                        continue
    except requests.exceptions.ConnectionError:
        console.print("[red]Cannot connect to llama.cpp server on port 8080.[/red]")
        console.print("Start it with: [dim]~/llama.cpp/build/bin/llama-server -m ~/models/qwen3-coder/... --port 8080 --n-gpu-layers 999[/dim]")
        return ""

    elapsed = time.time() - start
    tokens_approx = len(full_response.split())
    print()
    console.print(f"[dim]  {elapsed:.1f}s | ~{tokens_approx} tokens[/dim]")
    return full_response


def generate_code(task: str, language: str = "python",
                  max_tokens: int = 1024) -> str:
    """
    Generate code from a natural language task description.
    Wraps the task in the Qwen chat template and requests a code block.
    """
    prompt = (
        f"{CHAT_PREFIX}"
        f"Write complete, working {language} code for:\n\n{task}\n\n"
        f"Return ONLY the code, no explanations. Use proper formatting."
        f"{CHAT_SUFFIX}```{language}\n"
    )
    return stream_completion(
        prompt, TEMP_CODE, max_tokens,
        label=f"Generating {language} code"
    )


def explain_code(code: str, detail: str = "developer") -> str:
    """
    Explain what code does.
    detail: 'beginner' | 'developer' | 'senior'
    """
    depth = {
        "beginner": "Explain line by line in plain English for someone new to programming.",
        "developer": "Explain the logic, patterns used, and any edge cases.",
        "senior": "Explain design decisions, performance implications, and potential improvements.",
    }.get(detail, "Explain the logic, patterns used, and any edge cases.")

    prompt = (
        f"{CHAT_PREFIX}"
        f"```\n{code}\n```\n\n{depth}"
        f"{CHAT_SUFFIX}"
    )
    return stream_completion(prompt, TEMP_EXPLAIN, 1024, label="Explanation")


def debug_code(code: str, error: str = "") -> str:
    """
    Find bugs and return fixed code with explanation.
    Provide the error message if you have one — it dramatically improves accuracy.
    """
    error_section = f"\n\nError message:\n```\n{error}\n```" if error else ""
    prompt = (
        f"{CHAT_PREFIX}"
        f"Find and fix bugs in this code:{error_section}\n\n```\n{code}\n```\n\n"
        f"Return:\n1. What the bug(s) are\n2. The fixed code\n3. Why the fix works"
        f"{CHAT_SUFFIX}"
    )
    return stream_completion(prompt, TEMP_DEBUG, 1500, label="Debug Analysis")


def generate_tests(code: str, language: str = "python",
                   framework: str = "pytest") -> str:
    """
    Generate unit tests for the given code.
    Tests edge cases: empty input, None, boundary values, type errors.
    """
    prompt = (
        f"{CHAT_PREFIX}"
        f"Write comprehensive {framework} unit tests for this {language} code.\n\n"
        f"```{language}\n{code}\n```\n\n"
        f"Test coverage must include: happy path, edge cases (empty/None/boundary), and error cases."
        f"{CHAT_SUFFIX}```{language}\n"
    )
    return stream_completion(prompt, TEMP_TEST, 1024, label=f"Tests ({framework})")


def fim_complete(prefix: str, suffix: str = "", max_tokens: int = 256) -> str:
    """
    Fill-in-the-Middle (FIM) code completion.
    FIM lets you complete code between a prefix AND a suffix —
    unlike standard completion which only appends to the end.

    Example:
        prefix = "def calculate_area(radius):\n    "
        suffix = "\n    return area"
        → model fills in the middle: "area = 3.14159 * radius ** 2"
    """
    if suffix:
        # Structured FIM prompt: <prefix>CODE_BEFORE<suffix>CODE_AFTER<middle>
        prompt = f"{FIM_PREFIX}{prefix}{FIM_SUFFIX}{suffix}{FIM_MIDDLE}"
    else:
        # Simple prefix-only completion
        prompt = f"{FIM_PREFIX}{prefix}{FIM_MIDDLE}"

    return stream_completion(
        prompt, TEMP_CODE, max_tokens,
        label="FIM Completion"
    )


def refactor_code(code: str, goal: str = "readability") -> str:
    """
    Refactor code toward a specific goal.
    goal: 'readability' | 'performance' | 'pythonic' | 'maintainability'
    """
    goals = {
        "readability":     "Improve readability: clearer names, shorter functions, better comments.",
        "performance":     "Optimize for performance: reduce loops, use built-ins, avoid redundancy.",
        "pythonic":        "Make it more Pythonic: list comprehensions, context managers, type hints.",
        "maintainability": "Improve maintainability: single responsibility, reduce coupling, add docstrings.",
    }
    goal_desc = goals.get(goal, goals["readability"])
    prompt = (
        f"{CHAT_PREFIX}"
        f"Refactor this code. Goal: {goal_desc}\n\n"
        f"Original:\n```\n{code}\n```\n\n"
        f"Return ONLY the refactored code with a brief comment before each major change."
        f"{CHAT_SUFFIX}"
    )
    return stream_completion(prompt, TEMP_DEBUG, 1500, label=f"Refactor ({goal})")


def run_and_explain(code: str) -> None:
    """
    Execute Python code in a subprocess and display stdout/stderr.
    Then ask the model to explain any errors.
    """
    console.print(Rule("Running Code"))
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=30,
    )
    if result.stdout:
        console.print(f"[green]STDOUT:[/green]\n{result.stdout}")
    if result.stderr:
        console.print(f"[red]STDERR:[/red]\n{result.stderr}")
        console.print(Rule("Explaining Error"))
        debug_code(code, result.stderr)
    if result.returncode == 0 and not result.stdout:
        console.print("[dim]No output (returned 0)[/dim]")


def show_server_status() -> None:
    """Display model info from the /props endpoint."""
    try:
        props = requests.get(f"{SERVER_URL}/props", timeout=5).json()
        model_name = props.get("default_generation_settings", {}).get("model", "unknown")
        ctx_size   = props.get("default_generation_settings", {}).get("n_ctx", "?")
        console.print(Panel.fit(
            f"[bold]Server:[/bold] {SERVER_URL}\n"
            f"[bold]Model:[/bold] {model_name}\n"
            f"[bold]Context:[/bold] {ctx_size} tokens",
            title="llama.cpp Status",
            border_style="green",
        ))
    except Exception as e:
        console.print(f"[red]Status check failed: {e}[/red]")


# ── Interactive CLI ──────────────────────────────────────────────────────────

def main():
    if not check_server():
        console.print(Panel.fit(
            "[red]llama.cpp server not running on port 8080[/red]\n\n"
            "Start it with:\n"
            "[dim]~/llama.cpp/build/bin/llama-server \\\n"
            "  -m ~/models/qwen3-coder/qwen2.5-coder-7b-q4_k_m.gguf \\\n"
            "  --host 0.0.0.0 --port 8080 \\\n"
            "  --n-gpu-layers 999 --ctx-size 16384[/dim]",
            border_style="red",
        ))
        return

    show_server_status()
    console.print(Panel.fit(
        "[bold cyan]Qwen3 Coder — AI Pair Programmer[/bold cyan]\n"
        "[dim]Direct llama.cpp HTTP server | Streaming output | FIM completion[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]gen[/cyan]      Generate code from description")
    console.print("  [cyan]explain[/cyan]  Explain code")
    console.print("  [cyan]debug[/cyan]    Find and fix bugs (with optional error message)")
    console.print("  [cyan]test[/cyan]     Generate unit tests")
    console.print("  [cyan]fim[/cyan]      Fill-in-the-Middle completion")
    console.print("  [cyan]refactor[/cyan] Refactor toward a goal")
    console.print("  [cyan]run[/cyan]      Execute Python code + explain errors")
    console.print("  [cyan]status[/cyan]   Show server status")
    console.print("  [cyan]quit[/cyan]     Exit\n")

    last_code = ""

    while True:
        try:
            cmd = console.input("[bold blue]coder>[/bold blue] ").strip().lower()
            if not cmd:
                continue
            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "gen":
                task = console.input("Task description: ").strip()
                lang = console.input("Language [python]: ").strip() or "python"
                last_code = generate_code(task, lang)

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
                detail = console.input("Detail level [beginner/developer/senior]: ").strip() or "developer"
                explain_code(last_code, detail)

            elif cmd == "debug":
                console.print("Paste buggy code (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                last_code = "\n".join(lines)
                error_msg = console.input("Error message (optional, Enter to skip): ").strip()
                debug_code(last_code, error_msg)

            elif cmd == "test":
                if not last_code:
                    console.print("Paste code (blank line to finish):")
                    lines = []
                    while True:
                        line = input()
                        if not line and lines:
                            break
                        lines.append(line)
                    last_code = "\n".join(lines)
                lang = console.input("Language [python]: ").strip() or "python"
                fw   = console.input("Framework [pytest]: ").strip() or "pytest"
                generate_tests(last_code, lang, fw)

            elif cmd == "fim":
                console.print("Paste PREFIX (code before the gap), blank line to finish:")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                prefix = "\n".join(lines)
                console.print("Paste SUFFIX (code after the gap, optional, blank line to skip):")
                slines = []
                while True:
                    line = input()
                    if not line:
                        break
                    slines.append(line)
                suffix = "\n".join(slines)
                fim_complete(prefix, suffix)

            elif cmd == "refactor":
                if not last_code:
                    console.print("Paste code (blank line to finish):")
                    lines = []
                    while True:
                        line = input()
                        if not line and lines:
                            break
                        lines.append(line)
                    last_code = "\n".join(lines)
                goal = console.input("Goal [readability/performance/pythonic/maintainability]: ").strip() or "readability"
                last_code = refactor_code(last_code, goal)

            elif cmd == "run":
                if not last_code:
                    console.print("Paste Python code (blank line to finish):")
                    lines = []
                    while True:
                        line = input()
                        if not line and lines:
                            break
                        lines.append(line)
                    last_code = "\n".join(lines)
                run_and_explain(last_code)

            elif cmd == "status":
                show_server_status()

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
# Terminal 1: start the llama.cpp server (keep it running)
sudo nvpmodel -m 0 && sudo jetson_clocks
~/llama.cpp/build/bin/llama-server \
  -m ~/models/qwen3-coder/qwen2.5-coder-7b-q4_k_m.gguf \
  --host 0.0.0.0 --port 8080 \
  --n-gpu-layers 999 --ctx-size 16384 \
  --log-disable

# Terminal 2: run the client
cd ~/projects/qwen3_coder
source venv/bin/activate
python3 qwen3_coder.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Generate and Run Code

```
coder> gen
Task: Read a CSV file, compute the mean and std deviation of each column,
      and output a formatted summary table
Language: python

[code streams out]

coder> run
[executes the generated code — if it fails, model explains the error]
```

### Exercise 2: FIM — Fill in the Middle

FIM is more powerful than regular completion because you constrain **both ends**:

```
coder> fim

PREFIX:
def binary_search(arr: list, target: int) -> int:
    """Return index of target in sorted arr, or -1."""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) //

SUFFIX:
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

The model must fill in the single missing expression `2` between the prefix and suffix.

Try harder ones:
```
PREFIX:
import hashlib

def hash_password(password: str, salt: str = "") -> str:

SUFFIX:
    # Returns hex string
```

### Exercise 3: Debug with Error Message

Generate buggy code, then fix it:

```
coder> debug
[paste this code:]

def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    seq = [0, 1]
    for i in range(2, n):
        seq.append(seq[i-1] + seq[i-2])
    return seq

fib = fibonacci(10)
print(f"10th Fibonacci: {fib[10]}")   # Bug: index out of range

Error message: IndexError: list index out of range
```

Compare the response with and without providing the error — the error message makes diagnosis much more precise.

### Exercise 4: Tests for Edge Cases

```
coder> gen
Task: A function that validates an email address — returns True/False
Language: python

[after code appears]

coder> test
[last code used automatically]
Framework: pytest
```

The test suite should cover: valid email, missing @, missing domain, None input, empty string, spaces.

### Exercise 5: Refactor for Different Goals

Take the same function and refactor it three ways:

```
coder> gen
Task: Count word frequency in a text string, return top-N words as a dict
Language: python

coder> refactor
Goal: pythonic
[note the use of Counter, dict comprehensions]

coder> refactor
Goal: performance
[note the algorithmic changes]
```

Compare the three versions — same logic, different style priorities.

---

## Expected Output

```
coder> gen
Task: Parse a JSON file and find all keys containing 'error' (case-insensitive)
Language: python

Generating python code:

def find_error_keys(filepath: str) -> list[str]:
    import json
    with open(filepath) as f:
        data = json.load(f)

    def search(obj, path=""):
        keys = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                current = f"{path}.{k}" if path else k
                if "error" in k.lower():
                    keys.append(current)
                keys.extend(search(v, current))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                keys.extend(search(item, f"{path}[{i}]"))
        return keys

    return search(data)

  4.2s | ~98 tokens
```

**Performance (MAXN, Qwen2.5-Coder 7B Q4_K_M):** ~18–22 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot connect to llama.cpp server` | Server not started — run the `llama-server` command first |
| Server starts then crashes | Model path wrong; verify with `ls -lh ~/models/qwen3-coder/` |
| Out of memory error | Reduce `--ctx-size` to 8192; or use Q4_K_M instead of Q8 |
| Very slow (< 5 tok/s) | Check MAXN: `sudo nvpmodel -m 0 && sudo jetson_clocks`; verify `--n-gpu-layers 999` |
| FIM output is garbage | Model may not support FIM tokens — try `qwen2.5-coder` variants specifically |
| Generated code has syntax errors | Add `stop: ["```"]` to stop payload to prevent the model overrunning the code block |
| `tegrastats` shows low GPU% | Confirm `--n-gpu-layers 999` flag is set; default is CPU-only |

---

## Next Steps

- **[Codeqwen Assistant](codeqwen-assistant.md)** — Same capability via Ollama (easier setup)
- **[Granite Dev](granite-dev.md)** — Enterprise code review + security scanning
- **[Nomic Vectors](nomic-vectors.md)** — Embed your codebase for semantic search + RAG
