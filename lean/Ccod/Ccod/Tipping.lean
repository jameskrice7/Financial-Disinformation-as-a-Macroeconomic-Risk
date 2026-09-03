import Mathlib.Tactic

/-!
Proposition 3: the information trap.

With feedback from financial stress to future disinformation the update
map becomes ψ(x) = c + ρx + φ·G(x) with G the stress response.
(i) If the total slope ρ + φ·L < 1 (L a Lipschitz bound for G), the
    steady state is unique — routine incidents mean-revert.
(ii) Beyond that threshold multiplicity is possible: we exhibit an
    explicit calibration with THREE steady states (clean, contested, and
    trapped information environments).  Small parameter changes then move
    the economy discontinuously between basins — the formal basis for the
    paper's escalation-threshold policy discussion.
-/

namespace Ccod

/-- Prop. 3(i): a contraction has at most one fixed point (uniqueness of
the steady state below the feedback threshold). -/
theorem contraction_unique_fixed_point (ψ : ℝ → ℝ) (K : ℝ) (hK : K < 1)
    (hL : ∀ x y, |ψ x - ψ y| ≤ K * |x - y|) {x y : ℝ}
    (hx : ψ x = x) (hy : ψ y = y) : x = y := by
  by_contra hne
  have h : |x - y| ≤ K * |x - y| := by
    calc |x - y| = |ψ x - ψ y| := by rw [hx, hy]
    _ ≤ K * |x - y| := hL x y
  have hpos : 0 < |x - y| := abs_pos.mpr (sub_ne_zero.mpr hne)
  nlinarith

/-- The feedback map ψ(x) = c + ρx + φ·G(x) inherits a Lipschitz bound
ρ + φ·L from the stress response G. -/
theorem feedback_map_lipschitz (c ρ φ L : ℝ) (hρ : 0 ≤ ρ) (hφ : 0 ≤ φ)
    (G : ℝ → ℝ) (hG : ∀ x y, |G x - G y| ≤ L * |x - y|) :
    ∀ x y, |(c + ρ * x + φ * G x) - (c + ρ * y + φ * G y)| ≤
      (ρ + φ * L) * |x - y| := by
  intro x y
  have h1 : (c + ρ * x + φ * G x) - (c + ρ * y + φ * G y)
      = ρ * (x - y) + φ * (G x - G y) := by ring
  rw [h1]
  calc |ρ * (x - y) + φ * (G x - G y)|
      ≤ |ρ * (x - y)| + |φ * (G x - G y)| := abs_add_le _ _
    _ = ρ * |x - y| + φ * |G x - G y| := by
        rw [abs_mul, abs_mul, abs_of_nonneg hρ, abs_of_nonneg hφ]
    _ ≤ ρ * |x - y| + φ * (L * |x - y|) := by
        have := hG x y
        nlinarith [abs_nonneg (x - y)]
    _ = (ρ + φ * L) * |x - y| := by ring

/-- Piecewise-linear stress response (unit ramp): the tractable sigmoid
used for the explicit multiplicity example. -/
def ramp (x : ℝ) : ℝ := min (max x 0) 1

/-- Explicit calibration beyond the feedback threshold:
ρ = 1/2, φ = 2, c = −3/4, so ψ(x) = −3/4 + x/2 + 2·ramp(x).
Interior slope is ρ + φ = 5/2 > 1. -/
noncomputable def ψtrap (x : ℝ) : ℝ := -(3/4) + x / 2 + 2 * ramp x

/-- Prop. 3(ii): the calibrated feedback map has three steady states:
x⁻ = −3/2 (clean), x⁰ = 1/2 (contested, unstable), x⁺ = 5/2 (trap). -/
theorem information_trap :
    ψtrap (-(3/2)) = -(3/2) ∧ ψtrap (1/2) = 1/2 ∧ ψtrap (5/2) = 5/2 := by
  refine ⟨?_, ?_, ?_⟩
  · have h1 : max (-(3/2) : ℝ) 0 = 0 := max_eq_right (by norm_num)
    have h2 : min (0 : ℝ) 1 = 0 := min_eq_left (by norm_num)
    unfold ψtrap ramp
    rw [h1, h2]; norm_num
  · have h1 : max (1/2 : ℝ) 0 = 1/2 := max_eq_left (by norm_num)
    have h2 : min (1/2 : ℝ) 1 = 1/2 := min_eq_left (by norm_num)
    unfold ψtrap ramp
    rw [h1, h2]; norm_num
  · have h1 : max (5/2 : ℝ) 0 = 5/2 := max_eq_left (by norm_num)
    have h2 : min (5/2 : ℝ) 1 = 1 := min_eq_right (by norm_num)
    unfold ψtrap ramp
    rw [h1, h2]; norm_num

/-- The three steady states are distinct: genuine multiplicity. -/
theorem information_trap_distinct :
    (-(3/2) : ℝ) ≠ 1/2 ∧ (1/2 : ℝ) ≠ 5/2 ∧ (-(3/2) : ℝ) ≠ 5/2 := by
  norm_num

end Ccod
