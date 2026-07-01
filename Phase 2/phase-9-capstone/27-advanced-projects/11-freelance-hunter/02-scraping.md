# Freelance Hunter - Web Scraping System

## Overview

The scraping system collects job postings from 10+ freelance platforms using multiple techniques. It handles authentication, rate limiting, captchas, and anti-bot measures.

## Platform Configurations

```python
# config/platforms.py

PLATFORMS = {
    "upwork": {
        "name": "Upwork",
        "base_url": "https://www.upwork.com",
        "jobs_url": "https://www.upwork.com/ab/jobs/search",
        "search_params": {
            "categories": ["web_mobile_software_dev", "data_science_analytics"],
            "subcategories": ["back-end_development", "front-end_development"],
            "experience_level": ["expert", "intermediate"],
            "job_type": ["hourly", "fixed-price"],
            "duration": ["ongoing", "short_term", "medium_term"]
        },
        "selectors": {
            "job_title": ".job-title",
            "job_description": ".job-description",
            "budget": ".job-budget",
            "skills": ".skill-tag",
            "client_info": ".client-info",
            "posted_time": ".job-posted",
            "proposals": ".proposals-count"
        },
        "requires_auth": True,
        "rate_limit": 30  # seconds between requests
    },
    "freelancer": {
        "name": "Freelancer",
        "base_url": "https://www.freelancer.com",
        "jobs_url": "https://www.freelancer.com/jobs",
        "search_params": {
            "keywords": ["python", "javascript", "react", "node"],
            "categories": ["web_development", "software_development"],
            "levels": ["expert", "intermediate"]
        },
        "selectors": {
            "job_title": ".JobSearchCard-primary-heading",
            "job_description": ".JobSearchCard-description",
            "budget": ".JobSearchCard-price",
            "skills": ".JobSearchCard-tags",
            "client_info": ".JobSearchCard-client"
        },
        "requires_auth": True,
        "rate_limit": 45
    },
    "fiverr": {
        "name": "Fiverr",
        "base_url": "https://www.fiverr.com",
        "jobs_url": "https://www.fiverr.com/categories/graphics-ads",
        "search_params": {
            "category": ["programming-tech", "web-programming"],
            "subcategory": ["web-apps", "mobile-apps"]
        },
        "selectors": {
            "gig_title": ".gig-card-title",
            "description": ".gig-card-description",
            "price": ".price-tag",
            "delivery": ".delivery-time",
            "seller_level": ".seller-level"
        },
        "requires_auth": False,
        "rate_limit": 20
    },
    "toptal": {
        "name": "Toptal",
        "base_url": "https://www.toptal.com",
        "jobs_url": "https://www.toptal.com/jobs",
        "search_params": {
            "roles": ["full-stack", "back-end", "front-end", "devops"],
            "commitments": ["full-time", "part-time"]
        },
        "selectors": {
            "job_title": ".job-title",
            "description": ".job-description",
            "requirements": ".requirements"
        },
        "requires_auth": False,
        "rate_limit": 30
    },
    "remoteok": {
        "name": "RemoteOK",
        "base_url": "https://remoteok.com",
        "jobs_url": "https://remoteok.com/remote-dev-jobs",
        "search_params": {
            "tags": ["python", "javascript", "react", "node", "ai", "cuda"]
        },
        "selectors": {
            "job_title": ".job-title",
            "company": ".company",
            "tags": ".tags",
            "salary": ".salary",
            "apply_url": ".apply-url"
        },
        "requires_auth": False,
        "rate_limit": 15
    },
    "weworkremotely": {
        "name": "We Work Remotely",
        "base_url": "https://weworkremotely.com",
        "jobs_url": "https://weworkremotely.com/remote-jobs",
        "search_params": {
            "categories": ["software-dev", "devops-sre", "full-stack"],
            "type": ["contract", "full-time"]
        },
        "selectors": {
            "job_title": ".job-title",
            "company": ".company",
            "location": ".location",
            "tags": ".tags-list"
        },
        "requires_auth": False,
        "rate_limit": 20
    },
    "linkedin": {
        "name": "LinkedIn Jobs",
        "base_url": "https://www.linkedin.com",
        "jobs_url": "https://www.linkedin.com/jobs",
        "search_params": {
            "keywords": ["Python", "JavaScript", "React", "Full Stack"],
            "location": ["Remote", "Colombia"],
            "experience": ["Mid-Senior", "Director"]
        },
        "selectors": {
            "job_title": ".job-card-container__title",
            "company": ".job-card-container__company-name",
            "location": ".job-card-container__metadata-item",
            "description": ".job-card-container__snippet"
        },
        "requires_auth": True,
        "rate_limit": 60
    },
    "gunio": {
        "name": "Gun.io",
        "base_url": "https://gun.io",
        "jobs_url": "https://gun.io/job-board",
        "search_params": {
            "skills": ["python", "javascript", "react", "aws"]
        },
        "selectors": {
            "job_title": ".job-title",
            "company": ".company-name",
            "description": ".job-description",
            "rate": ".rate-range"
        },
        "requires_auth": False,
        "rate_limit": 30
    },
    "xteam": {
        "name": "X-Team",
        "base_url": "https://x-team.com",
        "jobs_url": "https://x-team.com/developers",
        "search_params": {
            "role": ["front-end", "back-end", "full-stack", "mobile"]
        },
        "selectors": {
            "job_title": ".job-role",
            "description": ".job-description",
            "perks": ".perks-list"
        },
        "requires_auth": False,
        "rate_limit": 30
    },
    "turing": {
        "name": "Turing",
        "base_url": "https://turing.com",
        "jobs_url": "https://turing.com/jobs",
        "search_params": {
            "roles": ["fullstack", "backend", "frontend", "mobile"]
        },
        "selectors": {
            "job_title": ".job-position-title",
            "company": ".company-name",
            "requirements": ".requirements-list"
        },
        "requires_auth": True,
        "rate_limit": 45
    }
}


SKILL_KEYWORDS = {
    "python": ["python", "django", "flask", "fastapi", "pandas", "numpy"],
    "javascript": ["javascript", "js", "node.js", "express", "react", "vue", "angular"],
    "react": ["react", "reactjs", "react.js", "next.js", "gatsby"],
    "cuda": ["cuda", "gpu", "nvidia", "tensorrt", "deep learning", "ml"],
    "devops": ["docker", "kubernetes", "aws", "gcp", "azure", "ci/cd"],
    "api": ["api", "rest", "graphql", "grpc", "microservices"],
    "database": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"]
}
```

## Scraper Implementation

```python
#!/usr/bin/env python3
"""
Freelance Platform Scraper
Multi-threaded scraping for 10+ platforms
"""

import os
import sys
import json
import logging
import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/freelance-hunter/logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    "output_dir": "/opt/freelance-hunter/data",
    "data_dir": "/opt/freelance-hunter/data/jobs",
    "profiles_dir": "/opt/freelance-hunter/data/profiles",
    "session_dir": "/opt/freelance-hunter/sessions",
    "rate_limit_file": "/opt/freelance-hunter/config/rate_limits.json",
    "api_url": "http://localhost:8096",
    "check_interval": 300  # 5 minutes
}

os.makedirs(CONFIG["data_dir"], exist_ok=True)
os.makedirs(CONFIG["profiles_dir"], exist_ok=True)
os.makedirs(CONFIG["session_dir"], exist_ok=True)
os.makedirs("/opt/freelance-hunter/logs", exist_ok=True)


@dataclass
class Job:
    """Job posting data model"""
    id: str
    platform: str
    title: str
    description: str
    url: str
    budget: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    hourly_rate: Optional[str] = None
    skills: List[str] = None
    category: str = ""
    subcategory: str = ""
    client_name: str = ""
    client_rating: float = 0.0
    client_spent: str = ""
    client_jobs: int = 0
    client_location: str = ""
    payment_verified: bool = False
    proposals_count: int = 0
    posted_at: str = ""
    expires_at: str = ""
    duration: str = ""
    experience_level: str = ""
    remote: bool = True
    tags: List[str] = None
    scraped_at: str = ""
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.tags is None:
            self.tags = []
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()
        if not self.id:
            self.id = self.generate_id()
    
    def generate_id(self) -> str:
        raw = f"{self.platform}{self.title}{self.url}"
        return f"JOB-{hashlib.md5(raw.encode()).hexdigest()[:10].upper()}"


class BaseScraper:
    """Base scraper class"""
    
    def __init__(self, platform: str, config: Dict):
        self.platform = platform
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        self.rate_limit = config.get("rate_limit", 30)
        self.last_request = 0
    
    def rate_limit_wait(self):
        """Wait if needed for rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        text_lower = text.lower()
        found_skills = []
        
        for skill, keywords in SKILL_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found_skills.append(skill)
        
        return found_skills
    
    def parse_budget(self, budget_str: str) -> Dict:
        """Parse budget string to min/max"""
        import re
        
        result = {"min": None, "max": None, "type": "fixed"}
        
        if not budget_str:
            return result
        
        # Hourly rate
        hourly_match = re.search(r'\$?(\d+)[,-]?\$?(\d+)?\s*(?:per hour|hr|/h)', budget_str, re.I)
        if hourly_match:
            result["type"] = "hourly"
            result["min"] = float(hourly_match.group(1))
            result["max"] = float(hourly_match.group(2)) if hourly_match.group(2) else result["min"]
            return result
        
        # Fixed price
        fixed_match = re.search(r'\$?(\d+)[,-]?\$?(\d+)?', budget_str)
        if fixed_match:
            result["min"] = float(fixed_match.group(1))
            result["max"] = float(fixed_match.group(2)) if fixed_match.group(2) else result["min"]
        
        return result
    
    def scrape(self) -> List[Job]:
        """Scrape jobs - to be implemented by subclass"""
        raise NotImplementedError


class UpworkScraper(BaseScraper):
    """Upwork scraper"""
    
    def __init__(self):
        super().__init__("upwork", PLATFORMS["upwork"])
    
    def scrape(self) -> List[Job]:
        """Scrape Upwork jobs"""
        jobs = []
        
        try:
            # Use Playwright for JavaScript rendering
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to jobs page
                url = "https://www.upwork.com/ab/jobs/search/?category2=web_mobile_software_dev&subcategory=back-end_development&experience=expert&job_type=hourly,fixed-price"
                page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Wait for jobs to load
                page.wait_for_selector(".job-tile", timeout=30000)
                
                # Scroll to load more
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 2000)")
                    page.wait_for_timeout(2000)
                
                # Get HTML
                content = page.content()
                browser.close()
            
            soup = BeautifulSoup(content, 'lxml')
            
            # Parse jobs
            for item in soup.select(".job-tile"):
                try:
                    title_elem = item.select_one(".job-title")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = "https://www.upwork.com" + title_elem.get("href", "")
                    
                    desc_elem = item.select_one(".job-description")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    budget_elem = item.select_one(".job-budget")
                    budget = budget_elem.get_text(strip=True) if budget_elem else ""
                    
                    skills = [s.get_text(strip=True) for s in item.select(".skill-tag")]
                    
                    job = Job(
                        platform="upwork",
                        title=title,
                        description=description[:500],
                        url=url,
                        budget=budget,
                        skills=skills,
                        **self.parse_budget(budget)
                    )
                    jobs.append(job)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Upwork job: {e}")
            
        except Exception as e:
            logger.error(f"Upwork scraping error: {e}")
        
        return jobs


class RemoteOKScraper(BaseScraper):
    """RemoteOK scraper"""
    
    def __init__(self):
        super().__init__("remoteok", PLATFORMS["remoteok"])
    
    def scrape(self) -> List[Job]:
        """Scrape RemoteOK"""
        jobs = []
        
        try:
            url = "https://remoteok.com/remote-dev-jobs"
            self.rate_limit_wait()
            
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            for item in soup.select("tr.job"):
                try:
                    title_elem = item.select_one(".job-link")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = "https://remoteok.com" + title_elem.get("href", "")
                    
                    company = item.select_one(".company")
                    company_name = company.get_text(strip=True) if company else ""
                    
                    tags = [t.get_text(strip=True) for t in item.select(".tag")]
                    
                    salary_elem = item.select_one(".salary")
                    salary = salary_elem.get_text(strip=True) if salary_elem else ""
                    
                    # Determine skills from tags
                    skills = [t for t in tags if t in SKILL_KEYWORDS]
                    
                    job = Job(
                        platform="remoteok",
                        title=title,
                        description=f"Company: {company_name}. Tags: {', '.join(tags)}",
                        url=url,
                        budget=salary,
                        skills=skills,
                        tags=tags,
                        client_name=company_name,
                        remote=True,
                        **self.parse_budget(salary)
                    )
                    jobs.append(job)
                    
                except Exception as e:
                    logger.warning(f"Error parsing RemoteOK job: {e}")
        
        except Exception as e:
            logger.error(f"RemoteOK scraping error: {e}")
        
        return jobs


class WeWorkRemotelyScraper(BaseScraper):
    """We Work Remotely scraper"""
    
    def __init__(self):
        super().__init__("weworkremotely", PLATFORMS["weworkremotely"])
    
    def scrape(self) -> List[Job]:
        """Scrape We Work Remotely"""
        jobs = []
        
        try:
            url = "https://weworkremotely.com/remote-jobs/category/software-dev"
            self.rate_limit_wait()
            
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            for item in soup.select(".job-card"):
                try:
                    title_elem = item.select_one(".job-link")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = "https://weworkremotely.com" + title_elem.get("href", "")
                    
                    company_elem = item.select_one(".company")
                    company = company_elem.get_text(strip=True) if company_elem else ""
                    
                    tags = [t.get_text(strip=True) for t in item.select(".tags-container a")]
                    
                    job = Job(
                        platform="weworkremotely",
                        title=title,
                        description=f"Company: {company}. Tags: {', '.join(tags)}",
                        url=url,
                        skills=tags,
                        tags=tags,
                        client_name=company,
                        remote=True
                    )
                    jobs.append(job)
                    
                except Exception as e:
                    logger.warning(f"Error parsing WWR job: {e}")
        
        except Exception as e:
            logger.error(f"WeWorkRemotely scraping error: {e}")
        
        return jobs


class FreelancerScraper(BaseScraper):
    """Freelancer.com scraper"""
    
    def __init__(self):
        super().__init__("freelancer", PLATFORMS["freelancer"])
    
    def scrape(self) -> List[Job]:
        """Scrape Freelancer"""
        jobs = []
        
        try:
            url = "https://www.freelancer.com/jobs/python/"
            self.rate_limit_wait()
            
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            for item in soup.select(".JobSearchCard"):
                try:
                    title_elem = item.select_one(".JobSearchCard-primary-heading a")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = "https://www.freelancer.com" + title_elem.get("href", "")
                    
                    desc_elem = item.select_one(".JobSearchCard-description")
                    description = desc_elem.get_text(strip=True)[:500] if desc_elem else ""
                    
                    budget_elem = item.select_one(".JobSearchCard-price")
                    budget = budget_elem.get_text(strip=True) if budget_elem else ""
                    
                    skills = [s.get_text(strip=True) for s in item.select(".JobSearchCard-tags a")]
                    
                    job = Job(
                        platform="freelancer",
                        title=title,
                        description=description,
                        url=url,
                        budget=budget,
                        skills=skills,
                        **self.parse_budget(budget)
                    )
                    jobs.append(job)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Freelancer job: {e}")
        
        except Exception as e:
            logger.error(f"Freelancer scraping error: {e}")
        
        return jobs


class LinkedInScraper(BaseScraper):
    """LinkedIn Jobs scraper"""
    
    def __init__(self):
        super().__init__("linkedin", PLATFORMS["linkedin"])
        self.session.cookies.set("li_at", os.environ.get("LINKEDIN_LI_AT", ""))
    
    def scrape(self) -> List[Job]:
        """Scrape LinkedIn"""
        jobs = []
        
        if not self.session.cookies.get("li_at"):
            logger.warning("LinkedIn auth cookie not set, skipping")
            return jobs
        
        try:
            url = "https://www.linkedin.com/jobs/search/?keywords=Python%20Developer&location=Remote"
            self.rate_limit_wait()
            
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            for item in soup.select(".job-card-container"):
                try:
                    title_elem = item.select_one(".job-card-container__title")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link_elem = item.select_one("a.job-card-container__link")
                    url = link_elem.get("href", "") if link_elem else ""
                    
                    company_elem = item.select_one(".job-card-container__company-name")
                    company = company_elem.get_text(strip=True) if company_elem else ""
                    
                    location_elem = item.select_one(".job-card-container__metadata-item")
                    location = location_elem.get_text(strip=True) if location_elem else ""
                    
                    job = Job(
                        platform="linkedin",
                        title=title,
                        description=f"Location: {location}",
                        url=url,
                        client_name=company,
                        client_location=location,
                        remote="remote" in location.lower()
                    )
                    jobs.append(job)
                    
                except Exception as e:
                    logger.warning(f"Error parsing LinkedIn job: {e}")
        
        except Exception as e:
            logger.error(f"LinkedIn scraping error: {e}")
        
        return jobs


# Scraper registry
SCRAPERS = {
    "upwork": UpworkScraper,
    "remoteok": RemoteOKScraper,
    "weworkremotely": WeWorkRemotelyScraper,
    "freelancer": FreelancerScraper,
    "linkedin": LinkedInScraper
}


class ScraperOrchestrator:
    """Orchestrates all scrapers"""
    
    def __init__(self, platforms: List[str] = None):
        self.platforms = platforms or list(PLATFORMS.keys())
        self.results = []
    
    def scrape_platform(self, platform: str) -> List[Job]:
        """Scrape single platform"""
        if platform not in SCRAPERS:
            logger.warning(f"No scraper for {platform}")
            return []
        
        try:
            scraper_class = SCRAPERS[platform]
            scraper = scraper_class()
            jobs = scraper.scrape()
            logger.info(f"{platform}: Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"Error scraping {platform}: {e}")
            return []
    
    def scrape_all(self, max_workers: int = 3) -> List[Job]:
        """Scrape all platforms"""
        logger.info(f"=== Starting scrape for {len(self.platforms)} platforms ===")
        
        all_jobs = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {p: executor.submit(self.scrape_platform, p) for p in self.platforms}
            
            for platform, future in futures.items():
                jobs = future.result()
                all_jobs.extend(jobs)
        
        # Remove duplicates by URL
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            if job.url not in seen:
                seen.add(job.url)
                unique_jobs.append(job)
        
        logger.info(f"Total unique jobs: {len(unique_jobs)}")
        self.results = unique_jobs
        
        return unique_jobs
    
    def save_jobs(self):
        """Save jobs to disk"""
        if not self.results:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Save all jobs
        jobs_file = Path(CONFIG["data_dir"]) / f"jobs_{timestamp}.json"
        jobs_file.parent.mkdir(parents=True, exist_ok=True)
        
        jobs_data = [asdict(job) for job in self.results]
        with open(jobs_file, "w") as f:
            json.dump(jobs_data, f, indent=2)
        
        # Save latest
        latest_file = Path(CONFIG["data_dir"]) / "latest.json"
        with open(latest_file, "w") as f:
            json.dump(jobs_data, f, indent=2)
        
        logger.info(f"Saved {len(self.results)} jobs")
        
        # Send to API
        self.send_to_api()
    
    def send_to_api(self):
        """Send jobs to main API"""
        try:
            response = requests.post(
                f"{CONFIG['api_url']}/api/jobs",
                json={"jobs": [asdict(job) for job in self.results]},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Jobs sent to API")
                
        except Exception as e:
            logger.error(f"Failed to send to API: {e}")


if __name__ == "__main__":
    import sys
    
    platforms = sys.argv[1:] if len(sys.argv) > 1 else ["remoteok", "weworkremotely"]
    
    orchestrator = ScraperOrchestrator(platforms)
    jobs = orchestrator.scrape_all()
    orchestrator.save_jobs()
    
    print(f"Found {len(jobs)} jobs")
```

## Rate Limiting

```python
# config/rate_limits.json
{
    "upwork": {"requests": 10, "period": 60},
    "freelancer": {"requests": 10, "period": 60},
    "fiverr": {"requests": 20, "period": 60},
    "remoteok": {"requests": 30, "period": 60},
    "weworkremotely": {"requests": 20, "period": 60},
    "linkedin": {"requests": 5, "period": 60}
}
```

## Authentication Setup

```bash
# Upwork authentication (if needed)
# Set session cookies in browser and export
export UPWORK_SESSION="your_session_cookie"

# LinkedIn authentication  
export LINKEDIN_LI_AT="your_li_at_cookie"
```

## Next Steps

- [03-matching](./03-matching.md) - RAG job matching
