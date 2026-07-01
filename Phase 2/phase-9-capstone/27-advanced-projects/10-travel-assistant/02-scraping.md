# Tourism Intelligence - Web Scraping System

## Overview

The scraping system collects data from multiple hotel booking sites, airline websites, and news sources for Colombian tourism intelligence.

## Sources Configuration

### Hotel Sources

```python
# config/sources.py

HOTEL_SOURCES = {
    "booking": {
        "name": "Booking.com",
        "base_url": "https://www.booking.com",
        "search_url": "/searchresults.html",
        "params": {
            "ss": "{city}",
            "checkin": "{checkin}",
            "checkout": "{checkout}",
            "group_adults": "2",
            "no_rooms": "1"
        },
        "selectors": {
            "hotel_name": ".pp-header__title",
            "price": ".prco-valign-middle-haligncenter",
            "rating": ".b5c098ed25-score-bar-scoreValue",
            "reviews": ".b5c098ed25-count",
            "location": ".f4bd1a7a6a",
            "amenities": ".facilitiesListItem",
            "availability": ".prco-valignmiddle-haligncenter"
        }
    },
    "tripadvisor": {
        "name": "TripAdvisor",
        "base_url": "https://www.tripadvisor.com",
        "search_url": "/Search",
        "params": {
            "q": "{city} hotels"
        },
        "selectors": {
            "hotel_name": ".result-title",
            "price": ".price-wrap",
            "rating": ".rating-reviews-count",
            "reviews": ".review-count",
            "location": ".result-location"
        }
    },
    "expedia": {
        "name": "Expedia",
        "base_url": "https://www.expedia.com",
        "search_url": "/Hotel-Search",
        "params": {
            "destination": "{city}"
        },
        "selectors": {
            "hotel_name": ".hotel-name",
            "price": ".uitk-type-500",
            "rating": ".uitk-type-500",
            "reviews": ".uitk-type-200"
        }
    },
    "google_hotels": {
        "name": "Google Hotels",
        "base_url": "https://www.google.com",
        "search_url": "/travel/hotels/search",
        "params": {
            "q": "hotels in {city}"
        }
    }
}

AIRLINE_SOURCES = {
    "avianca": {
        "name": "Avianca",
        "base_url": "https://www.avianca.com",
        "routes_url": "/co/es/",
        "monitored_routes": [
            "BOG-MDE", "BOG-CTG", "BOG-CLO", "BOG-BAQ",
            "MDE-BOG", "CTG-BOG", "BOG-SMR"
        ]
    },
    "latam": {
        "name": "LATAM Airlines",
        "base_url": "https://www.latam.com",
        "routes_url": "/co/es/",
        "monitored_routes": [
            "BOG-MDE", "BOG-CTG", "BOG-CLO", "BOG-BAQ"
        ]
    },
    "viva_air": {
        "name": "Viva Air",
        "base_url": "https://www.vivaair.com",
        "monitored_routes": [
            "BOG-MDE", "BOG-CTG", "BOG-CLO"
        ]
    }
}

NEWS_SOURCES = {
    "el_tiempo": {
        "name": "El Tiempo",
        "base_url": "https://www.eltiempo.com",
        "sections": ["/economia", "/vida", "/tecnosfera"],
        "keywords": ["turismo", "hotel", "viaje", "vacaciones"]
    },
    "portafolio": {
        "name": "Portafolio",
        "base_url": "https://www.portafolio.co",
        "sections": ["/economia", "/negocios"],
        "keywords": ["turismo", "hotel", "inversión"]
    },
    "semana": {
        "name": "Semana",
        "base_url": "https://www.semana.com",
        "sections": ["/economia", "/turismo"],
        "keywords": ["turismo", "hotel", "Colombia"]
    }
}

CITIES = {
    "bogota": {
        "name": "Bogotá",
        "code": "BOG",
        "country": "Colombia",
        "hotels_target": 250
    },
    "medellin": {
        "name": "Medellín",
        "code": "MDE",
        "country": "Colombia",
        "hotels_target": 180
    },
    "cartagena": {
        "name": "Cartagena",
        "code": "CTG",
        "country": "Colombia",
        "hotels_target": 150
    },
    "cali": {
        "name": "Cali",
        "code": "CLO",
        "country": "Colombia",
        "hotels_target": 120
    },
    "barranquilla": {
        "name": "Barranquilla",
        "code": "BAQ",
        "country": "Colombia",
        "hotels_target": 80
    },
    "santa_marta": {
        "name": "Santa Marta",
        "code": "SMR",
        "country": "Colombia",
        "hotels_target": 70
    }
}
```

## Scraper Implementation

```python
#!/usr/bin/env python3
"""
Hotel & Tourism Scraper for Tourism Intelligence Platform
"""

import os
import sys
import json
import logging
import asyncio
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/tourism-intel/logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_dir": "/opt/tourism-intel/data",
    "sheets_api": "http://localhost:8095",
    "data_retention_days": 90,
    "check_interval": 900  # 15 minutes
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)


class HotelScraper:
    """Scrapes hotel data from multiple sources"""
    
    def __init__(self, source: str = "booking"):
        self.source = source
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def generate_hotel_id(self, name: str, location: str) -> str:
        """Generate unique ID for hotel"""
        raw = f"{name}{location}{self.source}"
        return f"HOTEL-{hashlib.md5(raw.encode()).hexdigest()[:10].upper()}"
    
    async def scrape_booking(self, city: str, checkin: str, checkout: str) -> List[Dict]:
        """Scrape Booking.com"""
        hotels = []
        
        try:
            # Use Playwright for JavaScript rendering
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                url = f"https://www.booking.com/searchresults.html?ss={city}&checkin={checkin}&checkout={checkout}"
                await page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Scroll to load more results
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 2000)")
                    await page.wait_for_timeout(2000)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'lxml')
                
                # Parse hotels
                for item in soup.select('.sr_property_block'):
                    try:
                        name = item.select_one('.sr-hotel__name')
                        if not name:
                            continue
                            
                        hotel = {
                            "id": self.generate_hotel_id(name.get_text(strip=True), city),
                            "source": "booking",
                            "name": name.get_text(strip=True),
                            "location": city,
                            "url": "https://booking.com" + item.select_one('a')['href'] if item.select_one('a') else "",
                            "price": item.select_one('.prco-valignmiddle-haligncenter')?.get_text(strip=True) or "",
                            "rating": item.select_one('.b5c098ed25-score-bar-scoreValue')?.get_text(strip=True) or "",
                            "reviews_count": item.select_one('.b5c098ed25-count')?.get_text(strip=True) or "",
                            "stars": len(item.select('.startrack_star starTrack_star Gold')) or 0,
                            "scraped_at": datetime.now().isoformat()
                        }
                        hotels.append(hotel)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing hotel: {e}")
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Booking scraping error: {e}")
        
        return hotels
    
    def scrape_tripadvisor(self, city: str) -> List[Dict]:
        """Scrape TripAdvisor"""
        hotels = []
        
        try:
            url = f"https://www.tripadvisor.com/Hotels-{city}-Colombia"
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            for item in soup.select('.hotel'):
                try:
                    name = item.select_one('.property-title')
                    if not name:
                        continue
                    
                    hotel = {
                        "id": self.generate_hotel_id(name.get_text(strip=True), city),
                        "source": "tripadvisor",
                        "name": name.get_text(strip=True),
                        "location": city,
                        "rating": item.select_one('.ui_rating')?.get('alt', '').replace(' of 5 bubbles', '') or "",
                        "reviews_count": item.select_one('.review-count')?.get_text(strip=True) or "",
                        "scraped_at": datetime.now().isoformat()
                    }
                    hotels.append(hotel)
                    
                except Exception as e:
                    logger.warning(f"Error parsing TripAdvisor hotel: {e}")
                    
        except Exception as e:
            logger.error(f"TripAdvisor error: {e}")
        
        return hotels
    
    def scrape_all_sources(self, city: str) -> List[Dict]:
        """Scrape all sources for a city"""
        all_hotels = []
        
        # Calculate dates
        checkin = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        
        # Booking (async)
        logger.info(f"Scraping Booking for {city}...")
        booking = HotelScraper("booking")
        all_hotels.extend(asyncio.run(booking.scrape_booking(city, checkin, checkout)))
        
        # TripAdvisor (sync)
        logger.info(f"Scraping TripAdvisor for {city}...")
        tripadvisor = HotelScraper("tripadvisor")
        all_hotels.extend(tripadvisor.scrape_tripadvisor(city))
        
        # Remove duplicates by name
        seen = set()
        unique_hotels = []
        for hotel in all_hotels:
            if hotel['name'] not in seen:
                seen.add(hotel['name'])
                unique_hotels.append(hotel)
        
        logger.info(f"Found {len(unique_hotels)} unique hotels in {city}")
        return unique_hotels


class AirlineScraper:
    """Scrapes airline data"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
    
    def scrape_avianca(self) -> List[Dict]:
        """Scrape Avianca routes"""
        routes = []
        
        try:
            # This is a simplified version - real implementation would need more complex parsing
            url = "https://www.avianca.com/co/es/"
            response = self.session.get(url, timeout=30)
            
            # Parse routes (simplified)
            monitored = ["BOG-MDE", "BOG-CTG", "BOG-CLO", "BOG-BAQ", "BOG-SMR"]
            
            for route in monitored:
                routes.append({
                    "airline": "Avianca",
                    "route": route,
                    "origin": route.split("-")[0],
                    "destination": route.split("-")[1],
                    "scraped_at": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Avianca scraping error: {e}")
        
        return routes
    
    def scrape_latam(self) -> List[Dict]:
        """Scrape LATAM routes"""
        routes = []
        
        try:
            url = "https://www.latam.com/co/es/"
            response = self.session.get(url, timeout=30)
            
            monitored = ["BOG-MDE", "BOG-CTG", "BOG-CLO", "BOG-BAQ"]
            
            for route in monitored:
                routes.append({
                    "airline": "LATAM",
                    "route": route,
                    "origin": route.split("-")[0],
                    "destination": route.split("-")[1],
                    "scraped_at": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"LATAM scraping error: {e}")
        
        return routes


class NewsScraper:
    """Scrapes tourism news"""
    
    def __init__(self):
        self.session = requests.Session()
    
    def scrape_news(self, keyword: str = "turismo") -> List[Dict]:
        """Scrape tourism news"""
        articles = []
        
        sources = [
            ("el_tiempo", "https://www.eltiempo.com/buscar"),
            ("portafolio", "https://www.portafolio.co/buscar"),
            ("semana", "https://www.semana.com/buscar")
        ]
        
        for source, base_url in sources:
            try:
                params = {"q": keyword}
                response = self.session.get(base_url, params=params, timeout=30)
                soup = BeautifulSoup(response.content, 'lxml')
                
                for item in soup.select('article')[:10]:
                    title = item.select_one('h2, h3, .title')
                    if not title:
                        continue
                    
                    article = {
                        "source": source,
                        "title": title.get_text(strip=True),
                        "url": item.select_one('a')['href'] if item.select_one('a') else "",
                        "keyword": keyword,
                        "scraped_at": datetime.now().isoformat()
                    }
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"News scraping error for {source}: {e}")
        
        return articles


class Orchestrator:
    """Coordinates all scrapers"""
    
    def __init__(self):
        self.cities = ["bogota", "medellin", "cartagena", "cali", "barranquilla", "santa_marta"]
        self.hotel_scraper = HotelScraper()
        self.airline_scraper = AirlineScraper()
        self.news_scraper = NewsScraper()
    
    def run_full_cycle(self):
        """Run complete scraping cycle"""
        logger.info("=== Starting Full Scraping Cycle ===")
        
        all_data = {
            "hotels": [],
            "airlines": [],
            "news": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Scrape hotels for each city
        for city in self.cities:
            logger.info(f"Processing city: {city}")
            hotels = self.hotel_scraper.scrape_all_sources(city)
            all_data["hotels"].extend(hotels)
        
        # Scrape airlines
        logger.info("Scraping airlines...")
        all_data["airlines"].extend(self.airline_scraper.scrape_avianca())
        all_data["airlines"].extend(self.airline_scraper.scrape_latam())
        
        # Scrape news
        logger.info("Scraping news...")
        all_data["news"].extend(self.news_scraper.scrape_news("turismo Colombia"))
        all_data["news"].extend(self.news_scraper.scrape_news("hotel Colombia"))
        
        # Save to disk
        self.save_data(all_data)
        
        # Send to Sheets API
        self.send_to_sheets(all_data)
        
        logger.info(f"Cycle complete: {len(all_data['hotels'])} hotels, {len(all_data['airlines'])} routes, {len(all_data['news'])} articles")
        
        return all_data
    
    def save_data(self, data: Dict):
        """Save scraped data"""
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Hotels
        hotels_file = Path(CONFIG["output_dir"]) / "hotels" / f"{date_str}.json"
        hotels_file.parent.mkdir(parents=True, exist_ok=True)
        with open(hotels_file, "w") as f:
            json.dump(data["hotels"], f, indent=2)
        
        # Airlines
        airlines_file = Path(CONFIG["output_dir"]) / "airlines" / f"{date_str}.json"
        airlines_file.parent.mkdir(parents=True, exist_ok=True)
        with open(airlines_file, "w") as f:
            json.dump(data["airlines"], f, indent=2)
        
        # News
        news_file = Path(CONFIG["output_dir"]) / "news" / f"{date_str}.json"
        news_file.parent.mkdir(parents=True, exist_ok=True)
        with open(news_file, "w") as f:
            json.dump(data["news"], f, indent=2)
    
    def send_to_sheets(self, data: Dict):
        """Send data to Google Sheets"""
        try:
            response = requests.post(
                f"{CONFIG['sheets_api']}/data/hotels",
                json={"hotels": data["hotels"]},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Data sent to Google Sheets")
                
        except Exception as e:
            logger.error(f"Failed to send to sheets: {e}")


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run_full_cycle()
```

## Scheduler Integration

```python
# Run every 15 minutes
import schedule
import time

def run_scraping_cycle():
    orchestrator = Orchestrator()
    orchestrator.run_full_cycle()

# Schedule
schedule.every(15).minutes.do(run_scraping_cycle)

# Also run at specific times
schedule.every().day.at("06:00").do(run_scraping_cycle)
schedule.every().day.at("12:00").do(run_scraping_cycle)
schedule.every().day.at("18:00").do(run_scraping_cycle)
schedule.every().day.at("00:00").do(run_scraping_cycle)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Next Steps

- [03-sentiment](./03-sentiment.md) - Sentiment analysis
