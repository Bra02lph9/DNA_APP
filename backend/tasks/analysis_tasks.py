from __future__ import annotations

from typing import Any, Dict, List

from celery import group
from celery.result import allow_join_result

from tasks.celery_app import celery_app
from analysis.analysis_service import (
    analyze_sequence_by_type,
    analyze_folder_files,
)

from analysis.coding_orfs import find_coding_orfs, CodingORF
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
    update_analysis_summary,
    update_analysis_status,
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


def _store_empty_final_results(analysis_id: str, module: str) -> Dict[str, Any]:
    replace_module_results(
        analysis_id=analysis_id,
        module=module,
        results=[],
        kind="final",
    )
    update_module_status(analysis_id, module, "done")
    return {
        "analysis_id": analysis_id,
        "module": module,
        "count": 0,
        "status": "done",
    }


def _run_chunk_group_and_wait(task_signatures) -> List[dict]:
    if not task_signatures:
        return []

    job = group(task_signatures).apply_async()

    with allow_join_result():
        results = job.get(disable_sync_subtasks=False)

    return results


def _obj_to_dict(obj) -> dict:
    return vars(obj).copy()


@celery_app.task(name="tasks.process_feature_chunk")
def process_feature_chunk(
    chunk: Dict[str, Any],
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
    max_sd_mismatches: int = 2,
    stem_min: int = 5,
    stem_max: int = 10,
    loop_min: int = 3,
    loop_max: int = 7,
    max_stem_mismatches: int = 1,
    min_poly_t: int = 5,
    gc_threshold: float = 0.7,
) -> Dict[str, Any]:
    local_promoters = find_promoters(
        sequence=chunk["sequence"],
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
    )

    local_sd = find_shine_dalgarno_sites(
        sequence=chunk["sequence"],
        max_mismatches=max_sd_mismatches,
    )

    local_terminators = find_rho_independent_terminators(
        sequence=chunk["sequence"],
        stem_min=stem_min,
        stem_max=stem_max,
        loop_min=loop_min,
        loop_max=loop_max,
        max_stem_mismatches=max_stem_mismatches,
        min_poly_t=min_poly_t,
        gc_threshold=gc_threshold,
    )

    remapped_promoters = [remap_promoter_hit(hit, chunk["start"]) for hit in local_promoters]
    remapped_sd = [remap_sd_site(hit, chunk["start"]) for hit in local_sd]
    remapped_terminators = [remap_terminator_hit(hit, chunk["start"]) for hit in local_terminators]

    return {
        "promoters": serialize_promoters(remapped_promoters),
        "shine_dalgarno": serialize_sd_sites(remapped_sd),
        "terminators": serialize_terminators(remapped_terminators),
    }


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
        serialized = [_obj_to_dict(x) for x in coding_orfs]

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


@celery_app.task(name="tasks.run_chunked_features_store")
def run_chunked_features_store(
    analysis_id: str,
    sequence: str,
    chunk_size: int = 250_000,
    overlap: int = 500,
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
    max_sd_mismatches: int = 2,
    stem_min: int = 5,
    stem_max: int = 10,
    loop_min: int = 3,
    loop_max: int = 7,
    max_stem_mismatches: int = 1,
    min_poly_t: int = 5,
    gc_threshold: float = 0.7,
) -> Dict[str, Any]:
    update_module_status(analysis_id, "promoters", "running")
    update_module_status(analysis_id, "shine_dalgarno", "running")
    update_module_status(analysis_id, "terminators", "running")

    try:
        chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

        if not chunks:
            replace_module_results(analysis_id, "promoters", [], kind="final")
            replace_module_results(analysis_id, "shine_dalgarno", [], kind="final")
            replace_module_results(analysis_id, "terminators", [], kind="final")

            update_module_status(analysis_id, "promoters", "done")
            update_module_status(analysis_id, "shine_dalgarno", "done")
            update_module_status(analysis_id, "terminators", "done")

            return {
                "analysis_id": analysis_id,
                "status": "done",
                "promoters_count": 0,
                "shine_dalgarno_count": 0,
                "terminators_count": 0,
            }

        task_signatures = [
            process_feature_chunk.s(
                chunk=chunk,
                max_mismatches_box35=max_mismatches_box35,
                max_mismatches_box10=max_mismatches_box10,
                spacing_min=spacing_min,
                spacing_max=spacing_max,
                max_sd_mismatches=max_sd_mismatches,
                stem_min=stem_min,
                stem_max=stem_max,
                loop_min=loop_min,
                loop_max=loop_max,
                max_stem_mismatches=max_stem_mismatches,
                min_poly_t=min_poly_t,
                gc_threshold=gc_threshold,
            )
            for chunk in chunks
        ]

        chunk_results = _run_chunk_group_and_wait(task_signatures)

        all_promoters_dicts: List[dict] = []
        all_sd_dicts: List[dict] = []
        all_terminators_dicts: List[dict] = []

        for result in chunk_results:
            all_promoters_dicts.extend(result.get("promoters", []))
            all_sd_dicts.extend(result.get("shine_dalgarno", []))
            all_terminators_dicts.extend(result.get("terminators", []))

        promoter_hits = promoters_from_dicts(all_promoters_dicts)
        sd_hits = sd_sites_from_dicts(all_sd_dicts)
        terminator_hits = terminators_from_dicts(all_terminators_dicts)

        merged_promoters = deduplicate_promoters(promoter_hits)
        merged_sd = deduplicate_sd_sites(sd_hits)
        merged_terminators = deduplicate_terminators(terminator_hits)

        final_promoters = serialize_promoters(merged_promoters)
        final_sd = serialize_sd_sites(merged_sd)
        final_terminators = serialize_terminators(merged_terminators)

        replace_module_results(
            analysis_id=analysis_id,
            module="promoters",
            results=final_promoters,
            kind="final",
        )
        replace_module_results(
            analysis_id=analysis_id,
            module="shine_dalgarno",
            results=final_sd,
            kind="final",
        )
        replace_module_results(
            analysis_id=analysis_id,
            module="terminators",
            results=final_terminators,
            kind="final",
        )

        update_module_status(analysis_id, "promoters", "done")
        update_module_status(analysis_id, "shine_dalgarno", "done")
        update_module_status(analysis_id, "terminators", "done")

        return {
            "analysis_id": analysis_id,
            "status": "done",
            "promoters_count": len(final_promoters),
            "shine_dalgarno_count": len(final_sd),
            "terminators_count": len(final_terminators),
        }

    except Exception as exc:
        update_module_status(analysis_id, "promoters", "failed")
        update_module_status(analysis_id, "shine_dalgarno", "failed")
        update_module_status(analysis_id, "terminators", "failed")
        append_analysis_error(analysis_id, "chunked_features", str(exc))
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

        ranked_data = ranked if isinstance(ranked, list) else [_obj_to_dict(x) for x in ranked]

        replace_module_results(
            analysis_id=analysis_id,
            module="ranked_coding_orfs",
            results=ranked_data,
            kind="final",
        )

        summary = {
            "coding_orf_count": len(coding_orfs_data),
            "promoter_count": len(promoters_data),
            "shine_dalgarno_count": len(sd_sites_data),
            "terminator_count": len(terminators_data),
            "ranked_coding_orf_count": len(ranked_data),
        }

        update_analysis_summary(analysis_id, summary)
        update_module_status(analysis_id, module, "done")
        update_analysis_status(analysis_id, "completed")

        return {
            "analysis_id": analysis_id,
            "summary": summary,
            "status": "done",
        }

    except Exception as exc:
        update_module_status(analysis_id, module, "failed")
        update_analysis_status(analysis_id, "failed")
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
