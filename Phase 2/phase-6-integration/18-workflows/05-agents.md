# Agents on Jetson

## Table of Contents

1. [Introduction](#introduction)
2. [LangChain Agents](#langchain-agents)
3. [Tool-Using Agents](#tool-using-agents)
4. [ReAct Agents](#react-agents)
5. [Custom Jetson Agents](#custom-jetson-agents)

## Introduction

Agents are AI systems that can use tools, make decisions, and take actions. On Jetson, we create agents powered by Ollama models.

## LangChain Agents

### Using LangChain's Agent Executor

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0.3
)

# Define tools
from langchain.tools import Tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

search = DuckDuckGoSearchAPIWrapper()

tools = [
    Tool(
        name="Search",
        func=search.run,
        description="Search the web for information"
    ),
    Tool(
        name="Calculator",
        func=lambda x: str(eval(x)),
        description="Calculate mathematical expressions"
    )
]

# Create agent
prompt = PromptTemplate.from_template("""
Answer the following question using the tools available.

Question: {input}

Thought: Consider what to do next
Action: Search or Calculator
Action Input: The search query or calculation
Observation: Result from tool
Final Answer: {agent_scratchpad}
""")

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = agent_executor.invoke({
    "input": "What is JetPack version and what is 15 + 27?"
})
print(result['output'])
```

### Conversational Agents

```python
from langchain_ollama import ChatOllama
from langchain.agents import ConversationalChatAgent
from langchain.agent_toolkits import ConvoXAgentToolkit

llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

# Create tool kit
toolkit = ConvoXAgentToolkit.from_llm_and_tools(
    llm=llm,
    tools=tools
)

# Create agent
agent = ConversationalChatAgent.from_llm_and_tools(
    llm=llm,
    tools=tools
)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=None,
    verbose=True
)

response = executor.invoke({
    "input": "Tell me about CUDA on Jetson"
})
print(response['output'])
```

## Tool-Using Agents

### Define Custom Tools

```python
from langchain.tools import tool
import subprocess
import requests

@tool
def get_jetson_stats() -> str:
    """Get current Jetson system statistics."""
    try:
        # CPU and memory
        mem = subprocess.check_output(
            ["free", "-h"], text=True
        )
        cpu = subprocess.check_output(
            ["uptime"], text=True
        )
        return f"Memory:\n{mem}\nCPU:\n{cpu}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_gpu_info() -> str:
    """Get Jetson GPU information."""
    try:
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception:
        return "CUDA not directly available via nvcc on Jetson"

@tool
def check_ollama_models() -> str:
    """Check available Ollama models."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        models = response.json().get('models', [])
        return "\n".join([m['name'] for m in models])
    except Exception as e:
        return f"Ollama not running: {str(e)}"

@tool
def restart_service(service: str) -> str:
    """Restart a system service."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "restart", service],
            capture_output=True,
            text=True
        )
        return f"Service {service} restarted" if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

# Use tools
tools = [
    get_jetson_stats,
    get_gpu_info,
    check_ollama_models,
    restart_service
]
```

### Tool Agent with Jetson Tools

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

# Use the tools defined above
prompt = PromptTemplate.from_template("""
You are a Jetson AGX Orin system assistant. Use the provided tools to help the user.

Available tools:
- get_jetson_stats: Get CPU, memory stats
- get_gpu_info: Get GPU/CUDA info
- check_ollama_models: List Ollama models
- restart_service: Restart a service

Question: {input}
""")

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Query
result = executor.invoke({
    "input": "Show me system stats and list Ollama models"
})
print(result['output'])
```

## ReAct Agents

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import ReActSingleInputParser

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

# Tools
tools = [get_jetson_stats, check_ollama_models]

# ReAct prompt template
react_prompt = """Assistant can interact with external APIs to answer questions.

Available tools:
{tools}

Use the following format:

Question: the input question
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original question

Begin!

Question: {input}
{agent_scratchpad}
"""

# Create agent
agent = create_react_agent(llm, tools, react_prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "What are the current system stats?"
})
print(result['output'])
```

## Custom Jetson Agents

### Research Agent

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, Tool
from langchain.prompts import PromptTemplate
import requests

llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

def search_arxiv(query: str) -> str:
    """Search arXiv for papers."""
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results=5"
    try:
        response = requests.get(url)
        return response.text[:2000]
    except Exception as e:
        return f"Error: {str(e)}"

def search_web(query: str) -> str:
    """Search the web."""
    from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
    return DuckDuckGoSearchAPIWrapper().run(query)

tools = [
    Tool(
        name="arXiv Search",
        func=search_arxiv,
        description="Search academic papers on arXiv"
    ),
    Tool(
        name="Web Search",
        func=search_web,
        description="Search the web for information"
    ),
    Tool(
        name="Ollama Models",
        func=lambda x: str(requests.get("http://localhost:11434/api/tags").json()),
        description="List available Ollama models"
    )
]

prompt = PromptTemplate.from_template("""
You are a research agent for Jetson AI development.
Use the available tools to research the topic and provide a comprehensive answer.

Topic: {input}

Research and provide findings.
""")

agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "Latest research on transformer optimization for edge devices"
})
print(result['output'])
```

### Code Generation Agent

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, Tool
from langchain.prompts import PromptTemplate
import subprocess

llm = ChatOllama(model="llama3.2:3b", temperature=0.2)

@Tool
def run_python(code: str) -> str:
    """Execute Python code and return output."""
    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {str(e)}"

@Tool
def check_jetson_hardware() -> str:
    """Check Jetson hardware specs."""
    specs = []
    try:
        with open("/proc/cpuinfo", "r") as f:
            specs.append(f.read()[:500])
    except:
        pass
    return "\n".join(specs)

tools = [run_python, check_jetson_hardware]

prompt = PromptTemplate.from_template("""
You are a Python code generation agent for NVIDIA Jetson.
Use the available tools to verify your code works.

Task: {input}

Generate and test Python code for Jetson.
""")

agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "Generate code to read GPU temperature on Jetson"
})
print(result['output'])
```

## Next Steps

- [Workflows](./06-workflows.md)
- [n8n Setup](./07-n8n-setup.md)
