# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False

DEF MOTIF_LEN = 6

cdef str BOX35 = "TTGACA"
cdef str BOX10 = "TATAAT"


cdef inline int hamming6(str a, str b):
    cdef int d = 0
    if a[0] != b[0]:
        d += 1
    if a[1] != b[1]:
        d += 1
    if a[2] != b[2]:
        d += 1
    if a[3] != b[3]:
        d += 1
    if a[4] != b[4]:
        d += 1
    if a[5] != b[5]:
        d += 1
    return d


cdef inline bint has_N_6(str s, Py_ssize_t i):
    return (
        s[i] == 'N' or
        s[i + 1] == 'N' or
        s[i + 2] == 'N' or
        s[i + 3] == 'N' or
        s[i + 4] == 'N' or
        s[i + 5] == 'N'
    )


cpdef list scan_promoter_positions_cy(
    str search_seq,
    int max_mismatches_box35=2,
    int max_mismatches_box10=2,
    int spacing_min=16,
    int spacing_max=19,
):
    cdef Py_ssize_t seq_len = len(search_seq)
    cdef Py_ssize_t i35, i10
    cdef int mm35, mm10, spacing
    cdef Py_ssize_t end35
    cdef Py_ssize_t last_box35_start = seq_len - MOTIF_LEN
    cdef Py_ssize_t last_box10_start = seq_len - MOTIF_LEN
    cdef list hits_raw = []

    if spacing_min > spacing_max:
        return hits_raw

    if seq_len < (2 * MOTIF_LEN + spacing_min):
        return hits_raw

    for i35 in range(last_box35_start + 1):
        if has_N_6(search_seq, i35):
            continue

        mm35 = hamming6(search_seq[i35:i35 + MOTIF_LEN], BOX35)
        if mm35 > max_mismatches_box35:
            continue

        end35 = i35 + MOTIF_LEN

        for spacing in range(spacing_min, spacing_max + 1):
            i10 = end35 + spacing

            if i10 > last_box10_start:
                continue

            if has_N_6(search_seq, i10):
                continue

            mm10 = hamming6(search_seq[i10:i10 + MOTIF_LEN], BOX10)
            if mm10 > max_mismatches_box10:
                continue

            hits_raw.append((i35, mm35, i10, mm10, spacing))

    return hits_raw
