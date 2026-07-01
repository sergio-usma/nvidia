# Funding Finder - Document Processing & RAG

## Overview

This system downloads all public documents from funding opportunities, processes them into a RAG knowledge base, and enables AI agents to answer questions about requirements.

## Document Download System

### Downloader Implementation

```python
#!/usr/bin/env python3
"""
Document Downloader for Funding Opportunities
Downloads PDFs, DOCX, XLSX from funding sites
"""

import os
import sys
import json
import logging
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/funding-finder/logs/downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_base": "/opt/funding-finder/data/documents",
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "concurrent": 3,
    "retry": 3
}

DOCUMENT_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".zip": "application/zip"
}


class DocumentDownloader:
    """Downloads documents from funding opportunity pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def create_folder(self, opportunity_id: str, title: str) -> Path:
        """Create organized folder structure"""
        # Clean title for folder name
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " -_").strip()
        safe_title = safe_title.replace(" ", "_")
        
        folder = Path(CONFIG["output_base"]) / opportunity_id / safe_title
        folder.mkdir(parents=True, exist_ok=True)
        
        return folder
    
    def find_document_links(self, url: str) -> List[Dict]:
        """Find all document links on a page"""
        links = []
        
        try:
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find all links with document extensions
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                text = a.get_text(strip=True).lower()
                
                # Check if it's a document
                ext = None
                for extension in DOCUMENT_EXTENSIONS:
                    if extension in href.lower() or extension in text:
                        ext = extension
                        break
                
                if ext:
                    # Resolve relative URLs
                    if not href.startswith('http'):
                        from urllib.parse import urljoin
                        href = urljoin(url, href)
                    
                    links.append({
                        'url': href,
                        'filename': self.extract_filename(href, text),
                        'type': ext[1:]  # Remove dot
                    })
            
            logger.info(f"Found {len(links)} document links on {url}")
            
        except Exception as e:
            logger.error(f"Error finding links on {url}: {e}")
        
        return links
    
    def extract_filename(self, url: str, fallback: str) -> str:
        """Extract or generate filename from URL"""
        from urllib.parse import urlparse, parse_qs
        
        # Try to get filename from URL path
        path = urlparse(url).path
        if path and '/' in path:
            filename = path.split('/')[-1]
            if filename and '.' in filename:
                return filename
        
        # Generate from query params
        params = parse_qs(urlparse(url).query)
        if 'file' in params:
            return params['file'][0]
        
        # Use fallback
        return f"document_{hashlib.md5(url.encode()).hexdigest()[:8]}"
    
    async def download_file(self, url: str, folder: Path, max_retries: int = 3) -> Optional[Path]:
        """Download a single file"""
        filename = self.extract_filename(url, "document")
        
        # Ensure unique filename
        file_path = folder / filename
        counter = 1
        while file_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            file_path = folder / f"{stem}_{counter}{suffix}"
            counter += 1
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=60, stream=True)
                response.raise_for_status()
                
                # Check size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > CONFIG["max_file_size"]:
                    logger.warning(f"File too large: {url}")
                    return None
                
                # Download
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Downloaded: {file_path.name}")
                return file_path
                
            except Exception as e:
                logger.warning(f"Download attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to download {url}: {e}")
                    return None
        
        return None
    
    async def download_opportunity_documents(self, opportunity: Dict) -> Dict:
        """Download all documents for an opportunity"""
        opportunity_id = opportunity.get("id", "unknown")
        title = opportunity.get("title", "opportunity")
        url = opportunity.get("url", "")
        
        folder = self.create_folder(opportunity_id, title)
        
        # Find document links
        links = self.find_document_links(url)
        
        downloaded = []
        
        # Download in parallel
        import asyncio
        tasks = [
            self.download_file(link['url'], folder)
            for link in links
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for link, result in zip(links, results):
            if isinstance(result, Path):
                downloaded.append({
                    'filename': result.name,
                    'type': link['type'],
                    'path': str(result),
                    'size': result.stat().st_size
                })
        
        return {
            "opportunity_id": opportunity_id,
            "folder": str(folder),
            "documents": downloaded,
            "total": len(downloaded)
        }


class DocumentProcessor:
    """Processes downloaded documents for RAG"""
    
    def __init__(self):
        self.output_dir = Path(CONFIG["output_base"])
        
    def extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF"""
        try:
            reader = PdfReader(str(file_path))
            text = ""
            
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"PDF extraction error for {file_path}: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        try:
            doc = Document(str(file_path))
            text = "\n".join([p.text for p in doc.paragraphs])
            return text
            
        except Exception as e:
            logger.error(f"DOCX extraction error for {file_path}: {e}")
            return ""
    
    def extract_text_from_xlsx(self, file_path: Path) -> str:
        """Extract text from XLSX"""
        try:
            df = pd.read_excel(file_path, sheet_name=None)
            text = ""
            
            for sheet_name, sheet_df in df.items():
                text += f"\n=== Sheet: {sheet_name} ===\n"
                text += sheet_df.to_string() + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"XLSX extraction error for {file_path}: {e}")
            return ""
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text based on file type"""
        ext = file_path.suffix.lower()
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext in ['.doc', '.docx']:
            return self.extract_text_from_docx(file_path)
        elif ext in ['.xls', '.xlsx']:
            return self.extract_text_from_xlsx(file_path)
        elif ext == '.txt':
            return file_path.read_text(errors='ignore')
        elif ext == '.csv':
            df = pd.read_csv(file_path)
            return df.to_string()
        
        return ""
    
    def process_opportunity(self, opportunity_id: str) -> Dict:
        """Process all documents for an opportunity"""
        opp_dir = self.output_dir / opportunity_id
        
        if not opp_dir.exists():
            return {"error": "Opportunity folder not found"}
        
        documents = []
        
        for subdir in opp_dir.iterdir():
            if subdir.is_dir():
                for file_path in subdir.rglob("*"):
                    if file_path.is_file():
                        try:
                            text = self.extract_text(file_path)
                            
                            documents.append({
                                "filename": file_path.name,
                                "path": str(file_path),
                                "text": text,
                                "chars": len(text)
                            })
                            
                        except Exception as e:
                            logger.error(f"Error processing {file_path}: {e}")
        
        return {
            "opportunity_id": opportunity_id,
            "documents": documents,
            "total_documents": len(documents),
            "total_chars": sum(d["chars"] for d in documents)
        }
```

## RAG System

### ChromaDB Integration

```python
#!/usr/bin/env python3
"""
RAG Knowledge Base for Funding Finder
Uses ChromaDB for document retrieval
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/funding-finder/logs/rag.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "chroma_dir": "/opt/funding-finder/data/chroma",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "collection_name": "funding_documents"
}


class RAGSystem:
    """Retrieval-Augmented Generation for funding documents"""
    
    def __init__(self):
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=CONFIG["chroma_dir"],
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=CONFIG["collection_name"],
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize embedding model
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer(CONFIG["embedding_model"])
        
        logger.info("RAG system initialized")
    
    def add_documents(self, opportunity_id: str, documents: List[Dict]):
        """Add documents to the knowledge base"""
        
        texts = []
        ids = []
        metadatas = []
        
        for doc in documents:
            text = doc.get("text", "")
            if not text or len(text) < 50:  # Skip very short texts
                continue
            
            # Chunk text (simple approach - 1000 chars with overlap)
            chunks = self.chunk_text(text, chunk_size=1000, overlap=100)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{opportunity_id}_{doc['filename']}_{i}"
                
                texts.append(chunk)
                ids.append(chunk_id)
                metadatas.append({
                    "opportunity_id": opportunity_id,
                    "filename": doc["filename"],
                    "source": "document"
                })
        
        if texts:
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Add to ChromaDB
            self.collection.add(
                documents=texts,
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(texts)} chunks for {opportunity_id}")
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    start = break_point + 1
                else:
                    start = end - overlap
            else:
                start = end
            
            chunks.append(chunk.strip())
        
        return chunks
    
    def search(self, query: str, opportunity_id: str = None, top_k: int = 5) -> List[Dict]:
        """Search for relevant document chunks"""
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Build where clause if filtering by opportunity
        where = None
        if opportunity_id:
            where = {"opportunity_id": opportunity_id}
        
        # Search
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted = []
        for i in range(len(results["documents"][0])):
            formatted.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i]  # Convert distance to similarity
            })
        
        return formatted
    
    def get_context(self, query: str, opportunity_id: str, max_chars: int = 4000) -> str:
        """Get concatenated context for a query"""
        
        # Get more chunks than needed
        chunks = self.search(query, opportunity_id, top_k=10)
        
        context = ""
        for chunk in chunks:
            if len(context) + len(chunk["text"]) > max_chars:
                break
            context += f"\n\n---\n\n{chunk['text']}"
        
        return context
    
    def delete_opportunity(self, opportunity_id: str):
        """Remove opportunity from knowledge base"""
        
        # Get all IDs for this opportunity
        results = self.collection.get(where={"opportunity_id": opportunity_id})
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks for {opportunity_id}")
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        
        return {
            "total_chunks": self.collection.count(),
            "collection_name": CONFIG["collection_name"]
        }
```

## API Integration

```python
# Add to main API
@app.route("/documents/process", methods=["POST"])
def process_documents():
    """Process documents for an opportunity"""
    try:
        data = request.get_json()
        opportunity_id = data.get("opportunity_id")
        
        # Process documents
        processor = DocumentProcessor()
        processed = processor.process_opportunity(opportunity_id)
        
        # Add to RAG
        rag = RAGSystem()
        rag.add_documents(opportunity_id, processed["documents"])
        
        return jsonify({
            "success": True,
            "documents": processed["total_documents"],
            "chars": processed["total_chars"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/rag/query", methods=["POST"])
def query_rag():
    """Query the RAG system"""
    try:
        data = request.get_json()
        query = data.get("query")
        opportunity_id = data.get("opportunity_id")
        
        rag = RAGSystem()
        results = rag.search(query, opportunity_id)
        
        return jsonify({
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## Next Steps

- [05-agents](./05-agents.md) - Multi-agent proposal generation
