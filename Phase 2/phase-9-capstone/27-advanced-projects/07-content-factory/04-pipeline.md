# INNOVALABS — Pipeline Configuration

## Pipeline Overview

The Literature Factory runs as an automated pipeline triggered every 6 hours:

```
Time ─────────────────────────────────────────────────────────────►

│      │            │            │            │            │
│      ▼            ▼            ▼            ▼            ▼
│   Scout      Strategist    Architect     Writer      Editor
│   (10s)       (30s)         (2min)       (20min)     (1min)
│      │            │            │            │            │
│      └────────────┴────────────┴────────────┴────────────┘
│                           │
│                           ▼
│                    Google Sheets
│                    (State Update)
```

## Workflow Structure

### Phase 1: Scout (Trend Extraction)

| Parameter | Value |
|-----------|-------|
| Tool | Python script (pytrends) |
| Input | Google Trends API |
| Output | List of trending topics |
| Duration | 10-30 seconds |

**Process**:
1. Fetch top 10 trending searches
2. Filter by category (optional)
3. Select random topic
4. Return topic + context

### Phase 2: Strategist (Theme Selection)

| Parameter | Value |
|-----------|-------|
| Model | glm-4.7-flash:latest |
| Input | Trending topic |
| Output | JSON {tema, moraleja, escenario} |
| Temperature | 0.3 |
| Duration | 30-120 seconds |

**Process**:
1. Send topic to GLM-4.7 Flash
2. Parse JSON response
3. Validate output
4. Pass to next phase

### Phase 3: Architect (Blueprint Design)

| Parameter | Value |
|-----------|-------|
| Model | deepseek-r1:8b |
| Input | Theme + Moral + Setting |
| Output | JSON array (12 beats) |
| Temperature | 0.5 |
| Duration | 60-180 seconds |

**Process**:
1. Send structured prompt
2. Receive 12-step blueprint
3. Parse and validate JSON
4. Format for Writer

### Phase 4: Writer (Story Generation)

| Parameter | Value |
|-----------|-------|
| Tool | llama-cli |
| Model | Qwen3.5-27B-Q4.gguf |
| Input | Full prompt with blueprint |
| Output | Raw story (3000-6000 words) |
| Duration | 15-30 minutes |

**Critical Settings**:
```bash
llama-cli \
  -m ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf \
  -ngl 999 \
  -c 8192 \
  -n 8000 \
  --temp 0.8 \
  --repeat-penalty 1.1 \
  --no-mmap \
  -p "$(cat prompt.txt)"
```

### Phase 5: Editor (Polishing)

| Parameter | Value |
|-----------|-------|
| Model | nemotron-3-nano:latest |
| Input | Raw story |
| Output | Polished story |
| Temperature | 0.3 |
| Duration | 60-180 seconds |

**Process**:
1. Send raw story to Nemotron
2. Receive corrected version
3. Validate word count (>500)
4. Save to disk

## State Management

### Google Sheets Columns

| Column | Purpose | Values |
|--------|---------|--------|
| A: ID | Unique identifier | H-TIMESTAMP |
| B: Fecha | Creation date | ISO timestamp |
| C: Tema | Story theme | String |
| D: Contexto | Context | String |
| E: Estado | Status | PENDING/PROCESSING/COMPLETED/FAILED/FAILED_OOM |
| F: Path_Archivo | File path | /var/opt/.../Historia_*.md |
| G: Moraleja | Moral lesson | String |
| H: Blueprint_JSON | 12-step plan | JSON string |
| I: Error_Log | Error details | String |

### Status Flow

```
PENDING → PROCESSING → COMPLETED
              │
              └─→ FAILED / FAILED_OOM
```

## Output Format

### Story File Format

```markdown
---
title: "Historia H-1710432000000"
fecha_generacion: 2026-03-14
tema: "gentrificación"
moraleja: "La verdadera riqueza se mide en los puentes..."
escenario: "Ciudad latinoamericana contemporánea"
palabras: 4200
agente_escritor: Qwen3.5-27B-UD-Q4
agente_editor: nemotron-3-nano
---

[Story content begins here...]
```

### File Location

```
/var/opt/innovalabs/historias/
├── Historia_H-1710432000000.md
├── Historia_H-1710453600000.md
└── ...
```

## Configuration Files

### Environment Variables

```bash
# .env file
OLLAMA_HOST=http://localhost:11434
LLAMA_CLI_PATH=/usr/local/bin/llama-cli
LLAMA_MODEL=~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf
STORIES_DIR=/var/opt/innovalabs/historias
GSHEETS_SPREADSHEET_ID=YOUR_SPREADSHEET_ID
```

### Docker Compose (Optional)

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    runtime: nvidia
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    volumes:
      - n8n-data:/home/node/.n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - GENERIC_TIMEZONE=America/Bogota

volumes:
  ollama-data:
  n8n-data:
```

## Error Handling

### Automatic Recovery

| Error Type | Detection | Recovery |
|------------|-----------|----------|
| OOM | Log contains "out of memory" | Restart Ollama, requeue |
| Model Load | Log contains "failed to load" | Retry after 60s |
| API Timeout | Node timeout | Requeue with backoff |

### Manual Recovery

```bash
# Check failed items
curl "https://docs.google.com/spreadsheets/d/{ID}/gviz/tq?tq=select*"

# Re-run manually in n8n
# Workflow → Execute Workflow
```

## Scheduling

### Cron Expression

Default: Every 6 hours
```
0 */6 * * *
```

Alternative schedules:
```
# Every hour
0 * * * *

# Every 12 hours  
0 */12 * * *

# Daily at midnight
0 0 * * *
```

To change:
1. Open n8n → Workflow → Settings
2. Edit Cron node expression

## Performance Tuning

### Memory Management

```bash
# Before running
sudo nvpmodel -m 0
sudo jetson_clocks

# Check available memory
free -h
```

### Execution Timeout

| Phase | Default Timeout | Max Recommended |
|-------|----------------|----------------|
| Scout | 60s | 120s |
| Strategist | 180s | 300s |
| Architect | 300s | 600s |
| Writer | 1800s | 2400s |
| Editor | 300s | 600s |

### Concurrency

**ALWAYS 1** - Prevents VRAM collisions

In workflow Settings:
```json
{
  "maxConcurrency": 1
}
```
