# Project 3: n8n Google Calendar + Telegram Workflow

A comprehensive guide to building a local n8n automation workflow that manages Google Calendar events via Telegram with text and voice messages on Jetson AGX Orin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
6. [Running the System](#running-the-system)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a workflow automation system:

- **n8n Server**: Local automation platform
- **Telegram Bot**: Chat interface
- **Google Calendar**: Event management
- **Voice Input**: Whisper transcription
- **Natural Language**: Parse commands

### Features

| Feature | Description |
|---------|-------------|
| Telegram Bot | Chat interface |
| Calendar CRUD | Create, read, update, delete events |
| Voice Input | Speech-to-text |
| NLP | Natural language parsing |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    n8n Automation Architecture                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │  Telegram   │─────▶│    n8n      │─────▶│   Google    │           │
│   │    Bot      │      │   Server    │      │  Calendar   │           │
│   └──────────────┘      └──────┬───────┘      └──────────────┘           │
│                                 │                                           │
│                                 │                                           │
│                                 ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      WORKFLOW NODES                                │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│   │  │ Telegram │  │  Whisper │  │  Parse   │  │ Calendar │       │   │
│   │  │  Trigger │  │ (Voice)  │  │  NLP    │  │   API    │       │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation |
|-----------|-------------|
| Docker | Part 2 |
| n8n | Docker container |

### Pre-Setup

1. Create Telegram bot via @BotFather
2. Get Google Calendar API credentials

---

## What You'll Build

### Workflows

| Workflow | Function |
|----------|----------|
| Create Event | Add calendar event |
| List Events | Show upcoming events |
| Delete Event | Remove event |
| Voice Input | Transcribe and process |

---

## Implementation

### n8n Workflow

```json
{
  "nodes": [
    {
      "name": "Telegram Trigger",
      "type": "n8n-nodes-telegram.telegramTrigger",
      "parameters": {
        "updates": ["message"]
      }
    },
    {
      "name": "Google Calendar",
      "type": "google-calendar",
      "parameters": {
        "operation": "create"
      }
    }
  ]
}
```

### Voice Processing

```python
# Whisper integration
def transcribe_voice(file_id):
    """Transcribe voice message."""
    # Download audio
    # Process with Whisper
    return text
```

---

## Running the System

### Start n8n

```bash
docker run -d --name n8n -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e WEBHOOK_URL=http://localhost:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

### Access

- URL: `http://localhost:5678`
- Credentials: admin/admin

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot not responding | Check webhook URL |
| Calendar error | Verify API credentials |
| Voice fails | Check Whisper |

---

## License

MIT License
