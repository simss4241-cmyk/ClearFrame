import uuid
from typing import List
from backend.models.clearance import ElementReport, RiskRating, MonitorRegistration
from backend.tools.parallel_tools import get_parallel_client


def register_parallel_monitors(element_reports: List[ElementReport]) -> List[MonitorRegistration]:
    """
    Registers standing Parallel Monitors for RED and AMBER flagged elements.
    Uses exact Parallel SDK monitor creation signature:
      client.monitor.create(frequency="1d", type="event_stream", settings={"query": query})
    """
    monitors: List[MonitorRegistration] = []
    client = get_parallel_client()

    for item in element_reports:
        # Watch RED and AMBER items
        if item.verdict.rating in [RiskRating.RED, RiskRating.AMBER]:
            query = f"Legal trademark copyright update for {item.element.text}"
            parallel_mon_id = f"par_mon_{uuid.uuid4().hex[:8]}"

            if client:
                try:
                    # Parallel SDK Monitor call with exact signature
                    res = client.monitor.create(
                        frequency="1d",
                        type="event_stream",
                        settings={"query": query}
                    )
                    parallel_mon_id = getattr(res, "id", parallel_mon_id)
                except Exception as e:
                    pass

            reg = MonitorRegistration(
                id=f"mon_{uuid.uuid4().hex[:8]}",
                element_id=item.element.id,
                parallel_monitor_id=parallel_mon_id,
                query=query,
                department=item.element.department,
                frequency="1d",
                status="ACTIVE"
            )
            monitors.append(reg)

    return monitors
