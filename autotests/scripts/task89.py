"""Small happy-path checks for the HTML and Kafka homework steps."""
import urllib.parse


def kafka_flow(docker):
    from advanced import require

    for topic in ("movie_download_tasks", "movie_downloaded"):
        payload = docker.rpk("topic", "consume", topic, "-n", "1", "-o", "start", "-f", "%v")
        require(payload.strip(), "No message in Kafka topic " + topic)


def basic_cache(base, docker):
    from advanced import MOVIES, expect_search, films, require

    first = films(base, "/search?q=Solaris")
    expect_search(first, [MOVIES[0]])
    second = films(base, "/search?q=Solaris")
    require(first == second, "Repeated search returned different results")
    ttls = docker.redis_ttls()
    require(any(3500 <= ttl <= 3600 for ttl in ttls.values()), "No Redis response cache entry with a one-hour TTL")


def html_search(base):
    from advanced import FormParser, http, require

    status, headers, body = http(base + "/")
    require(status == 200 and "text/html" in headers.get("Content-Type", ""),
            "GET / must serve the HTML search form")
    parser = FormParser()
    parser.feed(body)
    require(parser.action is not None and parser.query, "Expected a form with input name=q")
    target = urllib.parse.urlsplit(urllib.parse.urljoin(base + "/", parser.action))
    origin = urllib.parse.urlsplit(base)
    require((target.scheme, target.netloc) == (origin.scheme, origin.netloc), "Form must submit to this service")
    for query in ("Solaris", "Tarkovsky"):
        parameters = urllib.parse.parse_qsl(target.query, keep_blank_values=True)
        parameters = [(key, value) for key, value in parameters if key != "q"] + [("q", query)]
        url = urllib.parse.urlunsplit(target._replace(query=urllib.parse.urlencode(parameters), fragment=""))
        status, headers, body = http(url)
        require(status == 200 and "text/html" in headers.get("Content-Type", "") and "Solaris" in body,
                "HTML search by title/director must show the matching movie: " + query)
