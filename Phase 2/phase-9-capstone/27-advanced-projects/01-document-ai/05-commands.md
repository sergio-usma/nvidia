# Usage & Commands

Complete command reference for the File Intelligence Hub.

## Main Commands

```bash
# Enable performance mode (always do this first)
sudo nvpmodel -m 0
sudo jetson_clocks

# Start Ollama
ollama serve &

# Pull required models
ollama pull nomic-embed-text
ollama pull qwen2.5-coder
```

## Scan Commands

```bash
# Scan a directory
python main.py scan --path /home/jetson/Documents

# Scan multiple directories
python main.py scan --path /home/jetson/Documents /home/jetson/Downloads

# Scan with exclusions
python main.py scan --path /home/jetson/Documents --exclude ".git,node_modules,__pycache__"

# Scan external drive
python main.py scan --path /media/jetson/usb/Documents
```

## Index Commands

```bash
# Create/update RAG index from scanned files
python main.py index

# Rebuild index from scratch
python main.py index --rebuild

# Build knowledge graph
python main.py graph --build
```

## Duplicate Commands

```bash
# Find duplicates
python main.py duplicates

# Find duplicates in specific path
python main.py duplicates --path /home/jetson/Documents

# Generate duplicate report
python main.py duplicates --report markdown

# Export duplicates to CSV
python main.py duplicates --export csv
```

## Query Commands

```bash
# Semantic search
python main.py query "machine learning tutorials"

# Graph-based search
python main.py query --graph "files about Python"

# Find related files
python main.py related /path/to/file.pdf
```

## API Server

```bash
# Start API server
python main.py serve --port 5000

# With authentication
python main.py serve --port 5000 --auth

# Background mode
python main.py serve --port 5000 &
```

## Configuration

Create `.env` file:

```bash
# .env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder
EMBEDDING_MODEL=nomic-embed-text

MAX_FILE_SIZE=100MB
BATCH_SIZE=10
PARALLEL_WORKERS=4

SIMILARITY_THRESHOLD=0.85
MIN_DUPLICATE_SIZE=1024

SCAN_PATHS=/home/jetson/Documents
EXCLUDE_PATHS=.git,node_modules,__pycache__,venv

API_PORT=5000
API_AUTH=false
```

## Programmatic Usage

```python
from scanner.file_scanner import FileScanner
from scanner.text_extractor import TextExtractor
from scanner.parallel_scanner import ParallelScanner
from rag.embedding_engine import EmbeddingEngine
from rag.vector_store import VectorStore
from rag.duplicate_detector import DuplicateDetector

# Configuration
config = {
    'ollama_host': 'http://localhost:11434',
    'embedding_model': 'nomic-embed-text',
    'similarity_threshold': 0.85,
    'batch_size': 10,
    'parallel_workers': 4
}

# Initialize components
scanner = FileScanner(config)
extractor = TextExtractor()
parallel = ParallelScanner(scanner, extractor)

# Scan files
files = parallel.scan_with_content(['/path/to/scan'])

# Create embeddings
embedding_engine = EmbeddingEngine(config)
for f in files:
    f['embedding'] = embedding_engine.generate_file_embedding(f)

# Store in vector database
vector_store = VectorStore(config)
vector_store.add_embeddings(files)

# Find duplicates
detector = DuplicateDetector(config, vector_store, embedding_engine)
duplicates = detector.find_duplicates(files)

print(f"Found {len(duplicates)} duplicates")
```

## API Endpoints

When running the API server:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/scan` | POST | Scan new path |
| `/search` | POST | Semantic search |
| `/duplicates` | GET | Get duplicate list |
| `/graph/query` | POST | Query knowledge graph |
| `/files/{id}` | GET | Get file info |

## Example Output

### Duplicate Report (Markdown)

```markdown
# Duplicate Files Report

Generated: 2024-01-15T10:30:00

Total duplicates: 45

## Duplicate Groups: 12

### Group: exact_abc123

- ✓ KEEP
  Path: /home/jetson/Documents/Project/report_final.pdf
  Size: 2048576 bytes
  Modified: 2024-01-10T15:30:00
  Reason: Newest version - KEEP

- ✗ DELETE (recommended)
  Path: /home/jetson/Backup/report_final.pdf
  Size: 2048576 bytes
  Modified: 2024-01-05T10:00:00
  Reason: Older version
```

## Troubleshooting

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check vector store
ls -la data/embeddings/

# Clear cache
rm -rf data/embeddings/chroma
rm -rf data/cache/*

# Verbose logging
python main.py --debug scan --path /path/to/scan
```

## Next Steps

Continue to Project 2: [Yacht Jobs Overview](./06-yacht-jobs-overview.md)
