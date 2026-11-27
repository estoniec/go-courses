"""Basic regression checks for homework 8–9; no student implementation fixtures."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import advanced
import task89


class KafkaFlowTests(unittest.TestCase):
    def test_messages_in_both_topics(self):
        docker = mock.Mock()
        docker.rpk.side_effect = ['{"last_id":0}', '{"id":1,"title":"Solaris","year":1972,"director":"Andrei Tarkovsky"}']
        task89.kafka_flow(docker)
        self.assertEqual(docker.rpk.call_args_list, [
            mock.call("topic", "consume", topic, "-n", "1", "-o", "start", "-f", "%v")
            for topic in ("movie_download_tasks", "movie_downloaded")])

    def test_missing_message_fails(self):
        for responses in (("",), ('{"last_id":0}', " ")):
            docker = mock.Mock()
            docker.rpk.side_effect = responses
            with self.subTest(responses=responses), self.assertRaisesRegex(AssertionError, "No message"):
                task89.kafka_flow(docker)


class BasicCacheTests(unittest.TestCase):
    def test_repeated_search_and_hourly_cache(self):
        docker = mock.Mock()
        docker.redis_ttls.return_value = {"index:solaris": -1, "cache": 3600}
        with mock.patch.object(advanced, "films", return_value=[advanced.MOVIES[0]]) as films:
            task89.basic_cache("http://catalog", docker)
        self.assertEqual(films.call_count, 2)
        docker.exec.assert_not_called()

    def test_missing_response_cache_fails(self):
        docker = mock.Mock()
        docker.redis_ttls.return_value = {"index:solaris": -1}
        with mock.patch.object(advanced, "films", return_value=[advanced.MOVIES[0]]), self.assertRaisesRegex(AssertionError, "cache"):
            task89.basic_cache("http://catalog", docker)


class HTMLSearchTests(unittest.TestCase):
    form = '<html><form method="get" action="/results"><input name="q"></form></html>'

    def test_title_and_director_use_existing_form_action(self):
        responses = [(200, {"Content-Type": "text/html"}, self.form)] + [
            (200, {"Content-Type": "text/html; charset=utf-8"}, "<html>Solaris</html>")] * 2
        with mock.patch.object(advanced, "http", side_effect=responses) as http:
            task89.html_search("http://catalog")
        self.assertEqual(http.call_args_list, [mock.call("http://catalog/"),
                                              mock.call("http://catalog/results?q=Solaris"),
                                              mock.call("http://catalog/results?q=Tarkovsky")])

    def test_result_must_show_movie_for_director_query(self):
        responses = [(200, {"Content-Type": "text/html"}, self.form),
                     (200, {"Content-Type": "text/html"}, "Solaris"),
                     (200, {"Content-Type": "text/html"}, "Search: Tarkovsky")]
        with mock.patch.object(advanced, "http", side_effect=responses), self.assertRaisesRegex(AssertionError, "Tarkovsky"):
            task89.html_search("http://catalog")

    def test_json_response_is_not_an_html_page(self):
        responses = [(200, {"Content-Type": "text/html"}, self.form),
                     (200, {"Content-Type": "application/json"}, '[{"title":"Solaris"}]')]
        with mock.patch.object(advanced, "http", side_effect=responses), self.assertRaisesRegex(AssertionError, "HTML search"):
            task89.html_search("http://catalog")


class CoverageTests(unittest.TestCase):
    def test_coverage_threshold_is_strictly_over_seventy(self):
        for covered in (70, 71):
            with self.subTest(covered=covered), tempfile.TemporaryDirectory() as tmp:
                module = Path(tmp)
                profile = module / "course-student-coverage.out"
                def write_profile(*args, **kwargs):
                    profile.write_text("mode: set\nstudent/value.go:1.1,2.1 {} 1\nstudent/value.go:3.1,4.1 {} 0\n".format(covered, 100 - covered))
                with mock.patch.object(advanced, "run", side_effect=write_profile) as run:
                    if covered == 70:
                        with self.assertRaisesRegex(AssertionError, ">70%"):
                            advanced.student_tests([module], {}, coverage=True)
                    else:
                        self.assertIn("71.00%", advanced.student_tests([module], {}, coverage=True))
                self.assertIn("-coverpkg=./...", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
