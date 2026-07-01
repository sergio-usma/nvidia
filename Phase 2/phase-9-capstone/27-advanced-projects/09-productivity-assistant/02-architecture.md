# AI Office - System Architecture

## Overview

The AI Office uses a distributed agent architecture where each agent is an independent process that communicates via a message queue and shared state.

## Components

### Message Queue

```python
# message_queue.py
import json
import time
from pathlib import Path
from datetime import datetime
from collections import deque
import threading

class MessageQueue:
    """Thread-safe message queue for agent communication"""
    
    def __init__(self, queue_file="/opt/ai-office/data/queue.json"):
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.load_queue()
    
    def load_queue(self):
        """Load queue from disk"""
        if self.queue_file.exists():
            with open(self.queue_file) as f:
                data = json.load(f)
                self.messages = deque(data.get("messages", []))
        else:
            self.messages = deque()
    
    def save_queue(self):
        """Save queue to disk"""
        with self.lock:
            with open(self.queue_file, "w") as f:
                json.dump({
                    "messages": list(self.messages),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
    
    def enqueue(self, message: dict):
        """Add message to queue"""
        with self.lock:
            message["timestamp"] = datetime.now().isoformat()
            message["id"] = f"msg-{len(self.messages)}"
            self.messages.append(message)
            self.save_queue()
    
    def dequeue(self) -> dict:
        """Get next message"""
        with self.lock:
            if self.messages:
                msg = self.messages.popleft()
                self.save_queue()
                return msg
            return None
    
    def peek(self) -> dict:
        """View next message without removing"""
        with self.lock:
            if self.messages:
                return self.messages[0]
            return None
    
    def size(self) -> int:
        """Get queue size"""
        return len(self.messages)
```

### Agent Communication

```python
# agent_bus.py
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class AgentBus:
    """Central message bus for agent communication"""
    
    def __init__(self, data_dir="/opt/ai-office/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.agents = {}
        self.activity_log = []
    
    def register_agent(self, agent_id: str, role: str):
        """Register an agent"""
        self.agents[agent_id] = {
            "role": role,
            "status": "idle",
            "current_task": None,
            "started_at": datetime.now().isoformat(),
            "tasks_completed": 0,
            "tokens_used": 0
        }
        self.log_activity(agent_id, "registered", f"Agent {role} registered")
    
    def update_status(self, agent_id: str, status: str, task: str = None):
        """Update agent status"""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = status
            if task:
                self.agents[agent_id]["current_task"] = task
            self.log_activity(agent_id, status, task or "")
    
    def complete_task(self, agent_id: str, tokens_used: int = 0):
        """Mark task as complete"""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "idle"
            self.agents[agent_id]["current_task"] = None
            self.agents[agent_id]["tasks_completed"] += 1
            self.agents[agent_id]["tokens_used"] += tokens_used
            self.log_activity(agent_id, "completed", f"Task complete. Tokens: {tokens_used}")
    
    def send_message(self, from_agent: str, to_agent: str, message: dict):
        """Send message between agents"""
        msg = {
            "from": from_agent,
            "to": to_agent,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.log_activity(from_agent, "message", f"To {to_agent}")
        
        # Store message
        msg_file = self.data_dir / "messages" / f"{to_agent}.json"
        msg_file.parent.mkdir(parents=True, exist_ok=True)
        
        messages = []
        if msg_file.exists():
            with open(msg_file) as f:
                messages = json.load(f)
        messages.append(msg)
        with open(msg_file, "w") as f:
            json.dump(messages, f, indent=2)
    
    def log_activity(self, agent_id: str, action: str, detail: str):
        """Log agent activity"""
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "agent": agent_id,
            "action": action,
            "detail": detail
        }
        self.activity_log.append(entry)
        
        # Keep last 1000 entries
        if len(self.activity_log) > 1000:
            self.activity_log = self.activity_log[-1000:]
        
        # Save to file
        log_file = self.data_dir / "activity.json"
        with open(log_file, "w") as f:
            json.dump(self.activity_log, f, indent=2)
    
    def get_status(self) -> Dict:
        """Get system status"""
        return {
            "agents": self.agents,
            "queue_size": self.get_queue_size(),
            "activity_log": self.activity_log[-20:]
        }
    
    def get_queue_size(self) -> int:
        """Get pending requests"""
        queue_file = self.data_dir / "queue.json"
        if queue_file.exists():
            with open(queue_file) as f:
                data = json.load(f)
                return len(data.get("messages", []))
        return 0
```

### Request Model

```python
# request_model.py
from datetime import datetime
from enum import Enum
from typing import Optional

class Priority(Enum):
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKLOG = 5

class RequestStatus(Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    IN_PROGRESS = "in_progress"
    QA = "qa"
    COMPLETED = "completed"
    FAILED = "failed"

class Request:
    """Work request model"""
    
    def __init__(
        self,
        title: str,
        description: str,
        request_type: str,  # feature, bugfix, content, docs
        priority: Priority = Priority.MEDIUM,
        created_by: str = "system"
    ):
        self.id = f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.title = title
        self.description = description
        self.request_type = request_type
        self.priority = priority
        self.status = RequestStatus.PENDING
        self.created_by = created_by
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.assigned_to = None
        self.completed_at = None
        self.tokens_used = 0
        self.cost_estimate = 0.0
        self.logs = []
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.request_type,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "tokens_used": self.tokens_used,
            "cost_estimate": self.cost_estimate
        }
```

## Model Configuration

### Agent Model Assignments

```python
# models.py
AGENT_MODELS = {
    "lead": {
        "model": "qwen2.5-coder:14b",
        "temperature": 0.3,
        "purpose": "Analysis and decision making"
    },
    "frontend": {
        "model": "qwen2.5-coder:14b",
        "temperature": 0.4,
        "purpose": "Frontend development"
    },
    "backend": {
        "model": "deepseek-r1:8b",
        "temperature": 0.4,
        "purpose": "Backend development"
    },
    "qa": {
        "model": "qwen2.5-coder:14b",
        "temperature": 0.2,
        "purpose": "Testing and security"
    },
    "content": {
        "model": "llama3.2:3b",
        "temperature": 0.7,
        "purpose": "Content generation"
    },
    "scheduler": {
        "model": "glm-4.7-flash:latest",
        "temperature": 0.3,
        "purpose": "Orchestration"
    }
}

# Cost per 1K tokens (estimate for local inference)
TOKEN_COSTS = {
    "qwen2.5-coder:14b": 0.001,  # Local, so very cheap
    "deepseek-r1:8b": 0.001,
    "llama3.2:3b": 0.001,
    "glm-4.7-flash:latest": 0.0005
}
```

## n8n Workflow

### Main Workflow Structure

```
1. Scheduler (Cron every 15 min)
   │
   ▼
2. Lead Agent (Analyze Request)
   │
   ▼ (Delegate)
3. Specialist Agent (Frontend/Backend/Content)
   │
   ▼
4. QA Agent (Validate)
   │
   ▼
5. Complete & Notify
```

### Workflow JSON

```json
{
  "name": "AI Office Workflow",
  "nodes": [
    {
      "name": "Scheduler",
      "type": "cron",
      "parameters": {
        "rule": {"minutesInterval": 15}
      }
    },
    {
      "name": "Get Next Request",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "GET",
        "url": "http://localhost:9001/api/requests/next"
      }
    },
    {
      "name": "Lead Agent Analyze",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:9001/api/agents/lead/analyze",
        "bodyParameters": {
          "parameters": [
            {"name": "request_id", "value": "={{ $json.id }}"},
            {"name": "description", "value": "={{ $json.description }}"}
          ]
        }
      }
    },
    {
      "name": "Delegate to Specialist",
      "type": "switch",
      "parameters": {
        "dataType": "string",
        "value1": "={{ $json.delegated_to }}",
        "cases": {
          "frontend": {"output": 0},
          "backend": {"output": 1},
          "content": {"output": 2}
        }
      }
    },
    {
      "name": "QA Validation",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:9001/api/agents/qa/validate"
      }
    },
    {
      "name": "Complete Request",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:9001/api/requests/complete"
      }
    }
  ]
}
```

## API Endpoints

### Core API (Port 9001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/requests | GET | List all requests |
| /api/requests | POST | Create new request |
| /api/requests/next | GET | Get next pending request |
| /api/agents/:id/status | GET | Get agent status |
| /api/agents/:id/task | POST | Assign task to agent |
| /api/activity | GET | Get activity log |
| /api/stats | GET | Get statistics |

## Next Steps

- [03-agents](./03-agents.md) - Individual agent implementations
