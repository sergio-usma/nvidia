# Express.js Setup

This guide covers Express.js setup for building APIs on Jetson AGX Orin.

## Install Express

```bash
mkdir my-app
cd my-app
npm init -y
npm install express
```

## Basic Server

```javascript
const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.send('Hello from Jetson!');
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
```

Run: `node app.js`

## REST API Routes

```javascript
const express = require('express');
const app = express();

app.use(express.json());

// GET
app.get('/api/users', (req, res) => {
  res.json(users);
});

// GET by ID
app.get('/api/users/:id', (req, res) => {
  const user = users.find(u => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).send('User not found');
  res.json(user);
});

// POST
app.post('/api/users', (req, res) => {
  const newUser = {
    id: users.length + 1,
    name: req.body.name,
    email: req.body.email
  };
  users.push(newUser);
  res.status(201).json(newUser);
});

// PUT
app.put('/api/users/:id', (req, res) => {
  const user = users.find(u => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).send('User not found');
  
  user.name = req.body.name || user.name;
  user.email = req.body.email || user.email;
  res.json(user);
});

// DELETE
app.delete('/api/users/:id', (req, res) => {
  const index = users.findIndex(u => u.id === parseInt(req.params.id));
  if (index === -1) return res.status(404).send('User not found');
  
  const deleted = users.splice(index, 1);
  res.json(deleted);
});
```

## Middleware

```javascript
// Logger
app.use((req, res, next) => {
  console.log(`${new Date()} - ${req.method} ${req.url}`);
  next();
});

// Error handler
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).send('Something broke!');
});

// Static files
app.use(express.static('public'));

// Body parser
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
```

## CORS

```bash
npm install cors
```

```javascript
const cors = require('cors');
app.use(cors());

// Or specific origin
app.use(cors({
  origin: 'http://example.com',
  optionsSuccessStatus: 200
}));
```

## Routing

```javascript
const router = express.Router();

router.get('/', (req, res) => {
  res.send('Users list');
});

router.get('/:id', (req, res) => {
  res.send(`User ${req.params.id}`);
});

app.use('/api/users', router);
```

## Connect to Ollama

```javascript
const axios = require('axios');

app.post('/api/chat', async (req, res) => {
  try {
    const response = await axios.post('http://localhost:11434/api/generate', {
      model: 'llama2',
      prompt: req.body.prompt,
      stream: false
    });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## File Upload

```bash
npm install multer
```

```javascript
const multer = require('multer');
const upload = multer({ dest: 'uploads/' });

app.post('/api/upload', upload.single('file'), (req, res) => {
  res.json({ 
    message: 'File uploaded',
    file: req.file 
  });
});
```

## Environment Variables

```bash
npm install dotenv
```

```javascript
require('dotenv').config();

const port = process.env.PORT || 3000;
const dbUrl = process.env.DATABASE_URL;
```

## Error Handling

```javascript
app.use((err, req, res, next) => {
  if (err.name === 'ValidationError') {
    return res.status(400).json(err);
  }
  if (err.name === 'UnauthorizedError') {
    return res.status(401).json(err);
  }
  res.status(500).json({ error: 'Internal server error' });
});
```

## Express in Production

```javascript
if (process.env.NODE_ENV === 'production') {
  app.use(express.static('build'));
  
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'build', 'index.html'));
  });
}
```

## PM2 Process Manager

```bash
npm install -g pm2
```

```bash
pm2 start app.js
pm2 list
pm2 logs
pm2 restart app
pm2 stop app
pm2 delete app
```

## Project Structure

```
my-app/
├── src/
│   ├── routes/
│   │   └── users.js
│   ├── controllers/
│   │   └── users.js
│   ├── models/
│   ├── middleware/
│   └── app.js
├── public/
├── .env
├── package.json
└── server.js
```
