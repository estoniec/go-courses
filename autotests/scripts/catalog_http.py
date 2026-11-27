"""Basic HTTP acceptance scenario for the catalog service."""
import json


def catalog_api(base):
    from advanced import MOVIES, expect_catalog, expect_search, http, require, search

    expect_catalog(base)
    status, _, body = http(base + "/last-movie")
    require(status == 200, "last-movie must return HTTP 200")
    last = json.loads(body)
    require(isinstance(last, dict), "last-movie must return a JSON object")
    expect_search([last], [MOVIES[-1]])
    search(base)
