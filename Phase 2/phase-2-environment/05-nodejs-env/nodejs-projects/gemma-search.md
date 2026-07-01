# Gemma Embeddings Fast Search (Node.js)

Create `gemma_search.js`:

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();

app.use(express.json());

const docs = [];
const embeddings = [];

// Embed text
app.post('/embed', async (req, res) => {
    const { text } = req.body;
    
    const response = await ollama.embeddings({
        model: 'embeddinggemma',
        prompt: text
    });
    
    res.json({ embedding: response.embedding });
});

// Add to index
app.post('/index', async (req, res) => {
    const { text, id } = req.body;
    
    const response = await ollama.embeddings({
        model: 'embeddinggemma',
        prompt: text
    });
    
    docs.push({ id: id || docs.length, text });
    embeddings.push(response.embedding);
    
    res.json({ id: docs.length - 1, indexed: true });
});

// Search
app.post('/search', async (req, res) => {
    const { query, top = 3 } = req.body;
    
    const q_emb = await ollama.embeddings({
        model: 'embeddinggemma',
        prompt: query
    });
    
    // Simple cosine similarity
    const scores = embeddings.map((emb, i) => ({
        id: docs[i].id,
        text: docs[i].text,
        score: cosine(q_emb.embedding, emb)
    }));
    
    scores.sort((a, b) => b.score - a.score);
    
    res.json({ results: scores.slice(0, top) });
});

function cosine(a, b) {
    const dot = a.reduce((s, v, i) => s + v * b[i], 0);
    const magA = Math.sqrt(a.reduce((s, v) => s + v * v, 0));
    const magB = Math.sqrt(b.reduce((s, v) => s + v * v, 0));
    return dot / (magA * magB);
}

app.listen(3006, () => console.log('Gemma search on port 3006'));
```

Run: `node gemma_search.js`
