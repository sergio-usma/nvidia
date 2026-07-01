# Freelance Hunter - Auto-Proposal Generation

## Overview

The proposal generation system creates customized cover letters and proposals for matched jobs using AI. It analyzes job requirements, matches them to your skills, and generates compelling proposals.

## Proposal Templates

```python
# config/templates.py

PROPOSAL_TEMPLATES = {
    "hourly": {
        "subject": "Expert {skill} Developer for {job_title}",
        "template": """Dear {client_name},

I came across your project posting for {job_title} and I'm excited to submit my proposal.

**Why I'm the Perfect Fit:**

{skill_match}

With {years} years of experience in {primary_skills}, I've successfully delivered similar projects. My expertise in {relevant_experience} makes me confident I can exceed your expectations.

**My Approach:**

{approach}

**Availability:**
- {availability}
- Communication: {response_time}

**Portfolio:**
{portfolio_links}

I'm available for a quick call to discuss your project in detail.

Best regards,
{your_name}"""
    },
    
    "fixed": {
        "subject": "Professional {job_title} - {experience} Developer",
        "template": """Hello {client_name},

Thank you for considering my proposal for {job_title}.

**Project Understanding:**
{project_understanding}

**Solution:**
{proposed_solution}

**Timeline:**
{proposed_timeline}

**Investment:**
{fixed_price} (includes {revisions} revisions)

**Why Me:**
{unique_value}

Looking forward to working with you!

{your_name}"""
    },
    
    "urgent": {
        "subject": "Ready to Start Now - {job_title}",
        "template": """Hi {client_name},

I can start on your {job_title} immediately! 
{availability_note}

Given the urgency, here's my commitment:
- Deliver within {urgent_timeline}
- {urgent_commitment}

{quick_intro}

Let's get started!

{your_name}"""
    }
}


SAMPLE_INTROS = [
    "I'm a senior full-stack developer with 8+ years of experience.",
    "As a specialized Python developer, I've built 50+ production applications.",
    "With expertise in {primary_skill}, I can deliver high-quality results.",
    "I'm a {experience_level} developer passionate about building scalable solutions."
]


APPROACH_TEMPLATES = {
    "web_development": "I'll start with a detailed requirements analysis, then build a clean, performant solution following best practices. Regular updates and testing at each stage.",
    "api_development": "I'll design a RESTful/GraphQL API with proper documentation, authentication, and error handling. Comprehensive unit tests included.",
    "mobile_development": "I'll create a native-quality mobile app with smooth UX, proper state management, and App Store-ready code.",
    "ml_ai": "I'll implement the ML pipeline with data preprocessing, model training, and deployment. Full documentation and optimization included.",
    "devops": "I'll analyze your infrastructure, then implement CI/CD pipelines, containerization, and monitoring for reliable deployments.",
    "custom": "I'll break down your requirements, create a detailed plan, and deliver incrementally with full testing and documentation."
}
```

## Proposal Generator

```python
#!/usr/bin/env python3
"""
AI Proposal Generator
Generates customized proposals for freelance jobs
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/freelance-hunter/data",
    "proposals_dir": "/opt/freelance-hunter/data/proposals",
    "templates_file": "/opt/freelance-hunter/config/templates.py",
    "profile_file": "/opt/freelance-hunter/config/profile.py",
    "ollama_host": "http://localhost:11434",
    "default_model": "qwen2.5-coder:14b",
    "fast_model": "glm-4.7-flash:latest"
}

os.makedirs(CONFIG["proposals_dir"], exist_ok=True)


class ProposalGenerator:
    """Generates AI-powered proposals"""
    
    def __init__(self):
        self.templates = self.load_templates()
        self.profile = self.load_profile()
        self.ollama = CONFIG["ollama_host"]
        self.model = CONFIG["default_model"]
    
    def load_templates(self) -> Dict:
        """Load proposal templates"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("templates", CONFIG["templates_file"])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, 'PROPOSAL_TEMPLATES', {})
        except:
            return {}
    
    def load_profile(self) -> Dict:
        """Load user profile"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("profile", CONFIG["profile_file"])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, 'SKILLS_PROFILE', {})
        except:
            return {}
    
    def generate_with_ai(self, job: Dict, match_data: Dict) -> str:
        """Generate proposal using AI"""
        
        prompt = self.build_proposal_prompt(job, match_data)
        
        try:
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_ctx": 4096,
                        "num_predict": 1500
                    }
                },
                timeout=120
            )
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return self.generate_template_based(job, match_data)
    
    def build_proposal_prompt(self, job: Dict, match_data: Dict) -> str:
        """Build prompt for AI generation"""
        
        skills = ", ".join(self.profile.get("primary_skills", [])[:5])
        years = self.profile.get("experience_years", 5)
        
        prompt = f"""Generate a professional freelance proposal for this job:

**Job Title:** {job.get('title', 'N/A')}
**Platform:** {job.get('platform', 'N/A')}
**Budget:** {job.get('budget', 'Negotiable')}
**Description:** {job.get('description', '')[:500]}

**Required Skills:** {', '.join(job.get('skills', []))}
**My Skills:** {skills}

**Match Score:** {match_data.get('score', 0):.2f}
**Why I Match:** {'; '.join(match_data.get('reasons', [])[:3])}

Generate a 200-300 word proposal that:
1. Shows understanding of the project
2. Highlights relevant skills and experience
3. Explains the approach
4. Includes timeline and rate
5. Has a professional closing

Write in {self.profile.get('languages', {}).get('English', 'English')}."""
        
        return prompt
    
    def generate_template_based(self, job: Dict, match_data: Dict) -> str:
        """Generate proposal using template (fallback)"""
        
        job_type = "hourly" if "hourly" in job.get("budget", "").lower() else "fixed"
        
        template = self.templates.get(job_type, self.templates.get("hourly"))
        
        # Fill template
        proposal = template["template"].format(
            client_name="Client",
            job_title=job.get("title", "your project"),
            skill_match=", ".join(match_data.get("reasons", ["Expert in required skills"])[:2]),
            years=self.profile.get("experience_years", 5),
            primary_skills=", ".join(self.profile.get("primary_skills", [])[:3]),
            relevant_experience="building similar applications",
            approach=APPROACH_TEMPLATES.get("custom", APPROACH_TEMPLATES["web_development"]),
            availability="Full-time, 40 hrs/week",
            response_time="Within 2 hours",
            portfolio_links="Available upon request",
            your_name="Your Name"
        )
        
        return proposal
    
    def generate_proposal(self, job: Dict, match_data: Dict) -> Dict:
        """Generate complete proposal"""
        
        # Check if should use AI or template
        use_ai = len(job.get("description", "")) > 200
        
        if use_ai:
            content = self.generate_with_ai(job, match_data)
        else:
            content = self.generate_template_based(job, match_data)
        
        # Determine rate
        recommended_rate = match_data.get("recommended_rate")
        rate = recommended_rate or self.profile.get("hourly_rate_min", 50)
        
        # Generate subject
        subject = self.generate_subject(job)
        
        proposal = {
            "id": f"PROP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "job_id": job.get("id"),
            "platform": job.get("platform"),
            "job_title": job.get("title"),
            "subject": subject,
            "content": content,
            "proposed_rate": rate,
            "estimated_hours": self.estimate_hours(job),
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "match_score": match_data.get("score", 0)
        }
        
        # Save proposal
        self.save_proposal(proposal)
        
        return proposal
    
    def generate_subject(self, job: Dict) -> str:
        """Generate proposal subject line"""
        
        primary = self.profile.get("primary_skills", ["Developer"])[0]
        
        templates = [
            f"Expert {primary} Developer - {job.get('title')}",
            f"Ready to build your {job.get('title')} project",
            f"{job.get('title')} - Professional Developer Proposal"
        ]
        
        return templates[0]
    
    def estimate_hours(self, job: Dict) -> int:
        """Estimate hours for job"""
        description = job.get("description", "")
        
        # Simple heuristic
        length = len(description)
        
        if length < 200:
            return 5
        elif length < 500:
            return 10
        elif length < 1000:
            return 20
        else:
            return 40
    
    def save_proposal(self, proposal: Dict):
        """Save proposal to disk"""
        
        # Save individual
        proposal_file = Path(CONFIG["proposals_dir"]) / f"{proposal['id']}.json"
        with open(proposal_file, "w") as f:
            json.dump(proposal, f, indent=2)
        
        # Update index
        index_file = Path(CONFIG["proposals_dir"]) / "index.json"
        
        if index_file.exists():
            with open(index_file) as f:
                index = json.load(f)
        else:
            index = {"proposals": []}
        
        index["proposals"].append({
            "id": proposal["id"],
            "job_id": proposal["job_id"],
            "platform": proposal["platform"],
            "status": proposal["status"],
            "created_at": proposal["created_at"]
        })
        
        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)


class QAProposal:
    """Quality assurance for proposals"""
    
    def __init__(self):
        self.min_score = 0.5
    
    def review_proposal(self, proposal: Dict, job: Dict) -> Dict:
        """Review proposal quality"""
        
        issues = []
        score = 1.0
        
        # Check length
        content = proposal.get("content", "")
        if len(content) < 100:
            issues.append("Too short")
            score -= 0.3
        elif len(content) > 500:
            issues.append("Too long")
            score -= 0.1
        
        # Check for required elements
        required = ["experience", "skills", "timeline"]
        for req in required:
            if req.lower() not in content.lower():
                issues.append(f"Missing: {req}")
                score -= 0.15
        
        # Check rate
        rate = proposal.get("proposed_rate", 0)
        if rate == 0:
            issues.append("No rate specified")
            score -= 0.2
        
        # Check match
        match = proposal.get("match_score", 0)
        if match < 0.3:
            issues.append("Low job match")
            score -= 0.2
        
        return {
            "score": max(0, score),
            "issues": issues,
            "approved": score >= self.min_score,
            "recommendations": self.get_recommendations(issues)
        }
    
    def get_recommendations(self, issues: List[str]) -> List[str]:
        """Get recommendations to fix issues"""
        
        recs = []
        
        if any("short" in i for i in issues):
            recs.append("Add more details about your relevant experience")
        
        if any("rate" in i for i in issues):
            recs.append("Include your hourly rate or fixed price")
        
        if any("timeline" in i for i in issues):
            recs.append("Add estimated timeline for completion")
        
        if not recs:
            recs.append("Proposal looks good!")
        
        return recs


class ProposalTracker:
    """Tracks proposal status and outcomes"""
    
    def __init__(self):
        self.proposals_dir = Path(CONFIG["proposals_dir"])
    
    def update_status(self, proposal_id: str, status: str, notes: str = ""):
        """Update proposal status"""
        
        proposal_file = self.proposals_dir / f"{proposal_id}.json"
        
        if not proposal_file.exists():
            return {"error": "Proposal not found"}
        
        with open(proposal_file) as f:
            proposal = json.load(f)
        
        proposal["status"] = status
        proposal["updated_at"] = datetime.now().isoformat()
        
        if notes:
            proposal["notes"] = notes
        
        with open(proposal_file, "w") as f:
            json.dump(proposal, f, indent=2)
        
        return {"status": "updated"}
    
    def get_stats(self) -> Dict:
        """Get proposal statistics"""
        
        index_file = self.proposals_dir / "index.json"
        
        if not index_file.exists():
            return {"total": 0}
        
        with open(index_file) as f:
            index = json.load(f)
        
        proposals = index.get("proposals", [])
        
        stats = {
            "total": len(proposals),
            "draft": len([p for p in proposals if p["status"] == "draft"]),
            "sent": len([p for p in proposals if p["status"] == "sent"]),
            "pending": len([p for p in proposals if p["status"] == "pending"]),
            "won": len([p for p in proposals if p["status"] == "won"]),
            "lost": len([p for p in proposals if p["status"] == "lost"])
        }
        
        return stats
    
    def get_pending(self) -> List[Dict]:
        """Get pending proposals"""
        
        index_file = self.proposals_dir / "index.json"
        
        if not index_file.exists():
            return []
        
        with open(index_file) as f:
            index = json.load(f)
        
        pending = []
        
        for p in index.get("proposals", []):
            if p["status"] in ["draft", "sent"]:
                proposal_file = self.proposals_dir / f"{p['id']}.json"
                if proposal_file.exists():
                    with open(proposal_file) as f:
                        pending.append(json.load(f))
        
        return pending


# API Integration

def setup_proposal_api(app):
    """Setup Flask API routes"""
    
    generator = ProposalGenerator()
    qa = QAProposal()
    tracker = ProposalTracker()
    
    @app.route("/api/proposals/generate", methods=["POST"])
    def generate_proposal():
        """Generate proposal for job"""
        data = request.get_json()
        job = data.get("job")
        match_data = data.get("match", {})
        
        proposal = generator.generate_proposal(job, match_data)
        
        return jsonify(proposal)
    
    @app.route("/api/proposals/<proposal_id>/review", methods=["GET"])
    def review_proposal(proposal_id):
        """Review proposal quality"""
        proposal_file = Path(CONFIG["proposals_dir"]) / f"{proposal_id}.json"
        
        if not proposal_file.exists():
            return jsonify({"error": "Not found"}), 404
        
        with open(proposal_file) as f:
            proposal = json.load(f)
        
        # Load job
        jobs_file = Path(CONFIG["data_dir"]) / "jobs" / "latest.json"
        job = {}
        
        if jobs_file.exists():
            with open(jobs_file) as f:
                jobs = json.load(f)
            job = next((j for j in jobs if j.get("id") == proposal.get("job_id")), {})
        
        review = qa.review_proposal(proposal, job)
        
        return jsonify(review)
    
    @app.route("/api/proposals/<proposal_id>/send", methods=["POST"])
    def send_proposal(proposal_id):
        """Mark proposal as sent"""
        data = request.get_json() or {}
        notes = data.get("notes", "")
        
        result = tracker.update_status(proposal_id, "sent", notes)
        
        return jsonify(result)
    
    @app.route("/api/proposals/<proposal_id>/status", methods=["PUT"])
    def update_proposal_status(proposal_id):
        """Update proposal status"""
        data = request.get_json()
        
        status = data.get("status", "draft")
        notes = data.get("notes", "")
        
        result = tracker.update_status(proposal_id, status, notes)
        
        return jsonify(result)
    
    @app.route("/api/proposals/stats", methods=["GET"])
    def get_proposal_stats():
        """Get proposal statistics"""
        return jsonify(tracker.get_stats())
    
    @app.route("/api/proposals/pending", methods=["GET"])
    def get_pending_proposals():
        """Get pending proposals"""
        return jsonify(tracker.get_pending())
    
    @app.route("/api/proposals/<proposal_id>", methods=["GET"])
    def get_proposal(proposal_id):
        """Get specific proposal"""
        proposal_file = Path(CONFIG["proposals_dir"]) / f"{proposal_id}.json"
        
        if not proposal_file.exists():
            return jsonify({"error": "Not found"}), 404
        
        with open(proposal_file) as f:
            return jsonify(json.load(f))
```

## Next Steps

- [05-agents](./05-agents.md) - Agent implementations
