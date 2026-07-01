# Tools and Functions

## Table of Contents

1. [Introduction](#introduction)
2. [Function Calling](#function-calling)
3. [Custom Tools](#custom-tools)
4. [Tool Composition](#tool-composition)

## Introduction

Tools extend LLM capabilities by enabling them to interact with external systems. On Jetson, we create tools for system control, data processing, and API interactions.

## Function Calling

### Using Ollama Function Calling

```python
from langchain_ollama import ChatOllama
from langchain.tools import tool

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

@tool
def get_jetson_temperature() -> str:
    """Get CPU/GPU temperature from Jetson."""
    import subprocess
    try:
        result = subprocess.run(
            ["cat", "/sys/class/thermal/thermal_zone0/temp"],
            capture_output=True,
            text=True
        )
        temp = int(result.stdout.strip()) / 1000
        return f"CPU Temperature: {temp}°C"
    except:
        return "Unable to read temperature"

@tool
def run_benchmark(task: str) -> str:
    """Run a performance benchmark on Jetson."""
    import time
    start = time.time()
    # Placeholder - add actual benchmark
    time.sleep(1)
    return f"Benchmark '{task}' completed in {time.time() - start:.2f}s"

tools = [get_jetson_temperature, run_benchmark]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Invoke with tool request
response = llm_with_tools.invoke(
    "What is the Jetson temperature and run a quick benchmark?"
)

# Check for tool calls
if hasattr(response, 'tool_calls') and response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"Tool: {tool_call['name']}")
        print(f"Args: {tool_call['args']}")
```

### Tool Result Handling

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

@tool
def execute_command(command: str) -> str:
    """Execute a shell command on Jetson."""
    import subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {str(e)}"

@tool  
def read_file(path: str) -> str:
    """Read a file from the filesystem."""
    try:
        with open(path, 'r') as f:
            return f.read()[:2000]  # Limit output
    except Exception as e:
        return f"Error: {str(e)}"

tools = [execute_command, read_file]

prompt = PromptTemplate.from_template("""
You are a Jetson assistant. Use tools when needed.

User: {input}
""")

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "Read the system memory info and show CPU usage"
})
```

## Custom Tools

### REST API Tool

```python
import requests
from langchain.tools import tool

class APITool:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def get(self, endpoint: str) -> str:
        try:
            resp = requests.get(f"{self.base_url}{endpoint}")
            return resp.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def post(self, endpoint: str, data: dict) -> str:
        try:
            resp = requests.post(f"{self.base_url}{endpoint}", json=data)
            return resp.text
        except Exception as e:
            return f"Error: {str(e)}"

@tool
def query_ollama(prompt: str, model: str = "llama3.2:3b") -> str:
    """Query Ollama LLM."""
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False}
    )
    return resp.json().get("response", "No response")

@tool
def list_ollama_models() -> str:
    """List available Ollama models."""
    resp = requests.get("http://localhost:11434/api/tags")
    models = resp.json().get("models", [])
    return "\n".join([m["name"] for m in models])

tools = [query_ollama, list_ollama_models]
```

### File Operations Tool

```python
import os
import glob
from langchain.tools import tool

@tool
def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files in a directory matching pattern."""
    try:
        files = glob.glob(f"{directory}/{pattern}")
        return "\n".join(files) if files else "No files found"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def file_info(path: str) -> str:
    """Get file information."""
    try:
        stat = os.stat(path)
        return f"Size: {stat.st_size} bytes\nModified: {stat.st_mtime}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def search_in_file(path: str, pattern: str) -> str:
    """Search for pattern in file."""
    try:
        import re
        with open(path, 'r') as f:
            content = f.read()
        matches = re.findall(f".*{pattern}.*", content, re.IGNORECASE)
        return "\n".join(matches[:10]) if matches else "No matches"
    except Exception as e:
        return f"Error: {str(e)}"
```

### System Monitoring Tool

```python
import psutil
from langchain.tools import tool

@tool
def system_stats() -> str:
    """Get comprehensive system statistics."""
    stats = []
    
    # CPU
    stats.append(f"CPU: {psutil.cpu_percent(interval=1)}%")
    stats.append(f"CPU Count: {psutil.cpu_count()}")
    
    # Memory
    mem = psutil.virtual_memory()
    stats.append(f"RAM: {mem.percent}% ({mem.used / 1e9:.1f}GB / {mem.total / 1e9:.1f}GB)")
    
    # Disk
    disk = psutil.disk_usage('/')
    stats.append(f"Disk: {disk.percent}% ({disk.used / 1e9:.1f}GB / {disk.total / 1e9:.1f}GB)")
    
    return "\n".join(stats)

@tool
def process_list(top: int = 10) -> str:
    """List top processes by CPU usage."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except:
            pass
    
    processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
    
    result = ["Top Processes:"]
    for p in processes[:top]:
        result.append(f"PID {p['pid']}: {p['name']} - CPU: {p['cpu_percent']:.1f}%, MEM: {p['memory_percent']:.1f}%")
    
    return "\n".join(result)

tools = [system_stats, process_list]
```

## Tool Composition

### Tool with Tool

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, Tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

# First tool
def get_weather(location: str) -> str:
    return "Sunny, 25°C"  # Simplified

# Second tool - uses first tool's result
def plan_activities(weather: str) -> str:
    prompt = PromptTemplate(
        template="Given weather: {weather}, suggest outdoor activities",
        input_variables=["weather"]
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run(weather=weather)

tools = [
    Tool(name="Weather", func=get_weather, description="Get weather for location"),
    Tool(name="Activities", func=plan_activities, description="Plan activities based on weather")
]

# Use in agent
prompt = PromptTemplate.from_template("""
Weather for {location}: {weather}
Activities: {activities}
""")

# Chain tools manually
weather_result = get_weather("San Francisco")
activities_result = plan_activities(weather_result)
```

### Sequential Tool Execution

```python
def execute_tool_chain(tools, initial_input):
    current_input = initial_input
    results = {}
    
    for tool in tools:
        result = tool.func(current_input)
        results[tool.name] = result
        current_input = result
    
    return results

# Example: Research → Summarize → Translate
tools = [
    Tool(name="research", func=lambda x: f"Research on: {x}"),
    Tool(name="summarize", func=lambda x: f"Summary of: {x[:50]}..."),
    Tool(name="translate", func=lambda x: f"ES: {x}")
]

results = execute_tool_chain(tools, "Jetson AGX Orin optimization")
```

## Next Steps

- [Memory Management](./11-memory.md)
- [Ollama Agents](./12-ollama-agents.md)
