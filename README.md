# Disinformation, Financial Fragility, and Downside Growth Risk

James Rice, Council for Countering Online Disinformation — September 2026 revision

The manuscript, empirical code, selected Lean formalizations, frozen data, and
regenerated outputs are versioned together. This revision corrects the empirical
implementation and narrows the conclusions to what the data support.

## Interpretation

- The DSP index measures the broad political information environment, not the
  fraction of financial messages that are false.
- Local projections describe conditional associations. They do not identify
  structural innovations, intervention effects, or policy cost-effectiveness.
- The revised growth–banking-stress interaction is negative. Sample restrictions
  and covariate definitions matter; see the full robustness table.
- Country-block bootstrap inference does **not** distinguish the tenth-quantile
  slope from the median or ninetieth. The original threefold-tail claim is withdrawn.
- Adding the index worsens tenth-quantile forecast loss by about 3.2% in the
  reported pseudo out-of-sample design (interval includes no change). This is not
  evidence of improved operational early warning.
- The previous structural GDP scenarios, normalized burden rankings, calibrated
  trap threshold, and policy frontier are withdrawn. Their original numerical
  outputs remain in `output/legacy/` solely for audit.

## Reproduce

Python 3.14 was used for this revision; exact resolved versions are recorded in
`requirements-lock.txt`. The analysis needs no raw-data download when using the
committed frozen inputs.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg \
  .venv/bin/python code/scripts/run_all.py
.venv/bin/python -m unittest discover -s tests -v
tectonic -X compile paper/main.tex --outdir paper --keep-logs
```

`run_all.py` uses 399 country-block bootstrap draws (both quantile stages are
refitted), ten chronological forecast origins, 1,999 target-year resamples for
forecast-loss intervals, and 200 Monte Carlo replications. The default is the
reported analysis; smaller `--bootstrap-reps` values are development runs and
must not be presented as the final paper's inference. The run writes numerical
macros consumed by the manuscript so its main results follow the code.

`code/scripts/make_tables.py` rebuilds tables from existing outputs.
The former standalone robustness command directs users to the integrated run.
`code/ccod/simulate.py::outcome_paths` intentionally raises an error: using
predictive level coefficients as structural convolution weights is unsupported.

## Files

- `paper/main.tex`, `paper/sections/`, `paper/bib/`: manuscript source.
- `paper/main.pdf`: compiled manuscript after the verified build.
- `paper/figures/`, `paper/tables/`: regenerated assets, tables and numerical macros.
- `code/ccod/estimation.py`: calendar-aligned panel estimation, clustered and
  Driscoll–Kraay covariance, observed outcomes, and lagged conditioning states.
- `code/ccod/validation.py`: training-window index construction, full two-stage
  quantile bootstrap, joint contrasts, and chronological forecast comparison.
- `output/`: machine-readable revised results, bootstrap draws, predictions,
  forecast losses, specification checks and input hashes.
- `data/processed/`: original frozen panel plus original DSP v8 components.
- `docs/REVISION.md`: changes, findings and remaining research limitations.
- `docs/DATA_PROVENANCE.md`: input sources, transformations and vintage caveats.
- `lean/Ccod/`: selected formal proofs; see `THEORY.md` for their precise scope.

The manuscript explains aggregate financing thresholds, the distinction between
stress interactions and quantile-slope differences, persistence sensitivity, and
finite parameter changes. These analytical extensions leave the reported
estimates unchanged and are distinguished from the companion Lean proofs. The
appendix closes with a synthesis; reproduction instructions remain here.

## Formal proofs

```bash
cd lean/Ccod
lake exe cache get
lake build
```

The Lean toolchain and mathlib version are pinned by the existing project.
Formalization checks selected mathematical statements, not empirical results,
identification, measurement validity or policy effectiveness. The Lean CI workflow
performs an axiom audit. Read the verification record in `docs/REVISION.md` for
what was actually run in this revision.
