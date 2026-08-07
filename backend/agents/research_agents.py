import datetime
import uuid
from backend.models.clearance import Element, Finding
from backend.tools.parallel_tools import deep_research_element_parallel


def conduct_department_research(element: Element) -> Finding:
    """
    Executes Parallel research for an extracted script element.
    Passes full Element model to deep_research_element_parallel.
    Zero risk rating or severity assignment in this step.
    """
    res = deep_research_element_parallel(element)

    finding = Finding(
        id=f"find_{uuid.uuid4().hex[:8]}",
        element_id=element.id,
        department=element.department,
        facts=res["facts"],
        basis=res["basis"],
        parallel_search_id=res.get("parallel_search_id"),
        researched_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    return finding
