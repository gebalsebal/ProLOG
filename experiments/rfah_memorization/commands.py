import argparse
import json
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from experiments.rfah_memorization.preflight import parse_help_flags


@dataclass(frozen=True, slots=True)
class RunConfig:
    colabfold_batch: Path
    fasta: Path
    out_dir: Path
    params_dir: Path
    amber: bool = False
    use_gpu_relax: bool = False
    single_sequence: bool = False


@dataclass(frozen=True, slots=True)
class CommandLog:
    command: list[str]
    supported_flags: dict[str, bool]
    executed: bool


def build_experiment_a(config: RunConfig) -> list[str]:
    command = [
        str(config.colabfold_batch),
        "--msa-mode",
        "single_sequence",
        "--model-type",
        "alphafold2_ptm",
        "--num-recycle",
        "0",
        "--num-models",
        "5",
        "--num-seeds",
        "5",
        "--random-seed",
        "0",
        "--data",
        str(config.params_dir),
    ]
    return _with_relax(command, config) + [str(config.fasta), str(config.out_dir)]


def build_experiment_b(config: RunConfig, supported_flags: dict[str, bool]) -> list[str]:
    command = [
        str(config.colabfold_batch),
        "--model-type",
        "alphafold2_ptm",
        "--num-recycle",
        "2",
        "--num-models",
        "1",
        "--model-order",
        "1",
        "--num-seeds",
        "1",
        "--random-seed",
        "0",
        "--data",
        str(config.params_dir),
    ]
    if config.single_sequence:
        command.extend(["--msa-mode", "single_sequence"])
    for flag in (
        "--save-recycles",
        "--save-all",
        "--save-single-representations",
        "--save-pair-representations",
    ):
        if supported_flags.get(flag, False):
            command.append(flag)
    return _with_relax(command, config) + [str(config.fasta), str(config.out_dir)]


def supported_flags_from_help(colabfold_batch: Path) -> dict[str, bool]:
    completed = subprocess.run(
        [str(colabfold_batch), "--help"], check=False, capture_output=True, text=True
    )
    return parse_help_flags(f"{completed.stdout}\n{completed.stderr}")


def write_command_log(log: CommandLog, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "command.json"
    payload = asdict(log) | {"shell_command": shlex.join(log.command)}
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def run_command(log: CommandLog, log_dir: Path) -> int:
    write_command_log(log, log_dir)
    if not log.executed:
        print(shlex.join(log.command))
        return 0
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    with stdout_path.open("w") as stdout_handle, stderr_path.open("w") as stderr_handle:
        completed = subprocess.run(
            log.command,
            check=False,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
    return completed.returncode


def _with_relax(command: list[str], config: RunConfig) -> list[str]:
    result = [*command]
    if config.amber:
        result.append("--amber")
    if config.use_gpu_relax:
        result.append("--use-gpu-relax")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or run RfaH ColabFold experiment commands."
    )
    parser.add_argument("experiment", choices=("A", "B"))
    parser.add_argument(
        "--colabfold-batch",
        type=Path,
        default=Path("/opt/conda/envs/colabfold/bin/colabfold_batch"),
    )
    parser.add_argument("--fasta", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--params-dir", type=Path, default=Path("/data/params"))
    parser.add_argument("--amber", action="store_true")
    parser.add_argument("--use-gpu-relax", action="store_true")
    parser.add_argument("--single-sequence", action="store_true")
    parser.add_argument("--run", action="store_true", help="Actually execute colabfold_batch.")
    args = parser.parse_args()
    config = RunConfig(
        colabfold_batch=args.colabfold_batch,
        fasta=args.fasta,
        out_dir=args.out_dir,
        params_dir=args.params_dir,
        amber=args.amber,
        use_gpu_relax=args.use_gpu_relax,
        single_sequence=args.single_sequence,
    )
    flags = supported_flags_from_help(args.colabfold_batch)
    command = (
        build_experiment_a(config)
        if args.experiment == "A"
        else build_experiment_b(config, flags)
    )
    log = CommandLog(command=command, supported_flags=flags, executed=args.run)
    return run_command(log, args.out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
