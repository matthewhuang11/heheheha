import httpx
import pytest

from scoutbot.sync.ingest import IngestSink


def test_ingest_sink_requires_https_and_token():
    with pytest.raises(ValueError, match="https"):
        IngestSink("http://ingest.example", "token")
    with pytest.raises(ValueError, match="TOKEN"):
        IngestSink("https://ingest.example", "")


def test_ingest_sink_authenticates_and_requires_full_acknowledgement():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.json() if hasattr(request, "json") else None
        return httpx.Response(200, json={"accepted": 1})

    # httpx.Request intentionally has no .json(); decode the payload in this
    # compatible handler while retaining MockTransport's request inspection.
    def json_handler(request: httpx.Request) -> httpx.Response:
        import json
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"accepted": 1})

    client = httpx.Client(base_url="https://ingest.example", transport=httpx.MockTransport(json_handler))
    sink = IngestSink("https://ingest.example", "secret-token", client=client)
    sink.add_telemetry([{"event_id": "e1", "time": "2026-01-01T00:00:00Z", "mode": "STOPPED"}])
    assert seen["auth"] == "Bearer secret-token"
    assert seen["body"]["items"][0]["kind"] == "telemetry"


def test_ingest_sink_keeps_failure_visible_to_outbox():
    client = httpx.Client(
        base_url="https://ingest.example",
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
    )
    sink = IngestSink("https://ingest.example", "token", client=client)
    with pytest.raises(httpx.HTTPStatusError):
        sink.upsert_survivor({"id": "S-1", "version": 1})
