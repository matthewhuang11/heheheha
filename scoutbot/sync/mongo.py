"""MongoDB sink (Atlas free tier). Put MONGODB_URI in .env. Database 'scoutbot':
  survivors  one document per survivor (_id = survivor id), including chat and triage; only newer versions overwrite
  sightings, telemetry  one document per row"""
from __future__ import annotations

class MongoSink:
    def __init__(self, uri: str, db: str = "scoutbot"):
        if not uri: raise ValueError("MONGODB_URI is not set in .env")
        from pymongo import MongoClient
        self.client = MongoClient(uri, serverSelectionTimeoutMS=4000, connectTimeoutMS=4000)
        self.db = self.client[db]; self.client.admin.command("ping")
        self.db.sightings.create_index([("survivor_id", 1), ("time", 1)])
        self.db.telemetry.create_index([("time", 1)])
        self.db.sightings.create_index("event_id", unique=True, sparse=True)
        self.db.telemetry.create_index("event_id", unique=True, sparse=True)
    def upsert_survivor(self, doc: dict) -> None:
        from pymongo.errors import DuplicateKeyError
        body = dict(doc); body["_id"] = doc["id"]
        try: self.db.survivors.update_one({"_id": doc["id"], "version": {"$lt": doc["version"]}}, {"$set": body}, upsert=True)
        except DuplicateKeyError: pass            # a newer version is already stored
    def add_sightings(self, rows: list[dict]) -> None:
        self._add_events("sightings", rows)
    def add_telemetry(self, rows: list[dict]) -> None:
        self._add_events("telemetry", rows)
    def _add_events(self, collection: str, rows: list[dict]) -> None:
        if not rows:
            return
        from pymongo import UpdateOne
        operations = []
        for row in rows:
            event_id = row.get("event_id")
            if event_id:
                operations.append(UpdateOne({"event_id": event_id}, {"$setOnInsert": dict(row)}, upsert=True))
            else:  # pre-id outbox files remain readable during upgrade.
                operations.append(UpdateOne(dict(row), {"$setOnInsert": dict(row)}, upsert=True))
        self.db[collection].bulk_write(operations, ordered=False)
