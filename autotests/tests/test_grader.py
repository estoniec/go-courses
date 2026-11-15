"""Grader reports and rejection checks without complete student solutions."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import contextlib
import io
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check

ROOT = Path(__file__).resolve().parent.parent


class GraderTests(unittest.TestCase):
    def check(self, task, solution, expected):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            result = subprocess.run(["python3", str(ROOT / "scripts/check.py"), task,
                                     str(solution), "--report", str(report)],
                                    capture_output=True, text=True, timeout=240)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            data = json.loads(report.read_text())
            self.assertEqual(data["status"], "pass" if expected == 0 else "fail")
            return data

    def test_task1_rejects_missing_required_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / "go.mod").write_text("module student\n\ngo 1.26.4\n")
            (source / "main.go").write_text("package main\nfunc main() {}\n")
            self.check("task1", source, 1)

    def test_report_reflects_check_result_for_each_basic_suite(self):
        for task in ("task1", "task2", "task3"):
            for action in ("pass", "fail", "skip"):
                with self.subTest(task=task, action=action), tempfile.TemporaryDirectory() as tmp:
                    source = Path(tmp)
                    (source / "go.mod").write_text("module student\n")
                    report = source / "report.json"
                    event = json.dumps({"Action": action, "Test": "TestCourseExample"})
                    with mock.patch.object(sys, "argv", ["check.py", task, str(source), "--report", str(report)]), \
                            mock.patch.object(check, "evaluate", return_value=(0, event)), \
                            mock.patch.object(check, "revision", return_value=None), \
                            contextlib.redirect_stdout(io.StringIO()):
                        code = check.main()
                    expected = "pass" if action == "pass" else "fail"
                    self.assertEqual(code, 0 if expected == "pass" else 1)
                    self.assertEqual(json.loads(report.read_text())["status"], expected)

    def test_parse_events_retains_test_status_and_diagnostic(self):
        output = "build diagnostic\n" + "\n".join(json.dumps(event) for event in (
            {"Action": "output", "Test": "TestCourseExample", "Output": "wrong result\n"},
            {"Action": "fail", "Test": "TestCourseExample", "Elapsed": 0.1}))
        tests, log = check.parse_events(output)
        self.assertEqual(tests, [{"name": "TestCourseExample", "status": "fail", "elapsed_seconds": 0.1}])
        self.assertIn("wrong result", log)
        self.assertIn("build diagnostic", log)

    def test_unsupported_task_rejected(self):
        result = subprocess.run(["python3", str(ROOT / "scripts/check.py"), "task11", "."],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_missing_module_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.check("task1", Path(tmp), 1)


if __name__ == "__main__":
    unittest.main()
