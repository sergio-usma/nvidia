# VS Code Remote SSH

Connect to your Jetson remotely using VS Code.

## Install VS Code on Your Computer

Download from [code.visualstudio.com](https://code.visualstudio.com/)

## Install Remote SSH Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Remote - SSH" by Microsoft
4. Install it

## Connect to Jetson

1. Click the green icon in bottom-left corner
2. Select "Connect to Host..."
3. Enter: `username@<jetson-ip>`

Find your Jetson's IP:

```bash
hostname -I
```

## First Connection

- Enter your Jetson password
- Accept/remember the host key
- VS Code will install the server component

## Working with Remote

- Open folders: File > Open Folder
- Use terminal: Terminal > New Terminal
- Install extensions in remote context

## Copy Files

Use the Remote Explorer in VS Code sidebar to browse and transfer files.

## SSH Key Setup (Passwordless)

On your local machine:

```bash
ssh-keygen -t ed25519
```

Copy public key to Jetson:

```bash
# On local machine
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh username@jetson-ip "cat >> ~/.ssh/authorized_keys"
```

Now connect without password.

## Next Steps

- [GitHub Setup](02-github-setup.md)
- [AI Coding with Continue](03-ai-coding-setup.md)
