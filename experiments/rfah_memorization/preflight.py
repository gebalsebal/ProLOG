import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final


REQUIRED_FLAGS: Final[tuple[str, ...]] = (
    "--msa-mode",
    "--num-recycle",
    "--num-seeds",
    "--num-models",
    "--model-type",
    "--use-dropout",
    "--save-recycles",
    "--save-pair-representations",
    "--save-single-representations",
    "--save-all",
    "--amber",
    "--use-gpu-relax",
    "--data",
)


@dataclass(frozen=True, slots=True)
class PreflightRecord:
    python: str
    platform: str
    colabfold_batch: str
    colabfold_help_exit_code: int
    requested_flags: dict[str, bool]
    params_dir: str
    params_present: bool


def parse_help_flags(help_text: str) -> dict[str, bool]:
    return {flag: flag in help_text for flag in REQUIRED_FLAGS}


def collect_preflight(colabfold_batch: Path, params_dir: Path) -> PreflightRecord:
    completed = subprocess.run(
        [str(colabfold_batch), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    help_text = f"{completed.stdout}\n{completed.stderr}"
    return PreflightRecord(
        python=sys.executable,
        platform=platform.platform(),
        colabfold_batch=str(colabfold_batch),
        colabfold_help_exit_code=completed.returncode,
        requested_flags=parse_help_flags(help_text),
        params_dir=str(params_dir),
        params_present=_params_present(params_dir),
    )


def write_preflight(record: PreflightRecord, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "preflight.json"
    path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + "\n")
    return path


def _params_present(params_dir: Path) -> bool:
    return all((params_dir / f"params_model_{index}_ptm.npz").exists() for index in range(1, 6))


def main() -> int:
    parser = argparse.ArgumentParser(description="Record RfaH ColabFold preflight information.")
    parser.add_argument("--colabfold-batch", default=shutil.which("colabfold_batch") or "colabfold_batch")
    parser.add_argument("--params-dir", type=Path, default=Path("/data/params"))
    parser.add_argument("--out-dir", type=Path, default=Path("experiments/rfah_memorization/runs/preflight"))
    args = parser.parse_args()
    path = write_preflight(collect_preflight(Path(args.colabfold_batch), args.params_dir), args.out_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
