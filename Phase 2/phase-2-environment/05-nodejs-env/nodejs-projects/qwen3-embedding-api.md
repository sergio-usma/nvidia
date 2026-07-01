# Qwen3 Embedding Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

const docs = [], embeddings = [];

app.post('/embed', async (req, res) => {
    const { text } = req.body;
    const r = await ollama.embeddings({ model: 'qwen3-embedding', prompt: text });
    res.json({ embedding: r.embedding });
});

app.post('/add', async (req, res) => {
    const { text } = req.body;
    const r = await ollama.embeddings({ model: 'qwen3-embedding', prompt: text });
    docs.push(text);
    embeddings.push(r.embedding);
    res.json({ id: docs.length - 1 });
});

app.post('/search', async (req, res) => {
    const { query, top = 3 } = req.body;
    const q = await ollama.embeddings({ model: 'qwen3-embedding', prompt: query });
    const scores = embeddings.map(e => cosine(q.embedding, e));
    const idx = scores.map((s, i) => [s, i]).sort((a, b) => b[0] - a[0]).slice(0, top);
    res.json({ results: idx.map(([s, i]) => ({ text: docs[i], score: s })) });
});

function cosine(a, b) { return a.reduce((s, v, i) => s + v * b[i], 0) / 
    (Math.sqrt(a.reduce((s, v) => s + v * v, 0)) * Math.sqrt(b.reduce((s, v) => s + v * v, 0))); }

app.listen(3022, () => console.log('Qwen3 Embedding API on 3022'));
```

Run: `node qwen3_embedding_api.js`
