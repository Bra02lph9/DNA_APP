from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from db.mongo import get_database


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_analysis(
    sequence_length: int,
    pipeline: str,
    parameters: Dict[str, Any],
) -> str:
    db = get_database()
    analysis_id = str(uuid4())

    doc = {
        "_id": analysis_id,
        "status": "running",
        "pipeline": pipeline,
        "sequence_length": sequence_length,
        "parameters": parameters,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "modules": {
            "coding_orfs": "pending",
            "promoters": "pending",
            "shine_dalgarno": "pending",
            "terminators": "pending",
            "ranking": "pending",
        },
        "summary": {},
        "errors": [],
    }

    db["analyses"].insert_one(doc)
    return analysis_id


def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    db = get_database()
    return db["analyses"].find_one({"_id": analysis_id})


def update_analysis_status(analysis_id: str, status: str) -> None:
    db = get_database()
    db["analyses"].update_one(
        {"_id": analysis_id},
        {
            "$set": {
                "status": status,
                "updated_at": utc_now(),
            }
        },
    )


def update_module_status(
    analysis_id: str,
    module: str,
    status: str,
) -> None:
    db = get_database()
    db["analyses"].update_one(
        {"_id": analysis_id},
        {
            "$set": {
                f"modules.{module}": status,
                "updated_at": utc_now(),
            }
        },
    )


def append_analysis_error(
    analysis_id: str,
    module: str,
    message: str,
) -> None:
    db = get_database()
    db["analyses"].update_one(
        {"_id": analysis_id},
        {
            "$push": {
                "errors": {
                    "module": module,
                    "message": message,
                    "timestamp": utc_now(),
                }
            },
            "$set": {"updated_at": utc_now()},
        },
    )


def replace_module_results(
    analysis_id: str,
    module: str,
    results: List[Dict[str, Any]],
    kind: str = "final",
    chunk_index: Optional[int] = None,
) -> int:
    db = get_database()
    collection = db["analysis_results"]

    delete_filter: Dict[str, Any] = {
        "analysis_id": analysis_id,
        "module": module,
        "kind": kind,
    }

    if chunk_index is not None:
        delete_filter["chunk_index"] = chunk_index

    collection.delete_many(delete_filter)

    if not results:
        return 0

    docs = []
    for item in results:
        doc = {
            "analysis_id": analysis_id,
            "module": module,
            "kind": kind,
            "chunk_index": chunk_index,
            "created_at": utc_now(),
            **item,
        }
        docs.append(doc)

    collection.insert_many(docs)
    return len(docs)


def fetch_module_results(
    analysis_id: str,
    module: str,
    kind: str = "final",
    sort_field: Optional[str] = None,
    sort_direction: int = 1,
    limit: Optional[int] = None,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    db = get_database()
    cursor = db["analysis_results"].find(
        {
            "analysis_id": analysis_id,
            "module": module,
            "kind": kind,
        },
        {"_id": 0},
    )

    if sort_field:
        cursor = cursor.sort(sort_field, sort_direction)

    if skip:
        cursor = cursor.skip(skip)

    if limit is not None:
        cursor = cursor.limit(limit)

    return list(cursor)


def count_module_results(
    analysis_id: str,
    module: str,
    kind: str = "final",
) -> int:
    db = get_database()
    return db["analysis_results"].count_documents(
        {
            "analysis_id": analysis_id,
            "module": module,
            "kind": kind,
        }
    )


def update_analysis_summary(
    analysis_id: str,
    summary: Dict[str, Any],
) -> None:
    db = get_database()
    db["analyses"].update_one(
        {"_id": analysis_id},
        {
            "$set": {
                "summary": summary,
                "updated_at": utc_now(),
            }
        },
    )
