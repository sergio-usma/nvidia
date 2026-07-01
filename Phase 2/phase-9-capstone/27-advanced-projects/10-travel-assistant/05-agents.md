# Tourism Intelligence - AI Agents

## Overview

The platform uses 8 specialized AI agents to collect, analyze, and report on tourism data.

## Agent Implementations

```python
#!/usr/bin/env python3
"""
AI Agents for Tourism Intelligence Platform
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "ollama_host": "http://localhost:11434",
    "api_url": "http://localhost:8095"
}


class BaseAgent:
    """Base agent class"""
    
    def __init__(self, agent_id: str, role: str, model: str):
        self.agent_id = agent_id
        self.role = role
        self.model = model
        self.ollama = CONFIG["ollama_host"]
        self.current_task = None
        
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Generate response"""
        
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
                timeout=120
            )
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return ""
    
    def log_activity(self, action: str, detail: str):
        """Log agent activity"""
        try:
            requests.post(
                f"{CONFIG['api_url']}/activity",
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
            pass
    
    def update_status(self, status: str, task: str = None):
        """Update agent status"""
        try:
            requests.post(
                f"{CONFIG['api_url']}/agents/{self.agent_id}/status",
                json={"status": status, "task": task or self.current_task},
                timeout=5
            )
        except:
            pass


class LeadAgent(BaseAgent):
    """Lead Agent - Orchestrates all tasks"""
    
    def __init__(self):
        super().__init__("lead", "lead", "qwen2.5-coder:14b")
    
    def analyze_task(self, task: Dict) -> Dict:
        """Analyze incoming task and delegate"""
        
        self.current_task = task.get("id")
        self.update_status("analyzing", task.get("title"))
        
        prompt = f"""You are the Lead Agent for a Tourism Intelligence Platform in Colombia.

Analyze this task and delegate to the right specialist:

Task: {task.get('title')}
Description: {task.get('description')}
Type: {task.get('type', 'general')}

Available specialists:
- researcher: Data collection and scraping
- sentiment: Review and sentiment analysis  
- analytics: Trend detection and patterns
- reporter: Report generation

Determine:
1. Priority (1-5)
2. Which specialist should handle it
3. Approach

Respond in JSON:
{{
  "priority": 1-5,
  "specialist": "researcher/sentiment/analytics/reporter",
  "approach": "brief approach"
}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        # Parse response
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"specialist": "researcher", "priority": 3}
        except:
            result = {"specialist": "researcher", "priority": 3}
        
        self.update_status("idle")
        self.log_activity("delegated", f"To {result.get('specialist')}")
        
        return result


class ResearcherAgent(BaseAgent):
    """Researcher Agent - Data collection"""
    
    def __init__(self):
        super().__init__("researcher", "researcher", "qwen2.5-coder:14b")
    
    def research_hotels(self, city: str) -> Dict:
        """Research hotels in city"""
        
        self.current_task = f"research_{city}"
        self.update_status("researching", f"Researching {city}")
        
        prompt = f"""Research top hotels in {city}, Colombia.

Provide:
1. List of top 10 hotels with their names
2. Typical price ranges
3. Key amenities
4. Tourist attractions nearby

Format as JSON:
{{
  "city": "{city}",
  "hotels": [
    {{"name": "...", "stars": 5, "price_range": "$$$", "amenities": []}}
  ],
  "tourist_spots": []
}}"""
        
        response = self.generate(prompt, temperature=0.4)
        
        self.update_status("idle")
        self.log_activity("completed", f"Researched {city}")
        
        return {"city": city, "data": response}


class SentimentAgent(BaseAgent):
    """Sentiment Agent - Review analysis"""
    
    def __init__(self):
        super().__init__("sentiment", "sentiment", "llama3.2:3b")
    
    def analyze_reviews(self, reviews: list) -> Dict:
        """Analyze sentiment of reviews"""
        
        self.current_task = "analyze_sentiment"
        self.update_status("analyzing", "Analyzing reviews")
        
        combined_reviews = "\n".join([r.get("text", "")[:200] for r in reviews[:10]])
        
        prompt = f"""Analyze these hotel reviews and provide:

1. Overall sentiment (positive/negative/neutral)
2. Key themes
3. Main complaints
4. Main praise

Reviews:
{combined_reviews}

Respond in JSON:
{{
  "sentiment": "positive/negative/neutral",
  "score": 1-10,
  "themes": [],
  "complaints": [],
  "praise": []
}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        self.update_status("idle")
        self.log_activity("completed", "Analyzed reviews")
        
        return {"data": response}


class AnalyticsAgent(BaseAgent):
    """Analytics Agent - Trend detection"""
    
    def __init__(self):
        super().__init__("analytics", "analytics", "deepseek-r1:8b")
    
    def detect_trends(self, data: Dict) -> Dict:
        """Detect trends in data"""
        
        self.current_task = "detect_trends"
        self.update_status("analyzing", "Detecting trends")
        
        prompt = f"""Analyze this tourism data and identify:

1. Emerging trends
2. Seasonal patterns
3. Price trends
4. Booking patterns

Data: {json.dumps(data)[:2000]}

Respond in JSON:
{{
  "trends": [],
  "patterns": [],
  "insights": []
}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        self.update_status("idle")
        self.log_activity("completed", "Detected trends")
        
        return {"data": response}


class ReporterAgent(BaseAgent):
    """Reporter Agent - Report generation"""
    
    def __init__(self):
        super().__init__("reporter", "reporter", "llama3.2:3b")
    
    def generate_report(self, data: Dict, report_type: str = "daily") -> str:
        """Generate intelligence report"""
        
        self.current_task = f"report_{report_type}"
        self.update_status("writing", f"Writing {report_type} report")
        
        if report_type == "daily":
            prompt = f"""Generate a daily tourism intelligence report for Colombia.

Include:
1. Today's top hotel availability
2. Price changes
3. Sentiment summary
4. News highlights

Data: {json.dumps(data)[:3000]}

Write in Spanish, professional tone."""
            
        elif report_type == "weekly":
            prompt = f"""Generate a weekly tourism intelligence report for Colombia.

Include:
1. Week summary
2. Top performing hotels
3. Trend analysis
4. Recommendations

Data: {json.dumps(data)[:5000]}

Write in Spanish, executive summary style."""
        
        response = self.generate(prompt, temperature=0.5, max_tokens=3000)
        
        self.update_status("idle")
        self.log_activity("completed", f"Generated {report_type} report")
        
        return response


class SchedulerAgent(BaseAgent):
    """Scheduler Agent - Orchestrates cycles"""
    
    def __init__(self):
        super().__init__("scheduler", "scheduler", "glm-4.7-flash:latest")
    
    def plan_cycle(self) -> Dict:
        """Plan next processing cycle"""
        
        prompt = """Plan the next 15-minute cycle for the tourism intelligence platform.

Tasks available:
- Scrape hotels (high priority)
- Check availability (high priority)
- Analyze sentiment (medium)
- Detect trends (low)
- Generate reports (daily)

Current time: {datetime.now().strftime('%H:%M')}

What should run in this cycle?

Respond in JSON:
{{
  "tasks": ["task1", "task2"],
  "reasoning": "..."
}}"""
        
        response = self.generate(prompt, temperature=0.3)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                plan = {"tasks": ["scrape_hotels", "check_availability"]}
        except:
            plan = {"tasks": ["scrape_hotels", "check_availability"]}
        
        return plan


class DataManagerAgent(BaseAgent):
    """Data Manager - Storage and retrieval"""
    
    def __init__(self):
        super().__init__("data_manager", "data_manager", "qwen2.5-coder:14b")
    
    def store_data(self, data_type: str, data: Dict) -> bool:
        """Store data in sheets"""
        
        self.current_task = f"store_{data_type}"
        self.update_status("storing", f"Storing {data_type}")
        
        try:
            response = requests.post(
                f"{CONFIG['api_url']}/sheets/{data_type}",
                json=data,
                timeout=30
            )
            
            self.update_status("idle")
            self.log_activity("stored", f"{data_type}")
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Storage error: {e}")
            return False


class AlertAgent(BaseAgent):
    """Alert Agent - Anomaly detection"""
    
    def __init__(self):
        super().__init__("alert", "alert", "deepseek-r1:8b")
    
    def check_alerts(self, data: Dict) -> List[Dict]:
        """Check for anomalies and alerts"""
        
        self.current_task = "check_alerts"
        self.update_status("monitoring", "Checking for alerts")
        
        alerts = []
        
        # Check availability
        rooms = data.get("rooms_available", 10)
        if rooms < 3:
            alerts.append({
                "type": "LOW_AVAILABILITY",
                "severity": "HIGH",
                "message": f"Only {rooms} rooms available"
            })
        
        # Check price
        price_change = data.get("price_change", 0)
        if abs(price_change) > 100000:
            alerts.append({
                "type": "PRICE_CHANGE",
                "severity": "MEDIUM",
                "message": f"Price changed by {price_change} COP"
            })
        
        # Check sentiment
        sentiment = data.get("sentiment", {})
        neg_ratio = sentiment.get("sentiment_ratio", {}).get("negative", 0)
        if neg_ratio > 30:
            alerts.append({
                "type": "NEGATIVE_SENTIMENT",
                "severity": "HIGH",
                "message": f"{neg_ratio}% negative reviews"
            })
        
        self.update_status("idle")
        
        if alerts:
            self.log_activity("alerts", f"Found {len(alerts)} alerts")
        
        return alerts


# Agent Registry
AGENTS = {
    "lead": LeadAgent,
    "researcher": ResearcherAgent,
    "sentiment": SentimentAgent,
    "analytics": AnalyticsAgent,
    "reporter": ReporterAgent,
    "scheduler": SchedulerAgent,
    "data_manager": DataManagerAgent,
    "alert": AlertAgent
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
@app.route("/api/agents/<agent_id>/run", methods=["POST"])
def run_agent(agent_id: str):
    """Run specific agent task"""
    data = request.get_json()
    
    agent = get_agent(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    
    try:
        if agent_id == "researcher":
            result = agent.research_hotels(data.get("city"))
        elif agent_id == "sentiment":
            result = agent.analyze_reviews(data.get("reviews", []))
        elif agent_id == "analytics":
            result = agent.detect_trends(data.get("data", {}))
        elif agent_id == "reporter":
            result = agent.generate_report(data.get("data", {}), data.get("type", "daily"))
        else:
            result = {"error": "Unknown action"}
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## Next Steps

- [06-scheduler](./06-scheduler.md) - 15-minute orchestration
