from __future__ import annotations

from typing import Any

from tasks.celery_app import celery_app
from analysis.analysis_service import (
    analyze_sequence_by_type,
    analyze_folder_files,
)


@celery_app.task(bind=True, name="tasks.run_sequence_analysis")
def run_sequence_analysis(
    self,
    sequence: str,
    analysis_type: str = "all",
    min_aa: int = 30,
) -> dict[str, Any]:
    """
    Run analysis on a single DNA sequence in background.
    """
    result = analyze_sequence_by_type(
        sequence=sequence,
        analysis_type=analysis_type,
        min_aa=min_aa,
    )

    return {
        "status": "completed",
        "analysis_type": analysis_type,
        "result": result,
    }


@celery_app.task(bind=True, name="tasks.run_folder_analysis")
def run_folder_analysis(
    self,
    files: list[dict[str, Any]],
    analysis_type: str = "all",
    min_aa: int = 30,
) -> dict[str, Any]:
    """
    Run analysis on multiple FASTA files in background.
    """
    result = analyze_folder_files(
        files=files,
        analysis_type=analysis_type,
        min_aa=min_aa,
    )

    return {
        "status": "completed",
        "analysis_type": analysis_type,
        "result": result,
    }
