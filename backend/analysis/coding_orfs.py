from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional

from .utils import reverse_complement


START_CODONS = {"ATG", "GTG", "TTG"}
STOP_CODONS = {"TAA", "TAG", "TGA"}


@dataclass
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
    original_len: int
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


def _build_orf(
    scanned_seq: str,
    original_seq_len: int,
    strand: str,
    frame_offset: int,
    start_0: int,
    stop_0: int,
) -> CodingORF:
    end_0_exclusive = stop_0 + 3
    orf_seq = scanned_seq[start_0:end_0_exclusive]
    length_nt = len(orf_seq)

    if strand == "+":
        start = start_0 + 1
        end = end_0_exclusive
    else:
        start, end = _map_rev_to_forward(start_0, end_0_exclusive, original_seq_len)

    return CodingORF(
        strand=strand,
        frame=frame_offset + 1,
        start=start,
        end=end,
        length_nt=length_nt,
        peptide_length_aa=(length_nt // 3) - 1,
        start_codon=scanned_seq[start_0:start_0 + 3],
        stop_codon=scanned_seq[stop_0:stop_0 + 3],
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


def find_coding_orfs_in_strand(
    sequence: str,
    strand: str = "+",
    min_aa: int = 30,
    start_codons: Optional[set[str]] = None,
    stop_codons: Optional[set[str]] = None,
    longest_only_per_stop: bool = False,
) -> List[CodingORF]:
    seq = _clean_sequence(sequence)
    if not seq:
        return []

    if start_codons is None:
        start_codons = START_CODONS
    if stop_codons is None:
        stop_codons = STOP_CODONS

    scanned_seq = seq if strand == "+" else reverse_complement(seq)
    original_len = len(seq)

    found: List[CodingORF] = []

    for frame_offset in range(3):
        starts_in_frame: List[int] = []

        for i in range(frame_offset, len(scanned_seq) - 2, 3):
            codon = scanned_seq[i:i + 3]

            if codon in start_codons:
                starts_in_frame.append(i)

            if codon in stop_codons:
                if starts_in_frame:
                    if longest_only_per_stop:
                        candidate_starts = [starts_in_frame[0]]
                    else:
                        candidate_starts = starts_in_frame[:]

                    for start_0 in candidate_starts:
                        length_nt = (i + 3) - start_0
                        peptide_len = (length_nt // 3) - 1

                        if peptide_len >= min_aa:
                            found.append(
                                _build_orf(
                                    scanned_seq=scanned_seq,
                                    original_seq_len=original_len,
                                    strand=strand,
                                    frame_offset=frame_offset,
                                    start_0=start_0,
                                    stop_0=i,
                                )
                            )

                starts_in_frame = []

    return _sort_orfs_biologically(found)


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
    )

    minus_orfs = find_coding_orfs_in_strand(
        sequence=seq,
        strand="-",
        min_aa=min_aa,
        start_codons=start_codons,
        stop_codons=stop_codons,
        longest_only_per_stop=longest_only_per_stop,
    )

    all_orfs = plus_orfs + minus_orfs
    return _sort_orfs_biologically(all_orfs)


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

    if not orfs:
        return None

    return orfs[0]


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
