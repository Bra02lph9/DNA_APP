from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from celery import group

from tasks.celery_app import celery_app
from analysis.analysis_service import (
    analyze_sequence_by_type,
    analyze_folder_files,
)

from analysis.coding_orfs import find_coding_orfs, CodingORF
from analysis.orf_finder import find_all_orfs
from analysis.promoters import find_promoters
from analysis.shine_dalgarno import find_shine_dalgarno_sites
from analysis.terminators import find_rho_independent_terminators
from analysis.coding_orf_ranker import rank_coding_orfs_from_features

from analysis.chunk_utils import (
    chunk_sequence,
    remap_promoter_hit,
    remap_sd_site,
    remap_terminator_hit,
    deduplicate_promoters,
    deduplicate_sd_sites,
    deduplicate_terminators,
    serialize_promoters,
    serialize_sd_sites,
    serialize_terminators,
    promoters_from_dicts,
    sd_sites_from_dicts,
    terminators_from_dicts,
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


def _coding_orf_from_dict(data: dict) -> CodingORF:
    return CodingORF(**data)


def _coding_orfs_from_dicts(items: List[dict]) -> List[CodingORF]:
    return [_coding_orf_from_dict(x) for x in items]


@celery_app.task(name="tasks.run_global_coding_orfs")
def run_global_coding_orfs(
    sequence: str,
    min_aa: int = 30,
    longest_only_per_stop: bool = False,
) -> List[dict]:
    coding_orfs = find_coding_orfs(
        sequence=sequence,
        min_aa=min_aa,
        longest_only_per_stop=longest_only_per_stop,
    )
    return [asdict(x) for x in coding_orfs]


@celery_app.task(name="tasks.run_global_orfs")
def run_global_orfs(sequence: str) -> List[dict]:
    orfs = find_all_orfs(sequence)
    return [asdict(x) for x in orfs]


@celery_app.task(name="tasks.run_promoter_chunk")
def run_promoter_chunk(
    chunk: Dict[str, Any],
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
) -> List[dict]:
    local_hits = find_promoters(
        sequence=chunk["sequence"],
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
    )

    remapped = [remap_promoter_hit(hit, chunk["start"]) for hit in local_hits]
    return serialize_promoters(remapped)


@celery_app.task(name="tasks.run_sd_chunk")
def run_sd_chunk(
    chunk: Dict[str, Any],
    max_mismatches: int = 2,
) -> List[dict]:
    local_hits = find_shine_dalgarno_sites(
        sequence=chunk["sequence"],
        max_mismatches=max_mismatches,
    )

    remapped = [remap_sd_site(hit, chunk["start"]) for hit in local_hits]
    return serialize_sd_sites(remapped)


@celery_app.task(name="tasks.run_terminator_chunk")
def run_terminator_chunk(
    chunk: Dict[str, Any],
    stem_min: int = 5,
    stem_max: int = 10,
    loop_min: int = 3,
    loop_max: int = 7,
    max_stem_mismatches: int = 1,
    min_poly_t: int = 5,
    gc_threshold: float = 0.7,
) -> List[dict]:
    local_hits = find_rho_independent_terminators(
        sequence=chunk["sequence"],
        stem_min=stem_min,
        stem_max=stem_max,
        loop_min=loop_min,
        loop_max=loop_max,
        max_stem_mismatches=max_stem_mismatches,
        min_poly_t=min_poly_t,
        gc_threshold=gc_threshold,
    )

    remapped = [remap_terminator_hit(hit, chunk["start"]) for hit in local_hits]
    return serialize_terminators(remapped)


@celery_app.task(name="tasks.run_chunked_promoters")
def run_chunked_promoters(
    sequence: str,
    chunk_size: int = 50_000,
    overlap: int = 1_000,
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
) -> List[dict]:
    chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

    job = group(
        run_promoter_chunk.s(
            chunk,
            max_mismatches_box35,
            max_mismatches_box10,
            spacing_min,
            spacing_max,
        )
        for chunk in chunks
    )

    grouped_result = job.apply_async().get()

    all_hits = []
    for sublist in grouped_result:
        all_hits.extend(promoters_from_dicts(sublist))

    merged = deduplicate_promoters(all_hits)
    return serialize_promoters(merged)


@celery_app.task(name="tasks.run_chunked_sd")
def run_chunked_sd(
    sequence: str,
    chunk_size: int = 50_000,
    overlap: int = 1_000,
    max_mismatches: int = 2,
) -> List[dict]:
    chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

    job = group(
        run_sd_chunk.s(chunk, max_mismatches)
        for chunk in chunks
    )

    grouped_result = job.apply_async().get()

    all_hits = []
    for sublist in grouped_result:
        all_hits.extend(sd_sites_from_dicts(sublist))

    merged = deduplicate_sd_sites(all_hits)
    return serialize_sd_sites(merged)


@celery_app.task(name="tasks.run_chunked_terminators")
def run_chunked_terminators(
    sequence: str,
    chunk_size: int = 50_000,
    overlap: int = 1_000,
    stem_min: int = 5,
    stem_max: int = 10,
    loop_min: int = 3,
    loop_max: int = 7,
    max_stem_mismatches: int = 1,
    min_poly_t: int = 5,
    gc_threshold: float = 0.7,
) -> List[dict]:
    chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

    job = group(
        run_terminator_chunk.s(
            chunk,
            stem_min,
            stem_max,
            loop_min,
            loop_max,
            max_stem_mismatches,
            min_poly_t,
            gc_threshold,
        )
        for chunk in chunks
    )

    grouped_result = job.apply_async().get()

    all_hits = []
    for sublist in grouped_result:
        all_hits.extend(terminators_from_dicts(sublist))

    merged = deduplicate_terminators(all_hits)
    return serialize_terminators(merged)


@celery_app.task(name="tasks.assemble_and_rank")
def assemble_and_rank(
    coding_orfs_data: List[dict],
    promoters_data: List[dict],
    sd_sites_data: List[dict],
    terminators_data: List[dict],
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> Dict[str, Any]:
    coding_orfs = _coding_orfs_from_dicts(coding_orfs_data)
    promoters = promoters_from_dicts(promoters_data)
    sd_sites = sd_sites_from_dicts(sd_sites_data)
    terminators = terminators_from_dicts(terminators_data)

    ranked = rank_coding_orfs_from_features(
        coding_orfs=coding_orfs,
        promoters=promoters,
        sd_sites=sd_sites,
        terminators=terminators,
        max_promoter_distance=max_promoter_distance,
        max_terminator_distance=max_terminator_distance,
    )

    return {
        "summary": {
            "coding_orf_count": len(coding_orfs),
            "promoter_count": len(promoters),
            "shine_dalgarno_count": len(sd_sites),
            "terminator_count": len(terminators),
            "ranked_coding_orf_count": len(ranked),
        },
        "coding_orfs": coding_orfs_data,
        "promoters": promoters_data,
        "shine_dalgarno_sites": sd_sites_data,
        "terminators": terminators_data,
        "ranked_coding_orfs": ranked,
    }
