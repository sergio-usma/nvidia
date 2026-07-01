# Production Deployment

Deploy the Ebook Summarizer Factory at scale for processing 200,000+ books.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Production Architecture                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │  Scheduler   │────▶│  Worker      │────▶│  Worker      │     │
│  │  (Cron/API)  │     │  Queue       │     │  Pool        │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                             │                     │               │
│                             ▼                     ▼               │
│                      ┌──────────────┐     ┌──────────────┐       │
│                      │  Processor   │     │  Processor   │       │
│                      │  (4 cores)   │     │  (4 cores)   │       │
│                      └──────────────┘     └──────────────┘       │
│                             │                     │               │
│                             └──────────┬──────────┘               │
│                                        ▼                          │
│  ┌──────────────┐     ┌──────────────┐                           │
│  │   Vector    │◀────│  Database    │                           │
│  │   Store     │     │  (Results)   │                           │
│  └──────────────┘     └──────────────┘                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Celery Workers

```python
# tasks/celery_app.py
from celery import Celery
from celery.config import Config

app = Celery('ebook_summarizer')

app.config_from_object({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/1',
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'task_routes': {
        'tasks.process_book': {'queue': 'processing'},
        'tasks.scan_library': {'queue': 'scan'},
    },
    'worker_prefetch_multiplier': 1,
    'task_acks_late': True,
    'worker_max_tasks_per_child': 50,
})

# tasks/processing.py
from tasks.celery_app import app
from processor.epub_parser import EPUBParser
from processor.pdf_parser import PDFParser
from agents.orchestrator import Orchestrator
from formatter.output_formatter import OutputFormatter
import os

@app.task
def process_book_task(book_path: str, config: dict) -> dict:
    """Process a single book"""
    
    # Get book type
    ext = os.path.splitext(book_path)[1].lower()
    
    if ext == '.epub':
        parser = EPUBParser()
    else:
        parser = PDFParser()
    
    # Parse
    book_data = parser.parse(book_path)
    
    if not book_data:
        return {'error': 'Failed to parse', 'path': book_path}
    
    # Process
    orchestrator = Orchestrator(config)
    result = orchestrator.process_book(book_data)
    
    # Save output
    formatter = OutputFormatter(config)
    saved = formatter.save_output(result, ['markdown', 'text'])
    
    return {
        'title': result['title'],
        'status': 'completed',
        'output_files': saved,
        'stats': result['stats']
    }

@app.task
def scan_library_task(library_path: str, config: dict) -> dict:
    """Scan library and queue all books"""
    
    from processor.scanner import BookScanner
    
    scanner = BookScanner(config)
    books = scanner.scan_directory(library_path)
    
    # Queue each book
    queued = 0
    for book in books:
        process_book_task.delay(book['path'], config)
        queued += 1
    
    return {
        'total_books': len(books),
        'queued': queued
    }
```

## Queue Management

```bash
# Start worker
celery -A tasks.celery_app worker -Q processing -c 4 --loglevel=info

# Start scan worker
celery -A tasks.celery_app worker -Q scan -c 1 --loglevel=info

# Start beat scheduler
celery -A tasks.celery_app beat --loglevel=info
```

## Systemd Services

```ini
# /etc/systemd/system/ebook-worker.service
[Unit]
Description=Ebook Summarizer Worker
After=network.target

[Service]
Type=forking
User=jetson
WorkingDirectory=/home/jetson/ebook-summarizer
ExecStart=/usr/bin/celery -A tasks.celery_app worker -Q processing -c 4 --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Performance Optimization

### GPU Acceleration

```python
# Use GPU for Ollama
config = {
    'ollama_model': 'qwen2.5-coder',
    'ollama_host': 'http://localhost:11434',
    # Add GPU layers
}

# Ensure CUDA is available
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
```

### Memory Management

```python
# Process large books in chunks
def process_large_book(book_path: str, config: dict):
    parser = EPUBParser()
    book_data = parser.parse(book_path)
    
    # Check size
    if book_data['word_count'] > 100000:
        # Process in stages
        chunks = split_book_into_chunks(book_data['full_text'])
        
        partial_results = []
        for chunk in chunks:
            result = process_chunk(chunk, config)
            partial_results.append(result)
        
        # Merge results
        final = merge_results(partial_results)
        return final
    else:
        return process_normal(book_data, config)
```

### Parallel Processing

```python
# Process multiple books in parallel
from concurrent.futures import ProcessPoolExecutor, as_completed

def parallel_process(book_paths: list, config: dict, workers: int = 4):
    results = []
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_book_task, path, config): path 
            for path in book_paths
        }
        
        for future in as_completed(futures):
            book_path = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({'error': str(e), 'path': book_path})
    
    return results
```

## Database Storage

```python
# storage/database.py
import sqlite3
from datetime import datetime

class BookDatabase:
    def __init__(self, db_path: str = 'data/books.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS books
                     (id TEXT PRIMARY KEY,
                      title TEXT,
                      author TEXT,
                      path TEXT,
                      format TEXT,
                      status TEXT,
                      processed_at TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS summaries
                     (book_id TEXT,
                      summary TEXT,
                      word_count INTEGER,
                      created_at TEXT)''')
        
        conn.commit()
        conn.close()
    
    def add_book(self, book: dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('INSERT INTO books VALUES (?,?,?,?,?,?,?)',
                  (book['id'], book['title'], book['author'],
                   book['path'], book['format'], 'pending', None))
        
        conn.commit()
        conn.close()
    
    def update_status(self, book_id: str, status: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('UPDATE books SET status=?, processed_at=? WHERE id=?',
                  (status, datetime.now().isoformat(), book_id))
        
        conn.commit()
        conn.close()
```

## API Server

```python
# api/server.py
from flask import Flask, request, jsonify
from tasks.processing import process_book_task, scan_library_task

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/scan', methods=['POST'])
def scan():
    data = request.json
    library_path = data.get('path')
    
    result = scan_library_task.delay(library_path, config)
    
    return jsonify({'task_id': result.id, 'status': 'queued'})

@app.route('/api/process', methods=['POST'])
def process():
    data = request.json
    book_path = data.get('path')
    
    result = process_book_task.delay(book_path, config)
    
    return jsonify({'task_id': result.id, 'status': 'queued'})

@app.route('/api/status/<task_id>')
def status(task_id):
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    
    return jsonify({
        'status': result.status,
        'result': result.result if result.ready() else None
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Monitoring

```bash
# Monitor Celery
celery -A tasks.celery_app inspect active
celery -A tasks.celery_app inspect stats

# Monitor system
htop
nvtop
```

## Processing Stats

| Metric | Value |
|--------|-------|
| Books/Day | ~500 |
| Avg Time/Book | 5-10 min |
| Memory/Worker | 8GB |
| GPU Memory | 16GB |
| Storage/Book | ~50KB |

## Commands

```bash
# Start workers
celery -A tasks.celery_app worker -Q processing -c 4 &

# Scan library
python -m api.server scan --path /data/ebooks

# Process specific book
python -m api.server process "book title"

# Check status
celery -A tasks.celery_app inspect active
```

## Troubleshooting

```bash
# Check worker logs
journalctl -u ebook-worker -f

# Check queue
celery -A tasks.celery_app inspect active_queues

# Restart workers
sudo systemctl restart ebook-worker
```

This completes Part 28 with all three advanced integration projects!
