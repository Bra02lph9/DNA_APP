from __future__ import annotations

from typing import Any, Callable

from analysis.orf_finder import find_all_orfs
from analysis.promoters import find_promoters, promoter_to_dict
from analysis.terminators import (
    find_rho_independent_terminators,
    terminator_to_dict,
)
from analysis.shine_dalgarno import (
    find_shine_dalgarno_sites,
    shine_dalgarno_to_dict,
)
from analysis.coding_orfs import (
    find_coding_orfs,
    choose_best_coding_orf,
    coding_orfs_to_dicts,
    coding_orf_to_dict,
)
from analysis.coding_orf_ranker import (
    rank_coding_orfs,
    choose_best_ranked_coding_orf,
)
from analysis.utils import validate_dna


VALID_ANALYSIS_TYPES = {
    "all",
    "orfs",
    "promoters",
    "terminators",
    "shine_dalgarno",
    "coding_orfs",
    "ranked_coding_orfs",
}


def clean_sequence(sequence: str) -> str:
    if not isinstance(sequence, str):
        raise ValueError("Sequence must be a string.")

    return (
        sequence.upper()
        .replace("\n", "")
        .replace("\r", "")
        .replace(" ", "")
        .strip()
    )


def prepare_sequence(sequence: str) -> str:
    seq = clean_sequence(sequence)
    validate_dna(seq)
    return seq


def orf_to_dict(orf) -> dict[str, Any]:
    return {
        "strand": orf.strand,
        "frame": orf.frame,
        "start": orf.start,
        "end": orf.end,
        "length_nt": orf.length_nt,
        "sequence": orf.sequence,
        "peptide_length_aa": getattr(orf, "peptide_length_aa", None),
    }


def sd_to_dict(site) -> dict[str, Any]:
    return {
        "strand": site.strand,
        "start": site.start,
        "end": site.end,
        "sequence": site.sequence,
        "mismatches": site.mismatches,
        "linked_start_codon": site.linked_start_codon,
        "linked_start_position": site.linked_start_position,
        "distance_to_start": site.distance_to_start,
        "score": site.score,
    }


def _serialize_orfs(orfs) -> list[dict[str, Any]]:
    return [orf_to_dict(o) for o in orfs]


def _serialize_promoters(promoters) -> list[dict[str, Any]]:
    return [promoter_to_dict(p) for p in promoters]


def _serialize_terminators(terminators) -> list[dict[str, Any]]:
    return [terminator_to_dict(t) for t in terminators]


def _serialize_sd_sites(sites) -> list[dict[str, Any]]:
    return [sd_to_dict(s) for s in sites]


def analyze_orfs(sequence: str) -> dict[str, Any]:
    seq = prepare_sequence(sequence)
    orfs = find_all_orfs(seq)

    return {
        "length": len(seq),
        "orfs": _serialize_orfs(orfs),
    }


def analyze_promoters(sequence: str) -> dict[str, Any]:
    seq = prepare_sequence(sequence)
    promoters = find_promoters(seq)

    return {
        "length": len(seq),
        "promoters": _serialize_promoters(promoters),
    }


def analyze_terminators(sequence: str) -> dict[str, Any]:
    seq = prepare_sequence(sequence)
    terminators = find_rho_independent_terminators(seq)

    return {
        "length": len(seq),
        "terminators": _serialize_terminators(terminators),
    }


def analyze_shine_dalgarno(sequence: str) -> dict[str, Any]:
    seq = prepare_sequence(sequence)
    sites = find_shine_dalgarno_sites(seq)

    return {
        "length": len(seq),
        "shine_dalgarno": _serialize_sd_sites(sites),
    }


def analyze_coding_orfs(sequence: str, min_aa: int = 30) -> dict[str, Any]:
    seq = prepare_sequence(sequence)
    coding_orfs = find_coding_orfs(seq, min_aa=min_aa)
    best_orf = choose_best_coding_orf(seq, min_aa=min_aa)

    return {
        "length": len(seq),
        "coding_orfs": coding_orfs_to_dicts(coding_orfs),
        "best_coding_orf": coding_orf_to_dict(best_orf) if best_orf else None,
    }


def analyze_ranked_coding_orfs(sequence: str, min_aa: int = 30) -> dict[str, Any]:
    seq = prepare_sequence(sequence)
    ranked = rank_coding_orfs(seq, min_aa=min_aa)
    best = choose_best_ranked_coding_orf(seq, min_aa=min_aa)

    return {
        "length": len(seq),
        "ranked_coding_orfs": ranked,
        "best_ranked_coding_orf": best,
    }


def analyze_all(sequence: str, min_aa: int = 30) -> dict[str, Any]:
    seq = prepare_sequence(sequence)

    orfs = find_all_orfs(seq)
    promoters = find_promoters(seq)
    terminators = find_rho_independent_terminators(seq)
    sd_sites = find_shine_dalgarno_sites(seq)

    coding_orfs = find_coding_orfs(seq, min_aa=min_aa)
    best_coding_orf = choose_best_coding_orf(seq, min_aa=min_aa)

    ranked_coding_orfs = rank_coding_orfs(seq, min_aa=min_aa)
    best_ranked_coding_orf = choose_best_ranked_coding_orf(seq, min_aa=min_aa)

    return {
        "length": len(seq),
        "orfs": _serialize_orfs(orfs),
        "promoters": _serialize_promoters(promoters),
        "terminators": _serialize_terminators(terminators),
        "shine_dalgarno": _serialize_sd_sites(sd_sites),
        "coding_orfs": coding_orfs_to_dicts(coding_orfs),
        "best_coding_orf": coding_orf_to_dict(best_coding_orf) if best_coding_orf else None,
        "ranked_coding_orfs": ranked_coding_orfs,
        "best_ranked_coding_orf": best_ranked_coding_orf,
    }


def get_analysis_handler(analysis_type: str) -> Callable[..., dict[str, Any]]:
    handlers: dict[str, Callable[..., dict[str, Any]]] = {
        "all": analyze_all,
        "orfs": analyze_orfs,
        "promoters": analyze_promoters,
        "terminators": analyze_terminators,
        "shine_dalgarno": analyze_shine_dalgarno,
        "coding_orfs": analyze_coding_orfs,
        "ranked_coding_orfs": analyze_ranked_coding_orfs,
    }

    if analysis_type not in handlers:
        raise ValueError(
            f"Invalid analysis_type '{analysis_type}'. "
            f"Allowed values: {', '.join(sorted(handlers.keys()))}"
        )

    return handlers[analysis_type]


def analyze_sequence_by_type(
    sequence: str,
    analysis_type: str = "all",
    min_aa: int = 30,
) -> dict[str, Any]:
    handler = get_analysis_handler(analysis_type)

    if analysis_type in {"coding_orfs", "ranked_coding_orfs", "all"}:
        return handler(sequence, min_aa=min_aa)

    return handler(sequence)


def analyze_folder_files(
    files: list[dict[str, Any]],
    analysis_type: str = "all",
    min_aa: int = 30,
) -> list[dict[str, Any]]:
    if analysis_type not in VALID_ANALYSIS_TYPES:
        raise ValueError(
            f"Invalid analysis_type '{analysis_type}'. "
            f"Allowed values: {', '.join(sorted(VALID_ANALYSIS_TYPES))}"
        )

    output: list[dict[str, Any]] = []

    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Each file entry must be a dictionary.")

        seq = item.get("sequence", "")
        name = item.get("name", "unknown")
        header = item.get("header")

        result = analyze_sequence_by_type(
            sequence=seq,
            analysis_type=analysis_type,
            min_aa=min_aa,
        )

        result["file"] = name
        if header is not None:
            result["header"] = header

        output.append(result)

    return output
