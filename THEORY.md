# Theory design note (internal)

Paper: "Financial Disinformation as a Macroeconomic Risk: Information Pollution,
Fragile States, and the Half-Life Rule"

## Primitives

- Information state M_t ∈ (0,1): share of marginal financial information flow that is
  distorted. x_t = logit(M_t).
- State equation (Eq. 1 of proposal): x_{t+1} = c + ρ x_t + δ s_t + u_{t+1}.
- Micro block: contamination signal model. Lenders observe s = V + b·d·η + ε,
  b ~ Bern(M), η = ±1. Conditional variance of fundamentals rises linearly in M:
  Var = σ_ε² + M d² ("information pollution"). Certainty-equivalent collateral
  valuation ⇒ credit limit L(M,F) = κ·max(0, W − γ(σ_ε² + M d²) − F).
  Constraint binds only in fragile states ⇒ effects of M on growth are
  STATE-DEPENDENT and concentrated in the lower tail (growth-at-risk).

## Propositions (each verified in Lean 4 / mathlib; lean/Ccod/)

P1 (Ergodicity & bounds). |ρ|<1 ⇒ unique stationary distribution;
   explicit solution x_t = ρ^t x_0 + Σ ρ^j (c+u); stationary mean μ = c/(1−ρ),
   variance σ²/(1−ρ²); M_t ∈ (0,1) always (logistic bounds).
   Lean: geometric series, logistic ∈ (0,1), contraction fixed point.
   File: StateDynamics.lean, Logistic.lean

P2 (State-dependent amplification). Harm H(M,F) = max(0, aM + bF − k), a,b ≥ 0,
   has increasing differences (supermodular): the marginal damage of
   disinformation is nondecreasing in fragility; zero in calm states.
   ⇒ mean effects small, tail effects large. Lean: Amplification.lean

P3 (Information trap / tipping). With feedback φ from stress to future
   disinformation, update map ψ(x) = c + ρx + φF(σ(x)).
   (i) If ρ + φ·Lip(F∘σ) < 1: unique globally attracting steady state
   (Banach). (ii) There exist parameters (explicit piecewise-linear sigmoid)
   with three steady states — an information trap; small parameter changes
   cause discontinuous jumps (hysteresis). Lean: Tipping.lean

P4 (Burden score & the Half-Life Rule).
   (i) 0 ≤ D_{t,H} ≤ Ȳ·(1+κ)/κ for |Ỹ|≤Ȳ (geometric bound), finite as H→∞.
   (ii) μ = c/(1−ρ): elasticity of stationary disinformation w.r.t.
   persistence is ρ/(1−ρ), w.r.t. inflow is 1. Persistence-targeting policy
   (rapid correction) dominates inflow-targeting (friction) iff ρ > 1/2 —
   i.e. iff the half-life of a false narrative exceeds one period.
   (iii) μ is convex in ρ: increasing returns to de-amplification near
   the trap boundary. Lean: Burden.lean

## Mapping to empirics

- Eq (1) panel FE estimate of ρ, δ on DSP-based M index (2000–2025, ~170 countries).
- Eq (2) local projections h=0..4, five channels G,N,I,T,F; interactions with
  fragility W = (F,T,I) ⇒ test P2 (supermodularity: φ̂ signs).
- Growth-at-risk quantile LPs: effect of M on 10th percentile vs median of growth ⇒ P2.
- Scenarios: baseline / high-disinfo / resilient → burden scores D (Eq. 3), sweeps over ω, κ.
- Tipping calibration: feedback φ from LP of stress on M and state-eq loading of stress.
- Monte Carlo: two-step estimator recovers known DGP parameters.

## Headline original results

1. The Half-Life Rule (ρ > 1/2 ⇒ corrections dominate friction).
2. Disinformation is a growth-at-risk amplifier, not a mean shifter
   (tail-concentrated damage; supermodularity with fragility).
3. Information trap: persistence + stress feedback ⇒ multiple steady states;
   escalation threshold for policy.
4. Burden score D as a bounded, internally consistent macro-information risk metric.
