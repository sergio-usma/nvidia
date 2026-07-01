# GLM-4.7 Flash llama.cpp Node.js

```javascript
const express = require('express');
const axios = require('axios');
const app = express();
app.use(express.json());

app.post('/fast', async (req, res) => {
    const { prompt } = req.body;
    const r = await axios.post('http://localhost:8080/completion', {
        prompt,
        n_predict: 256
    });
    res.json({ result: r.data.content });
});

app.listen(4002, () => console.log('GLM Flash on 4002'));
```

Run: `node glm_flash_llama.js`
