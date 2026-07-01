# Freelance Hunter - AI Agents

## Overview

The platform uses 10 specialized AI agents to discover, analyze, match, and propose freelance opportunities. Each agent has a specific role in the pipeline.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATION                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    ┌─────────┐                                                      │
│    │  LEAD   │  → Coordinates all agents, prioritizes tasks       │
│    │  AGENT  │  → Makes high-level decisions                       │
│    └────┬────┘                                                      │
│         │                                                            │
│    ┌────┴────────────────────────────────────────────┐              │
│    │              MESSAGE BUS                        │              │
│    │  - Task Queue    - Event Stream    - State     │              │
│    └────────────────────┬───────────────────────────┘              │
│                        │                                            │
│    ┌───────────────────┼────────────────────┐                       │
│    │                   │                    │                       │
│    ▼                   ▼                    ▼                       │
│ ┌────────┐         ┌─────────┐         ┌────────┐                  │
│ │SCRAPER│         │ANALYZER │         │WRITER  │                  │
│ │ AGENT │         │  AGENT  │         │  AGENT │                  │
│ └───┬────┘         └────┬────┘         └───┬────┘                  │
│     │                   │                   │                       │
│     │         ┌─────────┴─────────┐         │                       │
│     │         │                   │         │                       │
│     ▼         ▼                   ▼         ▼                       │
│ ┌─────────┐ ┌──────────┐   ┌──────────┐ ┌────────┐                 │
│ │Scheduler│ │Researcher│   │Notifier  │ │ QA     │                 │
│ │  AGENT  │ │  AGENT   │   │  AGENT   │ │ AGENT  │                 │
│ └─────────┘ └──────────┘   └──────────┘ └────────┘                 │
│       │          │               │          │                        │
│       └──────────┴───────────────┴──────────┘                       │
│                       │                                            │
│                       ▼                                            │
│               ┌─────────────┐                                      │
│               │   MANAGER   │                                      │
│               │    AGENT   │                                      │
│               └─────────────┘                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent Implementations

```python
#!/usr/bin/env python3
"""
AI Agents for Freelance Hunter Platform
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "ollama_host": "http://localhost:11434",
    "api_url": "http://localhost:8096",
    "data_dir": "/opt/freelance-hunter/data"
}


class AgentState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


class BaseAgent:
    """Base agent class"""
    
    def __init__(self, agent_id: str, role: str, model: str):
        self.agent_id = agent_id
        self.role = role
        self.model = model
        self.ollama = CONFIG["ollama_host"]
        self.state = AgentState.IDLE
        self.current_task = None
        self.task_history = []
    
    def generate(self, prompt: str, temperature: float = 0.3, 
                 max_tokens: int = 2000) -> str:
        """Generate response from Ollama"""
        
        try:
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
                timeout=180
            )
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return ""
    
    def log_activity(self, action: str, detail: str, 
                     metadata: Dict = None):
        """Log agent activity"""
        
        activity = {
            "agent": self.agent_id,
            "role": self.role,
            "action": action,
            "detail": detail,
            "task": self.current_task,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.task_history.append(activity)
        
        try:
            requests.post(
                f"{CONFIG['api_url']}/api/activity",
                json=activity,
                timeout=5
            )
        except:
            pass
    
    def update_state(self, state: AgentState, task: str = None):
        """Update agent state"""
        
        self.state = state
        if task:
            self.current_task = task
        
        try:
            requests.post(
                f"{CONFIG['api_url']}/api/agents/{self.agent_id}/status",
                json={
                    "state": state.value,
                    "task": task or self.current_task
                },
                timeout=5
            )
        except:
            pass


class LeadAgent(BaseAgent):
    """Lead Agent - Orchestrates all tasks"""
    
    def __init__(self):
        super().__init__("lead", "lead", "qwen2.5-coder:14b")
    
    def analyze_task(self, task: Dict) -> Dict:
        """Analyze task and delegate to specialist"""
        
        self.update_state(AgentState.BUSY, task.get("id"))
        
        task_type = task.get("type", "scrape")
        priority = task.get("priority", 3)
        
        prompt = f"""Analyze this task and determine which specialist should handle it:

Task: {task.get('title')}
Type: {task_type}
Priority: {priority}

Available specialists:
- scraper: Collects job data from platforms
- analyzer: Evaluates job fit
- writer: Generates proposals  
- qa: Reviews proposals
- researcher: Researches clients/companies
- notifier: Sends alerts

Determine:
1. Priority (1-5)
2. Best specialist
3. Reasoning

Respond in JSON:
{{"priority": 1-5, "specialist": "name", "reasoning": "..."}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        # Parse response
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"specialist": "scraper", "priority": 3}
        except:
            result = {"specialist": "scraper", "priority": 3}
        
        self.update_state(AgentState.IDLE)
        self.log_activity("delegated", f"To {result.get('specialist')}")
        
        return result
    
    def prioritize_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Prioritize jobs by opportunity score"""
        
        prompt = f"""Analyze these {len(jobs)} jobs and prioritize them:

Jobs:
{json.dumps([{"title": j.get("title"), "budget": j.get("budget"), "skills": j.get("skills")[:3]} for j in jobs[:10]])}

Consider:
- Budget alignment
- Skill match
- Competition (proposals count)
- Client quality

Return JSON array with job IDs in priority order:
{{"priority_order": ["job_id_1", "job_id_2"]}}"""
        
        response = self.generate(prompt, temperature=0.4)
        
        return jobs  # Return as-is if parsing fails


class ScraperAgent(BaseAgent):
    """Scraper Agent - Collects job data"""
    
    def __init__(self):
        super().__init__("scraper", "scraper", "qwen2.5-coder:14b")
    
    def scrape_platforms(self, platforms: List[str] = None) -> Dict:
        """Scrape specified platforms"""
        
        self.update_state(AgentState.BUSY, "scraping")
        
        platforms = platforms or ["remoteok", "weworkremotely", "upwork"]
        
        results = {
            "platforms": platforms,
            "jobs_found": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Call scraper orchestrator
            response = requests.post(
                f"{CONFIG['api_url']}/api/scraper/run",
                json={"platforms": platforms},
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                results["jobs_found"] = data.get("count", 0)
                results["status"] = "success"
            else:
                results["status"] = "failed"
                
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            results["status"] = "error"
            results["error"] = str(e)
        
        self.update_state(AgentState.IDLE)
        self.log_activity("completed", f"Found {results['jobs_found']} jobs")
        
        return results


class AnalyzerAgent(BaseAgent):
    """Analyzer Agent - Evaluates job fit"""
    
    def __init__(self):
        super().__init__("analyzer", "analyzer", "deepseek-r1:8b")
    
    def analyze_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Analyze jobs for fit"""
        
        self.update_state(AgentState.BUSY, "analyzing jobs")
        
        analyzed = []
        
        for job in jobs[:50]:  # Limit to avoid timeout
            analysis = self.analyze_single_job(job)
            analyzed.append(analysis)
        
        self.update_state(AgentState.IDLE)
        self.log_activity("completed", f"Analyzed {len(analyzed)} jobs")
        
        return analyzed
    
    def analyze_single_job(self, job: Dict) -> Dict:
        """Analyze single job"""
        
        prompt = f"""Analyze this freelance job for fit:

Title: {job.get('title')}
Budget: {job.get('budget')}
Skills: {', '.join(job.get('skills', []))}
Description: {job.get('description', '')[:300]}

Evaluate:
1. Fit score (1-10)
2. Key requirements
3. Red flags
4. Suggested rate
5. Why you should apply

Respond in JSON:
{{"score": 1-10, "requirements": [], "red_flags": [], "suggested_rate": 0, "reason": "..."}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        # Parse response
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {"score": 5, "reason": "Analysis unavailable"}
        except:
            analysis = {"score": 5, "reason": "Parse error"}
        
        analysis["job_id"] = job.get("id")
        analysis["platform"] = job.get("platform")
        
        return analysis


class WriterAgent(BaseAgent):
    """Writer Agent - Generates proposals"""
    
    def __init__(self):
        super().__init__("writer", "writer", "llama3.2:3b")
    
    def write_proposal(self, job: Dict, match_data: Dict) -> Dict:
        """Write proposal for job"""
        
        self.update_state(AgentState.BUSY, f"Writing proposal for {job.get('title')}")
        
        prompt = f"""Write a professional freelance proposal for this job:

Job: {job.get('title')}
Budget: {job.get('budget')}
Requirements: {job.get('description', '')[:500]}

Your Skills: Python, JavaScript, React, Node.js, Docker, AWS
Experience: 8 years
Rate: $75/hr

Write a 250-word proposal that:
1. Shows understanding of the project
2. Highlights relevant skills
3. Explains your approach
4. Includes timeline and rate
5. Professional closing"""
        
        content = self.generate(prompt, temperature=0.7, max_tokens=1000)
        
        proposal = {
            "id": f"PROP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "job_id": job.get("id"),
            "platform": job.get("platform"),
            "content": content,
            "rate": match_data.get("recommended_rate", 75),
            "status": "draft",
            "created_at": datetime.now().isoformat()
        }
        
        self.update_state(AgentState.IDLE)
        self.log_activity("completed", f"Wrote proposal for {job.get('title')}")
        
        return proposal
    
    def write_followup(self, proposal_id: str, context: str) -> str:
        """Write follow-up message"""
        
        prompt = f"""Write a professional follow-up message for a freelance proposal.

Context: {context}

Keep it brief, professional, and polite. 2-3 sentences max."""
        
        message = self.generate(prompt, temperature=0.5, max_tokens=200)
        
        return message


class QA Agent(BaseAgent):
    """QA Agent - Quality assurance"""
    
    def __init__(self):
        super().__init__("qa", "qa", "deepseek-r1:8b")
    
    def review_proposal(self, proposal: Dict, job: Dict) -> Dict:
        """Review proposal quality"""
        
        self.update_state(AgentState.BUSY, "Reviewing proposal")
        
        prompt = f"""Review this freelance proposal for quality:

Job: {job.get('title')}
Proposal: {proposal.get('content', '')[:500]}

Check for:
- Length (should be 200-400 words)
- Grammar and spelling
- Includes rate
- Includes timeline
- Professional tone
- Relevant skills mentioned
- Call to action

Respond in JSON:
{{"score": 1-10, "issues": [], "suggestions": [], "approved": true/false}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                review = json.loads(json_match.group())
            else:
                review = {"score": 5, "approved": False}
        except:
            review = {"score": 5, "approved": False}
        
        self.update_state(AgentState.IDLE)
        self.log_activity("completed", f"Review score: {review.get('score')}/10")
        
        return review


class SchedulerAgent(BaseAgent):
    """Scheduler Agent - Manages 5-minute cycles"""
    
    def __init__(self):
        super().__init__("scheduler", "scheduler", "glm-4.7-flash:latest")
    
    def plan_cycle(self) -> Dict:
        """Plan next 5-minute cycle"""
        
        prompt = """Plan the next 5-minute cycle for freelance hunting.

Tasks available:
- scrape: Scrape new jobs (run every 2 cycles)
- analyze: Analyze jobs for fit (every cycle)
- match: Match to profile (every cycle)
- write: Generate proposals for matches (every cycle)
- notify: Send alerts for hot jobs (every cycle)
- research: Research high-value clients (every 10 cycles)

Current time: {datetime.now().strftime('%H:%M')}

What should run in this cycle?

Respond in JSON:
{{"tasks": ["task1", "task2"], "reasoning": "..."}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                plan = {"tasks": ["scrape", "analyze", "match"]}
        except:
            plan = {"tasks": ["scrape", "analyze", "match"]}
        
        return plan
    
    def determine_priority_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Determine which jobs need immediate proposals"""
        
        urgent = []
        
        for job in jobs:
            # High budget + low competition = urgent
            budget = job.get("budget", "")
            proposals = job.get("proposals_count", 50)
            
            if "$" in budget and proposals < 10:
                if any(x in budget for x in ["1000", "2000", "5000", "10000"]):
                    urgent.append(job)
        
        return urgent[:5]


class NotifierAgent(BaseAgent):
    """Notifier Agent - Sends alerts"""
    
    def __init__(self):
        super().__init__("notifier", "notifier", "qwen2.5-coder:14b")
    
    def send_alert(self, job: Dict, match_data: Dict):
        """Send alert for hot job"""
        
        self.update_state(AgentState.BUSY, "Sending alert")
        
        message = self.format_alert(job, match_data)
        
        # Send to Discord
        self.send_discord(message)
        
        # Send to Telegram
        self.send_telegram(message)
        
        self.update_state(AgentState.IDLE)
        self.log_activity("sent", f"Alert for {job.get('title')}")
    
    def format_alert(self, job: Dict, match_data: Dict) -> str:
        """Format alert message"""
        
        emoji = "🔥" if match_data.get("score", 0) > 0.7 else "⭐"
        
        message = f"""{emoji} **{job.get('title')}**

Platform: {job.get('platform')}
Budget: {job.get('budget')}
Match: {match_data.get('score', 0):.0%}

{'; '.join(match_data.get('reasons', [])[:2])}

🔗 {job.get('url')}"""
        
        return message
    
    def send_discord(self, message: str):
        """Send to Discord webhook"""
        
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        
        if not webhook_url:
            return
        
        try:
            requests.post(
                webhook_url,
                json={"content": message},
                timeout=10
            )
        except Exception as e:
            logger.error(f"Discord error: {e}")
    
    def send_telegram(self, message: str):
        """Send to Telegram"""
        
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            return
        
        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=10
            )
        except Exception as e:
            logger.error(f"Telegram error: {e}")


class ResearcherAgent(BaseAgent):
    """Researcher Agent - Client research"""
    
    def __init__(self):
        super().__init__("researcher", "researcher", "qwen2.5-coder:14b")
    
    def research_client(self, client_info: Dict) -> Dict:
        """Research client/company"""
        
        self.update_state(AgentState.BUSY, f"Researching {client_info.get('name')}")
        
        prompt = f""" freelance client:

Research thisClient: {client_info.get('name', 'Unknown')}
Platform: {client_info.get('platform')}
History: {client_info.get('history', 'Unknown')}

Find:
1. Payment reliability indicators
2. Communication style
3. Project types
4. Any red flags
5. Tips for winning

Respond in JSON:
{{"reliability": "high/medium/low", "tips": [], "red_flags": []}}"""
        
        response = self.generate(prompt, temperature=0.4)
        
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                research = json.loads(json_match.group())
            else:
                research = {"reliability": "unknown"}
        except:
            research = {"reliability": "unknown"}
        
        self.update_state(AgentState.IDLE)
        
        return research


class ArchiverAgent(BaseAgent):
    """Archiver Agent - Data storage"""
    
    def __init__(self):
        super().__init__("archiver", "archiver", "glm-4.7-flash:latest")
    
    def archive_job(self, job: Dict):
        """Archive job to history"""
        
        import hashlib
        
        job_id = job.get("id", hashlib.md5(str(job).encode()).hexdigest()[:10])
        
        archive_file = Path(CONFIG["data_dir"]) / "archive" / f"{job_id}.json"
        archive_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(archive_file, "w") as f:
            json.dump(job, f, indent=2)
        
        self.log_activity("archived", f"Job {job_id}")
    
    def get_job_history(self, job_id: str) -> Optional[Dict]:
        """Get archived job"""
        
        archive_file = Path(CONFIG["data_dir"]) / "archive" / f"{job_id}.json"
        
        if archive_file.exists():
            with open(archive_file) as f:
                return json.load(f)
        
        return None


class ManagerAgent(BaseAgent):
    """Manager Agent - Pipeline management"""
    
    def __init__(self):
        super().__init__("manager", "manager", "qwen2.5-coder:14b")
    
    def get_pipeline_stats(self) -> Dict:
        """Get pipeline statistics"""
        
        try:
            response = requests.get(
                f"{CONFIG['api_url']}/api/proposals/stats",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return {
            "total": 0,
            "pending": 0,
            "sent": 0,
            "won": 0
        }
    
    def recommend_next_actions(self) -> List[str]:
        """Recommend next actions"""
        
        stats = self.get_pipeline_stats()
        
        actions = []
        
        if stats.get("pending", 0) > 5:
            actions.append("Follow up on pending proposals")
        
        if stats.get("sent", 0) < stats.get("total", 0) * 0.5:
            actions.append("Write more proposals")
        
        if stats.get("won", 0) > 0:
            actions.append("Request testimonials from won clients")
        
        return actions or ["Keep hunting!"]


# Agent Registry

AGENTS = {
    "lead": LeadAgent,
    "scraper": ScraperAgent,
    "analyzer": AnalyzerAgent,
    "writer": WriterAgent,
    "qa": QA Agent,
    "scheduler": SchedulerAgent,
    "notifier": NotifierAgent,
    "researcher": ResearcherAgent,
    "archiver": ArchiverAgent,
    "manager": ManagerAgent
}


def get_agent(agent_id: str):
    """Get agent instance"""
    agent_class = AGENTS.get(agent_id)
    if agent_class:
        return agent_class()
    return None
```

## Next Steps

- [06-scheduler](./06-scheduler.md) - 5-minute orchestration
