"""Check the frozen inputs, reported statistics and generated manuscript assets.

This reads stored inference; it does not replace a full estimation run.
Run from the repository root: python code/scripts/check_alignment.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from ccod.validation import fit_index


def check_alignment():
    results = json.loads((ROOT / "output/results.json").read_text(encoding="utf-8"))
    for filename, expected in results["sources_sha256"].items():
        actual = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen input hash mismatch: {filename}")
    panel = pd.read_csv(ROOT / "data/processed/panel.csv")
    assert not panel.duplicated(["iso3", "year"]).any()
    assert len(panel) == results["panel"]["n"]
    assert panel.iso3.nunique() == results["panel"]["countries"]
    assert [int(panel.year.min()), int(panel.year.max())] == results["panel"]["years"]
    components = pd.read_csv(ROOT / "data/processed/dsp_components.csv")
    _, index = fit_index(components, components)
    rebuilt = components[["iso3", "year"]].assign(rebuilt=index)
    joined = panel.merge(rebuilt, on=["iso3", "year"], validate="one_to_one")
    assert len(joined) == len(panel)
    np.testing.assert_allclose(joined.M, joined.rebuilt, atol=1e-14, rtol=0)

    # Regenerate in a temporary directory: a check never rewrites paper assets.
    spec = importlib.util.spec_from_file_location("make_tables", ROOT / "code/scripts/make_tables.py")
    tables = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tables)
    with tempfile.TemporaryDirectory(prefix=".alignment-", dir=ROOT) as temporary:
        tables.TAB = pathlib.Path(temporary)
        tables.main()
        for generated in tables.TAB.glob("*.tex"):
            committed = ROOT / "paper/tables" / generated.name
            if generated.read_text(encoding="utf-8") != committed.read_text(encoding="utf-8"):
                raise ValueError(f"Stale generated manuscript asset: {committed.relative_to(ROOT)}")

    predictions = pd.read_csv(ROOT / "output/forecast_predictions.csv")
    keys = ["origin", "target_year", "iso3"]
    assert not predictions.duplicated(keys + ["model", "metric"]).any()
    assert (predictions.target_year == predictions.origin + 1).all()
    assert sorted(predictions.target_year.unique()) == list(range(2015, 2025))
    scores = pd.read_csv(ROOT / "output/forecast_scores.csv")
    for row in scores.itertuples():
        group = predictions[(predictions.model == row.model) & (predictions.metric == row.metric)]
        np.testing.assert_allclose(group.loss.mean(), row.loss, rtol=1e-12)
        if row.model == "disinformation":
            benchmark = predictions[(predictions.model == "benchmark") & (predictions.metric == row.metric)]
            paired = group.merge(benchmark, on=keys, validate="one_to_one", suffixes=("_a", "_b"))
            assert len(paired) == len(group) == len(benchmark)
            np.testing.assert_array_equal(paired.actual_a, paired.actual_b)
            np.testing.assert_allclose(row.improvement_pct, 100 * (1 - row.loss / benchmark.loss.mean()))

    quantiles = pd.read_csv(ROOT / "output/qlp_results.csv").set_index("q")
    draws = pd.read_csv(ROOT / "output/quantile_bootstrap.csv")
    for quantile, row in quantiles.iterrows():
        # Bootstrap draws are stored wide, with one column per quantile.
        values = draws[f"q{quantile}"]
        assert len(values) == results["bootstrap_reps"]
        np.testing.assert_allclose(np.quantile(values, [0.05, 0.95]), [row.lo, row.hi], atol=1e-10)
    contrasts = pd.read_csv(ROOT / "output/quantile_contrasts.csv")
    for row in contrasts.itertuples():
        np.testing.assert_allclose(row.difference, quantiles.loc[row.q_a, "coef"] - quantiles.loc[row.q_b, "coef"])

    main = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    macros_text = (ROOT / "paper/tables/results_macros.tex").read_text(encoding="utf-8")
    macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]+)\}", macros_text))
    abstract = main.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0]
    for key, value in sorted(macros.items(), key=lambda pair: -len(pair[0])):
        abstract = abstract.replace("\\" + key, value)
    abstract = re.sub(r"\\[a-zA-Z]+", "", abstract).replace("$", "")
    words = len(abstract.split())
    assert words <= 200, f"Abstract has {words} words; REA maximum is 200"
    assert main.index(r"\input{sections/appendix}") < main.index(r"\bibliography{bib/refs}")
    print(f"Alignment passed: frozen inputs; pooled index; generated tables/macros; forecast losses/samples; bootstrap intervals; {words}-word abstract.")


if __name__ == "__main__":
    check_alignment()
