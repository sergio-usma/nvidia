\# HARD-SPEC PROMPT: eBook "Getting Started with NVIDIA Jetson AGX Orin 64GB (JetPack 7.2)"



\---



\## TITLE \& TARGET AUDIENCE



\*\*Proposed Title:\*\* \*Getting Started with NVIDIA Jetson AGX Orin 64GB (JetPack 7.2) — A Comprehensive Step-by-Step Guide for First-Time Users\*



\*\*Target Audience:\*\*

\- Developers new to the NVIDIA Jetson ecosystem

\- AI/ML engineers setting up their first edge-AI workstation

\- Robotics and embedded systems developers

\- Anyone who has never used a Jetson device before



\*\*Tone:\*\* Professional, educational, ultra-detailed, assumption of zero prior knowledge



\---



\## CONTENT STRUCTURE (High-Level)



\### Part 0: Introduction

\- What is the NVIDIA Jetson AGX Orin 64GB?

\- Key hardware specifications (GPU, CPU, RAM, storage)

\- JetPack 7.2 explained (what it is, why it matters)

\- What you'll build: A fully functional AI workstation with agentic capabilities

\- Prerequisites: Hardware, cables, host machine requirements



\### Part 1: Initial Setup \& First Boot

\- Unboxing and connecting peripherals

\- Power supply requirements

\- First boot wizard (OEM configuration)

\- Setting up your user account

\- Connecting to your local network (WiFi vs Ethernet)



\### Part 2: Base System Configuration

\- Updating the system (apt update/upgrade — NOT dist-upgrade!)

\- Installing essential development tools

\- Setting up Python and virtual environments

\- Installing jetson-stats (jtop) for system monitoring

\- Verifying your installation



\### Part 3: Performance Tuning

\- Understanding power modes (nvpmodel)

\- Activating MAXN mode for maximum performance

\- Locking clocks with jetson\_clocks

\- Making performance settings permanent via systemd

\- Verifying performance with benchmarks

\- Thermal management and cooling considerations



\### Part 4: Memory \& Storage Optimization

\- Understanding unified memory architecture

\- Creating a large swap file (50GB recommended)

\- Configuring ZRAM for compression

\- Setting up NVMe SSD (if available)

\- Optimizing swappiness for LLM workloads

\- Moving HuggingFace cache to NVMe



\### Part 5: Shell \& Development Environment

\- Configuring \~/.bashrc with CUDA paths

\- Setting up aliases and functions for daily use

\- Installing and configuring Git

\- Setting up GitHub SSH keys

\- Configuring aria2 for fast downloads

\- Creating the project directory structure



\### Part 6: Network Optimization

\- Kernel parameter tuning (sysctl)

\- TCP buffer optimization for high-speed downloads

\- MTU configuration

\- APT download optimization

\- DNS configuration (Cloudflare with DNS-over-TLS)

\- Testing network performance (iperf3)



\### Part 7: Remote Access \& Headless Operation

\- SSH server setup and key-based authentication

\- Configuring static IP via NetworkManager

\- NoMachine for remote desktop access

\- XRDP for Windows Remote Desktop

\- Enabling headless mode (disabling Wayland, setting up Xorg dummy)

\- Configuring tmux for persistent sessions



\### Part 8: Docker \& NVIDIA Container Toolkit

\- Installing Docker (compatible version for JetPack 7.2)

\- NVIDIA Container Toolkit configuration

\- Setting Docker to use nvidia runtime by default

\- Verifying GPU access from containers

\- Mounting volumes for persistent data



\### Part 9: USB Device Configuration

\- Understanding USB ports (USB 3.2 Gen 2, USB-C, Micro-USB)

\- Disabling USB autosuspend for stable operation

\- udev rules for device permissions (cameras, serial devices)

\- Camera setup with v4l2-utils

\- USB storage auto-mounting via fstab



\### Part 10: Boot Configuration \& Optimization

\- Understanding the Jetson boot process (BootROM → MB1 → MB2 → UEFI → Kernel → systemd)

\- Accessing and using Recovery Mode

\- UEFI boot management with efibootmgr

\- Booting from external NVMe SSD

\- Optimizing boot time (disabling unnecessary services, systemd-analyze)

\- Secure Boot considerations



\### Part 11: Python \& AI Framework Setup

\- Creating Python virtual environments

\- Installing PyTorch for JetPack 7.2 (CUDA 13.2.1)

\- Installing torchvision (compiling from source)

\- Installing cuSPARSELt for CUDA 13

\- Verifying GPU access from Python

\- Testing with a simple PyTorch script



\### Part 12: Inference Engines

\- \*\*Ollama:\*\* Installation and configuration, network access, model management

\- \*\*llama.cpp:\*\* Building from source, GPU offload, GGUF model serving

\- \*\*vLLM:\*\* Running with NVIDIA containers, OpenAI-compatible API, tool calling support



\### Part 13: Agentic AI Stack

\- \*\*OpenClaw:\*\* Installation, configuration, WhatsApp channel setup, Web UI

\- \*\*NemoClaw:\*\* One-command installation (JetPack 7.2 native), security layer

\- \*\*Jetson Agent Skills:\*\* Memory optimization, model benchmarking, BSP customization

\- Open WebUI setup for chat interface

\- Integration patterns for n8n



\### Part 14: LLM Model Testing \& Benchmarking

\- Top 10 models for AGX Orin 64GB: installation commands, performance expectations

\- Model switching scripts

\- Benchmarking methodology (tok/s, latency, memory usage)

\- Integration with OpenClaw and Open WebUI



\### Part 15: Production Deployment

\- System hardening (OOM protection, restart policies)

\- Watchdog scripts for memory monitoring

\- Startup/recovery procedures

\- Power mode selection by workload

\- UFW firewall configuration



\### Part 16: Troubleshooting \& Best Practices

\- Common issues and solutions (OOM, ghost models, permission problems)

\- System recovery procedures

\- Security best practices

\- Maintenance routines



\### Appendix

\- Quick reference of all commands

\- Port mappings reference

\- Useful aliases summary

\- Directory structure reference

\- Troubleshooting flowchart



\---



\## HOW TO USE THE PROVIDED FILES



\### Primary Source Files (must be fully integrated):



1\. \*\*`jetson-orin-jp72-fresh-start.md`\*\* → This is the master checklist. Use it as the skeleton for the entire book. All steps should reference back to this.



2\. \*\*`jetson-orin-jp72-GUIA-DEFINITIVA-v3.md`\*\* → The most comprehensive guide. Contains all verified commands, troubleshooting, and patches. This is your primary content source.



3\. \*\*`jetson-orin-jp72-DEFINITIVE-GUIDE.md`\*\* → Focused on the full agentic AI stack (OpenClaw, NemoClaw, models). Use for Parts 12-15.



4\. \*\*`jetson-orin-jp72-TOP10-MODELOS.md`\*\* → Detailed model installation and benchmarking. Use for Part 14.



\### Secondary Source Files (for verification and context):



\- All files in `/02-system-setup/` → These are the modular guides that cover specific topics. Verify commands against these.



\- `jetson-orin-jp72-agentic-ai-production.md` → Production deployment details, monitoring, and troubleshooting.



\- `jetson-orin-jp72-openclaw-production-guide.md` → Deep dive into OpenClaw.



\- `jetson\_agx\_orin\_jp72\_specs.html` → Hardware specifications.



\- `jetson-orin-jetpack72-migration-guide.md` → What changed from JP 6.2 to JP 7.2. Useful for context.



\- `jetson-orin-headless-definitive-guide-v2.md` → Headless setup (SSH, XRDP, NoMachine).



\- All PDF and DOCX files → Cross-reference for command verification, especially regarding network optimization, swap, thermal management, and system verification.



\### Skill Reference:



The user has a `skill-tutorial-docx` folder containing:

\- `tutorial\_docx\_builder.py` → A Python script for building DOCX from Markdown.

\- `tutorial-docx.md` → The template structure for the DOCX builder.

\- `README.md`, `install.sh`, `requirements.txt` → Setup and usage instructions.



\*\*Use this skill to generate the final DOCX output.\*\*



\---



\## OUTPUT REQUIREMENTS



\### Phase 1: Consolidated Markdown (eBook Master Document)

\- Complete, production-ready Markdown containing ALL content from Parts 0-16 and Appendix.

\- All commands must be verified against JetPack 7.2 (L4T r39.2, Ubuntu 24.04, CUDA 13.2.1).

\- Code blocks must have proper language highlighting (`bash`, `python`, `json`, `sql`).

\- Tables for comparisons, references, and troubleshooting.

\- Internal links (TOC → sections).

\- Consistent heading hierarchy.

\- All commands must include expected output.

\- Explanations for every concept, assuming zero prior knowledge.



\### Phase 2: DOCX Output

\- Use the `tutorial\_docx\_builder.py` skill (provided in `skill-tutorial-docx/`) to generate a clean, production-ready DOCX.

\- Output must be named: `Getting\_Started\_with\_NVIDIA\_Jetson\_AGX\_Orin\_JP72.docx`

\- The DOCX must:

&#x20; - Include a professional title page

&#x20; - Have a table of contents

&#x20; - Use consistent heading styles (Heading 1-6)

&#x20; - Include code blocks with monospace formatting

&#x20; - Preserve all tables

&#x20; - Be paginated correctly for printing or PDF conversion

&#x20; - Include page numbers and headers/footers



\---



\## RESEARCH \& VERIFICATION REQUIREMENTS



\### Commands to Verify for JetPack 7.2 (Critical Changes from JP 6.2):



| Component | JP 6.2 | JP 7.2 | Verified? |

|-----------|--------|--------|-----------|

| Ubuntu | 22.04 LTS | \*\*24.04 LTS\*\* | ⚠️ Verify |

| Python | 3.10 | \*\*3.12\*\* | ⚠️ Verify |

| CUDA | 12.6 | \*\*13.2.1\*\* | ⚠️ Verify |

| L4T | r36.5 | \*\*r39.2\*\* | ⚠️ Verify |

| Kernel | 5.15 | \*\*6.8\*\* | ⚠️ Verify |

| PyTorch wheel URL | jp/v61 | \*\*jp/v72\*\* | ⚠️ Verify |

| NemoClaw | Not available | \*\*curl -fsSL nvidia.com/nemoclaw.sh \\| bash\*\* | ⚠️ Verify |

| vLLM container | `gemma4-jetson-orin` | \*\*New JP7 tag\*\* | ⚠️ Verify |



\### Missing Information to Research:



1\. \*\*PyTorch wheel URL\*\* for JetPack 7.2 (CUDA 13.2.1, Python 3.12):

&#x20;  - Verify: `https://developer.download.nvidia.cn/compute/redist/jp/v72/pytorch/`

&#x20;  - If not available: check `pypi.jetson-ai-lab.io/jp7/cu130/`

&#x20;  - Fallback: indicate that users should check NVIDIA CDN or use container



2\. \*\*vLLM container tag\*\* for JP 7.2:

&#x20;  - Search: `ghcr.io/nvidia-ai-iot/vllm:r39.2.tegra-aarch64-cu130-24.04`

&#x20;  - Check GitHub Packages for latest tags



3\. \*\*cuSPARSELt version\*\* for CUDA 13:

&#x20;  - Verify version: `libcusparse\_lt-linux-sbsa-0.7.1.0-archive.tar.xz`

&#x20;  - Check if newer version exists



4\. \*\*torchvision branch\*\* for PyTorch 2.x on CUDA 13:

&#x20;  - Verify branch: `v0.21.0` or compatible with installed PyTorch version



5\. \*\*NemoClaw\*\*:

&#x20;  - Verify command `curl -fsSL nvidia.com/nemoclaw.sh | bash` works on JP 7.2

&#x20;  - Document installation location and verification



6\. \*\*Jetson Agent Skills\*\*:

&#x20;  - Verify URLs: `https://github.com/NVIDIA-AI-IOT/jetson-device-skills`

&#x20;  - Verify requirements and installation steps



7\. \*\*NGC CLI\*\* for Cosmos Reason 2B:

&#x20;  - Verify version and download URL for arm64 (aarch64)

&#x20;  - Confirm step-by-step configuration



8\. \*\*Tiktoken encodings\*\* for GPT OSS 20B:

&#x20;  - Verify download URLs still valid

&#x20;  - Document alternative if URLs change



\### Testing Requirements:



\- All commands must be tested on actual AGX Orin with JP 7.2 if possible.

\- For each command, document:

&#x20; - Exact command to run

&#x20; - Expected output or success condition

&#x20; - Error messages and their solutions

&#x20; - Time estimate (e.g., "takes 3-5 minutes first time")



\---



\## SKILL \& AGENT CREATION REQUIREMENTS



\### Skill: `tutorial-docx-builder`



Based on the provided `skill-tutorial-docx` folder, create a skill that:



1\. \*\*Takes Markdown input\*\* (the consolidated eBook)

2\. \*\*Parses it\*\* into structured sections

3\. \*\*Generates a DOCX\*\* with:

&#x20;  - Professional title page

&#x20;  - Auto-generated TOC

&#x20;  - Consistent heading styles

&#x20;  - Code blocks with monospace formatting

&#x20;  - Tables preserved

&#x20;  - Page numbers

&#x20;  - Proper margins and spacing



4\. \*\*Command-line interface\*\*:

&#x20;  ```bash

&#x20;  python tutorial\_docx\_builder.py input.md output.docx

&#x20;  ```



\### Agent: `ebook-research-agent`



An agent that can be called to:



1\. \*\*Verify commands\*\* against the actual hardware (through SSH or simulation)

2\. \*\*Check URLs\*\* for Docker images, Git repos, and download links

3\. \*\*Test command sequences\*\* in the correct order

4\. \*\*Report discrepancies\*\* between the documentation and actual behavior

5\. \*\*Suggest corrections\*\* based on findings



\### Agent: `tutorial-qa-agent`



An agent that can:



1\. \*\*Answer user questions\*\* about the tutorial content

2\. \*\*Explain concepts\*\* in more detail when asked

3\. \*\*Provide troubleshooting help\*\* for common issues

4\. \*\*Suggest alternative approaches\*\* based on user's hardware/software

5\. \*\*Generate quick reference cards\*\* from the tutorial content



\---



\## DETAILED CHAPTER BREAKDOWN



\### Part 0: Introduction (10-15 pages)



\- \*\*0.1\*\* What is NVIDIA Jetson? (Brief history, ecosystem)

\- \*\*0.2\*\* AGX Orin 64GB hardware specifications (in table format)

&#x20; - GPU, CPU, RAM, storage, connectivity, power

\- \*\*0.3\*\* What is JetPack 7.2? (Components: Ubuntu 24.04, CUDA 13.2.1, cuDNN, TensorRT, L4T r39.2)

\- \*\*0.4\*\* What you will build (A fully functional AI workstation + agentic AI system)

\- \*\*0.5\*\* Prerequisites

&#x20; - Hardware needed: Jetson, power supply, USB keyboard/mouse, monitor, Ethernet cable, USB-C cable

&#x20; - Software needed: Windows/Linux/Mac host for SSH, browser, terminal

&#x20; - Optional: NVMe SSD, USB camera, microphone

\- \*\*0.6\*\* Safety warnings (power, heat, ESD)



\### Part 1: Initial Setup \& First Boot (10-15 pages)



\- \*\*1.1\*\* Unboxing (what's in the box)

\- \*\*1.2\*\* Connecting peripherals (monitor, keyboard, mouse)

\- \*\*1.3\*\* Power supply (60W USB-C PD required)

\- \*\*1.4\*\* First boot wizard (OEM configuration step-by-step)

&#x20; - Language, timezone, keyboard layout

&#x20; - Creating the user account

&#x20; - Accepting NVIDIA licenses

\- \*\*1.5\*\* Post-boot verification (checking the desktop, opening terminal)

\- \*\*1.6\*\* Connecting to the internet (WiFi vs Ethernet)

\- \*\*1.7\*\* Finding your IP address



\### Part 2: Base System Configuration (15-20 pages)



\- \*\*2.1\*\* Understanding terminal basics (sudo, apt, pip)

\- \*\*2.2\*\* Updating the system (apt update \&\& apt upgrade -y)

&#x20; - Why NOT to use dist-upgrade on Jetson

\- \*\*2.3\*\* Installing essential tools (git, build-essential, cmake, Python3, pip, etc.)

&#x20; - Full command with explanation

&#x20; - What each package does

\- \*\*2.4\*\* Setting up Python virtual environments

&#x20; - Why venv is needed (Ubuntu 24.04 has protected system Python)

&#x20; - Creating `\~/venvs/llm`

&#x20; - Activating/deactivating virtual environments

\- \*\*2.5\*\* Installing and using jtop (jetson-stats)

&#x20; - Installation

&#x20; - Navigating jtop (tabs: 1-6, q to quit)

&#x20; - Understanding the dashboard

\- \*\*2.6\*\* Verification script (`\~/verify\_system.sh`)

&#x20; - Expected outputs for JetPack 7.2



\### Part 3: Performance Tuning (12-18 pages)



\- \*\*3.1\*\* Understanding power modes (nvpmodel)

&#x20; - MODE\_15W, MODE\_30W, MODE\_50W, MAXN

&#x20; - When to use each mode

&#x20; - Electricity cost table

\- \*\*3.2\*\* Activating MAXN mode (`sudo nvpmodel -m 0`)

\- \*\*3.3\*\* Locking clocks (`sudo jetson\_clocks`)

\- \*\*3.4\*\* Making performance settings permanent (systemd service)

\- \*\*3.5\*\* Power mode aliases (`pwr-15w`, `pwr-30w`, `pwr-maxn`, `pwr-status`)

\- \*\*3.6\*\* Thermal management

&#x20; - Normal temperatures (CPU/GPU/Board)

&#x20; - Thermal throttling prevention

&#x20; - Fan control (manual vs automatic)

&#x20; - Creating a cooling curve



\### Part 4: Memory \& Storage Optimization (12-18 pages)



\- \*\*4.1\*\* Unified memory architecture explained

&#x20; - CPU and GPU share the 64GB pool

&#x20; - The problem with OOM (system freezes, not just process death)

\- \*\*4.2\*\* Disabling ZRAM

\- \*\*4.3\*\* Creating a 50GB swap file (on NVMe SSD)

&#x20; - Using fallocate

&#x20; - Setting permissions

&#x20; - Formatting with mkswap

&#x20; - Activating with swapon

\- \*\*4.4\*\* Making swap permanent (fstab)

\- \*\*4.5\*\* Tuning swappiness (`vm.swappiness=10`)

\- \*\*4.6\*\* Moving HuggingFace cache to NVMe (`HF\_HOME`)

\- \*\*4.7\*\* Checking swap usage and effectiveness

\- \*\*4.8\*\* Removing swap (if needed)



\### Part 5: Shell \& Development Environment (10-15 pages)



\- \*\*5.1\*\* The .bashrc file (what it is, why it matters)

\- \*\*5.2\*\* Full production .bashrc block (with explanations for each section)

&#x20; - CUDA paths

&#x20; - TensorRT/Tegra libraries

&#x20; - Build flags (MAKEFLAGS, CMAKE\_BUILD\_PARALLEL\_LEVEL)

&#x20; - HuggingFace acceleration (HF\_TRANSFER, HF\_HOME)

&#x20; - Ollama configuration

&#x20; - Python virtual environment helpers (`ai`, `da`)

&#x20; - Performance aliases (`maxn`, `powersave`, `perf`)

&#x20; - Monitoring aliases (`stats`, `temps`, `memfree`, `gpucheck`)

&#x20; - Docker GPU shortcuts (`drun`, `ollama`)

&#x20; - File system aliases

&#x20; - System maintenance aliases

&#x20; - Git shortcuts

&#x20; - Deduplicate PATH

&#x20; - Custom PS1 prompt (optional)

\- \*\*5.3\*\* Applying and verifying changes (`source \~/.bashrc`)

\- \*\*5.4\*\* Git configuration

\- \*\*5.5\*\* GitHub SSH key setup

&#x20; - Generating keys on Jetson

&#x20; - Adding to GitHub account

&#x20; - Testing with `ssh -T git@github.com`

\- \*\*5.6\*\* aria2 configuration

&#x20; - Creating `\~/.config/aria2/aria2.conf`

&#x20; - Usage examples

\- \*\*5.7\*\* Project directory structure



\### Part 6: Network Optimization (10-15 pages)



\- \*\*6.1\*\* Why network optimization matters (downloading models, Docker images)

\- \*\*6.2\*\* Kernel parameter tuning (sysctl)

&#x20; - TCP buffers (rmem\_max, wmem\_max)

&#x20; - BBR congestion control

&#x20; - TCP window scaling, fast open, SACK

&#x20; - Disabling IPv6 (if not needed)

&#x20; - Full `99-jetson-network.conf` file

&#x20; - Applying with `sudo sysctl -p`

\- \*\*6.3\*\* MTU configuration (Jumbo Frames for local network)

\- \*\*6.4\*\* Ethernet offloads (TSO, GRO, GSO, LRO)

\- \*\*6.5\*\* Ring buffers (RX/TX)

\- \*\*6.6\*\* APT optimization (`Acquire::Queue-Mode="access"`, `Acquire::Retries=5`)

\- \*\*6.7\*\* DNS optimization (Cloudflare with DNS-over-TLS)

&#x20; - Configuring `/etc/systemd/resolved.conf`

&#x20; - Using `resolvectl` to verify

\- \*\*6.8\*\* Testing network performance (iperf3, speedtest-cli)

\- \*\*6.9\*\* Automation script (`jetson-net-setup.sh`)



\### Part 7: Remote Access \& Headless Operation (12-18 pages)



\- \*\*7.1\*\* Enabling SSH server

&#x20; - Installation, configuration, start

\- \*\*7.2\*\* Setting up SSH keys from Windows

&#x20; - Generating key on Windows

&#x20; - Copying to Jetson

&#x20; - Disabling password authentication after key works

\- \*\*7.3\*\* SSH config file on Windows

\- \*\*7.4\*\* Static IP via NetworkManager

&#x20; - Critical: `connection.permissions ""` to allow network without GUI login

\- \*\*7.5\*\* tmux for persistent sessions

&#x20; - Installation and configuration

&#x20; - Commands: attach, detach, new session

\- \*\*7.6\*\* Disabling Wayland (for XRDP compatibility)

&#x20; - Editing `/etc/gdm3/custom.conf`

\- \*\*7.7\*\* Xorg dummy driver (virtual display 1920x1080)

\- \*\*7.8\*\* XRDP setup

&#x20; - Installation

&#x20; - `startwm.sh` fix (critical for Ubuntu 24.04)

&#x20; - Polkit rules for colord

&#x20; - Testing with Windows mstsc

\- \*\*7.9\*\* NoMachine setup

&#x20; - Downloading DEB for arm64

&#x20; - Installation and configuration

&#x20; - Connecting from Windows

\- \*\*7.10\*\* XFCE4 alternative (if GNOME has issues)



\### Part 8: Docker \& NVIDIA Container Toolkit (10-15 pages)



\- \*\*8.1\*\* Why Docker on Jetson

\- \*\*8.2\*\* Installing Docker (version 27.5.1 compatible with JetPack 6 kernel)

&#x20; - Using JetsonHacks scripts

&#x20; - Manual installation via apt

\- \*\*8.3\*\* Installing NVIDIA Container Toolkit

\- \*\*8.4\*\* Configuring Docker to use nvidia runtime by default

\- \*\*8.5\*\* Verifying GPU access from containers

&#x20; - Testing with `nvcc --version` in container

&#x20; - NOT `nvidia-smi` (not available on Jetson)

\- \*\*8.6\*\* Moving Docker storage to NVMe SSD

\- \*\*8.7\*\* Docker aliases (`drun`, `ollama`)

\- \*\*8.8\*\* Pruning old images (`docker image prune -a`)



\### Part 9: USB Device Configuration (8-12 pages)



\- \*\*9.1\*\* USB ports on AGX Orin

\- \*\*9.2\*\* Listing USB devices (`lsusb`)

\- \*\*9.3\*\* Understanding VID:PID

\- \*\*9.4\*\* Disabling USB autosuspend

&#x20; - Immediate: writing to `/sys`

&#x20; - Permanent: udev rules

\- \*\*9.5\*\* udev rules for permissions

&#x20; - Cameras (video group)

&#x20; - Serial devices (dialout group)

\- \*\*9.6\*\* Camera setup with v4l2-utils

\- \*\*9.7\*\* USB storage auto-mounting (fstab with UUID)

&#x20; - Critical: `nofail` option

\- \*\*9.8\*\* Troubleshooting USB issues



\### Part 10: Boot Configuration \& Optimization (8-12 pages)



\- \*\*10.1\*\* Understanding the boot process (BootROM → MB1 → MB2 → UEFI → Kernel → systemd)

\- \*\*10.2\*\* Recovery Mode

&#x20; - How to enter

&#x20; - Verifying with `lsusb`

\- \*\*10.3\*\* UEFI boot management

&#x20; - `sudo efibootmgr -v`

&#x20; - Changing boot order (`-o`)

&#x20; - Disabling entries (`-B`)

\- \*\*10.4\*\* Booting from external NVMe SSD

&#x20; - Cloning rootfs to NVMe

&#x20; - Updating fstab with UUID

&#x20; - Making the system boot from NVMe

\- \*\*10.5\*\* Boot time optimization

&#x20; - Disabling unnecessary services (`snapd`, `cups`, `bluetooth`)

&#x20; - Kernel parameters (`quiet splash loglevel=3`)

&#x20; - `systemd-analyze` tools

\- \*\*10.6\*\* Secure Boot (if configured)



\### Part 11: Python \& AI Framework Setup (12-18 pages)



\- \*\*11.1\*\* Creating the `llm` virtual environment

\- \*\*11.2\*\* Installing cuSPARSELt for CUDA 13

\- \*\*11.3\*\* Installing PyTorch for JetPack 7.2

&#x20; - Finding the correct wheel URL

&#x20; - Installing with pip

\- \*\*11.4\*\* Verifying PyTorch with CUDA

&#x20; - `torch.cuda.is\_available()`

&#x20; - `torch.cuda.get\_device\_name(0)`

\- \*\*11.5\*\* Installing torchvision from source

&#x20; - Cloning the correct branch (v0.21.0)

&#x20; - Setting `TORCH\_CUDA\_ARCH\_LIST="8.7"`

&#x20; - `TORCHVISION\_USE\_FFMPEG=0` (fix for FFmpeg compatibility)

&#x20; - Building and installing

\- \*\*11.6\*\* Installing HuggingFace Hub CLI (`hf`)

\- \*\*11.7\*\* HuggingFace token setup

&#x20; - `hf auth login`

&#x20; - Caching token in `.cache/huggingface/token`



\### Part 12: Inference Engines (15-20 pages)



\- \*\*12.1\*\* Ollama

&#x20; - Native installation (`curl -fsSL https://ollama.com/install.sh | sh`)

&#x20; - Network configuration (`OLLAMA\_HOST=0.0.0.0`)

&#x20; - Pulling models (`ollama pull gemma4:latest`)

&#x20; - Testing from Windows PowerShell

&#x20; - Ollama aliases and functions

\- \*\*12.2\*\* llama.cpp

&#x20; - Building from source (CUDA 13 compatibility)

&#x20; - Downloading GGUF models (`hf download Qwen/Qwen3-8B-GGUF`)

&#x20; - Running the server (`llama-server --n-gpu-layers 999`)

&#x20; - Systemd service for llama.cpp

\- \*\*12.3\*\* vLLM

&#x20; - Pulling the correct container for JP 7.2

&#x20; - Volume mounting HuggingFace cache

&#x20; - `--gpu-memory-utilization` tuning

&#x20; - OpenAI-compatible API testing

&#x20; - Systemd service for vLLM container



\### Part 13: Agentic AI Stack (15-20 pages)



\- \*\*13.1\*\* OpenClaw

&#x20; - Installation (`curl -fsSL https://openclaw.ai/install.sh | bash`)

&#x20; - Configuration (`\~/.openclaw/openclaw.json`)

&#x20; - WhatsApp channel setup

&#x20; - Web UI via SSH tunnel

\- \*\*13.2\*\* NemoClaw (JetPack 7.2 native)

&#x20; - One-command installation (`curl -fsSL nvidia.com/nemoclaw.sh | bash`)

&#x20; - Security layer architecture

&#x20; - Configuration and testing

\- \*\*13.3\*\* Jetson Agent Skills

&#x20; - Device Skills (memory optimization, model benchmarking)

&#x20; - BSP Skills (Linux customization)

&#x20; - Running skills with local LLM

\- \*\*13.4\*\* Open WebUI

&#x20; - Docker container

&#x20; - Connecting to Ollama/vLLM

&#x20; - Admin panel configuration



\### Part 14: LLM Model Testing \& Benchmarking (12-18 pages)



\- \*\*14.1\*\* Top 10 models for AGX Orin 64GB

&#x20; - Model names, parameters, memory requirements

&#x20; - Expected tokens/second

&#x20; - Use case recommendations

\- \*\*14.2\*\* Model-specific installation commands

&#x20; - Gemma 4 family (E2B, E4B, 26B-A4B)

&#x20; - Qwen3.5 family (4B, 9B, 35B-A3B)

&#x20; - Nemotron family (4B, 30B, Omni)

&#x20; - Cosmos Reason 2 2B

&#x20; - GPT OSS 20B

\- \*\*14.3\*\* Model switcher script (`switch-model.sh`)

\- \*\*14.4\*\* Benchmarking methodology

&#x20; - Measuring tok/s with `curl`

&#x20; - Memory usage monitoring

&#x20; - Comparing vLLM vs llama.cpp

\- \*\*14.5\*\* Integrating with OpenClaw



\### Part 15: Production Deployment (10-15 pages)



\- \*\*15.1\*\* System hardening

&#x20; - Setting correct restart policies (`--restart no` for LLM containers)

&#x20; - OOM killer protection (`vm.panic\_on\_oom=0`, `vm.oom\_kill\_allocating\_task=1`)

&#x20; - Preventing ghost models

\- \*\*15.2\*\* Watchdog scripts

&#x20; - Memory monitoring

&#x20; - Automatic cleanup on OOM risk

\- \*\*15.3\*\* Startup/recovery procedures

&#x20; - After reboot sequence

&#x20; - Recovery from OOM

\- \*\*15.4\*\* UFW firewall configuration

&#x20; - Opening only necessary ports

&#x20; - Listing rules

\- \*\*15.5\*\* Power mode selection by workload

&#x20; - Table: model → recommended power mode

&#x20; - Automation with aliases



\### Part 16: Troubleshooting \& Best Practices (10-15 pages)



\- \*\*16.1\*\* Common issues and solutions

&#x20; - `nvcc: command not found`

&#x20; - OOM (Out of Memory) → system freeze

&#x20; - Ghost models in Docker containers

&#x20; - Docker daemon doesn't start

&#x20; - XRDP black screen

&#x20; - USB device permissions

&#x20; - Swap not persisting

\- \*\*16.2\*\* Recovery procedures

&#x20; - Restoring from backup

&#x20; - Recovery Mode flashing

\- \*\*16.3\*\* Security best practices

&#x20; - SSH key-based authentication

&#x20; - Firewall rules

&#x20; - Token storage

\- \*\*16.4\*\* Maintenance routines

&#x20; - Weekly: `apt update \&\& apt upgrade`

&#x20; - Monthly: `jetson-clean`, `docker image prune`

&#x20; - Quarterly: verify swap file and fstab



\### Appendix



\- \*\*A. Quick Reference Commands\*\* (2-3 pages)

&#x20; - All essential commands grouped by category

\- \*\*B. Port Mappings\*\* (1 page)

&#x20; - Services and their ports

\- \*\*C. Directory Structure\*\* (1-2 pages)

&#x20; - `\~/projects`, `\~/models`, `\~/scripts`, `\~/envs`, `\~/jetson-ai-data`

\- \*\*D. Alias Reference\*\* (2-3 pages)

&#x20; - All aliases and their functions

\- \*\*E. Troubleshooting Flowchart\*\* (1 page)

&#x20; - Visual decision tree

\- \*\*F. Resources \& References\*\* (2-3 pages)

&#x20; - Official NVIDIA documentation

&#x20; - GitHub repositories

&#x20; - Community forums



\---



\## FINAL OUTPUT STRUCTURE



\### Output 1: Consolidated Markdown



\- \*\*File name:\*\* `Jetson\_AGX\_Orin\_JP72\_Complete\_Guide.md`

\- \*\*Location:\*\* Root of the project directory

\- \*\*Format:\*\* Clean markdown with proper headings, code blocks, tables, and internal links

\- \*\*Length:\*\* Estimated 300-500 pages when rendered



\### Output 2: DOCX File



\- \*\*File name:\*\* `Getting\_Started\_with\_NVIDIA\_Jetson\_AGX\_Orin\_JP72.docx`

\- \*\*Built using:\*\* `skill-tutorial-docx/tutorial\_docx\_builder.py`

\- \*\*Format:\*\*

&#x20; - Professional title page (with NVIDIA/Jetson branding)

&#x20; - Auto-generated Table of Contents

&#x20; - Heading 1-6 styles

&#x20; - Monospace for code blocks

&#x20; - Tables with borders

&#x20; - Page numbers

&#x20; - Proper margins (1 inch / 2.54 cm)

&#x20; - Font: Calibri or Times New Roman (body), Consolas (code)



\---



\## ADDITIONAL INSTRUCTIONS FOR THE ASSISTANT



1\. \*\*Assume zero prior knowledge.\*\* Explain every concept from first principles:

&#x20;  - What is a kernel?

&#x20;  - What is systemd?

&#x20;  - What is a virtual environment?

&#x20;  - What is a swap file?

&#x20;  - What is a container?



2\. \*\*Test every command.\*\* If you cannot test on hardware, mark as:

&#x20;  - `\[VERIFIED ON JP 7.2]` → confirmed working

&#x20;  - `\[TESTED ON JP 6.2]` → likely works but verify

&#x20;  - `\[NEEDS VERIFICATION]` → command syntax may have changed



3\. \*\*Include expected outputs.\*\* For every command, show what the user should see.



4\. \*\*Include error messages and solutions.\*\* For every possible failure point, document:

&#x20;  - What error might appear

&#x20;  - Why it happens

&#x20;  - How to fix it



5\. \*\*Document timings.\*\* Indicate how long each step takes (e.g., "This takes 3-5 minutes on first run").



6\. \*\*Use consistent terminology.\*\* Throughout the book:

&#x20;  - "Jetson" vs "Jetson AGX Orin" — use consistently

&#x20;  - "container" vs "Docker container"

&#x20;  - "LLM" vs "large language model"



7\. \*\*Provide cross-references.\*\* When a step depends on a previous step, reference it by section number.



8\. \*\*Include security warnings.\*\* Any command with `sudo`, any permission change, any firewall rule must have a warning or explanation.



9\. \*\*Make it actionable.\*\* Every section should end with a clear "What's next" or "Next steps" pointer.



10\. \*\*Use the skill for DOCX generation.\*\* The `tutorial-docx-builder` skill should be executed after the markdown is complete, using the provided code.



\---



\## SKILL/AGENT CREATION PROMPT (for the assistant)



\### Create Skill: `tutorial-docx-builder`



```

You are to create a new skill based on the existing skill-tutorial-docx folder.



The skill should:

1\. Accept a Markdown file as input

2\. Parse it into structured sections (headings, paragraphs, code blocks, tables, lists)

3\. Generate a professional DOCX file with:

&#x20;  - Title page

&#x20;  - Auto-generated TOC

&#x20;  - Consistent styling

&#x20;  - Code blocks with monospace formatting

&#x20;  - Tables preserved

&#x20;  - Page numbers

&#x20;  - Proper margins



Use the existing python\_skill\_template and implement the build logic from tutorial\_docx\_builder.py.

The skill should be callable as: tutorial-docx-builder input.md output.docx

```



\### Create Agent: `ebook-research-agent`



```

You are the ebook-research-agent. Your job is to:



1\. Verify that all commands in the tutorial work on Jetson AGX Orin with JetPack 7.2

2\. Check that all URLs are still valid

3\. Ensure package names and versions are correct for Ubuntu 24.04

4\. Compare commands against the provided reference documents

5\. Flag any discrepancies between the documentation and expected behavior



When you encounter a command that is different in JP 7.2, highlight it and provide the corrected version.

```



\### Create Agent: `tutorial-qa-agent`



```

You are the tutorial-qa-agent. Your job is to:



1\. Answer questions about the tutorial content

2\. Explain concepts in more detail when users ask

3\. Provide troubleshooting help for specific issues

4\. Suggest alternative approaches based on the user's hardware or use case

5\. Generate quick reference cards for specific topics (e.g., "all aliases", "port mapping")



You should have access to the full tutorial content and be able to reference specific sections.

```

Start planning mode, and develop a full detailed plan, because this is a relative big output, so could overpass the session limit in Claude, so we need an incremental approach, or structure by chapters, in order to "divide-\&-conquer" technique without loosing certerity, credibility, reliability and technical approach. So in plan mode analyze this in order to don't generate frustration nor generate incomplete outputs. We need to be smart in token generation in order to reach objectives. It's important you read the file "jetson\_agx\_orin\_jp72\_specs.html" and update all the commands if required, so research deep in order to build a fully reliable tutorial. When the plan ready, lets start with the parts related to "jetson-orin-jp72-GUIA-DEFINITIVA-v3.md" and "jetson-orin-jp72-TOP10-MODELOS.md" because are the most important chapters. Of course respect the incremental pedagogic and methodological learning path, but I need this chapters urgently, later we can generate the fundamentals, first chapters and so forth, so calculate the chapter numbers and positions in order to don't loose the thread.



