from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

from app.core.collector import KubernetesCollector, RawEvidence

SAMPLE_LOG = "2025-05-01T10:00:00Z ERROR Missing DATABASE_URL"
SAMPLE_DESCRIBE = "Pod Status: CrashLoopBackOff\nContainer: demo-app"
SAMPLE_EVENTS = "10s Warning BackOff pod/demo-app Back-off restarting"
SAMPLE_JSONPATH = "3"


def make_mock_result(stdout="", stderr="", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


class TestKubernetesCollector:
    def setup_method(self):
        self.collector = KubernetesCollector()

    def test_get_pod_logs_calls_kubectl_correctly(self):
        with patch("subprocess.run", return_value=make_mock_result(SAMPLE_LOG)) as mock_run:
            logs = self.collector.get_pod_logs("demo", "demo-app-xxx")
            assert logs == SAMPLE_LOG
            cmd = mock_run.call_args[0][0]
            assert "logs" in cmd
            assert "-n" in cmd
            assert "demo" in cmd

    def test_get_pod_logs_uses_tail_flag(self):
        with patch("subprocess.run", return_value=make_mock_result(SAMPLE_LOG)) as mock_run:
            self.collector.get_pod_logs("demo", "pod-xyz", tail=200)
            cmd = mock_run.call_args[0][0]
            assert "--tail=200" in cmd
            assert "--timestamps=true" in cmd

    def test_get_pod_logs_previous_includes_flag(self):
        with patch("subprocess.run", return_value=make_mock_result("prev log")) as mock_run:
            self.collector.get_pod_logs("demo", "pod-xyz", previous=True)
            assert "--previous" in mock_run.call_args[0][0]

    def test_get_pod_logs_returns_empty_on_timeout(self):
        with patch("subprocess.run", side_effect=TimeoutExpired("kubectl", 30)):
            logs = self.collector.get_pod_logs("demo", "pod-xyz")
            assert logs == ""

    def test_get_pod_logs_kubectl_error_returns_stdout(self):
        with patch("subprocess.run", return_value=make_mock_result(
            stdout="", stderr="error: pod not found", returncode=1
        )):
            logs = self.collector.get_pod_logs("demo", "nonexistent")
            assert logs == ""

    def test_get_pod_description_calls_describe(self):
        with patch("subprocess.run", return_value=make_mock_result(SAMPLE_DESCRIBE)) as mock_run:
            desc = self.collector.get_pod_description("demo", "pod-abc")
            assert "CrashLoopBackOff" in desc
            cmd = mock_run.call_args[0][0]
            assert "describe" in cmd
            assert "pod" in cmd

    def test_get_events_includes_namespace(self):
        with patch("subprocess.run", return_value=make_mock_result(SAMPLE_EVENTS)) as mock_run:
            events = self.collector.get_events("demo")
            assert "BackOff" in events
            cmd = mock_run.call_args[0][0]
            assert "demo" in cmd

    def test_get_events_with_field_selector(self):
        with patch("subprocess.run", return_value=make_mock_result(SAMPLE_EVENTS)) as mock_run:
            self.collector.get_events("demo", field_selector="reason=BackOff")
            args = mock_run.call_args[0][0]
            assert "--field-selector=reason=BackOff" in args

    def test_get_restart_count_parses_int(self):
        with patch("subprocess.run", return_value=make_mock_result(SAMPLE_JSONPATH)):
            count = self.collector.get_restart_count("demo", "pod-abc")
            assert count == 3

    def test_get_restart_count_returns_zero_on_non_int(self):
        with patch("subprocess.run", return_value=make_mock_result("not_a_number")):
            count = self.collector.get_restart_count("demo", "pod-abc")
            assert count == 0

    def test_collect_returns_raw_evidence(self):
        with patch("subprocess.run", return_value=make_mock_result("some log")):
            ev = self.collector.collect("demo", "demo-app-abc")
            assert isinstance(ev, RawEvidence)
            assert ev.namespace == "demo"
            assert ev.pod_name == "demo-app-abc"
            assert ev.current_logs == "some log"

    def test_collect_calls_all_methods(self):
        returns = [
            make_mock_result("current log"),
            make_mock_result("prev log"),
            make_mock_result("pod status info"),
            make_mock_result("events info"),
            make_mock_result("2"),
            make_mock_result(""),
        ]
        with patch("subprocess.run", side_effect=returns) as mock_run:
            ev = self.collector.collect("demo", "pod-abc")
            assert ev.current_logs == "current log"
            assert ev.previous_logs == "prev log"
            assert ev.pod_status == "pod status info"
            assert ev.k8s_events == "events info"
            assert ev.restart_count == 2
            assert mock_run.call_count == 5

    def test_raw_evidence_defaults(self):
        ev = RawEvidence(namespace="ns", pod_name="p")
        assert ev.current_logs == ""
        assert ev.previous_logs == ""
        assert ev.restart_count == 0
        assert ev.container_states == {}

    def test_timeout_in_subprocess_returns_empty(self):
        with patch("subprocess.run", side_effect=TimeoutExpired("kubectl", 30)):
            assert self.collector.get_pod_logs("demo", "pod-x") == ""
            assert self.collector.get_pod_description("demo", "pod-x") == ""
            assert self.collector.get_events("demo") == ""
