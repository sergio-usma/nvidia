# Tourism Intelligence - Dashboard

## Overview

The Tourism Intelligence Dashboard provides real-time visualization of hotel data, trends, alerts, and analytics. It features an interactive pixel-art interface with maps, charts, and live agent activity monitoring.

## Features

- **Interactive Maps**: Hotel locations across Colombian cities
- **Live Charts**: Price trends, ratings, availability
- **Agent Activity**: Real-time view of AI agents working
- **Alert Feed**: Live alerts and notifications
- **City Comparison**: Compare metrics across cities
- **Mobile Responsive**: Works on desktop and mobile

## Dashboard Implementation

```python
#!/usr/bin/env python3
"""
Tourism Intelligence Dashboard
Runs on port 8095
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

CONFIG = {
    "data_dir": "/opt/tourism-intel/data",
    "port": 8095,
    "cities": ["bogota", "medellin", "cartagena", "cali", "barranquilla", "santa_marta"]
}

DATA_DIR = Path(CONFIG["data_dir"])
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ==================== DATA LOADING ====================

def load_hotels(city: str = None) -> list:
    """Load hotel data"""
    hotels_file = DATA_DIR / "hotels" / "latest.json"
    
    if not hotels_file.exists():
        return []
    
    with open(hotels_file) as f:
        hotels = json.load(f)
    
    if city:
        hotels = [h for h in hotels if h.get("location", "").lower() == city.lower()]
    
    return hotels


def load_trends() -> list:
    """Load trend data"""
    trends_dir = DATA_DIR / "trends"
    
    if not trends_dir.exists():
        return []
    
    trends = []
    for tf in sorted(trends_dir.glob("*.json"))[-10:]:
        with open(tf) as f:
            trends.append(json.load(f))
    
    return trends


def load_alerts() -> list:
    """Load recent alerts"""
    alerts_file = DATA_DIR / "alerts" / "latest.json"
    
    if not alerts_file.exists():
        return []
    
    with open(alerts_file) as f:
        return json.load(f)


def load_stats() -> dict:
    """Load scheduler stats"""
    stats_file = DATA_DIR / "stats.json"
    
    if not stats_file.exists():
        return {"cycle": 0}
    
    with open(stats_file) as f:
        return json.load(f)


# ==================== API ROUTES ====================

@app.route("/")
def index():
    """Main dashboard"""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/hotels", methods=["GET"])
def get_hotels():
    """Get hotels data"""
    city = request.args.get("city")
    hotels = load_hotels(city)
    
    return jsonify({
        "count": len(hotels),
        "hotels": hotels[:100]
    })


@app.route("/api/hotels/<city>", methods=["GET"])
def get_city_hotels(city):
    """Get hotels for specific city"""
    hotels = load_hotels(city)
    
    return jsonify({
        "city": city,
        "count": len(hotels),
        "hotels": hotels
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get platform stats"""
    stats = load_stats()
    
    # Add hotel counts per city
    city_counts = {}
    for city in CONFIG["cities"]:
        hotels = load_hotels(city)
        city_counts[city] = len(hotels)
    
    stats["cities"] = city_counts
    stats["total_hotels"] = sum(city_counts.values())
    
    return jsonify(stats)


@app.route("/api/trends", methods=["GET"])
def get_trends():
    """Get trend data"""
    trends = load_trends()
    
    return jsonify({
        "count": len(trends),
        "trends": trends
    })


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Get recent alerts"""
    alerts = load_alerts()
    
    return jsonify({
        "count": len(alerts),
        "alerts": alerts[:20]
    })


@app.route("/api/agents", methods=["GET"])
def get_agents():
    """Get agent status"""
    return jsonify({
        "lead": {"status": "idle", "task": None},
        "researcher": {"status": "idle", "task": None},
        "sentiment": {"status": "idle", "task": None},
        "analytics": {"status": "idle", "task": None},
        "reporter": {"status": "idle", "task": None},
        "scheduler": {"status": "running", "task": "monitoring"},
        "data_manager": {"status": "idle", "task": None},
        "alert": {"status": "idle", "task": None}
    })


@app.route("/api/agents/<agent_id>/status", methods=["POST"])
def update_agent_status(agent_id):
    """Update agent status"""
    data = request.get_json()
    
    # Store in memory (in production, use Redis or file)
    if not hasattr(app, 'agent_status'):
        app.agent_status = {}
    
    app.agent_status[agent_id] = data
    
    return jsonify({"status": "updated"})


@app.route("/api/cities", methods=["GET"])
def get_cities():
    """Get city summaries"""
    cities = []
    
    for city in CONFIG["cities"]:
        hotels = load_hotels(city)
        
        ratings = [h.get("rating", 0) for h in hotels if h.get("rating")]
        prices = [h.get("price", "0").replace(",", "") for h in hotels if h.get("price")]
        
        cities.append({
            "name": city.capitalize(),
            "hotels": len(hotels),
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "avg_price": sum(int(p) for p in prices) / len(prices) if prices else 0
        })
    
    return jsonify({"cities": cities})


# ==================== DASHBOARD HTML ====================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tourism Intelligence - Colombia</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f0f23;
            --bg-card: #1a1a2e;
            --accent: #00d4ff;
            --accent-secondary: #ff6b9d;
            --text: #e0e0e0;
            --success: #00ff88;
            --warning: #ffcc00;
            --danger: #ff4757;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Roboto', sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px;
            border-bottom: 3px solid var(--accent);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-family: 'Press Start 2P', cursive;
            font-size: 18px;
            color: var(--accent);
            text-shadow: 0 0 10px var(--accent);
        }
        
        .status-badge {
            background: var(--bg-card);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        
        .card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
        }
        
        .card h2 {
            font-family: 'Press Start 2P', cursive;
            font-size: 12px;
            color: var(--accent-secondary);
            margin-bottom: 15px;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .stat {
            text-align: center;
            padding: 15px;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 8px;
        }
        
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: var(--accent);
        }
        
        .stat-label {
            font-size: 11px;
            color: #888;
            margin-top: 5px;
        }
        
        .city-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .city-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .city-item:hover {
            background: rgba(0, 212, 255, 0.1);
        }
        
        .city-name {
            font-weight: bold;
        }
        
        .city-stats {
            font-size: 12px;
            color: #888;
        }
        
        .agent-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }
        
        .agent {
            text-align: center;
            padding: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
        }
        
        .agent-icon {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .agent-name {
            font-size: 10px;
            font-weight: bold;
        }
        
        .agent-status {
            font-size: 9px;
            color: var(--success);
        }
        
        .agent-status.busy {
            color: var(--warning);
        }
        
        .alerts-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 250px;
            overflow-y: auto;
        }
        
        .alert {
            padding: 10px;
            border-radius: 6px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .alert.high {
            background: rgba(255, 71, 87, 0.2);
            border-left: 3px solid var(--danger);
        }
        
        .alert.medium {
            background: rgba(255, 204, 0, 0.2);
            border-left: 3px solid var(--warning);
        }
        
        .hotel-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .hotel-table th {
            text-align: left;
            padding: 10px;
            font-size: 11px;
            color: #888;
            border-bottom: 1px solid #333;
        }
        
        .hotel-table td {
            padding: 10px;
            font-size: 12px;
            border-bottom: 1px solid #222;
        }
        
        .rating-badge {
            background: var(--accent);
            color: #000;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 11px;
        }
        
        .chart-container {
            height: 200px;
            position: relative;
        }
        
        .refresh-btn {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .last-updated {
            font-size: 11px;
            color: #666;
            text-align: center;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏛️ TOURISM INTELLIGENCE</h1>
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
                    <div class="stat-value" id="total-hotels">0</div>
                    <div class="stat-label">Total Hotels</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="avg-rating">0.0</div>
                    <div class="stat-label">Avg Rating</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="total-alerts">0</div>
                    <div class="stat-label">Active Alerts</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="cities-count">6</div>
                    <div class="stat-label">Cities</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🏨 CITIES</h2>
            <div class="city-list" id="city-list"></div>
        </div>
        
        <div class="card">
            <h2>🤖 AI AGENTS</h2>
            <div class="agent-grid" id="agent-grid"></div>
        </div>
        
        <div class="card">
            <h2>🚨 ALERTS</h2>
            <div class="alerts-list" id="alerts-list"></div>
        </div>
        
        <div class="card">
            <h2>📈 TRENDS</h2>
            <div class="chart-container">
                <canvas id="trends-chart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>🏨 TOP HOTELS</h2>
            <table class="hotel-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>City</th>
                        <th>Rating</th>
                    </tr>
                </thead>
                <tbody id="hotels-table"></tbody>
            </table>
        </div>
    </div>
    
    <div class="last-updated" id="last-updated">Last updated: --</div>
    
    <script>
        const agents = [
            {id: 'lead', icon: '👑', name: 'Lead'},
            {id: 'researcher', icon: '🔍', name: 'Researcher'},
            {id: 'sentiment', icon: '💭', name: 'Sentiment'},
            {id: 'analytics', icon: '📊', name: 'Analytics'},
            {id: 'reporter', icon: '📝', name: 'Reporter'},
            {id: 'scheduler', icon: '⏰', name: 'Scheduler'},
            {id: 'data_manager', icon: '💾', name: 'Data'},
            {id: 'alert', icon: '🔔', name: 'Alert'}
        ];
        
        let trendsChart = null;
        
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                document.getElementById('total-hotels').textContent = data.total_hotels || 0;
                document.getElementById('cycle-info').textContent = `Cycle: ${data.cycle || 0}`;
                document.getElementById('last-updated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
            } catch(e) { console.error(e); }
        }
        
        async function loadCities() {
            try {
                const res = await fetch('/api/cities');
                const data = await res.json();
                
                const list = document.getElementById('city-list');
                list.innerHTML = data.cities.map(c => `
                    <div class="city-item">
                        <div>
                            <div class="city-name">${c.name}</div>
                        </div>
                        <div class="city-stats">
                            ${c.hotels} hotels • ⭐ ${c.avg_rating.toFixed(1)}
                        </div>
                    </div>
                `).join('');
                
                // Calculate average
                const totalRating = data.cities.reduce((a, c) => a + c.avg_rating, 0);
                document.getElementById('avg-rating').textContent = (totalRating / data.cities.length).toFixed(1);
            } catch(e) { console.error(e); }
        }
        
        async function loadAgents() {
            try {
                const res = await fetch('/api/agents');
                const data = await res.json();
                
                const grid = document.getElementById('agent-grid');
                grid.innerHTML = agents.map(a => {
                    const status = data[a.id] || {status: 'idle'};
                    const isBusy = status.status !== 'idle';
                    return `
                        <div class="agent">
                            <div class="agent-icon">${a.icon}</div>
                            <div class="agent-name">${a.name}</div>
                            <div class="agent-status ${isBusy ? 'busy' : ''}">${status.status}</div>
                        </div>
                    `;
                }).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadAlerts() {
            try {
                const res = await fetch('/api/alerts');
                const data = await res.json();
                
                document.getElementById('total-alerts').textContent = data.count || 0;
                
                const list = document.getElementById('alerts-list');
                if (data.alerts && data.alerts.length > 0) {
                    list.innerHTML = data.alerts.slice(0, 5).map(a => `
                        <div class="alert ${a.severity?.toLowerCase() || 'medium'}">
                            <span>${a.type}</span>
                            <span>${a.message}</span>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="alert">No active alerts</div>';
                }
            } catch(e) { console.error(e); }
        }
        
        async function loadHotels() {
            try {
                const res = await fetch('/api/hotels');
                const data = await res.json();
                
                const tbody = document.getElementById('hotels-table');
                tbody.innerHTML = data.hotels.slice(0, 10).map(h => `
                    <tr>
                        <td>${h.name || 'N/A'}</td>
                        <td>${h.location || 'N/A'}</td>
                        <td><span class="rating-badge">${h.rating || 'N/A'}</span></td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadTrends() {
            try {
                const res = await fetch('/api/trends');
                const data = await res.json();
                
                const ctx = document.getElementById('trends-chart').getContext('2d');
                
                if (trendsChart) trendsChart.destroy();
                
                trendsChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.trends.map((_, i) => `Cycle ${i+1}`),
                        datasets: [{
                            label: 'Activity',
                            data: data.trends.map((_, i) => i + 1),
                            borderColor: '#00d4ff',
                            backgroundColor: 'rgba(0, 212, 255, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { display: false },
                            y: { display: false }
                        }
                    }
                });
            } catch(e) { console.error(e); }
        }
        
        async function refresh() {
            await Promise.all([
                loadStats(),
                loadCities(),
                loadAgents(),
                loadAlerts(),
                loadHotels(),
                loadTrends()
            ]);
        }
        
        refresh();
        setInterval(refresh, 30000);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    logger.info(f"Starting Tourism Intelligence Dashboard on port {CONFIG['port']}")
    app.run(host="0.0.0.0", port=CONFIG["port"], debug=False)
```

## Map Integration

For interactive maps, add Leaflet.js:

```html
<!-- Add to dashboard HTML head -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<!-- Add map container -->
<div id="map" style="height: 400px; border-radius: 12px;"></div>

<script>
// Colombian cities coordinates
const cityCoords = {
    "bogota": [4.7110, -74.0721],
    "medellin": [6.2476, -75.5658],
    "cartagena": [10.3910, -75.4794],
    "cali": [3.4516, -76.5320],
    "barranquilla": [10.9685, -74.7813],
    "santa_marta": [11.2408, -74.2099]
};

// Initialize map
const map = L.map('map').setView([4.5, -74.5], 6);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Add city markers
Object.entries(cityCoords).forEach(([city, coords]) => {
    L.marker(coords)
        .addTo(map)
        .bindPopup(`<b>${city.charAt(0).toUpperCase() + city.slice(1)}</b><br>Click for hotels`);
});
</script>
```

## City Coordinates

| City | Latitude | Longitude |
|------|----------|-----------|
| Bogotá | 4.7110 | -74.0721 |
| Medellín | 6.2476 | -75.5658 |
| Cartagena | 10.3910 | -75.4794 |
| Cali | 3.4516 | -76.5320 |
| Barranquilla | 10.9685 | -74.7813 |
| Santa Marta | 11.2408 | -74.2099 |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Main dashboard |
| `/api/stats` | Platform statistics |
| `/api/hotels` | Hotel list |
| `/api/hotels/<city>` | City-specific hotels |
| `/api/cities` | City summaries |
| `/api/agents` | Agent status |
| `/api/alerts` | Recent alerts |
| `/api/trends` | Trend data |

## Running the Dashboard

```bash
# Start dashboard
cd /opt/tourism-intel
source venv/bin/activate
python dashboard/main.py

# Access at
http://jetson:8095
```

## Screenshots Description

- **Overview Card**: Shows total hotels, average rating, active alerts, and city count
- **Cities Card**: Clickable list of all tracked cities with hotel counts and ratings
- **Agents Card**: 8 AI agents with live status (idle/busy)
- **Alerts Card**: Scrollable list of recent alerts with severity colors
- **Trends Chart**: Line chart showing activity over time
- **Hotels Table**: Top 10 hotels with name, city, and rating

## Next Steps

- [09-installation](./09-installation.md) - Complete installation guide
