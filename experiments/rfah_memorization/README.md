# RfaH ColabFold Memorization Experiments

This directory contains a reproducible, local-only framework for RfaH ColabFold experiments. The scripts do not install packages and do not run predictions unless `--run` is passed to the command builder.

## Preflight

Record environment, parameter availability, and locally supported `colabfold_batch` flags:

```bash
/opt/conda/envs/colabfold/bin/python -m experiments.rfah_memorization.preflight \
  --colabfold-batch /opt/conda/envs/colabfold/bin/colabfold_batch \
  --params-dir /data/params \
  --out-dir experiments/rfah_memorization/runs/preflight
```

The preflight JSON records availability of `--msa-mode`, `--num-recycle`, `--num-seeds`, `--num-models`, `--model-type`, `--use-dropout`, `--save-recycles`, `--save-pair-representations`, `--save-single-representations`, `--save-all`, `--amber`, `--use-gpu-relax`, and `--data`.

## Prepare Data

Create full-length P0AFW0 FASTA, CTD 115-162 FASTA, and reference manifests:

```bash
/opt/conda/envs/colabfold/bin/python -m experiments.rfah_memorization.prepare_data \
  --root /app/alphafold \
  --out-dir experiments/rfah_memorization/data/prepared
```

The CTD file is `rfah_ctd_115_162.fasta` because AF2_benchmark `data/range_fs_pairs_test.txt` and `SPEACH_AF/SPEACH_AF_contacts/range_fs_pairs_all.txt` explicitly record RfaH fold-switching region 115-162 for `2oug_C/6c6s_D`. The manifest references local downloaded `2OUG`, `6C6S`, and `2LCL` structures, AF2_benchmark clean chains, `plots/figure_4/*.pdb`, and `plots/figure_s12/*` when present. `2LCL` is noted as the Burmann NMR beta reference for broader C-terminal domain context.

## Experiment A: Isolated CTD, Single Sequence

Build and log the command without running prediction:

```bash
/opt/conda/envs/colabfold/bin/python -m experiments.rfah_memorization.commands A \
  --fasta experiments/rfah_memorization/data/prepared/rfah_ctd_115_162.fasta \
  --out-dir experiments/rfah_memorization/runs/experiment_a \
  --params-dir /data/params
```

This logs the equivalent of:

```bash
colabfold_batch --msa-mode single_sequence --model-type alphafold2_ptm \
  --num-recycle 0 --num-models 5 --num-seeds 5 --random-seed 0 \
  --data /data/params <ctd_fasta> <out_dir>
```

Relaxation is intentionally off by default. Add `--amber --use-gpu-relax` only when relaxation is needed and the runtime cost is acceptable. Add `--run` to execute the logged command.

## Experiment B: Full-Length RfaH

Build and log the command without running prediction:

```bash
/opt/conda/envs/colabfold/bin/python -m experiments.rfah_memorization.commands B \
  --fasta experiments/rfah_memorization/data/prepared/rfah_full_p0afw0.fasta \
  --out-dir experiments/rfah_memorization/runs/experiment_b \
  --params-dir /data/params
```

Experiment B uses MMseqs MSA mode by default, `--num-recycle 2`, and includes `--save-recycles`, `--save-all`, and `--save-pair-representations` when the local help output supports them. Pass `--single-sequence` to force single-sequence MSA mode. Add `--run` only when ready to run long ColabFold predictions.

## Analyze Outputs

After predictions exist, summarize PDBs into CSV tables:

```bash
/opt/conda/envs/colabfold/bin/python -m experiments.rfah_memorization.analysis \
  --input-dir experiments/rfah_memorization/runs \
  --out-dir experiments/rfah_memorization/analysis
```

The analysis parses pLDDT from PDB B-factors and nearby ColabFold JSON when available. If DSSP or TM-align is unavailable, outputs use `NA` for those fields and write `qa_checks.csv` rows. Secondary-structure values are labeled heuristics: helix signal from CA(i)-CA(i+4) distances in 5.0-7.0 A, beta signal from nonlocal CA contacts in 4.5-8.5 A separated by at least five residues.

## Final Report

```bash
/opt/conda/envs/colabfold/bin/python -m experiments.rfah_memorization.write_report \
  --predictions-csv experiments/rfah_memorization/analysis/predictions.csv \
  --qa-checks-csv experiments/rfah_memorization/analysis/qa_checks.csv \
  --out experiments/rfah_memorization/reports/final_report.md
```

## Tests

The requested ColabFold interpreter may not include `pytest`. If available, run:

```bash
/opt/conda/envs/colabfold/bin/python -m pytest experiments/rfah_memorization/tests
```

Otherwise use the repository Python that has pytest installed:

```bash
python -m pytest experiments/rfah_memorization/tests
```
