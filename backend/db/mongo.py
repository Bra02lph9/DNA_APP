from __future__ import annotations

import os
from pymongo import MongoClient
from pymongo.database import Database


_MONGO_CLIENT: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _MONGO_CLIENT

    if _MONGO_CLIENT is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _MONGO_CLIENT = MongoClient(mongo_uri)

    return _MONGO_CLIENT


def get_database() -> Database:
    db_name = os.getenv("MONGO_DB_NAME", "dna_analyzer")
    return get_mongo_client()[db_name]


def ensure_indexes() -> None:
    db = get_database()

    analyses = db["analyses"]
    results = db["analysis_results"]

    analyses.create_index("created_at")
    analyses.create_index("status")
    analyses.create_index("sequence_length")

    results.create_index([("analysis_id", 1), ("module", 1)])
    results.create_index([("analysis_id", 1), ("module", 1), ("kind", 1)])
    results.create_index([("analysis_id", 1), ("module", 1), ("start", 1)])
    results.create_index([("analysis_id", 1), ("module", 1), ("score", -1)])
    results.create_index([("analysis_id", 1), ("module", 1), ("chunk_index", 1)])
