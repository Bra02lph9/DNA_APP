from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple

from .utils import reverse_complement
from .numba_helpers import hamming_distance_numba, at_fraction_numba


BOX_35 = "TTGACA"
BOX_10 = "TATAAT"
VALID_DNA = {"A", "T", "C", "G", "N"}
MOTIF_LEN = 6


@dataclass
class PromoterHit:
    strand: str
    box35_start: int
    box35_end: int
    box35_seq: str
    box35_mismatches: int
    box10_start: int
    box10_end: int
    box10_seq: str
    box10_mismatches: int
    spacing: int
    spacer_seq: str
    spacer_at_fraction: float
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


def _map_rev_to_forward(
    rev_start_0: int,
    rev_end_0_exclusive: int,
    original_len: int,
) -> tuple[int, int]:
    forward_start_0 = original_len - rev_end_0_exclusive
    forward_end_0_exclusive = original_len - rev_start_0
    return forward_start_0 + 1, forward_end_0_exclusive


def _at_fraction(sequence: str) -> float:
    if not sequence:
        return 0.0
    return at_fraction_numba(sequence)


def _spacing_penalty(spacing: int, optimal: int = 17) -> float:
    return abs(spacing - optimal) * 1.5


def _score_promoter(
    box35_mismatches: int,
    box10_mismatches: int,
    spacing: int,
    spacer_at_fraction: float,
) -> float:
    score = 30.0
    score -= box35_mismatches * 5.0
    score -= box10_mismatches * 6.0
    score -= _spacing_penalty(spacing, optimal=17)
    score += spacer_at_fraction * 4.0
    return round(score, 3)


def _deduplicate_hits(hits: List[PromoterHit]) -> List[PromoterHit]:
    best_by_key: Dict[Tuple, PromoterHit] = {}

    for hit in hits:
        key = (
            hit.strand,
            hit.box35_start,
            hit.box35_end,
            hit.box10_start,
            hit.box10_end,
        )
        current = best_by_key.get(key)
        if current is None or hit.score > current.score:
            best_by_key[key] = hit

    return list(best_by_key.values())


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return not (a_end < b_start or b_end < a_start)


def _filter_redundant_hits(hits: List[PromoterHit]) -> List[PromoterHit]:
    sorted_hits = sorted(hits, key=lambda h: (-h.score, h.strand, h.box35_start))
    kept: List[PromoterHit] = []

    for hit in sorted_hits:
        hit_start = min(hit.box35_start, hit.box10_start)
        hit_end = max(hit.box35_end, hit.box10_end)

        redundant = False
        for prev in kept:
            if hit.strand != prev.strand:
                continue

            prev_start = min(prev.box35_start, prev.box10_start)
            prev_end = max(prev.box35_end, prev.box10_end)

            if _overlap(hit_start, hit_end, prev_start, prev_end):
                redundant = True
                break

        if not redundant:
            kept.append(hit)

    return kept


def _sort_promoters_biologically(hits: List[PromoterHit]) -> List[PromoterHit]:
    return sorted(
        hits,
        key=lambda h: (
            -h.score,
            h.box10_mismatches,
            h.box35_mismatches,
            abs(h.spacing - 17),
            0 if h.strand == "+" else 1,
            min(h.box35_start, h.box10_start),
        ),
    )


def _build_promoter_hit(
    strand: str,
    original_len: int,
    i35: int,
    seq35: str,
    mm35: int,
    i10: int,
    seq10: str,
    mm10: int,
    spacing: int,
    search_seq: str,
) -> PromoterHit:
    end35 = i35 + MOTIF_LEN
    spacer_seq = search_seq[end35:i10]
    spacer_at_fraction = _at_fraction(spacer_seq)
    score = _score_promoter(
        box35_mismatches=mm35,
        box10_mismatches=mm10,
        spacing=spacing,
        spacer_at_fraction=spacer_at_fraction,
    )

    if strand == "+":
        box35_start = i35 + 1
        box35_end = i35 + MOTIF_LEN
        box10_start = i10 + 1
        box10_end = i10 + MOTIF_LEN
    else:
        box35_start, box35_end = _map_rev_to_forward(
            i35, i35 + MOTIF_LEN, original_len
        )
        box10_start, box10_end = _map_rev_to_forward(
            i10, i10 + MOTIF_LEN, original_len
        )

    return PromoterHit(
        strand=strand,
        box35_start=box35_start,
        box35_end=box35_end,
        box35_seq=seq35,
        box35_mismatches=mm35,
        box10_start=box10_start,
        box10_end=box10_end,
        box10_seq=seq10,
        box10_mismatches=mm10,
        spacing=spacing,
        spacer_seq=spacer_seq,
        spacer_at_fraction=round(spacer_at_fraction, 3),
        score=score,
    )


def find_promoters_in_strand(
    sequence: str,
    strand: str = "+",
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
) -> List[PromoterHit]:
    seq = _clean_sequence(sequence)
    if not seq or not _contains_only_dna(seq):
        return []

    search_seq = seq if strand == "+" else reverse_complement(seq)
    original_len = len(seq)
    seq_len = len(search_seq)

    if seq_len < (2 * MOTIF_LEN + spacing_min):
        return []

    hits: List[PromoterHit] = []

    last_box35_start = seq_len - MOTIF_LEN
    last_box10_start = seq_len - MOTIF_LEN

    for i35 in range(last_box35_start + 1):
        seq35 = search_seq[i35:i35 + MOTIF_LEN]

        if "N" in seq35:
            continue

        mm35 = hamming_distance_numba(seq35, BOX_35)
        if mm35 > max_mismatches_box35:
            continue

        end35 = i35 + MOTIF_LEN

        for spacing in range(spacing_min, spacing_max + 1):
            i10 = end35 + spacing

            if i10 > last_box10_start:
                continue

            seq10 = search_seq[i10:i10 + MOTIF_LEN]

            if "N" in seq10:
                continue

            mm10 = hamming_distance_numba(seq10, BOX_10)
            if mm10 > max_mismatches_box10:
                continue

            hit = _build_promoter_hit(
                strand=strand,
                original_len=original_len,
                i35=i35,
                seq35=seq35,
                mm35=mm35,
                i10=i10,
                seq10=seq10,
                mm10=mm10,
                spacing=spacing,
                search_seq=search_seq,
            )
            hits.append(hit)

    hits = _deduplicate_hits(hits)
    hits = _filter_redundant_hits(hits)
    return _sort_promoters_biologically(hits)


def find_promoters(
    sequence: str,
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
) -> List[PromoterHit]:
    hits_plus = find_promoters_in_strand(
        sequence=sequence,
        strand="+",
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
    )

    hits_minus = find_promoters_in_strand(
        sequence=sequence,
        strand="-",
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
    )

    return _sort_promoters_biologically(hits_plus + hits_minus)


def promoter_to_dict(p: PromoterHit) -> dict:
    return asdict(p)


def format_promoters(promoters: List[PromoterHit]) -> str:
    if not promoters:
        return "No sigma70-like promoter region found."

    lines = [f"Detected {len(promoters)} promoter-like region(s):", ""]

    for idx, p in enumerate(promoters, start=1):
        lines.extend(
            [
                f"Promoter {idx}",
                f"  Strand: {p.strand}",
                f"  -35 box: {p.box35_seq} at {p.box35_start}..{p.box35_end} (mismatches={p.box35_mismatches})",
                f"  -10 box: {p.box10_seq} at {p.box10_start}..{p.box10_end} (mismatches={p.box10_mismatches})",
                f"  Spacing: {p.spacing} nt",
                f"  Spacer sequence: {p.spacer_seq}",
                f"  Spacer AT fraction: {p.spacer_at_fraction}",
                f"  Score: {p.score}",
                "",
            ]
        )

    return "\n".join(lines)
