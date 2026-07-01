# Node.js AI Libraries

This guide covers Node.js AI and machine learning libraries for Jetson AGX Orin.

## Transformers.js

Install:

```bash
npm install @xenova/transformers
```

Usage:

```javascript
import { pipeline } from '@xenova/transformers';

// Sentiment analysis
const classifier = await pipeline('sentiment-analysis');
const result = await classifier('I love this!');
console.log(result);

// Question answering
const qa = await pipeline('question-answering');
const answer = await qa({
  question: 'What is AI?',
  context: 'AI stands for Artificial Intelligence.'
});
```

## Ollama JavaScript SDK

Install:

```bash
npm install ollama
```

Usage:

```javascript
import { Ollama } from 'ollama';

const ollama = new Ollama({ host: 'http://localhost:11434' });

// Generate
const response = await ollama.generate({
  model: 'llama2',
  prompt: 'Hello!',
  stream: false
});

console.log(response.response);

// Chat
const chat = await ollama.chat({
  model: 'llama2',
  messages: [
    { role: 'user', content: 'Hello!' }
  ]
});
console.log(chat.message.content);

// Streaming
const stream = await ollama.generate({
  model: 'llama2',
  prompt: 'Count to 5',
  stream: true
});

for await (const part of stream) {
  process.stdout.write(part.response);
}
```

## TensorFlow.js

Install:

```bash
npm install @tensorflow/tfjs
```

Usage:

```javascript
const tf = require('@tensorflow/tfjs');

// Create tensor
const tensor = tf.tensor([[1, 2], [3, 4]]);

// Operations
const sum = tensor.sum();
const mean = tensor.mean();

// Model
const model = tf.sequential();
model.add(tf.layers.dense({ units: 1, inputShape: [1] }));
model.compile({ loss: 'meanSquaredError', optimizer: 'sgd' });

// Train
const xs = tf.tensor2d([1, 2, 3, 4], [4, 1]);
const ys = tf.tensor2d([1, 2, 3, 4], [4, 1]);

await model.fit(xs, ys, { epochs: 100 });

// Predict
const prediction = model.predict(tf.tensor2d([[5]], [1, 1]));
prediction.print();
```

## Brain.js

Install:

```bash
npm install brain.js
```

Usage:

```javascript
const brain = require('brain.js');

const network = new brain.neuralNetwork();

const trainingData = [
  { input: [0, 0], output: [0] },
  { input: [0, 1], output: [1] },
  { input: [1, 0], output: [1] },
  { input: [1, 1], output: [0] }
];

network.train(trainingData);

const output = network.run([1, 0]);
console.log(output);
```

## Compromise (NLP)

Install:

```bash
npm install compromise
```

Usage:

```javascript
const nlp = require('compromise');

const doc = nlp('John Smith is a software engineer in San Francisco');

doc.people().out('array'); // ['John Smith']
doc.places().out('array'); // ['San Francisco']
doc.verbs().out('array');  // ['is', 'work']
```

## Natural (NLP)

Install:

```bash
npm install natural
```

Usage:

```javascript
const natural = require('natural');
const tokenizer = new natural.WordTokenizer();

const tokens = tokenizer.tokenize('Hello world!');
console.log(tokens); // ['Hello', 'world', '!']

const stemmer = natural.PorterStemmer;
console.log(stemmer.stem('running')); // 'run'
```

## Synaptic (Neural Networks)

Install:

```bash
npm install synaptic
```

Usage:

```javascript
const synaptic = require('synaptic');
const Layer = synaptic.Layer;
const Network = synaptic.Network;
const Trainer = synaptic.Trainer;

const inputLayer = new Layer(2);
const hiddenLayer = new Layer(3);
const outputLayer = new Layer(1);

inputLayer.project(hiddenLayer);
hiddenLayer.project(outputLayer);

const network = new Network({ input: inputLayer, output: outputLayer });

const trainer = new Trainer(network);
const trainingData = [
  { input: [0, 0], output: [0] },
  { input: [0, 1], output: [1] },
  { input: [1, 0], output: [1] },
  { input: [1, 1], output: [0] }
];

trainer.train(trainingData);
```

## WebLLM

Install:

```bash
npm install webllm
```

Usage:

```javascript
import * as webllm from "webllm";

const engine = await webllm.CreateMLCEngine(
  "Llama-2-7b-chat-hf-q4f32_1",
  { initProgressCallback: (e) => console.log(e) }
);

const messages = [{ role: "user", content: "Hello!" }];
const output = await engine.chat.completions.create({
  messages,
  temperature: 0.7
});

console.log(output.choices[0].message.content);
```

## Node-Fetch / Axios for APIs

```javascript
const axios = require('axios');

async function queryOllama(prompt) {
  const response = await axios.post('http://localhost:11434/api/generate', {
    model: 'llama2',
    prompt: prompt,
    stream: false
  });
  return response.data.response;
}

async function queryWhisper(audioPath) {
  const formData = new FormData();
  formData.append('file', fs.createReadStream(audioPath));
  
  const response = await axios.post('http://localhost:8001/transcribe', formData);
  return response.data;
}
```

## Performance Tips

```javascript
// Use worker_threads for heavy computation
const { Worker } = require('worker');

const worker = new Worker('./compute-worker.js');
worker.on('message', (result) => console.log(result));

// Cache expensive computations
const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 600 });

function getCachedResult(key, compute) {
  const cached = cache.get(key);
  if (cached) return cached;
  
  const result = compute();
  cache.set(key, result);
  return result;
}
```
