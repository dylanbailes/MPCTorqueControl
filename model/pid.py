"""Baseline torque controller: cascaded PID -> current command.

This is the *fair* baseline for the project: a well-tuned PID (with
derivative action on the torque estimate to damp the two-mass resonance and
anti-windup), operating at the same 2 kHz rate as the MPC.  The comparison
story is PID vs MPC vs MPC + learned feedforward.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PIDConfig:
    kp: float = 15.0       # proportional          [A / (N.m)]
    ki: float = 60.0       # integral              [A / (N.m.s)]
    kd: float = 0.30       # derivative            [A . s / (N.m)]
    Tf: float = 1.0 / (2 * 3.14159 * 80.0)   # derivative filter time const [s]
    u_max: float = 6.0     # output saturation     [A]
    du_max: float = 1.5    # slew limit            [A / step]


class PidTorqueController:
    """PID torque controller with derivative filter and conditional anti-windup."""

    def __init__(self, cfg: PIDConfig | None = None):
        self.cfg = cfg if cfg is not None else PIDConfig()
        self.reset()

    def reset(self) -> None:
        self.err_int = 0.0
        self.err_d_prev = 0.0
        self.u_prev = 0.0

    def step(self, tau_ref: float, tau_est: float, dt: float) -> float:
        c = self.cfg
        err = tau_ref - tau_est
        self.err_int += c.ki * err * dt
        # derivative with low-pass filter (backward difference)
        err_d = (err - self.err_d_prev) / dt
        self.err_d_prev = err
        a = dt / (c.Tf + dt)
        # filtered derivative state
        self.der_filt = getattr(self, "der_filt", 0.0) + a * (err_d - getattr(self, "der_filt", 0.0))
        u_raw = c.kp * err + self.err_int + c.kd * self.der_filt
        u = max(-c.u_max, min(c.u_max, u_raw))
        # slew limiting
        du = c.du_max
        u = max(u, self.u_prev - du)
        u = min(u, self.u_prev + du)
        # conditional integration (freeze on saturation)
        if u_raw != u:
            self.err_int -= c.ki * err * dt
        self.u_prev = u
        return u
