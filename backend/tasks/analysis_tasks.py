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

from db.analysis_repository import (
    update_module_status,
    append_analysis_error,
    replace_module_results,
    fetch_module_results,
    count_module_results,
    update_analysis_summary,
)


@celery_app.task(bind=True, name="tasks.run_sequence_analysis")
def run_sequence_analysis(
    self,
    sequence: str,
    analysis_type: str = "all",
    min_aa: int = 30,
) -> dict[str, Any]:
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


@celery_app.task(name="tasks.run_global_coding_orfs_store")
def run_global_coding_orfs_store(
    analysis_id: str,
    sequence: str,
    min_aa: int = 30,
    longest_only_per_stop: bool = False,
) -> Dict[str, Any]:
    module = "coding_orfs"
    update_module_status(analysis_id, module, "running")

    try:
        coding_orfs = find_coding_orfs(
            sequence=sequence,
            min_aa=min_aa,
            longest_only_per_stop=longest_only_per_stop,
        )
        serialized = [asdict(x) for x in coding_orfs]
        count = replace_module_results(
            analysis_id=analysis_id,
            module=module,
            results=serialized,
            kind="final",
        )
        update_module_status(analysis_id, module, "done")
        return {
            "analysis_id": analysis_id,
            "module": module,
            "count": count,
            "status": "done",
        }
    except Exception as exc:
        update_module_status(analysis_id, module, "failed")
        append_analysis_error(analysis_id, module, str(exc))
        raise


@celery_app.task(name="tasks.run_promoter_chunk_store")
def run_promoter_chunk_store(
    analysis_id: str,
    chunk: Dict[str, Any],
    chunk_index: int,
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
) -> Dict[str, Any]:
    local_hits = find_promoters(
        sequence=chunk["sequence"],
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
    )

    remapped = [remap_promoter_hit(hit, chunk["start"]) for hit in local_hits]
    serialized = serialize_promoters(remapped)

    count = replace_module_results(
        analysis_id=analysis_id,
        module="promoters",
        results=serialized,
        kind="raw_chunk",
        chunk_index=chunk_index,
    )

    return {
        "analysis_id": analysis_id,
        "module": "promoters",
        "chunk_index": chunk_index,
        "count": count,
        "status": "done",
    }


@celery_app.task(name="tasks.run_sd_chunk_store")
def run_sd_chunk_store(
    analysis_id: str,
    chunk: Dict[str, Any],
    chunk_index: int,
    max_mismatches: int = 2,
) -> Dict[str, Any]:
    local_hits = find_shine_dalgarno_sites(
        sequence=chunk["sequence"],
        max_mismatches=max_mismatches,
    )

    remapped = [remap_sd_site(hit, chunk["start"]) for hit in local_hits]
    serialized = serialize_sd_sites(remapped)

    count = replace_module_results(
        analysis_id=analysis_id,
        module="shine_dalgarno",
        results=serialized,
        kind="raw_chunk",
        chunk_index=chunk_index,
    )

    return {
        "analysis_id": analysis_id,
        "module": "shine_dalgarno",
        "chunk_index": chunk_index,
        "count": count,
        "status": "done",
    }


@celery_app.task(name="tasks.run_terminator_chunk_store")
def run_terminator_chunk_store(
    analysis_id: str,
    chunk: Dict[str, Any],
    chunk_index: int,
    stem_min: int = 5,
    stem_max: int = 10,
    loop_min: int = 3,
    loop_max: int = 7,
    max_stem_mismatches: int = 1,
    min_poly_t: int = 5,
    gc_threshold: float = 0.7,
) -> Dict[str, Any]:
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
    serialized = serialize_terminators(remapped)

    count = replace_module_results(
        analysis_id=analysis_id,
        module="terminators",
        results=serialized,
        kind="raw_chunk",
        chunk_index=chunk_index,
    )

    return {
        "analysis_id": analysis_id,
        "module": "terminators",
        "chunk_index": chunk_index,
        "count": count,
        "status": "done",
    }


@celery_app.task(name="tasks.run_chunked_promoters_store")
def run_chunked_promoters_store(
    analysis_id: str,
    sequence: str,
    chunk_size: int = 50_000,
    overlap: int = 1_000,
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
) -> Dict[str, Any]:
    module = "promoters"
    update_module_status(analysis_id, module, "running")

    try:
        chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

        job = group(
            run_promoter_chunk_store.s(
                analysis_id,
                chunk,
                idx,
                max_mismatches_box35,
                max_mismatches_box10,
                spacing_min,
                spacing_max,
            )
            for idx, chunk in enumerate(chunks)
        )

        job.apply_async().get()

        raw_hits = fetch_module_results(
            analysis_id=analysis_id,
            module=module,
            kind="raw_chunk",
        )
        promoter_hits = promoters_from_dicts(raw_hits)
        merged = deduplicate_promoters(promoter_hits)
        serialized = serialize_promoters(merged)

        replace_module_results(
            analysis_id=analysis_id,
            module=module,
            results=serialized,
            kind="final",
        )

        update_module_status(analysis_id, module, "done")
        return {
            "analysis_id": analysis_id,
            "module": module,
            "count": len(serialized),
            "status": "done",
        }

    except Exception as exc:
        update_module_status(analysis_id, module, "failed")
        append_analysis_error(analysis_id, module, str(exc))
        raise


@celery_app.task(name="tasks.run_chunked_sd_store")
def run_chunked_sd_store(
    analysis_id: str,
    sequence: str,
    chunk_size: int = 50_000,
    overlap: int = 1_000,
    max_mismatches: int = 2,
) -> Dict[str, Any]:
    module = "shine_dalgarno"
    update_module_status(analysis_id, module, "running")

    try:
        chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

        job = group(
            run_sd_chunk_store.s(
                analysis_id,
                chunk,
                idx,
                max_mismatches,
            )
            for idx, chunk in enumerate(chunks)
        )

        job.apply_async().get()

        raw_hits = fetch_module_results(
            analysis_id=analysis_id,
            module=module,
            kind="raw_chunk",
        )
        sd_hits = sd_sites_from_dicts(raw_hits)
        merged = deduplicate_sd_sites(sd_hits)
        serialized = serialize_sd_sites(merged)

        replace_module_results(
            analysis_id=analysis_id,
            module=module,
            results=serialized,
            kind="final",
        )

        update_module_status(analysis_id, module, "done")
        return {
            "analysis_id": analysis_id,
            "module": module,
            "count": len(serialized),
            "status": "done",
        }

    except Exception as exc:
        update_module_status(analysis_id, module, "failed")
        append_analysis_error(analysis_id, module, str(exc))
        raise


@celery_app.task(name="tasks.run_chunked_terminators_store")
def run_chunked_terminators_store(
    analysis_id: str,
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
) -> Dict[str, Any]:
    module = "terminators"
    update_module_status(analysis_id, module, "running")

    try:
        chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

        job = group(
            run_terminator_chunk_store.s(
                analysis_id,
                chunk,
                idx,
                stem_min,
                stem_max,
                loop_min,
                loop_max,
                max_stem_mismatches,
                min_poly_t,
                gc_threshold,
            )
            for idx, chunk in enumerate(chunks)
        )

        job.apply_async().get()

        raw_hits = fetch_module_results(
            analysis_id=analysis_id,
            module=module,
            kind="raw_chunk",
        )
        terminator_hits = terminators_from_dicts(raw_hits)
        merged = deduplicate_terminators(terminator_hits)
        serialized = serialize_terminators(merged)

        replace_module_results(
            analysis_id=analysis_id,
            module=module,
            results=serialized,
            kind="final",
        )

        update_module_status(analysis_id, module, "done")
        return {
            "analysis_id": analysis_id,
            "module": module,
            "count": len(serialized),
            "status": "done",
        }

    except Exception as exc:
        update_module_status(analysis_id, module, "failed")
        append_analysis_error(analysis_id, module, str(exc))
        raise


@celery_app.task(name="tasks.assemble_and_rank_from_storage")
def assemble_and_rank_from_storage(
    analysis_id: str,
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> Dict[str, Any]:
    module = "ranking"
    update_module_status(analysis_id, module, "running")

    try:
        coding_orfs_data = fetch_module_results(
            analysis_id=analysis_id,
            module="coding_orfs",
            kind="final",
        )
        promoters_data = fetch_module_results(
            analysis_id=analysis_id,
            module="promoters",
            kind="final",
        )
        sd_sites_data = fetch_module_results(
            analysis_id=analysis_id,
            module="shine_dalgarno",
            kind="final",
        )
        terminators_data = fetch_module_results(
            analysis_id=analysis_id,
            module="terminators",
            kind="final",
        )

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

        ranked_data = ranked if isinstance(ranked, list) else [asdict(x) for x in ranked]

        replace_module_results(
            analysis_id=analysis_id,
            module="ranked_coding_orfs",
            results=ranked_data,
            kind="final",
        )

        summary = {
            "coding_orf_count": count_module_results(analysis_id, "coding_orfs", "final"),
            "promoter_count": count_module_results(analysis_id, "promoters", "final"),
            "shine_dalgarno_count": count_module_results(analysis_id, "shine_dalgarno", "final"),
            "terminator_count": count_module_results(analysis_id, "terminators", "final"),
            "ranked_coding_orf_count": count_module_results(analysis_id, "ranked_coding_orfs", "final"),
        }

        update_analysis_summary(analysis_id, summary)
        update_module_status(analysis_id, module, "done")

        return {
            "analysis_id": analysis_id,
            "summary": summary,
            "status": "done",
        }

    except Exception as exc:
        update_module_status(analysis_id, module, "failed")
        append_analysis_error(analysis_id, module, str(exc))
        raise


@celery_app.task(name="tasks.run_large_sequence_analysis_task")
def run_large_sequence_analysis_task(
    sequence: str,
    min_aa: int = 30,
):
    from analysis.large_sequence_service import run_large_sequence_analysis

    return run_large_sequence_analysis(
        sequence=sequence,
        min_aa=min_aa,
    )

