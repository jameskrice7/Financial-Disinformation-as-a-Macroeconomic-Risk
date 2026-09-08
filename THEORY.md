# Theory and formalization scope

The revised paper distinguishes the observed broad index M from the unobserved
financial contamination probability p. A monotone link between them is an
additional hypothesis, not a measured identity.

## Economic assumptions

For s = V + b η d + ε with mutually independent disturbances conditional on p,
Var(s | V,p) = σ²ε + p d². This is **signal-noise variance**, not Var(V | s,p).
The linear noise-sensitive lending rule is explicitly assumed; it is no longer
presented as a derived posterior certainty equivalent. Its max-linear investment
shortfall has increasing differences in p and financial pressure. Mean and
quantile growth patterns require additional distributional/aggregation assumptions.

Scalar AR(1) formulas condition on absent or fixed external inputs. If countries
jointly evolve with a nonnegative row-stochastic matrix W and nonnegative ρ,δ,
the homogeneous system's spectral radius is ρ+δ. The scalar half-life of the
latent rank index does not measure a narrative's lifetime or necessarily the
nonlinear index's half-life. E[sigmoid(x)] is not generally sigmoid(E[x]).

A contraction inequality is sufficient for uniqueness; failing it is not a fold
bifurcation. The explicit three-root example establishes possibility only. No
empirical feedback strength or policy escalation threshold is identified.

For c>0 and 0<ρ<1, the elasticity ratio ρ/(1−ρ) compares equal marginal
proportional parameter changes. For equal-cost policies with effectiveness
ηρ and ηc, the comparison is ηρ·ρ/(1−ρ)>ηc. For c=0 the proportional
elasticity of the zero steady state is undefined; with c<0, reducing ρ raises
the index toward one half. Neither intervention effectiveness nor cost is
estimated. The mathematical burden bound permits negative signed scores and
does not give welfare meaning or justify near-zero normalizations.

## What the existing Lean declarations cover

| File | Formal scope |
|---|---|
| `Logistic.lean` | Bounds, monotonicity and symmetry of the logistic function |
| `StateDynamics.lean` | Deterministic scalar orbit, steady-state value/uniqueness/convergence and a geometric variance identity |
| `Amplification.lean` | Increasing differences and the slack-constraint zero result for max-linear harm |
| `Tipping.lean` | Uniqueness given a contraction bound, a Lipschitz bound, and an explicit three-root example |
| `Burden.lean` | Absolute geometric burden bound, scalar derivative, elasticity identity (c≠0), ρ/(1−ρ)>1 iff ρ>1/2, midpoint convexity for c≥0 |

These declarations do not verify the signal lemma, lending behavior, posterior
inference, full stochastic ergodicity, endogenous-network stability, a smooth
fold's conditions, causal identification, quantile inference, forecast accuracy,
or policy cost-effectiveness. The revised manuscript supplies analytical
arguments or explicitly marks assumptions where the formalization is narrower.
The mathematical declarations are unchanged in this revision; comments have
been narrowed where they previously claimed policy conclusions.
