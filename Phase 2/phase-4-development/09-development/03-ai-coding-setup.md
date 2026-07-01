# AI Coding with Continue

Set up Continue extension in VS Code for AI-assisted coding with Ollama.

## Install Continue

In VS Code (connected to Jetson via SSH):

1. Go to Extensions
2. Search for "Continue"
3. Install

## Configure Continue

Edit `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Jetson Ollama",
      "provider": "ollama",
      "model": "qwen2.5-coder:14b",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen 1.5B (Autocomplete)",
    "provider": "ollama",
    "model": "qwen2.5-coder:1.5b",
    "apiBase": "http://localhost:11434"
  },
  "tabAutocompleteOptions": {
    "useCopyBuffer": true,
    "maxPromptTokens": 400,
    "debounceDelay": 350
  }
}
```

## Using Continue

- **Chat**: Press Ctrl+L or click Continue in sidebar
- **Autocomplete**: Start typing, suggestions appear
- **Edit**: Select code, press Ctrl+I
- **Context**: Use @codebase to search your code

## Download Models for Coding

```bash
ollama pull qwen2.5-coder:14b
ollama pull qwen2.5-coder:1.5b
```

## Model Recommendations

| Model | Use | Size |
|-------|-----|------|
| qwen2.5-coder:1.5b | Autocomplete | ~1GB |
| qwen2.5-coder:7b | Chat | ~4GB |
| qwen2.5-coder:14b | Complex tasks | ~9GB |
| llama3.2 | General | ~4GB |

## Keep Models Loaded

Prevent model unloading:

```bash
curl http://localhost:11434/api/generate -d '{"model": "qwen2.5-coder:14b", "keep_alive": -1}'
```

## Next Steps

- [jtop Monitoring](../part-9-monitoring/01-jtop-monitoring.md)
- [Service Management](../part-10-security/02-service-management.md)
