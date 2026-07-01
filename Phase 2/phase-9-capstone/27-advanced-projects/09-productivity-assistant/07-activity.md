# AI Office - Activity Logging

## Overview

The activity logging system tracks all agent actions in real-time, enabling monitoring of who is working on what and calculating costs.

## Activity Logger

```python
#!/usr/bin/env python3
"""
Activity Logger - Real-time activity tracking
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from collections import deque

class ActivityLogger:
    """Thread-safe activity logger"""
    
    def __init__(self, log_dir="/opt/ai-office/data"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.activity_file = self.log_dir / "activity.json"
        self.max_entries = 10000
        self.lock = threading.Lock()
        self.load_log()
    
    def load_log(self):
        """Load existing log"""
        if self.activity_file.exists():
            try:
                with open(self.activity_file) as f:
                    data = json.load(f)
                    self.entries = deque(data.get("entries", []), maxlen=self.max_entries)
            except:
                self.entries = deque(maxlen=self.max_entries)
        else:
            self.entries = deque(maxlen=self.max_entries)
    
    def save_log(self):
        """Save log to disk"""
        with self.lock:
            with open(self.log_dir, "w") as f:
                json.dump({
                    "entries": list(self.entries),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
    
    def log(self, agent: str, role: str, action: str, detail: str = "", 
            task: str = None, tokens: int = 0):
        """Log an activity"""
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "datetime": datetime.now().isoformat(),
            "agent": agent,
            "role": role,
            "action": action,
            "detail": detail,
            "task": task,
            "tokens": tokens,
            "cost": tokens * 0.001  # Approximate cost
        }
        
        with self.lock:
            self.entries.append(entry)
        
        # Save periodically
        if len(self.entries) % 10 == 0:
            self.save_log()
        
        return entry
    
    def get_recent(self, count: int = 20):
        """Get recent entries"""
        return list(self.entries)[-count:]
    
    def get_by_agent(self, agent: str, count: int = 20):
        """Get entries for specific agent"""
        agent_entries = [e for e in self.entries if e.get("agent") == agent]
        return agent_entries[-count:]
    
    def get_stats(self):
        """Get statistics"""
        total_tokens = sum(e.get("tokens", 0) for e in self.entries)
        total_cost = sum(e.get("cost", 0) for e in self.entries)
        
        by_agent = {}
        for e in self.entries:
            agent = e.get("agent", "unknown")
            if agent not in by_agent:
                by_agent[agent] = {"tasks": 0, "tokens": 0}
            by_agent[agent]["tasks"] += 1
            by_agent[agent]["tokens"] += e.get("tokens", 0)
        
        by_action = {}
        for e in self.entries:
            action = e.get("action", "unknown")
            by_action[action] = by_action.get(action, 0) + 1
        
        return {
            "total_entries": len(self.entries),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_agent": by_agent,
            "by_action": by_action
        }


# Global logger instance
logger = ActivityLogger()


# Flask routes for logging
@app.route("/api/activity", methods=["GET"])
def get_activity():
    """Get activity log"""
    count = request.args.get("count", 20, type=int)
    return jsonify({
        "activity_log": logger.get_recent(count)
    })


@app.route("/api/activity/<agent_id>", methods=["GET"])
def get_agent_activity(agent_id: str):
    """Get activity for specific agent"""
    count = request.args.get("count", 20, type=int)
    return jsonify({
        "activity_log": logger.get_by_agent(agent_id, count)
    })


@app.route("/api/activity", methods=["POST"])
def log_activity():
    """Log new activity"""
    data = request.get_json()
    
    entry = logger.log(
        agent=data.get("agent", "unknown"),
        role=data.get("role", "unknown"),
        action=data.get("action", "log"),
        detail=data.get("detail", ""),
        task=data.get("task"),
        tokens=data.get("tokens", 0)
    )
    
    return jsonify({"success": True, "entry": entry})


@app.route("/api/activity/stats", methods=["GET"])
def get_activity_stats():
    """Get activity statistics"""
    return jsonify(logger.get_stats())
```

## Cost Tracking

```python
# cost_tracker.py
"""
Cost tracking per operation
"""

TOKEN_COSTS = {
    "qwen2.5-coder:14b": 0.0001,  # Per token
    "deepseek-r1:8b": 0.0001,
    "llama3.2:3b": 0.00008,
    "glm-4.7-flash:latest": 0.00005
}

def calculate_cost(model: str, tokens: int) -> float:
    """Calculate cost for operation"""
    rate = TOKEN_COSTS.get(model, 0.0001)
    return tokens * rate

# Example usage:
# cost = calculate_cost("qwen2.5-coder:14b", 1500)
# print(f"Cost: ${cost:.4f}")
```

## Metrics Collection

```python
# metrics.py
"""
Metrics collection and reporting
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

class MetricsCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, data_dir="/opt/ai-office/data"):
        self.data_dir = Path(data_dir)
        self.metrics_file = self.data_dir / "metrics.json"
    
    def collect(self):
        """Collect current metrics"""
        # Agent metrics
        agent_metrics = {}
        
        # Get from activity log
        activity_file = self.data_dir / "activity.json"
        if activity_file.exists():
            with open(activity_file) as f:
                data = json.load(f)
                entries = data.get("entries", [])
                
                # Aggregate by agent
                for entry in entries:
                    agent = entry.get("agent")
                    if agent not in agent_metrics:
                        agent_metrics[agent] = {
                            "tasks": 0,
                            "tokens": 0,
                            "cost": 0,
                            "actions": {}
                        }
                    
                    agent_metrics[agent]["tasks"] += 1
                    agent_metrics[agent]["tokens"] += entry.get("tokens", 0)
                    agent_metrics[agent]["cost"] += entry.get("cost", 0)
                    
                    action = entry.get("action", "unknown")
                    agent_metrics[agent]["actions"][action] = \
                        agent_metrics[agent]["actions"].get(action, 0) + 1
        
        # Get queue metrics
        queue_file = self.data_dir / "requests.json"
        queue_metrics = {"total": 0, "pending": 0, "completed": 0}
        
        if queue_file.exists():
            with open(queue_file) as f:
                data = json.load(f)
                requests = data.get("requests", [])
                
                queue_metrics["total"] = len(requests)
                queue_metrics["pending"] = len([r for r in requests if r.get("status") == "pending"])
                queue_metrics["completed"] = len([r for r in requests if r.get("status") == "completed"])
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "agents": agent_metrics,
            "queue": queue_metrics,
            "total_cost": sum(a.get("cost", 0) for a in agent_metrics.values())
        }
        
        # Save
        with open(self.metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)
        
        return metrics
```

## Real-time Dashboard Data

```python
# Dashboard data endpoint
@app.route("/api/dashboard")
def dashboard_data():
    """Get all dashboard data"""
    activity_logger = ActivityLogger()
    
    # Get recent activity
    recent = activity_logger.get_recent(20)
    
    # Get stats
    stats = activity_logger.get_stats()
    
    # Get metrics
    metrics = MetricsCollector().collect()
    
    # Get queue status
    queue_file = Path(CONFIG["data_dir"]) / "requests.json"
    queue = []
    if queue_file.exists():
        with open(queue_file) as f:
            queue = json.load(f).get("requests", [])
    
    return jsonify({
        "activity": recent,
        "agent_stats": stats,
        "metrics": metrics,
        "queue": {
            "size": len(queue),
            "pending": len([r for r in queue if r.get("status") == "pending"]),
            "in_progress": len([r for r in queue if r.get("status") == "in_progress"])
        },
        "timestamp": datetime.now().isoformat()
    })
```

## Example Activity Log Entry

```json
{
  "timestamp": "14:35:22",
  "datetime": "2024-01-15T14:35:22.123456",
  "agent": "backend-1",
  "role": "backend",
  "action": "generating",
  "detail": "Created API endpoint /users",
  "task": "REQ-20240115143001",
  "tokens": 1250,
  "cost": 0.125
}
```

## Dashboard Display

The activity log shows in the dashboard:

```
📊 Activity Log
────────────────────────────────────
[14:35] backend-1: generating → Created API endpoint
[14:34] content-1: completed → Wrote 850 chars
[14:33] qa-1: testing → Running security scan
[14:32] lead-1: analyzing → Priority: HIGH
[14:31] frontend-1: completed → Generated React component
[14:30] backend-1: delegated → Task REQ-20240115143001
```

## Next Steps

- [08-installation](./08-installation.md) - Complete installation guide
