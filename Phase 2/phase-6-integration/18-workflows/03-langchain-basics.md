# LangChain Basics

## Table of Contents

1. [Introduction](#introduction)
2. [LLM Chains](#llm-chains)
3. [Prompts](#prompts)
4. [Output Parsers](#output-parsers)
5. [Jetson-Specific Examples](#jetson-specific-examples)

## Introduction

LangChain is a framework for developing applications powered by large language models. On Jetson AGX Orin, you can run LangChain with Ollama to create powerful AI automation workflows.

## LLM Chains

```python
from langchain_ollama import ChatOllama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Initialize Ollama on Jetson
llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    temperature=0.7
)

# Create a simple chain
template = """You are a helpful AI assistant on a Jetson device.
User: {question}
Assistant:"""

prompt = PromptTemplate(
    template=template,
    input_variables=["question"]
)

chain = LLMChain(llm=llm, prompt=prompt)

# Run the chain
response = chain.run("What can you help me with?")
print(response)
```

## Prompts

### Few-Shot Prompting

```python
from langchain.prompts import FewShotPromptTemplate

examples = [
    {"input": "Summarize this: The Jetson AGX Orin is powerful", 
     "output": "Jetson AGX Orin is powerful"},
    {"input": "Summarize this: CUDA acceleration", 
     "output": "CUDA provides acceleration"},
]

example_prompt = PromptTemplate(
    template="Input: {input}\nOutput: {output}",
    input_variables=["input", "output"]
)

prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix="Summarize the following:",
    suffix="Input: {input}\nOutput:",
    input_variables=["input"]
)
```

### Chat Prompts

```python
from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import HumanMessagePromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a {role} expert on NVIDIA Jetson"),
    ("human", "Explain {topic} to me")
])

formatted_prompt = prompt.format_messages(
    role="embedded",
    topic="CUDA acceleration"
)

response = llm.invoke(formatted_prompt)
print(response.content)
```

## Output Parsers

```python
from langchain.output_parsers import CommaSeparatedListOutputParser

output_parser = CommaSeparatedListOutputParser()

template = """List {number} AI capabilities of Jetson AGX Orin:"""
prompt = PromptTemplate(
    template=template,
    input_variables=["number"],
    output_parser=output_parser
)

chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run(number=5)
parsed = output_parser.parse(result)
print(parsed)
```

## Jetson-Specific Examples

### System Monitor Chain

```python
from langchain_ollama import ChatOllama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import subprocess

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

template = """You are a Jetson system monitor assistant.
Current stats:
- CPU Usage: {cpu}
- Memory: {memory}
- GPU: {gpu}

Provide a brief analysis and recommendations:"""

prompt = PromptTemplate(
    template=template,
    input_variables=["cpu", "memory", "gpu"]
)

chain = LLMChain(llm=llm, prompt=prompt)

def get_system_stats():
    # Get actual stats from Jetson
    cpu = subprocess.check_output(
        ["top", "-bn1"], text=True
    ).split("\n")[2]
    memory = subprocess.check_output(
        ["free", "-m"], text=True
    ).split("\n")[1]
    gpu = "N/A"  # Use jtop for GPU stats
    
    return {
        "cpu": cpu,
        "memory": memory,
        "gpu": gpu
    }

stats = get_system_stats()
result = chain.run(**stats)
print(result)
```

### Model Selector Chain

```python
from langchain_ollama import ChatOllama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import JsonOutputParser
from pydantic import BaseModel

class ModelSelection(BaseModel):
    model: str
    reason: str
    vram_needed: str

parser = JsonOutputParser(pydantic_object=ModelSelection)

llm = ChatOllama(model="llama3.2:3b", temperature=0.2)

template = """Select the best Ollama model for Jetson AGX Orin 64GB.

Requirements: {requirements}
Memory available: {memory}

{format_instructions}"""

prompt = PromptTemplate(
    template=template,
    input_variables=["requirements", "memory"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run(
    requirements="code generation and reasoning",
    memory="60GB"
)
selected = parser.parse(result)
print(f"Model: {selected['model']}")
print(f"Reason: {selected['reason']}")
```

## Next Steps

- [LangChain on Jetson](./04-langchain-jetson.md)
- [Agents](./05-agents.md)
