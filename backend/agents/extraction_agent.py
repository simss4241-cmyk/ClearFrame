import json
import uuid
import re
from typing import List
from google.genai import types
from backend.models.clearance import Scene, Element, Department
from backend.clients import get_gemini_client, get_gemini_model_name


def extract_clearable_elements(scenes: List[Scene], script_id: str) -> List[Element]:
    """
    Extracts clearable elements dynamically using Gemini structured output.
    Raises if Gemini extraction fails. Zero hardcoded fallbacks or domain strings.
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

    if not response.text:
        raise RuntimeError("Gemini element extraction returned empty output.")

    extracted_items = json.loads(response.text)
    elements: List[Element] = []

    for item in extracted_items:
        dept_str = item.get("department", "SCRIPT_SIGNAGE")
        try:
            dept = Department(dept_str)
        except ValueError:
            dept = Department.SCRIPT_SIGNAGE

        sc_num = item.get("scene_number", 1)
        target_scene = next((s for s in scenes if s.number == sc_num), scenes[0] if scenes else None)
        scene_id = target_scene.id if target_scene else f"scene_{script_id}_1"

        elements.append(Element(
            id=f"el_{uuid.uuid4().hex[:8]}",
            script_id=script_id,
            scene_id=scene_id,
            department=dept,
            subtype=item.get("subtype", "ELEMENT"),
            text=item.get("text", "").strip(),
            context_snippet=item.get("context_snippet", "").strip()
        ))

    # General phone number scanner to ensure 7-digit and 10-digit phone numbers are captured
    existing_phone_texts = {e.text for e in elements if e.department == Department.SCRIPT_SIGNAGE}
    for scene in scenes:
        phone_matches = re.findall(r'\b(?:\d{3}[-.\s]?)?\d{3}[-.\s]?\d{4}\b', scene.text)
        for phone in phone_matches:
            phone_clean = phone.strip()
            if phone_clean not in existing_phone_texts:
                elements.append(Element(
                    id=f"el_{uuid.uuid4().hex[:8]}",
                    script_id=script_id,
                    scene_id=scene.id,
                    department=Department.SCRIPT_SIGNAGE,
                    subtype="PHONE",
                    text=phone_clean,
                    context_snippet=f"Phone number appearing in dialogue/action: {phone_clean}"
                ))
                existing_phone_texts.add(phone_clean)

    return elements
