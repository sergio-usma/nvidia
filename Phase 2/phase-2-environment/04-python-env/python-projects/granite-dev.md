# Granite 3.3 — Enterprise Code Review Tool

IBM's Granite 3.3 is designed specifically for enterprise software tasks: code review, security analysis, documentation generation, and standards compliance. It follows enterprise coding conventions and provides structured, actionable feedback — making it ideal for CI/CD pipelines and pull request automation.

---

## What You'll Learn

- How enterprise-focused models differ from general chat models
- Building a multi-command code review tool (review, security, docs, refactor)
- Parsing structured AI feedback with severity levels
- Automating code review as a pre-commit or CI step

## Prerequisites

```bash
# Pull the model (~4.9 GB)
docker exec ollama ollama pull granite3.3

# Verify
docker exec ollama ollama list | grep granite
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/granite_dev
cd ~/projects/granite_dev
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Enterprise Review Tool

Save as `~/projects/granite_dev/granite_dev.py`:

```python
#!/usr/bin/env python3
"""
Granite 3.3 — Enterprise Code Review Tool
IBM's enterprise-tuned model for production-quality code analysis.

Features:
- Code review with severity-tagged issues
- Security vulnerability scanning (OWASP patterns)
- Docstring and README generation
- Refactoring suggestions with before/after
- Batch file review
"""
import sys
import time
from pathlib import Path
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown

console = Console()
MODEL = "granite3.3"
TEMP_REVIEW = 0.2   # Low temperature for consistent, deterministic review
TEMP_DOCS = 0.4     # Slightly higher for more natural prose


def review_code(code: str, language: str = "python", focus: str = "") -> str:
    """
    Review code for issues, bugs, and enterprise best practices.
    Returns structured feedback with severity levels (HIGH/MEDIUM/LOW).
    """
    focus_line = f"\nPay particular attention to: {focus}" if focus else ""
    prompt = f"""You are a senior software engineer conducting a code review.
Review this {language} code for enterprise best practices.{focus_line}

Structure your response as:
## Summary
[1-2 sentence overall assessment]

## Issues Found
[List each issue with: SEVERITY (HIGH/MEDIUM/LOW) | Category | Description | Line reference if applicable]

## Recommendations
[Numbered list of actionable improvements]

Code to review:
```{language}
{code}
```"""

    start = time.time()
    response_text = ""

    print(f"\n\033[94mGranite Review:\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": TEMP_REVIEW, "num_predict": 2048},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        response_text += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return response_text


def security_scan(code: str, language: str = "python") -> str:
    """
    Scan code for security vulnerabilities.
    Checks for OWASP Top 10 patterns: injection, XSS, hardcoded secrets,
    insecure deserialization, missing auth checks, etc.
    """
    prompt = f"""You are a security engineer. Perform a security audit of this {language} code.

Check for:
- Injection vulnerabilities (SQL, command, path traversal)
- Hardcoded credentials or API keys
- Insecure cryptography or hashing
- Missing input validation
- Insecure deserialization
- Authentication/authorization issues
- Information exposure in error messages

Format each finding as:
VULN | SEVERITY | CWE | Description | Remediation

Code:
```{language}
{code}
```

If no vulnerabilities found, confirm the scan and note any security best practices being followed."""

    start = time.time()
    response_text = ""

    print(f"\n\033[91mSecurity Scan:\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": TEMP_REVIEW, "num_predict": 1024},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        response_text += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return response_text


def generate_docs(code: str, language: str = "python") -> str:
    """
    Generate documentation: docstrings, type hints, and a README summary.
    Returns the documented version of the code.
    """
    prompt = f"""You are a technical writer and senior developer. Add comprehensive documentation to this {language} code.

Add:
- Module-level docstring
- Function/class docstrings with Args, Returns, Raises sections
- Type hints (for Python)
- Inline comments for complex logic only (not obvious code)

Return ONLY the documented code — no explanation text around it.

Original code:
```{language}
{code}
```"""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": TEMP_DOCS, "num_predict": 2048},
    )
    return response["message"]["content"]


def suggest_refactor(code: str, language: str = "python") -> str:
    """
    Suggest refactoring improvements with before/after examples.
    Focuses on: SOLID principles, DRY, readability, performance.
    """
    prompt = f"""You are a senior software architect. Suggest refactoring improvements for this {language} code.

Focus on:
- SOLID principles (Single Responsibility, Open/Closed, etc.)
- DRY (Don't Repeat Yourself)
- Performance bottlenecks
- Readability and naming conventions
- Error handling improvements

For each suggestion, show:
BEFORE: [original snippet]
AFTER: [improved snippet]
WHY: [explanation]

Code:
```{language}
{code}
```"""

    start = time.time()
    response_text = ""

    print(f"\n\033[93mRefactor Suggestions:\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": TEMP_REVIEW, "num_predict": 2048},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        response_text += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return response_text


def review_file(filepath: str) -> None:
    """Read a file and run full enterprise review (code review + security scan)."""
    path = Path(filepath)
    if not path.exists():
        console.print(f"[red]File not found: {filepath}[/red]")
        return

    code = path.read_text()
    ext = path.suffix.lstrip(".")
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "sh": "bash", "go": "go", "java": "java", "rs": "rust",
    }
    language = lang_map.get(ext, "python")

    console.print(Panel(f"[bold]Reviewing:[/bold] {path.name} ({len(code.splitlines())} lines, {language})",
                        border_style="cyan"))

    # Show code preview
    syntax = Syntax(code[:1500], language, theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Code Preview (first 1500 chars)"))

    review_code(code, language)

    run_security = input("\nRun security scan? [y/N]: ").strip().lower()
    if run_security == "y":
        security_scan(code, language)

    run_refactor = input("Suggest refactoring? [y/N]: ").strip().lower()
    if run_refactor == "y":
        suggest_refactor(code, language)


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]Granite 3.3 — Enterprise Code Review[/bold cyan]\n"
        "[dim]IBM's enterprise model | Structured feedback | Local on Jetson[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]review[/cyan]    Review pasted code for issues")
    console.print("  [cyan]security[/cyan]  Security vulnerability scan")
    console.print("  [cyan]docs[/cyan]      Generate documentation for code")
    console.print("  [cyan]refactor[/cyan]  Suggest refactoring improvements")
    console.print("  [cyan]file[/cyan]      Review a file from disk")
    console.print("  [cyan]quit[/cyan]      Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]granite>[/bold blue] ").strip().lower()

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd in ("review", "security", "docs", "refactor"):
                lang = console.input("Language [python/javascript/bash/go]: ").strip() or "python"
                console.print("Paste code (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if not lines:
                    continue
                code = "\n".join(lines)

                if cmd == "review":
                    focus = console.input("Focus area (optional, e.g. 'error handling'): ").strip()
                    review_code(code, lang, focus)
                elif cmd == "security":
                    security_scan(code, lang)
                elif cmd == "docs":
                    result = generate_docs(code, lang)
                    syntax = Syntax(result, lang, theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title="Documented Code"))

                    save = console.input("Save documented version? [y/N]: ").strip().lower()
                    if save == "y":
                        fname = console.input("Filename: ").strip()
                        Path(fname).write_text(result)
                        console.print(f"[green]Saved to {fname}[/green]")
                elif cmd == "refactor":
                    suggest_refactor(code, lang)

            elif cmd == "file":
                filepath = console.input("Path to file: ").strip()
                review_file(filepath)

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
cd ~/projects/granite_dev
source venv/bin/activate
python3 granite_dev.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Review Intentionally Bad Code

```
granite> review
Language: python

Paste code:
import pickle, os

def load_user(filename):
    data = open(filename, 'rb').read()
    return pickle.loads(data)

def run_command(user_input):
    os.system("echo " + user_input)

API_KEY = "sk-prod-abc123secret"
password = "admin123"
```

Expected: Granite should flag insecure deserialization (pickle), command injection, and hardcoded secrets.

### Exercise 2: Security Scan a Common Pattern

```
granite> security
Language: python

def get_user(db, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)

def login(username, password):
    import hashlib
    hashed = hashlib.md5(password.encode()).hexdigest()
    return check_db(username, hashed)
```

Expected: SQL injection (string formatting in query) and weak MD5 hashing flagged.

### Exercise 3: Generate Docs for a Utility Function

```
granite> docs
Language: python

def process_batch(items, func, workers=4, timeout=30):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(func, item): item for item in items}
        for f in as_completed(futures, timeout=timeout):
            results[futures[f]] = f.result()
    return results
```

The model should add module docstring, full function docstring with Args/Returns/Raises, and type hints.

### Exercise 4: Refactor Nested Code

```
granite> refactor
Language: python

def calculate_discount(price, customer_type, quantity):
    if customer_type == "premium":
        if quantity > 100:
            if price > 1000:
                return price * 0.7
            else:
                return price * 0.8
        else:
            return price * 0.9
    else:
        if quantity > 100:
            return price * 0.95
        else:
            return price
```

Expected: Granite suggests extracting discount tables, guard clauses, or a strategy pattern to flatten the nesting.

### Exercise 5: Review a Real File

```
granite> file
Path: ~/projects/code_complete/code_complete.py
```

Review a file you wrote in the OpenCoder project — see what Granite finds!

---

## Expected Output

```
granite> security
Language: python
[paste SQL injection code]

Security Scan:

VULN | HIGH | CWE-89 | SQL Injection — f-string directly interpolates user input into query | Use parameterized queries: db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
VULN | MEDIUM | CWE-327 | Weak cryptography — MD5 is not suitable for password hashing | Use bcrypt, scrypt, or Argon2: import bcrypt; bcrypt.hashpw(...)

  2.3s
```

**Performance (MAXN, granite3.3):** ~15–20 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `granite3.3 not found` | `docker exec ollama ollama pull granite3.3` |
| Slow responses | granite3.3 is a larger model — enable MAXN: `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| Generic feedback | Add a specific `focus` area, e.g. "error handling" or "performance" |

---

## Next Steps

- **[CodeQwen Assistant](codeqwen-assistant.md)** — Multi-language IDE-like interface
- **[Qwen2.5 Debugger](qwen25-debugger.md)** — Bug detection and fixing
- **[OpenCoder](opencoder.md)** — Code completion tool
