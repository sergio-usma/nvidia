# DeepScaler Node.js Math API

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
const ollama = new Ollama();
app.use(express.json());

app.post('/solve', async (req, res) => {
    const { problem } = req.body;
    const r = await ollama.generate({ model: 'deepscaler', prompt: `Solve: ${problem}` });
    res.json({ solution: r.response });
});

app.post('/verify', async (req, res) => {
    const { problem, solution } = req.body;
    const r = await ollama.generate({ model: 'deepscaler', prompt: `Verify: ${problem} = ${solution}` });
    res.json({ result: r.response });
});

app.listen(3010, () => console.log('DeepScaler API on 3010'));
```

Run: `node deepscaler_api.js`
