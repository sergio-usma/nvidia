# WebSocket Implementation

This guide covers WebSocket implementation for real-time communication on Jetson AGX Orin.

## Install WebSocket Library

```bash
npm install ws
```

## Basic WebSocket Server

```javascript
const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws) => {
  console.log('Client connected');
  
  ws.on('message', (message) => {
    console.log('Received:', message.toString());
    ws.send('Echo: ' + message);
  });
  
  ws.send('Welcome to the server!');
});

console.log('WebSocket server on port 8080');
```

## WebSocket with Express

```javascript
const express = require('express');
const http = require('http');
const WebSocket = require('ws');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
  ws.on('message', (message) => {
    // Broadcast to all clients
    wss.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message.toString());
      }
    });
  });
});

server.listen(3000, () => {
  console.log('Server on port 3000');
});
```

## Client-Side WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8080');

ws.onopen = () => {
  console.log('Connected');
  ws.send('Hello Server!');
};

ws.onmessage = (event) => {
  console.log('Received:', event.data);
};

ws.onclose = () => {
  console.log('Disconnected');
};

ws.onerror = (error) => {
  console.error('Error:', error);
};
```

## Real-Time Chat Example

Server:

```javascript
const express = require('express');
const http = require('http');
const WebSocket = require('ws');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

let clients = [];

wss.on('connection', (ws) => {
  const clientId = Date.now();
  ws.clientId = clientId;
  clients.push(ws);
  
  console.log(`Client ${clientId} connected`);
  
  ws.on('message', (message) => {
    const data = JSON.parse(message);
    
    // Broadcast to all clients
    clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({
          type: 'message',
          id: clientId,
          text: data.text,
          timestamp: Date.now()
        }));
      }
    });
  });
  
  ws.on('close', () => {
    clients = clients.filter(c => c.clientId !== clientId);
    console.log(`Client ${clientId} disconnected`);
  });
});

server.listen(3000, () => {
  console.log('Chat server on port 3000');
});
```

## WebSocket with Ollama Streaming

```javascript
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const axios = require('axios');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

wss.on('connection', async (ws) => {
  ws.on('message', async (message) => {
    const { prompt, model } = JSON.parse(message);
    
    try {
      const response = await axios.post(
        'http://localhost:11434/api/generate',
        { model: model || 'llama2', prompt, stream: true },
        { responseType: 'stream' }
      );
      
      response.data.on('data', (chunk) => {
        const lines = chunk.toString().split('\n').filter(Boolean);
        
        lines.forEach((line) => {
          try {
            const data = JSON.parse(line);
            if (data.response) {
              ws.send(JSON.stringify({ type: 'chunk', content: data.response }));
            }
            if (data.done) {
              ws.send(JSON.stringify({ type: 'done' }));
            }
          } catch (e) {}
        });
      });
    } catch (error) {
      ws.send(JSON.stringify({ type: 'error', message: error.message }));
    }
  });
});

server.listen(3000, () => {
  console.log('WebSocket AI server on port 3000');
});
```

## Heartbeat/Keep-Alive

```javascript
const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws) => {
  ws.isAlive = true;
  
  ws.on('pong', () => {
    ws.isAlive = true;
  });
  
  ws.on('message', (message) => {
    ws.send('Pong');
  });
});

// Heartbeat interval
setInterval(() => {
  wss.clients.forEach((ws) => {
    if (ws.isAlive === false) {
      return ws.terminate();
    }
    ws.isAlive = false;
    ws.ping();
  });
}, 30000);
```

## WebSocket Security

```javascript
const WebSocket = require('ws');
const jwt = require('jsonwebtoken');

const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws, req) => {
  // Verify token
  const token = req.url.split('token=')[1];
  
  try {
    const decoded = jwt.verify(token, 'secret-key');
    ws.user = decoded;
  } catch (e) {
    ws.close(1008, 'Invalid token');
    return;
  }
  
  ws.on('message', (message) => {
    // Handle message
  });
});
```

## Socket.io (Alternative)

Install:

```bash
npm install socket.io
```

Server:

```javascript
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

io.on('connection', (socket) => {
  console.log('User connected:', socket.id);
  
  socket.on('chat message', (msg) => {
    io.emit('chat message', msg);
  });
  
  socket.on('disconnect', () => {
    console.log('User disconnected');
  });
});

server.listen(3000);
```

Client:

```html
<script src="/socket.io/socket.io.js"></script>
<script>
  const socket = io();
  
  socket.on('chat message', (msg) => {
    console.log(msg);
  });
  
  socket.emit('chat message', 'Hello!');
</script>
```

## Debug WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8080');

ws.on('open', () => {
  console.log('Connected');
  console.log('URL:', ws.url);
  console.log('Protocol:', ws.protocol);
  console.log('ReadyState:', ws.readyState);
});
```

## Close Connection Gracefully

```javascript
// Server side
ws.close(1000, 'Normal closure');

// Client side
ws.addEventListener('close', (event) => {
  console.log('Code:', event.code);
  console.log('Reason:', event.reason);
});
```
