from pydantic import BaseModel
from typing import Literal, Optional


class EvidenceItem(BaseModel):
    source: Literal["pod_log", "previous_pod_log", "kubernetes_event", "pod_status"]
    pod: str
    timestamp: Optional[str] = None
    evidence: str
