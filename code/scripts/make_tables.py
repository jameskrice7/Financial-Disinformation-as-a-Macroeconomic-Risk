"""Generate all LaTeX tables for the paper from pipeline outputs."""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from ccod.data import build_panel  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "output"
TABDIR = ROOT / "paper" / "tables"
TABDIR.mkdir(exist_ok=True)


def star(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def cell(coef, se, p):
    return f"{coef:.3f}{star(p)} & ({se:.3f})"


def write(name, body):
    (TABDIR / name).write_text(body)
    print(f"  wrote {name}")


def tab_summary(panel):
    rows = [
        ("Disinformation index $M_{r,t}$", "M", 2),
        ("Real GDP growth (\\%)", "gdp_growth", 1),
        ("Investment growth (\\%)", "inv_growth", 1),
        ("Gini index", "gini_i", 1),
        ("Real export growth (\\%)", "export_growth", 1),
        ("Bank NPLs (\\% gross loans)", "npl_i", 1),
        ("Trade (\\% GDP)", "trade_gdp", 0),
        ("CPI inflation (\\%)", "inflation", 1),
        ("Government effectiveness (WGI)", "gov_eff", 2),
    ]
    lines = []
    for lab, col, dec in rows:
        s = panel[col].dropna()
        lines.append(
            f"{lab} & {s.mean():.{dec}f} & {s.std():.{dec}f} & "
            f"{s.quantile(.1):.{dec}f} & {s.quantile(.9):.{dec}f} & "
            f"{len(s):,} \\\\")
    body = "\n".join(lines)
    write("tab1_summary.tex", body)


def tab_state():
    t = pd.read_csv(OUT / "state_equation.csv", index_col=0)
    labels = {
        "logitM": "$\\operatorname{logit}(M_{r,t})$ \\quad ($\\rho$)",
        "spill": "Regional spillover $S_{r,t}$ \\quad ($\\delta$)",
        "stress": "Banking stress $F_{r,t}$",
        "stressXlogitM": "Stress $\\times$ $\\operatorname{logit}(M_{r,t})$",
        "infl_z": "Inflation (standardized)",
    }
    lines = []
    for var, lab in labels.items():
        r = t.loc[var]
        lines.append(f"{lab} & {r.coef:.3f}{star(r.p)} & ({r.se:.3f}) \\\\")
    write("tab2_state.tex", "\n".join(lines))


def tab_lp():
    lp = pd.read_csv(OUT / "lp_results.csv")
    chans = {"G": "Growth", "N": "Investment", "I": "Inequality",
             "T": "Exports", "F": "Fin.\\ stress"}
    lines = []
    for k, lab in chans.items():
        row_m = [lab + " & $M_{r,t}$"]
        row_i = [" & $M \\times F$"]
        for h in [0, 1, 2, 3, 4]:
            m = lp[(lp.channel == k) & (lp.h == h) & (lp["var"] == "M_z")]
            i = lp[(lp.channel == k) & (lp.h == h) & (lp["var"] == "MxW_F")]
            row_m.append(f"{m.coef.iloc[0]:.2f}{star(m.p.iloc[0])}")
            row_i.append(f"{i.coef.iloc[0]:.2f}{star(i.p.iloc[0])}")
        n = lp[(lp.channel == k) & (lp.h == 2) & (lp["var"] == "M_z")].n.iloc[0]
        row_m.append(f"{int(n):,}")
        row_i.append("")
        lines.append(" & ".join(row_m) + " \\\\")
        lines.append(" & ".join(row_i) + " \\\\[2pt]")
    write("tab3_lp.tex", "\n".join(lines))


def tab_burden(results):
    b = results["burden"]
    order = [("resilient", "Resilient information"),
             ("baseline", "Baseline"),
             ("high", "High disinformation")]
    lines = []
    for key, lab in order:
        lines.append(f"{lab} & {b[key]['mean']:.2f} & ({b[key]['sd']:.2f}) \\\\")
    lines.append("\\midrule")
    lines.append(f"High $-$ baseline & {b['high_minus_baseline']:.2f} & \\\\")
    lines.append(
        f"Baseline $-$ resilient & {b['baseline_minus_resilient']:.2f} & \\\\")
    write("tab4_burden.tex", "\n".join(lines))


def tab_mc(results):
    labels = {"rho_hat": "$\\hat\\rho$ (within)",
              "rho_bc": "$\\hat\\rho$ (bias-corrected)",
              "beta_hat": "$\\hat\\beta$ (mean effect)",
              "phi_hat": "$\\hat\\phi$ (interaction)"}
    lines = []
    for m in results["montecarlo"]:
        lab = labels[m["estimator"]]
        lines.append(
            f"{lab} & {m['true']:.2f} & {m['mean']:.3f} & {m['bias']:.3f} & "
            f"{m['sd']:.3f} & {m['rmse']:.3f} \\\\")
    write("tab5_mc.tex", "\n".join(lines))


def tab_gar(results):
    lines = []
    for q in ["q10", "q25", "q50", "q75", "q90"]:
        g = results["gar"][q]
        lines.append(f"{q[1:]}th & {g['coef']:.2f} & "
                     f"[{g['lo']:.2f}, {g['hi']:.2f}] \\\\")
    write("tab6_gar.tex", "\n".join(lines))


def tab_iv(results):
    lines = []
    for h in ("h1", "h2"):
        iv = results["iv"][h]
        lines.append(
            f"$h={h[1]}$ & {iv['beta_M']:.2f} & ({iv['se_M']:.2f}) & "
            f"{iv['first_stage_F']:.1f} & {iv['n']:,} \\\\")
    write("tab7_iv.tex", "\n".join(lines))


def tab_pretrend():
    lp = pd.read_csv(OUT / "lp_results.csv")
    chans = {"G": "Growth", "N": "Investment", "T": "Exports",
             "F": "Fin.\\ stress", "I": "Inequality"}
    lines = []
    for k, lab in chans.items():
        row = [lab]
        for h in (-2, -1):
            m = lp[(lp.channel == k) & (lp.h == h) & (lp["var"] == "M_z")]
            if len(m):
                row.append(f"{m.coef.iloc[0]:.2f}{star(m.p.iloc[0])} "
                           f"({m.se.iloc[0]:.2f})")
            else:
                row.append("--")
        lines.append(" & ".join(row) + " \\\\")
    write("tab8_pretrend.tex", "\n".join(lines))


if __name__ == "__main__":
    panel = build_panel()
    results = json.load(open(OUT / "results.json"))
    tab_summary(panel)
    tab_state()
    tab_lp()
    tab_burden(results)
    tab_mc(results)
    tab_gar(results)
    tab_iv(results)
    tab_pretrend()
