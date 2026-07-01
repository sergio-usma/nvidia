# File Scanning Engine

The core engine for scanning and extracting content from files.

## File Scanner Implementation

```python
# scanner/file_scanner.py
import os
import hashlib
import magic
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class FileScanner:
    """Scans directories and extracts file metadata"""
    
    SUPPORTED_EXTENSIONS = {
        # Documents
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain',
        '.rtf': 'application/rtf',
        # Spreadsheets
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.csv': 'text/csv',
        # Presentations
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        # E-books
        '.epub': 'application/epub+zip',
        '.mobi': 'application/x-mobipocket-ebook',
        '.azw3': 'application/vnd.amazon.ebook',
        # Markdown
        '.md': 'text/markdown',
        '.markdown': 'text/markdown',
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.exclude_dirs = config.get('exclude_paths', '.git,node_modules,__pycache__').split(',')
        self.max_file_size = self._parse_size(config.get('max_file_size', '100MB'))
        self.files_found = []
        
    def _parse_size(self, size_str: str) -> int:
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        size_str = size_str.upper().strip()
        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                return int(size_str[:-len(unit)]) * multiplier
        return int(size_str)
    
    def scan(self, path: str, recursive: bool = True) -> List[Dict]:
        """Scan a directory for supported files"""
        self.files_found = []
        scan_path = Path(path)
        
        if not scan_path.exists():
            logger.error(f"Path does not exist: {path}")
            return []
        
        if scan_path.is_file():
            return [self._process_file(scan_path)]
        
        self._scan_directory(scan_path, recursive)
        logger.info(f"Found {len(self.files_found)} files")
        return self.files_found
    
    def _scan_directory(self, directory: Path, recursive: bool):
        """Recursively scan directory"""
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    if item.name not in self.exclude_dirs and recursive:
                        self._scan_directory(item, recursive)
                elif item.is_file():
                    if self._is_supported(item):
                        file_data = self._process_file(item)
                        if file_data:
                            self.files_found.append(file_data)
        except PermissionError:
            logger.warning(f"Permission denied: {directory}")
    
    def _is_supported(self, file_path: Path) -> bool:
        """Check if file type is supported"""
        ext = file_path.suffix.lower()
        
        # Check by extension
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        
        # Check by MIME type
        try:
            mime = magic.from_file(str(file_path), mime=True)
            return any(mime.startswith(prefix) for prefix in ['text/', 'application/pdf', 'application/epub'])
        except:
            return False
    
    def _process_file(self, file_path: Path) -> Optional[Dict]:
        """Extract metadata from a file"""
        try:
            stat = file_path.stat()
            
            # Skip files that are too large or too small
            if stat.st_size > self.max_file_size:
                logger.debug(f"Skipping large file: {file_path}")
                return None
                
            if stat.st_size < 100:  # Too small to be meaningful
                return None
            
            file_data = {
                'path': str(file_path.absolute()),
                'name': file_path.name,
                'extension': file_path.suffix.lower(),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'mime_type': self._get_mime_type(file_path),
                'hash': self._calculate_hash(file_path),
            }
            
            return file_data
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type of file"""
        try:
            return magic.from_file(str(file_path), mime=True)
        except:
            return self.SUPPORTED_EXTENSIONS.get(file_path.suffix.lower(), 'application/octet-stream')
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash for quick duplicate detection"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                # Read only first and last 64KB for speed
                hasher.update(f.read(65536))
                f.seek(max(0, file_path.stat().st_size - 65536))
                hasher.update(f.read(65536))
            return hasher.hexdigest()
        except:
            return ""
    
    def scan_multiple_paths(self, paths: List[str]) -> List[Dict]:
        """Scan multiple paths"""
        all_files = []
        for path in paths:
            files = self.scan(path)
            all_files.extend(files)
        return all_files
```

## Text Extraction

```python
# scanner/text_extractor.py
import logging
from pathlib import Path
from typing import Optional
import subprocess

logger = logging.getLogger(__name__)

class TextExtractor:
    """Extract text content from various file formats"""
    
    def __init__(self):
        self.extractors = {
            '.pdf': self._extract_pdf,
            '.docx': self._extract_docx,
            '.doc': self._extract_doc,
            '.txt': self._extract_txt,
            '.md': self._extract_txt,
            '.markdown': self._extract_txt,
            '.csv': self._extract_txt,
            '.xlsx': self._extract_xlsx,
            '.xls': self._extract_xls,
            '.pptx': self._extract_pptx,
            '.ppt': self._extract_ppt,
            '.epub': self._extract_epub,
            '.rtf': self._extract_rtf,
        }
    
    def extract(self, file_path: str) -> Optional[str]:
        """Extract text from file"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        extractor = self.extractors.get(ext)
        if not extractor:
            logger.warning(f"No extractor for {ext}")
            return None
        
        try:
            return extractor(path)
        except Exception as e:
            logger.error(f"Error extracting from {file_path}: {e}")
            return None
    
    def _extract_txt(self, path: Path) -> str:
        """Extract plain text"""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            with open(path, 'r', encoding='latin-1', errors='ignore') as f:
                return f.read()
    
    def _extract_pdf(self, path: Path) -> str:
        """Extract text from PDF using pypdf"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""
    
    def _extract_docx(self, path: Path) -> str:
        """Extract text from DOCX"""
        try:
            from docx import Document
            doc = Document(path)
            return "\n".join([para.text for para in doc.paragraphs])
        except:
            return ""
    
    def _extract_doc(self, path: Path) -> str:
        """Extract text from DOC using antiword or tika"""
        try:
            # Try using antiword
            result = subprocess.run(
                ['antiword', str(path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        
        # Fallback: return empty (DOC parsing is complex)
        logger.warning("DOC parsing not available - install antiword")
        return ""
    
    def _extract_xlsx(self, path: Path) -> str:
        """Extract text from XLSX"""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            text = ""
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                for row in ws.iter_rows():
                    for cell in row:
                        if cell.value:
                            text += str(cell.value) + " "
            return text
        except:
            return ""
    
    def _extract_xls(self, path: Path) -> str:
        """Extract text from XLS"""
        try:
            import xlrd
            wb = xlrd.open_workbook(path)
            text = ""
            for sheet in wb.sheets():
                for row in range(sheet.nrows):
                    for cell in sheet.row(row):
                        if cell.value:
                            text += str(cell.value) + " "
            return text
        except:
            return ""
    
    def _extract_pptx(self, path: Path) -> str:
        """Extract text from PPTX"""
        try:
            from pptx import Presentation
            prs = Presentation(path)
            text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
            return text
        except:
            return ""
    
    def _extract_ppt(self, path: Path) -> str:
        """Extract text from PPT"""
        # PPT parsing is complex - requires external tools
        return ""
    
    def _extract_epub(self, path: Path) -> str:
        """Extract text from EPUB"""
        try:
            import epub2
            book = epub2.open_epub(str(path))
            text = ""
            for item in book.spine:
                html = item.read()
                # Simple text extraction from HTML
                import re
                text += re.sub(r'<[^>]+>', '', html.decode('utf-8', errors='ignore'))
            return text
        except:
            # Fallback to simple extraction
            try:
                import zipfile
                text = ""
                with zipfile.ZipFile(path) as z:
                    for name in z.namelist():
                        if name.endswith('.html') or name.endswith('.xhtml'):
                            content = z.read(name).decode('utf-8', errors='ignore')
                            import re
                            text += re.sub(r'<[^>]+>', '', content)
                return text
            except:
                return ""
    
    def _extract_rtf(self, path: Path) -> str:
        """Extract text from RTF"""
        try:
            with open(path, 'r', errors='ignore') as f:
                content = f.read()
            # Remove RTF formatting
            import re
            return re.sub(r'\\[a-z]+\d*\s?', '', content)
        except:
            return ""
```

## Parallel Processing

```python
# scanner/parallel_scanner.py
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class ParallelScanner:
    """Process files in parallel for better performance"""
    
    def __init__(self, scanner: 'FileScanner', extractor: 'TextExtractor', workers: int = 4):
        self.scanner = scanner
        self.extractor = extractor
        self.workers = workers
    
    def scan_with_content(self, paths: List[str]) -> List[Dict]:
        """Scan files and extract content in parallel"""
        # First, get all files
        all_files = []
        for path in paths:
            files = self.scanner.scan(path)
            all_files.extend(files)
        
        logger.info(f"Processing {len(all_files)} files with {self.workers} workers")
        
        # Process files in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_file = {
                executor.submit(self._process_file, f): f 
                for f in all_files
            }
            
            for future in as_completed(future_to_file):
                file_data = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {file_data['path']}: {e}")
        
        return results
    
    def _process_file(self, file_data: Dict) -> Dict:
        """Process single file - extract content"""
        try:
            content = self.extractor.extract(file_data['path'])
            file_data['content'] = content
            file_data['content_length'] = len(content) if content else 0
            file_data['word_count'] = len(content.split()) if content else 0
            return file_data
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return file_data
```

## Usage Example

```python
# main.py (excerpt)
from scanner.file_scanner import FileScanner
from scanner.text_extractor import TextExtractor
from scanner.parallel_scanner import ParallelScanner
import json

def scan_command(args):
    config = load_config()
    
    scanner = FileScanner(config)
    extractor = TextExtractor()
    parallel = ParallelScanner(scanner, extractor, workers=config.get('parallel_workers', 4))
    
    paths = args.path or config.get('scan_paths', ['.']).split(',')
    
    results = parallel.scan_with_content(paths)
    
    # Save results
    output_file = 'data/scan_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Scan complete. Found {len(results)} files.")
    print(f"Results saved to {output_file}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', nargs='+', help='Paths to scan')
    args = parser.parse_args()
    scan_command(args)
```

## Next Steps

- [RAG & Duplicate Detection](./03-rag-duplicate-detection.md) - Generate embeddings and find duplicates
- [GraphRAG Implementation](./04-graphrag-implementation.md) - Build knowledge graphs
