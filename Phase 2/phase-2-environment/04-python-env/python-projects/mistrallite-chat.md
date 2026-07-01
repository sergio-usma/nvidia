# MistralLite — Fast Single-Turn Chat Tool

MistralLite is fine-tuned for quick, focused answers — ideal for pipelines where you call the model programmatically and need fast, single-shot responses without conversation overhead.

---

## What You'll Learn

- Single-turn vs multi-turn chat: when each is appropriate
- Building a CLI tool with subcommands (chat, summarize, translate, explain)
- Using a model as a library function in your own scripts
- Piping text through the model from the terminal

## Prerequisites

```bash
docker exec ollama ollama pull mistrallite
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/lite_chat
cd ~/projects/lite_chat
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Tool

Save as `~/projects/lite_chat/lite_chat.py`:

```python
#!/usr/bin/env python3
"""
MistralLite — Fast single-turn chat tool.

Key difference from other chat bots:
- No conversation history stored (single-turn by default)
- Designed to be called from scripts, cron jobs, pipelines
- Each call is independent → fast, stateless, predictable
- Use mistral-chat.py when you need multi-turn conversation
"""
import sys
import time
import argparse
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

MODEL = "mistrallite"


def ask(prompt: str, system: str = "", temperature: float = 0.7,
        max_tokens: int = 1024, stream: bool = True) -> str:
    """
    Single-turn request — no history stored.
    This is the core function you'll call from your own scripts.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    start = time.time()

    if stream:
        response_text = ""
        for chunk in ollama.chat(
            model=MODEL,
            messages=messages,
            stream=True,
            options={"temperature": temperature, "num_predict": max_tokens},
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            response_text += token
        print()
        elapsed = time.time() - start
        tokens = len(response_text.split())
        console.print(f"[dim]  {elapsed:.1f}s[/dim]")
        return response_text
    else:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return response["message"]["content"]


# ── Specialized Task Functions ─────────────────────────────────────────────
# These wrap ask() with task-specific system prompts.
# This is the pattern for building AI-powered utilities.

def summarize(text: str, length: str = "brief") -> str:
    lengths = {
        "brief": "3 sentences",
        "medium": "a paragraph",
        "bullets": "5 bullet points"
    }
    system = f"You are a summarizer. Summarize in {lengths.get(length, '3 sentences')}."
    return ask(f"Summarize:\n\n{text}", system=system, temperature=0.3)


def translate(text: str, target_lang: str) -> str:
    system = f"You are a translator. Translate to {target_lang}. Return ONLY the translation."
    return ask(text, system=system, temperature=0.1)


def explain(term: str, level: str = "beginner") -> str:
    levels = {
        "beginner": "a complete beginner with no technical background",
        "developer": "an experienced software developer",
        "expert": "a domain expert"
    }
    system = f"Explain to {levels.get(level, levels['beginner'])}. Be clear and concise."
    return ask(f"Explain: {term}", system=system, temperature=0.5)


def improve_text(text: str, goal: str = "clarity") -> str:
    goals = {
        "clarity": "clearer and more readable",
        "professional": "more professional and formal",
        "concise": "shorter without losing meaning",
        "engaging": "more engaging and interesting"
    }
    system = f"Rewrite to be {goals.get(goal, goals['clarity'])}. Return only the improved text."
    return ask(text, system=system, temperature=0.4)


# ── Interactive Mode ───────────────────────────────────────────────────────

def interactive():
    """Simple interactive mode for quick Q&A."""
    console.print(Panel.fit(
        "[bold cyan]MistralLite Fast Chat[/bold cyan]\n"
        "[dim]Single-turn mode — no history. Commands: /summarize /translate /explain /improve /quit[/dim]",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                parts = user_input[1:].split(None, 1)
                cmd = parts[0].lower()

                if cmd in ("quit", "exit", "q"):
                    break

                elif cmd == "summarize":
                    if len(parts) > 1:
                        text = parts[1]
                    else:
                        console.print("Paste text (blank line to end):")
                        lines = []
                        while True:
                            line = input()
                            if not line and lines:
                                break
                            lines.append(line)
                        text = "\n".join(lines)
                    length = console.input("Length [brief/medium/bullets]: ").strip() or "brief"
                    summarize(text, length)

                elif cmd == "translate":
                    lang = console.input("Translate to: ").strip()
                    if len(parts) > 1:
                        translate(parts[1], lang)
                    else:
                        text = console.input("Text: ")
                        translate(text, lang)

                elif cmd == "explain":
                    term = parts[1] if len(parts) > 1 else console.input("What to explain: ")
                    level = console.input("Level [beginner/developer/expert]: ").strip() or "beginner"
                    explain(term, level)

                elif cmd == "improve":
                    console.print("Paste text to improve (blank line to end):")
                    lines = []
                    while True:
                        line = input()
                        if not line and lines:
                            break
                        lines.append(line)
                    text = "\n".join(lines)
                    goal = console.input("Goal [clarity/professional/concise/engaging]: ").strip() or "clarity"
                    improve_text(text, goal)

                else:
                    console.print("[yellow]Unknown command[/yellow]")
                continue

            # Regular question
            ask(user_input)

        except KeyboardInterrupt:
            break


# ── CLI Argument Mode ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MistralLite — Fast AI tool")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommands for scripting
    chat_p = subparsers.add_parser("chat", help="Ask a question")
    chat_p.add_argument("question", nargs="?", help="Question to ask")

    sum_p = subparsers.add_parser("summarize", help="Summarize text")
    sum_p.add_argument("text", nargs="?", help="Text or read from stdin")
    sum_p.add_argument("--length", choices=["brief", "medium", "bullets"], default="brief")

    tr_p = subparsers.add_parser("translate", help="Translate text")
    tr_p.add_argument("target", help="Target language")
    tr_p.add_argument("text", nargs="?", help="Text or read from stdin")

    args = parser.parse_args()

    if args.command == "chat":
        text = args.question or sys.stdin.read().strip()
        ask(text, stream=False)
        result = ask(text, stream=True)

    elif args.command == "summarize":
        text = args.text or sys.stdin.read().strip()
        summarize(text, args.length)

    elif args.command == "translate":
        text = args.text or sys.stdin.read().strip()
        translate(text, args.target)

    else:
        interactive()


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/lite_chat
source venv/bin/activate

# Interactive mode
python3 lite_chat.py

# Or use as CLI tool:
python3 lite_chat.py chat "What is the Jetson unified memory architecture?"
python3 lite_chat.py summarize --length bullets "Long article text..."

# Pipe from stdin (great for scripting):
cat my_document.txt | python3 lite_chat.py summarize
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Summarize a Long Text
```
/summarize
Paste text...
Length: bullets
```

### Exercise 2: Translate to Multiple Languages
```
/translate
Translate to: Spanish
Text: The Jetson AGX Orin has 64GB of unified memory and 275 TOPS of AI performance.
```

Then repeat with French, German, Japanese.

### Exercise 3: Explain Technical Concepts at Different Levels
```
/explain
What to explain: CUDA
Level: beginner
```
Then:
```
/explain CUDA
Level: expert
```
Compare the two outputs — same model, very different responses based on system prompt.

### Exercise 4: Use as a Pipe Tool

```bash
# Summarize a local file
cat ~/projects/any_script.py | python3 lite_chat.py summarize

# Translate a file
cat README.md | python3 lite_chat.py translate Spanish
```

---

## Expected Output

```
You: What is quantization in the context of LLMs?

Quantization reduces the precision of model weights from 32-bit floats
to lower bit formats (8-bit, 4-bit). A 7B model shrinks from 14GB (FP16)
to ~4GB (Q4_K_M) with minimal quality loss. This makes large models fit
in devices like the Jetson AGX Orin's 64GB unified memory.

  1.8s
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mistrallite not found` | `docker exec ollama ollama pull mistrallite` |
| Empty response from stdin pipe | Check `sys.stdin.read()` got data: `echo "test" \| python3 lite_chat.py chat` |
| Slow | `sudo nvpmodel -m 0 && sudo jetson_clocks` |

---

## Next Steps

- **[Mistral Chat](mistral-chat.md)** — Multi-turn conversation with history
- **[Nemo Assistant](nemo-assistant.md)** — Larger Mistral-Nemo model
