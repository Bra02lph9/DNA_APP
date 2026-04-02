from __future__ import annotations

from typing import Dict, Any, Optional


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
    """
    Pipeline hybride biologiquement sûr :
      - coding ORFs : globaux
      - ORFs généraux : globaux optionnels
      - promoteurs / SD / terminateurs : chunkés
      - ranking final : global

    IMPORTANT :
    Cette fonction doit être appelée depuis la couche service / Flask,
    pas depuis une autre tâche Celery déjà en cours, pour éviter
    des tâches imbriquées bloquantes.
    """
    # import local pour éviter import circulaire
    from tasks.analysis_tasks import (
        run_global_coding_orfs,
        run_global_orfs,
        run_chunked_promoters,
        run_chunked_sd,
        run_chunked_terminators,
        assemble_and_rank,
    )

    seq = sequence.strip().upper()

    if not seq:
        return {
            "summary": {
                "coding_orf_count": 0,
                "promoter_count": 0,
                "shine_dalgarno_count": 0,
                "terminator_count": 0,
                "ranked_coding_orf_count": 0,
            },
            "coding_orfs": [],
            "promoters": [],
            "shine_dalgarno_sites": [],
            "terminators": [],
            "ranked_coding_orfs": [],
            "pipeline": {
                "mode": "hybrid_celery_large_sequence",
                "chunk_size": chunk_size,
                "overlap": overlap,
                "coding_orfs_strategy": "global_full_sequence",
                "promoters_strategy": "chunked_parallel",
                "shine_dalgarno_strategy": "chunked_parallel",
                "terminators_strategy": "chunked_parallel",
            },
        }

    coding_task = run_global_coding_orfs.delay(
        sequence=seq,
        min_aa=min_aa,
        longest_only_per_stop=longest_only_per_stop,
    )

    promoter_task = run_chunked_promoters.delay(
        sequence=seq,
        chunk_size=chunk_size,
        overlap=overlap,
        max_mismatches_box35=promoter_max_mismatches_box35,
        max_mismatches_box10=promoter_max_mismatches_box10,
        spacing_min=promoter_spacing_min,
        spacing_max=promoter_spacing_max,
    )

    sd_task = run_chunked_sd.delay(
        sequence=seq,
        chunk_size=chunk_size,
        overlap=overlap,
        max_mismatches=sd_max_mismatches,
    )

    terminator_task = run_chunked_terminators.delay(
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

    general_orfs_data = []
    if include_general_orfs:
        general_orf_task = run_global_orfs.delay(sequence=seq)
        general_orfs_data = general_orf_task.get(timeout=timeout)

    coding_orfs_data = coding_task.get(timeout=timeout)
    promoters_data = promoter_task.get(timeout=timeout)
    sd_sites_data = sd_task.get(timeout=timeout)
    terminators_data = terminator_task.get(timeout=timeout)

    final_task = assemble_and_rank.delay(
        coding_orfs_data=coding_orfs_data,
        promoters_data=promoters_data,
        sd_sites_data=sd_sites_data,
        terminators_data=terminators_data,
        max_promoter_distance=max_promoter_distance,
        max_terminator_distance=max_terminator_distance,
    )
    final_result = final_task.get(timeout=timeout)

    if include_general_orfs:
        final_result["orfs"] = general_orfs_data
        final_result["summary"]["orf_count"] = len(general_orfs_data)

    final_result["pipeline"] = {
        "mode": "hybrid_celery_large_sequence",
        "chunk_size": chunk_size,
        "overlap": overlap,
        "coding_orfs_strategy": "global_full_sequence",
        "promoters_strategy": "chunked_parallel",
        "shine_dalgarno_strategy": "chunked_parallel",
        "terminators_strategy": "chunked_parallel",
    }

    return final_result


def should_use_large_sequence_pipeline(
    sequence: str,
    threshold: int = DEFAULT_LARGE_SEQUENCE_THRESHOLD,
) -> bool:
    return len(sequence.strip()) >= threshold
