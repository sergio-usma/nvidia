#!/usr/bin/env python3
"""
Interactive Prompt Generator for AI Image Generation

A comprehensive tool for creating professional image generation prompts
with customizable parameters for the Jetson AGX Orin.

Author: Jetson Developer
Version: 1.0.0
"""

import os
import json
from datetime import datetime

# Parameter options as specified by user
PARAMETER_OPTIONS = {
    "Environment": {
        1: "Interior",
        2: "Cityscape",
        3: "Beach",
        4: "Mountain",
        5: "Desert",
        6: "Underwater",
        7: "Forest",
        8: "Jungle",
        9: "Urban street"
    },
    "Color_palette": {
        1: "Stardust palette",
        2: "Night sky palette",
        3: "Vibrant colors",
        4: "Monochrome (black and white)",
        5: "Winter colors",
        6: "Neon colors",
        7: "Earth tones",
        8: "Vivid colors",
        9: "Matte colors"
    },
    "Lighting": {
        1: "Golden hour, Low-light conditions",
        2: "Bright Lighting",
        3: "Firelight",
        4: "Overcast sky",
        5: "Night, Low-light conditions",
        6: "Harsh sunlight",
        7: "Candlelight",
        8: "Studio lighting",
        9: "Moonlight"
    },
    "Composition": {
        1: "Avoid Too Much Negative Space, Obey the Rule of Thirds",
        2: "Center focus",
        3: "Leading lines",
        4: "Diagonal composition",
        5: "Symmetry and patterns",
        6: "Framing",
        7: "Rule of odds",
        8: "Rule of space",
        9: "Rule of simplicity"
    },
    "Depth_of_Field": {
        1: "Shallow depth of field",
        2: "Medium depth of field",
        3: "Deep depth of field",
        4: "All in focus",
        5: "Bokeh effect",
        6: "Blurry background",
        7: "Sharp focus",
        8: "Soft focus",
        9: "Selective focus"
    },
    "Mood": {
        1: "Inspiring",
        2: "Epic",
        3: "Energetic",
        4: "Mysterious",
        5: "Romantic",
        6: "Dreamy",
        7: "Dramatic",
        8: "Whimsical",
        9: "Surreal"
    },
    "Time_and_Weather": {
        1: "Sunset, moderately cloudy",
        2: "Sunrise, clear sky",
        3: "Nighttime, city lights",
        4: "Midday, sunny",
        5: "Rainy day",
        6: "Snowy landscape",
        7: "Foggy morning",
        8: "Thunderstorm",
        9: "Windy day"
    },
    "Human_Emotion": {
        1: "Happiness, Joy",
        2: "Contentment, Peace",
        3: "Curiosity, Wonder",
        4: "Surprise, Excitement",
        5: "Fear, Anxiety",
        6: "Sadness, Grief",
        7: "Anger, Frustration",
        8: "Love, Affection",
        9: "Neutral, No emotion"
    },
    "Camera": {
        1: "Sigma 18-35mm F1.8 lens",
        2: "Canon EF 85mm lens",
        3: "Canon EF 50mm f/1.8 STM lens",
        4: "Nikon AF-S DX NIKKOR 35mm f/1.8G lens",
        5: "Tamron 70-200mm f/2.8 Di VC USD G2 lens",
        6: "Sony FE 24-70mm f/2.8 GM lens",
        7: "Fujifilm XF 56mm f/1.2 R lens",
        8: "Insta360 ONE X2",
        9: "GoPro Hero 9 Black"
    },
    "Camera_Angle": {
        1: "Eye-level",
        2: "Bird's-eye view",
        3: "Worm's-eye view",
        4: "Close-up",
        5: "Wide-angle",
        6: "Over-the-shoulder",
        7: "Macro shot",
        8: "Selfie mode",
        9: "Aerial view"
    }
}

# Additional technical parameters
TECHNICAL_PARAMS = {
    "Width": [256, 512, 768, 1024, 1280, 1536, 2048],
    "Height": [256, 512, 768, 1024, 1280, 1536, 2048],
    "Steps": [10, 20, 30, 50, 75, 100],
    "CFG_Scale": [1, 3, 5, 7, 9, 12, 15, 20, 25],
    "Seed": list(range(-1, 100))  # -1 for random
}


def print_header():
    """Print header."""
    print("\n" + "="*60)
    print("   INTERACTIVE AI IMAGE PROMPT GENERATOR")
    print("   For Jetson AGX Orin Image Generation")
    print("="*60 + "\n")


def get_user_prompt():
    """Get the main prompt from user."""
    print("\n" + "-"*40)
    print("STEP 1: Main Prompt")
    print("-"*40)
    user_prompt = input("Enter your desired custom prompt: ").strip()
    
    if not user_prompt:
        print("Error: Prompt cannot be empty!")
        return get_user_prompt()
    
    return user_prompt


def get_user_parameters():
    """Get additional user parameters."""
    print("\n" + "-"*40)
    print("STEP 2: Additional Parameters (Optional)")
    print("-"*40)
    
    user_parameters = {}
    
    # Objects
    objects = input("Enter objects (separated by commas) [Press Enter to skip]: ").strip()
    if objects:
        user_parameters["Objects"] = objects
    
    # Geolocation
    geo = input("Enter a geolocation, city or place [Press Enter to skip]: ").strip()
    if geo:
        user_parameters["Geolocation"] = geo
    
    return user_parameters


def select_parameters():
    """Let user select from parameter options."""
    print("\n" + "-"*40)
    print("STEP 3: Configure Image Parameters")
    print("-"*40)
    
    configure = input("Do you want to configure image parameters (y/n)? ").lower()
    
    if configure != 'y':
        return {}
    
    selected = {}
    
    for param_name, options in PARAMETER_OPTIONS.items():
        print(f"\n{param_name.replace('_', ' ').title()}:")
        
        for num, desc in options.items():
            print(f"  {num}: {desc}")
        
        try:
            choice = input(f"Select option (1-9) or press Enter to skip: ").strip()
            if choice and choice.isdigit():
                choice = int(choice)
                if 1 <= choice <= 9:
                    selected[param_name] = options[choice]
        except ValueError:
            continue
    
    return selected


def select_technical_params():
    """Let user select technical parameters."""
    print("\n" + "-"*40)
    print("STEP 4: Technical Parameters")
    print("-"*40)
    
    configure = input("Configure technical parameters (y/n)? ").lower()
    
    if configure != 'y':
        return {
            "Width": 1024,
            "Height": 1024,
            "Steps": 30,
            "CFG_Scale": 7,
            "Seed": -1
        }
    
    tech_params = {}
    
    # Width
    print(f"\nWidth options: {TECHNICAL_PARAMS['Width']}")
    width = input(f"Select width [default: 1024]: ").strip()
    tech_params["Width"] = int(width) if width and width.isdigit() else 1024
    
    # Height
    print(f"\nHeight options: {TECHNICAL_PARAMS['Height']}")
    height = input(f"Select height [default: 1024]: ").strip()
    tech_params["Height"] = int(height) if height and height.isdigit() else 1024
    
    # Steps
    print(f"\nSteps options: {TECHNICAL_PARAMS['Steps']}")
    steps = input(f"Select steps [default: 30]: ").strip()
    tech_params["Steps"] = int(steps) if steps and steps.isdigit() else 30
    
    # CFG Scale
    print(f"\nCFG Scale options: {TECHNICAL_PARAMS['CFG_Scale']}")
    cfg = input(f"Select CFG scale [default: 7]: ").strip()
    tech_params["CFG_Scale"] = int(cfg) if cfg and cfg.isdigit() else 7
    
    # Seed
    seed = input("Enter seed number (-1 for random) [default: -1]: ").strip()
    tech_params["Seed"] = int(seed) if seed and seed.lstrip('-').isdigit() else -1
    
    return tech_params


def generate_final_prompt(main_prompt, user_params, selected_params):
    """Generate the final formatted prompt."""
    prompt_parts = [main_prompt]
    
    # Add objects
    if "Objects" in user_params:
        prompt_parts.append(f"with {user_params['Objects']}")
    
    # Add geolocation
    if "Geolocation" in user_params:
        prompt_parts.append(f"at {user_params['Geolocation']}")
    
    # Add selected parameters
    for param_name, value in selected_params.items():
        formatted_name = param_name.replace('_', ' ').lower()
        prompt_parts.append(f"{formatted_name}: {value}")
    
    return ", ".join(prompt_parts)


def display_results(main_prompt, user_params, selected_params, tech_params):
    """Display the generated prompts and parameters."""
    print("\n" + "="*60)
    print("GENERATED OUTPUT")
    print("="*60)
    
    # Generate main prompt
    final_prompt = generate_final_prompt(main_prompt, user_params, selected_params)
    
    print("\n📝 MAIN PROMPT:")
    print("-"*40)
    print(final_prompt)
    
    # Generate negative prompt
    negative_prompt = "blurry, low quality, distorted, deformed, ugly, bad anatomy"
    print("\n❌ NEGATIVE PROMPT:")
    print("-"*40)
    print(negative_prompt)
    
    # Technical parameters
    print("\n⚙️ TECHNICAL PARAMETERS:")
    print("-"*40)
    for key, value in tech_params.items():
        print(f"  {key}: {value}")
    
    # Save to file
    save = input("\nSave to file (y/n)? ").lower()
    if save == 'y':
        save_to_file(main_prompt, user_params, selected_params, tech_params, final_prompt, negative_prompt)


def save_to_file(main_prompt, user_params, selected_params, tech_params, final_prompt, negative_prompt):
    """Save prompts to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prompt_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write("="*60 + "\n")
        f.write("AI IMAGE GENERATION PROMPTS\n")
        f.write("="*60 + "\n\n")
        
        f.write("MAIN PROMPT:\n")
        f.write("-"*40 + "\n")
        f.write(final_prompt + "\n\n")
        
        f.write("NEGATIVE PROMPT:\n")
        f.write("-"*40 + "\n")
        f.write(negative_prompt + "\n\n")
        
        f.write("TECHNICAL PARAMETERS:\n")
        f.write("-"*40 + "\n")
        for key, value in tech_params.items():
            f.write(f"{key}: {value}\n")
        
        if user_params:
            f.write("\nUSER PARAMETERS:\n")
            f.write("-"*40 + "\n")
            for key, value in user_params.items():
                f.write(f"{key}: {value}\n")
        
        if selected_params:
            f.write("\nSELECTED PARAMETERS:\n")
            f.write("-"*40 + "\n")
            for key, value in selected_params.items():
                f.write(f"{key}: {value}\n")
    
    print(f"✅ Saved to: {filename}")


def export_json(main_prompt, user_params, selected_params, tech_params):
    """Export prompts as JSON for programmatic use."""
    data = {
        "main_prompt": main_prompt,
        "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy",
        "technical_params": tech_params,
        "user_parameters": user_params,
        "selected_parameters": selected_params,
        "full_prompt": generate_final_prompt(main_prompt, user_params, selected_params)
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prompt_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ JSON exported to: {filename}")
    return filename


def generate_image_prompt():
    """Main function to run the interactive prompt generator."""
    print_header()
    
    # Get inputs
    main_prompt = get_user_prompt()
    user_params = get_user_parameters()
    selected_params = select_parameters()
    tech_params = select_technical_params()
    
    # Display results
    display_results(main_prompt, user_params, selected_params, tech_params)
    
    # Export JSON option
    export = input("\nExport as JSON for image generation (y/n)? ").lower()
    if export == 'y':
        export_json(main_prompt, user_params, selected_params, tech_params)
    
    # Another prompt?
    again = input("\nGenerate another prompt (y/n)? ").lower()
    if again == 'y':
        generate_image_prompt()
    else:
        print("\n👋 Thank you for using the Interactive Prompt Generator!")


if __name__ == "__main__":
    generate_image_prompt()
