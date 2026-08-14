import os
import json
import logging
from typing import Dict, Any, List, Optional
from google.genai import types
from backend.models.clearance import Element, Facts, BasisItem, Finding
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


def batch_research_elements_parallel(elements: List[Element]) -> Dict[str, Finding]:
    """
    TASK B: Batch Gemini Research Phase.
    1. Runs Parallel Search for every element to collect individual search evidence.
    2. Sends ONE single Gemini request containing all elements' search excerpts.
    3. Maps response back by element_id without evidence cross-contamination.
    Total Gemini API spend: Exactly 1 call.
    """
    if not elements:
        return {}

    element_search_data: Dict[str, Dict[str, Any]] = {}
    blocks_for_gemini: List[str] = []

    # Phase 1: Parallel Search per element (per-element objectives & queries)
    for element in elements:
        objective = (
            f"Determine the copyright, trademark, publicity, or location rights clearance status "
            f"of the {element.subtype} '{element.text}' (department: {element.department.value}) "
            f"given context: '{element.context_snippet}'"
        )
        search_queries = [
            f"{element.text} {element.subtype} copyright rights clearance",
            f"{element.text} legal status"
        ]

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

        if excerpts:
            blocks_for_gemini.append(
                f"--- ELEMENT ID: {element.id} ---\n"
                f"Text: '{element.text}' | Subtype: {element.subtype} | Dept: {element.department.value}\n"
                f"Context Snippet: '{element.context_snippet}'\n"
                f"Search Excerpts:\n" + "\n".join(excerpts)
            )

    findings_map: Dict[str, Finding] = {}

    # If no elements produced web search excerpts, return default empty findings
    if not blocks_for_gemini:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
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

    # Phase 2: ONE Single Batch Gemini Extraction Request
    gemini_client = get_gemini_client()
    model = get_gemini_model_name()

    prompt = (
        "You are a factual evidence analyst for screenplay clearance.\n"
        "Read the following search excerpts grouped strictly by ELEMENT ID.\n\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Analyze each element ONLY using its own provided search excerpts. Never mix evidence across elements.\n"
        "2. For each element_id, extract factual fields supported by its search excerpts.\n"
        "3. If an excerpt states a composition is public domain, set is_public_domain=true.\n"
        "4. If an excerpt states a composition is protected by active copyright, set is_public_domain=false.\n"
        "5. If an excerpt states a master sound recording is protected, set master_recording_protected=true.\n"
        "6. If searching a person name and excerpts show a living person in the same city/profession, set living_person_match_count=1 and living_person_same_profession=true.\n"
        "7. Leave any unproven or unresearched field as null/None.\n"
        "8. Summarize facts objectively in raw_summary.\n\n"
        + "\n\n".join(blocks_for_gemini)
    )

    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
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

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
            Facts(raw_summary=f"No live web search evidence retrieved for '{element.text}'.")
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
