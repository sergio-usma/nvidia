# GLM-OCR — Vision-Powered Document Scanner

GLM-OCR uses GLM-4V's vision capabilities to extract and structure text from images. Unlike traditional OCR (Tesseract), it understands context — it can parse receipts, invoices, tables, and handwritten notes while understanding what the content means. This project builds a practical document scanning pipeline.

---

## What You'll Learn

- How multimodal models combine vision and language understanding
- Base64 image encoding for passing images to the Ollama API
- Structured data extraction: JSON output from unstructured images
- Building a batch document processor

## Traditional OCR vs Vision Models

| Feature | Tesseract (Traditional) | GLM-4V (Vision Model) |
|---------|------------------------|----------------------|
| Plain text extraction | Excellent | Good |
| Understanding context | No | Yes |
| Structured extraction (JSON) | No | Yes |
| Handwriting | Poor | Good |
| Tables | Fair | Excellent |
| Multiple languages | Good | Excellent |
| Requires training | Yes (for custom) | No |

## Prerequisites

```bash
# GLM-4V is the vision variant of GLM-4
docker exec ollama ollama pull glm4

# Check if vision capabilities are available
docker exec ollama ollama list | grep glm

# For image processing
sudo apt-get install -y imagemagick
```

> **Note:** GLM-4 with vision support handles OCR tasks. The exact model tag depends on what's available on Ollama. Try `glm4` first.

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/glm_ocr
cd ~/projects/glm_ocr
python3 -m venv venv
source venv/bin/activate
pip install ollama rich pillow
```

---

## Step 2 — Create Test Images

Before running the OCR tool, create sample images to scan:

```bash
# Create a fake receipt image
convert -size 400x600 xc:white \
  -font DejaVu-Sans -pointsize 18 \
  -draw "text 100,50 'NVIDIA TECH STORE'" \
  -draw "text 50,100 'Date: 2026-03-15'" \
  -draw "text 50,130 'Jetson AGX Orin 64GB  $999'" \
  -draw "text 50,160 'USB-C Cable           $29'" \
  -draw "text 50,190 'Thermal Pad           $15'" \
  -draw "text 50,250 'Subtotal:            $1043'" \
  -draw "text 50,280 'Tax (8.5%):           $89'" \
  -draw "text 50,310 'TOTAL:               $1132'" \
  ~/projects/glm_ocr/test_receipt.png

# Create a table image
convert -size 500x400 xc:white \
  -font DejaVu-Sans -pointsize 16 \
  -draw "text 50,50 'Model       Params  Speed    Size'" \
  -draw "text 50,80 '──────────────────────────────'" \
  -draw "text 50,110 'tinyllama   1.1B    60 tok/s  637MB'" \
  -draw "text 50,140 'llama3.2:3b  3B     40 tok/s  2.0GB'" \
  -draw "text 50,170 'qwen2.5:7b  7B     22 tok/s  4.4GB'" \
  -draw "text 50,200 'mistral:7b  7B     20 tok/s  4.1GB'" \
  ~/projects/glm_ocr/test_table.png

echo "Test images created in ~/projects/glm_ocr/"
ls -la ~/projects/glm_ocr/*.png
```

---

## Step 3 — Create the OCR Tool

Save as `~/projects/glm_ocr/glm_ocr.py`:

```python
#!/usr/bin/env python3
"""
GLM-OCR — Vision-Powered Document Scanner
Uses GLM-4V's multimodal capabilities for intelligent document parsing.

Key insight: Vision models don't just read text — they understand it.
They can extract structured data (JSON), recognize relationships between
elements, and handle layouts that trip up traditional OCR.

Supported document types:
- Receipts: items, prices, totals, tax
- Invoices: invoice number, dates, line items, amounts
- Tables: parse rows/columns into structured data
- Business cards: name, title, company, contact info
- General documents: plain text extraction
- Handwritten notes: best-effort transcription
"""
import base64
import json
import time
from pathlib import Path
from typing import Optional
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table as RichTable
from rich.syntax import Syntax

console = Console()

# GLM-4 vision model — try glm4, fallback to llava if needed
MODEL = "glm4"
# Alternative if glm4 doesn't support vision in your version:
# MODEL = "llava:7b"


def load_image_b64(image_path: str) -> str:
    """
    Load an image and encode as base64 string.
    The Ollama API accepts images as base64-encoded strings.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        image_data = f.read()

    # Detect format from extension
    ext = path.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime = mime_types.get(ext, "image/jpeg")

    b64 = base64.b64encode(image_data).decode("utf-8")
    return b64


def scan_image(image_path: str, custom_prompt: str = "") -> str:
    """
    Extract all text from an image.
    Returns the raw text content as a string.
    """
    b64 = load_image_b64(image_path)

    prompt = custom_prompt or (
        "Extract all text from this image exactly as it appears. "
        "Preserve the layout as much as possible. "
        "Return only the extracted text, no commentary."
    )

    start = time.time()
    response_text = ""

    print("\n\033[94mExtracted Text:\033[0m\n", flush=True)
    for chunk in ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [b64],
        }],
        stream=True,
        options={"temperature": 0.05, "num_predict": 2048},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        response_text += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return response_text


def extract_receipt(image_path: str) -> dict:
    """
    Parse a receipt image into structured JSON.
    Returns: store_name, date, items (list), subtotal, tax, total
    """
    b64 = load_image_b64(image_path)

    prompt = """Extract all information from this receipt image.
Return ONLY valid JSON with this structure:
{
  "store_name": "...",
  "date": "...",
  "items": [
    {"name": "...", "quantity": 1, "price": 0.00}
  ],
  "subtotal": 0.00,
  "tax": 0.00,
  "total": 0.00,
  "payment_method": "..."
}
Use null for fields not visible in the image."""

    response = ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [b64],
        }],
        options={"temperature": 0.05, "num_predict": 1024},
    )

    raw = response["message"]["content"]

    # Parse JSON from response
    try:
        # Find JSON block
        json_match = raw
        if "```json" in raw:
            json_match = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_match = raw.split("```")[1].split("```")[0].strip()
        return json.loads(json_match)
    except json.JSONDecodeError:
        return {"raw": raw, "error": "Could not parse JSON — showing raw response"}


def extract_table(image_path: str, output_format: str = "csv") -> str:
    """
    Extract a table from an image into structured format.
    output_format: 'csv', 'json', 'markdown'
    """
    b64 = load_image_b64(image_path)

    format_instructions = {
        "csv": "Return as CSV with header row, comma-separated.",
        "json": "Return as JSON array of objects with column names as keys.",
        "markdown": "Return as a markdown table with | separators.",
    }
    format_note = format_instructions.get(output_format, format_instructions["csv"])

    prompt = f"Extract the table from this image. {format_note} Return only the table data, no commentary."

    start = time.time()
    result = ""
    for chunk in ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [b64],
        }],
        stream=True,
        options={"temperature": 0.05, "num_predict": 1024},
    ):
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        result += token

    print()
    elapsed = time.time() - start
    console.print(f"[dim]  {elapsed:.1f}s[/dim]")
    return result


def extract_invoice(image_path: str) -> dict:
    """Parse an invoice image into structured data."""
    b64 = load_image_b64(image_path)

    prompt = """Extract all invoice information. Return ONLY valid JSON:
{
  "invoice_number": "...",
  "date": "...",
  "due_date": "...",
  "vendor": {"name": "...", "address": "..."},
  "client": {"name": "...", "address": "..."},
  "line_items": [{"description": "...", "qty": 1, "unit_price": 0.00, "total": 0.00}],
  "subtotal": 0.00,
  "tax_rate": 0.0,
  "tax_amount": 0.00,
  "total_due": 0.00
}"""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt, "images": [b64]}],
        options={"temperature": 0.05, "num_predict": 2048},
    )
    raw = response["message"]["content"]
    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw, "error": "JSON parse failed"}


def describe_image(image_path: str) -> str:
    """
    Get a general description of what's in an image.
    Useful for understanding an image before deciding which extractor to use.
    """
    b64 = load_image_b64(image_path)
    prompt = "Describe what you see in this image in 2-3 sentences. Include any text content visible."

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt, "images": [b64]}],
        options={"temperature": 0.3, "num_predict": 256},
    )
    return response["message"]["content"]


def batch_scan(image_paths: list[str], output_dir: str = ".") -> None:
    """
    Scan multiple images and save extracted text to individual files.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Processing {len(image_paths)} images...[/cyan]")
    results = []

    for i, img_path in enumerate(image_paths):
        console.print(f"[{i+1}/{len(image_paths)}] {Path(img_path).name}")
        try:
            text = scan_image(img_path)
            out_file = out_path / (Path(img_path).stem + "_extracted.txt")
            out_file.write_text(text)
            results.append({"file": img_path, "status": "ok", "chars": len(text)})
        except Exception as e:
            results.append({"file": img_path, "status": f"error: {e}", "chars": 0})

    # Summary table
    t = RichTable(title="Batch Results")
    t.add_column("File", style="cyan")
    t.add_column("Status")
    t.add_column("Characters")
    for r in results:
        status_style = "green" if r["status"] == "ok" else "red"
        t.add_row(
            Path(r["file"]).name,
            f"[{status_style}]{r['status']}[/{status_style}]",
            str(r["chars"]),
        )
    console.print(t)


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]GLM-OCR — Vision Document Scanner[/bold cyan]\n"
        "[dim]AI-powered text extraction and document parsing[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]scan[/cyan]       Extract all text from image")
    console.print("  [cyan]receipt[/cyan]    Parse receipt to JSON")
    console.print("  [cyan]invoice[/cyan]    Parse invoice to JSON")
    console.print("  [cyan]table[/cyan]      Extract table (CSV/JSON/Markdown)")
    console.print("  [cyan]describe[/cyan]   Describe image content")
    console.print("  [cyan]batch[/cyan]      Process multiple images")
    console.print("  [cyan]quit[/cyan]       Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]ocr>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "scan":
                img_path = console.input("Image path: ").strip()
                custom_prompt = console.input("Custom instructions (optional): ").strip()
                result = scan_image(img_path, custom_prompt)
                save = console.input("Save to file? [filename or Enter]: ").strip()
                if save:
                    Path(save).write_text(result)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "receipt":
                img_path = console.input("Receipt image path: ").strip()
                console.print("[dim]Parsing receipt...[/dim]")
                data = extract_receipt(img_path)
                if "error" not in data:
                    # Display as table
                    console.print("\n[bold]Receipt Data:[/bold]")
                    for key, val in data.items():
                        if key == "items":
                            console.print("\n[cyan]Items:[/cyan]")
                            t = RichTable()
                            t.add_column("Item")
                            t.add_column("Qty")
                            t.add_column("Price", justify="right")
                            for item in val:
                                t.add_row(
                                    str(item.get("name", "")),
                                    str(item.get("quantity", "")),
                                    f"${item.get('price', 0):.2f}",
                                )
                            console.print(t)
                        else:
                            console.print(f"  [cyan]{key}:[/cyan] {val}")
                else:
                    console.print(Panel(data.get("raw", ""), title="Raw Response"))

                save = console.input("Save JSON? [filename or Enter]: ").strip()
                if save:
                    Path(save).write_text(json.dumps(data, indent=2))
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "invoice":
                img_path = console.input("Invoice image path: ").strip()
                data = extract_invoice(img_path)
                json_str = json.dumps(data, indent=2)
                console.print(Syntax(json_str, "json", theme="monokai"))
                save = console.input("Save JSON? [filename or Enter]: ").strip()
                if save:
                    Path(save).write_text(json_str)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "table":
                img_path = console.input("Table image path: ").strip()
                fmt = console.input("Output format [csv/json/markdown]: ").strip() or "csv"
                print(f"\n\033[94mTable ({fmt}):\033[0m\n", flush=True)
                result = extract_table(img_path, fmt)
                save = console.input("Save? [filename or Enter]: ").strip()
                if save:
                    Path(save).write_text(result)
                    console.print(f"[green]Saved to {save}[/green]")

            elif cmd == "describe":
                img_path = console.input("Image path: ").strip()
                desc = describe_image(img_path)
                console.print(Panel(desc, title="Image Description"))

            elif cmd == "batch":
                paths = []
                console.print("Enter image paths (blank line to finish):")
                while True:
                    p = input("  Path: ").strip()
                    if not p:
                        break
                    paths.append(p)
                if paths:
                    output_dir = console.input("Output directory [./output]: ").strip() or "./output"
                    batch_scan(paths, output_dir)

            else:
                console.print("[yellow]Unknown command[/yellow]")

        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
```

---

## Step 4 — Run It

```bash
cd ~/projects/glm_ocr
source venv/bin/activate
python3 glm_ocr.py
```

---

## Step 5 — Hands-On Exercises

### Exercise 1: Scan a Test Receipt

```
ocr> scan
Image path: ~/projects/glm_ocr/test_receipt.png
```

Expected: The model reads all text including item names, prices, tax, and total.

### Exercise 2: Extract Receipt as JSON

```
ocr> receipt
Image path: ~/projects/glm_ocr/test_receipt.png
Save JSON: receipt_data.json
```

Then verify the output:
```bash
cat receipt_data.json
```

Expected JSON structure with `store_name`, `items` array, `subtotal`, `tax`, `total`.

### Exercise 3: Extract a Table

```
ocr> table
Image path: ~/projects/glm_ocr/test_table.png
Format: csv
Save: models.csv
```

Then open the CSV:
```bash
column -t -s',' models.csv
```

### Exercise 4: Describe Before Scanning

Use `describe` first to understand an unknown image before deciding which extractor to use:
```
ocr> describe
Image path: [any image on your system]
```

This helps route to the right extraction method.

### Exercise 5: Batch Process

Create multiple test images and process them together:
```bash
# Create another test image
convert -size 400x300 xc:white \
  -font DejaVu-Sans -pointsize 16 \
  -draw "text 50,50 'Meeting Notes - 2026-03-15'" \
  -draw "text 50,80 '1. Deploy Jetson inference server'" \
  -draw "text 50,110 '2. Test LLM latency benchmarks'" \
  -draw "text 50,140 '3. Optimize MAXN power settings'" \
  ~/projects/glm_ocr/test_notes.png
```

```
ocr> batch
~/projects/glm_ocr/test_receipt.png
~/projects/glm_ocr/test_table.png
~/projects/glm_ocr/test_notes.png

Output: ./ocr_output
```

---

## Expected Output

```
ocr> receipt
Image path: test_receipt.png

Receipt Data:
  store_name: NVIDIA TECH STORE
  date: 2026-03-15

Items:
Item                  Qty  Price
Jetson AGX Orin 64GB  1    $999.00
USB-C Cable           1    $29.00
Thermal Pad           1    $15.00

  subtotal: 1043.0
  tax: 89.0
  total: 1132.0

  3.8s
```

**Performance (MAXN, glm4 vision):** ~10–15 tok/s (vision models are slower than text-only)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `glm4 not found` | `docker exec ollama ollama pull glm4` |
| "Model doesn't support vision" | Try `docker exec ollama ollama pull llava:7b` and change MODEL to `"llava:7b"` |
| JSON parse error | The model output isn't clean JSON; add `"temperature": 0.0` for more deterministic output |
| Low quality extraction | Improve image quality: higher resolution, better contrast; use imagemagick to preprocess |
| `convert: not found` | `sudo apt-get install imagemagick` |

---

## Next Steps

- **[DeepSeek OCR](deepseek-ocr.md)** — OCR with OpenCV preprocessing for better accuracy
- **[GLM Chat](glm-chat.md)** — Text-only GLM-4 for bilingual chat
- **[Nomic Vectors](nomic-vectors.md)** — Index extracted text for semantic search
