# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is an eBook authoring workspace for **"Getting Started with NVIDIA Jetson AGX Orin 64GB (JetPack 7.2)"** — a 300–500 page comprehensive technical guide targeting first-time Jetson users (developers, AI/ML engineers, robotics engineers).

**Target platform:** NVIDIA Jetson AGX Orin 64GB running JetPack 7.2 (L4T r39.2, Ubuntu 24.04, CUDA 13.2.1, Python 3.12, Kernel 6.8)

## Output Workflow

### Phase 1 — Consolidated Markdown
Write content to: `Jetson_AGX_Orin_JP72_Complete_Guide.md` (root of this directory)

### Phase 2 — DOCX Generation
Use the installed skill `/tutorial-docx` or invoke the builder directly:

```bash
# If skill is installed (via skill-tutorial-docx/install.sh):
/tutorial-docx Jetson_AGX_Orin_JP72_Complete_Guide.md

# Or run the builder script directly:
python3 skill-tutorial-docx/tutorial_docx_builder.py
```

The builder requires `python-docx>=1.1.0`. Install with:
```bash
pip3 install python-docx
# or: pip3 install -r skill-tutorial-docx/requirements.txt
```

Final DOCX output name: `Getting_Started_with_NVIDIA_Jetson_AGX_Orin_JP72.docx`

## Content Source Files

### Primary sources (must be fully integrated):
| File | Role |
|------|------|
| `jetson-orin-jp72-fresh-start.md` | Master checklist / skeleton for the entire book |
| `jetson-orin-jp72-GUIA-DEFINITIVA-v3.md` | Primary content — all verified commands and troubleshooting |
| `jetson-orin-jp72-DEFINITIVE-GUIDE.md` | Full agentic AI stack (Parts 12–15) |
| `jetson-orin-jp72-TOP10-MODELOS.md` | Model installation and benchmarking (Part 14) |

### Secondary sources (verification and context):
- `02-system-setup/*.md` — Modular topic guides; cross-check commands here
- `jetson-orin-jp72-agentic-ai-production.md` — Production deployment and monitoring
- `jetson-orin-jp72-openclaw-production-guide.md` — OpenClaw deep dive
- `jetson_agx_orin_jp72_specs.html` — Hardware specifications (authoritative)
- `jetson-orin-jetpack72-migration-guide.md` — JP 6.2 → JP 7.2 delta (critical for command accuracy)
- `jetson-orin-headless-definitive-guide-v2.md` — Headless/SSH/XRDP/NoMachine

## Book Structure (16 Parts + Appendix)

The book follows this chapter sequence. **Parts 12–15 (inference engines, agentic AI, model benchmarking, production) are the highest-priority deliverables** — write these first, then fill in earlier chapters.

| Part | Topic |
|------|-------|
| 0 | Introduction & hardware specs |
| 1 | Initial setup & first boot |
| 2 | Base system configuration |
| 3 | Performance tuning (nvpmodel, jetson_clocks) |
| 4 | Memory & storage (swap, ZRAM, NVMe) |
| 5 | Shell & dev environment (.bashrc, aliases, Git) |
| 6 | Network optimization (sysctl, BBR, DNS-over-TLS) |
| 7 | Remote access & headless (SSH, XRDP, NoMachine) |
| 8 | Docker & NVIDIA Container Toolkit |
| 9 | USB device configuration |
| 10 | Boot configuration & optimization |
| 11 | Python & AI framework setup (PyTorch, CUDA 13) |
| 12 | Inference engines (Ollama, llama.cpp, vLLM) |
| 13 | Agentic AI stack (OpenClaw, NemoClaw, Open WebUI) |
| 14 | LLM model testing & benchmarking (Top 10 models) |
| 15 | Production deployment (hardening, watchdogs, UFW) |
| 16 | Troubleshooting & best practices |
| Appendix | Quick-reference commands, port maps, aliases |

## Content Standards

### Command verification tagging
Every command must be tagged:
- `[VERIFIED ON JP 7.2]` — confirmed working
- `[TESTED ON JP 6.2]` — likely works, verify
- `[NEEDS VERIFICATION]` — syntax may have changed

### Critical JP 6.2 → JP 7.2 changes to watch for
| Component | JP 6.2 | JP 7.2 |
|-----------|--------|--------|
| Ubuntu | 22.04 | **24.04** |
| Python | 3.10 | **3.12** |
| CUDA | 12.6 | **13.2.1** |
| L4T | r36.5 | **r39.2** |
| Kernel | 5.15 | **6.8** |
| PyTorch wheel path | `jp/v61` | `jp/v72` |

### Writing rules
- Audience assumes zero prior knowledge — explain every concept (kernel, systemd, venv, swap, container)
- Every command must include expected output
- Every failure point must include error message → cause → fix
- Include time estimates (e.g., "takes 3–5 minutes")
- Cross-reference sections by number when steps depend on previous steps
- Use `sudo` warnings for privileged commands
- Language: Spanish narrative text; commands/code stay in English/bash
- Verb form: "Ejecute", "Verifique", "Configure" (formal usted) — keep consistent throughout
- Mark Docker GPU verification with `nvcc --version` (NOT `nvidia-smi` — not available on Jetson)
- System update: always `apt update && apt upgrade -y`, NEVER `dist-upgrade` on Jetson

## DOCX Skill (`/tutorial-docx`)

### Install
```bash
cd skill-tutorial-docx/
bash install.sh
```

### Usage in Claude Code session
```
/tutorial-docx /path/to/file.md
```

### Content dict structure
The builder accepts a Python `content` dict with keys: `title`, `subtitle`, `version`, `date`, `specs`, `chapters[]`, `appendices[]`. Each chapter has `sections[]` with typed blocks: `body`, `subsection`, `step`, `code`, `output`, `callout`, `table`, `bullets`.

Callout types: `IMPORTANTE | NOTA | CONSEJO | ADVERTENCIA | ATENCIÓN`

Color palette: cover teal `#0F3D3D`, accent `#1D9CB8`, table header `#1A5A6A`, code bg `#1A2233`

### Script execution path
The generated script imports from `~/.claude/tutorial_docx_builder.py` (installed by `install.sh`). If running on Windows, adjust the path accordingly or run from the `skill-tutorial-docx/` directory directly.

## Divide-and-Conquer Strategy

For long-session writing tasks, work chapter-by-chapter and append to the master file incrementally. Start with Parts 12–14 (the urgent priority), then Parts 0–11 and 15–16. Use the `jetson-orin-jp72-GUIA-DEFINITIVA-v3.md` and `jetson-orin-jp72-TOP10-MODELOS.md` as the primary content source for those sections.
