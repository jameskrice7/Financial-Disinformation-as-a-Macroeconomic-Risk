import Mathlib.Analysis.SpecificLimits.Basic
import Mathlib.Analysis.SpecificLimits.Normed
import Mathlib.Algebra.Field.GeomSum

/-!
Proposition 1: dynamics of the disinformation state on the logit scale.

The deterministic skeleton of Eq. (1) is x_{n+1} = c + ρ x_n.  We verify:
(a) the closed-form solution;
(b) uniqueness of the steady state μ = c/(1-ρ) for ρ ≠ 1;
(c) global convergence to μ when |ρ| < 1;
(d) the stationary-variance geometric series σ²/(1-ρ²).
-/

namespace Ccod

/-- Deterministic skeleton of the state equation: `x_{n+1} = c + ρ x_n`. -/
def orbit (c ρ x₀ : ℝ) : ℕ → ℝ
  | 0 => x₀
  | n + 1 => c + ρ * orbit c ρ x₀ n

/-- Prop. 1(a): closed form `x_n = ρⁿ x₀ + c (1-ρⁿ)/(1-ρ)`. -/
theorem orbit_closed_form (c ρ x₀ : ℝ) (hρ : ρ ≠ 1) (n : ℕ) :
    orbit c ρ x₀ n = ρ ^ n * x₀ + c * (1 - ρ ^ n) / (1 - ρ) := by
  have h1 : (1 : ℝ) - ρ ≠ 0 := sub_ne_zero.mpr (Ne.symm hρ)
  induction n with
  | zero => simp [orbit]
  | succ n ih =>
      simp only [orbit]
      rw [ih]
      field_simp
      ring

/-- Prop. 1(b): the steady state of the skeleton is unique when ρ ≠ 1. -/
theorem steady_state_unique (c ρ x y : ℝ) (hρ : ρ ≠ 1)
    (hx : x = c + ρ * x) (hy : y = c + ρ * y) : x = y := by
  have h : (1 - ρ) * (x - y) = 0 := by nlinarith [hx, hy]
  rcases mul_eq_zero.mp h with h' | h'
  · exact absurd (by linarith : ρ = 1) hρ
  · linarith

/-- Prop. 1(b): `μ = c/(1-ρ)` is a steady state. -/
theorem steady_state_value (c ρ : ℝ) (hρ : ρ ≠ 1) :
    c / (1 - ρ) = c + ρ * (c / (1 - ρ)) := by
  have h1 : (1 : ℝ) - ρ ≠ 0 := sub_ne_zero.mpr (Ne.symm hρ)
  field_simp
  ring

/-- Prop. 1(c): global convergence `x_n → μ` when `|ρ| < 1`
(mean-reversion of the information environment; no information trap
without feedback). -/
theorem orbit_tendsto (c ρ x₀ : ℝ) (hρ : |ρ| < 1) :
    Filter.Tendsto (orbit c ρ x₀) Filter.atTop (nhds (c / (1 - ρ))) := by
  have hρ1 : ρ ≠ 1 := by
    intro h; rw [h] at hρ; simp at hρ
  have hpow : Filter.Tendsto (fun n : ℕ => ρ ^ n) Filter.atTop (nhds 0) :=
    tendsto_pow_atTop_nhds_zero_of_abs_lt_one hρ
  have h1 : (1 : ℝ) - ρ ≠ 0 := sub_ne_zero.mpr (Ne.symm hρ1)
  have key : Filter.Tendsto
      (fun n : ℕ => ρ ^ n * x₀ + c * (1 - ρ ^ n) / (1 - ρ))
      Filter.atTop (nhds (0 * x₀ + c * (1 - 0) / (1 - ρ))) := by
    exact ((hpow.mul_const x₀).add
      (((tendsto_const_nhds.sub hpow).const_mul c).div_const (1 - ρ)))
  have : (0 : ℝ) * x₀ + c * (1 - 0) / (1 - ρ) = c / (1 - ρ) := by ring
  rw [this] at key
  exact key.congr fun n => (orbit_closed_form c ρ x₀ hρ1 n).symm

/-- Prop. 1(d): stationary variance.  The MA(∞) representation gives
`Var = Σ_j ρ^{2j} σ² = σ²/(1-ρ²)`; persistence amplifies the variance of
information shocks by the factor `1/(1-ρ²)`. -/
theorem stationary_variance (s ρ : ℝ) (hρ : |ρ| < 1) :
    ∑' j : ℕ, (ρ ^ 2) ^ j * s ^ 2 = s ^ 2 / (1 - ρ ^ 2) := by
  have h0 : (0 : ℝ) ≤ ρ ^ 2 := sq_nonneg ρ
  have h1 : ρ ^ 2 < 1 := by
    have := abs_lt.mp hρ
    nlinarith
  rw [tsum_mul_right, tsum_geometric_of_lt_one h0 h1, inv_mul_eq_div]

end Ccod
