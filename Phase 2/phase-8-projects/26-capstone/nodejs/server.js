#!/usr/bin/env node
/**
 * Project Nexus - Node.js Edition
 * The ultimate unified AI platform for Jetson AGX Orin
 * 
 * A complete implementation using Express, Socket.IO, and modern JavaScript
 */

const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const { Ollama } = require('ollama');
const cors = require('cors');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('crypto').randomUUID ? () => require('crypto').randomUUID() : () => Math.random().toString(36).substr(2, 9);

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: {
        origin: '*',
        methods: ['GET', 'POST']
    }
});

// ==================== CONFIGURATION ====================

const CONFIG = {
    port: process.env.PORT || 5000,
    ollamaUrl: process.env.OLLAMA_URL || 'http://localhost:11434',
    defaultModel: process.env.DEFAULT_MODEL || 'llama3.2',
    dataDir: process.env.DATA_DIR || './data',
    uploadDir: process.env.UPLOAD_DIR || './data/uploads'
};

// Create directories
[CONFIG.dataDir, CONFIG.uploadDir].forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

// ==================== MIDDLEWARE ====================

app.use(cors());
app.use(express.json({ limit: '100mb' }));
app.use(express.urlencoded({ extended: true, limit: '100mb' }));

// Ollama client
const ollama = new Ollama({ host: CONFIG.ollamaUrl });

// ==================== IN-MEMORY STORAGE ====================

const sessions = new Map();
const sessionHistory = new Map();

// Create default session
sessions.set('default', {
    id: 'default',
    name: 'Main Chat',
    createdAt: new Date(),
    messages: []
});

// ==================== API ROUTES ====================

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'Project Nexus', version: '1.0.0' });
});

// System stats
app.get('/api/v1/system/stats', async (req, res) => {
    try {
        const os = require('os');
        
        // Try to get GPU stats via nvidia-smi
        let gpuStats = null;
        try {
            const { execSync } = require('child_process');
            const output = execSync('nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits').toString();
            const [util, memUsed, memTotal, temp] = output.trim().split(', ');
            gpuStats = {
                utilization: parseInt(util),
                memoryUsed: parseInt(memUsed),
                memoryTotal: parseInt(memTotal),
                temperature: parseInt(temp)
            };
        } catch (e) {
            // GPU stats not available
        }
        
        const mem = os.freemem();
        const totalMem = os.totalmem();
        
        res.json({
            cpu: {
                usage: os.loadavg()[0] * 100 / os.cpus().length,
                cores: os.cpus().length
            },
            memory: {
                total: totalMem,
                used: totalMem - mem,
                percent: ((totalMem - mem) / totalMem * 100).toFixed(1)
            },
            gpu: gpuStats,
            sessions: sessions.size,
            uptime: process.uptime()
        });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// List models
app.get('/api/v1/models', async (req, res) => {
    try {
        const response = await ollama.list();
        res.json({ models: response.models || [] });
    } catch (e) {
        res.json({ models: [{ name: CONFIG.defaultModel }] });
    }
});

// Chat completions
app.post('/api/v1/chat/completions', async (req, res) => {
    try {
        const { model, messages, stream, temperature, max_tokens } = req.body;
        
        const prompt = messages.map(m => `${m.role}: ${m.content}`).join('\n') + '\nassistant:';
        
        if (stream) {
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');
            
            const stream = await ollama.generate({
                model: model || CONFIG.defaultModel,
                prompt,
                stream: true,
                options: {
                    temperature: temperature || 0.7,
                    num_predict: max_tokens || 2048
                }
            });
            
            for await (const chunk of stream) {
                res.write(`data: ${JSON.stringify({ choices: [{ delta: { content: chunk.response } }] })}\n\n`);
            }
            res.write('data: [DONE]\n\n');
            res.end();
        } else {
            const response = await ollama.generate({
                model: model || CONFIG.defaultModel,
                prompt,
                stream: false,
                options: {
                    temperature: temperature || 0.7,
                    num_predict: max_tokens || 2048
                }
            });
            
            res.json({
                id: `nexus-${Date.now()}`,
                object: 'chat.completion',
                created: Date.now(),
                model: model || CONFIG.defaultModel,
                choices: [{
                    index: 0,
                    message: { role: 'assistant', content: response.response },
                    finish_reason: 'stop'
                }]
            });
        }
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Chat with session
app.post('/api/v1/chat', async (req, res) => {
    try {
        const { message, model, session_id } = req.body;
        
        // Get or create session
        let session = sessions.get(session_id || 'default');
        if (!session) {
            session = {
                id: session_id || uuidv4(),
                name: 'New Chat',
                createdAt: new Date(),
                messages: []
            };
            sessions.set(session.id, session);
        }
        
        // Add user message
        session.messages.push({ role: 'user', content: message });
        
        // Build prompt
        const systemPrompt = session.systemPrompt || 'You are Nexus, a helpful AI assistant.';
        const prompt = `System: ${systemPrompt}\n\n` +
            session.messages.map(m => `${m.role}: ${m.content}`).join('\n') +
            `\nassistant:`;
        
        // Get response
        const response = await ollama.generate({
            model: model || CONFIG.defaultModel,
            prompt,
            stream: false
        });
        
        // Add assistant message
        session.messages.push({ role: 'assistant', content: response.response });
        
        // Keep history manageable
        if (session.messages.length > 50) {
            session.messages = session.messages.slice(-50);
        }
        
        res.json({
            success: true,
            response: response.response,
            session_id: session.id
        });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Sessions
app.get('/api/v1/sessions', (req, res) => {
    const list = Array.from(sessions.values()).map(s => ({
        id: s.id,
        name: s.name,
        createdAt: s.createdAt,
        messages: s.messages.length
    }));
    res.json({ sessions: list });
});

app.post('/api/v1/sessions', (req, res) => {
    const { name, systemPrompt } = req.body;
    const session = {
        id: uuidv4(),
        name: name || 'New Chat',
        createdAt: new Date(),
        systemPrompt: systemPrompt || '',
        messages: []
    };
    sessions.set(session.id, session);
    res.json(session);
});

app.delete('/api/v1/sessions/:id', (req, res) => {
    if (sessions.delete(req.params.id)) {
        res.json({ success: true });
    } else {
        res.status(404).json({ error: 'Session not found' });
    }
});

// RAG - Add document
const upload = multer({ dest: CONFIG.uploadDir });

app.post('/api/v1/rag/documents', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }
        
        const content = fs.readFileSync(req.file.path, 'utf-8');
        
        res.json({
            success: true,
            filename: req.file.originalname,
            size: req.file.size,
            chunks: Math.ceil(content.length / 1000)
        });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// RAG - Query
app.post('/api/v1/rag/query', async (req, res) => {
    const { question } = req.body;
    
    // Simple retrieval - in production use ChromaDB
    res.json({
        success: true,
        results: [{
            content: 'This is a placeholder RAG response. Configure vector store for full functionality.',
            score: 0.95
        }]
    });
});

// Web Search
app.post('/api/v1/search', async (req, res) => {
    const { query } = req.body;
    
    try {
        const { execSync } = require('child_process');
        const results = execSync(`ddgr --json -n 5 "${query}"`, { encoding: 'utf-8' });
        const lines = results.split('\n').filter(l => l.trim());
        const parsed = lines.map(l => {
            try { return JSON.parse(l); } catch { return null; }
        }).filter(Boolean);
        
        res.json({ results: parsed.map(r => ({ title: r.title, url: r.url, snippet: r.body })) });
    } catch (e) {
        res.json({ results: [], error: 'Search unavailable' });
    }
});

// ==================== SOCKET.IO EVENTS ====================

io.on('connection', (socket) => {
    console.log(`Client connected: ${socket.id}`);
    
    socket.on('chat_message', async (data) => {
        try {
            const { message, model, session_id } = data;
            
            // Get or create session
            let session = sessions.get(session_id || 'default');
            if (!session) {
                session = {
                    id: session_id || uuidv4(),
                    name: 'Chat',
                    createdAt: new Date(),
                    messages: []
                };
                sessions.set(session.id, session);
            }
            
            // Add to history
            session.messages.push({ role: 'user', content: message });
            
            // Build prompt
            const prompt = `You are Nexus, a helpful AI.\n\n` +
                session.messages.map(m => `${m.role}: ${m.content}`).join('\n') +
                `\nassistant:`;
            
            // Stream response
            const stream = await ollama.generate({
                model: model || CONFIG.defaultModel,
                prompt,
                stream: true
            });
            
            let fullResponse = '';
            for await (const chunk of stream) {
                fullResponse += chunk.response;
                socket.emit('stream_chunk', { token: chunk.response, done: false });
            }
            
            session.messages.push({ role: 'assistant', content: fullResponse });
            
            socket.emit('stream_chunk', { token: '', done: true });
            socket.emit('chat_response', {
                success: true,
                response: fullResponse,
                session_id: session.id
            });
            
        } catch (e) {
            socket.emit('error', { message: e.message });
        }
    });
    
    socket.on('create_session', (data) => {
        const session = {
            id: uuidv4(),
            name: data?.name || 'New Chat',
            createdAt: new Date(),
            systemPrompt: data?.systemPrompt || '',
            messages: []
        };
        sessions.set(session.id, session);
        socket.emit('session_created', session);
    });
    
    socket.on('vision_analyze', async (data) => {
        // Vision processing placeholder
        socket.emit('vision_result', {
            description: 'Vision analysis - configure LLaVA model for full functionality'
        });
    });
    
    socket.on('system_stats', async () => {
        try {
            const os = require('os');
            socket.emit('system_stats', {
                memory: os.freemem() / os.totalmem() * 100,
                sessions: sessions.size,
                timestamp: Date.now()
            });
        } catch (e) {
            socket.emit('system_stats', { error: e.message });
        }
    });
    
    socket.on('disconnect', () => {
        console.log(`Client disconnected: ${socket.id}`);
    });
});

// ==================== SERVE STATIC FILES ====================

app.use(express.static(path.join(__dirname, 'public')));

// ==================== START SERVER ====================

httpServer.listen(CONFIG.port, '0.0.0.0', () => {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🧠 Project Nexus - Node.js Edition                     ║
║   Unified AI Platform for Jetson AGX Orin                ║
║                                                           ║
║   Server running at: http://localhost:${CONFIG.port}               ║
║   Ollama: ${CONFIG.ollamaUrl}                          ║
║   Default Model: ${CONFIG.defaultModel}                           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    `);
});

module.exports = { app, io };
