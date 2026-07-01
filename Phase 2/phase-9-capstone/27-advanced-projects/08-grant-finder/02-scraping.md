# Funding Finder - Web Scraping System

## Scrapling Installation

### Install Scrapling

```bash
# Create virtual environment
python3 -m venv /opt/funding-finder/venv
source /opt/funding-finder/venv/bin/activate

# Install Scrapling
pip install scrapling
pip install -U scrapling

# Install additional dependencies
pip install \
  requests \
  beautifulsoup4 \
  lxml \
  playwright \
  pypdf2 \
  python-docx \
  openpyxl \
  pandas \
  schedule

# Install Playwright browsers
playwright install chromium
playwright install-deps
```

### Install undetected-chromedriver (for dynamic sites)

```bash
pip install undetected-chromedriver
```

## Scraping Targets

### Colombian Government Sources

```python
COLOMBIA_SOURCES = {
    # Science & Technology
    "colciencias": {
        "url": "https://colciencias.gov.co/convocatorias",
        "keywords": ["convocatoria", "financiación", "proyecto"],
        "filter": "Colombia"
    },
    
    # National Learning Service
    "senasena": {
        "url": "https://www.sena.edu.co/Pages/Convocatorias.aspx",
        "keywords": ["convocatoria", "fondo", "proyecto"],
        "filter": "Colombia"
    },
    
    # Export Promotion
    "procolombia": {
        "url": "https://procolombia.co/convocatorias",
        "keywords": ["convocatoria", "financiero"],
        "filter": "Colombia"
    },
    
    # Findeter (Development Finance)
    "findeter": {
        "url": "https://www.findeter.gov.co/convocatorias/",
        "keywords": ["convocatoria", "financiación"],
        "filter": "Colombia"
    },
    
    # Bancoldex (Foreign Trade Bank)
    "bancoldex": {
        "url": "https://www.bancoldex.com/convocatorias",
        "keywords": ["convocatoria", "fondo"],
        "filter": "Colombia"
    },
    
    # ICONTEC (Standards)
    "icontec": {
        "url": "https://www.icontec.org/convocatorias",
        "keywords": ["convocatoria"],
        "filter": "Colombia"
    },
    
    # ICETEX (Education Credits)
    "icetex": {
        "url": "https://www.icetex.gov.co/convocatorias",
        "keywords": ["convocatoria", "becas"],
        "filter": "Colombia"
    },
    
    # Ministry of Education
    "mineducacion": {
        "url": "https://www.mineducacion.gov.co/convocatorias",
        "keywords": ["convocatoria", "educación"],
        "filter": "Colombia"
    },
    
    # INVIMA (Health)
    "invima": {
        "url": "https://www.invima.gov.co/convocatorias",
        "keywords": ["convocatoria", "investigación"],
        "filter": "Colombia"
    },
    
    # Environmental
    "minambiente": {
        "url": "https://www.minambiente.gov.co/convocatorias",
        "keywords": ["convocatoria", "ambiental"],
        "filter": "Colombia"
    }
}
```

### International Sources

```python
INTERNATIONAL_SOURCES = {
    # European Union
    "eu_cordis": {
        "url": "https://cordis.europa.eu/projects",
        "keywords": ["Colombia", "Latin America", "international"],
        "filter": "open"
    },
    
    "eu_ideas": {
        "url": "https://ec.europa.eu/info/funding-tenders",
        "keywords": ["third country", "developing"],
        "filter": "open"
    },
    
    # United Nations
    "undp": {
        "url": "https://www.undp.org/procurement",
        "keywords": ["call", "proposal", "Colombia"],
        "filter": "active"
    },
    
    "unesco": {
        "url": "https://www.unesco.org/en/fellowships",
        "keywords": ["Colombia", "grant"],
        "filter": "open"
    },
    
    # World Bank / IDB
    "worldbank": {
        "url": "https://www.worldbank.org/en/projects-operations/procurement",
        "keywords": ["Colombia", "loan"],
        "filter": "open"
    },
    
    "idb": {
        "url": "https://www.iadb.org/en/procuring",
        "keywords": ["Colombia", "project"],
        "filter": "open"
    },
    
    # Bilateral
    "usaid": {
        "url": "https://www.usaid.gov/partnership-opportunities",
        "keywords": ["Colombia", "grant"],
        "filter": "open"
    },
    
    "aeci": {
        "url": "https://www.aecid.es/convocatorias",
        "keywords": ["Colombia", "América Latina"],
        "filter": "open"
    },
    
    # Private Foundations
    "ford_foundation": {
        "url": "https://fordfoundation.org/Grants/",
        "keywords": ["Colombia", "Latin America"],
        "filter": "open"
    },
    
    "gates": {
        "url": "https://www.gatesfoundation.org/How-We-Work",
        "keywords": ["Latin America", "Colombia"],
        "filter": "open"
    }
}
```

## Scraper Implementation

### Main Scraper Script

```python
#!/usr/bin/env python3
"""
Funding Opportunity Scraper using Scrapling
Runs 24/7 searching for Colombia-related funding opportunities
"""

import os
import sys
import json
import time
import logging
import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import scrapling
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/funding-finder/logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_dir": "/opt/funding-finder/data/opportunities",
    "sheets_api": "http://localhost:8080/api/sheets",  # Local API
    "filter_word": "Colombia",
    "check_interval": 3600,  # 1 hour
    "max_concurrent": 5
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)


class FundingScraper:
    """Main scraper class for funding opportunities"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.found_opportunities = []
        
    def generate_id(self, title: str, url: str) -> str:
        """Generate unique ID for opportunity"""
        raw = f"{title}{url}{datetime.now().date()}"
        return f"FU-{hashlib.md5(raw.encode()).hexdigest()[:12].upper()}"
    
    def is_colombia_related(self, text: str) -> bool:
        """Check if opportunity is related to Colombia"""
        colomba_keywords = [
            "colombia", "colombiano", "colombiana",
            "bogotá", "medellín", "cali", "barranquilla",
            "latinoamérica", "américa latina", "latin american",
            "iberoamérica", "hispanohablante", "spanish speaking",
            "suramérica", "south america",
            "países andinos", "andean country"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in colomba_keywords)
    
    def parse_opportunity(self, source: str, url: str, title: str, 
                         description: str, deadline: str = None,
                         budget: str = None, category: str = None) -> Optional[Dict]:
        """Parse and validate opportunity"""
        
        full_text = f"{title} {description} {budget or ''}"
        
        if not self.is_colombia_related(full_text):
            return None
        
        # Determine category
        if category is None:
            cat_keywords = {
                "educational": ["educación", "educacion", "learning", "school", "university"],
                "technological": ["tecnología", "tecnologia", "tech", "innovation", "I+D"],
                "environmental": ["ambiental", "ambiente", "environment", "climate", "green"],
                "social": ["social", "community", "people"],
                "tourism": ["turismo", "tourism", "cultura", "culture"],
                "health": ["salud", "health", "médico", "medical"],
                "agricultural": ["agricultura", "agricultural", "rural", "farmer"],
                "economic": ["económic", "economic", "business", "enterprise", "pyme"]
            }
            for cat, keywords in cat_keywords.items():
                if any(kw in full_text.lower() for kw in keywords):
                    category = cat
                    break
            category = category or "general"
        
        return {
            "id": self.generate_id(title, url),
            "source": source,
            "url": url,
            "title": title.strip(),
            "description": description.strip()[:500],
            "deadline": deadline,
            "budget": budget,
            "category": category,
            "status": "NEW",
            "language": "es" if any(w in full_text.lower() for w in 
                ["colombia", "convocatoria", "fondo", "ministerio"]) else "en",
            "date_found": datetime.now().isoformat(),
            "documents_downloaded": False,
            "proposal_status": "PENDING"
        }
    
    async def scrape_with_scrapling(self, url: str, selectors: Dict) -> List[Dict]:
        """Use Scrapling for dynamic content"""
        try:
            # Use Scrapling's spider
            spider = scrapling.Spider()
            
            # Custom selectors for funding sites
            result = spider.crawl(url, custom_selectors=selectors)
            
            opportunities = []
            for item in result.get('items', []):
                opportunities.append({
                    'title': item.get('title', ''),
                    'description': item.get('description', ''),
                    'url': item.get('url', url),
                    'deadline': item.get('deadline', ''),
                    'budget': item.get('budget', '')
                })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Scrapling error for {url}: {e}")
            return []
    
    async def scrape_with_playwright(self, url: str) -> List[Dict]:
        """Fallback to Playwright for JavaScript-heavy sites"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(url, wait_until='networkidle')
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'lxml')
                
                opportunities = []
                
                # Generic extraction - adapt per site
                # This is a template - customize selectors per source
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if any(kw in text.lower() for kw in ['convocatoria', 'call', 'grant', 'funding']):
                        opportunities.append({
                            'title': text,
                            'description': '',
                            'url': href if href.startswith('http') else f"{url}{href}",
                            'deadline': '',
                            'budget': ''
                        })
                
                await browser.close()
                return opportunities
                
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return []
    
    def scrape_static_site(self, url: str) -> List[Dict]:
        """Scrape static HTML sites"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            opportunities = []
            
            # Generic extraction - customize per source
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if any(kw in text.lower() for kw in ['convocatoria', 'call', 'grant', 'funding', 'fondo']):
                    opportunities.append({
                        'title': text,
                        'description': link.find_next_sibling('p').get_text(strip=True) if link.find_next_sibling('p') else '',
                        'url': href if href.startswith('http') else f"{url}{href}",
                        'deadline': '',
                        'budget': ''
                    })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Static scrape error for {url}: {e}")
            return []
    
    async def process_source(self, source_name: str, source_config: Dict) -> List[Dict]:
        """Process a single source"""
        url = source_config.get("url", "")
        
        logger.info(f"Scraping {source_name}: {url}")
        
        opportunities = []
        
        # Try static first
        raw_opps = self.scrape_static_site(url)
        
        # If empty, try dynamic methods
        if not raw_opps:
            try:
                raw_opps = await self.scrape_with_playwright(url)
            except:
                pass
        
        # Parse each opportunity
        for raw in raw_opps:
            opp = self.parse_opportunity(
                source=source_name,
                url=raw.get('url', url),
                title=raw.get('title', ''),
                description=raw.get('description', ''),
                deadline=raw.get('deadline'),
                budget=raw.get('budget')
            )
            
            if opp:
                opportunities.append(opp)
        
        logger.info(f"Found {len(opportunities)} Colombia-related opportunities in {source_name}")
        return opportunities
    
    async def run_scraping_cycle(self):
        """Run one complete scraping cycle"""
        from .sources import COLOMBIA_SOURCES, INTERNATIONAL_SOURCES
        
        all_sources = {**COLOMBIA_SOURCES, **INTERNATIONAL_SOURCES}
        
        logger.info(f"Starting scraping cycle - {len(all_sources)} sources")
        
        tasks = []
        for source_name, source_config in all_sources.items():
            tasks.append(self.process_source(source_name, source_config))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                self.found_opportunities.extend(result)
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_opportunities = []
        for opp in self.found_opportunities:
            if opp['url'] not in seen_urls:
                seen_urls.add(opp['url'])
                unique_opportunities.append(opp)
        
        self.found_opportunities = unique_opportunities
        
        logger.info(f"Cycle complete - {len(self.found_opportunities)} unique opportunities")
        
        # Send to Google Sheets API
        await self.send_to_sheets()
        
        return len(self.found_opportunities)
    
    async def send_to_sheets(self):
        """Send opportunities to local API for Google Sheets"""
        try:
            response = requests.post(
                f"{CONFIG['sheets_api']}/add_opportunities",
                json={"opportunities": self.found_opportunities},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Opportunities sent to Google Sheets")
            else:
                logger.error(f"Failed to send to sheets: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending to sheets: {e}")
    
    async def continuous_scrape(self):
        """Run scraping continuously"""
        logger.info("Starting continuous scraping...")
        
        while True:
            try:
                count = await self.run_scraping_cycle()
                logger.info(f"Sleeping {CONFIG['check_interval']}s before next cycle")
                await asyncio.sleep(CONFIG['check_interval"])
                
            except KeyboardInterrupt:
                logger.info("Scraping stopped by user")
                break
            except Exception as e:
                logger.error(f"Scraping cycle error: {e}")
                await asyncio.sleep(60)  # Wait 1 min on error


async def main():
    """Main entry point"""
    scraper = FundingScraper()
    await scraper.continuous_scrape()


if __name__ == "__main__":
    asyncio.run(main())
```

### Source Configuration

```python
# sources.py

COLOMBIA_SOURCES = {
    "colciencias": {
        "url": "https://colciencias.gov.co/convocatorias",
        "method": "static",
        "selectors": {
            "title": ".convocatoria-title",
            "description": ".convocatoria-description", 
            "deadline": ".convocatoria-fecha",
            "budget": ".convocatoria-presupuesto"
        }
    },
    "senasena": {
        "url": "https://www.sena.edu.co/Pages/Convocatorias.aspx",
        "method": "playwright",
        "selectors": {}
    },
    # Add more sources...
}

INTERNATIONAL_SOURCES = {
    "eu_cordis": {
        "url": "https://cordis.europa.eu/projects",
        "method": "static",
        "selectors": {}
    },
    # Add more sources...
}
```

## Scheduled Scraping

### Cron-like Scheduler

```python
# scheduler.py
import schedule
import time
import asyncio

def run_scraper():
    """Run scraper on schedule"""
    from scraper import FundingScraper
    
    async def run():
        scraper = FundingScraper()
        await scraper.run_scraping_cycle()
    
    asyncio.run(run())

# Schedule scraping
schedule.every().hour.do(run_scraper)
schedule.every().day.at("06:00").do(run_scraper)  # Morning scan
schedule.every().day.at("18:00").do(run_scraper)  # Evening scan

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Installation

```bash
# Create service
sudo tee /etc/systemd/system/funding-scraper.service << 'EOF'
[Unit]
Description=Funding Opportunity Scraper
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/funding-finder
ExecStart=/opt/funding-finder/venv/bin/python scraper.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable funding-scraper
sudo systemctl start funding-scraper
```

## Next Steps

- [03-sheets](./03-sheets.md) - Google Sheets integration
- [04-documents](./04-documents.md) - Document processing
