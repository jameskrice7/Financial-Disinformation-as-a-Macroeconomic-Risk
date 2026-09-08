"""Regression checks for substantive errors found during manuscript revision."""

import pathlib, sys, unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "code"))
from ccod.estimation import (
    calendar_shift,
    _lp_outcome,
    CHANNELS,
    panel_ols,
    past_fill,
)
from ccod.validation import fit_index, two_way_effects, quantile_fit
from ccod.data import DSP_COMPONENTS
from ccod.simulate import outcome_paths


class RevisionTests(unittest.TestCase):
    def test_calendar_gaps_are_not_adjacent_years(self):
        d = pd.DataFrame(
            {"iso3": ["A"] * 3, "year": [2000, 2002, 2003], "v": [1.0, 3.0, 4.0]}
        )
        lag = calendar_shift(d, "v", 1)
        self.assertTrue(np.isnan(lag.iloc[1]))
        self.assertEqual(lag.iloc[2], 3)
        self.assertTrue(np.isnan(_lp_outcome(d, "v", 1, "cum").iloc[0]))
        self.assertEqual(_lp_outcome(d, "v", 1, "cum").iloc[1], 7)

    def test_forward_carry_respects_calendar_age(self):
        d = pd.DataFrame(
            {"iso3": ["A"] * 3, "year": [2000, 2001, 2005], "v": [2.0, np.nan, np.nan]}
        )
        r = past_fill(d, "v", 2)
        self.assertEqual(r.iloc[1], 2)
        self.assertTrue(np.isnan(r.iloc[2]))

    def test_lp_stress_change_is_not_mechanically_explained(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "output"
        lp = pd.read_csv(root / "lp_results.csv")
        r = lp[(lp.channel == "F") & (lp.h == 0) & (lp["var"] == "M_z")].iloc[0]
        self.assertGreater(r.se, 1e-6)
        self.assertGreater(r.n, 0)

    def test_observed_outcomes_and_nondegenerate_placebo(self):
        self.assertEqual(CHANNELS["F"][0], "npl")
        self.assertEqual(CHANNELS["I"][0], "gini")
        d = pd.DataFrame(
            {
                "iso3": ["A"] * 4,
                "year": [2000, 2001, 2002, 2003],
                "v": [2.0, 5.0, 8.0, np.nan],
            }
        )
        self.assertEqual(_lp_outcome(d, "v", -1, "diff").iloc[2], 3)
        self.assertTrue(np.isnan(_lp_outcome(d, "v", 1, "diff").iloc[2]))

    def test_index_uses_training_only_and_handles_ties(self):
        tr = pd.DataFrame({c: [0.0, 1.0, 1.0, 2.0] for c in DSP_COMPONENTS})
        ev = pd.DataFrame({c: [-1e9, 1.0, 1e9] for c in DSP_COMPONENTS})
        a, b = fit_index(tr, ev)
        a2, b2 = fit_index(tr, ev.iloc[:1])
        np.testing.assert_array_equal(a, a2)
        self.assertEqual(b.iloc[0], b2.iloc[0])
        self.assertTrue(((b > 0) & (b < 1)).all())
        self.assertEqual(a.iloc[1], a.iloc[2])

    def test_two_way_effects_unbalanced(self):
        d = pd.DataFrame({"iso3": ["A", "A", "B", "B", "B"], "year": [0, 1, 0, 1, 2]})
        r = d.iso3.map({"A": 2.0, "B": -1.0}) + d.year.map({0: 3.0, 1: 4.0, 2: 7.0})
        np.testing.assert_allclose(two_way_effects(d, r), r, atol=1e-8)

    def test_quantile_solver_and_contrast_identity(self):
        x = np.column_stack([np.ones(10), np.arange(10)])
        for q in [0.1, 0.5, 0.9]:
            np.testing.assert_allclose(
                quantile_fit(x, x @ np.array([2.0, 3.0]), q), [2, 3], atol=1e-8
            )
        root = pathlib.Path(__file__).resolve().parents[1] / "output"
        if (root / "quantile_contrasts.csv").exists():
            q = pd.read_csv(root / "qlp_results.csv").set_index("q")
            for _, r in pd.read_csv(root / "quantile_contrasts.csv").iterrows():
                self.assertAlmostEqual(
                    r.difference, q.loc[r.q_a, "coef"] - q.loc[r.q_b, "coef"]
                )

    def test_cluster_covariance_matches_explicit_fixed_effect_fit(self):
        import statsmodels.api as sm

        rng = np.random.default_rng(1)
        n = 200
        d = pd.DataFrame(
            {
                "iso3": np.repeat(np.arange(20), 10),
                "year": np.tile(np.arange(10), 20),
                "x": rng.normal(size=n),
                "z": rng.normal(size=n),
            }
        )
        d["y"] = d.x * 2 + d.z * 0.4 + d.iso3 * 0.1 + d.year * 0.3 + rng.normal(size=n)
        result = panel_ols(d, "y", ["x", "z"])
        X = pd.concat(
            [
                d[["x", "z"]],
                pd.get_dummies(d.iso3, prefix="c", drop_first=True, dtype=float),
                pd.get_dummies(d.year, prefix="t", drop_first=True, dtype=float),
            ],
            axis=1,
        )
        fit = sm.OLS(d.y, sm.add_constant(X)).fit(
            cov_type="cluster", cov_kwds={"groups": d.iso3, "use_correction": False}
        )
        np.testing.assert_allclose(result.coef, fit.params[["x", "z"]], atol=1e-9)
        correction = 20 / 19 * (n - 1) / (n - 2)
        np.testing.assert_allclose(
            result.attrs["cov"],
            fit.cov_params().loc[["x", "z"], ["x", "z"]] * correction,
            atol=1e-9,
        )

    def test_invalid_structural_simulation_cannot_run(self):
        with self.assertRaises(NotImplementedError):
            outcome_paths(np.zeros((1, 4)), None)


if __name__ == "__main__":
    unittest.main()
