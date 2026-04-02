from __future__ import annotations

from typing import Dict, Any, Optional

from db.analysis_repository import (
    create_analysis,
    update_analysis_status,
)


DEFAULT_CHUNK_SIZE = 50_000
DEFAULT_OVERLAP = 1_000
DEFAULT_LARGE_SEQUENCE_THRESHOLD = 10_000


def run_large_sequence_analysis(
    sequence: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    min_aa: int = 30,
    longest_only_per_stop: bool = False,
    include_general_orfs: bool = False,
    promoter_max_mismatches_box35: int = 2,
    promoter_max_mismatches_box10: int = 2,
    promoter_spacing_min: int = 16,
    promoter_spacing_max: int = 19,
    sd_max_mismatches: int = 2,
    terminator_stem_min: int = 5,
    terminator_stem_max: int = 10,
    terminator_loop_min: int = 3,
    terminator_loop_max: int = 7,
    terminator_max_stem_mismatches: int = 1,
    terminator_min_poly_t: int = 5,
    terminator_gc_threshold: float = 0.7,
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    from tasks.analysis_tasks import (
        run_global_coding_orfs_store,
        run_chunked_promoters_store,
        run_chunked_sd_store,
        run_chunked_terminators_store,
        assemble_and_rank_from_storage,
    )

    seq = sequence.strip().upper()

    if not seq:
        return {
            "status": "empty_sequence",
            "analysis_id": None,
            "summary": {
                "coding_orf_count": 0,
                "promoter_count": 0,
                "shine_dalgarno_count": 0,
                "terminator_count": 0,
                "ranked_coding_orf_count": 0,
            },
        }

    analysis_id = create_analysis(
        sequence_length=len(seq),
        pipeline="hybrid_celery_large_sequence",
        parameters={
            "chunk_size": chunk_size,
            "overlap": overlap,
            "min_aa": min_aa,
            "longest_only_per_stop": longest_only_per_stop,
            "include_general_orfs": include_general_orfs,
            "promoter_max_mismatches_box35": promoter_max_mismatches_box35,
            "promoter_max_mismatches_box10": promoter_max_mismatches_box10,
            "promoter_spacing_min": promoter_spacing_min,
            "promoter_spacing_max": promoter_spacing_max,
            "sd_max_mismatches": sd_max_mismatches,
            "terminator_stem_min": terminator_stem_min,
            "terminator_stem_max": terminator_stem_max,
            "terminator_loop_min": terminator_loop_min,
            "terminator_loop_max": terminator_loop_max,
            "terminator_max_stem_mismatches": terminator_max_stem_mismatches,
            "terminator_min_poly_t": terminator_min_poly_t,
            "terminator_gc_threshold": terminator_gc_threshold,
            "max_promoter_distance": max_promoter_distance,
            "max_terminator_distance": max_terminator_distance,
        },
    )

    try:
        coding_task = run_global_coding_orfs_store.delay(
            analysis_id=analysis_id,
            sequence=seq,
            min_aa=min_aa,
            longest_only_per_stop=longest_only_per_stop,
        )

        promoter_task = run_chunked_promoters_store.delay(
            analysis_id=analysis_id,
            sequence=seq,
            chunk_size=chunk_size,
            overlap=overlap,
            max_mismatches_box35=promoter_max_mismatches_box35,
            max_mismatches_box10=promoter_max_mismatches_box10,
            spacing_min=promoter_spacing_min,
            spacing_max=promoter_spacing_max,
        )

        sd_task = run_chunked_sd_store.delay(
            analysis_id=analysis_id,
            sequence=seq,
            chunk_size=chunk_size,
            overlap=overlap,
            max_mismatches=sd_max_mismatches,
        )

        terminator_task = run_chunked_terminators_store.delay(
            analysis_id=analysis_id,
            sequence=seq,
            chunk_size=chunk_size,
            overlap=overlap,
            stem_min=terminator_stem_min,
            stem_max=terminator_stem_max,
            loop_min=terminator_loop_min,
            loop_max=terminator_loop_max,
            max_stem_mismatches=terminator_max_stem_mismatches,
            min_poly_t=terminator_min_poly_t,
            gc_threshold=terminator_gc_threshold,
        )

        coding_task.get(timeout=timeout)
        promoter_task.get(timeout=timeout)
        sd_task.get(timeout=timeout)
        terminator_task.get(timeout=timeout)

        final_task = assemble_and_rank_from_storage.delay(
            analysis_id=analysis_id,
            max_promoter_distance=max_promoter_distance,
            max_terminator_distance=max_terminator_distance,
        )
        final_result = final_task.get(timeout=timeout)

        update_analysis_status(analysis_id, "completed")

        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "summary": final_result.get("summary", {}),
            "pipeline": {
                "mode": "hybrid_celery_large_sequence",
                "chunk_size": chunk_size,
                "overlap": overlap,
                "storage": "mongodb",
            },
        }

    except Exception as exc:
        update_analysis_status(analysis_id, "failed")
        raise exc


def should_use_large_sequence_pipeline(
    sequence: str,
    threshold: int = DEFAULT_LARGE_SEQUENCE_THRESHOLD,
) -> bool:
    return len(sequence.strip()) >= threshold
