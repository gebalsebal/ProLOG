import argparse
import csv
from pathlib import Path


def write_report(predictions_csv: Path, qa_checks_csv: Path, out_path: Path) -> Path:
    predictions = _read_csv(predictions_csv)
    qa_rows = _read_csv(qa_checks_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_report_text(predictions_csv, qa_checks_csv, predictions, qa_rows))
    return out_path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _report_text(
    predictions_csv: Path, qa_checks_csv: Path, predictions: list[dict[str, str]], qa_rows: list[dict[str, str]]
) -> str:
    missing = [row["item"] for row in qa_rows if row.get("status") == "missing"]
    return "\n".join(
        [
            "# RfaH ColabFold Memorization Report",
            "",
            "## Inputs",
            "- Full-length RfaH uses UniProt P0AFW0 from `data/references/RfaH_full.fasta`.",
            "- CTD FASTA is residues 115-162 because AF2_benchmark records 2oug_C/6c6s_D fold-switching region 115-162.",
            "- 2LCL is treated as the Burmann NMR beta reference in broader C-terminal domain context.",
            "",
            "## Outputs Analyzed",
            f"- Prediction rows: {len(predictions)} from `{predictions_csv}`.",
            f"- QA checks: `{qa_checks_csv}`.",
            "",
            "## Methods Note",
            "- DSSP/TM-align are optional. When absent, TM-align fields are NA and secondary-structure labels use a coordinate heuristic.",
            "- Heuristic helix_pct is the fraction of CA(i)-CA(i+4) distances in 5.0-7.0 A.",
            "- Heuristic beta_pct is conservatively normalized from nonlocal CA contacts in 4.5-8.5 A separated by at least five residues.",
            "",
            "## QA Summary",
            f"- Missing optional tools: {', '.join(missing) if missing else 'none'}.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a concise RfaH experiment report.")
    parser.add_argument("--predictions-csv", type=Path, required=True)
    parser.add_argument("--qa-checks-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("experiments/rfah_memorization/reports/final_report.md"))
    args = parser.parse_args()
    print(write_report(args.predictions_csv, args.qa_checks_csv, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
