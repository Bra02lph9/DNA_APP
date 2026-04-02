from __future__ import annotations

from typing import List, Optional, Dict, Any

from .coding_orfs import (
    find_coding_orfs,
    coding_orf_to_dict,
    CodingORF,
)
from .promoters import (
    find_promoters,
    promoter_to_dict,
    PromoterHit,
)
from .shine_dalgarno import (
    find_shine_dalgarno_sites,
    shine_dalgarno_to_dict,
    ShineDalgarnoSite,
)
from .terminators import (
    find_rho_independent_terminators,
    terminator_to_dict,
    TerminatorHit,
)


def score_orf_length(peptide_length_aa: int) -> float:
    if peptide_length_aa >= 300:
        return 35.0
    if peptide_length_aa >= 200:
        return 28.0
    if peptide_length_aa >= 120:
        return 20.0
    if peptide_length_aa >= 80:
        return 14.0
    if peptide_length_aa >= 50:
        return 8.0
    return 3.0


def score_start_codon(start_codon: str) -> float:
    if start_codon == "ATG":
        return 10.0
    if start_codon == "GTG":
        return 7.0
    if start_codon == "TTG":
        return 5.0
    return 0.0


def score_sd(site: Optional[ShineDalgarnoSite]) -> float:
    if site is None:
        return 0.0

    base = float(site.score)

    if site.distance_to_start is not None:
        if 6 <= site.distance_to_start <= 9:
            base += 3.0
        elif 4 <= site.distance_to_start <= 12:
            base += 1.0

    return round(min(base, 35.0), 3)


def _promoter_distance_to_orf(hit: PromoterHit, orf: CodingORF) -> Optional[int]:
    if hit.strand != orf.strand:
        return None

    if orf.strand == "+":
        if hit.box10_end < orf.start:
            return orf.start - hit.box10_end
        return None

    if hit.box10_start > orf.end:
        return hit.box10_start - orf.end
    return None


def score_promoter(hit: Optional[PromoterHit], orf: CodingORF) -> float:
    if hit is None:
        return 0.0

    base = float(hit.score)
    upstream_distance = _promoter_distance_to_orf(hit, orf)

    if upstream_distance is None:
        return round(min(base, 40.0), 3)

    if 1 <= upstream_distance <= 80:
        base += 6.0
    elif 81 <= upstream_distance <= 150:
        base += 3.0
    elif 151 <= upstream_distance <= 300:
        base += 1.0

    return round(min(base, 40.0), 3)


def _terminator_distance_to_orf(hit: TerminatorHit, orf: CodingORF) -> Optional[int]:
    if hit.strand != orf.strand:
        return None

    if orf.strand == "+":
        if hit.stem_left_start > orf.end:
            return hit.stem_left_start - orf.end
        return None

    if hit.stem_right_end < orf.start:
        return orf.start - hit.stem_right_end
    return None


def score_terminator(hit: Optional[TerminatorHit], orf: CodingORF) -> float:
    if hit is None:
        return 0.0

    base = float(hit.score)
    downstream_distance = _terminator_distance_to_orf(hit, orf)

    if downstream_distance is None:
        return round(min(base, 30.0), 3)

    if 1 <= downstream_distance <= 100:
        base += 5.0
    elif 101 <= downstream_distance <= 250:
        base += 2.0

    return round(min(base, 30.0), 3)


def _group_by_strand(items) -> Dict[str, list]:
    grouped = {"+": [], "-": []}
    for item in items:
        strand = getattr(item, "strand", None)
        if strand in grouped:
            grouped[strand].append(item)
    return grouped


def find_best_sd_for_orf(
    orf: CodingORF,
    sd_sites: List[ShineDalgarnoSite],
) -> Optional[ShineDalgarnoSite]:
    best: Optional[ShineDalgarnoSite] = None
    best_key = None

    for site in sd_sites:
        if site.strand != orf.strand:
            continue
        if site.linked_start_position is None:
            continue
        if site.linked_start_position != orf.start:
            continue

        key = (
            -site.score,
            site.mismatches,
            abs((site.distance_to_start or 999) - 7),
            site.start,
        )

        if best is None or key < best_key:
            best = site
            best_key = key

    return best


def find_best_promoter_for_orf(
    orf: CodingORF,
    promoters: List[PromoterHit],
    max_distance: int = 300,
) -> Optional[PromoterHit]:
    best: Optional[PromoterHit] = None
    best_key = None

    for p in promoters:
        distance = _promoter_distance_to_orf(p, orf)
        if distance is None:
            continue
        if distance > max_distance:
            continue

        key = (distance, -p.score)

        if best is None or key < best_key:
            best = p
            best_key = key

    return best


def find_best_terminator_for_orf(
    orf: CodingORF,
    terminators: List[TerminatorHit],
    max_distance: int = 300,
) -> Optional[TerminatorHit]:
    best: Optional[TerminatorHit] = None
    best_key = None

    for t in terminators:
        distance = _terminator_distance_to_orf(t, orf)
        if distance is None:
            continue
        if distance > max_distance:
            continue

        key = (distance, -t.score)

        if best is None or key < best_key:
            best = t
            best_key = key

    return best


def _build_ranked_orf_entry(
    orf: CodingORF,
    best_sd: Optional[ShineDalgarnoSite],
    best_promoter: Optional[PromoterHit],
    best_terminator: Optional[TerminatorHit],
) -> Dict[str, Any]:
    length_score = score_orf_length(orf.peptide_length_aa)
    start_score = score_start_codon(orf.start_codon)
    sd_score = score_sd(best_sd)
    promoter_score = score_promoter(best_promoter, orf)
    terminator_score = score_terminator(best_terminator, orf)

    total_score = round(
        length_score
        + start_score
        + sd_score
        + promoter_score
        + terminator_score,
        3,
    )

    return {
        "orf": coding_orf_to_dict(orf),
        "total_score": total_score,
        "score_breakdown": {
            "length_score": round(length_score, 3),
            "start_codon_score": round(start_score, 3),
            "shine_dalgarno_score": round(sd_score, 3),
            "promoter_score": round(promoter_score, 3),
            "terminator_score": round(terminator_score, 3),
        },
        "best_promoter": promoter_to_dict(best_promoter) if best_promoter else None,
        "best_shine_dalgarno": shine_dalgarno_to_dict(best_sd) if best_sd else None,
        "best_terminator": terminator_to_dict(best_terminator) if best_terminator else None,
    }


def rank_coding_orfs_from_features(
    coding_orfs: List[CodingORF],
    promoters: List[PromoterHit],
    sd_sites: List[ShineDalgarnoSite],
    terminators: List[TerminatorHit],
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []

    promoters_by_strand = _group_by_strand(promoters)
    sd_by_strand = _group_by_strand(sd_sites)
    terminators_by_strand = _group_by_strand(terminators)

    for orf in coding_orfs:
        strand = orf.strand

        best_sd = find_best_sd_for_orf(orf, sd_by_strand.get(strand, []))
        best_promoter = find_best_promoter_for_orf(
            orf,
            promoters_by_strand.get(strand, []),
            max_distance=max_promoter_distance,
        )
        best_terminator = find_best_terminator_for_orf(
            orf,
            terminators_by_strand.get(strand, []),
            max_distance=max_terminator_distance,
        )

        ranked.append(
            _build_ranked_orf_entry(
                orf=orf,
                best_sd=best_sd,
                best_promoter=best_promoter,
                best_terminator=best_terminator,
            )
        )

    ranked.sort(
        key=lambda x: (
            -x["total_score"],
            -x["score_breakdown"]["shine_dalgarno_score"],
            -x["score_breakdown"]["promoter_score"],
            -x["score_breakdown"]["terminator_score"],
            -x["score_breakdown"]["length_score"],
            0 if x["orf"]["strand"] == "+" else 1,
            x["orf"]["start"],
        )
    )

    return ranked


def rank_coding_orfs(
    sequence: str,
    min_aa: int = 30,
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> List[Dict[str, Any]]:
    coding_orfs = find_coding_orfs(sequence=sequence, min_aa=min_aa)
    promoters = find_promoters(sequence)
    sd_sites = find_shine_dalgarno_sites(sequence)
    terminators = find_rho_independent_terminators(sequence)

    return rank_coding_orfs_from_features(
        coding_orfs=coding_orfs,
        promoters=promoters,
        sd_sites=sd_sites,
        terminators=terminators,
        max_promoter_distance=max_promoter_distance,
        max_terminator_distance=max_terminator_distance,
    )


def choose_best_ranked_coding_orf_from_ranked(
    ranked: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    return ranked[0] if ranked else None


def choose_best_ranked_coding_orf(
    sequence: str,
    min_aa: int = 30,
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> Optional[Dict[str, Any]]:
    ranked = rank_coding_orfs(
        sequence=sequence,
        min_aa=min_aa,
        max_promoter_distance=max_promoter_distance,
        max_terminator_distance=max_terminator_distance,
    )
    return choose_best_ranked_coding_orf_from_ranked(ranked)
