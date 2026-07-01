# Creative Studio - Project Integration

## Overview

This guide shows how to integrate Creative Studio with all previous projects, creating powerful end-to-end AI workflows.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CREATIVE STUDIO INTEGRATIONS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PROJECT 6    │  │ PROJECT 7    │  │ PROJECT 8    │  │ PROJECT 9    │    │
│  │ VIDEO STUDIO │  │ INNOVALABS  │  │FUNDING FIND │  │  AI OFFICE  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│    Story-to-Video    Script-to-Video    Video Proposals    Agent Videos   │
│         │                 │                 │                 │            │
│         └─────────────────┼─────────────────┼─────────────────┘            │
│                           │                 │                              │
│                    ┌──────┴─────────────────┴───────┐                       │
│                    │    CREATIVE STUDIO API         │                       │
│                    │         (Port 8083)           │                       │
│                    └───────────────────────────────┘                       │
│                                       │                                     │
│  ┌──────────────┐  ┌──────────────┐  │  ┌──────────────┐  ┌──────────┐   │
│  │ PROJECT 10   │  │ PROJECT 11    │  │  │  OLLAMA      │  │ COMFYUI  │   │
│  │ TOURISM INTEL│  │FREELANCE HUNT│◄─┘  │  PROMPTS    │  │ WORKFLOWS│   │
│  └──────────────┘  └──────────────┘     └──────────────┘  └──────────┘   │
│                                                                             │
│  Video Reports    Job Videos     Prompt Enhance    Custom Nodes           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Integration 1: Project 6 (Video Studio) Enhancement

Enhance the original Video Studio with LTX-2.3:

```python
#!/usr/bin/env python3
"""
Enhanced Video Studio with LTX-2.3
"""

from creative_studio import TextToVideoGenerator, ImageToVideoGenerator


class EnhancedVideoStudio:
    """Enhanced Video Studio with LTX-2.3"""
    
    def __init__(self):
        self.t2v = TextToVideoGenerator()
        self.i2v = ImageToVideoGenerator()
    
    def story_to_video(self, story: str, scenes: int = 5) -> dict:
        """Convert story to video using LTX-2.3"""
        
        # Split story into scenes
        scenes_list = self.split_into_scenes(story, scenes)
        
        # Generate each scene
        videos = []
        for scene in scenes_list:
            result = self.t2v.generate(
                prompt=scene,
                duration=5,
                enhance_prompt=True
            )
            videos.append(result["output_file"])
        
        # Combine into final video
        final = self.combine_scenes(videos)
        
        return {"status": "success", "output": final}
    
    def image_sequence_to_video(self, images: list) -> dict:
        """Convert image sequence to video"""
        
        clips = []
        
        for img in images:
            result = self.i2v.generate(
                image=img,
                prompt="Smooth camera movement",
                duration=3
            )
            clips.append(result["output_file"])
        
        return {"clips": clips}
```

## Integration 2: Project 7 (INNOVALABS) - Video Proposals

```python
#!/usr/bin/env python3
"""
INNOVALABS Video Proposal Integration
"""

from creative_studio import TextToVideoGenerator
from innovalabs import StoryGenerator, AgentPipeline


class VideoProposalGenerator:
    """Generate video proposals for INNOVALABS"""
    
    def __init__(self):
        self.t2v = TextToVideoGenerator()
        self.story_gen = StoryGenerator()
    
    def create_proposal_video(
        self,
        topic: str,
        script: str,
        visuals_style: str = "cinematic"
    ) -> dict:
        """Create promotional video for proposal"""
        
        # Generate keyframes from script
        keyframes = self.story_gen.extract_keyframes(script, count=5)
        
        # Generate video clips
        clips = []
        for kf in keyframes:
            result = self.t2v.generate(
                prompt=f"{kf} {visuals_style} style",
                duration=3,
                enhance_prompt=True
            )
            clips.append(result["output_file"])
        
        # Combine and add narration audio
        final_video = self.combine_with_audio(clips, script)
        
        return {
            "status": "success",
            "video": final_video,
            "keyframes": keyframes
        }
    
    def create_testimonial_video(
        self,
        client_name: str,
        testimonial_text: str,
        background_theme: str = "corporate"
    ) -> dict:
        """Create testimonial video"""
        
        prompt = f"Professional testimonial background, {background_theme}, clean minimal design, {client_name}"
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=30,
            resolution="1920x1080"
        )
        
        return {"video": result["output_file"]}
```

## Integration 3: Project 8 (Funding Finder) - Video Reports

```python
#!/usr/bin/env python3
"""
Funding Finder Video Reports
"""

from creative_studio import TextToVideoGenerator


class VideoReportGenerator:
    """Generate video reports for Funding Finder"""
    
    def __init__(self):
        self.t2v = TextToVideoGenerator()
    
    def create_funding_opportunity_video(
        self,
        opportunity: dict
    ) -> dict:
        """Create video for funding opportunity"""
        
        prompt = f"""{opportunity['title']}, {opportunity['description']}, 
        professional corporate animation, business data visualization"""
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=15,
            resolution="1920x1080"
        )
        
        return {
            "status": "success",
            "video": result["output_file"],
            "opportunity": opportunity["title"]
        }
    
    def create_daily_digest_video(
        self,
        opportunities: list
    ) -> dict:
        """Create daily digest video"""
        
        clips = []
        
        for opp in opportunities[:5]:
            result = self.t2v.generate(
                prompt=f"Funding opportunity: {opp['title']}, {opp['category']}",
                duration=5
            )
            clips.append(result["output_file"])
        
        # Combine
        final = self.combine_clips(clips)
        
        return {"video": final, "count": len(clips)}
```

## Integration 4: Project 9 (AI Office) - Agent Videos

```python
#!/usr/bin/env python3
"""
AI Office Video Integration
"""

from creative_studio import TextToVideoGenerator


class AgentVideoGenerator:
    """Generate videos for AI Office agents"""
    
    def __init__(self):
        self.t2v = TextToVideoGenerator()
    
    def create_agent_intro(self, agent_role: str) -> dict:
        """Create intro video for agent"""
        
        prompts = {
            "lead": "Professional leader in modern office, commanding presence",
            "frontend": "Creative designer working on UI, vibrant colors",
            "backend": "Developer writing code, matrix style background",
            "qa": "Quality inspector with magnifying glass, thorough",
            "content": "Content creator with ideas floating, creative",
            "scheduler": "Clock with gears, organized timeline, efficiency"
        }
        
        prompt = prompts.get(agent_role, "Professional worker")
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=5,
            resolution="1080x1920"  # Portrait for social
        )
        
        return {"intro_video": result["output_file"]}
    
    def create_status_update_video(
        self,
        agent_name: str,
        status: str,
        metrics: dict
    ) -> dict:
        """Create agent status video"""
        
        prompt = f"""Animated dashboard showing {agent_name} {status}, 
        data visualization, progress bars, success metrics"""
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=10
        )
        
        return {"status_video": result["output_file"]}
```

## Integration 5: Project 10 (Tourism Intel) - Video Reports

```python
#!/usr/bin/env python3
"""
Tourism Intelligence Video Reports
"""

from creative_studio import TextToVideoGenerator


class TourismVideoReports:
    """Generate video reports for Tourism Intelligence"""
    
    def create_city_highlight(self, city: str, stats: dict) -> dict:
        """Create city highlight video"""
        
        prompt = f"""Aerial drone view of {city} Colombia, stunning skyline, 
        tourist attractions, vibrant city life, cinematic drone shot"""
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=10,
            resolution="1920x1080"
        )
        
        return {"video": result["output_file"], "city": city}
    
    def create_hotel_showcase(self, hotel: dict) -> dict:
        """Create hotel showcase video"""
        
        prompt = f"""Luxury hotel {hotel['name']} in {hotel['location']}, 
        stunning architecture, pool area, elegant interiors"""
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=15
        )
        
        return {"showcase": result["output_file"]}
```

## Integration 6: Project 11 (Freelance Hunter) - Portfolio Videos

```python
#!/usr/bin/env python3
"""
Freelance Hunter Portfolio Videos
"""

from creative_studio import TextToVideoGenerator


class PortfolioVideoGenerator:
    """Generate portfolio videos for freelancers"""
    
    def create_skill_showcase(self, skill: str) -> dict:
        """Create skill showcase video"""
        
        prompts = {
            "python": "Python code floating, data processing visualization, tech aesthetic",
            "react": "React components building UI, modern web design",
            "cuda": "GPU computing visualization, neural networks, AI hardware",
            "docker": "Container ships, shipping containers, technology logistics"
        }
        
        prompt = prompts.get(skill.lower(), f"Professional {skill} work demonstration")
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=10,
            resolution="1920x1080"
        )
        
        return {"skill_video": result["output_file"]}
    
    def create_job_application_video(
        self,
        job: dict,
        proposal: str
    ) -> dict:
        """Create job application video"""
        
        prompt = f"""Professional portfolio showcase for {job['title']}, 
        {job['skills']}, clean modern design, corporate style"""
        
        result = self.t2v.generate(
            prompt=prompt,
            duration=30,
            resolution="1920x1080"
        )
        
        return {"application_video": result["output_file"]}
```

## Unified API Endpoint

```python
# Creative Studio Unified Integration API

@app.route("/api/integrate/<project>", methods=["POST"])
def integrate_with_project(project: str):
    """Unified endpoint for all project integrations"""
    
    data = request.get_json()
    
    if project == "video-studio":
        from integration.video_studio import EnhancedVideoStudio
        studio = EnhancedVideoStudio()
        return jsonify(studio.story_to_video(data.get("story")))
    
    elif project == "innovalabs":
        from integration.innovalabs import VideoProposalGenerator
        gen = VideoProposalGenerator()
        return jsonify(gen.create_proposal_video(data.get("topic"), data.get("script")))
    
    elif project == "funding-finder":
        from integration.funding import VideoReportGenerator
        gen = VideoReportGenerator()
        return jsonify(gen.create_funding_opportunity_video(data.get("opportunity")))
    
    # ... more integrations
    
    return jsonify({"error": "Unknown project"}), 400
```

## Example: Complete Workflow

```python
# Example: Create video proposal for freelance job

from creative_studio import TextToVideoGenerator
from freelance_hunter import ProposalGenerator
from piper_tts import AudioGenerator
from ffmpeg import FFmpeg

# 1. Get job details
job = get_job_from_freelancer("JOB123")

# 2. Generate proposal text
proposal = ProposalGenerator().generate(job)

# 3. Generate video
t2v = TextToVideoGenerator()
video = t2v.generate(
    prompt=f"Professional portfolio showcasing {job['skills']}, modern tech aesthetic",
    duration=15
)

# 4. Generate audio narration
audio = AudioGenerator().generate(proposal[:500])

# 5. Combine
FFmpeg.combine_video_audio(
    video=video["output_file"],
    audio=audio["output_file"],
    output="proposal_video.mp4"
)

# 6. Send to client
EmailClient().send(
    to=job["client_email"],
    subject=f"Proposal for {job['title']}",
    attachments=["proposal_video.mp4"]
)
```

## Next Steps

- [10-installation](./10-installation.md) - Complete setup guide
