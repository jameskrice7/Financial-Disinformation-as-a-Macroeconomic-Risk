"""Panel estimation: state equation (Eq. 1), local projections (Eq. 2),
and growth-at-risk quantile projections.

All regressions use country and year fixed effects.  Standard errors are
clustered by country (Driscoll–Kraay available as robustness).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# small within-estimator utilities (transparent, no black boxes)
# --------------------------------------------------------------------------

def _demean_two_way(df: pd.DataFrame, cols: list[str], entity: str,
                    time: str, tol: float = 1e-10, max_iter: int = 200
                    ) -> pd.DataFrame:
    """Iterated two-way within transformation (entity and time FE)."""
    x = df[cols].astype(float).copy()
    for _ in range(max_iter):
        x0 = x.copy()
        x = x - x.groupby(df[entity]).transform("mean")
        x = x - x.groupby(df[time]).transform("mean")
        if (x - x0).abs().to_numpy().max() < tol:
            break
    return x


def panel_ols(df: pd.DataFrame, y: str, xvars: list[str], entity="iso3",
              time="year", cluster=True) -> pd.DataFrame:
    """Two-way FE OLS with entity-clustered standard errors.

    Returns a table with coef, se, t, p and adds n_obs / n_entities attrs.
    """
    cols = [y] + xvars
    d = df[[entity, time] + cols].dropna().reset_index(drop=True)
    w = _demean_two_way(d, cols, entity, time)
    Y = w[y].to_numpy()
    X = w[xvars].to_numpy()
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (X.T @ Y)
    resid = Y - X @ beta

    if cluster:
        meat = np.zeros((len(xvars), len(xvars)))
        for _, idx in d.groupby(entity).indices.items():
            Xg = X[idx]
            ug = resid[idx]
            s = Xg.T @ ug
            meat += np.outer(s, s)
        G = d[entity].nunique()
        n, k = X.shape
        dfc = G / (G - 1) * (n - 1) / (n - k)
        V = dfc * XtX_inv @ meat @ XtX_inv
    else:
        s2 = resid @ resid / (len(Y) - len(xvars))
        V = s2 * XtX_inv

    se = np.sqrt(np.diag(V))
    t = beta / se
    from scipy import stats
    p = 2 * stats.t.sf(np.abs(t), df=d[entity].nunique() - 1)
    out = pd.DataFrame({"coef": beta, "se": se, "t": t, "p": p}, index=xvars)
    out.attrs["n_obs"] = len(d)
    out.attrs["n_entities"] = d[entity].nunique()
    out.attrs["r2_within"] = 1 - resid @ resid / (Y @ Y) if Y @ Y > 0 else np.nan
    return out


# --------------------------------------------------------------------------
# Eq. (1): state equation on the logit scale
# --------------------------------------------------------------------------

def estimate_state_equation(panel: pd.DataFrame) -> dict:
    """logit(M_{t+1}) = a_r + l_t + rho*logit(M_t) + delta*spill + theta'X + u."""
    d = panel.sort_values(["iso3", "year"]).copy()
    d["logitM_lead"] = d.groupby("iso3")["logitM"].shift(-1)
    d["stress"] = d.groupby("iso3")["npl_i"].transform(
        lambda s: (s - s.mean()) / (s.std() if s.std() > 0 else 1.0))
    d["infl_z"] = (d["inflation"].clip(-10, 60) - d["inflation"].clip(-10, 60).mean()) / \
        d["inflation"].clip(-10, 60).std()

    d["stressXlogitM"] = d["stress"] * d["logitM"]
    xvars = ["logitM", "spill", "stress", "stressXlogitM", "infl_z"]
    tab = panel_ols(d, "logitM_lead", xvars)

    # innovation scale: sd of residual implied by within regression
    dd = d[["iso3", "year", "logitM_lead"] + xvars].dropna()
    w = _demean_two_way(dd, ["logitM_lead"] + xvars, "iso3", "year")
    resid = w["logitM_lead"].to_numpy() - w[xvars].to_numpy() @ tab["coef"].to_numpy()
    sigma_u = float(np.std(resid, ddof=len(xvars)))

    # bias-corrected persistence (Nickell 1981, approx: rho_hat + (1+rho_hat)/T)
    T = dd.groupby("iso3")["year"].count().mean()
    rho_hat = float(tab.loc["logitM", "coef"])
    rho_bc = rho_hat + (1 + rho_hat) / T

    return {"table": tab, "sigma_u": sigma_u, "rho": rho_hat,
            "rho_bias_corrected": min(rho_bc, 0.99),
            "delta": float(tab.loc["spill", "coef"]),
            "theta_stress": float(tab.loc["stress", "coef"]),
            "rho_stress": float(tab.loc["stressXlogitM", "coef"]),
            "rho_stress_se": float(tab.loc["stressXlogitM", "se"]),
            "avg_T": float(T)}


# --------------------------------------------------------------------------
# Eq. (2): local projections with fragility interactions
# --------------------------------------------------------------------------

#: outcome variable per channel k
CHANNELS = {
    "G": ("gdp_growth", "cum"),     # cumulative growth over h+1 years
    "N": ("inv_growth", "cum"),     # cumulative investment growth
    "I": ("gini_i", "diff"),        # change in Gini
    "T": ("export_growth", "cum"),  # cumulative export growth
    "F": ("npl_i", "diff"),         # change in NPL ratio
}


def _lp_outcome(d: pd.DataFrame, var: str, h: int, kind: str) -> pd.Series:
    g = d.groupby("iso3")[var]
    if h < 0:  # pre-trend placebo: outcome accumulated over t+h .. t-1
        if kind == "cum":
            return sum(g.shift(-j) for j in range(h, 0))
        return g.shift(1) - g.shift(-h)
    if kind == "cum":
        out = sum(g.shift(-j) for j in range(h + 1))
        return out / 1.0
    # kind == "diff": level change from t-1 to t+h
    return g.shift(-h) - g.shift(1)


def local_projections(panel: pd.DataFrame, horizons=range(0, 5),
                      interactions=True) -> pd.DataFrame:
    """Estimate Eq. (2) per channel and horizon; return long table of coefs."""
    d = panel.sort_values(["iso3", "year"]).copy()

    # standardized conditioning states W = (F, T, I) at time t
    for src, name in [("npl_i", "W_F"), ("trade_gdp", "W_T"), ("gini_i", "W_I")]:
        x = d[src]
        d[name] = (x - x.mean()) / x.std()
    d["M_z"] = (d["M"] - d["M"].mean()) / d["M"].std()

    # controls Z
    d["infl_z"] = (d["inflation"].clip(-10, 60) - d["inflation"].clip(-10, 60).mean()) / \
        d["inflation"].clip(-10, 60).std()
    d["lgdp_pc"] = np.log(d["gdp_pc"])
    d["gov_eff_z"] = (d["gov_eff"] - d["gov_eff"].mean()) / d["gov_eff"].std()
    d["growth_lag"] = d.groupby("iso3")["gdp_growth"].shift(1)

    if interactions:
        for w in ["W_F", "W_T", "W_I"]:
            d[f"Mx{w}"] = d["M_z"] * d[w]
        xvars = ["M_z", "MxW_F", "MxW_T", "MxW_I", "W_F", "W_T", "W_I",
                 "infl_z", "gov_eff_z", "growth_lag"]
    else:
        xvars = ["M_z", "W_F", "W_T", "W_I", "infl_z", "gov_eff_z", "growth_lag"]

    rows = []
    for k, (var, kind) in CHANNELS.items():
        for h in horizons:
            d["_y"] = _lp_outcome(d, var, h, kind)
            # pre-trend placebos: drop the lagged-outcome control, which is
            # mechanically collinear with the h = -1 outcome window
            xv = [v for v in xvars if v != "growth_lag"] if h < 0 else xvars
            tab = panel_ols(d, "_y", xv)
            for v in xv:
                rows.append({"channel": k, "h": h, "var": v,
                             "coef": tab.loc[v, "coef"], "se": tab.loc[v, "se"],
                             "p": tab.loc[v, "p"], "n": tab.attrs["n_obs"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# growth-at-risk: quantile local projections
# --------------------------------------------------------------------------

def quantile_lp(panel: pd.DataFrame, quantiles=(0.1, 0.25, 0.5, 0.75, 0.9),
                h: int = 1) -> pd.DataFrame:
    """Effect of M on the conditional quantiles of h-step cumulative growth.

    Within-transformed quantile regression (Canay 2011 two-step: remove
    estimated fixed effects from a mean regression, then pooled quantile
    regression on the transformed data).
    """
    import statsmodels.api as sm
    from statsmodels.regression.quantile_regression import QuantReg

    d = panel.sort_values(["iso3", "year"]).copy()
    d["M_z"] = (d["M"] - d["M"].mean()) / d["M"].std()
    d["infl_z"] = (d["inflation"].clip(-10, 60) - d["inflation"].clip(-10, 60).mean()) / \
        d["inflation"].clip(-10, 60).std()
    d["W_F"] = (d["npl_i"] - d["npl_i"].mean()) / d["npl_i"].std()
    d["growth_lag"] = d.groupby("iso3")["gdp_growth"].shift(1)
    d["_y"] = _lp_outcome(d, "gdp_growth", h, "cum")

    xvars = ["M_z", "W_F", "infl_z", "growth_lag"]
    dd = d[["iso3", "year", "_y"] + xvars].dropna().reset_index(drop=True)

    # step 1: two-way FE mean regression -> estimated fixed effects
    w = _demean_two_way(dd, ["_y"] + xvars, "iso3", "year")
    beta = np.linalg.lstsq(w[xvars].to_numpy(), w["_y"].to_numpy(), rcond=None)[0]
    fe = dd["_y"].to_numpy() - dd[xvars].to_numpy() @ beta
    fe_entity = pd.Series(fe).groupby(dd["iso3"]).transform("mean")
    y_tilde = dd["_y"] - fe_entity

    X = sm.add_constant(dd[xvars])
    rows = []
    for q in quantiles:
        res = QuantReg(y_tilde, X).fit(q=q)
        rows.append({"q": q, "coef": res.params["M_z"],
                     "se": res.bse["M_z"],
                     "lo": res.conf_int().loc["M_z", 0],
                     "hi": res.conf_int().loc["M_z", 1],
                     "n": int(res.nobs)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# shift-share style IV robustness for Eq. (2), h = 1, growth channel
# --------------------------------------------------------------------------

def iv_growth(panel: pd.DataFrame, h: int = 1) -> dict:
    """2SLS with a shift-share instrument: lagged regional disinformation
    pressure (the shift) interacted with the country's pre-period internet
    penetration share (the exposure weight, fixed at its 2000-2004 mean)."""
    import pathlib
    d = panel.sort_values(["iso3", "year"]).copy()
    net = pd.read_csv(pathlib.Path(__file__).resolve().parents[2] /
                      "data" / "raw" / "internet.csv")
    w = (net[net.year <= 2004].groupby("iso3")["internet"].mean() / 100.0)
    d["exposure"] = d["iso3"].map(w)
    d["M_z"] = (d["M"] - d["M"].mean()) / d["M"].std()
    d["spill_lag"] = d.groupby("iso3")["spill"].shift(1) * d["exposure"]
    d["infl_z"] = (d["inflation"].clip(-10, 60) - d["inflation"].clip(-10, 60).mean()) / \
        d["inflation"].clip(-10, 60).std()
    d["growth_lag"] = d.groupby("iso3")["gdp_growth"].shift(1)
    d["_y"] = _lp_outcome(d, "gdp_growth", h, "cum")

    cols = ["_y", "M_z", "spill_lag", "infl_z", "growth_lag"]
    dd = d[["iso3", "year"] + cols].dropna().reset_index(drop=True)
    w = _demean_two_way(dd, cols, "iso3", "year")

    exog = w[["infl_z", "growth_lag"]].to_numpy()
    z = np.column_stack([w["spill_lag"].to_numpy(), exog])
    x = np.column_stack([w["M_z"].to_numpy(), exog])
    y = w["_y"].to_numpy()

    # first stage
    pi = np.linalg.lstsq(z, w["M_z"].to_numpy(), rcond=None)[0]
    mhat = z @ pi
    r1 = w["M_z"].to_numpy() - mhat
    fstat = ((np.var(mhat) / max(np.var(r1), 1e-12)) * (len(y) - z.shape[1]))

    xhat = np.column_stack([mhat, exog])
    beta = np.linalg.lstsq(xhat, y, rcond=None)[0]
    resid = y - x @ beta
    # cluster-robust (by entity) IV covariance
    XtX = xhat.T @ xhat
    XtX_inv = np.linalg.pinv(XtX)
    meat = np.zeros((x.shape[1], x.shape[1]))
    for _, idx in dd.groupby("iso3").indices.items():
        s = xhat[idx].T @ resid[idx]
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    return {"beta_M": float(beta[0]), "se_M": float(np.sqrt(V[0, 0])),
            "first_stage_F": float(fstat), "n": len(y)}
