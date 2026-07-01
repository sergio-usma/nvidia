# AI Office - Discord Integration

## Overview

The AI Office can be controlled via Discord, allowing you to interact with agents, create requests, and monitor status through a bot.

## Discord Bot Setup

### 1. Create Discord Application

1. Go to https://discord.com/developers/applications
2. Create new application
3. Go to Bot section
4. Create Bot
5. Get token
6. Enable Message Content Intent

### 2. Invite Bot

1. Go to OAuth2 → URL Generator
2. Select scopes: bot
3. Select permissions:
   - Send Messages
   - Read Message History
   - Use Slash Commands
4. Generate URL and invite bot

## Bot Implementation

```python
#!/usr/bin/env python3
"""
Discord Bot for AI Office
"""

import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "token": os.getenv("DISCORD_BOT_TOKEN", ""),
    "api_url": "http://localhost:9001",
    "allowed_guilds": []  # Add your guild IDs
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


class AIOfficeCog(commands.Cog):
    """AI Office Discord commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="status", description="Get AI Office status")
    async def status(self, interaction: discord.Interaction):
        """Show office status"""
        try:
            response = requests.get(f"{CONFIG['api_url']}/api/status", timeout=10)
            data = response.json()
            
            embed = discord.Embed(
                title="🏢 AI Office Status",
                color=discord.Color.green()
            )
            
            # Agents
            agents_text = ""
            for agent_id, info in data.get("agents", {}).items():
                status = info.get("status", "unknown")
                task = info.get("current_task", "")
                emoji = "🟢" if status == "idle" else "🟡" if status == "working" else "🔴"
                agents_text += f"{emoji} {agent_id}: {status}"
                if task:
                    agents_text += f" - {task[:30]}"
                agents_text += "\n"
            
            embed.add_field(name="Agents", value=agents_text or "No agents", inline=False)
            
            # Queue
            embed.add_field(
                name="Queue",
                value=f"Pending: {data.get('queue_size', 0)}",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}")
    
    @app_commands.command(name="request", description="Create new request")
    @app_commands.describe(title="Request title", description="Description", 
                          type="feature, bugfix, content, docs")
    async def create_request(self, interaction: discord.Interaction, 
                            title: str, description: str, 
                            type: str = "feature"):
        """Create new work request"""
        await interaction.response.defer()
        
        try:
            response = requests.post(
                f"{CONFIG['api_url']}/api/requests",
                json={
                    "title": title,
                    "description": description,
                    "type": type,
                    "priority": 3,
                    "created_by": interaction.user.name
                },
                timeout=30
            )
            
            if response.status_code == 201:
                request = response.json()
                embed = discord.Embed(
                    title="✅ Request Created",
                    color=discord.Color.green()
                )
                embed.add_field(name="ID", value=request.get("id"))
                embed.add_field(name="Title", value=title)
                embed.add_field(name="Type", value=type)
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Failed to create request")
                
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")
    
    @app_commands.command(name="queue", description="Show request queue")
    async def show_queue(self, interaction: discord.Interaction):
        """Show pending requests"""
        try:
            response = requests.get(f"{CONFIG['api_url']}/api/requests", timeout=10)
            requests_data = response.json()
            
            pending = [r for r in requests_data if r.get("status") == "pending"]
            
            if not pending:
                await interaction.response.send_message("No pending requests!")
                return
            
            embed = discord.Embed(
                title="📋 Request Queue",
                color=discord.Color.blue()
            )
            
            for req in pending[:10]:  # Show first 10
                priority = req.get("priority", 5)
                priority_emoji = "🔴" if priority <= 1 else "🟠" if priority <= 2 else "🟡"
                
                embed.add_field(
                    name=f"{priority_emoji} {req.get('id')} - {req.get('type')}",
                    value=req.get("title", "")[:50],
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}")
    
    @app_commands.command(name="activity", description="Recent activity")
    async def show_activity(self, interaction: discord.Interaction):
        """Show recent activity"""
        try:
            response = requests.get(f"{CONFIG['api_url']}/api/activity", timeout=10)
            data = response.json()
            
            embed = discord.Embed(
                title="📊 Recent Activity",
                color=discord.Color.blurple()
            )
            
            for entry in data.get("activity_log", [])[-10:]:
                timestamp = entry.get("timestamp", "")
                agent = entry.get("agent", "")
                action = entry.get("action", "")
                detail = entry.get("detail", "")
                
                embed.add_field(
                    name=f"[{timestamp}] {agent}",
                    value=f"{action}: {detail[:50]}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}")
    
    @app_commands.command(name="stats", description="Office statistics")
    async def show_stats(self, interaction: discord.Interaction):
        """Show statistics"""
        try:
            response = requests.get(f"{CONFIG['api_url']}/api/stats", timeout=10)
            data = response.json()
            
            embed = discord.Embed(
                title="📈 Office Statistics",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="Total Requests", value=str(data.get("total", 0)))
            embed.add_field(name="Pending", value=str(data.get("pending", 0)))
            embed.add_field(name="In Progress", value=str(data.get("in_progress", 0)))
            embed.add_field(name="Completed", value=str(data.get("completed", 0)))
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}")
    
    @app_commands.command(name="agent", description="Assign agent to task")
    @app_commands.describe(agent="Agent name", task="Task description")
    async def assign_agent(self, interaction: discord.Interaction,
                          agent: str, task: str):
        """Manually assign agent"""
        await interaction.response.defer()
        
        try:
            response = requests.post(
                f"{CONFIG['api_url']}/api/agents/{agent}/task",
                json={"description": task},
                timeout=60
            )
            
            if response.status_code == 200:
                await interaction.followup.send(f"✅ Task assigned to {agent}")
            else:
                await interaction.followup.send(f"❌ Failed: {response.text}")
                
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")


@bot.event
async def on_ready():
    """Bot ready"""
    logger.info(f"Bot logged in as {bot.user}")
    
    # Sync commands
    await bot.add_cog(AIOfficeCog(bot))
    await bot.tree.sync()
    
    logger.info("Commands synced")


def run_bot():
    """Run the bot"""
    if not CONFIG["token"]:
        logger.error("DISCORD_BOT_TOKEN not set")
        return
    
    bot.run(CONFIG["token"])


if __name__ == "__main__":
    run_bot()
```

## Discord Commands

| Command | Description |
|---------|-------------|
| `/status` | Show AI Office status |
| `/request <title> <description> <type>` | Create new request |
| `/queue` | Show pending requests |
| `/activity` | Show recent activity |
| `/stats` | Show statistics |
| `/agent <name> <task>` | Assign agent manually |

## Example Usage

```
# Check status
/status

# Create feature request
/request "Add dark mode" "Implement dark theme for the application" feature

# Create bug fix
/request "Fix API timeout" "The /users endpoint times out after 30s" bugfix

# Create content
/request "Tech article" "Write about our new AI features" content

# View queue
/queue

# Check activity
/activity
```

## Service Configuration

```bash
# Create service
sudo tee /etc/systemd/system/ai-office-discord.service << 'EOF'
[Unit]
Description=AI Office Discord Bot
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/ai-office
ExecStart=/opt/ai-office/venv/bin/python discord/bot.py
Restart=always
Environment="DISCORD_BOT_TOKEN=your_token_here"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-office-discord
sudo systemctl start ai-office-discord
```

## Next Steps

- [06-dashboard](./06-dashboard.md) - Pixel art dashboard
