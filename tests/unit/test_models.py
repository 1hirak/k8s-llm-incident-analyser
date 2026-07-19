import pytest

from app.models.evidence import EvidenceItem
from app.models.incident import FailureCategory, IncidentReport, Severity


class TestEvidenceItem:
    def test_valid_evidence_item(self):
        item = EvidenceItem(
            source="pod_log",
            pod="demo-app-abc",
            timestamp="2025-05-01T10:00:00Z",
            evidence="ERROR Missing DATABASE_URL",
        )
        assert item.source == "pod_log"
        assert item.pod == "demo-app-abc"
        assert item.evidence == "ERROR Missing DATABASE_URL"

    def test_valid_source_values(self):
        for source in ["pod_log", "previous_pod_log", "kubernetes_event", "pod_status"]:
            item = EvidenceItem(source=source, pod="p", evidence="test")
            assert item.source == source

    def test_invalid_source_rejected(self):
        with pytest.raises(ValueError):
            EvidenceItem(source="invalid_source", pod="p", evidence="test")

    def test_timestamp_optional(self):
        item = EvidenceItem(source="pod_log", pod="p", evidence="test")
        assert item.timestamp is None


class TestIncidentReport:
    def test_valid_full_report(self):
        report = IncidentReport(
            incident_summary="Pod crashed due to missing env var",
            likely_root_cause="DATABASE_URL environment variable not set",
            affected_component="demo-app",
            failure_category="config",
            severity="critical",
            confidence=0.95,
            supporting_evidence=[
                EvidenceItem(
                    source="pod_log", pod="demo-app",
                    evidence="FATAL: Missing DATABASE_URL",
                )
            ],
            suggested_fix="Add DATABASE_URL to deployment env",
            recommended_commands=["kubectl set env deploy/demo-app DATABASE_URL=postgres://..."],
            human_verification_steps=["Check deployment YAML", "Verify pod logs"],
        )
        assert report.failure_category == "config"
        assert report.severity == "critical"
        assert report.confidence == 0.95

    def test_all_failure_categories(self):
        for cat in ["crash", "config", "dependency", "network",
                     "image", "resource", "probe", "unknown"]:
            r = IncidentReport(
                incident_summary="x" * 10,
                likely_root_cause="y" * 10,
                affected_component="c",
                failure_category=cat,
                severity="medium",
                confidence=0.5,
                supporting_evidence=[EvidenceItem(source="pod_log", pod="p", evidence="e")],
                suggested_fix="fix",
                recommended_commands=["cmd"],
                human_verification_steps=["step"],
            )
            assert r.failure_category == cat

    def test_invalid_failure_category_rejected(self):
        with pytest.raises(ValueError):
            IncidentReport(
                incident_summary="x" * 10,
                likely_root_cause="y" * 10,
                affected_component="c",
                failure_category="bad_category",
                severity="medium",
                confidence=0.5,
                supporting_evidence=[EvidenceItem(source="pod_log", pod="p", evidence="e")],
                suggested_fix="fix",
                recommended_commands=["cmd"],
                human_verification_steps=["step"],
            )

    def test_all_severity_values(self):
        for sev in ["low", "medium", "high", "critical"]:
            r = IncidentReport(
                incident_summary="x" * 10,
                likely_root_cause="y" * 10,
                affected_component="c",
                failure_category="crash",
                severity=sev,
                confidence=0.5,
                supporting_evidence=[EvidenceItem(source="pod_log", pod="p", evidence="e")],
                suggested_fix="fix",
                recommended_commands=["cmd"],
                human_verification_steps=["step"],
            )
            assert r.severity == sev

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            IncidentReport(
                incident_summary="x" * 10, likely_root_cause="y" * 10,
                affected_component="c", failure_category="crash",
                severity="low", confidence=1.5,
                supporting_evidence=[EvidenceItem(source="pod_log", pod="p", evidence="e")],
                suggested_fix="fix", recommended_commands=["cmd"],
                human_verification_steps=["step"],
            )

    def test_min_length_summary_too_short(self):
        with pytest.raises(ValueError):
            IncidentReport(
                incident_summary="short",
                likely_root_cause="y" * 10,
                affected_component="c",
                failure_category="crash",
                severity="low",
                confidence=0.5,
                supporting_evidence=[EvidenceItem(source="pod_log", pod="p", evidence="e")],
                suggested_fix="fix",
                recommended_commands=["cmd"],
                human_verification_steps=["step"],
            )

    def test_empty_supporting_evidence_rejected(self):
        with pytest.raises(ValueError):
            IncidentReport(
                incident_summary="x" * 10,
                likely_root_cause="y" * 10,
                affected_component="c",
                failure_category="crash",
                severity="low",
                confidence=0.5,
                supporting_evidence=[],
                suggested_fix="fix",
                recommended_commands=["cmd"],
                human_verification_steps=["step"],
            )

    def test_extra_fields_ignored(self):
        report = IncidentReport(
            incident_summary="x" * 10,
            likely_root_cause="y" * 10,
            affected_component="c",
            failure_category="crash",
            severity="low",
            confidence=0.5,
            supporting_evidence=[EvidenceItem(source="pod_log", pod="p", evidence="e")],
            suggested_fix="fix",
            recommended_commands=["cmd"],
            human_verification_steps=["step"],
            extra_field="should be ignored",
        )
        assert not hasattr(report, "extra_field")

    def test_model_json_schema(self):
        schema = IncidentReport.model_json_schema()
        assert schema["title"] == "IncidentReport"
        assert "incident_summary" in schema["properties"]
        assert "confidence" in schema["properties"]

    def test_failure_category_type_alias(self):
        assert FailureCategory.__args__ == (
            "crash", "config", "dependency", "network", "image", "resource", "probe", "unknown"
        )

    def test_severity_type_alias(self):
        assert Severity.__args__ == ("low", "medium", "high", "critical")
