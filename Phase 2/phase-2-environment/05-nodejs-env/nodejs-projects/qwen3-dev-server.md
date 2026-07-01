# Qwen3 Coder llama.cpp Node.js

```javascript
const express = require('express');
const axios = require('axios');
const app = express();
app.use(express.json());

const LLAMA_URL = 'http://localhost:8080';

app.post('/code', async (req, res) => {
    const { task } = req.body;
    const r = await axios.post(`${LLAMA_URL}/completion`, {
        prompt: `Write code: ${task}`,
        n_predict: 1024
    });
    res.json({ code: r.data.content });
});

app.listen(4000, () => console.log('Qwen3 Coder (llama.cpp) on 4000'));
```

Run server first: `llama-cli -m ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf -ngl 999 -c 4096 --server`
Then: `node qwen3_dev_server.js`
