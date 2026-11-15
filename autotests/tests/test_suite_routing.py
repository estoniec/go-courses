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
import task9
import task78


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
                         "student_tests", "web_ui", "kubernetes", "observability_config", "metrics"):
                mocks[name] = patches.enter_context(mock.patch.object(advanced, name))
            patches.enter_context(mock.patch.object(advanced, "list_modules", return_value=[source]))
            kafka = patches.enter_context(mock.patch.object(task78, "kafka_flow"))
            cache = patches.enter_context(mock.patch.object(task78, "basic_cache"))
            api = patches.enter_context(mock.patch.object(task9, "compose_api"))
            docker = mocks["Docker"].return_value
            docker.env = {}
            docker.stored_movies.return_value = 3
            mocks["Apps"].return_value.base = "http://catalog"
            mocks["Compose"].return_value.base = "http://catalog"
            code, output = advanced.evaluate("task" + str(number), source)
            self.assertEqual(code, 0, output)
            events = [json.loads(line) for line in output.splitlines()]
            names = {event["Test"] for event in events}
            if number in (7, 8):
                self.assertIn("TestCourseKafkaFlow", names)
                self.assertIn("TestCourseRedisCache", names)
                self.assertIn("TestCourseCatalogAPI", names)
                self.assertNotIn("TestCourseAPIReadsDatabase", names)
                kafka.assert_called_once_with(docker)
                cache.assert_called_once_with("http://catalog", docker)
                api.assert_called_once_with("http://catalog")
                mocks["cache"].assert_not_called()
                mocks["task6_index"].assert_not_called()
                docker.exec.assert_not_called()
                if number == 8:
                    mocks["web_ui"].assert_called_once_with("http://catalog")
                else:
                    mocks["web_ui"].assert_not_called()
                self.assertEqual(mocks["student_tests"].call_args.kwargs["coverage"], number == 8)
            else:
                self.assertIn("TestCourseComposeAPI", names)
                api.assert_called_once_with("http://catalog")
                if number == 9:
                    mocks["kubernetes"].assert_called_once()
                    mocks["metrics"].assert_not_called()
                else:
                    mocks["observability_config"].assert_called_once()
                    mocks["metrics"].assert_called_once()

    def test_task7_basic_suite(self):
        self.evaluate(7)

    def test_task8_html_and_student_coverage(self):
        self.evaluate(8)

    def test_task9_compose_api_and_manifests(self):
        self.evaluate(9)

    def test_task10_compose_api_and_observability(self):
        self.evaluate(10)


if __name__ == "__main__":
    unittest.main()
