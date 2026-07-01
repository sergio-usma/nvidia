# Tourism Intelligence Platform - Hotel & Tourist Analytics

## Project Overview

The Tourism Intelligence Platform is a comprehensive AI-powered commercial intelligence system that monitors hotels, tourist rentals, airlines, and tourism trends in Colombian cities. It combines OSINT techniques, real-time availability tracking, sentiment analysis, and multi-agent orchestration to provide actionable insights for the tourism industry.

This platform combines and extends:
- **Project 7 (INNOVALABS)**: Multi-agent storytelling and proposal generation
- **Project 8 (Funding Finder)**: Web scraping, RAG, delivery systems
- **Project 9 (AI Office)**: Agent team management, dashboard, Discord control

### What It Does

1. **Web Scraping**: Collects data from Booking, TripAdvisor, Google Hotels, Expedia
2. **Review Analysis**: Sentiment analysis on hotel reviews
3. **Availability Tracking**: Monitors room availability every 15 minutes
4. **Price Intelligence**: Tracks pricing trends
5. **Airline Monitoring**: Tracks Colombian airline routes and prices
6. **News Monitoring**: Tracks tourism-related news
7. **Trend Analysis**: Identifies emerging patterns
8. **Report Generation**: Creates automated intelligence reports

### Features

- **8 Specialized AI Agents**: Each with specific roles
- **Real-time Dashboard**: Pixel art office showing agents working
- **15-Minute Monitoring Cycles**: Continuous data collection
- **Sentiment Analysis**: Multi-language review analysis
- **Google Sheets Integration**: Track all data in real-time
- **Discord Control**: Manage via Discord commands
- **Automated Reports**: Daily/weekly intelligence summaries
- **24/7 Autonomous Operation**: Self-managing workflow

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 TOURISM INTELLIGENCE PLATFORM                              │
│                  Colombia Hotel & Tourist Analytics                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DATA COLLECTION LAYER                             │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │  │
│  │  │   HOTELS    │ │   AIRLINES  │ │    NEWS    │                │  │
│  │  │  Scraping   │ │  Scraping   │ │  Scraping   │                │  │
│  │  │ • Booking   │ │ • Avianca   │ │ • El Tiempo │                │  │
│  │  │ • TripAdvisor│ │ • LATAM     │ │ • Portafolio│                │  │
│  │  │ • Expedia   │ │ • Viva Air  │ │ • Semana   │                │  │
│  │  │ • Google    │ │ • Ultra Air │ │ • RCNS     │                │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                │  │
│  └─────────┼────────────────┼────────────────┼─────────────────────────┘  │
│            │                │                │                             │
│  ┌─────────┴────────────────┴────────────────┴─────────────────────────┐  │
│  │                    DATA PROCESSING LAYER                           │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │  │
│  │  │  SENTIMENT   │ │  ANALYTICS  │ │   RAG KB     │               │  │
│  │  │  Analysis    │ │  Engine     │ │   System     │               │  │
│  │  │              │ │              │ │              │               │  │
│  │  │ • Reviews    │ │ • Trends    │ │ • Historical │               │  │
│  │  │ • Comments   │ │ • Patterns  │ │ • Reports    │               │  │
│  │  │ • Ratings    │ │ • Predictions│ │ • Context   │               │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│  ┌────────────────────────────────┴───────────────────────────────────┐   │
│  │                    AGENT ORCHESTRATION LAYER                      │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐        │   │
│  │  │  LEAD     │ │ RESEARCHER│ │ ANALYST   │ │ REPORTER  │        │   │
│  │  │  AGENT    │ │  AGENT    │ │  AGENT    │ │  AGENT    │        │   │
│  │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘        │   │
│  │        │             │             │             │                │   │
│  │  ┌─────┴─────────────┴─────────────┴─────────────┴─────┐         │   │
│  │  │              SCHEDULER AGENT                       │         │   │
│  │  │        Runs every 15 minutes                       │         │   │
│  │  └─────────────────────────────────────────────────────┘         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                      │
│  ┌────────────────────────────────┴───────────────────────────────────┐   │
│  │                        OUTPUT LAYER                              │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │   │
│  │  │  GOOGLE    │ │  DASHBOARD │ │   EMAIL     │               │   │
│  │  │  SHEETS    │ │   (8095)   │ │  REPORTS    │               │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Supported Cities

### Colombian Cities

| City | Code | Hotels Tracked |
|------|------|----------------|
| Bogotá | BOG | 250+ |
| Medellín | MDE | 180+ |
| Cartagena | CTG | 150+ |
| Cali | CLO | 120+ |
| Barranquilla | BAQ | 80+ |
| Santa Marta | SMR | 70+ |
| Bucaramanga | BGA | 60+ |
| Pereira | PEI | 50+ |

## Supported Sources

### Hotel Booking Sites

- Booking.com
- TripAdvisor
- Expedia
- Google Hotels
- Hoteles.com
- Airbnb (Colombia)

### Airline Sources

- Avianca
- LATAM Colombia
- Viva Air
- Ultra Air
- WhichAirline

### News Sources

- El Tiempo
- Portafolio
- Semana
- RC Noticias
- La República

## AI Agents

### Agent Roles

| Agent | Function | Model |
|------|----------|-------|
| **Lead Agent** | Orchestrates all tasks, prioritizes | qwen2.5-coder:14b |
| **Researcher Agent** | Scrapes and collects data | qwen2.5-coder:14b |
| **Sentiment Agent** | Analyzes reviews and feelings | llama3.2:3b |
| **Analytics Agent** | Finds trends and patterns | deepseek-r1:8b |
| **Reporter Agent** | Generates reports and summaries | llama3.2:3b |
| **Scheduler Agent** | Manages 15-min cycles | glm-4.7-flash |
| **Data Manager** | Stores in Sheets/DB | qwen2.5-coder:14b |
| **Alert Agent** | Detects anomalies | deepseek-r1:8b |

## Data Points Collected

### Per Hotel

- Name, location, stars
- Room availability (updated every 15 min)
- Price per night
- Review score
- Number of reviews
- Sentiment score
- Amenities
- Photos count

### Per Review

- Review text
- Rating (1-5)
- Date
- Traveler type
- Sentiment (positive/negative/neutral)
- Key themes

### Per Airline

- Routes
- Prices
- Schedule
- On-time performance
- Reviews

## Integration Features

### From Project 7 (INNOVALABS)

- Multi-agent pipeline
- Quality assurance checks
- Error recovery
- Logging system

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

## Next Steps

- [02-scraping](./02-scraping.md) - Web scraping configuration
- [03-sentiment](./03-sentiment.md) - Sentiment analysis system
- [04-availability](./04-availability.md) - Real-time availability
- [05-agents](./05-agents.md) - Agent implementations
- [06-scheduler](./06-scheduler.md) - 15-minute orchestration
- [07-sheets](./07-sheets.md) - Google Sheets integration
- [08-dashboard](./08-dashboard.md) - Dashboard & reporting
- [09-installation](./09-installation.md) - Complete setup guide
