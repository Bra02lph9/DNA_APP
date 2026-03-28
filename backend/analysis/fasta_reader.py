from __future__ import annotations

from pathlib import Path
from typing import Generator

from Bio import SeqIO

from analysis.utils import is_fasta_file, validate_dna


def normalize_sequence(sequence: str) -> str:
    return sequence.upper().replace("\n", "").replace("\r", "").replace(" ", "")


def read_first_fasta_record(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if not is_fasta_file(path):
        raise ValueError(f"Unsupported FASTA file extension: {file_path}")

    record = next(SeqIO.parse(str(path), "fasta"), None)
    if record is None:
        raise ValueError(f"No FASTA record found in file: {file_path}")

    sequence = normalize_sequence(str(record.seq))
    validate_dna(sequence)

    return {
        "file": path.name,
        "header": record.id,
        "sequence": sequence,
    }


def read_all_fasta_records(file_path: str) -> list[dict]:
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if not is_fasta_file(path):
        raise ValueError(f"Unsupported FASTA file extension: {file_path}")

    results: list[dict] = []

    for record in SeqIO.parse(str(path), "fasta"):
        sequence = normalize_sequence(str(record.seq))
        validate_dna(sequence)

        results.append(
            {
                "file": path.name,
                "header": record.id,
                "sequence": sequence,
            }
        )

    if not results:
        raise ValueError(f"No FASTA record found in file: {file_path}")

    return results


def iter_fasta_records(file_path: str) -> Generator[dict, None, None]:
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if not is_fasta_file(path):
        raise ValueError(f"Unsupported FASTA file extension: {file_path}")

    found = False

    for record in SeqIO.parse(str(path), "fasta"):
        found = True
        sequence = normalize_sequence(str(record.seq))
        validate_dna(sequence)

        yield {
            "file": path.name,
            "header": record.id,
            "sequence": sequence,
        }

    if not found:
        raise ValueError(f"No FASTA record found in file: {file_path}")


def iter_fasta_folder(folder_path: str) -> Generator[dict, None, None]:
    folder = Path(folder_path)

    if not folder.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")

    if not folder.is_dir():
        raise ValueError(f"Path is not a folder: {folder_path}")

    fasta_files = sorted(
        [p for p in folder.iterdir() if p.is_file() and is_fasta_file(p)]
    )

    if not fasta_files:
        raise ValueError(f"No FASTA files found in folder: {folder_path}")

    for fasta_file in fasta_files:
        for record in iter_fasta_records(str(fasta_file)):
            yield record


def split_sequence_into_chunks(sequence: str, chunk_size: int, overlap: int = 0) -> Generator[dict, None, None]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")

    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    sequence = normalize_sequence(sequence)
    validate_dna(sequence)

    step = chunk_size - overlap
    seq_len = len(sequence)

    for start in range(0, seq_len, step):
        end = min(start + chunk_size, seq_len)

        yield {
            "chunk_start": start + 1,
            "chunk_end": end,
            "sequence": sequence[start:end],
        }

        if end == seq_len:
            break
