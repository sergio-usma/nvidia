# Mistral-Nemo — Advanced Long-Context Assistant

Mistral-Nemo is a 12B parameter model with a 128k token context window — the largest context of any model in this series. It excels at processing long documents, multi-step reasoning, and complex multi-turn conversations. Use it when you need to reason over entire codebases, long reports, or technical papers.

---

## What You'll Learn

- How large context windows enable new workflows (document Q&A, code archaeology)
- Building a document-aware assistant that processes multiple files at once
- Context window management: how to fit large inputs without truncation
- Comparing response quality between small (7B) and large (12B) models

## Why Mistral-Nemo?

| Model | Parameters | Context | Speed (Jetson) | Best For |
|-------|-----------|---------|----------------|---------|
| mistral:7b | 7B | 32k | ~20 tok/s | General chat |
| mistral-nemo | 12B | 128k | ~12 tok/s | Long docs, complex tasks |
| mistral-nemo | 12B | 128k | ~12 tok/s | Multi-file code analysis |

The 128k context = ~96,000 words = an entire technical book at once.

## Prerequisites

```bash
# Pull the model (~7.1 GB)
docker exec ollama ollama pull mistral-nemo

# Verify
docker exec ollama ollama list | grep nemo
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/nemo_assistant
cd ~/projects/nemo_assistant
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Long-Context Assistant

Save as `~/projects/nemo_assistant/nemo_assistant.py`:

```python
#!/usr/bin/env python3
"""
Mistral-Nemo — Advanced Long-Context Assistant
12B model with 128k context window for complex, document-heavy tasks.

Use cases:
- Analyze entire codebases in one shot
- Q&A over long technical documents
- Multi-file summarization
- Complex multi-turn reasoning
- Comparing and contrasting long texts
"""
import time
import sys
from pathlib import Path
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()
MODEL = "mistral-nemo"

# Context window sizing guide:
# - 1 token ≈ 4 characters ≈ 0.75 words
# - 128k tokens ≈ 512k characters ≈ 96k words
# - Keep total (prompt + history + response) under 100k tokens for safety
MAX_CHARS = 300_000   # ~75k tokens input budget for documents


class NemoAssistant:
    """
    Long-context assistant with streaming, document loading, and history.

    The key advantage over smaller models:
    - Can hold entire files in context simultaneously
    - Maintains coherence over very long conversations
    - Better at following complex multi-step instructions
    """

    def __init__(self, system: str = "You are a helpful, knowledgeable assistant. "
                                    "Provide thorough, accurate responses."):
        self.system = system
        self.history = [{"role": "system", "content": system}]
        self.turn = 0
        self.loaded_docs: dict[str, str] = {}

    def chat(self, message: str, temperature: float = 0.7,
             max_tokens: int = 2048) -> str:
        """Send a message with full conversation history."""
        self.history.append({"role": "user", "content": message})
        self.turn += 1

        start = time.time()
        response_text = ""

        print(f"\n\033[94m[Turn {self.turn}] Nemo:\033[0m ", end="", flush=True)
        for chunk in ollama.chat(
            model=MODEL,
            messages=self.history,
            stream=True,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": 32768,  # Use 32k context for chat; increase for large docs
            },
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            response_text += token

        print()
        elapsed = time.time() - start
        tokens_approx = len(response_text.split())
        tok_s = tokens_approx / elapsed if elapsed > 0 else 0
        console.print(f"[dim]  {elapsed:.1f}s | ~{tok_s:.0f} tok/s | "
                      f"turn {self.turn} | history: {len(self.history)} msgs[/dim]")

        self.history.append({"role": "assistant", "content": response_text})
        return response_text

    def ask_about_document(self, question: str, document_text: str,
                           doc_name: str = "document") -> str:
        """
        Answer a question about a specific document.
        Uses single-turn to fit large documents in context.
        """
        # Truncate if too large
        if len(document_text) > MAX_CHARS:
            console.print(f"[yellow]Document truncated to {MAX_CHARS:,} chars "
                          f"(was {len(document_text):,})[/yellow]")
            document_text = document_text[:MAX_CHARS]

        prompt = f"""Here is the content of {doc_name}:

<document>
{document_text}
</document>

Question: {question}

Answer based on the document above. If the answer isn't in the document, say so."""

        start = time.time()
        response = ""

        print(f"\n\033[94mNemo (on {doc_name}):\033[0m ", end="", flush=True)
        for chunk in ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": self.system},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            options={
                "temperature": 0.3,    # Low temp for factual doc Q&A
                "num_predict": 2048,
                "num_ctx": 65536,      # 64k context for large documents
            },
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            response += token

        print()
        elapsed = time.time() - start
        console.print(f"[dim]  {elapsed:.1f}s[/dim]")
        return response

    def load_file(self, filepath: str) -> bool:
        """Load a file into the document store for later querying."""
        path = Path(filepath)
        if not path.exists():
            console.print(f"[red]File not found: {filepath}[/red]")
            return False

        content = path.read_text(errors="replace")
        self.loaded_docs[path.name] = content
        chars = len(content)
        tokens_est = chars // 4
        console.print(f"[green]Loaded {path.name}[/green] "
                      f"[dim]({chars:,} chars, ~{tokens_est:,} tokens)[/dim]")
        return True

    def ask_about_loaded_docs(self, question: str) -> str:
        """Query all loaded documents at once."""
        if not self.loaded_docs:
            console.print("[yellow]No documents loaded. Use 'load' first.[/yellow]")
            return ""

        # Combine all docs
        combined = ""
        for name, content in self.loaded_docs.items():
            combined += f"\n\n=== {name} ===\n{content}"

        return self.ask_about_document(question, combined, "loaded documents")

    def summarize_document(self, document_text: str, style: str = "bullets") -> str:
        """
        Summarize a long document.
        style: 'bullets' | 'executive' | 'technical'
        """
        styles = {
            "bullets": "5–10 bullet points covering the main points",
            "executive": "3 paragraphs: situation, key findings, recommendations",
            "technical": "detailed technical summary with all key specifications and numbers",
        }
        length_desc = styles.get(style, styles["bullets"])

        if len(document_text) > MAX_CHARS:
            document_text = document_text[:MAX_CHARS]

        prompt = f"""Summarize this document as {length_desc}:

{document_text}"""

        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.4, "num_predict": 1024, "num_ctx": 65536},
        )
        return response["message"]["content"]

    def compare_texts(self, text1: str, text2: str,
                      name1: str = "Text A", name2: str = "Text B") -> str:
        """Compare two documents or code snippets side by side."""
        prompt = f"""Compare and contrast these two texts. Identify:
1. Key similarities
2. Key differences
3. What each does better than the other
4. Which to use and when

=== {name1} ===
{text1[:20000]}

=== {name2} ===
{text2[:20000]}"""

        response = ""
        print(f"\n\033[94mComparison:\033[0m ", end="", flush=True)
        for chunk in ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            options={"temperature": 0.5, "num_predict": 2048, "num_ctx": 65536},
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            response += token
        print()
        return response

    def show_status(self) -> None:
        """Show current session state."""
        t = Table(title="Nemo Session Status")
        t.add_column("Property", style="cyan")
        t.add_column("Value")
        t.add_row("Model", MODEL)
        t.add_row("Turns", str(self.turn))
        t.add_row("History messages", str(len(self.history)))
        t.add_row("Loaded documents", str(len(self.loaded_docs)))
        for name, content in self.loaded_docs.items():
            t.add_row(f"  {name}", f"{len(content):,} chars (~{len(content)//4:,} tokens)")
        console.print(t)

    def reset(self) -> None:
        """Reset conversation but keep loaded documents."""
        system_msg = self.history[0]
        self.history = [system_msg]
        self.turn = 0
        console.print("[yellow]Conversation cleared (documents kept)[/yellow]")


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]Mistral-Nemo — Long-Context Assistant[/bold cyan]\n"
        "[dim]12B model | 128k context | Deep document analysis[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]chat[/cyan]      Multi-turn conversation mode")
    console.print("  [cyan]load[/cyan]      Load a file for document Q&A")
    console.print("  [cyan]ask[/cyan]       Ask a question about loaded docs")
    console.print("  [cyan]summarize[/cyan] Summarize a document")
    console.print("  [cyan]compare[/cyan]   Compare two text files")
    console.print("  [cyan]status[/cyan]    Show session info")
    console.print("  [cyan]reset[/cyan]     Clear conversation history")
    console.print("  [cyan]quit[/cyan]      Exit\n")

    nemo = NemoAssistant()

    # Check if user wants a custom system prompt
    custom_sys = console.input("Custom system prompt? [Enter to skip]: ").strip()
    if custom_sys:
        nemo.system = custom_sys
        nemo.history[0]["content"] = custom_sys
        console.print("[green]Custom persona set[/green]")

    console.print("\n[dim]Type /quit to exit at any time[/dim]\n")

    while True:
        try:
            cmd = console.input("[bold blue]nemo>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("/quit", "quit", "exit", "q"):
                break

            elif cmd == "chat":
                console.print("[dim]Conversation mode. /reset, /status, /quit[/dim]\n")
                while True:
                    msg = console.input("[green]You:[/green] ").strip()
                    if not msg:
                        continue
                    if msg.startswith("/"):
                        inner = msg[1:].lower()
                        if inner in ("quit", "q"):
                            break
                        elif inner == "reset":
                            nemo.reset()
                        elif inner == "status":
                            nemo.show_status()
                        continue
                    nemo.chat(msg)

            elif cmd == "load":
                filepath = console.input("File path: ").strip()
                nemo.load_file(filepath)

            elif cmd == "ask":
                if not nemo.loaded_docs:
                    console.print("[yellow]Load a document first with 'load'[/yellow]")
                    continue
                nemo.show_status()
                question = console.input("Question: ").strip()
                nemo.ask_about_loaded_docs(question)

            elif cmd == "summarize":
                filepath = console.input("File path (or leave blank to use loaded docs): ").strip()
                style = console.input("Style [bullets/executive/technical]: ").strip() or "bullets"

                if filepath:
                    path = Path(filepath)
                    if not path.exists():
                        console.print("[red]File not found[/red]")
                        continue
                    text = path.read_text(errors="replace")
                else:
                    if not nemo.loaded_docs:
                        console.print("[yellow]No document loaded. Use 'load' or specify a file path.[/yellow]")
                        continue
                    text = "\n\n".join(nemo.loaded_docs.values())

                with console.status("[bold green]Summarizing..."):
                    summary = nemo.summarize_document(text, style)
                console.print(Panel(Markdown(summary), title=f"Summary ({style})"))

            elif cmd == "compare":
                f1 = console.input("First file path: ").strip()
                f2 = console.input("Second file path: ").strip()
                p1, p2 = Path(f1), Path(f2)
                if not p1.exists() or not p2.exists():
                    console.print("[red]One or both files not found[/red]")
                    continue
                nemo.compare_texts(p1.read_text(), p2.read_text(), p1.name, p2.name)

            elif cmd == "status":
                nemo.show_status()

            elif cmd == "reset":
                nemo.reset()

            else:
                # Treat as chat message if not a command
                nemo.chat(cmd)

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
cd ~/projects/nemo_assistant
source venv/bin/activate
python3 nemo_assistant.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Long Conversation Memory Test

Enter `chat` mode and have a 10-turn conversation building on previous context:
```
You: I'm building a REST API for an inventory management system
You: It needs to track products, warehouses, and stock movements
You: What database schema would you recommend?
You: How would you handle concurrent updates to stock levels?
You: What caching strategy makes sense here?
```

Notice how Nemo maintains context across all turns — compare this to TinyLlama which would forget early messages.

### Exercise 2: Document Q&A

Load and analyze a large file:
```
nemo> load
File path: ~/projects/mistral_chat/mistral_chat.py

nemo> ask
Question: What personas are defined and what are their system prompts?

nemo> ask
Question: How does the conversation history trimming work?

nemo> ask
Question: What commands does the user have available?
```

### Exercise 3: Summarize a Long Config or Log File

```
nemo> summarize
File path: /etc/docker/daemon.json
Style: technical
```

Or summarize a large Python file:
```
nemo> summarize
File path: ~/projects/granite_dev/granite_dev.py
Style: bullets
```

### Exercise 4: Compare Two Implementations

Load two similar files and compare them:
```
nemo> compare
First file: ~/projects/mistral_chat/mistral_chat.py
Second file: ~/projects/tinyllama/edge_chat.py
```

Nemo should identify: sliding window vs full history, persona support differences, benchmark capabilities, etc.

### Exercise 5: Direct Chat for Complex Reasoning

Type a question directly (it goes straight to chat):
```
nemo> Explain the CAP theorem with a concrete example of a distributed inventory system where we must choose between consistency and availability during a network partition. Then recommend which to choose for an e-commerce system and why.
```

---

## Expected Output

```
nemo> chat
You: What's the architectural difference between a monolith and microservices?

[Turn 1] Nemo: The core difference comes down to deployment boundaries...
[proceeds with detailed multi-part answer]

  4.2s | ~12 tok/s | turn 1 | history: 3 msgs
```

**Performance (MAXN, mistral-nemo 12B):** ~10–14 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mistral-nemo not found` | `docker exec ollama ollama pull mistral-nemo` |
| OOM on large documents | Reduce `num_ctx` from 65536 to 16384; trim document to 50k chars |
| Slow for short queries | Use `mistral:7b` for quick questions; save Nemo for long docs |
| Context overflow warning | Keep total input under 100k tokens; use `status` to monitor |

---

## Next Steps

- **[Mistral Chat](mistral-chat.md)** — Faster multi-persona chat with mistral:7b
- **[Nomic Vectors](nomic-vectors.md)** — Add semantic search to document Q&A
- **[Qwen3 RAG](qwen3-rag.md)** — Full RAG pipeline for large document collections
