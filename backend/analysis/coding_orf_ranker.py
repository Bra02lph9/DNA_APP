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


def score_promoter(hit: Optional[PromoterHit], orf: CodingORF) -> float:
    if hit is None:
        return 0.0

    base = float(hit.score)
    if orf.strand == "+":
        upstream_distance = orf.start - hit.box10_end
    else:
        upstream_distance = hit.box10_start - orf.end

    if 1 <= upstream_distance <= 80:
        base += 6.0
    elif 81 <= upstream_distance <= 150:
        base += 3.0
    elif 151 <= upstream_distance <= 300:
        base += 1.0

    return round(min(base, 40.0), 3)


def score_terminator(hit: Optional[TerminatorHit], orf: CodingORF) -> float:
    if hit is None:
        return 0.0

    base = float(hit.score)

    if orf.strand == "+":
        downstream_distance = hit.stem_left_start - orf.end
    else:
        downstream_distance = orf.start - hit.stem_right_end

    if 1 <= downstream_distance <= 100:
        base += 5.0
    elif 101 <= downstream_distance <= 250:
        base += 2.0

    return round(min(base, 30.0), 3)


def find_best_sd_for_orf(
    orf: CodingORF,
    sd_sites: List[ShineDalgarnoSite],
) -> Optional[ShineDalgarnoSite]:
    candidates: List[ShineDalgarnoSite] = []

    for site in sd_sites:
        if site.strand != orf.strand:
            continue

        if site.linked_start_position is None:
            continue

        # on veut un SD lié exactement au start de cette ORF
        if site.linked_start_position == orf.start:
            candidates.append(site)

    if not candidates:
        return None

    candidates.sort(
        key=lambda s: (
            -s.score,
            s.mismatches,
            abs((s.distance_to_start or 999) - 7),
            s.start,
        )
    )
    return candidates[0]


def find_best_promoter_for_orf(
    orf: CodingORF,
    promoters: List[PromoterHit],
    max_distance: int = 300,
) -> Optional[PromoterHit]:
    candidates: List[tuple[int, PromoterHit]] = []

    for p in promoters:
        if p.strand != orf.strand:
            continue

        if orf.strand == "+":
            if p.box10_end < orf.start:
                distance = orf.start - p.box10_end
                if distance <= max_distance:
                    candidates.append((distance, p))
        else:
            if p.box10_start > orf.end:
                distance = p.box10_start - orf.end
                if distance <= max_distance:
                    candidates.append((distance, p))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], -x[1].score))
    return candidates[0][1]


def find_best_terminator_for_orf(
    orf: CodingORF,
    terminators: List[TerminatorHit],
    max_distance: int = 300,
) -> Optional[TerminatorHit]:
    candidates: List[tuple[int, TerminatorHit]] = []

    for t in terminators:
        if t.strand != orf.strand:
            continue

        if orf.strand == "+":
            # terminateur après l'ORF
            if t.stem_left_start > orf.end:
                distance = t.stem_left_start - orf.end
                if distance <= max_distance:
                    candidates.append((distance, t))
        else:
            # sur le brin -, le terminateur est à gauche de l'ORF
            if t.stem_right_end < orf.start:
                distance = orf.start - t.stem_right_end
                if distance <= max_distance:
                    candidates.append((distance, t))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], -x[1].score))
    return candidates[0][1]


def rank_coding_orfs(
    sequence: str,
    min_aa: int = 30,
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> List[Dict[str, Any]]:
    """
    Retourne toutes les ORFs codantes triées par plausibilité biologique.
    """

    coding_orfs = find_coding_orfs(sequence=sequence, min_aa=min_aa)
    promoters = find_promoters(sequence)
    sd_sites = find_shine_dalgarno_sites(sequence)
    terminators = find_rho_independent_terminators(sequence)

    ranked: List[Dict[str, Any]] = []

    for orf in coding_orfs:
        best_sd = find_best_sd_for_orf(orf, sd_sites)
        best_promoter = find_best_promoter_for_orf(
            orf, promoters, max_distance=max_promoter_distance
        )
        best_terminator = find_best_terminator_for_orf(
            orf, terminators, max_distance=max_terminator_distance
        )

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

        ranked.append(
            {
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

    if not ranked:
        return None

    return ranked[0]
