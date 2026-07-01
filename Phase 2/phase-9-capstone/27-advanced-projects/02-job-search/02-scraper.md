# Job Scraper

Multi-site job scraping with support for Indeed, LinkedIn, and other job boards.

## Base Scraper

```python
# scraper/base_scraper.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all job scrapers"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    @abstractmethod
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict]:
        """Search for jobs"""
        pass
    
    @abstractmethod
    def get_job_details(self, job_url: str) -> Dict:
        """Get detailed job information"""
        pass
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        # Remove extra whitespace, newlines
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_salary(self, text: str) -> Optional[Dict]:
        """Extract salary information"""
        import re
        
        # Pattern for salary ranges
        patterns = [
            r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?(?:\s*/\s*(?:hour|day|week|month|year))?',
            r'[\d,]+(?:\s*-\s*[\d,]+)?\s*(?:USD|EUR|GBP)\s*(?:/|\s+per)\s*(?:hour|day|week|month|year)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'raw': match.group(),
                    'text': text[max(0, match.start()-20):match.end()+20]
                }
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract posting date"""
        import re
        from datetime import timedelta
        
        text_lower = text.lower()
        
        # Time patterns
        patterns = {
            r'(\d+)\s*hours?\s*ago': lambda m: datetime.now() - timedelta(hours=int(m.group(1))),
            r'(\d+)\s*days?\s*ago': lambda m: datetime.now() - timedelta(days=int(m.group(1))),
            r'(\d+)\s*weeks?\s*ago': lambda m: datetime.now() - timedelta(weeks=int(m.group(1))),
        }
        
        for pattern, converter in patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                date = converter(match)
                return date.isoformat()
        
        return None
```

## Indeed Scraper

```python
# scraper/indeed.py
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class IndeedScraper(BaseScraper):
    """Scrape jobs from Indeed"""
    
    BASE_URL = "https://www.indeed.com"
    
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict]:
        jobs = []
        start = 0
        
        for page in range(kwargs.get('max_pages', 3)):
            url = f"{self.BASE_URL}/jobs?q={keywords}&l={location}&start={start}"
            
            try:
                response = requests.get(url, headers=self.session_headers, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.select('div.jobsearch-ResultsList > li')
                
                if not job_cards:
                    break
                
                for card in job_cards:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                
                start += 10
                
            except Exception as e:
                logger.error(f"Error scraping Indeed: {e}")
                break
        
        logger.info(f"Found {len(jobs)} jobs from Indeed")
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Dict]:
        """Parse a job card element"""
        try:
            # Get job title and URL
            title_elem = card.select_one('h2.jobTitle a')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            url = self.BASE_URL + title_elem.get('href', '')
            
            # Get company
            company_elem = card.select_one('span.companyName')
            company = company_elem.get_text(strip=True) if company_elem else ""
            
            # Get location
            location_elem = card.select_one('div.companyLocation')
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Get salary
            salary_elem = card.select_one('span.salaryText')
            salary = salary_elem.get_text(strip=True) if salary_elem else ""
            
            # Get snippet
            snippet_elem = card.select_one('div.job-snippet')
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Get date
            date_elem = card.select_one('span.date')
            date_posted = date_elem.get_text(strip=True) if date_elem else ""
            
            return {
                'source': 'indeed',
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'salary': salary,
                'snippet': snippet,
                'date_posted': date_posted,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing job card: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Dict:
        """Get full job description"""
        try:
            response = requests.get(job_url, headers=self.session_headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get full description
            desc_elem = soup.select_one('div.jobsearch-JobComponent-description')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Get job details
            details = {}
            for row in soup.select('div.jobsearch-JobDetailAttributesItem'):
                label = row.select_one('span.label')
                value = row.select_one('span.value')
                if label and value:
                    details[label.get_text(strip=True)] = value.get_text(strip=True)
            
            return {
                'url': job_url,
                'description': description,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return {'url': job_url, 'description': '', 'details': {}}
```

## LinkedIn Scraper

```python
# scraper/linkedin.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class LinkedInScraper(BaseScraper):
    """Scrape jobs from LinkedIn (requires authentication)"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.driver = None
    
    def _get_driver(self):
        """Get or create WebDriver"""
        if not self.driver:
            self.driver = webdriver.Chrome(options=self.options)
        return self.driver
    
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict]:
        jobs = []
        driver = self._get_driver()
        
        # Build URL
        url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
        
        try:
            driver.get(url)
            
            # Wait for jobs to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.jobs-search-results__list-item'))
            )
            
            # Scroll to load more
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                import time
                time.sleep(2)
            
            # Parse jobs
            job_elements = driver.find_elements(By.CSS_SELECTOR, '.jobs-search-results__list-item')
            
            for elem in job_elements:
                job = self._parse_job_element(elem)
                if job:
                    jobs.append(job)
                    
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
        finally:
            # Don't close driver - reuse it
            pass
        
        logger.info(f"Found {len(jobs)} jobs from LinkedIn")
        return jobs
    
    def _parse_job_element(self, elem) -> Optional[Dict]:
        """Parse a LinkedIn job element"""
        try:
            title_elem = elem.find_element(By.CSS_SELECTOR, '.job-card-list__title')
            title = title_elem.text.strip()
            url = title_elem.get_attribute('href')
            
            company_elem = elem.find_element(By.CSS_SELECTOR, '.job-card-container__company-name')
            company = company_elem.text.strip()
            
            location_elem = elem.find_element(By.CSS_SELECTOR, '.job-card-container__metadata-item')
            location = location_elem.text.strip()
            
            return {
                'source': 'linkedin',
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return None
    
    def get_job_details(self, job_url: str) -> Dict:
        """Get full job description"""
        driver = self._get_driver()
        
        try:
            driver.get(job_url)
            
            # Wait for description
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.jobs-description__content'))
            )
            
            desc_elem = driver.find_element(By.CSS_SELECTOR, '.jobs-description__content')
            description = desc_elem.text
            
            return {
                'url': job_url,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Error getting LinkedIn job details: {e}")
            return {'url': job_url, 'description': ''}
    
    def close(self):
        """Close driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
```

## Multi-Site Aggregator

```python
# scraper/aggregator.py
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class JobAggregator:
    """Aggregate jobs from multiple sources"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.scrapers = {
            'indeed': IndeedScraper(config),
            'linkedin': LinkedInScraper(config),
        }
    
    def search_all(
        self, 
        keywords: str, 
        locations: List[str],
        sources: List[str] = None,
        max_workers: int = 3
    ) -> List[Dict]:
        """Search all sources in parallel"""
        if sources is None:
            sources = ['indeed', 'linkedin']
        
        all_jobs = []
        
        def search_source(source, keywords, location):
            scraper = self.scrapers.get(source)
            if scraper:
                return scraper.search(keywords, location)
            return []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for source in sources:
                for location in locations:
                    future = executor.submit(search_source, source, keywords, location)
                    futures.append((source, location, future))
            
            for source, location, future in futures:
                try:
                    jobs = future.result()
                    for job in jobs:
                        job['search_keywords'] = keywords
                        job['search_location'] = location
                    all_jobs.extend(jobs)
                    logger.info(f"{source} ({location}): {len(jobs)} jobs")
                except Exception as e:
                    logger.error(f"Error from {source} ({location}): {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        logger.info(f"Total unique jobs: {len(unique_jobs)}")
        return unique_jobs
    
    def close(self):
        """Close all scrapers"""
        for scraper in self.scrapers.values():
            if hasattr(scraper, 'close'):
                scraper.close()
```

## Usage

```python
# main.py - Job scraping
from scraper.aggregator import JobAggregator

config = {
    'max_pages': 3
}

aggregator = JobAggregator(config)

# Search for yacht jobs
jobs = aggregator.search_all(
    keywords="yacht chef",
    locations=["Miami, FL", "Fort Lauderdale, FL"],
    sources=['indeed']
)

# Save results
import json
with open('data/jobs_raw.json', 'w') as f:
    json.dump(jobs, f, indent=2)

aggregator.close()
```

## Next Steps

- [AI Processing](./08-ai-processing.md) - Filter and format jobs
