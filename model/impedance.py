"""Impedance control and experimental collision-response layer.

Two pieces:

1. **Impedance control** — the outer loop.  The torque reference to the inner
   torque controller behaves like a virtual spring-damper anchored at the
   desired position theta_d:

       tau_ref = k_imp (theta_d - theta_l) + b_imp (0 - omega_l)

   With a *torque-controlled* SEA this aims for compliant, backdrivable
   behavior: push the output and it yields with programmable stiffness.

2. **Collision detection** — a momentum (residual) observer on the motor
   side, plus a stall detector on the load side:

       rho_dot = k_obs (tau_m - tau_s - tau_fric_hat(omega_m) - rho)
       tau_coll_hat = rho

   The friction estimate `tau_fric_hat` comes from the learned friction model
   (see learn/), which both improves torque tracking *and* sharpens collision
   detection.  On detection the safety layer commands a safe stop (torque ->
   0), so the actuator "gives way".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ImpedanceConfig:
    k_imp: float = 0.8         # virtual stiffness   [N.m/rad]
    b_imp: float = 0.15        # virtual damping     [N.m.s/rad]
    k_obs: float = 100.0       # momentum observer gain [1/s]
    coll_tau_thresh: float = 0.40   # collision torque threshold [N.m]
    coll_debounce: float = 0.05     # detection debounce [s]
    stall_w_thresh: float = 0.05    # load velocity "stalled" [rad/s]
    stall_tau_thresh: float = 0.15  # stall torque threshold [N.m]
    stall_debounce: float = 0.08    # stall debounce [s]


@dataclass
class CollisionState:
    detected: bool = False
    time: float = 0.0
    tau_coll_hat: float = 0.0
    source: str = ""
    history: list = field(default_factory=list)


class ImpedanceSafety:
    """Outer impedance loop + collision detection + safe-stop logic."""

    def __init__(self, cfg: ImpedanceConfig | None = None):
        self.cfg = cfg if cfg is not None else ImpedanceConfig()
        self.friction_model = None  # configuration survives state resets
        self.reset()

    def reset(self) -> None:
        self.rho = 0.0
        self.t_coll_accum = 0.0
        self.t_stall_accum = 0.0
        self.coll = CollisionState()

    def set_friction_model(self, f) -> None:
        """Attach a learned friction model tau_fric_hat(omega) for the observer."""
        self.friction_model = f

    def torque_reference(self, theta_d: float, theta_l: float, omega_l: float) -> float:
        """Virtual spring-damper torque reference."""
        c = self.cfg
        return c.k_imp * (theta_d - theta_l) - c.b_imp * omega_l

    def update_observer(self, tau_m: float, tau_s: float, omega_m: float,
                        dt: float) -> float:
        """Momentum observer update; returns collision torque estimate [N.m]."""
        c = self.cfg
        fric = self.friction_model(omega_m) if self.friction_model else 0.0
        self.rho += c.k_obs * dt * (tau_m - tau_s - fric - self.rho)
        self.coll.tau_coll_hat = self.rho
        return self.rho

    def check(self, tau_s: float, omega_l: float, tau_ref: float, dt: float) -> None:
        """Run detection logic; sets coll.detected and coll.source."""
        c = self.cfg
        if self.coll.detected:
            return
        # 1) momentum-observer residual
        if abs(self.coll.tau_coll_hat) > c.coll_tau_thresh:
            self.t_coll_accum += dt
        else:
            self.t_coll_accum = 0.0
        # 2) load-side stall: torque building while the output is pinned
        stalled = abs(omega_l) < c.stall_w_thresh and abs(tau_s) > c.stall_tau_thresh
        if stalled:
            self.t_stall_accum += dt
        else:
            self.t_stall_accum = 0.0

        if self.t_coll_accum >= c.coll_debounce:
            self._trigger("momentum_observer", dt)
        elif self.t_stall_accum >= c.stall_debounce:
            self._trigger("stall", dt)

    def _trigger(self, source: str, dt: float) -> None:
        self.coll.detected = True
        self.coll.source = source
        self.coll.time += dt
        self.coll.history.append((source, self.coll.time, self.coll.tau_coll_hat))

    def safe_command(self, u_cmd: float) -> float:
        """On detection, immediately set the current command to zero."""
        if self.coll.detected:
            return 0.0
        return u_cmd
