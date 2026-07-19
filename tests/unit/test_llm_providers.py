import os
from unittest.mock import patch

import pytest

from app.core.llm import get_provider
from app.core.llm.base import BaseLLMProvider
from app.core.llm.mock_provider import MockProvider
from app.core.preprocessor import EvidencePackage
from app.models.incident import IncidentReport


@pytest.fixture
def evidence_package():
    return EvidencePackage(
        namespace="demo",
        pod_name="demo-app-abc",
        current_logs="ERROR Missing DATABASE_URL",
        previous_logs="WARN previous log",
        pod_status_summary="Status: CrashLoopBackOff",
        k8s_events_filtered="Warning BackOff restarting",
        restart_count=3,
    )


class TestBaseLLMProvider:
    def test_abstract_class_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseLLMProvider()


class TestMockProvider:
    def test_mock_provider_is_concrete(self):
        provider = MockProvider()
        assert isinstance(provider, BaseLLMProvider)

    @pytest.mark.asyncio
    async def test_analyse_returns_incident_report(self, evidence_package):
        provider = MockProvider()
        report = await provider.analyse(evidence_package)
        assert isinstance(report, IncidentReport)

    @pytest.mark.asyncio
    async def test_analyse_detects_config_failure(self, evidence_package):
        provider = MockProvider()
        report = await provider.analyse(evidence_package)
        assert report.failure_category == "config"
        assert "DATABASE_URL" in report.likely_root_cause

    @pytest.mark.asyncio
    async def test_analyse_is_async(self, evidence_package):
        provider = MockProvider()
        report = await provider.analyse(evidence_package)
        assert isinstance(report, IncidentReport)

    @pytest.mark.asyncio
    async def test_detects_connection_refused(self):
        pkg = EvidencePackage(
            namespace="demo", pod_name="p",
            current_logs="ERROR connection refused to database",
            previous_logs="", pod_status_summary="", k8s_events_filtered="",
            restart_count=1,
        )
        provider = MockProvider()
        report = await provider.analyse(pkg)
        assert report.failure_category == "dependency"

    @pytest.mark.asyncio
    async def test_detects_oom(self):
        pkg = EvidencePackage(
            namespace="demo", pod_name="p",
            current_logs="memory allocation failed",
            previous_logs="", pod_status_summary="OOMKilled container demo",
            k8s_events_filtered="", restart_count=1,
        )
        provider = MockProvider()
        report = await provider.analyse(pkg)
        assert report.failure_category == "resource"

    @pytest.mark.asyncio
    async def test_detects_image_pull_failure(self):
        pkg = EvidencePackage(
            namespace="demo", pod_name="p",
            current_logs="ImagePullBackOff error",
            previous_logs="", pod_status_summary="",
            k8s_events_filtered="", restart_count=0,
        )
        provider = MockProvider()
        report = await provider.analyse(pkg)
        assert report.failure_category == "image"

    @pytest.mark.asyncio
    async def test_defaults_to_unknown(self):
        pkg = EvidencePackage(
            namespace="demo", pod_name="p",
            current_logs="INFO normal operation", previous_logs="",
            pod_status_summary="Status: Running", k8s_events_filtered="",
            restart_count=0,
        )
        provider = MockProvider()
        report = await provider.analyse(pkg)
        assert report.failure_category == "unknown"
        assert report.confidence == 0.5

    @pytest.mark.asyncio
    async def test_report_contains_required_fields(self, evidence_package):
        provider = MockProvider()
        report = await provider.analyse(evidence_package)
        assert len(report.incident_summary) >= 10
        assert len(report.likely_root_cause) >= 10
        assert len(report.supporting_evidence) >= 1
        assert len(report.recommended_commands) >= 1
        assert len(report.human_verification_steps) >= 1

    @pytest.mark.asyncio
    async def test_supporting_evidence_has_valid_source(self, evidence_package):
        provider = MockProvider()
        report = await provider.analyse(evidence_package)
        for ev in report.supporting_evidence:
            assert ev.source in (
                "pod_log", "previous_pod_log", "kubernetes_event", "pod_status"
            )

    @pytest.mark.asyncio
    async def test_confidence_within_range(self, evidence_package):
        provider = MockProvider()
        report = await provider.analyse(evidence_package)
        assert 0.0 <= report.confidence <= 1.0


class TestGetProvider:
    def test_get_provider_returns_mock_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = get_provider()
            assert isinstance(provider, MockProvider)

    def test_get_provider_returns_mock_when_set(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "mock"}, clear=True):
            provider = get_provider()
            assert isinstance(provider, MockProvider)

    def test_get_provider_returns_openai(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-fake-key-for-testing-only",
        }, clear=True):
            provider = get_provider()
            from app.core.llm.openai_provider import OpenAIProvider
            assert isinstance(provider, OpenAIProvider)

    def test_get_provider_returns_anthropic(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "sk-ant-test-fake-key-for-testing-only",
        }, clear=True):
            provider = get_provider()
            from app.core.llm.anthropic_provider import AnthropicProvider
            assert isinstance(provider, AnthropicProvider)

    def test_get_provider_returns_deepseek(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "test-fake-key-for-testing-only",
        }, clear=True):
            provider = get_provider()
            from app.core.llm.deepseek_provider import DeepSeekProvider
            assert isinstance(provider, DeepSeekProvider)

    def test_get_provider_case_insensitive(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "OPENAI",
            "OPENAI_API_KEY": "sk-test-fake-key-for-testing-only",
        }, clear=True):
            provider = get_provider()
            from app.core.llm.openai_provider import OpenAIProvider
            assert isinstance(provider, OpenAIProvider)
