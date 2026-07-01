# Summary Generation

Generate professional summaries in multiple output formats.

## Output Formatter

```python
# formatter/output_formatter.py
from typing import Dict, List
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class OutputFormatter:
    """Format summaries into various output formats"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.output_dir = config.get('summaries_path', 'data/summaries')
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def format_markdown(self, result: Dict) -> str:
        """Format summary as Markdown"""
        
        title = result.get('title', 'Unknown')
        author = result.get('author', 'Unknown')
        summary = result.get('summary', '')
        bullets = result.get('bullets', [])
        extraction = result.get('extraction', {})
        stats = result.get('stats', {})
        
        # Build markdown
        md = []
        
        # Header
        md.append(f"# {title}")
        md.append(f"\n**Author:** {author}")
        md.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d')}*")
        md.append("\n---\n")
        
        # Stats
        md.append(f"**Original Length:** {stats.get('original_words', 0):,} words")
        md.append(f"**Summary Length:** {stats.get('summary_words', 0):,} words")
        md.append(f"**Compression:** {stats.get('compression_ratio', 0)}%")
        md.append("\n---\n")
        
        # Summary
        md.append("## Executive Summary\n")
        md.append(summary)
        md.append("\n---\n")
        
        # Key Takeaways
        md.append("## Key Takeaways\n")
        
        if bullets:
            for bullet in bullets[:30]:
                md.append(f"- {bullet}")
        else:
            md.append("*No bullet points extracted*")
        
        md.append("\n---\n")
        
        # Quotes
        quotes = extraction.get('quotes', [])
        if quotes:
            md.append("## Notable Quotes\n")
            for quote in quotes[:10]:
                md.append(f"> {quote}\n")
            md.append("\n---\n")
        
        # Concepts
        concepts = extraction.get('concepts', [])
        if concepts:
            md.append("## Key Concepts\n")
            for concept in concepts[:15]:
                md.append(f"- **{concept}**")
            md.append("\n---\n")
        
        # Target Audience (from analysis)
        analysis = result.get('analysis', {})
        audience = analysis.get('target_audience', 'General readers')
        md.append(f"## Target Audience\n{audience}\n")
        
        return '\n'.join(md)
    
    def format_pdf(self, result: Dict) -> bytes:
        """Format summary as PDF"""
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            
            # Create buffer
            buffer = []
            
            # Build document
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Title
            title = result.get('title', 'Unknown')
            buffer.append(Paragraph(title, styles['Title']))
            buffer.append(Spacer(1, 0.2*inch))
            
            # Author
            author = result.get('author', 'Unknown')
            buffer.append(Paragraph(f"by {author}", styles['Author']))
            buffer.append(Spacer(1, 0.3*inch))
            
            # Summary
            summary = result.get('summary', '')
            for para in summary.split('\n\n'):
                if para.strip():
                    buffer.append(Paragraph(para, styles['BodyText']))
                    buffer.append(Spacer(1, 0.1*inch))
            
            # Build PDF
            pdf_data = doc.build(buffer)
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return b""
    
    def format_text(self, result: Dict) -> str:
        """Format summary as plain text"""
        
        title = result.get('title', 'Unknown')
        author = result.get('author', 'Unknown')
        summary = result.get('summary', '')
        bullets = result.get('bullets', [])
        
        text = []
        
        text.append("=" * 60)
        text.append(title.upper())
        text.append("=" * 60)
        text.append(f"\nBy: {author}\n")
        text.append(f"Generated: {datetime.now().strftime('%Y-%m-%d')}\n")
        text.append("=" * 60)
        
        # Summary
        text.append("\nEXECUTIVE SUMMARY\n")
        text.append("-" * 40)
        text.append(summary)
        
        # Key Takeaways
        text.append("\n\nKEY TAKEAWAYS\n")
        text.append("-" * 40)
        
        for bullet in bullets[:20]:
            text.append(f"  • {bullet}")
        
        return '\n'.join(text)
    
    def save_output(self, result: Dict, formats: List[str] = None) -> Dict:
        """Save summary in multiple formats"""
        
        if formats is None:
            formats = ['markdown']
        
        title = result.get('title', 'unknown')
        safe_title = ''.join(c for c in title if c.isalnum() or c in ' -').strip()[:50]
        
        saved = {}
        
        for fmt in formats:
            if fmt == 'markdown':
                content = self.format_markdown(result)
                filename = f"{safe_title}.md"
                filepath = Path(self.output_dir) / filename
                
                with open(filepath, 'w') as f:
                    f.write(content)
                
                saved['markdown'] = str(filepath)
                logger.info(f"Saved Markdown: {filepath}")
            
            elif fmt == 'pdf':
                content = self.format_pdf(result)
                if content:
                    filename = f"{safe_title}.pdf"
                    filepath = Path(self.output_dir) / filename
                    
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    saved['pdf'] = str(filepath)
                    logger.info(f"Saved PDF: {filepath}")
            
            elif fmt == 'text':
                content = self.format_text(result)
                filename = f"{safe_title}.txt"
                filepath = Path(self.output_dir) / filename
                
                with open(filepath, 'w') as f:
                    f.write(content)
                
                saved['text'] = str(filepath)
                logger.info(f"Saved Text: {filepath}")
        
        return saved
```

## Audio Generation

```python
# formatter/audio_generator.py
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class AudioGenerator:
    """Generate audio versions of summaries"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def generate_audio(self, result: Dict, output_path: str) -> bool:
        """Generate audio from summary"""
        
        try:
            import pyttsx3
            
            # Initialize TTS engine
            engine = pyttsx3.init()
            
            # Configure
            rate = self.config.get('tts_rate', 150)
            engine.setProperty('rate', rate)
            
            volume = self.config.get('tts_volume', 1.0)
            engine.setProperty('volume', volume)
            
            # Get available voices
            voices = engine.getProperty('voices')
            if voices:
                engine.setProperty('voice', voices[0].id)
            
            # Build text
            title = result.get('title', '')
            summary = result.get('summary', '')
            bullets = result.get('bullets', [])
            
            text = f"{title}. {summary}. "
            text += "Key takeaways: " + ". ".join(bullets[:10])
            
            # Save to file
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            
            logger.info(f"Generated audio: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return False
    
    def generate_with_ollama(self, result: Dict, output_path: str) -> bool:
        """Generate more natural audio using Whisper/TTS"""
        # This would use a TTS model via Ollama
        # For now, return False to use fallback
        return False
```

## Batch Processing

```python
# main.py - Batch processing
from processor.scanner import BookScanner
from processor.epub_parser import EPUBParser
from processor.pdf_parser import PDFParser
from agents.orchestrator import Orchestrator
from formatter.output_formatter import OutputFormatter
import json

def process_book(book_path: str, config: Dict) -> Dict:
    """Process single book"""
    
    # Parse book
    ext = book_path.split('.')[-1].lower()
    
    if ext == 'epub':
        parser = EPUBParser()
    else:
        parser = PDFParser()
    
    book_data = parser.parse(book_path)
    
    if not book_data:
        return {'error': 'Failed to parse book'}
    
    # Process with agents
    orchestrator = Orchestrator(config)
    result = orchestrator.process_book(book_data)
    
    # Format output
    formatter = OutputFormatter(config)
    saved = formatter.save_output(result, ['markdown', 'text'])
    
    result['output_files'] = saved
    
    return result

def batch_process(books_dir: str, config: Dict, limit: int = None):
    """Process multiple books"""
    
    # Scan for books
    scanner = BookScanner(config)
    books = scanner.scan_directory(books_dir)
    
    if limit:
        books = books[:limit]
    
    print(f"Processing {len(books)} books...")
    
    results = []
    
    for i, book in enumerate(books):
        print(f"Processing {i+1}/{len(books)}: {book['title']}")
        
        try:
            result = process_book(book['path'], config)
            results.append(result)
            
            # Save progress
            with open('data/processing_results.json', 'w') as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"Error processing {book['title']}: {e}")
            results.append({
                'title': book['title'],
                'error': str(e)
            })
    
    print(f"\nCompleted {len(results)} books")
    
    # Summary stats
    successful = len([r for r in results if 'error' not in r])
    print(f"Successful: {successful}/{len(results)}")
    
    return results
```

## Usage Example

```python
# Single book processing
config = {
    'ollama_model': 'qwen2.5-coder',
    'ollama_host': 'http://localhost:11434',
    'summaries_path': 'data/summaries',
    'summary_ratio': 0.05
}

# Process single book
result = process_book('/data/ebooks/my-book.epub', config)

print(f"Summary saved to: {result['output_files']}")
print(f"Compression: {result['stats']['compression_ratio']}%")

# Batch process
results = batch_process('/data/ebooks', config, limit=100)
```

## Output Examples

### Markdown Output

```markdown
# The Pragmatic Programmer

**Author:** Andrew Hunt, David Thomas

*Generated: 2024-01-15*

---

**Original Length:** 45,000 words
**Summary Length:** 2,250 words
**Compression:** 5%

---

## Executive Summary

[Summary paragraphs...]

## Key Takeaways

- DRY (Don't Repeat Yourself): Every piece of knowledge should have a single, unambiguous representation
- Orthogonality: Keep unrelated things unrelated
- Automation: Eliminate manual steps wherever possible
- Composition over Inheritance
- Test Early, Test Often

## Notable Quotes

> "Don't live with broken windows" - Page 7
> "Refactor early, refactor often" - Page 45
```

## Next Steps

- [Production Deployment](./15-production-deployment.md) - Scale to 200k+ books
