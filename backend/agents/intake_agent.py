import json
from typing import List
from google.genai import types
from backend.models.clearance import Scene
from backend.clients import get_gemini_client, get_gemini_model_name


def parse_script_scenes(script_text: str, script_id: str) -> List[Scene]:
    """
    Parses raw screenplay text into structured Scene models using Gemini structured output.
    Enforces temperature=0.0 for zero-variance intake.
    """
    client = get_gemini_client()
    model = get_gemini_model_name()

    prompt = (
        "Parse the following screenplay text into structured scenes. "
        "Extract scene numbers, scene headings (e.g. EXT. LOCATION - TIME), and the verbatim text under each scene.\n\n"
        f"Screenplay Text:\n{script_text}"
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
