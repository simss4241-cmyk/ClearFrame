import logging
from typing import List, Dict
from backend.models.clearance import Element, Finding
from backend.tools.parallel_tools import batch_research_elements_parallel

logger = logging.getLogger("clearframe.research")


def conduct_department_research_batch(elements: List[Element]) -> Dict[str, Finding]:
    """
    Executes grounded research for a batch of elements.
    Interleaves Parallel Search calls, then sends ONE batch Gemini request.
    Returns mapping of element_id -> Finding.
    """
    return batch_research_elements_parallel(elements)
