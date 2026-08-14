from typing import List, Dict, Callable, Optional
from backend.models.clearance import Element, Facts, Verdict, RiskRating, Department
from backend.risk.rules import (
    rule_mus_001, rule_mus_002, rule_mus_003,
    rule_sig_001, rule_sig_002,
    rule_cas_001,
    rule_loc_001,
    rule_prp_001,
    rule_vis_001, rule_vis_002,
    rule_lit_001, rule_lit_002,
    create_verdict
)

# Department-Scoped Rule Registry
DEPARTMENT_RULES: Dict[Department, List[Callable[[Element, Facts, List[str]], Optional[Verdict]]]] = {
    Department.SOUND_MUSIC: [rule_mus_001, rule_mus_002, rule_mus_003],
    Department.SCRIPT_SIGNAGE: [rule_sig_001, rule_sig_002],
    Department.CAST_CHARACTERS: [rule_cas_001],
    Department.LOCATIONS_SETS: [rule_loc_001],
    Department.PROPS_BRANDS: [rule_prp_001],
    Department.CAMERA_VISUALS: [rule_vis_001, rule_vis_002, rule_lit_001, rule_lit_002],
}


def evaluate_risk(element: Element, facts: Optional[Facts], citations: List[str]) -> Verdict:
    """
    STRICT DETERMINISTIC RULE ENGINE (DEPARTMENT SCOPED):
    Evaluates raw facts strictly against rules registered for the element's department.
    First matching rule wins. Every verdict carries a rule ID.
    If no department rule matches, falls back to AMBER / UNRESOLVED (rule_id: DEFAULT-000).
    """
    if facts is None:
        facts = Facts()

    rules_for_dept = DEPARTMENT_RULES.get(element.department, [])

    for rule in rules_for_dept:
        verdict = rule(element, facts, citations)
        if verdict is not None:
            return verdict

    # Fallback to AMBER / UNRESOLVED
    return create_verdict(
        element=element,
        rating=RiskRating.AMBER,
        rule_id="DEFAULT-000",
        rationale="Element rights status unresolved — flagged for production counsel manual clearance.",
        citations=citations
    )
