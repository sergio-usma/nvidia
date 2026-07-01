# MistralLite Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/chat', async (req, res) => {
    const { message } = req.body;
    const r = await ollama.chat({ model: 'mistrallite', 
        messages: [{ role: 'user', content: message }] });
    res.json({ reply: r.message.content });
});

app.listen(3013, () => console.log('MistralLite API on 3013'));
```

Run: `node mistrallite_api.js`
