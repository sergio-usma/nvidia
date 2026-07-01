# AI Office - Virtual AI Team

## Project Overview

The AI Office is a fully operational virtual team of specialized AI agents that work 24/7. Unlike a concept or demo, this is a real production system where each AI agent has a specific role, communicates with others, and handles real tasks.

### What It Does

1. **Lead Agent** - Analyzes requests, prioritizes tasks, delegates to specialists
2. **Frontend Agent** - Develops UI components, fixes frontend bugs
3. **Backend Agent** - Builds APIs, databases, server logic
4. **QA Agent** - Tests code, finds vulnerabilities, validates quality
5. **Content Agent** - Generates and publishes LinkedIn posts
6. **Scheduler Agent** - Orchestrates work queue every 15 minutes

### Features

- **Real-time Activity Log**: See who is working in real-time
- **Request Tracking**: Monitor what each agent is processing
- **Token Consumption**: Track token usage per operation
- **Cost Analytics**: Calculate cost per operation
- **Discord Integration**: Agents communicate via Discord
- **Pixel Art Dashboard**: RPG-style office visualization
- **24/7 Autonomous Operation**: Self-managing workflow

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI OFFICE - VIRTUAL TEAM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    SCHEDULER AGENT (Orchestrator)                    │  │
│  │                    Runs every 15 minutes                              │  │
│  │                    - Polls request queue                              │  │
│  │                    - Assigns tasks to agents                         │  │
│  │                    - Monitors completion                              │  │
│  └─────────────────────────────┬───────────────────────────────────────────┘  │
│                                │                                             │
│     ┌─────────────────────────┼──────────────────────────────────────────┐  │
│     │                         │                                          │  │
│     ▼                         ▼                                          ▼  │
│  ┌──────────┐          ┌──────────────┐          ┌──────────────────┐  │
│  │   LEAD    │          │   FRONTEND   │          │    BACKEND       │  │
│  │   AGENT   │◄────────►│    AGENT     │◄────────►│     AGENT        │  │
│  │           │          │              │          │                  │  │
│  │ • Analyze │          │ • UI Code    │          │ • APIs           │  │
│  │ • Prioritize│         │ • Components │          │ • Database       │  │
│  │ • Delegate │          │ • Fix bugs   │          │ • Logic          │  │
│  │ • Review  │          │ • Styling    │          │ • Security       │  │
│  └─────┬──────┘          └──────┬───────┘          └────────┬─────────┘  │
│        │                       │                            │              │
│        └───────────────────────┼────────────────────────────┘              │
│                                │                                            │
│                                ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         QA AGENT                                     │  │
│  │  • Unit tests    • Integration tests    • Vulnerability scans     │  │
│  │  • Code review   • Quality metrics       • Performance testing     │  │
│  └─────────────────────────────────────┬───────────────────────────────┘  │
│                                        │                                   │
│                                        ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      CONTENT AGENT                                   │  │
│  │  • LinkedIn posts    • Technical articles    • Documentation       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DASHBOARD (Port 9000)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   ████████ PIXEL ART OFFICE ████████████████████████████████      │   │
│  │                                                                     │   │
│  │   [Lead PC] [Dev PC] [Dev PC] [QA PC] [Content PC]                │   │
│  │   ░░░░░░░ ░░░░░░░░ ░░░░░░░░ ░░░WORK░░░ ░░IDLE░░░░              │   │
│  │   ░░MEET░░ ░░CODE░░ ░░DEBUG░░ ░░TESTING░░ ░░POSTING░░           │   │
│  │                                                                     │   │
│  │   📋 Request Queue: 12 │ ⚡ Active: 3 │ ✅ Done: 47 │ 💰 Cost: $0.23│   │
│  │                                                                     │   │
│  │   📊 Activity Log (real-time)                                      │   │
│  │   ─────────────────────────────────────                             │   │
│  │   [14:32] Lead: Analyzing request #234                            │   │
│  │   [14:33] Backend: Implementing API /users                          │   │
│  │   [14:34] QA: Running security scan on PR #89                     │   │
│  │   [14:35] Content: Publishing LinkedIn post                        │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Device | Jetson AGX Orin 64GB | Jetson AGX Orin 64GB |
| RAM | 32GB | 64GB |
| Storage | 128GB | 256GB NVMe |

### Models Used

| Agent | Model | Purpose |
|-------|-------|---------|
| Lead | qwen2.5-coder:14b | Analysis & decision making |
| Frontend | qwen2.5-coder:14b | Frontend development |
| Backend | deepseek-r1:8b | Backend & APIs |
| QA | qwen2.5-coder:14b | Testing & security |
| Content | llama3.2:3b | Content generation |
| Scheduler | glm-4.7-flash | Fast orchestration |

### Software

- Ubuntu 22.04 LTS (aarch64)
- JetPack 6.2+
- Ollama + llama.cpp
- Node.js 20 + n8n
- Python 3.10+
- Discord Bot Token (optional)

## Agent Roles

### Lead Agent

- Analyzes incoming requests
- Determines priority (1-5)
- Delegates to appropriate specialist
- Reviews completed work
- Escalates issues

### Frontend Agent

- Generates React/Vue components
- Fixes CSS/UI bugs
- Implements responsive designs
- Creates animations
- Optimizes performance

### Backend Agent

- Builds REST/GraphQL APIs
- Designs database schemas
- Implements authentication
- Creates business logic
- Secures endpoints

### QA Agent

- Writes unit tests
- Performs security scans
- Validates code quality
- Checks performance
- Reviews pull requests

### Content Agent

- Generates LinkedIn posts
- Creates technical articles
- Writes documentation
- Optimizes for engagement
- Schedules publishing

### Scheduler Agent

- Polls request queue every 15 minutes
- Assigns tasks to agents
- Monitors deadlines
- Handles timeouts
- Reports status

## Next Steps

- [02-architecture](./02-architecture.md) - System architecture & communication
- [03-agents](./03-agents.md) - Individual agent implementations
- [04-scheduler](./04-scheduler.md) - Task orchestration
- [05-discord](./05-discord.md) - Discord integration
- [06-dashboard](./06-dashboard.md) - Pixel art dashboard
- [07-activity](./07-activity.md) - Real-time logging
- [08-installation](./08-installation.md) - Setup guide
