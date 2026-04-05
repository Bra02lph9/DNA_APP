# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
# cython: cdivision=True

cdef inline bint is_gc_char(str ch):
    return ch == 'G' or ch == 'C'


cdef inline str complement_char(str ch):
    if ch == 'A':
        return 'T'
    elif ch == 'T':
        return 'A'
    elif ch == 'C':
        return 'G'
    elif ch == 'G':
        return 'C'
    return 'N'


cdef inline int count_stem_mismatches_direct(
    str seq,
    int left_start,
    int right_start,
    int stem_len,
    int max_stem_mismatches,
) except -1:
    cdef int k
    cdef int mismatches = 0
    cdef str left_ch
    cdef str right_ch

    for k in range(stem_len):
        left_ch = seq[left_start + k]
        right_ch = seq[right_start + stem_len - 1 - k]

        # Reject ambiguous bases in either arm
        if left_ch == 'N' or right_ch == 'N':
            return max_stem_mismatches + 1

        if left_ch != complement_char(right_ch):
            mismatches += 1
            if mismatches > max_stem_mismatches:
                return mismatches

    return mismatches


cpdef list scan_terminator_positions_cy(
    str search_seq,
    int stem_min=5,
    int stem_max=10,
    int loop_min=3,
    int loop_max=7,
    int max_stem_mismatches=1,
    int min_poly_t=5,
    double gc_threshold=0.7,
):
    cdef int n = len(search_seq)
    cdef int min_total_len = (2 * stem_min) + loop_min + min_poly_t

    cdef int i
    cdef int stem_len
    cdef int loop_len
    cdef int poly_start_0
    cdef int poly_len
    cdef int poly_end_0_exclusive
    cdef int right_end_0_exclusive
    cdef int right_start_0
    cdef int left_end_0_exclusive
    cdef int left_start_0
    cdef int mismatches

    cdef int gc_count
    cdef double gc_fraction

    cdef list hits_raw = []

    # Prefix GC counts: gc_prefix[i] = number of GC in seq[0:i]
    cdef list gc_prefix = [0] * (n + 1)

    # T-run lengths: t_run[i] = consecutive T count starting at i
    cdef list t_run = [0] * (n + 1)

    if n < min_total_len:
        return hits_raw

    # Build GC prefix
    for i in range(n):
        gc_prefix[i + 1] = gc_prefix[i] + (1 if is_gc_char(search_seq[i]) else 0)

    # Build T-run lengths from right to left
    for i in range(n - 1, -1, -1):
        if search_seq[i] == 'T':
            t_run[i] = t_run[i + 1] + 1
        else:
            t_run[i] = 0

    # Biological strategy:
    # Start from poly-T starts, then search upstream for compatible hairpins.
    for poly_start_0 in range(n - min_poly_t + 1):
        poly_len = t_run[poly_start_0]
        if poly_len < min_poly_t:
            continue

        poly_end_0_exclusive = poly_start_0 + poly_len
        right_end_0_exclusive = poly_start_0

        for stem_len in range(stem_min, stem_max + 1):
            right_start_0 = right_end_0_exclusive - stem_len
            if right_start_0 < 0:
                continue

            for loop_len in range(loop_min, loop_max + 1):
                left_end_0_exclusive = right_start_0 - loop_len
                left_start_0 = left_end_0_exclusive - stem_len

                if left_start_0 < 0:
                    continue

                # Fast GC check on left arm using prefix sums
                gc_count = gc_prefix[left_end_0_exclusive] - gc_prefix[left_start_0]
                gc_fraction = gc_count / <double>stem_len
                if gc_fraction < gc_threshold:
                    continue

                mismatches = count_stem_mismatches_direct(
                    search_seq,
                    left_start_0,
                    right_start_0,
                    stem_len,
                    max_stem_mismatches,
                )
                if mismatches > max_stem_mismatches:
                    continue

                hits_raw.append(
                    (
                        left_start_0,
                        left_end_0_exclusive,
                        right_start_0,
                        right_end_0_exclusive,
                        poly_start_0,
                        poly_end_0_exclusive,
                        mismatches,
                    )
                )

    return hits_raw
