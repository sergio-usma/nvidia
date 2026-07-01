# OpenCoder Node.js API

```javascript
const express = require('express');
const { Ollama } = require('olama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/complete', async (req, res) => {
    const { code } = req.body;
    const r = await ollama.generate({ model: 'opencoder', prompt: `Complete: ${code}` });
    res.json({ completion: r.response });
});

app.listen(3014, () => console.log('OpenCoder API on 3014'));
```

Run: `node opencoder_api.js`
