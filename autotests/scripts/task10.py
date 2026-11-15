"""Basic observability acceptance check; dashboard semantics stay on review."""
import json
import re


def metrics(base, logs):
    from advanced import http, require

    status, _, body = http(base + "/metrics")
    require(status == 200, "GET /metrics must return 200")
    # TYPE comments are optional in Prometheus text exposition. Libraries may
    # also choose their own metric names, so do not require course-specific names.
    samples = re.findall(
        r"^[a-zA-Z_:][a-zA-Z0-9_:]*(?:\{[^\n]*\})?\s+"
        r"(?:[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|[-+]?Inf|NaN)"
        r"(?:\s+[0-9]+)?\s*$", body, re.M)
    require(samples, "Expected Prometheus text exposition with metric samples")

    events = []
    for line in logs.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("level") and event.get("msg"):
            events.append(event)
    require(events, "No structured slog JSON records")

    def has_request_id(value):
        if not isinstance(value, dict):
            return False
        return any(
            (re.fullmatch(r"request[_-]?id|correlation[_-]?id", key, re.I)
             and isinstance(item, str) and bool(item.strip()))
            or has_request_id(item)
            for key, item in value.items()
        )

    require(any(has_request_id(event) for event in events),
            "No nonempty request/correlation id in structured request logs")
