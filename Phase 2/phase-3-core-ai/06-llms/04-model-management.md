# Model Management

Organize your models efficiently to avoid data loss and permission issues.

## Recommended Directory Structure

```
~/models/           # All AI models
~/envs/             # Python virtual environments
```

## Create Model Directory

```bash
mkdir -p ~/models
```

## Download Models

### Using huggingface-hub

```bash
pip install huggingface-hub

huggingface-cli download org/model-name --local-dir ~/models/model-name
```

### Using Ollama

```bash
ollama pull model-name
```

### Using llama.cpp

Download GGUF files and place in `~/models/`.

## Move Existing Models

If you accidentally downloaded models in the wrong location:

```bash
mv -v ~/old_location/model ~/models/
```

## Set Correct Permissions

```bash
sudo chown -R $USER:$USER ~/models/
```

## Create Symbolic Links

If you have scripts pointing to old locations:

```bash
ln -s ~/models/model-name ~/old_location/model-name
```

## Manage Ollama Models

### List Ollama Models

```bash
ollama list
```

### Remove Ollama Model

```bash
ollama rm model-name
```

## Manage Hugging Face Cache

By default, models are cached in `~/.cache/huggingface/`. To change:

```bash
export HF_HOME="/path/to/new/cache"
```

Add to `.bashrc` to make permanent.

## Disk Space Management

Check model sizes:

```bash
du -sh ~/models/*
du -sh ~/.cache/huggingface/
```

Remove unused models to free space.

## Backup Models

To backup models to external storage:

```bash
# Backup
rsync -av ~/models/ /path/to/backup/models/

# Restore
rsync -av /path/to/backup/models/ ~/models/
```

## Next Steps

- [Swap for Large Models](05-swap-for-large-models.md)
- [Configure Audio Output](../part-6-speech-audio/01-audio-hdmi.md)
