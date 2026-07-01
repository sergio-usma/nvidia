# Qwen3 Embedding RAG Pipeline — Production-Quality Document Q&A with ChromaDB

Build a production-quality Retrieval-Augmented Generation (RAG) pipeline that uses `qwen3-embedding` for semantic search and `qwen2.5:7b` for answer generation, with ChromaDB providing persistent vector storage. Documents are indexed once and survive restarts — no re-embedding needed. The system supports bulk indexing, semantic search with similarity scores, RAG Q&A with cited sources, and an interactive query shell.

---

## What You'll Learn

- How to generate high-quality text embeddings via the Ollama embeddings API
- Using ChromaDB as a persistent local vector database (no cloud, no API keys)
- Building a complete RAG pipeline: index → retrieve → augment → generate
- Citing sources in model responses so answers are grounded and traceable
- Chunking long documents for better retrieval precision
- Combining semantic similarity scores with generative answers in a rich CLI

## Prerequisites

```bash
# Ensure Ollama container is running
docker ps | grep ollama

# Pull embedding model (Ollama runs in Docker — always use docker exec)
docker exec ollama ollama pull qwen3-embedding

# Pull the generation model
docker exec ollama ollama pull qwen2.5:7b

# Verify both are present
docker exec ollama ollama list
```

```bash
# Set MAXN mode for inference
sudo nvpmodel -m 0
sudo jetson_clocks
```

---

## Step 1 — Project Setup

```bash
mkdir -p ~/projects/qwen3-rag
cd ~/projects/qwen3-rag
python3 -m venv venv
source venv/bin/activate
pip install ollama chromadb rich
```

ChromaDB will create a local persistent database directory automatically. No server to run.

---

## Step 2 — Create the RAG Pipeline

Save as `~/projects/qwen3-rag/rag_pipeline.py`:

```python
#!/usr/bin/env python3
"""
Qwen3 Embedding RAG Pipeline
Production-quality RAG with ChromaDB persistence, source citation,
semantic search, and interactive Q&A.

Models:
  - qwen3-embedding  (Ollama Docker) -- document and query embeddings
  - qwen2.5:7b       (Ollama Docker) -- answer generation

Storage:
  - ChromaDB (local disk at ~/projects/qwen3-rag/chroma_db/)

Jetson AGX Orin 64GB / JetPack 6.2.2 / CUDA 12.6
"""

import time
import sys
import argparse
import hashlib
from pathlib import Path
from typing import Optional
import ollama
import chromadb
from chromadb.config import Settings
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

console = Console()

# ── Configuration ─────────────────────────────────────────────────────────────

EMBED_MODEL   = "qwen3-embedding"
GEN_MODEL     = "qwen2.5:7b"
OLLAMA_HOST   = "http://localhost:11434"
DB_PATH       = str(Path.home() / "projects" / "qwen3-rag" / "chroma_db")
COLLECTION    = "documents"
CHUNK_SIZE    = 400   # characters per chunk
CHUNK_OVERLAP = 80    # overlap between consecutive chunks
TOP_K         = 4     # documents to retrieve per query

SYSTEM_RAG = """You are a precise, helpful assistant that answers questions using only
the provided context documents. Rules:
1. Base your answer ONLY on the context provided -- do not use outside knowledge.
2. At the end of your answer, list the sources you used as: Sources: [doc_id, ...]
3. If the context does not contain enough information to answer, say:
   "The provided documents do not contain enough information to answer this question."
4. Be concise and accurate. Quote directly from sources when helpful."""


# ── ChromaDB setup ────────────────────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    """Open or create the persistent ChromaDB collection."""
    client = chromadb.PersistentClient(
        path=DB_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list:
    """Generate an embedding for a single text using qwen3-embedding via Ollama."""
    ollama_client = ollama.Client(host=OLLAMA_HOST)
    try:
        response = ollama_client.embeddings(
            model=EMBED_MODEL,
            prompt=text,
        )
        return response["embedding"]
    except ollama.ResponseError as e:
        console.print(f"[red]Embedding error: {e}[/red]")
        if "not found" in str(e).lower():
            console.print(
                f"[yellow]Pull the model:[/yellow] "
                f"docker exec ollama ollama pull {EMBED_MODEL}"
            )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Connection error: {e}[/red]")
        console.print("[yellow]Check:[/yellow] docker ps | grep ollama")
        sys.exit(1)


def embed_batch(texts: list) -> list:
    """Embed a list of texts, showing a progress bar."""
    embeddings = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding documents...", total=len(texts))
        for text in texts:
            embeddings.append(embed_text(text))
            progress.advance(task)
    return embeddings


# ── Text chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """
    Split text into overlapping chunks.
    Tries to break at sentence boundaries ('. ') where possible.
    """
    if len(text) <= size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Try to cut at the last sentence boundary within the window
        boundary = text.rfind(". ", start, end)
        if boundary != -1 and boundary > start + size // 2:
            end = boundary + 1  # include the period
        chunks.append(text[start:end].strip())
        start = end - overlap  # overlap for context continuity
    return [c for c in chunks if c]


# ── Indexing ──────────────────────────────────────────────────────────────────

def make_doc_id(source: str, chunk_index: int) -> str:
    """Generate a stable, unique ID for a document chunk."""
    raw = f"{source}::chunk_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def index_document(
    text: str,
    source: str,
    collection: chromadb.Collection,
    metadata: Optional[dict] = None,
    overwrite: bool = False,
) -> int:
    """
    Index a document into ChromaDB with chunking.
    Returns the number of chunks added.
    """
    chunks = chunk_text(text)
    ids = [make_doc_id(source, i) for i in range(len(chunks))]

    if overwrite:
        existing = collection.get(where={"source": source})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])

    # Skip already-indexed chunks
    existing_ids = set(collection.get(ids=ids)["ids"])
    new_pairs = [(c, i) for i, c in zip(ids, chunks) if i not in existing_ids]

    if not new_pairs:
        return 0

    texts_to_embed = [p[0] for p in new_pairs]
    chunk_ids = [p[1] for p in new_pairs]

    embeddings = embed_batch(texts_to_embed)

    base_meta = {"source": source}
    if metadata:
        base_meta.update(metadata)

    metas = [
        {**base_meta, "chunk_index": idx, "chunk_total": len(chunks)}
        for idx in range(len(new_pairs))
    ]

    collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=texts_to_embed,
        metadatas=metas,
    )
    return len(new_pairs)


def index_file(filepath: str, collection: chromadb.Collection, overwrite: bool = False) -> int:
    """Read a text file and index it."""
    path = Path(filepath)
    if not path.exists():
        console.print(f"[red]File not found: {filepath}[/red]")
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    source = path.name
    return index_document(text, source, collection, overwrite=overwrite)


# ── Search ────────────────────────────────────────────────────────────────────

def semantic_search(
    query: str,
    collection: chromadb.Collection,
    top_k: int = TOP_K,
) -> list:
    """
    Embed the query and retrieve the top_k most similar chunks.
    Returns list of dicts with keys: id, text, source, chunk, score.
    """
    if collection.count() == 0:
        return []

    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity in [0, 1]
        score = 1.0 - (distance / 2.0)
        hits.append({
            "id":     results["ids"][0][i],
            "text":   results["documents"][0][i],
            "source": results["metadatas"][0][i].get("source", "unknown"),
            "chunk":  results["metadatas"][0][i].get("chunk_index", 0),
            "score":  score,
        })
    return hits


# ── RAG generation ────────────────────────────────────────────────────────────

def rag_answer(
    query: str,
    collection: chromadb.Collection,
    top_k: int = TOP_K,
) -> tuple:
    """
    Full RAG pipeline: retrieve relevant chunks, then generate a cited answer.
    Returns (answer_text, retrieved_hits).
    """
    hits = semantic_search(query, collection, top_k=top_k)

    if not hits:
        return "No documents indexed yet. Run with --index first.", []

    # Build context block with labeled source references
    context_parts = []
    for i, hit in enumerate(hits, 1):
        context_parts.append(
            f"[Document {i} | source: {hit['source']} | chunk: {hit['chunk']}]\n"
            f"{hit['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"Context documents:\n\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer (cite sources by document number):"
    )

    ollama_client = ollama.Client(host=OLLAMA_HOST)
    messages = [
        {"role": "system", "content": SYSTEM_RAG},
        {"role": "user",   "content": prompt},
    ]

    console.print(Rule("[bold cyan]Generated Answer[/bold cyan]"))

    full_text = ""
    token_count = 0
    start = time.time()

    try:
        stream = ollama_client.chat(model=GEN_MODEL, messages=messages, stream=True)
        for chunk in stream:
            delta = chunk["message"]["content"]
            full_text += delta
            token_count += 1
            console.print(delta, end="", markup=False)

    except ollama.ResponseError as e:
        console.print(f"\n[red]Generation error: {e}[/red]")
        if "not found" in str(e).lower():
            console.print(
                f"[yellow]Pull:[/yellow] docker exec ollama ollama pull {GEN_MODEL}"
            )
        return "", hits

    elapsed = time.time() - start
    tps = token_count / elapsed if elapsed > 0 else 0.0

    console.print()
    console.print(
        Rule(
            f"[dim]{token_count} tokens · {elapsed:.1f}s · "
            f"[bold green]{tps:.1f} tok/s[/bold green][/dim]"
        )
    )
    return full_text, hits


# ── Display helpers ───────────────────────────────────────────────────────────

def print_search_results(hits: list) -> None:
    if not hits:
        console.print("[yellow]No results found.[/yellow]")
        return
    table = Table(
        title="Semantic Search Results",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Rank",    width=4,  justify="right")
    table.add_column("Score",   width=7,  justify="right", style="green")
    table.add_column("Source",  max_width=22)
    table.add_column("Chunk",   width=5,  justify="right")
    table.add_column("Preview", max_width=52)

    for i, hit in enumerate(hits, 1):
        preview = hit["text"][:120].replace("\n", " ") + "..."
        table.add_row(
            str(i),
            f"{hit['score']:.4f}",
            hit["source"],
            str(hit["chunk"]),
            preview,
        )
    console.print(table)


def print_db_stats(collection: chromadb.Collection) -> None:
    count = collection.count()
    table = Table(title="Knowledge Base Status", box=box.SIMPLE_HEAD, border_style="dim")
    table.add_column("Property", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Collection name",     COLLECTION)
    table.add_row("Total chunks indexed", str(count))
    table.add_row("Embedding model",     EMBED_MODEL)
    table.add_row("Generation model",    GEN_MODEL)
    table.add_row("Database path",       DB_PATH)
    table.add_row("Chunk size",          f"{CHUNK_SIZE} chars")
    table.add_row("Chunk overlap",       f"{CHUNK_OVERLAP} chars")
    table.add_row("Top-K retrieval",     str(TOP_K))
    console.print(table)


# ── Sample documents ──────────────────────────────────────────────────────────

SAMPLE_DOCS = [
    {
        "source": "jetson_overview.txt",
        "text": (
            "The NVIDIA Jetson AGX Orin is NVIDIA's flagship edge AI module. "
            "It delivers up to 275 TOPS of INT8 performance using a 12-core "
            "ARM Cortex-A78AE CPU and an Ampere GPU with 2048 CUDA cores and "
            "64 Tensor Cores. The 64GB variant provides 64GB of LPDDR5 unified "
            "memory shared between CPU and GPU. JetPack 6.2 ships with CUDA 12.6, "
            "TensorRT 10.3, cuDNN 9.3, and DeepStream 7. The Jetson unified memory "
            "architecture means GPU and CPU share the same physical memory, eliminating "
            "PCIe copy overhead present in discrete GPU systems. The module supports NVMe "
            "SSD via M.2 slot, USB 3.2, PCIe Gen4, and multiple camera interfaces (MIPI CSI-2). "
            "Power modes range from 15W (MODE_15W) up to full MAXN mode which uses up to 60W. "
            "The nvpmodel command controls power mode: sudo nvpmodel -m 0 enables MAXN. "
            "jetson_clocks locks all clocks to maximum for sustained performance. "
            "For monitoring, jtop provides a comprehensive dashboard of CPU, GPU, memory, "
            "and thermal data specific to Jetson hardware."
        ),
    },
    {
        "source": "rag_explained.txt",
        "text": (
            "Retrieval-Augmented Generation (RAG) is an AI technique that enhances language "
            "models by connecting them to an external knowledge base at inference time. "
            "RAG has two phases: indexing and querying. During indexing, documents are split "
            "into chunks, each chunk is converted to a dense vector embedding using an "
            "embedding model, and those vectors are stored in a vector database. "
            "During querying, the user question is embedded using the same model, the "
            "vector database finds the most similar document chunks via cosine similarity, "
            "and those chunks are passed as context to the language model along with the query. "
            "The LLM generates an answer grounded in the retrieved documents. "
            "RAG reduces hallucination because the model is constrained to retrieved context. "
            "It allows updating the knowledge base without retraining the LLM. "
            "Key parameters: chunk size (larger gives more context per chunk but less precision), "
            "top-k (how many chunks to retrieve), and similarity threshold. "
            "Popular vector databases for RAG: ChromaDB (local), Pinecone (cloud), "
            "Qdrant, Weaviate, and FAISS. ChromaDB is ideal for local Jetson deployments "
            "because it requires no server and stores data on disk as SQLite and Parquet."
        ),
    },
    {
        "source": "ollama_guide.txt",
        "text": (
            "Ollama is an open-source tool for running large language models locally. "
            "It provides a simple HTTP API compatible with the OpenAI API format. "
            "On Jetson, Ollama runs inside the dustynv/ollama Docker container which includes "
            "CUDA 12.6 support compiled for aarch64 (ARM64). "
            "To start the container: docker run --runtime nvidia --gpus all -d -p 11434:11434 "
            "--name ollama dustynv/ollama:r36.4.0. "
            "Models are pulled with: docker exec ollama ollama pull <model_name>. "
            "The Ollama Python SDK communicates with the server at http://localhost:11434. "
            "Key API methods: ollama.chat() for conversational inference, ollama.generate() "
            "for single-shot completion, and ollama.embeddings() for dense vector embeddings. "
            "Streaming is enabled by passing stream=True to chat() or generate(). "
            "The embeddings() endpoint returns a list of floats representing the semantic "
            "position of the input in the model latent space. "
            "Supported embedding models include qwen3-embedding (0.6B, 1024-dim), "
            "nomic-embed-text (137M, 768-dim), and mxbai-embed-large (334M, 1024-dim). "
            "Ollama keeps models in GPU memory between requests for low-latency reuse. "
            "OLLAMA_KEEP_ALIVE environment variable controls how long models stay loaded."
        ),
    },
    {
        "source": "chromadb_guide.txt",
        "text": (
            "ChromaDB is an open-source vector database designed for embedding storage and "
            "similarity search. It runs entirely in-process with no server required when using "
            "PersistentClient, storing data as SQLite and Parquet files on local disk. "
            "Key concepts: a Collection is a named set of embeddings, documents, and metadata. "
            "Documents are added with collection.add(ids, embeddings, documents, metadatas). "
            "Similarity search is performed with collection.query(query_embeddings, n_results). "
            "ChromaDB uses cosine distance by default when hnsw:space is set to cosine. "
            "Distance values range from 0 (identical) to 2 (opposite vectors), "
            "so similarity = 1 - (distance / 2). "
            "The PersistentClient constructor takes a path parameter pointing to storage. "
            "Collections persist across Python process restarts automatically. "
            "Filtering by metadata is supported via the where parameter. "
            "ChromaDB supports HNSW indexing which provides approximate nearest neighbor "
            "search with O(log n) query complexity. "
            "For Jetson, ChromaDB is installed with pip install chromadb. "
            "It requires no GPU and runs on CPU, so it does not compete with the LLM for memory."
        ),
    },
    {
        "source": "quantization_guide.txt",
        "text": (
            "Model quantization reduces the precision of weights from 32-bit floats (FP32) "
            "to lower bit-widths, reducing memory footprint and increasing inference speed. "
            "Common formats: FP16 (16-bit float, roughly 2x memory reduction, negligible quality "
            "loss), INT8 (8-bit integer, roughly 4x reduction, small quality loss), "
            "INT4 (4-bit, roughly 8x reduction, noticeable quality loss on smaller models). "
            "GGUF is the file format used by llama.cpp, supporting Q2_K through Q8_0 quantization. "
            "Q4_K_M is widely recommended as the best quality/size tradeoff: "
            "it uses 4-bit for most weights and higher precision for key layers. "
            "Q8_0 is near-lossless but only marginally smaller than FP16. "
            "On Jetson AGX Orin, the Ampere GPU supports FP16 and INT8 natively in hardware "
            "via Tensor Cores, giving a significant speedup over FP32. "
            "TensorRT can further optimize quantized models through layer fusion, kernel autotuning, "
            "and activation caching. For GGUF models in Ollama or llama.cpp, quantization is "
            "applied at download/conversion time. The user selects quantization level by choosing "
            "the appropriate GGUF file, for example model-Q4_K_M.gguf. "
            "Embedding models like qwen3-embedding are typically kept at FP16 precision "
            "because embedding quality is sensitive to quantization noise."
        ),
    },
]


# ── Mode functions ────────────────────────────────────────────────────────────

def run_index_demo(collection: chromadb.Collection) -> None:
    """Index the built-in sample documents."""
    console.print(
        Panel(
            f"[bold]Indexing {len(SAMPLE_DOCS)} sample documents[/bold]\n"
            f"[dim]Embedding model: {EMBED_MODEL} · Chunk size: {CHUNK_SIZE} chars[/dim]",
            border_style="yellow",
            title="Document Indexer",
        )
    )
    total_added = 0
    for doc in SAMPLE_DOCS:
        console.print(f"\n[bold yellow]Source:[/bold yellow] {doc['source']}")
        added = index_document(doc["text"], doc["source"], collection)
        if added:
            console.print(f"  [green]Added {added} chunks[/green]")
            total_added += added
        else:
            console.print("  [dim]Already indexed (skipped)[/dim]")

    console.print()
    console.print(
        Panel(
            f"[green]Indexing complete.[/green]\n"
            f"New chunks added: [bold]{total_added}[/bold]\n"
            f"Total in database: [bold]{collection.count()}[/bold]",
            border_style="green",
        )
    )


def run_index_file(filepath: str, collection: chromadb.Collection) -> None:
    """Index a user-specified text file."""
    console.print(f"[bold]Indexing file:[/bold] {filepath}")
    added = index_file(filepath, collection)
    if added:
        console.print(
            f"[green]Added {added} chunks. Total in DB: {collection.count()}[/green]"
        )
    else:
        console.print("[yellow]No new chunks added (already indexed or file empty).[/yellow]")


def run_search(query: str, collection: chromadb.Collection) -> None:
    """Semantic search without LLM generation."""
    console.print(
        Panel(
            f"[bold]Query:[/bold] {query}",
            title="[cyan]Semantic Search[/cyan]",
            border_style="cyan",
        )
    )
    start = time.time()
    hits = semantic_search(query, collection, top_k=TOP_K)
    elapsed = time.time() - start

    print_search_results(hits)
    console.print(f"[dim]Search time: {elapsed * 1000:.1f}ms[/dim]")


def run_rag(query: str, collection: chromadb.Collection) -> None:
    """Full RAG: retrieve + show results + generate cited answer."""
    console.print(
        Panel(
            f"[bold]Question:[/bold] {query}",
            title="[cyan]RAG Query[/cyan]",
            border_style="cyan",
        )
    )

    if collection.count() == 0:
        console.print(
            "[yellow]Knowledge base is empty. Run with --index first.[/yellow]"
        )
        return

    console.print("[dim]Retrieving relevant documents...[/dim]")
    hits = semantic_search(query, collection, top_k=TOP_K)

    if not hits:
        console.print("[yellow]No relevant documents found.[/yellow]")
        return

    console.print()
    print_search_results(hits)
    console.print()

    rag_answer(query, collection, top_k=TOP_K)


def run_interactive(collection: chromadb.Collection) -> None:
    """Interactive Q&A shell backed by the persistent knowledge base."""
    console.print(
        Panel(
            "[bold cyan]RAG Interactive Shell[/bold cyan]\n"
            f"[dim]Knowledge base: {collection.count()} chunks indexed\n"
            f"Embedding: {EMBED_MODEL} · Generation: {GEN_MODEL}\n\n"
            "Type a question to get a cited answer from your documents.\n"
            "Commands:\n"
            "  [bold]/search <query>[/bold]    semantic search only (no generation)\n"
            "  [bold]/index <path>[/bold]      index a text file into the knowledge base\n"
            "  [bold]/stats[/bold]             show database statistics\n"
            "  [bold]/quit[/bold]              exit[/dim]",
            border_style="cyan",
        )
    )

    if collection.count() == 0:
        console.print(
            "[yellow]Warning: no documents indexed yet. "
            "Run[/yellow] [bold]python3 rag_pipeline.py --index[/bold] [yellow]first.[/yellow]\n"
        )

    while True:
        try:
            user_input = console.input("\n[bold cyan]Q>[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.lower() == "/stats":
            print_db_stats(collection)
            continue

        if user_input.lower().startswith("/search "):
            run_search(user_input[8:].strip(), collection)
            continue

        if user_input.lower().startswith("/index "):
            run_index_file(user_input[7:].strip(), collection)
            continue

        # Default: full RAG Q&A
        run_rag(user_input, collection)


# ── Help menu ─────────────────────────────────────────────────────────────────

def print_menu(collection: chromadb.Collection) -> None:
    table = Table(
        title="Qwen3 Embedding RAG Pipeline",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Mode",          style="bold")
    table.add_column("Flag",          style="green")
    table.add_column("Description")

    table.add_row("Index samples",   "--index",              "Index 5 built-in sample documents")
    table.add_row("Index file",      "--index-file <path>",  "Index any plain-text or markdown file")
    table.add_row("Semantic search", "--search 'query'",     "Semantic search only (no generation)")
    table.add_row("RAG Q&A",         "--ask 'question'",     "Full RAG: retrieve + generate + cite")
    table.add_row("Interactive",     "--chat",               "Interactive Q&A shell")
    table.add_row("Stats",           "--stats",              "Show database statistics")

    console.print(table)
    console.print(
        f"\n[dim]DB path: {DB_PATH}[/dim]\n"
        f"[dim]Chunks currently indexed: {collection.count()}[/dim]"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Qwen3 Embedding RAG pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--index",       action="store_true", help="Index sample documents")
    group.add_argument("--index-file",  metavar="PATH",      help="Index a text file")
    group.add_argument("--search",      metavar="QUERY",     help="Semantic search only")
    group.add_argument("--ask",         metavar="QUESTION",  help="Full RAG Q&A")
    group.add_argument("--chat",        action="store_true", help="Interactive Q&A shell")
    group.add_argument("--stats",       action="store_true", help="Show database stats")
    args = parser.parse_args()

    console.print(
        Panel(
            "[bold cyan]Qwen3 Embedding RAG Pipeline[/bold cyan]\n"
            f"[dim]Embed: {EMBED_MODEL} · Generate: {GEN_MODEL} · "
            f"Store: ChromaDB (persistent)[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )

    collection = get_collection()

    if args.index:
        run_index_demo(collection)
    elif args.index_file:
        run_index_file(args.index_file, collection)
    elif args.search:
        run_search(args.search, collection)
    elif args.ask:
        run_rag(args.ask, collection)
    elif args.chat:
        run_interactive(collection)
    elif args.stats:
        print_db_stats(collection)
    else:
        print_menu(collection)


if __name__ == "__main__":
    main()
```

---

## Step 3 — Run It

```bash
cd ~/projects/qwen3-rag
source venv/bin/activate

# Show available modes and current DB status
python3 rag_pipeline.py

# Step A: Index the 5 sample documents (run once — DB persists on disk)
python3 rag_pipeline.py --index

# Step B: Semantic search only (fast — no LLM generation)
python3 rag_pipeline.py --search "how does quantization work on Jetson?"

# Step C: Full RAG Q&A with source citation
python3 rag_pipeline.py --ask "What is ChromaDB and how does it store data?"

# Step D: Index your own text file
python3 rag_pipeline.py --index-file ~/my_notes.txt

# Step E: Interactive Q&A shell (best for exploration)
python3 rag_pipeline.py --chat

# Check DB stats
python3 rag_pipeline.py --stats
```

---

## Step 4 — Hands-On Exercises

### Exercise 1: Verify persistence
Index the sample documents, exit Python, and confirm the data survived:

```bash
python3 rag_pipeline.py --index
python3 rag_pipeline.py --stats    # note the chunk count
# Close the terminal, open a new one:
source ~/projects/qwen3-rag/venv/bin/activate
python3 rag_pipeline.py --stats    # should show the same chunk count
```

ChromaDB writes to `~/projects/qwen3-rag/chroma_db/`. The data is on disk, not in RAM.

### Exercise 2: Source attribution accuracy test
Ask a question whose answer can only come from one document:

```bash
python3 rag_pipeline.py --ask "What is the nvpmodel command and what does MAXN mode do?"
```

The answer should cite `jetson_overview.txt`. Then ask:

```bash
python3 rag_pipeline.py --ask "How does ChromaDB handle approximate nearest neighbor search?"
```

This should cite `chromadb_guide.txt`. Verify the model correctly attributes its sources.

### Exercise 3: Out-of-scope question test
Ask something not in any indexed document:

```bash
python3 rag_pipeline.py --ask "What is the best pizza restaurant in Barcelona?"
```

The model should reply with the configured fallback: "The provided documents do not contain enough information to answer this question." This confirms the RAG system refuses to hallucinate from outside the knowledge base.

### Exercise 4: Index a real document from your Jetson
Index one of the actual guide files from this project:

```bash
python3 rag_pipeline.py --index-file \
  ~/Desktop/JETSON-CONFIG/jetson-getting-started/getting_started_jetson.md

python3 rag_pipeline.py --ask "How do I install PyTorch on Jetson?"
```

### Exercise 5: Chunking impact experiment
Edit `rag_pipeline.py` and change `CHUNK_SIZE = 400` to `CHUNK_SIZE = 150`. Delete the old DB and re-index:

```bash
rm -rf ~/projects/qwen3-rag/chroma_db
python3 rag_pipeline.py --index
python3 rag_pipeline.py --stats   # should show more chunks than before
```

Ask the same question from Exercise 2 and compare answer quality. Smaller chunks improve retrieval precision but give the LLM less surrounding context per chunk.

---

## Expected Output

```
╭────────────────────────────────────────────────────────────╮
│  Qwen3 Embedding RAG Pipeline                              │
│  Embed: qwen3-embedding · Generate: qwen2.5:7b · ChromaDB │
╰────────────────────────────────────────────────────────────╯

Q> What embedding models does Ollama support?

╭─ RAG Query ─────────────────────────────────────────────────╮
│  Question: What embedding models does Ollama support?       │
╰─────────────────────────────────────────────────────────────╯
Retrieving relevant documents...

  Semantic Search Results
 ┌──────┬────────┬─────────────────────┬───────┬───────────────┐
 │ Rank │  Score │ Source              │ Chunk │ Preview       │
 ├──────┼────────┼─────────────────────┼───────┼───────────────┤
 │    1 │ 0.9241 │ ollama_guide.txt    │     1 │ ...qwen3...   │
 │    2 │ 0.8817 │ chromadb_guide.txt  │     0 │ ...vector...  │
 └──────┴────────┴─────────────────────┴───────┴───────────────┘

──────────────── Generated Answer ──────────────────────────────
According to the documentation, Ollama supports several embedding
models including qwen3-embedding (0.6B, 1024-dim), nomic-embed-text
(137M, 768-dim), and mxbai-embed-large (334M, 1024-dim).

Sources: [Document 1 — ollama_guide.txt]
──────────── 89 tokens · 5.8s · 15.3 tok/s ─────────────────────
```

**Performance (MAXN):**
- Embedding with qwen3-embedding: ~8–12ms per chunk
- Generation with qwen2.5:7b: ~15–18 tok/s
- ChromaDB cosine search: under 5ms for collections up to ~10,000 chunks

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `model "qwen3-embedding" not found` | `docker exec ollama ollama pull qwen3-embedding` |
| `model "qwen2.5:7b" not found` | `docker exec ollama ollama pull qwen2.5:7b` |
| `Connection refused localhost:11434` | `docker start ollama` or check `docker ps` |
| `ModuleNotFoundError: chromadb` | `pip install chromadb` inside the venv |
| ChromaDB version conflict on install | `pip install chromadb --upgrade` |
| DB appears empty after restart | Confirm `DB_PATH` in the script matches where you indexed |
| Answers cite wrong sources | Lower `CHUNK_SIZE` for more precise retrieval |
| Slow embedding (less than 1 chunk/sec) | `sudo nvpmodel -m 0`; note that Ollama embeddings run on CPU |
| High RAM usage | ChromaDB itself is lightweight; check with `jtop` |
| All docs show "already indexed (skipped)" | Normal on re-run — chunks are deduplicated by hash |

---

## Next Steps

- `qwen25-logic.md` — use Qwen2.5 for structured logical reasoning on retrieved content
- `gpt-oss.md` — swap in `gpt-oss:20b` as the generator for higher-quality answers
- `glm-flash.md` — use GLM Flash as the generator for faster (lower-latency) RAG
- `../../../../experiment_llm_nvidia.md` — full voice + vision + RAG pipeline with Docker Compose
- `../../../../use_jetson_as_local_ai_server.md` — expose this RAG pipeline as a network API
