# LangGraph for Complex Agents

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Graph](#basic-graph)
4. [State Management](#state-management)
5. [Conditional Flows](#conditional-flows)

## Introduction

LangGraph is LangChain's library for building stateful, multi-agent workflows with cycles - essential for complex AI applications on Jetson.

## Installation

```bash
pip install langgraph
```

## Basic Graph

### Simple Node Graph

```python
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from typing import TypedDict

llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

# Define state
class GraphState(TypedDict):
    input: str
    output: str
    steps: list

# Define nodes
def generate(state: GraphState) -> GraphState:
    response = llm.invoke(f"Generate a short story about: {state['input']}")
    return {"output": response.content, "steps": state.get("steps", []) + ["generate"]}

def refine(state: GraphState) -> GraphState:
    response = llm.invoke(f"Refine this: {state['output']}")
    return {"output": response.content, "steps": state.get("steps", []) + ["refine"]}

# Create graph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("generate", generate)
workflow.add_node("refine", refine)

# Define edges
workflow.set_entry_point("generate")
workflow.add_edge("generate", "refine")
workflow.add_edge("refine", END)

# Compile
app = workflow.compile()

# Run
result = app.invoke({
    "input": "a robot on Jetson",
    "output": "",
    "steps": []
})

print(result['output'])
```

### Graph with Multiple Paths

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class MultiState(TypedDict):
    question: str
    answer: str
    category: str
    needs_search: bool

def categorize(state: MultiState) -> MultiState:
    response = llm.invoke(
        f"Categorize this question: {state['question']}\n"
        "Return: tech, science, or general"
    )
    category = response.content.lower()
    if "tech" in category:
        cat = "tech"
    elif "science" in category:
        cat = "science"
    else:
        cat = "general"
    return {"category": cat, "needs_search": cat != "general"}

def answer_tech(state: MultiState) -> MultiState:
    response = llm.invoke(f"Answer as a tech expert: {state['question']}")
    return {"answer": response.content}

def answer_science(state: MultiState) -> MultiState:
    response = llm.invoke(f"Answer as a science expert: {state['question']}")
    return {"answer": response.content}

def answer_general(state: MultiState) -> MultiState:
    response = llm.invoke(state['question'])
    return {"answer": response.content}

def should_search(state: MultiState) -> str:
    if state.get("needs_search"):
        return "search"
    return "answer"

# Create graph
workflow = StateGraph(MultiState)

workflow.add_node("categorize", categorize)
workflow.add_node("answer_tech", answer_tech)
workflow.add_node("answer_science", answer_science)
workflow.add_node("answer_general", answer_general)

workflow.set_entry_point("categorize")

workflow.add_conditional_edges(
    "categorize",
    should_search,
    {
        "search": "answer_tech",
        "answer": "answer_general"
    }
)

workflow.add_edge("answer_tech", END)
workflow.add_edge("answer_general", END)
workflow.add_edge("answer_science", END)

app = workflow.compile()

result = app.invoke({
    "question": "What is CUDA?",
    "answer": "",
    "category": "",
    "needs_search": False
})

print(result['answer'])
```

## State Management

### Persistent State

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from typing import TypedDict

# Checkpoint for memory persistence
checkpointer = MemorySaver()

workflow = StateGraph(GraphState)
workflow.add_node("generate", generate)
workflow.set_entry_point("generate")
workflow.add_edge("generate", END)

app = workflow.compile(checkpointer=checkpointer)

# Run with thread_id for persistence
config = {"configurable": {"thread_id": "user-123"}}

result = app.invoke(
    {"input": "Jetson AI", "output": "", "steps": []},
    config
)
print(result['output'])

# Continue conversation
result = app.invoke(
    {"input": "Make it shorter", "output": "", "steps": []},
    config
)
```

### State Updates

```python
from langgraph.graph import StateGraph
from typing import TypedDict
from operator import add

class State(TypedDict):
    count: int
    history: list

def increment(state: State):
    return {"count": add(state["count"], 1), "history": add(state["history"], ["increment"])}

def decrement(state: State):
    return {"count": add(state["count"], -1), "history": add(state["history"], ["decrement"])}

workflow = StateGraph(State)
workflow.add_node("increment", increment)
workflow.add_node("decrement", decrement)
workflow.set_entry_point("increment")
workflow.add_edge("increment", "decrement")
workflow.add_edge("decrement", END)

app = workflow.compile()

result = app.invoke({"count": 0, "history": []})
print(f"Count: {result['count']}")  # -1
print(f"History: {result['history']}")  # ['increment', 'decrement']
```

## Conditional Flows

### Branch by Condition

```python
from langgraph.graph import StateGraph, END

class BranchState(TypedDict):
    user_input: str
    sentiment: str
    response: str

def analyze_sentiment(state: BranchState) -> BranchState:
    response = llm.invoke(
        f"Analyze sentiment: {state['user_input']}\n"
        "Return: positive, negative, or neutral"
    )
    return {"sentiment": response.content.lower()}

def respond_positive(state: BranchState) -> BranchState:
    return {"response": "That's great to hear!"}

def respond_negative(state: BranchState) -> BranchState:
    return {"response": "I'm sorry to hear that."}

def respond_neutral(state: BranchState) -> BranchState:
    return {"response": "I understand."}

def route_sentiment(state: BranchState) -> str:
    sentiment = state["sentiment"]
    if "positive" in sentiment:
        return "positive"
    elif "negative" in sentiment:
        return "negative"
    return "neutral"

workflow = StateGraph(BranchState)

workflow.add_node("analyze", analyze_sentiment)
workflow.add_node("respond_positive", respond_positive)
workflow.add_node("respond_negative", respond_negative)
workflow.add_node("respond_neutral", respond_neutral)

workflow.set_entry_point("analyze")

workflow.add_conditional_edges(
    "analyze",
    route_sentiment,
    {
        "positive": "respond_positive",
        "negative": "respond_negative",
        "neutral": "respond_neutral"
    }
)

workflow.add_edge("respond_positive", END)
workflow.add_edge("respond_negative", END)
workflow.add_edge("respond_neutral", END)

app = workflow.compile()

result = app.invoke({
    "user_input": "I love using my Jetson!",
    "sentiment": "",
    "response": ""
})

print(result['response'])
```

### Loop with Condition

```python
from langgraph.graph import StateGraph, END

class LoopState(TypedDict):
    iteration: int
    max_iterations: int
    result: str

def generate_candidate(state: LoopState) -> LoopState:
    response = llm.invoke(f"Generate idea #{state['iteration'] + 1}")
    return {"iteration": state["iteration"] + 1, "result": response.content}

def evaluate(state: LoopState) -> str:
    if state["iteration"] >= state["max_iterations"]:
        return "done"
    return "continue"

workflow = StateGraph(LoopState)

workflow.add_node("generate", generate_candidate)
workflow.set_entry_point("generate")

workflow.add_conditional_edges(
    "generate",
    evaluate,
    {
        "continue": "generate",
        "done": END
    }
)

app = workflow.compile()

result = app.invoke({
    "iteration": 0,
    "max_iterations": 3,
    "result": ""
})

print(f"Iterations: {result['iteration']}")
print(f"Final result: {result['result']}")
```

### Human-in-the-Loop

```python
from langgraph.graph import StateGraph, END

def human_review(state: GraphState) -> GraphState:
    # In production, this would pause and wait for human input
    user_approved = input("Approve this output? (y/n): ") == "y"
    return {"approved": user_approved, "steps": state.get("steps", []) + ["human_review"]}

def should_approve(state: GraphState) -> str:
    return "approved" if state.get("approved") else "reject"

# Add to workflow
workflow.add_node("generate", generate)
workflow.add_node("human_review", human_review)

workflow.set_entry_point("generate")
workflow.add_edge("generate", "human_review")

workflow.add_conditional_edges(
    "human_review",
    should_approve,
    {
        "approved": END,
        "reject": "generate"  # Loop back for regeneration
    }
)
```

## Jetson-Specific Examples

### System Monitoring Agent

```python
import subprocess
from langgraph.graph import StateGraph, END
from typing import TypedDict

class MonitorState(TypedDict):
    cpu_threshold: float
    gpu_threshold: float
    status: str
    actions: list

def check_system(state: MonitorState) -> MonitorState:
    # Check CPU
    result = subprocess.run(["cat", "/proc/stat"], capture_output=True, text=True)
    # Simplified check - in production use proper metrics
    return {"status": "checked", "actions": state.get("actions", []) + ["check_system"]}

def recommend_action(state: MonitorState) -> MonitorState:
    response = llm.invoke(
        f"Given system status: {state['status']}, "
        f"CPU threshold: {state['cpu_threshold']}, "
        f"GPU threshold: {state['gpu_threshold']}, "
        "What action should be taken?"
    )
    return {"actions": state.get("actions", []) + [response.content]}

workflow = StateGraph(MonitorState)
workflow.add_node("check", check_system)
workflow.add_node("recommend", recommend_action)
workflow.set_entry_point("check")
workflow.add_edge("check", "recommend")
workflow.add_edge("recommend", END)

app = workflow.compile()

result = app.invoke({
    "cpu_threshold": 80.0,
    "gpu_threshold": 90.0,
    "status": "",
    "actions": []
})

print(result['actions'])
```

## Next Steps

- [RAG Automation](./09-rag-automation.md)
- [Tools & Functions](./10-tools-functions.md)
