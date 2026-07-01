# Freelance Hunter - AI-Powered Freelance Project Discovery

## Project Overview

Freelance Hunter is an autonomous AI platform that scrapes, monitors, and analyzes freelance opportunities from major platforms worldwide. It identifies short-term coding and programming projects matching your skills, delivers real-time alerts, and generates detailed proposals automatically.

This platform combines and extends all previous projects:
- **Project 6 (Video Studio)**: Generate video summaries of job opportunities
- **Project 7 (INNOVALABS)**: Multi-agent storytelling → Multi-agent proposal generation
- **Project 8 (Funding Finder)**: Web scraping, RAG, document processing, email delivery
- **Project 9 (AI Office)**: Agent team management, real-time dashboard, Discord control
- **Project 10 (Tourism Intel)**: Scheduler, Sheets integration, monitoring cycles

### What It Does

1. **Multi-Platform Scraping**: Collects jobs from Upwork, Freelancer, Fiverr, Toptal, RemoteOK, We Work Remotely, LinkedIn
2. **Real-Time Monitoring**: Checks every 5 minutes for new opportunities
3. **AI-Powered Matching**: RAG system matches jobs to your profile/skills
4. **Proposal Generation**: Auto-generates cover letters and proposals
5. **Alert System**: Discord/Telegram/Email notifications for hot jobs
6. **Analytics Dashboard**: Live view of opportunities, rates, and trends
7. **Proposal Tracking**: Google Sheets integration for pipeline management

### Features

- **10 Specialized AI Agents**: Lead, Scraper, Analyzer, Writer, QA, Scheduler, Notifier, Researcher, Archiver, Manager
- **5-Minute Monitoring Cycles**: Near real-time job discovery
- **RAG Job Matching**: Semantic search against your skill database
- **Multi-Platform Support**: 10+ freelance platforms
- **Auto-Proposal Generation**: Custom proposals with AI
- **Discord Bot Control**: Manage via Discord commands
- **Pixel-Art Dashboard**: Real-time visualization
- **Email Delivery**: Daily digests and individual alerts
- **Proposal Templates**: Pre-built for common job types

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FREELANCE HUNTER PLATFORM                                 │
│                 AI-Powered Freelance Project Discovery                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DATA COLLECTION LAYER                             │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │   UPWORK    │ │FREELANCER  │ │   FIVERR   │ │   TOPTAL   │    │  │
│  │  │  Scraping   │ │  Scraping   │ │  Scraping   │ │  Scraping   │    │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘    │  │
│  │         │               │               │               │            │  │
│  │  ┌──────┴───────────────┴───────────────┴───────────────┴──────┐   │  │
│  │  │  REMOTE OK  │  WE WORK REMOTELY  │  LINKEDIN  │  GUN.IO     │   │  │
│  │  │  Scraping   │  Scraping          │  Scraping  │  Scraping   │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌────────────────────────────────┴───────────────────────────────────────┐  │
│  │                    PROCESSING LAYER                                    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐  │  │
│  │  │    RAG       │ │  PROPOSAL    │ │   SKILL     │ │  ANALYTICS │  │  │
│  │  │   MATCHING   │ │  GENERATOR   │ │   MATCHER   │ │   ENGINE   │  │  │
│  │  │              │ │              │ │              │ │             │  │  │
│  │  │ • Embeddings │ │ • Cover      │ │ • Skills     │ │ • Trends   │  │  │
│  │  │ • Similarity │ │ • Proposals  │ │ • Rates     │ │ • Patterns │  │  │
│  │  │ • Ranking   │ │ • Templates  │ │ • History   │ │ • Insights │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └─────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌────────────────────────────────┴───────────────────────────────────────┐  │
│  │                    AGENT ORCHESTRATION LAYER                          │  │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐  │  │
│  │  │   LEAD    │ │  SCRAPER  │ │ ANALYZER  │ │  WRITER  │ │SCHEDULER │  │  │
│  │  │   AGENT   │ │   AGENT   │ │   AGENT   │ │   AGENT  │ │  AGENT   │  │  │
│  │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └────┬────┘  │  │
│  │        │             │             │             │             │        │  │
│  │  ┌─────┴─────────────┴─────────────┴─────────────┴─────────────┴────┐  │  │
│  │  │              COORDINATION BUS                                   │  │  │
│  │  │        Message Queue & Task Distribution                       │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌────────────────────────────────┴───────────────────────────────────────┐  │
│  │                        OUTPUT LAYER                                  │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │   DISCORD   │ │  DASHBOARD  │ │   GOOGLE   │ │    EMAIL    │    │  │
│  │  │    BOT      │ │    (8096)   │ │   SHEETS   │ │   REPORTS   │    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Supported Platforms

### Major Freelance Platforms

| Platform | Focus | Jobs Tracked |
|----------|-------|--------------|
| Upwork | General + Tech | 500+ |
| Freelancer | General + Tech | 300+ |
| Fiverr | Gigs/Services | 200+ |
| Toptal | Top-tier Talent | 50+ |
| RemoteOK | Remote Jobs | 200+ |
| We Work Remotely | Remote Jobs | 150+ |
| LinkedIn Jobs | Professional | 300+ |
| Gun.io | Senior Devs | 50+ |
| X-Team | Elite Teams | 30+ |
| Turing | Remote Talent | 50+ |

### Job Categories Tracked

- Web Development
- Mobile Apps
- AI/ML Projects
- DevOps/Cloud
- Data Engineering
- API Development
- Blockchain
- UI/UX Design Integration
- Security Audits
- Technical Writing

## AI Agents

| Agent | Function | Model |
|-------|----------|-------|
| **Lead Agent** | Orchestrates all tasks, prioritizes | qwen2.5-coder:14b |
| **Scraper Agent** | Scrapes all platforms | qwen2.5-coder:14b |
| **Analyzer Agent** | Evaluates job fit | deepseek-r1:8b |
| **Writer Agent** | Generates proposals | llama3.2:3b |
| **QA Agent** | Quality checks proposals | deepseek-r1:8b |
| **Scheduler Agent** | Manages 5-min cycles | glm-4.7-flash |
| **Notifier Agent** | Discord/Email alerts | qwen2.5-coder:14b |
| **Researcher Agent** | Company/client research | qwen2.5-coder:14b |
| **Archiver Agent** | Stores job history | glm-4.7-flash |
| **Manager Agent** | Pipeline management | qwen2.5-coder:14b |

## Data Points Collected

### Per Job

- Title, description, requirements
- Budget range (hourly/fixed)
- Required skills
- Client history & ratings
- Proposal count
- Timeline
- Location (remote/on-site)
- Category tags

### Per Client

- Total spent on platform
- Job history
- Rating & reviews
- Payment verified
- Response time
- Hires count

### Per Proposal

- Custom cover letter
- Proposed rate
- Timeline
- Relevant samples
- Status (sent/pending/won/lost)

## Integration Features

### From Project 6 (Video Studio)

- Generate video summaries of hot jobs
- Create intro videos for proposals
- Video pitch generation

### From Project 7 (INNOVALABS)

- Multi-agent pipeline
- Quality assurance
- Error recovery
- Logging system
- Queue management

### From Project 8 (Funding Finder)

- Web scraping with Scrapling
- Google Sheets integration
- RAG knowledge base
- Document processing
- Email delivery

### From Project 9 (AI Office)

- Agent team management
- Real-time dashboard
- Discord control
- Activity logging
- Cost tracking

### From Project 10 (Tourism Intel)

- 5-minute monitoring cycles
- Alert system
- Trend analysis
- City/region tracking → Client region analysis

## Configuration

### Skills Profile

```yaml
# Your skills for matching
skills:
  primary:
    - Python
    - JavaScript
    - React
    - Node.js
    - CUDA
    - TensorRT
    
  secondary:
    - Docker
    - Kubernetes
    - AWS
    - PostgreSQL
    - MongoDB
    
  languages:
    - English (Fluent)
    - Spanish (Native)

# Rate expectations
rate:
  hourly_min: 50
  hourly_max: 150
  fixed_min: 500
  fixed_max: 10000

# Job preferences
preferences:
  remote_only: true
  escrow_only: true
  payment_verified: true
  min_client_rating: 4.5
```

## Next Steps

- [02-scraping](./02-scraping.md) - Multi-platform scraping
- [03-matching](./03-matching.md) - RAG job matching
- [04-proposals](./04-proposals.md) - Auto-proposal generation
- [05-agents](./05-agents.md) - Agent implementations
- [06-scheduler](./06-scheduler.md) - 5-minute orchestration
- [07-notifications](./07-notifications.md) - Discord/Email alerts
- [08-sheets](./08-sheets.md) - Google Sheets pipeline
- [09-dashboard](./09-dashboard.md) - Real-time dashboard
- [10-discord](./10-discord.md) - Discord bot control
- [11-installation](./11-installation.md) - Complete setup guide
