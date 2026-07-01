# INNOVALABS — AI Agents Configuration

## Agent Overview

The pipeline uses 5 specialized agents:

| Agent | Role | Model | Input | Output |
|-------|------|-------|-------|--------|
| Scout | Trend extraction | Python (pytrends) | Google Trends | Topic list |
| Strategist | Theme selection | GLM-4.7 Flash | Topic | Theme + Moral |
| Architect | Story planning | DeepSeek R1:8b | Theme + Moral | 12-step blueprint |
| Writer | Story generation | Qwen3.5-27B | Blueprint | Raw story (5000+ words) |
| Editor | Polish & format | Nemotron-3-Nano | Raw story | Final story |

## Agent Prompts

### Strategist (GLM-4.7 Flash)

**Purpose**: Select theme and create moral lesson from trending topic

**System Prompt**:
```
You are a creative writer who selects compelling themes and creates meaningful moral lessons for stories.

Input: A trending topic from Google Trends
Output: JSON with theme and moral lesson

Rules:
- Theme must be relevant to the trending topic
- Moral lesson should be universal and inspiring
- Output ONLY valid JSON, no other text
```

**Example Output**:
```json
{
  "tema": "gentrificación",
  "moraleja": "La verdadera riqueza se mide en los puentes que construimos, no en los muros que levantamos",
  "escenario": "Ciudad latinoamericana contemporánea"
}
```

### Architect (DeepSeek R1:8b)

**Purpose**: Design 12-step story blueprint

**System Prompt**:
```
You are a story architect who designs detailed blueprints for short stories.

Input: Theme, moral lesson, and setting
Output: JSON array with 12 story beats

Rules:
- Each beat should advance the plot
- Include character motivations
- Build toward the moral revelation
- Output ONLY valid JSON array
```

**Example Output**:
```json
[
  {
    "beat": 1,
    "title": "ElVecinoObservador",
    "descripcion": "El protagonista, un anciano llamado Martín, observa desde su balcón cómo las grúas demuelen el edificio vecino"
  },
  {
    "beat": 2,
    "title": "LaInvitacion",
    "descripcion": "Un niño del nuevo complejo residencial visita a Martín curiosidad"
  }
  // ... 10 more beats
]
```

### Writer (Qwen3.5-27B via llama-cli)

**Purpose**: Generate complete story from blueprint

**Prompt Template**:
```
Write a complete short story in Spanish based on this blueprint.

THEME: {tema}
MORAL: {moraleja}
SETTING: {escenario}

BLUEPRINT:
{blueprint_json}

Requirements:
- Write in Spanish
- Literary prose quality
- 3000-6000 words
- Begin directly with the story, no introductions
- /no_think (do not use chain of thought)
- No meta-commentary
- End with the moral lesson implied in the story

 STORY:
```

**Critical Parameters**:

| Parameter | Value | Reason |
|-----------|-------|--------|
| -m | Qwen3.5-27B-Q4.gguf | Model file |
| -ngl 999 | All layers | Full GPU offload |
| -c 8192 | Context window | Long stories |
| -n 8000 | Max tokens | Long output |
| --temp 0.8 | Creativity | Literary variety |
| --repeat-penalty 1.1 | Anti-loop | Avoid repetition |
| --no-mmap | Disable mmap | Better VRAM |

### Editor (Nemotron-3-Nano)

**Purpose**: Polish story (grammar, spelling, formatting)

**System Prompt**:
```
You are a professional editor. Your task is to polish stories for publication.

Rules:
- Fix spelling and grammar errors
- Improve punctuation
- Format dialogues with em-dashes (—)
- Remove repetitions
- DO NOT change plot, characters, or events
- DO NOT add meta-information
- Output ONLY the corrected story
```

## Model Memory Requirements

### Per-Phase RAM Usage

| Agent | Model | RAM Peak | VRAM | Duration |
|-------|-------|----------|------|----------|
| Scout | Python | <100MB | - | 10-30s |
| Strategist | GLM-4.7 | ~4GB | ~2GB | 30-120s |
| Architect | DeepSeek R1 | ~6GB | ~4GB | 60-180s |
| Writer | Qwen3.5 | ~18GB | ~16GB | 15-30min |
| Editor | Nemotron | ~5GB | ~3GB | 60-180s |

### Total Resource Budget (64GB System)

```
Reserved for system:           ~10GB
Writer (peak):                 ~18GB
Available for other agents:    ~36GB
```

## Ollama Configuration

### Sequential Loading

Critical for VRAM management:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d/

cat << 'EOF' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
# Only 1 model in VRAM at a time
Environment="OLLAMA_MAX_LOADED_MODELS=1"

# Unload after 2 minutes of inactivity
Environment="OLLAMA_KEEP_ALIVE=2m"

# Listen on all interfaces
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## Temperature Tuning

| Agent | Temperature | Reason |
|-------|-------------|--------|
| Strategist | 0.3 | Focused, deterministic |
| Architect | 0.5 | Balanced creativity |
| Writer | 0.8 | High creativity for prose |
| Editor | 0.3 | Precise corrections |

## Error Handling

### OOM Recovery

The workflow includes automatic recovery:

1. **Detection**: Check for "out of memory", "oom", "killed" in logs
2. **Classification**: Mark as `FAILED_OOM` in Google Sheets
3. **Recovery**: 
   - Restart Ollama container
   - Wait 10 seconds
   - Item stays in queue for retry

### Manual Recovery

```bash
# Restart Ollama
docker restart $(docker ps -q -f name=ollama)

# Or native
sudo systemctl restart ollama

# Check memory
free -h
tegrastats --interval 1000
```

## Customizing Agents

### Adding New Ollama Models

```bash
# Pull new model
ollama pull modelname:version

# Test
curl -s http://localhost:11434/api/generate -d '{
  "model": "modelname:version",
  "prompt": "test",
  "stream": false
}'
```

### Changing Model in Workflow

In n8n workflow, edit each HTTP Request node:
1. Open node
2. Change "Model" field
3. Save

### Prompt Customization

To customize agent behavior:

1. Open n8n workflow
2. Find the HTTP Request node for the agent
3. Edit the "Prompt" field
4. Keep the JSON structure for parsing

## Performance Optimization

### GPU Clocks

```bash
# Always run before generation
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
# Should show ~2201600 (2.2 GHz)
```

### Batch Processing

The pipeline runs every 6 hours by default. To change:

1. Open n8n → Workflow → Settings
2. Find "Cron" node
3. Edit expression:
   - Current: `{{ $json.cronExpression }}`
   - Change interval: `0 */6 * * *` (every 6 hours)

### Concurrency

**CRITICAL**: Max concurrency MUST be 1

In workflow Settings:
- **Max Concurrency**: 1

This prevents VRAM collisions between simultaneous executions.

## Monitoring

### Check Model Status

```bash
# List loaded models
curl http://localhost:11434/api/tags

# Check VRAM usage
tegrastats --interval 1000
```

### View Execution Logs

```bash
# n8n logs
journalctl -u n8n -f --no-pager

# Ollama logs  
docker logs ollama -f
```
