"""Generate complete table environments and numerical macros from revised outputs."""

import json, pathlib, sys
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "output"
TAB = ROOT / "paper/tables"


def star(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def tex(s):
    return str(s).replace("&", r"\&").replace("_", r"\_")


def table(file, caption, label, headers, rows, note):
    spec = "l" + "r" * (len(headers) - 1)
    body = "\n".join(" & ".join(map(str, r)) + r" \\" for r in rows)
    text = r"""\begin{table}[!htbp]
\centering\small
\caption{CAPTION}\label{LABEL}
\begin{tabular}{SPEC}\toprule
HEAD \\
\midrule
BODY
\bottomrule\end{tabular}
\par\smallskip\begin{minipage}{0.98\linewidth}\footnotesize NOTE\end{minipage}
\end{table}
"""
    for a, b in [
        ("CAPTION", caption),
        ("LABEL", label),
        ("SPEC", spec),
        ("HEAD", " & ".join(headers)),
        ("BODY", body),
        ("NOTE", note),
    ]:
        text = text.replace(a, b)
    (TAB / file).write_text(text)


def main(panel=None):
    TAB.mkdir(parents=True, exist_ok=True)
    if panel is None:
        panel = pd.read_csv(ROOT / "data/processed/panel.csv")
    r = json.loads((OUT / "results.json").read_text())
    lp = pd.read_csv(OUT / "lp_results.csv")
    q = pd.read_csv(OUT / "qlp_results.csv")
    labels = {
        "G": "Growth",
        "N": "Investment",
        "I": "Inequality",
        "T": "Exports",
        "F": "NPLs",
    }
    rows = []
    for k in labels:
        for h in range(5):
            z = lp[(lp.channel == k) & (lp.h == h)].set_index("var")
            m = z.loc["M_z"]
            f = z.loc["MxW_F"]
            rows.append(
                [
                    labels[k] if h == 0 else "",
                    str(h),
                    f"{m.coef:.2f}{star(m.p)}",
                    f"({m.se:.2f})",
                    f"{f.coef:.2f}{star(f.p)}",
                    f"({f.se:.2f})",
                    f"{int(m.n):,}",
                ]
            )
    table(
        "revised_lp.tex",
        "Conditional associations and banking-stress interactions",
        "tab:lp",
        ["Outcome", "$h$", "$M$", "SE", "$M\\times F$", "SE", "$n$"],
        rows,
        r"Growth, investment and exports sum annual growth from $t$ through $t+h$ (percentage points); Gini and NPL outcomes are observed changes from $t-1$ through $t+h$. Thus $h=2$ includes three annual observations. Country and year effects; country-clustered SEs. $M$ coefficient is evaluated at mean conditioning states. $^{***},^{**},^*$ denote 1, 5 and 10 percent significance. No outcome interpolation.",
    )
    st = pd.read_csv(OUT / "state_equation.csv", index_col=0)
    labs = {
        "logitM": "Index persistence",
        "spill": "Regional association",
        "stress": "Banking stress",
        "stressXlogitM": "Stress $\\times$ latent index",
        "infl_z": "Inflation",
    }
    table(
        "revised_state.tex",
        "Conditional index dynamics",
        "tab:state",
        ["Regressor", "Estimate", "SE"],
        [
            [labs[v], f"{a.coef:.3f}{star(a.p)}", f"({a.se:.3f})"]
            for v, a in st.iterrows()
        ],
        f"Country and year effects; {r['state']['n_obs']:,} observations from {r['state']['n_entities']} countries. Stress is standardized within country. The persistence adjustment discussed in the text is an uncapped approximation.",
    )
    table(
        "revised_quantiles.tex",
        "Two-year cumulative growth: conditional quantile slopes",
        "tab:gar",
        ["Quantile", "Slope", "90\\% interval", "$n$"],
        [
            [
                f"{100 * a.q:.0f}th",
                f"{a.coef:.2f}",
                f"[{a.lo:.2f}, {a.hi:.2f}]",
                f"{int(a.n):,}",
            ]
            for _, a in q.iterrows()
        ],
        f"{r['bootstrap_reps']} country-block bootstrap replications, refitting both stages. Intervals condition on the observed index and additive country/year location effects.",
    )
    c = pd.read_csv(OUT / "quantile_contrasts.csv")
    table(
        "revised_contrasts.tex",
        "Tests of differences between quantile slopes",
        "tab:contrasts",
        ["Contrast", "Difference", "90\\% interval", "$p$"],
        [
            [
                f"{100 * a.q_a:.0f}th minus {100 * a.q_b:.0f}th",
                f"{a.difference:.2f}",
                f"[{a.lo:.2f}, {a.hi:.2f}]",
                f"{a.p:.3f}",
            ]
            for _, a in c.iterrows()
        ],
        r"Paired country-block draws preserve covariance between quantile estimates; $p$ values use the centered bootstrap null distribution. These are pointwise tests, without multiplicity adjustment.",
    )
    f = pd.read_csv(OUT / "forecast_scores.csv")
    b = f[f.model == "benchmark"].set_index("metric")
    forecast_aug = f[f.model == "disinformation"]
    table(
        "revised_forecast.tex",
        "Pseudo out-of-sample forecast comparison",
        "tab:forecast",
        ["Loss", "Benchmark", "With index", "Gain (\\%)", "90\\% interval"],
        [
            [
                tex(row.metric)
                .replace("squared\\_error", "Mean squared error")
                .replace("pinball\\_", "Pinball "),
                f"{b.loc[row.metric, 'loss']:.3f}",
                f"{row.loss:.3f}",
                f"{row.improvement_pct:.2f}",
                f"[{row.lo:.2f}, {row.hi:.2f}]",
            ]
            for _, row in forecast_aug.iterrows()
        ],
        r"Positive gain means lower loss. Identical evaluation samples; target years 2015--2024. Predictor availability lag is one year; training targets end before the forecast origin. Components, index ranks and scaling are fitted within training windows. Intervals resample entire target years (1,999 draws; only ten year blocks). Latest-vintage inputs make this a pseudo rather than real-time evaluation.",
    )
    rob = pd.read_csv(OUT / "robustness.csv")
    rows = []
    for name, z in rob[(rob.channel == "G") & (rob.h == 2)].groupby("specification"):
        z = z.set_index("var")
        m = z.loc["M_z"]
        i = z.loc["MxW_F"]
        rows.append(
            [
                tex(name).replace("omit\\_", "Omit "),
                f"{m.coef:.2f}{star(m.p)}",
                f"({m.se:.2f})",
                f"{i.coef:.2f}{star(i.p)}",
                f"{int(m.n):,}",
            ]
        )
    table(
        "revised_robustness.tex",
        "Growth associations under alternative specifications ($h=2$)",
        "tab:robustness",
        ["Specification", "$M$", "SE", "$M\\times F$", "$n$"],
        rows,
        r"No-fill uses observed conditioning states only. Raw-composite uses the unranked weighted index; each index is standardized in its specification. Alternative weights and samples can change results; stability is not presumed.",
    )
    rows = []
    for k in labels:
        for h in [-2, -1]:
            a = lp[(lp.channel == k) & (lp.h == h) & (lp["var"] == "M_z")].iloc[0]
            rows.append(
                [
                    labels[k],
                    str(h),
                    f"{a.coef:.2f}{star(a.p)}",
                    f"({a.se:.2f})",
                    f"{int(a.n):,}",
                ]
            )
    table(
        "revised_placebo.tex",
        "Associations with prior outcomes",
        "tab:placebo",
        ["Outcome", "$h$", "Coefficient", "SE", "$n$"],
        rows,
        r"Past growth outcomes sum years $t+h$ through $t-1$; past level changes run from $t+h-1$ to $t-1$. Lagged outcomes are omitted to avoid mechanical overlap. These are reverse-timing diagnostics, not clean falsification tests for a persistent index.",
    )
    rows = []
    for lab, col in [
        ("Disinformation index", "M"),
        ("GDP growth", "gdp_growth"),
        ("Investment growth", "inv_growth"),
        ("Gini", "gini"),
        ("Export growth", "export_growth"),
        ("NPL ratio", "npl"),
    ]:
        s = panel[col].dropna()
        rows.append([lab, f"{s.mean():.2f}", f"{s.std():.2f}", f"{len(s):,}"])
    table(
        "revised_summary.tex",
        "Observed data coverage",
        "tab:summary",
        ["Variable", "Mean", "SD", "$n$"],
        rows,
        "Unfilled outcome observations. Regression samples are smaller because covariates, lags and leads must be observed.",
    )
    macros = {
        "Rho": f"{r['state']['rho']:.3f}",
        "RhoSE": f"{st.loc['logitM', 'se']:.3f}",
        "RhoBC": f"{r['state']['rho_bias_corrected']:.3f}",
        "HalfLife": f"{r['half_life']:.1f}",
        "StateN": str(int(r["state"]["n_obs"])),
        "StateCountries": str(int(r["state"]["n_entities"])),
        "NetworkSlope": f"{r['rho_plus_delta']:.3f}",
        "BootReps": str(r["bootstrap_reps"]),
    }
    for h in [1, 2, 3]:
        z = lp[(lp.channel == "G") & (lp.h == h)].set_index("var")
        macros[f"Growth{['Zero', 'One', 'Two', 'Three'][h]}"] = (
            f"{z.loc['M_z', 'coef']:.2f}"
        )
        macros[f"Fragility{['Zero', 'One', 'Two', 'Three'][h]}"] = (
            f"{z.loc['MxW_F', 'coef']:.2f}"
        )
    for _, row in q.iterrows():
        macros[
            "Quantile"
            + {
                0.1: "Ten",
                0.25: "TwentyFive",
                0.5: "Fifty",
                0.75: "SeventyFive",
                0.9: "Ninety",
            }[row.q]
        ] = f"{row.coef:.2f}"
    for _, row in forecast_aug.iterrows():
        key = {
            "squared_error": "Mean",
            "pinball_0.1": "Tail",
            "pinball_0.5": "Median",
            "pinball_0.9": "Upper",
        }[row.metric]
        macros["Forecast" + key] = f"{row.improvement_pct:.2f}"
    (TAB / "results_macros.tex").write_text(
        "\n".join("\\newcommand{\\" + k + "}{" + v + "}" for k, v in macros.items())
        + "\n"
    )


if __name__ == "__main__":
    main()
