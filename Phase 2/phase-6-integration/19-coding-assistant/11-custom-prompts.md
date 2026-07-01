# Custom Prompts and Workflows

## Table of Contents

1. [Introduction](#introduction)
2. [System Prompts](#system-prompts)
3. [Custom Commands](#custom-commands)
4. [Workflow Examples](#workflow-examples)
5. [Advanced Configuration](#advanced-configuration)

## Introduction

Custom prompts and workflows optimize AI coding tools for your specific needs on Jetson.

## System Prompts

### Basic System Prompt

```yaml
# OpenCode config
system_prompt: |
  You are an expert Python developer.
  Write clean, efficient, well-documented code.
```

### Advanced System Prompt

```yaml
system_prompt: |
  You are an expert software engineer specializing in Python and CUDA programming.
  
  Guidelines:
  - Write type-annotated Python code
  - Use docstrings with Google style
  - Follow PEP 8
  - Optimize for Jetson/ARM when relevant
  - Include error handling
  - Write unit tests when appropriate
  
  Code quality standards:
  - Maximum 100 lines per function
  - Use meaningful variable names
  - Prefer composition over inheritance
```

### Language-Specific Prompt

```yaml
system_prompt: |
  You are a JavaScript/TypeScript expert.
  
  - Use ES6+ features
  - Prefer functional components in React
  - Use TypeScript for type safety
  - Follow Airbnb style guide
  - Write unit tests with Jest
```

## Custom Commands

### OpenCode Commands

```yaml
# ~/.config/opencode/config.yaml
commands:
  review:
    description: "Review code for bugs"
    prompt: |
      Review this code for:
      1. Security vulnerabilities
      2. Performance issues
      3. Code smells
      4. Best practice violations
      
      Provide specific recommendations.

  test:
    description: "Generate unit tests"
    prompt: |
      Write comprehensive unit tests using pytest.
      Include:
      - Unit tests for each function
      - Edge case testing
      - Mock external dependencies
      - At least 80% coverage

  refactor:
    description: "Refactor code"
    prompt: |
      Refactor this code to:
      1. Improve readability
      2. Reduce complexity
      3. Improve performance
      4. Add type hints
      
      Maintain the same functionality.

  explain:
    description: "Explain code"
    prompt: |
      Explain this code in simple terms.
      Cover:
      - What it does
      - How it works
      - Key concepts
```

### Continue.dev Custom Commands

```python
# ~/.continue/config.py
config = ContinueConfig(
    custom_commands=[
        CustomCommand(
            name="review",
            description="Review code",
            prompt="""Review this code and suggest improvements."""
        ),
        CustomCommand(
            name="test",
            description="Write tests",
            prompt="""Write unit tests for this code using pytest."""
        )
    ]
)
```

## Workflow Examples

### Code Review Workflow

```python
# review_workflow.py
import requests

def review_code(file_path: str):
    """Automated code review"""
    with open(file_path, 'r') as f:
        code = f.read()
    
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "qwen2.5-coder:latest",
            "messages": [
                {"role": "system", "content": "Review code for issues"},
                {"role": "user", "content": f"Review:\n{code}"}
            ]
        }
    )
    
    return response.json()["choices"][0]["message"]["content"]

# Usage
result = review_code("main.py")
print(result)
```

### Automated Testing Workflow

```python
# test_workflow.py
def generate_tests(file_path: str):
    """Generate tests for a file"""
    with open(file_path, 'r') as f:
        code = f.read()
    
    prompt = f"""Write pytest tests for:
{code}

Include:
- test_ functions for each function
- Mock external calls
- Edge case tests
"""
    
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "qwen2.5-coder:latest",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    # Save tests
    tests = response.json()["choices"][0]["message"]["content"]
    test_path = file_path.replace(".py", "_test.py")
    with open(test_path, 'w') as f:
        f.write(tests)
    
    return test_path
```

### Documentation Workflow

```python
# docs_workflow.py
def generate_docs(file_path: str):
    """Generate documentation"""
    with open(file_path, 'r') as f:
        code = f.read()
    
    prompt = f"""Generate documentation for:
{code}

Include:
- Module docstring
- Function docstrings (Google style)
- Type hints explanation
- Usage examples
"""
    
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "qwen2.5-coder:latest",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    return response.json()["choices"][0]["message"]["content"]
```

### Commit Message Workflow

```python
# git_workflow.py
import subprocess

def generate_commit_message():
    """Generate git commit message"""
    # Get diff
    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True
    )
    diff = result.stdout
    
    if not diff:
        return "No changes to commit"
    
    prompt = f"""Generate a concise git commit message for:
{diff[:2000]}

Format:
- First line: Short description (50 chars)
- Body: Detailed explanation

Use imperative mood."""
    
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "mistral:latest",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    return response.json()["choices"][0]["message"]["content"]
```

## Advanced Configuration

### Ollama Modelfile

```bash
# Create custom model
cat > ~/.ollama/models/coder << 'EOF'
FROM qwen2.5-coder:latest

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096

SYSTEM You are an expert Python developer specializing in CUDA and ARM optimization.
EOF

ollama create coder -f ~/.ollama/models/coder

# Use it
ollama run coder
```

### Environment-Specific Prompts

```yaml
# For Jetson/CUDA development
system_prompt: |
  You are a CUDA/Python developer for NVIDIA Jetson.
  
  - Optimize for ARM64 architecture
  - Use CUDA kernels when beneficial
  - Consider memory constraints
  - Use Jetson-specific libraries (jtop, torch)

# For web development
system_prompt: |
  You are a full-stack web developer.
  
  - Modern JavaScript/TypeScript
  - RESTful API design
  - Database optimization
  - Security best practices
```

### Prompt Templates

```python
# Template system
templates = {
    "bug_fix": """Find and fix the bug in:
{code}

Explain the issue and provide the fix.""",

    "optimize": """Optimize this code:
{code}

Focus on:
- Performance
- Memory usage
- Algorithm efficiency""",

    "security": """Review for security issues:
{code}

Check for:
- Injection vulnerabilities
- Authentication issues
- Data exposure""",

    "docs": """Document this code:
{code}

Use Google docstring style."""
}

def use_template(template_name: str, code: str):
    return templates[template_name].format(code=code)
```

## Next Steps

- [Performance Optimization](./12-performance.md)
- [Troubleshooting](./13-troubleshooting.md)
