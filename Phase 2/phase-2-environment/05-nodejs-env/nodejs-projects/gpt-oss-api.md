# GPT-OSS Node.js API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/assist', async (req, res) => {
    const { task } = req.body;
    const r = await ollama.generate({ model: 'gpt-oss:20b', prompt: task });
    res.json({ result: r.response });
});

app.listen(3024, () => console.log('GPT-OSS API on 3024'));
```

Run: `node gpt_oss_api.js`
