# Fastify for High Performance

This guide covers Fastify framework for high-performance APIs on Jetson AGX Orin.

## Install Fastify

```bash
npm install fastify
```

## Basic Server

```javascript
const fastify = require('fastify')({ logger: true });

fastify.get('/', async (request, reply) => {
  return { message: 'Hello from Fastify!' };
});

const start = async () => {
  try {
    await fastify.listen({ port: 3000 });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
```

## Routes

```javascript
// GET
fastify.get('/api/users', async (request, reply) => {
  return users;
});

// GET with params
fastify.get('/api/users/:id', async (request, reply) => {
  const { id } = request.params;
  const user = users.find(u => u.id === parseInt(id));
  if (!user) {
    reply.code(404);
    return { error: 'User not found' };
  }
  return user;
});

// POST
fastify.post('/api/users', async (request, reply) => {
  const { name, email } = request.body;
  const newUser = {
    id: users.length + 1,
    name,
    email
  };
  users.push(newUser);
  reply.code(201);
  return newUser;
});

// PUT
fastify.put('/api/users/:id', async (request, reply) => {
  const { id } = request.params;
  const user = users.find(u => u.id === parseInt(id));
  if (!user) {
    reply.code(404);
    return { error: 'User not found' };
  }
  
  Object.assign(user, request.body);
  return user;
});

// DELETE
fastify.delete('/api/users/:id', async (request, reply) => {
  const { id } = request.params;
  const index = users.findIndex(u => u.id === parseInt(id));
  if (index === -1) {
    reply.code(404);
    return { error: 'User not found' };
  }
  
  users.splice(index, 1);
  reply.code(204);
});
```

## Query Parameters

```javascript
fastify.get('/api/users', async (request, reply) => {
  let result = users;
  
  // Filter
  if (request.query.name) {
    result = result.filter(u => 
      u.name.includes(request.query.name)
    );
  }
  
  // Sort
  if (request.query.sort) {
    const key = request.query.sort;
    result.sort((a, b) => a[key] > b[key] ? 1 : -1);
  }
  
  // Limit
  if (request.query.limit) {
    result = result.slice(0, parseInt(request.query.limit));
  }
  
  return result;
});
```

## Schema Validation

```javascript
const userSchema = {
  body: {
    type: 'object',
    required: ['name', 'email'],
    properties: {
      name: { type: 'string', minLength: 1 },
      email: { type: 'string', format: 'email' }
    }
  },
  params: {
    type: 'object',
    properties: {
      id: { type: 'integer' }
    }
  },
  response: {
    200: {
      type: 'object',
      properties: {
        id: { type: 'integer' },
        name: { type: 'string' },
        email: { type: 'string' }
      }
    }
  }
};

fastify.post('/api/users', { schema: userSchema }, async (request, reply) => {
  const { name, email } = request.body;
  const newUser = { id: users.length + 1, name, email };
  users.push(newUser);
  reply.code(201);
  return newUser;
});
```

## Middleware

```javascript
// Logger
fastify.addHook('onRequest', async (request, reply) => {
  request.log.info({ url: request.url, method: request.method }, 'incoming request');
});

// Response hook
fastify.addHook('onResponse', async (request, reply, done) => {
  request.log.info({ 
    url: request.url, 
    method: request.method,
    statusCode: reply.statusCode,
    responseTime: reply.elapsedTime
  }, 'request completed');
  done();
});
```

## Fastify with Ollama

```javascript
const axios = require('axios');

fastify.post('/api/chat', async (request, reply) => {
  const { prompt, model } = request.body;
  
  try {
    const response = await axios.post('http://localhost:11434/api/generate', {
      model: model || 'llama2',
      prompt,
      stream: false
    });
    
    return response.data;
  } catch (error) {
    reply.code(500);
    return { error: error.message };
  }
});
```

## Plugins

```javascript
// my-plugin.js
async function myPlugin(fastify, options) {
  fastify.decorate('myUtility', () => 'utility value');
  
  fastify.get('/plugin-route', async (request, reply) => {
    return { message: fastify.myUtility() };
  });
}

module.exports = myPlugin;

// Use plugin
fastify.register(myPlugin);
```

## CORS

```bash
npm install @fastify/cors
```

```javascript
const cors = require('@fastify/cors');

fastify.register(cors, { 
  origin: true 
});
```

## Static Files

```bash
npm install @fastify/static
```

```javascript
const static = require('@fastify/static');
const path = require('path');

fastify.register(static, {
  root: path.join(__dirname, 'public')
});
```

## Rate Limiting

```bash
npm install @fastify/rate-limit
```

```javascript
const rateLimit = require('@fastify/rate-limit');

fastify.register(rateLimit, {
  max: 100,
  timeWindow: '1 minute'
});
```

## Fastify vs Express Performance

Fastify is typically 2-3x faster than Express for JSON APIs due to:
- Schema-based serialization
- Native async/await
- Lower overhead

## Production Config

```javascript
const fastify = require('fastify')({
  logger: {
    level: 'info',
    transport: {
      target: 'pino-pretty'
    }
  },
  requestTimeout: 30000,
  bodyLimit: 1048576
});
```

## Decorators

```javascript
// Add utility functions
fastify.decorate('getTimestamp', () => Date.now());

// Use in routes
fastify.get('/time', async () => {
  return { timestamp: fastify.getTimestamp() };
});
```
