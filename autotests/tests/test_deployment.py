"""Small default-scenario checks; no student implementation or cluster required."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import advanced
from catalog_http import catalog_api


class ComposeAPITests(unittest.TestCase):
    def response(self, url):
        parsed = urllib.parse.urlsplit(url)
        if parsed.path == "/load-movies":
            data = advanced.MOVIES
        elif parsed.path == "/last-movie":
            data = advanced.MOVIES[-1]
        else:
            query = urllib.parse.parse_qs(parsed.query)["q"][0].lower()
            data = [movie for movie in advanced.MOVIES
                    if query in (movie["title"] + " " + movie["director"]).lower().split()]
        return 200, {}, json.dumps(data)

    def test_default_api_with_four_field_movies(self):
        self.assertTrue(all(set(movie) == {"id", "title", "year", "director"} for movie in advanced.MOVIES))
        with mock.patch.object(advanced, "http", side_effect=self.response) as http:
            catalog_api("http://catalog")
        self.assertTrue(any(call.args[0].endswith("/last-movie") for call in http.call_args_list))

    def test_last_movie_must_have_the_current_four_fields(self):
        for last in (advanced.MOVIES[0], {"id": 3, "title": advanced.MOVIES[-1]["title"]}):
            def response(url):
                if url.endswith("/last-movie"):
                    return 200, {}, json.dumps(last)
                return self.response(url)
            with self.subTest(last=last), mock.patch.object(advanced, "http", side_effect=response):
                with self.assertRaises(AssertionError):
                    catalog_api("http://catalog")

    def test_last_movie_http_failure_is_reported(self):
        with mock.patch.object(advanced, "expect_catalog"), \
                mock.patch.object(advanced, "http", return_value=(500, {}, "database error")):
            with self.assertRaisesRegex(AssertionError, "HTTP 200"):
                catalog_api("http://catalog")

    def compose(self, services, with_kafka):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "compose.yaml").write_text("services: {}\n")
            with mock.patch.object(advanced, "run", side_effect=["Docker", json.dumps({"services": services})]):
                compose = advanced.Compose(source, mock.Mock(port=12345), with_kafka=with_kafka)
            return json.loads(compose.override.read_text())["services"]

    def services(self):
        return {"catalog-service": {"build": ".", "ports": [{"target": 8080}]},
                "postgres": {"image": "postgres:16-alpine"},
                "redis": {"image": "redis:7-alpine"}}

    def test_task7_compose_passes_fixture_url_to_catalog(self):
        override = self.compose(self.services(), with_kafka=False)
        self.assertEqual(set(override), {"catalog-service"})
        self.assertEqual(override["catalog-service"]["environment"]["MOVIE_BASE_URL"],
                         "http://host.docker.internal:12345")

    def test_task10_compose_passes_fixture_url_to_downloader(self):
        services = dict(self.services(), downloader={"build": "."}, broker={"image": "redpandadata/redpanda"})
        override = self.compose(services, with_kafka=True)
        self.assertEqual(set(override), {"downloader"})
        self.assertEqual(override["downloader"]["environment"]["MOVIE_BASE_URL"],
                         "http://host.docker.internal:12345")

    def test_task10_still_requires_broker(self):
        services = dict(self.services(), downloader={"build": "."})
        with self.assertRaisesRegex(AssertionError, "Compose lacks Kafka"):
            self.compose(services, with_kafka=True)


class KubernetesBasicTests(unittest.TestCase):
    def manifests(self):
        labels = {"app": "catalog"}
        return [
            {"kind": "ConfigMap"},
            {"kind": "Secret"},
            {"kind": "Deployment", "metadata": {"name": "catalog"}, "spec": {
                "replicas": 2,
                "selector": {"matchLabels": labels},
                "template": {"metadata": {"labels": labels}, "spec": {"containers": [{
                    "name": "catalog", "readinessProbe": {"tcpSocket": {"port": 8080}},
                    "livenessProbe": {"tcpSocket": {"port": 8080}}, "resources": {
                        "requests": {"cpu": "100m", "memory": "64Mi"},
                        "limits": {"cpu": "1", "memory": "128Mi"}}}]}}}},
            {"kind": "Service", "spec": {"selector": labels}},
        ]

    def check(self, documents):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "k8s.yaml").write_text(json.dumps({"kind": "List", "items": documents}))
            advanced.kubernetes(source)

    def test_accepts_only_catalog_app(self):
        self.check(self.manifests())

    def test_service_must_select_the_application_pods(self):
        documents = self.manifests()
        documents[3]["spec"]["selector"] = {"app": "different"}
        with self.assertRaisesRegex(AssertionError, "Service selecting catalog"):
            self.check(documents)

    def test_catalog_deployment_is_required(self):
        documents = self.manifests()
        documents[2]["metadata"]["name"] = "postgres"
        with self.assertRaisesRegex(AssertionError, "Deployment for catalog"):
            self.check(documents)


if __name__ == "__main__":
    unittest.main()
