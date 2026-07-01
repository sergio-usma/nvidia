# AI Office - Scheduler Agent

## Overview

The Scheduler Agent orchestrates the work queue, polls for new requests, assigns tasks to specialists, and monitors completion. It runs every 15 minutes.

## Scheduler Implementation

```python
#!/usr/bin/env python3
"""
Scheduler Agent - Orchestrates work queue
Runs every 15 minutes
"""

import os
import sys
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/ai-office/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/ai-office/data",
    "requests_file": "/opt/ai-office/data/requests.json",
    "bus_api": "http://localhost:9001",
    "ollama_host": "http://localhost:11434",
    "poll_interval": 900,  # 15 minutes
    "max_concurrent": 3
}

os.makedirs(CONFIG["data_dir"], exist_ok=True)
os.makedirs("/opt/ai-office/logs", exist_ok=True)


class SchedulerAgent:
    """Orchestrates the work queue"""
    
    def __init__(self):
        self.data_dir = Path(CONFIG["data_dir"])
        self.requests_file = Path(CONFIG["requests_file"])
        self.load_requests()
        
    def load_requests(self):
        """Load requests from disk"""
        if self.requests_file.exists():
            with open(self.requests_file) as f:
                data = json.load(f)
                self.requests = data.get("requests", [])
        else:
            self.requests = []
    
    def save_requests(self):
        """Save requests to disk"""
        with open(self.requests_file, "w") as f:
            json.dump({
                "requests": self.requests,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)
    
    def get_pending_requests(self):
        """Get pending requests sorted by priority"""
        pending = [r for r in self.requests if r.get("status") == "pending"]
        return sorted(pending, key=lambda x: x.get("priority", 5))
    
    def get_available_agents(self):
        """Get agents that are idle"""
        try:
            response = requests.get(f"{CONFIG['bus_api']}/api/agents", timeout=5)
            if response.status_code == 200:
                agents = response.json().get("agents", {})
                available = [
                    agent_id for agent_id, info in agents.items()
                    if info.get("status") == "idle"
                ]
                return available
        except:
            pass
        return ["frontend-1", "backend-1", "content-1"]
    
    def analyze_with_lead(self, request: dict):
        """Use Lead Agent to analyze request"""
        try:
            response = requests.post(
                f"{CONFIG['bus_api']}/api/agents/lead/analyze",
                json={"task": request},
                timeout=60
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Lead analysis failed: {e}")
        
        # Fallback: auto-assign
        return {
            "delegated_to": "backend-1",
            "priority": request.get("priority", 3)
        }
    
    def assign_to_agent(self, request: dict, agent_id: str):
        """Assign request to specific agent"""
        try:
            response = requests.post(
                f"{CONFIG['bus_api']}/api/agents/{agent_id}/task",
                json=request,
                timeout=120
            )
            
            if response.status_code == 200:
                # Update request status
                for req in self.requests:
                    if req.get("id") == request.get("id"):
                        req["status"] = "in_progress"
                        req["assigned_to"] = agent_id
                        req["started_at"] = datetime.now().isoformat()
                self.save_requests()
                
                logger.info(f"Assigned {request.get('id')} to {agent_id}")
                return True
                
        except Exception as e:
            logger.error(f"Assignment failed: {e}")
        
        return False
    
    def check_completion(self):
        """Check for completed tasks"""
        try:
            response = requests.get(
                f"{CONFIG['bus_api']}/api/agents/status",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check each agent
                for agent_id, info in data.get("agents", {}).items():
                    if info.get("status") == "idle" and info.get("current_task"):
                        # Task was just completed
                        task_id = info.get("current_task")
                        
                        # Move to QA or complete
                        for req in self.requests:
                            if req.get("id") == task_id:
                                if req.get("status") == "in_progress":
                                    req["status"] = "qa"
                                    logger.info(f"Task {task_id} moved to QA")
                        self.save_requests()
                        
        except Exception as e:
            logger.error(f"Completion check failed: {e}")
    
    def run_cycle(self):
        """Run one scheduling cycle"""
        logger.info("=== Scheduler Cycle Started ===")
        
        # Reload requests
        self.load_requests()
        
        # Check for completions
        self.check_completion()
        
        # Get pending requests
        pending = self.get_pending_requests()
        
        if not pending:
            logger.info("No pending requests")
            return
        
        # Get available agents
        available = self.get_available_agents()
        
        logger.info(f"Pending: {len(pending)}, Available agents: {len(available)}")
        
        # Assign tasks
        assigned = 0
        for request in pending[:len(available)]:
            # Analyze with Lead
            analysis = self.analyze_with_lead(request)
            
            # Get target agent
            target = analysis.get("delegated_to", "backend-1")
            
            if target in available:
                if self.assign_to_agent(request, target):
                    assigned += 1
                    available.remove(target)  # Agent is now busy
        
        logger.info(f"Cycle complete: {assigned} tasks assigned")
        
        # Log stats
        self.log_stats()
    
    def log_stats(self):
        """Log current statistics"""
        stats = {
            "total_requests": len(self.requests),
            "pending": len([r for r in self.requests if r.get("status") == "pending"]),
            "in_progress": len([r for r in self.requests if r.get("status") == "in_progress"]),
            "completed": len([r for r in self.requests if r.get("status") == "completed"]),
            "qa": len([r for r in self.requests if r.get("status") == "qa"])
        }
        
        logger.info(f"Stats: {stats}")
        
        # Save stats
        stats_file = self.data_dir / "stats.json"
        stats["timestamp"] = datetime.now().isoformat()
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
    
    def run_continuous(self):
        """Run scheduler continuously"""
        logger.info(f"Scheduler started - polling every {CONFIG['poll_interval']}s")
        
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            # Sleep until next cycle
            time.sleep(CONFIG["poll_interval"])


def create_request(title: str, description: str, request_type: str, 
                   priority: int = 3) -> dict:
    """Helper to create new request"""
    scheduler = SchedulerAgent()
    
    request = {
        "id": f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "title": title,
        "description": description,
        "type": request_type,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    scheduler.requests.append(request)
    scheduler.save_requests()
    
    return request


if __name__ == "__main__":
    scheduler = SchedulerAgent()
    scheduler.run_continuous()
```

## Request Creation API

```python
# Add to API
@app.route("/api/requests", methods=["POST"])
def create_request_api():
    """Create new request"""
    data = request.get_json()
    
    request = {
        "id": f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "type": data.get("type", "feature"),
        "priority": data.get("priority", 3),
        "status": "pending",
        "created_by": data.get("created_by", "api"),
        "created_at": datetime.now().isoformat()
    }
    
    # Load and update
    requests_file = Path(CONFIG["data_dir"]) / "requests.json"
    if requests_file.exists():
        with open(requests_file) as f:
            all_requests = json.load(f)
    else:
        all_requests = {"requests": []}
    
    all_requests["requests"].append(request)
    
    with open(requests_file, "w") as f:
        json.dump(all_requests, f, indent=2)
    
    return jsonify(request), 201


@app.route("/api/requests", methods=["GET"])
def list_requests():
    """List all requests"""
    requests_file = Path(CONFIG["data_dir"]) / "requests.json"
    
    if requests_file.exists():
        with open(requests_file) as f:
            data = json.load(f)
            return jsonify(data.get("requests", []))
    
    return jsonify([])


@app.route("/api/requests/next", methods=["GET"])
def get_next_request():
    """Get next pending request"""
    scheduler = SchedulerAgent()
    pending = scheduler.get_pending_requests()
    
    if pending:
        return jsonify(pending[0])
    
    return jsonify(None)


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get queue statistics"""
    scheduler = SchedulerAgent()
    scheduler.load_requests()
    
    return jsonify({
        "total": len(scheduler.requests),
        "pending": len([r for r in scheduler.requests if r.get("status") == "pending"]),
        "in_progress": len([r for r in scheduler.requests if r.get("status") == "in_progress"]),
        "completed": len([r for r in scheduler.requests if r.get("status") == "completed"])
    })
```

## Example Requests

```python
# Example: Create work requests

# Feature request
create_request(
    title="Add user dashboard",
    description="Create a dashboard showing user stats and activity",
    request_type="feature",
    priority=2
)

# Bug fix
create_request(
    title="Fix login redirect",
    description="Users are not redirected after successful login",
    request_type="bugfix",
    priority=1
)

# Content
create_request(
    title="LinkedIn post - New feature",
    description="Write a LinkedIn post announcing the new API endpoint",
    request_type="content",
    priority=3
)
```

## Cron Setup

```bash
# Alternative: Run via cron
crontab -e

# Add: Run every 15 minutes
*/15 * * * * /opt/ai-office/venv/bin/python /opt/ai-office/scheduler/main.py >> /opt/ai-office/logs/scheduler.log 2>&1
```

## Next Steps

- [05-discord](./05-discord.md) - Discord integration
