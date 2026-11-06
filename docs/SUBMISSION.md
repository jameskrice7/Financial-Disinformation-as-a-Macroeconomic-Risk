# November 2026 manuscript and repository alignment

## Target journal

**Review of Economic Analysis**, the official journal of the International Centre
for Economic Analysis, hosted by the University of Waterloo Library.

- [Journal and author guidance](https://openjournals.uwaterloo.ca/index.php/rofea/about/submissions)
- [Journal information and fee policy](https://releve.erudit.org/fr/revues/rea/)
- [Submission portal](https://openjournals.uwaterloo.ca/rofea/login)

Requirements checked on 6 November 2026: English PDF or Word; abstract no longer
than 200 words; author affiliation and correspondence details on page one; JEL
codes and up to ten keywords; an unnumbered acknowledgement footnote; numbered
sections and equations; embedded tables and figures; appendices before references;
and double-spaced references. References are alphabetized using `plainnat`.
The journal's detailed reference style is requested on acceptance. It charges no
submission or publication fees. This broad economics outlet accommodates the
paper's combination of an illustrative model and observational panel evidence.

The alternative Journal of Economics and Finance has a relevant scope but asks
for at most 30 double-spaced pages inclusive of references, figures and tables,
which would require a more substantial restructuring. Journal of Economic
Interaction and Coordination emphasizes interacting-agent and collective-behavior
research; that is a less direct match to the current empirical contribution.

## One authoritative source

The supplied LaTeX archive had a fuller literature discussion, declarations,
source links and citation metadata than repository commit
`972ac974f4eba18591adc7b541098cf44d962fc1`. Those additions have been consolidated
in `paper/`; there is no second independently maintained submission manuscript.
The main text, proofs, data, figures and empirical estimates retain their existing
substantive scope. The title now explicitly identifies the political-information
proxy and avoids suggesting that a disproportionate downside effect was found.

Changes include:

- A 168-word abstract reporting the actual three-year regression sample,
  1,539 observations in 121 countries, alongside the broader 175-country panel.
- Generated numerical macros for standard errors, estimation-sample counts,
  stress-conditioned slopes and the number of held-out forecasts. Calculating the
  high-stress slope from unrounded coefficients gives -2.47, correcting -2.46.
- Corrected reverse-timing methods: lagged outcome controls are omitted in those
  regressions, while lagged conditioning states remain. The previous prose
  incorrectly said the overlapping lagged outcome controls were retained.
- Interaction standard errors added to the robustness table.
- First-page formatting, declarations, appendix/reference order and reference
  spacing adapted to the chosen journal. AI assistance remains disclosed.
- Public compilation omits the telephone line. The submission build supplies
  `\SubmissionTelephone`; this contact detail changes no analytical content.
- A read-only alignment audit and CI workflow; Windows reproduction instructions;
  canonical LF checkout for the input files whose SHA-256 hashes are recorded.

`code/scripts/make_tables.py` remains the sole generator of manuscript tables and
result macros. Run it after intentionally updating numerical outputs, then run
`code/scripts/check_alignment.py`. The audit fails on stale generated assets.

## Verification on 6 November 2026

- All 11 existing regression tests passed.
- Frozen input hashes match `output/results.json`; reconstructing the index from
  DSP components matches the panel to floating-point precision.
- The new alignment audit passes, including all generated tables/macros, forecast
  samples and score means, bootstrap percentile intervals, and abstract length.
- Fresh estimation reproduced the state equation and every baseline and negative-
  horizon local-projection coefficient, standard error, p-value and sample size.
- The complete ten-origin forecasting exercise reproduced committed predictions,
  losses, gain percentages and gain intervals to numerical tolerance.
- The stored empirical CSVs and frozen input contents were not changed. The 399-
  draw quantile bootstrap was checked from its stored draws rather than rerun.
- Local verification used Python 3.12.14, NumPy 2.5.4, pandas 3.1.1, SciPy 1.18.1
  and statsmodels 0.15.0 on Windows; the original Python 3.14 lock file is retained
  and used by CI. The cross-environment reproduction tolerances were 1e-7 or tighter.
- Existing Lean source and formalization claims were not changed or rebuilt.

- Both public and journal copies compile to 25 pages with MiKTeX/pdfLaTeX and
  BibTeX, without undefined citations/references or overfull/underfull boxes.
  All rendered pages and the one-page cover letter were visually inspected.
  The two manuscript PDFs differ only in the submission telephone/fax line.

This document records preparation and verification, not a journal submission ID.

## Remaining research limits

The DSP index does not validate financial-message exposure. There is no identified
causal intervention, the contemporary stress interaction is imprecise, all reported
quantile-slope intervals include zero, and the index does not improve the evaluated
forecasts. Stronger financial-content measurement, identification and external
validation require new research. These limitations remain explicit in the paper.
