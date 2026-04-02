from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple

from .utils import reverse_complement
from .numba_helpers import gc_fraction_numba, hamming_distance_numba

try:
    from ._terminators_cy import scan_terminator_positions_cy
except ImportError:
    scan_terminator_positions_cy = None


VALID_DNA = {"A", "T", "C", "G", "N"}


@dataclass(slots=True)
class TerminatorHit:
    strand: str
    stem_left_start: int
    stem_left_end: int
    stem_left_seq: str
    loop_seq: str
    stem_right_start: int
    stem_right_end: int
    stem_right_seq: str
    poly_t_start: int
    poly_t_end: int
    poly_t_seq: str
    stem_length: int
    loop_length: int
    mismatches: int
    gc_fraction: float
    poly_t_length: int
    score: float


def _clean_sequence(sequence: str) -> str:
    return (
        sequence.replace("\n", "")
        .replace("\r", "")
        .replace(" ", "")
        .upper()
    )


def _contains_only_dna(sequence: str) -> bool:
    return all(base in VALID_DNA for base in sequence)


def _is_gc_rich(sequence: str, threshold: float = 0.7) -> bool:
    if not sequence:
        return False
    return gc_fraction_numba(sequence) >= threshold


def _gc_fraction(sequence: str) -> float:
    if not sequence:
        return 0.0
    return gc_fraction_numba(sequence)


def _revcomp_simple(seq: str) -> str:
    trans = str.maketrans("ATCGN", "TAGCN")
    return seq.translate(trans)[::-1]


def _map_rev_to_forward(
    rev_start_0: int,
    rev_end_0_exclusive: int,
    original_len: int,
) -> tuple[int, int]:
    forward_start_0 = original_len - rev_end_0_exclusive
    forward_end_0_exclusive = original_len - rev_start_0
    return forward_start_0 + 1, forward_end_0_exclusive


def _count_mismatches(seq1: str, seq2: str) -> int:
    return hamming_distance_numba(seq1, seq2)


def _calculate_score(
    stem_length: int,
    loop_length: int,
    mismatches: int,
    gc_fraction: float,
    poly_t_length: int,
) -> float:
    loop_penalty = abs(loop_length - 4.5) * 0.8
    mismatch_penalty = mismatches * 4.0

    score = (
        stem_length * 2.5
        + gc_fraction * 12.0
        + poly_t_length * 3.0
        - mismatch_penalty
        - loop_penalty
    )
    return round(score, 3)


def _build_hit(
    strand: str,
    sequence_len: int,
    left_start_0: int,
    left_end_0_exclusive: int,
    left_seq: str,
    loop_seq: str,
    right_start_0: int,
    right_end_0_exclusive: int,
    right_seq: str,
    poly_start_0: int,
    poly_end_0_exclusive: int,
    poly_t_seq: str,
    stem_length: int,
    loop_length: int,
    mismatches: int,
) -> TerminatorHit:
    gc_fraction = _gc_fraction(left_seq)
    poly_t_length = len(poly_t_seq)
    score = _calculate_score(
        stem_length=stem_length,
        loop_length=loop_length,
        mismatches=mismatches,
        gc_fraction=gc_fraction,
        poly_t_length=poly_t_length,
    )

    if strand == "+":
        stem_left_start = left_start_0 + 1
        stem_left_end = left_end_0_exclusive
        stem_right_start = right_start_0 + 1
        stem_right_end = right_end_0_exclusive
        poly_t_start = poly_start_0 + 1
        poly_t_end = poly_end_0_exclusive
    else:
        stem_left_start, stem_left_end = _map_rev_to_forward(
            left_start_0, left_end_0_exclusive, sequence_len
        )
        stem_right_start, stem_right_end = _map_rev_to_forward(
            right_start_0, right_end_0_exclusive, sequence_len
        )
        poly_t_start, poly_t_end = _map_rev_to_forward(
            poly_start_0, poly_end_0_exclusive, sequence_len
        )

    return TerminatorHit(
        strand=strand,
        stem_left_start=stem_left_start,
        stem_left_end=stem_left_end,
        stem_left_seq=left_seq,
        loop_seq=loop_seq,
        stem_right_start=stem_right_start,
        stem_right_end=stem_right_end,
        stem_right_seq=right_seq,
        poly_t_start=poly_t_start,
        poly_t_end=poly_t_end,
        poly_t_seq=poly_t_seq,
        stem_length=stem_length,
        loop_length=loop_length,
        mismatches=mismatches,
        gc_fraction=round(gc_fraction, 3),
        poly_t_length=poly_t_length,
        score=score,
    )


def _deduplicate_hits(hits: List[TerminatorHit]) -> List[TerminatorHit]:
    best_by_key: Dict[Tuple, TerminatorHit] = {}

    for hit in hits:
        key = (
            hit.strand,
            hit.stem_left_start,
            hit.stem_left_end,
            hit.stem_right_start,
            hit.stem_right_end,
            hit.poly_t_start,
            hit.poly_t_end,
        )
        current = best_by_key.get(key)
        if current is None or hit.score > current.score:
            best_by_key[key] = hit

    return list(best_by_key.values())


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return not (a_end < b_start or b_end < a_start)


def _filter_redundant_overlaps(hits: List[TerminatorHit]) -> List[TerminatorHit]:
    sorted_hits = sorted(hits, key=lambda h: (-h.score, h.strand, h.poly_t_start))
    kept: List[TerminatorHit] = []

    for hit in sorted_hits:
        hit_start = min(hit.poly_t_start, hit.stem_left_start, hit.stem_right_start)
        hit_end = max(hit.poly_t_end, hit.stem_left_end, hit.stem_right_end)

        redundant = False
        for prev in kept:
            if hit.strand != prev.strand:
                continue

            prev_start = min(prev.poly_t_start, prev.stem_left_start, prev.stem_right_start)
            prev_end = max(prev.poly_t_end, prev.stem_left_end, prev.stem_right_end)

            if _overlap(hit_start, hit_end, prev_start, prev_end):
                redundant = True
                break

        if not redundant:
            kept.append(hit)

    return kept


def _sort_terminators_biologically(hits: List[TerminatorHit]) -> List[TerminatorHit]:
    return sorted(
        hits,
        key=lambda h: (
            -h.score,
            -h.poly_t_length,
            -h.stem_length,
            h.mismatches,
            h.loop_length,
            0 if h.strand == "+" else 1,
            min(h.poly_t_start, h.stem_left_start, h.stem_right_start),
        ),
    )


def _collect_poly_t(search_seq: str, start_0: int) -> tuple[int, str]:
    n = len(search_seq)
    end_0_exclusive = start_0

    while end_0_exclusive < n and search_seq[end_0_exclusive] == "T":
        end_0_exclusive += 1

    return end_0_exclusive, search_seq[start_0:end_0_exclusive]


def _scan_terminator_positions_python(
    search_seq: str,
    stem_min: int,
    stem_max: int,
    loop_min: int,
    loop_max: int,
    max_stem_mismatches: int,
    min_poly_t: int,
    gc_threshold: float,
) -> List[tuple[int, int, int, int, int, int, int]]:
    n = len(search_seq)
    min_total_len = (2 * stem_min) + loop_min + min_poly_t
    if n < min_total_len:
        return []

    hits_raw: List[tuple[int, int, int, int, int, int, int]] = []
    max_left_start = n - min_total_len

    for i in range(max_left_start + 1):
        for stem_len in range(stem_min, stem_max + 1):
            left_start_0 = i
            left_end_0_exclusive = i + stem_len

            if left_end_0_exclusive > n:
                continue

            left = search_seq[left_start_0:left_end_0_exclusive]
            if "N" in left:
                continue
            if not _is_gc_rich(left, threshold=gc_threshold):
                continue

            expected_right = _revcomp_simple(left)

            for loop_len in range(loop_min, loop_max + 1):
                right_start_0 = left_end_0_exclusive + loop_len
                right_end_0_exclusive = right_start_0 + stem_len

                if right_end_0_exclusive > n:
                    continue

                right = search_seq[right_start_0:right_end_0_exclusive]
                if "N" in right:
                    continue

                mismatches = _count_mismatches(right, expected_right)
                if mismatches > max_stem_mismatches:
                    continue

                poly_start_0 = right_end_0_exclusive
                poly_end_0_exclusive, poly_t_seq = _collect_poly_t(search_seq, poly_start_0)

                if len(poly_t_seq) < min_poly_t:
                    continue

                hits_raw.append(
                    (
                        left_start_0,
                        left_end_0_exclusive,
                        right_start_0,
                        right_end_0_exclusive,
                        poly_start_0,
                        poly_end_0_exclusive,
                        mismatches,
                    )
                )

    return hits_raw


def _scan_terminator_positions(
    search_seq: str,
    stem_min: int,
    stem_max: int,
    loop_min: int,
    loop_max: int,
    max_stem_mismatches: int,
    min_poly_t: int,
    gc_threshold: float,
) -> List[tuple[int, int, int, int, int, int, int]]:
    if scan_terminator_positions_cy is not None:
        return scan_terminator_positions_cy(
            search_seq,
            stem_min,
            stem_max,
            loop_min,
            loop_max,
            max_stem_mismatches,
            min_poly_t,
            gc_threshold,
        )

    return _scan_terminator_positions_python(
        search_seq=search_seq,
        stem_min=stem_min,
        stem_max=stem_max,
        loop_min=loop_min,
        loop_max=loop_max,
        max_stem_mismatches=max_stem_mismatches,
        min_poly_t=min_poly_t,
        gc_threshold=gc_threshold,
    )


def find_rho_independent_terminators_in_strand(
    sequence: str,
    strand: str = "+",
    stem_min: int = 5,
    stem_max: int = 10,
    loop_min: int = 3,
    loop_max: int = 7,
    max_stem_mismatches: int = 1,
    min_poly_t: int = 5,
    gc_threshold: float = 0.7,
    already_clean: bool = False,
) -> List[TerminatorHit]:
    seq = sequence if already_clean else _clean_sequence(sequence)
    if not seq or not _contains_only_dna(seq):
        return []

    search_seq = seq if strand == "+" else reverse_complement(seq)
    n = len(search_seq)

    min_total_len = (2 * stem_min) + loop_min + min_poly_t
    if n < min_total_len:
        return []

    raw_hits = _scan_terminator_positions(
        search_seq=search_seq,
        stem_min=stem_min,
        stem_max=stem_max,
        loop_min=loop_min,
        loop_max=loop_max,
        max_stem_mismatches=max_stem_mismatches,
        min_poly_t=min_poly_t,
        gc_threshold=gc_threshold,
    )

    hits: List[TerminatorHit] = []

    for (
        left_start_0,
        left_end_0_exclusive,
        right_start_0,
        right_end_0_exclusive,
        poly_start_0,
        poly_end_0_exclusive,
        mismatches,
    ) in raw_hits:
        left = search_seq[left_start_0:left_end_0_exclusive]
        loop_seq = search_seq[left_end_0_exclusive:right_start_0]
        right = search_seq[right_start_0:right_end_0_exclusive]
        poly_t_seq = search_seq[poly_start_0:poly_end_0_exclusive]

        hit = _build_hit(
            strand=strand,
            sequence_len=len(seq),
            left_start_0=left_start_0,
            left_end_0_exclusive=left_end_0_exclusive,
            left_seq=left,
            loop_seq=loop_seq,
            right_start_0=right_start_0,
            right_end_0_exclusive=right_end_0_exclusive,
            right_seq=right,
            poly_start_0=poly_start_0,
            poly_end_0_exclusive=poly_end_0_exclusive,
            poly_t_seq=poly_t_seq,
            stem_length=left_end_0_exclusive - left_start_0,
            loop_length=right_start_0 - left_end_0_exclusive,
            mismatches=mismatches,
        )
        hits.append(hit)

    hits = _deduplicate_hits(hits)
    hits = _filter_redundant_overlaps(hits)
    return _sort_terminators_biologically(hits)


def find_rho_independent_terminators(
    sequence: str,
    stem_min: int = 5,
    stem_max: int = 10,
    loop_min: int = 3,
    loop_max: int = 7,
    max_stem_mismatches: int = 1,
    min_poly_t: int = 5,
    gc_threshold: float = 0.7,
) -> List[TerminatorHit]:
    seq = _clean_sequence(sequence)
    if not seq or not _contains_only_dna(seq):
        return []

    plus_hits = find_rho_independent_terminators_in_strand(
        sequence=seq,
        strand="+",
        stem_min=stem_min,
        stem_max=stem_max,
        loop_min=loop_min,
        loop_max=loop_max,
        max_stem_mismatches=max_stem_mismatches,
        min_poly_t=min_poly_t,
        gc_threshold=gc_threshold,
        already_clean=True,
    )

    minus_hits = find_rho_independent_terminators_in_strand(
        sequence=seq,
        strand="-",
        stem_min=stem_min,
        stem_max=stem_max,
        loop_min=loop_min,
        loop_max=loop_max,
        max_stem_mismatches=max_stem_mismatches,
        min_poly_t=min_poly_t,
        gc_threshold=gc_threshold,
        already_clean=True,
    )

    return _sort_terminators_biologically(plus_hits + minus_hits)


def terminator_to_dict(t: TerminatorHit) -> dict:
    return asdict(t)


def format_terminators(terminators: List[TerminatorHit]) -> str:
    if not terminators:
        return "No rho-independent terminator-like structure found."

    lines = [f"Detected {len(terminators)} terminator-like region(s):", ""]

    for idx, t in enumerate(terminators, start=1):
        lines.extend(
            [
                f"Terminator {idx}",
                f"  Strand:       {t.strand}",
                f"  Left stem:    {t.stem_left_seq} at {t.stem_left_start}..{t.stem_left_end}",
                f"  Loop:         {t.loop_seq}",
                f"  Right stem:   {t.stem_right_seq} at {t.stem_right_start}..{t.stem_right_end}",
                f"  Poly-T:       {t.poly_t_seq} at {t.poly_t_start}..{t.poly_t_end}",
                f"  Stem length:  {t.stem_length}",
                f"  Loop length:  {t.loop_length}",
                f"  Mismatches:   {t.mismatches}",
                f"  GC fraction:  {t.gc_fraction}",
                f"  Poly-T len:   {t.poly_t_length}",
                f"  Score:        {t.score}",
                "",
            ]
        )

    return "\n".join(lines)
