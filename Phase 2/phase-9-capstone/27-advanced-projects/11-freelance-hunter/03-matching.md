# Freelance Hunter - RAG Job Matching

## Overview

The RAG (Retrieval-Augmented Generation) system matches incoming jobs against your skills profile, past successes, and preferences. It uses embeddings to find semantically similar jobs and ranks them by match score.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAG MATCHING SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │    JOBS      │    │   SKILLS     │    │   HISTORY    │     │
│  │   DATABASE   │    │   PROFILE    │    │   DATABASE   │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    │   INDEX BUILDER  │                          │
│                    │  (Embeddings)    │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    │   VECTOR STORE   │                          │
│                    │   (Chroma/FAISS) │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│         ┌───────────────────┼───────────────────┐               │
│         │                   │                   │               │
│  ┌──────┴───────┐   ┌──────┴───────┐   ┌──────┴───────┐       │
│  │  SEMANTIC    │   │   SKILL      │   │   BUDGET     │       │
│  │  SEARCH      │   │   MATCHER    │   │   FILTER     │       │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘       │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    │   RANKING      │                          │
│                    │    ENGINE       │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    │   JOB MATCHES   │                          │
│                    │   (Ranked List) │                          │
│                    └─────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Profile Configuration

```python
# config/profile.py

SKILLS_PROFILE = {
    "primary_skills": [
        "Python", "JavaScript", "React", "Node.js",
        "CUDA", "TensorRT", "Deep Learning",
        "Docker", "Kubernetes", "AWS"
    ],
    "secondary_skills": [
        "PostgreSQL", "MongoDB", "Redis",
        "GraphQL", "REST APIs", "FastAPI",
        "CI/CD", "Git", "Linux"
    ],
    "languages": {
        "English": "fluent",
        "Spanish": "native"
    },
    "experience_years": 8,
    "hourly_rate_min": 50,
    "hourly_rate_max": 150,
    "fixed_min": 500,
    "fixed_max": 15000,
    "preferences": {
        "remote_only": True,
        "escrow_required": True,
        "payment_verified": True,
        "min_client_rating": 4.0,
        "max_proposals": 20,
        "avoid_platforms": ["toptal"]  # Requires exclusive commitment
    },
    "job_types_accepted": ["hourly", "fixed"],
    "categories": [
        "web_development",
        "mobile_development", 
        "ai_ml",
        "devops",
        "api_development",
        "blockchain"
    ]
}


SUCCESSFUL_JOBS = [
    {
        "title": "Build REST API with FastAPI",
        "description": "Need experienced Python developer to build REST API...",
        "skills_used": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "rate": 75,
        "outcome": "completed"
    },
    {
        "title": "React Frontend Development",
        "description": "Looking for React developer for e-commerce site...",
        "skills_used": ["React", "JavaScript", "Node.js"],
        "rate": 80,
        "outcome": "completed"
    },
    {
        "title": "GPU Acceleration with CUDA",
        "description": "Need CUDA developer for image processing...",
        "skills_used": ["CUDA", "Python", "TensorRT"],
        "rate": 120,
        "outcome": "completed"
    }
]
```

## RAG Implementation

```python
#!/usr/bin/env python3
"""
RAG Job Matching System
Uses embeddings for semantic job matching
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "data_dir": "/opt/freelance-hunter/data",
    "embeddings_dir": "/opt/freelance-hunter/data/embeddings",
    "profile_file": "/opt/freelance-hunter/config/profile.py",
    "ollama_host": "http://localhost:11434",
    "embedding_model": "nomic-embed-text-v2-moe:latest",
    "top_k": 10,
    "min_match_score": 0.5
}

os.makedirs(CONFIG["embeddings_dir"], exist_ok=True)


@dataclass
class JobMatch:
    """Job match result"""
    job_id: str
    platform: str
    title: str
    url: str
    match_score: float
    skill_match: float
    semantic_score: float
    budget_match: float
    reasons: List[str]
    recommended_rate: Optional[float] = None


class ProfileManager:
    """Manages user profile"""
    
    def __init__(self):
        self.profile = self.load_profile()
    
    def load_profile(self) -> Dict:
        """Load skills profile"""
        # Load from file
        profile_file = Path(CONFIG["profile_file"])
        if profile_file.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("profile", profile_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, 'SKILLS_PROFILE', {})
        
        # Default profile
        return {
            "primary_skills": ["Python", "JavaScript"],
            "secondary_skills": [],
            "hourly_rate_min": 50,
            "hourly_rate_max": 100
        }
    
    def get_all_skills(self) -> List[str]:
        """Get all skills"""
        return self.profile.get("primary_skills", []) + \
               self.profile.get("secondary_skills", [])
    
    def get_rate_range(self) -> Tuple[float, float]:
        """Get rate range"""
        return (
            self.profile.get("hourly_rate_min", 50),
            self.profile.get("hourly_rate_max", 150)
        )


class EmbeddingManager:
    """Manages embeddings using Ollama"""
    
    def __init__(self):
        self.model = CONFIG["embedding_model"]
        self.ollama = CONFIG["ollama_host"]
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        import requests
        
        try:
            response = requests.post(
                f"{self.ollama}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=30
            )
            
            result = response.json()
            return result.get("embedding", [])
            
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            # Return zero vector as fallback
            return [0.0] * 768
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        return [self.get_embedding(t) for t in texts]
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity"""
        if not a or not b:
            return 0.0
        
        a = np.array(a)
        b = np.array(b)
        
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot / (norm_a * norm_b))


class RAGMatcher:
    """RAG-based job matching"""
    
    def __init__(self):
        self.profile = ProfileManager()
        self.embeddings = EmbeddingManager()
        self.job_index = {}
    
    def build_job_index(self, jobs: List[Dict]):
        """Build job index with embeddings"""
        logger.info(f"Building index for {len(jobs)} jobs")
        
        for job in jobs:
            job_id = job.get("id", "")
            
            # Create searchable text
            searchable = self.create_searchable_text(job)
            
            # Get embedding
            embedding = self.embeddings.get_embedding(searchable)
            
            # Store
            self.job_index[job_id] = {
                "job": job,
                "embedding": embedding,
                "searchable": searchable
            }
        
        logger.info(f"Index built with {len(self.job_index)} jobs")
    
    def create_searchable_text(self, job: Dict) -> str:
        """Create searchable text from job"""
        parts = [
            job.get("title", ""),
            job.get("description", ""),
            ", ".join(job.get("skills", [])),
            job.get("category", ""),
            job.get("budget", "")
        ]
        
        return " | ".join([p for p in parts if p])
    
    def match_jobs(self, jobs: List[Dict], top_k: int = 10) -> List[JobMatch]:
        """Match jobs to profile"""
        matches = []
        
        # Build index
        self.build_job_index(jobs)
        
        # Get profile embedding
        profile_text = " | ".join(self.profile.get_all_skills())
        profile_embedding = self.embeddings.get_embedding(profile_text)
        
        for job_id, data in self.job_index.items():
            job = data["job"]
            job_embedding = data["embedding"]
            
            # Calculate scores
            semantic_score = self.embeddings.cosine_similarity(
                profile_embedding, job_embedding
            )
            
            skill_score = self.calculate_skill_match(job)
            budget_score = self.calculate_budget_match(job)
            
            # Weighted final score
            final_score = (
                semantic_score * 0.4 +
                skill_score * 0.4 +
                budget_score * 0.2
            )
            
            if final_score >= CONFIG["min_match_score"]:
                match = JobMatch(
                    job_id=job_id,
                    platform=job.get("platform", ""),
                    title=job.get("title", ""),
                    url=job.get("url", ""),
                    match_score=final_score,
                    skill_match=skill_score,
                    semantic_score=semantic_score,
                    budget_match=budget_score,
                    reasons=self.generate_reasons(job, skill_score, budget_score),
                    recommended_rate=self.recommend_rate(job)
                )
                matches.append(match)
        
        # Sort by score
        matches.sort(key=lambda x: x.match_score, reverse=True)
        
        return matches[:top_k]
    
    def calculate_skill_match(self, job: Dict) -> float:
        """Calculate skill match score"""
        job_skills = [s.lower() for s in job.get("skills", [])]
        profile_skills = [s.lower() for s in self.profile.get_all_skills()]
        
        if not job_skills:
            return 0.0
        
        matches = sum(1 for js in job_skills if any(ps in js or js in ps for ps in profile_skills))
        
        # Bonus for primary skills
        primary_matches = sum(
            1 for js in job_skills 
            if any(ps in js for ps in [p.lower() for p in self.profile.get("primary_skills", [])])
        )
        
        score = matches / len(job_skills)
        score += primary_matches * 0.1
        
        return min(score, 1.0)
    
    def calculate_budget_match(self, job: Dict) -> float:
        """Calculate budget match score"""
        rate_min, rate_max = self.profile.get_rate_range()
        
        budget = job.get("budget", "")
        
        # Try to extract rate from budget
        import re
        
        hourly = re.search(r'\$(\d+)\s*(?:/hr|per hour|/h)', budget, re.I)
        if hourly:
            rate = float(hourly.group(1))
            if rate_min <= rate <= rate_max:
                return 1.0
            elif rate < rate_min:
                return max(0, 1 - (rate_min - rate) / rate_min)
            else:
                return max(0, 1 - (rate - rate_max) / rate_max)
        
        # Fixed price
        fixed = re.search(r'\$(\d+)', budget)
        if fixed:
            amount = float(fixed.group(1))
            # Assume 10-40 hours for fixed price
            implied_rate = amount / 25
            if rate_min <= implied_rate <= rate_max:
                return 0.8
            elif implied_rate < rate_min:
                return max(0, 1 - (rate_min - implied_rate) / rate_min)
            else:
                return max(0, 1 - (implied_rate - rate_max) / rate_max)
        
        return 0.5  # Unknown
    
    def generate_reasons(self, job: Dict, skill_score: float, budget_score: float) -> List[str]:
        """Generate match reasons"""
        reasons = []
        
        # Skill reasons
        job_skills = [s.lower() for s in job.get("skills", [])]
        matched_skills = []
        
        for skill in self.profile.get("primary_skills", []):
            if any(skill.lower() in js or js in skill.lower() for js in job_skills):
                matched_skills.append(skill)
        
        if matched_skills:
            reasons.append(f"Skills match: {', '.join(matched_skills[:3])}")
        
        if skill_score > 0.7:
            reasons.append("Strong skill alignment")
        
        # Budget reasons
        if budget_score > 0.8:
            reasons.append("Within your rate range")
        elif budget_score < 0.5:
            reasons.append("Below your minimum rate")
        
        # Other reasons
        if job.get("payment_verified"):
            reasons.append("Client payment verified")
        
        if job.get("proposals_count", 100) < 10:
            reasons.append("Low competition")
        
        return reasons
    
    def recommend_rate(self, job: Dict) -> Optional[float]:
        """Recommend rate for job"""
        rate_min, rate_max = self.profile.get_rate_range()
        
        # Use skills to determine rate
        primary_skills = self.profile.get("primary_skills", [])
        job_skills = [s.lower() for s in job.get("skills", [])]
        
        has_cuda = any("cuda" in js or "gpu" in js for js in job_skills)
        has_ml = any("ml" in js or "ai" in js or "learning" in js for js in job_skills)
        
        if has_cuda or has_ml:
            return rate_max  # High-value skills
        
        return (rate_min + rate_max) / 2


class JobFilter:
    """Filters jobs based on preferences"""
    
    def __init__(self):
        self.profile = ProfileManager()
    
    def filter_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs based on preferences"""
        prefs = self.profile.profile.get("preferences", {})
        
        filtered = []
        
        for job in jobs:
            # Remote filter
            if prefs.get("remote_only") and not job.get("remote", False):
                continue
            
            # Payment verified
            if prefs.get("payment_verified") and not job.get("payment_verified", False):
                continue
            
            # Client rating
            min_rating = prefs.get("min_client_rating", 0)
            if job.get("client_rating", 0) < min_rating:
                continue
            
            # Proposals count
            max_proposals = prefs.get("max_proposals", 100)
            if job.get("proposals_count", 0) > max_proposals:
                continue
            
            # Platform filter
            avoid = prefs.get("avoid_platforms", [])
            if job.get("platform") in avoid:
                continue
            
            # Budget filter
            rate_min, rate_max = self.profile.get_rate_range()
            if not self.budget_in_range(job, rate_min, rate_max):
                continue
            
            filtered.append(job)
        
        return filtered
    
    def budget_in_range(self, job: Dict, rate_min: float, rate_max: float) -> bool:
        """Check if budget is in range"""
        budget = job.get("budget", "")
        
        import re
        hourly = re.search(r'\$(\d+)', budget)
        if hourly:
            rate = float(hourly.group(1))
            return rate_min <= rate <= rate_max
        
        return True  # Can't determine, include anyway


# API Integration

def setup_matching_api(app):
    """Setup Flask API routes for matching"""
    
    matcher = RAGMatcher()
    job_filter = JobFilter()
    
    @app.route("/api/match", methods=["POST"])
    def match_jobs():
        """Match jobs to profile"""
        data = request.get_json()
        jobs = data.get("jobs", [])
        
        # Filter first
        filtered = job_filter.filter_jobs(jobs)
        
        # Match
        matches = matcher.match_jobs(filtered)
        
        return jsonify({
            "count": len(matches),
            "matches": [
                {
                    "job_id": m.job_id,
                    "platform": m.platform,
                    "title": m.title,
                    "url": m.url,
                    "score": m.match_score,
                    "reasons": m.reasons,
                    "recommended_rate": m.recommended_rate
                }
                for m in matches
            ]
        })
    
    @app.route("/api/match/<job_id>", methods=["GET"])
    def match_single_job(job_id):
        """Match single job"""
        # Load job from storage
        jobs_file = Path(CONFIG["data_dir"]) / "jobs" / "latest.json"
        
        if not jobs_file.exists():
            return jsonify({"error": "No jobs loaded"}), 404
        
        with open(jobs_file) as f:
            jobs = json.load(f)
        
        job = next((j for j in jobs if j.get("id") == job_id), None)
        
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Match
        matches = matcher.match_jobs([job], top_k=1)
        
        if matches:
            m = matches[0]
            return jsonify({
                "job_id": m.job_id,
                "score": m.match_score,
                "skill_match": m.skill_match,
                "reasons": m.reasons,
                "recommended_rate": m.recommended_rate
            })
        
        return jsonify({"score": 0, "reasons": ["No match"]})
    
    @app.route("/api/profile", methods=["GET"])
    def get_profile():
        """Get current profile"""
        return jsonify(matcher.profile.profile)
    
    @app.route("/api/profile", methods=["PUT"])
    def update_profile():
        """Update profile"""
        data = request.get_json()
        
        # Save to file
        profile_file = Path(CONFIG["profile_file"])
        profile_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Update and save
        matcher.profile.profile.update(data)
        
        import json
        with open(profile_file, "w") as f:
            json.dump(matcher.profile.profile, f, indent=2)
        
        return jsonify({"status": "updated"})
```

## Semantic Search Example

```python
# Example: Semantic search for similar jobs

matcher = RAGMatcher()

# Jobs in database
jobs = [
    {"title": "Python FastAPI Developer", "skills": ["Python", "FastAPI"]},
    {"title": "React Frontend Engineer", "skills": ["React", "JavaScript"]},
    {"title": "CUDA GPU Developer", "skills": ["CUDA", "Python", "GPU"]},
]

# Find similar to successful job
query_job = {"title": "Build ML Pipeline", "skills": ["Python", "ML"]}

# Get query embedding
query_text = " | ".join([query_job["title"], ", ".join(query_job["skills"])])
query_embedding = matcher.embeddings.get_embedding(query_text)

# Find similar
results = []
for job in jobs:
    job_text = " | ".join([job["title"], ", ".join(job["skills"])])
    job_embedding = matcher.embeddings.get_embedding(job_text)
    
    score = matcher.embeddings.cosine_similarity(query_embedding, job_embedding)
    results.append((job, score))

results.sort(key=lambda x: x[1], reverse=True)

print("Similar jobs:")
for job, score in results[:3]:
    print(f"  {job['title']}: {score:.2f}")
```

## Next Steps

- [04-proposals](./04-proposals.md) - Auto-proposal generation
