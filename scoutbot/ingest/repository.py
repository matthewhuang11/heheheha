"""MongoDB persistence owned by the server-side ingestion service."""
from __future__ import annotations

from datetime import datetime, timezone


def received_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class MongoRepository:
    def __init__(self, uri: str, database: str = "scoutbot"):
        if not uri:
            raise ValueError("MONGODB_URI is not configured on the ingest server")
        from pymongo import MongoClient
        self.client = MongoClient(uri, serverSelectionTimeoutMS=4000, connectTimeoutMS=4000)
        self.db = self.client[database]
        self.client.admin.command("ping")
        self.db.survivors.create_index("last_seen")
        self.db.survivors.create_index("triage.category")
        self.db.sightings.create_index([("survivor_id", 1), ("time", 1)])
        self.db.sightings.create_index("event_id", unique=True)
        self.db.telemetry.create_index("time")
        self.db.telemetry.create_index([("robot_id", 1), ("time", 1)])
        self.db.telemetry.create_index("event_id", unique=True)

    def health(self) -> None:
        self.client.admin.command("ping")

    def upsert_survivor(self, doc: dict) -> None:
        from pymongo.errors import DuplicateKeyError
        body = {**doc, "_id": doc["id"], "received_at": received_at()}
        try:
            self.db.survivors.update_one(
                {"_id": doc["id"], "version": {"$lt": doc["version"]}},
                {"$set": body},
                upsert=True,
            )
        except DuplicateKeyError:
            pass  # A newer version won a concurrent race.

    def add_event(self, kind: str, event: dict) -> None:
        collection = self.db[f"{kind}s"]
        collection.update_one(
            {"event_id": event["event_id"]},
            {"$setOnInsert": {**event, "received_at": received_at()}},
            upsert=True,
        )
