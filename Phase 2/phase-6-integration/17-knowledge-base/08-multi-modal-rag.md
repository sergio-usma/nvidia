# Multi-Modal RAG

## Table of Contents

1. [Introduction](#introduction)
2. [Image Embeddings](#image-embeddings)
3. [Multi-Modal Retrieval](#multi-modal-retrieval)
4. [Implementation](#implementation)

## Introduction

Multi-modal RAG handles text, images, and other media types.

## Image Embeddings

```python
# Using CLIP for image-text embeddings
from transformers import CLIPProcessor, CLIPModel
import torch

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def embed_image(image_path):
    from PIL import Image
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
    return features.numpy()

def embed_text(text):
    inputs = processor(text=text, return_tensors="pt")
    with torch.no_grad():
        features = model.get_text_features(**inputs)
    return features.numpy()
```

## Multi-Modal Retrieval

```python
import chromadb
from PIL import Image

class MultiModalRAG:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("multimodal")
        self.image_dir = "./images"
    
    def add_image(self, image_path, text=None, metadata=None):
        import os
        image_id = os.path.basename(image_path)
        
        # Extract text from image using OCR
        if text is None:
            # Use pytesseract or similar
            text = "image description"
        
        self.collection.add(
            documents=[text],
            ids=[image_id],
            metadatas=[metadata or {"type": "image"}]
        )
    
    def search(self, query, n=3):
        results = self.collection.query(
            query_texts=[query],
            n_results=n
        )
        return results

# Usage
mm_rag = MultiModalRAG()
mm_rag.add_image("diagram.png", "Architecture diagram for Jetson system")
results = mm_rag.search("Jetson architecture")
```

## Implementation

```python
# Complete multi-modal pipeline
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2:3b")

def multimodal_rag(query, text_results, image_results):
    context = "Text context:\n" + "\n".join(text_results)
    context += "\n\nImage context:\n" + "\n".join(image_results)
    
    prompt = f"""Based on this multi-modal context, answer:

Question: {query}

Context: {context}

Answer:"""
    
    return llm.invoke(prompt)
```

## Next Steps

- [Embedding Models](./09-embedding-models.md)
- [RAG Pipelines](./10-rag-pipelines.md)
