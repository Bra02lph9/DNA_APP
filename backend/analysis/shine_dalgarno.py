from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple

from .utils import reverse_complement
from .numba_helpers import hamming_distance_numba


SD_CONSENSUS = "AGGAGG"
START_CODONS = {"ATG", "GTG", "TTG"}
VALID_DNA = {"A", "T", "C", "G", "N"}

MIN_SD_DISTANCE = 4
MAX_SD_DISTANCE = 12
SD_LEN = len(SD_CONSENSUS)


@dataclass
class ShineDalgarnoSite:
    strand: str
    start: int
    end: int
    sequence: str
    mismatches: int
    linked_start_codon: Optional[str] = None
    linked_start_position: Optional[int] = None
    distance_to_start: Optional[int] = None
    score: float = 0.0


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


def _start_codon_priority(codon: str) -> int:
    if codon == "ATG":
        return 0
    if codon == "GTG":
        return 1
    if codon == "TTG":
        return 2
    return 3


def _distance_score(distance: int) -> float:
    ideal = 7
    return max(0.0, 10.0 - abs(distance - ideal) * 2.0)


def _codon_score(codon: str) -> float:
    if codon == "ATG":
        return 5.0
    if codon == "GTG":
        return 3.0
    if codon == "TTG":
        return 2.0
    return 0.0


def _calculate_sd_score(
    mismatches: int,
    distance_to_start: Optional[int],
    start_codon: Optional[str],
) -> float:
    score = 20.0
    score -= mismatches * 4.0

    if distance_to_start is not None:
        score += _distance_score(distance_to_start)

    if start_codon is not None:
        score += _codon_score(start_codon)

    return round(score, 3)


def _find_start_codons(search_seq: str) -> List[Tuple[int, str]]:
    starts: List[Tuple[int, str]] = []
    seq_len = len(search_seq)

    for i in range(seq_len - 2):
        codon = search_seq[i:i + 3]
        if codon in START_CODONS:
            starts.append((i, codon))

    return starts


def _evaluate_sd_window(
    search_seq: str,
    site_start_0: int,
    start_codon: str,
    distance: int,
    max_mismatches: int,
) -> Optional[Tuple[int, int, str, int, int, float]]:
    site_end_0_exclusive = site_start_0 + SD_LEN

    if site_start_0 < 0:
        return None
    if site_end_0_exclusive > len(search_seq):
        return None

    window = search_seq[site_start_0:site_end_0_exclusive]
    if len(window) != SD_LEN:
        return None
    if "N" in window:
        return None

    mm = hamming_distance_numba(window, SD_CONSENSUS)
    if mm > max_mismatches:
        return None

    score = _calculate_sd_score(
        mismatches=mm,
        distance_to_start=distance,
        start_codon=start_codon,
    )

    return (
        site_start_0,
        site_end_0_exclusive,
        window,
        mm,
        distance,
        score,
    )


def _best_sd_for_start(
    search_seq: str,
    start_pos_0: int,
    start_codon: str,
    max_mismatches: int,
) -> Optional[Tuple[int, int, str, int, int, float]]:
    candidates: List[Tuple[int, int, str, int, int, float]] = []

    for distance in range(MIN_SD_DISTANCE, MAX_SD_DISTANCE + 1):
        site_end_0_exclusive = start_pos_0 - distance
        site_start_0 = site_end_0_exclusive - SD_LEN

        candidate = _evaluate_sd_window(
            search_seq=search_seq,
            site_start_0=site_start_0,
            start_codon=start_codon,
            distance=distance,
            max_mismatches=max_mismatches,
        )

        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            -x[5],
            x[3],
            abs(x[4] - 7),
            x[0],
        )
    )
    return candidates[0]


def _build_sd_hit(
    strand: str,
    original_len: int,
    site_start_0: int,
    site_end_0_exclusive: int,
    window: str,
    mismatches: int,
    start_pos_0: int,
    start_codon: str,
    distance: int,
    score: float,
) -> ShineDalgarnoSite:
    if strand == "+":
        start = site_start_0 + 1
        end = site_end_0_exclusive
        linked_start_position = start_pos_0 + 1
    else:
        start, end = _map_rev_to_forward(
            site_start_0,
            site_end_0_exclusive,
            original_len,
        )
        linked_start_position, _ = _map_rev_to_forward(
            start_pos_0,
            start_pos_0 + 3,
            original_len,
        )

    return ShineDalgarnoSite(
        strand=strand,
        start=start,
        end=end,
        sequence=window,
        mismatches=mismatches,
        linked_start_codon=start_codon,
        linked_start_position=linked_start_position,
        distance_to_start=distance,
        score=score,
    )


def _deduplicate_sites(sites: List[ShineDalgarnoSite]) -> List[ShineDalgarnoSite]:
    best_by_key: Dict[Tuple, ShineDalgarnoSite] = {}

    for site in sites:
        key = (
            site.strand,
            site.start,
            site.end,
            site.linked_start_position,
            site.linked_start_codon,
        )
        current = best_by_key.get(key)
        if current is None or site.score > current.score:
            best_by_key[key] = site

    return list(best_by_key.values())


def _sort_sites_biologically(sites: List[ShineDalgarnoSite]) -> List[ShineDalgarnoSite]:
    return sorted(
        sites,
        key=lambda s: (
            -s.score,
            s.mismatches,
            abs((s.distance_to_start or 999) - 7),
            _start_codon_priority(s.linked_start_codon or ""),
            0 if s.strand == "+" else 1,
            s.start,
        ),
    )


def find_shine_dalgarno_sites_in_strand(
    sequence: str,
    strand: str = "+",
    max_mismatches: int = 2,
) -> List[ShineDalgarnoSite]:
    seq = _clean_sequence(sequence)
    if not seq or not _contains_only_dna(seq):
        return []

    search_seq = seq if strand == "+" else reverse_complement(seq)
    original_len = len(seq)

    if len(search_seq) < SD_LEN + MIN_SD_DISTANCE + 3:
        return []

    hits: List[ShineDalgarnoSite] = []
    start_codons = _find_start_codons(search_seq)

    for start_pos_0, start_codon in start_codons:
        best_sd = _best_sd_for_start(
            search_seq=search_seq,
            start_pos_0=start_pos_0,
            start_codon=start_codon,
            max_mismatches=max_mismatches,
        )

        if best_sd is None:
            continue

        site_start_0, site_end_0_exclusive, window, mm, distance, score = best_sd

        hit = _build_sd_hit(
            strand=strand,
            original_len=original_len,
            site_start_0=site_start_0,
            site_end_0_exclusive=site_end_0_exclusive,
            window=window,
            mismatches=mm,
            start_pos_0=start_pos_0,
            start_codon=start_codon,
            distance=distance,
            score=score,
        )
        hits.append(hit)

    hits = _deduplicate_sites(hits)
    return _sort_sites_biologically(hits)


def find_shine_dalgarno_sites(
    sequence: str,
    max_mismatches: int = 2,
) -> List[ShineDalgarnoSite]:
    seq = _clean_sequence(sequence)
    if not seq or not _contains_only_dna(seq):
        return []

    plus_hits = find_shine_dalgarno_sites_in_strand(
        sequence=seq,
        strand="+",
        max_mismatches=max_mismatches,
    )

    minus_hits = find_shine_dalgarno_sites_in_strand(
        sequence=seq,
        strand="-",
        max_mismatches=max_mismatches,
    )

    return _sort_sites_biologically(plus_hits + minus_hits)


def shine_dalgarno_to_dict(site: ShineDalgarnoSite) -> dict:
    return asdict(site)


def format_shine_dalgarno_sites(sites: List[ShineDalgarnoSite]) -> str:
    if not sites:
        return "No Shine-Dalgarno-like site found."

    lines = [f"Detected {len(sites)} Shine-Dalgarno-like site(s):", ""]

    for idx, site in enumerate(sites, start=1):
        relation = (
            f"linked to {site.linked_start_codon} at position {site.linked_start_position} "
            f"with spacing {site.distance_to_start} nt"
            if site.linked_start_position
            else "no suitable downstream start codon found in expected spacing window"
        )

        lines.extend(
            [
                f"Site {idx}",
                f"  Strand: {site.strand}",
                f"  Positions: {site.start}..{site.end}",
                f"  Sequence: {site.sequence}",
                f"  Mismatches vs consensus {SD_CONSENSUS}: {site.mismatches}",
                f"  Context: {relation}",
                f"  Score: {site.score}",
                "",
            ]
        )

    return "\n".join(lines)
