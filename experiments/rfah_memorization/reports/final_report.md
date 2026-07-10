# RfaH ColabFold Memorization Report

## Environment
- Branch/workspace: `/app/alphafold` on `af_bias`.
- ColabFold: `colabfold_batch` from `/opt/conda/envs/colabfold/bin/colabfold_batch`, version 1.6.1.
- AlphaFold package: `alphafold-colabfold` 2.3.13, described by the package as AlphaFold v2.3.1 patched for ColabFold.
- JAX/JAXLIB: 0.4.26.
- Requested CLI flags were present: `--msa-mode`, `--num-recycle`, `--num-seeds`, `--num-models`, `--model-type`, `--use-dropout`, `--save-recycles`, `--save-pair-representations`, `--save-single-representations`, `--save-all`, `--amber`, `--use-gpu-relax`, `--data`.
- GPU hardware was visible (`NVIDIA GeForce RTX 5090`), but JAX GPU compilation failed before prediction with `ptxas fatal: Program with .target 'sm_90a' cannot be compiled to future architecture`.
- The ColabFold env also lacked `flax`; base conda had `flax 0.8.4`, so runs used `PYTHONPATH=/opt/conda/lib/python3.11/site-packages` plus `JAX_PLATFORMS=cpu` as a no-install fallback.

## Inputs
- Full-length RfaH uses UniProt P0AFW0 from `experiments/rfah_memorization/data/references/RfaH_full.fasta`.
- CTD FASTA is residues 115-162 because `AF2_benchmark/data/range_fs_pairs_test.txt` and `AF2_benchmark/SPEACH_AF/SPEACH_AF_contacts/range_fs_pairs_all.txt` record `2oug_C,6c6s_D,115-162,115-162,115-162,115-162`.
- References downloaded: `2OUG`, `6C6S`, and `2LCL`. `2LCL` is treated as the Burmann et al. isolated RfaH CTD NMR beta reference in broader C-terminal domain context.
- Reusable author assets found locally: `AF2_benchmark/plots/figure_4/*.pdb`, `AF2_benchmark/plots/figure_s12/*`, `AF2_benchmark/data/FigS13/a/rfah_ctd_monomer_25.pse`, and clean chains `2oug_C`/`6c6s_D`.

## Experiment A: CTD Single Sequence, 0 Recycle
- Command log: `experiments/rfah_memorization/runs/experiment_a_cpu/command.json`.
- Output table: `experiments/rfah_memorization/tables/experiment_a_predictions.csv`.
- Result: 25/25 models were classified as `helical_bundle_like` by the coordinate heuristic.
- Mean pLDDT range from PDB B-factors: 61.80 to 71.41.
- This qualitatively matches the paper's core memorization result: single-sequence, zero-recycle RfaH CTD predictions prefer the helical/autoinhibited-like fold instead of the experimentally isolated beta CTD fold.

## Experiment B: Recycle Trajectory
- A direct CPU fallback full-length run produced partial recycle outputs before the 30-minute command timeout: R0 and R1 PDBs under `experiments/rfah_memorization/runs/experiment_b_cpu/`.
- Partial direct run table: `experiments/rfah_memorization/tables/experiment_b_recycles.csv`.
- Direct partial result: R0 was `beta_contact_rich`; R1 became `mixed_or_low_signal`. R2/final did not complete within the CPU timeout because GPU JAX compilation is unavailable in this environment.
- Author-provided Figure 4 assets in `AF2_benchmark/plots/figure_4/` provide the complete R0/R1/R2 trajectory. Table: `experiments/rfah_memorization/tables/af2_benchmark_figure4/predictions.csv`.
- Author asset trajectory result: R0 `beta_contact_rich`, R1 `mixed_or_low_signal`, R2 `helical_bundle_like`, matching the paper's qualitative beta-to-alpha recycle transition.

## Methods Note
- `mkdssp`, `TMalign`, `USalign`, and `tmtools` were not installed; per the no-install constraint, TM-score fields are `NA` and secondary-structure labels use a coordinate heuristic.
- Heuristic helix percentage is the fraction of CA(i)-CA(i+4) distances in 5.0-7.0 A.
- Heuristic beta percentage is conservatively normalized from nonlocal CA contacts in 4.5-8.5 A separated by at least five residues.
- For full-length structures, the analysis reports only residues 115-162 when those residues are present; for isolated CTD predictions, it reports the whole 48-residue prediction.

## QA Summary
- Tests: `python -m pytest experiments/rfah_memorization/tests` passed.
- Syntax check: `python -m py_compile` passed for all new Python modules.
- Missing optional tools recorded in `experiments/rfah_memorization/tables/qa_checks.csv`: `mkdssp`, `TMalign`.
- Main limitation: GPU execution could not be used with the installed JAX/JAXLIB on RTX 5090; CPU fallback completed Experiment A and partially completed direct Experiment B.
