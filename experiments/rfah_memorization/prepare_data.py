import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from experiments.rfah_memorization.fasta_tools import extract_range, read_fasta, write_fasta


@dataclass(frozen=True, slots=True)
class PreparedData:
    full_fasta: str
    ctd_fasta: str
    ctd_boundary_json: str
    manifest_csv: str
    manifest_json: str


@dataclass(frozen=True, slots=True)
class ManifestRow:
    role: str
    path: str
    present: str
    note: str


def prepare_data(root: Path, out_dir: Path) -> PreparedData:
    references = root / "experiments/rfah_memorization/data/references"
    benchmark = root / "AF2_benchmark"
    out_dir.mkdir(parents=True, exist_ok=True)
    full_record = read_fasta(references / "RfaH_full.fasta")
    full_path = out_dir / "rfah_full_p0afw0.fasta"
    ctd_path = out_dir / "rfah_ctd_115_162.fasta"
    boundary_path = out_dir / "ctd_boundary.json"
    write_fasta(full_record, full_path)
    write_fasta(extract_range(full_record, 115, 162, "rfah_ctd_115_162"), ctd_path)
    _write_boundary(boundary_path)
    rows = _manifest_rows(root, references, benchmark, full_path, ctd_path)
    manifest_csv = out_dir / "reference_manifest.csv"
    manifest_json = out_dir / "reference_manifest.json"
    _write_manifest_csv(rows, manifest_csv)
    manifest_json.write_text(json.dumps([asdict(row) for row in rows], indent=2) + "\n")
    return PreparedData(
        full_fasta=str(full_path),
        ctd_fasta=str(ctd_path),
        ctd_boundary_json=str(boundary_path),
        manifest_csv=str(manifest_csv),
        manifest_json=str(manifest_json),
    )


def _write_boundary(path: Path) -> None:
    payload = {
        "protein": "E. coli RfaH",
        "uniprot": "P0AFW0",
        "ctd_start": 115,
        "ctd_end": 162,
        "coordinate_system": "UniProt one-index inclusive residues",
        "primary_source": "AF2_benchmark data/range_fs_pairs_test.txt and SPEACH_AF/SPEACH_AF_contacts/range_fs_pairs_all.txt",
        "primary_source_entry": "2oug_C,6c6s_D,115-162,115-162,115-162,115-162",
        "beta_reference_note": "2LCL is the Burmann et al. isolated RfaH CTD NMR beta reference in broader C-terminal domain context.",
        "reason": "Use the exact fold-switching region used by the Chakravarty et al. AF2_benchmark assets instead of guessing a CTD boundary.",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _manifest_rows(
    root: Path, references: Path, benchmark: Path, full_path: Path, ctd_path: Path
) -> list[ManifestRow]:
    paths = [
        ("input_fasta", full_path, "P0AFW0 full-length RfaH copied from downloaded reference FASTA"),
        ("input_fasta", ctd_path, "CTD 115-162 from AF2_benchmark fold-switching ranges"),
        ("reference", references / "2OUG.pdb", "RfaH alpha reference downloaded locally"),
        ("reference", references / "6C6S.pdb", "RfaH beta/autoinhibited reference downloaded locally"),
        ("reference", references / "2LCL.pdb", "Burmann NMR beta reference; broader C-terminal domain context"),
        ("af2_benchmark_clean_chain", benchmark / "data/clean_chains/2oug_C.pdb", "clean RfaH 2oug_C chain"),
        ("af2_benchmark_clean_chain", benchmark / "data/clean_chains/6c6s_D.pdb", "clean RfaH 6c6s_D chain"),
        ("af2_benchmark_range", benchmark / "data/range_fs_pairs_test.txt", "records RfaH 115-162 test range"),
        ("af2_benchmark_range", benchmark / "SPEACH_AF/SPEACH_AF_contacts/range_fs_pairs_all.txt", "records RfaH 115-162 all-set range"),
    ]
    rows = [_row(role, path, note) for role, path, note in paths]
    rows.extend(_glob_rows("af2_benchmark_figure_4", benchmark / "plots/figure_4", "*.pdb"))
    rows.extend(_glob_rows("af2_benchmark_figure_s12", benchmark / "plots/figure_s12", "**/*"))
    return [_relative_row(root, row) for row in rows]


def _row(role: str, path: Path, note: str) -> ManifestRow:
    return ManifestRow(role=role, path=str(path), present=str(path.exists()), note=note)


def _glob_rows(role: str, directory: Path, pattern: str) -> list[ManifestRow]:
    return [
        _row(role, path, "AF2_benchmark support asset")
        for path in sorted(directory.glob(pattern))
        if path.is_file()
    ]


def _relative_row(root: Path, row: ManifestRow) -> ManifestRow:
    path = Path(row.path)
    try:
        display = path.relative_to(root)
    except ValueError:
        display = path
    return ManifestRow(role=row.role, path=str(display), present=row.present, note=row.note)


def _write_manifest_csv(rows: list[ManifestRow], path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["role", "path", "present", "note"])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare RfaH FASTA files and reference manifests.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out-dir", type=Path, default=Path("experiments/rfah_memorization/data/prepared"))
    args = parser.parse_args()
    print(json.dumps(asdict(prepare_data(args.root, args.out_dir)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
