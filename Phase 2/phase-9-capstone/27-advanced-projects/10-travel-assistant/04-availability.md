# Tourism Intelligence - Availability Monitoring

## Overview

The availability monitoring system tracks hotel room availability every 15 minutes and detects changes.

## Availability Monitor

```python
#!/usr/bin/env python3
"""
Availability Monitor - Tracks hotel availability every 15 minutes
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/tourism-intel/data",
    "check_interval": 900,  # 15 minutes
    "sheets_api": "http://localhost:8095"
}


class AvailabilityMonitor:
    """Monitors hotel availability"""
    
    def __init__(self):
        self.data_dir = Path(CONFIG["data_dir"])
        self.session = requests.Session()
        
    def check_availability(self, hotel_id: str) -> Dict:
        """Check current availability for hotel"""
        
        # Simulate availability check (real implementation would scrape)
        import random
        
        rooms_available = random.randint(0, 15)
        price = random.randint(150000, 800000)  # COP
        
        return {
            "hotel_id": hotel_id,
            "rooms_available": rooms_available,
            "price_cop": price,
            "price_usd": round(price / 4000, 2),  # Approximate USD
            "last_update": datetime.now().isoformat(),
            "booking_link": f"https://booking.com/hotel/{hotel_id}"
        }
    
    def compare_availability(self, hotel_id: str) -> Dict:
        """Compare current vs previous availability"""
        
        current = self.check_availability(hotel_id)
        
        # Load previous data
        prev_file = self.data_dir / "availability" / f"{hotel_id}_latest.json"
        
        if prev_file.exists():
            with open(prev_file) as f:
                previous = json.load(f)
            
            # Calculate changes
            rooms_change = current["rooms_available"] - previous.get("rooms_available", 0)
            price_change = current["price_cop"] - previous.get("price_cop", 0)
            
            comparison = {
                "hotel_id": hotel_id,
                "current": current,
                "previous": previous,
                "changes": {
                    "rooms": rooms_change,
                    "price": price_change,
                    "price_pct": round(price_change / previous.get("price_cop", 1) * 100, 1) if previous.get("price_cop") else 0
                },
                "alert": self.generate_alert(rooms_change, price_change)
            }
        else:
            comparison = {
                "hotel_id": hotel_id,
                "current": current,
                "previous": None,
                "changes": None,
                "alert": "first_check"
            }
        
        # Save current
        self.save_availability(hotel_id, current)
        
        return comparison
    
    def generate_alert(self, rooms_change: int, price_change: int) -> str:
        """Generate alert based on changes"""
        
        if rooms_change < -5:
            return "HIGH_ALERT"  # Rooms running out
        elif rooms_change < 0:
            return "LOW_ROOMS"  # Some rooms booked
        elif price_change > 50000:
            return "PRICE_UP"  # Significant price increase
        elif price_change < -50000:
            return "PRICE_DOWN"  # Price drop
        elif rooms_change > 5:
            return "ROOMS_AVAILABLE"  # More rooms added
        
        return "NORMAL"
    
    def save_availability(self, hotel_id: str, data: Dict):
        """Save availability data"""
        avail_dir = self.data_dir / "availability"
        avail_dir.mkdir(parents=True, exist_ok=True)
        
        # Save latest
        with open(avail_dir / f"{hotel_id}_latest.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # Save historical
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        with open(avail_dir / f"{hotel_id}_{timestamp}.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def monitor_all_hotels(self, hotel_ids: List[str]) -> List[Dict]:
        """Monitor all hotels"""
        
        results = []
        
        for hotel_id in hotel_ids:
            try:
                result = self.compare_availability(hotel_id)
                results.append(result)
                
                # Alert if significant change
                if result.get("alert") not in ["NORMAL", "first_check", None]:
                    self.send_alert(result)
                    
            except Exception as e:
                logger.error(f"Error monitoring {hotel_id}: {e}")
        
        return results
    
    def send_alert(self, result: Dict):
        """Send availability alert"""
        
        alert = result.get("alert", "")
        hotel_id = result.get("hotel_id", "")
        
        logger.warning(f"ALERT [{alert}] {hotel_id}")
        
        # Send to Sheets API
        try:
            requests.post(
                f"{CONFIG['sheets_api']}/alerts/availability",
                json=result,
                timeout=10
            )
        except:
            pass


class AvailabilityHistory:
    """Analyzes availability history"""
    
    def __init__(self):
        self.data_dir = Path(CONFIG["data_dir"])
    
    def get_availability_trend(self, hotel_id: str, days: int = 7) -> Dict:
        """Get availability trend for hotel"""
        
        avail_dir = self.data_dir / "availability"
        
        if not avail_dir.exists():
            return {"error": "No data"}
        
        # Get files from last N days
        cutoff = datetime.now() - timedelta(days=days)
        
        files = sorted(avail_dir.glob(f"{hotel_id}_*.json"))
        
        history = []
        for f in files:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > cutoff:
                    with open(f) as fp:
                        data = json.load(fp)
                        history.append({
                            "timestamp": mtime.isoformat(),
                            "rooms": data.get("rooms_available"),
                            "price": data.get("price_cop")
                        })
            except:
                pass
        
        if len(history) < 2:
            return {"trend": "insufficient_data", "history": history}
        
        # Calculate trend
        recent = history[-5:] if len(history) >= 5 else history
        older = history[:5] if len(history) >= 5 else history
        
        avg_recent = sum(h["rooms"] for h in recent) / len(recent)
        avg_older = sum(h["rooms"] for h in older) / len(older)
        
        rooms_trend = "increasing" if avg_recent > avg_older else "decreasing"
        
        return {
            "hotel_id": hotel_id,
            "history": history,
            "rooms_trend": rooms_trend,
            "avg_rooms_recent": round(avg_recent, 1),
            "avg_rooms_older": round(avg_older, 1),
            "data_points": len(history)
        }
    
    def find_availability_opportunities(self) -> List[Dict]:
        """Find hotels with good availability/value"""
        
        avail_dir = self.data_dir / "availability"
        
        if not avail_dir.exists():
            return []
        
        opportunities = []
        
        # Check latest files
        for f in avail_dir.glob("*_latest.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                
                rooms = data.get("rooms_available", 0)
                price = data.get("price_cop", 999999)
                
                if rooms >= 5 and price < 300000:  # At least 5 rooms under 300k COP
                    opportunities.append({
                        "hotel_id": data.get("hotel_id"),
                        "rooms": rooms,
                        "price": price,
                        "value_score": rooms / (price / 100000)
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {f}: {e}")
        
        # Sort by value
        opportunities.sort(key=lambda x: x["value_score"], reverse=True)
        
        return opportunities[:10]


# API Endpoints
@app.route("/api/availability/check/<hotel_id>")
def check_availability(hotel_id: str):
    """Check hotel availability"""
    monitor = AvailabilityMonitor()
    result = monitor.compare_availability(hotel_id)
    return jsonify(result)


@app.route("/api/availability/trend/<hotel_id>")
def availability_trend(hotel_id: str):
    """Get availability trend"""
    history = AvailabilityHistory()
    result = history.get_availability_trend(hotel_id)
    return jsonify(result)


@app.route("/api/availability/opportunities")
def find_opportunities():
    """Find availability opportunities"""
    history = AvailabilityHistory()
    opportunities = history.find_availability_opportunities()
    return jsonify({"opportunities": opportunities})


@app.route("/api/availability/all")
def all_availability():
    """Get all current availability"""
    monitor = AvailabilityMonitor()
    
    # Get hotel IDs
    avail_dir = Path(CONFIG["data_dir"]) / "availability"
    hotel_ids = set()
    
    if avail_dir.exists():
        for f in avail_dir.glob("*_latest.json"):
            hotel_id = f.stem.replace("_latest", "")
            hotel_ids.add(hotel_id)
    
    results = monitor.monitor_all_hotels(list(hotel_ids))
    
    return jsonify({"results": results})
```

## Real-time Dashboard Data

```python
@app.route("/api/dashboard/availability")
def dashboard_availability():
    """Get availability data for dashboard"""
    
    history = AvailabilityHistory()
    opportunities = history.find_availability_opportunities()
    
    # Get alerts
    from pathlib import Path
    avail_dir = Path(CONFIG["data_dir"]) / "availability"
    alerts = []
    
    if avail_dir.exists():
        for f in avail_dir.glob("*_latest.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    rooms = data.get("rooms_available", 0)
                    if rooms < 3:
                        alerts.append({
                            "hotel_id": data.get("hotel_id"),
                            "rooms": rooms,
                            "alert": "LOW_AVAILABILITY"
                        })
            except:
                pass
    
    return jsonify({
        "opportunities": opportunities[:5],
        "alerts": alerts,
        "last_update": datetime.now().isoformat()
    })
```

## Next Steps

- [05-agents](./05-agents.md) - Agent implementations
