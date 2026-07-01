# Funding Finder - Multi-Agent Proposal Generation

## Overview

The proposal generation system uses 6 specialized AI agents working in parallel to create comprehensive project proposals based on funding opportunity requirements.

## Agent Architecture

### Agent Roles

| Agent | Model | Function | Parallel |
|-------|-------|----------|----------|
| **Project Lead** | qwen2.5-coder:14b | Define vision, objectives, outcomes | Yes |
| **Technical Writer** | llama3.2:3b | Create technical documentation | Yes |
| **Budget Expert** | glm-4.7-flash | Build financial projections | Yes |
| **Compliance Analyst** | deepseek-r1:8b | Ensure requirement adherence | Yes |
| **Legal Reviewer** | qwen2.5-coder:14b | Check legal constraints | Yes |
| **Final Reviewer** | llama3.2:3b | Quality assurance | No (last) |

### Parallel Processing

```
                    ┌─────────────────────────────────────────┐
                    │         OPPORTUNITY RECEIVED            │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │     RAG SYSTEM (Load Context)         │
                    │   - Requirements                       │
                    │   - Deadlines                          │
                    │   - Budget limits                      │
                    │   - Previous successful proposals       │
                    └──────────────────┬──────────────────────┘
                                       │
         ┌─────────────┬───────────────┼───────────────┬─────────────┐
         │             │               │               │             │
         ▼             ▼               ▼               ▼             ▼
    ┌─────────┐  ┌──────────┐   ┌───────────┐   ┌─────────────┐  ┌──────────┐
    │ Project │  │Technical │   │  Budget   │   │ Compliance  │  │  Legal   │
    │  Lead   │  │ Writer   │   │  Expert   │   │  Analyst    │  │Reviewer  │
    └────┬────┘  └────┬─────┘   └─────┬─────┘   └──────┬──────┘  └────┬─────┘
         │             │               │               │             │
         └─────────────┴───────────────┼───────────────┴─────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │         FINAL REVIEWER                  │
                    │   - Assemble final proposal             │
                    │   - Create ZIP package                 │
                    │   - Prepare for delivery                │
                    └─────────────────────────────────────────┘
```

## Agent Implementation

### Base Agent Class

```python
#!/usr/bin/env python3
"""
Base Agent Class for Funding Finder
"""

import os
import json
import logging
import requests
from typing import Dict, Optional, List
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "timeout": 300
}


class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, agent_name: str, model: str):
        self.agent_name = agent_name
        self.model = model
        self.ollama = CONFIG["ollama_host"]
        
    def generate(self, prompt: str, temperature: float = 0.3, 
                 max_tokens: int = 4000) -> str:
        """Generate response using Ollama"""
        
        try:
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_ctx": 8192,
                        "num_predict": max_tokens
                    }
                },
                timeout=CONFIG["timeout"]
            )
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"{self.agent_name} generation error: {e}")
            raise
    
    @abstractmethod
    def process(self, context: Dict) -> Dict:
        """Process context and generate output"""
        pass
```

### Project Lead Agent

```python
class ProjectLeadAgent(BaseAgent):
    """Defines project vision, objectives, and outcomes"""
    
    def __init__(self):
        super().__init__("Project Lead", "qwen2.5-coder:14b")
    
    def process(self, context: Dict) -> Dict:
        """Generate project vision and objectives"""
        
        opportunity = context.get("opportunity", {})
        requirements = context.get("requirements", "")
        
        prompt = f"""You are a senior project manager creating a funding proposal.
Based on the following opportunity and requirements:

OPPORTUNITY:
- Title: {opportunity.get('title', '')}
- Source: {opportunity.get('source', '')}
- Deadline: {opportunity.get('deadline', '')}
- Budget: {opportunity.get('budget', '')}
- Category: {opportunity.get('category', '')}

REQUIREMENTS:
{requirements[:2000]}

Create a project vision and objectives section including:
1. Project title (compelling and aligned with funder priorities)
2. Vision statement (2-3 sentences)
3. Specific objectives (3-5 SMART objectives)
4. Expected outcomes (quantifiable)
5. Target beneficiaries
6. Project duration recommendation

Respond in JSON format:
{{
  "project_title": "...",
  "vision": "...",
  "objectives": ["...", "..."],
  "outcomes": ["...", "..."],
  "beneficiaries": "...",
  "duration_months": 12
}}
"""
        
        response = self.generate(prompt, temperature=0.4)
        
        try:
            # Try to extract JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"error": "Failed to parse response", "raw": response}
```

### Technical Writer Agent

```python
class TechnicalWriterAgent(BaseAgent):
    """Creates technical documentation"""
    
    def __init__(self):
        super().__init__("Technical Writer", "llama3.2:3b")
    
    def process(self, context: Dict) -> Dict:
        """Generate technical methodology"""
        
        project = context.get("project", {})
        requirements = context.get("requirements", "")
        documents = context.get("documents", [])
        
        # Get relevant context from RAG
        rag_context = context.get("rag_context", "")
        
        prompt = f"""You are a technical writer creating a methodology section for a funding proposal.

PROJECT OVERVIEW:
- Title: {project.get('project_title', '')}
- Objectives: {', '.join(project.get('objectives', []))}

TECHNICAL REQUIREMENTS:
{requirements[:1500]}

RELEVANT CONTEXT FROM DOCUMENTS:
{rag_context[:1500]}

Create a detailed methodology section including:
1. Approach and methodology
2. Work packages or phases (at least 4)
3. Technical innovation elements
4. Technology stack (if applicable)
5. Quality assurance measures
6. Risk mitigation approach
7. Timeline/milestones

Respond in JSON format:
{{
  "methodology": "...",
  "work_packages": [
    {{"name": "...", "description": "...", "duration_months": ...}},
  ],
  "innovation": ["...", "..."],
  "quality_assurance": ["...", "..."],
  "risks": [
    {{"risk": "...", "mitigation": "..."}}
  ]
}}
"""
        
        response = self.generate(prompt, temperature=0.3)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"error": "Failed to parse response", "raw": response}
```

### Budget Expert Agent

```python
class BudgetExpertAgent(BaseAgent):
    """Creates financial projections"""
    
    def __init__(self):
        super().__init__("Budget Expert", "glm-4.7-flash")
    
    def process(self, context: Dict) -> Dict:
        """Generate budget proposal"""
        
        project = context.get("project", {})
        opportunity = context.get("opportunity", {})
        duration = project.get("duration_months", 12)
        
        # Parse budget range from opportunity
        budget_str = opportunity.get("budget", "")
        
        prompt = f"""You are a financial expert creating a detailed budget for a funding proposal.

PROJECT:
- Title: {project.get('project_title', '')}
- Duration: {duration} months
- Objectives: {', '.join(project.get('objectives', []))}

FUNDING OPPORTUNITY:
- Available budget: {budget_str}
- Category: {opportunity.get('category', '')}

Create a detailed budget including:
1. Total budget requested
2. Personnel costs (with positions and monthly rates)
3. Equipment and materials
4. Travel and dissemination
5. Indirect costs (overhead)
6. Contingency reserve (5-10%)
7. Budget justification for each item

Respond in JSON format:
{{
  "total_budget": ...,
  "currency": "USD",
  "personnel": [
    {{"role": "...", "monthly_rate": ..., "months": ...}}
  ],
  "equipment": [...],
  "travel": [...],
  "indirect_costs": ...,
  "contingency": ...,
  "budget_justification": "..."
}}
"""
        
        response = self.generate(prompt, temperature=0.2)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"error": "Failed to parse response", "raw": response}
```

### Compliance Analyst Agent

```python
class ComplianceAnalystAgent(BaseAgent):
    """Ensures requirement adherence"""
    
    def __init__(self):
        super().__init__("Compliance Analyst", "deepseek-r1:8b")
    
    def process(self, context: Dict) -> Dict:
        """Check compliance with requirements"""
        
        requirements = context.get("requirements", "")
        documents = context.get("documents", [])
        
        prompt = f"""You are a compliance analyst reviewing a funding proposal for eligibility.

REQUIREMENTS CHECKLIST:
{requirements[:2000]}

Analyze and verify:
1. Eligibility criteria compliance
2. Required attachments/documents
3. Deadline compliance
4. Budget limits compliance
5. Geographic eligibility
6. Required partnerships

Respond in JSON format:
{{
  "eligible": true/false,
  "eligibility_notes": [...],
  "missing_documents": [...],
  "compliance_issues": [...],
  "recommendations": [...]
}}
"""
        
        response = self.generate(prompt, temperature=0.2)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"error": "Failed to parse response"}
```

### Legal Reviewer Agent

```python
class LegalReviewerAgent(BaseAgent):
    """Checks legal constraints"""
    
    def __init__(self):
        super().__init__("Legal Reviewer", "qwen2.5-coder:14b")
    
    def process(self, context: Dict) -> Dict:
        """Review legal aspects"""
        
        opportunity = context.get("opportunity", {})
        documents = context.get("documents", [])
        
        prompt = f"""You are a legal expert reviewing funding proposal requirements.

OPPORTUNITY:
- Source: {opportunity.get('source', '')}
- Category: {opportunity.get('category', '')}

Review and provide:
1. Intellectual property requirements
2. Reporting obligations
3. Matching fund requirements (if any)
4. Sustainability requirements
5. Consortium/partnership requirements
6. Ethical considerations

Respond in JSON format:
{{
  "ip_requirements": "...",
  "reporting_obligations": [...],
  "matching_funds": {{"required": true/false, "percentage": ...}},
  "sustainability": "...",
  "partnership_requirements": [...],
  "ethical_considerations": [...]
}}
"""
        
        response = self.generate(prompt, temperature=0.2)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"error": "Failed to parse response"}
```

## Orchestrator

```python
class ProposalOrchestrator:
    """Orchestrates all agents for proposal generation"""
    
    def __init__(self):
        self.agents = {
            "project_lead": ProjectLeadAgent(),
            "technical_writer": TechnicalWriterAgent(),
            "budget_expert": BudgetExpertAgent(),
            "compliance_analyst": ComplianceAnalystAgent(),
            "legal_reviewer": LegalReviewerAgent()
        }
        self.rag = RAGSystem()
    
    def generate_proposal(self, opportunity_id: str) -> Dict:
        """Generate complete proposal"""
        
        # Get opportunity from API
        response = requests.get(f"http://localhost:8081/queue/{opportunity_id}")
        opportunity = response.json()
        
        # Get requirements from documents
        requirements = self.get_requirements(opportunity_id)
        
        # Get RAG context
        rag_context = self.rag.get_context(
            "requirements eligibility criteria deadline budget",
            opportunity_id,
            max_chars=4000
        )
        
        # Build context
        context = {
            "opportunity": opportunity,
            "requirements": requirements,
            "rag_context": rag_context,
            "documents": []
        }
        
        # Run parallel agents
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(agent.process, context): name
                for name, agent in self.agents.items()
            }
            
            results = {}
            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    results[agent_name] = future.result()
                except Exception as e:
                    logger.error(f"{agent_name} failed: {e}")
                    results[agent_name] = {"error": str(e)}
        
        # Run final reviewer
        final_review = self.final_review(results)
        
        # Compile proposal
        proposal = {
            "opportunity_id": opportunity_id,
            "project": results.get("project_lead", {}),
            "technical": results.get("technical_writer", {}),
            "budget": results.get("budget_expert", {}),
            "compliance": results.get("compliance_analyst", {}),
            "legal": results.get("legal_reviewer", {}),
            "final_review": final_review,
            "generated_at": datetime.now().isoformat()
        }
        
        return proposal
    
    def final_review(self, agent_results: Dict) -> Dict:
        """Quality assurance review"""
        
        reviewer = BaseAgent("Final Reviewer", "llama3.2:3b")
        
        prompt = f"""You are a senior reviewer performing final QA on a funding proposal.

Review the following sections and provide final approval:
- Project: {json.dumps(agent_results.get('project_lead', {}), indent=2)}
- Technical: {json.dumps(agent_results.get('technical_writer', {}), indent=2)}
- Budget: {json.dumps(agent_results.get('budget_expert', {}), indent=2)}
- Compliance: {json.dumps(agent_results.get('compliance_analyst', {}), indent=2)}

Provide:
1. Overall quality score (1-10)
2. Completeness check
3. Final recommendations

Respond in JSON format:
{{
  "quality_score": ...,
  "complete": true/false,
  "recommendations": [...]
}}
"""
        
        response = reviewer.generate(prompt, temperature=0.2)
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"complete": True, "quality_score": 8}
```

## API Integration

```python
# Add to main API
@app.route("/proposal/generate", methods=["POST"])
def generate_proposal():
    """Generate proposal for an opportunity"""
    try:
        data = request.get_json()
        opportunity_id = data.get("opportunity_id")
        
        orchestrator = ProposalOrchestrator()
        proposal = orchestrator.generate_proposal(opportunity_id)
        
        return jsonify(proposal)
        
    except Exception as e:
        logger.error(f"Proposal generation error: {e}")
        return jsonify({"error": str(e)}), 500
```

## Next Steps

- [06-dashboard](./06-dashboard.md) - Animated dashboard
