# AI Processing

Process scraped jobs with local AI to identify yacht positions and generate LinkedIn posts.

## Job Filter

```python
# processor/job_filter.py
import ollama
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class JobFilter:
    """Filter jobs using local AI"""
    
    YACHT_KEYWORDS = [
        'yacht', 'superyacht', 'mega yacht', 'boat', 'vessel', 'marine',
        'deck', 'captain', 'mate', 'deckhand', 'crew', 'steward', 'stewardess',
        'chef', 'sous chef', 'cook', 'galley', 'engineer', 'chief engineer',
        'first mate', 'second mate', 'third mate', 'bosun', 'able seaman',
        'pilot', 'dive', 'diving', 'watersport', 'jet ski', 'fishing',
        'charter', 'private', 'crew', 'marina', 'shipyard', 'boatyard'
    ]
    
    EXCLUDE_KEYWORDS = [
        'intern', 'unpaid', 'trainee', 'volunteer', 'student',
        'fake', 'scam', 'mlm'
    ]
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = config.get('ollama_model', 'llama3.2')
        self.host = config.get('ollama_host', 'http://localhost:11434')
        self.client = ollama.Client(host=self.host)
    
    def is_yacht_job(self, job: Dict) -> Dict:
        """Determine if job is yacht-related"""
        text = f"{job.get('title', '')} {job.get('company', '')} {job.get('snippet', '')}".lower()
        
        # Quick keyword check
        yacht_score = sum(1 for kw in self.YACHT_KEYWORDS if kw in text)
        
        # Quick exclusion check
        for exc in self.EXCLUDE_KEYWORDS:
            if exc in text:
                return {
                    'is_yacht_job': False,
                    'confidence': 0.0,
                    'reason': f'Contains excluded keyword: {exc}'
                }
        
        # Use AI for ambiguous cases
        if yacht_score >= 1:
            # Verify with AI
            return self._ai_verify(job, yacht_score)
        else:
            return {
                'is_yacht_job': False,
                'confidence': 0.0,
                'reason': 'No yacht keywords found'
            }
    
    def _ai_verify(self, job: Dict, keyword_score: int) -> Dict:
        """Use AI to verify yacht job"""
        prompt = f"""Analyze this job posting and determine if it's related to the yacht/marine industry.

Job Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Description: {job.get('snippet', '')[:500]}

Is this a yacht or marine industry job? Answer with YES or NO, followed by a brief explanation.
Also identify the specific role type (Deck, Engineering, Galley, Entertainment, Watersports, Management)."""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}
            )
            
            answer = response['message']['content'].upper()
            is_yacht = 'YES' in answer[:10]
            
            # Extract role type
            role_type = 'Unknown'
            role_types = ['DECK', 'ENGINEERING', 'GALLEY', 'ENTERTAINMENT', 'WATERSPORTS', 'MANAGEMENT']
            for rt in role_types:
                if rt in answer:
                    role_type = rt
                    break
            
            confidence = 0.9 if is_yacht else 0.3
            
            return {
                'is_yacht_job': is_yacht,
                'confidence': confidence,
                'role_type': role_type,
                'ai_explanation': response['message']['content'][:200]
            }
            
        except Exception as e:
            logger.error(f"AI verification error: {e}")
            return {
                'is_yacht_job': keyword_score >= 2,
                'confidence': 0.7 if keyword_score >= 2 else 0.3,
                'reason': 'Fallback to keyword matching'
            }
    
    def filter_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Filter list of jobs"""
        filtered = []
        
        for job in jobs:
            result = self.is_yacht_job(job)
            job.update(result)
            
            if result.get('is_yacht_job'):
                filtered.append(job)
        
        logger.info(f"Filtered {len(filtered)} yacht jobs from {len(jobs)} total")
        return filtered
```

## LinkedIn Post Generator

```python
# processor/post_generator.py
import ollama
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class LinkedInPostGenerator:
    """Generate human-like LinkedIn posts from job descriptions"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = config.get('ollama_model', 'llama3.2')
        self.host = config.get('ollama_host', 'http://localhost:11434')
        self.client = ollama.Client(host=self.host)
    
    def generate_post(self, job: Dict) -> str:
        """Generate a LinkedIn post for a job"""
        
        prompt = f"""Create a LinkedIn post about the following yacht job opportunity. 

The post should:
- Be professional but engaging
- Include all relevant details in a scannable format
- Use appropriate emojis sparingly
- Include relevant hashtags
- Have a clear call-to-action
- Sound human-written, not AI-generated

Job Details:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Salary: {job.get('salary', 'Not specified')}
Description: {job.get('description', job.get('snippet', ''))[:1000]}

Write the LinkedIn post now:"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            logger.error(f"Error generating post: {e}")
            return self._fallback_post(job)
    
    def _fallback_post(self, job: Dict) -> str:
        """Generate a basic post if AI fails"""
        title = job.get('title', 'Yacht Job')
        company = job.get('company', '')
        location = job.get('location', '')
        
        return f"""⚓ Exciting Opportunity in the Yachting Industry!

{title} position available at {company}

📍 Location: {location}
💼 Great opportunity for marine professionals

If you're looking for a career in the yacht industry, this could be your next move! 

#YachtJobs #MarineJobs #Boating #Careers #Yachting #Superyacht
"""
    
    def generate_post_variations(self, job: Dict, count: int = 3) -> List[str]:
        """Generate multiple post variations"""
        variations = []
        
        for i in range(count):
            prompt = f"""Create a LinkedIn post (variation {i+1}/{count}) for this yacht job.

Job: {job.get('title', '')} at {job.get('company', '')}
Location: {job.get('location', '')}

Make this variation unique and different from the others. Use a different tone or angle."""

            try:
                response = self.client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.9}
                )
                variations.append(response['message']['content'].strip())
            except:
                variations.append(self._fallback_post(job))
        
        return variations
```

## Job Categorizer

```python
# processor/categorizer.py
import ollama
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class JobCategorizer:
    """Categorize and enrich job postings"""
    
    CATEGORIES = {
        'DECK': ['captain', 'mate', 'deckhand', 'bosun', 'able seaman', 'first mate', 'second mate', 'third mate'],
        'ENGINEERING': ['engineer', 'chief engineer', 'mechanic', 'electrician', 'electronics'],
        'GALLEY': ['chef', 'sous chef', 'cook', 'steward', 'stewardess', 'butler'],
        'ENTERTAINMENT': ['entertainer', 'cruise director', 'massage therapist', 'beautician'],
        'WATERSPORTS': ['dive', 'diving', 'watersport', 'jet ski', 'fishing', 'instructor'],
        'MANAGEMENT': ['manager', 'broker', 'charter', 'director', 'supervisor']
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = config.get('ollama_model', 'llama3.2')
        self.host = config.get('ollama_host', 'http://localhost:11434')
        self.client = ollama.Client(host=self.host)
    
    def categorize(self, job: Dict) -> Dict:
        """Categorize a job"""
        title = job.get('title', '').lower()
        
        # Quick category matching
        for category, keywords in self.CATEGORIES.items():
            if any(kw in title for kw in keywords):
                job['category'] = category
                return job
        
        # AI categorization for unknown
        return self._ai_categorize(job)
    
    def _ai_categorize(self, job: Dict) -> Dict:
        """Use AI to categorize"""
        prompt = f"""Categorize this yacht job into one of these categories:
- DECK (captain, mate, deckhand, bosun)
- ENGINEERING (engineer, mechanic, electrician)
- GALLEY (chef, sous chef, steward)
- ENTERTAINMENT (entertainer, massage therapist)
- WATERSPORTS (dive instructor, watersports)
- MANAGEMENT (manager, broker)

Job Title: {job.get('title', '')}
Company: {job.get('company', '')}
Description: {job.get('description', job.get('snippet', ''))[:300]}

Respond with just the category name:"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}
            )
            
            category = response['message']['content'].strip().upper()
            if category in self.CATEGORIES:
                job['category'] = category
            else:
                job['category'] = 'OTHER'
                
        except Exception as e:
            logger.error(f"AI categorization error: {e}")
            job['category'] = 'UNKNOWN'
        
        return job
    
    def enrich(self, job: Dict) -> Dict:
        """Enrich job with additional metadata"""
        
        # Extract requirements
        job['requirements'] = self._extract_requirements(job)
        
        # Extract benefits
        job['benefits'] = self._extract_benefits(job)
        
        # Experience level
        job['experience_level'] = self._extract_experience(job)
        
        # Visa sponsorship
        job['visa_sponsorship'] = self._check_visa(job)
        
        return job
    
    def _extract_requirements(self, job: Dict) -> List[str]:
        """Extract job requirements"""
        text = job.get('description', job.get('snippet', ''))
        
        requirements = []
        
        # Common requirements
        common = ['STCW', 'ENG1', 'Yacht Master', 'RYA', 'Cuisine', 'culinary']
        
        for req in common:
            if req.lower() in text.lower():
                requirements.append(req)
        
        return requirements
    
    def _extract_benefits(self, job: Dict) -> List[str]:
        """Extract job benefits"""
        text = job.get('description', job.get('snippet', '')).lower()
        
        benefits = []
        
        benefit_keywords = {
            'crew': ['crew', 'team'],
            'travel': ['travel', 'charter', 'worldwide'],
            'salary': ['salary', 'wage', 'pay'],
            'accommodation': ['accommodation', 'cabin', 'room'],
            'flights': ['flights', 'airfare', 'travel allowance']
        }
        
        for benefit, keywords in benefit_keywords.items():
            if any(kw in text for kw in keywords):
                benefits.append(benefit)
        
        return benefits
    
    def _extract_experience(self, job: Dict) -> str:
        """Extract required experience level"""
        text = job.get('description', job.get('snippet', '')).lower()
        
        if any(x in text for x in ['senior', '10+ years', '10 years', 'extensive experience']):
            return 'Senior'
        elif any(x in text for x in ['5+ years', '5 years', 'mid-level', 'several years']):
            return 'Mid-Level'
        elif any(x in text for x in ['entry', 'junior', 'no experience', 'trainee']):
            return 'Entry'
        
        return 'Not specified'
    
    def _check_visa(self, job: Dict) -> bool:
        """Check if visa sponsorship is mentioned"""
        text = job.get('description', job.get('snippet', '')).lower()
        
        visa_keywords = ['visa', 'sponsorship', 'work permit', 'relocation']
        return any(kw in text for kw in visa_keywords)
```

## Usage

```python
# Process jobs
from processor.job_filter import JobFilter
from processor.post_generator import LinkedInPostGenerator
from processor.categorizer import JobCategorizer

config = {
    'ollama_model': 'llama3.2',
    'ollama_host': 'http://localhost:11434'
}

# Load jobs
with open('data/jobs_raw.json') as f:
    jobs = json.load(f)

# Filter yacht jobs
job_filter = JobFilter(config)
yacht_jobs = job_filter.filter_jobs(jobs)

# Categorize
categorizer = JobCategorizer(config)
for job in yacht_jobs:
    job = categorizer.categorize(job)
    job = categorizer.enrich(job)

# Generate LinkedIn posts
post_generator = LinkedInPostGenerator(config)
for job in yacht_jobs:
    job['linkedin_post'] = post_generator.generate_post(job)

# Save processed jobs
with open('data/jobs_processed.json', 'w') as f:
    json.dump(yacht_jobs, f, indent=2)
```

## Next Steps

- [n8n Orchestration](./09-n8n-orchestration.md) - Automate the workflow
