from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

from analysis.analysis_service import (
    analyze_sequence_by_type,
    VALID_ANALYSIS_TYPES,
)


def _run_analysis(
    analysis_type: str,
    sequence: str,
    min_aa: int = 30,
) -> dict[str, Any]:
    return analyze_sequence_by_type(
        sequence=sequence,
        analysis_type=analysis_type,
        min_aa=min_aa,
    )


def analyze_files_in_parallel(
    files: list[dict[str, Any]],
    analysis_type: str = "all",
    min_aa: int = 30,
    max_workers: int | None = None,
) -> list[dict[str, Any]]:
    if analysis_type not in VALID_ANALYSIS_TYPES:
        raise ValueError(
            f"Invalid analysis_type '{analysis_type}'. "
            f"Allowed values: {', '.join(sorted(VALID_ANALYSIS_TYPES))}"
        )

    if not isinstance(files, list):
        raise ValueError("'files' must be a list of dictionaries.")

    results: list[dict[str, Any] | None] = [None] * len(files)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_meta: dict[Any, tuple[int, dict[str, Any]]] = {}

        for idx, item in enumerate(files):
            if not isinstance(item, dict):
                raise ValueError("Each file entry must be a dictionary.")

            seq = item.get("sequence", "")
            future = executor.submit(_run_analysis, analysis_type, seq, min_aa)
            future_to_meta[future] = (idx, item)

        for future in as_completed(future_to_meta):
            idx, item = future_to_meta[future]
            result = future.result()

            result["file"] = item.get("name", "unknown")

            if "header" in item:
                result["header"] = item.get("header")

            results[idx] = result

    return [result for result in results if result is not None]


def analyze_sequences_in_parallel(
    sequences: list[str],
    analysis_type: str = "all",
    min_aa: int = 30,
    max_workers: int | None = None,
) -> list[dict[str, Any]]:
    if analysis_type not in VALID_ANALYSIS_TYPES:
        raise ValueError(
            f"Invalid analysis_type '{analysis_type}'. "
            f"Allowed values: {', '.join(sorted(VALID_ANALYSIS_TYPES))}"
        )

    if not isinstance(sequences, list):
        raise ValueError("'sequences' must be a list of strings.")

    results: list[dict[str, Any] | None] = [None] * len(sequences)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_index: dict[Any, int] = {}

        for idx, seq in enumerate(sequences):
            if not isinstance(seq, str):
                raise ValueError("Each sequence must be a string.")

            future = executor.submit(_run_analysis, analysis_type, seq, min_aa)
            future_to_index[future] = idx

        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            results[idx] = future.result()

    return [result for result in results if result is not None]
