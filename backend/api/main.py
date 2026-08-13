import os
import logging
from dotenv import load_dotenv

# Load environment variables at import time
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router as clearance_router
from backend.clients import get_gemini_client, get_parallel_client

logger = logging.getLogger("clearframe.main")

app = FastAPI(
    title="CLEARFRAME — Screenplay Clearance Agent",
    description="Cited, risk-rated screenplay clearance report engine powered by Google Cloud & Parallel.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    return JSONResponse(
        status_code=502,
        content={"detail": f"Upstream AI/Service Error: {str(exc)}"}
    )


# TASK 4: Fail Fast Startup Check — Raises on boot if credentials or SDKs are unconfigured
@app.on_event("startup")
def verify_credentials_on_boot():
    logger.info("Executing preflight credential check...")
    get_gemini_client()
    get_parallel_client()
    logger.info("Credentials & SDK clients verified successfully.")


# Include Clearance API router
app.include_router(clearance_router)


# TASK 5: Declare /health route BEFORE static files mount so Cloud Run health check matches correctly
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "CLEARFRAME"}


# Mount static frontend directory
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
