import re
import datetime
import uuid
from typing import Optional, List
from backend.models.clearance import Element, Facts, Verdict, RiskRating, Department, Subtype


def is_555_fictional_range(phone_text: str) -> bool:
    """
    Checks if a phone number falls within NANPA's reserved fictional range:
    555-0100 through 555-0199 (both 7-digit and 10-digit formats).
    """
    digits = re.sub(r'\D', '', phone_text)
    if len(digits) == 7:
        return digits.startswith("55501")
    elif len(digits) == 10:
        return digits[3:].startswith("55501")
    elif len(digits) == 11 and digits.startswith("1"):
        return digits[4:].startswith("55501")

    return "555-01" in phone_text or "555.01" in phone_text


def create_verdict(
    element: Element,
    rating: RiskRating,
    rule_id: str,
    rationale: str,
    citations: List[str]
) -> Verdict:
    return Verdict(
        id=f"verdict_{uuid.uuid4().hex[:8]}",
        element_id=element.id,
        department=element.department,
        rating=rating,
        rule_id=rule_id,
        rationale=rationale,
        citations=citations,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


# ----------------------------------------------------
# Department: SOUND_MUSIC
# ----------------------------------------------------
def rule_mus_001(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """MUS-001: Both composition and master recording in public domain."""
    if facts.is_public_domain is True and facts.master_recording_protected is False:
        return create_verdict(
            element=element,
            rating=RiskRating.GREEN,
            rule_id="MUS-001",
            rationale="Both composition and master recording are in the public domain. Free for synchronization use.",
            citations=citations
        )
    return None


def rule_mus_002(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """MUS-002: Composition is PD but master sound recording is protected by copyright."""
    if facts.is_public_domain is True and facts.master_recording_protected is True:
        return create_verdict(
            element=element,
            rating=RiskRating.AMBER,
            rule_id="MUS-002",
            rationale="Composition entered US public domain, but this specific master recording is protected by copyright. License master or re-record.",
            citations=citations
        )
    return None


def rule_mus_003(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """MUS-003: Composition protected by active copyright."""
    if facts.is_public_domain is False:
        return create_verdict(
            element=element,
            rating=RiskRating.RED,
            rule_id="MUS-003",
            rationale="Musical composition is protected by active copyright. Synchronization license required from music publisher.",
            citations=citations
        )
    return None


# ----------------------------------------------------
# Department: SCRIPT_SIGNAGE
# ----------------------------------------------------
def rule_sig_001(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """SIG-001: Phone number outside reserved 555 range (Subtype.PHONE)."""
    if element.subtype == Subtype.PHONE:
        if facts.is_555_range is False or (facts.is_555_range is None and not is_555_fictional_range(element.text)):
            return create_verdict(
                element=element,
                rating=RiskRating.RED,
                rule_id="SIG-001",
                rationale="Phone number is outside the reserved 555 fictional range (555-0100 through 555-0199). High live line collision risk.",
                citations=citations
            )
    return None


def rule_sig_002(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """SIG-002: Phone number inside reserved 555 range (Subtype.PHONE)."""
    if element.subtype == Subtype.PHONE:
        if facts.is_555_range is True or (facts.is_555_range is None and is_555_fictional_range(element.text)):
            return create_verdict(
                element=element,
                rating=RiskRating.GREEN,
                rule_id="SIG-002",
                rationale="Phone number is safely within the reserved NANPA 555-0100 through 555-0199 fictitious range.",
                citations=citations
            )
    return None


# ----------------------------------------------------
# Department: CAST_CHARACTERS
# ----------------------------------------------------
def rule_cas_001(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """CAS-001: Character collides with a living person in the same city and profession."""
    if facts.living_person_match_count is not None and facts.living_person_match_count > 0 and facts.living_person_same_profession is True:
        city_str = f" in {facts.living_person_city}" if facts.living_person_city else ""
        return create_verdict(
            element=element,
            rating=RiskRating.RED,
            rule_id="CAS-001",
            rationale=f"Character shares full name with an active living person{city_str} in the exact same profession. Defamation and right of publicity risk.",
            citations=citations
        )
    return None


# ----------------------------------------------------
# Department: LOCATIONS_SETS
# ----------------------------------------------------
def rule_loc_001(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """LOC-001: Real private street address."""
    if facts.is_real_address is True and facts.is_private_property is True:
        return create_verdict(
            element=element,
            rating=RiskRating.RED,
            rule_id="LOC-001",
            rationale="Identifies an active real street address on private commercial/residential property. Location release required.",
            citations=citations
        )
    return None


# ----------------------------------------------------
# Department: PROPS_BRANDS
# ----------------------------------------------------
def rule_prp_001(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """PRP-001: Trademarked brand depicted disparagingly."""
    if facts.is_trademarked_brand is True and facts.is_depiction_disparaging is True:
        return create_verdict(
            element=element,
            rating=RiskRating.AMBER,
            rule_id="PRP-001",
            rationale="Trademarked product depicted disparagingly or associated with illegal/harmful conduct. Defeats nominative fair use defense.",
            citations=citations
        )
    return None


# ----------------------------------------------------
# Department: CAMERA_VISUALS (Visual Art & Literary Quotes)
# ----------------------------------------------------
def rule_vis_001(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """VIS-001: Visual artwork under active copyright protection."""
    if element.subtype in [Subtype.ARTWORK, Subtype.PHOTOGRAPH, Subtype.OTHER]:
        current_year = datetime.datetime.now(datetime.timezone.utc).year
        if facts.is_public_domain is False or (facts.copyright_expiration_year and facts.copyright_expiration_year > current_year):
            exp = f" (expires {facts.copyright_expiration_year})" if facts.copyright_expiration_year else ""
            return create_verdict(
                element=element,
                rating=RiskRating.AMBER,
                rule_id="VIS-001",
                rationale=f"Featured artwork is protected by active copyright{exp}. Permission required from estate/rights administrator.",
                citations=citations
            )
    return None


def rule_vis_002(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """VIS-002: Visual artwork in public domain."""
    if element.subtype in [Subtype.ARTWORK, Subtype.PHOTOGRAPH]:
        if facts.is_public_domain is True:
            return create_verdict(
                element=element,
                rating=RiskRating.GREEN,
                rule_id="VIS-002",
                rationale="Visual artwork is in the public domain.",
                citations=citations
            )
    return None


def rule_lit_001(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """LIT-001: Literary quote / poetry under active copyright."""
    if element.subtype == Subtype.LITERARY_QUOTE:
        if facts.is_public_domain is False:
            return create_verdict(
                element=element,
                rating=RiskRating.AMBER,
                rule_id="LIT-001",
                rationale="Literary excerpt or poem is protected by active copyright. Synchronization / print clearance required.",
                citations=citations
            )
    return None


def rule_lit_002(element: Element, facts: Facts, citations: List[str]) -> Optional[Verdict]:
    """LIT-002: Literary quote / poetry in public domain."""
    if element.subtype == Subtype.LITERARY_QUOTE:
        if facts.is_public_domain is True:
            return create_verdict(
                element=element,
                rating=RiskRating.GREEN,
                rule_id="LIT-002",
                rationale="Literary work or poem is in the public domain.",
                citations=citations
            )
    return None
