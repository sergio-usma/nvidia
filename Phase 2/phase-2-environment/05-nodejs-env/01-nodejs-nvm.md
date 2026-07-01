# Install Node.js via NVM

Set up Node.js for JavaScript/TypeScript development on your Jetson.

## Install NVM

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
```

## Configure NVM in .bashrc

Add to the end of your `~/.bashrc`:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# CUDA 12.6 paths
export CUDA_HOME=/usr/local/cuda-12.6
export PATH=/usr/local/cuda-12.6/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:$LD_LIBRARY_PATH
```

Apply changes:

```bash
source ~/.bashrc
```

## Install Node.js LTS

```bash
nvm install --lts
```

This installs the latest LTS version for ARM64.

## Verify Installation

```bash
node -v
npm -v
```

## Install Build Tools

```bash
sudo apt install -y build-essential libpixman-1-dev libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev
```

## Test Native Module Compilation

Install a package that requires native compilation:

```bash
npm install -g canvas
```

This will use all 12 CPU cores during compilation.

## Create Test Script

```bash
cat << 'EOF' > test-orin-node.js
const os = require('os');
console.log("--- Jetson AGX Orin Node.js Report ---");
console.log("Arquitectura:", process.arch);
console.log("Núcleos CPU:", os.cpus().length);
console.log("Memoria total:", (os.totalmem() / 1024 / 1024 / 1024).toFixed(2), "GB");
console.log("Versión Node:", process.version);
console.log("---------------------------------------");
EOF

node test-orin-node.js
```

## Install Common Global Packages

```bash
# For API development
npm install -g express

# For AI/LLM integration
npm install -g langchain
```

## Managing Node Versions

```bash
nvm list          # List installed versions
nvm use <version> # Switch version
nvm default <version> # Set default
```

## Next Steps

Now that Node.js is set up, proceed to:
- [Ollama Setup](../part-5-llms/01-ollama-setup.md)
- [AI Coding Setup](../part-8-development-tools/03-ai-coding-setup.md)
