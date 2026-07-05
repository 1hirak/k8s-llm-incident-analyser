import os

import yaml

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "k8s", "base")
SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "k8s", "scenarios")


def _load_yaml(path):
    with open(path) as f:
        return list(yaml.safe_load_all(f))


class TestK8sBaseManifests:
    def test_namespace_yaml_is_valid(self):
        docs = _load_yaml(os.path.join(BASE_DIR, "namespace.yaml"))
        assert len(docs) >= 1
        assert docs[0]["kind"] == "Namespace"
        assert docs[0]["metadata"]["name"] == "demo"

    def test_configmap_yaml_is_valid(self):
        docs = _load_yaml(os.path.join(BASE_DIR, "configmap.yaml"))
        assert docs[0]["kind"] == "ConfigMap"
        assert "APP_ENV" in docs[0]["data"]

    def test_deployment_yaml_is_valid(self):
        docs = _load_yaml(os.path.join(BASE_DIR, "deployment.yaml"))
        assert docs[0]["kind"] == "Deployment"
        assert docs[0]["metadata"]["name"] == "demo-app"
        containers = docs[0]["spec"]["template"]["spec"]["containers"]
        assert len(containers) == 1
        assert containers[0]["name"] == "demo-app"

    def test_deployment_has_readiness_probe(self):
        docs = _load_yaml(os.path.join(BASE_DIR, "deployment.yaml"))
        probe = docs[0]["spec"]["template"]["spec"]["containers"][0].get("readinessProbe")
        assert probe is not None
        assert probe["httpGet"]["path"] == "/ready"

    def test_deployment_has_liveness_probe(self):
        docs = _load_yaml(os.path.join(BASE_DIR, "deployment.yaml"))
        probe = docs[0]["spec"]["template"]["spec"]["containers"][0].get("livenessProbe")
        assert probe is not None
        assert probe["httpGet"]["path"] == "/health"

    def test_service_yaml_is_valid(self):
        docs = _load_yaml(os.path.join(BASE_DIR, "service.yaml"))
        assert docs[0]["kind"] == "Service"
        assert docs[0]["spec"]["ports"][0]["targetPort"] == 8000


class TestK8sScenarioFaults:
    def test_all_scenario_dirs_exist(self):
        expected = [
            "01-missing-env", "02-db-unavailable", "03-crashloop",
            "04-imagepull", "05-oom", "06-readiness", "07-liveness",
            "08-bad-configmap", "09-app-exception", "10-wrong-port",
        ]
        for s in expected:
            path = os.path.join(SCENARIOS_DIR, s, "fault.yaml")
            assert os.path.exists(path), f"Missing: {path}"

    def test_all_scenario_yamls_are_valid(self):
        for d in sorted(os.listdir(SCENARIOS_DIR)):
            path = os.path.join(SCENARIOS_DIR, d, "fault.yaml")
            if os.path.exists(path):
                docs = _load_yaml(path)
                assert len(docs) >= 1

    def test_missing_env_sets_empty_url(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "01-missing-env", "fault.yaml"))
        env = docs[0]["spec"]["template"]["spec"]["containers"][0]["env"]
        assert env[0]["name"] == "DATABASE_URL"
        assert env[0]["value"] == ""

    def test_db_unavailable_sets_unreachable_url(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "02-db-unavailable", "fault.yaml"))
        env = docs[0]["spec"]["template"]["spec"]["containers"][0]["env"]
        assert "unavailable" in env[0]["value"]

    def test_crashloop_uses_nonexistent_command(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "03-crashloop", "fault.yaml"))
        cmd = docs[0]["spec"]["template"]["spec"]["containers"][0].get("command")
        assert cmd == ["/bin/nonexistent"]

    def test_imagepull_uses_nonexistent_tag(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "04-imagepull", "fault.yaml"))
        image = docs[0]["spec"]["template"]["spec"]["containers"][0].get("image")
        assert "nonexistent" in image

    def test_oom_lowers_memory_limit(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "05-oom", "fault.yaml"))
        limits = docs[0]["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]
        assert limits["memory"] == "32Mi"

    def test_readiness_fault_uses_bad_path(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "06-readiness", "fault.yaml"))
        probe = docs[0]["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]
        assert "does-not-exist" in probe["httpGet"]["path"]

    def test_liveness_fault_uses_slow_endpoint(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "07-liveness", "fault.yaml"))
        probe = docs[0]["spec"]["template"]["spec"]["containers"][0]["livenessProbe"]
        assert "fault/slow" in probe["httpGet"]["path"]

    def test_bad_configmap_has_invalid_loglevel(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "08-bad-configmap", "fault.yaml"))
        assert docs[0]["data"]["LOG_LEVEL"] == "INVALID"

    def test_wrong_port_uses_9999(self):
        docs = _load_yaml(os.path.join(SCENARIOS_DIR, "10-wrong-port", "fault.yaml"))
        assert docs[0]["spec"]["ports"][0]["targetPort"] == 9999
