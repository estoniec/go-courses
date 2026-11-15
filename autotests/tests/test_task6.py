"""Regression tests for task 6 acceptance checks, without a Docker daemon."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import advanced


class SearchTests(unittest.TestCase):
    def test_fixture_matches_kinosearch_four_field_contract(self):
        for movie in advanced.MOVIES:
            self.assertEqual(set(movie), {"id", "title", "year", "director"})

    def test_search_requires_all_four_fields_with_correct_types_and_values(self):
        for field in ("id", "title", "year", "director"):
            for value in (None, "incorrect", False):
                wrong = dict(advanced.MOVIES[0])
                wrong[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                    advanced.expect_search([wrong], [advanced.MOVIES[0]])

    def test_each_field_and_unknown_word(self):
        responses = [[advanced.MOVIES[index]] for index in (0, 0, 1, 1, 2)] + [[]]
        with mock.patch.object(advanced, "films", side_effect=responses) as films:
            advanced.search("http://catalog")
        self.assertEqual(films.call_count, 6)

    def test_missing_field_matches_and_false_positives_fail(self):
        for index in range(5):
            for wrong in ([], advanced.MOVIES, [advanced.MOVIES[0]] * 2):
                responses = [[advanced.MOVIES[i]] for i in (0, 0, 1, 1, 2)]
                responses[index] = wrong
                with self.subTest(field=index, wrong=wrong), mock.patch.object(advanced, "films", side_effect=responses):
                    with self.assertRaises(AssertionError):
                        advanced.search("http://catalog")

    def test_unknown_word_must_return_empty_array(self):
        responses = [[advanced.MOVIES[i]] for i in (0, 0, 1, 1, 2)] + [[advanced.MOVIES[0]]]
        with mock.patch.object(advanced, "films", side_effect=responses):
            with self.assertRaisesRegex(AssertionError, "Unknown term"):
                advanced.search("http://catalog")

    def test_blank_query_and_case_contract(self):
        with mock.patch.object(advanced, "http", return_value=(400, {}, "q is required")), \
                mock.patch.object(advanced, "films", return_value=[advanced.MOVIES[0]]):
            advanced.task6_search_contract("http://catalog")

    def test_blank_query_rejects_success_or_empty_error(self):
        for response in ((200, {}, "[]"), (400, {}, "")):
            with self.subTest(response=response), mock.patch.object(advanced, "http", return_value=response):
                with self.assertRaises(AssertionError):
                    advanced.task6_search_contract("http://catalog")


class CacheTests(unittest.TestCase):
    def check_cache(self, ttl=3600, cached=None, wrong_first=False):
        docker = mock.Mock(pg="postgres", redis="redis")
        # Unrelated expiring keys must not count as evidence of response caching.
        docker.redis_ttls.side_effect = [{"index": -1, "unrelated": 3600}, {"index": -1},
                                         {"index": -1, **({"response": ttl} if ttl is not None else {})}]
        first = [] if wrong_first else [advanced.MOVIES[0]]
        responses = [first, first, first if cached is None else cached]
        with mock.patch.object(advanced, "films", side_effect=responses), \
                mock.patch.object(advanced, "run") as run, \
                mock.patch.object(advanced, "eventually", side_effect=lambda fn, **kw: fn()):
            advanced.cache("http://catalog", docker)
        docker.exec.assert_any_call("redis", "redis-cli", "DEL", "unrelated")
        self.assertEqual(run.call_args_list, [mock.call(["docker", "stop", "postgres"], timeout=30),
                                              mock.call(["docker", "start", "postgres"], timeout=30)])

    def test_cached_response_with_one_hour_ttl(self):
        self.check_cache()

    def test_wrong_ttl_or_no_new_cache_fails(self):
        for ttl in (None, -1, 60, 7200):
            with self.subTest(ttl=ttl), self.assertRaises(AssertionError):
                self.check_cache(ttl=ttl)

    def test_empty_response_cannot_prove_cache(self):
        with self.assertRaises(AssertionError):
            self.check_cache(wrong_first=True)

    def test_database_is_restarted_after_cache_failure(self):
        docker = mock.Mock(pg="postgres", redis="redis")
        docker.redis_ttls.side_effect = [{"index": -1}, {"index": -1}, {"index": -1, "response": 3600}]
        with mock.patch.object(advanced, "films", side_effect=[[advanced.MOVIES[0]], [advanced.MOVIES[0]], OSError("DB offline")]), \
                mock.patch.object(advanced, "run") as run, \
                mock.patch.object(advanced, "eventually", side_effect=lambda fn, **kw: fn()):
            with self.assertRaises(OSError):
                advanced.cache("http://catalog", docker)
        self.assertEqual(run.call_args_list[-1], mock.call(["docker", "start", "postgres"], timeout=30))


class IndexTests(unittest.TestCase):
    def check_index(self, response, keys=None):
        apps = mock.Mock(base="http://catalog")
        docker = mock.Mock(redis="redis")
        states = [{"index": -1}]
        if response[0] == 200 and json.loads(response[2]):
            states.append({} if keys is None else keys)
        states.append({"rebuilt": -1} if keys is None else keys)
        docker.redis_ttls.side_effect = states
        with mock.patch.object(advanced, "http", return_value=response), \
                mock.patch.object(advanced, "films", return_value=[advanced.MOVIES[0]]):
            try:
                advanced.task6_index(apps, docker)
            finally:
                apps.stop.assert_called_once()
                apps.start.assert_called_once()
        docker.exec.assert_called_once_with("redis", "redis-cli", "FLUSHDB")

    def test_missing_index_can_return_empty_or_error(self):
        for response in ((200, {}, "[]"), (503, {}, "index unavailable")):
            with self.subTest(response=response):
                self.check_index(response)

    def test_sql_or_memory_fallback_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "fallback"):
            self.check_index((200, {}, json.dumps([advanced.MOVIES[0]])))

    def test_index_can_be_rebuilt_on_demand(self):
        self.check_index((200, {}, json.dumps([advanced.MOVIES[0]])), keys={"rebuilt": -1})

    def test_restart_must_rebuild_index(self):
        with self.assertRaisesRegex(AssertionError, "rebuild"):
            self.check_index((200, {}, "[]"), keys={})

    def test_index_must_exist_before_first_search(self):
        docker = mock.Mock()
        docker.redis_ttls.return_value = {}
        with self.assertRaisesRegex(AssertionError, "Startup"):
            advanced.task6_index(mock.Mock(), docker)

    def test_search_reads_current_postgres_data_and_restores_it(self):
        for title in (advanced.MOVIES[0]["title"], advanced.MOVIES[0]["title"] + " (changed in PostgreSQL)"):
            docker = mock.Mock()
            docker.movie_tables.return_value = ["movies"]
            docker.sql.return_value = "1"
            docker.redis_ttls.return_value = {"index": -1}
            with self.subTest(title=title), mock.patch.object(advanced, "films", return_value=[dict(advanced.MOVIES[0], title=title)]):
                if title == advanced.MOVIES[0]["title"]:
                    with self.assertRaisesRegex(AssertionError, "stale"):
                        advanced.task6_database_source(mock.Mock(), docker)
                else:
                    advanced.task6_database_source(mock.Mock(), docker)
            self.assertIn("SET title='Solaris'", docker.sql.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
