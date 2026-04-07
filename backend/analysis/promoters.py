from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import List, Dict, Tuple

from .utils import reverse_complement
from .numba_helpers import hamming_distance_numba

try:
    from ._promoters_cy import scan_promoter_positions_cy
except Exception as e:
    print("IMPORT ERROR _promoters_cy:", repr(e))
    scan_promoter_positions_cy = None


BOX_35 = "TTGACA"
BOX_10 = "TATAAT"
MOTIF_LEN = 6

RawHit = tuple[int, int, int, int, int, float, float]


@dataclass(slots=True)
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
    return "".join(sequence.split()).upper()


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

    at_count = 0
    for ch in sequence:
        if ch == "A" or ch == "T":
            at_count += 1

    return at_count / len(sequence)


def _score_promoter(
    box35_mismatches: int,
    box10_mismatches: int,
    spacing: int,
    spacer_at_fraction: float,
) -> float:
    score = 30.0
    score -= box35_mismatches * 5.0
    score -= box10_mismatches * 6.0
    score -= abs(spacing - 17) * 1.5
    score += spacer_at_fraction * 4.0
    return round(score, 3)


def _raw_interval(raw_hit: RawHit, strand: str, original_len: int) -> tuple[int, int]:
    i35, _, i10, _, _, _, _ = raw_hit

    if strand == "+":
        box35_start = i35 + 1
        box35_end = i35 + MOTIF_LEN
        box10_start = i10 + 1
        box10_end = i10 + MOTIF_LEN
    else:
        box35_start, box35_end = _map_rev_to_forward(i35, i35 + MOTIF_LEN, original_len)
        box10_start, box10_end = _map_rev_to_forward(i10, i10 + MOTIF_LEN, original_len)

    return min(box35_start, box10_start), max(box35_end, box10_end)


def _deduplicate_raw_hits(raw_hits: List[RawHit], strand: str, original_len: int) -> List[RawHit]:
    best_by_key: Dict[Tuple, RawHit] = {}

    for hit in raw_hits:
        i35, mm35, i10, mm10, spacing, spacer_at_fraction, score = hit

        if strand == "+":
            box35_start = i35 + 1
            box35_end = i35 + MOTIF_LEN
            box10_start = i10 + 1
            box10_end = i10 + MOTIF_LEN
        else:
            box35_start, box35_end = _map_rev_to_forward(i35, i35 + MOTIF_LEN, original_len)
            box10_start, box10_end = _map_rev_to_forward(i10, i10 + MOTIF_LEN, original_len)

        key = (
            strand,
            box35_start,
            box35_end,
            box10_start,
            box10_end,
        )

        current = best_by_key.get(key)
        if current is None or score > current[6]:
            best_by_key[key] = hit

    return list(best_by_key.values())


def _has_overlap_sorted(
    starts: List[int],
    intervals: List[tuple[int, int]],
    start: int,
    end: int,
) -> bool:
    if not intervals:
        return False

    i = bisect_left(starts, start)

    j = i - 1
    while j >= 0 and intervals[j][1] >= start:
        if intervals[j][0] <= end:
            return True
        j -= 1

    k = i
    n = len(intervals)
    while k < n and intervals[k][0] <= end:
        if intervals[k][1] >= start:
            return True
        k += 1

    return False


def _insert_interval_sorted(
    starts: List[int],
    intervals: List[tuple[int, int]],
    start: int,
    end: int,
) -> None:
    idx = bisect_left(starts, start)
    starts.insert(idx, start)
    intervals.insert(idx, (start, end))


def _filter_redundant_raw_hits(
    raw_hits: List[RawHit],
    strand: str,
    original_len: int,
) -> List[RawHit]:
    sorted_hits = sorted(
        raw_hits,
        key=lambda h: (-h[6], h[3], h[1], abs(h[4] - 17), h[0]),
    )

    kept: List[RawHit] = []
    starts: List[int] = []
    intervals: List[tuple[int, int]] = []

    append_kept = kept.append

    for hit in sorted_hits:
        hit_start, hit_end = _raw_interval(hit, strand, original_len)

        redundant = _has_overlap_sorted(starts, intervals, hit_start, hit_end)
        if not redundant:
            append_kept(hit)
            _insert_interval_sorted(starts, intervals, hit_start, hit_end)

    return kept


def _sort_raw_hits_biologically(raw_hits: List[RawHit]) -> List[RawHit]:
    return sorted(
        raw_hits,
        key=lambda h: (
            -h[6],              # score
            h[3],               # box10 mismatches
            h[1],               # box35 mismatches
            abs(h[4] - 17),     # spacing distance
            h[0],               # i35
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
    spacer_at_fraction: float,
    score: float,
) -> PromoterHit:
    end35 = i35 + MOTIF_LEN
    spacer_seq = search_seq[end35:i10]

    if strand == "+":
        box35_start = i35 + 1
        box35_end = i35 + MOTIF_LEN
        box10_start = i10 + 1
        box10_end = i10 + MOTIF_LEN
    else:
        box35_start, box35_end = _map_rev_to_forward(i35, i35 + MOTIF_LEN, original_len)
        box10_start, box10_end = _map_rev_to_forward(i10, i10 + MOTIF_LEN, original_len)

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
        spacer_at_fraction=spacer_at_fraction,
        score=score,
    )


def _scan_promoter_positions_python(
    search_seq: str,
    max_mismatches_box35: int,
    max_mismatches_box10: int,
    spacing_min: int,
    spacing_max: int,
) -> List[RawHit]:
    seq_len = len(search_seq)
    hits_raw: List[RawHit] = []

    motif_len = MOTIF_LEN
    box35_motif = BOX_35
    box10_motif = BOX_10
    hamming = hamming_distance_numba
    append_hit = hits_raw.append

    last_box35_start = seq_len - motif_len
    last_box10_start = seq_len - motif_len

    for i35 in range(last_box35_start + 1):
        seq35 = search_seq[i35:i35 + motif_len]

        if "N" in seq35:
            continue

        mm35 = hamming(seq35, box35_motif)
        if mm35 > max_mismatches_box35:
            continue

        end35 = i35 + motif_len

        for spacing in range(spacing_min, spacing_max + 1):
            i10 = end35 + spacing
            if i10 > last_box10_start:
                break

            seq10 = search_seq[i10:i10 + motif_len]
            if "N" in seq10:
                continue

            mm10 = hamming(seq10, box10_motif)
            if mm10 > max_mismatches_box10:
                continue

            spacer_seq = search_seq[end35:i10]
            spacer_at_fraction = _at_fraction(spacer_seq)
            score = _score_promoter(mm35, mm10, spacing, spacer_at_fraction)

            append_hit((i35, mm35, i10, mm10, spacing, spacer_at_fraction, score))

    return hits_raw


def _scan_promoter_positions(
    search_seq: str,
    max_mismatches_box35: int,
    max_mismatches_box10: int,
    spacing_min: int,
    spacing_max: int,
):
    use_cython = (
        scan_promoter_positions_cy is not None
        and spacing_min <= spacing_max
    )

    print("scan_promoter_positions_cy:", scan_promoter_positions_cy)
    print("use_cython:", use_cython)

    if use_cython:
        return scan_promoter_positions_cy(
            search_seq.encode("ascii"),
            max_mismatches_box35,
            max_mismatches_box10,
            spacing_min,
            spacing_max,
        )

    return _scan_promoter_positions_python(
        search_seq=search_seq,
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
    )

def find_promoters_in_strand(
    sequence: str,
    strand: str = "+",
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
    already_clean: bool = False,
) -> List[PromoterHit]:
    seq = sequence if already_clean else _clean_sequence(sequence)
    if not seq:
        return []

    search_seq = seq if strand == "+" else reverse_complement(seq)
    original_len = len(seq)

    if len(search_seq) < (2 * MOTIF_LEN + spacing_min):
        return []

    raw_hits = _scan_promoter_positions(
        search_seq=search_seq,
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
    )

    if not raw_hits:
        return []

    raw_hits = _deduplicate_raw_hits(raw_hits, strand, original_len)
    raw_hits = _filter_redundant_raw_hits(raw_hits, strand, original_len)
    raw_hits = _sort_raw_hits_biologically(raw_hits)

    hits: List[PromoterHit] = []
    append_hit = hits.append
    motif_len = MOTIF_LEN

    for i35, mm35, i10, mm10, spacing, spacer_at_fraction, score in raw_hits:
        append_hit(
            _build_promoter_hit(
                strand=strand,
                original_len=original_len,
                i35=i35,
                seq35=search_seq[i35:i35 + motif_len],
                mm35=mm35,
                i10=i10,
                seq10=search_seq[i10:i10 + motif_len],
                mm10=mm10,
                spacing=spacing,
                search_seq=search_seq,
                spacer_at_fraction=spacer_at_fraction,
                score=score,
            )
        )

    return hits


def find_promoters(
    sequence: str,
    max_mismatches_box35: int = 2,
    max_mismatches_box10: int = 2,
    spacing_min: int = 16,
    spacing_max: int = 19,
    already_clean: bool = False,
) -> List[PromoterHit]:
    seq = sequence if already_clean else _clean_sequence(sequence)
    if not seq:
        return []

    hits_plus = find_promoters_in_strand(
        sequence=seq,
        strand="+",
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
        already_clean=True,
    )

    hits_minus = find_promoters_in_strand(
        sequence=seq,
        strand="-",
        max_mismatches_box35=max_mismatches_box35,
        max_mismatches_box10=max_mismatches_box10,
        spacing_min=spacing_min,
        spacing_max=spacing_max,
        already_clean=True,
    )

    if not hits_plus:
        return hits_minus
    if not hits_minus:
        return hits_plus

    return sorted(
        hits_plus + hits_minus,
        key=lambda h: (
            -h.score,
            h.box10_mismatches,
            h.box35_mismatches,
            abs(h.spacing - 17),
            0 if h.strand == "+" else 1,
            min(h.box35_start, h.box10_start),
        ),
    )


def promoter_to_dict(p: PromoterHit) -> dict:
    return {
        "strand": p.strand,
        "box35_start": p.box35_start,
        "box35_end": p.box35_end,
        "box35_seq": p.box35_seq,
        "box35_mismatches": p.box35_mismatches,
        "box10_start": p.box10_start,
        "box10_end": p.box10_end,
        "box10_seq": p.box10_seq,
        "box10_mismatches": p.box10_mismatches,
        "spacing": p.spacing,
        "spacer_seq": p.spacer_seq,
        "spacer_at_fraction": p.spacer_at_fraction,
        "score": p.score,
    }


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
