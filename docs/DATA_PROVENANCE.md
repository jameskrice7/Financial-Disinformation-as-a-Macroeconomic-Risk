# Data provenance

## Frozen merged panel

`data/processed/panel.csv` is unchanged from repository commit `f4a476d`.
It has 4,539 country-year records for 175 countries in 2000–2025. The upstream
repository identifies DSP v8, World Bank WDI and the WGI 2023 update as sources.
The original raw WDI/WGI archives and their retrieval timestamps were not
committed. This revision does not invent missing archive dates or call the
latest-vintage historical data real-time.

The input includes observed `gini`/`npl` and legacy two-sided interpolated
`gini_i`/`npl_i`. Revised estimation uses **observed** outcome endpoints.
Conditioning copies are rebuilt from past observations only (NPL at most two
calendar years old; Gini at most five). Main LP conditioning states are then
lagged one calendar year. Growth rates are summed, not compounded. NPL/Gini
outcome changes are from t−1 to t+h, requiring both observed endpoints.
Governance values already carried forward after 2022 remain in this frozen
vintage, and an end-2022 sample check is provided.

## Original DSP components added for validation

Source: https://digitalsocietyproject.org/data/
Archive: https://digitalsocietyproject.org/wp-content/uploads/2026/03/DigitalSocietyProject-v8-CSV.zip
Retrieved for this revision: 2026-09-08.

`data/processed/dsp_components.csv` extracts `country_text_id`, `year`,
`v2smgovdom`, `v2smpardom`, `v2smfordom`, `v2smgovab`, `v2smparab` from
`DSP_CY_v8.csv`; `country_text_id` is renamed `iso3`. It contains 4,636 rows
(the five score columns are the original measurement-model point estimates).
These data are freely downloadable from DSP; cite Mechkova, Pemstein, Seim
and Wilson (2026), Digital Society Project Dataset v8. The package does not
claim ownership of the original data or replace the source's terms.

The full retrospective rank index is retained in the frozen panel for
comparability. Alternative weights use the original components. In forecast
validation, component means, standard deviations and empirical-CDF reference
ranks are fitted **only within training observations**. Average ranks are used
for ties; observations beyond training support are clipped to [0.5/n,1−0.5/n].
No full-panel rank or composite is used as the forecasting index. Source
checksums are recorded in `output/results.json`.

## Forecast timing

At origin t, predict t+1 growth using predictors from t−1. Training target
years must be <=t−1 (training source years therefore <=t−3). Origins are
2014–2023; held-out target years are 2015–2024. The frozen panel is joined
one-to-one with the original components; complete cases and previously seen
countries are used identically by benchmark and augmented models. Missing NPL
and credit levels can use a past observation up to two calendar years old.
Latest-vintage source revisions and retrospective expert assessments remain;
this is a pseudo out-of-sample rather than a real-time evaluation. The design
was implemented to audit predictive claims, not preregistered.
