import os
import uuid
import re
from typing import List
from backend.models.clearance import Scene

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None


def parse_script_scenes(script_text: str, script_id: str) -> List[Scene]:
    """
    Parses raw screenplay text into structured scenes.
    Uses Gemini structured output via google-genai when available, or reliable screenplay header regex fallback.
    """
    scenes: List[Scene] = []

    # Try Gemini via google-genai SDK if API key present
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key and genai is not None:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Parse the following screenplay text into individual scene headings and body text:\n\n{script_text}"
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "heading": {"type": "STRING"},
                                "text": {"type": "STRING"}
                            },
                            "required": ["heading", "text"]
                        }
                    }
                )
            )
            import json
            data = json.loads(response.text)
            for idx, item in enumerate(data, start=1):
                scenes.append(Scene(
                    id=f"scene_{script_id}_{idx}",
                    number=idx,
                    heading=item.get("heading", f"SCENE {idx}"),
                    text=item.get("text", "")
                ))
            if scenes:
                return scenes
        except Exception:
            pass

    # Regex screenplay parser fallback (EXT. / INT. scene headers)
    scene_blocks = re.split(r'\n(?=(?:INT\.|EXT\.|INT\./EXT\.|EXT\./INT\.)\s)', script_text)
    scene_num = 1
    for block in scene_blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n", 1)
        heading = lines[0].strip()
        text = lines[1].strip() if len(lines) > 1 else block
        scenes.append(Scene(
            id=f"scene_{script_id}_{scene_num}",
            number=scene_num,
            heading=heading if re.match(r'^(INT|EXT)', heading) else f"SCENE {scene_num}: {heading[:30]}",
            text=text
        ))
        scene_num += 1

    return scenes
