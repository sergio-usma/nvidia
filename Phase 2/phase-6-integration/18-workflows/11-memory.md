# Memory Management

## Table of Contents

1. [Introduction](#introduction)
2. [Conversation Memory](#conversation-memory)
3. [Persistent Storage](#persistent-storage)
4. [Memory Strategies](#memory-strategies)

## Introduction

Memory enables AI agents to maintain context across conversations. On Jetson, we implement various memory strategies optimized for ARM64.

## Conversation Memory

### Buffer Memory

```python
from langchain.memory import ConversationBufferMemory
from langchain_ollama import ChatOllama
from langchain.chains import ConversationChain

llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

memory = ConversationBufferMemory(
    memory_key="history",
    return_messages=True
)

conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# Chat
conversation.invoke("Hi, I'm using a Jetson AGX Orin")
conversation.invoke("What models can I run on it?")
conversation.invoke("How much memory does it have?")

# Get history
print(memory.load_memory_variables({}))
```

### Windowed Memory

```python
from langchain.memory import ConversationBufferWindowMemory

# Keep only last k exchanges
memory = ConversationBufferWindowMemory(
    k=3,  # Last 3 exchanges
    memory_key="history",
    return_messages=True
)

# Works same as buffer but limits history
```

### Token Memory

```python
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import Ollama

llm = Ollama(model="llama3.2:3b")

# Limit by token count instead of messages
memory = ConversationTokenBufferMemory(
    llm=llm,
    max_token_limit=1000,
    memory_key="history",
    return_messages=True
)
```

## Persistent Storage

### SQLite Memory

```python
from langchain.memory import SQLiteEntityStore
from langchain.memory import ConversationEntityMemory

# Entity memory with SQLite persistence
entity_store = SQLiteEntityStore(
    db_file="memory_entities.db"
)

memory = ConversationEntityMemory(
    llm=llm,
    entity_store=entity_store,
    k=5
)

# Entities are automatically persisted
memory.save_context(
    {"input": "My name is Sergio"},
    {"output": "Nice to meet you, Sergio!"}
)
```

### Redis Memory

```python
from langchain.memory import RedisChatMessageHistory

# Requires Redis running
message_history = RedisChatMessageHistory(
    url="redis://localhost:6379",
    session_id="user-session-123"
)

memory = ConversationBufferMemory(
    message_history=message_history,
    memory_key="history",
    return_messages=True
)
```

### File-Based Memory

```python
import json
from langchain.memory import Memory

class FileMemory(Memory):
    def load_memory_variables(self, inputs):
        try:
            with open("conversation_history.json", "r") as f:
                history = json.load(f)
        except:
            history = []
        return {"history": history}
    
    def save_context(self, inputs, outputs):
        try:
            with open("conversation_history.json", "r") as f:
                history = json.load(f)
        except:
            history = []
        
        history.append({
            "input": inputs.get("input", ""),
            "output": outputs.get("output", "")
        })
        
        with open("conversation_history.json", "w") as f:
            json.dump(history, f)
    
    def clear(self):
        with open("conversation_history.json", "w") as f:
            json.dump([], f)

memory = FileMemory()
```

## Memory Strategies

### Summary Memory

```python
from langchain.memory import ConversationSummaryMemory

memory = ConversationSummaryMemory(
    llm=llm,
    memory_key="summary",
    return_messages=True
)

# LLM summarizes older messages
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# After many exchanges, older messages get summarized
for i in range(10):
    conversation.invoke(f"Message {i}")
```

### Multi-User Memory

```python
class MultiUserMemory:
    def __init__(self):
        self.memories = {}
    
    def get_memory(self, user_id: str):
        if user_id not in self.memories:
            self.memories[user_id] = ConversationBufferMemory(
                memory_key="history",
                return_messages=True
            )
        return self.memories[user_id]
    
    def chat(self, user_id: str, message: str):
        memory = self.get_memory(user_id)
        conversation = ConversationChain(llm=llm, memory=memory)
        return conversation.invoke(message)

# Usage
multi_mem = MultiUserMemory()
multi_mem.chat("user1", "I like Llama models")
multi_mem.chat("user2", "I prefer Mistral")
```

### Vector Store Memory

```python
from langchain.memory import VectorStoreRetrieverMemory
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import FAISS

embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Create in-memory vector store for memories
memory_store = FAISS.from_texts(
    ["Initial context"],
    embeddings
)

retriever = memory_store.as_retriever(search_kwargs={"k": 2})

memory = VectorStoreRetrieverMemory(
    retriever=retriever,
    memory_key="prior_context"
)

# Save context
memory.save_context(
    {"input": "User likes CUDA programming"},
    {"output": "Noted preference for CUDA"}
)

# Recall relevant context
print(memory.load_memory_variables({}))
```

### Hybrid Memory

```python
from langchain.memory import CombinedMemory

# Combine multiple memory types
buffer_memory = ConversationBufferMemory(
    memory_key="buffer",
    return_messages=True
)

summary_memory = ConversationSummaryMemory(
    llm=llm,
    memory_key="summary",
    return_messages=True
)

memory = CombinedMemory(
    memories=[buffer_memory, summary_memory]
)

conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)
```

### Jetson-Specific: Persistent Session

```python
import os
import json
from datetime import datetime

class JetsonPersistentMemory:
    def __init__(self, session_id: str, storage_dir: str = "./memory"):
        self.session_id = session_id
        self.storage_dir = storage_dir
        self.memory_file = f"{storage_dir}/{session_id}.json"
        
        os.makedirs(storage_dir, exist_ok=True)
        self.load()
    
    def load(self):
        try:
            with open(self.memory_file, "r") as f:
                self.data = json.load(f)
        except:
            self.data = {
                "created": datetime.now().isoformat(),
                "messages": [],
                "entities": {}
            }
    
    def save(self):
        with open(self.memory_file, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def add_message(self, role: str, content: str):
        self.data["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.save()
    
    def add_entity(self, key: str, value: str):
        self.data["entities"][key] = value
        self.save()
    
    def get_context(self) -> str:
        recent = self.data["messages"][-5:]
        return "\n".join([f"{m['role']}: {m['content']}" for m in recent])
    
    def clear(self):
        self.data["messages"] = []
        self.save()

# Usage
session = JetsonPersistentMemory("jetson-session-001")
session.add_message("user", "I need help with CUDA")
session.add_message("assistant", "I'll help you with CUDA on Jetson")
print(session.get_context())
```

## Memory Optimization for Jetson

```python
import gc

def optimize_memory():
    """Clear memory on Jetson between conversations."""
    gc.collect()
    
    # If using CUDA/torch
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except:
        pass

class OptimizedConversation:
    def __init__(self):
        self.llm = ChatOllama(model="llama3.2:3b")
        self.memory = ConversationBufferMemory(
            memory_key="history",
            max_token_limit=500  # Limit to save memory
        )
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory
        )
    
    def chat(self, message: str):
        response = self.conversation.invoke(message)
        
        # Periodically optimize
        if len(self.memory.chat_memory.messages) > 20:
            optimize_memory()
        
        return response
```

## Next Steps

- [Ollama Agents](./12-ollama-agents.md)
- [Troubleshooting](./13-troubleshooting.md)
