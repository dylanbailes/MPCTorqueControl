"""Embedded-style QP solvers: projected gradient and ADMM.

Both solve

    min_U   0.5 U' H U + g' U          (H symmetric positive definite)
    s.t.    lo <= U <= hi

on the *condensed* MPC problem (the optimization variable is the full input
sequence, so only box constraints remain), warm-started from the previous
solve.  Each ports 1:1 to the STM32 firmware.

* `ProjectedGradientQP` — simple, robust, converges slowly on ill-conditioned
  problems (fine for tests and small N).
* `AdmmQP` — the workhorse.  The (H + rho*I) system is Cholesky-factorized
  once (constant for LTI plants), so each iteration is two triangular solves
  (O(N^2)) plus a box projection.  10-20 warm-started iterations are enough
  in practice — this is the same structure as OSQP/acados.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import cho_factor, cho_solve


def max_eig_power(H: np.ndarray, iters: int = 200) -> float:
    """Largest eigenvalue of a symmetric PD matrix via power iteration."""
    n = H.shape[0]
    v = np.random.default_rng(0).normal(size=n)
    v /= np.linalg.norm(v)
    for _ in range(iters):
        Hv = H @ v
        lam = float(v @ Hv)
        v = Hv / (np.linalg.norm(Hv) + 1e-30)
    return max(lam, 1e-12)


class ProjectedGradientQP:
    """Warm-started projected gradient (step = 1/L, no line search)."""

    def __init__(self, H: np.ndarray, max_iter: int = 100, tol: float = 1e-9):
        self.H = np.asarray(H, dtype=float)
        self.n = self.H.shape[0]
        self.L = max_eig_power(self.H)
        self.max_iter = max_iter
        self.tol = tol
        self.iterations = 0
        self.warm = np.zeros(self.n)

    def set_warm_start(self, u: np.ndarray) -> None:
        self.warm = np.asarray(u, dtype=float).reshape(-1)

    def solve(self, g: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
        g = np.asarray(g, dtype=float).reshape(-1)
        lo = np.asarray(lo, dtype=float).reshape(-1)
        hi = np.asarray(hi, dtype=float).reshape(-1)
        u = np.clip(self.warm, lo, hi)
        step = 1.0 / self.L
        for it in range(self.max_iter):
            self.iterations = it + 1
            grad = self.H @ u + g
            u_new = np.clip(u - step * grad, lo, hi)
            if it > 0 and np.max(np.abs(u_new - u)) < self.tol:
                u = u_new
                break
            u = u_new
        self.warm = u
        return u


class AdmmQP:
    """Warm-started ADMM for box-constrained QP (Cholesky-preconditioned)."""

    def __init__(self, H: np.ndarray, rho: float = 1.0, max_iter: int = 25,
                 tol: float = 1e-8):
        self.H = np.asarray(H, dtype=float)
        self.n = self.H.shape[0]
        self.rho = rho
        self.max_iter = max_iter
        self.tol = tol
        self.M = self.H + rho * np.eye(self.n)
        self._cf = cho_factor(self.M, lower=True)
        self.z = np.zeros(self.n)     # box-projected iterate (warm start)
        self.lam = np.zeros(self.n)   # dual variable (warm start)
        self.iterations = 0

    def set_warm_start(self, u: np.ndarray) -> None:
        self.z = np.asarray(u, dtype=float).reshape(-1)

    def solve(self, g: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
        g = np.asarray(g, dtype=float).reshape(-1)
        lo = np.asarray(lo, dtype=float).reshape(-1)
        hi = np.asarray(hi, dtype=float).reshape(-1)
        z = self.z
        lam = self.lam
        rho = self.rho
        for it in range(self.max_iter):
            self.iterations = it + 1
            rhs = -g + rho * (z - lam)
            u = cho_solve(self._cf, rhs)
            z_new = np.clip(u + lam, lo, hi)
            lam = lam + u - z_new
            # residual-based early exit
            if it > 0 and np.max(np.abs(z_new - z)) < self.tol:
                z = z_new
                break
            z = z_new
        self.z = z
        self.lam = lam
        return z


def qp_from_scipy(H: np.ndarray, g: np.ndarray, lo: np.ndarray, hi: np.ndarray,
                  u0: np.ndarray) -> np.ndarray:
    """Reference QP solution via scipy (tests only): min 0.5 u'Hu + g'u."""
    from scipy.optimize import minimize

    n = H.shape[0]
    res = minimize(
        lambda u: 0.5 * u @ H @ u + g @ u,
        u0,
        bounds=list(zip(lo, hi)),
        method="L-BFGS-B",
        options={"ftol": 1e-12, "maxiter": 5000},
    )
    return res.x
