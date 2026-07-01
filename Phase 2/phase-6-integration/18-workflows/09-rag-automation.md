# RAG Automation

## Table of Contents

1. [Introduction](#introduction)
2. [Document Processing](#document-processing)
3. [Vector Store Management](#vector-store-management)
4. [Query Automation](#query-automation)
5. [Scheduled RAG](#scheduled-rag)

## Introduction

RAG (Retrieval-Augmented Generation) automation enables AI applications to query your documents and knowledge bases on Jetson.

## Document Processing

### Multi-Format Loader

```python
from langchain_community.document_loaders import (
    TextLoader,
    PDFLoader,
    CSVLoader,
    DirectoryLoader,
    UnstructuredURLLoader
)

def load_documents(source: str, source_type: str = "text"):
    if source_type == "pdf":
        loader = PDFLoader(source)
    elif source_type == "csv":
        loader = CSVLoader(source)
    elif source_type == "directory":
        loader = DirectoryLoader(source, glob="**/*.txt")
    elif source_type == "url":
        loader = UnstructuredURLLoader([source])
    else:
        loader = TextLoader(source)
    
    return loader.load()

# Load multiple sources
docs = []
docs.extend(load_documents("jetson_guide.txt", "text"))
docs.extend(load_documents("technical_specs.pdf", "pdf"))
```

### Document Chunking

```python
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter
)

# Standard chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", " ", ""]
)

chunks = text_splitter.split_documents(docs)

# Markdown-aware chunking
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on
)

md_chunks = markdown_splitter.split_text(markdown_text)
```

## Vector Store Management

### Create Vector Store

```python
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import FAISS

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

def create_vectorstore(documents, store_name="vectorstore"):
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embeddings
    )
    vectorstore.save_local(store_name)
    return vectorstore

# Create store
vs = create_vectorstore(chunks, "jetson_knowledge")
```

### Load Vector Store

```python
def load_vectorstore(store_name="jetson_knowledge"):
    return FAISS.load_local(
        store_name,
        embeddings,
        allow_dangerous_deserialization=True
    )

vs = load_vectorstore()
retriever = vs.as_retriever(search_kwargs={"k": 4})
```

### Update Vector Store

```python
def add_to_vectorstore(new_documents, store_name="jetson_knowledge"):
    vs = load_vectorstore(store_name)
    vs.add_documents(new_documents)
    vs.save_local(store_name)
    return vs

# Add new documents
new_docs = load_documents("new_article.txt")
add_to_vectorstore(new_docs)
```

## Query Automation

### Automated RAG Chain

```python
from langchain_ollama import ChatOllama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

def create_rag_chain(vectorstore):
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    
    prompt = PromptTemplate(
        template="""Use the following context to answer the question.
        
Context: {context}

Question: {question}

Provide a detailed answer based on the context.""",
        input_variables=["context", "question"]
    )
    
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )

# Use chain
vs = load_vectorstore()
qa_chain = create_rag_chain(vs)

result = qa_chain.invoke({
    "query": "How do I optimize Jetson for inference?"
})

print(result['result'])
print("\nSources:")
for doc in result['source_documents']:
    print(f"- {doc.metadata.get('source', 'Unknown')}")
```

### Hybrid Search

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# BM25 retriever
bm25_retriever = BM25Retriever.from_texts(
    [doc.page_content for doc in chunks]
)
bm25_retriever.k = 3

# Vector retriever
vs_retriever = vs.as_retriever(search_kwargs={"k": 3})

# Combine
ensemble = EnsembleRetriever(
    retrievers=[bm25_retriever, vs_retriever],
    weights=[0.5, 0.5]
)

# Use in chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=ensemble,
    chain_type="stuff"
)
```

### Multi-Query RAG

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

def multi_query_rag(query, vectorstore):
    # Generate multiple queries
    llm_temp = ChatOllama(model="llama3.2:3b", temperature=0.7)
    
    query_generation_prompt = PromptTemplate(
        template="Generate 3 different versions of this question:\n{query}",
        input_variables=["query"]
    )
    
    queries = llm_temp.invoke(query_generation_prompt.format(query=query))
    query_list = queries.content.split("\n")[:3] + [query]
    
    # Retrieve for each query
    all_docs = []
    retriever = vectorstore.as_retriever()
    
    for q in query_list:
        docs = retriever.invoke(q)
        all_docs.extend(docs)
    
    # Deduplicate
    unique_docs = list({doc.page_content: doc for doc in all_docs}.values())
    
    # Answer
    context = "\n\n".join([doc.page_content for doc in unique_docs])
    
    answer_prompt = PromptTemplate(
        template="Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
        input_variables=["context", "question"]
    )
    
    answer = llm.invoke(answer_prompt.format(context=context, question=query))
    return answer.content, unique_docs
```

## Scheduled RAG

### Scheduled Knowledge Updates

```python
import schedule
import time
import threading
from datetime import datetime

class ScheduledRAG:
    def __init__(self):
        self.vectorstore = None
        self.qa_chain = None
        self.sources = ["doc1.txt", "doc2.pdf"]
    
    def update_knowledge(self):
        print(f"[{datetime.now()}] Updating knowledge base...")
        
        # Reload documents
        all_docs = []
        for source in self.sources:
            docs = load_documents(source)
            all_docs.extend(docs)
        
        # Recreate vectorstore
        chunks = text_splitter.split_documents(all_docs)
        self.vectorstore = create_vectorstore(chunks)
        self.qa_chain = create_rag_chain(self.vectorstore)
        
        print(f"[{datetime.now()}] Knowledge base updated")
    
    def start_scheduler(self):
        # Update every hour
        schedule.every().hour.do(self.update_knowledge)
        
        # Also update at specific times
        schedule.every().day.at("00:00").do(self.update_knowledge)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
    
    def query(self, question):
        if not self.qa_chain:
            self.update_knowledge()
        return self.qa_chain.invoke({"query": question})

# Usage
rag = ScheduledRAG()
rag.start_scheduler()
rag.update_knowledge()  # Initial load
```

### API Server with RAG

```python
from flask import Flask, request, jsonify

app = Flask(__name__)
rag_system = ScheduledRAG()
rag_system.update_knowledge()

@app.route("/query", methods=["POST"])
def query():
    data = request.json
    question = data.get("question")
    
    result = rag_system.query(question)
    
    return jsonify({
        "answer": result['result'],
        "sources": [doc.metadata for doc in result['source_documents']]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Webhook-Triggered RAG

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook/rag", methods=["POST"])
def rag_webhook():
    data = request.json
    query = data.get("query")
    sources = data.get("sources", [])  # Optional: specify sources
    
    if sources:
        # Load specific sources
        docs = []
        for src in sources:
            docs.extend(load_documents(src))
        chunks = text_splitter.split_documents(docs)
        vs = create_vectorstore(chunks)
    else:
        vs = load_vectorstore()
    
    qa = create_rag_chain(vs)
    result = qa.invoke({"query": query})
    
    return jsonify({
        "response": result['result'],
        "sources": result['source_documents']
    })
```

## Next Steps

- [Tools & Functions](./10-tools-functions.md)
- [Memory Management](./11-memory.md)
