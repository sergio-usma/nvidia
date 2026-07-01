# Freelance Hunter - Google Sheets Integration

## Overview

The platform stores all job data, matches, and proposals in Google Sheets for real-time tracking, sharing, and analysis.

## Google Sheets Structure

### Spreadsheet: Freelance Hunter Pipeline

| Sheet | Purpose |
|-------|---------|
| Jobs | All scraped jobs |
| Matches | Matched opportunities |
| Proposals | Generated proposals |
| Sent | Sent proposals |
| Won | Won contracts |
| Lost | Lost proposals |
| Stats | Daily statistics |

## Sheets Implementation

```python
#!/usr/bin/env python3
"""
Google Sheets Integration for Freelance Hunter
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "credentials_file": "/opt/freelance-hunter/config/sheets-credentials.json",
    "spreadsheet_id": os.environ.get("FREELANCE_SPREADSHEET_ID", ""),
    "api_url": "http://localhost:8096",
    "data_dir": "/opt/freelance-hunter/data"
}


class SheetsManager:
    """Manages Google Sheets operations"""
    
    def __init__(self, spreadsheet_id: str = None):
        self.spreadsheet_id = spreadsheet_id or CONFIG["spreadsheet_id"]
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                CONFIG["credentials_file"],
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.file'
                ]
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Authenticated with Google Sheets")
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.service = None
    
    def create_spreadsheet(self, title: str) -> str:
        """Create new spreadsheet"""
        if not self.service:
            return None
        
        spreadsheet = {
            'properties': {'title': title},
            'sheets': [
                {'properties': {'title': 'Jobs'}},
                {'properties': {'title': 'Matches'}},
                {'properties': {'title': 'Proposals'}},
                {'properties': {'title': 'Sent'}},
                {'properties': {'title': 'Won'}},
                {'properties': {'title': 'Lost'}},
                {'properties': {'title': 'Stats'}}
            ]
        }
        
        result = self.service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId'
        ).execute()
        
        return result.get('spreadsheetId')
    
    def write_data(self, sheet_name: str, data: List[List[Any]], start: str = "A1"):
        """Write data to sheet"""
        if not self.service:
            return False
        
        try:
            body = {'values': data}
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{start}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Write failed: {e}")
            return False
    
    def read_data(self, sheet_name: str, range: str = "A1:Z1000") -> List[List]:
        """Read data from sheet"""
        if not self.service:
            return []
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{range}"
            ).execute()
            
            return result.get('values', [])
            
        except Exception as e:
            logger.error(f"Read failed: {e}")
            return []
    
    def append_rows(self, sheet_name: str, data: List[List[Any]]):
        """Append rows to sheet"""
        if not self.service:
            return False
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A"
            ).execute()
            
            start_row = len(result.get('values', [])) + 1
            
            body = {'values': data}
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A{start_row}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Append failed: {e}")
            return False
    
    def clear_sheet(self, sheet_name: str):
        """Clear sheet content"""
        if not self.service:
            return False
        
        try:
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Clear failed: {e}")
            return False
    
    def update_cell(self, sheet_name: str, cell: str, value: Any):
        """Update single cell"""
        if not self.service:
            return False
        
        try:
            body = {'values': [[value]]}
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{cell}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Cell update failed: {e}")
            return False


class FreelanceSheets:
    """Freelance Hunter sheet operations"""
    
    def __init__(self):
        self.sheets = SheetsManager()
    
    # ============ JOBS SHEET ============
    
    def format_jobs_header(self) -> List[List]:
        """Jobs header"""
        return [["ID", "Platform", "Title", "URL", "Budget", "Skills", 
                 "Client", "Rating", "Proposals", "Posted", "Scraped"]]
    
    def format_jobs_data(self, jobs: List[Dict]) -> List[List]:
        """Format jobs for Sheets"""
        data = self.format_jobs_header()
        
        for job in jobs:
            row = [
                job.get("id", ""),
                job.get("platform", ""),
                job.get("title", ""),
                job.get("url", ""),
                job.get("budget", ""),
                ", ".join(job.get("skills", [])),
                job.get("client_name", ""),
                job.get("client_rating", ""),
                job.get("proposals_count", ""),
                job.get("posted_at", ""),
                job.get("scraped_at", "")
            ]
            data.append(row)
        
        return data
    
    def update_jobs(self, jobs: List[Dict]):
        """Update Jobs sheet"""
        data = self.format_jobs_data(jobs)
        self.sheets.clear_sheet("Jobs")
        self.sheets.write_data("Jobs", data)
        logger.info(f"Updated Jobs sheet with {len(jobs)} entries")
    
    def append_jobs(self, jobs: List[Dict]):
        """Append new jobs"""
        data = self.format_jobs_data(jobs)[1:]
        
        if data:
            self.sheets.append_rows("Jobs", data)
            logger.info(f"Appended {len(data)} jobs")
    
    # ============ MATCHES SHEET ============
    
    def format_matches_header(self) -> List[List]:
        """Matches header"""
        return [["Job ID", "Platform", "Title", "URL", "Score", "Skills Match", 
                 "Budget Match", "Reasons", "Recommended Rate", "Date"]]
    
    def format_matches_data(self, matches: List[Dict]) -> List[List]:
        """Format matches for Sheets"""
        data = self.format_matches_header()
        
        for match in matches:
            job = match.get("job_data", {})
            row = [
                match.get("job_id", ""),
                job.get("platform", ""),
                match.get("title", ""),
                match.get("url", ""),
                f"{match.get('score', 0):.0%}",
                f"{match.get('skill_match', 0):.0%}",
                f"{match.get('budget_match', 0):.0%}",
                "; ".join(match.get("reasons", [])),
                match.get("recommended_rate", ""),
                datetime.now().strftime("%Y-%m-%d")
            ]
            data.append(row)
        
        return data
    
    def update_matches(self, matches: List[Dict]):
        """Update Matches sheet"""
        data = self.format_matches_data(matches)
        self.sheets.clear_sheet("Matches")
        self.sheets.write_data("Matches", data)
        logger.info(f"Updated Matches sheet with {len(matches)} entries")
    
    # ============ PROPOSALS SHEET ============
    
    def format_proposals_header(self) -> List[List]:
        """Proposals header"""
        return [["ID", "Job ID", "Platform", "Title", "Proposed Rate", 
                 "Status", "Created", "Sent", "Response"]]
    
    def format_proposals_data(self, proposals: List[Dict]) -> List[List]:
        """Format proposals for Sheets"""
        data = self.format_proposals_header()
        
        for prop in proposals:
            row = [
                prop.get("id", ""),
                prop.get("job_id", ""),
                prop.get("platform", ""),
                prop.get("job_title", ""),
                prop.get("proposed_rate", ""),
                prop.get("status", ""),
                prop.get("created_at", ""),
                prop.get("sent_at", ""),
                prop.get("response", "")
            ]
            data.append(row)
        
        return data
    
    def update_proposals(self, proposals: List[Dict]):
        """Update Proposals sheet"""
        data = self.format_proposals_data(proposals)
        self.sheets.clear_sheet("Proposals")
        self.sheets.write_data("Proposals", data)
        logger.info(f"Updated Proposals sheet with {len(proposals)} entries")
    
    # ============ PIPELINE SHEET ============
    
    def update_pipeline(self, proposals: List[Dict]):
        """Update Sent/Won/Lost sheets"""
        
        # Sent
        sent = [p for p in proposals if p.get("status") == "sent"]
        self.update_sheet_with_filter("Sent", sent, ["id", "job_id", "platform", 
                  "job_title", "proposed_rate", "sent_at", "response"])
        
        # Won
        won = [p for p in proposals if p.get("status") == "won"]
        self.update_sheet_with_filter("Won", won, ["id", "job_id", "platform", 
                 "job_title", "proposed_rate", "sent_at", "closed_at", "earnings"])
        
        # Lost
        lost = [p for p in proposals if p.get("status") == "lost"]
        self.update_sheet_with_filter("Lost", lost, ["id", "job_id", "platform", 
                "job_title", "proposed_rate", "sent_at", "closed_at", "reason"])
    
    def update_sheet_with_filter(self, sheet_name: str, items: List[Dict], columns: List[str]):
        """Update sheet with filtered items"""
        
        data = [columns]
        
        for item in items:
            row = [item.get(col, "") for col in columns]
            data.append(row)
        
        self.sheets.clear_sheet(sheet_name)
        self.sheets.write_data(sheet_name, data)
    
    # ============ STATS SHEET ============
    
    def update_stats(self, stats: Dict):
        """Update Stats sheet"""
        
        data = [
            ["Metric", "Value"],
            ["Total Proposals", stats.get("total", 0)],
            ["Draft", stats.get("draft", 0)],
            ["Sent", stats.get("sent", 0)],
            ["Pending", stats.get("pending", 0)],
            ["Won", stats.get("won", 0)],
            ["Lost", stats.get("lost", 0)],
            ["Win Rate", f"{stats.get('won', 0) / max(stats.get('sent', 1), 1):.0%}"],
            ["Total Earnings", stats.get("earnings", "$0")],
            ["Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M")]
        ]
        
        self.sheets.clear_sheet("Stats")
        self.sheets.write_data("Stats", data)
        logger.info("Updated Stats sheet")
    
    # ============ SYNC ============
    
    def sync_all(self, jobs: List[Dict] = None, matches: List[Dict] = None, 
                 proposals: List[Dict] = None, stats: Dict = None):
        """Sync all sheets"""
        
        if jobs:
            self.update_jobs(jobs)
        
        if matches:
            self.update_matches(matches)
        
        if proposals:
            self.update_proposals(proposals)
            self.update_pipeline(proposals)
        
        if stats:
            self.update_stats(stats)


# API Integration

def setup_sheets_api(app):
    """Setup Flask API routes"""
    
    sheets = FreelanceSheets()
    
    @app.route("/sheets/jobs", methods=["POST"])
    def update_jobs_sheet():
        """Update jobs in Sheets"""
        data = request.get_json()
        jobs = data.get("jobs", [])
        
        sheets.update_jobs(jobs)
        
        return jsonify({"status": "success", "count": len(jobs)})
    
    @app.route("/sheets/jobs/append", methods=["POST"])
    def append_jobs_sheet():
        """Append jobs to Sheets"""
        data = request.get_json()
        jobs = data.get("jobs", [])
        
        sheets.append_jobs(jobs)
        
        return jsonify({"status": "success", "count": len(jobs)})
    
    @app.route("/sheets/matches", methods=["POST"])
    def update_matches_sheet():
        """Update matches in Sheets"""
        data = request.get_json()
        matches = data.get("matches", [])
        
        sheets.update_matches(matches)
        
        return jsonify({"status": "success", "count": len(matches)})
    
    @app.route("/sheets/proposals", methods=["POST"])
    def update_proposals_sheet():
        """Update proposals in Sheets"""
        data = request.get_json()
        proposals = data.get("proposals", [])
        
        sheets.update_proposals(proposals)
        
        return jsonify({"status": "success", "count": len(proposals)})
    
    @app.route("/sheets/stats", methods=["POST"])
    def update_stats_sheet():
        """Update stats in Sheets"""
        data = request.get_json()
        stats = data.get("stats", {})
        
        sheets.update_stats(stats)
        
        return jsonify({"status": "success"})
    
    @app.route("/sheets/sync", methods=["POST"])
    def sync_all_sheets():
        """Sync all sheets"""
        
        # Load data from files
        jobs_file = Path(CONFIG["data_dir"]) / "jobs" / "latest.json"
        jobs = []
        if jobs_file.exists():
            with open(jobs_file) as f:
                jobs = json.load(f)
        
        # Get matches
        matches = []
        try:
            response = requests.get(f"{CONFIG['api_url']}/api/match", timeout=10)
            if response.status_code == 200:
                matches = response.json().get("matches", [])
        except:
            pass
        
        # Get proposals
        proposals = []
        try:
            response = requests.get(f"{CONFIG['api_url']}/api/proposals/pending", timeout=10)
            if response.status_code == 200:
                proposals = response.json()
        except:
            pass
        
        # Get stats
        stats = {}
        try:
            response = requests.get(f"{CONFIG['api_url']}/api/proposals/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
        except:
            pass
        
        sheets.sync_all(jobs, matches, proposals, stats)
        
        return jsonify({"status": "synced"})
    
    @app.route("/sheets/create", methods=["POST"])
    def create_spreadsheet():
        """Create new spreadsheet"""
        data = request.get_json()
        title = data.get("title", "Freelance Hunter Pipeline")
        
        spreadsheet_id = sheets.sheets.create_spreadsheet(title)
        
        return jsonify({"spreadsheet_id": spreadsheet_id})


# Example Usage

if __name__ == "__main__":
    sheets = FreelanceSheets()
    
    # Test data
    test_jobs = [
        {
            "id": "TEST001",
            "platform": "upwork",
            "title": "Python Developer Needed",
            "url": "https://example.com/job/123",
            "budget": "$500-1000",
            "skills": ["Python", "Django"],
            "client_name": "Tech Corp",
            "client_rating": "4.8",
            "proposals_count": 5,
            "scraped_at": datetime.now().isoformat()
        }
    ]
    
    sheets.update_jobs(test_jobs)
    print("Sheets updated!")
```

## Sheet Schemas

### Jobs Sheet

| Column | Description |
|--------|-------------|
| A | Job ID |
| B | Platform (upwork, freelancer, etc.) |
| C | Job title |
| D | URL to job |
| E | Budget (fixed/hourly) |
| F | Required skills |
| G | Client name |
| H | Client rating |
| I | Number of proposals |
| J | Posted date |
| K | Scraped timestamp |

### Matches Sheet

| Column | Description |
|--------|-------------|
| A | Job ID |
| B | Platform |
| C | Title |
| D | URL |
| E | Overall match score |
| F | Skills match % |
| G | Budget match % |
| H | Match reasons |
| I | Recommended rate |
| J | Date matched |

### Proposals Sheet

| Column | Description |
|--------|-------------|
| A | Proposal ID |
| B | Job ID |
| C | Platform |
| D | Job title |
| E | Proposed rate |
| F | Status (draft/sent/pending/won/lost) |
| G | Created date |
| H | Sent date |
| I | Client response |

### Stats Sheet

| Column | Description |
|--------|-------------|
| A | Metric name |
| B | Value |

## Environment Variables

```bash
# Set in /opt/freelance-hunter/.env
export FREELANCE_SPREADSHEET_ID="1abc123..."
export GOOGLE_APPLICATION_CREDENTIALS="/opt/freelance-hunter/config/sheets-credentials.json"
```

## Next Steps

- [09-dashboard](./09-dashboard.md) - Real-time dashboard
