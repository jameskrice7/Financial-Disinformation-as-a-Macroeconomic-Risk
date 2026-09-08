"""Reproduce revised estimates, validation, figures and manuscript tables.
Run from repository root: .venv/bin/python code/scripts/run_all.py
"""

from __future__ import annotations
import argparse, hashlib, json, pathlib, sys, warnings
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scipy.optimize import OptimizeWarning
from ccod.data import build_panel
from ccod.estimation import (
    estimate_state_equation,
    local_projections,
    past_fill,
)
from ccod.validation import quantile_inference, forecast_validation, fit_index
from ccod.montecarlo import run_montecarlo, summarize_montecarlo
from ccod import figures as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "output"


def main(n_boot=399):
    warnings.filterwarnings(
        "ignore", message="Unrecognized options detected", category=OptimizeWarning
    )
    OUT.mkdir(exist_ok=True)
    panel = build_panel().sort_values(["iso3", "year"]).reset_index(drop=True)
    # Original raw outcomes are preserved. Only past observations fill controls.
    for var, limit in [("npl", 2), ("gini", 5)]:
        panel[var + "_i"] = past_fill(panel, var, limit)
    comp = pd.read_csv(ROOT / "data/processed/dsp_components.csv")
    print("state equation", flush=True)
    state = estimate_state_equation(panel)
    state["table"].to_csv(OUT / "state_equation.csv")
    print("local projections", flush=True)
    lp = local_projections(panel, horizons=range(-2, 5))
    lp.to_csv(OUT / "lp_results.csv", index=False)
    # Rerun claimed robustness checks; do not infer them from baseline results.
    robustness = []
    for name in [
        "no_fill",
        "post2015",
        "end2022",
        "raw_composite",
        "domestic_only",
        "equal_weights",
        "dk",
        "index_history",
    ]:
        d = panel.copy()
        if name == "no_fill":
            d["npl_i"] = d.npl
            d["gini_i"] = d.gini
        elif name == "post2015":
            d = d[d.year >= 2015]
        elif name == "end2022":
            d = d[d.year <= 2022]
        elif name == "raw_composite":
            d["M"] = d.disinfo_score
        elif name in ["dk", "index_history"]:
            pass
        else:
            weights = (
                {"v2smgovdom": 1 / 3, "v2smpardom": 1 / 3, "v2smfordom": 1 / 3}
                if name == "domestic_only"
                else {
                    k: 0.2
                    for k in [
                        "v2smgovdom",
                        "v2smpardom",
                        "v2smfordom",
                        "v2smgovab",
                        "v2smparab",
                    ]
                }
            )
            _, m = fit_index(comp, comp, weights)
            d = d.drop(columns="M").merge(
                comp[["iso3", "year"]].assign(M=m),
                on=["iso3", "year"],
                validate="one_to_one",
            )
        tab = local_projections(
            d,
            horizons=[1, 2],
            covariance="dk" if name == "dk" else "cluster",
            include_history=name == "index_history",
        )
        tab["specification"] = name
        robustness.append(tab)
    for region in panel.region.unique():
        tab = local_projections(panel[panel.region != region], horizons=[2])
        tab["specification"] = "omit_" + region
        robustness.append(tab)
    pd.concat(robustness).to_csv(OUT / "robustness.csv", index=False)
    print("quantile inference", flush=True)
    q, contrasts, draws = quantile_inference(panel, n_boot=n_boot)
    q.to_csv(OUT / "qlp_results.csv", index=False)
    contrasts.to_csv(OUT / "quantile_contrasts.csv", index=False)
    draws.to_csv(OUT / "quantile_bootstrap.csv", index=False)
    print("chronological forecast validation", flush=True)
    scores, forecast = forecast_validation(panel, comp)
    scores.to_csv(OUT / "forecast_predictions.csv", index=False)
    forecast.to_csv(OUT / "forecast_scores.csv", index=False)
    print("simulation estimator check", flush=True)
    mc = summarize_montecarlo(run_montecarlo(n_rep=200))
    mc.to_csv(OUT / "montecarlo.csv", index=False)
    rho = state["rho"]
    bc = state["rho_bias_corrected"]

    def half(r):
        return float(-np.log(2) / np.log(r)) if 0 < r < 1 else None

    result = {
        "revision": "2026-09 submission revision",
        "panel": {
            "n": len(panel),
            "countries": panel.iso3.nunique(),
            "years": [int(panel.year.min()), int(panel.year.max())],
        },
        "state": {k: v for k, v in state.items() if k != "table"},
        "half_life": half(rho),
        "half_life_bc": half(bc),
        "rho_plus_delta": rho + state["delta"],
        "bootstrap_reps": n_boot,
        "sources_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                ROOT / "data/processed/panel.csv",
                ROOT / "data/processed/dsp_components.csv",
            ]
        },
        "withdrawn": [
            "structural GDP scenarios",
            "normalized burden comparisons",
            "policy cost-effectiveness frontier",
            "estimated trap threshold",
            "weak-IV sign validation",
        ],
        "interpretation": "Conditional associations; pseudo out-of-sample forecasting with latest-vintage data. No causal policy effects identified.",
    }
    (OUT / "results.json").write_text(
        json.dumps(result, indent=2, default=float, allow_nan=False) + "\n"
    )
    F.fig_index_trends(panel)
    F.fig_lp_irfs(lp[lp.h >= 0])
    F.fig_amplification(lp[lp.h >= 0])
    F.fig_growth_at_risk(q)
    from scripts.make_tables import main as make_tables

    make_tables(panel)
    print("Revised outputs complete", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap-reps", type=int, default=399)
    args = ap.parse_args()
    main(args.bootstrap_reps)
