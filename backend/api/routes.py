import os
import uuid
import hashlib
import datetime
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header
from fastapi.responses import JSONResponse
from backend.models.clearance import (
    ClearanceReport, DepartmentSummary, ElementReport,
    RiskRating, Department, MonitorWebhookPayload
)
from backend.agents.intake_agent import parse_script_scenes
from backend.agents.extraction_agent import extract_clearable_elements
from backend.agents.research_agents import conduct_department_research_batch
from backend.risk.engine import evaluate_risk
from backend.agents.watch_agent import register_parallel_monitors
from backend.db import storage

router = APIRouter(prefix="/api/clearance", tags=["Clearance"])


def run_full_clearance_pipeline(script_text: str, filename: str = "script.txt", title: str = "Screenplay Clearance Report") -> ClearanceReport:
    script_id = f"scr_{uuid.uuid4().hex[:8]}"
    script_hash = hashlib.sha256(script_text.encode("utf-8")).hexdigest()[:12]

    # Step 1: Intake & Scene Parsing via Gemini (Gemini Call 1)
    scenes = parse_script_scenes(script_text, script_id)

    # Step 2: Element Extraction across 6 Department Plugins via Gemini (Gemini Call 2)
    elements = extract_clearable_elements(scenes, script_id)

    # Step 3: Grounded Research via Parallel Search & Single Batch Gemini Call (Gemini Call 3)
    findings_map = conduct_department_research_batch(elements)

    dept_summaries: Dict[str, DepartmentSummary] = {
        dept.value: DepartmentSummary(department=dept) for dept in Department
    }

    total_red = 0
    total_amber = 0
    total_green = 0

    element_reports: list[ElementReport] = []

    for element in elements:
        element.quoted_source_passage = element.context_snippet

        finding = findings_map.get(element.id)
        citations = [b.url for b in finding.basis] if finding else []
        facts = finding.facts if finding else None

        # Department-Scoped Deterministic Risk Scoring (Plain Python Rule Engine)
        verdict = evaluate_risk(element, facts, citations)

        item_report = ElementReport(
            element=element,
            finding=finding,
            verdict=verdict,
            verdict_history=[verdict]
        )
        element_reports.append(item_report)

        # Department metrics update
        dept_key = element.department.value
        summary = dept_summaries[dept_key]
        summary.elements.append(item_report)
        summary.total_elements += 1

        if verdict.rating == RiskRating.RED:
            summary.red_count += 1
            total_red += 1
        elif verdict.rating == RiskRating.AMBER:
            summary.amber_count += 1
            total_amber += 1
        elif verdict.rating == RiskRating.GREEN:
            summary.green_count += 1
            total_green += 1

    # Step 4: Register Parallel Monitors for RED/AMBER items
    monitors = register_parallel_monitors(element_reports)

    report = ClearanceReport(
        script_id=script_id,
        filename=filename,
        script_hash=script_hash,
        title=title,
        scenes=scenes,
        departments=dept_summaries,
        monitors=monitors,
        total_elements=len(elements),
        red_count=total_red,
        amber_count=total_amber,
        green_count=total_green,
        status="COMPLETE",
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    # Save to persistent storage
    storage.save_report(report)
    return report


@router.get("/demo")
def run_demo_clearance():
    """Runs end-to-end clearance pipeline ONLY on explicit demo button click."""
    seed_path = os.path.join(os.path.dirname(__file__), "..", "..", "seed", "scene_01.txt")
    if not os.path.exists(seed_path):
        raise HTTPException(status_code=404, detail="Seed scene file not found.")

    with open(seed_path, "r", encoding="utf-8") as f:
        script_text = f.read()

    try:
        return run_full_clearance_pipeline(script_text, filename="scene_01.txt", title="Seeded Screenplay Scene 01")
    except Exception as e:
        script_hash = hashlib.sha256(script_text.encode("utf-8")).hexdigest()[:12]
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(e),
                "filename": "scene_01.txt",
                "script_hash": script_hash,
                "status": "INCOMPLETE_ERROR"
            }
        )


@router.post("/analyze")
def analyze_script(
    text: Optional[str] = Form(None),
    filename: Optional[str] = Form("submitted_script.txt"),
    title: Optional[str] = Form("Uploaded Screenplay"),
    file: Optional[UploadFile] = File(None)
):
    """
    Ingests raw text or script file and returns full clearance report.
    FAIL-LOUD ENFORCEMENT: Never substitutes example content during a real run.
    If Gemini/Parallel fails, returns a 502 JSON error marking the run INCOMPLETE.
    """
    script_text = ""
    target_filename = filename or "submitted_script.txt"

    if file is not None and hasattr(file, "file"):
        script_text = file.file.read().decode("utf-8", errors="ignore")
        if file.filename:
            target_filename = file.filename
    elif text:
        script_text = text
    else:
        raise HTTPException(status_code=400, detail="Must provide script text or file.")

    script_hash = hashlib.sha256(script_text.encode("utf-8")).hexdigest()[:12]

    try:
        return run_full_clearance_pipeline(script_text, filename=target_filename, title=title or target_filename)
    except Exception as err:
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(err),
                "filename": target_filename,
                "script_hash": script_hash,
                "status": "INCOMPLETE_ERROR"
            }
        )


@router.get("/report/{script_id}", response_model=ClearanceReport)
def get_report(script_id: str):
    report = storage.get_report(script_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.post("/webhooks/monitor")
def parallel_monitor_webhook(payload: MonitorWebhookPayload, x_monitor_secret: Optional[str] = Header(None)):
    secret = os.getenv("MONITOR_WEBHOOK_SECRET")
    if secret and x_monitor_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret signature.")

    element_id = payload.element_id
    target_report: Optional[ClearanceReport] = None
    target_item: Optional[ElementReport] = None

    # Locate element across persistent reports
    all_reports = storage.get_all_reports()
    for r in all_reports.values():
        for dept in r.departments.values():
            for item in dept.elements:
                if item.element.id == element_id:
                    target_item = item
                    target_report = r
                    break

    if not target_item or not target_report:
        return {"status": "ignored", "reason": "Element not found in persistent store"}

    # Re-evaluate risk with updated facts
    new_verdict = evaluate_risk(target_item.element, payload.updated_facts, payload.cites)

    # Link superseded verdict
    previous_verdict = target_item.verdict
    previous_verdict.superseded_by = new_verdict.id

    # Update active verdict & append to audit history
    target_item.verdict = new_verdict
    target_item.verdict_history.append(new_verdict)

    # Persist updated report
    storage.save_report(target_report)

    return {
        "status": "success",
        "element_id": element_id,
        "new_rating": new_verdict.rating,
        "rule_id": new_verdict.rule_id,
        "audit_history_length": len(target_item.verdict_history)
    }
