"""Small task 10 checks, without Docker or a complete student solution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import advanced
import task10


class Task10Tests(unittest.TestCase):
    def test_metrics_and_request_log(self):
        body = '# TYPE http_requests_total counter\nhttp_requests_total{method="GET"} 3\n'
        logs = 'container starting\n' + json.dumps({"level": "INFO", "msg": "request", "request_id": "req-1"})
        with mock.patch.object(advanced, "http", return_value=(200, {}, body)) as http:
            task10.metrics("http://catalog", logs)
        http.assert_called_once_with("http://catalog/metrics")

    def test_standard_untyped_metric_and_nested_correlation_id(self):
        logs = json.dumps({"level": "INFO", "msg": "request", "request": {"correlation_id": "req-2"}})
        with mock.patch.object(advanced, "http", return_value=(200, {}, "application_requests 2\n")):
            task10.metrics("http://catalog", logs)

    def test_success_page_is_not_metrics(self):
        with mock.patch.object(advanced, "http", return_value=(200, {}, "<html>OK</html>")):
            with self.assertRaisesRegex(AssertionError, "Prometheus"):
                task10.metrics("http://catalog", "")

    def test_empty_request_id_is_not_request_context(self):
        logs = json.dumps({"level": "INFO", "msg": "request", "request_id": ""})
        with mock.patch.object(advanced, "http", return_value=(200, {}, "requests_total 1\n")):
            with self.assertRaisesRegex(AssertionError, "nonempty"):
                task10.metrics("http://catalog", logs)

    def test_six_dashboards_and_provisioning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for title in ("Search", "Downloads", "Catalog", "API", "Infrastructure", "Services"):
                (root / (title + ".json")).write_text(json.dumps({"title": title, "panels": [{"type": "timeseries"}]}))
            # JSON is valid YAML, and keeps these small inputs easy to inspect.
            (root / "dashboards.yml").write_text(json.dumps({"providers": [{"name": "course"}]}))
            (root / "datasources.yml").write_text(json.dumps({"datasources": [{"name": "Prometheus"}]}))
            config = {"services": {name: {"image": name} for name in ("prometheus", "grafana", "loki", "alloy")}}
            advanced.observability_config(root, config)


if __name__ == "__main__":
    unittest.main()
