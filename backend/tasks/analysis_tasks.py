from __future__ import annotations
from functools import lru_cache
import logging
import time
from dataclasses import asdict, is_dataclass
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

logger = logging.getLogger(__name__)


class StepTimer:
    def __init__(self, label: str, extra: dict[str, Any] | None = None):
        self.label = label
        self.extra = extra or {}
        self.start = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        logger.debug("[START] %s | %s", self.label, self.extra)
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.perf_counter() - self.start
        logger.debug("[DONE] %s took %.4fs | %s", self.label, elapsed, self.extra)


@celery_app.task(bind=True, name="tasks.run_sequence_analysis")
def run_sequence_analysis(
    self,
    sequence: str,
    analysis_type: str = "all",
    min_aa: int = 30,
) -> dict[str, Any]:
    with StepTimer(
        "run_sequence_analysis",
        {"analysis_type": analysis_type, "seq_len": len(sequence)},
    ):
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
    with StepTimer(
        "run_folder_analysis",
        {"analysis_type": analysis_type, "file_count": len(files)},
    ):
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
    allowed_fields = set(getattr(CodingORF, "__dataclass_fields__", {}).keys())

    clean = {
        key: value
        for key, value in data.items()
        if key in allowed_fields
    }

    return CodingORF(**clean)


def _coding_orfs_from_dicts(items: List[dict]) -> List[CodingORF]:
    return [_coding_orf_from_dict(x) for x in items]


def _clean_mongo_fields(items: List[dict]) -> List[dict]:
    mongo_fields = {
        "analysis_id",
        "module",
        "kind",
        "chunk_index",
        "created_at",
    }

    return [
        {key: value for key, value in item.items() if key not in mongo_fields}
        for item in items
    ]


def _safe_update_module_status(analysis_id: str, module: str, status: str) -> None:
    try:
        update_module_status(analysis_id, module, status)
    except Exception as exc:
        logger.warning(
            "update_module_status failed | analysis_id=%s module=%s status=%s err=%s",
            analysis_id,
            module,
            status,
            exc,
        )


def _safe_append_analysis_error(analysis_id: str, module: str, message: str) -> None:
    try:
        append_analysis_error(analysis_id, module, message)
    except Exception as exc:
        logger.warning(
            "append_analysis_error failed | analysis_id=%s module=%s err=%s",
            analysis_id,
            module,
            exc,
        )


def _safe_replace_module_results(
    analysis_id: str,
    module: str,
    results: list,
    kind: str = "final",
) -> int:
    try:
        return replace_module_results(
            analysis_id=analysis_id,
            module=module,
            results=results,
            kind=kind,
        )
    except Exception as exc:
        logger.warning(
            "replace_module_results failed | analysis_id=%s module=%s kind=%s err=%s",
            analysis_id,
            module,
            kind,
            exc,
        )
        return len(results)


def _safe_update_analysis_summary(analysis_id: str, summary: dict) -> None:
    try:
        update_analysis_summary(analysis_id, summary)
    except Exception as exc:
        logger.warning(
            "update_analysis_summary failed | analysis_id=%s err=%s",
            analysis_id,
            exc,
        )


def _safe_update_analysis_status(analysis_id: str, status: str) -> None:
    try:
        update_analysis_status(analysis_id, status)
    except Exception as exc:
        logger.warning(
            "update_analysis_status failed | analysis_id=%s status=%s err=%s",
            analysis_id,
            status,
            exc,
        )


def _run_chunk_group_and_wait(task_signatures) -> List[dict]:
    if not task_signatures:
        return []

    with StepTimer("chunk_group_dispatch", {"task_count": len(task_signatures)}):
        job = group(task_signatures).apply_async()

    with StepTimer("chunk_group_wait", {"task_count": len(task_signatures)}):
        with allow_join_result():
            results = job.get(disable_sync_subtasks=False)

    return results


def _obj_to_dict(obj) -> dict:
    if obj is None:
        return {}

    if isinstance(obj, dict):
        return obj.copy()

    if is_dataclass(obj):
        return asdict(obj)

    if hasattr(obj, "__dict__"):
        return obj.__dict__.copy()

    slots = getattr(obj, "__slots__", None)
    if slots:
        if isinstance(slots, str):
            slots = [slots]
        return {slot: getattr(obj, slot) for slot in slots if hasattr(obj, slot)}

    raise TypeError(f"Cannot serialize object of type {type(obj).__name__}")


def _serialize_list(items: list[Any]) -> list[dict]:
    return [_obj_to_dict(x) for x in items]


def _feature_task_kwargs(
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
) -> dict[str, Any]:
    return {
        "max_mismatches_box35": max_mismatches_box35,
        "max_mismatches_box10": max_mismatches_box10,
        "spacing_min": spacing_min,
        "spacing_max": spacing_max,
        "max_sd_mismatches": max_sd_mismatches,
        "stem_min": stem_min,
        "stem_max": stem_max,
        "loop_min": loop_min,
        "loop_max": loop_max,
        "max_stem_mismatches": max_stem_mismatches,
        "min_poly_t": min_poly_t,
        "gc_threshold": gc_threshold,
    }


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
    chunk_start = chunk["start"]
    chunk_seq = chunk["sequence"]

    with StepTimer(
        "process_feature_chunk",
        {"chunk_start": chunk_start, "chunk_len": len(chunk_seq)},
    ):
        local_promoters = find_promoters(
            sequence=chunk_seq,
            max_mismatches_box35=max_mismatches_box35,
            max_mismatches_box10=max_mismatches_box10,
            spacing_min=spacing_min,
            spacing_max=spacing_max,
        )

        local_sd = find_shine_dalgarno_sites(
            sequence=chunk_seq,
            max_mismatches=max_sd_mismatches,
        )

        local_terminators = find_rho_independent_terminators(
            sequence=chunk_seq,
            stem_min=stem_min,
            stem_max=stem_max,
            loop_min=loop_min,
            loop_max=loop_max,
            max_stem_mismatches=max_stem_mismatches,
            min_poly_t=min_poly_t,
            gc_threshold=gc_threshold,
        )

        remapped_promoters = [
            remap_promoter_hit(hit, chunk_start) for hit in local_promoters
        ]
        remapped_sd = [remap_sd_site(hit, chunk_start) for hit in local_sd]
        remapped_terminators = [
            remap_terminator_hit(hit, chunk_start) for hit in local_terminators
        ]

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
    _safe_update_module_status(analysis_id, module, "running")

    try:
        with StepTimer(
            "find_coding_orfs",
            {"analysis_id": analysis_id, "seq_len": len(sequence)},
        ):
            coding_orfs = find_coding_orfs(
                sequence=sequence,
                min_aa=min_aa,
                longest_only_per_stop=longest_only_per_stop,
            )

        with StepTimer(
            "store_coding_orfs",
            {"analysis_id": analysis_id, "count": len(coding_orfs)},
        ):
            serialized = _serialize_list(coding_orfs)
            count = _safe_replace_module_results(
                analysis_id=analysis_id,
                module=module,
                results=serialized,
                kind="final",
            )

        _safe_update_module_status(analysis_id, module, "done")
        return {
            "analysis_id": analysis_id,
            "module": module,
            "count": count,
            "status": "done",
        }

    except Exception as exc:
        _safe_update_module_status(analysis_id, module, "failed")
        _safe_append_analysis_error(analysis_id, module, str(exc))
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
    modules = ("promoters", "shine_dalgarno", "terminators")
    for module in modules:
        _safe_update_module_status(analysis_id, module, "running")

    try:
        with StepTimer(
            "chunk_sequence",
            {
                "analysis_id": analysis_id,
                "seq_len": len(sequence),
                "chunk_size": chunk_size,
                "overlap": overlap,
            },
        ):
            chunks = chunk_sequence(sequence, chunk_size=chunk_size, overlap=overlap)

        if not chunks:
            for module in modules:
                _safe_replace_module_results(analysis_id, module, [], kind="final")
                _safe_update_module_status(analysis_id, module, "done")

            return {
                "analysis_id": analysis_id,
                "status": "done",
                "promoters_count": 0,
                "shine_dalgarno_count": 0,
                "terminators_count": 0,
            }

        feature_kwargs = _feature_task_kwargs(
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

        task_signatures = [
            process_feature_chunk.s(chunk=chunk, **feature_kwargs)
            for chunk in chunks
        ]

        chunk_results = _run_chunk_group_and_wait(task_signatures)

        with StepTimer(
            "merge_chunk_results",
            {"analysis_id": analysis_id, "chunk_count": len(chunk_results)},
        ):
            all_promoters_dicts: List[dict] = []
            all_sd_dicts: List[dict] = []
            all_terminators_dicts: List[dict] = []

            for result in chunk_results:
                all_promoters_dicts.extend(result.get("promoters", []))
                all_sd_dicts.extend(result.get("shine_dalgarno", []))
                all_terminators_dicts.extend(result.get("terminators", []))

        with StepTimer("deserialize_and_deduplicate", {"analysis_id": analysis_id}):
            promoter_hits = promoters_from_dicts(all_promoters_dicts)
            sd_hits = sd_sites_from_dicts(all_sd_dicts)
            terminator_hits = terminators_from_dicts(all_terminators_dicts)

            merged_promoters = deduplicate_promoters(promoter_hits)
            merged_sd = deduplicate_sd_sites(sd_hits)
            merged_terminators = deduplicate_terminators(terminator_hits)

        with StepTimer("serialize_final_features", {"analysis_id": analysis_id}):
            final_promoters = serialize_promoters(merged_promoters)
            final_sd = serialize_sd_sites(merged_sd)
            final_terminators = serialize_terminators(merged_terminators)

        with StepTimer("store_final_features", {"analysis_id": analysis_id}):
            _safe_replace_module_results(
                analysis_id=analysis_id,
                module="promoters",
                results=final_promoters,
                kind="final",
            )
            _safe_replace_module_results(
                analysis_id=analysis_id,
                module="shine_dalgarno",
                results=final_sd,
                kind="final",
            )
            _safe_replace_module_results(
                analysis_id=analysis_id,
                module="terminators",
                results=final_terminators,
                kind="final",
            )

        for module in modules:
            _safe_update_module_status(analysis_id, module, "done")

        return {
            "analysis_id": analysis_id,
            "status": "done",
            "chunk_count": len(chunks),
            "promoters_count": len(final_promoters),
            "shine_dalgarno_count": len(final_sd),
            "terminators_count": len(final_terminators),
        }

    except Exception as exc:
        for module in modules:
            _safe_update_module_status(analysis_id, module, "failed")
        _safe_append_analysis_error(analysis_id, "chunked_features", str(exc))
        raise


@celery_app.task(name="tasks.assemble_and_rank_from_storage")
def assemble_and_rank_from_storage(
    analysis_id: str,
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> Dict[str, Any]:
    module = "ranking"
    _safe_update_module_status(analysis_id, module, "running")

    try:
        with StepTimer("fetch_results_for_ranking", {"analysis_id": analysis_id}):
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

        with StepTimer(
            "deserialize_results_for_ranking",
            {"analysis_id": analysis_id},
        ):
            coding_orfs = _coding_orfs_from_dicts(coding_orfs_data)
            promoters = promoters_from_dicts(_clean_mongo_fields(promoters_data))
            sd_sites = sd_sites_from_dicts(_clean_mongo_fields(sd_sites_data))
            terminators = terminators_from_dicts(_clean_mongo_fields(terminators_data))

        with StepTimer(
            "rank_coding_orfs_from_features",
            {"analysis_id": analysis_id, "orf_count": len(coding_orfs)},
        ):
            ranked = rank_coding_orfs_from_features(
                coding_orfs=coding_orfs,
                promoters=promoters,
                sd_sites=sd_sites,
                terminators=terminators,
                max_promoter_distance=max_promoter_distance,
                max_terminator_distance=max_terminator_distance,
            )

        with StepTimer("serialize_ranked_orfs", {"analysis_id": analysis_id}):
            ranked_data = _serialize_list(ranked)

        with StepTimer(
            "store_ranked_orfs",
            {"analysis_id": analysis_id, "count": len(ranked_data)},
        ):
            _safe_replace_module_results(
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

        _safe_update_analysis_summary(analysis_id, summary)
        _safe_update_module_status(analysis_id, module, "done")
        _safe_update_analysis_status(analysis_id, "completed")

        return {
            "analysis_id": analysis_id,
            "summary": summary,
            "status": "done",
        }

    except Exception as exc:
        _safe_update_module_status(analysis_id, module, "failed")
        _safe_update_analysis_status(analysis_id, "failed")
        _safe_append_analysis_error(analysis_id, module, str(exc))
        raise


@celery_app.task(name="tasks.run_large_sequence_analysis_task")
def run_large_sequence_analysis_task(
    sequence: str,
    min_aa: int = 30,
):
    from analysis.large_sequence_service import run_large_sequence_analysis

    with StepTimer(
        "run_large_sequence_analysis_task",
        {"seq_len": len(sequence), "min_aa": min_aa},
    ):
        return run_large_sequence_analysis(
            sequence=sequence,
            min_aa=min_aa,
        )


CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def translate_dna_to_protein(sequence: str) -> str:
    sequence = sequence.upper().replace("U", "T").replace(" ", "").replace("\n", "")
    protein = []

    for i in range(0, len(sequence) - 2, 3):
        codon = sequence[i:i + 3]
        aa = CODON_TABLE.get(codon, "X")

        if aa == "*":
            break

        protein.append(aa)

    return "".join(protein)


def kmer_set(seq: str, k: int = 3) -> set[str]:
    if len(seq) < k:
        return set()
    return {seq[i:i + k] for i in range(len(seq) - k + 1)}


def kmer_jaccard(seq1: str, seq2: str, k: int = 3) -> float:
    s1 = kmer_set(seq1, k)
    s2 = kmer_set(seq2, k)

    if not s1 or not s2:
        return 0.0

    return len(s1 & s2) / len(s1 | s2)


def needleman_wunsch_global(
    seq1: str,
    seq2: str,
    match_score: int = 2,
    mismatch_score: int = -1,
    gap_score: int = -2,
) -> dict:
    n = len(seq1)
    m = len(seq2)

    score = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        score[i][0] = i * gap_score

    for j in range(1, m + 1):
        score[0][j] = j * gap_score

    for i in range(1, n + 1):
        a = seq1[i - 1]

        for j in range(1, m + 1):
            b = seq2[j - 1]

            diag = score[i - 1][j - 1] + (match_score if a == b else mismatch_score)
            up = score[i - 1][j] + gap_score
            left = score[i][j - 1] + gap_score

            score[i][j] = max(diag, up, left)

    aligned1 = []
    aligned2 = []

    i = n
    j = m

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            current = score[i][j]
            diag_score = score[i - 1][j - 1] + (
                match_score if seq1[i - 1] == seq2[j - 1] else mismatch_score
            )

            if current == diag_score:
                aligned1.append(seq1[i - 1])
                aligned2.append(seq2[j - 1])
                i -= 1
                j -= 1
                continue

        if i > 0 and score[i][j] == score[i - 1][j] + gap_score:
            aligned1.append(seq1[i - 1])
            aligned2.append("-")
            i -= 1
        else:
            aligned1.append("-")
            aligned2.append(seq2[j - 1])
            j -= 1

    aligned1 = "".join(reversed(aligned1))
    aligned2 = "".join(reversed(aligned2))

    aligned_length = len(aligned1)
    matches = sum(
        1 for a, b in zip(aligned1, aligned2)
        if a == b and a != "-" and b != "-"
    )

    identity = matches / aligned_length if aligned_length else 0.0

    return {
        "identity": identity,
        "identity_percent": round(identity * 100, 2),
        "alignment_score": score[n][m],
        "aligned_seq_1": aligned1,
        "aligned_seq_2": aligned2,
        "matches": matches,
        "alignment_length": aligned_length,
    }


def get_orf_score(orf: dict) -> float:
    for key in ["final_score", "biological_score", "score", "rank_score", "total_score"]:
        value = orf.get(key)
        if isinstance(value, (int, float)):
            return float(value)

    return float(orf.get("peptide_length_aa", 0))


def preview_alignment(seq: str, size: int = 160) -> str:
    if len(seq) <= size:
        return seq
    return seq[:size] + "..."


@celery_app.task(name="tasks.align_similar_orfs_from_storage")
def align_similar_orfs_from_storage(
    analysis_id: str,
    identity_threshold: float = 0.90,
    max_orfs: int = 500,
    kmer_threshold: float = 0.50,
) -> Dict[str, Any]:
    module = "aligned_orfs"
    _safe_update_module_status(analysis_id, module, "running")

    try:
        ranked_orfs = fetch_module_results(
            analysis_id=analysis_id,
            module="ranked_coding_orfs",
            kind="final",
            limit=max_orfs,
        )

        prepared = []

        for idx, orf in enumerate(ranked_orfs):
            protein = translate_dna_to_protein(orf.get("sequence", ""))

            if not protein:
                continue

            prepared.append({
                **orf,
                "orf_uid": f"ORF_{idx + 1}",
                "protein_sequence": protein,
            })

        visited = set()
        clusters = []

        for i in range(len(prepared)):
            if i in visited:
                continue

            cluster_orfs = [prepared[i]]
            pair_alignments = []

            for j in range(i + 1, len(prepared)):
                if j in visited:
                    continue

                seq1 = prepared[i]["protein_sequence"]
                seq2 = prepared[j]["protein_sequence"]

                length_ratio = min(len(seq1), len(seq2)) / max(len(seq1), len(seq2))
                if length_ratio < 0.80:
                    continue

                kmer_score = kmer_jaccard(seq1, seq2, k=3)
                if kmer_score < kmer_threshold:
                    continue

                alignment = needleman_wunsch_global(seq1, seq2)

                if alignment["identity"] >= identity_threshold:
                    cluster_orfs.append(prepared[j])
                    visited.add(j)

                    pair_alignments.append({
                        "orf_1": prepared[i]["orf_uid"],
                        "orf_2": prepared[j]["orf_uid"],
                        "identity_percent": alignment["identity_percent"],
                        "alignment_score": alignment["alignment_score"],
                        "matches": alignment["matches"],
                        "alignment_length": alignment["alignment_length"],
                        "aligned_seq_1": preview_alignment(alignment["aligned_seq_1"]),
                        "aligned_seq_2": preview_alignment(alignment["aligned_seq_2"]),
                    })

            if len(cluster_orfs) >= 2:
                visited.add(i)

                best_orf = max(cluster_orfs, key=get_orf_score)

                clusters.append({
                    "cluster_id": len(clusters) + 1,
                    "identity_threshold": identity_threshold * 100,
                    "orf_count": len(cluster_orfs),
                    "best_orf_uid": best_orf["orf_uid"],
                    "best_orf_start": best_orf.get("start"),
                    "best_orf_end": best_orf.get("end"),
                    "best_orf_strand": best_orf.get("strand"),
                    "best_orf_score": get_orf_score(best_orf),
                    "orfs": [
                        {
                            "orf_uid": item["orf_uid"],
                            "start": item.get("start"),
                            "end": item.get("end"),
                            "strand": item.get("strand"),
                            "frame": item.get("frame"),
                            "length_nt": item.get("length_nt"),
                            "peptide_length_aa": item.get("peptide_length_aa"),
                            "start_codon": item.get("start_codon"),
                            "stop_codon": item.get("stop_codon"),
                            "score": get_orf_score(item),
                            "protein_preview": preview_alignment(item["protein_sequence"], 100),
                        }
                        for item in cluster_orfs
                    ],
                    "alignments": pair_alignments,
                })

        _safe_replace_module_results(
            analysis_id=analysis_id,
            module=module,
            results=clusters,
            kind="final",
        )

        _safe_update_module_status(analysis_id, module, "done")

        return {
            "analysis_id": analysis_id,
            "module": module,
            "status": "done",
            "cluster_count": len(clusters),
            "identity_threshold": identity_threshold,
            "method": "kmer_filter + Needleman-Wunsch global protein alignment",
        }

    except Exception as exc:
        _safe_update_module_status(analysis_id, module, "failed")
        _safe_append_analysis_error(analysis_id, module, str(exc))
        raise
