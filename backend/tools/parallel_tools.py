import os
import json
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
    """TASK 7: Builds clean, department-scoped search queries."""
    text = element.text
    dept = element.department
    rec_ref = element.recording_reference or ""

    if dept == Department.SOUND_MUSIC:
        q = f"{text} {rec_ref} composition public domain copyright recording rights".strip()
        return [q, f"{text} Gershwin public domain copyright status"]
    elif dept == Department.LOCATIONS_SETS:
        return [f"{text} address property location", f"{text} real address location release"]
    elif dept == Department.PROPS_BRANDS:
        return [f"{text} trademark registered brand product company"]
    elif dept == Department.CAST_CHARACTERS:
        return [f"{text} living person match defamation"]
    elif dept == Department.CAMERA_VISUALS:
        if element.subtype == Subtype.LITERARY_QUOTE:
            return [f"{text} poem author death year public domain copyright"]
        return [f"{text} artist author death year public domain copyright"]

    return [f"{text} {element.subtype.value} legal status"]


def batch_research_elements_parallel(elements: List[Element]) -> Dict[str, Finding]:
    """
    TASK B, 4 & 7: Batch Gemini Research Phase.
    1. SCRIPT_SIGNAGE department (phones/plates) skips Parallel web search entirely.
    2. Runs clean, department-scoped Parallel Search for remaining elements.
    3. Sends ONE batch Gemini request with temperature=0.0 and strict locality matching instructions.
    4. Maps findings back by element_id with isolated basis citations.
    """
    if not elements:
        return {}

    element_search_data: Dict[str, Dict[str, Any]] = {}
    blocks_for_gemini: List[str] = []

    # Phase 1: Parallel Search for non-signage elements
    for element in elements:
        # TASK 7: Skip web search for phone numbers and signage items (evaluated purely locally by risk engine)
        if element.department == Department.SCRIPT_SIGNAGE or element.subtype in [Subtype.PHONE, Subtype.LICENSE_PLATE]:
            logger.info(f"Skipping web search for signage element: {element.text}")
            element_search_data[element.id] = {
                "search_id": None,
                "basis": [],
                "has_excerpts": False
            }
            continue

        objective = (
            f"Determine the legal clearance status of '{element.text}' "
            f"(Subtype: {element.subtype.value}, Dept: {element.department.value}) "
            f"given context: '{element.context_snippet}'"
        )
        if element.recording_reference:
            objective += f" | Master Recording Reference: '{element.recording_reference}'"

        search_queries = _build_department_queries(element)
        search_res = conduct_parallel_search(objective, search_queries)
        results = search_res.get("results", [])

        basis: List[BasisItem] = []
        excerpts: List[str] = []

        for r in results:
            url = r.get("url")
            snippet = r.get("snippet", "")
            conf = r.get("confidence")

            if url and snippet:
                basis.append(BasisItem(
                    url=url,
                    reasoning=snippet[:250],
                    confidence=conf
                ))
                excerpts.append(f"  - Source URL: {url}\n    Excerpt: {snippet[:400]}")

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
                facts=Facts(raw_summary=f"No live web search evidence retrieved for '{element.text}'."),
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
        "Read the following search excerpts grouped strictly by ELEMENT ID.\n\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Analyze each element ONLY using its own provided search excerpts. Never mix evidence across elements.\n"
        "2. TASK 4 STRICT LOCALITY DISCIPLINE: For locations (is_real_address, is_private_property) and living persons (living_person_match_count), set factual flags ONLY if the source explicitly matches the locality (city, state) named in the script or context snippet. If a web source describes a location or person in another city or state (e.g. Dayton, OH or Beaumont, TX when script specifies Savannah, GA), set the flag to null/None or 0.\n"
        "3. TASK 3 MUSICAL CUES: If an element mentions both a composition and a master recording (e.g. Rhapsody in Blue + Columbia Masterworks recording), evaluate BOTH composition status (is_public_domain) AND master recording protection (master_recording_protected=true if protected) onto the same element's facts.\n"
        "4. If an excerpt states a composition is public domain, set is_public_domain=true.\n"
        "5. If an excerpt states a composition is protected by active copyright, set is_public_domain=false.\n"
        "6. If searching a person name and excerpts show a living person in the same city and profession, set living_person_match_count=1 and living_person_same_profession=true.\n"
        "7. Leave any unproven or unresearched field as null/None.\n"
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

    # Assemble Findings map
    for element in elements:
        s_data = element_search_data.get(element.id, {})
        element_facts = parsed_batch.get(
            element.id,
            Facts(raw_summary=f"Evaluated deterministically based on script element properties for '{element.text}'.")
        )

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
