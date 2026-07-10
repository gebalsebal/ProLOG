import argparse
import csv
import json
import math
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypeAlias

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]

PREDICTION_RE = re.compile(
    r"^(?P<target>.+?)_(?:(?:unrelaxed_|relaxed_)?rank_(?P<rank>\d+)_)?.*?"
    r"model_(?P<model>\d+)_seed_(?P<seed>\d+)(?:\.r(?P<recycle>\d+))?\.pdb$"
)


@dataclass(frozen=True, slots=True)
class PredictionName:
    target: str
    rank: int | None
    model: int | None
    seed: int | None
    recycle: int | None


@dataclass(frozen=True, slots=True)
class AtomCa:
    residue: int
    x: float
    y: float
    z: float
    bfactor: float


@dataclass(frozen=True, slots=True)
class AnalysisRow:
    experiment: str
    file: str
    target: str
    rank: str
    model: str
    seed: str
    recycle: str
    mean_plddt_bfactor: str
    mean_plddt_score_json: str
    residue_count_analyzed: str
    helix_pct_heuristic: str
    beta_pct_heuristic: str
    classification: str
    dssp_source: str
    tm_align_status: str


def parse_prediction_name(name: str) -> PredictionName:
    match = PREDICTION_RE.match(name)
    if match is None:
        return PredictionName(target=Path(name).stem, rank=None, model=None, seed=None, recycle=None)
    groups = match.groupdict()
    return PredictionName(
        target=groups["target"],
        rank=_int_or_none(groups["rank"]),
        model=int(groups["model"]),
        seed=int(groups["seed"]),
        recycle=_int_or_none(groups["recycle"]),
    )


def classify_tools(lookup: dict[str, str | None] | None = None) -> list[dict[str, str]]:
    tools = lookup if lookup is not None else {"mkdssp": shutil.which("mkdssp"), "TMalign": shutil.which("TMalign")}
    rows: list[dict[str, str]] = []
    details = {
        "mkdssp": "DSSP unavailable; using labeled coordinate heuristic",
        "TMalign": "TM-align unavailable; writing NA structural alignment fields",
    }
    for tool, detail in details.items():
        status = "available" if tools.get(tool) else "missing"
        rows.append({"check": "optional_tool", "item": tool, "status": status, "detail": detail if status == "missing" else str(tools[tool])})
    return rows


def analyze_outputs(input_dir: Path, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    qa_rows = classify_tools()
    rows = [_analyze_pdb(path, input_dir) for path in sorted(input_dir.rglob("*.pdb"))]
    predictions_csv = out_dir / "predictions.csv"
    qa_csv = out_dir / "qa_checks.csv"
    _write_dataclass_csv(rows, predictions_csv, AnalysisRow)
    _write_dataclass_csv(_filter_rows(rows, "experiment_a"), out_dir / "experiment_a_predictions.csv", AnalysisRow)
    _write_dataclass_csv(_filter_rows(rows, "experiment_b"), out_dir / "experiment_b_recycles.csv", AnalysisRow)
    _write_dict_csv(qa_rows, qa_csv, ["check", "item", "status", "detail"])
    return predictions_csv, qa_csv


def ca_atoms_from_pdb(path: Path) -> list[AtomCa]:
    atoms: list[AtomCa] = []
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            atoms.append(
                AtomCa(
                    residue=int(line[22:26]),
                    x=float(line[30:38]),
                    y=float(line[38:46]),
                    z=float(line[46:54]),
                    bfactor=float(line[60:66]),
                )
            )
    return atoms


def heuristic_secondary_structure(atoms: list[AtomCa]) -> tuple[float, float]:
    if not atoms:
        return 0.0, 0.0
    helix_total = max(len(atoms) - 4, 1)
    helix_hits = sum(1 for index in range(len(atoms) - 4) if 5.0 <= _distance(atoms[index], atoms[index + 4]) <= 7.0)
    beta_contacts = 0
    for left_index, left in enumerate(atoms):
        for right in atoms[left_index + 5 :]:
            if 4.5 <= _distance(left, right) <= 8.5:
                beta_contacts += 1
    beta_pct = min(beta_contacts / (len(atoms) * 2), 1.0)
    return helix_hits / helix_total, beta_pct


def mean_plddt_from_bfactor(atoms: list[AtomCa]) -> float | None:
    if not atoms:
        return None
    return sum(atom.bfactor for atom in atoms) / len(atoms)


def mean_plddt_from_score_json(pdb_path: Path) -> float | None:
    candidates = [pdb_path.with_suffix(".json"), pdb_path.parent / "ranking_debug.json"]
    for path in candidates:
        if path.exists():
            value: JsonValue = json.loads(path.read_text())
            result = _plddt_from_json(value, pdb_path.stem)
            if result is not None:
                return result
    return None


def _analyze_pdb(path: Path, input_dir: Path) -> AnalysisRow:
    relative_path = path.relative_to(input_dir)
    parsed = parse_prediction_name(path.name)
    atoms = ca_atoms_from_pdb(path)
    signal_atoms = _ctd_or_all_atoms(atoms)
    helix_pct, beta_pct = heuristic_secondary_structure(signal_atoms)
    return AnalysisRow(
        experiment=relative_path.parts[0] if len(relative_path.parts) > 1 else input_dir.name,
        file=str(relative_path),
        target=parsed.target,
        rank=_format_int(parsed.rank),
        model=_format_int(parsed.model),
        seed=_format_int(parsed.seed),
        recycle=_format_int(parsed.recycle),
        mean_plddt_bfactor=_format_float(mean_plddt_from_bfactor(signal_atoms)),
        mean_plddt_score_json=_format_float(mean_plddt_from_score_json(path)),
        residue_count_analyzed=str(len(signal_atoms)),
        helix_pct_heuristic=_format_float(helix_pct),
        beta_pct_heuristic=_format_float(beta_pct),
        classification=_classification(helix_pct, beta_pct),
        dssp_source="coordinate_heuristic_labeled_not_dssp",
        tm_align_status="NA",
    )


def _ctd_or_all_atoms(atoms: list[AtomCa]) -> list[AtomCa]:
    ctd_atoms = [atom for atom in atoms if 115 <= atom.residue <= 162]
    return ctd_atoms if len(ctd_atoms) >= 20 else atoms


def _classification(helix_pct: float, beta_pct: float) -> str:
    if helix_pct > 0.5:
        return "helical_bundle_like"
    if beta_pct > 0.5:
        return "beta_contact_rich"
    return "mixed_or_low_signal"


def _plddt_from_json(value: JsonValue, stem: str) -> float | None:
    if isinstance(value, dict):
        plddt = value.get("plddt")
        if isinstance(plddt, int | float):
            return float(plddt)
        if isinstance(plddt, list):
            numbers = [float(item) for item in plddt if isinstance(item, int | float)]
            return sum(numbers) / len(numbers) if numbers else None
        ranking = value.get("plddts")
        if isinstance(ranking, dict):
            for key, item in ranking.items():
                if key in stem and isinstance(item, int | float):
                    return float(item)
    return None


def _distance(left: AtomCa, right: AtomCa) -> float:
    return math.sqrt((left.x - right.x) ** 2 + (left.y - right.y) ** 2 + (left.z - right.z) ** 2)


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value is not None else None


def _format_int(value: int | None) -> str:
    return "NA" if value is None else str(value)


def _format_float(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4f}"


def _write_dataclass_csv(rows: list[AnalysisRow], path: Path, row_type: type[AnalysisRow]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row_type.__dataclass_fields__))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _filter_rows(rows: list[AnalysisRow], prefix: str) -> list[AnalysisRow]:
    return [row for row in rows if row.experiment.startswith(prefix)]


def _write_dict_csv(rows: list[dict[str, str]], path: Path, fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze RfaH ColabFold output PDB files.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("experiments/rfah_memorization/analysis"))
    args = parser.parse_args()
    predictions_csv, qa_csv = analyze_outputs(args.input_dir, args.out_dir)
    print(json.dumps({"predictions_csv": str(predictions_csv), "qa_checks_csv": str(qa_csv)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
