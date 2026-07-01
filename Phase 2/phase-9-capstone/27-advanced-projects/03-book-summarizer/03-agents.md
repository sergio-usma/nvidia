# Multi-Agent System

Five specialized agents working together to generate professional book summaries.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Multi-Agent System                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator Agent                        │   │
│  │              (Coordinates all other agents)                  │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                        │
│         ┌───────────────────┼───────────────────┐                   │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │  Analyzer   │     │  Extractor  │     │  Synthesizer │        │
│  │   Agent     │     │   Agent     │     │   Agent      │        │
│  │             │     │             │     │              │        │
│  │ • Structure │     │ • Quotes   │     │ • Bullets   │        │
│  │ • Themes    │     │ • Concepts │     │ • Summary   │        │
│  │ • Outline   │     │ • Key ideas│     │ • Synthesis │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
│                                                                      │
│  Output: Professional Summary with Key Takeaways                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Base Agent

```python
# agents/base_agent.py
from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional
import ollama
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, config: Dict, agent_name: str):
        self.config = config
        self.agent_name = agent_name
        self.model = config.get('ollama_model', 'qwen2.5-coder')
        self.host = config.get('ollama_host', 'http://localhost:11434')
        self.client = ollama.Client(host=self.host)
        self.temperature = config.get('temperature', 0.7)
    
    @abstractmethod
    def process(self, input_data: Dict) -> Dict:
        """Process input and return output"""
        pass
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response using LLM"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    "top_p": 0.9,
                    "num_ctx": 8192
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return ""
    
    def log(self, message: str):
        """Log agent activity"""
        logger.info(f"[{self.agent_name}] {message}")
```

## Analyzer Agent

```python
# agents/analyzer_agent.py
from agents.base_agent import BaseAgent

class AnalyzerAgent(BaseAgent):
    """Analyze book structure, themes, and key elements"""
    
    SYSTEM_PROMPT = """You are a professional book analyst. Analyze books and identify:
- Main themes and topics
- Book structure and organization  
- Key arguments and ideas
- Target audience
- Writing style and tone

Provide detailed, structured analysis in your responses."""
    
    def __init__(self, config: Dict):
        super().__init__(config, "Analyzer")
    
    def process(self, input_data: Dict) -> Dict:
        """Analyze book content"""
        
        book_text = input_data.get('full_text', '')
        book_title = input_data.get('title', 'Unknown')
        author = input_data.get('author', 'Unknown')
        
        # Get first portion for analysis
        analysis_text = book_text[:10000]
        
        prompt = f"""Analyze this book and provide detailed insights:

Title: {book_title}
Author: {author}

Content (first 10,000 words):
{analysis_text}

Provide analysis covering:
1. **Main Themes**: What are the central themes and topics?
2. **Book Structure**: How is the book organized? What are the main sections?
3. **Key Arguments**: What are the main points or arguments made?
4. **Target Audience**: Who is this book best suited for?
5. **Writing Style**: Describe the author's writing approach
6. **Chapter Overview**: Summarize each major chapter/section

Be thorough and professional in your analysis."""
        
        self.log(f"Analyzing book: {book_title}")
        
        analysis = self.generate(prompt, self.SYSTEM_PROMPT)
        
        # Parse key themes
        themes = self._extract_themes(analysis)
        
        # Identify structure
        structure = self._extract_structure(analysis)
        
        return {
            'analysis': analysis,
            'themes': themes,
            'structure': structure,
            'target_audience': self._extract_audience(analysis),
            'word_count': len(book_text.split())
        }
    
    def _extract_themes(self, analysis: str) -> list:
        """Extract main themes from analysis"""
        themes = []
        
        # Simple extraction - in production use more sophisticated parsing
        if 'theme' in analysis.lower():
            lines = analysis.split('\n')
            for line in lines:
                if 'theme' in line.lower() and '- ' in line:
                    theme = line.split('- ', 1)[-1].strip()
                    if theme and len(theme) < 100:
                        themes.append(theme)
        
        return themes[:10]  # Limit to 10 themes
    
    def _extract_structure(self, analysis: str) -> list:
        """Extract book structure"""
        structure = []
        
        if 'chapter' in analysis.lower():
            lines = analysis.split('\n')
            for line in lines:
                if 'chapter' in line.lower():
                    structure.append(line.strip())
        
        return structure[:20]  # Limit to 20 sections
    
    def _extract_audience(self, analysis: str) -> str:
        """Extract target audience"""
        if 'audience' in analysis.lower():
            lines = analysis.split('\n')
            for line in lines:
                if 'audience' in line.lower():
                    return line.split(':', 1)[-1].strip()
        
        return "General readers"
```

## Extractor Agent

```python
# agents/extractor_agent.py
from agents.base_agent import BaseAgent

class ExtractorAgent(BaseAgent):
    """Extract key insights, quotes, and concepts from book"""
    
    SYSTEM_PROMPT = """You are a skilled information extractor. Your job is to identify and extract:
- Important quotes and passages
- Key concepts and definitions
- Critical insights and findings
- Actionable takeaways
- Supporting evidence and examples

Extract information accurately and preserve context."""
    
    def __init__(self, config: Dict):
        super().__init__(config, "Extractor")
    
    def process(self, input_data: Dict) -> Dict:
        """Extract key information from book"""
        
        book_text = input_data.get('full_text', '')
        analysis = input_data.get('analysis', '')
        
        # Process in chunks for large books
        chunks = self._chunk_text(book_text)
        
        all_quotes = []
        all_concepts = []
        all_insights = []
        
        self.log(f"Processing {len(chunks)} chunks for extraction")
        
        for i, chunk in enumerate(chunks[:10]):  # Limit to first 10 chunks for speed
            prompt = f"""Extract key information from this book section:

{chunk[:3000]}

Identify and list:
1. **Key Quotes**: Important statements (include page context if available)
2. **Concepts**: Important terms and their definitions
3. **Insights**: Valuable observations or findings

Format as a structured list."""
            
            result = self.generate(prompt, self.SYSTEM_PROMPT)
            
            # Parse results
            quotes = self._extract_quotes(result)
            concepts = self._extract_concepts(result)
            insights = self._extract_insights(result)
            
            all_quotes.extend(quotes)
            all_concepts.extend(concepts)
            all_insights.extend(insights)
        
        # Deduplicate
        all_quotes = list(set(all_quotes))[:20]
        all_concepts = list(set(all_concepts))[:15]
        all_insights = list(set(all_insights))[:20]
        
        return {
            'quotes': all_quotes,
            'concepts': all_concepts,
            'insights': all_insights,
            'quote_count': len(all_quotes),
            'concept_count': len(all_concepts),
            'insight_count': len(all_insights)
        }
    
    def _chunk_text(self, text: str) -> list:
        """Split text into chunks"""
        # Simple chunking
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), 2000):
            chunk = ' '.join(words[i:i+2000])
            chunks.append(chunk)
        
        return chunks
    
    def _extract_quotes(self, text: str) -> list:
        """Extract quotes from text"""
        quotes = []
        
        lines = text.split('\n')
        for line in lines:
            if '"' in line and len(line) > 20:
                quote = line.strip()
                if not quote.startswith('-'):
                    quotes.append(quote)
        
        return quotes
    
    def _extract_concepts(self, text: str) -> list:
        """Extract concepts"""
        concepts = []
        
        lines = text.split('\n')
        for line in lines:
            if 'concept' in line.lower() or 'term' in line.lower():
                if '- ' in line:
                    concepts.append(line.split('- ', 1)[-1].strip())
        
        return concepts
    
    def _extract_insights(self, text: str) -> list:
        """Extract insights"""
        insights = []
        
        lines = text.split('\n')
        for line in lines:
            if 'insight' in line.lower() or 'finding' in line.lower():
                if '- ' in line:
                    insights.append(line.split('- ', 1)[-1].strip())
        
        return insights
```

## Synthesizer Agent

```python
# agents/synthesizer_agent.py
from agents.base_agent import BaseAgent

class SynthesizerAgent(BaseAgent):
    """Create condensed summary from extracted information"""
    
    SYSTEM_PROMPT = """You are an expert at creating concise, professional summaries. Your summaries should:
- Be approximately 5% of the original book length
- Use bullet points for key takeaways
- Maintain the original voice and tone
- Include actionable insights
- Be suitable for busy professionals

Focus on the most valuable information."""
    
    def __init__(self, config: Dict):
        super().__init__(config, "Synthesizer")
        self.summary_ratio = config.get('summary_ratio', 0.05)
    
    def process(self, input_data: Dict) -> Dict:
        """Synthesize summary from analysis and extraction"""
        
        book_text = input_data.get('full_text', '')
        analysis = input_data.get('analysis', '')
        extraction = input_data.get('extraction', {})
        
        book_title = input_data.get('title', 'Unknown')
        author = input_data.get('author', 'Unknown')
        word_count = len(book_text.split())
        target_summary_words = int(word_count * self.summary_ratio)
        
        # Prepare context
        context = f"""Book: {book_title}
Author: {author}
Original Length: {word_count} words
Target Summary: ~{target_summary_words} words (5%)

Analysis:
{analysis[:3000]}

Key Quotes:
{chr(10).join(extraction.get('quotes', [])[:10])}

Key Concepts:
{chr(10).join(extraction.get('concepts', [])[:10])}

Insights:
{chr(10).join(extraction.get('insights', [])[:10])}"""
        
        prompt = f"""Create a professional summary of this book.

{context}

Create a summary that includes:

## Executive Summary
A 3-5 sentence overview of the book and its main value proposition.

## Key Takeaways
Organized by category:
- **Fundamentals**: Core concepts and principles
- **Key Insights**: Most valuable observations
- **Practical Applications**: How to apply the knowledge
- **Notable Quotes**: Important statements

## Target Audience
Who will benefit most from this book.

The summary should be professional, concise, and approximately 5% of the original length."""
        
        self.log(f"Synthesizing summary for: {book_title}")
        
        summary = self.generate(prompt, self.SYSTEM_PROMPT)
        
        # Extract bullet points
        bullets = self._extract_bullets(summary)
        
        # Calculate actual ratio
        actual_words = len(summary.split())
        actual_ratio = (actual_words / word_count) * 100 if word_count > 0 else 0
        
        return {
            'summary': summary,
            'bullets': bullets,
            'word_count': actual_words,
            'original_word_count': word_count,
            'compression_ratio': round(actual_ratio, 1)
        }
    
    def _extract_bullets(self, text: str) -> list:
        """Extract bullet points from summary"""
        bullets = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('- ', '• ', '* ')):
                bullets.append(line[2:].strip())
        
        return bullets[:30]
```

## Orchestrator

```python
# agents/orchestrator.py
from agents.analyzer_agent import AnalyzerAgent
from agents.extractor_agent import ExtractorAgent
from agents.synthesizer_agent import SynthesizerAgent
import logging

logger = logging.getLogger(__name__)

class Orchestrator:
    """Coordinate all agents to process a book"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Initialize agents
        self.analyzer = AnalyzerAgent(config)
        self.extractor = ExtractorAgent(config)
        self.synthesizer = SynthesizerAgent(config)
    
    def process_book(self, book_data: Dict) -> Dict:
        """Process book through all agents"""
        
        logger.info(f"Starting processing for: {book_data.get('title')}")
        
        # Step 1: Analyze
        logger.info("Step 1: Analyzing book...")
        analysis = self.analyzer.process(book_data)
        
        # Step 2: Extract
        logger.info("Step 2: Extracting key information...")
        book_data['analysis'] = analysis.get('analysis', '')
        extraction = self.extractor.process(book_data)
        
        # Step 3: Synthesize
        logger.info("Step 3: Synthesizing summary...")
        book_data['extraction'] = extraction
        synthesis = self.synthesizer.process(book_data)
        
        # Combine results
        result = {
            'title': book_data.get('title'),
            'author': book_data.get('author'),
            'analysis': analysis,
            'extraction': extraction,
            'summary': synthesis.get('summary'),
            'bullets': synthesis.get('bullets'),
            'stats': {
                'original_words': analysis.get('word_count'),
                'summary_words': synthesis.get('word_count'),
                'compression_ratio': synthesis.get('compression_ratio'),
                'quotes_extracted': extraction.get('quote_count'),
                'concepts_extracted': extraction.get('concept_count')
            }
        }
        
        logger.info(f"Completed processing: {book_data.get('title')}")
        
        return result
```

## Usage

```python
# Process a book with all agents
from agents.orchestrator import Orchestrator

config = {
    'ollama_model': 'qwen2.5-coder',
    'ollama_host': 'http://localhost:11434',
    'summary_ratio': 0.05
}

# Initialize orchestrator
orchestrator = Orchestrator(config)

# Process book (from parser)
book_data = {
    'title': 'The Pragmatic Programmer',
    'author': 'Andrew Hunt, David Thomas',
    'full_text': book_text,  # From EPUB/PDF parser
    'word_count': len(book_text.split())
}

# Process through agents
result = orchestrator.process_book(book_data)

print(f"Summary: {result['summary'][:500]}...")
print(f"Stats: {result['stats']}")
```

## Next Steps

- [Summary Generation](./14-summary-generation.md) - Output formats
