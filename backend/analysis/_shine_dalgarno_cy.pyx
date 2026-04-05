# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
# cython: nonecheck=False
# cython: cdivision=True

DEF SD_LEN = 6
DEF MIN_SD_DISTANCE = 4
DEF MAX_SD_DISTANCE = 12


cdef inline bint is_start_codon_at(str seq, Py_ssize_t i):
    cdef str a = seq[i]
    cdef str b = seq[i + 1]
    cdef str c = seq[i + 2]
    return (
        (a == 'A' and b == 'T' and c == 'G') or
        (a == 'G' and b == 'T' and c == 'G') or
        (a == 'T' and b == 'T' and c == 'G')
    )


cdef inline str start_codon_value(str seq, Py_ssize_t i):
    cdef str a = seq[i]
    if a == 'A':
        return "ATG"
    elif a == 'G':
        return "GTG"
    return "TTG"


cdef inline int codon_score_int(str codon):
    if codon == "ATG":
        return 5
    if codon == "GTG":
        return 3
    if codon == "TTG":
        return 2
    return 0


cdef inline double distance_score_int(int distance):
    cdef int delta = distance - 7
    if delta < 0:
        delta = -delta

    cdef double score = 10.0 - delta * 2.0
    if score < 0.0:
        return 0.0
    return score


cdef inline bint has_N_6(str s, Py_ssize_t i):
    return (
        s[i] == 'N' or
        s[i + 1] == 'N' or
        s[i + 2] == 'N' or
        s[i + 3] == 'N' or
        s[i + 4] == 'N' or
        s[i + 5] == 'N'
    )


cdef inline int hamming_sd_at(str s, Py_ssize_t i):
    cdef int d = 0
    if s[i] != 'A':
        d += 1
    if s[i + 1] != 'G':
        d += 1
    if s[i + 2] != 'G':
        d += 1
    if s[i + 3] != 'A':
        d += 1
    if s[i + 4] != 'G':
        d += 1
    if s[i + 5] != 'G':
        d += 1
    return d


cpdef list find_start_codons_cy(str search_seq):
    cdef list starts = []
    cdef object append_start = starts.append
    cdef Py_ssize_t seq_len = len(search_seq)
    cdef Py_ssize_t i

    if seq_len < 3:
        return starts

    for i in range(seq_len - 2):
        if is_start_codon_at(search_seq, i):
            append_start((i, start_codon_value(search_seq, i)))

    return starts


cpdef object best_sd_for_start_cy(
    str search_seq,
    int start_pos_0,
    str start_codon,
    int max_mismatches=2,
):
    cdef Py_ssize_t seq_len = len(search_seq)
    cdef int distance
    cdef int site_end_0_exclusive
    cdef int site_start_0
    cdef int mm
    cdef double score
    cdef object best_result = None
    cdef int best_mm = 999
    cdef int best_distance_delta = 999
    cdef int current_distance_delta
    cdef double best_score = -1e18

    if start_pos_0 < 0 or start_pos_0 >= seq_len:
        return None

    for distance in range(MIN_SD_DISTANCE, MAX_SD_DISTANCE + 1):
        site_end_0_exclusive = start_pos_0 - distance
        site_start_0 = site_end_0_exclusive - SD_LEN

        if site_start_0 < 0:
            continue

        if site_end_0_exclusive > seq_len:
            continue

        if has_N_6(search_seq, site_start_0):
            continue

        mm = hamming_sd_at(search_seq, site_start_0)
        if mm > max_mismatches:
            continue

        score = 20.0
        score -= mm * 4.0
        score += distance_score_int(distance)
        score += codon_score_int(start_codon)

        current_distance_delta = distance - 7
        if current_distance_delta < 0:
            current_distance_delta = -current_distance_delta

        if best_result is None:
            best_score = score
            best_mm = mm
            best_distance_delta = current_distance_delta
            best_result = (
                site_start_0,
                site_end_0_exclusive,
                mm,
                distance,
                round(score, 3),
            )
        else:
            if score > best_score:
                best_score = score
                best_mm = mm
                best_distance_delta = current_distance_delta
                best_result = (
                    site_start_0,
                    site_end_0_exclusive,
                    mm,
                    distance,
                    round(score, 3),
                )
            elif score == best_score:
                if mm < best_mm:
                    best_mm = mm
                    best_distance_delta = current_distance_delta
                    best_result = (
                        site_start_0,
                        site_end_0_exclusive,
                        mm,
                        distance,
                        round(score, 3),
                    )
                elif mm == best_mm:
                    if current_distance_delta < best_distance_delta:
                        best_distance_delta = current_distance_delta
                        best_result = (
                            site_start_0,
                            site_end_0_exclusive,
                            mm,
                            distance,
                            round(score, 3),
                        )
                    elif current_distance_delta == best_distance_delta:
                        if site_start_0 < best_result[0]:
                            best_result = (
                                site_start_0,
                                site_end_0_exclusive,
                                mm,
                                distance,
                                round(score, 3),
                            )

    return best_result
