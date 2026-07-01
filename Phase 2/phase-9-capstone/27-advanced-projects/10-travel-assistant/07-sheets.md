# Tourism Intelligence - Google Sheets Integration

## Overview

The platform stores all tourism data in Google Sheets for real-time access, sharing, and analysis. Multiple sheets track hotels, airlines, news, trends, and alerts.

## Google Cloud Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: `tourism-intelligence`
3. Enable APIs:
   - Google Sheets API
   - Google Drive API

### 2. Create Service Account

1. Go to IAM & Admin > Service Accounts
2. Create service account: `tourism-sheets@tourism-intelligence.iam.gserviceaccount.com`
3. Add roles:
   - Sheets Viewer
   - Sheets Editor
   - Drive Viewer
4. Create JSON key, download as `/opt/tourism-intel/config/sheets-credentials.json`

### 3. Share Sheets

Create these sheets and share with service account email:
- `Tourism_Hotels`
- `Tourism_Airlines`
- `Tourism_News`
- `Tourism_Trends`
- `Tourism_Alerts`

## Sheets Integration Code

```python
#!/usr/bin/env python3
"""
Google Sheets Integration for Tourism Intelligence
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "credentials_file": "/opt/tourism-intel/config/sheets-credentials.json",
    "spreadsheet_id": os.environ.get("SPREADSHEET_ID", ""),
    "api_url": "http://localhost:8095"
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
                {'properties': {'title': 'Hotels'}},
                {'properties': {'title': 'Airlines'}},
                {'properties': {'title': 'News'}},
                {'properties': {'title': 'Trends'}},
                {'properties': {'title': 'Alerts'}}
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
            body = {
                'values': data
            }
            
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
            # Get existing row count
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


class TourismDataSheets:
    """Handles tourism-specific sheet operations"""
    
    def __init__(self):
        self.sheets = SheetsManager()
    
    def format_hotels_header(self) -> List[List]:
        """Hotel data header"""
        return [["ID", "Name", "City", "Source", "Price", "Rating", "Reviews", "Stars", "URL", "Last Updated"]]
    
    def format_hotels_data(self, hotels: List[Dict]) -> List[List]:
        """Format hotels for Sheets"""
        data = self.format_hotels_header()
        
        for hotel in hotels:
            row = [
                hotel.get("id", ""),
                hotel.get("name", ""),
                hotel.get("location", ""),
                hotel.get("source", ""),
                hotel.get("price", ""),
                hotel.get("rating", ""),
                hotel.get("reviews_count", ""),
                hotel.get("stars", ""),
                hotel.get("url", ""),
                hotel.get("scraped_at", "")
            ]
            data.append(row)
        
        return data
    
    def update_hotels(self, hotels: List[Dict]):
        """Update Hotels sheet"""
        data = self.format_hotels_data(hotels)
        
        # Clear and rewrite
        self.sheets.clear_sheet("Hotels")
        self.sheets.write_data("Hotels", data)
        
        logger.info(f"Updated Hotels sheet with {len(hotels)} entries")
    
    def append_hotels(self, hotels: List[Dict]):
        """Append new hotels"""
        data = self.format_hotels_data(hotels)[1:]  # Skip header
        
        if data:
            self.sheets.append_rows("Hotels", data)
            logger.info(f"Appended {len(data)} hotels")
    
    def format_trends_header(self) -> List[List]:
        """Trends header"""
        return [["Date", "City", "Metric", "Value", "Change", "Notes"]]
    
    def append_trends(self, trends: List[Dict]):
        """Append trend data"""
        data = self.format_trends_header()
        
        for trend in trends:
            row = [
                datetime.now().strftime("%Y-%m-%d"),
                trend.get("city", ""),
                trend.get("metric", ""),
                trend.get("value", ""),
                trend.get("change", ""),
                trend.get("notes", "")
            ]
            data.append(row)
        
        self.sheets.append_rows("Trends", data[1:])
    
    def format_alerts_header(self) -> List[List]:
        """Alerts header"""
        return [["Timestamp", "Type", "Severity", "Message", "Hotel", "Value", "Resolved"]]
    
    def append_alerts(self, alerts: List[Dict]):
        """Append alert data"""
        data = self.format_alerts_header()
        
        for alert in alerts:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                alert.get("type", ""),
                alert.get("severity", ""),
                alert.get("message", ""),
                alert.get("hotel", ""),
                alert.get("value", ""),
                "No"
            ]
            data.append(row)
        
        self.sheets.append_rows("Alerts", data[1:])
        logger.info(f"Appended {len(alerts)} alerts")
    
    def get_city_summary(self, city: str) -> Dict:
        """Get summary for a city"""
        hotels = self.sheets.read_data("Hotels")
        
        city_hotels = [h for h in hotels[1:] if len(h) > 2 and h[2].lower() == city.lower()]
        
        if not city_hotels:
            return {"city": city, "hotels": 0}
        
        # Calculate averages
        ratings = [float(h[5]) for h in city_hotels if h[5] and h[5].replace('.', '').isdigit()]
        
        return {
            "city": city,
            "hotels": len(city_hotels),
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "data": city_hotels[:10]
        }


# API Integration

def setup_sheets_api(app):
    """Setup Flask API routes for Sheets"""
    
    sheets_manager = TourismDataSheets()
    
    @app.route("/sheets/hotels", methods=["POST"])
    def update_hotels_sheet():
        """Update hotels in Sheets"""
        data = request.get_json()
        hotels = data.get("hotels", [])
        
        sheets_manager.update_hotels(hotels)
        
        return jsonify({"status": "success", "count": len(hotels)})
    
    
    @app.route("/sheets/hotels/append", methods=["POST"])
    def append_hotels_sheet():
        """Append hotels to Sheets"""
        data = request.get_json()
        hotels = data.get("hotels", [])
        
        sheets_manager.append_hotels(hotels)
        
        return jsonify({"status": "success", "count": len(hotels)})
    
    
    @app.route("/sheets/trends", methods=["POST"])
    def update_trends_sheet():
        """Update trends in Sheets"""
        data = request.get_json()
        trends = data.get("trends", [])
        
        sheets_manager.append_trends(trends)
        
        return jsonify({"status": "success", "count": len(trends)})
    
    
    @app.route("/sheets/alerts", methods=["POST"])
    def update_alerts_sheet():
        """Update alerts in Sheets"""
        data = request.get_json()
        alerts = data.get("alerts", [])
        
        sheets_manager.append_alerts(alerts)
        
        return jsonify({"status": "success", "count": len(alerts)})
    
    
    @app.route("/sheets/city/<city>", methods=["GET"])
    def get_city_summary(city):
        """Get city summary"""
        summary = sheets_manager.get_city_summary(city)
        
        return jsonify(summary)
    
    
    @app.route("/sheets/create", methods=["POST"])
    def create_spreadsheet():
        """Create new spreadsheet"""
        data = request.get_json()
        title = data.get("title", "Tourism Intelligence")
        
        spreadsheet_id = sheets_manager.sheets.create_spreadsheet(title)
        
        return jsonify({"spreadsheet_id": spreadsheet_id})
```

## Sheet Structure

### Hotels Sheet

| Column | Description |
|--------|-------------|
| A | Hotel ID |
| B | Hotel Name |
| C | City |
| D | Source (booking, tripadvisor, etc.) |
| E | Price per night |
| F | Rating (1-10) |
| G | Number of reviews |
| H | Star rating |
| I | Booking URL |
| J | Last updated timestamp |

### Airlines Sheet

| Column | Description |
|--------|-------------|
| A | Route (e.g., BOG-MDE) |
| B | Airline |
| C | Origin city |
| D | Destination city |
| E | Typical price |
| F | On-time rate |
| G | Last updated |

### News Sheet

| Column | Description |
|--------|-------------|
| A | Article title |
| B | Source |
| C | URL |
| D | Keywords |
| E | Published date |
| F | Scraped date |

### Trends Sheet

| Column | Description |
|--------|-------------|
| A | Date |
| B | City |
| C | Metric |
| D | Value |
| E | Change % |
| F | Notes |

### Alerts Sheet

| Column | Description |
|--------|-------------|
| A | Timestamp |
| B | Alert type |
| C | Severity |
| D | Message |
| E | Hotel name |
| F | Value |
| G | Resolved |

## Environment Variables

```bash
# Set in /opt/tourism-intel/.env
export SPREADSHEET_ID="1abc123..."
export GOOGLE_APPLICATION_CREDENTIALS="/opt/tourism-intel/config/sheets-credentials.json"
```

## Testing

```python
# Test sheets integration
from sheets import TourismDataSheets

sheets = TourismDataSheets()

# Test data
hotels = [
    {
        "id": "HOTEL-001",
        "name": "Hotel Example",
        "location": "Bogota",
        "source": "booking",
        "price": "350000",
        "rating": "8.5",
        "reviews_count": "150",
        "stars": "4",
        "url": "https://example.com",
        "scraped_at": "2024-01-15T10:00:00"
    }
]

# Update
sheets.update_hotels(hotels)
```

## Next Steps

- [08-dashboard](./08-dashboard.md) - Tourism dashboard
