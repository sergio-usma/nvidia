# Part 12: Hands-On Advanced AI Projects

This section contains advanced, production-ready AI applications that leverage local LLM capabilities for complex tasks.

## Hardware Requirements

These projects are optimized for:
- **Jetson AGX Orin 64GB** (recommended)
- **Orin Nano/Pro** (with reduced models)
- Minimum 16GB RAM for some projects

## Supported LLM Backends

All projects support multiple backends:
- **Ollama** - Local inference server
- **LM Studio** - Alternative local GUI
- **llama.cpp** - Pure C++ inference
- **MLC-LLM** - High-performance deployment

---

## Project Overview

| Project | Description | Complexity |
|---------|-------------|------------|
| [01-super-rag](01-super-rag.md) | Enterprise RAG with file processing, structured outputs, fine-tuning datasets | ⭐⭐⭐⭐⭐ |
| [02-multi-agent-writing](02-multi-agent-writing.md) | Multi-agent system for academic writing | ⭐⭐⭐⭐ |
| [03-n8n-calendar-telegram](03-n8n-calendar-telegram.md) | n8n workflow with Google Calendar + Telegram | ⭐⭐⭐ |
| [04-langchain-agent](04-langchain-agent.md) | LangChain agent with local LLM | ⭐⭐⭐ |
| [05-math-tutor-agent](05-math-tutor-agent.md) | Calculus teaching with visualizations | ⭐⭐⭐⭐ |

---

## Prerequisites

Before starting any project:

1. ✅ Complete [Part 1: System Setup](../part-1-system-setup/)
2. ✅ Install [Ollama](../part-5-llms/01-ollama-setup.md) or configure preferred LLM backend
3. ✅ Complete [Python Environment](../part-3-python-environment/)
4. ✅ Install [Docker](../part-2-docker/) for containerized services

---

## LLM Configuration

Each project can use different LLM backends. Configure in each project:

```bash
# Default: Ollama
export LLM_BACKEND=ollama
export OLLAMA_BASE_URL=http://localhost:11434

# Alternative: LM Studio
export LLM_BACKEND=lmstudio
export LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Alternative: llama.cpp
export LLM_BACKEND=llamacpp
export LLAMACPP_BASE_URL=http://localhost:8080

# Alternative: MLC-LLM
export LLM_BACKEND=mlc
export MLC_BASE_URL=http://localhost:8000/v1
```

---

## Quick Start

### Project 1: Super RAG
Best for: Document processing, knowledge management, creating training data

### Project 2: Multi-Agent Writing
Best for: Academic research, content generation, automated writing

### Project 3: n8n Calendar + Telegram
Best for: Calendar management, voice commands, automation

### Project 4: LangChain Agent
Best for: Conversational AI, tool use, chain-of-thought reasoning

### Project 5: Math Tutor
Best for: Education, step-by-step problem solving, visualization

---

## Common Dependencies

```bash
# Core dependencies for all projects
pip3 install requests python-dotenv pydantic

# For RAG and embeddings
pip3 install langchain langchain-community chromadb sentence-transformers

# For document processing
pip3 install pypdf python-docx python-pptx whisper

# For agents
pip3 install langgraph crewai autogen

# For n8n integration
pip3 install n8n-api-client google-api-python-client

# For math and visualization
pip3 install numpy matplotlib sympy
```

---

## Performance Notes

| Project | Recommended Model | RAM Usage | GPU Required |
|---------|------------------|-----------|--------------|
| Super RAG | llama3.2 (7B) | 16GB+ | Yes |
| Multi-Agent Writing | llama3.2 (7B) | 16GB+ | Yes |
| n8n Workflow | llama3.1 (3B) | 8GB | Optional |
| LangChain Agent | llama3.2 (7B) | 12GB+ | Yes |
| Math Tutor | mathstral (7B) | 16GB+ | Yes |

---

## Project Tips

1. **Start small** - Test with small documents first
2. **Monitor resources** - Use `jtop` to watch GPU/RAM
3. **Incremental development** - Build one component at a time
4. **Persist data** - All projects include database/storage
5. **Error handling** - Implement retries for API calls

---

## Support & Troubleshooting

- Check logs in each project's `logs/` directory
- Verify LLM backend is running before starting projects
- Ensure sufficient disk space for processed documents
- Review AGENTS.md for hardware-specific optimizations

---

## Next Steps

After completing these projects, consider:
- [Part 11: Production Projects](../part-11-projects/) for deployment patterns
- Custom fine-tuning with generated datasets
- Multi-device clustering for scaling

Good luck with your advanced AI projects!
