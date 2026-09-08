"""Revised inference and chronological validation using repository panel data.

Forecast evaluation is pseudo out of sample: transforms and models are fitted
on training years only, but input releases are the latest available vintage.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, eye, hstack
from .estimation import _demean_two_way, _lp_outcome, calendar_shift, past_fill
from .data import DSP_COMPONENTS


def quantile_fit(X, y, q):
    """Exact check-loss LP; avoids silently accepting unconverged IRLS fits."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n, k = X.shape
    A = hstack([csr_matrix(X), eye(n), -eye(n)], format="csr")
    cost = np.r_[np.zeros(k), np.full(n, q), np.full(n, 1 - q)]
    fit = linprog(
        cost,
        A_eq=A,
        b_eq=y,
        bounds=[(None, None)] * k + [(0, None)] * (2 * n),
        method="highs",
        options={"threads": 1},
    )
    if not fit.success:
        raise RuntimeError(f"Quantile optimization failed: {fit.message}")
    return fit.x[:k]


def two_way_effects(d, residual):
    """Additive entity + year effects, estimated by backfitting on residuals."""
    r = pd.Series(np.asarray(residual), index=d.index)
    a = pd.Series(0.0, index=d.index)
    t = a.copy()
    for _ in range(300):
        old = a + t
        a = (r - t).groupby(d.iso3).transform("mean")
        t = (r - a).groupby(d.year).transform("mean")
        if np.max(np.abs(a + t - old)) < 1e-10:
            return a + t
    raise RuntimeError("Fixed-effect backfitting did not converge")


def quantile_sample(panel, h):
    d = panel.sort_values(["iso3", "year"]).copy()
    for src, dst in [("M", "M_z"), ("npl_i", "W_F"), ("gov_eff", "gov_eff_z")]:
        d[dst] = (d[src] - d[src].mean()) / d[src].std()
    x = d.inflation.clip(-10, 60)
    d["infl_z"] = (x - x.mean()) / x.std()
    d["growth_lag"] = calendar_shift(d, "gdp_growth", 1)
    d["lgdp_pc"] = np.log(d.gdp_pc.where(d.gdp_pc > 0))
    d["_y"] = _lp_outcome(d, "gdp_growth", h, "cum")
    cols = ["M_z", "W_F", "infl_z", "growth_lag", "lgdp_pc", "gov_eff_z"]
    return d[["iso3", "year", "_y"] + cols].dropna().reset_index(drop=True), cols


def _two_step(d, cols, qs):
    w = _demean_two_way(d, ["_y"] + cols, "iso3", "year")
    b = np.linalg.lstsq(w[cols], w._y, rcond=None)[0]
    fe = two_way_effects(d, d._y.to_numpy() - d[cols].to_numpy() @ b)
    yt = d._y.to_numpy() - fe.to_numpy()
    X = np.column_stack([np.ones(len(d)), d[cols].to_numpy()])
    return np.array([quantile_fit(X, yt, q)[1] for q in qs])


def quantile_inference(
    panel, quantiles=(0.1, 0.25, 0.5, 0.75, 0.9), h=1, n_boot=399, seed=20260908
):
    """Country block bootstrap refits both FE and quantile stages.

    Inference conditions on the measured index and treats common year effects
    as additive location shifts. It does not incorporate expert measurement
    uncertainty or fully allow residual dependence between countries.
    """
    d, cols = quantile_sample(panel, h)
    point = _two_step(d, cols, quantiles)
    ids = d.iso3.unique()
    groups = {c: g for c, g in d.groupby("iso3")}
    rng = np.random.default_rng(seed)
    draws = []
    for b in range(n_boot):
        blocks = [
            groups[c].assign(iso3=f"boot{i}")
            for i, c in enumerate(rng.choice(ids, len(ids)))
        ]
        sample = pd.concat(blocks, ignore_index=True)
        draws.append(_two_step(sample, cols, quantiles))
        if (b + 1) % 50 == 0:
            print(f"quantile bootstrap {b + 1}/{n_boot}", flush=True)
    draws = np.asarray(draws)
    result = pd.DataFrame(
        {
            "q": quantiles,
            "coef": point,
            "se": draws.std(axis=0, ddof=1),
            "lo": np.quantile(draws, 0.05, axis=0),
            "hi": np.quantile(draws, 0.95, axis=0),
            "n": len(d),
            "countries": len(ids),
            "bootstrap_reps": n_boot,
            "h": h,
        }
    )
    contrasts = []
    for qa, qb in [(0.1, 0.5), (0.1, 0.9)]:
        ia = list(quantiles).index(qa)
        ib = list(quantiles).index(qb)
        delta = draws[:, ia] - draws[:, ib]
        observed = point[ia] - point[ib]
        # Centered bootstrap null distribution; finite-Monte-Carlo correction.
        p = (1 + np.sum(np.abs(delta - observed) >= abs(observed))) / (n_boot + 1)
        contrasts.append(
            {
                "q_a": qa,
                "q_b": qb,
                "difference": observed,
                "lo": np.quantile(delta, 0.05),
                "hi": np.quantile(delta, 0.95),
                "p": p,
                "n_boot": n_boot,
            }
        )
    return (
        result,
        pd.DataFrame(contrasts),
        pd.DataFrame(draws, columns=[f"q{q}" for q in quantiles]),
    )


def fit_index(training, evaluation, weights=None):
    """Fit component means/SDs and empirical CDF on training observations only."""
    weights = DSP_COMPONENTS if weights is None else weights
    cols = list(weights)
    mu = (-training[cols]).mean()
    sd = (-training[cols]).std()
    if sd.isna().any() or (sd <= 0).any():
        raise ValueError("Constant or missing index component in training data")

    def composite(d):
        return (((-d[cols] - mu) / sd) * pd.Series(weights)).sum(axis=1, skipna=False)

    tr = composite(training)
    ev = composite(evaluation)
    ref = np.sort(tr.dropna().to_numpy())
    n = len(ref)

    def transform(s):
        # Midrank for ties; clip out-of-training-range values to finite tails.
        a = np.searchsorted(ref, s.to_numpy(), side="left")
        b = np.searchsorted(ref, s.to_numpy(), side="right")
        out = pd.Series(np.clip((a + b) / (2 * n), 0.5 / n, 1 - 0.5 / n), index=s.index)
        return out.where(s.notna())

    return transform(tr), transform(ev)


def forecast_validation(panel, components, first_origin=2014, last_origin=2023):
    """At origin t, predict t+1 growth using t-1 macro/DSP covariates.

    Macro/DSP inputs have a conservative one-year availability lag. Training
    targets must end by origin-1. Same sample for benchmark and augmented
    models. No future year dummy, interpolation, or updated full-panel rank.
    Latest-vintage data still preclude a real-time forecasting claim.
    """
    d = panel.sort_values(["iso3", "year"]).copy()
    for src in ["npl", "credit_gdp"]:
        d[src + "_past"] = past_fill(d, src, 2)
    d["lgdp_pc"] = np.log(d.gdp_pc.where(d.gdp_pc > 0))
    d["infl_clip"] = d.inflation.clip(-10, 60)
    # Source row s becomes information at origin s+1, target s+2.
    d["target"] = calendar_shift(d, "gdp_growth", -2)
    d = d.merge(components, on=["iso3", "year"], how="left", validate="one_to_one")
    baseline = [
        "gdp_growth",
        "infl_clip",
        "lgdp_pc",
        "trade_gdp",
        "npl_past",
        "credit_gdp_past",
        "gov_eff",
    ]
    records = []
    for origin in range(first_origin, last_origin + 1):
        train = d[d.year + 2 <= origin - 1].copy()
        test = d[d.year == origin - 1].copy()
        mtr, mte = fit_index(train, test)
        train["M_train"] = mtr
        test["M_train"] = mte
        needed = baseline + ["M_train", "target"]
        train = train.dropna(subset=needed)
        test = test.dropna(subset=needed)
        # Seen countries only; fixed effects fitted solely on training data.
        cats = sorted(train.iso3.unique())
        test = test[test.iso3.isin(cats)]
        if len(test) == 0:
            continue
        mu = train[baseline + ["M_train"]].mean()
        sd = train[baseline + ["M_train"]].std()
        tr = (train[baseline + ["M_train"]] - mu) / sd
        te = (test[baseline + ["M_train"]] - mu) / sd
        for name, features in [
            ("benchmark", baseline),
            ("disinformation", baseline + ["M_train"]),
        ]:
            # Direct conditional forecasting with country intercepts; no year FE
            # that would require estimating the target year's common shock.
            country_tr = pd.get_dummies(
                pd.Categorical(train.iso3, categories=cats),
                drop_first=True,
                dtype=float,
            ).to_numpy()
            country_te = pd.get_dummies(
                pd.Categorical(test.iso3, categories=cats), drop_first=True, dtype=float
            ).to_numpy()
            X = np.column_stack([np.ones(len(train)), tr[features], country_tr])
            Z = np.column_stack([np.ones(len(test)), te[features], country_te])
            y = train.target.to_numpy()
            b = np.linalg.lstsq(X, y, rcond=None)[0]
            pred = Z @ b
            for i, (_, row) in enumerate(test.iterrows()):
                records.append(
                    {
                        "origin": origin,
                        "target_year": origin + 1,
                        "iso3": row.iso3,
                        "model": name,
                        "metric": "squared_error",
                        "loss": float((row.target - pred[i]) ** 2),
                        "actual": row.target,
                        "prediction": pred[i],
                        "n_train": len(train),
                    }
                )
            for q in [0.1, 0.5, 0.9]:
                b = quantile_fit(X, y, q)
                pred = Z @ b
                e = test.target.to_numpy() - pred
                loss = np.maximum(q * e, (q - 1) * e)
                for i, (_, row) in enumerate(test.iterrows()):
                    records.append(
                        {
                            "origin": origin,
                            "target_year": origin + 1,
                            "iso3": row.iso3,
                            "model": name,
                            "metric": f"pinball_{q}",
                            "loss": float(loss[i]),
                            "actual": row.target,
                            "prediction": pred[i],
                            "n_train": len(train),
                        }
                    )
        print(
            f"forecast origin {origin}, train {len(train)}, test {len(test)}",
            flush=True,
        )
    scores = pd.DataFrame(records)
    agg = (
        scores.groupby(["metric", "model"])
        .agg(loss=("loss", "mean"), n=("loss", "size"))
        .reset_index()
    )
    base = agg[agg.model == "benchmark"].set_index("metric").loss
    agg["improvement_pct"] = 100 * (1 - agg.loss / agg.metric.map(base))
    # Resample complete target years to retain within-year dependence.
    ci = []
    rng = np.random.default_rng(20260908)
    for metric, sub in scores.groupby("metric"):
        pairs = sub.pivot(
            index=["target_year", "iso3"], columns="model", values="loss"
        ).dropna()
        byyear = pairs.groupby(level="target_year").sum()
        draws = []
        for _ in range(1999):
            sample = rng.integers(0, len(byyear), len(byyear))
            a = byyear.iloc[sample].sum()
            draws.append(100 * (1 - a.disinformation / a.benchmark))
        ci.append(
            {
                "metric": metric,
                "lo": np.quantile(draws, 0.05),
                "hi": np.quantile(draws, 0.95),
                "target_years": len(byyear),
            }
        )
    return scores, agg.merge(pd.DataFrame(ci), on="metric")
