# MCP Prompts on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [System Prompts](#system-prompts)
3. [AI Task Prompts](#ai-task-prompts)
4. [Custom Prompts](#custom-prompts)

## Introduction

Create reusable prompt templates.

## System Prompts

```python
Prompt(
    name="system_status",
    description="Get system status",
    arguments=[]
)

Prompt(
    name="analyze_logs",
    description="Analyze system logs",
    arguments=[
        {
            "name": "log_file",
            "description": "Path to log file",
            "required": True
        }
    ]
)
```

## AI Task Prompts

```python
Prompt(
    name="generate_image",
    description="Generate an image",
    arguments=[
        {
            "name": "subject",
            "description": "Image subject",
            "required": True
        }
    ]
)

Prompt(
    name="transcribe_audio",
    description="Transcribe audio",
    arguments=[
        {
            "name": "file_path",
            "description": "Audio file path",
            "required": True
        }
    ]
)
```

## Custom Prompts

```python
# Custom prompt template
{
    "name": "code_review",
    "description": "Review code for issues",
    "template": """
    Please review the following code:
    
    {{code}}
    
    Look for:
    - Security issues
    - Performance problems
    - Code style violations
    - Potential bugs
    
    Provide a detailed report.
    """
}
```

## Next Steps

- [Jetson Tools](./09-jetson-tools.md)
- [Ollama Integration](./10-ollama-integration.md)
