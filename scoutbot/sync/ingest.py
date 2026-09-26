"""Authenticated client for the Scoutbot HTTPS ingestion service."""
from __future__ import annotations

from urllib.parse import urlparse

import httpx


class IngestSink:
    """Send outbox records to a server that alone holds MongoDB credentials."""

    def __init__(self, url: str, token: str, *, client: httpx.Client | None = None):
        self.url = url.rstrip("/")
        if not self.url:
            raise ValueError("INGEST_URL is not set in .env")
        if urlparse(self.url).scheme != "https":
            raise ValueError("INGEST_URL must use https")
        if not token.strip():
            raise ValueError("INGEST_TOKEN is not set in .env")
        self.http = client or httpx.Client(base_url=self.url, timeout=5.0)
        self.http.headers["Authorization"] = f"Bearer {token}"

    def health(self) -> None:
        response = self.http.get("/healthz")
        response.raise_for_status()

    def _send(self, kind: str, records: list[dict]) -> None:
        if not records:
            return
        response = self.http.post("/v1/ingest", json={"items": [{"kind": kind, "payload": row} for row in records]})
        response.raise_for_status()
        body = response.json()
        if body.get("accepted") != len(records):
            raise RuntimeError("ingest server did not acknowledge every record")

    def upsert_survivor(self, doc: dict) -> None:
        self._send("survivor", [doc])

    def add_sightings(self, rows: list[dict]) -> None:
        self._send("sighting", rows)

    def add_telemetry(self, rows: list[dict]) -> None:
        self._send("telemetry", rows)
