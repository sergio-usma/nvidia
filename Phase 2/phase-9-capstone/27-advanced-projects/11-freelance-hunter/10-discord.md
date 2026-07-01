# Freelance Hunter - Discord Bot

## Overview

The Discord bot allows you to control Freelance Hunter, check jobs, and manage proposals directly from Discord.

## Discord Bot Implementation

```python
#!/usr/bin/env python3
"""
Discord Bot for Freelance Hunter
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import requests
import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/freelance-hunter/data",
    "api_url": "http://localhost:8096",
    "discord_token": os.environ.get("DISCORD_BOT_TOKEN")
}


class FreelanceHunterBot(commands.Bot):
    """Freelance Hunter Discord Bot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix="!", intents=intents)
        
        self.data_dir = Path(CONFIG["data_dir"])
        self.api_url = CONFIG["api_url"]
    
    async def setup_hook(self):
        """Setup bot"""
        await self.add_cog(FreelanceCog(self))
        await self.add_cog(JobsCog(self))
        await self.add_cog(ProposalsCog(self))
    
    async def on_ready(self):
        """Bot ready"""
        logger.info(f"Logged in as {self.user}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for freelance jobs"
            )
        )


class FreelanceCog(commands.Cog):
    """General commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="status")
    async def status(self, ctx):
        """Show platform status"""
        try:
            response = requests.get(f"{self.bot.api_url}/api/stats", timeout=10)
            data = response.json()
            
            embed = discord.Embed(
                title="🎯 Freelance Hunter Status",
                color=0xff6b35
            )
            
            embed.add_field(
                name="📊 Overview",
                value=f"Total Jobs: {data.get('total_jobs', 0)}\n"
                      f"Matches: {data.get('total_matches', 0)}\n"
                      f"Proposals: {data.get('total_proposals', 0)}\n"
                      f"Win Rate: {data.get('win_rate', '0%')}",
                inline=True
            )
            
            embed.add_field(
                name="⏰ Cycle",
                value=f"Current: {data.get('cycle', 0)}",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check bot latency"""
        await ctx.send(f"🏓 Pong! Latency: {self.bot.latency * 1000:.0f}ms")
    
    @commands.command(name="help")
    async def help_cmd(self, ctx):
        """Show help"""
        embed = discord.Embed(
            title="🎯 Freelance Hunter Commands",
            color=0xff6b35
        )
        
        commands_list = """
**General:**
!status - Platform status
!ping - Check latency

**Jobs:**
!jobs - List recent jobs
!hot - Show hot jobs
!job <id> - Get job details

**Proposals:**
!proposals - List proposals
!proposal <id> - Get proposal
!send <id> - Mark as sent
!won <id> - Mark as won
!lost <id> - Mark as lost

**Actions:**
!scrape - Force scrape
!match - Force matching
!sync - Sync sheets
        """
        
        embed.add_field(name="Commands", value=commands_list, inline=False)
        
        await ctx.send(embed=embed)


class JobsCog(commands.Cog):
    """Job-related commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="jobs")
    async def list_jobs(self, ctx, limit: int = 10):
        """List recent jobs"""
        try:
            response = requests.get(
                f"{self.bot.api_url}/api/jobs",
                params={"limit": limit},
                timeout=10
            )
            data = response.json()
            
            jobs = data.get("jobs", [])
            
            if not jobs:
                await ctx.send("No jobs found")
                return
            
            embed = discord.Embed(
                title=f"💼 Recent Jobs ({len(jobs)})",
                color=0xff6b35
            )
            
            for job in jobs[:10]:
                title = job.get("title", "N/A")[:50]
                platform = job.get("platform", "N/A")
                budget = job.get("budget", "Negotiable")
                
                embed.add_field(
                    name=title,
                    value=f"{platform} | {budget}\nID: {job.get('id', 'N/A')}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="hot")
    async def hot_jobs(self, ctx):
        """Show hot jobs"""
        try:
            response = requests.get(
                f"{self.bot.api_url}/api/hot",
                params={"threshold": 0.6},
                timeout=10
            )
            data = response.json()
            
            jobs = data.get("jobs", [])
            
            if not jobs:
                await ctx.send("No hot jobs found")
                return
            
            embed = discord.Embed(
                title=f"🔥 Hot Jobs ({len(jobs)})",
                color=0xff4757
            )
            
            for job in jobs[:10]:
                title = job.get("title", "N/A")[:60]
                score = job.get("score", 0)
                budget = job.get("budget", "Negotiable")
                
                embed.add_field(
                    name=f"{title}",
                    value=f"Match: {score:.0%} | {budget}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="job")
    async def job_details(self, ctx, job_id: str):
        """Get job details"""
        try:
            response = requests.get(
                f"{self.bot.api_url}/api/jobs/{job_id}",
                timeout=10
            )
            
            if response.status_code == 404:
                await ctx.send("Job not found")
                return
            
            job = response.json()
            
            embed = discord.Embed(
                title=job.get("title", "Job Details"),
                color=0xff6b35,
                url=job.get("url", "")
            )
            
            embed.add_field(
                name="Platform",
                value=job.get("platform", "N/A"),
                inline=True
            )
            
            embed.add_field(
                name="Budget",
                value=job.get("budget", "Negotiable"),
                inline=True
            )
            
            skills = ", ".join(job.get("skills", [])[:5])
            embed.add_field(
                name="Skills",
                value=skills or "None listed",
                inline=False
            )
            
            desc = job.get("description", "No description")[:500]
            embed.add_field(
                name="Description",
                value=desc,
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="platform")
    async def platform_jobs(self, ctx, platform: str):
        """List jobs from specific platform"""
        try:
            response = requests.get(
                f"{self.bot.api_url}/api/jobs",
                params={"platform": platform.lower()},
                timeout=10
            )
            data = response.json()
            
            jobs = data.get("jobs", [])
            
            embed = discord.Embed(
                title=f"💼 {platform.title()} Jobs ({len(jobs)})",
                color=0xff6b35
            )
            
            for job in jobs[:10]:
                title = job.get("title", "N/A")[:50]
                budget = job.get("budget", "Negotiable")
                
                embed.add_field(
                    name=title,
                    value=budget,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error: {e}")


class ProposalsCog(commands.Cog):
    """Proposal-related commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="proposals")
    async def list_proposals(self, ctx):
        """List all proposals"""
        try:
            response = requests.get(
                f"{self.bot.api_url}/api/proposals",
                timeout=10
            )
            data = response.json()
            
            proposals = data.get("proposals", [])
            
            if not proposals:
                await ctx.send("No proposals found")
                return
            
            # Count by status
            by_status = {}
            for p in proposals:
                status = p.get("status", "draft")
                by_status[status] = by_status.get(status, 0) + 1
            
            embed = discord.Embed(
                title=f"📝 Proposals ({len(proposals)})",
                color=0xff6b35
            )
            
            status_str = "\n".join([f"{k}: {v}" for k, v in by_status.items()])
            embed.add_field(name="By Status", value=status_str, inline=False)
            
            # Recent proposals
            recent = "\n".join([
                f"• {p.get('job_title', 'N/A')[:40]} - {p.get('status', 'draft')}"
                for p in proposals[:5]
            ])
            embed.add_field(name="Recent", value=recent, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="send")
    async def send_proposal(self, ctx, proposal_id: str):
        """Mark proposal as sent"""
        try:
            response = requests.put(
                f"{self.bot.api_url}/api/proposals/{proposal_id}/status",
                json={"status": "sent"},
                timeout=10
            )
            
            if response.status_code == 200:
                await ctx.send(f"✅ Proposal {proposal_id} marked as sent!")
            else:
                await ctx.send(f"❌ Error updating proposal")
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="won")
    async def won_proposal(self, ctx, proposal_id: str):
        """Mark proposal as won"""
        try:
            response = requests.put(
                f"{self.bot.api_url}/api/proposals/{proposal_id}/status",
                json={"status": "won"},
                timeout=10
            )
            
            if response.status_code == 200:
                await ctx.send(f"🎉 Proposal {proposal_id} marked as WON!")
            else:
                await ctx.send(f"❌ Error updating proposal")
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="lost")
    async def lost_proposal(self, ctx, proposal_id: str):
        """Mark proposal as lost"""
        try:
            response = requests.put(
                f"{self.bot.api_url}/api/proposals/{proposal_id}/status",
                json={"status": "lost"},
                timeout=10
            )
            
            if response.status_code == 200:
                await ctx.send(f"😢 Proposal {proposal_id} marked as lost")
            else:
                await ctx.send(f"❌ Error updating proposal")
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="scrape")
    async def force_scrape(self, ctx):
        """Force scraping"""
        try:
            await ctx.send("🔄 Running scrape...")
            
            response = requests.post(
                f"{self.bot.api_url}/api/scheduler/run",
                json={"task": "scrape"},
                timeout=180
            )
            
            if response.status_code == 200:
                data = response.json()
                await ctx.send(f"✅ Scraped! Found {data.get('jobs_found', 0)} jobs")
            else:
                await ctx.send("❌ Scrape failed")
            
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="sync")
    async def sync_sheets(self, ctx):
        """Sync with Google Sheets"""
        try:
            await ctx.send("🔄 Syncing sheets...")
            
            response = requests.post(
                f"{self.bot.api_url}/sheets/sync",
                timeout=60
            )
            
            if response.status_code == 200:
                await ctx.send("✅ Sheets synced!")
            else:
                await ctx.send("❌ Sync failed")
            
        except Exception as e:
            await ctx.send(f"Error: {e}")


# Run bot

def run_bot():
    """Run the Discord bot"""
    
    if not CONFIG["discord_token"]:
        logger.error("DISCORD_BOT_TOKEN not set!")
        return
    
    bot = FreelanceHunterBot()
    
    try:
        bot.run(CONFIG["discord_token"])
    except Exception as e:
        logger.error(f"Bot error: {e}")


if __name__ == "__main__":
    run_bot()
```

## Discord Commands

### General

| Command | Description |
|---------|-------------|
| `!status` | Show platform status |
| `!ping` | Check latency |
| `!help` | Show help |

### Jobs

| Command | Description |
|---------|-------------|
| `!jobs` | List recent jobs |
| `!hot` | Show hot jobs |
| `!job <id>` | Get job details |
| `!platform <name>` | Jobs from platform |

### Proposals

| Command | Description |
|---------|-------------|
| `!proposals` | List all proposals |
| `!send <id>` | Mark as sent |
| `!won <id>` | Mark as won |
| `!lost <id>` | Mark as lost |

### Actions

| Command | Description |
|---------|-------------|
| `!scrape` | Force scrape |
| `!sync` | Sync Sheets |

## Setup

```bash
# Create Discord Application
# 1. Go to https://discord.com/developers/applications
# 2. Create new application
# 3. Add Bot -> Reset Token
# 4. Enable MESSAGE CONTENT intent
# 5. Copy token

# Set environment variable
export DISCORD_BOT_TOKEN="your_token_here"

# Run bot
cd /opt/freelance-hunter
source venv/bin/activate
python discord/bot.py

# Add bot to server
# 1. OAuth2 -> URL Generator
# 2. Scopes: bot
# 3. Permissions: Send Messages, Read Message History
# 4. Copy URL and open
```

## Environment Variables

```bash
export DISCORD_BOT_TOKEN="MTE..."
export DISCORD_GUILD_ID="123456789"
```

## Next Steps

- [11-installation](./11-installation.md) - Complete installation guide
