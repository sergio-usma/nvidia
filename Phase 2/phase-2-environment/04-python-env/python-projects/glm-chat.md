# GLM-4 Flash — Fast Bilingual Chat Tool

GLM-4 Flash is Zhipu AI's fast, bilingual (English/Chinese) chat model. It excels at rapid Q&A, summarization, and translation between English and Chinese. This project builds a practical bilingual assistant with streaming, conversation history, and a set of text processing utilities.

---

## What You'll Learn

- How bilingual models handle code-switching (mixing languages)
- Building a persistent conversation loop with history management
- Task-specific prompting for summarization, translation, and Q&A
- Using streaming vs non-streaming API calls

## Why GLM-4 Flash?

| Feature | GLM-4 Flash | Mistral 7B |
|---------|-------------|------------|
| English | Excellent | Excellent |
| Chinese | Native quality | Basic |
| Speed | ~25 tok/s | ~20 tok/s |
| Size | ~4.7 GB | ~4.1 GB |

If your project involves Chinese text, documents, or users — GLM-4 Flash is the clear choice.

## Prerequisites

```bash
# Pull the model (~4.7 GB)
docker exec ollama ollama pull glm4

# Verify
docker exec ollama ollama list | grep glm
```

> **Note:** The Ollama model tag is `glm4` (not `glm-4.7-flash`). Check with `ollama list` after pulling.

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/glm_chat
cd ~/projects/glm_chat
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Bilingual Chat Tool

Save as `~/projects/glm_chat/glm_chat.py`:

```python
#!/usr/bin/env python3
"""
GLM-4 Flash — Fast Bilingual Chat Tool
Zhipu AI's model: excellent English + native Chinese quality.

Key features:
- Auto-detects input language and responds in kind
- Translation between English and Chinese (and other languages)
- Fast streaming (~25 tok/s on Jetson)
- Persistent conversation history
- Text processing utilities (summarize, explain, translate)

When to use GLM-4 vs other models:
- Chinese text or users → GLM-4 (native quality)
- English-only tasks → mistral:7b or qwen2.5:7b
- Code tasks → qwen2.5-coder:7b
"""
import time
import sys
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()

# Check what GLM variant you have
# Try glm4 first, fall back to alternatives
MODEL = "glm4"


class GLMChat:
    """
    Bilingual chat session with history and task-specific modes.

    GLM-4 is special: it natively understands context switches between
    English and Chinese within the same conversation.
    """

    def __init__(self, system: str = "You are a helpful bilingual assistant "
                                     "fluent in both English and Chinese. "
                                     "Respond in the same language the user writes in."):
        self.system = system
        self.history = [{"role": "system", "content": system}]
        self.turn = 0
        self.total_tokens = 0
        self.total_time = 0.0

    def chat(self, message: str, temperature: float = 0.7,
             max_tokens: int = 2048) -> str:
        """Send a message. The model responds in the user's language."""
        self.history.append({"role": "user", "content": message})
        self.turn += 1

        # Trim history: keep system + last 20 messages
        if len(self.history) > 21:
            system_msg = self.history[0]
            self.history = [system_msg] + self.history[-20:]

        start = time.time()
        response_text = ""
        tokens = 0

        print(f"\n\033[94m[Turn {self.turn}] GLM:\033[0m ", end="", flush=True)
        for chunk in ollama.chat(
            model=MODEL,
            messages=self.history,
            stream=True,
            options={"temperature": temperature, "num_predict": max_tokens},
        ):
            token = chunk["message"]["content"]
            print(token, end="", flush=True)
            response_text += token
            tokens += 1

        print()
        elapsed = time.time() - start
        tok_s = tokens / elapsed if elapsed > 0 else 0
        console.print(f"[dim]  {elapsed:.1f}s | {tok_s:.1f} tok/s[/dim]")

        self.history.append({"role": "assistant", "content": response_text})
        self.total_tokens += tokens
        self.total_time += elapsed
        return response_text

    def translate(self, text: str, target_lang: str,
                  source_lang: str = "auto") -> str:
        """
        Translate text using GLM-4's native bilingual capability.
        Best results for English ↔ Chinese; also supports other languages.
        """
        if source_lang == "auto":
            from_note = "from its current language"
        else:
            from_note = f"from {source_lang}"

        prompt = (f"Translate the following text {from_note} to {target_lang}. "
                  f"Return ONLY the translation, nothing else:\n\n{text}")

        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 1024},
        )
        return response["message"]["content"]

    def summarize(self, text: str, length: str = "brief",
                  output_lang: str = "same") -> str:
        """
        Summarize text. GLM-4 can summarize Chinese and English equally well.
        output_lang: 'same' (match input), 'english', or 'chinese'
        """
        length_map = {
            "brief": "2-3 sentences",
            "medium": "one paragraph",
            "detailed": "3-5 paragraphs with key details",
            "bullets": "5-7 bullet points",
        }
        length_desc = length_map.get(length, length_map["brief"])
        lang_note = "" if output_lang == "same" else f" Write the summary in {output_lang}."

        prompt = (f"Summarize the following text in {length_desc}.{lang_note}\n\n{text}")

        start = time.time()
        response = ""
        for chunk in ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            options={"temperature": 0.3, "num_predict": 512},
        ):
            print(chunk["message"]["content"], end="", flush=True)
            response += chunk["message"]["content"]
        print()
        console.print(f"[dim]  {time.time() - start:.1f}s[/dim]")
        return response

    def explain_term(self, term: str, context: str = "",
                     output_lang: str = "english") -> str:
        """Explain a technical term or concept."""
        context_note = f" in the context of {context}" if context else ""
        prompt = (f"Explain '{term}'{context_note} clearly and concisely. "
                  f"Give a definition, why it matters, and one practical example. "
                  f"Write in {output_lang}.")

        response = ""
        print(f"\n\033[94mExplanation:\033[0m\n", flush=True)
        for chunk in ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            options={"temperature": 0.5, "num_predict": 1024},
        ):
            print(chunk["message"]["content"], end="", flush=True)
            response += chunk["message"]["content"]
        print()
        return response

    def reset(self) -> None:
        """Clear conversation history but keep system prompt."""
        system_msg = self.history[0]
        self.history = [system_msg]
        self.turn = 0
        console.print("[yellow]History cleared[/yellow]")

    def show_stats(self) -> None:
        """Display session statistics."""
        t = Table(title="GLM Session Stats")
        t.add_column("Metric", style="cyan")
        t.add_column("Value")
        t.add_row("Model", MODEL)
        t.add_row("Turns completed", str(self.turn))
        t.add_row("History messages", str(len(self.history) - 1))
        t.add_row("Total tokens", str(self.total_tokens))
        avg = self.total_tokens / self.total_time if self.total_time > 0 else 0
        t.add_row("Avg speed", f"{avg:.1f} tok/s")
        console.print(t)


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]GLM-4 Flash — Bilingual Assistant[/bold cyan]\n"
        "[dim]English + Chinese | Fast streaming | Local on Jetson[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]chat[/cyan]       Multi-turn conversation")
    console.print("  [cyan]translate[/cyan]  Translate text (EN ↔ ZH and more)")
    console.print("  [cyan]summarize[/cyan]  Summarize a text")
    console.print("  [cyan]explain[/cyan]    Explain a term or concept")
    console.print("  [cyan]quit[/cyan]       Exit\n")

    bot = GLMChat()

    while True:
        try:
            cmd = console.input("[bold blue]glm>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "chat":
                console.print("[dim]Chat mode. /reset, /stats, /quit[/dim]\n")
                while True:
                    msg = console.input("[green]You:[/green] ").strip()
                    if not msg:
                        continue
                    if msg.startswith("/"):
                        inner = msg[1:].lower()
                        if inner in ("quit", "q"):
                            break
                        elif inner == "reset":
                            bot.reset()
                        elif inner == "stats":
                            bot.show_stats()
                        continue
                    bot.chat(msg)

            elif cmd == "translate":
                console.print("[dim]Translation mode. /quit to exit[/dim]")
                console.print("[dim]Language codes: English, Chinese, Spanish, French, etc.[/dim]\n")
                while True:
                    text = console.input("[green]Text to translate:[/green] ").strip()
                    if text.lower() in ("/quit", "quit", "q"):
                        break
                    target = console.input("Translate to: ").strip() or "English"
                    result = bot.translate(text, target)
                    console.print(Panel(result, title=f"→ {target}", border_style="green"))

            elif cmd == "summarize":
                console.print("[dim]Summarize any text. Paste text, blank line to finish.[/dim]\n")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    text = "\n".join(lines)
                    length = console.input("Length [brief/medium/detailed/bullets]: ").strip() or "brief"
                    lang = console.input("Output language [same/english/chinese]: ").strip() or "same"
                    print("\n\033[94mSummary:\033[0m\n")
                    bot.summarize(text, length, lang)

            elif cmd == "explain":
                term = console.input("Term or concept to explain: ").strip()
                context = console.input("Context (optional, e.g. 'machine learning'): ").strip()
                lang = console.input("Explain in [english/chinese]: ").strip() or "english"
                bot.explain_term(term, context, lang)

            else:
                # Treat as direct chat message
                bot.chat(cmd)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    bot.show_stats()


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/glm_chat
source venv/bin/activate
python3 glm_chat.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Bilingual Conversation

Enter `chat` mode and mix languages:
```
You: Hello! Can you explain what a neural network is?
You: 你能用中文再解释一遍吗？(Can you explain again in Chinese?)
You: Now compare it to the human brain, in English
You: 有什么实际应用？(What are the practical applications?)
```

Notice: GLM-4 switches language automatically to match what you write.

### Exercise 2: Technical Translation

Enter `translate` mode:
```
Text: The Jetson AGX Orin features 2048 CUDA cores, 64GB LPDDR5 unified memory at 204.8 GB/s bandwidth, and delivers 275 TOPS of AI performance at up to 60W power consumption.
Translate to: Chinese
```

Then translate back:
```
Text: [paste the Chinese result]
Translate to: English
```

Compare the back-translation to the original — how accurately was the technical content preserved?

### Exercise 3: Cross-Language Summarization

Enter `summarize` mode and paste a long English article. Then:
```
Output language: chinese
```

You now have a Chinese executive summary of an English document — useful for creating bilingual documentation.

### Exercise 4: Explain Technical Concepts in Chinese

Enter `explain` mode:
```
Term: Docker container
Context: software deployment
Explain in: chinese
```

Then:
```
Term: CUDA unified memory
Context: NVIDIA Jetson GPU computing
Explain in: chinese
```

### Exercise 5: Direct Chat — Technical Q&A

Type any question directly without entering a mode:
```
glm> What is the difference between 量化 (quantization) in LLMs and quantization in digital signal processing?
```

GLM-4 will handle the mixed English/Chinese question fluently.

---

## Expected Output

```
glm> chat
You: 你好！什么是深度学习？

[Turn 1] GLM: 你好！深度学习是机器学习的一个分支...
[Full Chinese response about deep learning]
  3.1s | 24.8 tok/s

You: Can you give me an English example?

[Turn 2] GLM: Sure! A practical example of deep learning...
[English response building on previous context]
  2.8s | 25.2 tok/s
```

**Performance (MAXN, glm4):** ~22–28 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `glm4 not found` | `docker exec ollama ollama pull glm4` |
| Responds in wrong language | Add `"Respond in the same language the user writes in."` to system prompt |
| Chinese characters show as boxes | Your terminal doesn't support UTF-8; run `export LANG=en_US.UTF-8` |
| Slow performance | Enable MAXN: `sudo nvpmodel -m 0 && sudo jetson_clocks` |

---

## Next Steps

- **[GLM OCR](glm-ocr.md)** — GLM-4's vision for document and image understanding
- **[Nemotron Nano](nemotron-nano.md)** — Another bilingual chat option with translation pipeline
- **[Mistral Chat](mistral-chat.md)** — English-focused multi-persona chat
