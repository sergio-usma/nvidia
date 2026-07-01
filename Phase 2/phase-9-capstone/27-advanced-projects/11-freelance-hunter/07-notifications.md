# Freelance Hunter - Notifications System

## Overview

The notifications system delivers real-time alerts for hot job opportunities via Discord, Telegram, and Email. It filters opportunities based on match score and user preferences.

## Notification Configuration

```python
# config/notifications.py

NOTIFICATION_CONFIG = {
    "discord": {
        "enabled": True,
        "webhook_url": os.environ.get("DISCORD_WEBHOOK_URL", ""),
        "mentions": {
            "enabled": True,
            "users": ["@user"],  # Discord user mentions
            "roles": []  # Discord role mentions
        },
        "embed_color": 0x00FF88,  # Green
        "throttle_minutes": 5
    },
    "telegram": {
        "enabled": True,
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "chat_ids": os.environ.get("TELEGRAM_CHAT_IDS", "").split(","),
        "parse_mode": "Markdown",
        "throttle_minutes": 3
    },
    "email": {
        "enabled": True,
        "smtp_host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "smtp_user": os.environ.get("SMTP_USER", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "from_email": os.environ.get("FROM_EMAIL", "alerts@freelance-hunter.local"),
        "to_emails": os.environ.get("TO_EMAILS", "").split(","),
        "digest_enabled": True,
        "digest_interval_hours": 24
    },
    "thresholds": {
        "hot_job_score": 0.7,      # Send immediately for >70% match
        "warm_job_score": 0.5,      # Include in digest
        "min_budget": 500,           # Minimum budget to notify
        "max_age_hours": 24          # Don't notify for old jobs
    }
}


ALERT_TEMPLATES = {
    "hot_job": {
        "emoji": "🔥",
        "title": "HOT JOB ALERT",
        "priority": "high"
    },
    "new_match": {
        "emoji": "⭐",
        "title": "New Job Match",
        "priority": "medium"
    },
    "proposal_won": {
        "emoji": "🎉",
        "title": "Proposal Accepted!",
        "priority": "high"
    },
    "proposal_lost": {
        "emoji": "😢",
        "title": "Proposal Not Selected",
        "priority": "low"
    },
    "daily_digest": {
        "emoji": "📋",
        "title": "Daily Digest",
        "priority": "low"
    }
}
```

## Notification Implementation

```python
#!/usr/bin/env python3
"""
Notification System - Discord, Telegram, Email Alerts
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/freelance-hunter/data",
    "notifications_dir": "/opt/freelance-hunter/data/notifications",
    "throttle_file": "/opt/freelance-hunter/config/throttle.json"
}

os.makedirs(CONFIG["notifications_dir"], exist_ok=True)


@dataclass
class JobAlert:
    """Job alert data"""
    job_id: str
    platform: str
    title: str
    url: str
    budget: str
    match_score: float
    skills: List[str]
    reasons: List[str]
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DiscordNotifier:
    """Discord notifications"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
        self.throttle_minutes = 5
        self.last_sent = {}
    
    def should_send(self, alert_type: str) -> bool:
        """Check if should send (throttling)"""
        
        key = f"discord_{alert_type}"
        last = self.last_sent.get(key)
        
        if not last:
            return True
        
        elapsed = (datetime.now() - last).total_seconds() / 60
        
        return elapsed >= self.throttle_minutes
    
    def send(self, alert: JobAlert, mention: str = None):
        """Send Discord notification"""
        
        if not self.webhook_url:
            logger.warning("Discord webhook not configured")
            return False
        
        if not self.should_send("hot_job"):
            logger.info("Discord throttled")
            return False
        
        # Build embed
        embed = self.build_embed(alert)
        
        # Build payload
        content = ""
        if mention:
            content = mention
        
        payload = {
            "content": content,
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                self.last_sent["discord_hot_job"] = datetime.now()
                logger.info(f"Discord notification sent for {alert.title}")
                return True
            else:
                logger.error(f"Discord error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Discord send error: {e}")
        
        return False
    
    def build_embed(self, alert: JobAlert) -> Dict:
        """Build Discord embed"""
        
        score_color = 0xFF0000 if alert.match_score > 0.8 else \
                      0xFFA500 if alert.match_score > 0.6 else 0x00FF00
        
        embed = {
            "title": f"🔥 {alert.title[:200]}",
            "url": alert.url,
            "color": score_color,
            "fields": [
                {
                    "name": "Platform",
                    "value": alert.platform.upper(),
                    "inline": True
                },
                {
                    "name": "Budget",
                    "value": alert.budget or "Negotiable",
                    "inline": True
                },
                {
                    "name": "Match",
                    "value": f"{alert.match_score:.0%}",
                    "inline": True
                },
                {
                    "name": "Why",
                    "value": ", ".join(alert.reasons[:3])[:500] or "Great opportunity!",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Freelance Hunter • {datetime.now().strftime('%H:%M')}"
            }
        }
        
        return embed


class TelegramNotifier:
    """Telegram notifications"""
    
    def __init__(self, bot_token: str = None, chat_ids: List[str] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_ids = chat_ids or os.environ.get("TELEGRAM_CHAT_IDS", "").split(",")
        self.throttle_minutes = 3
    
    def send(self, alert: JobAlert):
        """Send Telegram notification"""
        
        if not self.bot_token:
            logger.warning("Telegram bot not configured")
            return False
        
        message = self.format_message(alert)
        
        for chat_id in self.chat_ids:
            if not chat_id:
                continue
            
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id.strip(),
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Telegram sent to {chat_id}")
                else:
                    logger.error(f"Telegram error: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Telegram send error: {e}")
        
        return True
    
    def format_message(self, alert: JobAlert) -> str:
        """Format Telegram message"""
        
        emoji = "🔥" if alert.match_score > 0.7 else "⭐"
        
        message = f"""{emoji} **{alert.title[:100]}**

Platform: {alert.platform.upper()}
Budget: {alert.budget or 'Negotiable'}
Match: {alert.match_score:.0%}

Why: {', '.join(alert.reasons[:2]) if alert.reasons else 'Great fit!'}

🔗 [View Job]({alert.url})"""
        
        return message


class EmailNotifier:
    """Email notifications"""
    
    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER")
        self.smtp_password = os.environ.get("SMTP_PASSWORD")
        self.from_email = os.environ.get("FROM_EMAIL", "alerts@freelance-hunter.local")
        self.to_emails = os.environ.get("TO_EMAILS", "").split(",")
        self.digest_queue = []
    
    def send(self, alert: JobAlert):
        """Send immediate email"""
        
        if not self.smtp_user or not self.smtp_password:
            logger.warning("Email not configured")
            return False
        
        # Add to digest queue
        self.digest_queue.append(alert)
        
        # Send if hot
        if alert.match_score > 0.8:
            self.send_immediate(alert)
    
    def send_immediate(self, alert: JobAlert):
        """Send immediate email for hot jobs"""
        
        subject = f"🔥 Hot Job: {alert.title[:50]}"
        
        body = self.format_email(alert)
        
        self.send_email(subject, body)
    
    def send_digest(self):
        """Send daily digest"""
        
        if not self.digest_queue:
            return
        
        subject = f"📋 Freelance Hunter - {len(self.digest_queue)} New Opportunities"
        
        body = self.format_digest()
        
        self.send_email(subject, body)
        
        # Clear queue
        self.digest_queue = []
    
    def send_email(self, subject: str, body: str):
        """Send email"""
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join([e for e in self.to_emails if e])
            msg["Subject"] = subject
            
            msg.attach(MIMEText(body, "html"))
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Email error: {e}")
            return False
    
    def format_email(self, alert: JobAlert) -> str:
        """Format email body"""
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2 style="color: #ff6b00;">🔥 Hot Job Alert</h2>
            
            <h3>{alert.title}</h3>
            
            <p><strong>Platform:</strong> {alert.platform}</p>
            <p><strong>Budget:</strong> {alert.budget or 'Negotiable'}</p>
            <p><strong>Match Score:</strong> {alert.match_score:.0%}</p>
            
            <p><strong>Why this fits you:</strong></p>
            <ul>
                {''.join(f'<li>{r}</li>' for r in alert.reasons[:3])}
            </ul>
            
            <a href="{alert.url}" style="background: #00aaff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Job</a>
            
            <hr>
            <p style="color: #888; font-size: 12px;">
                Sent by Freelance Hunter • {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </p>
        </body>
        </html>
        """
        
        return html
    
    def format_digest(self) -> str:
        """Format digest email"""
        
        html = """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2>📋 Daily Freelance Opportunities</h2>
        """
        
        for i, alert in enumerate(self.digest_queue[:10], 1):
            html += f"""
            <div style="margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 8px;">
                <h3>{i}. {alert.title[:80]}</h3>
                <p><strong>Platform:</strong> {alert.platform} | 
                   <strong>Budget:</strong> {alert.budget or 'Negotiable'} | 
                   <strong>Match:</strong> {alert.match_score:.0%}</p>
                <p><strong>Why:</strong> {', '.join(alert.reasons[:2]) if alert.reasons else 'Good fit'}</p>
                <a href="{alert.url}">View Job</a>
            </div>
            """
        
        html += """
            <hr>
            <p style="color: #888; font-size: 12px;">
                Sent by Freelance Hunter • {datetime.now().strftime('%Y-%m-%d')}
            </p>
        </body>
        </html>
        """
        
        return html


class NotificationManager:
    """Manages all notifications"""
    
    def __init__(self):
        self.discord = DiscordNotifier()
        self.telegram = TelegramNotifier()
        self.email = EmailNotifier()
        self.thresholds = {
            "hot_score": 0.7,
            "min_budget": 500
        }
    
    def send_job_alert(self, job: Dict, match_data: Dict):
        """Send alert for hot job"""
        
        # Create alert
        alert = JobAlert(
            job_id=job.get("id", ""),
            platform=job.get("platform", ""),
            title=job.get("title", ""),
            url=job.get("url", ""),
            budget=job.get("budget", ""),
            match_score=match_data.get("score", 0),
            skills=job.get("skills", []),
            reasons=match_data.get("reasons", [])
        )
        
        # Check threshold
        if alert.match_score < self.thresholds["hot_score"]:
            logger.debug(f"Job below threshold: {alert.match_score}")
            return {"sent": 0}
        
        sent = 0
        
        # Send to Discord
        if self.discord.send(alert):
            sent += 1
        
        # Send to Telegram
        if self.telegram.send(alert):
            sent += 1
        
        # Queue for email
        self.email.send(alert)
        
        # Log notification
        self.log_notification(alert, sent)
        
        return {"sent": sent, "alert": alert}
    
    def log_notification(self, alert: JobAlert, sent: int):
        """Log notification"""
        
        log_file = Path(CONFIG["notifications_dir"]) / "log.json"
        
        logs = []
        if log_file.exists():
            with open(log_file) as f:
                logs = json.load(f)
        
        logs.append({
            "job_id": alert.job_id,
            "title": alert.title,
            "score": alert.match_score,
            "sent": sent,
            "timestamp": alert.timestamp
        })
        
        # Keep last 100
        logs = logs[-100:]
        
        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)


# API Integration

def setup_notifications_api(app):
    """Setup Flask API routes"""
    
    notifier = NotificationManager()
    
    @app.route("/api/notifications/send", methods=["POST"])
    def send_notifications():
        """Send notifications for jobs"""
        data = request.get_json()
        jobs = data.get("jobs", [])
        
        results = []
        
        for job in jobs:
            match_data = job.get("match", {})
            result = notifier.send_job_alert(job, match_data)
            results.append(result)
        
        return jsonify({
            "sent": sum(r.get("sent", 0) for r in results),
            "count": len(results)
        })
    
    @app.route("/api/notifications/send/<job_id>", methods=["POST"])
    def send_single_notification(job_id):
        """Send notification for specific job"""
        
        # Load job
        jobs_file = Path(CONFIG["data_dir"]) / "jobs" / "latest.json"
        
        if not jobs_file.exists():
            return jsonify({"error": "No jobs"}), 404
        
        with open(jobs_file) as f:
            jobs = json.load(f)
        
        job = next((j for j in jobs if j.get("id") == job_id), None)
        
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        match_data = {"score": 0.8, "reasons": ["Test"]}
        result = notifier.send_job_alert(job, match_data)
        
        return jsonify(result)
    
    @app.route("/api/notifications/log", methods=["GET"])
    def get_notification_log():
        """Get notification log"""
        
        log_file = Path(CONFIG["notifications_dir"]) / "log.json"
        
        if not log_file.exists():
            return jsonify([])
        
        with open(log_file) as f:
            logs = json.load(f)
        
        return jsonify(logs[-20:])
    
    @app.route("/api/notifications/test", methods=["POST"])
    def test_notifications():
        """Test notification channels"""
        
        test_alert = JobAlert(
            job_id="TEST001",
            platform="test",
            title="Test Job - Python Developer",
            url="https://example.com",
            budget="$1000",
            match_score=0.85,
            skills=["Python", "Django"],
            reasons=["Perfect skill match", "High budget"]
        )
        
        results = {
            "discord": notifier.discord.send(test_alert),
            "telegram": notifier.telegram.send(test_alert),
            "email": notifier.email.send_immediate(test_alert)
        }
        
        return jsonify(results)
    
    @app.route("/api/notifications/digest", methods=["POST"])
    def send_digest():
        """Send daily digest"""
        notifier.email.send_digest()
        return jsonify({"status": "sent"})
```

## Environment Variables

```bash
# Discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Telegram
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
export TELEGRAM_CHAT_IDS="123456789,987654321"

# Email (Gmail)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export FROM_EMAIL="alerts@freelance-hunter.local"
export TO_EMAILS="you@example.com,other@example.com"
```

## Next Steps

- [08-sheets](./08-sheets.md) - Google Sheets pipeline
