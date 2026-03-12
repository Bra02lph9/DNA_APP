from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .utils import reverse_complement


@dataclass
class ORF:
    strand: str
    frame: int
    start: int
    end: int
    length_nt: int
    sequence: str
    peptide_length_aa: int


def _map_rev_to_forward(
    rev_start_0: int,
    rev_end_0_exclusive: int,
    original_len: int
) -> tuple[int, int]:
    forward_start_0 = original_len - rev_end_0_exclusive
    forward_end_0_exclusive = original_len - rev_start_0
    return forward_start_0 + 1, forward_end_0_exclusive


def find_orfs_in_strand(sequence: str, strand: str = "+") -> List[ORF]:
    search_seq = sequence if strand == "+" else reverse_complement(sequence)
    original_len = len(sequence)
    frames: List[ORF] = []

    for offset in range(3):
        usable_len = len(search_seq) - offset
        usable_len -= usable_len % 3

        if usable_len < 3:
            continue

        start_0 = offset
        end_0_exclusive = offset + usable_len
        frame_seq = search_seq[start_0:end_0_exclusive]

        if strand == "+":
            start = start_0 + 1
            end = end_0_exclusive
        else:
            start, end = _map_rev_to_forward(start_0, end_0_exclusive, original_len)

        frames.append(
            ORF(
                strand=strand,
                frame=offset + 1,
                start=start,
                end=end,
                length_nt=len(frame_seq),
                sequence=frame_seq,
                peptide_length_aa=len(frame_seq) // 3,
            )
        )

    return frames


def find_all_orfs(sequence: str) -> List[ORF]:
    return find_orfs_in_strand(sequence, "+") + find_orfs_in_strand(sequence, "-")


def format_orfs(orfs: List[ORF]) -> str:
    if not orfs:
        return "No reading frames found."

    lines = [f"Detected {len(orfs)} reading frame(s):", ""]

    for idx, orf in enumerate(orfs, start=1):
        lines.extend(
            [
                f"Frame {idx}",
                f"  Strand: {orf.strand}",
                f"  Frame: {orf.frame}",
                f"  Positions: {orf.start}..{orf.end}",
                f"  Length: {orf.length_nt} nt ({orf.peptide_length_aa} codons)",
                f"  Sequence: {orf.sequence[:90]}{'...' if len(orf.sequence) > 90 else ''}",
                "",
            ]
        )

    return "\n".join(lines)
