from pathlib import Path

from experiments.rfah_memorization.analysis import classify_tools, parse_prediction_name
from experiments.rfah_memorization.commands import RunConfig, build_experiment_b
from experiments.rfah_memorization.fasta_tools import extract_range, parse_fasta
from experiments.rfah_memorization.preflight import REQUIRED_FLAGS, parse_help_flags


def test_parse_help_flags_when_colabfold_help_lists_requested_flags() -> None:
    # Given: help text with the RfaH framework's required ColabFold flags.
    help_text = "\n".join(f"  {flag} VALUE" for flag in REQUIRED_FLAGS)

    # When: the help text is parsed.
    flags = parse_help_flags(help_text)

    # Then: every requested flag is recorded as available.
    assert flags == {flag: True for flag in REQUIRED_FLAGS}


def test_extract_range_when_rfah_ctd_region_is_requested() -> None:
    # Given: the downloaded full-length RfaH FASTA content.
    fasta_text = Path(
        "experiments/rfah_memorization/data/references/RfaH_full.fasta"
    ).read_text()
    record = parse_fasta(fasta_text)

    # When: residues 115-162 are extracted using AF2_benchmark coordinates.
    ctd = extract_range(record, 115, 162, "rfah_ctd_115_162")

    # Then: the isolated CTD sequence is one-index inclusive and length 48.
    assert ctd.header == "rfah_ctd_115_162|P0AFW0|residues_115_162"
    assert len(ctd.sequence) == 48
    assert ctd.sequence == "KVIITEGAFEGFQAIFTEPDGEARSMLLLNLINKEIKHSVKNTEFRKL"


def test_classify_tools_when_dssp_and_tmalign_are_missing() -> None:
    # Given: PATH lookup results without optional structural tools.
    lookup = {"mkdssp": None, "TMalign": None}

    # When: tool availability is classified.
    rows = classify_tools(lookup)

    # Then: unavailable tools become qa_checks rows instead of hard failures.
    assert rows == [
        {
            "check": "optional_tool",
            "item": "mkdssp",
            "status": "missing",
            "detail": "DSSP unavailable; using labeled coordinate heuristic",
        },
        {
            "check": "optional_tool",
            "item": "TMalign",
            "status": "missing",
            "detail": "TM-align unavailable; writing NA structural alignment fields",
        },
    ]


def test_parse_prediction_name_when_colabfold_recycle_filename() -> None:
    # Given: a ColabFold output filename with rank, model, seed, and recycle.
    name = "RfaH_unrelaxed_rank_001_alphafold2_model_2_seed_003.r2.pdb"

    # When: prediction metadata is parsed from the filename.
    parsed = parse_prediction_name(name)

    # Then: numeric fields are normalized for CSV output.
    assert parsed.target == "RfaH"
    assert parsed.rank == 1
    assert parsed.model == 2
    assert parsed.seed == 3
    assert parsed.recycle == 2


def test_parse_prediction_name_when_save_recycles_omits_rank() -> None:
    # Given: a save-recycles output filename before ranking is available.
    name = "RfaH_unrelaxed_alphafold2_ptm_model_1_seed_000.r1.pdb"

    # When: prediction metadata is parsed from the filename.
    parsed = parse_prediction_name(name)

    # Then: model, seed, and recycle are still captured.
    assert parsed.target == "RfaH"
    assert parsed.rank is None
    assert parsed.model == 1
    assert parsed.seed == 0
    assert parsed.recycle == 1


def test_build_experiment_b_when_saving_recycles_is_supported() -> None:
    # Given: supported representation flags and a full-length FASTA input.
    config = RunConfig(
        colabfold_batch=Path("colabfold_batch"),
        fasta=Path("rfah_full_p0afw0.fasta"),
        out_dir=Path("out_b"),
        params_dir=Path("/data/params"),
    )
    supported = {
        "--save-recycles": True,
        "--save-all": True,
        "--save-single-representations": True,
        "--save-pair-representations": True,
    }

    # When: the Experiment B command is built.
    command = build_experiment_b(config, supported)

    # Then: the recycle trajectory MVP runs one model/seed and saves supported artifacts.
    assert "--num-models" in command
    assert command[command.index("--num-models") + 1] == "1"
    assert command[command.index("--num-seeds") + 1] == "1"
    assert "--save-recycles" in command
    assert "--save-single-representations" in command
    assert "--save-pair-representations" in command
