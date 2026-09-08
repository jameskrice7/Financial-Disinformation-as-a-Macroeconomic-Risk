# September 2026 submission revision

## Main findings after correction

This is a substantive re-analysis, not a cosmetic restatement of the original
findings. The broad information index remains associated with growth and
financial fragility in the baseline, but the main tail-risk and policy claims
have weakened or been withdrawn.

- Three-year cumulative-growth slope at mean states: approximately **−1.52 pp**
  per standard deviation (country-clustered SE 0.73; p≈0.039).
- Interaction with prior banking stress at the same horizon: approximately
  **−0.94 pp** (SE 0.29; p≈0.0014). Sample: **1,539 observations, 121 countries**.
- In the no-fill specification, the growth slope is −0.45 (SE 0.74), while
  the interaction remains −1.02 (SE 0.27). The post-2015 interaction is −0.10
  (SE 0.61), and omitting Europe/Central Asia yields imprecise interaction
  estimates. These are material limits on stability, not uniformly successful
  robustness checks.
- Persistence is approximately **0.864** (SE 0.054), with a conditional latent
  index half-life of **4.7 years**. The uncapped approximation is 0.985,
  corresponding to about 44.6 years. Neither number is a narrative lifetime.
- Quantile slopes are approximately **−0.71, −0.55, −0.82 pp** at the tenth,
  median and ninetieth quantiles. Every 90% bootstrap interval includes zero.
  Paired comparisons have p=0.575 (tenth vs median) and p=0.805 (tenth vs
  ninetieth). The original threefold/disproportionate lower-tail claim is withdrawn.
- In 1,111 held-out country-year predictions (target years 2015–2024), adding
  the index **worsens** tenth-quantile loss by **3.22%**; its gain interval is
  [−5.44%, 1.29%]. No reported loss metric improves at the point estimate.
  This is a specific latest-vintage pseudo out-of-sample comparison, not proof
  that disinformation never helps forecast in another setting.

The generated CSVs and manuscript macros are authoritative for exact values.
The scope and benchmarks were chosen during this revision, not preregistered.

## Repairs

1. Added the supplied LaTeX source to `paper/` and made the title, abstract,
   claims, captions, methods and conclusion consistent with the measured proxy.
2. Separated political-disinformation rank M from financial contamination p;
   replaced the false posterior-variance derivation with an explicit lending
   assumption. Qualified distributional implications of increasing differences.
3. Restricted scalar stationarity arguments; added the endogenous-network
   condition. Separated sufficient contraction from a fold bifurcation.
4. Qualified the half-life elasticity with sign, observation-period, marginal
   intervention-effectiveness and cost conditions. Corrected the half-life
   arithmetic and removed the arbitrary cap on the persistence adjustment.
5. Replaced interpolated Gini/NPL outcomes with observed endpoints. Rebuilt
   conditioning states using past-only, age-limited carries; lagged them one
   year in LPs. Added the previously computed-but-omitted log GDP control and
   appropriate outcome lags. Calendar gaps are handled explicitly.
6. Fixed the degenerate negative-horizon level-change placebo. Included full
   coefficient covariance in the stress-conditioned growth intervals.
7. Re-estimated both additive FE and quantile stages in a 399-replication
   country-block bootstrap; used an exact linear-programming quantile solver,
   90% intervals and paired contrasts. Removed unsupported claims of other
   estimators/robustness checks that were not implemented.
8. Recomputed raw-composite, alternative-weight, sample, no-fill,
   lagged-index, Driscoll–Kraay and leave-region-out checks.
9. Added chronological forecasting with original DSP components, training-only
   scaling/ranks and the same benchmark/augmented sample; exported predictions,
   losses and whole-target-year bootstrap intervals.
10. Disabled unsupported structural LP convolution, withdrew GDP scenarios,
    unstable burden normalization, trap calibration and policy cost frontier.
    Original numerical files are isolated under `output/legacy`.
11. Withdrew weak-IV sign corroboration. The optional legacy IV helper's sample
    now follows its exposure window and uses an excluded-instrument clustered
    Wald statistic. No new IV result is claimed by the paper.
12. Narrowed Lean documentation to what the declarations actually prove. The
    theorem statements and proof terms themselves were not changed.

## What still requires new research before a strong submission

- Financial-specific construct validation or independent financial-message data.
- Credible variation for causal claims about misinformation or interventions.
- Better supported policy-effectiveness and cost functions for policy rankings.
- Real-time source vintages, richer forecast benchmarks, a longer evaluation
  sample and further external validation before operational early-warning claims.
- Measurement uncertainty and stronger treatment of cross-country dependence.

The revision implements the defensible analyses available in the repository.
It does not invent new data or preserve positive findings that the checks no
longer support. Journal expectations should be reconsidered using these revised
findings rather than the original abstract.

## Verification record

The final checks and build results are recorded here before delivery.

- `OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -v`:
  **9 tests passed**.
- `.venv/bin/ruff check code tests --select F` and Python bytecode compilation:
  **passed**.
- `git diff --check`: **passed**.
- `tectonic -X compile paper/main.tex --outdir paper --keep-logs`:
  **completed**, producing a 20-page PDF; rendered page contact sheets were
  inspected for clipping, unreadable tables or broken figures.
- `lake exe cache get && lake build` in `lean/Ccod`: **completed successfully**
  (3,034 jobs; existing style/import linter warnings only).
- Reconstructing the retrospective pooled index from the committed DSP
  components reproduces the frozen panel to a maximum absolute difference of
  $1.1\times10^{-16}$.

The last PDF recompile attempt after an unchanged source-only cleanup was
blocked by the host's automatic approval usage limit; the PDF in `paper/` is
the already compiled and visually inspected artifact. The same limit blocked
the requested external `rsync` into `/Users/jameskrice/Downloads/paper/` and
the GitHub push. The local commit is complete and ready for those two commands
when external writes are available.
