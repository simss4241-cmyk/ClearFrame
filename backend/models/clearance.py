from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class Department(str, Enum):
    SCRIPT_SIGNAGE = "SCRIPT_SIGNAGE"
    CAST_CHARACTERS = "CAST_CHARACTERS"
    LOCATIONS_SETS = "LOCATIONS_SETS"
    PROPS_BRANDS = "PROPS_BRANDS"
    SOUND_MUSIC = "SOUND_MUSIC"
    CAMERA_VISUALS = "CAMERA_VISUALS"


class RiskRating(str, Enum):
    RED = "RED"
    AMBER = "AMBER"
    GREEN = "GREEN"


class Scene(BaseModel):
    id: str
    number: int
    heading: str
    text: str


class Element(BaseModel):
    id: str
    script_id: str
    scene_id: str
    department: Department
    subtype: str
    text: str
    context_snippet: str


class BasisItem(BaseModel):
    url: str
    reasoning: str
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class Facts(BaseModel):
    """
    STRICT COMPLIANCE: Models pass ONLY raw factual metrics to the risk engine.
    No LLM ever assigns a risk rating, color tag, or severity score.
    """
    is_public_domain: Optional[bool] = None
    master_recording_protected: Optional[bool] = None
    is_555_range: Optional[bool] = None
    living_person_match_count: int = 0
    living_person_same_profession: Optional[bool] = None
    living_person_city: Optional[str] = None
    is_real_address: Optional[bool] = None
    is_private_property: Optional[bool] = None
    is_trademarked_brand: Optional[bool] = None
    is_depiction_disparaging: Optional[bool] = None
    artwork_author_death_year: Optional[int] = None
    copyright_expiration_year: Optional[int] = None
    raw_summary: str = ""


class Finding(BaseModel):
    id: str
    element_id: str
    department: Department
    facts: Facts
    basis: List[BasisItem] = Field(default_factory=list)
    parallel_search_id: Optional[str] = None
    researched_at: str


class Verdict(BaseModel):
    id: str
    element_id: str
    department: Department
    rating: RiskRating
    rule_id: str
    rationale: str
    citations: List[str] = Field(default_factory=list)
    created_at: str
    superseded_by: Optional[str] = None


class ElementReport(BaseModel):
    element: Element
    finding: Optional[Finding] = None
    verdict: Verdict
    verdict_history: List[Verdict] = Field(default_factory=list)


class DepartmentSummary(BaseModel):
    department: Department
    total_elements: int = 0
    red_count: int = 0
    amber_count: int = 0
    green_count: int = 0
    elements: List[ElementReport] = Field(default_factory=list)


class ClearanceReport(BaseModel):
    script_id: str
    title: str
    scenes: List[Scene] = Field(default_factory=list)
    departments: Dict[str, DepartmentSummary] = Field(default_factory=dict)
    total_elements: int = 0
    red_count: int = 0
    amber_count: int = 0
    green_count: int = 0
    generated_at: str


class MonitorRegistration(BaseModel):
    id: str
    element_id: str
    parallel_monitor_id: str
    query: str
    department: Department
    frequency: str = "daily"
    status: str = "ACTIVE"


class MonitorWebhookPayload(BaseModel):
    monitor_id: str
    element_id: str
    event_content: str
    updated_facts: Facts
    cites: List[str] = Field(default_factory=list)
