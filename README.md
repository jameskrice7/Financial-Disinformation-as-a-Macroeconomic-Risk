# Financial Disinformation as a Macroeconomic Risk

**Information Pollution, Fragile States, and the Half-Life Rule**
James Rice, Council for Countering Online Disinformation — July 2026

[![Lean proofs](https://github.com/jameskrice7/Financial-Disinformation-as-a-Macroeconomic-Risk/actions/workflows/lean-ci.yml/badge.svg)](https://github.com/jameskrice7/Financial-Disinformation-as-a-Macroeconomic-Risk/actions/workflows/lean-ci.yml)

This repository holds the code, formal proofs, and estimation outputs behind
the paper. The LaTeX manuscript and compiled PDF are kept outside the
repository; everything needed to regenerate the paper's figures, tables, and
numbers is here.

## What is here

- `code/ccod/` — Python package: data construction (`data.py`), panel
  estimation — state equation, local projections, quantile growth-at-risk,
  shift-share IV (`estimation.py`), scenario simulation and burden score
  (`simulate.py`), Monte Carlo validation (`montecarlo.py`), figures
  (`figures.py`).
- `code/scripts/` — `run_all.py` reproduces every number, figure, and
  table (writes `output/results.json`); `make_tables.py` and
  `robustness.py` write the LaTeX tables.
- `lean/Ccod/` — Lean 4 / mathlib formalization of all four propositions
  (logistic bounds, AR(1) dynamics, supermodular amplification, the
  information trap, burden bound + Half-Life Rule). `lake build`
  compiles with zero errors and no `sorry`.
- `data/processed/panel.csv` — the merged estimation panel (175 countries,
  2000–2025). Raw inputs (Digital Society Project v8, World Bank WDI bulk
  archive, WGI) are not committed; `code/ccod/data.py` downloads them into
  `data/raw/` on first run.
- `output/` — estimation outputs and `results.json`, the machine-readable
  source of every number quoted in the paper.

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cd code
../.venv/bin/python -m scripts.run_all      # data → estimation → simulation → figures
../.venv/bin/python -m scripts.make_tables  # LaTeX tables
../.venv/bin/python -m scripts.robustness   # appendix robustness tables

cd ../lean/Ccod && lake build               # verify all proofs (needs elan/mathlib)
```

`run_all.py` downloads the raw sources on first run and caches them under
`data/raw/` (untracked; the World Bank bulk archive is ~280 MB). Delete that
directory to force a re-download.

## Headline results

1. **The Half-Life Rule.** Stationary disinformation is `c/(1−ρ)`; its
   elasticity w.r.t. persistence ρ is `ρ/(1−ρ)` vs. 1 for the inflow c.
   Corrections beat friction iff ρ > 1/2. Estimated ρ = 0.92
   (half-life ≈ 8.5 years) ⇒ elasticity ratio ≈ 12.
2. **Risk amplifier, not mean shifter.** Damage is supermodular in
   (disinformation, fragility) and zero in calm states; empirically the
   10th-percentile growth effect is ~3× the 90th, and interactions with
   banking stress dominate.
3. **Information trap.** With stress→narrative feedback the update map
   folds at φ* ≈ 0.29 given ρ = 0.92; escalation should key on the
   fragility interaction, not content volume.
4. **Burden score.** Bounded macro-information risk metric; high vs.
   resilient scenario differ by ~2.8 normalized units over 12 years.
