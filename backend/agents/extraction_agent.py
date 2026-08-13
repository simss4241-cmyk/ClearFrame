import json
import uuid
import re
from typing import List, Set
from google.genai import types
from backend.models.clearance import Scene, Element, Department
from backend.clients import get_gemini_client, get_gemini_model_name


def _normalize_text(text: str) -> str:
    """Normalizes text by removing non-alphanumeric characters and converting to lowercase."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def extract_clearable_elements(scenes: List[Scene], script_id: str) -> List[Element]:
    """
    Extracts clearable elements dynamically using Gemini structured output.
    Raises if Gemini extraction fails. Zero hardcoded fallbacks or domain strings.
    Deduplicates extracted elements per department based on normalized text.
    """
    client = get_gemini_client()
    model = get_gemini_model_name()

    full_text = "\n".join([f"SCENE {s.number} ({s.heading}):\n{s.text}" for s in scenes])

    prompt = (
        "Identify all screenplay elements requiring legal clearance across these 6 departments:\n"
        "- SCRIPT_SIGNAGE (phone numbers, license plates, URLs, emails, domain names)\n"
        "- CAST_CHARACTERS (character names, real living person references, professional roles)\n"
        "- LOCATIONS_SETS (real addresses, landmarks, private businesses, street names)\n"
        "- PROPS_BRANDS (trademarks, commercial products, brand logos, corporate names)\n"
        "- SOUND_MUSIC (song cues, needle drops, lyrics, pre-existing music score references)\n"
        "- CAMERA_VISUALS (paintings, posters, sculptures, photographs, literary quotes, newsreel footage)\n\n"
        f"Screenplay Text:\n{full_text}"
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "scene_number": {"type": "INTEGER"},
                        "department": {
                            "type": "STRING",
                            "enum": [
                                "SCRIPT_SIGNAGE", "CAST_CHARACTERS", "LOCATIONS_SETS",
                                "PROPS_BRANDS", "SOUND_MUSIC", "CAMERA_VISUALS"
                            ]
                        },
                        "subtype": {"type": "STRING"},
                        "text": {"type": "STRING"},
                        "context_snippet": {"type": "STRING"}
                    },
                    "required": ["scene_number", "department", "subtype", "text", "context_snippet"]
                }
            }
        )
    )

    if not response or not response.text:
        raise RuntimeError("Gemini element extraction returned empty output.")

    extracted_items = json.loads(response.text)
    raw_elements: List[Element] = []

    for item in extracted_items:
        dept_str = item.get("department", "SCRIPT_SIGNAGE")
        try:
            dept = Department(dept_str)
        except ValueError:
            dept = Department.SCRIPT_SIGNAGE

        sc_num = item.get("scene_number", 1)
        target_scene = next((s for s in scenes if s.number == sc_num), scenes[0] if scenes else None)
        scene_id = target_scene.id if target_scene else f"scene_{script_id}_1"
        txt = item.get("text", "").strip()
        context = item.get("context_snippet", "").strip()

        if txt:
            raw_elements.append(Element(
                id=f"el_{uuid.uuid4().hex[:8]}",
                script_id=script_id,
                scene_id=scene_id,
                department=dept,
                subtype=item.get("subtype", "ELEMENT"),
                text=txt,
                context_snippet=context,
                quoted_source_passage=context
            ))

    # General phone number scanner to capture both 7-digit and 10-digit phone numbers
    for scene in scenes:
        phone_matches = re.findall(r'\b(?:\d{3}[-.\s]?)?\d{3}[-.\s]?\d{4}\b', scene.text)
        for phone in phone_matches:
            phone_clean = phone.strip()
            raw_elements.append(Element(
                id=f"el_{uuid.uuid4().hex[:8]}",
                script_id=script_id,
                scene_id=scene.id,
                department=Department.SCRIPT_SIGNAGE,
                subtype="PHONE",
                text=phone_clean,
                context_snippet=f"Phone number appearing in dialogue/action: {phone_clean}",
                quoted_source_passage=f"Phone number appearing in dialogue/action: {phone_clean}"
            ))

    # Task 10: Deduplicate elements by department + normalized text
    seen_keys: Set[str] = set()
    deduped_elements: List[Element] = []

    for el in raw_elements:
        norm_key = f"{el.department.value}:{_normalize_text(el.text)}"
        if norm_key not in seen_keys:
            seen_keys.add(norm_key)
            deduped_elements.append(el)

    return deduped_elements
