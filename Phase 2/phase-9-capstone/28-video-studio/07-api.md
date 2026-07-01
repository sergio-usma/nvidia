# Creative Studio - REST API Reference

## Overview

The Creative Studio API provides programmatic access to all video generation capabilities. Running on port 8083.

## Base Configuration

```python
# config/api.py
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8083,
    "debug": False,
    "max_content_length": 100 * 1024 * 1024  # 100MB
}
```

## Endpoints

### Health & Status

#### GET /api/health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### GET /api/status

Get platform status.

**Response:**
```json
{
  "providers": ["fal_ai", "comfyui"],
  "active_provider": "fal_ai",
  "queue": {
    "pending": 2,
    "processing": 1
  }
}
```

### Text-to-Video

#### POST /api/generate/text2video

Generate video from text prompt.

**Request:**
```json
{
  "prompt": "A serene lake at sunset with birds flying",
  "duration": 5,
  "fps": 24,
  "resolution": "1216x704",
  "quality": "high",
  "seed": -1,
  "enhance_prompt": true
}
```

**Response:**
```json
{
  "status": "success",
  "job_id": "job_abc123",
  "prompt": "Enhanced prompt here...",
  "video_url": "https://...",
  "audio_url": "https://...",
  "output_file": "/opt/creative-studio/outputs/text2video_20240115.mp4",
  "metadata": {
    "duration": 5,
    "fps": 24,
    "resolution": "1216x704",
    "seed": 42,
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prompt | string | required | Text prompt |
| duration | int | 5 | Video duration (seconds) |
| fps | int | 24 | Frame rate |
| resolution | string | 1216x704 | Resolution |
| quality | string | high | high or fast |
| seed | int | -1 | Random seed (-1 for random) |
| enhance_prompt | bool | true | Use AI prompt enhancement |

#### POST /api/generate/text2video/batch

Generate multiple videos from prompts.

**Request:**
```json
{
  "prompts": [
    {"prompt": "Scene 1", "duration": 3},
    {"prompt": "Scene 2", "duration": 3},
    {"prompt": "Scene 3", "duration": 3}
  ]
}
```

### Image-to-Video

#### POST /api/generate/image2video

Generate video from image.

**Request:**
```json
{
  "image": "data:image/png;base64,...",
  "prompt": "Camera pans left",
  "duration": 5,
  "fps": 24,
  "resolution": "1216x704",
  "motion_strength": 0.5
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| image | string | required | Image (URL, path, or base64) |
| prompt | string | "" | Motion description |
| duration | int | 5 | Video duration |
| fps | int | 24 | Frame rate |
| resolution | string | 1216x704 | Resolution |
| motion_strength | float | 0.5 | Motion intensity (0-1) |

### Audio-to-Video

#### POST /api/generate/audio2video

Generate video from audio.

**Request:**
```json
{
  "audio": "data:audio/mp3;base64,...",
  "duration": 5,
  "fps": 24,
  "resolution": "1216x704",
  "visual_style": "abstract"
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| audio | string | required | Audio file (URL, path, or base64) |
| duration | int | 5 | Video duration |
| fps | int | 24 | Frame rate |
| resolution | string | 1216x704 | Resolution |
| visual_style | string | abstract | Visual style |

### Video Extension

#### POST /api/generate/extend

Extend existing video.

**Request:**
```json
{
  "video": "/path/to/video.mp4",
  "prompt": "Continue forward movement",
  "duration": 5,
  "direction": "forward"
}
```

### Video Retake

#### POST /api/generate/retake

Retake specific portion of video.

**Request:**
```json
{
  "video": "/path/to/video.mp4",
  "start_time": 2.5,
  "end_time": 5.0,
  "prompt": "Show different action"
}
```

### Project Management

#### POST /api/projects

Create new project.

**Request:**
```json
{
  "name": "My Video Project",
  "description": "Project description",
  "type": "video"
}
```

**Response:**
```json
{
  "id": "proj_abc123",
  "name": "My Video Project",
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### GET /api/projects

List all projects.

#### GET /api/projects/{id}

Get project details.

#### DELETE /api/projects/{id}

Delete project.

### Asset Management

#### POST /api/assets/upload

Upload asset (image/audio/video).

**Request:**
```bash
curl -X POST http://localhost:8083/api/assets/upload \
  -F "file=@/path/to/file.mp4"
```

#### GET /api/assets

List assets.

#### GET /api/assets/{id}

Get asset details.

### Webhook

#### POST /api/webhooks

Register webhook for async notifications.

**Request:**
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["generation.complete", "generation.failed"]
}
```

### Jobs & Queue

#### GET /api/jobs

List all jobs.

#### GET /api/jobs/{id}

Get job status.

#### DELETE /api/jobs/{id}

Cancel job.

## Presets

### GET /api/presets

Get available generation presets.

**Response:**
```json
{
  "text2video": {
    "cinematic": {
      "resolution": "1216x704",
      "fps": 24,
      "duration": 5,
      "quality": "high"
    },
    "fast": {
      "resolution": "704x576",
      "fps": 24,
      "duration": 3,
      "quality": "fast"
    },
    "portrait": {
      "resolution": "1080x1920",
      "fps": 24,
      "duration": 5,
      "quality": "high"
    }
  },
  "motion": {
    "gentle": {"motion_strength": 0.3},
    "moderate": {"motion_strength": 0.5},
    "dynamic": {"motion_strength": 0.7}
  }
}
```

### GET /api/presets/{type}

Get specific preset type.

## Example Usage

### Python

```python
import requests

API = "http://localhost:8083"

# Text-to-video
response = requests.post(f"{API}/api/generate/text2video", json={
    "prompt": "A sunset over mountains",
    "duration": 5,
    "fps": 24
})

result = response.json()
print(f"Video: {result['output_file']}")
```

### cURL

```bash
# Text-to-video
curl -X POST http://localhost:8083/api/generate/text2video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A sunset over mountains", "duration": 5}'

# Image-to-video
curl -X POST http://localhost:8083/api/generate/image2video \
  -F "image=@/path/to/image.png" \
  -d '{"prompt": "Camera pans left", "duration": 5}'

# Check status
curl http://localhost:8083/api/status
```

### JavaScript

```javascript
// Text-to-video
const response = await fetch('http://localhost:8083/api/generate/text2video', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    prompt: 'A sunset over mountains',
    duration: 5
  })
});

const result = await response.json();
console.log('Video:', result.output_file);
```

## Rate Limits

| Plan | Requests/min | Concurrent |
|------|-------------|------------|
| Free | 5 | 1 |
| Pro | 30 | 3 |
| Enterprise | 100 | 10 |

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 413 | Payload Too Large |
| 429 | Rate Limited |
| 500 | Internal Error |
| 503 | Service Unavailable |

## Next Steps

- [08-web-interface](./08-web-interface.md) - Web UI guide
