# RAG & Duplicate Detection

Generate embeddings and detect duplicates using local AI models.

## Embedding Engine

```python
# rag/embedding_engine.py
import logging
from typing import List, Dict, Optional
import ollama
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """Generate embeddings for files using Ollama"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = config.get('embedding_model', 'nomic-embed-text')
        self.host = config.get('ollama_host', 'http://localhost:11434')
        self.batch_size = config.get('batch_size', 10)
        
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        try:
            response = ollama.embeddings(
                model=self.model,
                prompt=text[:8000]  # Limit text length
            )
            return response.get('embedding')
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            for text in batch:
                try:
                    emb = self.generate_embedding(text)
                    embeddings.append(emb)
                except Exception as e:
                    logger.error(f"Error in batch: {e}")
                    embeddings.append(None)
        
        return embeddings
    
    def generate_file_embedding(self, file_data: Dict) -> Optional[List[float]]:
        """Generate embedding for a file based on its content"""
        # Combine relevant fields for embedding
        content = file_data.get('content', '')
        if not content:
            # Fallback to filename
            content = file_data.get('name', '')
        
        # Truncate to reasonable size
        content = content[:8000]
        
        return self.generate_embedding(content)
    
    def generate_chunk_embeddings(self, text: str, chunk_size: int = 1000) -> List[Dict]:
        """Generate embeddings for text chunks"""
        chunks = []
        
        # Simple chunking
        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            embedding = self.generate_embedding(chunk)
            
            if embedding:
                chunks.append({
                    'text': chunk,
                    'embedding': embedding,
                    'word_count': len(chunk.split())
                })
        
        return chunks
```

## Vector Store (ChromaDB)

```python
# rag/vector_store.py
import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorStore:
    """ChromaDB-based vector store for file embeddings"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.persist_dir = config.get('persist_directory', 'data/embeddings')
        
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = None
        self._init_collection()
    
    def _init_collection(self):
        """Initialize or get collection"""
        try:
            self.collection = self.client.get_or_create_collection(
                name="file_intelligence",
                metadata={"description": "File embeddings for RAG and duplicate detection"}
            )
        except Exception as e:
            logger.error(f"Error initializing collection: {e}")
            raise
    
    def add_embeddings(self, documents: List[Dict]):
        """Add document embeddings to the store"""
        ids = []
        embeddings = []
        metadatas = []
        documents_text = []
        
        for doc in documents:
            if 'embedding' not in doc or doc['embedding'] is None:
                continue
            
            # Generate ID
            doc_id = doc.get('id') or hashlib.md5(
                doc['path'].encode()
            ).hexdigest()
            
            ids.append(doc_id)
            embeddings.append(doc['embedding'])
            metadatas.append({
                'path': doc['path'],
                'name': doc.get('name', ''),
                'size': doc.get('size', 0),
                'modified': doc.get('modified', ''),
                'extension': doc.get('extension', '')
            })
            documents_text.append(doc.get('content', '')[:5000])  # Store truncated content
        
        if ids:
            try:
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents_text
                )
                logger.info(f"Added {len(ids)} documents to vector store")
            except Exception as e:
                logger.error(f"Error adding embeddings: {e}")
    
    def similarity_search(
        self, 
        query_embedding: List[float], 
        n_results: int = 10,
        threshold: float = 0.0
    ) -> List[Dict]:
        """Find similar documents"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            similar_docs = []
            if results['ids'] and len(results['ids']) > 0:
                for i, doc_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    if similarity >= threshold:
                        similar_docs.append({
                            'id': doc_id,
                            'path': results['metadatas'][0][i]['path'],
                            'name': results['metadatas'][0][i]['name'],
                            'similarity': similarity,
                            'distance': distance
                        })
            
            return similar_docs
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    def get_all_documents(self) -> List[Dict]:
        """Get all documents from store"""
        try:
            results = self.collection.get()
            documents = []
            
            for i, doc_id in enumerate(results['ids']):
                documents.append({
                    'id': doc_id,
                    'path': results['metadatas'][i]['path'],
                    'name': results['metadatas'][i]['name'],
                    'embedding': results['embeddings'][i] if 'embeddings' in results else None
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []
    
    def delete_document(self, doc_id: str):
        """Delete a document"""
        try:
            self.collection.delete(ids=[doc_id])
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
    
    def clear(self):
        """Clear all documents"""
        try:
            self.client.delete_collection("file_intelligence")
            self._init_collection()
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
```

## Duplicate Detection

```python
# rag/duplicate_detector.py
import logging
from typing import List, Dict, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class DuplicateDetector:
    """Detect duplicate and similar files"""
    
    def __init__(self, config: Dict, vector_store: 'VectorStore', embedding_engine: 'EmbeddingEngine'):
        self.config = config
        self.vector_store = vector_store
        self.embedding_engine = embedding_engine
        self.similarity_threshold = config.get('similarity_threshold', 0.85)
        self.min_duplicate_size = config.get('min_duplicate_size', 1024)  # 1KB
    
    def find_duplicates(self, files: List[Dict]) -> List[Dict]:
        """Find duplicate files"""
        duplicates = []
        
        # Group by hash for exact duplicates
        hash_groups = {}
        for file_data in files:
            file_hash = file_data.get('hash', '')
            if file_hash:
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(file_data)
        
        # Process exact duplicates
        for file_hash, group in hash_groups.items():
            if len(group) > 1:
                duplicate_group = self._analyze_duplicate_group(group, 'exact')
                duplicates.extend(duplicate_group)
        
        logger.info(f"Found {len(duplicates)} exact duplicates")
        
        # Find similar files using embeddings
        similar = self._find_similar_files(files)
        duplicates.extend(similar)
        
        logger.info(f"Found {len(similar)} similar files")
        
        return duplicates
    
    def _find_similar_files(self, files: List[Dict]) -> List[Dict]:
        """Find similar files using embeddings"""
        similar_files = []
        
        # Process files in batches
        batch_size = self.config.get('batch_size', 10)
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            
            for file_data in batch:
                if not file_data.get('content'):
                    continue
                
                # Skip small files
                if file_data.get('size', 0) < self.min_duplicate_size:
                    continue
                
                # Generate embedding
                embedding = self.embedding_engine.generate_file_embedding(file_data)
                
                if not embedding:
                    continue
                
                # Find similar files
                similar = self.vector_store.similarity_search(
                    embedding,
                    n_results=20,
                    threshold=self.similarity_threshold
                )
                
                # Filter to actual duplicates (different paths)
                file_path = file_data['path']
                similar = [s for s in similar if s['path'] != file_path]
                
                if similar:
                    # Determine which to keep
                    group = [file_data]
                    for s in similar:
                        # Find the original file data
                        orig = next((f for f in files if f['path'] == s['path']), None)
                        if orig:
                            group.append(orig)
                    
                    if len(group) > 1:
                        duplicate_group = self._analyze_duplicate_group(group, 'similar')
                        similar_files.extend(duplicate_group)
        
        return similar_files
    
    def _analyze_duplicate_group(self, group: List[Dict], duplicate_type: str) -> List[Dict]:
        """Analyze a group of duplicate files"""
        if not group:
            return []
        
        # Sort by modification time (newest first)
        sorted_group = sorted(
            group,
            key=lambda x: x.get('modified', ''),
            reverse=True
        )
        
        # The newest file is the keeper
        keeper = sorted_group[0]
        
        duplicates = []
        for i, file_data in enumerate(sorted_group):
            duplicate_info = {
                'type': duplicate_type,
                'group_id': f"{duplicate_type}_{hash(tuple([f['path'] for f in group]))}",
                'path': file_data['path'],
                'name': file_data.get('name', ''),
                'size': file_data.get('size', 0),
                'modified': file_data.get('modified', ''),
                'is_keeper': i == 0,
                'is_recommended_delete': i > 0 and self._should_delete(file_data, keeper),
                'reason': self._get_duplicate_reason(i, keeper, file_data)
            }
            duplicates.append(duplicate_info)
        
        return duplicates
    
    def _should_delete(self, candidate: Dict, keeper: Dict) -> bool:
        """Determine if a candidate should be deleted"""
        # If candidate is newer or same size, don't delete
        if candidate.get('modified', '') >= keeper.get('modified', ''):
            return False
        
        # If candidate is smaller, might want to keep
        if candidate.get('size', 0) < keeper.get('size', 0):
            return False
        
        return True
    
    def _get_duplicate_reason(self, index: int, keeper: Dict, candidate: Dict) -> str:
        """Get reason for duplicate classification"""
        if index == 0:
            return "Newest version - KEEP"
        
        reason = "Older version"
        
        if candidate.get('size', 0) < keeper.get('size', 0):
            reason += " (smaller than keeper)"
        elif candidate.get('size', 0) > keeper.get('size', 0):
            reason += " (larger - possible damage)"
        
        return reason
    
    def generate_duplicate_report(self, duplicates: List[Dict]) -> str:
        """Generate a human-readable duplicate report"""
        report = []
        report.append("# Duplicate Files Report")
        report.append(f"\nGenerated: {datetime.now().isoformat()}")
        report.append(f"\nTotal duplicates: {len(duplicates)}")
        
        # Group by group_id
        groups = {}
        for dup in duplicates:
            gid = dup.get('group_id', 'unknown')
            if gid not in groups:
                groups[gid] = []
            groups[gid].append(dup)
        
        report.append(f"\n## Duplicate Groups: {len(groups)}")
        
        for gid, group in groups.items():
            report.append(f"\n### Group: {gid}")
            
            for dup in sorted(group, key=lambda x: not x.get('is_keeper', False)):
                status = "✓ KEEP" if dup.get('is_keeper') else "✗ DELETE"
                if dup.get('is_recommended_delete'):
                    status += " (recommended)"
                
                report.append(f"\n- {status}")
                report.append(f"  Path: {dup['path']}")
                report.append(f"  Size: {dup['size']} bytes")
                report.append(f"  Modified: {dup['modified']}")
                report.append(f"  Reason: {dup.get('reason', '')}")
        
        return '\n'.join(report)
```

## Usage

```python
# main.py - RAG and duplicate detection
def index_command(args):
    config = load_config()
    
    # Initialize components
    embedding_engine = EmbeddingEngine(config)
    vector_store = VectorStore(config)
    
    # Load scanned files
    with open('data/scan_results.json') as f:
        files = json.load(f)
    
    # Generate embeddings
    print(f"Generating embeddings for {len(files)} files...")
    for i, file_data in enumerate(files):
        embedding = embedding_engine.generate_file_embedding(file_data)
        file_data['embedding'] = embedding
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(files)}")
    
    # Add to vector store
    vector_store.add_embeddings(files)
    
    print("RAG index created successfully")

def duplicates_command(args):
    config = load_config()
    
    embedding_engine = EmbeddingEngine(config)
    vector_store = VectorStore(config)
    detector = DuplicateDetector(config, vector_store, embedding_engine)
    
    # Load scanned files
    with open('data/scan_results.json') as f:
        files = json.load(f)
    
    # Find duplicates
    print("Finding duplicates...")
    duplicates = detector.find_duplicates(files)
    
    # Generate report
    report = detector.generate_duplicate_report(duplicates)
    
    # Save report
    with open('data/duplicates_report.md', 'w') as f:
        f.write(report)
    
    print(f"Found {len(duplicates)} duplicates")
    print("Report saved to data/duplicates_report.md")
```

## Next Steps

- [GraphRAG Implementation](./04-graphrag-implementation.md) - Build knowledge graphs
- [Usage & Commands](./05-usage-commands.md) - Full command reference
