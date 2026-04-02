# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False

cdef inline double gc_fraction_local(str seq):
    cdef Py_ssize_t i, n = len(seq)
    cdef int gc = 0
    if n == 0:
        return 0.0
    for i in range(n):
        if seq[i] == 'G' or seq[i] == 'C':
            gc += 1
    return gc / n


cdef inline bint is_gc_rich_local(str seq, double threshold):
    return gc_fraction_local(seq) >= threshold


cdef inline str revcomp_simple_local(str seq):
    cdef list out = []
    cdef Py_ssize_t i
    cdef str ch
    for i in range(len(seq) - 1, -1, -1):
        ch = seq[i]
        if ch == 'A':
            out.append('T')
        elif ch == 'T':
            out.append('A')
        elif ch == 'C':
            out.append('G')
        elif ch == 'G':
            out.append('C')
        else:
            out.append('N')
    return ''.join(out)


cdef inline int hamming_local(str a, str b):
    cdef Py_ssize_t i, n = len(a)
    cdef int d = 0
    for i in range(n):
        if a[i] != b[i]:
            d += 1
    return d


cdef inline bint contains_N(str seq):
    return 'N' in seq


cdef inline int collect_poly_t_end(str search_seq, int start_0):
    cdef int n = len(search_seq)
    cdef int end_0_exclusive = start_0

    while end_0_exclusive < n and search_seq[end_0_exclusive] == 'T':
        end_0_exclusive += 1

    return end_0_exclusive


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
    cdef int max_left_start
    cdef int i
    cdef int stem_len
    cdef int loop_len
    cdef int left_start_0
    cdef int left_end_0_exclusive
    cdef int right_start_0
    cdef int right_end_0_exclusive
    cdef int poly_start_0
    cdef int poly_end_0_exclusive
    cdef int mismatches
    cdef str left
    cdef str right
    cdef str expected_right
    cdef list hits_raw = []

    if n < min_total_len:
        return hits_raw

    max_left_start = n - min_total_len

    for i in range(max_left_start + 1):
        for stem_len in range(stem_min, stem_max + 1):
            left_start_0 = i
            left_end_0_exclusive = i + stem_len

            if left_end_0_exclusive > n:
                continue

            left = search_seq[left_start_0:left_end_0_exclusive]
            if contains_N(left):
                continue
            if not is_gc_rich_local(left, gc_threshold):
                continue

            expected_right = revcomp_simple_local(left)

            for loop_len in range(loop_min, loop_max + 1):
                right_start_0 = left_end_0_exclusive + loop_len
                right_end_0_exclusive = right_start_0 + stem_len

                if right_end_0_exclusive > n:
                    continue

                right = search_seq[right_start_0:right_end_0_exclusive]
                if contains_N(right):
                    continue

                mismatches = hamming_local(right, expected_right)
                if mismatches > max_stem_mismatches:
                    continue

                poly_start_0 = right_end_0_exclusive
                poly_end_0_exclusive = collect_poly_t_end(search_seq, poly_start_0)

                if (poly_end_0_exclusive - poly_start_0) < min_poly_t:
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
