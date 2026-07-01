# Yacht Jobs Automation - Overview

An automated system to search for yacht industry jobs, process them with AI, and publish to LinkedIn using n8n orchestration.

## Features

- **Multi-site Job Scraping**: Scan job boards simultaneously
- **AI-Powered Filtering**: Identify yacht-related positions
- **Smart Formatting**: Generate professional LinkedIn posts
- **n8n Integration**: Orchestrate the entire workflow
- **100% Local**: All AI processing on your Jetson

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Yacht Jobs Automation                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Job Scraper  │───▶│  AI Filter   │───▶│ LinkedIn      │  │
│  │              │    │              │    │ Publisher     │  │
│  └──────────────┘    └──────────────┘    └───────────────┘  │
│        │                    │                    │              │
│        │                    │                    │              │
│        ▼                    ▼                    ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Job Sites    │    │ Ollama/LLaMA │    │ n8n           │  │
│  │ Indeed, etc. │    │ (Local AI)   │    │ Workflow      │  │
│  └──────────────┘    └──────────────┘    └───────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Job Sources

| Site | URL Pattern | Status |
|------|-------------|--------|
| Indeed | indeed.com/jobs | Supported |
| LinkedIn | linkedin.com/jobs | Supported |
| Glassdoor | glassdoor.com | Supported |
| Simply Yacht Jobs | simplyyachtjobs.com | Supported |
| Yacht Crew | yachtcrewcad.com | Supported |
| Crew Finder | crewfinder.com | Supported |
| MarineJobs | marinejobs.com | Supported |

## Job Categories

- Deck Crew (Captain, Mate, Deckhand)
- Engineering (Chief Engineer, Engineer, Electrician)
- Galley (Chef, Sous Chef, Steward/ess)
- Entertainment (Cruise Director, Entertainer)
- Watersports (Dive Instructor, Watersports Coordinator)
- Management (Yacht Manager, Charter Broker)

## Installation

```bash
# Create project directory
mkdir -p ~/yacht-jobs
cd ~/yacht-jobs

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data logs

# Copy environment template
cp .env.example .env
```

## Requirements

```
# requirements.txt
requests>=2.31.0
beautifulsoup4>=4.12.0
selenium>=4.15.0
webdriver-manager>=4.0.0
ollama>=0.1.0
python-dotenv>=1.0.0
pydantic>=2.5.0
httpx>=0.25.0
```

## Configuration

```bash
# .env file
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Job Search
SEARCH_KEYWORDS=yacht jobs,superyacht,boat crew,marine jobs,yacht captain
LOCATIONS=Miami,Fort Lauderdale,Monaco,Antibes,Palma,Sydney,Dubai
SEARCH_RADIUS=50

# LinkedIn
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=your_password
LINKEDIN_PROFILE_URL=https://linkedin.com/in/yourprofile

# n8n
N8N_WEBHOOK_URL=http://localhost:5678/webhook/yacht-jobs

# Filtering
MIN_SALARY=50000
EXCLUDE_KEYWORDS=intern,unpaid,trainee
```

## Quick Start

```bash
# Start Ollama
ollama serve &

# Test scraping
python -m scraper.scrape --keywords "yacht captain" --location Miami

# Test AI filtering
python -m processor.filter --test

# Run full pipeline
python main.py run --keywords "yacht chef"
```

## Workflow (n8n)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Scheduled  │────▶│   Scrape    │────▶│    AI       │────▶│  LinkedIn   │
│  Trigger    │     │   Jobs      │     │   Process   │     │   Post      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   Every day           Indeed,           Categorize,          Human-like
   at 8 AM            LinkedIn,          Format,               post with
                      etc.               Summarize             all details
```

## Next Steps

- [Job Scraper](./07-job-scraper.md) - Multi-site job scraping
- [AI Processing](./08-ai-processing.md) - AI filtering and formatting
- [n8n Orchestration](./09-n8n-orchestration.md) - Workflow automation
- [LinkedIn Publishing](./10-linkedin-publishing.md) - Post generation
