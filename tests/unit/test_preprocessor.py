from app.core.collector import RawEvidence
from app.core.preprocessor import EvidencePackage, LogPreprocessor


class TestLogPreprocessor:
    def setup_method(self):
        self.pre = LogPreprocessor()

    def test_filter_with_context_removes_noise_far_from_signal(self):
        logs = """2025-01-01T00:00:00Z INFO GET /health
2025-01-01T00:00:01Z INFO GET /ready
2025-01-01T00:00:10Z INFO GET /metrics
2025-01-01T00:00:02Z ERROR Database connection refused
2025-01-01T00:00:03Z INFO GET /metrics"""
        pre = LogPreprocessor(context_window=0)
        result = pre._filter_with_context(logs)
        assert "Database connection refused" in result
        assert "GET /health" not in result
        assert "GET /ready" not in result
        assert "GET /metrics" not in result

    def test_filter_with_context_keeps_signal_with_context_window(self):
        logs = """line 1 ok
line 2 normal
ERROR something broke
line 4 after
line 5 more"""
        pre = LogPreprocessor(context_window=1)
        result = pre._filter_with_context(logs)
        assert "line 2 normal" in result
        assert "ERROR something broke" in result
        assert "line 4 after" in result

    def test_filter_with_context_deduplicates_duplicate_lines(self):
        logs = """ERROR first failure
INFO normal
ERROR first failure
INFO normal
ERROR second failure"""
        result = self.pre._filter_with_context(logs)
        assert result.count("ERROR first failure") == 1

    def test_filter_with_context_limits_max_lines(self):
        pre = LogPreprocessor(max_log_lines=2, context_window=0)
        logs = "\n".join([f"ERROR line {i}" for i in range(20)])
        result = pre._filter_with_context(logs)
        assert len(result.splitlines()) <= 2

    def test_filter_with_context_handles_empty_input(self):
        result = self.pre._filter_with_context("")
        assert result == ""

    def test_is_noise_detects_health_probes(self):
        assert self.pre._is_noise("GET /health 200")
        assert self.pre._is_noise("GET /ready 200 OK")
        assert self.pre._is_noise("GET /metrics prometheus_data")
        assert self.pre._is_noise("")

    def test_is_noise_rejects_non_noise(self):
        assert not self.pre._is_noise("ERROR DB connection failed")

    def test_is_signal_detects_error_keywords(self):
        assert self.pre._is_signal("ERROR connection refused")
        assert self.pre._is_signal("FATAL: Out of memory")
        assert self.pre._is_signal("Traceback (most recent call last):")
        assert self.pre._is_signal("CrashLoopBackOff detected")
        assert self.pre._is_signal("missing required config")

    def test_is_signal_rejects_normal_lines(self):
        assert not self.pre._is_signal("GET /health 200")
        assert not self.pre._is_signal("INFO Server started")

    def test_extract_events_filters_warnings(self):
        events = """10s Normal Scheduled pod/demo-app Node assigned
10s Warning BackOff pod/demo-app Back-off restarting
20s Normal Pulled pod/demo-app Container image pulled"""
        result = self.pre._extract_events(events)
        assert "Warning BackOff" in result
        assert "Normal Scheduled" not in result

    def test_process_returns_evidence_package(self):
        raw = RawEvidence(
            namespace="demo",
            pod_name="demo-app-abc",
            current_logs="ERROR connection refused",
            previous_logs="WARN previous startup failed",
            pod_status="Status: CrashLoopBackOff\n" * 500,
            k8s_events="10s Warning BackOff pod/demo-app restarting",
            restart_count=3,
        )
        pkg = self.pre.process(raw)
        assert isinstance(pkg, EvidencePackage)
        assert pkg.namespace == "demo"
        assert pkg.pod_name == "demo-app-abc"
        assert "connection refused" in pkg.current_logs
        assert pkg.restart_count == 3
        assert isinstance(pkg.pod_status_summary, str)

    def test_process_truncates_long_pod_status(self):
        raw = RawEvidence(
            namespace="demo", pod_name="p",
            pod_status="Line\n" * 5000,
        )
        pkg = self.pre.process(raw)
        assert len(pkg.pod_status_summary) <= 2000

    def test_evidence_package_defaults(self):
        pkg = EvidencePackage(
            namespace="ns", pod_name="p",
            current_logs="", previous_logs="",
            pod_status_summary="", k8s_events_filtered="",
            restart_count=0,
        )
        assert pkg.restart_count == 0

    def test_identity_works_for_complex_realistic_logs(self):
        logs = """2025-06-01 10:00:00 INFO Server started on port 8000
2025-06-01 10:00:01 INFO Loading configuration
2025-06-01 10:00:02 ERROR [MainThread] RuntimeError: Missing config: DATABASE_URL
2025-06-01 10:00:02 ERROR [MainThread] Traceback (most recent call last):
2025-06-01 10:00:02 ERROR [MainThread]   File "app/main.py", line 12, in lifespan
2025-06-01 10:00:02 ERROR [MainThread]     raise RuntimeError("Missing config: DATABASE_URL")
2025-06-01 10:00:03 INFO Shutting down"""
        pre = LogPreprocessor(context_window=1)
        result = pre._filter_with_context(logs)
        assert "RuntimeError" in result
        assert "Traceback" in result
        assert "DATABASE_URL" in result
        assert "Loading configuration" in result
        assert "Shutting down" in result
