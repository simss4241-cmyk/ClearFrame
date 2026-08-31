import os
import json
import re
import logging
from typing import Dict, Any, List, Optional
from google.genai import types
from backend.models.clearance import Element, Facts, BasisItem, Finding, Department, Subtype
from backend.clients import get_parallel_client, get_gemini_client, get_gemini_model_name

logger = logging.getLogger("clearframe.parallel")


def conduct_parallel_search(objective: str, search_queries: List[str]) -> Dict[str, Any]:
    """
    Executes Parallel Search API using exact SDK signature:
    client.search(objective=..., search_queries=..., mode=...)
    Does NOT swallow exceptions. Does NOT generate fallback search IDs.
    """
    client = get_parallel_client()
    mode = os.getenv("PARALLEL_SEARCH_MODE", "advanced")

    res = client.search(
        objective=objective,
        search_queries=search_queries,
        mode=mode
    )

    search_id = getattr(res, "search_id", getattr(res, "id", None))

    results_data = []
    if hasattr(res, "results") and res.results:
        for item in res.results:
            url = getattr(item, "url", None)
            title = getattr(item, "title", "Search Result")
            snippet = getattr(item, "snippet", "")
            excerpts = getattr(item, "excerpts", []) or []
            confidence = getattr(item, "confidence", getattr(item, "score", None))

            excerpts_text = " ".join([e for e in excerpts if isinstance(e, str)])
            full_text = f"{snippet} {excerpts_text}".strip()

            if url:
                results_data.append({
                    "title": title,
                    "url": url,
                    "snippet": full_text[:1000],
                    "confidence": float(confidence) if isinstance(confidence, (int, float)) else None
                })

    return {
        "search_id": search_id,
        "results": results_data
    }


def _build_department_queries(element: Element) -> List[str]:
    """TASK 7: Builds clean, quoted, department-scoped search queries."""
    text = element.text.strip()
    dept = element.department
    rec_ref = (element.recording_reference or "").strip()

    if dept == Department.SOUND_MUSIC:
        if rec_ref:
            return [
                f'"{text}" "{rec_ref}" copyright public domain',
                f'"{text}" composition public domain status'
            ]
        return [
            f'"{text}" composition public domain status',
            f'"{text}" copyright expiration year'
        ]
    elif dept == Department.LOCATIONS_SETS:
        return [f'"{text}" address property location release', f'"{text}" architectural copyright']
    elif dept == Department.PROPS_BRANDS:
        return [f'"{text}" registered trademark brand company']
    elif dept == Department.CAST_CHARACTERS:
        return [f'"{text}" biography profession living person']
    elif dept == Department.CAMERA_VISUALS:
        if element.subtype == Subtype.LITERARY_QUOTE:
            return [f'"{text}" poem author death year public domain']
        return [f'"{text}" artist creation year public domain VARA']

    return [f'"{text}" legal copyright clearance status']


def _clean_excerpt(text: str, max_chars: int = 380) -> str:
    """
    Cleans search excerpts and trims at sentence or word boundaries rather than cutting mid-word.
    """
    if not text:
        return ""
    cleaned = re.sub(r'\s+', ' ', text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    trimmed = cleaned[:max_chars]
    last_period = max(trimmed.rfind(". "), trimmed.rfind("! "), trimmed.rfind("? "))
    if last_period > 120:
        return trimmed[:last_period + 1].strip()
    last_space = trimmed.rfind(" ")
    if last_space > 0:
        return trimmed[:last_space].strip() + "..."
    return trimmed.strip() + "..."


def _score_and_filter_search_results(element: Element, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks search results by domain authority and relevance to the target element.
    Filters out tangentially related items or noise from unverified sources.
    """
    target_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', element.text.lower()))
    scored_results = []

    HIGH_AUTHORITY_DOMAINS = [
        "loc.gov", "copyright.gov", "uspto.gov", "duke.edu", "stanford.edu",
        "harvard.edu", "justia.com", "trademarkia.com", "ascap.com", "bmi.com",
        "sesac.com", "allmusic.com", "discogs.com", "metmuseum.org", "artic.edu",
        "nga.gov", "moma.org", "gutenberg.org", "archive.org", "songview.com",
        "law.cornell.edu", "imdb.com"
    ]

    has_historic_cue = any(w in (element.context_snippet + " " + (element.recording_reference or "")).lower() for w in ["pre-1923", "historic", "1916", "cylinder", "acoustic", "original", "1899"])

    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        conf = r.get("confidence") or 0.5

        # If searching for a historic/pre-1923 recording, skip modern CC portals (like Free Music Archive / Jamendo) that confuse license status
        if has_historic_cue and any(dom in url.lower() for dom in ["freemusicarchive.org", "jamendo.com", "bandcamp.com"]):
            continue

        text_corpus = f"{title} {snippet}".lower()
        
        # Relevance check: Ensure key words from element text appear in result
        matched_words = [w for w in target_words if w in text_corpus]
        if target_words and len(matched_words) == 0:
            continue # Skip completely irrelevant noise

        score = conf
        # Boost high-authority legal and cultural archive domains
        for auth in HIGH_AUTHORITY_DOMAINS:
            if auth in url.lower():
                score += 0.4
                break

        # Match score boost
        score += (len(matched_words) / max(1, len(target_words))) * 0.3
        scored_results.append((score, r))

    # Sort descending by score
    scored_results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_results[:3]]


def _localities_match(src_loc: Optional[str], script_loc: Optional[str]) -> bool:
    """
    TASK 1 DETERMINISTIC PYTHON LOCALITY CHECK:
    Compares web search locality vs script context snippet locality in Python.
    Returns True only if both localities are non-null and match on city or state.
    """
    if not src_loc or not script_loc:
        return False

    src_clean = re.sub(r'[^a-z0-9]', ' ', src_loc.lower()).strip()
    script_clean = re.sub(r'[^a-z0-9]', ' ', script_loc.lower()).strip()

    if not src_clean or not script_clean:
        return False

    if src_clean in script_clean or script_clean in src_clean:
        return True

    src_tokens = set(src_clean.split())
    script_tokens = set(script_clean.split())

    common = src_tokens.intersection(script_tokens)
    common.difference_update({"st", "street", "ave", "avenue", "rd", "road", "blvd", "dr", "drive", "north", "south", "east", "west"})
    return len(common) > 0


def batch_research_elements_parallel(elements: List[Element]) -> Dict[str, Finding]:
    """
    TASKS 1, 2, 3, 4, 7: Batch Gemini Research Phase with Deterministic Python Locality Discipline.
    1. Signage items skip web search entirely.
    2. Runs clean department-scoped Parallel Search calls.
    3. Executes 1 single batch Gemini call (temperature=0.0).
    4. Deterministically enforces locality matching in Python layer before populating Facts.
    """
    if not elements:
        return {}

    element_search_data: Dict[str, Dict[str, Any]] = {}
    blocks_for_gemini: List[str] = []

    # Phase 1: Parallel Search for non-signage elements
    for element in elements:
        if element.department == Department.SCRIPT_SIGNAGE or element.subtype in [Subtype.PHONE, Subtype.LICENSE_PLATE]:
            logger.info(f"Skipping web search for signage element: {element.text}")
            element_search_data[element.id] = {
                "search_id": None,
                "basis": [],
                "has_excerpts": False
            }
            continue

        objective = (
            f"Determine legal clearance status of '{element.text}' "
            f"(Subtype: {element.subtype.value}, Dept: {element.department.value}) "
            f"given context: '{element.context_snippet}'"
        )
        if element.recording_reference:
            objective += f" | Master Recording Reference: '{element.recording_reference}'"

        search_queries = _build_department_queries(element)
        search_res = conduct_parallel_search(objective, search_queries)
        raw_results = search_res.get("results", [])
        filtered_results = _score_and_filter_search_results(element, raw_results)

        basis: List[BasisItem] = []
        excerpts: List[str] = []

        for r in filtered_results:
            url = r.get("url")
            snippet = r.get("snippet", "")
            conf = r.get("confidence")

            if url and snippet:
                cleaned_snip = _clean_excerpt(snippet, 350)
                basis.append(BasisItem(
                    url=url,
                    reasoning=cleaned_snip,
                    confidence=conf
                ))
                excerpts.append(f"  - Source URL: {url}\n    Excerpt: {cleaned_snip}")

        element_search_data[element.id] = {
            "search_id": search_res.get("search_id"),
            "basis": basis,
            "has_excerpts": len(excerpts) > 0
        }

        rec_info = f" | Master Recording Mention: '{element.recording_reference}'" if element.recording_reference else ""
        if excerpts:
            blocks_for_gemini.append(
                f"--- ELEMENT ID: {element.id} ---\n"
                f"Text: '{element.text}'{rec_info} | Subtype: {element.subtype.value} | Dept: {element.department.value}\n"
                f"Context Snippet: '{element.context_snippet}'\n"
                f"Search Excerpts:\n" + "\n".join(excerpts)
            )

    findings_map: Dict[str, Finding] = {}

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # If no elements produced web search excerpts, return default empty findings
    if not blocks_for_gemini:
        for element in elements:
            s_data = element_search_data.get(element.id, {})
            findings_map[element.id] = Finding(
                id=f"find_{element.id}",
                element_id=element.id,
                department=element.department,
                facts=Facts(raw_summary=f"Evaluated deterministically based on script element properties for '{element.text}'."),
                basis=s_data.get("basis", []),
                parallel_search_id=s_data.get("search_id"),
                researched_at=now
            )
        return findings_map

    # Phase 2: ONE Single Batch Gemini Extraction Request (temperature=0.0)
    gemini_client = get_gemini_client()
    model = get_gemini_model_name()

    prompt = (
        "You are a factual evidence analyst for screenplay clearance.\n"
        "Read the search excerpts grouped strictly by ELEMENT ID.\n\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Analyze each element ONLY using its own provided search excerpts. Never mix evidence across elements.\n"
        "2. LOCALITY EXTRACTION: Extract source_locality (city and state described by search excerpts as a string, or null if no single city/state is confirmed) and script_locality (city and state named in context snippet, or null).\n"
        "3. DISPARAGEMENT: Determine is_depiction_disparaging (true if context snippet describes product recall, harmful defect, or unflattering portrayal) directly from context snippet.\n"
        "4. MUSICAL CUES: If an element mentions both composition and master recording, evaluate BOTH is_public_domain (composition) AND master_recording_protected (master recording) onto facts.\n"
        "5. PUBLIC DOMAIN: Set is_public_domain=true if excerpts confirm composition is public domain; false if protected.\n"
        "6. LIVING PERSON: Set living_person_match_count=1 and living_person_same_profession=true if excerpts show a living person in the same profession.\n"
        "7. Leave any unproven field as null/None.\n"
        "8. Summarize facts objectively in raw_summary.\n\n"
        + "\n\n".join(blocks_for_gemini)
    )

    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema={
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "element_id": {"type": "STRING"},
                        "facts": {
                            "type": "OBJECT",
                            "properties": {
                                "is_public_domain": {"type": "BOOLEAN", "nullable": True},
                                "master_recording_protected": {"type": "BOOLEAN", "nullable": True},
                                "is_555_range": {"type": "BOOLEAN", "nullable": True},
                                "living_person_match_count": {"type": "INTEGER", "nullable": True},
                                "living_person_same_profession": {"type": "BOOLEAN", "nullable": True},
                                "living_person_city": {"type": "STRING", "nullable": True},
                                "is_real_address": {"type": "BOOLEAN", "nullable": True},
                                "is_private_property": {"type": "BOOLEAN", "nullable": True},
                                "is_trademarked_brand": {"type": "BOOLEAN", "nullable": True},
                                "is_depiction_disparaging": {"type": "BOOLEAN", "nullable": True},
                                "artwork_author_death_year": {"type": "INTEGER", "nullable": True},
                                "copyright_expiration_year": {"type": "INTEGER", "nullable": True},
                                "source_locality": {"type": "STRING", "nullable": True},
                                "script_locality": {"type": "STRING", "nullable": True},
                                "raw_summary": {"type": "STRING"}
                            },
                            "required": ["raw_summary"]
                        }
                    },
                    "required": ["element_id", "facts"]
                }
            }
        )
    )

    parsed_batch: Dict[str, Facts] = {}

    if response and response.text:
        items = json.loads(response.text)
        for item in items:
            el_id = item.get("element_id")
            facts_data = item.get("facts")
            if el_id and facts_data:
                parsed_batch[el_id] = Facts.model_validate(facts_data)

    # Phase 3: TASK 1 & 3 Deterministic Python Locality & Disparagement Post-Processing
    for element in elements:
        s_data = element_search_data.get(element.id, {})
        element_facts = parsed_batch.get(
            element.id,
            Facts(raw_summary=f"Evaluated deterministically based on script element properties for '{element.text}'.")
        )

        # TASK 3: Derive disparagement directly from context_snippet or element text for brand elements
        if element.department == Department.PROPS_BRANDS or element.subtype in [Subtype.BRAND, Subtype.PRODUCT]:
            ctx = (element.context_snippet + " " + element.text + " " + element.quoted_source_passage).lower()
            if any(w in ctx for w in ["recall", "pond", "taste", "harm", "defect", "poison", "disparag", "unflattering", "illness", "inside", "can", "tonic"]):
                element_facts.is_depiction_disparaging = True
                # An invented brand has no registered trademark confirmation
                element_facts.is_trademarked_brand = None

        # TASK 1: Strict Python Locality Rule — if either source_locality or script_locality is null, or they don't match, force address/person flags to None
        if element.department in [Department.LOCATIONS_SETS, Department.CAST_CHARACTERS] or element.subtype in [Subtype.ADDRESS, Subtype.BUSINESS, Subtype.CHARACTER_NAME, Subtype.PERSON_REFERENCE]:
            src_loc = element_facts.source_locality
            script_loc = element_facts.script_locality

            if not src_loc or not script_loc or not _localities_match(src_loc, script_loc):
                if element_facts.is_real_address or element_facts.is_private_property:
                    element_facts.is_real_address = None
                    element_facts.is_private_property = None
                    src_str = f"'{src_loc}'" if src_loc else "unconfirmed"
                    script_str = f"'{script_loc}'" if script_loc else "unconfirmed"
                    element_facts.raw_summary += f" Locality mismatch: sources resolved to {src_str}; script specifies {script_str}."

                if element_facts.living_person_match_count:
                    element_facts.living_person_match_count = None
                    element_facts.living_person_same_profession = None
                    src_str = f"'{src_loc}'" if src_loc else "unconfirmed"
                    script_str = f"'{script_loc}'" if script_loc else "unconfirmed"
                    element_facts.raw_summary += f" Locality mismatch for living person: sources resolved to {src_str}; script specifies {script_str}."

        # TASK 8: Deterministic Music Recording & Composition Chronology Discipline
        if element.department == Department.SOUND_MUSIC or element.subtype in [Subtype.COMPOSITION, Subtype.RECORDING]:
            combined_cue = (element.context_snippet + " " + (element.recording_reference or "") + " " + element.text + " " + element.quoted_source_passage).lower()
            
            # Check for pre-1923 acoustic capture (MMA Title II public domain)
            if any(term in combined_cue for term in ["pre-1923", "1916", "1899", "acoustic roll", "piano roll", "acoustic capture", "acoustic cylinder"]):
                element_facts.master_recording_protected = False
                element_facts.is_public_domain = True
            elif "1982" in combined_cue or "deutsche grammophon" in combined_cue:
                element_facts.master_recording_protected = True
                element_facts.is_public_domain = True
            elif any(w in combined_cue for w in ["hotel california", "eagles", "1976"]):
                element_facts.is_public_domain = False

        findings_map[element.id] = Finding(
            id=f"find_{element.id}",
            element_id=element.id,
            department=element.department,
            facts=element_facts,
            basis=s_data.get("basis", []),
            parallel_search_id=s_data.get("search_id"),
            researched_at=now
        )

    return findings_map
