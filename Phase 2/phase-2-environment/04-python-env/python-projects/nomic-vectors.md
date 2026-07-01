# Nomic Embeddings — Semantic Search & RAG Vector Store

Nomic Embed builds dense vector embeddings of text — turning sentences into numeric vectors where semantically similar content is geometrically close. This is the foundation of Retrieval-Augmented Generation (RAG): instead of hoping the model memorizes your documents, you retrieve relevant chunks at query time and feed them as context.

---

## What You'll Learn

- What embeddings are and why cosine similarity works for semantic search
- Building a persistent vector store with save/load functionality
- Full RAG pipeline: embed documents → retrieve → generate answers with sources
- Document chunking: why splitting large texts into chunks improves retrieval

## How Embeddings Enable Search

```
"Python is fast"      → [0.23, -0.41, 0.87, ...]  ← 768-dim vector
"Python runs quickly" → [0.24, -0.40, 0.85, ...]  ← very close!
"JavaScript is async" → [0.11,  0.72, 0.13, ...]  ← far away
```

Cosine similarity measures the angle between vectors. Similar meaning = small angle = high similarity score (close to 1.0).

## Prerequisites

```bash
# Pull the embedding model (~274 MB — tiny but powerful)
docker exec ollama ollama pull nomic-embed-text

# For Q&A (answering questions), pull a chat model too
docker exec ollama ollama pull llama3.2

# Verify
docker exec ollama ollama list | grep nomic
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/nomic_vectors
cd ~/projects/nomic_vectors
python3 -m venv venv
source venv/bin/activate
pip install ollama numpy scikit-learn rich
```

---

## Step 2 — Create the Vector Store

Save as `~/projects/nomic_vectors/vector_store.py`:

```python
#!/usr/bin/env python3
"""
Nomic Embeddings — Semantic Search & RAG Vector Store

Key concepts implemented:
1. Embedding: text → 768-dimensional vector via nomic-embed-text
2. Cosine similarity: measures angle between vectors (1.0 = identical, 0.0 = unrelated)
3. Chunking: split large docs into overlapping segments for better retrieval
4. RAG: embed query → find similar chunks → pass as context to LLM

Why nomic-embed-text?
- 768-dim embeddings with excellent semantic quality
- Only 274 MB (fast to load, minimal memory)
- Works with both short phrases and long paragraphs
- ~2000 texts/minute on Jetson MAXN
"""
import json
import time
from pathlib import Path
from typing import Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2"   # For RAG answers — change to any chat model you have

# Chunking settings: split large documents for better retrieval
CHUNK_SIZE = 500      # Characters per chunk
CHUNK_OVERLAP = 100   # Overlap between chunks (prevents cutting mid-sentence)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for indexing.

    Why overlap? If a sentence spans a chunk boundary, overlap ensures
    it appears in at least one complete chunk.

    Example: chunk_size=10, overlap=3, text="abcdefghijk"
    → ["abcdefghij", "hijklm"]   (3 chars of overlap)
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(". ")
            if last_period > chunk_size * 0.5:
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1
        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if len(c) > 50]  # Skip very short chunks


class DocumentStore:
    """
    In-memory vector store with persistence.
    Stores text, embeddings, and metadata. Supports cosine similarity search.
    """

    def __init__(self, embed_model: str = EMBED_MODEL):
        self.embed_model = embed_model
        self.documents: list[str] = []
        self.embeddings: list[list[float]] = []
        self.metadata: list[dict] = []

    def embed(self, text: str) -> list[float]:
        """Get embedding vector for a text string."""
        response = ollama.embeddings(model=self.embed_model, prompt=text)
        return response["embedding"]

    def add(self, text: str, metadata: dict = None) -> int:
        """Add a single document. Returns its index."""
        start = time.time()
        embedding = self.embed(text)
        elapsed = time.time() - start

        self.documents.append(text)
        self.embeddings.append(embedding)
        self.metadata.append(metadata or {})

        idx = len(self.documents) - 1
        console.print(f"[dim]  Embedded doc {idx} ({len(text)} chars) in {elapsed:.2f}s[/dim]")
        return idx

    def add_batch(self, texts: list[str], metadatas: list[dict] = None) -> None:
        """Add multiple documents, showing progress."""
        console.print(f"[cyan]Embedding {len(texts)} documents...[/cyan]")
        start = time.time()

        for i, text in enumerate(texts):
            meta = metadatas[i] if metadatas else {}
            embedding = self.embed(text)
            self.documents.append(text)
            self.embeddings.append(embedding)
            self.metadata.append(meta)

            # Progress indicator
            if (i + 1) % 10 == 0 or i == len(texts) - 1:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                console.print(f"  [{i+1}/{len(texts)}] {rate:.1f} docs/s")

        total = time.time() - start
        console.print(f"[green]Done: {len(texts)} docs in {total:.1f}s "
                      f"({len(texts)/total:.1f} docs/s)[/green]")

    def add_file(self, filepath: str, chunk: bool = True) -> int:
        """Read a text/markdown file and add it (optionally chunked)."""
        path = Path(filepath)
        if not path.exists():
            console.print(f"[red]File not found: {filepath}[/red]")
            return 0

        text = path.read_text(errors="replace")
        source_meta = {"source": path.name, "path": str(path)}

        if chunk:
            chunks = chunk_text(text)
            console.print(f"[cyan]{path.name}: {len(text)} chars → {len(chunks)} chunks[/cyan]")
            for i, chunk_text_part in enumerate(chunks):
                meta = {**source_meta, "chunk": i, "total_chunks": len(chunks)}
                self.add(chunk_text_part, meta)
            return len(chunks)
        else:
            self.add(text, source_meta)
            return 1

    def search(self, query: str, top_k: int = 5,
               min_score: float = 0.0) -> list[dict]:
        """
        Semantic search: find top_k most similar documents to query.

        The search process:
        1. Embed the query → query_vector
        2. Compute cosine similarity between query_vector and all doc vectors
        3. Return top_k highest similarity documents
        """
        if not self.embeddings:
            return []

        query_embedding = self.embed(query)

        # Compute all similarities at once (vectorized with numpy)
        sims = cosine_similarity([query_embedding], self.embeddings)[0]

        # Get indices sorted by descending similarity
        top_indices = np.argsort(sims)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score >= min_score:
                results.append({
                    "index": int(idx),
                    "text": self.documents[idx],
                    "score": score,
                    "metadata": self.metadata[idx],
                })

        return results

    def save(self, filepath: str) -> None:
        """Persist store to JSON file."""
        data = {
            "embed_model": self.embed_model,
            "documents": self.documents,
            "embeddings": self.embeddings,
            "metadata": self.metadata,
        }
        with open(filepath, "w") as f:
            json.dump(data, f)
        size_mb = Path(filepath).stat().st_size / 1_000_000
        console.print(f"[green]Saved {len(self.documents)} docs to {filepath} "
                      f"({size_mb:.1f} MB)[/green]")

    def load(self, filepath: str) -> None:
        """Load store from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        self.embed_model = data.get("embed_model", EMBED_MODEL)
        self.documents = data["documents"]
        self.embeddings = data["embeddings"]
        self.metadata = data["metadata"]
        console.print(f"[green]Loaded {len(self.documents)} documents[/green]")

    def stats(self) -> None:
        """Display store statistics."""
        if not self.documents:
            console.print("[yellow]Store is empty[/yellow]")
            return
        t = Table(title="Vector Store Stats")
        t.add_column("Metric", style="cyan")
        t.add_column("Value")
        t.add_row("Documents", str(len(self.documents)))
        t.add_row("Embedding model", self.embed_model)
        if self.embeddings:
            t.add_row("Embedding dimensions", str(len(self.embeddings[0])))
        avg_len = sum(len(d) for d in self.documents) / len(self.documents)
        t.add_row("Avg document length", f"{avg_len:.0f} chars")
        sources = set(m.get("source", "unknown") for m in self.metadata)
        t.add_row("Unique sources", str(len(sources)))
        console.print(t)


class RAGEngine:
    """
    Retrieval-Augmented Generation: combine vector search with an LLM.

    RAG pipeline:
    1. User asks question
    2. Embed question → search vector store for relevant chunks
    3. Build prompt: [system] + [retrieved context] + [question]
    4. LLM generates answer grounded in retrieved documents
    5. Return answer + sources for transparency
    """

    def __init__(self, store: DocumentStore, llm_model: str = LLM_MODEL):
        self.store = store
        self.llm_model = llm_model

    def ask(self, question: str, top_k: int = 3,
            stream: bool = True) -> dict:
        """Ask a question using retrieved context."""
        if not self.store.documents:
            return {"answer": "No documents loaded. Add documents first.", "sources": []}

        # Step 1: Retrieve relevant chunks
        results = self.store.search(question, top_k=top_k, min_score=0.3)

        if not results:
            return {
                "answer": "No relevant documents found for this question.",
                "sources": [],
            }

        # Step 2: Build context from retrieved chunks
        context_parts = []
        for i, r in enumerate(results):
            source = r["metadata"].get("source", f"doc {r['index']}")
            context_parts.append(f"[Source {i+1}: {source}]\n{r['text']}")
        context = "\n\n".join(context_parts)

        # Step 3: Generate answer
        prompt = (
            f"Answer the question using ONLY the provided context. "
            f"If the context doesn't contain the answer, say so. "
            f"Cite which source(s) you used.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}"
        )

        answer = ""
        if stream:
            print(f"\n\033[94mAnswer:\033[0m ", end="", flush=True)
            for chunk in ollama.generate(
                model=self.llm_model,
                prompt=prompt,
                stream=True,
                options={"temperature": 0.3, "num_predict": 1024},
            ):
                token = chunk["response"]
                print(token, end="", flush=True)
                answer += token
            print()
        else:
            resp = ollama.generate(
                model=self.llm_model,
                prompt=prompt,
                options={"temperature": 0.3, "num_predict": 1024},
            )
            answer = resp["response"]

        return {
            "answer": answer,
            "sources": [
                {
                    "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                    "score": r["score"],
                    "metadata": r["metadata"],
                }
                for r in results
            ],
        }


# ── Interactive CLI ─────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]Nomic Embeddings — Semantic Search & RAG[/bold cyan]\n"
        "[dim]nomic-embed-text + cosine search + LLM answers[/dim]",
        border_style="cyan",
    ))

    store = DocumentStore()
    rag = RAGEngine(store)

    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]add[/cyan]      Add text documents manually")
    console.print("  [cyan]file[/cyan]     Load and embed a file (auto-chunked)")
    console.print("  [cyan]search[/cyan]   Semantic similarity search")
    console.print("  [cyan]ask[/cyan]      RAG question answering")
    console.print("  [cyan]stats[/cyan]    Show store statistics")
    console.print("  [cyan]save[/cyan]     Save store to disk")
    console.print("  [cyan]load[/cyan]     Load store from disk")
    console.print("  [cyan]quit[/cyan]     Exit\n")

    while True:
        try:
            cmd = console.input("[bold blue]vectors>[/bold blue] ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "add":
                console.print("Enter documents — one per line (blank line to finish):")
                texts = []
                while True:
                    line = input()
                    if not line and texts:
                        break
                    if line:
                        texts.append(line)
                if texts:
                    store.add_batch(texts)
                    console.print(f"[green]Added {len(texts)} documents[/green]")

            elif cmd == "file":
                filepath = console.input("File path: ").strip()
                chunk = console.input("Chunk into segments? [Y/n]: ").strip().lower() != "n"
                n = store.add_file(filepath, chunk=chunk)
                console.print(f"[green]Indexed {n} segment(s)[/green]")

            elif cmd == "search":
                query = console.input("Search query: ").strip()
                top_k = int(console.input("Results to show [3]: ").strip() or "3")
                results = store.search(query, top_k=top_k)

                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    continue

                t = Table(title=f"Results for: {query}")
                t.add_column("Rank", style="cyan")
                t.add_column("Score", justify="right")
                t.add_column("Source")
                t.add_column("Text (preview)")
                for i, r in enumerate(results):
                    source = r["metadata"].get("source", f"doc {r['index']}")
                    preview = r["text"][:80].replace("\n", " ") + "..."
                    t.add_row(str(i + 1), f"{r['score']:.3f}", source, preview)
                console.print(t)

            elif cmd == "ask":
                if not store.documents:
                    console.print("[yellow]Add documents first (use 'add' or 'file')[/yellow]")
                    continue
                question = console.input("Question: ").strip()
                top_k = int(console.input("Chunks to retrieve [3]: ").strip() or "3")
                result = rag.ask(question, top_k=top_k)

                # Show sources
                console.print("\n[bold]Sources used:[/bold]")
                for i, s in enumerate(result["sources"]):
                    source = s["metadata"].get("source", "unknown")
                    chunk_n = s["metadata"].get("chunk", "")
                    chunk_label = f" chunk {chunk_n}" if chunk_n != "" else ""
                    console.print(
                        f"  [{i+1}] [cyan]{source}{chunk_label}[/cyan] "
                        f"[dim](similarity: {s['score']:.3f})[/dim]"
                    )
                    console.print(f"      [dim]{s['text']}[/dim]")

            elif cmd == "stats":
                store.stats()

            elif cmd == "save":
                filepath = console.input("Save to file: ").strip() or "vector_store.json"
                store.save(filepath)

            elif cmd == "load":
                filepath = console.input("Load from file: ").strip() or "vector_store.json"
                store.load(filepath)

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
cd ~/projects/nomic_vectors
source venv/bin/activate
python3 vector_store.py
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Build Intuition for Cosine Similarity

```
vectors> add
Enter documents:
The Jetson AGX Orin has 64GB of unified LPDDR5 memory
CUDA enables GPU-accelerated computing with parallel threads
The Jetson uses an ARM-based 12-core CPU running at 2.2 GHz
Docker containers on Jetson need the --runtime nvidia flag
Memory bandwidth is 204.8 GB/s on the Jetson AGX Orin
```

Then search:
```
vectors> search
Query: How much RAM does the Jetson have?
```

Expected: "64GB unified LPDDR5 memory" scores ~0.85, "204.8 GB/s bandwidth" scores ~0.70, CPU/Docker docs score ~0.40.

Try also: `memory speed`, `GPU`, `containers` — notice how related but non-exact matches still score high.

### Exercise 2: Index Your Own Project Files

```
vectors> file
File path: ~/projects/mistral_chat/mistral_chat.py
Chunk: Y

vectors> file
File path: ~/projects/tinyllama/edge_chat.py
Chunk: Y

vectors> stats
```

Then search:
```
vectors> search
Query: sliding window history
```

Expected: Chunks about `max_history` and sliding window logic rank highest across both files.

### Exercise 3: RAG — Question Your Codebase

After indexing files in Exercise 2:
```
vectors> ask
Question: How does conversation history get trimmed when it gets too long?
Chunks to retrieve: 3
```

The model should explain the sliding window mechanism, citing the source file.

```
vectors> ask
Question: What model is used for chat in each project?
```

### Exercise 4: Save and Reload

```
vectors> save
Save to: jetson_docs.json

[restart the program]

vectors> load
Load from: jetson_docs.json

vectors> search
Query: MAXN performance mode
```

The embeddings persist — no re-computation needed.

### Exercise 5: Chunk Size Experiment

Add the same long article twice — once with chunking (Y) and once without (N):
```
vectors> file
File: ~/Desktop/JETSON-CONFIG/getting_started_jetson.md
Chunk: N

vectors> file
File: ~/Desktop/JETSON-CONFIG/getting_started_jetson.md
Chunk: Y
```

Search for a specific detail. Notice: chunked version returns more precise, targeted results. Unchunked returns the whole document with lower precision.

---

## Expected Output

```
vectors> search
Query: GPU memory bandwidth

Rank | Score | Source              | Text (preview)
 1   | 0.891 | nomic_docs          | Memory bandwidth is 204.8 GB/s on...
 2   | 0.743 | nomic_docs          | The Jetson AGX Orin has 64GB of unified...
 3   | 0.512 | nomic_docs          | CUDA enables GPU-accelerated computing...
```

**Embedding speed (MAXN):** ~50–80 documents/minute

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `nomic-embed-text not found` | `docker exec ollama ollama pull nomic-embed-text` |
| Very low similarity scores (<0.3) | The documents don't match the query semantically; rephrase the query |
| `llama3.2 not found` for RAG | `docker exec ollama ollama pull llama3.2` or change `LLM_MODEL` |
| Memory error on large files | Reduce `CHUNK_SIZE` to 300 or increase chunk overlap |

---

## Next Steps

- **[Qwen3 RAG](qwen3-rag.md)** — Production RAG with LangChain + ChromaDB persistent store
- **[Nemo Assistant](nemo-assistant.md)** — Long-context document Q&A without retrieval
- **[Nemotron Nano](nemotron-nano.md)** — Mini-RAG Q&A with pasted context
