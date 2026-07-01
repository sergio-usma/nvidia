# LFM2 Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/complete', async (req, res) => {
    const { text } = req.body;
    const r = await ollama.generate({ model: 'lfm2', prompt: text });
    res.json({ completion: r.response });
});

app.listen(3021, () => console.log('LFM2 API on 3021'));
```

Run: `node lfm2_api.js`
