from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class Department(str, Enum):
    SCRIPT_SIGNAGE = "SCRIPT_SIGNAGE"
    CAST_CHARACTERS = "CAST_CHARACTERS"
    LOCATIONS_SETS = "LOCATIONS_SETS"
    PROPS_BRANDS = "PROPS_BRANDS"
    SOUND_MUSIC = "SOUND_MUSIC"
    CAMERA_VISUALS = "CAMERA_VISUALS"


class Subtype(str, Enum):
    # SCRIPT_SIGNAGE
    PHONE = "PHONE"
    LICENSE_PLATE = "LICENSE_PLATE"
    URL = "URL"
    EMAIL = "EMAIL"

    # CAST_CHARACTERS
    CHARACTER_NAME = "CHARACTER_NAME"
    PERSON_REFERENCE = "PERSON_REFERENCE"

    # LOCATIONS_SETS
    ADDRESS = "ADDRESS"
    STREET = "STREET"
    BUSINESS = "BUSINESS"
    LANDMARK = "LANDMARK"

    # PROPS_BRANDS
    BRAND = "BRAND"
    PRODUCT = "PRODUCT"

    # SOUND_MUSIC
    COMPOSITION = "COMPOSITION"
    RECORDING = "RECORDING"
    LYRIC = "LYRIC"

    # CAMERA_VISUALS
    ARTWORK = "ARTWORK"
    PHOTOGRAPH = "PHOTOGRAPH"
    LITERARY_QUOTE = "LITERARY_QUOTE"
    ARCHIVAL_FOOTAGE = "ARCHIVAL_FOOTAGE"

    # FALLBACK
    OTHER = "OTHER"


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
    subtype: Subtype = Subtype.OTHER
    text: str
    context_snippet: str
    quoted_source_passage: str = ""
    recording_reference: Optional[str] = None

    @field_validator("subtype", mode="before")
    @classmethod
    def validate_subtype(cls, v):
        if isinstance(v, Subtype):
            return v
        if isinstance(v, str):
            v_clean = v.strip().upper().replace(" ", "_")
            mapping = {
                "PHONE_NUMBER": Subtype.PHONE,
                "CHARACTER_NAME": Subtype.CHARACTER_NAME,
                "REAL_ADDRESS": Subtype.ADDRESS,
                "PRIVATE_BUSINESS": Subtype.BUSINESS,
                "TRADEMARK": Subtype.BRAND,
                "COMMERCIAL_PRODUCT": Subtype.PRODUCT,
                "SONG_CUE": Subtype.COMPOSITION,
                "RECORDING/COPYRIGHT_REFERENCE": Subtype.RECORDING,
                "PAINTING": Subtype.ARTWORK,
                "ART": Subtype.ARTWORK,
                "STREET_NAME": Subtype.STREET,
                "DOMAIN_NAME": Subtype.URL,
                "LITERARY_REFERENCE": Subtype.LITERARY_QUOTE,
            }
            if v_clean in mapping:
                return mapping[v_clean]
            try:
                return Subtype(v_clean)
            except ValueError:
                return Subtype.OTHER
        return Subtype.OTHER


class BasisItem(BaseModel):
    url: str
    reasoning: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class Facts(BaseModel):
    """
    STRICT COMPLIANCE: Models pass ONLY raw factual metrics to the risk engine.
    No LLM ever assigns a risk rating, color tag, or severity score.
    """
    is_public_domain: Optional[bool] = None
    master_recording_protected: Optional[bool] = None
    is_555_range: Optional[bool] = None
    living_person_match_count: Optional[int] = None
    living_person_same_profession: Optional[bool] = None
    living_person_city: Optional[str] = None
    is_real_address: Optional[bool] = None
    is_private_property: Optional[bool] = None
    is_trademarked_brand: Optional[bool] = None
    is_depiction_disparaging: Optional[bool] = None
    artwork_author_death_year: Optional[int] = None
    copyright_expiration_year: Optional[int] = None
    is_motion_picture_soundtrack: Optional[bool] = None
    film_copyright_active: Optional[bool] = None
    source_locality: Optional[str] = None
    script_locality: Optional[str] = None
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


class MonitorRegistration(BaseModel):
    id: str
    element_id: str
    parallel_monitor_id: Optional[str] = None
    query: str
    department: Department
    frequency: str = "1d"
    status: str = "ACTIVE"


class ClearanceReport(BaseModel):
    script_id: str
    filename: str = "script.txt"
    script_hash: str = ""
    title: str
    scenes: List[Scene] = Field(default_factory=list)
    departments: Dict[str, DepartmentSummary] = Field(default_factory=dict)
    monitors: List[MonitorRegistration] = Field(default_factory=list)
    total_elements: int = 0
    red_count: int = 0
    amber_count: int = 0
    green_count: int = 0
    status: str = "COMPLETE"
    error_message: Optional[str] = None
    generated_at: str


class MonitorWebhookPayload(BaseModel):
    monitor_id: str
    element_id: str
    event_content: str
    updated_facts: Facts
    cites: List[str] = Field(default_factory=list)
