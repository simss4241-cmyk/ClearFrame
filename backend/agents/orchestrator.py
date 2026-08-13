import logging
from typing import Dict, Any, List
import google.adk as adk
from backend.models.clearance import ClearanceReport

logger = logging.getLogger("clearframe.orchestrator")


class IntakeAgent(adk.Agent):
    """ADK Intake Agent: Ingests screenplay text into structured Scene models."""
    def __init__(self):
        super().__init__(name="IntakeAgent")

    def run(self, script_text: str, script_id: str):
        from backend.agents.intake_agent import parse_script_scenes
        return parse_script_scenes(script_text, script_id)


class ExtractionAgent(adk.Agent):
    """ADK Extraction Agent: Extracts elements across 6 Department Plugins using Gemini."""
    def __init__(self):
        super().__init__(name="ExtractionAgent")

    def run(self, scenes: List[Any], script_id: str):
        from backend.agents.extraction_agent import extract_clearable_elements
        return extract_clearable_elements(scenes, script_id)


class ResearchFanoutAgent(adk.Agent):
    """ADK Research Fanout Agent: Funs out Parallel search calls to gather grounded web basis."""
    def __init__(self):
        super().__init__(name="ResearchFanoutAgent")

    def run(self, elements: List[Any]):
        from backend.agents.research_agents import conduct_department_research
        findings = []
        for element in elements:
            findings.append((element, conduct_department_research(element)))
        return findings


class RiskEngineAgent(adk.Agent):
    """ADK Risk Engine Agent: Plain Python rule engine for deterministic scoring."""
    def __init__(self):
        super().__init__(name="RiskEngineAgent")

    def run(self, element_finding_pairs: List[Any]):
        from backend.risk.engine import evaluate_risk
        from backend.models.clearance import ElementReport
        
        element_reports = []
        for element, finding in element_finding_pairs:
            citations = [b.url for b in finding.basis] if finding else []
            verdict = evaluate_risk(element, finding.facts if finding else None, citations)
            element_reports.append(ElementReport(
                element=element,
                finding=finding,
                verdict=verdict,
                verdict_history=[verdict]
            ))
        return element_reports


class WatchAgent(adk.Agent):
    """ADK Watch Agent: Registers standing Parallel Monitors for RED/AMBER elements."""
    def __init__(self):
        super().__init__(name="WatchAgent")

    def run(self, element_reports: List[Any]):
        from backend.agents.watch_agent import register_parallel_monitors
        return register_parallel_monitors(element_reports)


class ClearanceADKOrchestrator:
    """
    ADK Agent Topology orchestrating the 5-stage clearance pipeline:
      1. IntakeAgent
      2. ExtractionAgent
      3. ResearchFanoutAgent
      4. RiskEngineAgent
      5. WatchAgent
    """
    def __init__(self):
        self.intake = IntakeAgent()
        self.extraction = ExtractionAgent()
        self.research = ResearchFanoutAgent()
        self.risk = RiskEngineAgent()
        self.watch = WatchAgent()

    def execute(self, script_text: str, filename: str = "script.txt", title: str = "Screenplay Clearance Report") -> ClearanceReport:
        from backend.api.routes import run_full_clearance_pipeline
        return run_full_clearance_pipeline(script_text, filename=filename, title=title)


orchestrator = ClearanceADKOrchestrator()
