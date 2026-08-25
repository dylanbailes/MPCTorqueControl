"""Model Predictive Control for SEA torque tracking.

Linear prediction model (the two-mass system with the spring linearized):

    x = [theta_m, omega_m, theta_l, omega_l]'      u = iq_ref [A]
    y = tau_s = k_s (theta_m - theta_l)            (torque estimate)

    theta_m_dot = omega_m
    omega_m_dot = (Kt u - bm omega_m - k_s (theta_m - theta_l)) / Jm
    theta_l_dot = omega_l
    omega_l_dot = (k_s (theta_m - theta_l) - bl omega_l) / Jl

The controller is a *condensed* MPC: the full input sequence over the horizon
is the optimization variable, so the QP has only box constraints, solved with
the projected-gradient solver in `qp.py` (fixed iterations, warm start — the
same shape as the firmware port).

Cost:
    sum_k (y_k - yref_k)^2 * Q_y  +  sum_k u_k^2 * R_u  +  (u_0 - u_prev)^2 * S_rate

Constraints:
    |u_k| <= u_max,   |u_0 - u_prev| <= du_max

Optional learned feedforward (the "learning augmentation"):
    u_total = u_mpc + u_ff(x, yref), clipped to u_max.
The residual model in `learn/residual.py` produces u_ff from the measured
state; this is the compensation that handles friction, cogging, and spring
nonlinearity that the linear prediction model does not contain.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import block_diag, expm

from model.qp import ProjectedGradientQP


@dataclass
class MPCConfig:
    T: float = 0.5e-3        # torque-loop period [s] (2 kHz)
    N: int = 20              # prediction horizon (steps)
    Q_y: float = 3e4         # torque tracking weight   [1 / (N.m)^2]
    R_u: float = 5e-3        # control effort weight    [1 / A^2]
    S_rate: float = 0.3      # slew-rate penalty        [1 / (A/step)^2]
    u_max: float = 6.0       # current limit            [A]
    du_max: float = 1.5      # max |u0 - u_prev|        [A/step]
    solver: str = "admm"     # "admm" (embedded workhorse) or "pg"
    max_iter: int = 20       # QP iterations per solve


class LinearSeaModel:
    """Continuous + discretized linear two-mass SEA model (ZOH)."""

    def __init__(self, Jm: float, bm: float, Jl: float, bl: float,
                 ks: float, Kt: float, T: float, k_block: float = 0.0):
        """Linear two-mass SEA model (ZOH discretized).

        k_block > 0 models a *blocked-output* fixture: a stiff spring from
        the load to ground, so theta_l ~= 0 (the classic torque-control test
        rig).  The free-load impedance experiments use k_block = 0.
        """
        self.T = T
        self.k_block = k_block
        A = np.array([
            [0.0, 1.0, 0.0, 0.0],
            [-ks / Jm, -bm / Jm, ks / Jm, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [ks / Jl, 0.0, -(ks + k_block) / Jl, -bl / Jl],
        ])
        B = np.array([[0.0], [Kt / Jm], [0.0], [0.0]])
        C = np.array([[ks, 0.0, -ks, 0.0]])
        D = np.zeros((1, 1))
        # exact ZOH discretization via matrix exponential
        n = A.shape[0]
        M = expm(np.block([[A * T, B * T], [np.zeros((1, n)), 0.0]]))
        self.Ad = M[:n, :n]
        self.Bd = M[:n, n:]
        self.Cd = C
        self.Dd = D
        self.nx, self.nu, self.ny = n, 1, 1

    def condense(self, N: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Build (F, G, Cx) such that Y = Cx F x0 + Cx G U over the horizon."""
        A, B, C = self.Ad, self.Bd, self.Cd
        F = np.vstack([np.linalg.matrix_power(A, i + 1) for i in range(N)])
        G = np.zeros((self.nx * N, self.nu * N))
        for i in range(N):
            for j in range(i + 1):
                G[i * self.nx:(i + 1) * self.nx, j * self.nu:(j + 1) * self.nu] = (
                    np.linalg.matrix_power(A, i - j) @ B)
        Cx = block_diag(*([C] * N))
        return F, G, Cx


class SeaMPC:
    """Receding-horizon torque MPC with optional learned feedforward."""

    def __init__(self, model: LinearSeaModel, cfg: MPCConfig):
        self.model = model
        self.cfg = cfg
        F, G, Cx = model.condense(cfg.N)
        self.F, self.G, self.Cx = F, G, Cx

        Q = np.eye(model.ny) * cfg.Q_y
        R = np.eye(model.nu) * cfg.R_u
        self.Qt = block_diag(*([Q] * cfg.N))
        Rt = block_diag(*([R] * cfg.N))
        self.Qt_c = Cx.T @ self.Qt @ Cx     # state-space weight (for H)
        self.H = 2.0 * (G.T @ self.Qt_c @ G + Rt)
        # full-horizon slew-rate penalty: S_rate * sum_k (u_k - u_{k-1})^2,
        # with u_{-1} = u_prev.  E is the lower-bidiagonal difference matrix:
        #   E U = [u0-u_prev, u1-u0, ..., u_{N-1}-u_{N-2}]
        E = np.zeros((cfg.N, cfg.N))
        for i in range(cfg.N):
            E[i, i] = 1.0
            if i > 0:
                E[i, i - 1] = -1.0
        self.E = E
        self.H += 2.0 * cfg.S_rate * (E.T @ E)
        self._rate_e0 = -2.0 * cfg.S_rate * E.T[:, 0]  # contribution of u_prev to g
        if cfg.solver == "admm":
            from model.qp import AdmmQP
            self.solver = AdmmQP(self.H, max_iter=cfg.max_iter)
        else:
            self.solver = ProjectedGradientQP(self.H, max_iter=cfg.max_iter)
        self.ff = None          # learned feedforward: u_ff(x, yref) -> A
        self.u_prev = 0.0
        self.last_solve_ms = 0.0

    def set_feedforward(self, ff) -> None:
        self.ff = ff

    def reset(self) -> None:
        self.u_prev = 0.0
        self.solver.warm = np.zeros(self.cfg.N)

    def _g(self, x0: np.ndarray, yref: np.ndarray) -> np.ndarray:
        Y0 = self.Cx @ self.F @ x0 - np.ones(self.cfg.N) * yref
        g = 2.0 * (self.Cx @ self.G).T @ self.Qt @ Y0
        g += self._rate_e0 * self.u_prev
        return g

    def _bounds(self) -> tuple[np.ndarray, np.ndarray]:
        N = self.cfg.N
        lo = np.full(N, -self.cfg.u_max)
        hi = np.full(N, self.cfg.u_max)
        lo[0] = max(-self.cfg.u_max, self.u_prev - self.cfg.du_max)
        hi[0] = min(self.cfg.u_max, self.u_prev + self.cfg.du_max)
        return lo, hi

    def step(self, x0: np.ndarray, yref: float, t0=None) -> float:
        """One torque-loop update; returns the applied current command [A]."""
        import time as _time
        g = self._g(x0, yref)
        lo, hi = self._bounds()
        t_start = _time.perf_counter()
        U = self.solver.solve(g, lo, hi)
        self.last_solve_ms = (_time.perf_counter() - t_start) * 1e3
        u_mpc = float(U[0])
        u_ff = 0.0
        if self.ff is not None:
            u_ff = float(self.ff(x0, yref))
        u = float(np.clip(u_mpc + u_ff, -self.cfg.u_max, self.cfg.u_max))
        self.u_prev = u
        return u

    def solve_sequence(self, x0: np.ndarray, yref: float) -> np.ndarray:
        """Expose the full planned input sequence (diagnostics/plots)."""
        g = self._g(x0, yref)
        lo, hi = self._bounds()
        return self.solver.solve(g, lo, hi)

    # ------------------------------------------------------------------
    # Firmware export: the condensed MPC is a *constant* affine map in
    # (x0, yref, u_prev), plus the ADMM Cholesky factor.  These are the
    # only numbers the STM32 needs at runtime.
    # ------------------------------------------------------------------

    def export_to_c(self, path: str) -> str:
        N = self.cfg.N
        # gradient affine map: g = M_x @ x0 + m_y * yref + m_prev * u_prev
        CG = self.Cx @ self.G
        M_x = 2.0 * CG.T @ self.Qt @ (self.Cx @ self.F)       # (N, 4)
        m_y = -2.0 * CG.T @ self.Qt @ np.ones(N)               # (N,)
        m_prev = self._rate_e0                                 # (N,)
        # ADMM: Cholesky of (H + rho*I)
        from scipy.linalg import cholesky
        rho = self.solver.rho
        L = cholesky(self.H + rho * np.eye(N), lower=True)

        def fmt(a) -> str:
            return np.array2string(np.asarray(a, dtype=np.float32), precision=8,
                                   separator=",", threshold=10000,
                                   suppress_small=True).replace("[", "{").replace("]", "}")

        lines = [
            "/* Auto-generated by model/mpc.py::export_to_c — do not edit. */",
            "#ifndef MPC_MODEL_H",
            "#define MPC_MODEL_H",
            "",
            f"#define MPC_N {N}",
            f"#define MPC_NX 4",
            f"#define MPC_RHO {rho:.9g}f",
            f"#define MPC_U_MAX {self.cfg.u_max:.9g}f",
            f"#define MPC_DU_MAX {self.cfg.du_max:.9g}f",
            f"#define MPC_S_RATE {self.cfg.S_rate:.9g}f",
            "",
            "/* g(U) = M_x x0 + m_y yref + m_prev u_prev,  N x 1 each */",
            f"static const float MPC_MX[MPC_N * MPC_NX] = {fmt(M_x)};",
            f"static const float MPC_MY[MPC_N] = {fmt(m_y)};",
            f"static const float MPC_MPREV[MPC_N] = {fmt(m_prev)};",
            "",
            "/* Lower-triangular Cholesky L with L L' = H + rho I */",
            f"static const float MPC_L[MPC_N * MPC_N] = {fmt(L)};",
            "",
            "#endif /* MPC_MODEL_H */",
        ]
        text = "\n".join(lines) + "\n"
        with open(path, "w") as f:
            f.write(text)
        return "mpc_model.h"
