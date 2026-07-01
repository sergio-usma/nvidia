# Freelance Hunter - Scheduler Agent

## Overview

The Scheduler Agent orchestrates the Freelance Hunter platform with 5-minute monitoring cycles. It coordinates all 10 AI agents, manages the pipeline, and ensures continuous job discovery.

## Scheduler Implementation

```python
#!/usr/bin/env python3
"""
Scheduler Agent - Orchestrates Freelance Hunter cycles
Runs every 5 minutes
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
        logging.FileHandler('/opt/freelance-hunter/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/freelance-hunter/data",
    "logs_dir": "/opt/freelance-hunter/logs",
    "api_url": "http://localhost:8096",
    "ollama_host": "http://localhost:11434",
    "poll_interval": 300,  # 5 minutes
    "platforms": ["remoteok", "weworkremotely", "upwork", "freelancer", "linkedin"]
}

os.makedirs(CONFIG["data_dir"], exist_ok=True)
os.makedirs(CONFIG["logs_dir"], exist_ok=True)


class SchedulerAgent:
    """Orchestrates the Freelance Hunter platform"""
    
    def __init__(self):
        self.data_dir = Path(CONFIG["data_dir"])
        self.cycle_count = 0
        self.hour = datetime.now().hour
        self.platforms = CONFIG["platforms"]
    
    def get_hour(self) -> int:
        """Get current hour"""
        return datetime.now().hour
    
    def should_scrape(self) -> bool:
        """Determine if scraping should run"""
        # Scrape every 2 cycles (10 min) during active hours
        if 6 <= self.get_hour() <= 23:
            return self.cycle_count % 2 == 0
        # Less frequent at night
        return self.cycle_count % 6 == 0
    
    def should_analyze(self) -> bool:
        """Run analysis every cycle"""
        return True
    
    def should_generate_proposals(self) -> bool:
        """Generate proposals for matches"""
        # Run every cycle
        return True
    
    def should_notify(self) -> bool:
        """Send notifications for hot jobs"""
        return self.cycle_count % 1 == 0
    
    def should_research_clients(self) -> bool:
        """Research clients periodically"""
        return self.cycle_count % 10 == 0
    
    def should_archive(self) -> bool:
        """Archive old jobs"""
        return self.cycle_count % 4 == 0
    
    def call_api(self, endpoint: str, data: Dict = None, timeout: int = 60) -> Dict:
        """Call API endpoint"""
        try:
            url = f"{CONFIG['api_url']}{endpoint}"
            
            if data:
                response = requests.post(url, json=data, timeout=timeout)
            else:
                response = requests.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            logger.error(f"API call failed: {endpoint} - {e}")
        
        return {"error": "failed"}
    
    def run_scrape_cycle(self):
        """Run scraping cycle"""
        
        if not self.should_scrape():
            logger.info("Skipping scrape (not due)")
            return {"status": "skipped"}
        
        logger.info("=== Running Scrape Cycle ===")
        
        # Call scraper API
        result = self.call_api(
            "/api/scraper/run",
            {"platforms": self.platforms},
            timeout=180
        )
        
        if result.get("error"):
            logger.error(f"Scraping failed: {result}")
            return {"status": "failed", "error": result.get("error")}
        
        logger.info(f"Scraping complete: {result.get('count', 0)} jobs")
        
        return {
            "status": "success",
            "jobs_found": result.get("count", 0)
        }
    
    def run_analysis_cycle(self):
        """Run job analysis"""
        
        if not self.should_analyze():
            return {"status": "skipped"}
        
        logger.info("=== Running Analysis Cycle ===")
        
        # Get jobs
        jobs_result = self.call_api("/api/jobs")
        jobs = jobs_result.get("jobs", [])
        
        if not jobs:
            logger.info("No jobs to analyze")
            return {"status": "skipped", "reason": "no_jobs"}
        
        # Match jobs
        match_result = self.call_api(
            "/api/match",
            {"jobs": jobs},
            timeout=180
        )
        
        matches = match_result.get("matches", [])
        
        # Filter hot matches (score > 0.7)
        hot_matches = [m for m in matches if m.get("score", 0) > 0.7]
        
        logger.info(f"Analysis complete: {len(matches)} matches, {len(hot_matches)} hot")
        
        return {
            "status": "success",
            "total_matches": len(matches),
            "hot_matches": len(hot_matches)
        }
    
    def run_proposal_cycle(self):
        """Generate proposals"""
        
        if not self.should_generate_proposals():
            return {"status": "skipped"}
        
        logger.info("=== Running Proposal Cycle ===")
        
        # Get hot matches
        matches_result = self.call_api("/api/match", {"limit": 10})
        matches = matches_result.get("matches", [])
        
        if not matches:
            logger.info("No matches for proposals")
            return {"status": "skipped", "reason": "no_matches"}
        
        proposals_created = 0
        
        for match in matches[:5]:  # Limit to 5 per cycle
            # Generate proposal
            job = match.get("job_data", {})
            
            if not job:
                continue
            
            proposal_result = self.call_api(
                "/api/proposals/generate",
                {"job": job, "match": match},
                timeout=120
            )
            
            if proposal_result.get("id"):
                proposals_created += 1
        
        logger.info(f"Created {proposals_created} proposals")
        
        return {
            "status": "success",
            "proposals_created": proposals_created
        }
    
    def run_notification_cycle(self):
        """Send notifications"""
        
        if not self.should_notify():
            return {"status": "skipped"}
        
        logger.info("=== Running Notification Cycle ===")
        
        # Get hot jobs
        hot_result = self.call_api("/api/hot", timeout=30)
        hot_jobs = hot_result.get("jobs", [])
        
        if not hot_jobs:
            return {"status": "skipped", "reason": "no_hot_jobs"}
        
        # Send notifications
        notify_result = self.call_api(
            "/api/notifications/send",
            {"jobs": hot_jobs},
            timeout=60
        )
        
        logger.info(f"Sent {notify_result.get('sent', 0)} notifications")
        
        return {
            "status": "success",
            "sent": notify_result.get("sent", 0)
        }
    
    def run_research_cycle(self):
        """Research high-value clients"""
        
        if not self.should_research_clients():
            return {"status": "skipped"}
        
        logger.info("=== Running Research Cycle ===")
        
        # Get high-budget jobs
        jobs_result = self.call_api("/api/jobs?min_budget=1000")
        jobs = jobs_result.get("jobs", [])
        
        researched = 0
        
        for job in jobs[:5]:
            client_info = {
                "name": job.get("client_name", "Unknown"),
                "platform": job.get("platform"),
                "history": job.get("client_history", "")
            }
            
            self.call_api(
                "/api/research",
                {"client": client_info},
                timeout=60
            )
            
            researched += 1
        
        return {
            "status": "success",
            "researched": researched
        }
    
    def run_archive_cycle(self):
        """Archive old jobs"""
        
        if not self.should_archive():
            return {"status": "skipped"}
        
        logger.info("=== Running Archive Cycle ===")
        
        result = self.call_api("/api/archive/cleanup", timeout=30)
        
        return {
            "status": "success",
            "archived": result.get("archived", 0)
        }
    
    def run_cycle(self):
        """Run one complete scheduling cycle"""
        
        self.cycle_count += 1
        self.hour = self.get_hour()
        
        cycle_start = datetime.now()
        
        logger.info(f"=== Cycle {self.cycle_count} Started at {cycle_start.strftime('%H:%M:%S')} ===")
        
        results = {
            "scrape": None,
            "analysis": None,
            "proposals": None,
            "notifications": None,
            "research": None,
            "archive": None
        }
        
        # 1. Scrape new jobs
        results["scrape"] = self.run_scrape_cycle()
        
        # 2. Analyze jobs
        results["analysis"] = self.run_analysis_cycle()
        
        # 3. Generate proposals
        results["proposals"] = self.run_proposal_cycle()
        
        # 4. Send notifications
        results["notifications"] = self.run_notification_cycle()
        
        # 5. Research clients (every ~50 min)
        results["research"] = self.run_research_cycle()
        
        # 6. Archive (every ~20 min)
        results["archive"] = self.run_archive_cycle()
        
        # Log completion
        duration = (datetime.now() - cycle_start).total_seconds()
        
        logger.info(f"Cycle {self.cycle_count} complete in {duration:.1f}s")
        
        # Log stats
        self.log_stats(results, duration)
        
        return results
    
    def log_stats(self, results: Dict, duration: float):
        """Log cycle statistics"""
        
        stats = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "results": {
                k: v.get("status") if v else "none"
                for k, v in results.items()
            },
            "counts": {
                "scrape": results.get("scrape", {}).get("jobs_found", 0),
                "matches": results.get("analysis", {}).get("total_matches", 0),
                "proposals": results.get("proposals", {}).get("proposals_created", 0),
                "notifications": results.get("notifications", {}).get("sent", 0)
            }
        }
        
        # Save stats
        stats_file = self.data_dir / "stats.json"
        
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
        
        # Get pipeline stats
        pipeline = self.call_api("/api/proposals/stats", timeout=10)
        
        logger.info(f"Pipeline: {pipeline}")
        
        return stats
    
    def run_continuous(self):
        """Run scheduler continuously"""
        
        logger.info(f"Scheduler started - polling every {CONFIG['poll_interval']}s")
        logger.info(f"Monitoring {len(self.platforms)} platforms")
        
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
                time.sleep(30)  # Brief pause on error


def get_next_cycle_time() -> datetime:
    """Calculate next cycle time"""
    now = datetime.now()
    next_cycle = now + timedelta(seconds=CONFIG["poll_interval"])
    
    return next_cycle


if __name__ == "__main__":
    scheduler = SchedulerAgent()
    scheduler.run_continuous()
```

## Cycle Timing

| Time | Task | Frequency |
|------|------|-----------|
| Every cycle (5 min) | Analyze jobs | Always |
| Every cycle (5 min) | Generate proposals | Always |
| Every cycle (5 min) | Send notifications | Always |
| Every 2 cycles (10 min) | Scrape platforms | Day only |
| Every 10 cycles (50 min) | Research clients | Periodic |
| Every 4 cycles (20 min) | Archive jobs | Periodic |

## Daily Schedule

| Time | Tasks |
|------|-------|
| 6:00 AM | Full scrape, analyze, generate proposals |
| 6:00-23:00 | 5-min cycles with scraping every 10 min |
| 23:00-6:00 | Reduced frequency, no scraping |
| 6:00 PM | Daily summary report |

## API Endpoints

```python
# Scheduler API endpoints

@app.route("/api/scheduler/status", methods=["GET"])
def scheduler_status():
    """Get scheduler status"""
    return jsonify({
        "cycle": scheduler.cycle_count,
        "next_run": get_next_cycle_time().isoformat(),
        "platforms": CONFIG["platforms"]
    })


@app.route("/api/scheduler/run", methods=["POST"])
def force_run():
    """Force run a cycle"""
    data = request.get_json()
    task = data.get("task", "all")
    
    if task == "scrape":
        result = scheduler.run_scrape_cycle()
    elif task == "analyze":
        result = scheduler.run_analysis_cycle()
    elif task == "proposals":
        result = scheduler.run_proposal_cycle()
    elif task == "notify":
        result = scheduler.run_notification_cycle()
    else:
        result = scheduler.run_cycle()
    
    return jsonify(result)


@app.route("/api/scheduler/cycle/<task>", methods=["POST"])
def run_specific_task(task: str):
    """Run specific task only"""
    result = scheduler.run_cycle()
    return jsonify(result)
```

## Cron Alternative

```bash
# Alternative: Run via cron
crontab -e

# Add: Run every 5 minutes
*/5 * * * * /opt/freelance-hunter/venv/bin/python /opt/freelance-hunter/scheduler/main.py >> /opt/freelance-hunter/logs/scheduler.log 2>&1
```

## Monitoring

```bash
# Check scheduler logs
tail -f /opt/freelance-hunter/logs/scheduler.log

# Check cycle stats
cat /opt/freelance-hunter/data/stats.json

# Check pipeline
curl http://localhost:8096/api/proposals/stats

# Check hot jobs
curl http://localhost:8096/api/hot
```

## Performance Tuning

```python
# Adjust cycle timing

# More frequent scraping
CONFIG["scrape_interval"] = 1  # Every cycle

# More proposals
CONFIG["max_proposals_per_cycle"] = 10

# Less notifications
CONFIG["notify_threshold"] = 0.8  # Only >80% match
```

## Next Steps

- [07-notifications](./07-notifications.md) - Discord/Email alerts
