# DeepSeek — Vision OCR Scanner

Build a document scanner that extracts text from images using a vision-language model. No Tesseract, no cloud API — pure local AI inference on your Jetson's GPU.

---

## What You'll Learn

- Encoding images as base64 for multimodal LLMs
- Using OpenCV for image preprocessing (contrast, denoising)
- Extracting structured data (tables, receipts, forms) from images
- Batch processing multiple documents

## Prerequisites

```bash
# Pull the vision model (~4.7 GB)
docker exec ollama ollama pull llava:7b

# Alternative with better OCR quality (~7.9 GB):
# docker exec ollama ollama pull llama3.2-vision:11b

# Install OpenCV
sudo apt install python3-opencv -y
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/ocr_scanner
cd ~/projects/ocr_scanner
python3 -m venv venv
source venv/bin/activate
pip install ollama opencv-python-headless pillow rich
```

---

## Step 2 — Create a Test Image

If you don't have an image to test with, create one:

```bash
# Install imagemagick to create test images
sudo apt install imagemagick -y

# Create a test document image with text
convert -size 800x400 xc:white \
  -font DejaVu-Sans -pointsize 36 \
  -fill black -annotate +50+80 "Invoice #1042" \
  -annotate +50+140 "Date: 2024-01-15" \
  -annotate +50+200 "Item: Jetson AGX Orin   $999.00" \
  -annotate +50+260 "Item: NVMe SSD 2TB      $149.00" \
  -annotate +50+340 "TOTAL: $1,148.00" \
  test_invoice.png

echo "Created test_invoice.png"
```

---

## Step 3 — Create the OCR Scanner

Save as `~/projects/ocr_scanner/ocr_scanner.py`:

```python
#!/usr/bin/env python3
"""
Vision OCR Scanner — DeepSeek / LLaVA on Jetson
Uses a vision-language model to extract text from images.
No cloud required, no Tesseract, pure AI inference.
"""
import sys
import base64
import json
import time
from pathlib import Path

import cv2
import numpy as np
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Use llava:7b (fast) or llama3.2-vision:11b (more accurate)
MODEL = "llava:7b"


def preprocess_image(image_path: str) -> tuple[np.ndarray, str]:
    """
    Preprocess image for better OCR results.

    Steps:
    1. Load with OpenCV
    2. Convert to grayscale (removes color noise)
    3. Apply adaptive thresholding (handles uneven lighting)
    4. Denoise (removes small artifacts)

    Returns both the processed numpy array and a base64-encoded version.
    """
    # Load original
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {image_path}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold: works better than fixed threshold on photos
    # block_size=11: looks at 11x11 pixel neighborhoods
    # C=2: subtract 2 from calculated mean for threshold
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Denoise to remove salt-and-pepper artifacts
    denoised = cv2.fastNlMeansDenoising(thresh, h=10)

    # Encode to PNG bytes for the vision model
    _, buffer = cv2.imencode(".png", denoised)
    b64 = base64.b64encode(buffer).decode("utf-8")

    return denoised, b64


def extract_text(image_path: str, prompt: str = None) -> dict:
    """
    Extract text from an image using the vision model.

    The model receives the image as a base64-encoded string alongside
    the text prompt. Vision models process both simultaneously.
    """
    processed_img, b64_image = preprocess_image(image_path)

    if prompt is None:
        prompt = (
            "Extract ALL text from this image exactly as written. "
            "Preserve the original formatting, line breaks, and structure. "
            "Return only the text content, nothing else."
        )

    start = time.time()

    # Ollama vision API: pass images as a list of base64 strings
    response = ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [b64_image],  # <-- key: send image as base64
        }],
        options={"temperature": 0.1, "num_predict": 2048},
    )

    elapsed = time.time() - start
    extracted = response["message"]["content"]

    return {
        "file": image_path,
        "text": extracted,
        "elapsed": round(elapsed, 2),
        "chars": len(extracted),
    }


def extract_structured(image_path: str, doc_type: str = "receipt") -> dict:
    """
    Extract structured data from common document types.
    Returns JSON-formatted results instead of raw text.
    """
    prompts = {
        "receipt": (
            "Extract all data from this receipt. "
            "Return as JSON with keys: store_name, date, items (list of {name, price}), total, tax"
        ),
        "invoice": (
            "Extract invoice data. "
            "Return as JSON with keys: invoice_number, date, vendor, line_items (list of {description, qty, price}), subtotal, total"
        ),
        "form": (
            "Extract all form fields and their values. "
            "Return as JSON with field names as keys and their filled values as values."
        ),
        "table": (
            "Extract the table data. "
            "Return as JSON: {headers: [...], rows: [[...], ...]}"
        ),
        "business_card": (
            "Extract contact info from this business card. "
            "Return as JSON: {name, title, company, email, phone, address}"
        ),
    }

    prompt = prompts.get(doc_type, prompts["receipt"])
    result = extract_text(image_path, prompt)

    # Try to parse JSON from response
    try:
        text = result["text"]
        # Find JSON block if the model wrapped it in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        result["structured"] = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        result["structured"] = None
        result["raw_json_attempt"] = result["text"]

    return result


def batch_scan(image_dir: str, output_file: str = "scan_results.json") -> list:
    """
    Process all images in a directory.
    Useful for scanning a folder of scanned documents.
    """
    image_dir = Path(image_dir)
    extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
    image_files = [f for f in image_dir.iterdir() if f.suffix.lower() in extensions]

    if not image_files:
        console.print(f"[yellow]No images found in {image_dir}[/yellow]")
        return []

    results = []
    for i, img_path in enumerate(image_files, 1):
        console.print(f"[{i}/{len(image_files)}] Scanning {img_path.name}...")
        try:
            result = extract_text(str(img_path))
            results.append(result)
            console.print(f"  [green]✓ Extracted {result['chars']} chars in {result['elapsed']}s[/green]")
        except Exception as e:
            console.print(f"  [red]✗ Error: {e}[/red]")
            results.append({"file": str(img_path), "error": str(e)})

    # Save all results
    Path(output_file).write_text(json.dumps(results, indent=2, ensure_ascii=False))
    console.print(f"\n[green]Saved results to {output_file}[/green]")
    return results


def show_result(result: dict):
    """Pretty-print an extraction result."""
    info = Table.grid(padding=1)
    info.add_row("[bold]File:[/bold]", result["file"])
    info.add_row("[bold]Time:[/bold]", f"{result['elapsed']}s")
    info.add_row("[bold]Characters:[/bold]", str(result["chars"]))
    console.print(Panel(info, title="Scan Info"))
    console.print(Panel(result["text"], title="Extracted Text"))


def interactive_mode():
    """Interactive CLI for the OCR scanner."""
    console.print(Panel.fit(
        "[bold cyan]Vision OCR Scanner[/bold cyan]\n"
        f"[dim]Model: {MODEL} | Runs locally on Jetson[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]scan[/cyan]       Extract text from image")
    console.print("  [cyan]structured[/cyan] Extract structured data (receipt/invoice/form/table)")
    console.print("  [cyan]batch[/cyan]      Process all images in a folder")
    console.print("  [cyan]quit[/cyan]       Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]ocr>[/bold blue] ").strip().lower()

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "scan":
                path = console.input("Image path: ").strip()
                with console.status("[bold green]Scanning..."):
                    result = extract_text(path)
                show_result(result)

            elif cmd == "structured":
                path = console.input("Image path: ").strip()
                doc_type = console.input("Document type [receipt/invoice/form/table/business_card]: ").strip()
                with console.status("[bold green]Extracting structured data..."):
                    result = extract_structured(path, doc_type)

                if result.get("structured"):
                    console.print(Panel(
                        json.dumps(result["structured"], indent=2),
                        title="Structured Data (JSON)"
                    ))
                else:
                    console.print(Panel(result["text"], title="Extracted Text (could not parse JSON)"))

            elif cmd == "batch":
                folder = console.input("Folder path: ").strip()
                output = console.input("Output JSON file [scan_results.json]: ").strip()
                batch_scan(folder, output or "scan_results.json")

            else:
                console.print("[yellow]Unknown command[/yellow]")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# CLI shortcut: python3 ocr_scanner.py image.png
if __name__ == "__main__":
    if len(sys.argv) == 2:
        result = extract_text(sys.argv[1])
        show_result(result)
    else:
        interactive_mode()
```

---

## Step 4 — Run It

```bash
cd ~/projects/ocr_scanner
source venv/bin/activate

# Interactive mode
python3 ocr_scanner.py

# Or direct scan from CLI:
python3 ocr_scanner.py test_invoice.png
```

---

## Step 5 — Hands-On Exercises

### Exercise 1: Scan the Test Invoice

```
ocr> scan
Image path: test_invoice.png
```

Check if all items, prices, and the total were captured correctly.

### Exercise 2: Extract Structured Data

```
ocr> structured
Image path: test_invoice.png
Document type: invoice
```

The model should return JSON with `invoice_number`, `line_items`, `total`.

### Exercise 3: Scan a Real Photo

Take a photo of a receipt, business card, or handwritten note with your phone. Transfer it to the Jetson:

```bash
# From your phone via SSH (on Windows/Mac):
scp receipt.jpg sergiok@<jetson-ip>:~/projects/ocr_scanner/

# Then scan it:
python3 ocr_scanner.py receipt.jpg
```

### Exercise 4: Batch Process a Folder

```bash
mkdir ~/documents/to_scan
cp *.png ~/documents/to_scan/

# In the app:
ocr> batch
Folder path: ~/documents/to_scan
```

---

## Expected Output

```
Scan Info
 File:       test_invoice.png
 Time:       4.2s
 Characters: 127

Extracted Text
Invoice #1042
Date: 2024-01-15
Item: Jetson AGX Orin   $999.00
Item: NVMe SSD 2TB      $149.00
TOTAL: $1,148.00
```

**Performance on Jetson (MAXN, llava:7b):** ~12–18 tok/s generation. Image encoding ~200ms.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `model not found` | `docker exec ollama ollama pull llava:7b` |
| `cv2 not found` | `pip install opencv-python-headless` |
| Poor text extraction | Try preprocessing with higher contrast; use `llama3.2-vision:11b` for better accuracy |
| `base64` error | Ensure image file is not corrupted: `file image.png` |
| Very slow (~3 tok/s) | Enable MAXN: `sudo nvpmodel -m 0 && sudo jetson_clocks` |

---

## Next Steps

- **[GLM OCR Scanner](glm-ocr.md)** — Alternative vision model for OCR
- **[Nomic Vectors](nomic-vectors.md)** — Build a searchable index from extracted text
- **Phase 3: Vision Models** — Real-time camera-based OCR
