from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple

from .utils import hamming_distance, reverse_complement


SD_CONSENSUS = "AGGAGG"
START_CODONS = {"ATG", "GTG", "TTG"}
VALID_DNA = {"A", "T", "C", "G", "N"}


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
    for i in range(0, len(search_seq) - 2):
        codon = search_seq[i:i + 3]
        if codon in START_CODONS:
            starts.append((i, codon))
    return starts


def _link_best_start_for_site(
    site_start_0: int,
    site_end_0_exclusive: int,
    starts: List[Tuple[int, str]],
) -> tuple[Optional[int], Optional[str], Optional[int]]:
    candidates = []

    for start_pos_0, codon in starts:
        distance = start_pos_0 - site_end_0_exclusive
        if 4 <= distance <= 12:
            candidates.append((start_pos_0, codon, distance))

    if not candidates:
        return None, None, None

    candidates.sort(
        key=lambda x: (
            abs(x[2] - 7),
            _start_codon_priority(x[1]),
            x[0],
        )
    )

    best_start_0, best_codon, best_distance = candidates[0]
    return best_start_0, best_codon, best_distance


def _deduplicate_sites(sites: List[ShineDalgarnoSite]) -> List[ShineDalgarnoSite]:
    best_by_key: Dict[Tuple, ShineDalgarnoSite] = {}

    for site in sites:
        key = (site.strand, site.start, site.end, site.linked_start_position)
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

    hits: List[ShineDalgarnoSite] = []
    motif_len = len(SD_CONSENSUS)

    start_codons = _find_start_codons(search_seq)

    for i in range(0, len(search_seq) - motif_len + 1):
        window = search_seq[i:i + motif_len]
        if "N" in window:
            continue

        mm = hamming_distance(window, SD_CONSENSUS)
        if mm > max_mismatches:
            continue

        site_start_0 = i
        site_end_0_exclusive = i + motif_len

        linked_start_0, linked_codon, distance = _link_best_start_for_site(
            site_start_0,
            site_end_0_exclusive,
            start_codons,
        )

        score = _calculate_sd_score(
            mismatches=mm,
            distance_to_start=distance,
            start_codon=linked_codon,
        )

        if strand == "+":
            start = site_start_0 + 1
            end = site_end_0_exclusive
            linked_start_position = linked_start_0 + 1 if linked_start_0 is not None else None
        else:
            start, end = _map_rev_to_forward(
                site_start_0,
                site_end_0_exclusive,
                original_len,
            )
            if linked_start_0 is not None:
                linked_start_position, _linked_end = _map_rev_to_forward(
                    linked_start_0,
                    linked_start_0 + 3,
                    original_len,
                )
            else:
                linked_start_position = None

        hits.append(
            ShineDalgarnoSite(
                strand=strand,
                start=start,
                end=end,
                sequence=window,
                mismatches=mm,
                linked_start_codon=linked_codon,
                linked_start_position=linked_start_position,
                distance_to_start=distance,
                score=score,
            )
        )

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
