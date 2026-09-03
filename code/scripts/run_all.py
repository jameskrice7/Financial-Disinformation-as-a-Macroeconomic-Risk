"""Master script: reproduces every number, figure, and table in the paper.

Usage:  python -m scripts.run_all          (from the code/ directory)

Outputs:
  output/results.json      all headline numbers cited in the text
  output/*.csv             estimation tables
  paper/figures/*.pdf      all figures
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ccod.data import build_panel
from ccod.estimation import (estimate_state_equation, local_projections,
                             quantile_lp, iv_growth)
from ccod.montecarlo import run_montecarlo, summarize_montecarlo
from ccod import simulate as sim
from ccod import figures as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

RESULTS: dict = {}


def main():
    rng_info = {}
    print("== 1. panel ==")
    panel = build_panel()
    RESULTS["panel"] = {
        "n_obs": int(len(panel)),
        "n_countries": int(panel.iso3.nunique()),
        "years": [int(panel.year.min()), int(panel.year.max())],
        "M_mean": float(panel.M.mean()), "M_sd": float(panel.M.std()),
        "M_world_2000": float(panel[panel.year == 2000].M.mean()),
        "M_world_2019": float(panel[panel.year == 2019].M.mean()),
        "M_world_2024": float(panel[panel.year == 2024].M.mean()),
    }

    print("== 2. state equation ==")
    se = estimate_state_equation(panel)
    tab = se["table"]
    tab.round(4).to_csv(OUT / "state_equation.csv")
    RESULTS["state_eq"] = {
        "rho": se["rho"], "rho_se": float(tab.loc["logitM", "se"]),
        "rho_bc": se["rho_bias_corrected"],
        "delta": se["delta"], "delta_se": float(tab.loc["spill", "se"]),
        "theta_stress": se["theta_stress"],
        "theta_stress_se": float(tab.loc["stress", "se"]),
        "sigma_u": se["sigma_u"],
        "n": int(tab.attrs["n_obs"]), "N": int(tab.attrs["n_entities"]),
        "half_life_years": float(np.log(0.5) / np.log(se["rho"])),
    }

    print("== 3. local projections (incl. pre-trends) ==")
    lp = local_projections(panel, horizons=range(-2, 5))
    lp.to_csv(OUT / "lp_results.csv", index=False)
    mz = lp[lp["var"] == "M_z"]
    RESULTS["lp"] = {
        f"{k}_h{h}": {"coef": float(r.coef), "se": float(r.se), "p": float(r.p)}
        for (k, h), r in mz.set_index(["channel", "h"]).iterrows()
    }
    RESULTS["lp_inter_GxF"] = {
        f"h{int(r.h)}": {"coef": float(r.coef), "se": float(r.se), "p": float(r.p)}
        for _, r in lp[(lp["var"] == "MxW_F") & (lp.channel == "G")].iterrows()
    }
    RESULTS["lp_inter_FxF"] = {
        f"h{int(r.h)}": {"coef": float(r.coef), "se": float(r.se), "p": float(r.p)}
        for _, r in lp[(lp["var"] == "MxW_F") & (lp.channel == "F")].iterrows()
    }

    print("== 4. growth-at-risk quantiles ==")
    qlp = quantile_lp(panel, h=1)
    qlp.to_csv(OUT / "qlp_results.csv", index=False)
    RESULTS["gar"] = {f"q{int(100*r.q)}": {"coef": float(r.coef),
                                           "lo": float(r.lo), "hi": float(r.hi)}
                      for _, r in qlp.iterrows()}

    print("== 5. IV robustness ==")
    RESULTS["iv"] = {f"h{h}": iv_growth(panel, h=h) for h in (1, 2)}

    print("== 6. Monte Carlo validation ==")
    mc = run_montecarlo(n_rep=200)
    mcsum = summarize_montecarlo(mc)
    mcsum.round(4).to_csv(OUT / "montecarlo.csv", index=False)
    RESULTS["montecarlo"] = mcsum.to_dict("records")

    # ------------------------------------------------------------------
    print("== 7. scenario simulations ==")
    rho = se["rho"]
    sigma_u = se["sigma_u"]
    # intercept anchored to the world-mean M in the last panel years
    m_bar = float(panel[panel.year >= 2020].M.mean())
    c = (1 - rho) * sim.logit(m_bar)
    scen = sim.make_scenarios(rho, c, sigma_u)
    T, NS = 12, 20_000
    m_paths = {k: sim.simulate_paths(p, T=T, n_sims=NS) for k, p in scen.items()}

    # outcome map: LP responses h=0..4 per channel, signed so larger = worse
    horiz = np.arange(0, 5)
    beta = {}
    sign_flip = {"G": -1.0, "N": -1.0, "T": -1.0, "I": 1.0, "F": 1.0}
    for k in ["G", "N", "I", "T", "F"]:
        b = (mz[(mz.channel == k) & (mz.h >= 0)].sort_values("h").coef
             .to_numpy())
        # standardize each channel by its own |h=2| response for comparability
        scale = max(abs(b[2]), 1e-9)
        beta[k] = sign_flip[k] * b / scale
    omap = sim.OutcomeMap(horizons=horiz, beta=beta,
                          m_sd=float(panel.M.std()), m_mean=m_bar)
    ypaths = {k: sim.outcome_paths(mp, omap) for k, mp in m_paths.items()}

    omega = {"G": 0.30, "N": 0.20, "I": 0.10, "T": 0.20, "F": 0.20}
    kappa = 0.04
    burden_rows = []
    for k in scen:
        D = sim.burden_score(m_paths[k], ypaths[k], omega, kappa=kappa)
        burden_rows.append(pd.DataFrame({"scenario": k, "D": D}))
    burden_tab = pd.concat(burden_rows)
    RESULTS["burden"] = {
        k: {"mean": float(burden_tab[burden_tab.scenario == k].D.mean()),
            "sd": float(burden_tab[burden_tab.scenario == k].D.std())}
        for k in scen
    }
    RESULTS["burden"]["high_minus_baseline"] = float(
        RESULTS["burden"]["high"]["mean"]
        - RESULTS["burden"]["baseline"]["mean"])
    RESULTS["burden"]["baseline_minus_resilient"] = float(
        RESULTS["burden"]["baseline"]["mean"]
        - RESULTS["burden"]["resilient"]["mean"])

    sweep_rows = []
    for kap in [0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15]:
        for k in scen:
            D = sim.burden_score(m_paths[k], ypaths[k], omega, kappa=kap)
            sweep_rows.append({"kappa": kap, "scenario": k,
                               "D": float(D.mean())})
    sweep = pd.DataFrame(sweep_rows)
    sweep.to_csv(OUT / "burden_sweep.csv", index=False)

    # growth deviation paths for the fan chart (raw pp units, not scaled)
    bG = mz[(mz.channel == "G") & (mz.h >= 0)].sort_values("h").coef.to_numpy()
    gmap = sim.OutcomeMap(horizons=horiz, beta={"G": bG},
                          m_sd=float(panel.M.std()), m_mean=m_bar)
    g_paths = {k: sim.outcome_paths(mp, gmap)["G"] for k, mp in m_paths.items()}
    RESULTS["scenarios"] = {
        k: {"M_final_median": float(np.median(mp[:, -1])),
            "G_dev_mean": float(np.mean(g_paths[k]))}
        for k, mp in m_paths.items()
    }

    # ------------------------------------------------------------------
    print("== 8. tipping / information trap ==")
    # Reduced-form feedback calibration.  Two ingredients:
    # (a) disinformation raises future stress in fragile states
    #     (LP interaction of the F channel, h = 4);
    # (b) stress raises the effective persistence of disinformation
    #     (state-equation interaction rho_stress).
    # Effective persistence in a fragile state (stress at +2 sd):
    dF_dM_fragile = (RESULTS["lp"]["F_h4"]["coef"]
                     + 1.0 * RESULTS["lp_inter_FxF"]["h4"]["coef"])
    rho_eff_calm = se["rho"]
    rho_eff_stress2 = se["rho"] + 2.0 * se["rho_stress"]
    RESULTS["tipping"] = {
        "dF_dM_fragile": float(dF_dM_fragile),
        "theta_F": se["theta_stress"],
        "rho_stress": se["rho_stress"],
        "rho_stress_se": se["rho_stress_se"],
        "rho_eff_calm": float(rho_eff_calm),
        "rho_eff_stress2": float(rho_eff_stress2),
    }

    stress_fn = sim.default_stress_fn
    xg = np.linspace(-6, 6, 1201)
    phi_low, phi_high = 0.15, 0.95
    p_lo = sim.ScenarioParams(rho=rho, c=c - phi_low * 0.5, phi=phi_low)
    p_hi = sim.ScenarioParams(rho=rho, c=c - phi_high * 0.5, phi=phi_high)
    psi_grid = {
        "x": xg,
        "low": sim.deterministic_map(xg, p_lo, stress_fn),
        "high": sim.deterministic_map(xg, p_hi, stress_fn),
        "phi_low": phi_low, "phi_high": phi_high,
        "roots_high": sim.fixed_points(p_hi, stress_fn),
    }
    # bifurcation diagram over phi
    bif_rows = []
    phis = np.linspace(0.0, 1.6, 161)
    n_roots = []
    for ph in phis:
        p = sim.ScenarioParams(rho=rho, c=c - ph * 0.5, phi=ph)
        roots = sim.fixed_points(p, stress_fn)
        n_roots.append(len(roots))
        for i, r in enumerate(roots):
            stable = abs(rho + ph * _stress_slope(r)) < 1
            branch = ("low" if i == 0 else "high" if i == len(roots) - 1
                      else "middle")
            bif_rows.append({"phi": ph, "M": sim.sigmoid(r),
                             "branch": branch, "stable": stable})
    bif = pd.DataFrame(bif_rows)
    crit = phis[next((i for i, n in enumerate(n_roots) if n >= 3),
                     len(phis) - 1)]
    bif.attrs["phi_crit"] = float(crit)
    RESULTS["tipping"]["phi_crit"] = float(crit)
    bif.to_csv(OUT / "bifurcation.csv", index=False)

    # ------------------------------------------------------------------
    print("== 9. policy frontier ==")
    efforts = np.linspace(0, 0.30, 13)
    base_D = RESULTS["burden"]["baseline"]["mean"]
    pol_rows = []
    for lever in ["rho", "c", "sigma"]:
        for e in efforts:
            p = sim.ScenarioParams(rho=rho * (1 - e) if lever == "rho" else rho,
                                   c=c * (1 - e) if lever == "c" else c,
                                   sigma_u=sigma_u * (1 - e) if lever == "sigma"
                                   else sigma_u,
                                   x0=c / (1 - rho))
            mp = sim.simulate_paths(p, T=T, n_sims=5000)
            yp = sim.outcome_paths(mp, omap)
            D = float(sim.burden_score(mp, yp, omega, kappa=kappa).mean())
            pol_rows.append({"lever": lever, "effort": e,
                             "dD": 100 * (1 - D / base_D)})
    policy = pd.DataFrame(pol_rows)
    policy.to_csv(OUT / "policy_frontier.csv", index=False)
    RESULTS["policy"] = {
        lever: float(policy[(policy.lever == lever) &
                            (policy.effort > 0.29)].dD.iloc[0])
        for lever in ["rho", "c", "sigma"]
    }

    # ------------------------------------------------------------------
    print("== 10. figures ==")
    F.fig_index_trends(panel)
    F.fig_lp_irfs(lp[lp.h >= 0])
    F.fig_amplification(lp[lp.h >= 0])
    F.fig_growth_at_risk(qlp)
    F.fig_scenarios(m_paths, g_paths)
    F.fig_burden(burden_tab, sweep)
    F.fig_tipping(psi_grid, bif)
    F.fig_policy(policy)

    with open(OUT / "results.json", "w") as f:
        json.dump(RESULTS, f, indent=2, default=float)
    print("\nAll results written to output/results.json")


def _stress_slope(x, slope=6.0, mid=0.6):
    """d/dx [ default_stress_fn(sigmoid(x)) ] for stability classification."""
    m = sim.sigmoid(x)
    s = sim.default_stress_fn(m)
    return s * (1 - s) * slope * m * (1 - m)


if __name__ == "__main__":
    main()
