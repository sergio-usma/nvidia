# Nemotron-3-Nano Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/chat', async (req, res) => {
    const { message } = req.body;
    const r = await ollama.chat({ model: 'nemotron-3-nano',
        messages: [{ role: 'user', content: message }] });
    res.json({ reply: r.message.content });
});

app.listen(3019, () => console.log('Nemotron Nano API on 3019'));
```

Run: `node nemotron_api.js`
