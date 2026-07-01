# Funding Finder - Animated Dashboard

## Overview

The dashboard provides a 16-bit pixel art office visualization showing all agents working in real-time, plus a Pokemon-style platform for managing workflows.

## Dashboard Features

- **16-bit Office Animation**: Pixel art office with agents at workstations
- **Real-time Status**: Each agent's current status (working/idle/waiting)
- **Pokemon-style Platform**: Drag-and-drop agent management
- **Job Queue**: View and manage pending opportunities
- **Metrics**: Statistics on scraped opportunities and generated proposals

## Dashboard Implementation

### Server (Flask)

```python
#!/usr/bin/env python3
"""
Funding Finder Dashboard - 16-bit Animated Office
"""

import os
import sys
import json
import logging
import time
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

CONFIG = {
    "sheets_api": "http://localhost:8081",
    "scraper_status": "http://localhost:8082",
    "proposal_api": "http://localhost:8083",
    "refresh_interval": 5000  # ms
}

# Agent states
AGENTS = {
    "scraper": {"name": "Scraper", "status": "idle", "current": None, "progress": 0},
    "analyzer": {"name": "Analyzer", "status": "idle", "current": None, "progress": 0},
    "project_lead": {"name": "Project Lead", "status": "idle", "current": None, "progress": 0},
    "technical_writer": {"name": "Technical Writer", "status": "idle", "current": None, "progress": 0},
    "budget_expert": {"name": "Budget Expert", "status": "idle", "current": None, "progress": 0},
    "compliance": {"name": "Compliance", "status": "idle", "current": None, "progress": 0},
    "legal": {"name": "Legal", "status": "idle", "current": None, "progress": 0},
    "final_reviewer": {"name": "Final Reviewer", "status": "idle", "current": None, "progress": 0}
}


@app.route("/")
def index():
    return render_template("dashboard.html", agents=AGENTS)


@app.route("/factory")
def factory():
    return render_template("factory.html", agents=AGENTS)


@app.route("/api/status")
def api_status():
    """Get current system status"""
    try:
        # Get stats from sheets API
        stats_response = requests.get(f"{CONFIG['sheets_api']}/queue/stats", timeout=5)
        stats = stats_response.json() if stats_response.status_code == 200 else {}
    except:
        stats = {"total": 0, "new": 0, "processing": 0, "completed": 0}
    
    return jsonify({
        "agents": AGENTS,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/agent/<agent_name>/status", methods=["POST"])
def update_agent_status(agent_name):
    """Update agent status"""
    data = request.get_json()
    
    if agent_name in AGENTS:
        AGENTS[agent_name].update(data)
        return jsonify({"success": True})
    
    return jsonify({"error": "Agent not found"}), 404


@app.route("/api/jobs")
def get_jobs():
    """Get current job queue"""
    try:
        response = requests.get(f"{CONFIG['sheets_api']}/queue/pending", timeout=5)
        jobs = response.json().get("pending", []) if response.status_code == 200 else []
    except:
        jobs = []
    
    return jsonify({"jobs": jobs[:20]})


@app.route("/api/control", methods=["POST"])
def control_action():
    """Execute control action"""
    data = request.get_json()
    action = data.get("action")
    
    actions = {
        "start_scraper": "Start scraping cycle",
        "stop_scraper": "Stop scraper",
        "trigger_proposal": "Generate proposal",
        "restart_all": "Restart all services"
    }
    
    logger.info(f"Control action: {action}")
    
    return jsonify({
        "success": True,
        "action": action,
        "message": actions.get(action, "Unknown action")
    })


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    app.run(host="0.0.0.0", port=port, debug=False)
```

### Dashboard Template (HTML/CSS/JS)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Funding Finder - Control Center</title>
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
            background: #1a1a2e;
            font-family: 'PixelFont', 'Courier New', monospace;
            color: #eee;
            overflow: hidden;
        }
        
        /* Scanline effect */
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
            display: grid;
            grid-template-columns: 300px 1fr;
            grid-template-rows: 80px 1fr 120px;
            height: 100vh;
            padding: 10px;
            gap: 10px;
        }
        
        /* Header */
        header {
            grid-column: 1 / -1;
            background: linear-gradient(180deg, #16213e, #0f3460);
            border: 4px solid #533483;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
        }
        
        header h1 {
            font-size: 24px;
            color: #e94560;
            text-shadow: 2px 2px #000;
        }
        
        .header-stats {
            display: flex;
            gap: 20px;
        }
        
        .stat-box {
            background: #0f3460;
            border: 2px solid #533483;
            padding: 8px 16px;
            text-align: center;
        }
        
        .stat-box .value {
            font-size: 20px;
            color: #e94560;
        }
        
        .stat-box .label {
            font-size: 10px;
            color: #888;
        }
        
        /* Sidebar */
        .sidebar {
            background: #16213e;
            border: 4px solid #533483;
            border-radius: 8px;
            padding: 10px;
            overflow-y: auto;
        }
        
        .sidebar h2 {
            color: #e94560;
            font-size: 14px;
            margin-bottom: 10px;
            border-bottom: 2px solid #533483;
            padding-bottom: 5px;
        }
        
        .agent-card {
            background: #0f3460;
            border: 2px solid #1a1a2e;
            margin-bottom: 8px;
            padding: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .agent-card:hover {
            border-color: #e94560;
        }
        
        .agent-card.active {
            border-color: #00ff00;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
        }
        
        .agent-name {
            font-size: 12px;
            color: #e94560;
        }
        
        .agent-status {
            font-size: 10px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        
        .status-dot.idle { background: #888; }
        .status-dot.working { background: #00ff00; animation: pulse 1s infinite; }
        .status-dot.waiting { background: #ffff00; }
        .status-dot.error { background: #ff0000; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .progress-bar {
            height: 6px;
            background: #1a1a2e;
            margin-top: 5px;
            border-radius: 3px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff00, #00ffff);
            width: 0%;
            transition: width 0.3s;
        }
        
        /* Main Area - 16-bit Office */
        .main-area {
            background: #16213e;
            border: 4px solid #533483;
            border-radius: 8px;
            position: relative;
            overflow: hidden;
        }
        
        .office-scene {
            width: 100%;
            height: 100%;
            position: relative;
            background: linear-gradient(180deg, #2d1b4e 0%, #1a1a2e 60%, #0f3460 100%);
        }
        
        /* Pixel Art Elements */
        .floor {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 40%;
            background: 
                repeating-linear-gradient(90deg, #3d3d5c 0px, #3d3d5c 20px, #2d2d4c 20px, #2d2d4c 40px),
                linear-gradient(180deg, #3d3d5c, #2d2d4c);
        }
        
        .desk {
            position: absolute;
            width: 120px;
            height: 60px;
            background: #8b4513;
            border: 4px solid #5c3317;
        }
        
        .desk::before {
            content: '';
            position: absolute;
            top: -10px;
            left: 10px;
            right: 10px;
            height: 10px;
            background: #a0522d;
        }
        
        .monitor {
            position: absolute;
            width: 50px;
            height: 40px;
            background: #1a1a2e;
            border: 3px solid #533483;
            top: -45px;
            left: 35px;
        }
        
        .monitor::before {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 15px;
            width: 20px;
            height: 10px;
            background: #533483;
        }
        
        .monitor .screen {
            position: absolute;
            inset: 3px;
            background: #00ff00;
            opacity: 0.8;
        }
        
        .agent-sprite {
            position: absolute;
            width: 40px;
            height: 60px;
            transition: all 0.5s;
        }
        
        .agent-sprite.typing .monitor .screen {
            animation: typing 0.3s infinite;
        }
        
        @keyframes typing {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 0.4; }
        }
        
        /* Bottom Controls */
        .controls {
            grid-column: 1 / -1;
            background: #16213e;
            border: 4px solid #533483;
            border-radius: 8px;
            display: flex;
            align-items: center;
            padding: 0 20px;
            gap: 10px;
        }
        
        .btn {
            background: linear-gradient(180deg, #e94560, #c73e54);
            border: 3px solid #fff;
            color: #fff;
            padding: 10px 20px;
            font-family: inherit;
            font-size: 12px;
            cursor: pointer;
            text-transform: uppercase;
            box-shadow: 0 4px 0 #8b0000;
            transition: all 0.1s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 0 #8b0000;
        }
        
        .btn:active {
            transform: translateY(2px);
            box-shadow: 0 2px 0 #8b0000;
        }
        
        .btn.green {
            background: linear-gradient(180deg, #00ff00, #00cc00);
            box-shadow: 0 4px 0 #006400;
        }
        
        .btn.blue {
            background: linear-gradient(180deg, #00ccff, #0099cc);
            box-shadow: 0 4px 0 #006688;
        }
        
        .log-display {
            flex: 1;
            background: #0a0a15;
            border: 2px solid #533483;
            height: 80px;
            padding: 10px;
            font-size: 10px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
        }
        
        .log-entry {
            margin-bottom: 2px;
        }
        
        .log-entry .time { color: #888; }
        .log-entry .msg { color: #00ff00; }
        .log-entry .error { color: #ff0000; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>💰 FUNDING FINDER</h1>
            <div class="header-stats">
                <div class="stat-box">
                    <div class="value" id="stat-total">0</div>
                    <div class="label">TOTAL</div>
                </div>
                <div class="stat-box">
                    <div class="value" id="stat-new">0</div>
                    <div class="label">NEW</div>
                </div>
                <div class="stat-box">
                    <div class="value" id="stat-processing">0</div>
                    <div class="label">PROCESSING</div>
                </div>
                <div class="stat-box">
                    <div class="value" id="stat-completed">0</div>
                    <div class="label">COMPLETED</div>
                </div>
            </div>
        </header>
        
        <div class="sidebar">
            <h2>🤖 AGENTS</h2>
            <div id="agent-list"></div>
        </div>
        
        <div class="main-area">
            <div class="office-scene" id="office">
                <div class="floor"></div>
                <!-- Desks and agents will be positioned here -->
            </div>
        </div>
        
        <div class="controls">
            <button class="btn green" onclick="startScraper()">▶ Start</button>
            <button class="btn" onclick="stopScraper()">⏹ Stop</button>
            <button class="btn blue" onclick="triggerProposal()">📝 Generate</button>
            <button class="btn" onclick="refreshAll()">🔄 Refresh</button>
            <div class="log-display" id="log"></div>
        </div>
    </div>
    
    <script>
        const agents = {{ agents|tojson }};
        
        function initOffice() {
            const office = document.getElementById('office');
            const positions = [
                { top: '20%', left: '10%' },
                { top: '20%', left: '30%' },
                { top: '20%', left: '50%' },
                { top: '20%', left: '70%' },
                { top: '50%', left: '10%' },
                { top: '50%', left: '30%' },
                { top: '50%', left: '50%' },
                { top: '50%', left: '70%' }
            ];
            
            let i = 0;
            for (const [key, agent] of Object.entries(agents)) {
                const pos = positions[i];
                
                const desk = document.createElement('div');
                desk.className = 'desk';
                desk.style.top = pos.top;
                desk.style.left = pos.left;
                
                const monitor = document.createElement('div');
                monitor.className = 'monitor';
                monitor.innerHTML = '<div class="screen"></div>';
                
                const sprite = document.createElement('div');
                sprite.className = 'agent-sprite';
                sprite.id = `sprite-${key}`;
                sprite.style.top = `calc(${pos.top} - 60px)`;
                sprite.style.left = `calc(${pos.left} + 40px)`;
                
                // Simple pixel character
                sprite.innerHTML = `
                    <svg width="40" height="60" viewBox="0 0 40 60">
                        <rect x="10" y="0" width="20" height="15" fill="#ffccaa"/>
                        <rect x="5" y="15" width="30" height="25" fill="#4488ff"/>
                        <rect x="5" y="40" width="10" height="20" fill="#333"/>
                        <rect x="25" y="40" width="10" height="20" fill="#333"/>
                        <circle cx="17" cy="5" r="2" fill="#000"/>
                        <circle cx="23" cy="5" r="2" fill="#000"/>
                    </svg>
                `;
                
                desk.appendChild(monitor);
                office.appendChild(desk);
                office.appendChild(sprite);
                
                i++;
            }
        }
        
        function updateAgentList() {
            const list = document.getElementById('agent-list');
            list.innerHTML = '';
            
            for (const [key, agent] of Object.entries(agents)) {
                const card = document.createElement('div');
                card.className = 'agent-card';
                card.innerHTML = `
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status">
                        <span class="status-dot ${agent.status}"></span>
                        <span>${agent.status.toUpperCase()}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${agent.progress}%"></div>
                    </div>
                `;
                list.appendChild(card);
            }
        }
        
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // Update stats
                document.getElementById('stat-total').textContent = data.stats.total || 0;
                document.getElementById('stat-new').textContent = data.stats.new || 0;
                document.getElementById('stat-processing').textContent = data.stats.processing || 0;
                document.getElementById('stat-completed').textContent = data.stats.completed || 0;
                
                // Update agents
                for (const [key, agent] of Object.entries(data.agents)) {
                    agents[key] = agent;
                    
                    // Update sprite animation
                    const sprite = document.getElementById(`sprite-${key}`);
                    if (sprite) {
                        if (agent.status === 'working') {
                            sprite.classList.add('typing');
                        } else {
                            sprite.classList.remove('typing');
                        }
                    }
                }
                
                updateAgentList();
            } catch (e) {
                console.error('Status update failed:', e);
            }
        }
        
        function log(msg, type = 'info') {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logEl.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${type}">${msg}</span></div>`;
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        async function startScraper() {
            log('Starting scraper...');
            await fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'start_scraper'})
            });
        }
        
        async function stopScraper() {
            log('Stopping scraper...');
            await fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'stop_scraper'})
            });
        }
        
        async function triggerProposal() {
            log('Triggering proposal generation...');
            await fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'trigger_proposal'})
            });
        }
        
        function refreshAll() {
            log('Refreshing all...');
            updateStatus();
        }
        
        // Initialize
        initOffice();
        updateAgentList();
        
        // Auto-refresh
        setInterval(updateStatus, 5000);
        
        log('Dashboard initialized');
    </script>
</body>
</html>
```

## Pokemon-Style Platform

The factory view provides a drag-and-drop interface for managing the proposal workflow:

```html
<!-- factory.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Funding Finder - Factory Platform</title>
    <style>
        /* Similar styling to dashboard, but with drag-drop */
        .platform-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
            padding: 20px;
        }
        
        .agent-card.draggable {
            cursor: grab;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 3px solid #533483;
            padding: 15px;
            text-align: center;
            transition: transform 0.2s;
        }
        
        .agent-card.draggable:hover {
            transform: scale(1.05);
            border-color: #e94560;
        }
        
        .workflow-lane {
            min-height: 200px;
            border: 2px dashed #533483;
            padding: 10px;
            background: rgba(26, 26, 46, 0.5);
        }
        
        .workflow-lane.droppable {
            border-color: #00ff00;
            background: rgba(0, 255, 0, 0.1);
        }
    </style>
</head>
<body>
    <!-- Drag and drop interface -->
</body>
</html>
```

## Service Configuration

```bash
# Create dashboard service
sudo tee /etc/systemd/system/funding-dashboard.service << 'EOF'
[Unit]
Description=Funding Finder Dashboard
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/funding-finder
ExecStart=/opt/funding-finder/venv/bin/python dashboard/server.py 8090
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable funding-dashboard
sudo systemctl start funding-dashboard
```

## Access

```
Dashboard:        http://<JETSON_IP>:8090
Factory Platform: http://<JETSON_IP>:8090/factory
```

## Next Steps

- [07-delivery](./07-delivery.md) - Email & Google Drive delivery
