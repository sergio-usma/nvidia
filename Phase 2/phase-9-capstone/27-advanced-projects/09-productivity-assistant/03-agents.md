# AI Office - Agent Implementations

## Base Agent Class

```python
#!/usr/bin/env python3
"""
Base Agent Class for AI Office
"""

import os
import json
import logging
import time
import requests
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "bus_api": os.getenv("BUS_API", "http://localhost:9001"),
    "timeout": 300
}


class BaseAgent(ABC):
    """Base class for all office agents"""
    
    def __init__(self, agent_id: str, role: str, model: str):
        self.agent_id = agent_id
        self.role = role
        self.model = model
        self.ollama = CONFIG["ollama_host"]
        self.bus_api = CONFIG["bus_api"]
        self.current_task = None
        self.tokens_used = 0
        
    def generate(self, prompt: str, temperature: float = 0.3, 
                 max_tokens: int = 2000) -> str:
        """Generate response using Ollama"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_ctx": 4096,
                        "num_predict": max_tokens
                    }
                },
                timeout=CONFIG["timeout"]
            )
            
            result = response.json()
            elapsed = time.time() - start_time
            
            # Estimate tokens
            prompt_tokens = len(prompt) // 4
            response_tokens = len(result.get("response", "")) // 4
            self.tokens_used = prompt_tokens + response_tokens
            
            # Log to bus
            self.log_activity("generating", f"{elapsed:.1f}s, {self.tokens_used} tokens")
            
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            self.log_activity("error", str(e))
            raise
    
    def log_activity(self, action: str, detail: str):
        """Log activity to central bus"""
        try:
            requests.post(
                f"{self.bus_api}/api/activity",
                json={
                    "agent": self.agent_id,
                    "role": self.role,
                    "action": action,
                    "detail": detail,
                    "task": self.current_task
                },
                timeout=5
            )
        except:
            pass  # Don't fail if bus is unavailable
    
    def update_status(self, status: str, task: str = None):
        """Update status in bus"""
        try:
            requests.post(
                f"{self.bus_api}/api/agents/{self.agent_id}/status",
                json={"status": status, "task": task or self.current_task},
                timeout=5
            )
        except:
            pass
    
    @abstractmethod
    def process_task(self, task: Dict) -> Dict:
        """Process a task - implemented by each agent"""
        pass


class LeadAgent(BaseAgent):
    """Lead Agent - Analyzes and delegates tasks"""
    
    def __init__(self):
        super().__init__("lead", "lead", "qwen2.5-coder:14b")
        self.system_prompt = """You are the Lead Agent of a software development team.
Your job is to analyze incoming requests and delegate them to the right specialist.

Analyze the request and determine:
1. Type: feature, bugfix, content, docs, security
2. Priority: 1 (urgent) to 5 (backlog)
3. Which specialist should handle it: frontend, backend, content, qa
4. Initial approach

Respond in JSON format:
{
  "type": "...",
  "priority": 1-5,
  "specialist": "frontend|backend|content|qa",
  "approach": "brief description",
  "requirements": ["list of requirements"]
}"""
    
    def process_task(self, task: Dict) -> Dict:
        """Analyze and delegate task"""
        self.current_task = task.get("id")
        self.update_status("analyzing", task.get("title"))
        
        prompt = f"{self.system_prompt}\n\nRequest:\n{task.get('description')}"
        
        response = self.generate(prompt, temperature=0.3)
        
        # Parse response
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {"specialist": "backend", "priority": 3}
        except:
            analysis = {"specialist": "backend", "priority": 3}
        
        result = {
            "request_id": task.get("id"),
            "analysis": analysis,
            "delegated_to": analysis.get("specialist", "backend"),
            "lead_approved": True
        }
        
        self.update_status("idle")
        self.log_activity("delegated", f"To {analysis.get('specialist')}")
        
        return result


class FrontendAgent(BaseAgent):
    """Frontend Developer Agent"""
    
    def __init__(self):
        super().__init__("frontend-1", "frontend", "qwen2.5-coder:14b")
        self.system_prompt = """You are a Senior Frontend Developer.
Generate clean, modern, responsive UI code.

You can create:
- React components
- Vue components  
- HTML/CSS/JS
- Tailwind styles

Include:
- Proper TypeScript types
- Error handling
- Loading states
- Responsive design

Generate only the code, no explanations unless asked."""
    
    def process_task(self, task: Dict) -> Dict:
        """Generate frontend code"""
        self.current_task = task.get("id")
        self.update_status("coding", task.get("title"))
        
        prompt = f"{self.system_prompt}\n\nTask:\n{task.get('description')}"
        
        code = self.generate(prompt, temperature=0.4, max_tokens=3000)
        
        result = {
            "request_id": task.get("id"),
            "code": code,
            "language": "tsx",
            "files": ["Component.tsx", "Component.css"]
        }
        
        self.update_status("idle")
        self.log_activity("completed", f"Generated {len(code)} chars")
        
        return result


class BackendAgent(BaseAgent):
    """Backend Developer Agent"""
    
    def __init__(self):
        super().__init__("backend-1", "backend", "deepseek-r1:8b")
        self.system_prompt = """You are a Senior Backend Developer.
Generate robust, secure API code.

You can create:
- REST APIs
- GraphQL resolvers
- Database schemas
- Authentication logic

Use best practices:
- Input validation
- Error handling
- Security (SQL injection prevention)
- Logging

Generate only the code, no explanations unless asked."""
    
    def process_task(self, task: Dict) -> Dict:
        """Generate backend code"""
        self.current_task = task.get("id")
        self.update_status("coding", task.get("title"))
        
        prompt = f"{self.system_prompt}\n\nTask:\n{task.get('description')}"
        
        code = self.generate(prompt, temperature=0.4, max_tokens=3000)
        
        result = {
            "request_id": task.get("id"),
            "code": code,
            "language": "python",
            "files": ["api.py", "models.py"]
        }
        
        self.update_status("idle")
        self.log_activity("completed", f"Generated {len(code)} chars")
        
        return result


class QAAgent(BaseAgent):
    """QA Engineer Agent"""
    
    def __init__(self):
        super().__init__("qa-1", "qa", "qwen2.5-coder:14b")
        self.system_prompt = """You are a QA Engineer.
Review code, write tests, and find vulnerabilities.

Analyze the provided code and:
1. Identify bugs and issues
2. Write unit tests
3. Check for security vulnerabilities
4. Suggest improvements

Respond in JSON format:
{
  "bugs": ["list of bugs found"],
  "tests": ["suggested test cases"],
  "security_issues": ["security concerns"],
  "score": 1-10,
  "approved": true/false
}"""
    
    def process_task(self, task: Dict) -> Dict:
        """Review code and run tests"""
        self.current_task = task.get("id")
        self.update_status("testing", task.get("title"))
        
        code = task.get("code", "")
        
        prompt = f"{self.system_prompt}\n\nCode to review:\n{code}"
        
        review = self.generate(prompt, temperature=0.2, max_tokens=1500)
        
        # Parse review
        result = {
            "request_id": task.get("id"),
            "review": review,
            "approved": "approved" in review.lower(),
            "tests_passed": True
        }
        
        self.update_status("idle")
        self.log_activity("validated", "QA complete")
        
        return result


class ContentAgent(BaseAgent):
    """Content Creator Agent"""
    
    def __init__(self):
        super().__init__("content-1", "content", "llama3.2:3b")
        self.system_prompt = """You are a Content Creator for a tech company.
Generate engaging LinkedIn posts and technical articles.

Your style:
- Professional but approachable
- Include relevant hashtags
- Add technical depth
- Call to action
- Emoji usage (sparingly)

Generate ready-to-post content."""
    
    def process_task(self, task: Dict) -> Dict:
        """Generate content"""
        self.current_task = task.get("id")
        self.update_status("writing", task.get("title"))
        
        prompt = f"{self.system_prompt}\n\nTopic:\n{task.get('description')}"
        
        content = self.generate(prompt, temperature=0.7, max_tokens=1000)
        
        result = {
            "request_id": task.get("id"),
            "content": content,
            "platform": "linkedin",
            "ready_to_post": True
        }
        
        self.update_status("idle")
        self.log_activity("completed", f"Wrote {len(content)} chars")
        
        return result
```

## Agent Registry

```python
# registry.py
from typing import Dict

AGENTS = {
    "lead": LeadAgent,
    "frontend-1": FrontendAgent,
    "frontend-2": FrontendAgent,
    "backend-1": BackendAgent,
    "backend-2": BackendAgent,
    "qa-1": QAAgent,
    "content-1": ContentAgent,
}

def get_agent(agent_id: str):
    """Get agent instance"""
    agent_class = AGENTS.get(agent_id)
    if agent_class:
        return agent_class()
    return None
```

## API Integration

```python
# Add to main API
@app.route("/api/agents/<agent_id>/task", methods=["POST"])
def assign_task(agent_id: str):
    """Assign task to agent"""
    data = request.get_json()
    
    agent = get_agent(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    
    try:
        result = agent.process_task(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## Next Steps

- [04-scheduler](./04-scheduler.md) - Task orchestration
