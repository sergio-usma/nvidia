# Qwen3 Coder Node.js Backend

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/generate', async (req, res) => {
    const { prompt } = req.body;
    const r = await ollama.generate({ model: 'qwen3-coder', prompt: `Code: ${prompt}` });
    res.json({ code: r.response });
});

app.listen(3018, () => console.log('Qwen3 Coder API on 3018'));
```

Run: `node qwen3coder_backend.js`
