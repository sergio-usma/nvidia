# Workflows with LangChain

## Table of Contents

1. [Introduction](#introduction)
2. [Sequential Chains](#sequential-chains)
3. [Router Chains](#router-chains)
4. [Transform Chains](#transform-chains)
5. [Custom Workflows](#custom-workflows)

## Introduction

Workflows chain multiple LLM operations together to create complex AI pipelines on Jetson.

## Sequential Chains

### Simple Sequential Chain

```python
from langchain_ollama import ChatOllama
from langchain.chains import SimpleSequentialChain
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

# First chain - generate topic
template1 = "Generate a short topic about {input}"
prompt1 = PromptTemplate(template=template1, input_variables=["input"])
chain1 = LLMChain(llm=llm, prompt=prompt1)

# Second chain - expand on topic
template2 = "Expand this into a brief explanation: {topic}"
prompt2 = PromptTemplate(template=template2, input_variables=["topic"])
chain2 = LLMChain(llm=llm, prompt=prompt2)

# Combine
workflow = SimpleSequentialChain(
    chains=[chain1, chain2],
    verbose=True
)

result = workflow.invoke({"input": "CUDA on Jetson"})
print(result['output'])
```

### More Complex Sequential

```python
from langchain.chains import SequentialChain

# Chain 1: Topic
chain1 = LLMChain(
    llm=llm,
    prompt=PromptTemplate(
        template="What is the best topic for {user_request}?",
        input_variables=["user_request"]
    ),
    output_key="topic"
)

# Chain 2: Outline
chain2 = LLMChain(
    llm=llm,
    prompt=PromptTemplate(
        template="Create an outline for: {topic}",
        input_variables=["topic"]
    ),
    output_key="outline"
)

# Chain 3: Content
chain3 = LLMChain(
    llm=llm,
    prompt=PromptTemplate(
        template="Write content for this outline:\n{outline}",
        input_variables=["outline"]
    ),
    output_key="content"
)

# Execute
workflow = SequentialChain(
    chains=[chain1, chain2, chain3],
    input_variables=["user_request"],
    output_variables=["topic", "outline", "content"],
    verbose=True
)

result = workflow.invoke({
    "user_request": "Jetson AGX Orin optimization"
})

print(f"Topic: {result['topic']}")
print(f"Outline: {result['outline']}")
print(f"Content: {result['content'][:500]}...")
```

## Router Chains

### LLMRouterChain

```python
from langchain.chains.router import LLMRouterChain
from langchain.chains.router import MultiPromptChain
from langchain.prompts import PromptTemplate

# Define destination chains
physics_template = """You are a physics expert.
Question: {input}
Answer:"""

math_template = """You are a mathematics expert.
Question: {input}
Answer:"""

cs_template = """You are a computer science expert.
Question: {input}
Answer:"""

prompt_infos = [
    {"name": "physics", "description": "For physics questions", "prompt_template": physics_template},
    {"name": "math", "description": "For math questions", "prompt_template": math_template},
    {"name": "cs", "description": "For CS questions", "prompt_template": cs_template},
]

destination_chains = {}
for info in prompt_infos:
    chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate(
            template=info["prompt_template"],
            input_variables=["input"]
        )
    )
    destination_chains[info["name"]] = chain

# Default chain
default_chain = LLMChain(llm=llm, prompt=PromptTemplate(
    template="Explain: {input}",
    input_variables=["input"]
))

# Router prompt
router_template = """Given a question, choose the best destination:

{destinations}

Question: {input}

Return the name of the destination:"""

router_prompt = PromptTemplate(
    template=router_template,
    input_variables=["input"],
    output_variables=["destination"]
)

router_chain = LLMRouterChain.from_llm(llm, router_prompt)

# MultiPromptChain
chain = MultiPromptChain(
    router_chain=router_chain,
    destination_chains=destination_chains,
    default_chain=default_chain,
    verbose=True
)

result = chain.invoke({"input": "What is CUDA?"})
print(result['text'])
```

## Transform Chains

### Input/Output Transformation

```python
from langchain.chains import TransformChain
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

# Transform input
def transform_input(inputs: dict) -> dict:
    text = inputs["text"]
    return {
        "processed": text.upper() + " [PROCESSED]"
    }

# Transform output
def transform_output(inputs: dict) -> dict:
    text = inputs["text"]
    return {
        "final": text.replace(".", "!")
    }

input_chain = TransformChain(
    transform=transform_input,
    input_variables=["text"],
    output_variables=["processed"]
)

llm_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate(
        template="Rephrase: {processed}",
        input_variables=["processed"]
    ),
    output_variables=["response"]
)

output_chain = TransformChain(
    transform=transform_output,
    input_variables=["response"],
    output_variables=["final"]
)

# Combine
from langchain.chains import SequentialChain
workflow = SequentialChain(
    chains=[input_chain, llm_chain, output_chain],
    input_variables=["text"],
    output_variables=["final"],
    verbose=True
)

result = workflow.invoke({"text": "Jetson is powerful"})
print(result['final'])
```

## Custom Workflows

### RAG Workflow

```python
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Load vector store
vectorstore = FAISS.load_local(
    "jetson_docs",
    embeddings,
    allow_dangerous_deserialization=True
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# RAG prompt
rag_prompt = PromptTemplate(
    template="""Use the context to answer.

Context: {context}

Question: {question}

Answer:""",
    input_variables=["context", "question"]
)

# RAG chain
rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": rag_prompt}
)

# Test
result = rag_chain.invoke({
    "query": "How to optimize Jetson for inference?"
})
print(result['result'])
```

### Multi-Modal Workflow

```python
from langchain_ollama import ChatOllama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

# Analyze image description
image_prompt = PromptTemplate(
    template="Analyze this image description: {description}. What objects/people are present?",
    input_variables=["description"]
)
image_chain = LLMChain(llm=llm, prompt=image_prompt, output_key="analysis")

# Generate caption
caption_prompt = PromptTemplate(
    template="Based on this analysis: {analysis}, write a creative caption.",
    input_variables=["analysis"]
)
caption_chain = LLMChain(llm=llm, prompt=caption_prompt, output_key="caption")

# Workflow
from langchain.chains import SequentialChain
workflow = SequentialChain(
    chains=[image_chain, caption_chain],
    input_variables=["description"],
    output_variables=["analysis", "caption"],
    verbose=True
)

result = workflow.invoke({
    "description": "A person standing next to a NVIDIA Jetson AGX Orin device"
})
print(f"Analysis: {result['analysis']}")
print(f"Caption: {result['caption']}")
```

### Agent Workflow

```python
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, Tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

# Define tools
import subprocess

def get_stats(input: str) -> str:
    """Get system statistics."""
    try:
        result = subprocess.run(
            ["free", "-h"],
            capture_output=True,
            text=True
        )
        return result.stdout
    except:
        return "Error getting stats"

tools = [Tool(name="Stats", func=get_stats, description="Get system stats")]

# Create agent
from langchain.agents import create_react_agent

prompt = PromptTemplate.from_template("""
Use tools to help answer.

Question: {input}
""")

agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Combine with LLM chain
template = """Given the stats: {stats}, provide optimization advice."""
advice_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate(template=template, input_variables=["stats"]),
    output_key="advice"
)

# Combined workflow
stats_result = executor.invoke({"input": "Get system stats"})
advice_result = advice_chain.invoke({"stats": stats_result['output']})

print(advice_result['text'])
```

## Next Steps

- [n8n Setup](./07-n8n-setup.md)
- [LangGraph](./08-langgraph.md)
