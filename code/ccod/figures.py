"""All paper figures.  Each function writes a PDF to paper/figures/.

Style: single consistent look, colorblind-safe categorical palette,
no chartjunk, direct labeling where possible.
"""

from __future__ import annotations

import pathlib

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FIGDIR = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

# colorblind-safe palette
C_BASE = "#4269d0"     # blue: baseline / main
C_HIGH = "#ff585d"     # red: high-disinformation / bad
C_RES = "#3ca951"      # green: resilient
C_NEUT = "#9498a0"     # gray: neutral / reference
C_ACC = "#efb118"      # amber: accent

mpl.rcParams.update({
    "figure.dpi": 150,
    "font.size": 9,
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9,
    "legend.frameon": False,
    "pdf.fonttype": 42,
})


def _save(fig, name):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGDIR / name, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")


# ------------------------------------------------------------------ fig 1
def fig_index_trends(panel: pd.DataFrame):
    """Disinformation index: world and region trends, 2000-2025."""
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0))

    ax = axes[0]
    wm = panel.groupby("year")["M"].mean()
    q25 = panel.groupby("year")["M"].quantile(0.25)
    q75 = panel.groupby("year")["M"].quantile(0.75)
    ax.fill_between(wm.index, q25, q75, color=C_BASE, alpha=0.18, lw=0,
                    label="interquartile range")
    ax.plot(wm.index, wm.values, color=C_BASE, lw=1.8, label="world mean")
    ax.set_title("A. World disinformation intensity $M_{r,t}$")
    ax.set_ylabel("index (panel percentile / 100)")
    ax.legend(loc="upper left", fontsize=8)

    ax = axes[1]
    regs = panel.groupby(["region", "year"])["M"].mean().unstack(0)
    order = regs.loc[2024].sort_values(ascending=False).index
    colors = plt.cm.viridis(np.linspace(0.05, 0.85, len(order)))
    shorten = {"Latin America & Caribbean": "Latin America",
               "Europe & Central Asia": "Europe & C. Asia",
               "Middle East, North Africa, Afghanistan & Pakistan": "MENA+",
               "Middle East & North Africa": "MENA",
               "East Asia & Pacific": "East Asia & Pacific",
               "Sub-Saharan Africa": "Sub-Saharan Africa",
               "North America": "North America",
               "South Asia": "South Asia"}
    for c, reg in zip(colors, order):
        ax.plot(regs.index, regs[reg], lw=1.3, color=c,
                label=shorten.get(reg, reg))
    ax.set_xlim(2000, 2025)
    ax.legend(fontsize=6.2, ncol=2, loc="upper left", handlelength=1.2,
              columnspacing=0.8, labelspacing=0.3)
    ax.set_title("B. Regional means")
    fig.tight_layout()
    _save(fig, "fig1_index_trends.pdf")


# ------------------------------------------------------------------ fig 2
def fig_lp_irfs(lp: pd.DataFrame):
    """Local-projection responses of the five channels to M."""
    labels = {"G": "Growth (cum. %)", "N": "Investment (cum. %)",
              "I": "Inequality (Δ Gini)", "T": "Exports (cum. %)",
              "F": "Financial stress (Δ NPL)"}
    fig, axes = plt.subplots(1, 5, figsize=(10.5, 2.4), sharex=True)
    for ax, (k, lab) in zip(axes, labels.items()):
        d = lp[(lp.channel == k) & (lp["var"] == "M_z")].sort_values("h")
        ax.axhline(0, color=C_NEUT, lw=0.8)
        ax.fill_between(d.h, d.coef - 1.645 * d.se, d.coef + 1.645 * d.se,
                        color=C_BASE, alpha=0.20, lw=0)
        ax.fill_between(d.h, d.coef - 0.674 * d.se, d.coef + 0.674 * d.se,
                        color=C_BASE, alpha=0.30, lw=0)
        ax.plot(d.h, d.coef, color=C_BASE, lw=1.8, marker="o", ms=3)
        ax.set_title(lab, fontsize=8.5)
        ax.set_xlabel("horizon $h$ (years)")
        ax.set_xticks(range(0, 5))
    axes[0].set_ylabel("response to +1 s.d. $M$")
    fig.tight_layout()
    _save(fig, "fig2_lp_irfs.pdf")


# ------------------------------------------------------------------ fig 3
def fig_amplification(lp: pd.DataFrame):
    """Interaction coefficients: fragility amplification (Prop. 2 test)."""
    inter = {"MxW_F": "× financial stress", "MxW_T": "× trade exposure",
             "MxW_I": "× inequality"}
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0))

    # left: growth channel interactions across horizons
    ax = axes[0]
    colors = [C_HIGH, C_ACC, "#a463f2"]
    for c, (v, lab) in zip(colors, inter.items()):
        d = lp[(lp.channel == "G") & (lp["var"] == v)].sort_values("h")
        ax.errorbar(d.h + {"MxW_F": -0.12, "MxW_T": 0, "MxW_I": 0.12}[v],
                    d.coef, yerr=1.645 * d.se, fmt="o", ms=4, lw=1.2,
                    capsize=2, color=c, label=lab)
    ax.axhline(0, color=C_NEUT, lw=0.8)
    ax.set_title("A. Growth: interaction of $M$ with fragility states")
    ax.set_xlabel("horizon $h$ (years)")
    ax.set_ylabel("interaction coefficient")
    ax.legend(fontsize=8)

    # right: total effect of M on growth at low/mid/high stress, h=2
    ax = axes[1]
    d = lp[(lp.channel == "G") & (lp.h == 2)]
    b = d[d["var"] == "M_z"].coef.iloc[0]
    phi = d[d["var"] == "MxW_F"].coef.iloc[0]
    se_b = d[d["var"] == "M_z"].se.iloc[0]
    se_p = d[d["var"] == "MxW_F"].se.iloc[0]
    ws = np.linspace(-1.5, 2.5, 100)
    tot = b + phi * ws
    se = np.sqrt(se_b ** 2 + (ws * se_p) ** 2)  # conservative, no cov term
    ax.fill_between(ws, tot - 1.645 * se, tot + 1.645 * se, alpha=0.18,
                    color=C_HIGH, lw=0)
    ax.plot(ws, tot, color=C_HIGH, lw=1.8)
    ax.axhline(0, color=C_NEUT, lw=0.8)
    ax.set_title("B. Total growth effect of $M$ by financial stress ($h{=}2$)")
    ax.set_xlabel("financial stress (s.d. from mean)")
    ax.set_ylabel("cum. growth response (pp)")
    fig.tight_layout()
    _save(fig, "fig3_amplification.pdf")


# ------------------------------------------------------------------ fig 4
def fig_growth_at_risk(qlp: pd.DataFrame):
    """Quantile LP: effect of M across the growth distribution."""
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    ax.axhline(0, color=C_NEUT, lw=0.8)
    ax.fill_between(qlp.q, qlp.lo, qlp.hi, color=C_BASE, alpha=0.2, lw=0)
    ax.plot(qlp.q, qlp.coef, color=C_BASE, lw=1.8, marker="o", ms=4)
    ax.set_xlabel("quantile of 2-year cumulative growth")
    ax.set_ylabel("effect of +1 s.d. $M$ (pp)")
    ax.set_title("Growth-at-risk: disinformation moves the lower tail")
    fig.tight_layout()
    _save(fig, "fig4_growth_at_risk.pdf")


# ------------------------------------------------------------------ fig 5
def fig_scenarios(m_paths: dict, g_paths: dict):
    """Scenario fan charts: M and growth deviation paths."""
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0))
    colors = {"baseline": C_BASE, "high": C_HIGH, "resilient": C_RES}
    labels = {"baseline": "baseline", "high": "high-disinformation",
              "resilient": "resilient-information"}
    T = m_paths["baseline"].shape[1]
    ax = axes[0]
    for k, mp in m_paths.items():
        med = np.median(mp, axis=0)
        lo, hi = np.percentile(mp, [10, 90], axis=0)
        ax.fill_between(range(T), lo, hi, color=colors[k], alpha=0.14, lw=0)
        ax.plot(range(T), med, color=colors[k], lw=1.8, label=labels[k])
    ax.set_title("A. Disinformation index $M_t$")
    ax.set_xlabel("years")
    ax.legend(fontsize=8)

    ax = axes[1]
    for k, gp in g_paths.items():
        med = np.median(gp, axis=0)
        lo, hi = np.percentile(gp, [10, 90], axis=0)
        ax.fill_between(range(T), lo, hi, color=colors[k], alpha=0.14, lw=0)
        ax.plot(range(T), med, color=colors[k], lw=1.8, label=labels[k])
    ax.axhline(0, color=C_NEUT, lw=0.8)
    ax.set_title("B. Growth deviation from clean-information path (pp)")
    ax.set_xlabel("years")
    fig.tight_layout()
    _save(fig, "fig5_scenarios.pdf")


# ------------------------------------------------------------------ fig 6
def fig_burden(burden_tab: pd.DataFrame, sweep: pd.DataFrame):
    """Burden scores by scenario + kappa/omega sensitivity."""
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0))
    ax = axes[0]
    colors = {"baseline": C_BASE, "high": C_HIGH, "resilient": C_RES}
    means = burden_tab.groupby("scenario")["D"].mean()
    err = burden_tab.groupby("scenario")["D"].std()
    order = ["resilient", "baseline", "high"]
    ax.bar([0, 1, 2], means[order], yerr=err[order], capsize=3,
           color=[colors[o] for o in order], width=0.62)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["resilient", "baseline", "high-disinfo"])
    ax.set_ylabel("burden score $\\mathcal{D}_{t,H}$")
    ax.set_title("A. Macro-information risk score by scenario")

    ax = axes[1]
    piv = sweep.pivot(index="kappa", columns="scenario", values="D")
    for k in order:
        ax.plot(piv.index, piv[k], color=colors[k], lw=1.8, label=k)
    ax.set_xlabel("discount rate $\\kappa$")
    ax.set_ylabel("burden score")
    ax.set_title("B. Sensitivity to discounting")
    ax.legend(fontsize=8)
    fig.tight_layout()
    _save(fig, "fig6_burden.pdf")


# ------------------------------------------------------------------ fig 7
def fig_tipping(psi_grid: dict, bifurcation: pd.DataFrame):
    """Information trap: update map and bifurcation diagram."""
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2))
    ax = axes[0]
    xs = psi_grid["x"]
    ax.axhline(0, color=C_NEUT, lw=1.0, ls="--", label="45° line")
    ax.plot(xs, psi_grid["low"] - xs, color=C_BASE, lw=1.6,
            label=f"$\\varphi={psi_grid['phi_low']:.2f}$ (unique)")
    ax.plot(xs, psi_grid["high"] - xs, color=C_HIGH, lw=1.6,
            label=f"$\\varphi={psi_grid['phi_high']:.2f}$ (trap)")
    for r in psi_grid["roots_high"]:
        ax.plot(r, 0, "o", ms=5, mfc="white", mec=C_HIGH, mew=1.4, zorder=5)
    ax.set_xlabel("$x_t$ (logit scale)")
    ax.set_ylabel("$\\psi(x_t) - x_t$")
    ax.set_title("A. Update map with stress feedback (deviation from 45°)")
    ax.legend(fontsize=7.5, loc="upper right")

    ax = axes[1]
    st = bifurcation[bifurcation["stable"]]
    un = bifurcation[~bifurcation["stable"]]
    ax.scatter(st["phi"], st["M"], s=3, color=C_BASE, label="stable")
    ax.scatter(un["phi"], un["M"], s=3, color=C_NEUT, marker="x",
               linewidths=0.7, label="unstable")
    ax.legend(fontsize=7.5, loc="center right")
    ax.axvline(bifurcation.attrs.get("phi_crit", np.nan), color=C_HIGH,
               lw=0.9, ls="--")
    ax.annotate("escalation\nthreshold $\\varphi^{*}$",
                (bifurcation.attrs.get("phi_crit", 0), 0.5),
                fontsize=7.5, color=C_HIGH,
                xytext=(6, 0), textcoords="offset points")
    ax.set_xlabel("feedback strength $\\varphi$")
    ax.set_ylabel("steady-state $M$")
    ax.set_title("B. Bifurcation: birth of the information trap")
    fig.tight_layout()
    _save(fig, "fig7_tipping.pdf")


# ------------------------------------------------------------------ fig 8
def fig_policy(policy: pd.DataFrame):
    """Half-life rule and policy frontier."""
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0))
    ax = axes[0]
    rhos = np.linspace(0.01, 0.97, 200)
    ax.plot(rhos, rhos / (1 - rhos), color=C_BASE, lw=1.8,
            label="$\\varepsilon_\\rho = \\rho/(1-\\rho)$")
    ax.axhline(1, color=C_NEUT, lw=1.0, label="$\\varepsilon_c = 1$")
    ax.axvline(0.5, color=C_HIGH, lw=0.9, ls="--")
    ax.annotate("$\\rho = 1/2$:\ncorrections beat friction",
                (0.52, 3.2), fontsize=8, color=C_HIGH)
    ax.set_ylim(0, 8)
    ax.set_xlabel("persistence $\\rho$")
    ax.set_ylabel("elasticity of stationary $\\mu$")
    ax.set_title("A. The Half-Life Rule (Prop. 4)")
    ax.legend(fontsize=8, loc="upper left")

    ax = axes[1]
    colors = {"rho": C_BASE, "c": C_ACC, "sigma": C_RES}
    labels = {"rho": "rapid correction ($\\rho\\downarrow$)",
              "c": "platform friction ($c\\downarrow$)",
              "sigma": "verified messaging ($\\sigma_u\\downarrow$)"}
    for lever, d in policy.groupby("lever"):
        ax.plot(d["effort"], d["dD"], color=colors[lever], lw=1.8,
                label=labels[lever])
    ax.axhline(100, color=C_NEUT, lw=0.8, ls="--")
    ax.annotate("full elimination of baseline burden", (0.005, 103),
                fontsize=7, color=C_NEUT)
    ax.set_ylim(-5, 185)
    ax.set_xlabel("policy effort (proportional parameter reduction)")
    ax.set_ylabel("reduction in burden score (%)")
    ax.set_title("B. Policy frontier under estimated parameters")
    ax.legend(fontsize=8)
    fig.tight_layout()
    _save(fig, "fig8_policy.pdf")
