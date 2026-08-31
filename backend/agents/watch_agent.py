import os
import logging
from typing import List, Optional
from backend.models.clearance import ElementReport, RiskRating, MonitorRegistration
from backend.clients import get_parallel_client

logger = logging.getLogger("clearframe.watch")


def register_parallel_monitors(element_reports: List[ElementReport]) -> List[MonitorRegistration]:
    """
    Registers standing Parallel Monitors for RED and AMBER flagged elements.
    Uses exact Parallel SDK monitor creation signature.
    Respects ENABLE_PARALLEL_MONITORS to prevent credit exhaustion during local development / automated tests.
    Does NOT invent fallback monitor IDs when the API returns none or fails.
    """
    monitors: List[MonitorRegistration] = []

    enable_monitors = os.getenv("ENABLE_PARALLEL_MONITORS", "true").lower() in ("true", "1", "yes")
    max_monitors_str = os.getenv("PARALLEL_MONITOR_MAX_COUNT", "10")
    try:
        max_monitors = int(max_monitors_str)
    except ValueError:
        max_monitors = 10

    if not enable_monitors:
        logger.info("ENABLE_PARALLEL_MONITORS is disabled (false). Skipping live Parallel Monitor creation.")
        for item in element_reports:
            if item.verdict.rating in [RiskRating.RED, RiskRating.AMBER]:
                monitors.append(MonitorRegistration(
                    id=f"mon_{item.element.id}",
                    element_id=item.element.id,
                    parallel_monitor_id=None,
                    query=f"Legal trademark copyright update for {item.element.text}",
                    department=item.element.department,
                    frequency=os.getenv("PARALLEL_MONITOR_FREQUENCY", "1d"),
                    status="DISABLED"
                ))
        return monitors

    client = get_parallel_client()
    base_url = os.getenv("PUBLIC_BASE_URL", "")
    is_local = not base_url or base_url.startswith("http://localhost") or base_url.startswith("http://127.0.0.1")

    registered_count = 0

    for item in element_reports:
        # Register watch for RED and AMBER items
        if item.verdict.rating in [RiskRating.RED, RiskRating.AMBER]:
            if max_monitors > 0 and registered_count >= max_monitors:
                logger.info(f"Reached PARALLEL_MONITOR_MAX_COUNT ({max_monitors}). Skipping remaining monitors.")
                monitors.append(MonitorRegistration(
                    id=f"mon_{item.element.id}",
                    element_id=item.element.id,
                    parallel_monitor_id=None,
                    query=f"Legal trademark copyright update for {item.element.text}",
                    department=item.element.department,
                    frequency=os.getenv("PARALLEL_MONITOR_FREQUENCY", "1d"),
                    status="CAPPED"
                ))
                continue

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
                logger.info(f"PUBLIC_BASE_URL is local ({base_url}). Creating monitor without unreachable local webhook.")

            mon_id = None
            status = "ACTIVE"
            try:
                res = client.monitor.create(**payload)
                if res:
                    mon_id = getattr(res, "monitor_id", getattr(res, "id", None))
                if not mon_id:
                    status = "FAILED"
                else:
                    registered_count += 1
            except Exception as e:
                logger.error(f"Parallel Monitor creation failed for element '{item.element.id}' ({item.element.text}): {e}")
                status = "FAILED"

            reg = MonitorRegistration(
                id=f"mon_{item.element.id}",
                element_id=item.element.id,
                parallel_monitor_id=mon_id,
                query=query,
                department=item.element.department,
                frequency=payload["frequency"],
                status=status
            )
            monitors.append(reg)

    return monitors
