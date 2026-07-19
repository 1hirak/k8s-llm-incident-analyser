from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.collector import RawEvidence
from app.core.preprocessor import EvidencePackage
from app.main import app
from app.models.evidence import EvidenceItem
from app.models.incident import IncidentReport


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_includes_provider(self, client):
        with patch.dict("os.environ", {"LLM_PROVIDER": "mock"}, clear=True):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["provider"] == "mock"


class TestAnalyseEndpoint:
    @patch("app.api.analyse.collector.collect")
    @patch("app.api.analyse.preprocessor.process")
    @patch("app.api.analyse.redactor.redact")
    @patch("app.api.analyse.get_provider")
    def test_analyse_pod_returns_incident_report(
        self, mock_get_provider, mock_redact, mock_process, mock_collect, client
    ):
        mock_provider = AsyncMock()
        mock_provider.analyse.return_value = IncidentReport(
            incident_summary="Pod crash detected",
            likely_root_cause="Missing DATABASE_URL environment variable",
            affected_component="demo-app",
            failure_category="config",
            severity="critical",
            confidence=0.95,
            supporting_evidence=[
                EvidenceItem(
                    source="pod_log", pod="demo-app",
                    evidence="ERROR missing DATABASE_URL",
                )
            ],
            suggested_fix="Add DATABASE_URL to deployment",
            recommended_commands=[
                "kubectl set env deploy/demo-app DATABASE_URL=postgres://..."
            ],
            human_verification_steps=["Check deployment YAML"],
        )
        mock_get_provider.return_value = mock_provider

        mock_collect.return_value = RawEvidence(
            namespace="demo", pod_name="demo-app-abc",
            current_logs="ERROR missing DATABASE_URL",
        )
        mock_process.return_value = EvidencePackage(
            namespace="demo", pod_name="demo-app-abc",
            current_logs="ERROR missing DATABASE_URL",
            previous_logs="", pod_status_summary="", k8s_events_filtered="",
            restart_count=0,
        )
        mock_redact.return_value = EvidencePackage(
            namespace="demo", pod_name="demo-app-abc",
            current_logs="ERROR missing DATABASE_URL",
            previous_logs="", pod_status_summary="", k8s_events_filtered="",
            restart_count=0,
        )

        response = client.post("/analyse/pod/demo/demo-app-abc")
        assert response.status_code == 200
        data = response.json()
        assert data["incident_summary"] == "Pod crash detected"
        assert data["failure_category"] == "config"
        assert data["severity"] == "critical"
        assert data["confidence"] == 0.95

    @patch("app.api.analyse.collector.collect")
    @patch("app.api.analyse.preprocessor.process")
    @patch("app.api.analyse.redactor.redact")
    @patch("app.api.analyse.get_provider")
    def test_analyse_pod_handles_errors(
        self, mock_get_provider, mock_redact, mock_process, mock_collect, client
    ):
        mock_provider = AsyncMock()
        mock_provider.analyse.side_effect = Exception("kubectl not found")
        mock_get_provider.return_value = mock_provider
        mock_collect.return_value = RawEvidence(
            namespace="demo", pod_name="demo-app-abc",
        )
        mock_process.return_value = EvidencePackage(
            namespace="demo", pod_name="demo-app-abc",
            current_logs="", previous_logs="",
            pod_status_summary="", k8s_events_filtered="",
            restart_count=0,
        )
        mock_redact.return_value = EvidencePackage(
            namespace="demo", pod_name="demo-app-abc",
            current_logs="", previous_logs="",
            pod_status_summary="", k8s_events_filtered="",
            restart_count=0,
        )

        response = client.post("/analyse/pod/demo/demo-app-abc")
        assert response.status_code == 500
        assert "Analysis failed" in response.json()["detail"]
