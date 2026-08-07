import os
import uuid
from typing import List
from backend.models.clearance import ElementReport, RiskRating, MonitorRegistration
from backend.clients import get_parallel_client


def register_parallel_monitors(element_reports: List[ElementReport]) -> List[MonitorRegistration]:
    """
    Registers standing Parallel Monitors for RED and AMBER flagged elements.
    Uses exact Parallel SDK monitor creation signature:
      client.monitor.create(
          type="event_stream",
          frequency="1d",
          processor="lite",
          settings={"query": query},
          webhook=...,
          metadata={"external_id": element.id}
      )
    Skips webhook parameter when PUBLIC_BASE_URL is unset or localhost.
    """
    monitors: List[MonitorRegistration] = []
    client = get_parallel_client()
    base_url = os.getenv("PUBLIC_BASE_URL", "")

    is_local = not base_url or base_url.startswith("http://localhost") or base_url.startswith("http://127.0.0.1")

    for item in element_reports:
        # Watch RED and AMBER items
        if item.verdict.rating in [RiskRating.RED, RiskRating.AMBER]:
            query = f"Legal trademark copyright update for {item.element.text}"
            
            payload = {
                "type": "event_stream",
                "frequency": os.getenv("PARALLEL_MONITOR_FREQUENCY", "1d"),
                "processor": os.getenv("PARALLEL_MONITOR_PROCESSOR", "lite"),
                "settings": {"query": query},
                "metadata": {"external_id": item.element.id}
            }

            if not is_local:
                payload["webhook"] = {
                    "url": f"{base_url}/api/clearance/webhooks/monitor",
                    "event_types": ["monitor.event.detected"]
                }
            else:
                print(f"[WATCH AGENT NOTICE] PUBLIC_BASE_URL is local ({base_url}). Registering monitor without unreachable local webhook.")

            res = client.monitor.create(**payload)
            mon_id = getattr(res, "monitor_id", getattr(res, "id", f"par_mon_{uuid.uuid4().hex[:8]}"))

            reg = MonitorRegistration(
                id=f"mon_{uuid.uuid4().hex[:8]}",
                element_id=item.element.id,
                parallel_monitor_id=mon_id,
                query=query,
                department=item.element.department,
                frequency=payload["frequency"],
                status="ACTIVE"
            )
            monitors.append(reg)

    return monitors
