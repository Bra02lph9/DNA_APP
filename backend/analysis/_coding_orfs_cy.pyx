# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False

DEF CODON_SIZE = 3


cdef inline bint is_start_codon(str seq, Py_ssize_t i):
    cdef str a = seq[i]
    cdef str b = seq[i + 1]
    cdef str c = seq[i + 2]
    return (
        (a == 'A' and b == 'T' and c == 'G') or
        (a == 'G' and b == 'T' and c == 'G') or
        (a == 'T' and b == 'T' and c == 'G')
    )


cdef inline bint is_stop_codon(str seq, Py_ssize_t i):
    cdef str a = seq[i]
    cdef str b = seq[i + 1]
    cdef str c = seq[i + 2]
    return (
        (a == 'T' and b == 'A' and c == 'A') or
        (a == 'T' and b == 'A' and c == 'G') or
        (a == 'T' and b == 'G' and c == 'A')
    )


cpdef list scan_orf_positions_in_strand_cy(
    str scanned_seq,
    int min_aa=30,
    bint longest_only_per_stop=False,
):
    cdef Py_ssize_t n = len(scanned_seq)
    cdef int frame_offset
    cdef Py_ssize_t i, start_0
    cdef int length_nt
    cdef int peptide_len
    cdef list found_positions = []
    cdef list starts_in_frame

    if n < 6:
        return found_positions

    for frame_offset in range(CODON_SIZE):
        starts_in_frame = []

        for i in range(frame_offset, n - 2, CODON_SIZE):
            if is_start_codon(scanned_seq, i):
                starts_in_frame.append(i)

            if is_stop_codon(scanned_seq, i):
                if starts_in_frame:
                    if longest_only_per_stop:
                        start_0 = starts_in_frame[0]
                        length_nt = (i + CODON_SIZE) - start_0
                        peptide_len = (length_nt // CODON_SIZE) - 1
                        if peptide_len >= min_aa:
                            found_positions.append((frame_offset, start_0, i))
                    else:
                        for start_0 in starts_in_frame:
                            length_nt = (i + CODON_SIZE) - start_0
                            peptide_len = (length_nt // CODON_SIZE) - 1
                            if peptide_len >= min_aa:
                                found_positions.append((frame_offset, start_0, i))

                starts_in_frame = []

    return found_positions
