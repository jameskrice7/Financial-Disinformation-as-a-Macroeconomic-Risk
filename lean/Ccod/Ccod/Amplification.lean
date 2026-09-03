import Mathlib.Order.MinMax
import Mathlib.Tactic

/-!
Proposition 2: state-dependent amplification.

In the micro block, realized macro-financial harm is
H(m, f) = max(a·m + b·f − k, 0): losses occur only when the
collateral/rollover constraint binds (the kinked region), and the
constraint tightens in both the disinformation index m and fragility f.

We verify that H has *increasing differences* (supermodularity) in
(m, f): the marginal damage of disinformation is nondecreasing in
fragility, and is zero in calm states.  This is the formal content of
"disinformation is a risk amplifier, not a mean shifter."
-/

namespace Ccod

/-- Core inequality: for a convex kink `g(x) = max(x,0)` and nonnegative
increments `p, q`, `g(s+p) + g(s+q) ≤ g(s+p+q) + g(s)`. -/
theorem max_zero_superadditive_increments (s p q : ℝ)
    (hp : 0 ≤ p) (hq : 0 ≤ q) :
    max (s + p) 0 + max (s + q) 0 ≤ max (s + p + q) 0 + max s 0 := by
  rcases le_or_gt s 0 with hs | hs
  · rcases le_or_gt (s + p + q) 0 with hspq | hspq
    · -- everything at or below the kink: all terms vanish
      have h1 : s + p ≤ 0 := by linarith
      have h2 : s + q ≤ 0 := by linarith
      rw [max_eq_right h1, max_eq_right h2, max_eq_right hspq,
        max_eq_right hs]
    · -- s below, s+p+q above the kink
      have hbig : max (s + p + q) 0 = s + p + q := max_eq_left hspq.le
      have hs0 : max s 0 = 0 := max_eq_right hs
      rcases le_or_gt (s + p) 0 with h1 | h1
      · rcases le_or_gt (s + q) 0 with h2 | h2
        · rw [max_eq_right h1, max_eq_right h2, hbig, hs0]; linarith
        · rw [max_eq_right h1, max_eq_left h2.le, hbig, hs0]; linarith
      · rcases le_or_gt (s + q) 0 with h2 | h2
        · rw [max_eq_left h1.le, max_eq_right h2, hbig, hs0]; linarith
        · rw [max_eq_left h1.le, max_eq_left h2.le, hbig, hs0]; linarith
  · -- s above the kink: all four terms interior, equality
    have h1 : max (s + p) 0 = s + p := max_eq_left (by linarith)
    have h2 : max (s + q) 0 = s + q := max_eq_left (by linarith)
    have h3 : max (s + p + q) 0 = s + p + q := max_eq_left (by linarith)
    have h4 : max s 0 = s := max_eq_left hs.le
    rw [h1, h2, h3, h4]; linarith

/-- Harm function of the micro block: `H(m,f) = max(a m + b f − k, 0)`. -/
def harm (a b k m f : ℝ) : ℝ := max (a * m + b * f - k) 0

/-- Prop. 2: increasing differences.  For `a, b ≥ 0` and any
`m₁ ≤ m₂`, `f₁ ≤ f₂`, the damage increment from more disinformation is
larger in the more fragile state:
`H(m₂,f₁) − H(m₁,f₁) ≤ H(m₂,f₂) − H(m₁,f₂)`. -/
theorem harm_increasing_differences (a b k : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b)
    {m₁ m₂ f₁ f₂ : ℝ} (hm : m₁ ≤ m₂) (hf : f₁ ≤ f₂) :
    harm a b k m₂ f₁ - harm a b k m₁ f₁ ≤
      harm a b k m₂ f₂ - harm a b k m₁ f₂ := by
  set s := a * m₁ + b * f₁ - k with hs
  set p := a * (m₂ - m₁) with hpdef
  set q := b * (f₂ - f₁) with hqdef
  have hp : 0 ≤ p := mul_nonneg ha (by linarith)
  have hq : 0 ≤ q := mul_nonneg hb (by linarith)
  have e1 : a * m₂ + b * f₁ - k = s + p := by rw [hs, hpdef]; ring
  have e2 : a * m₁ + b * f₂ - k = s + q := by rw [hs, hqdef]; ring
  have e3 : a * m₂ + b * f₂ - k = s + p + q := by rw [hs, hpdef, hqdef]; ring
  unfold harm
  rw [e1, e2, e3]
  have := max_zero_superadditive_increments s p q hp hq
  linarith

/-- Calm-state neutrality: if the constraint is slack even at the higher
disinformation level (`a m₂ + b f − k ≤ 0`), disinformation causes no
damage at all — the mean effect in tranquil states is exactly zero. -/
theorem harm_zero_in_calm_states (a b k m₁ m₂ f : ℝ)
    (ha : 0 ≤ a) (hm : m₁ ≤ m₂) (hcalm : a * m₂ + b * f - k ≤ 0) :
    harm a b k m₂ f - harm a b k m₁ f = 0 := by
  have h1 : a * m₁ + b * f - k ≤ 0 := by nlinarith
  unfold harm
  rw [max_eq_right hcalm, max_eq_right h1]
  ring

end Ccod
