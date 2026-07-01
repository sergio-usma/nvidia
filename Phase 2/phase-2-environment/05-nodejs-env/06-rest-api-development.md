# REST API Development

This guide covers REST API development best practices for Jetson AGX Orin.

## API Design Principles

- Use nouns for resources: `/users`, `/products`
- Use HTTP methods: GET, POST, PUT, DELETE
- Use status codes properly
- Version your API: `/api/v1/users`

## Project Setup

```bash
mkdir api-project
cd api-project
npm init -y
npm install express cors helmet morgan dotenv
```

## Complete REST API

```javascript
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());

// In-memory data store
let users = [
  { id: 1, name: 'John', email: 'john@example.com' },
  { id: 2, name: 'Jane', email: 'jane@example.com' }
];

// GET all
app.get('/api/users', (req, res) => {
  res.json(users);
});

// GET one
app.get('/api/users/:id', (req, res) => {
  const user = users.find(u => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json(user);
});

// POST
app.post('/api/users', (req, res) => {
  const { name, email } = req.body;
  
  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email required' });
  }
  
  const newUser = {
    id: users.length + 1,
    name,
    email
  };
  
  users.push(newUser);
  res.status(201).json(newUser);
});

// PUT
app.put('/api/users/:id', (req, res) => {
  const user = users.find(u => u.id === parseInt(req.params.id));
  if (!user) return res.status(404).json({ error: 'User not found' });
  
  const { name, email } = req.body;
  user.name = name || user.name;
  user.email = email || user.email;
  
  res.json(user);
});

// DELETE
app.delete('/api/users/:id', (req, res) => {
  const index = users.findIndex(u => u.id === parseInt(req.params.id));
  if (index === -1) return res.status(404).json({ error: 'User not found' });
  
  users.splice(index, 1);
  res.status(204).send();
});

// Error handling
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, () => {
  console.log(`API running on port ${PORT}`);
});
```

## Query Parameters

```javascript
app.get('/api/users', (req, res) => {
  let result = users;
  
  // Filter
  if (req.query.name) {
    result = result.filter(u => 
      u.name.toLowerCase().includes(req.query.name.toLowerCase())
    );
  }
  
  // Sort
  if (req.query.sort) {
    const sortKey = req.query.sort;
    result.sort((a, b) => a[sortKey] > b[sortKey] ? 1 : -1);
  }
  
  // Pagination
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 10;
  const start = (page - 1) * limit;
  const end = start + limit;
  
  res.json({
    data: result.slice(start, end),
    page,
    limit,
    total: result.length
  });
});
```

## Nested Routes

```javascript
// User posts: /api/users/:userId/posts
app.get('/api/users/:userId/posts', (req, res) => {
  const posts = userPosts.filter(p => 
    p.userId === parseInt(req.params.userId)
  );
  res.json(posts);
});

// Create post for user
app.post('/api/users/:userId/posts', (req, res) => {
  const post = {
    id: posts.length + 1,
    userId: parseInt(req.params.userId),
    title: req.body.title,
    content: req.body.content
  };
  posts.push(post);
  res.status(201).json(post);
});
```

## Response Formats

```javascript
// Success response
res.status(200).json({
  success: true,
  data: user
});

// Error response
res.status(400).json({
  success: false,
  error: {
    code: 'VALIDATION_ERROR',
    message: 'Invalid email format'
  }
});

// Paginated response
res.status(200).json({
  success: true,
  data: users,
  pagination: {
    page: 1,
    limit: 10,
    total: 100,
    pages: 10
  }
});
```

## Input Validation

```bash
npm install express-validator
```

```javascript
const { body, validationResult } = require('express-validator');

app.post('/api/users',
  body('name').isLength({ min: 2 }).trim(),
  body('email').isEmail().normalizeEmail(),
  body('age').optional().isInt({ min: 0 }),
  
  (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    
    // Create user
    res.status(201).json({ message: 'User created' });
  }
);
```

## Rate Limiting

```bash
npm install express-rate-limit
```

```javascript
const rateLimit = require('express-rate-limit');

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP
  message: { error: 'Too many requests' }
});

app.use('/api/', limiter);
```

## API Documentation

```bash
npm install swagger-jsdoc swagger-ui-express
```

```javascript
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'My API',
      version: '1.0.0'
    }
  },
  apis: ['./routes/*.js']
};

const specs = swaggerJsdoc(options);
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));
```

## API Versioning

```javascript
// /api/v1/users
app.use('/api/v1', require('./routes/v1/users'));
// /api/v2/users
app.use('/api/v2', require('./routes/v2/users'));
```

## Testing with cURL

```bash
# GET
curl http://localhost:3000/api/users

# POST
curl -X POST http://localhost:3000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John","email":"john@example.com"}'

# PUT
curl -X PUT http://localhost:3000/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"John Updated"}'

# DELETE
curl -X DELETE http://localhost:3000/api/users/1
```

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Error |
