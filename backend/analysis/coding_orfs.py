from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional

from .utils import reverse_complement

try:
    from ._coding_orfs_cy import scan_orf_positions_in_strand_cy
except ImportError:
    scan_orf_positions_in_strand_cy = None


START_CODONS = {"ATG", "GTG", "TTG"}
STOP_CODONS = {"TAA", "TAG", "TGA"}
CODON_SIZE = 3


@dataclass(slots=True)
class CodingORF:
    strand: str
    frame: int
    start: int
    end: int
    length_nt: int
    peptide_length_aa: int
    start_codon: str
    stop_codon: str
    sequence: str
    start_index_in_strand: int
    stop_index_in_strand: int


def _clean_sequence(sequence: str) -> str:
    return sequence.replace("\n", "").replace("\r", "").replace(" ", "").upper()


def _map_rev_to_forward(
    rev_start_0: int,
    rev_end_0_exclusive: int,
    original_len: int,
) -> tuple[int, int]:
    forward_start_0 = original_len - rev_end_0_exclusive
    forward_end_0_exclusive = original_len - rev_start_0
    return forward_start_0 + 1, forward_end_0_exclusive


def _start_codon_priority(codon: str) -> int:
    if codon == "ATG":
        return 0
    if codon == "GTG":
        return 1
    if codon == "TTG":
        return 2
    return 3


def _peptide_length_from_nt(length_nt: int) -> int:
    return (length_nt // CODON_SIZE) - 1


def _build_orf(
    scanned_seq: str,
    original_seq_len: int,
    strand: str,
    frame_offset: int,
    start_0: int,
    stop_0: int,
) -> CodingORF:
    end_0_exclusive = stop_0 + CODON_SIZE
    orf_seq = scanned_seq[start_0:end_0_exclusive]
    length_nt = end_0_exclusive - start_0

    if strand == "+":
        start = start_0 + 1
        end = end_0_exclusive
    else:
        start, end = _map_rev_to_forward(
            start_0,
            end_0_exclusive,
            original_seq_len,
        )

    return CodingORF(
        strand=strand,
        frame=frame_offset + 1,
        start=start,
        end=end,
        length_nt=length_nt,
        peptide_length_aa=_peptide_length_from_nt(length_nt),
        start_codon=scanned_seq[start_0:start_0 + CODON_SIZE],
        stop_codon=scanned_seq[stop_0:stop_0 + CODON_SIZE],
        sequence=orf_seq,
        start_index_in_strand=start_0,
        stop_index_in_strand=stop_0,
    )


def _sort_orfs_biologically(orfs: List[CodingORF]) -> List[CodingORF]:
    return sorted(
        orfs,
        key=lambda o: (
            -o.peptide_length_aa,
            _start_codon_priority(o.start_codon),
            0 if o.strand == "+" else 1,
            o.start,
            o.end,
        ),
    )


def _scan_orf_positions_in_strand_python(
    scanned_seq: str,
    min_aa: int,
    start_codons: set[str],
    stop_codons: set[str],
    longest_only_per_stop: bool,
) -> List[tuple[int, int, int]]:
    n = len(scanned_seq)
    found_positions: List[tuple[int, int, int]] = []

    for frame_offset in range(CODON_SIZE):
        starts_in_frame: List[int] = []

        for i in range(frame_offset, n - 2, CODON_SIZE):
            codon = scanned_seq[i:i + CODON_SIZE]

            if codon in start_codons:
                starts_in_frame.append(i)

            if codon in stop_codons:
                if starts_in_frame:
                    if longest_only_per_stop:
                        start_0 = starts_in_frame[0]
                        length_nt = (i + CODON_SIZE) - start_0
                        peptide_len = _peptide_length_from_nt(length_nt)
                        if peptide_len >= min_aa:
                            found_positions.append((frame_offset, start_0, i))
                    else:
                        for start_0 in starts_in_frame:
                            length_nt = (i + CODON_SIZE) - start_0
                            peptide_len = _peptide_length_from_nt(length_nt)
                            if peptide_len >= min_aa:
                                found_positions.append((frame_offset, start_0, i))

                starts_in_frame = []

    return found_positions


def _scan_orf_positions_in_strand(
    scanned_seq: str,
    min_aa: int,
    start_codons: set[str],
    stop_codons: set[str],
    longest_only_per_stop: bool,
) -> List[tuple[int, int, int]]:
    use_cython = (
        scan_orf_positions_in_strand_cy is not None
        and start_codons == START_CODONS
        and stop_codons == STOP_CODONS
    )

    if use_cython:
        return scan_orf_positions_in_strand_cy(
            scanned_seq,
            min_aa,
            longest_only_per_stop,
        )

    return _scan_orf_positions_in_strand_python(
        scanned_seq=scanned_seq,
        min_aa=min_aa,
        start_codons=start_codons,
        stop_codons=stop_codons,
        longest_only_per_stop=longest_only_per_stop,
    )


def find_coding_orfs_in_strand(
    sequence: str,
    strand: str = "+",
    min_aa: int = 30,
    start_codons: Optional[set[str]] = None,
    stop_codons: Optional[set[str]] = None,
    longest_only_per_stop: bool = False,
    already_clean: bool = False,
) -> List[CodingORF]:
    seq = sequence if already_clean else _clean_sequence(sequence)
    if not seq:
        return []

    start_codons = start_codons or START_CODONS
    stop_codons = stop_codons or STOP_CODONS

    scanned_seq = seq if strand == "+" else reverse_complement(seq)
    original_len = len(seq)

    if len(scanned_seq) < CODON_SIZE * 2:
        return []

    raw_positions = _scan_orf_positions_in_strand(
        scanned_seq=scanned_seq,
        min_aa=min_aa,
        start_codons=start_codons,
        stop_codons=stop_codons,
        longest_only_per_stop=longest_only_per_stop,
    )

    return [
        _build_orf(
            scanned_seq=scanned_seq,
            original_seq_len=original_len,
            strand=strand,
            frame_offset=frame_offset,
            start_0=start_0,
            stop_0=stop_0,
        )
        for frame_offset, start_0, stop_0 in raw_positions
    ]


def find_coding_orfs(
    sequence: str,
    min_aa: int = 30,
    start_codons: Optional[set[str]] = None,
    stop_codons: Optional[set[str]] = None,
    longest_only_per_stop: bool = False,
) -> List[CodingORF]:
    seq = _clean_sequence(sequence)
    if not seq:
        return []

    plus_orfs = find_coding_orfs_in_strand(
        sequence=seq,
        strand="+",
        min_aa=min_aa,
        start_codons=start_codons,
        stop_codons=stop_codons,
        longest_only_per_stop=longest_only_per_stop,
        already_clean=True,
    )

    minus_orfs = find_coding_orfs_in_strand(
        sequence=seq,
        strand="-",
        min_aa=min_aa,
        start_codons=start_codons,
        stop_codons=stop_codons,
        longest_only_per_stop=longest_only_per_stop,
        already_clean=True,
    )

    return _sort_orfs_biologically(plus_orfs + minus_orfs)


def choose_best_coding_orf_from_list(orfs: List[CodingORF]) -> Optional[CodingORF]:
    return orfs[0] if orfs else None


def choose_best_coding_orf(
    sequence: str,
    min_aa: int = 30,
    start_codons: Optional[set[str]] = None,
    stop_codons: Optional[set[str]] = None,
) -> Optional[CodingORF]:
    orfs = find_coding_orfs(
        sequence=sequence,
        min_aa=min_aa,
        start_codons=start_codons,
        stop_codons=stop_codons,
        longest_only_per_stop=False,
    )
    return choose_best_coding_orf_from_list(orfs)


def coding_orf_to_dict(orf: CodingORF) -> dict:
    return asdict(orf)


def coding_orfs_to_dicts(orfs: List[CodingORF]) -> List[dict]:
    return [coding_orf_to_dict(orf) for orf in orfs]


def format_coding_orfs(orfs: List[CodingORF]) -> str:
    if not orfs:
        return "No coding ORFs found."

    lines = [f"Detected {len(orfs)} coding ORF(s):", ""]

    for idx, orf in enumerate(orfs, start=1):
        lines.extend(
            [
                f"Coding ORF {idx}",
                f"  Strand: {orf.strand}",
                f"  Frame: {orf.frame}",
                f"  Start: {orf.start}",
                f"  End: {orf.end}",
                f"  Length: {orf.length_nt} nt",
                f"  Peptide length: {orf.peptide_length_aa} aa",
                f"  Start codon: {orf.start_codon}",
                f"  Stop codon: {orf.stop_codon}",
                f"  Sequence: {orf.sequence[:90]}{'...' if len(orf.sequence) > 90 else ''}",
                "",
            ]
        )

    return "\n".join(lines)
