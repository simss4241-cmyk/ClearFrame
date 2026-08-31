import os
import logging
from typing import Optional
from google import genai
from parallel import Parallel

logger = logging.getLogger("clearframe.clients")


def get_gemini_client() -> genai.Client:
    """
    Resolves Google Cloud Gemini Client.
    Supports Vertex AI (ADC) or Direct API Key via GEMINI_API_KEY.
    FAIL-LOUD COMPLIANCE: If Vertex AI is requested but GOOGLE_CLOUD_PROJECT is unset
    or placeholder, raises a fast RuntimeError instead of silent fallback.
    """
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key and api_key.strip():
        logger.info("Initializing Gemini Client via Google AI API Key.")
        return genai.Client(api_key=api_key.strip())

    if use_vertex:
        if not project or project.strip() == "" or project == "your-gcp-project-id":
            raise RuntimeError(
                "GOOGLE_GENAI_USE_VERTEXAI is set to true, but GOOGLE_CLOUD_PROJECT is unset or placeholder. "
                "Set a valid GCP project ID or set GOOGLE_GENAI_USE_VERTEXAI=false to use GEMINI_API_KEY."
            )
        logger.info(f"Initializing Gemini Client via Vertex AI (project={project}, location={location})")
        return genai.Client(vertexai=True, project=project, location=location)

    raise RuntimeError(
        "No valid Google Cloud AI credentials found. "
        "Provide GEMINI_API_KEY in .env or configure Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=true)."
    )


def get_parallel_client() -> Parallel:
    """
    Resolves Parallel SDK Client.
    FAIL-LOUD COMPLIANCE: Raises RuntimeError if PARALLEL_API_KEY is missing.
    """
    api_key = os.getenv("PARALLEL_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("PARALLEL_API_KEY is not configured in environment or .env file.")

    return Parallel(api_key=api_key.strip())


def get_gemini_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
