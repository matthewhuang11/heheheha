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
    def upsert_survivor(self, doc: dict) -> None:
        from pymongo.errors import DuplicateKeyError
        body = dict(doc); body["_id"] = doc["id"]
        try: self.db.survivors.update_one({"_id": doc["id"], "version": {"$lt": doc["version"]}}, {"$set": body}, upsert=True)
        except DuplicateKeyError: pass            # a newer version is already stored
    def add_sightings(self, rows: list[dict]) -> None:
        if rows: self.db.sightings.insert_many([dict(r) for r in rows])
    def add_telemetry(self, rows: list[dict]) -> None:
        if rows: self.db.telemetry.insert_many([dict(r) for r in rows])
