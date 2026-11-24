"""Verify basic suite wiring without running a student solution or containers."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import advanced
import check
import catalog_http
import task89


class SuiteRoutingTests(unittest.TestCase):
    def evaluate(self, number):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as patches:
            source = Path(tmp)

            def copy_solution(_, destination):
                destination.mkdir()
                (destination / "schema.sql").write_text("CREATE TABLE movies (title text);")

            patches.enter_context(mock.patch.object(check, "copy_solution", side_effect=copy_solution))
            mocks = {}
            for name in ("Docker", "Upstream", "Apps", "Compose", "run", "search", "cache", "task6_index",
                         "student_tests", "web_ui", "kubernetes", "observability_config", "metrics", "http", "expect_catalog"):
                mocks[name] = patches.enter_context(mock.patch.object(advanced, name))
            patches.enter_context(mock.patch.object(advanced, "list_modules", return_value=[source]))
            kafka = patches.enter_context(mock.patch.object(task89, "kafka_flow"))
            cache = patches.enter_context(mock.patch.object(task89, "basic_cache"))
            api = patches.enter_context(mock.patch.object(catalog_http, "catalog_api"))
            docker = mocks["Docker"].return_value
            mocks["http"].return_value = (200, {}, '{"id": 3}')
            docker.env = {}
            docker.stored_movies.return_value = 3
            mocks["Apps"].return_value.base = "http://catalog"
            mocks["Compose"].return_value.base = "http://catalog"
            code, output = advanced.evaluate("task" + str(number), source)
            self.assertEqual(code, 0, output)
            events = [json.loads(line) for line in output.splitlines()]
            names = {event["Test"] for event in events}
            api.assert_called_once_with("http://catalog")
            self.assertEqual("TestCourseHTMLSearch" in names, number in (8, 9, 10))
            self.assertEqual("TestCourseStudentCoverage" in names, number == 8)
            self.assertEqual(mocks["student_tests"].call_args.kwargs.get("coverage", False), number == 8)

            if number in (8, 9):
                self.assertIn("TestCourseCatalogAPI", names)
                self.assertIn("TestCourseRedisCache", names)
                cache.assert_called_once_with("http://catalog", docker)
                docker.services.assert_called_once_with(number)
                self.assertEqual(mocks["Apps"].call_args.args[2], number)
                mocks["Compose"].assert_not_called()
            else:
                self.assertIn("TestCourseComposeAPI", names)
                self.assertEqual(mocks["Compose"].call_args.kwargs["with_kafka"], number == 10)
                mocks["Docker"].assert_not_called()
                mocks["Apps"].assert_not_called()
                cache.assert_not_called()

            self.assertEqual("TestCourseAPIReadsDatabase" in names, number == 8)
            self.assertEqual("TestCourseKafkaFlow" in names, number == 9)
            if number == 9:
                kafka.assert_called_once_with(docker)
            else:
                kafka.assert_not_called()

            self.assertEqual("TestCourseKubernetesManifests" in names, number == 7)
            self.assertEqual("TestCourseObservabilityConfig" in names, number == 10)
            self.assertEqual("TestCourseMetricsAndLogs" in names, number == 10)

    def test_task7_compose_api_and_manifests(self):
        self.evaluate(7)

    def test_task8_one_service_html_and_coverage(self):
        self.evaluate(8)

    def test_task9_kafka_html_and_student_tests(self):
        self.evaluate(9)

    def test_task10_compose_api_and_observability(self):
        self.evaluate(10)


class NativeStartupTests(unittest.TestCase):
    def test_only_task9_starts_a_broker_for_native_apps(self):
        for number in (8, 9):
            with self.subTest(number=number), mock.patch.object(advanced, "run"), \
                    mock.patch.object(advanced.Docker, "start", return_value=("dependency", 12345)) as start, \
                    mock.patch.object(advanced.Docker, "exec", return_value="PONG"), \
                    mock.patch.object(advanced.Docker, "rpk") as rpk, \
                    mock.patch.object(advanced, "free_port", return_value=12345):
                docker = advanced.Docker()
                docker.services(number)
                self.assertEqual(start.call_count, 2 if number == 8 else 3)
                self.assertEqual("KAFKA_BROKERS" in docker.env, number == 9)
                if number == 8:
                    rpk.assert_not_called()
                else:
                    rpk.assert_any_call("topic", "create", "movie_download_tasks")
                    rpk.assert_any_call("topic", "create", "movie_downloaded")

    def test_task8_accepts_one_server_and_task9_requires_both_roles(self):
        source = Path("/solution")
        catalog = {"Name": "main", "GoFiles": ["main.go"], "Dir": str(source / "cmd/catalog-service")}
        downloader = {"Name": "main", "GoFiles": ["main.go"], "Dir": str(source / "cmd/downloader-service")}
        with mock.patch.object(advanced, "run"), mock.patch.object(advanced, "packages") as packages:
            packages.return_value = [catalog]
            self.assertIsNone(advanced.Apps(source, [source], 8, {}, None).downloader)
            with self.assertRaisesRegex(AssertionError, "downloader main package"):
                advanced.Apps(source, [source], 9, {}, None)
            packages.return_value = [catalog, downloader]
            apps = advanced.Apps(source, [source], 9, {}, None)
            self.assertEqual(apps.catalog[1], Path(catalog["Dir"]))
            self.assertEqual(apps.downloader[1], Path(downloader["Dir"]))


if __name__ == "__main__":
    unittest.main()
