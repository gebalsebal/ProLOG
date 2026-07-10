from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FastaRecord:
    header: str
    sequence: str


@dataclass(frozen=True, slots=True)
class FastaFormatError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail


def parse_fasta(text: str) -> FastaRecord:
    """Parse a single-record FASTA file."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith(">"):
        raise FastaFormatError("expected a FASTA header on the first non-empty line")
    headers = [line for line in lines if line.startswith(">")]
    if len(headers) != 1:
        raise FastaFormatError("expected exactly one FASTA record")
    sequence = "".join(line for line in lines[1:] if not line.startswith(">"))
    if not sequence:
        raise FastaFormatError("expected a non-empty FASTA sequence")
    return FastaRecord(header=lines[0][1:], sequence=sequence)


def read_fasta(path: Path) -> FastaRecord:
    return parse_fasta(path.read_text())


def write_fasta(record: FastaRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f">{record.header}"]
    lines.extend(record.sequence[start : start + 60] for start in range(0, len(record.sequence), 60))
    path.write_text("\n".join(lines) + "\n")


def extract_range(record: FastaRecord, start: int, end: int, name: str) -> FastaRecord:
    """Extract a one-index inclusive residue range."""
    if start < 1 or end < start or end > len(record.sequence):
        raise FastaFormatError(
            f"invalid one-index range {start}-{end} for length {len(record.sequence)}"
        )
    accession = _accession(record.header)
    return FastaRecord(
        header=f"{name}|{accession}|residues_{start}_{end}",
        sequence=record.sequence[start - 1 : end],
    )


def _accession(header: str) -> str:
    fields = header.split("|")
    if len(fields) >= 2 and fields[1]:
        return fields[1]
    return header.split()[0]
