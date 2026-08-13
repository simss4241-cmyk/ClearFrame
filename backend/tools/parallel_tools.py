import os
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from google.genai import types
from backend.models.clearance import Element, Facts, BasisItem, Department
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


def deep_research_element_parallel(
    element: Element
) -> Dict[str, Any]:
    """
    Executes Parallel Search research and uses Gemini to derive raw factual indicators
    STRICTLY from search excerpts. Zero manufactured confidence scores or synthetic URLs.
    """
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
    excerpts_for_gemini: List[str] = []

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
            excerpts_for_gemini.append(f"Source URL: {url}\nExcerpt: {snippet}")

    # If no Parallel results/excerpts were returned, return empty facts (Risk engine yields AMBER / DEFAULT-000)
    if not excerpts_for_gemini:
        return {
            "facts": Facts(raw_summary=f"No live web search evidence retrieved for '{element.text}'."),
            "basis": [],
            "parallel_search_id": search_res.get("search_id")
        }

    # Pass Parallel search excerpts to Gemini to extract raw factual fields ONLY if supported by excerpts
    gemini_client = get_gemini_client()
    model = get_gemini_model_name()

    prompt = (
        f"You are a factual evidence analyst for screenplay clearance.\n"
        f"Target Element: '{element.text}' (Subtype: {element.subtype}, Dept: {element.department.value})\n"
        f"Context Snippet: '{element.context_snippet}'\n\n"
        f"Read the following live web search excerpts retrieved from Parallel:\n"
        f"{chr(10).join(excerpts_for_gemini)}\n\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Extract ONLY factual indicators that are EXPLICITLY supported by the search excerpts.\n"
        "2. If an excerpt states a musical composition is in the public domain, set is_public_domain=true.\n"
        "3. If an excerpt states a musical composition is protected by active copyright, set is_public_domain=false.\n"
        "4. If an excerpt states a master sound recording is protected, set master_recording_protected=true.\n"
        "5. If searching a person name and excerpts show a real living person in the same city/profession, set living_person_match_count=1 and living_person_same_profession=true.\n"
        "6. Leave any unproven or unresearched field as null/None.\n"
        "7. Do NOT invent facts or URLs. Summarize excerpts objectively in raw_summary."
    )

    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
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
        )
    )

    facts = Facts()
    if response and response.text:
        parsed_facts = json.loads(response.text)
        facts = Facts.model_validate(parsed_facts)

    return {
        "facts": facts,
        "basis": basis,
        "parallel_search_id": search_res.get("search_id")
    }
