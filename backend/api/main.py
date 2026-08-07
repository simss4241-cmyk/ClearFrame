import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router as clearance_router

app = FastAPI(
    title="CLEARFRAME — Screenplay Clearance Agent",
    description="Cited, risk-rated screenplay clearance report engine powered by Google Cloud & Parallel.",
    version="1.0.0"
)

# CORS middleware for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Clearance API router
app.include_router(clearance_router)

# Mount frontend directory for single-service Cloud Run deployment
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "CLEARFRAME"}
