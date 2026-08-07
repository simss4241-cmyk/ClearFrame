import json
import uuid
from typing import List
from google.genai import types
from backend.models.clearance import Scene
from backend.clients import get_gemini_client, get_gemini_model_name


def parse_script_scenes(script_text: str, script_id: str) -> List[Scene]:
    """
    Parses raw screenplay text into structured scene headings and body text using Gemini.
    No silent fallbacks. If Gemini fails or credentials are invalid, raises RuntimeError.
    """
    client = get_gemini_client()
    model = get_gemini_model_name()

    prompt = (
        "Parse the following screenplay text into individual scene headings and body text.\n"
        "Return a JSON array of scene objects where each object has a 'number' (integer starting at 1), "
        "'heading' (e.g. EXT. STREET - NIGHT), and 'text' (body text of the scene).\n\n"
        f"Screenplay Text:\n{script_text}"
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
                        "number": {"type": "INTEGER"},
                        "heading": {"type": "STRING"},
                        "text": {"type": "STRING"}
                    },
                    "required": ["number", "heading", "text"]
                }
            }
        )
    )

    if not response.text:
        raise RuntimeError("Gemini intake agent returned empty output.")

    raw_data = json.loads(response.text)
    scenes: List[Scene] = []
    for item in raw_data:
        num = item.get("number", len(scenes) + 1)
        scenes.append(Scene(
            id=f"scene_{script_id}_{num}",
            number=num,
            heading=item.get("heading", f"SCENE {num}"),
            text=item.get("text", "")
        ))

    if not scenes:
        raise RuntimeError("Gemini intake agent produced 0 parsed scenes.")

    return scenes
