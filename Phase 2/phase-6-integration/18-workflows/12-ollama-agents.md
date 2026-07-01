# Ollama Agents

## Table of Contents

1. [Introduction](#introduction)
2. [Direct Ollama Agent](#direct-ollama-agent)
3. [Multi-Model Agents](#multi-model-agents)
4. [Specialized Agents](#specialized-agents)

## Introduction

Build autonomous agents powered by Ollama on Jetson AGX Orin.

## Direct Ollama Agent

### Simple Autonomous Agent

```python
import requests
import json
from typing import List, Dict, Any

class OllamaAgent:
    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.tools = []
    
    def add_tool(self, func, description: str):
        self.tools.append({
            "function": func,
            "description": description
        })
    
    def generate(self, prompt: str, system: str = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        return response.json().get("response", "")
    
    def chat(self, messages: List[Dict]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        return response.json().get("message", {}).get("content", "")
    
    def run(self, task: str, max_iterations: int = 5):
        messages = [
            {"role": "system", "content": "You are an autonomous agent. Complete the task step by step."}
        ]
        
        for i in range(max_iterations):
            messages.append({"role": "user", "content": task})
            
            response = self.chat(messages)
            messages.append({"role": "assistant", "content": response})
            
            # Simple completion check
            if len(response) > 50:
                break
        
        return response

# Usage
agent = OllamaAgent(model="llama3.2:3b")
result = agent.run("Explain how to optimize Jetson for inference")
print(result)
```

### Tool-Enabled Agent

```python
class ToolOllamaAgent(OllamaAgent):
    def __init__(self, model: str = "llama3.2:3b"):
        super().__init__(model)
    
    def execute_with_tools(self, task: str) -> str:
        # Build tool descriptions
        tool_desc = "\n".join([
            f"- {t['description']}" for t in self.tools
        ])
        
        system_prompt = f"""You have access to these tools:
{tool_desc}

Use tools when needed to complete the task. Format your response as:
THINK: Your reasoning
ACTION: Tool name or NONE
INPUT: Tool input or N/A
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # First turn
        messages.append({"role": "user", "content": task})
        response = self.chat(messages)
        
        # Parse and execute
        # (Simplified - in production use proper parsing)
        return response

# Add tools
def get_system_info():
    import subprocess
    return subprocess.check_output(["uname", "-a"]).decode()

agent = ToolOllamaAgent()
agent.add_tool(get_system_info, "Get system information")
result = agent.execute_with_tools("What system are we running on?")
```

## Multi-Model Agents

### Router Agent

```python
class RouterAgent:
    def __init__(self):
        self.models = {
            "reasoning": "deepseek-r1:7b",
            "chat": "llama3.2:3b",
            "code": "codellama:7b",
            "embedding": "nomic-embed-text"
        }
        self.agents = {name: OllamaAgent(model) for name, model in self.models.items()}
    
    def route(self, task: str) -> str:
        # Determine best model
        router_prompt = f"""Classify this task: {task}
        
Categories: reasoning, chat, code
Return only the category name."""

        router = OllamaAgent("llama3.2:3b")
        category = router.generate(router_prompt).strip().lower()
        
        # Default to chat
        if category not in self.agents:
            category = "chat"
        
        return category
    
    def run(self, task: str):
        category = self.route(task)
        agent = self.agents[category]
        return agent.run(task)

# Usage
router = RouterAgent()
result = router.run("Write a Python function to calculate fibonacci")
print(f"Used model category: {result}")
```

### Ensemble Agent

```python
class EnsembleAgent:
    def __init__(self, models: List[str] = None):
        if models is None:
            models = ["llama3.2:3b", "mistral:7b", "qwen:7b"]
        self.agents = [OllamaAgent(m) for m in models]
    
    def run(self, task: str) -> str:
        # Run all models
        responses = []
        for agent in self.agents:
            try:
                response = agent.run(task)
                responses.append(response)
            except:
                pass
        
        # Consolidate responses
        if not responses:
            return "No responses"
        
        if len(responses) == 1:
            return responses[0]
        
        # Use one model to consolidate
        consolidation_prompt = f"""Given these responses, provide the best answer:

"""
        for i, r in enumerate(responses, 1):
            consolidation_prompt += f"\n{i}. {r}\n"
        
        consolidator = OllamaAgent("llama3.2:3b")
        return consolidator.generate(consolidation_prompt)
```

## Specialized Agents

### Research Agent

```python
class ResearchAgent:
    def __init__(self):
        self.ollama = OllamaAgent("llama3.2:3b")
        self.tools = {
            "search": self.web_search,
            "analyze": self.analyze_paper,
            "summarize": self.summarize
        }
    
    def web_search(self, query: str) -> str:
        # Use DuckDuckGo or other search
        from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
        search = DuckDuckGoSearchAPIWrapper()
        return search.run(query)
    
    def analyze_paper(self, text: str) -> str:
        prompt = f"Analyze this research paper:\n{text[:2000]}"
        return self.ollama.generate(prompt)
    
    def summarize(self, text: str) -> str:
        prompt = f"Summarize this:\n{text}"
        return self.ollama.generate(prompt)
    
    def research(self, topic: str) -> Dict[str, str]:
        # Step 1: Search
        search_results = self.tools["search"](f"{topic} research")
        
        # Step 2: Analyze
        analysis = self.tools["analyze"](search_results)
        
        # Step 3: Summarize
        summary = self.tools["summarize"](analysis)
        
        return {
            "search_results": search_results,
            "analysis": analysis,
            "summary": summary
        }

# Usage
researcher = ResearchAgent()
results = researcher.research("transformer optimization edge devices")
```

### Code Agent

```python
class CodeAgent:
    def __init__(self):
        self.ollama = OllamaAgent("codellama:7b")
        self.executor = {
            "python": self.run_python,
            "bash": self.run_bash
        }
    
    def run_python(self, code: str) -> str:
        import subprocess
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    
    def run_bash(self, command: str) -> str:
        import subprocess
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    
    def generate_and_run(self, task: str, language: str = "python") -> str:
        # Generate code
        prompt = f"""Write {language} code to accomplish this task:
{task}

Only output the code, no explanations."""
        
        code = self.ollama.generate(prompt)
        
        # Execute
        if language in self.executor:
            return self.executor[language](code)
        return code

# Usage
code_agent = CodeAgent()
result = code_agent.generate_and_run("Print hello world")
```

### Data Processing Agent

```python
import pandas as pd

class DataAgent:
    def __init__(self):
        self.ollama = OllamaAgent("llama3.2:3b")
    
    def analyze_data(self, data_path: str) -> str:
        # Read data
        if data_path.endswith('.csv'):
            df = pd.read_csv(data_path)
        elif data_path.endswith('.json'):
            df = pd.read_json(data_path)
        else:
            return "Unsupported file format"
        
        # Get summary
        summary = f"Shape: {df.shape}\nColumns: {list(df.columns)}\n"
        summary += f"Data types:\n{df.dtypes}\n"
        
        # Let LLM analyze
        prompt = f"Analyze this dataset and provide insights:\n{summary}"
        return self.ollama.generate(prompt)
    
    def clean_data(self, data_path: str, operations: List[str]) -> str:
        df = pd.read_csv(data_path)
        
        for op in operations:
            if "drop_na" in op:
                df = df.dropna()
            elif "remove_duplicates" in op:
                df = df.drop_duplicates()
        
        output_path = data_path.replace(".csv", "_cleaned.csv")
        df.to_csv(output_path, index=False)
        
        return f"Cleaned data saved to {output_path}"

# Usage
data_agent = DataAgent()
analysis = data_agent.analyze_data("data.csv")
```

### System Admin Agent

```python
import subprocess
import psutil

class SystemAdminAgent:
    def __init__(self):
        self.ollama = OllamaAgent("llama3.2:3b")
    
    def get_status(self) -> Dict:
        return {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "temperature": self.get_temperature()
        }
    
    def get_temperature(self) -> str:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return f"{int(f.read()) / 1000}°C"
        except:
            return "N/A"
    
    def analyze_and_recommend(self) -> str:
        status = self.get_status()
        
        prompt = f"""Analyze these Jetson system stats and recommend actions:
CPU: {status['cpu']}%
Memory: {status['memory']}%
Disk: {status['disk']}%
Temperature: {status['temperature']}

Provide recommendations."""
        
        return self.ollama.generate(prompt)

# Usage
admin = SystemAdminAgent()
recommendations = admin.analyze_and_recommend()
```

## Next Steps

- [Troubleshooting](./13-troubleshooting.md)
