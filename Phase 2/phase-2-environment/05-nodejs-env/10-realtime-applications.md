# Real-time Applications

This guide covers building real-time applications on Jetson AGX Orin.

## Socket.io Server

```javascript
const { Server } = require('socket.io');
const io = new Server(3000, {
  cors: {
    origin: '*'
  }
});

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  socket.on('chat message', (msg) => {
    io.emit('chat message', msg);
  });
  
  socket.on('disconnect', () => {
    console.log('Client disconnected');
  });
});
```

## Socket.io Client

```html
<script src="/socket.io/socket.io.js"></script>
<script>
  const socket = io();
  
  socket.on('chat message', (msg) => {
    const item = document.createElement('li');
    item.textContent = msg;
    document.getElementById('messages').appendChild(item);
  });
  
  document.getElementById('form').addEventListener('submit', (e) => {
    e.preventDefault();
    socket.emit('chat message', document.getElementById('input').value);
  });
</script>
```

## Ollama Streaming

```javascript
const io = require('socket.io')(3000);

io.on('connection', (socket) => {
  socket.on('generate', async (prompt) => {
    const response = await fetch('http://localhost:11434/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'llama2',
        prompt,
        stream: true
      })
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(Boolean);
      
      for (const line of lines) {
        try {
          const data = JSON.parse(line);
          socket.emit('chunk', data.response);
        } catch (e) {}
      }
    }
    
    socket.emit('done');
  });
});
```

## Presence System

```javascript
const users = new Map();

io.on('connection', (socket) => {
  users.set(socket.id, { status: 'online' });
  io.emit('users', Array.from(users.values()));
  
  socket.on('disconnect', () => {
    users.delete(socket.id);
    io.emit('users', Array.from(users.values()));
  });
});
```

## Rooms

```javascript
io.on('connection', (socket) => {
  socket.on('join room', (room) => {
    socket.join(room);
    socket.to(room).emit('user joined');
  });
  
  socket.on('leave room', (room) => {
    socket.leave(room);
    socket.to(room).emit('user left');
  });
  
  socket.on('room message', (data) => {
    io.to(data.room).emit('message', data.message);
  });
});
```

## Real-time Notifications

```javascript
// Server
io.on('connection', (socket) => {
  socket.on('subscribe', (userId) => {
    socket.join(`user:${userId}`);
  });
});

// Send notification
function notifyUser(userId, message) {
  io.to(`user:${userId}`).emit('notification', message);
}
```

## Real-time Collaboration

```javascript
io.on('connection', (socket) => {
  socket.on('cursor move', (data) => {
    socket.broadcast.emit('cursor update', {
      user: socket.id,
      position: data.position
    });
  });
  
  socket.on('text change', (data) => {
    socket.broadcast.emit('text update', {
      user: socket.id,
      changes: data.changes
    });
  });
});
```

## Heartbeat

```javascript
setInterval(() => {
  io.emit('ping');
}, 30000);

io.on('connection', (socket) => {
  socket.on('pong', () => {
    // Client responsive
  });
  
  socket.on('disconnect', () => {
    console.log('Client disconnected');
  });
});
```

## Authentication

```javascript
io.use((socket, next) => {
  const token = socket.handshake.auth.token;
  
  try {
    const decoded = jwt.verify(token, 'secret');
    socket.user = decoded;
    next();
  } catch (err) {
    next(new Error('Unauthorized'));
  }
});

io.on('connection', (socket) => {
  console.log('Authenticated:', socket.user.id);
});
```

## Error Handling

```javascript
io.on('connection', (socket) => {
  socket.on('error', (err) => {
    console.error('Socket error:', err);
  });
});

io.engine.on('connection_error', (err) => {
  console.error('Connection error:', err);
});
```

## Scaling

```bash
# Using Redis adapter
npm install @socket.io/redis-adapter

const { createAdapter } = require('@socket.io/redis-adapter');
const { createClient } = require('redis');

const pubClient = createClient({ url: 'redis://localhost:6379' });
const subClient = pubClient.duplicate();

io.adapter(createAdapter(pubClient, subClient));
```
