# Granite Node.js Enterprise API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/review', async (req, res) => {
    const { code } = req.body;
    const r = await ollama.generate({ model: 'granite3.3', 
        prompt: `Review: ${code}` });
    res.json({ review: r.response });
});

app.listen(3015, () => console.log('Granite API on 3015'));
```

Run: `node granite_api.js`
