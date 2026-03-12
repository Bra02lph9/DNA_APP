from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from Bio import SeqIO
from Bio.Seq import Seq


VALID_DNA = {"A", "T", "C", "G", "N"}
FASTA_EXTENSIONS = {".fasta", ".fa", ".fna", ".fas", ".txt"}


def is_fasta_file(file_path: str | Path) -> bool:
    return Path(file_path).suffix.lower() in FASTA_EXTENSIONS


def load_fasta_sequence(file_path: str) -> tuple[str, str]:
    record = next(SeqIO.parse(file_path, "fasta"), None)
    if record is None:
        raise ValueError(f"No FASTA record found in file: {file_path}")

    sequence = str(record.seq).upper().replace("\n", "").replace("\r", "")
    validate_dna(sequence)
    return record.id, sequence


def load_all_fasta_sequences(file_path: str) -> list[tuple[str, str]]:
    records = list(SeqIO.parse(file_path, "fasta"))
    if not records:
        raise ValueError(f"No FASTA record found in file: {file_path}")

    results: list[tuple[str, str]] = []
    for record in records:
        sequence = str(record.seq).upper().replace("\n", "").replace("\r", "")
        validate_dna(sequence)
        results.append((record.id, sequence))

    return results


def load_fasta_folder(folder_path: str) -> list[dict]:
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

    all_sequences: list[dict] = []

    for fasta_file in fasta_files:
        records = load_all_fasta_sequences(str(fasta_file))
        for header, sequence in records:
            all_sequences.append(
                {
                    "file": fasta_file.name,
                    "header": header,
                    "sequence": sequence,
                }
            )

    return all_sequences


def validate_dna(sequence: str) -> None:
    if not sequence:
        raise ValueError("Sequence is empty.")
    invalid = sorted(set(sequence.upper()) - VALID_DNA)
    if invalid:
        raise ValueError(f"Invalid DNA characters found: {', '.join(invalid)}")


def reverse_complement(sequence: str) -> str:
    return str(Seq(sequence).reverse_complement())


def hamming_distance(a: str, b: str) -> int:
    if len(a) != len(b):
        raise ValueError("Strings must have the same length.")
    return sum(1 for x, y in zip(a, b) if x != y)


def chunk_string(sequence: str, width: int = 80) -> str:
    return "\n".join(sequence[i:i + width] for i in range(0, len(sequence), width))


def safe_fragment(sequence: str, start: int, end: int) -> str:
    start = max(0, start)
    end = min(len(sequence), end)
    return sequence[start:end]
