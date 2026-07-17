import logging
import subprocess
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RawEvidence:
    namespace: str
    pod_name: str
    current_logs: str = ""
    previous_logs: str = ""
    pod_status: str = ""
    k8s_events: str = ""
    restart_count: int = 0
    container_states: dict = field(default_factory=dict)


class KubernetesCollector:
    def __init__(self, kubectl_path: str = "kubectl", timeout: int = 30):
        self.kubectl = kubectl_path
        self.timeout = timeout

    def _run(self, *args) -> str:
        cmd = [self.kubectl, *args]
        logger.debug("Running: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, check=False,
            )
            if result.returncode != 0:
                logger.warning(
                    "kubectl returned %d: %s",
                    result.returncode, result.stderr[:200],
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error("kubectl timed out: %s", " ".join(cmd))
            return ""

    def get_pod_logs(
        self, namespace: str, pod: str, previous: bool = False, tail: int = 500
    ) -> str:
        args = [
            "logs", "-n", namespace, pod,
            f"--tail={tail}", "--timestamps=true",
        ]
        if previous:
            args.append("--previous")
        return self._run(*args)

    def get_pod_description(self, namespace: str, pod: str) -> str:
        return self._run("describe", "pod", "-n", namespace, pod)

    def get_events(self, namespace: str, field_selector: str = "") -> str:
        args = [
            "get", "events", "-n", namespace,
            "--sort-by=.metadata.creationTimestamp",
        ]
        if field_selector:
            args.append(f"--field-selector={field_selector}")
        return self._run(*args)

    def get_restart_count(self, namespace: str, pod: str) -> int:
        raw = self._run(
            "get", "pod", "-n", namespace, pod,
            "-o", "jsonpath={.status.containerStatuses[0].restartCount}",
        )
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    def collect(self, namespace: str, pod_name: str) -> RawEvidence:
        logger.info("Collecting evidence for %s/%s", namespace, pod_name)
        ev = RawEvidence(namespace=namespace, pod_name=pod_name)
        ev.current_logs = self.get_pod_logs(namespace, pod_name, previous=False)
        ev.previous_logs = self.get_pod_logs(namespace, pod_name, previous=True)
        ev.pod_status = self.get_pod_description(namespace, pod_name)
        ev.k8s_events = self.get_events(namespace)
        ev.restart_count = self.get_restart_count(namespace, pod_name)
        return ev
