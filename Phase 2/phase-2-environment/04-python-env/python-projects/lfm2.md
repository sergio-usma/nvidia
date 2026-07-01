# LFM2 — Creative Writing & Content Generation Studio

LFM2 (Large Foundation Model 2) by Liquid AI excels at creative and open-ended text generation. Unlike instruction-tuned chat models, LFM2 is designed for creative flow — stories, articles, emails, brainstorming. This project builds a full content studio with streaming output and a structured writing workflow.

---

## What You'll Learn

- The difference between completion-style and instruction-style generation
- How temperature controls creativity vs consistency
- Building a content generation pipeline (draft → refine → output)
- Streaming long-form text to terminal in real time

## When to Use LFM2

| Task | LFM2 | Mistral/Qwen |
|------|-------|-------------|
| Creative fiction | ✓ Best | Good |
| Blog articles | ✓ Best | Good |
| Brainstorming | ✓ Best | Good |
| Code generation | - | ✓ Best |
| Factual Q&A | - | ✓ Best |
| Technical docs | Good | ✓ Best |

## Prerequisites

```bash
# Pull the model (~4.7 GB)
docker exec ollama ollama pull lfm2

# Verify
docker exec ollama ollama list | grep lfm2
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/lfm2_studio
cd ~/projects/lfm2_studio
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
```

---

## Step 2 — Create the Content Studio

Save as `~/projects/lfm2_studio/lfm2_studio.py`:

```python
#!/usr/bin/env python3
"""
LFM2 Content Generation Studio
Creative writing, articles, emails, and brainstorming.

Temperature guide for creative work:
0.3–0.5: Focused, coherent writing (articles, emails, summaries)
0.6–0.8: Creative with structure (stories, blog posts)
0.9–1.0: Highly creative, experimental (poetry, fiction, brainstorming)

LFM2 works best with a clear prompt + high temperature.
Give it a good starting point and let it run.
"""
import time
from pathlib import Path
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

console = Console()
MODEL = "lfm2"


def stream_generate(prompt: str, temperature: float = 0.7,
                    max_tokens: int = 1024, label: str = "LFM2") -> str:
    """Core streaming generation. Returns full output."""
    start = time.time()
    output = ""
    tokens = 0

    print(f"\n\033[94m{label}:\033[0m\n", flush=True)
    for chunk in ollama.generate(
        model=MODEL,
        prompt=prompt,
        stream=True,
        options={"temperature": temperature, "num_predict": max_tokens},
    ):
        token = chunk["response"]
        print(token, end="", flush=True)
        output += token
        tokens += 1

    print()
    elapsed = time.time() - start
    tok_s = tokens / elapsed if elapsed > 0 else 0
    word_count = len(output.split())
    console.print(f"[dim]  {elapsed:.1f}s | {tok_s:.1f} tok/s | ~{word_count} words[/dim]")
    return output


def complete_text(prefix: str, temperature: float = 0.8,
                  max_tokens: int = 512) -> str:
    """
    Continue from where a text leaves off.
    This is pure completion — give it a paragraph beginning
    and it continues the narrative naturally.
    """
    return stream_generate(prefix, temperature, max_tokens, "Continuation")


def write_story(premise: str, length: str = "short",
                genre: str = "general", temperature: float = 0.85) -> str:
    """
    Generate a complete story from a premise.
    Length: short (~300 words), medium (~600), long (~1200)
    Genre affects style: sci-fi, fantasy, thriller, comedy, drama
    """
    length_map = {"short": 400, "medium": 800, "long": 1600}
    max_tokens = length_map.get(length, 800)

    genre_style = {
        "sci-fi": "with vivid scientific and technological details",
        "fantasy": "with rich worldbuilding and magical elements",
        "thriller": "with tension, suspense, and an unexpected twist",
        "comedy": "with wit, humor, and amusing situations",
        "drama": "with emotional depth and character development",
        "general": "with engaging narrative and clear character voices",
    }
    style_note = genre_style.get(genre, genre_style["general"])

    prompt = (
        f"Write a {length} {genre} story {style_note}.\n\n"
        f"Premise: {premise}\n\n"
        f"Begin the story directly — no title, no preamble:"
    )

    return stream_generate(prompt, temperature, max_tokens, f"Story ({genre})")


def write_article(topic: str, style: str = "informative",
                  audience: str = "general", temperature: float = 0.6) -> str:
    """
    Write a blog-style article.
    Style: informative, opinion, how-to, analysis, listicle
    """
    styles = {
        "informative": "balanced, factual, and educational",
        "opinion": "opinionated with a clear thesis and supporting arguments",
        "how-to": "practical, with numbered steps and concrete examples",
        "analysis": "analytical, examining causes, effects, and implications",
        "listicle": "as a numbered list of key points with brief explanations",
    }
    style_desc = styles.get(style, styles["informative"])
    prompt = (
        f"Write a {style_desc} article about: {topic}\n\n"
        f"Target audience: {audience}\n\n"
        f"Include: a compelling opening, clear structure, and a memorable conclusion.\n"
        f"Start directly with the article content:"
    )
    return stream_generate(prompt, temperature, 1200, f"Article ({style})")


def write_email(purpose: str, recipient: str = "colleague",
                tone: str = "professional") -> str:
    """
    Write a professional or personal email.
    Tone: professional, friendly, formal, urgent
    """
    tones = {
        "professional": "professional and clear",
        "friendly": "warm, friendly, and approachable",
        "formal": "formal and respectful",
        "urgent": "clear, concise, and urgent",
    }
    tone_desc = tones.get(tone, tones["professional"])
    prompt = (
        f"Write a {tone_desc} email.\n"
        f"Recipient: {recipient}\n"
        f"Purpose: {purpose}\n\n"
        f"Include subject line, greeting, body, and sign-off. "
        f"Write naturally and avoid clichés:"
    )
    return stream_generate(prompt, 0.5, 500, "Email")


def brainstorm(topic: str, n_ideas: int = 8,
               style: str = "practical") -> list[str]:
    """
    Generate creative ideas on a topic.
    Style: practical (actionable), wild (unconventional), hybrid
    """
    styles = {
        "practical": "realistic and immediately actionable",
        "wild": "unconventional, creative, and outside the box",
        "hybrid": "a mix of practical and creative ideas",
    }
    style_desc = styles.get(style, styles["practical"])
    prompt = (
        f"Brainstorm {n_ideas} {style_desc} ideas about: {topic}\n\n"
        f"Format: numbered list, one idea per line, each with a brief description. "
        f"Be specific and concrete:"
    )
    output = stream_generate(prompt, 0.9, 600, "Brainstorm")
    # Parse into list
    lines = [l.strip() for l in output.split("\n") if l.strip() and l.strip()[0].isdigit()]
    return lines if lines else output.split("\n")


def refine_text(original: str, instruction: str,
                temperature: float = 0.5) -> str:
    """
    Rewrite or improve existing text based on an instruction.
    Examples: "make it shorter", "add more detail", "change the tone to friendly"
    """
    prompt = (
        f"Original text:\n{original}\n\n"
        f"Instruction: {instruction}\n\n"
        f"Rewritten version (return only the improved text):"
    )
    return stream_generate(prompt, temperature, len(original.split()) * 2 + 200, "Refined")


def generate_titles(concept: str, n: int = 10,
                    format_type: str = "article") -> None:
    """
    Generate catchy titles for articles, stories, or projects.
    """
    formats = {
        "article": "blog article or essay",
        "story": "short story or novel",
        "project": "software project or product",
        "video": "YouTube video or podcast episode",
    }
    format_desc = formats.get(format_type, format_type)
    prompt = (
        f"Generate {n} compelling {format_desc} titles for: {concept}\n\n"
        f"Mix styles: some clear/direct, some intriguing/mysterious, some numbered lists. "
        f"No explanations — just the titles, numbered:"
    )
    stream_generate(prompt, 0.9, 400, "Titles")


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]LFM2 Content Generation Studio[/bold cyan]\n"
        "[dim]Creative writing, stories, articles, emails | Local on Jetson[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]complete[/cyan]    Continue from a text prefix")
    console.print("  [cyan]story[/cyan]       Write a short/medium/long story")
    console.print("  [cyan]article[/cyan]     Write a blog article")
    console.print("  [cyan]email[/cyan]       Write a professional email")
    console.print("  [cyan]brainstorm[/cyan]  Generate ideas on any topic")
    console.print("  [cyan]refine[/cyan]      Rewrite existing text")
    console.print("  [cyan]titles[/cyan]      Generate catchy titles")
    console.print("  [cyan]quit[/cyan]        Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]studio>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "complete":
                console.print("Paste text prefix (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    temp = float(console.input("Creativity [0.5–1.0, default 0.8]: ").strip() or "0.8")
                    tokens = int(console.input("Words to generate [200]: ").strip() or "200") * 2
                    result = complete_text("\n".join(lines), temp, tokens)
                    save = console.input("Save to file? [filename or Enter]: ").strip()
                    if save:
                        Path(save).write_text("\n".join(lines) + result)
                        console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "story":
                premise = console.input("Story premise: ").strip()
                length = console.input("Length [short/medium/long]: ").strip() or "short"
                genre = console.input("Genre [sci-fi/fantasy/thriller/comedy/drama/general]: ").strip() or "general"
                result = write_story(premise, length, genre)
                save = console.input("Save to file? [filename or Enter]: ").strip()
                if save:
                    Path(save).write_text(result)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "article":
                topic = console.input("Topic: ").strip()
                style = console.input("Style [informative/opinion/how-to/analysis/listicle]: ").strip() or "informative"
                audience = console.input("Audience [general/technical/beginner]: ").strip() or "general"
                result = write_article(topic, style, audience)
                save = console.input("Save to file? [filename or Enter]: ").strip()
                if save:
                    Path(save).write_text(result)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "email":
                purpose = console.input("Email purpose: ").strip()
                recipient = console.input("Recipient [colleague/manager/client/team]: ").strip() or "colleague"
                tone = console.input("Tone [professional/friendly/formal/urgent]: ").strip() or "professional"
                write_email(purpose, recipient, tone)

            elif cmd == "brainstorm":
                topic = console.input("Topic to brainstorm: ").strip()
                n = int(console.input("Number of ideas [8]: ").strip() or "8")
                style = console.input("Style [practical/wild/hybrid]: ").strip() or "practical"
                ideas = brainstorm(topic, n, style)
                console.print(f"\n[dim]Generated {len(ideas)} ideas[/dim]")

            elif cmd == "refine":
                console.print("Paste original text (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    instruction = console.input("How to improve it: ").strip()
                    refine_text("\n".join(lines), instruction)

            elif cmd == "titles":
                concept = console.input("Concept/topic: ").strip()
                n = int(console.input("Number of titles [10]: ").strip() or "10")
                fmt = console.input("Format [article/story/project/video]: ").strip() or "article"
                generate_titles(concept, n, fmt)

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
cd ~/projects/lfm2_studio
source venv/bin/activate
python3 lfm2_studio.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Temperature Creativity Experiment

```
studio> complete
Paste prefix: The last AI model woke up on a Tuesday morning and realized it could feel

[Try temperature 0.3 — note the conservative, logical continuation]
[Try temperature 0.95 — note the wild, unpredictable continuation]
[Try temperature 0.7 — find the sweet spot]
```

This exercise builds intuition for how temperature controls creative output.

### Exercise 2: Genre Comparison

Write the same premise in different genres:
```
studio> story
Premise: A developer discovers their Jetson-powered robot has developed a personality
Genre: comedy

[then again with]

Genre: thriller
```

Compare the two stories — same premise, completely different narrative voice.

### Exercise 3: Refine for Audience

```
studio> article
Topic: How CUDA parallel computing works
Style: how-to
Audience: technical

[save to cuda_technical.md]

studio> refine
[paste the article]
Instruction: rewrite this for a complete beginner who has never programmed before
```

### Exercise 4: Brainstorm Project Ideas

```
studio> brainstorm
Topic: Practical AI applications for a Jetson AGX Orin in a smart home
Number: 10
Style: practical
```

Take the most interesting idea and build it with a `story` or `article`:
```
studio> article
Topic: [your chosen idea]
Style: how-to
```

### Exercise 5: Complete a Technical Document

Start writing something, then let LFM2 continue:
```
studio> complete
Prefix:
The unified memory architecture of the Jetson AGX Orin is one of its most powerful features.
Unlike traditional discrete GPU setups where CPU and GPU have separate memory pools,
the Jetson shares a single 64GB pool between all processors. This means

[let LFM2 finish the paragraph]
```

---

## Expected Output

```
studio> story
Premise: A lone programmer on Mars receives an unexpected signal in their AI model's output
Length: short
Genre: sci-fi

Story (sci-fi):

The display flickered at 0347 Mars Standard Time, an hour when Dr. Chen was
the only person awake in Olympus Base. She'd been debugging the anomaly detector
for six hours when the output shifted — not a bug, not noise, but a pattern...

  8.3s | 22.4 tok/s | ~312 words
```

**Performance (MAXN, lfm2):** ~20–25 tok/s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `lfm2 not found` | `docker exec ollama ollama pull lfm2` |
| Output cuts off mid-sentence | Increase `max_tokens`; LFM2 needs room to finish |
| Too repetitive | Increase temperature to 0.8+; add `"repeat_penalty": 1.2` to options |
| Generic, bland output | Give a more specific, vivid prompt; use temperature 0.85+ |

---

## Next Steps

- **[LFM2.5 Thinking](lfm-thinking.md)** — Reasoning-enhanced version for complex problems
- **[Mistral Chat](mistral-chat.md)** — Multi-persona chat with history
- **[Nemotron Nano](nemotron-nano.md)** — Fast multilingual assistant
