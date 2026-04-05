# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
# cython: nonecheck=False
# cython: cdivision=True

DEF MOTIF_LEN = 6

cdef inline bint has_N_6(str s, Py_ssize_t i):
    return (
        s[i] == 'N' or
        s[i + 1] == 'N' or
        s[i + 2] == 'N' or
        s[i + 3] == 'N' or
        s[i + 4] == 'N' or
        s[i + 5] == 'N'
    )


cdef inline int hamming_box35_at(str s, Py_ssize_t i):
    cdef int d = 0
    if s[i] != 'T':
        d += 1
    if s[i + 1] != 'T':
        d += 1
    if s[i + 2] != 'G':
        d += 1
    if s[i + 3] != 'A':
        d += 1
    if s[i + 4] != 'C':
        d += 1
    if s[i + 5] != 'A':
        d += 1
    return d


cdef inline int hamming_box10_at(str s, Py_ssize_t i):
    cdef int d = 0
    if s[i] != 'T':
        d += 1
    if s[i + 1] != 'A':
        d += 1
    if s[i + 2] != 'T':
        d += 1
    if s[i + 3] != 'A':
        d += 1
    if s[i + 4] != 'A':
        d += 1
    if s[i + 5] != 'T':
        d += 1
    return d


cpdef list scan_promoter_positions_cy(
    str search_seq,
    int max_mismatches_box35=2,
    int max_mismatches_box10=2,
    int spacing_min=16,
    int spacing_max=19,
):
    cdef Py_ssize_t seq_len = len(search_seq)
    cdef Py_ssize_t i35, i10
    cdef Py_ssize_t end35
    cdef Py_ssize_t last_box35_start
    cdef Py_ssize_t last_box10_start
    cdef int mm35, mm10, spacing
    cdef list hits_raw = []
    cdef object append_hit = hits_raw.append

    if seq_len == 0:
        return hits_raw

    if spacing_min > spacing_max:
        return hits_raw

    if spacing_min < 0:
        return hits_raw

    if seq_len < (2 * MOTIF_LEN + spacing_min):
        return hits_raw

    last_box35_start = seq_len - MOTIF_LEN
    last_box10_start = seq_len - MOTIF_LEN

    for i35 in range(last_box35_start + 1):
        if has_N_6(search_seq, i35):
            continue

        mm35 = hamming_box35_at(search_seq, i35)
        if mm35 > max_mismatches_box35:
            continue

        end35 = i35 + MOTIF_LEN

        for spacing in range(spacing_min, spacing_max + 1):
            i10 = end35 + spacing

            if i10 > last_box10_start:
                break

            if has_N_6(search_seq, i10):
                continue

            mm10 = hamming_box10_at(search_seq, i10)
            if mm10 > max_mismatches_box10:
                continue

            append_hit((i35, mm35, i10, mm10, spacing))

    return hits_raw
    