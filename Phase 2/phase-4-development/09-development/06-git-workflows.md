# Git Advanced Workflows

This guide covers advanced Git workflows for collaborative development on Jetson AGX Orin.

## Git Configuration

```bash
# Set identity
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Set default editor
git config --global core.editor nano

# Aliases
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.lg "log --oneline --graph --decorate"
```

## Branching Strategies

```bash
# Create feature branch
git checkout -b feature/my-feature

# Create bugfix branch
git checkout -b bugfix/issue-fix

# Create release branch
git checkout -b release/v1.0.0

# Switch branches
git checkout main
git checkout develop

# Delete branch
git branch -d feature/my-feature
git branch -D feature/old-feature  # force delete
```

## Stashing

```bash
# Save changes
git stash
git stash push -m "Work in progress"

# List stashes
git stash list

# Apply stash
git stash apply
git stash apply stash@{0}

# Pop stash
git stash pop

# Drop stash
git stash drop stash@{0}
```

## Rebasing

```bash
# Rebase onto main
git checkout feature/my-feature
git rebase main

# Interactive rebase
git rebase -i HEAD~5

# Continue after resolving conflicts
git add .
git rebase --continue

# Abort rebase
git rebase --abort
```

## Cherry-picking

```bash
# Cherry-pick a commit
git cherry-pick abc123

# Cherry-pick without committing
git cherry-pick -n abc123
```

## Merging

```bash
# Merge branch
git checkout main
git merge feature/my-feature

# Merge with no fast-forward
git merge --no-ff feature/my-feature

# Abort merge
git merge --abort
```

## Reset and Revert

```bash
# Unstage files
git reset HEAD file.txt

# Reset to previous commit (keep changes)
git reset --soft HEAD~1

# Reset to previous commit (discard changes)
git reset --hard HEAD~1

# Revert a commit
git revert abc123
```

## Working with Remote

```bash
# Add remote
git remote add origin https://github.com/user/repo.git
git remote add upstream https://github.com/original/repo.git

# Fetch updates
git fetch origin
git fetch --all

# Pull with rebase
git pull --rebase origin main

# Push
git push origin main
git push -u origin feature/my-feature
```

## Git Hooks

```bash
# Create pre-commit hook
mkdir -p .git/hooks
nano .git/hooks/pre-commit
```

```bash
#!/bin/bash
# Pre-commit hook

# Run linting
npm run lint
# or
python -m flake8 .

# Run tests
pytest
```

```bash
chmod +x .git/hooks/pre-commit
```

## Gitignore Patterns

```gitignore
# Ignore node_modules
node_modules/

# Ignore Python cache
__pycache__/
*.py[cod]
*.pyc

# Ignore environment
.env
.venv
venv/

# Ignore IDE
.vscode/
.idea/

# Ignore logs
*.log

# Ignore build
build/
dist/
*.egg-info/
```

## GitHub CLI

```bash
# Install
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh
```

```bash
# Authenticate
gh auth login

# Create PR
gh pr create --title "Feature" --body "Description"

# List PRs
gh pr list

# Review PR
gh pr review PR_NUMBER
```

## GitFlow Workflow

```bash
# Start feature
git checkout develop
git checkout -b feature/new-feature

# Finish feature
git checkout develop
git merge --no-ff feature/new-feature
git branch -d feature/new-feature

# Start release
git checkout develop
git checkout -b release/v1.0.0

# Finish release
git checkout main
git merge --no-ff release/v1.0.0
git tag -a v1.0.0 -m "Release v1.0.0"
git checkout develop
git merge --no-ff release/v1.0.0
git branch -d release/v1.0.0
```

## Git Bisect

```bash
# Start bisect
git bisect start

# Mark current as bad
git bisect bad

# Mark known good commit
git bisect good v1.0.0

# Test each commit
# After finding bad commit
git bisect reset
```

## Git LFS

```bash
# Install
sudo apt install git-lfs

# Initialize
git lfs install

# Track large files
git lfs track "*.psd"
git lfs track "*.zip"

# View tracked
git lfs ls-files
```
