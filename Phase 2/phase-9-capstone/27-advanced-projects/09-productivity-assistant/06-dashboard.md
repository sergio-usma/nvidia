# AI Office - Pixel Art Dashboard

## Overview

The dashboard provides a visual representation of the AI Office with a pixel art RPG-style interface showing all agents working in real-time.

## Dashboard Implementation

```python
#!/usr/bin/env python3
"""
AI Office Dashboard - Pixel Art Office
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

CONFIG = {
    "bus_api": "http://localhost:9001",
    "port": 9000
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """Get system status"""
    try:
        response = requests.get(f"{CONFIG['bus_api']}/api/status", timeout=5)
        return response.json()
    except:
        return {
            "agents": {},
            "queue_size": 0,
            "activity_log": []
        }


@app.route("/api/stats")
def api_stats():
    """Get statistics"""
    try:
        response = requests.get(f"{CONFIG['bus_api']}/api/stats", timeout=5)
        return response.json()
    except:
        return {}


@app.route("/api/activity")
def api_activity():
    """Get activity log"""
    try:
        response = requests.get(f"{CONFIG['bus_api']}/api/activity", timeout=5)
        return response.json()
    except:
        return {"activity_log": []}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=CONFIG["port"], debug=False)
```

## HTML Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Office - Pixel Dashboard</title>
    <style>
        @font-face {
            font-family: 'PixelFont';
            src: url('/static/pixel.ttf') format('truetype');
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0d0d1a;
            font-family: 'PixelFont', 'Courier New', monospace;
            color: #eee;
            min-height: 100vh;
        }
        
        /* CRT Effect */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: repeating-linear-gradient(
                0deg,
                rgba(0, 0, 0, 0.1),
                rgba(0, 0, 0, 0.1) 1px,
                transparent 1px,
                transparent 2px
            );
            pointer-events: none;
            z-index: 9999;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(180deg, #1a1a3a, #0d0d1a);
            border: 4px solid #4a4a6a;
            margin-bottom: 20px;
        }
        
        h1 {
            color: #00ff88;
            text-shadow: 0 0 10px #00ff88;
            font-size: 32px;
            letter-spacing: 4px;
        }
        
        .stats-bar {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 15px;
        }
        
        .stat {
            background: #1a1a3a;
            border: 2px solid #4a4a6a;
            padding: 10px 20px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 24px;
            color: #00ff88;
        }
        
        .stat-label {
            font-size: 10px;
            color: #888;
            text-transform: uppercase;
        }
        
        /* Office Scene */
        .office {
            background: linear-gradient(180deg, #2a2a4a 0%, #1a1a3a 70%, #3a3a5a 100%);
            border: 4px solid #4a4a6a;
            padding: 30px;
            position: relative;
            min-height: 400px;
            margin-bottom: 20px;
        }
        
        .floor {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 120px;
            background: 
                repeating-linear-gradient(90deg, #4a4a6a 0px, #4a4a6a 40px, #3a3a5a 40px, #3a3a5a 80px);
        }
        
        .desk-row {
            display: flex;
            justify-content: space-around;
            position: relative;
            z-index: 1;
            padding-bottom: 100px;
        }
        
        .workstation {
            text-align: center;
        }
        
        .pc {
            width: 80px;
            height: 60px;
            background: #2a2a4a;
            border: 3px solid #5a5a8a;
            position: relative;
            margin: 0 auto 10px;
        }
        
        .pc-screen {
            position: absolute;
            inset: 4px;
            background: #0a0a1a;
        }
        
        .pc-screen.active {
            background: #00ff88;
            animation: blink 0.5s infinite;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .pc-stand {
            width: 20px;
            height: 10px;
            background: #5a5a8a;
            margin: 0 auto;
        }
        
        .agent-name {
            color: #00ff88;
            font-size: 12px;
            margin-top: 5px;
        }
        
        .agent-status {
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 3px;
            margin-top: 3px;
        }
        
        .agent-status.idle { background: #333; color: #888; }
        .agent-status.working { background: #00ff88; color: #000; }
        .agent-status.waiting { background: #ffaa00; color: #000; }
        
        /* Activity Log */
        .activity-panel {
            background: #0a0a1a;
            border: 4px solid #4a4a6a;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .activity-title {
            color: #00ff88;
            font-size: 14px;
            margin-bottom: 10px;
            border-bottom: 2px solid #4a4a6a;
            padding-bottom: 5px;
        }
        
        .activity-entry {
            padding: 5px 0;
            border-bottom: 1px solid #2a2a4a;
            font-size: 11px;
        }
        
        .activity-time { color: #666; }
        .activity-agent { color: #00ff88; }
        .activity-action { color: #aaa; }
        
        /* Controls */
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .btn {
            background: linear-gradient(180deg, #4a4a6a, #3a3a5a);
            border: 2px solid #6a6a9a;
            color: #eee;
            padding: 10px 20px;
            font-family: inherit;
            cursor: pointer;
            font-size: 12px;
        }
        
        .btn:hover {
            background: linear-gradient(180deg, #5a5a7a, #4a4a6a);
        }
        
        .btn.green { border-color: #00ff88; color: #00ff88; }
        .btn.red { border-color: #ff4444; color: #ff4444; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏢 AI OFFICE</h1>
            <div class="stats-bar">
                <div class="stat">
                    <div class="stat-value" id="stat-queue">0</div>
                    <div class="stat-label">Queue</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="stat-active">0</div>
                    <div class="stat-label">Active</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="stat-completed">0</div>
                    <div class="stat-label">Done</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="stat-tokens">0</div>
                    <div class="stat-label">Tokens</div>
                </div>
            </div>
        </header>
        
        <div class="office">
            <div class="floor"></div>
            <div class="desk-row" id="workstations">
                <!-- Workstations will be rendered here -->
            </div>
        </div>
        
        <div class="activity-panel">
            <div class="activity-title">📊 Activity Log</div>
            <div id="activity-log">
                <!-- Activity entries -->
            </div>
        </div>
        
        <div class="controls">
            <button class="btn green" onclick="refresh()">🔄 Refresh</button>
            <button class="btn" onclick="createRequest()">➕ New Request</button>
            <button class="btn" onclick="showQueue()">📋 Queue</button>
        </div>
    </div>
    
    <script>
        const agentConfig = [
            { id: 'lead', name: 'Lead', role: 'lead', x: 0 },
            { id: 'frontend-1', name: 'Frontend', role: 'frontend', x: 1 },
            { id: 'backend-1', name: 'Backend', role: 'backend', x: 2 },
            { id: 'qa-1', name: 'QA', role: 'qa', x: 3 },
            { id: 'content-1', name: 'Content', role: 'content', x: 4 }
        ];
        
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                return await response.json();
            } catch (e) {
                return { agents: {}, queue_size: 0, activity_log: [] };
            }
        }
        
        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                return await response.json();
            } catch (e) {
                return {};
            }
        }
        
        function renderWorkstations(data) {
            const container = document.getElementById('workstations');
            container.innerHTML = '';
            
            const agents = data.agents || {};
            
            agentConfig.forEach(agent => {
                const info = agents[agent.id] || {};
                const status = info.status || 'idle';
                const task = info.current_task || '';
                
                const div = document.createElement('div');
                div.className = 'workstation';
                div.innerHTML = `
                    <div class="pc">
                        <div class="pc-screen ${status === 'working' ? 'active' : ''}"></div>
                    </div>
                    <div class="pc-stand"></div>
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status ${status}">${status.toUpperCase()}</div>
                    ${task ? `<div class="agent-status waiting">${task.substring(0, 15)}...</div>` : ''}
                `;
                container.appendChild(div);
            });
        }
        
        function renderActivity(log) {
            const container = document.getElementById('activity-log');
            container.innerHTML = '';
            
            (log || []).forEach(entry => {
                const div = document.createElement('div');
                div.className = 'activity-entry';
                div.innerHTML = `
                    <span class="activity-time">[${entry.timestamp}]</span>
                    <span class="activity-agent">${entry.agent}:</span>
                    <span class="activity-action">${entry.action} ${entry.detail || ''}</span>
                `;
                container.appendChild(div);
            });
        }
        
        async function updateDashboard() {
            const status = await fetchStatus();
            const stats = await fetchStats();
            
            // Update stats
            document.getElementById('stat-queue').textContent = status.queue_size || 0;
            document.getElementById('stat-active').textContent = 
                Object.values(status.agents || {}).filter(a => a.status === 'working').length;
            document.getElementById('stat-completed').textContent = stats.completed || 0;
            
            let totalTokens = 0;
            Object.values(status.agents || {}).forEach(a => {
                totalTokens += a.tokens_used || 0;
            });
            document.getElementById('stat-tokens').textContent = totalTokens;
            
            // Update workstations
            renderWorkstations(status);
            
            // Update activity
            renderActivity(status.activity_log);
        }
        
        async function refresh() {
            await updateDashboard();
        }
        
        async function createRequest() {
            const title = prompt('Request title:');
            if (!title) return;
            
            const desc = prompt('Description:');
            if (!desc) return;
            
            const type = prompt('Type (feature/bugfix/content/docs):') || 'feature';
            
            await fetch('/api/requests', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    title, description: desc, type, priority: 3
                })
            });
            
            alert('Request created!');
            refresh();
        }
        
        async function showQueue() {
            alert('Check /queue endpoint for full queue view');
        }
        
        // Auto-refresh
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
```

## Service Configuration

```bash
# Create service
sudo tee /etc/systemd/system/ai-office-dashboard.service << 'EOF'
[Unit]
Description=AI Office Dashboard
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/ai-office
ExecStart=/opt/ai-office/venv/bin/python dashboard/server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-office-dashboard
sudo systemctl start ai-office-dashboard
```

## Access

```
Dashboard: http://<JETSON_IP>:9000
```

## Features

- **Real-time Agent Status**: See who is working
- **Task Display**: Current task for each agent
- **Activity Log**: Live feed of all actions
- **Statistics**: Queue size, completed tasks, token usage
- **Controls**: Create requests, refresh view

## Next Steps

- [07-activity](./07-activity.md) - Activity logging system
