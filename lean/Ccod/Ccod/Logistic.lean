import Mathlib.Analysis.SpecialFunctions.Exp

/-!
Logistic (sigmoid) function: basic properties used by Proposition 1.

The disinformation index is M = logistic(x) where x follows a linear
state equation on the logit scale.  These lemmas verify that the index
remains in the open unit interval at every horizon (no ad hoc clipping),
that the transformation is strictly monotone (so orderings on the latent
scale are preserved), and the symmetry used in the paper's discussion of
index normalization.
-/

noncomputable section

namespace Ccod

/-- The logistic function `σ(x) = 1 / (1 + e^{-x})`. -/
def logistic (x : ℝ) : ℝ := 1 / (1 + Real.exp (-x))

/-- Paper, Prop. 1(i): the simulated index is strictly positive. -/
theorem logistic_pos (x : ℝ) : 0 < logistic x := by
  unfold logistic
  have h : 0 < 1 + Real.exp (-x) := by positivity
  positivity

/-- Paper, Prop. 1(i): the simulated index is strictly below one. -/
theorem logistic_lt_one (x : ℝ) : logistic x < 1 := by
  unfold logistic
  have h : 0 < 1 + Real.exp (-x) := by positivity
  rw [div_lt_one h]
  linarith [Real.exp_pos (-x)]

/-- The index stays in the open unit interval: `M ∈ (0,1)` always. -/
theorem logistic_mem_Ioo (x : ℝ) : logistic x ∈ Set.Ioo (0 : ℝ) 1 :=
  ⟨logistic_pos x, logistic_lt_one x⟩

/-- Strict monotonicity: a worse latent information state means a
strictly higher index. -/
theorem logistic_strictMono : StrictMono logistic := by
  intro x y hxy
  unfold logistic
  have hx : 0 < 1 + Real.exp (-x) := by positivity
  have hy : 0 < 1 + Real.exp (-y) := by positivity
  apply div_lt_div_of_pos_left one_pos hy
  have : Real.exp (-y) < Real.exp (-x) := Real.exp_lt_exp.mpr (by linarith)
  linarith

/-- Symmetry `σ(-x) = 1 - σ(x)`, used for the index normalization. -/
theorem logistic_neg (x : ℝ) : logistic (-x) = 1 - logistic x := by
  unfold logistic
  rw [neg_neg]
  have h1 : (1 : ℝ) + Real.exp (-x) ≠ 0 := by positivity
  have h2 : (1 : ℝ) + Real.exp x ≠ 0 := by positivity
  have hx : Real.exp (-x) * Real.exp x = 1 := by
    rw [← Real.exp_add]; simp
  field_simp
  nlinarith [hx]

end Ccod
