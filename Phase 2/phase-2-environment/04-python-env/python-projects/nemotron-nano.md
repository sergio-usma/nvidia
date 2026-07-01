# Nemotron Nano — Fast Chat & Translation Hub

Nemotron Nano is NVIDIA's own compact model, optimized for edge AI devices. This project builds a multilingual chat tool with translation, language detection, and a quick Q&A mode perfect for building chatbots or voice assistant backends.

---

## What You'll Learn

- How to build a multilingual assistant with automatic language detection
- Translation pipelines: chain two model calls (detect → translate)
- Creating reusable "task wrappers" around a base chat function
- Building a simple REST API with FastAPI so other apps can use your model

## Prerequisites

```bash
# Pull the model (~2.0 GB)
docker exec ollama ollama pull nemotron-mini

# Alternative (check availability):
# docker exec ollama ollama pull nemotron:3b
docker exec ollama ollama list | grep -i nemotron
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/nemotron_nano
cd ~/projects/nemotron_nano
python3 -m venv venv
source venv/bin/activate
pip install ollama rich langdetect
```

---

## Step 2 — Create the Multilingual Assistant

Save as `~/projects/nemotron_nano/nemotron_chat.py`:

```python
#!/usr/bin/env python3
"""
Nemotron Nano — Multilingual Chat & Translation Hub
NVIDIA's edge-optimized model running locally on Jetson.

Features:
- Fast chat with conversation history
- Language detection (langdetect library)
- Translation to any language
- Q&A mode with source citations
- Response time tracking
"""
import time
import sys
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

console = Console()

# Use whatever nemotron variant you have
# Priority: nemotron-mini > nemotron:3b > llama3.2 (fallback)
MODEL = "nemotron-mini"

LANGUAGES = {
    "es": "Spanish",    "fr": "French",
    "de": "German",     "it": "Italian",
    "pt": "Portuguese", "zh": "Chinese",
    "ja": "Japanese",   "ko": "Korean",
    "ar": "Arabic",     "ru": "Russian",
    "hi": "Hindi",      "en": "English",
}


def detect_language(text: str) -> str:
    """Detect the language of a text string."""
    if LANGDETECT_AVAILABLE:
        try:
            code = detect(text)
            return LANGUAGES.get(code, f"unknown ({code})")
        except LangDetectException:
            return "unknown"
    return "detection unavailable (pip install langdetect)"


def chat_once(message: str, system: str = "", temperature: float = 0.7) -> tuple[str, float]:
    """
    Single-turn chat. Returns (response, tok_per_sec).
    No history stored — each call is independent.
    Use ChatSession below for multi-turn conversations.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    start = time.time()
    response_text = ""
    tokens = 0

    print("\n\033[94mNemotron:\033[0m ", end="", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=messages,
        stream=True,
        options={"temperature": temperature, "num_predict": 1024},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        response_text += token
        tokens += 1

    print()
    elapsed = time.time() - start
    tok_s = tokens / elapsed if elapsed > 0 else 0
    return response_text, tok_s


def translate(text: str, target_language: str,
              source_language: str = "auto") -> str:
    """
    Translate text to target language.
    If source_language is 'auto', detect it first.
    """
    if source_language == "auto" and LANGDETECT_AVAILABLE:
        detected = detect_language(text)
        if detected != target_language:
            source_language = detected
        else:
            return text  # Already in target language

    system = (
        f"You are a professional translator. "
        f"Translate the following text to {target_language}. "
        f"Return ONLY the translation, no explanations."
    )

    response, _ = chat_once(text, system=system, temperature=0.1)
    return response


def answer_question(question: str, context: str = "") -> str:
    """
    Answer a question, optionally with document context (mini-RAG).
    """
    if context:
        system = (
            "Answer the question using ONLY the provided context. "
            "If the context doesn't contain the answer, say so."
        )
        prompt = f"Context:\n{context}\n\nQuestion: {question}"
    else:
        system = "Answer the question accurately and concisely."
        prompt = question

    response, _ = chat_once(prompt, system=system, temperature=0.2)
    return response


class ChatSession:
    """Multi-turn conversation with history."""

    def __init__(self, system: str = "You are a helpful assistant."):
        self.messages = [{"role": "system", "content": system}]
        self.turn_count = 0

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        self.turn_count += 1

        start = time.time()
        response_text = ""

        print(f"\n\033[94m[Turn {self.turn_count}] Nemotron:\033[0m ", end="", flush=True)
        for chunk in ollama.chat(
            model=MODEL,
            messages=self.messages,
            stream=True,
            options={"temperature": 0.7},
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            response_text += token

        print()
        elapsed = time.time() - start
        console.print(f"[dim]  {elapsed:.1f}s[/dim]")

        self.messages.append({"role": "assistant", "content": response_text})
        return response_text

    def reset(self):
        system = self.messages[0]
        self.messages = [system]
        self.turn_count = 0


def show_language_info(text: str) -> None:
    """Show language detection result with rich formatting."""
    lang = detect_language(text)
    code = "unknown"
    if LANGDETECT_AVAILABLE:
        try:
            code = detect(text)
        except Exception:
            pass

    t = Table(title="Language Detection")
    t.add_column("Property", style="cyan")
    t.add_column("Value")
    t.add_row("Text", text[:100] + ("..." if len(text) > 100 else ""))
    t.add_row("Detected language", lang)
    t.add_row("Language code", code)
    console.print(t)


def main():
    console.print(Panel.fit(
        "[bold cyan]Nemotron Nano — Multilingual Assistant[/bold cyan]\n"
        f"[dim]Model: {MODEL} | Jetson AGX Orin[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Modes:[/bold]")
    console.print("  [cyan]1[/cyan] — Quick chat (single turn)")
    console.print("  [cyan]2[/cyan] — Conversation (multi-turn)")
    console.print("  [cyan]3[/cyan] — Translation tool")
    console.print("  [cyan]4[/cyan] — Q&A with context\n")

    mode = console.input("Select mode [1/2/3/4]: ").strip()

    if mode == "1":
        console.print("[dim]Quick chat — each message is independent. /quit to exit[/dim]\n")
        while True:
            msg = console.input("[green]You:[/green] ").strip()
            if msg.lower() in ("/quit", "quit", "q"):
                break
            if msg.startswith("/detect "):
                show_language_info(msg[8:])
                continue
            response, tok_s = chat_once(msg)
            console.print(f"[dim]  {tok_s:.1f} tok/s[/dim]")

    elif mode == "2":
        console.print("[dim]Conversation mode — model remembers context. /reset to clear. /quit to exit[/dim]\n")
        session = ChatSession()
        while True:
            msg = console.input("[green]You:[/green] ").strip()
            if not msg:
                continue
            if msg.lower() in ("/quit", "quit"):
                break
            if msg.lower() == "/reset":
                session.reset()
                console.print("[yellow]History cleared[/yellow]")
                continue
            session.chat(msg)

    elif mode == "3":
        console.print("[dim]Translation mode. /quit to exit[/dim]\n")
        target = console.input("Default target language: ").strip() or "Spanish"
        while True:
            text = console.input("[green]Text to translate:[/green] ").strip()
            if text.lower() in ("/quit", "quit"):
                break
            lang_override = console.input(f"Translate to [{target}]: ").strip() or target
            result = translate(text, lang_override)
            console.print(Panel(result, title=f"Translation → {lang_override}"))
            if LANGDETECT_AVAILABLE:
                show_language_info(text)

    elif mode == "4":
        console.print("[dim]Q&A with optional context (paste document, ask questions)[/dim]\n")
        console.print("Paste context document (blank line to skip):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        context = "\n".join(lines)

        while True:
            question = console.input("[green]Question:[/green] ").strip()
            if question.lower() in ("/quit", "quit"):
                break
            answer_question(question, context)
    else:
        console.print("[yellow]Invalid mode, starting quick chat[/yellow]")
        main()


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/nemotron_nano
source venv/bin/activate
python3 nemotron_chat.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Quick Multilingual Chat

Select mode `1`, then type in different languages:
```
You: Bonjour, comment allez-vous?
You: ¿Cuál es la capital de España?
You: 今日の天気はどうですか？
```

The model responds in the language you write in.

### Exercise 2: Translation Pipeline

Select mode `3`:
```
Text: The Jetson AGX Orin is a powerful edge AI computer with 64GB unified memory.
Target: Spanish

Then: French
Then: Japanese
```

Compare translations across languages.

### Exercise 3: Q&A with Context (Mini-RAG)

Select mode `4`, paste this as context:
```
The Jetson AGX Orin has 2048 CUDA cores, 12-core ARM CPU, and 64GB LPDDR5 memory.
MAXN mode enables maximum performance at up to 60W power consumption.
JetPack 6.2.2 includes CUDA 12.6, TensorRT 10.3, and cuDNN 9.3.
```

Then ask:
```
Question: How many CUDA cores does the Jetson have?
Question: What is included in JetPack 6.2.2?
Question: What is the power consumption in MAXN mode?
```

Notice how the model answers from context only — this is the foundation of RAG.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `nemotron-mini not found` | Try `docker exec ollama ollama pull nemotron-mini` or change MODEL to `llama3.2` |
| `langdetect` ImportError | `pip install langdetect` |
| Wrong translation | Specify source language explicitly; avoid short ambiguous texts |

---

## Next Steps

- **[Nemo Assistant](nemo-assistant.md)** — Larger Mistral-Nemo for advanced tasks
- **[Mistral Chat](mistral-chat.md)** — Persona-based chat with history
- **[Nomic Vectors](nomic-vectors.md)** — Add real RAG to this Q&A system
