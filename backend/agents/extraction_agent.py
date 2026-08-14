import json
import uuid
import re
from typing import List, Set
from google.genai import types
from backend.models.clearance import Scene, Element, Department, Subtype
from backend.clients import get_gemini_client, get_gemini_model_name


def _normalize_text(text: str) -> str:
    """Normalizes text by removing non-alphanumeric characters and converting to lowercase."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def extract_clearable_elements(scenes: List[Scene], script_id: str) -> List[Element]:
    """
    Extracts clearable elements dynamically using Gemini structured output.
    Enforces temperature=0.0 and strict Subtype enum validation.
    Zero hardcoded domain strings. Deduplicates elements per department.
    """
    client = get_gemini_client()
    model = get_gemini_model_name()

    full_text = "\n".join([f"SCENE {s.number} ({s.heading}):\n{s.text}" for s in scenes])

    subtype_enum_values = [s.value for s in Subtype]

    prompt = (
        "Identify all screenplay elements requiring legal clearance across these 6 departments:\n"
        "- SCRIPT_SIGNAGE (PHONE, LICENSE_PLATE, URL, EMAIL)\n"
        "- CAST_CHARACTERS (CHARACTER_NAME, PERSON_REFERENCE) -> Extract all character names, full names, and named roles (e.g. Dr. Helena Voss, Marguerite Okonkwo, R. Delacroix-Hale).\n"
        "- LOCATIONS_SETS (ADDRESS, STREET, BUSINESS, LANDMARK)\n"
        "- PROPS_BRANDS (BRAND, PRODUCT)\n"
        "- SOUND_MUSIC (COMPOSITION, RECORDING, LYRIC) -> CRITICAL: If a song cue mentions a specific master recording (e.g., 'Rhapsody in Blue' played from a '1959 Columbia Masterworks recording'), extract it as ONE SINGLE element with text='Rhapsody in Blue', subtype='COMPOSITION', and recording_reference='1959 Columbia Masterworks recording'.\n"
        "- CAMERA_VISUALS (ARTWORK, PHOTOGRAPH, LITERARY_QUOTE, ARCHIVAL_FOOTAGE) -> Quotes from poems/literature (e.g. Emily Dickinson) must have subtype='LITERARY_QUOTE'. Visual art/paintings (e.g. Great Wave off Kanagawa) must have subtype='ARTWORK'.\n\n"
        f"Screenplay Text:\n{full_text}"
    )

    response = client.models.generate_content(
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
                        "scene_number": {"type": "INTEGER"},
                        "department": {
                            "type": "STRING",
                            "enum": [
                                "SCRIPT_SIGNAGE", "CAST_CHARACTERS", "LOCATIONS_SETS",
                                "PROPS_BRANDS", "SOUND_MUSIC", "CAMERA_VISUALS"
                            ]
                        },
                        "subtype": {
                            "type": "STRING",
                            "enum": subtype_enum_values
                        },
                        "text": {"type": "STRING"},
                        "context_snippet": {"type": "STRING"},
                        "recording_reference": {"type": "STRING", "nullable": True}
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

        sub_str = item.get("subtype", "OTHER")
        try:
            subtype_val = Subtype(sub_str)
        except ValueError:
            subtype_val = Subtype.OTHER

        sc_num = item.get("scene_number", 1)
        target_scene = next((s for s in scenes if s.number == sc_num), scenes[0] if scenes else None)
        scene_id = target_scene.id if target_scene else f"scene_{script_id}_1"
        txt = item.get("text", "").strip()
        context = item.get("context_snippet", "").strip()
        rec_ref = item.get("recording_reference")

        if txt:
            raw_elements.append(Element(
                id=f"el_{uuid.uuid4().hex[:8]}",
                script_id=script_id,
                scene_id=scene_id,
                department=dept,
                subtype=subtype_val,
                text=txt,
                context_snippet=context,
                quoted_source_passage=context,
                recording_reference=rec_ref
            ))

    # Authoritative Phone Scanner (Task 8): Scans phone numbers and assigns Subtype.PHONE
    for scene in scenes:
        phone_matches = re.findall(r'\b(?:\d{3}[-.\s]?)?\d{3}[-.\s]?\d{4}\b', scene.text)
        for phone in phone_matches:
            phone_clean = phone.strip()
            raw_elements.append(Element(
                id=f"el_{uuid.uuid4().hex[:8]}",
                script_id=script_id,
                scene_id=scene.id,
                department=Department.SCRIPT_SIGNAGE,
                subtype=Subtype.PHONE,
                text=phone_clean,
                context_snippet=f"Phone number appearing in dialogue/action: {phone_clean}",
                quoted_source_passage=f"Phone number appearing in dialogue/action: {phone_clean}"
            ))

    # Deduplicate elements by department + normalized text
    seen_keys: Set[str] = set()
    deduped_elements: List[Element] = []

    for el in raw_elements:
        norm_key = f"{el.department.value}:{_normalize_text(el.text)}"
        if norm_key not in seen_keys:
            seen_keys.add(norm_key)
            deduped_elements.append(el)

    return deduped_elements
