# Phi4 Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/reason', async (req, res) => {
    const { problem } = req.body;
    const r = await ollama.generate({ model: 'phi4-mini-reasoning', 
        prompt: `Reason: ${problem}` });
    res.json({ result: r.response });
});

app.listen(3016, () => console.log('Phi4 API on 3016'));
```

Run: `node phi4_api.js`
