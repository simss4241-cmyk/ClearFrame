import json
import xml.etree.ElementTree as ET
from typing import List
from google.genai import types
from backend.models.clearance import Scene
from backend.clients import get_gemini_client, get_gemini_model_name


def clean_screenplay_input(script_text: str) -> str:
    """
    Normalizes screenplay input. If Final Draft (.fdx) XML is detected,
    parses Paragraph and Text nodes into standard screenplay text.
    """
    trimmed = script_text.strip()
    if trimmed.startswith("<?xml") or "<FinalDraft" in trimmed or "<Paragraph" in trimmed:
        try:
            root = ET.fromstring(trimmed)
            lines = []
            for elem in root.iter("Paragraph"):
                p_type = elem.get("Type", "")
                text_parts = [t.text for t in elem.iter("Text") if t.text]
                p_text = "".join(text_parts).strip()
                if not p_text:
                    continue
                if p_type == "Scene Heading":
                    lines.append(f"\n{p_text.upper()}\n")
                elif p_type == "Character":
                    lines.append(f"\n                    {p_text.upper()}")
                elif p_type == "Parenthetical":
                    lines.append(f"              {p_text}")
                elif p_type == "Dialogue":
                    lines.append(f"          {p_text}")
                elif p_type == "Transition":
                    lines.append(f"\n                                              {p_text}\n")
                else:
                    lines.append(f"{p_text}")
            return "\n".join(lines).strip()
        except Exception:
            # If XML parsing fails, proceed with raw text
            pass
    return script_text


def parse_script_scenes(script_text: str, script_id: str) -> List[Scene]:
    """
    Parses raw screenplay text into structured Scene models using Gemini structured output.
    Enforces temperature=0.0 for zero-variance intake.
    """
    cleaned_text = clean_screenplay_input(script_text)
    client = get_gemini_client()
    model = get_gemini_model_name()

    prompt = (
        "Parse the following screenplay text into structured scenes. "
        "Extract scene numbers, scene headings (e.g. EXT. LOCATION - TIME), and the verbatim text under each scene.\n\n"
        f"Screenplay Text:\n{cleaned_text}"
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
                        "number": {"type": "INTEGER"},
                        "heading": {"type": "STRING"},
                        "text": {"type": "STRING"}
                    },
                    "required": ["number", "heading", "text"]
                }
            }
        )
    )

    if not response or not response.text:
        raise RuntimeError("Gemini scene intake returned empty output.")

    raw_scenes = json.loads(response.text)
    scenes: List[Scene] = []
    for sc in raw_scenes:
        sc_num = sc.get("number", len(scenes) + 1)
        scenes.append(Scene(
            id=f"scene_{script_id}_{sc_num}",
            number=sc_num,
            heading=sc.get("heading", "SCENE"),
            text=sc.get("text", "")
        ))

    return scenes
