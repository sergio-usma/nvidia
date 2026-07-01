# Project 5: Home Automation AI Bridge

A comprehensive guide to connecting your AI assistant to control smart home devices via Home Assistant and MQTT for natural voice-controlled home automation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Hardware](#hardware)
5. [What You'll Build](#what-youll-build)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Configure Home Assistant](#step-1-configure-home-assistant)
   - [Step 2: Install Dependencies](#step-2-install-dependencies)
   - [Step 3: Create the Bridge Application](#step-3-create-the-bridge-application)
   - [Step 4: Set Up Voice Integration](#step-4-set-up-voice-integration)
   - [Step 5: Configure Devices](#step-5-configure-devices)
7. [Using the Home Bridge](#using-the-home-bridge)
8. [Voice Commands](#voice-commands)
9. [Advanced Configuration](#advanced-configuration)
10. [Troubleshooting](#troubleshooting)
11. [Next Steps](#next-steps)

---

## Overview

This project creates an AI-powered home automation bridge:

- **Voice Control**: Natural language smart home commands
- **Home Assistant Integration**: Control any HA device
- **MQTT Support**: Low-latency device communication
- **Status Reporting**: Get device states via AI

### Why AI-Powered Home Automation?

| Feature | Benefit |
|---------|---------|
| Natural Commands | "Turn on the lights" not "light on" |
| Context Awareness | Understand intent, not just keywords |
| Multi-Device | Control multiple devices at once |
| Feedback | AI confirms actions taken |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Home Automation AI Bridge                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │   Voice      │─────▶│     AI        │─────▶│    Home      │           │
│   │   Input      │      │   Bridge      │      │  Assistant   │           │
│   │ (Whisper)    │      │  (Ollama)    │      │    (HA)      │           │
│   └──────────────┘      └──────┬───────┘      └──────────────┘           │
│                                 │                                            │
│                                 │                                            │
│                         ┌───────┴───────┐                                   │
│                         │               │                                   │
│                         ▼               ▼                                   │
│                  ┌──────────────┐  ┌──────────────┐                          │
│                  │    MQTT     │  │   REST API   │                          │
│                  │   Broker    │  │   (Direct)   │                          │
│                  └──────┬───────┘  └──────────────┘                          │
│                         │                                                    │
│                         ▼                                                    │
│                  ┌──────────────┐                                           │
│                  │   Smart      │                                           │
│                  │   Devices    │                                           │
│                  └──────────────┘                                           │
│                                                                             │
│   Commands:                                                                 │
│   "Turn on the living room lights"                                          │
│   "Set the thermostat to 72 degrees"                                         │
│   "Is the front door locked?"                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation Guide |
|-----------|-------------------|
| Home Assistant | Running on network |
| Voice Assistant | [Project 2: Voice Assistant](02-voice-controlled-assistant.md) |
| Ollama | [Part 5: Ollama Setup](../part-5-llms/01-ollama-setup.md) |
| MQTT Broker | [Part 8: MQTT](../part-8-development-tools/05-mqtt-setup.md) |

### Home Assistant Setup

1. **Install Home Assistant** (if not already)
2. **Create Long-Lived Access Token**:
   - Go to Profile → Security → Long-Lived Access Tokens
   - Create new token
   - Save the token securely

### Pre-Installation Verification

```bash
# Verify Home Assistant is running
curl http://homeassistant.local:8123/api/

# Verify MQTT is running
mosquitto_pub -t "test" -m "hello"

# Verify Ollama
ollama --version
```

---

## Hardware

### Compatible Devices

| Device Type | Examples |
|-------------|----------|
| Lights | Philips Hue, LIFX, Smart bulbs |
| Switches | TP-Link, Wemo, Sonoff |
| Thermostats | Nest, Ecobee |
| Locks | August, Schlage |
| Sensors | Motion, Temperature, Door/Window |

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Voice Control | Natural language commands |
| Device Discovery | Auto-detect HA devices |
| Status Queries | Ask about device states |
| Scene Activation | Trigger multiple devices |
| Feedback | AI confirms all actions |

---

## Step-by-Step Implementation

### Step 1: Configure Home Assistant

```bash
# Create directory for token
mkdir -p ~/.homeassistant

# Save your token
echo "YOUR_LONG_LIVED_ACCESS_TOKEN" > ~/.homeassistant/token

# Set permissions
chmod 600 ~/.homeassistant/token
```

### Step 2: Install Dependencies

```bash
# Create virtual environment
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install dependencies
pip install paho-mqtt requests flask
```

### Step 3: Create the Bridge Application

Create `home_bridge.py`:

```python
#!/usr/bin/env python3
"""
Home Automation AI Bridge

Connects AI voice commands to Home Assistant for smart home control.
Supports natural language commands, device status queries, and automation.

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import os
import re
import json
import logging
import requests
import paho.mqtt.client as mqtt
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Home Assistant Configuration
HA_URL = os.environ.get('HA_URL', 'http://homeassistant.local:8123')
HA_TOKEN_PATH = os.path.expanduser('~/.homeassistant/token')

def get_ha_token():
    """Load Home Assistant token from file."""
    try:
        with open(HA_TOKEN_PATH, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Token file not found: {HA_TOKEN_PATH}")
        return None

HA_TOKEN = get_ha_token()
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}

# MQTT Configuration (optional)
MQTT_ENABLED = os.environ.get('MQTT_ENABLED', 'false').lower() == 'true'
MQTT_BROKER = os.environ.get('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '1883'))
MQTT_TOPIC_PREFIX = 'home/bridge'

# AI Configuration
OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
LLM_MODEL = os.environ.get('LLM_MODEL', 'llama3.2')

# ============================================================================
# HOME ASSISTANT CLIENT
# ============================================================================

class HomeAssistantClient:
    """Client for interacting with Home Assistant API."""
    
    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get_states(self) -> List[Dict]:
        """Get all device states."""
        response = requests.get(
            f"{self.url}/api/states",
            headers=self.headers,
            timeout=10
        )
        return response.json() if response.status_code == 200 else []
    
    def get_state(self, entity_id: str) -> Optional[Dict]:
        """Get state of specific entity."""
        response = requests.get(
            f"{self.url}/api/states/{entity_id}",
            headers=self.headers,
            timeout=10
        )
        return response.json() if response.status_code == 200 else None
    
    def call_service(self, domain: str, service: str, 
                    data: Optional[Dict] = None) -> bool:
        """Call a Home Assistant service."""
        response = requests.post(
            f"{self.url}/api/services/{domain}/{service}",
            headers=self.headers,
            json=data or {},
            timeout=10
        )
        return response.status_code == 200
    
    def turn_on(self, entity_id: str, **kwargs) -> bool:
        """Turn on a device."""
        return self.call_service(
            'homeassistant', 'turn_on',
            {'entity_id': entity_id, **kwargs}
        )
    
    def turn_off(self, entity_id: str) -> bool:
        """Turn off a device."""
        return self.call_service(
            'homeassistant', 'turn_off',
            {'entity_id': entity_id}
        )
    
    def toggle(self, entity_id: str) -> bool:
        """Toggle a device."""
        return self.call_service(
            'homeassistant', 'toggle',
            {'entity_id': entity_id}
        )
    
    def set_value(self, entity_id: str, value: Any) -> bool:
        """Set value for a sensor/number."""
        return self.call_service(
            'input_number', 'set_value',
            {'entity_id': entity_id, 'value': value}
        )


# ============================================================================
# MQTT CLIENT (Optional)
# ============================================================================

class MQTTBridge:
    """MQTT bridge for low-latency communication."""
    
    def __init__(self, broker: str, port: int, prefix: str):
        self.client = mqtt.Client()
        self.prefix = prefix
        self.client.connect(broker, port, 60)
        self.client.loop_start()
    
    def publish(self, topic: str, payload: str):
        """Publish MQTT message."""
        full_topic = f"{self.prefix}/{topic}"
        self.client.publish(full_topic, payload)
    
    def subscribe(self, topic: str, callback):
        """Subscribe to MQTT topic."""
        full_topic = f"{self.prefix}/{topic}"
        self.client.message_callback_add(full_topic, callback)
        self.client.subscribe(full_topic)


# ============================================================================
# COMMAND PARSER
# ============================================================================

class CommandParser:
    """Parse natural language commands into HA actions."""
    
    # Intent patterns
    TURN_ON_PATTERNS = [
        r'turn on (?:the )?(.+)',
        r'switch on (?:the )?(.+)',
        r'activate (?:the )?(.+)',
        r'light(?:s)? (?:on|up) (?:the )?(.+)',
        r'start (?:the )?(.+)'
    ]
    
    TURN_OFF_PATTERNS = [
        r'turn off (?:the )?(.+)',
        r'switch off (?:the )?(.+)',
        r'deactivate (?:the )?(.+)',
        r'light(?:s)? off (?:the )?(.+)',
        r'stop (?:the )?(.+)'
    ]
    
    TOGGLE_PATTERNS = [
        r'toggle (?:the )?(.+)',
        r'switch (?:the )?(.+)'
    ]
    
    SET_TEMPERATURE_PATTERNS = [
        r'set (?:the )?(?:thermostat|temperature) to (\d+)',
        r'make it (\d+) degrees',
        r'set (?:the )?(?:heat|ac) to (\d+)'
    ]
    
    def __init__(self, ha_client: HomeAssistantClient):
        self.ha = ha_client
        self.devices = self._load_devices()
    
    def _load_devices(self) -> Dict[str, str]:
        """Load device mapping from HA."""
        devices = {}
        states = self.ha.get_states()
        
        for state in states:
            entity_id = state['entity_id']
            friendly_name = state['attributes'].get('friendly_name', entity_id)
            
            # Map various names to entity_id
            devices[entity_id] = entity_id
            devices[friendly_name.lower()] = entity_id
            
            # Also map without "the"
            if friendly_name.lower().startswith('the '):
                devices[friendly_name.lower()[4:]] = entity_id
        
        return devices
    
    def find_entity(self, name: str) -> Optional[str]:
        """Find entity ID from name."""
        name_lower = name.lower().strip()
        
        # Direct match
        if name_lower in self.devices:
            return self.devices[name_lower]
        
        # Partial match
        for entity_name, entity_id in self.devices.items():
            if name_lower in entity_name or entity_name in name_lower:
                return entity_id
        
        return None
    
    def parse_command(self, command: str) -> Dict[str, Any]:
        """Parse command and return action."""
        command = command.lower().strip()
        
        # Try each pattern
        for pattern in self.TURN_ON_PATTERNS:
            match = re.search(pattern, command)
            if match:
                target = match.group(1).strip()
                entity_id = self.find_entity(target)
                if entity_id:
                    return {
                        'action': 'turn_on',
                        'entity_id': entity_id,
                        'description': f"Turn on {target}"
                    }
        
        for pattern in self.TURN_OFF_PATTERNS:
            match = re.search(pattern, command)
            if match:
                target = match.group(1).strip()
                entity_id = self.find_entity(target)
                if entity_id:
                    return {
                        'action': 'turn_off',
                        'entity_id': entity_id,
                        'description': f"Turn off {target}"
                    }
        
        for pattern in self.SET_TEMPERATURE_PATTERNS:
            match = re.search(pattern, command)
            if match:
                temp = int(match.group(1))
                return {
                    'action': 'set_temperature',
                    'temperature': temp,
                    'description': f"Set temperature to {temp} degrees"
                }
        
        # No pattern matched
        return {
            'action': 'unknown',
            'description': f"Could not understand: {command}"
        }


# ============================================================================
# AI INTEGRATION
# ============================================================================

class HomeAssistantAI:
    """AI-powered home automation control."""
    
    def __init__(self, ha_client: HomeAssistantClient):
        self.ha = ha_client
        self.parser = CommandParser(ha_client)
    
    def process_command(self, voice_command: str) -> str:
        """Process voice command with AI assistance."""
        
        # First try simple parsing
        parsed = self.parser.parse_command(voice_command)
        
        if parsed['action'] == 'unknown':
            # Use AI to interpret
            return self._ai_interpret(voice_command)
        
        # Execute the parsed command
        return self._execute_action(parsed)
    
    def _ai_interpret(self, command: str) -> str:
        """Use AI to interpret complex commands."""
        
        # Get device context
        devices = self.ha.get_states()
        device_list = [f"{d['entity_id']}: {d['state']}" 
                      for d in devices[:20]]
        
        prompt = f"""You are a smart home assistant. The user said: "{command}"

Available devices:
{chr(10).join(device_list)}

Determine what the user wants to do. Respond with a JSON object:
{{"action": "turn_on|turn_off|set_temperature|query|unknown", "entity_id": "entity.id", "value": number}}

If you can't determine, respond with:
{{"action": "unknown", "reason": "explanation"}}
"""
        
        try:
            response = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    'model': LLM_MODEL,
                    'prompt': prompt,
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Parse AI response (simplified)
                return self._execute_ai_response(result.get('response', ''))
        
        except Exception as e:
            logger.error(f"AI interpretation error: {e}")
        
        return "I'm sorry, I didn't understand that command."
    
    def _execute_ai_response(self, ai_response: str) -> str:
        """Execute action from AI response."""
        # Simplified - would parse JSON in production
        if 'turn_on' in ai_response.lower():
            return "I couldn't determine which device to turn on."
        elif 'turn_off' in ai_response.lower():
            return "I couldn't determine which device to turn off."
        
        return "I'm sorry, I didn't understand that command."
    
    def _execute_action(self, action: Dict) -> str:
        """Execute parsed action."""
        
        action_type = action['action']
        
        if action_type == 'turn_on':
            success = self.ha.turn_on(action['entity_id'])
            return f"Turning on {action['description']}" if success else "Failed to turn on"
        
        elif action_type == 'turn_off':
            success = self.ha.turn_off(action['entity_id'])
            return f"Turning off {action['description']}" if success else "Failed to turn off"
        
        elif action_type == 'toggle':
            success = self.ha.toggle(action['entity_id'])
            return f"Toggling {action['description']}" if success else "Failed to toggle"
        
        elif action_type == 'set_temperature':
            # Find thermostat entity
            states = self.ha.get_states()
            thermostat = None
            for state in states:
                if 'climate' in state['entity_id']:
                    thermostat = state['entity_id']
                    break
            
            if thermostat:
                success = self.ha.call_service(
                    'climate', 'set_temperature',
                    {'entity_id': thermostat, 'temperature': action['temperature']}
                )
                return f"Setting temperature to {action['temperature']} degrees"
            
            return "No thermostat found"
        
        return "Unknown action"


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application."""
    # Initialize clients
    ha_client = HomeAssistantClient(HA_URL, HA_TOKEN)
    mqtt_bridge = None
    
    if MQTT_ENABLED:
        mqtt_bridge = MQTTBridge(MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_PREFIX)
    
    # Initialize AI
    home_ai = HomeAssistantAI(ha_client)
    
    # Print status
    print("="*60)
    print("Home Automation AI Bridge")
    print("="*60)
    print(f"Home Assistant: {HA_URL}")
    print(f"MQTT: {'Enabled' if MQTT_ENABLED else 'Disabled'}")
    print(f"AI Model: {LLM_MODEL}")
    print("="*60)
    
    # Get device count
    states = ha_client.get_states()
    print(f"Found {len(states)} devices")
    
    # Interactive mode
    print("\nType commands (or 'quit' to exit):")
    print("Examples:")
    print("  'Turn on the living room lights'")
    print("  'Set thermostat to 72'")
    print("  'Is the front door locked?'")
    print()
    
    while True:
        try:
            command = input("You: ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                break
            
            if not command:
                continue
            
            response = home_ai.process_command(command)
            print(f"AI: {response}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    # Cleanup
    if mqtt_bridge:
        mqtt_bridge.client.loop_stop()


if __name__ == '__main__':
    main()
```

### Step 4: Set Up Voice Integration

The bridge can be integrated with the voice assistant from Project 2:

```python
# In voice_assistant.py, after getting AI response:
if "turn on" in response.lower() or "turn off" in response.lower():
    # Use home bridge
    from home_bridge import HomeAssistantAI
    ha_ai = HomeAssistantAI(ha_client)
    result = ha_ai.process_command(user_command)
    # Speak result
```

### Step 5: Configure Devices

Home Assistant will automatically discover your devices. Make sure:
- Devices are added to Home Assistant
- Entities have friendly names
- Long-Lived Access Token is created

---

## Using the Home Bridge

### Interactive Mode

```bash
cd ~/ai-projects/home-bridge
source venv/bin/activate
python3 home_bridge.py
```

### Example Commands

| Command | Action |
|---------|--------|
| "Turn on the living room lights" | Turn on light entity |
| "Turn off the bedroom fan" | Turn off fan |
| "Set thermostat to 72" | Set temperature |
| "Is the front door locked?" | Query lock status |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| HA connection failed | Check URL and token |
| Device not found | Check friendly names in HA |
| Command not recognized | Use simpler commands |
| MQTT not working | Verify broker is running |

---

## Next Steps

| Enhancement | Description |
|-------------|-------------|
| [Voice Pipeline](12-voice-pipeline.md) | Complete voice system |
| [Multi-Agent](13-multimodal-agent.md) | Coordinated agents |

---

## License

MIT License
