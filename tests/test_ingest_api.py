from fastapi.testclient import TestClient

from scoutbot.ingest.app import create_app


class Repository:
    def __init__(self, fail=False):
        self.fail = fail
        self.survivors = {}
        self.events = {"sighting": {}, "telemetry": {}}

    def health(self):
        if self.fail:
            raise ConnectionError()

    def upsert_survivor(self, doc):
        if self.fail:
            raise ConnectionError()
        if doc["version"] > self.survivors.get(doc["id"], {}).get("version", -1):
            self.survivors[doc["id"]] = doc

    def add_event(self, kind, event):
        if self.fail:
            raise ConnectionError()
        self.events[kind].setdefault(event["event_id"], event)


def survivor(version=1):
    return {
        "id": "S-1", "first_seen": "2026-01-01T00:00:00Z", "last_seen": "2026-01-01T00:00:00Z",
        "pose": {"x_cm": 1, "y_cm": 2, "source": "sim"}, "version": version,
    }


def telemetry(event_id="t1"):
    return {
        "event_id": event_id, "time": "2026-01-01T00:00:00Z", "mode": "STOPPED", "action": "STOP",
        "rule": 1, "left_cm": 1, "center_cm": 2, "right_cm": 3, "internet": True, "x_cm": 4, "y_cm": 5,
    }


def test_health_and_bearer_authentication():
    repo = Repository()
    client = TestClient(create_app(repository=repo, token="test-token"))
    assert client.get("/healthz").json() == {"status": "ok"}
    response = client.post("/v1/ingest", json={"items": [{"kind": "survivor", "payload": survivor()}]})
    assert response.status_code == 401


def test_validated_ingest_versions_and_duplicate_events_are_idempotent():
    repo = Repository()
    client = TestClient(create_app(repository=repo, token="test-token"))
    headers = {"Authorization": "Bearer test-token"}
    body = {"items": [
        {"kind": "survivor", "payload": survivor(2)},
        {"kind": "telemetry", "payload": telemetry()},
    ]}
    assert client.post("/v1/ingest", json=body, headers=headers).json() == {"accepted": 2}
    assert client.post("/v1/ingest", json=body, headers=headers).json() == {"accepted": 2}
    assert repo.survivors["S-1"]["version"] == 2
    assert len(repo.events["telemetry"]) == 1


def test_ingest_rejects_invalid_payloads_before_writing():
    repo = Repository()
    client = TestClient(create_app(repository=repo, token="test-token"))
    response = client.post(
        "/v1/ingest",
        json={"items": [{"kind": "telemetry", "payload": {"event_id": "x"}}]},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 422
    assert not repo.events["telemetry"]


def test_database_failure_returns_retryable_response_without_details():
    client = TestClient(create_app(repository=Repository(fail=True), token="test-token"))
    response = client.post(
        "/v1/ingest",
        json={"items": [{"kind": "survivor", "payload": survivor()}]},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "ingest unavailable"}
