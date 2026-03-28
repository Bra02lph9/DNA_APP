from __future__ import annotations

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


@njit(cache=True)
def hamming_distance_numba(a: str, b: str) -> int:
    if len(a) != len(b):
        raise ValueError("Strings must have the same length.")

    count = 0
    for i in range(len(a)):
        if a[i] != b[i]:
            count += 1
    return count


@njit(cache=True)
def count_gc_numba(seq: str) -> int:
    count = 0
    for i in range(len(seq)):
        if seq[i] == "G" or seq[i] == "C":
            count += 1
    return count


@njit(cache=True)
def gc_fraction_numba(seq: str) -> float:
    n = len(seq)
    if n == 0:
        return 0.0
    return count_gc_numba(seq) / n


@njit(cache=True)
def count_at_numba(seq: str) -> int:
    count = 0
    for i in range(len(seq)):
        if seq[i] == "A" or seq[i] == "T":
            count += 1
    return count


@njit(cache=True)
def at_fraction_numba(seq: str) -> float:
    n = len(seq)
    if n == 0:
        return 0.0
    return count_at_numba(seq) / n


@njit(cache=True)
def motif_mismatches_numba(sequence: str, start: int, motif: str) -> int:
    motif_len = len(motif)

    if start < 0 or start + motif_len > len(sequence):
        return -1

    mismatches = 0
    for j in range(motif_len):
        if sequence[start + j] != motif[j]:
            mismatches += 1

    return mismatches


@njit(cache=True)
def motif_matches_with_max_mismatches_numba(
    sequence: str,
    start: int,
    motif: str,
    max_mismatches: int,
) -> bool:
    motif_len = len(motif)

    if start < 0 or start + motif_len > len(sequence):
        return False

    mismatches = 0
    for j in range(motif_len):
        if sequence[start + j] != motif[j]:
            mismatches += 1
            if mismatches > max_mismatches:
                return False

    return True


@njit(cache=True)
def count_motif_matches_with_max_mismatches(
    sequence: str,
    motif: str,
    max_mismatches: int,
) -> int:
    seq_len = len(sequence)
    motif_len = len(motif)

    if motif_len == 0 or seq_len < motif_len:
        return 0

    total = 0

    for i in range(seq_len - motif_len + 1):
        mismatches = 0

        for j in range(motif_len):
            if sequence[i + j] != motif[j]:
                mismatches += 1
                if mismatches > max_mismatches:
                    break

        if mismatches <= max_mismatches:
            total += 1

    return total


@njit(cache=True)
def find_motif_positions_limited(
    sequence: str,
    motif: str,
    max_mismatches: int,
    max_hits: int = 100000,
):
    seq_len = len(sequence)
    motif_len = len(motif)

    if motif_len == 0 or seq_len < motif_len:
        return []

    positions = []

    for i in range(seq_len - motif_len + 1):
        mismatches = 0

        for j in range(motif_len):
            if sequence[i + j] != motif[j]:
                mismatches += 1
                if mismatches > max_mismatches:
                    break

        if mismatches <= max_mismatches:
            positions.append(i)
            if len(positions) >= max_hits:
                break

    return positions


@njit(cache=True)
def is_start_codon_at(sequence: str, pos: int) -> bool:
    if pos < 0 or pos + 3 > len(sequence):
        return False

    a = sequence[pos]
    b = sequence[pos + 1]
    c = sequence[pos + 2]

    return (
        (a == "A" and b == "T" and c == "G") or
        (a == "G" and b == "T" and c == "G") or
        (a == "T" and b == "T" and c == "G")
    )


@njit(cache=True)
def is_stop_codon_at(sequence: str, pos: int) -> bool:
    if pos < 0 or pos + 3 > len(sequence):
        return False

    a = sequence[pos]
    b = sequence[pos + 1]
    c = sequence[pos + 2]

    return (
        (a == "T" and b == "A" and c == "A") or
        (a == "T" and b == "A" and c == "G") or
        (a == "T" and b == "G" and c == "A")
    )


@njit(cache=True)
def is_start_codon(codon: str) -> bool:
    return codon == "ATG" or codon == "GTG" or codon == "TTG"


@njit(cache=True)
def is_stop_codon(codon: str) -> bool:
    return codon == "TAA" or codon == "TAG" or codon == "TGA"
