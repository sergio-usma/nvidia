# Mistral-Nemo Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/ask', async (req, res) => {
    const { question } = req.body;
    const r = await ollama.chat({ model: 'mistral-nemo', 
        messages: [{ role: 'user', content: question }] });
    res.json({ answer: r.message.content });
});

app.post('/multi', async (req, res) => {
    const { tasks } = req.body;
    const results = await Promise.all(tasks.map(t => 
        ollama.generate({ model: 'mistral-nemo', prompt: t })));
    res.json({ results: results.map(r => r.response) });
});

app.listen(3012, () => console.log('Mistral-Nemo API on 3012'));
```

Run: `node nemo_api.js`
