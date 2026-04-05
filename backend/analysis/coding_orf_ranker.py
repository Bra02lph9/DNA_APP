from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import List, Optional, Dict, Any, Tuple

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
    distance = site.distance_to_start

    if distance is not None:
        if 6 <= distance <= 9:
            base += 3.0
        elif 4 <= distance <= 12:
            base += 1.0

    return min(base, 35.0)


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
        return min(base, 40.0)

    if 1 <= upstream_distance <= 80:
        base += 6.0
    elif 81 <= upstream_distance <= 150:
        base += 3.0
    elif 151 <= upstream_distance <= 300:
        base += 1.0

    return min(base, 40.0)


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
        return min(base, 30.0)

    if 1 <= downstream_distance <= 100:
        base += 5.0
    elif 101 <= downstream_distance <= 250:
        base += 2.0

    return min(base, 30.0)


def _group_by_strand(items) -> Dict[str, list]:
    grouped = {"+": [], "-": []}
    plus_items = grouped["+"]
    minus_items = grouped["-"]

    for item in items:
        strand = getattr(item, "strand", None)
        if strand == "+":
            plus_items.append(item)
        elif strand == "-":
            minus_items.append(item)

    return grouped


def _sd_sort_key(site: ShineDalgarnoSite) -> tuple:
    distance = site.distance_to_start
    return (
        -site.score,
        site.mismatches,
        abs((distance if distance is not None else 999) - 7),
        site.start,
    )


def _promoter_sort_key(p: PromoterHit, distance: int) -> tuple:
    return (distance, -p.score, p.box10_start, p.box35_start)


def _terminator_sort_key(t: TerminatorHit, distance: int) -> tuple:
    return (distance, -t.score, t.stem_left_start, t.poly_t_start)


def _index_sd_sites(
    sd_sites: List[ShineDalgarnoSite],
) -> Dict[str, Dict[int, ShineDalgarnoSite]]:
    indexed: Dict[str, Dict[int, ShineDalgarnoSite]] = {"+": {}, "-": {}}

    for site in sd_sites:
        strand = site.strand
        linked_start = site.linked_start_position

        if strand not in indexed or linked_start is None:
            continue

        current = indexed[strand].get(linked_start)
        if current is None or _sd_sort_key(site) < _sd_sort_key(current):
            indexed[strand][linked_start] = site

    return indexed


def _index_promoters_by_strand(
    promoters: List[PromoterHit],
) -> Dict[str, Tuple[List[int], List[PromoterHit]]]:
    grouped = _group_by_strand(promoters)

    plus_items = sorted(grouped["+"], key=lambda p: p.box10_end)
    minus_items = sorted(grouped["-"], key=lambda p: p.box10_start)

    return {
        "+": ([p.box10_end for p in plus_items], plus_items),
        "-": ([p.box10_start for p in minus_items], minus_items),
    }


def _index_terminators_by_strand(
    terminators: List[TerminatorHit],
) -> Dict[str, Tuple[List[int], List[TerminatorHit]]]:
    grouped = _group_by_strand(terminators)

    plus_items = sorted(grouped["+"], key=lambda t: t.stem_left_start)
    minus_items = sorted(grouped["-"], key=lambda t: t.stem_right_end)

    return {
        "+": ([t.stem_left_start for t in plus_items], plus_items),
        "-": ([t.stem_right_end for t in minus_items], minus_items),
    }


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

        key = _sd_sort_key(site)
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
        if distance is None or distance > max_distance:
            continue

        key = _promoter_sort_key(p, distance)
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
        if distance is None or distance > max_distance:
            continue

        key = _terminator_sort_key(t, distance)
        if best is None or key < best_key:
            best = t
            best_key = key

    return best


def _find_best_sd_for_orf_indexed(
    orf: CodingORF,
    sd_index: Dict[str, Dict[int, ShineDalgarnoSite]],
) -> Optional[ShineDalgarnoSite]:
    return sd_index.get(orf.strand, {}).get(orf.start)


def _find_best_promoter_for_orf_indexed(
    orf: CodingORF,
    promoter_index: Dict[str, Tuple[List[int], List[PromoterHit]]],
    max_distance: int = 300,
) -> Optional[PromoterHit]:
    positions, items = promoter_index.get(orf.strand, ([], []))
    if not items:
        return None

    best: Optional[PromoterHit] = None
    best_key = None

    if orf.strand == "+":
        left_bound = orf.start - max_distance
        right_bound = orf.start - 1

        lo = bisect_left(positions, left_bound)
        hi = bisect_right(positions, right_bound)

        for i in range(lo, hi):
            p = items[i]
            distance = orf.start - p.box10_end
            if distance < 1 or distance > max_distance:
                continue

            key = _promoter_sort_key(p, distance)
            if best is None or key < best_key:
                best = p
                best_key = key

    else:
        left_bound = orf.end + 1
        right_bound = orf.end + max_distance

        lo = bisect_left(positions, left_bound)
        hi = bisect_right(positions, right_bound)

        for i in range(lo, hi):
            p = items[i]
            distance = p.box10_start - orf.end
            if distance < 1 or distance > max_distance:
                continue

            key = _promoter_sort_key(p, distance)
            if best is None or key < best_key:
                best = p
                best_key = key

    return best


def _find_best_terminator_for_orf_indexed(
    orf: CodingORF,
    terminator_index: Dict[str, Tuple[List[int], List[TerminatorHit]]],
    max_distance: int = 300,
) -> Optional[TerminatorHit]:
    positions, items = terminator_index.get(orf.strand, ([], []))
    if not items:
        return None

    best: Optional[TerminatorHit] = None
    best_key = None

    if orf.strand == "+":
        left_bound = orf.end + 1
        right_bound = orf.end + max_distance

        lo = bisect_left(positions, left_bound)
        hi = bisect_right(positions, right_bound)

        for i in range(lo, hi):
            t = items[i]
            distance = t.stem_left_start - orf.end
            if distance < 1 or distance > max_distance:
                continue

            key = _terminator_sort_key(t, distance)
            if best is None or key < best_key:
                best = t
                best_key = key

    else:
        left_bound = orf.start - max_distance
        right_bound = orf.start - 1

        lo = bisect_left(positions, left_bound)
        hi = bisect_right(positions, right_bound)

        for i in range(lo, hi):
            t = items[i]
            distance = orf.start - t.stem_right_end
            if distance < 1 or distance > max_distance:
                continue

            key = _terminator_sort_key(t, distance)
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

    total_score = (
        length_score
        + start_score
        + sd_score
        + promoter_score
        + terminator_score
    )

    orf_dict = coding_orf_to_dict(orf)

    entry = {
        "orf": orf_dict,
        "total_score": round(total_score, 3),
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

    entry["_sort_key"] = (
        -entry["total_score"],
        -entry["score_breakdown"]["shine_dalgarno_score"],
        -entry["score_breakdown"]["promoter_score"],
        -entry["score_breakdown"]["terminator_score"],
        -entry["score_breakdown"]["length_score"],
        0 if orf_dict["strand"] == "+" else 1,
        orf_dict["start"],
    )

    return entry


def rank_coding_orfs_from_features(
    coding_orfs: List[CodingORF],
    promoters: List[PromoterHit],
    sd_sites: List[ShineDalgarnoSite],
    terminators: List[TerminatorHit],
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []

    sd_index = _index_sd_sites(sd_sites)
    promoter_index = _index_promoters_by_strand(promoters)
    terminator_index = _index_terminators_by_strand(terminators)

    append_ranked = ranked.append

    for orf in coding_orfs:
        best_sd = _find_best_sd_for_orf_indexed(orf, sd_index)
        best_promoter = _find_best_promoter_for_orf_indexed(
            orf,
            promoter_index,
            max_distance=max_promoter_distance,
        )
        best_terminator = _find_best_terminator_for_orf_indexed(
            orf,
            terminator_index,
            max_distance=max_terminator_distance,
        )

        append_ranked(
            _build_ranked_orf_entry(
                orf=orf,
                best_sd=best_sd,
                best_promoter=best_promoter,
                best_terminator=best_terminator,
            )
        )

    ranked.sort(key=lambda x: x["_sort_key"])

    for entry in ranked:
        entry.pop("_sort_key", None)

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


def choose_best_ranked_coding_orf_from_features(
    coding_orfs: List[CodingORF],
    promoters: List[PromoterHit],
    sd_sites: List[ShineDalgarnoSite],
    terminators: List[TerminatorHit],
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> Optional[Dict[str, Any]]:
    ranked = rank_coding_orfs_from_features(
        coding_orfs=coding_orfs,
        promoters=promoters,
        sd_sites=sd_sites,
        terminators=terminators,
        max_promoter_distance=max_promoter_distance,
        max_terminator_distance=max_terminator_distance,
    )
    return ranked[0] if ranked else None


def choose_best_ranked_coding_orf(
    sequence: str,
    min_aa: int = 30,
    max_promoter_distance: int = 300,
    max_terminator_distance: int = 300,
) -> Optional[Dict[str, Any]]:
    coding_orfs = find_coding_orfs(sequence=sequence, min_aa=min_aa)
    promoters = find_promoters(sequence)
    sd_sites = find_shine_dalgarno_sites(sequence)
    terminators = find_rho_independent_terminators(sequence)

    return choose_best_ranked_coding_orf_from_features(
        coding_orfs=coding_orfs,
        promoters=promoters,
        sd_sites=sd_sites,
        terminators=terminators,
        max_promoter_distance=max_promoter_distance,
        max_terminator_distance=max_terminator_distance,
    )
