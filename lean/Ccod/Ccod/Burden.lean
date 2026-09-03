import Mathlib.Algebra.Field.GeomSum
import Mathlib.Analysis.Calculus.Deriv.Add
import Mathlib.Analysis.Calculus.Deriv.Inv
import Mathlib.Tactic

/-!
Proposition 4: the burden score and the Half-Life Rule.

(i)   The discounted, disinformation-weighted burden score of Eq. (3) is
      uniformly bounded by Ȳ(1+κ)/κ at every horizon: the risk metric
      cannot explode, so cross-country and cross-scenario comparisons are
      well defined.
(ii)  Half-Life Rule: with stationary mean μ(c,ρ) = c/(1−ρ), the
      elasticity of μ with respect to persistence ρ is ρ/(1−ρ), while the
      elasticity with respect to the inflow c is 1.  Persistence-targeting
      policy (rapid correction) dominates inflow-targeting policy
      (friction) precisely when ρ > 1/2 — i.e. when the half-life of a
      false narrative exceeds one period.
(iii) μ is midpoint-convex in ρ: increasing returns to de-amplification
      as the environment approaches the trap boundary ρ → 1.
-/

namespace Ccod

/-- Prop. 4(i): burden-score bound.  If each signed outcome response is
bounded by Ȳ and the weights M_h lie in [0,1], then for κ > 0 the
horizon-H burden score satisfies |D| ≤ Ȳ(1+κ)/κ, uniformly in H. -/
theorem burden_bound (κ Ybar : ℝ) (hκ : 0 < κ) (M Y : ℕ → ℝ)
    (hM0 : ∀ h, 0 ≤ M h) (hM1 : ∀ h, M h ≤ 1) (hY : ∀ h, |Y h| ≤ Ybar)
    (H : ℕ) :
    |∑ h ∈ Finset.range (H + 1), ((1 + κ)⁻¹) ^ h * M h * Y h| ≤
      Ybar * (1 + κ) / κ := by
  set r : ℝ := (1 + κ)⁻¹ with hr
  have hr0 : 0 ≤ r := by positivity
  have hr1 : r < 1 := by
    rw [hr, inv_lt_one_iff₀]; right; linarith
  have hYbar : 0 ≤ Ybar := le_trans (abs_nonneg _) (hY 0)
  -- termwise bound |r^h M_h Y_h| ≤ Ȳ r^h
  have hterm : ∀ h, |r ^ h * M h * Y h| ≤ Ybar * r ^ h := by
    intro h
    rw [abs_mul, abs_mul, abs_pow, abs_of_nonneg hr0, abs_of_nonneg (hM0 h)]
    have h1 : r ^ h * M h ≤ r ^ h * 1 :=
      mul_le_mul_of_nonneg_left (hM1 h) (pow_nonneg hr0 h)
    have h2 : |Y h| ≤ Ybar := hY h
    calc r ^ h * M h * |Y h| ≤ (r ^ h * 1) * Ybar := by
          apply mul_le_mul (by linarith) h2 (abs_nonneg _)
          positivity
      _ = Ybar * r ^ h := by ring
  -- partial geometric sum bound Σ r^h ≤ 1/(1−r) = (1+κ)/κ
  have hgeom : ∑ h ∈ Finset.range (H + 1), r ^ h ≤ (1 + κ) / κ := by
    have hne : r ≠ 1 := ne_of_lt hr1
    rw [geom_sum_eq hne]
    have h1r : 0 < 1 - r := by linarith
    have hpow : 0 ≤ r ^ (H + 1) := pow_nonneg hr0 _
    have key : (r ^ (H + 1) - 1) / (r - 1) = (1 - r ^ (H + 1)) / (1 - r) := by
      rw [div_eq_div_iff (by linarith) (by linarith)]; ring
    rw [key]
    have h2 : (1 - r ^ (H + 1)) / (1 - r) ≤ 1 / (1 - r) := by
      gcongr
      linarith
    have h3 : (1 : ℝ) - r = κ / (1 + κ) := by
      have hκ1 : (0 : ℝ) < 1 + κ := by linarith
      rw [hr, eq_div_iff (ne_of_gt hκ1), sub_mul, inv_mul_cancel₀ (ne_of_gt hκ1)]
      ring
    have h4 : (1 : ℝ) / (1 - r) = (1 + κ) / κ := by
      rw [h3, one_div_div]
    linarith [h2, h4.le, h4.ge]
  calc |∑ h ∈ Finset.range (H + 1), r ^ h * M h * Y h|
      ≤ ∑ h ∈ Finset.range (H + 1), |r ^ h * M h * Y h| :=
        Finset.abs_sum_le_sum_abs _ _
    _ ≤ ∑ h ∈ Finset.range (H + 1), Ybar * r ^ h :=
        Finset.sum_le_sum fun h _ => hterm h
    _ = Ybar * ∑ h ∈ Finset.range (H + 1), r ^ h := by
        rw [Finset.mul_sum]
    _ ≤ Ybar * ((1 + κ) / κ) :=
        mul_le_mul_of_nonneg_left hgeom hYbar
    _ = Ybar * (1 + κ) / κ := by ring

/-- Stationary mean of the latent state: μ(c,ρ) = c/(1−ρ). -/
noncomputable def statMean (c ρ : ℝ) : ℝ := c / (1 - ρ)

/-- Marginal value of persistence reduction: ∂μ/∂ρ = c/(1−ρ)². -/
theorem statMean_hasDerivAt_rho (c ρ : ℝ) (h : ρ ≠ 1) :
    HasDerivAt (fun r => statMean c r) (c / (1 - ρ) ^ 2) ρ := by
  have h0 : (1 : ℝ) - ρ ≠ 0 := sub_ne_zero.mpr (Ne.symm h)
  have h1 : HasDerivAt (fun r : ℝ => 1 - r) (0 - 1) ρ :=
    HasDerivAt.sub (hasDerivAt_const ρ (1 : ℝ)) (hasDerivAt_id' ρ)
  rw [zero_sub] at h1
  have h2 : HasDerivAt (fun r : ℝ => c / (1 - r))
      ((0 * (1 - ρ) - c * (-1)) / (1 - ρ) ^ 2) ρ :=
    (hasDerivAt_const ρ c).fun_div h1 h0
  have hval : (0 * (1 - ρ) - c * (-1)) / (1 - ρ) ^ 2 = c / (1 - ρ) ^ 2 := by
    ring
  rw [hval] at h2
  exact h2

/-- Prop. 4(ii), the Half-Life Rule: the elasticity of the stationary
disinformation level with respect to persistence, ρ/(1−ρ), exceeds the
(unit) elasticity with respect to the inflow exactly when ρ > 1/2. -/
theorem half_life_rule (ρ : ℝ) (h0 : 0 < ρ) (h1 : ρ < 1) :
    1 < ρ / (1 - ρ) ↔ 1 / 2 < ρ := by
  rw [lt_div_iff₀ (by linarith)]
  constructor <;> intro h <;> linarith

/-- Elasticity identity: (∂μ/∂ρ)·(ρ/μ) = ρ/(1−ρ) whenever c ≠ 0. -/
theorem elasticity_identity (c ρ : ℝ) (hc : c ≠ 0) (h1 : ρ ≠ 1) :
    (c / (1 - ρ) ^ 2) * (ρ / statMean c ρ) = ρ / (1 - ρ) := by
  have h0 : (1 : ℝ) - ρ ≠ 0 := sub_ne_zero.mpr (Ne.symm h1)
  unfold statMean
  field_simp

/-- Prop. 4(iii): μ is midpoint-convex in ρ on (−∞,1) for c ≥ 0 —
increasing returns to de-amplification near the trap boundary. -/
theorem statMean_midpoint_convex (c a b : ℝ) (hc : 0 ≤ c)
    (ha : a < 1) (hb : b < 1) :
    statMean c ((a + b) / 2) ≤ (statMean c a + statMean c b) / 2 := by
  unfold statMean
  set u : ℝ := 1 - a with hu
  set v : ℝ := 1 - b with hv
  have hu0 : 0 < u := by rw [hu]; linarith
  have hv0 : 0 < v := by rw [hv]; linarith
  have hmid : (1 : ℝ) - (a + b) / 2 = (u + v) / 2 := by rw [hu, hv]; ring
  rw [hmid]
  have huv : 0 < u + v := by linarith
  rw [div_le_div_iff₀ (by linarith) (by norm_num : (0:ℝ) < 2)]
  have expand : (c / u + c / v) * ((u + v) / 2) - c * 2 =
      c * ((u - v) ^ 2 / (2 * u * v)) := by
    field_simp
    ring
  nlinarith [mul_nonneg hc (div_nonneg (sq_nonneg (u - v))
    (by positivity : (0:ℝ) ≤ 2 * u * v))]

end Ccod
