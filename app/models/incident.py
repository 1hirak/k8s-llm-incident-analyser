from typing import Literal

from pydantic import BaseModel, Field

from app.models.evidence import EvidenceItem

FailureCategory = Literal[
    "crash", "config", "dependency", "network", "image", "resource", "probe", "unknown"
]
Severity = Literal["low", "medium", "high", "critical"]


class IncidentReport(BaseModel):
    incident_summary: str = Field(..., min_length=10)
    likely_root_cause: str = Field(..., min_length=10)
    affected_component: str
    failure_category: FailureCategory
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_evidence: list[EvidenceItem] = Field(..., min_length=1)
    suggested_fix: str
    recommended_commands: list[str]
    human_verification_steps: list[str]

    model_config = {"extra": "ignore"}
