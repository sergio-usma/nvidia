# Project 7: Knowledge Base RAG System

A comprehensive guide to building a Retrieval-Augmented Generation (RAG) system that allows you to query your documents using natural language and local AI models.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Project Structure](#project-structure)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Install Ollama Models](#step-3-install-ollama-models)
   - [Step 4: Create RAG Application](#step-4-create-rag-application)
   - [Step 5: Create Web Interface](#step-5-create-web-interface)
   - [Step 6: Run the System](#step-6-run-the-system)
7. [Using the RAG System](#using-the-rag-system)
8. [Advanced Configuration](#advanced-configuration)
9. [Troubleshooting](#troubleshooting)
10. [Next Steps](#next-steps)

---

## Overview

This project creates a complete RAG system:

- **Document Ingestion**: Load PDF, TXT, Markdown, DOCX files
- **Semantic Search**: Find relevant content using embeddings
- **Question Answering**: Ask questions and get AI answers
- **Web Interface**: Easy-to-use browser interface
- **Local Processing**: Everything runs on your Jetson

### Why RAG?

| Traditional QA | RAG System |
|---------------|------------|
| Limited to training data | Uses your own documents |
| May hallucinate | Grounded in source material |
| No source attribution | Provides citations |
| Static knowledge | Dynamic, updateable |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAG System Architecture                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Documents   │───▶│   Loader     │───▶│   Splitter   │               │
│  │ (PDF/TXT)   │    │  (LangChain) │    │   (Chunks)   │               │
│  └──────────────┘    └──────────────┘    └──────┬───────┘               │
│                                                   │                        │
│                                                   ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │    User      │───▶│   Retrieval  │◀───│  Embeddings  │               │
│  │   Question   │    │   (Chroma)   │    │  (Ollama)    │               │
│  └──────────────┘    └──────┬───────┘    └──────────────┘               │
│                             │                                            │
│                             ▼                                            │
│                      ┌──────────────┐    ┌──────────────┐               │
│                      │    Prompt    │───▶│     LLM       │               │
│                      │  Template    │    │   (Ollama)   │               │
│                      └──────────────┘    └──────┬───────┘               │
│                                                   │                        │
│                                                   ▼                        │
│                                              ┌──────────────┐             │
│                                              │   Answer     │             │
│                                              │ + Sources    │             │
│                                              └──────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation Guide |
|-----------|-------------------|
| Ollama | [Part 5: Ollama Setup](../part-5-llms/01-ollama-setup.md) |
| Python | [Part 3: Python Setup](../part-3-python-environment/01-python-setup.md) |
| Docker | [Part 2: Docker Basics](../part-2-docker/01-docker-basics.md) |

### Pre-Installation Verification

```bash
# Verify Python
python3 --version

# Verify pip
pip3 --version

# Verify Ollama
ollama --version
ollama list
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Multi-format Support | PDF, TXT, MD, DOCX |
| Semantic Search | Find relevant passages |
| Question Answering | Natural language queries |
| Source Citations | Show which documents |
| Web UI | Browser interface |
| Document Upload | Add new documents |

---

## Project Structure

```
~/ai-projects/rag-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Dependencies
├── documents/             # Source documents
│   └── (your .txt, .pdf, .md files)
├── uploads/               # Uploaded documents
├── templates/
│   └── index.html        # Web interface
├── chroma_db/            # Vector database
└── logs/                 # Application logs
```

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Create virtual environment
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install RAG dependencies
pip install flask requests \
    langchain langchain-community langchain-ollama \
    pypdf python-docx \
    sentence-transformers chromadb \
    flask-cors
```

### Step 2: Create Project Directory

```bash
# Create project directory
mkdir -p ~/ai-projects/rag-system
cd ~/ai-projects/rag-system

# Create subdirectories
mkdir -p documents uploads templates chroma_db logs
```

### Step 3: Install Ollama Models

```bash
# Pull embedding model (required for RAG)
ollama pull nomic-embed-text

# Pull chat model
ollama pull llama3.2

# Verify models
ollama list
```

### Step 4: Create RAG Application

Create `app.py`:

```python
#!/usr/bin/env python3
"""
Knowledge Base RAG System

A Retrieval-Augmented Generation system that allows you to
query your documents using natural language and local AI.

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import os
import glob
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, MarkdownLoader, 
    Docx2txtLoader, DirectoryLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# ============================================================================
# CONFIGURATION
# ============================================================================

# Flask configuration
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'documents')
UPLOAD_DIR = os.path.join(BASE_DIR, app.config['UPLOAD_FOLDER'])
CHROMA_DIR = os.path.join(BASE_DIR, 'chroma_db')

# Ensure directories exist
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

# RAG Configuration
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'nomic-embed-text')
LLM_MODEL = os.environ.get('LLM_MODEL', 'llama3.2')
COLLECTION_NAME = 'knowledge-base'

# Text splitting configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# ============================================================================
# GLOBAL STATE
# ============================================================================

vectorstore = None
llm = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_supported_extensions():
    """Get list of supported file extensions."""
    return ['.txt', '.pdf', '.md', '.docx']


def load_document(file_path):
    """
    Load a document based on its file type.
    
    Args:
        file_path: Path to the document
    
    Returns:
        list: List of Document objects
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    loaders = {
        '.txt': TextLoader,
        '.md': TextLoader,
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader
    }
    
    if ext not in loaders:
        print(f"Unsupported file type: {ext}")
        return []
    
    try:
        loader = loaders[ext](file_path)
        return loader.load()
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []


def load_documents_from_directory(directory):
    """
    Load all supported documents from a directory.
    
    Args:
        directory: Path to directory
    
    Returns:
        list: List of Document objects
    """
    documents = []
    supported = get_supported_extensions()
    
    for ext in supported:
        pattern = os.path.join(directory, f'*{ext}')
        files = glob.glob(pattern)
        
        for file_path in files:
            print(f"Loading: {file_path}")
            docs = load_document(file_path)
            documents.extend(docs)
    
    return documents


def split_documents(documents):
    """
    Split documents into chunks for embedding.
    
    Args:
        documents: List of Document objects
    
    Returns:
        list: List of chunked Document objects
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True
    )
    
    return text_splitter.split_documents(documents)


def initialize_vectorstore():
    """
    Initialize the vector store with embeddings.
    
    Returns:
        Chroma: Initialized vector store
    """
    global vectorstore
    
    # Initialize embeddings
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url='http://localhost:11434'
    )
    
    # Check if existing database
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        print("Loading existing vector database...")
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )
    else:
        print("Creating new vector database...")
        # Load and process documents
        documents = load_documents_from_directory(DOCS_DIR)
        
        if documents:
            chunks = split_documents(documents)
            print(f"Creating embeddings for {len(chunks)} chunks...")
            
            vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=CHROMA_DIR,
                collection_name=COLLECTION_NAME
            )
        else:
            # Create empty vectorstore
            vectorstore = Chroma(
                embedding_function=embeddings,
                persist_directory=CHROMA_DIR,
                collection_name=COLLECTION_NAME
            )
    
    return vectorstore


def initialize_llm():
    """
    Initialize the LLM.
    
    Returns:
        OllamaLLM: Initialized LLM
    """
    global llm
    
    llm = OllamaLLM(
        model=LLM_MODEL,
        base_url='http://localhost:11434',
        temperature=0.3
    )
    
    return llm


def get_retriever(search_kwargs=None):
    """
    Get a retriever from the vector store.
    
    Args:
        search_kwargs: Search parameters
    
    Returns:
        Retriever object
    """
    if vectorstore is None:
        initialize_vectorstore()
    
    if search_kwargs is None:
        search_kwargs = {"k": 5}
    
    return vectorstore.as_retriever(
        search_kwargs=search_kwargs
    )


def create_qa_chain():
    """
    Create a question-answering chain.
    
    Returns:
        chain: Configured chain
    """
    if llm is None:
        initialize_llm()
    
    # Create prompt template
    template = """You are a helpful AI assistant that answers questions based on the provided context.

Context from documents:
{context}

Question: {question}

Instructions:
- Answer based only on the provided context
- If the answer is not in the context, say so
- Provide specific references when possible
- Be clear and concise

Answer:"""

    prompt = PromptTemplate(
        template=template,
        input_variables=['context', 'question']
    )
    
    # Create chain
    from langchain.chains import RetrievalQA
    
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=get_retriever(),
        chain_type_kwargs={'prompt': prompt},
        return_source_documents=True
    )
    
    return chain


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all documents in the knowledge base."""
    supported = get_supported_extensions()
    documents = []
    
    for ext in supported:
        pattern = os.path.join(DOCS_DIR, f'*{ext}')
        files = glob.glob(pattern)
        for f in files:
            documents.append({
                'name': os.path.basename(f),
                'path': f,
                'size': os.path.getsize(f),
                'modified': datetime.fromtimestamp(
                    os.path.getmtime(f)
                ).isoformat()
            })
    
    return jsonify({
        'documents': documents,
        'total': len(documents)
    })


@app.route('/api/documents', methods=['POST'])
def upload_document():
    """Upload a new document."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    file_path = os.path.join(DOCS_DIR, filename)
    file.save(file_path)
    
    # Re-initialize vectorstore with new document
    global vectorstore
    vectorstore = None
    initialize_vectorstore()
    
    return jsonify({
        'success': True,
        'filename': filename,
        'message': 'Document uploaded and indexed'
    })


@app.route('/api/documents/refresh', methods=['POST'])
def refresh_documents():
    """Refresh the document index."""
    global vectorstore
    vectorstore = None
    initialize_vectorstore()
    
    return jsonify({
        'success': True,
        'message': 'Documents refreshed'
    })


@app.route('/api/query', methods=['POST'])
def query():
    """Query the knowledge base."""
    data = request.get_json()
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Initialize if needed
        if vectorstore is None:
            initialize_vectorstore()
        if llm is None:
            initialize_llm()
        
        # Create and run chain
        chain = create_qa_chain()
        result = chain.invoke(question)
        
        # Format sources
        sources = []
        if 'source_documents' in result:
            for doc in result['source_documents']:
                sources.append({
                    'content': doc.page_content[:200] + '...',
                    'source': os.path.basename(doc.metadata.get('source', 'unknown'))
                })
        
        return jsonify({
            'success': True,
            'answer': result['result'],
            'sources': sources
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def stats():
    """Get statistics about the knowledge base."""
    if vectorstore is None:
        initialize_vectorstore()
    
    try:
        count = vectorstore._collection.count()
    except:
        count = 0
    
    return jsonify({
        'document_count': count,
        'collection_name': COLLECTION_NAME,
        'embedding_model': EMBEDDING_MODEL,
        'llm_model': LLM_MODEL
    })


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("="*60)
    print("Knowledge Base RAG System")
    print("="*60)
    
    # Initialize
    print("\nInitializing vector store...")
    initialize_vectorstore()
    
    print("\nInitializing LLM...")
    initialize_llm()
    
    print("\n" + "="*60)
    print("RAG System Ready!")
    print("="*60)
    print(f"Documents directory: {DOCS_DIR}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"LLM model: {LLM_MODEL}")
    print("="*60)
    
    # Run app
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### Step 5: Create Web Interface

Create `templates/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Base RAG</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; color: #e8e8e8;
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #e94560; margin-bottom: 20px; }
        .card {
            background: #16213e; border-radius: 12px; padding: 20px;
            margin-bottom: 20px; border: 1px solid #2a2a4a;
        }
        .query-area { display: flex; gap: 10px; margin-bottom: 20px; }
        input, button, textarea {
            padding: 12px; border-radius: 8px; border: 1px solid #2a2a4a;
            background: #0f3460; color: #e8e8e8; font-size: 16px;
        }
        input, textarea { flex: 1; }
        button {
            background: #e94560; color: white; border: none; cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #d13652; }
        button:disabled { background: #666; cursor: not-allowed; }
        .sources { margin-top: 20px; }
        .source {
            background: #0f3460; padding: 12px; margin-bottom: 8px;
            border-radius: 8px; font-size: 14px;
        }
        .source-name { color: #e94560; font-weight: bold; font-size: 12px; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat { background: #0f3460; padding: 10px 20px; border-radius: 8px; }
        .stat-label { font-size: 12px; color: #a0a0a0; }
        .stat-value { font-size: 20px; font-weight: bold; }
        #loading { display: none; color: #a0a0a0; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Knowledge Base RAG</h1>
        
        <div class="stats" id="stats">
            <div class="stat">
                <div class="stat-label">Indexed Chunks</div>
                <div class="stat-value" id="chunk-count">-</div>
            </div>
            <div class="stat">
                <div class="stat-label">Embedding Model</div>
                <div class="stat-value" style="font-size: 14px;" id="embed-model">-</div>
            </div>
        </div>
        
        <div class="card">
            <h3>Ask a Question</h3>
            <div class="query-area">
                <textarea id="question" rows="2" placeholder="What would you like to know?"></textarea>
                <button onclick="ask()" id="ask-btn">Ask</button>
            </div>
            <div id="loading">Processing...</div>
        </div>
        
        <div class="card" id="answer-card" style="display: none;">
            <h3>Answer</h3>
            <div id="answer"></div>
        </div>
        
        <div class="card" id="sources-card" style="display: none;">
            <h3>Sources</h3>
            <div class="sources" id="sources"></div>
        </div>
        
        <div class="card">
            <h3>Upload Documents</h3>
            <div class="query-area">
                <input type="file" id="file-input" accept=".txt,.pdf,.md,.docx">
                <button onclick="upload()">Upload</button>
            </div>
            <div id="upload-status"></div>
        </div>
        
        <div class="card">
            <h3>Documents</h3>
            <div id="documents"></div>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('chunk-count').textContent = data.document_count;
            document.getElementById('embed-model').textContent = data.embedding_model;
        }
        
        async function loadDocuments() {
            const res = await fetch('/api/documents');
            const data = await res.json();
            const container = document.getElementById('documents');
            if (data.total === 0) {
                container.innerHTML = '<p>No documents loaded. Upload some files!</p>';
            } else {
                container.innerHTML = data.documents.map(d => 
                    `<div>${d.name} (${Math.round(d.size/1024)}KB)</div>`
                ).join('');
            }
        }
        
        async function ask() {
            const question = document.getElementById('question').value.trim();
            if (!question) return;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('ask-btn').disabled = true;
            
            try {
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question})
                });
                const data = await res.json();
                
                if (data.success) {
                    document.getElementById('answer').textContent = data.answer;
                    document.getElementById('answer-card').style.display = 'block';
                    
                    document.getElementById('sources').innerHTML = data.sources.map(s => 
                        `<div class="source"><div class="source-name">${s.source}</div>${s.content}</div>`
                    ).join('');
                    document.getElementById('sources-card').style.display = 'block';
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Error: ' + e);
            }
            
            document.getElementById('loading').style.display = 'none';
            document.getElementById('ask-btn').disabled = false;
        }
        
        async function upload() {
            const file = document.getElementById('file-input').files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            document.getElementById('upload-status').textContent = 'Uploading...';
            
            const res = await fetch('/api/documents', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.success) {
                document.getElementById('upload-status').textContent = 'Uploaded!';
                loadDocuments();
                loadStats();
            } else {
                document.getElementById('upload-status').textContent = 'Error: ' + data.error;
            }
        }
        
        loadStats();
        loadDocuments();
    </script>
</body>
</html>
```

### Step 6: Run the System

```bash
# Activate virtual environment
cd ~/ai-projects/rag-system
source venv/bin/activate

# Run the application
python3 app.py
```

### Access the RAG System

Open `http://localhost:5000` in your browser.

---

## Using the RAG System

### Adding Documents

1. Place documents in the `documents/` folder
2. Supported formats: `.txt`, `.pdf`, `.md`, `.docx`
3. The system will automatically index them

### Asking Questions

1. Type your question in the text box
2. Click "Ask" or press Enter
3. View the answer and sources

### Example Questions

- "What is this document about?"
- "Summarize the key points"
- "Find information about [topic]"

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No embeddings found" | Run `ollama pull nomic-embed-text` |
| "Model not found" | Run `ollama pull llama3.2` |
| Empty results | Add documents to `documents/` folder |
| Slow queries | Use smaller chunk size |

---

## Next Steps

| Enhancement | Description |
|-------------|-------------|
| [Super RAG](../part-12-hands-on/01-super-rag.md) | Advanced RAG features |
| [Production API Server](08-ai-api-server.md) | REST API deployment |

---

## License

MIT License
