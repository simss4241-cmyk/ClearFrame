import os
from typing import Any
from dotenv import load_dotenv

# Load .env variables into environment
load_dotenv()

try:
    from google import genai
except ImportError:
    genai = None

try:
    from parallel import Parallel
except ImportError:
    Parallel = None


def get_gemini_client() -> Any:
    """
    Resolves Gemini Client via google-genai SDK.
    Supports Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT)
    or Direct Gemini API Key (GEMINI_API_KEY or GOOGLE_API_KEY).
    Fails loudly if neither is configured.
    """
    if genai is None:
        raise RuntimeError("google-genai package is not installed.")

    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    if use_vertex:
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if not project or project == "your-project-id":
            # Fallback to API Key if Vertex project ID is unconfigured placeholder
            key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if key:
                return genai.Client(api_key=key)
            raise RuntimeError(
                "GOOGLE_GENAI_USE_VERTEXAI=true but GOOGLE_CLOUD_PROJECT is unset or placeholder."
            )
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "Gemini client initialization failed: Neither Vertex AI nor GEMINI_API_KEY is configured."
        )
    return genai.Client(api_key=key)


def get_parallel_client() -> Any:
    """
    Resolves Parallel Client via parallel-web SDK.
    Fails loudly if PARALLEL_API_KEY is missing.
    """
    if Parallel is None:
        raise RuntimeError("parallel-web package is not installed.")

    key = os.getenv("PARALLEL_API_KEY")
    if not key:
        raise RuntimeError(
            "Parallel client initialization failed: PARALLEL_API_KEY is missing."
        )
    return Parallel(api_key=key)


def get_gemini_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
