"""Scenario simulation engine and burden score (Eq. 3).

The state process is simulated on the logit scale,

    x_{t+1} = c + rho * x_t + phi * F(sigma(x_t)) + u_{t+1},

with optional stress feedback phi (the information-trap channel).  Outcome
paths use the estimated local-projection responses.  The burden score is

    D = sum_h (1+kappa)^{-h} M_{t+h} * sum_k omega_k * Ytilde^k_{t+h}.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def logit(m):
    return np.log(m / (1.0 - m))


@dataclass
class ScenarioParams:
    """Parameters of the disinformation process under one scenario."""
    name: str = "baseline"
    rho: float = 0.85          # persistence (estimated)
    c: float = 0.0             # inflow / drift on logit scale
    sigma_u: float = 0.35      # innovation s.d. (estimated)
    phi: float = 0.0           # stress -> disinformation feedback
    shock_prob: float = 0.0    # probability of a discrete event shock
    shock_size: float = 0.0    # size of event shock (logit units)
    x0: float = 0.0            # initial condition, logit scale
    seed: int = 20260705


@dataclass
class OutcomeMap:
    """Linear(ized) outcome responses to M (per channel, per horizon).

    beta[k] is the vector of h-step responses of channel k to a one s.d.
    increase in M (from the local projections), already SIGNED so that
    larger = worse (growth and innovation responses enter with flipped
    sign; see Eq. 3 discussion).
    """
    horizons: np.ndarray
    beta: dict = field(default_factory=dict)      # k -> array over horizons
    m_sd: float = 0.2                              # s.d. of M in the panel
    m_mean: float = 0.5


def simulate_paths(p: ScenarioParams, T: int = 12, n_sims: int = 10_000,
                   stress_fn=None) -> np.ndarray:
    """Simulate M paths (n_sims x T+1). stress_fn: M -> stress level in [0,1]."""
    rng = np.random.default_rng(p.seed)
    x = np.full(n_sims, p.x0, dtype=float)
    out = np.empty((n_sims, T + 1))
    out[:, 0] = sigmoid(x)
    for t in range(1, T + 1):
        u = rng.normal(0.0, p.sigma_u, n_sims)
        if p.shock_prob > 0:
            hit = rng.random(n_sims) < p.shock_prob
            u = u + hit * p.shock_size
        fb = 0.0
        if p.phi != 0.0 and stress_fn is not None:
            fb = p.phi * stress_fn(sigmoid(x))
        x = p.c + p.rho * x + fb + u
        out[:, t] = sigmoid(x)
    return out


def default_stress_fn(m, slope=6.0, mid=0.6):
    """Fragility response of financial stress to disinformation (logistic)."""
    return 1.0 / (1.0 + np.exp(-slope * (m - mid)))


def outcome_paths(m_paths: np.ndarray, omap: OutcomeMap) -> dict:
    """Map simulated M paths into signed outcome deviation paths per channel.

    The h-step response is beta_k[h] * (M_t - m_mean)/m_sd applied to the
    disinformation level prevailing h periods earlier, cumulated as in a
    linear moving-average representation of the local projections.
    """
    n, Tp1 = m_paths.shape
    dev = (m_paths - omap.m_mean) / omap.m_sd
    paths = {}
    H = len(omap.horizons)
    for k, b in omap.beta.items():
        y = np.zeros((n, Tp1))
        for t in range(Tp1):
            for h in range(min(H, Tp1 - t)):
                y[:, t + h] += b[h] * dev[:, t] / max(1, 1)
        # average of overlapping responses to keep scale of a one-period LP
        paths[k] = y / np.sqrt(H)
    return paths


def burden_score(m_paths: np.ndarray, ypaths: dict, omega: dict,
                 kappa: float = 0.04, H: int | None = None) -> np.ndarray:
    """Eq. (3): discounted disinformation-weighted sum of signed outcomes."""
    n, Tp1 = m_paths.shape
    H = Tp1 - 1 if H is None else min(H, Tp1 - 1)
    D = np.zeros(n)
    for h in range(H + 1):
        disc = (1.0 + kappa) ** (-h)
        ysum = sum(omega[k] * ypaths[k][:, h] for k in omega)
        D += disc * m_paths[:, h] * ysum
    return D


def deterministic_map(x, p: ScenarioParams, stress_fn=None):
    """Deterministic skeleton psi(x) = c + rho x + phi F(sigma(x))."""
    fb = p.phi * stress_fn(sigmoid(x)) if (p.phi and stress_fn) else 0.0
    return p.c + p.rho * x + fb


def fixed_points(p: ScenarioParams, stress_fn=None, grid=(-8, 8, 200001)):
    """All fixed points of the deterministic skeleton by sign changes."""
    xs = np.linspace(*grid)
    g = deterministic_map(xs, p, stress_fn) - xs
    sign = np.sign(g)
    idx = np.where(np.diff(sign) != 0)[0]
    roots = []
    for i in idx:
        a, b = xs[i], xs[i + 1]
        for _ in range(80):  # bisection
            mid = 0.5 * (a + b)
            if (deterministic_map(a, p, stress_fn) - a) * \
               (deterministic_map(mid, p, stress_fn) - mid) <= 0:
                b = mid
            else:
                a = mid
        roots.append(0.5 * (a + b))
    return np.array(roots)


# --------------------------------------------------------------------------
# scenario definitions used in the paper
# --------------------------------------------------------------------------

def make_scenarios(rho, c, sigma_u, delta_effect=0.0) -> dict[str, ScenarioParams]:
    """Baseline / high-disinformation / resilient-information scenarios.

    Policy levers map onto parameters exactly as in the proposal:
    rapid-response communication lowers rho; platform friction and
    data-sharing lower the inflow c (and spillover, absorbed in c here);
    verified messaging lowers shock size/probability.
    """
    base = ScenarioParams(name="baseline", rho=rho, c=c, sigma_u=sigma_u,
                          x0=c / (1 - rho))
    high = replace(base, name="high-disinformation",
                   c=c + 0.15, shock_prob=0.10, shock_size=0.8,
                   sigma_u=sigma_u * 1.25)
    resilient = replace(base, name="resilient-information",
                        rho=max(0.0, rho - 0.20), c=c - 0.15,
                        sigma_u=sigma_u * 0.8)
    return {"baseline": base, "high": high, "resilient": resilient}


# --------------------------------------------------------------------------
# analytics for Proposition 4 (half-life rule) figures
# --------------------------------------------------------------------------

def stationary_mean_logit(c, rho):
    return c / (1.0 - rho)


def elasticity_rho(c, rho):
    """d mu / d rho * rho / mu = rho / (1 - rho)."""
    return rho / (1.0 - rho)


def elasticity_c(c, rho):
    """d mu / d c * c / mu = 1."""
    return 1.0
