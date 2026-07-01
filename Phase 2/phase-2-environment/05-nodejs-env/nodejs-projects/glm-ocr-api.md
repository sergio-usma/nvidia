# GLM-OCR Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/scan', async (req, res) => {
    const { image } = req.body;
    const r = await ollama.generate({ model: 'glm-ocr', prompt: `OCR: ${image}` });
    res.json({ text: r.response });
});

app.listen(3020, () => console.log('GLM OCR API on 3020'));
```

Run: `node glm_ocr_api.js`
