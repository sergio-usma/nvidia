# EPUB Processor

Process and extract content from EPUB, PDF, and other ebook formats.

## Book Scanner

```python
# processor/scanner.py
import os
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class BookScanner:
    """Scan directories for ebook files"""
    
    SUPPORTED_FORMATS = {
        '.epub': 'epub',
        '.pdf': 'pdf',
        '.mobi': 'mobi',
        '.azw3': 'azw3',
        '.txt': 'txt'
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.exclude_dirs = config.get('exclude_dirs', ['.git', '__pycache__', 'node_modules'])
    
    def scan_directory(self, path: str, recursive: bool = True) -> List[Dict]:
        """Scan directory for ebook files"""
        books = []
        path_obj = Path(path)
        
        if not path_obj.exists():
            logger.error(f"Path does not exist: {path}")
            return []
        
        if path_obj.is_file():
            book = self._process_file(path_obj)
            if book:
                books.append(book)
        else:
            books = self._scan_recursive(path_obj) if recursive else self._scan_single(path_obj)
        
        logger.info(f"Found {len(books)} books in {path}")
        return books
    
    def _scan_recursive(self, directory: Path) -> List[Dict]:
        """Recursively scan directory"""
        books = []
        
        for item in directory.iterdir():
            if item.is_dir():
                if item.name not in self.exclude_dirs:
                    books.extend(self._scan_recursive(item))
            elif item.is_file():
                book = self._process_file(item)
                if book:
                    books.append(book)
        
        return books
    
    def _scan_single(self, directory: Path) -> List[Dict]:
        """Scan single directory (non-recursive)"""
        books = []
        
        for item in directory.iterdir():
            if item.is_file():
                book = self._process_file(item)
                if book:
                    books.append(book)
        
        return books
    
    def _process_file(self, file_path: Path) -> Optional[Dict]:
        """Process single file"""
        ext = file_path.suffix.lower()
        
        if ext not in self.SUPPORTED_FORMATS:
            return None
        
        try:
            stat = file_path.stat()
            
            return {
                'id': self._generate_id(file_path),
                'path': str(file_path.absolute()),
                'filename': file_path.name,
                'title': file_path.stem,
                'format': self.SUPPORTED_FORMATS[ext],
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'scanned_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None
    
    def _generate_id(self, file_path: Path) -> str:
        """Generate unique ID for book"""
        import hashlib
        return hashlib.md5(str(file_path).encode()).hexdigest()[:12]
```

## EPUB Parser

```python
# processor/epub_parser.py
import logging
from typing import Dict, List, Optional
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class EPUBParser:
    """Parse EPUB files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, file_path: str) -> Optional[Dict]:
        """Parse EPUB and extract content"""
        
        try:
            book = epub.read_epub(file_path)
            
            # Extract metadata
            metadata = self._extract_metadata(book)
            
            # Extract chapters
            chapters = self._extract_chapters(book)
            
            # Extract full text
            full_text = self._extract_full_text(chapters)
            
            # Estimate page count
            page_count = self._estimate_pages(full_text)
            
            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'language': metadata.get('language', 'en'),
                'publisher': metadata.get('publisher', ''),
                'description': metadata.get('description', ''),
                'chapters': chapters,
                'full_text': full_text,
                'word_count': len(full_text.split()),
                'page_count': page_count,
                'chapter_count': len(chapters)
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing EPUB {file_path}: {e}")
            return None
    
    def _extract_metadata(self, book) -> Dict:
        """Extract book metadata"""
        metadata = {}
        
        # Get title
        title = book.get_metadata('DC', 'title')
        if title:
            metadata['title'] = title[0][0] if title else ''
        
        # Get author
        creator = book.get_metadata('DC', 'creator')
        if creator:
            metadata['author'] = creator[0][0] if creator else ''
        
        # Get description
        desc = book.get_metadata('DC', 'description')
        if desc:
            metadata['description'] = desc[0][0] if desc else ''
        
        # Get language
        lang = book.get_metadata('DC', 'language')
        if lang:
            metadata['language'] = lang[0][0] if lang else 'en'
        
        # Get publisher
        pub = book.get_metadata('DC', 'publisher')
        if pub:
            metadata['publisher'] = pub[0][0] if pub else ''
        
        return metadata
    
    def _extract_chapters(self, book) -> List[Dict]:
        """Extract chapters from book"""
        chapters = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Parse HTML
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                
                # Get title
                title = soup.find('h1') or soup.find('h2') or soup.find('title')
                title_text = title.get_text(strip=True) if title else f"Chapter {len(chapters) + 1}"
                
                # Get text
                text = soup.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)  # Clean whitespace
                
                if len(text) > 100:  # Skip very short chapters
                    chapters.append({
                        'title': title_text,
                        'text': text,
                        'word_count': len(text.split())
                    })
        
        return chapters
    
    def _extract_full_text(self, chapters: List[Dict]) -> str:
        """Combine all chapter text"""
        return ' '.join([ch['text'] for ch in chapters])
    
    def _estimate_pages(self, text: str) -> int:
        """Estimate page count (250 words/page)"""
        words = len(text.split())
        return max(1, round(words / 250))
```

## PDF Parser

```python
# processor/pdf_parser.py
import logging
from typing import Dict, List, Optional
from pypdf import PdfReader
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFParser:
    """Parse PDF files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, file_path: str) -> Optional[Dict]:
        """Parse PDF and extract content"""
        
        try:
            reader = PdfReader(file_path)
            
            # Extract metadata
            metadata = self._extract_metadata(reader)
            
            # Extract pages
            pages = self._extract_pages(reader)
            
            # Extract full text
            full_text = '\n\n'.join([p['text'] for p in pages])
            
            # Estimate page count
            page_count = len(reader.pages)
            
            return {
                'title': metadata.get('title', Path(file_path).stem),
                'author': metadata.get('author', ''),
                'language': 'en',
                'publisher': metadata.get('publisher', ''),
                'description': '',
                'pages': pages,
                'full_text': full_text,
                'word_count': len(full_text.split()),
                'page_count': page_count,
                'chapter_count': 1  # PDFs often don't have clear chapters
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing PDF {file_path}: {e}")
            return None
    
    def _extract_metadata(self, reader) -> Dict:
        """Extract PDF metadata"""
        metadata = {}
        
        if reader.metadata:
            metadata['title'] = reader.metadata.get('/Title', '')
            metadata['author'] = reader.metadata.get('/Author', '')
            metadata['publisher'] = reader.metadata.get('/Producer', '')
        
        return metadata
    
    def _extract_pages(self, reader) -> List[Dict]:
        """Extract text from pages"""
        pages = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            
            if text and len(text.strip()) > 50:
                pages.append({
                    'page_number': i + 1,
                    'text': text,
                    'word_count': len(text.split())
                })
        
        return pages
```

## Text Splitter

```python
# processor/text_splitter.py
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class TextSplitter:
    """Split text into chunks for processing"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.chunk_size = config.get('chunk_size', 5000)
        self.chunk_overlap = config.get('chunk_overlap', 500)
    
    def split_text(self, text: str) -> List[Dict]:
        """Split text into chunks"""
        chunks = []
        
        # Simple word-based splitting
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append({
                'text': chunk_text,
                'word_count': len(chunk_words),
                'start_index': i,
                'end_index': i + len(chunk_words)
            })
        
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def split_by_chapters(self, chapters: List[Dict]) -> List[Dict]:
        """Split by chapters, then by size"""
        all_chunks = []
        
        for i, chapter in enumerate(chapters):
            chapter_chunks = self.split_text(chapter['text'])
            
            for chunk in chapter_chunks:
                all_chunks.append({
                    'chapter_index': i,
                    'chapter_title': chapter.get('title', f'Chapter {i+1}'),
                    'text': chunk['text'],
                    'word_count': chunk['word_count']
                })
        
        return all_chunks
```

## Usage

```python
# Process an ebook
from processor.scanner import BookScanner
from processor.epub_parser import EPUBParser
from processor.pdf_parser import PDFParser
from processor.text_splitter import TextSplitter
import json

# Scan directory
scanner = BookScanner(config)
books = scanner.scan_directory('/data/ebooks')

# Parse first book
book = books[0]

if book['format'] == 'epub':
    parser = EPUBParser()
elif book['format'] == 'pdf':
    parser = PDFParser()

parsed = parser.parse(book['path'])

# Split into chunks
splitter = TextSplitter(config)
chunks = splitter.split_by_chapters(parsed.get('chapters', [{'text': parsed['full_text']}]))

print(f"Book: {parsed['title']}")
print(f"Author: {parsed['author']}")
print(f"Pages: {parsed['page_count']}")
print(f"Words: {parsed['word_count']}")
print(f"Chunks: {len(chunks)}")
```

## Next Steps

- [Multi-Agent System](./13-multi-agent-system.md) - Agent architecture
