# Mistral — Multi-Persona Chat Bot

Build a chat bot that supports multiple Mistral models and swappable personas (assistant, teacher, developer, creative writer). Demonstrates conversation history management, system prompts, and streaming output.

---

## What You'll Learn

- How system prompts shape the model's behavior and "persona"
- Managing conversation history (context window limits)
- Streaming responses for a real-time feel
- Switching models mid-session without losing history

## Prerequisites

```bash
# Pull the main Mistral model (~4.1 GB)
docker exec ollama ollama pull mistral:7b

# Optional: faster, smaller variant (~1.5 GB)
docker exec ollama ollama pull mistrallite
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/mistral_chat
cd ~/projects/mistral_chat
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Chat Bot

Save as `~/projects/mistral_chat/mistral_chat.py`:

```python
#!/usr/bin/env python3
"""
Mistral Multi-Persona Chat Bot
Switch between personas, models, and conversation modes.
Running locally on Jetson AGX Orin — no internet required.
"""
import sys
import time
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

console = Console()

# ── Persona Library ────────────────────────────────────────────────────────
# A persona is just a system prompt. The model uses it to set its "character".
# Experiment with different personas to see how they change responses.

PERSONAS = {
    "assistant": (
        "You are a helpful, accurate, and concise assistant. "
        "Answer questions clearly. When unsure, say so."
    ),
    "developer": (
        "You are a senior software engineer. Provide production-quality code. "
        "Use best practices, add error handling, and explain your decisions briefly."
    ),
    "teacher": (
        "You are a patient teacher. Explain concepts step by step with analogies. "
        "Check understanding by asking follow-up questions."
    ),
    "writer": (
        "You are a creative writer. Be imaginative and expressive. "
        "Use vivid descriptions and engaging narrative."
    ),
    "jetson": (
        "You are an expert on NVIDIA Jetson AGX Orin and embedded AI. "
        "Provide Jetson-specific advice with exact commands for JetPack 6.2.2. "
        "Always mention MAXN mode and jtop for GPU monitoring."
    ),
}

MODELS = {
    "1": ("mistral:7b", "Mistral 7B — general purpose, balanced"),
    "2": ("mistrallite", "MistralLite — smaller, faster"),
    "3": ("mistral-nemo", "Mistral Nemo 12B — larger context"),
}


class MistralChat:
    """
    Chat bot with conversation history and persona support.

    History works like this:
    - messages = [system_prompt, user_msg_1, assistant_msg_1, user_msg_2, ...]
    - The model sees ALL previous messages every request
    - This lets it remember what was said earlier
    - But: more history = more tokens = slower response
    - max_history trims old messages to keep responses fast
    """

    def __init__(self, model: str = "mistral:7b", persona: str = "assistant",
                 max_history: int = 20):
        self.model = model
        self.max_history = max_history
        self.messages = []
        self.set_persona(persona)

    def set_persona(self, persona_name: str) -> None:
        """Set or change the persona (system prompt)."""
        system_text = PERSONAS.get(persona_name, PERSONAS["assistant"])
        # Find and replace existing system message, or add new one
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = system_text
        else:
            self.messages.insert(0, {"role": "system", "content": system_text})
        self.current_persona = persona_name

    def chat(self, user_message: str, stream: bool = True) -> str:
        """Send a message. Returns full response as string."""
        self.messages.append({"role": "user", "content": user_message})

        # Trim history: keep system prompt + last max_history messages
        if len(self.messages) > self.max_history + 1:
            system = self.messages[0]
            recent = self.messages[-(self.max_history):]
            self.messages = [system] + recent

        start = time.time()

        if stream:
            # Streaming: print tokens as they arrive
            print("\n\033[94mMistral:\033[0m ", end="", flush=True)
            full_response = ""
            tokens = 0
            for chunk in ollama.chat(
                model=self.model,
                messages=self.messages,
                stream=True,
                options={"temperature": 0.7},
            ):
                token = chunk["message"]["content"]
                print(token, end="", flush=True)
                full_response += token
                tokens += 1
            print()  # newline
            elapsed = time.time() - start
            print(f"\033[90m  [{tokens} tokens, {tokens/elapsed:.1f} tok/s, "
                  f"{len(self.messages)//2} turns]\033[0m")
        else:
            response = ollama.chat(
                model=self.model,
                messages=self.messages,
                options={"temperature": 0.7},
            )
            full_response = response["message"]["content"]

        self.messages.append({"role": "assistant", "content": full_response})
        return full_response

    def clear_history(self) -> None:
        """Clear conversation but keep persona."""
        persona_msg = self.messages[0] if self.messages else None
        self.messages = [persona_msg] if persona_msg else []
        console.print("[yellow]History cleared[/yellow]")

    def show_info(self) -> None:
        t = Table(title="Chat Info")
        t.add_column("Setting", style="cyan")
        t.add_column("Value")
        t.add_row("Model", self.model)
        t.add_row("Persona", self.current_persona)
        t.add_row("History length", str(len(self.messages)))
        t.add_row("Max history", str(self.max_history))
        console.print(t)


def select_model() -> str:
    console.print("\n[bold]Available Models:[/bold]")
    for key, (model, desc) in MODELS.items():
        console.print(f"  [cyan]{key}[/cyan]. {desc}")
    choice = console.input("Select [1/2/3] (default 1): ").strip()
    return MODELS.get(choice, MODELS["1"])[0]


def select_persona() -> str:
    console.print("\n[bold]Available Personas:[/bold]")
    for name in PERSONAS:
        console.print(f"  [cyan]{name}[/cyan]")
    choice = console.input("Select persona (default: assistant): ").strip()
    return choice if choice in PERSONAS else "assistant"


def main():
    console.print(Panel.fit(
        "[bold cyan]Mistral Multi-Persona Chat Bot[/bold cyan]\n"
        "[dim]Local AI | Jetson AGX Orin | No internet required[/dim]",
        border_style="cyan",
    ))

    model = select_model()
    persona = select_persona()

    bot = MistralChat(model=model, persona=persona)

    console.print(f"\n[green]Ready: {model} | Persona: {persona}[/green]")
    console.print("[dim]Commands: /clear /persona /model /info /quit[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            # Slash commands
            if user_input.startswith("/"):
                cmd = user_input[1:].lower()
                if cmd in ("quit", "exit", "q"):
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                elif cmd == "clear":
                    bot.clear_history()
                elif cmd == "persona":
                    new_persona = select_persona()
                    bot.set_persona(new_persona)
                    console.print(f"[green]Switched to {new_persona} persona[/green]")
                elif cmd == "model":
                    new_model = select_model()
                    bot.model = new_model
                    console.print(f"[green]Switched to {new_model}[/green]")
                elif cmd == "info":
                    bot.show_info()
                else:
                    console.print("[yellow]Unknown command[/yellow]")
                continue

            bot.chat(user_input)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/mistral_chat
source venv/bin/activate
python3 mistral_chat.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Compare Personas

Start with the `assistant` persona and ask:
```
You: Explain recursion in programming
```

Then switch and ask the same question:
```
/persona
teacher

You: Explain recursion in programming
```

Notice how the same model gives very different responses based on persona.

### Exercise 2: The Developer Persona

Switch to `developer`:
```
You: Write a Python function to cache API responses to disk
```

The developer persona should return production-ready code with error handling.

### Exercise 3: Test Context Memory

Ask a multi-turn question that requires memory:
```
You: My name is Sergio and I'm building a Jetson AI project
You: What was my name again?
You: What am I building?
```

The model should remember all previous messages.

### Exercise 4: Jetson Expert Persona

Switch to `jetson` persona:
```
You: How do I make my LLM inference faster?
You: What's the best model size for real-time chat?
```

### Exercise 5: Context Limit Test

Send 25+ messages and watch the `[X turns]` counter. After `max_history` is reached, the oldest messages are trimmed — the model may forget early context.

---

## Expected Output

```
You: What is temperature in LLMs?

Mistral: Temperature controls how "creative" or "random" the model's output is.
At temperature 0, the model always picks the most likely next token — responses
are deterministic and focused. At temperature 1.0, it samples more randomly,
leading to more varied (sometimes surprising) output.

For factual Q&A: use 0.1–0.3
For creative writing: use 0.7–1.0

  [89 tokens, 21.4 tok/s, 1 turns]
```

**Performance (MAXN, mistral:7b):** ~18–22 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mistral:7b not found` | `docker exec ollama ollama pull mistral:7b` |
| Slow responses | Enable MAXN: `sudo nvpmodel -m 0 && sudo jetson_clocks` |
| Model forgets previous messages | Increase `max_history` (uses more memory) |
| OOM error with long history | Lower `max_history` or use a smaller model |

---

## Next Steps

- **[MistralLite Chat](mistrallite-chat.md)** — Faster, lighter version
- **[Nemo Assistant](nemo-assistant.md)** — Larger Mistral-Nemo with more capabilities
- **[GLM Chat](glm-chat.md)** — Alternative fast chat model
