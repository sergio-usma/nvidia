# Funding Finder - Google Sheets Integration

## Overview

The Google Sheets integration tracks all funding opportunities, monitors status, and manages the proposal workflow.

## Google Sheets Structure

### Main Spreadsheet: "Funding Tracker"

Create a spreadsheet with multiple sheets:

#### Sheet 1: "Queue"

| A | B | C | D | E | F | G | H | I | J | K | L |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ID | Source | Title | URL | Category | Deadline | Budget | Status | Date Found | Language | Docs | Proposal |

**Columns:**
- **ID**: Unique identifier (FU-XXXXXXXXXXXX)
- **Source**: Website/platform name
- **Title**: Opportunity title
- **URL**: Link to full details
- **Category**: social/educational/technological/etc
- **Deadline**: Submission deadline
- **Budget**: Available funding
- **Status**: NEW/PROCESSING/COMPLETED/FAILED/SENT
- **Date Found**: ISO date
- **Language**: es/en/pt/fr
- **Docs**: YES/NO
- **Proposal**: PENDING/GENERATING/COMPLETED/READY

#### Sheet 2: "Projects"

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| ID | Title | Partner Org | Budget | Deadline | Submitted | Response |

#### Sheet 3: "Analytics"

| A | B | C | D | E |
|---|---|---|---|---|
| Category | Total | Success Rate | Avg Days | Top Sources |

## API Implementation

### Flask API for Sheets

```python
#!/usr/bin/env python3
"""
Google Sheets API for Funding Finder
Provides REST endpoints for n8n integration
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import gspread
from google.oauth2 import service_account

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/funding-finder/logs/sheets.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
CONFIG = {
    "credentials_file": os.getenv(
        "GOOGLE_CREDENTIALS",
        "/opt/funding-finder/config/credentials.json"
    ),
    "spreadsheet_id": os.getenv("SPREADSHEET_ID", ""),
    "queue_sheet": "Queue",
    "projects_sheet": "Projects"
}

# Google Sheets client
def get_gsheet():
    """Get authenticated Google Sheets client"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            CONFIG["credentials_file"],
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        gc = gspread.authorize(credentials)
        return gc
    except Exception as e:
        logger.error(f"Failed to authenticate: {e}")
        raise


def get_worksheet(sheet_name):
    """Get worksheet by name"""
    gc = get_gsheet()
    sh = gc.open_by_key(CONFIG["spreadsheet_id"])
    return sh.worksheet(sheet_name)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "sheets-api"})


@app.route("/queue/add", methods=["POST"])
def add_opportunities():
    """Add new opportunities to queue"""
    try:
        data = request.get_json()
        opportunities = data.get("opportunities", [])
        
        if not opportunities:
            return jsonify({"error": "No opportunities provided"}), 400
        
        ws = get_worksheet(CONFIG["queue_sheet"])
        
        # Get existing IDs to avoid duplicates
        existing_ids = ws.col_values(1)[1:]  # Skip header
        
        new_rows = []
        for opp in opportunities:
            if opp["id"] not in existing_ids:
                row = [
                    opp.get("id", ""),
                    opp.get("source", ""),
                    opp.get("title", ""),
                    opp.get("url", ""),
                    opp.get("category", "general"),
                    opp.get("deadline", ""),
                    opp.get("budget", ""),
                    opp.get("status", "NEW"),
                    opp.get("date_found", ""),
                    opp.get("language", "es"),
                    opp.get("documents_downloaded", "NO"),
                    opp.get("proposal_status", "PENDING")
                ]
                new_rows.append(row)
        
        if new_rows:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")
            logger.info(f"Added {len(new_rows)} new opportunities")
        
        return jsonify({
            "added": len(new_rows),
            "duplicates": len(opportunities) - len(new_rows)
        })
        
    except Exception as e:
        logger.error(f"Error adding opportunities: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/queue/pending", methods=["GET"])
def get_pending():
    """Get pending opportunities for processing"""
    try:
        ws = get_worksheet(CONFIG["queue_sheet"])
        
        # Get all rows
        records = ws.get_all_records()
        
        # Filter pending
        pending = [
            r for r in records 
            if r.get("Status") == "NEW" and r.get("Docs") == "NO"
        ]
        
        return jsonify({"pending": pending})
        
    except Exception as e:
        logger.error(f"Error getting pending: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/queue/update", methods=["POST"])
def update_opportunity():
    """Update opportunity status"""
    try:
        data = request.get_json()
        opp_id = data.get("id")
        
        if not opp_id:
            return jsonify({"error": "ID required"}), 400
        
        ws = get_worksheet(CONFIG["queue_sheet"])
        
        # Find row
        ids = ws.col_values(1)
        row_num = None
        for i, cell_id in enumerate(ids, start=1):
            if cell_id == opp_id:
                row_num = i
                break
        
        if not row_num:
            return jsonify({"error": "Not found"}), 404
        
        # Update fields
        updates = data.get("updates", {})
        for key, value in updates.items():
            col_map = {
                "status": "H",
                "documents_downloaded": "K",
                "proposal_status": "L",
                "deadline": "F",
                "budget": "G"
            }
            if key in col_map:
                ws.update_cell(row_num, ord(col_map[key]) - ord('A') + 1, value)
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error updating: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/queue/next", methods=["GET"])
def get_next():
    """Get next opportunity for processing"""
    try:
        ws = get_worksheet(CONFIG["queue_sheet"])
        records = ws.get_all_records()
        
        for i, r in enumerate(records, start=2):
            if r.get("Status") == "NEW":
                # Mark as processing
                ws.update_cell(i, 8, "PROCESSING")
                return jsonify({"opportunity": r})
        
        return jsonify({"opportunity": None})
        
    except Exception as e:
        logger.error(f"Error getting next: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/queue/stats", methods=["GET"])
def get_stats():
    """Get queue statistics"""
    try:
        ws = get_worksheet(CONFIG["queue_sheet"])
        records = ws.get_all_records()
        
        stats = {
            "total": len(records),
            "new": sum(1 for r in records if r.get("Status") == "NEW"),
            "processing": sum(1 for r in records if r.get("Status") == "PROCESSING"),
            "completed": sum(1 for r in records if r.get("Status") == "COMPLETED"),
            "failed": sum(1 for r in records if r.get("Status") == "FAILED"),
            "by_category": {},
            "by_source": {}
        }
        
        for r in records:
            cat = r.get("Category", "unknown")
            src = r.get("Source", "unknown")
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    app.run(host="0.0.0.0", port=port, debug=False)
```

## Google Cloud Setup

### 1. Create Project

1. Go to https://console.cloud.google.com/
2. Create project: `funding-finder`
3. Enable APIs:
   - Google Sheets API
   - Google Drive API

### 2. Create Service Account

1. IAM & Admin → Service Accounts → Create
2. Name: `funding-finder`
3. Role: Editor
4. Create JSON key
5. Download credentials.json

### 3. Share Spreadsheet

Share the spreadsheet with the service account email:

```
funding-finder@funding-finder.iam.gserviceaccount.com
```

## Service Configuration

```bash
# Create service
sudo tee /etc/systemd/system/funding-sheets.service << 'EOF'
[Unit]
Description=Funding Finder Sheets API
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/funding-finder
ExecStart=/opt/funding-finder/venv/bin/python api/sheets.py 8081
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable funding-sheets
sudo systemctl start funding-sheets
```

## n8n Integration

### Workflow: Process New Opportunities

```
1. Cron (every hour)
   │
   ▼
2. HTTP Request → GET http://localhost:8081/queue/next
   │
   ▼
3. IF opportunity exists
   │
   ├──▶ 4. Download Documents (see Documents section)
   │
   ├──▶ 5. Update Status → POST http://localhost:8081/queue/update
   │
   └──▶ 6. Loop until no more pending
```

### n8n Nodes Configuration

```json
{
  "nodes": [
    {
      "name": "Get Next Opportunity",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "GET",
        "url": "http://localhost:8081/queue/next"
      }
    },
    {
      "name": "Update Status",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8081/queue/update",
        "bodyParameters": {
          "parameters": [
            {
              "name": "id",
              "value": "={{ $json.opportunity.ID }}"
            },
            {
              "name": "updates",
              "value": {
                "status": "PROCESSING"
              }
            }
          ]
        }
      }
    }
  ]
}
```

## Testing

```bash
# Test API
curl http://localhost:8081/health

# Get stats
curl http://localhost:8081/queue/stats

# Get pending
curl http://localhost:8081/queue/pending
```

## Next Steps

- [04-documents](./04-documents.md) - Document download and RAG
