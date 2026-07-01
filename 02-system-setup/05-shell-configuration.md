# Configure Your Shell (.bashrc)

A well-configured shell saves hours of debugging. This guide gives you a production-ready `.bashrc` for Jetson AI development — covering CUDA paths, Python environments, performance flags, and quality-of-life aliases.

---

## Strategy: Append a Clean Block

Rather than editing your existing `.bashrc` line by line, paste the entire block below at the end. The guards at the top prevent duplicate entries.

---

## Complete Production .bashrc Block

Open `.bashrc`:
```bash
nano ~/.bashrc
```

Scroll to the bottom and paste this entire block:

```bash
# ============================================================
# Jetson AGX Orin — AI Development Environment
# JetPack 6.2.2 | CUDA 12.6 | aarch64
# ============================================================

# --- Guard: only run in interactive shells ---
[[ $- != *i* ]] && return

# --- CUDA 12.6 ---
export CUDA_HOME=/usr/local/cuda-12.6
export PATH=/usr/local/cuda-12.6/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:/usr/local/cuda-12.6/extras/CUPTI/lib64:$LD_LIBRARY_PATH

# --- TensorRT (needed for some Python bindings) ---
export LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:$LD_LIBRARY_PATH

# --- Local user binaries (pip install --user) ---
export PATH="$HOME/.local/bin:$PATH"

# --- Models directory (change if you store models elsewhere) ---
export MODELS_DIR="$HOME/models"

# --- Hugging Face acceleration ---
export HF_HUB_ENABLE_HF_TRANSFER=1          # Faster downloads via hf_transfer
export HF_HOME="$HOME/.cache/huggingface"   # Cache location (move to NVMe if available)

# --- Build flags: use all 12 cores ---
export MAKEFLAGS="-j$(nproc)"
export CMAKE_BUILD_PARALLEL_LEVEL=$(nproc)

# --- Ollama (if running as a service, not Docker) ---
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODELS="$HOME/.ollama/models"

# --- Python virtual environment helpers ---
# Activate the main AI venv quickly: 'ai'
alias ai='source ~/envs/ai_env/bin/activate'
# Deactivate: 'da'
alias da='deactivate'

# --- Pyenv (if installed) ---
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
command -v pyenv > /dev/null && eval "$(pyenv init - bash)" && eval "$(pyenv virtualenv-init -)"

# --- NVM for Node.js (if installed) ---
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# --- Jetson performance shortcuts ---
alias maxn='sudo nvpmodel -m 0 && sudo jetson_clocks && echo "✓ MAXN mode + clocks locked"'
alias powersave='sudo nvpmodel -m 3 && echo "✓ 15W power-save mode"'
alias perf='sudo nvpmodel -q && sudo jetson_clocks --show 2>/dev/null | grep -E "(CPU|GPU|EMC).*Freq"'

# --- Monitoring shortcuts ---
alias stats='tegrastats --interval 1000'
alias temps='cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | awk "{printf \"%.1f°C\n\", \$1/1000}"'
alias memfree='free -h | grep -E "^(Mem|Swap)"'
alias gpucheck='tegrastats | head -1'

# --- Docker GPU shortcuts ---
alias drun='docker run --runtime nvidia --gpus all'
alias ollama='docker exec -it ollama ollama'   # proxy ollama commands through container

# --- File system ---
alias ls='ls --color=auto'
alias ll='ls -alFh --color=auto'
alias la='ls -A --color=auto'
alias ..='cd ..'
alias ...='cd ../..'
alias mkdir='mkdir -pv'

# --- System ---
alias update='sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y'
alias disk='df -h | grep -E "^(/dev|Filesystem)"'
alias ports='ss -tulnp'

# --- Git shortcuts ---
alias gs='git status'
alias gd='git diff'
alias gl='git log --oneline -10'

# --- Deduplicate PATH (prevents bloat across shell reloads) ---
export PATH=$(echo -n "$PATH" | awk -v RS=: -v ORS=: '!x[$0]++' | sed 's/:$//')

# --- Greeting: show Jetson status on terminal open ---
if command -v tegrastats &>/dev/null; then
    POWER_MODE=$(sudo nvpmodel -q 2>/dev/null | grep "NV Power Mode" | awk '{print $NF}')
    echo "Jetson AGX Orin 64GB | Mode: ${POWER_MODE:-unknown} | $(free -h | grep Mem | awk '{print "RAM: "$3"/"$2}')"
fi
```

---

## Apply and Verify

```bash
# Apply without reopening terminal
source ~/.bashrc

# Verify CUDA is in PATH
nvcc --version | grep "release"

# Verify the make parallelism flag
echo "Build cores: $MAKEFLAGS"

# Test the shortcut aliases
memfree
```

---

## Test the `maxn` Alias

```bash
maxn
```

Expected:
```
✓ MAXN mode + clocks locked
```

Then verify with:
```bash
perf
```

---

## Hugging Face Token (Optional)

If you need to download gated models (Llama 3, Mistral, etc.):

1. Get your token at `https://huggingface.co/settings/tokens` (read-only token is sufficient)
2. Add to `.bashrc` (add after the block above):
   ```bash
   export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxx"
   ```
3. Or use the CLI login (safer — stores token in `~/.cache/huggingface/token`):
   ```bash
   pip install huggingface_hub
   huggingface-cli login
   ```

> **Security:** Never commit `.bashrc` to a public repo if it contains your HF token.

---

## Move HuggingFace Cache to NVMe (If Available)

If you have an NVMe mounted at `/data`, redirect the ~10–100 GB HF model cache:

```bash
# Add to .bashrc after the HF_HOME line
export HF_HOME="/data/.cache/huggingface"
mkdir -p "$HF_HOME"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `nvcc: not found` after sourcing | Check CUDA_HOME path: `ls /usr/local/cuda-12.6/bin/nvcc` |
| Greeting hangs on `tegrastats` | The `sudo` inside `$()` may prompt for password — remove that line |
| Duplicate PATH entries | The dedup block at the bottom handles this; confirm it ran with `echo $PATH` |
| `ollama` alias conflicts with native install | If Ollama is installed natively, remove the alias line |

---

## Next Steps

- **[Network Optimization](06-network-optimization.md)** — Faster downloads for large models
- **[Back to System Verification](01-verify-system.md)** — Confirm everything is still working
