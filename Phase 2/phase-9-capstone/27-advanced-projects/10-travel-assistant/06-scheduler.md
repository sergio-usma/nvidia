# Tourism Intelligence - Scheduler Agent

## Overview

The Scheduler Agent orchestrates the Tourism Intelligence Platform, running every 15 minutes to collect data, analyze trends, and generate reports. It coordinates all 8 AI agents and manages the data pipeline.

## Scheduler Implementation

```python
#!/usr/bin/env python3
"""
Scheduler Agent - Orchestrates Tourism Intelligence cycles
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
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/tourism-intel/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/tourism-intel/data",
    "logs_dir": "/opt/tourism-intel/logs",
    "api_url": "http://localhost:8095",
    "ollama_host": "http://localhost:11434",
    "poll_interval": 900,  # 15 minutes
    "cities": ["bogota", "medellin", "cartagena", "cali", "barranquilla", "santa_marta"]
}

os.makedirs(CONFIG["data_dir"], exist_ok=True)
os.makedirs(CONFIG["logs_dir"], exist_ok=True)


class SchedulerAgent:
    """Orchestrates the Tourism Intelligence platform"""
    
    def __init__(self):
        self.data_dir = Path(CONFIG["data_dir"])
        self.cycle_count = 0
        self.last_full_scrape = None
        
    def get_hour(self) -> int:
        """Get current hour"""
        return datetime.now().hour
    
    def should_scrape_hotels(self) -> bool:
        """Determine if hotel scraping should run"""
        hour = self.get_hour()
        
        # More frequent during day (6am - 11pm)
        if 6 <= hour <= 23:
            return True
        
        # Less frequent at night but still periodic
        return self.cycle_count % 4 == 0
    
    def should_analyze_sentiment(self) -> bool:
        """Determine if sentiment analysis should run"""
        # Run every 4 cycles (every hour)
        return self.cycle_count % 4 == 0
    
    def should_generate_report(self) -> bool:
        """Determine if report should be generated"""
        hour = self.get_hour()
        
        # Daily reports at 6am, 12pm, 6pm
        if hour in [6, 12, 18]:
            return True
        
        return False
    
    def call_agent(self, agent_id: str, endpoint: str, data: Dict = None) -> Dict:
        """Call an agent via API"""
        try:
            url = f"{CONFIG['api_url']}/api/agents/{agent_id}/{endpoint}"
            response = requests.post(url, json=data or {}, timeout=120)
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            logger.error(f"Agent call failed: {agent_id}/{endpoint} - {e}")
        
        return {"error": "failed"}
    
    def run_scrape_cycle(self):
        """Run hotel/airline/news scraping"""
        logger.info("=== Running Scrape Cycle ===")
        
        results = {
            "hotels": [],
            "airlines": [],
            "news": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Scrape each city
        for city in CONFIG["cities"]:
            logger.info(f"Scraping hotels in {city}...")
            
            response = self.call_agent(
                "researcher",
                "research_hotels",
                {"city": city}
            )
            
            if response and "data" in response:
                results["hotels"].append({
                    "city": city,
                    "data": response["data"]
                })
        
        # Scrape airlines
        logger.info("Scraping airlines...")
        # Airline scraping handled by researcher agent
        
        # Scrape news
        logger.info("Scraping news...")
        # News scraping handled by researcher agent
        
        return results
    
    def run_sentiment_cycle(self):
        """Run sentiment analysis on recent reviews"""
        logger.info("=== Running Sentiment Cycle ===")
        
        # Load recent hotels
        hotels_file = self.data_dir / "hotels" / "latest.json"
        
        if not hotels_file.exists():
            logger.warning("No hotel data for sentiment analysis")
            return None
        
        with open(hotels_file) as f:
            hotels = json.load(f)
        
        # Analyze sample
        sample_hotels = hotels[:10]
        
        for hotel in sample_hotels:
            response = self.call_agent(
                "sentiment",
                "analyze_reviews",
                {"reviews": hotel.get("reviews", [])}
            )
            
            if response:
                hotel["sentiment"] = response.get("data", {})
        
        # Save updated data
        with open(hotels_file, "w") as f:
            json.dump(hotels, f, indent=2)
        
        return sample_hotels
    
    def run_analytics_cycle(self):
        """Run trend detection"""
        logger.info("=== Running Analytics Cycle ===")
        
        # Load all recent data
        data = self.load_recent_data()
        
        response = self.call_agent(
            "analytics",
            "detect_trends",
            {"data": data}
        )
        
        if response:
            # Save trends
            trends_file = self.data_dir / "trends" / f"{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            trends_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(trends_file, "w") as f:
                json.dump(response, f, indent=2)
        
        return response
    
    def run_alert_cycle(self):
        """Check for alerts"""
        logger.info("=== Running Alert Cycle ===")
        
        # Load latest data
        hotels_file = self.data_dir / "hotels" / "latest.json"
        
        if not hotels_file.exists():
            return []
        
        with open(hotels_file) as f:
            hotels = json.load(f)
        
        alerts = []
        
        for hotel in hotels:
            response = self.call_agent(
                "alert",
                "check_alerts",
                hotel
            )
            
            if response and isinstance(response, list):
                alerts.extend(response)
        
        if alerts:
            logger.warning(f"Found {len(alerts)} alerts")
            
            # Send to Discord if configured
            self.send_alerts(alerts)
        
        return alerts
    
    def run_report_cycle(self):
        """Generate intelligence report"""
        logger.info("=== Running Report Cycle ===")
        
        # Gather data for report
        data = self.load_recent_data()
        
        # Determine report type
        hour = self.get_hour()
        
        if hour in [6, 18]:
            report_type = "daily"
        else:
            report_type = "weekly"
        
        response = self.call_agent(
            "reporter",
            "generate_report",
            {"data": data, "type": report_type}
        )
        
        if response:
            # Save report
            reports_dir = self.data_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = reports_dir / f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            
            with open(report_file, "w") as f:
                f.write(response if isinstance(response, str) else str(response))
            
            logger.info(f"Report saved: {report_file}")
        
        return response
    
    def load_recent_data(self) -> Dict:
        """Load recent data from all sources"""
        data = {
            "hotels": [],
            "trends": [],
            "alerts": []
        }
        
        # Load hotels
        hotels_file = self.data_dir / "hotels" / "latest.json"
        if hotels_file.exists():
            with open(hotels_file) as f:
                data["hotels"] = json.load(f)
        
        # Load latest trends
        trends_dir = self.data_dir / "trends"
        if trends_dir.exists():
            trends_files = sorted(trends_dir.glob("*.json"))[-3:]
            for tf in trends_files:
                with open(tf) as f:
                    data["trends"].append(json.load(f))
        
        return data
    
    def send_alerts(self, alerts: List[Dict]):
        """Send alerts to Discord/webhook"""
        try:
            webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
            
            if not webhook_url:
                return
            
            message = "🚨 **Tourism Intelligence Alerts**\n\n"
            
            for alert in alerts[:10]:
                severity = alert.get("severity", "MEDIUM")
                emoji = "🔴" if severity == "HIGH" else "🟡"
                message += f"{emoji} {alert.get('type')}: {alert.get('message')}\n"
            
            requests.post(webhook_url, json={"content": message}, timeout=10)
            
        except Exception as e:
            logger.error(f"Alert notification failed: {e}")
    
    def run_cycle(self):
        """Run one complete scheduling cycle"""
        self.cycle_count += 1
        cycle_start = datetime.now()
        
        logger.info(f"=== Cycle {self.cycle_count} Started at {cycle_start.strftime('%H:%M:%S')} ===")
        
        cycle_results = {
            "scrape": False,
            "sentiment": False,
            "analytics": False,
            "alerts": False,
            "report": False
        }
        
        # Always scrape (main data collection)
        if self.should_scrape_hotels():
            self.run_scrape_cycle()
            cycle_results["scrape"] = True
        
        # Sentiment analysis (hourly)
        if self.should_analyze_sentiment():
            self.run_sentiment_cycle()
            cycle_results["sentiment"] = True
        
        # Analytics (every 2 hours)
        if self.cycle_count % 8 == 0:
            self.run_analytics_cycle()
            cycle_results["analytics"] = True
        
        # Alerts (every cycle)
        alerts = self.run_alert_cycle()
        if alerts:
            cycle_results["alerts"] = True
        
        # Reports (twice daily)
        if self.should_generate_report():
            self.run_report_cycle()
            cycle_results["report"] = True
        
        # Log cycle completion
        duration = (datetime.now() - cycle_start).total_seconds()
        
        logger.info(f"Cycle {self.cycle_count} complete in {duration:.1f}s")
        logger.info(f"Results: {cycle_results}")
        
        # Save cycle stats
        self.save_cycle_stats(cycle_results, duration)
        
        return cycle_results
    
    def save_cycle_stats(self, results: Dict, duration: float):
        """Save cycle statistics"""
        stats_file = self.data_dir / "stats.json"
        
        stats = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "results": results
        }
        
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
    
    def run_continuous(self):
        """Run scheduler continuously"""
        logger.info(f"Scheduler started - polling every {CONFIG['poll_interval']}s")
        logger.info(f"Monitoring {len(CONFIG['cities'])} cities")
        
        # Initial run
        self.run_cycle()
        
        while True:
            try:
                # Sleep until next cycle
                time.sleep(CONFIG["poll_interval"])
                
                # Run cycle
                self.run_cycle()
                
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Brief pause on error


def get_next_cycle_time() -> datetime:
    """Calculate next cycle time"""
    now = datetime.now()
    next_cycle = now + timedelta(seconds=CONFIG["poll_interval"])
    
    # Round to nearest 15 minutes
    minute = (next_cycle.minute // 15) * 15
    next_cycle = next_cycle.replace(minute=minute, second=0, microsecond=0)
    
    return next_cycle


if __name__ == "__main__":
    scheduler = SchedulerAgent()
    scheduler.run_continuous()
```

## Cycle Timing

| Time | Task | Frequency |
|------|------|-----------|
| Every cycle (15 min) | Scrape hotels | Always |
| Every cycle (15 min) | Check alerts | Always |
| Every cycle (15 min) | Scrape airlines | Day only |
| Hourly | Sentiment analysis | Every 4 cycles |
| Every 2 hours | Trend detection | Every 8 cycles |
| 6 AM, 6 PM | Daily report | Twice daily |
| Weekly | Full weekly report | Every 672 cycles |

## API Endpoints

```python
# Add to Flask app

@app.route("/api/scheduler/status", methods=["GET"])
def scheduler_status():
    """Get scheduler status"""
    return jsonify({
        "cycle": scheduler.cycle_count,
        "next_run": get_next_cycle_time().isoformat(),
        "cities": CONFIG["cities"]
    })


@app.route("/api/scheduler/run", methods=["POST"])
def force_cycle():
    """Force run a cycle"""
    data = request.get_json()
    task = data.get("task", "all")
    
    if task == "scrape":
        result = scheduler.run_scrape_cycle()
    elif task == "sentiment":
        result = scheduler.run_sentiment_cycle()
    elif task == "analytics":
        result = scheduler.run_analytics_cycle()
    elif task == "report":
        result = scheduler.run_report_cycle()
    else:
        result = scheduler.run_cycle()
    
    return jsonify({"status": "completed", "result": result})


@app.route("/api/scheduler/cycle/<task>", methods=["POST"])
def run_specific_task(task: str):
    """Run specific task"""
    result = scheduler.run_cycle()
    return jsonify(result)
```

## Cron Alternative

```bash
# Alternative: Run via cron
crontab -e

# Add: Run every 15 minutes
*/15 * * * * /opt/tourism-intel/venv/bin/python /opt/tourism-intel/scheduler/main.py >> /opt/tourism-intel/logs/scheduler.log 2>&1
```

## Monitoring

```bash
# Check scheduler logs
tail -f /opt/tourism-intel/logs/scheduler.log

# Check cycle stats
cat /opt/tourism-intel/data/stats.json

# Check recent reports
ls -la /opt/tourism-intel/data/reports/
```

## Next Steps

- [07-sheets](./07-sheets.md) - Google Sheets integration
