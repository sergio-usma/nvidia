# Nomic Embeddings Node.js API

A semantic search API using nomic-embed-text-v2-moe embeddings.

## Prerequisites

- [x] Ollama with `nomic-embed-text-v2-moe` model
- [x] Node.js 18+

## Installation

```bash
mkdir nomic-search
cd nomic-search
npm init -y
npm install express ollama cors body-parser
```

## Create the API

Create `server.js`:

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const ollama = new Ollama({ host: 'http://localhost:11434' });

app.use(cors());
app.use(bodyParser.json());

// In-memory store
const documents = [];
const embeddings = [];

// Generate embedding
async function getEmbedding(text) {
    const response = await ollama.embeddings({
        model: 'nomic-embed-text-v2-moe',
        prompt: text
    });
    return response.embedding;
}

// Cosine similarity
function cosineSimilarity(a, b) {
    const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0);
    const magA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
    const magB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));
    return dotProduct / (magA * magB);
}

// Health
app.get('/health', (req, res) => {
    res.json({ status: 'ok', documents: documents.length });
});

// Add document
app.post('/documents', async (req, res) => {
    try {
        const { text, metadata = {} } = req.body;
        
        if (!text) {
            return res.status(400).json({ error: 'Text is required' });
        }
        
        const embedding = await getEmbedding(text);
        
        const doc = {
            id: documents.length,
            text,
            metadata,
            embedding,
            created: new Date().toISOString()
        };
        
        documents.push(doc);
        embeddings.push(embedding);
        
        res.json({ success: true, id: doc.id, document: doc });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Add multiple documents
app.post('/documents/bulk', async (req, res) => {
    try {
        const { docs } = req.body;
        
        if (!docs || !Array.isArray(docs)) {
            return res.status(400).json({ error: 'Array of documents required' });
        }
        
        const results = [];
        
        for (const doc of docs) {
            const text = typeof doc === 'string' ? doc : doc.text;
            const metadata = typeof doc === 'object' ? doc.metadata || {} : {};
            
            const embedding = await getEmbedding(text);
            
            const document = {
                id: documents.length,
                text,
                metadata,
                embedding,
                created: new Date().toISOString()
            };
            
            documents.push(document);
            embeddings.push(embedding);
            results.push({ id: document.id, text: text.substring(0, 50) + '...' });
        }
        
        res.json({ success: true, added: results.length, documents: results });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Search
app.post('/search', async (req, res) => {
    try {
        const { query, top_k = 5 } = req.body;
        
        if (!query) {
            return res.status(400).json({ error: 'Query is required' });
        }
        
        const queryEmbedding = await getEmbedding(query);
        
        const similarities = embeddings.map((emb, idx) => ({
            id: documents[idx].id,
            text: documents[idx].text,
            metadata: documents[idx].metadata,
            score: cosineSimilarity(queryEmbedding, emb)
        }));
        
        similarities.sort((a, b) => b.score - a.score);
        
        res.json({
            query,
            results: similarities.slice(0, top_k)
        });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// RAG Query
app.post('/rag', async (req, res) => {
    try {
        const { question, top_k = 3, llm_model = 'llama3.2' } = req.body;
        
        if (!question) {
            return res.status(400).json({ error: 'Question is required' });
        }
        
        // Search relevant documents
        const queryEmbedding = await getEmbedding(question);
        
        const similarities = embeddings.map((emb, idx) => ({
            id: documents[idx].id,
            text: documents[idx].text,
            score: cosineSimilarity(queryEmbedding, emb)
        }));
        
        similarities.sort((a, b) => b.score - a.score);
        const contextDocs = similarities.slice(0, top_k);
        
        const context = contextDocs.map(d => d.text).join('\n\n');
        
        // Generate answer
        const prompt = `Based on the following context, answer the question.

Context:
${context}

Question: ${question}

Answer:`;
        
        const response = await ollama.generate({
            model: llm_model,
            prompt,
            options: { temperature: 0.7, num_predict: 512 }
        });
        
        res.json({
            question,
            answer: response.response,
            sources: contextDocs.map(d => ({
                id: d.id,
                text: d.text.substring(0, 100) + '...',
                score: d.score
            }))
        });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// List documents
app.get('/documents', (req, res) => {
    res.json({
        count: documents.length,
        documents: documents.map(d => ({
            id: d.id,
            text: d.text.substring(0, 100),
            metadata: d.metadata
        }))
    });
});

// Delete document
app.delete('/documents/:id', (req, res) => {
    const id = parseInt(req.params.id);
    
    if (id < 0 || id >= documents.length) {
        return res.status(404).json({ error: 'Document not found' });
    }
    
    documents.splice(id, 1);
    embeddings.splice(id, 1);
    
    // Re-index remaining documents
    for (let i = 0; i < documents.length; i++) {
        documents[i].id = i;
    }
    
    res.json({ success: true });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`Nomic Embeddings API running on port ${PORT}`);
});
```

## Run

```bash
node server.js
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/documents` | POST | Add document |
| `/documents/bulk` | POST | Add multiple docs |
| `/documents` | GET | List documents |
| `/documents/:id` | DELETE | Delete document |
| `/search` | POST | Semantic search |
| `/rag` | POST | Q&A with context |

## Example Usage

```bash
# Add documents
curl -X POST http://localhost:3001/documents \
  -H "Content-Type: application/json" \
  -d '{"text": "Python is a programming language", "metadata": {"category": "tech"}}'

# Search
curl -X POST http://localhost:3001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "programming language", "top_k": 3}'

# RAG Question
curl -X POST http://localhost:3001/rag \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?"}'
```

## JavaScript Client

```javascript
const API = 'http://localhost:3001';

// Add documents
await fetch(`${API}/documents/bulk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        docs: [
            'Python is a high-level language',
            'JavaScript runs in browsers',
            'Machine learning uses Python'
        ]
    })
});

// Search
const search = await fetch(`${API}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'web development', top_k: 2 })
});
const { results } = await search.json();
```
