# Complete RAG Pipelines

## Table of Contents

1. [Basic Pipeline](#basic-pipeline)
2. [Advanced Pipeline](#advanced-pipeline)
3. [Production Pipeline](#production-pipeline)

## Basic Pipeline

```python
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# 1. Load documents
loader = TextLoader("docs.txt")
documents = loader.load()

# 2. Split text
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(documents)

# 3. Create embeddings and vector store
embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
vectorstore = FAISS.from_documents(chunks, embeddings)

# 4. Create retriever
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 5. Create QA chain
llm = ChatOllama(model="llama3.2:3b", temperature=0.3)
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# 6. Query
result = qa_chain.invoke({"query": "Your question here"})
print(result["result"])
```

## Advanced Pipeline

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

class AdvancedRAG:
    def __init__(self, documents):
        # Split documents
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500)
        self.chunks = self.splitter.split_documents(documents)
        
        # Embeddings
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
        
        # Vector store
        self.vectorstore = FAISS.from_documents(self.chunks, self.embeddings)
        
        # BM25 retriever
        self.bm25 = BM25Retriever.from_documents(self.chunks)
        
        # Vector retriever
        self.vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        
        # Ensemble
        self.ensemble = EnsembleRetriever(
            retrievers=[self.bm25, self.vector_retriever],
            weights=[0.3, 0.7]
        )
        
        # LLM
        self.llm = ChatOllama(model="llama3.2:3b", temperature=0.3)
    
    def query(self, question):
        # Retrieve
        docs = self.ensemble.invoke(question)
        
        # Build context
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Generate
        prompt = f"""Context: {context}\n\nQuestion: {question}\n\nAnswer:"""
        response = self.llm.invoke(prompt)
        
        return {
            "answer": response.content,
            "sources": [doc.metadata for doc in docs]
        }

# Usage
rag = AdvancedRAG(documents)
result = rag.query("Your question")
```

## Production Pipeline

```python
import os
import json
from datetime import datetime

class ProductionRAG:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.vectorstore = None
        self.llm = ChatOllama(model="qwen2.5-coder:latest", temperature=0.3)
        self._load_or_build()
    
    def _load_or_build(self):
        index_path = os.path.join(self.data_dir, "faiss_index")
        
        if os.path.exists(index_path):
            embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
            self.vectorstore = FAISS.load_local(
                index_path, embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            self._build_index()
    
    def _build_index(self):
        # Load all documents
        documents = []
        for f in os.listdir(self.data_dir):
            if f.endswith(".txt"):
                loader = TextLoader(os.path.join(self.data_dir, f))
                documents.extend(loader.load())
        
        # Build index
        splitter = RecursiveCharacterTextSplitter(chunk_size=500)
        chunks = splitter.split_documents(documents)
        
        embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
        self.vectorstore = FAISS.from_documents(chunks, embeddings)
        
        # Save
        self.vectorstore.save_local(os.path.join(self.data_dir, "faiss_index"))
    
    def query(self, question, return_sources=True):
        docs = self.vectorstore.similarity_search(question, k=5)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
        response = self.llm.invoke(prompt)
        
        result = {"answer": response.content}
        
        if return_sources:
            result["sources"] = [{"source": doc.metadata.get("source", "unknown")} 
                                for doc in docs]
        
        return result

# API Server
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/query", methods=["POST"])
def query_endpoint():
    data = request.json
    result = rag.query(data["question"])
    return jsonify(result)

if __name__ == "__main__":
    rag = ProductionRAG("./knowledge_base")
    app.run(host="0.0.0.0", port=5000)
```

## Next Steps

- [Evaluation](./11-evaluation.md)
- [Production](./12-production.md)
- [Troubleshooting](./13-troubleshooting.md)
