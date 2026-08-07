import os
from typing import List, Dict, Any
from backend.models.clearance import ClearanceReport, Scene, Element, Finding, Verdict, ElementReport
from backend.agents.intake_agent import parse_script_scenes
from backend.agents.extraction_agent import extract_clearable_elements
from backend.agents.research_agents import conduct_department_research
from backend.risk.engine import evaluate_risk
from backend.agents.watch_agent import register_parallel_monitors

try:
    import google.adk as adk
except ImportError:
    adk = None


class ClearancePipelineOrchestrator:
    """
    ADK Sequential Agent Topology:
      1. IntakeAgent (Script parsing to Scenes)
      2. ExtractionAgent (Gemini element extraction across 6 departments)
      3. ResearchFanout (Parallel Search/Task grounded research)
      4. RiskEngine (Deterministic Python rule evaluation)
      5. WatchAgent (Parallel Monitor standing registration)
    """

    def __init__(self, name: str = "clearance_pipeline"):
        self.name = name

    def execute(self, script_text: str, title: str = "Untitled Screenplay") -> ClearanceReport:
        from backend.api.routes import run_full_clearance_pipeline
        return run_full_clearance_pipeline(script_text, title=title)


orchestrator = ClearancePipelineOrchestrator()
