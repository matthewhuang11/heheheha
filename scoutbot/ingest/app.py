"""Vultr-hosted authenticated HTTPS ingestion API."""
from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request, status

from scoutbot.ingest.models import IngestRequest
from scoutbot.ingest.repository import MongoRepository

MAX_BODY_BYTES = 1_000_000


def create_app(*, repository=None, token: str | None = None) -> FastAPI:
    """Create the isolated ingest service; never attach this to the dashboard app."""
    expected_token = token if token is not None else os.getenv("INGEST_TOKEN", "")
    repo = repository or MongoRepository(os.getenv("MONGODB_URI", ""))
    app = FastAPI(title="Scoutbot ingest", docs_url=None, redoc_url=None, openapi_url=None)

    def authorize(authorization: str | None) -> None:
        expected = f"Bearer {expected_token}"
        if not expected_token or not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    @app.get("/healthz")
    def healthz():
        try:
            repo.health()
        except Exception:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable")
        return {"status": "ok"}

    @app.post("/v1/ingest")
    def ingest(
        request: Request,
        body: IngestRequest,
        authorization: str | None = Header(default=None),
    ):
        length = request.headers.get("content-length")
        if length:
            try:
                too_large = int(length) > MAX_BODY_BYTES
            except ValueError:
                too_large = True
            if too_large:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="request too large")
        authorize(authorization)
        try:
            for item in body.items:
                if item.kind == "survivor":
                    repo.upsert_survivor(item.payload)
                else:
                    repo.add_event(item.kind, item.payload)
        except Exception:
            # Do not disclose database internals. Retrying the same batch is safe.
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ingest unavailable")
        return {"accepted": len(body.items)}

    return app
