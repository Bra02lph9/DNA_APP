from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Any

from .promoters import PromoterHit
from .shine_dalgarno import ShineDalgarnoSite
from .terminators import TerminatorHit


DEFAULT_CHUNK_SIZE = 50_000
DEFAULT_OVERLAP = 1_000


def chunk_sequence(
    sequence: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Découpe une séquence ADN en chunks avec overlap.
    Coordonnées retournées en 1-based inclusives.
    """
    seq = sequence.upper().strip()

    if not seq:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size doit être > 0")

    if overlap < 0:
        raise ValueError("overlap doit être >= 0")

    if overlap >= chunk_size:
        raise ValueError("overlap doit être strictement inférieur à chunk_size")

    n = len(seq)
    step = chunk_size - overlap
    chunks: List[Dict[str, Any]] = []

    chunk_id = 0
    global_start = 1

    while global_start <= n:
        global_end = min(global_start + chunk_size - 1, n)
        chunk_seq = seq[global_start - 1:global_end]

        chunks.append(
            {
                "chunk_id": chunk_id,
                "start": global_start,   # 1-based inclusive
                "end": global_end,       # 1-based inclusive
                "sequence": chunk_seq,
            }
        )

        if global_end == n:
            break

        global_start += step
        chunk_id += 1

    return chunks


def remap_promoter_hit(hit: PromoterHit, chunk_global_start: int) -> PromoterHit:
    return PromoterHit(
        strand=hit.strand,
        box35_start=hit.box35_start + chunk_global_start - 1,
        box35_end=hit.box35_end + chunk_global_start - 1,
        box35_seq=hit.box35_seq,
        box35_mismatches=hit.box35_mismatches,
        box10_start=hit.box10_start + chunk_global_start - 1,
        box10_end=hit.box10_end + chunk_global_start - 1,
        box10_seq=hit.box10_seq,
        box10_mismatches=hit.box10_mismatches,
        spacing=hit.spacing,
        spacer_seq=hit.spacer_seq,
        spacer_at_fraction=hit.spacer_at_fraction,
        score=hit.score,
    )


def remap_sd_site(site: ShineDalgarnoSite, chunk_global_start: int) -> ShineDalgarnoSite:
    return ShineDalgarnoSite(
        strand=site.strand,
        start=site.start + chunk_global_start - 1,
        end=site.end + chunk_global_start - 1,
        sequence=site.sequence,
        mismatches=site.mismatches,
        linked_start_codon=site.linked_start_codon,
        linked_start_position=(
            site.linked_start_position + chunk_global_start - 1
            if site.linked_start_position is not None
            else None
        ),
        distance_to_start=site.distance_to_start,
        score=site.score,
    )


def remap_terminator_hit(hit: TerminatorHit, chunk_global_start: int) -> TerminatorHit:
    return TerminatorHit(
        strand=hit.strand,
        stem_left_start=hit.stem_left_start + chunk_global_start - 1,
        stem_left_end=hit.stem_left_end + chunk_global_start - 1,
        stem_left_seq=hit.stem_left_seq,
        loop_seq=hit.loop_seq,
        stem_right_start=hit.stem_right_start + chunk_global_start - 1,
        stem_right_end=hit.stem_right_end + chunk_global_start - 1,
        stem_right_seq=hit.stem_right_seq,
        poly_t_start=hit.poly_t_start + chunk_global_start - 1,
        poly_t_end=hit.poly_t_end + chunk_global_start - 1,
        poly_t_seq=hit.poly_t_seq,
        stem_length=hit.stem_length,
        loop_length=hit.loop_length,
        mismatches=hit.mismatches,
        gc_fraction=hit.gc_fraction,
        poly_t_length=hit.poly_t_length,
        score=hit.score,
    )


def deduplicate_promoters(promoters: List[PromoterHit]) -> List[PromoterHit]:
    best_by_key: Dict[tuple, PromoterHit] = {}

    for hit in promoters:
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

    return sorted(
        best_by_key.values(),
        key=lambda p: (
            0 if p.strand == "+" else 1,
            min(p.box35_start, p.box10_start),
            max(p.box35_end, p.box10_end),
            -p.score,
        ),
    )


def deduplicate_sd_sites(sd_sites: List[ShineDalgarnoSite]) -> List[ShineDalgarnoSite]:
    best_by_key: Dict[tuple, ShineDalgarnoSite] = {}

    for site in sd_sites:
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

    return sorted(
        best_by_key.values(),
        key=lambda s: (
            0 if s.strand == "+" else 1,
            s.start,
            s.end,
            -s.score,
        ),
    )


def deduplicate_terminators(terminators: List[TerminatorHit]) -> List[TerminatorHit]:
    best_by_key: Dict[tuple, TerminatorHit] = {}

    for hit in terminators:
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

    return sorted(
        best_by_key.values(),
        key=lambda t: (
            0 if t.strand == "+" else 1,
            min(t.stem_left_start, t.stem_right_start, t.poly_t_start),
            max(t.stem_left_end, t.stem_right_end, t.poly_t_end),
            -t.score,
        ),
    )


def serialize_promoters(promoters: List[PromoterHit]) -> List[dict]:
    return [asdict(x) for x in promoters]


def serialize_sd_sites(sd_sites: List[ShineDalgarnoSite]) -> List[dict]:
    return [asdict(x) for x in sd_sites]


def serialize_terminators(terminators: List[TerminatorHit]) -> List[dict]:
    return [asdict(x) for x in terminators]


def promoter_from_dict(data: dict) -> PromoterHit:
    return PromoterHit(**data)


def sd_site_from_dict(data: dict) -> ShineDalgarnoSite:
    return ShineDalgarnoSite(**data)


def terminator_from_dict(data: dict) -> TerminatorHit:
    return TerminatorHit(**data)


def promoters_from_dicts(items: List[dict]) -> List[PromoterHit]:
    return [promoter_from_dict(x) for x in items]


def sd_sites_from_dicts(items: List[dict]) -> List[ShineDalgarnoSite]:
    return [sd_site_from_dict(x) for x in items]


def terminators_from_dicts(items: List[dict]) -> List[TerminatorHit]:
    return [terminator_from_dict(x) for x in items]
