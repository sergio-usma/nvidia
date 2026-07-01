# Freelance Hunter - Dashboard

## Overview

The Freelance Hunter Dashboard provides real-time visualization of job opportunities, matches, proposals, and agent activity. It features a pixel-art interface with live metrics.

## Dashboard Implementation

```python
#!/usr/bin/env python3
"""
Freelance Hunter Dashboard
Runs on port 8096
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

CONFIG = {
    "data_dir": "/opt/freelance-hunter/data",
    "port": 8096,
    "platforms": ["upwork", "freelancer", "remoteok", "weworkremotely", "linkedin", "toptal"]
}

DATA_DIR = Path(CONFIG["data_dir"])
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ==================== DATA LOADING ====================

def load_jobs() -> list:
    """Load job data"""
    jobs_file = DATA_DIR / "jobs" / "latest.json"
    
    if not jobs_file.exists():
        return []
    
    with open(jobs_file) as f:
        return json.load(f)


def load_matches() -> list:
    """Load match data"""
    # Load from jobs with match scores
    jobs = load_jobs()
    
    matches = []
    for job in jobs:
        if job.get("match_score", 0) > 0:
            matches.append({
                "job_id": job.get("id"),
                "title": job.get("title"),
                "platform": job.get("platform"),
                "url": job.get("url"),
                "budget": job.get("budget"),
                "score": job.get("match_score", 0),
                "skills": job.get("skills", [])
            })
    
    return sorted(matches, key=lambda x: x.get("score", 0), reverse=True)


def load_proposals() -> list:
    """Load proposals"""
    proposals_file = DATA_DIR / "proposals" / "index.json"
    
    if not proposals_file.exists():
        return []
    
    with open(proposals_file) as f:
        data = json.load(f)
        return data.get("proposals", [])


def load_stats() -> dict:
    """Load scheduler stats"""
    stats_file = DATA_DIR / "stats.json"
    
    if not stats_file.exists():
        return {"cycle": 0}
    
    with open(stats_file) as f:
        return json.load(f)


def load_notifications() -> list:
    """Load recent notifications"""
    notif_file = DATA_DIR / "notifications" / "log.json"
    
    if not notif_file.exists():
        return []
    
    with open(notif_file) as f:
        return json.load(f)


# ==================== API ROUTES ====================

@app.route("/")
def index():
    """Main dashboard"""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """Get jobs data"""
    platform = request.args.get("platform")
    jobs = load_jobs()
    
    if platform:
        jobs = [j for j in jobs if j.get("platform") == platform]
    
    return jsonify({
        "count": len(jobs),
        "jobs": jobs[:100]
    })


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    """Get specific job"""
    jobs = load_jobs()
    job = next((j for j in jobs if j.get("id") == job_id), None)
    
    if not job:
        return jsonify({"error": "Not found"}), 404
    
    return jsonify(job)


@app.route("/api/match", methods=["GET"])
def get_matches():
    """Get job matches"""
    matches = load_matches()
    
    limit = request.args.get("limit", 20, type=int)
    
    return jsonify({
        "count": len(matches),
        "matches": matches[:limit]
    })


@app.route("/api/hot", methods=["GET"])
def get_hot_jobs():
    """Get hot jobs (high match)"""
    matches = load_matches()
    
    threshold = request.args.get("threshold", 0.7, type=float)
    
    hot = [m for m in matches if m.get("score", 0) >= threshold]
    
    return jsonify({
        "count": len(hot),
        "jobs": hot[:10]
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get platform stats"""
    stats = load_stats()
    proposals = load_proposals()
    
    # Count by status
    status_counts = {}
    for p in proposals:
        status = p.get("status", "draft")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Platform counts
    jobs = load_jobs()
    platform_counts = {}
    for job in jobs:
        platform = job.get("platform", "unknown")
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    return jsonify({
        "cycle": stats.get("cycle", 0),
        "total_jobs": len(jobs),
        "total_matches": len(load_matches()),
        "total_proposals": len(proposals),
        "status_counts": status_counts,
        "platform_counts": platform_counts,
        "last_run": stats.get("timestamp", "")
    })


@app.route("/api/proposals", methods=["GET"])
def get_proposals():
    """Get proposals"""
    proposals = load_proposals()
    
    status = request.args.get("status")
    
    if status:
        proposals = [p for p in proposals if p.get("status") == status]
    
    return jsonify({
        "count": len(proposals),
        "proposals": proposals
    })


@app.route("/api/agents", methods=["GET"])
def get_agents():
    """Get agent status"""
    return jsonify({
        "lead": {"state": "idle", "task": None},
        "scraper": {"state": "idle", "task": None},
        "analyzer": {"state": "idle", "task": None},
        "writer": {"state": "idle", "task": None},
        "qa": {"state": "idle", "task": None},
        "scheduler": {"state": "running", "task": "monitoring"},
        "notifier": {"state": "idle", "task": None},
        "researcher": {"state": "idle", "task": None},
        "archiver": {"state": "idle", "task": None},
        "manager": {"state": "idle", "task": None}
    })


@app.route("/api/agents/<agent_id>/status", methods=["POST"])
def update_agent(agent_id):
    """Update agent status"""
    data = request.get_json()
    
    return jsonify({"status": "updated"})


@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Get notification log"""
    notifications = load_notifications()
    
    return jsonify({
        "count": len(notifications),
        "notifications": notifications[-20:]
    })


@app.route("/api/activity", methods=["POST"])
def log_activity():
    """Log agent activity"""
    data = request.get_json()
    
    return jsonify({"status": "logged"})


# ==================== DASHBOARD HTML ====================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Freelance Hunter - AI Job Discovery</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --accent: #ff6b35;
            --accent-secondary: #00ff9f;
            --text: #e0e0e0;
            --text-dim: #888;
            --success: #00ff88;
            --warning: #ffcc00;
            --danger: #ff4757;
            --purple: #a855f7;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Roboto', sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            background-image: 
                radial-gradient(ellipse at top, #1a1a2e 0%, transparent 50%),
                linear-gradient(180deg, #0a0a0f 0%, #12121a 100%);
        }
        
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
            padding: 20px 30px;
            border-bottom: 3px solid var(--accent);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-family: 'Press Start 2P', cursive;
            font-size: 16px;
            color: var(--accent);
            text-shadow: 0 0 20px var(--accent);
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .header h1 span {
            color: var(--accent-secondary);
        }
        
        .status-badge {
            background: var(--bg-card);
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid #333;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 10px var(--success);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.9); }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            padding: 25px;
        }
        
        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #222;
            transition: all 0.3s;
        }
        
        .card:hover {
            border-color: var(--accent);
            box-shadow: 0 0 30px rgba(255, 107, 53, 0.1);
        }
        
        .card h2 {
            font-family: 'Press Start 2P', cursive;
            font-size: 11px;
            color: var(--accent-secondary);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        
        .stat {
            text-align: center;
            padding: 15px;
            background: rgba(255, 107, 53, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(255, 107, 53, 0.2);
        }
        
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: var(--accent);
            text-shadow: 0 0 10px rgba(255, 107, 53, 0.5);
        }
        
        .stat-label {
            font-size: 10px;
            color: var(--text-dim);
            margin-top: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .platform-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }
        
        .platform {
            text-align: center;
            padding: 12px 8px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            transition: all 0.2s;
        }
        
        .platform:hover {
            background: rgba(255, 107, 53, 0.1);
        }
        
        .platform-icon {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .platform-name {
            font-size: 9px;
            font-weight: bold;
        }
        
        .platform-count {
            font-size: 11px;
            color: var(--accent);
        }
        
        .agent-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
        }
        
        .agent {
            text-align: center;
            padding: 12px 5px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            transition: all 0.2s;
        }
        
        .agent:hover {
            background: rgba(0, 255, 159, 0.1);
        }
        
        .agent-icon {
            font-size: 20px;
            margin-bottom: 5px;
        }
        
        .agent-name {
            font-size: 8px;
            font-weight: bold;
            color: var(--text-dim);
        }
        
        .agent-status {
            font-size: 8px;
            color: var(--success);
            margin-top: 3px;
        }
        
        .agent-status.busy {
            color: var(--warning);
        }
        
        .job-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 350px;
            overflow-y: auto;
        }
        
        .job-item {
            padding: 12px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            border-left: 3px solid var(--accent);
            transition: all 0.2s;
        }
        
        .job-item:hover {
            background: rgba(255, 107, 53, 0.1);
        }
        
        .job-item.hot {
            border-left-color: var(--danger);
        }
        
        .job-item .title {
            font-weight: bold;
            font-size: 13px;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .job-item .meta {
            font-size: 11px;
            color: var(--text-dim);
            display: flex;
            gap: 10px;
        }
        
        .job-item .score {
            font-weight: bold;
            color: var(--accent);
        }
        
        .job-item .score.hot {
            color: var(--danger);
        }
        
        .proposal-stats {
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        
        .proposal-stat {
            padding: 15px;
        }
        
        .proposal-stat .value {
            font-size: 24px;
            font-weight: bold;
        }
        
        .proposal-stat .label {
            font-size: 10px;
            color: var(--text-dim);
        }
        
        .proposal-stat.draft .value { color: var(--text-dim); }
        .proposal-stat.sent .value { color: var(--warning); }
        .proposal-stat.won .value { color: var(--success); }
        .proposal-stat.lost .value { color: var(--danger); }
        
        .chart-container {
            height: 200px;
            position: relative;
        }
        
        .btn {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
            transition: all 0.2s;
        }
        
        .btn:hover {
            background: var(--accent-secondary);
            transform: translateY(-2px);
        }
        
        .last-updated {
            font-size: 11px;
            color: var(--text-dim);
            text-align: center;
            margin-top: 20px;
            padding-bottom: 20px;
        }
        
        .progress-bar {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .progress-bar .fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
            border-radius: 4px;
            transition: width 0.5s;
        }
        
        ::-webkit-scrollbar {
            width: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-dark);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--accent);
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 FREELANCE <span>HUNTER</span></h1>
        <div class="status-badge">
            <div class="status-dot"></div>
            <span id="cycle-info">Cycle: 0</span>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>📊 OVERVIEW</h2>
            <div class="stat-grid">
                <div class="stat">
                    <div class="stat-value" id="total-jobs">0</div>
                    <div class="stat-label">Total Jobs</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="hot-jobs">0</div>
                    <div class="stat-label">Hot Matches</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="total-proposals">0</div>
                    <div class="stat-label">Proposals</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="win-rate">0%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>💼 PLATFORMS</h2>
            <div class="platform-grid" id="platform-grid"></div>
        </div>
        
        <div class="card">
            <h2>🤖 AI AGENTS</h2>
            <div class="agent-grid" id="agent-grid"></div>
        </div>
        
        <div class="card">
            <h2>🔥 HOT JOBS</h2>
            <div class="job-list" id="hot-jobs-list"></div>
        </div>
        
        <div class="card">
            <h2>📝 PROPOSALS</h2>
            <div class="proposal-stats">
                <div class="proposal-stat draft">
                    <div class="value" id="proposals-draft">0</div>
                    <div class="label">Draft</div>
                </div>
                <div class="proposal-stat sent">
                    <div class="value" id="proposals-sent">0</div>
                    <div class="label">Sent</div>
                </div>
                <div class="proposal-stat won">
                    <div class="value" id="proposals-won">0</div>
                    <div class="label">Won</div>
                </div>
                <div class="proposal-stat lost">
                    <div class="value" id="proposals-lost">0</div>
                    <div class="label">Lost</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📈 ACTIVITY</h2>
            <div class="chart-container">
                <canvas id="activity-chart"></canvas>
            </div>
        </div>
    </div>
    
    <div class="last-updated" id="last-updated">Last updated: --</div>
    
    <script>
        const platforms = [
            {id: 'upwork', icon: '💼', name: 'Upwork'},
            {id: 'freelancer', icon: '🎯', name: 'Freelancer'},
            {id: 'remoteok', icon: '🌴', name: 'RemoteOK'},
            {id: 'weworkremotely', icon: '🏠', name: 'WWR'},
            {id: 'linkedin', icon: '💼', name: 'LinkedIn'},
            {id: 'toptal', icon: '⭐', name: 'Toptal'}
        ];
        
        const agents = [
            {id: 'lead', icon: '👑', name: 'Lead'},
            {id: 'scraper', icon: '🔍', name: 'Scraper'},
            {id: 'analyzer', icon: '📊', name: 'Analyzer'},
            {id: 'writer', icon: '✍️', name: 'Writer'},
            {id: 'scheduler', icon: '⏰', name: 'Scheduler'},
            {id: 'notifier', icon: '🔔', name: 'Notifier'},
            {id: 'researcher', icon: '🔬', name: 'Researcher'},
            {id: 'qa', icon: '✅', name: 'QA'},
            {id: 'archiver', icon: '📦', name: 'Archiver'},
            {id: 'manager', icon: '📋', name: 'Manager'}
        ];
        
        let activityChart = null;
        
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                document.getElementById('total-jobs').textContent = data.total_jobs || 0;
                document.getElementById('total-proposals').textContent = data.total_proposals || 0;
                document.getElementById('cycle-info').textContent = `Cycle: ${data.cycle || 0}`;
                
                // Calculate win rate
                const sent = data.status_counts?.sent || 0;
                const won = data.status_counts?.won || 0;
                document.getElementById('win-rate').textContent = sent > 0 ? `${Math.round(won/sent*100)}%` : '0%';
                
                // Platform counts
                const platformGrid = document.getElementById('platform-grid');
                platformGrid.innerHTML = platforms.map(p => {
                    const count = data.platform_counts?.[p.id] || 0;
                    return `
                        <div class="platform">
                            <div class="platform-icon">${p.icon}</div>
                            <div class="platform-name">${p.name}</div>
                            <div class="platform-count">${count}</div>
                        </div>
                    `;
                }).join('');
                
                // Proposal stats
                const counts = data.status_counts || {};
                document.getElementById('proposals-draft').textContent = counts.draft || 0;
                document.getElementById('proposals-sent').textContent = counts.sent || 0;
                document.getElementById('proposals-won').textContent = counts.won || 0;
                document.getElementById('proposals-lost').textContent = counts.lost || 0;
                
            } catch(e) { console.error(e); }
        }
        
        async function loadHotJobs() {
            try {
                const res = await fetch('/api/hot?threshold=0.6');
                const data = await res.json();
                
                document.getElementById('hot-jobs').textContent = data.count || 0;
                
                const list = document.getElementById('hot-jobs-list');
                list.innerHTML = data.jobs?.slice(0, 8).map(j => `
                    <div class="job-item ${j.score > 0.8 ? 'hot' : ''}">
                        <div class="title">${j.title || 'Untitled'}</div>
                        <div class="meta">
                            <span>${j.platform || 'N/A'}</span>
                            <span>${j.budget || 'Negotiable'}</span>
                            <span class="score ${j.score > 0.8 ? 'hot' : ''}">${Math.round(j.score * 100)}%</span>
                        </div>
                    </div>
                `).join('') || '<div class="job-item">No hot jobs yet</div>';
                
            } catch(e) { console.error(e); }
        }
        
        async function loadAgents() {
            try {
                const res = await fetch('/api/agents');
                const data = await res.json();
                
                const grid = document.getElementById('agent-grid');
                grid.innerHTML = agents.map(a => {
                    const status = data[a.id] || {state: 'idle'};
                    const isBusy = status.state !== 'idle';
                    return `
                        <div class="agent">
                            <div class="agent-icon">${a.icon}</div>
                            <div class="agent-name">${a.name}</div>
                            <div class="agent-status ${isBusy ? 'busy' : ''}">${status.state}</div>
                        </div>
                    `;
                }).join('');
                
            } catch(e) { console.error(e); }
        }
        
        async function loadActivity() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                const ctx = document.getElementById('activity-chart').getContext('2d');
                
                if (activityChart) activityChart.destroy();
                
                activityChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Jobs', 'Matches', 'Proposals'],
                        datasets: [{
                            label: 'Today',
                            data: [
                                data.total_jobs || 0,
                                data.total_matches || 0,
                                data.total_proposals || 0
                            ],
                            backgroundColor: '#ff6b35',
                            borderRadius: 8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { display: false }, ticks: { color: '#888' } },
                            y: { grid: { color: '#222' }, ticks: { color: '#888' } }
                        }
                    }
                });
                
            } catch(e) { console.error(e); }
        }
        
        async function refresh() {
            document.getElementById('last-updated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
            await Promise.all([
                loadStats(),
                loadHotJobs(),
                loadAgents(),
                loadActivity()
            ]);
        }
        
        refresh();
        setInterval(refresh, 30000);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    logger.info(f"Starting Freelance Hunter Dashboard on port {CONFIG['port']}")
    app.run(host="0.0.0.0", port=CONFIG["port"], debug=False)
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Main dashboard |
| `/api/stats` | Platform statistics |
| `/api/jobs` | Job list |
| `/api/jobs/<id>` | Specific job |
| `/api/match` | Matched jobs |
| `/api/hot` | Hot jobs (high match) |
| `/api/proposals` | Proposal list |
| `/api/agents` | Agent status |
| `/api/notifications` | Notification log |

## Running the Dashboard

```bash
# Start dashboard
cd /opt/freelance-hunter
source venv/bin/activate
python dashboard/main.py

# Access at
http://jetson:8096
```

## Screenshots Description

- **Overview Card**: Total jobs, hot matches, proposals, win rate
- **Platforms Card**: Job counts per platform (Upwork, Freelancer, RemoteOK, etc.)
- **Agents Card**: 10 AI agents with live status
- **Hot Jobs Card**: Top matching jobs with scores
- **Proposals Card**: Draft/Sent/Won/Lost counts
- **Activity Chart**: Bar chart of today's activity

## Next Steps

- [10-discord](./10-discord.md) - Discord bot control
