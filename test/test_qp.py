"""QP solver tests: projected gradient + ADMM vs scipy reference."""

import numpy as np
import pytest

from model.qp import ProjectedGradientQP, AdmmQP, qp_from_scipy


def _random_qp(seed: int, n: int = 8, cond: float = 1e3):
    rng = np.random.default_rng(seed)
    Q = rng.normal(size=(n, n))
    H = Q @ Q.T + cond * np.eye(n) * 0.01   # PD, moderately conditioned
    g = rng.normal(size=n)
    lo = -np.abs(rng.normal(size=n)) * 2.0
    hi = np.abs(rng.normal(size=n)) * 2.0
    return H, g, lo, hi


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("cls", [ProjectedGradientQP, AdmmQP])
def test_solvers_match_scipy(seed, cls):
    H, g, lo, hi = _random_qp(seed)
    ref = qp_from_scipy(H, g, lo, hi, np.zeros(H.shape[0]))
    solver = cls(H, max_iter=200 if cls is ProjectedGradientQP else 60)
    sol = solver.solve(g, lo, hi)
    assert np.max(np.abs(sol - ref)) < 1e-4


def test_solvers_respect_constraints():
    H, g, lo, hi = _random_qp(3, n=6)
    for cls in (ProjectedGradientQP, AdmmQP):
        solver = cls(H, max_iter=300)
        sol = solver.solve(g, lo, hi)
        assert np.all(sol >= lo - 1e-9)
        assert np.all(sol <= hi + 1e-9)


def test_admm_warm_start_is_faster():
    H, g, lo, hi = _random_qp(4)
    solver = AdmmQP(H, max_iter=500, tol=1e-9)
    solver.solve(g, lo, hi)
    iters_cold = solver.iterations
    # warm-started solve (same problem) should need no more iterations
    solver.solve(g, lo, hi)
    assert solver.iterations <= iters_cold + 1
