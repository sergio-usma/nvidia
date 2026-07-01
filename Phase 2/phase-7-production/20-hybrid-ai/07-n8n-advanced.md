# Advanced n8n Workflows

## Table of Contents

1. [AI Pipeline Workflows](#ai-pipeline-workflows)
2. [Multi-Step Automation](#multi-step-automation)
3. [Error Handling](#error-handling)

## AI Pipeline Workflows

### Chat Pipeline

```
[Webhook] → [LLM (Ollama)] → [Format JSON] → [Response]
```

```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "httpMethod": "POST",
        "path": "chat"
      }
    },
    {
      "name": "LLM",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:11434/api/generate",
        "bodyParameters": {
          "model": "qwen2.5-coder:latest",
          "prompt": "={{ $json.prompt }}"
        }
      }
    },
    {
      "name": "Respond",
      "type": "n8n-nodes-base.respondToWebhook"
    }
  ]
}
```

### RAG Workflow

```
[Webhook] → [Embed Query] → [Vector Search] → [LLM] → [Response]
```

### Scheduled Batch Processing

```
[Schedule] → [Read Items] → [Loop] → [LLM] → [Save Results]
```

## Multi-Step Automation

### Email Automation

```
[IMAP] → [Extract Content] → [LLM Summary] → [Send Email]
```

### Slack Bot

```
[Slack Trigger] → [Process Command] → [LLM] → [Slack Response]
```

## Error Handling

### Retry Logic

```json
{
  "errorWorkflow": "error-handler",
  "maxTries": 3,
  "retryInterval": 5000
}
```

### Fallback Model

```
[Try: qwen2.5-coder] → [Error] → [Try: mistral] → [Error] → [Try: llama3.2]
```

## Next Steps

- [External Services](./08-external-services.md) - Connect APIs
- [Automation Patterns](./09-automation-patterns.md) - Advanced patterns
