"""Monte Carlo validation of the two-step design.

Generates synthetic panels from the model's own DGP (state equation +
state-dependent outcome equation) and checks that the estimation pipeline
recovers (i) the persistence rho, (ii) the mean outcome effect beta, and
(iii) the interaction (amplification) coefficient phi -- including the
tail-concentration prediction of Proposition 2.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .estimation import panel_ols, _demean_two_way
from .simulate import sigmoid, logit


def simulate_panel_dgp(R=150, T=24, rho=0.85, c=0.0, sigma_u=0.5,
                       beta=-0.4, phi=-0.5, seed=1) -> pd.DataFrame:
    """Country-year DGP with heterogeneous intercepts, year shocks, and a
    fragility-interacted outcome equation.

    Outcome: g_{r,t+1} = a_r + l_t + beta*Mz + phi*Mz*F + 0.3F + e,
    where F is slow-moving fragility.
    """
    rng = np.random.default_rng(seed)
    a_r = rng.normal(0, 0.5, R)           # state-eq country effects
    l_t = rng.normal(0, 0.2, T)
    ag_r = rng.normal(2.0, 1.0, R)        # growth country effects
    lg_t = rng.normal(0, 0.8, T)

    rows = []
    for r in range(R):
        x = a_r[r] / (1 - rho)
        F = np.clip(rng.normal(0, 1), -2, 2)
        for t in range(T):
            F = 0.9 * F + rng.normal(0, 0.3)
            x = a_r[r] + l_t[t] + rho * (x - 0) + rng.normal(0, sigma_u)
            M = sigmoid(x)
            rows.append({"iso3": f"C{r:03d}", "year": 2000 + t,
                         "M": M, "logitM": x, "F": F})
    d = pd.DataFrame(rows)
    d["Mz"] = (d["M"] - d["M"].mean()) / d["M"].std()
    # outcome at t+1 responds to the information state at t (LP timing)
    d["Mz_lag"] = d.groupby("iso3")["Mz"].shift(1)
    d["F_lag"] = d.groupby("iso3")["F"].shift(1)
    d["g"] = (np.repeat(ag_r, T) + np.tile(lg_t, R)
              + beta * d["Mz_lag"].fillna(0)
              + phi * (d["Mz_lag"] * d["F_lag"]).fillna(0)
              + 0.3 * d["F"] + rng.normal(0, 1.5, R * T))
    return d


def run_montecarlo(n_rep=200, **dgp_kwargs) -> pd.DataFrame:
    """Repeat DGP + estimation; return distribution of estimates."""
    true = dict(rho=0.85, beta=-0.4, phi=-0.5)
    true.update({k: v for k, v in dgp_kwargs.items() if k in true})
    recs = []
    for rep in range(n_rep):
        d = simulate_panel_dgp(seed=1000 + rep, **dgp_kwargs)
        # state equation
        d2 = d.copy()
        d2["logitM_lead"] = d2.groupby("iso3")["logitM"].shift(-1)
        t1 = panel_ols(d2, "logitM_lead", ["logitM"])
        rho_hat = t1.loc["logitM", "coef"]
        T = d2.groupby("iso3")["year"].count().mean()
        rho_bc = rho_hat + (1 + rho_hat) / T
        # outcome equation with interaction (same timing as the LPs)
        d2["MxF"] = d2["Mz_lag"] * d2["F_lag"]
        t2 = panel_ols(d2, "g", ["Mz_lag", "MxF", "F"])
        recs.append({"rep": rep, "rho_hat": rho_hat, "rho_bc": rho_bc,
                     "beta_hat": t2.loc["Mz_lag", "coef"],
                     "phi_hat": t2.loc["MxF", "coef"]})
    out = pd.DataFrame(recs)
    out.attrs["true"] = true
    return out


def summarize_montecarlo(mc: pd.DataFrame) -> pd.DataFrame:
    true = mc.attrs["true"]
    rows = []
    for est, tr in [("rho_hat", true["rho"]), ("rho_bc", true["rho"]),
                    ("beta_hat", true["beta"]), ("phi_hat", true["phi"])]:
        rows.append({
            "estimator": est, "true": tr,
            "mean": mc[est].mean(), "bias": mc[est].mean() - tr,
            "sd": mc[est].std(),
            "rmse": np.sqrt(((mc[est] - tr) ** 2).mean()),
        })
    return pd.DataFrame(rows)
