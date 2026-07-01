# OpenThinker Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/think', async (req, res) => {
    const { problem } = req.body;
    const r = await ollama.generate({ model: 'openthinker', prompt: `Think: ${problem}` });
    res.json({ reasoning: r.response });
});

app.post('/analyze', async (req, res) => {
    const { topic } = req.body;
    const r = await ollama.generate({ model: 'openthinker', prompt: `Analyze: ${topic}` });
    res.json({ analysis: r.response });
});

app.listen(3011, () => console.log('OpenThinker API on 3011'));
```

Run: `node openthinker_api.js`
