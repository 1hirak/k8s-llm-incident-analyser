import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyse, reports, scenarios

app = FastAPI(
    title="K8s LLM Incident Analyser",
    description="LLM-assisted Kubernetes incident analysis pipeline",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyse.router, prefix="/analyse", tags=["Analysis"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])

if os.environ.get("ENABLE_SCENARIOS", "false").lower() == "true":
    app.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "provider": os.environ.get("LLM_PROVIDER")}
