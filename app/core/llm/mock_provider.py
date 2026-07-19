from app.core.llm.base import BaseLLMProvider
from app.core.preprocessor import EvidencePackage
from app.models.evidence import EvidenceItem
from app.models.incident import IncidentReport


class MockProvider(BaseLLMProvider):
    async def analyse(self, package: EvidencePackage) -> IncidentReport:
        logs = (package.current_logs + package.previous_logs).lower()

        if "database_url" in logs:
            category, cause = "config", "Missing DATABASE_URL environment variable"
        elif "connection refused" in logs:
            category, cause = "dependency", "Dependent service is unreachable"
        elif "oomkilled" in logs or "memory" in logs or \
                "memory" in package.pod_status_summary.lower():
            category, cause = "resource", "Container exceeded memory limit (OOMKilled)"
        elif "imagepullbackoff" in logs:
            category, cause = "image", "Kubernetes cannot pull the container image"
        else:
            category, cause = "unknown", "Unable to determine root cause from evidence"

        return IncidentReport(
            incident_summary=f"[MOCK] Failure detected in {package.pod_name}",
            likely_root_cause=cause,
            affected_component=package.pod_name,
            failure_category=category,
            severity="medium",
            confidence=0.5,
            supporting_evidence=[
                EvidenceItem(
                    source="pod_log",
                    pod=package.pod_name,
                    evidence=package.current_logs[:200] or "(no logs)",
                )
            ],
            suggested_fix="[MOCK] Investigate the reported root cause.",
            recommended_commands=[
                f"kubectl describe pod -n {package.namespace} {package.pod_name}"
            ],
            human_verification_steps=[
                "Check the logs manually",
                "Verify environment variables",
            ],
        )
