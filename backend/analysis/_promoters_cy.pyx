# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
# cython: nonecheck=False
# cython: cdivision=True

from libc.math cimport floor

DEF MOTIF_LEN = 6

cdef unsigned char C_A = ord('A')
cdef unsigned char C_T = ord('T')
cdef unsigned char C_G = ord('G')
cdef unsigned char C_C = ord('C')
cdef unsigned char C_N = ord('N')


cdef inline double round3(double x):
    return floor(x * 1000.0 + 0.5) / 1000.0


cdef inline bint has_N_6(const unsigned char* s, Py_ssize_t i) nogil:
    return (
        s[i] == C_N or
        s[i + 1] == C_N or
        s[i + 2] == C_N or
        s[i + 3] == C_N or
        s[i + 4] == C_N or
        s[i + 5] == C_N
    )


cdef inline int hamming_box35_at(const unsigned char* s, Py_ssize_t i) nogil:
    cdef int d = 0
    if s[i] != C_T:
        d += 1
    if s[i + 1] != C_T:
        d += 1
    if s[i + 2] != C_G:
        d += 1
    if s[i + 3] != C_A:
        d += 1
    if s[i + 4] != C_C:
        d += 1
    if s[i + 5] != C_A:
        d += 1
    return d


cdef inline int hamming_box10_at(const unsigned char* s, Py_ssize_t i) nogil:
    cdef int d = 0
    if s[i] != C_T:
        d += 1
    if s[i + 1] != C_A:
        d += 1
    if s[i + 2] != C_T:
        d += 1
    if s[i + 3] != C_A:
        d += 1
    if s[i + 4] != C_A:
        d += 1
    if s[i + 5] != C_T:
        d += 1
    return d


cdef inline double score_promoter_c(
    int box35_mismatches,
    int box10_mismatches,
    int spacing,
    double spacer_at_fraction,
) nogil:
    cdef double score = 30.0
    score -= box35_mismatches * 5.0
    score -= box10_mismatches * 6.0
    score -= abs(spacing - 17) * 1.5
    score += spacer_at_fraction * 4.0
    return score


cpdef list scan_promoter_positions_cy(
    bytes search_seq,
    int max_mismatches_box35=2,
    int max_mismatches_box10=2,
    int spacing_min=16,
    int spacing_max=19,
):
    cdef Py_ssize_t seq_len = len(search_seq)
    cdef Py_ssize_t i, i35, i10, end35
    cdef Py_ssize_t last_box35_start, last_box10_start
    cdef int mm35, mm10, spacing
    cdef double spacer_at_fraction, score
    cdef list hits_raw = []
    cdef object append_hit = hits_raw.append
    cdef const unsigned char* s
    cdef list at_prefix

    if seq_len == 0:
        return hits_raw

    if spacing_min > spacing_max or spacing_min < 0:
        return hits_raw

    if seq_len < (2 * MOTIF_LEN + spacing_min):
        return hits_raw

    s = <const unsigned char*> search_seq

    at_prefix = [0] * (seq_len + 1)

    for i in range(seq_len):
        at_prefix[i + 1] = at_prefix[i] + (s[i] == C_A or s[i] == C_T)

    last_box35_start = seq_len - MOTIF_LEN
    last_box10_start = seq_len - MOTIF_LEN

    for i35 in range(last_box35_start + 1):
        if has_N_6(s, i35):
            continue

        mm35 = hamming_box35_at(s, i35)
        if mm35 > max_mismatches_box35:
            continue

        end35 = i35 + MOTIF_LEN

        for spacing in range(spacing_min, spacing_max + 1):
            i10 = end35 + spacing

            if i10 > last_box10_start:
                break

            if has_N_6(s, i10):
                continue

            mm10 = hamming_box10_at(s, i10)
            if mm10 > max_mismatches_box10:
                continue

            spacer_at_fraction = (
                (at_prefix[i10] - at_prefix[end35]) / <double>spacing
            )

            score = score_promoter_c(mm35, mm10, spacing, spacer_at_fraction)

            append_hit((
                i35,
                mm35,
                i10,
                mm10,
                spacing,
                round3(spacer_at_fraction),
                round3(score),
            ))

    return hits_raw
