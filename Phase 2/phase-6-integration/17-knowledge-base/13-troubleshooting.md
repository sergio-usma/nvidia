# Troubleshooting

## Common Issues

### Out of Memory

```bash
# Reduce chunk size
chunk_size=200

# Use smaller embedding model
model="embeddinggemma:latest"

# Clear memory
import gc
gc.collect()
```

### Slow Retrieval

```python
# Use smaller k
k=3  # instead of 10

# Use FAISS instead of Chroma
vectorstore = FAISS.from_documents(chunks, embeddings)
```

### Connection Errors

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama
```

### Model Not Found

```bash
# Pull model
ollama pull nomic-embed-text:latest
ollama pull llama3.2:3b
```

## Performance Tips

- Use FAISS for faster search
- Reduce context window
- Use smaller embedding models
- Enable caching

## Getting Help

- LangChain docs
- Ollama GitHub
- NVIDIA Jetson forums
