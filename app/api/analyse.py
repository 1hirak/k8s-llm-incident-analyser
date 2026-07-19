import uuid

import structlog
from fastapi import APIRouter, HTTPException

from app.core.collector import KubernetesCollector
from app.core.llm import get_provider
from app.core.preprocessor import LogPreprocessor
from app.core.redactor import LogRedactor
from app.models.incident import IncidentReport

router = APIRouter()
log = structlog.get_logger()

collector = KubernetesCollector()
preprocessor = LogPreprocessor()
redactor = LogRedactor()


@router.post("/pod/{namespace}/{pod_name}", response_model=IncidentReport)
async def analyse_pod(namespace: str, pod_name: str) -> IncidentReport:
    request_id = str(uuid.uuid4())[:8]
    log.info("analysis_started", id=request_id, ns=namespace, pod=pod_name)

    try:
        raw = collector.collect(namespace, pod_name)
        filtered = preprocessor.process(raw)
        safe = redactor.redact(filtered)
        provider = get_provider()
        report = await provider.analyse(safe)
        log.info(
            "analysis_complete",
            id=request_id,
            category=report.failure_category,
        )
        return report
    except Exception as e:
        log.error("analysis_failed", id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
