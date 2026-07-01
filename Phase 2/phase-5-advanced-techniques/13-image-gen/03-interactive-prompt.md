# Interactive Prompt Generator Tutorial

A comprehensive guide to using the interactive prompt generator for AI image creation.

## Overview

The Interactive Prompt Generator is a Python tool that helps you create professional image generation prompts with customizable parameters for optimal results.

## Running the Tool

```bash
# Navigate to the directory
cd ~/JETSON-CONFIG/jetson-getting-started/part-17-image-processing-generation

# Run the generator
python3 03-interactive-prompt.py
```

## Parameter Categories

### 1. Environment

| Option | Setting |
|--------|----------|
| 1 | Interior |
| 2 | Cityscape |
| 3 | Beach |
| 4 | Mountain |
| 5 | Desert |
| 6 | Underwater |
| 7 | Forest |
| 8 | Jungle |
| 9 | Urban street |

### 2. Color Palette

| Option | Setting |
|--------|----------|
| 1 | Stardust palette |
| 2 | Night sky palette |
| 3 | Vibrant colors |
| 4 | Monochrome (black and white) |
| 5 | Winter colors |
| 6 | Neon colors |
| 7 | Earth tones |
| 8 | Vivid colors |
| 9 | Matte colors |

### 3. Lighting

| Option | Setting |
|--------|----------|
| 1 | Golden hour, Low-light conditions |
| 2 | Bright Lighting |
| 3 | Firelight |
| 4 | Overcast sky |
| 5 | Night, Low-light conditions |
| 6 | Harsh sunlight |
| 7 | Candlelight |
| 8 | Studio lighting |
| 9 | Moonlight |

### 4. Composition

| Option | Setting |
|--------|----------|
| 1 | Avoid Too Much Negative Space, Obey the Rule of Thirds |
| 2 | Center focus |
| 3 | Leading lines |
| 4 | Diagonal composition |
| 5 | Symmetry and patterns |
| 6 | Framing |
| 7 | Rule of odds |
| 8 | Rule of space |
| 9 | Rule of simplicity |

### 5. Depth of Field

| Option | Setting |
|--------|----------|
| 1 | Shallow depth of field |
| 2 | Medium depth of field |
| 3 | Deep depth of field |
| 4 | All in focus |
| 5 | Bokeh effect |
| 6 | Blurry background |
| 7 | Sharp focus |
| 8 | Soft focus |
| 9 | Selective focus |

### 6. Mood

| Option | Setting |
|--------|----------|
| 1 | Inspiring |
| 2 | Epic |
| 3 | Energetic |
| 4 | Mysterious |
| 5 | Romantic |
| 6 | Dreamy |
| 7 | Dramatic |
| 8 | Whimsical |
| 9 | Surreal |

### 7. Time and Weather

| Option | Setting |
|--------|----------|
| 1 | Sunset, moderately cloudy |
| 2 | Sunrise, clear sky |
| 3 | Nighttime, city lights |
| 4 | Midday, sunny |
| 5 | Rainy day |
| 6 | Snowy landscape |
| 7 | Foggy morning |
| 8 | Thunderstorm |
| 9 | Windy day |

### 8. Human Emotion

| Option | Setting |
|--------|----------|
| 1 | Happiness, Joy |
| 2 | Contentment, Peace |
| 3 | Curiosity, Wonder |
| 4 | Surprise, Excitement |
| 5 | Fear, Anxiety |
| 6 | Sadness, Grief |
| 7 | Anger, Frustration |
| 8 | Love, Affection |
| 9 | Neutral, No emotion |

### 9. Camera

| Option | Setting |
|--------|----------|
| 1 | Sigma 18-35mm F1.8 lens |
| 2 | Canon EF 85mm lens |
| 3 | Canon EF 50mm f/1.8 STM lens |
| 4 | Nikon AF-S DX NIKKOR 35mm f/1.8G lens |
| 5 | Tamron 70-200mm f/2.8 Di VC USD G2 lens |
| 6 | Sony FE 24-70mm f/2.8 GM lens |
| 7 | Fujifilm XF 56mm f/1.2 R lens |
| 8 | Insta360 ONE X2 |
| 9 | GoPro Hero 9 Black |

### 10. Camera Angle

| Option | Setting |
|--------|----------|
| 1 | Eye-level |
| 2 | Bird's-eye view |
| 3 | Worm's-eye view |
| 4 | Close-up |
| 5 | Wide-angle |
| 6 | Over-the-shoulder |
| 7 | Macro shot |
| 8 | Selfie mode |
| 9 | Aerial view |

## Technical Parameters

| Parameter | Options | Default |
|-----------|---------|---------|
| Width | 256-2048 | 1024 |
| Height | 256-2048 | 1024 |
| Steps | 10-100 | 30 |
| CFG Scale | 1-25 | 7 |
| Seed | -1 (random) | -1 |

## Example Output

### Input
```
Enter your desired custom prompt: A dragon flying over mountains
Enter objects (separated by commas): castle, clouds
Do you want to configure image parameters (y/n)? y

Environment: 4 (Mountain)
Color_palette: 2 (Night sky palette)
Lighting: 9 (Moonlight)
Mood: 4 (Mysterious)
```

### Generated Prompt
```
A dragon flying over mountains, with castle, clouds, mountain, night sky palette, mysterious mood, moonlight
```

## JSON Export

The tool also exports JSON for programmatic use:

```json
{
  "main_prompt": "A dragon flying over mountains",
  "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy",
  "technical_params": {
    "Width": 1024,
    "Height": 1024,
    "Steps": 30,
    "CFG_Scale": 7,
    "Seed": -1
  },
  "selected_parameters": {
    "Environment": "Mountain",
    "Color_palette": "Night sky palette",
    "Lighting": "Moonlight",
    "Mood": "Mysterious"
  }
}
```

## Next Steps

- [Stable Diffusion XL](./04-stable-diffusion-xl.md) - Generate images using SDXL
- [FLUX.1 Models](./05-flux-models.md) - Try FLUX models
