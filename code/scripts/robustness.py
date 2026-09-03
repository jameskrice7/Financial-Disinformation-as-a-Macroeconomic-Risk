"""Appendix robustness: subsample estimates, weight sensitivity, full LP
table, and country coverage listing."""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ccod.data import build_panel
from ccod.estimation import estimate_state_equation, local_projections
from ccod import simulate as sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "output"
TABDIR = ROOT / "paper" / "tables"


def star(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def write(name, body):
    (TABDIR / name).write_text(body + "\n")
    print(f"  wrote {name}")


def full_lp_table(lp):
    """All five channels, coef (se) at h = 0..4, mean effect only."""
    chans = {"G": "Growth (cum.\\ pp)", "N": "Investment (cum.\\ pp)",
             "I": "Inequality ($\\Delta$ Gini)", "T": "Exports (cum.\\ pp)",
             "F": "Fin.\\ stress ($\\Delta$ NPL)"}
    lines = []
    for k, lab in chans.items():
        row_c = [lab]
        row_s = [""]
        for h in range(0, 5):
            m = lp[(lp.channel == k) & (lp.h == h) & (lp["var"] == "M_z")]
            row_c.append(f"{m.coef.iloc[0]:.3f}{star(m.p.iloc[0])}")
            row_s.append(f"({m.se.iloc[0]:.3f})")
        lines.append(" & ".join(row_c) + " \\\\")
        lines.append(" & ".join(row_s) + " \\\\[2pt]")
    write("tab9_full_lp.tex", "\n".join(lines))


def subsample(panel):
    """Post-2015 subsample: state equation and growth LP at h in 1..3."""
    sub = panel[panel.year >= 2015].copy()
    se_full = estimate_state_equation(panel)
    se_sub = estimate_state_equation(sub)
    lp_full = local_projections(panel, horizons=[1, 2, 3])
    lp_sub = local_projections(sub, horizons=[1, 2, 3])
    lines = []
    rows = [
        ("$\\rho$ (persistence)",
         se_full["rho"], se_full["table"].loc["logitM", "se"],
         se_sub["rho"], se_sub["table"].loc["logitM", "se"]),
        ("$\\delta$ (spillover)",
         se_full["delta"], se_full["table"].loc["spill", "se"],
         se_sub["delta"], se_sub["table"].loc["spill", "se"]),
    ]
    for h in (1, 2, 3):
        f = lp_full[(lp_full.channel == "G") & (lp_full.h == h)
                    & (lp_full["var"] == "M_z")]
        s = lp_sub[(lp_sub.channel == "G") & (lp_sub.h == h)
                   & (lp_sub["var"] == "M_z")]
        rows.append((f"Growth response, $h={h}$",
                     f.coef.iloc[0], f.se.iloc[0],
                     s.coef.iloc[0], s.se.iloc[0]))
    for lab, cf, sf, cs, ss in rows:
        lines.append(f"{lab} & {cf:.3f} & ({sf:.3f}) & {cs:.3f} & ({ss:.3f}) \\\\")
    write("tab10_subsample.tex", "\n".join(lines))


def weight_sensitivity(panel, results):
    """Burden ranking across alternative weight vectors."""
    rho = results["state_eq"]["rho"]
    sigma_u = results["state_eq"]["sigma_u"]
    m_bar = float(panel[panel.year >= 2020].M.mean())
    c = (1 - rho) * sim.logit(m_bar)
    scen = sim.make_scenarios(rho, c, sigma_u)
    m_paths = {k: sim.simulate_paths(p, T=12, n_sims=5000)
               for k, p in scen.items()}
    lp = pd.read_csv(OUT / "lp_results.csv")
    mz = lp[lp["var"] == "M_z"]
    sign_flip = {"G": -1.0, "N": -1.0, "T": -1.0, "I": 1.0, "F": 1.0}
    beta = {}
    for k in sign_flip:
        b = mz[(mz.channel == k) & (mz.h >= 0)].sort_values("h").coef.to_numpy()
        beta[k] = sign_flip[k] * b / max(abs(b[2]), 1e-9)
    omap = sim.OutcomeMap(horizons=np.arange(5), beta=beta,
                          m_sd=float(panel.M.std()), m_mean=m_bar)
    ypaths = {k: sim.outcome_paths(mp, omap) for k, mp in m_paths.items()}

    weightings = {
        "Headline $(0.30,0.20,0.10,0.20,0.20)$":
            {"G": .3, "N": .2, "I": .1, "T": .2, "F": .2},
        "Equal weights": {k: .2 for k in "GNITF"},
        "Growth only": {"G": 1, "N": 0, "I": 0, "T": 0, "F": 0},
        "Stability only": {"G": 0, "N": 0, "I": 0, "T": 0, "F": 1},
        "Growth and stability": {"G": .5, "N": 0, "I": 0, "T": 0, "F": .5},
    }
    lines = []
    for lab, om in weightings.items():
        Ds = {k: float(sim.burden_score(m_paths[k], ypaths[k], om,
                                        kappa=0.04).mean()) for k in scen}
        ok = Ds["high"] > Ds["baseline"] > Ds["resilient"]
        lines.append(f"{lab} & {Ds['resilient']:.2f} & {Ds['baseline']:.2f} & "
                     f"{Ds['high']:.2f} & {'yes' if ok else 'no'} \\\\")
    write("tab11_weights.tex", "\n".join(lines))


def coverage(panel):
    """Country counts and example coverage by region."""
    def esc(s):
        return str(s).replace("&", "\\&")
    lines = []
    for reg, d in panel.groupby("region"):
        n = d.iso3.nunique()
        obs = len(d)
        ex = ", ".join(esc(c) for c in sorted(d.groupby("iso3").country.first())[:4])
        lines.append(f"{esc(reg)} & {n} & {obs:,} & {ex}, \\dots \\\\")
    write("tab12_coverage.tex", "\n".join(lines))


if __name__ == "__main__":
    panel = build_panel()
    results = json.load(open(OUT / "results.json"))
    lp = pd.read_csv(OUT / "lp_results.csv")
    full_lp_table(lp)
    subsample(panel)
    weight_sensitivity(panel, results)
    coverage(panel)
