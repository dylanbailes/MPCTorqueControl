"""Series-Elastic Actuator (SEA) plant model — the digital twin.

A two-mass system coupled by a torsional spring:

    [BLDC motor] --(torque Kt*iq)--> J_m --[spring k_s]--> J_l --(output)--> load

States (SI units):
    theta_m  motor rotor angle        [rad]
    omega_m  motor rotor velocity     [rad/s]
    theta_l  output/load angle        [rad]
    omega_l  output/load velocity     [rad/s]
    iq       q-axis current           [A]

The q-axis current is driven by a PI current controller (the "FOC current
loop" in the digital twin) with back-EMF feedforward and voltage saturation
against the DC bus.  This mirrors the real firmware on the B-G431B-ESC1.

Unmodeled-dynamics sources that the learned residual must capture:
  * Stribeck friction on both inertias
  * motor cogging and current-proportional torque ripple
  * cubic spring nonlinearity (the *observer* uses the linear spring only)
  * encoder quantization (14-bit AS5048A) and measurement noise
  * current-loop lag / voltage saturation

Integration: explicit RK4 at dt = 10 us (100 kHz) — the electrical time
constant (L/R ~ 0.12 ms) is resolved ~10x per time constant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, sin, tanh

import numpy as np

# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------


@dataclass
class PlantParams:
    # --- motor electrical (100 W-class BLDC) -------------------------------
    R: float = 1.5           # winding resistance                [ohm]
    L: float = 3.0e-4        # winding inductance                [H]
    Kt: float = 0.1          # torque constant                   [N.m/A]
    Ke: float = 0.1          # back-EMF constant (=Kt in SI)     [V.s/rad]
    # --- motor mechanical ---------------------------------------------------
    Jm: float = 8.0e-5       # rotor inertia                     [kg.m^2]
    bm: float = 3.0e-5       # viscous damping                   [N.m.s/rad]
    tau_c_m: float = 8.0e-3  # Coulomb friction                  [N.m]
    tau_st_m: float = 12.0e-3  # Stribeck peak friction          [N.m]
    w_st_m: float = 0.6      # Stribeck velocity                 [rad/s]
    bv_m: float = 2.0e-4     # extra viscous friction            [N.m.s/rad]
    cog_A6: float = 3.0e-3   # 6th-order cogging amplitude       [N.m]
    cog_phi6: float = 0.3    # 6th-order cogging phase          [rad]
    cog_A12: float = 1.5e-3  # 12th-order cogging amplitude      [N.m]
    cog_phi12: float = 1.1   # 12th-order cogging phase         [rad]
    rip_frac: float = 0.01   # current-proportional ripple frac  [-]
    # --- series spring (linear; the *nonlinearity story* lives in the
    #     learned disturbance model instead of the spring) --------------------
    ks: float = 1.0          # linear stiffness                  [N.m/rad]
    knl: float = 0.0         # cubic stiffness (linear spring)   [N.m/rad^3]
    # --- load ---------------------------------------------------------------
    Jl: float = 1.2e-3       # load inertia                      [kg.m^2]
    bl: float = 1.0e-4       # viscous damping                   [N.m.s/rad]
    tau_c_l: float = 4.0e-3  # Coulomb friction                  [N.m]
    tau_st_l: float = 6.0e-3 # Stribeck peak friction            [N.m]
    w_st_l: float = 0.4      # Stribeck velocity                 [rad/s]
    bv_l: float = 8.0e-5     # extra viscous friction            [N.m.s/rad]
    # --- power stage --------------------------------------------------------
    Vbus: float = 24.0       # DC bus voltage                    [V]
    f_cur: float = 10e3      # current-loop rate                 [Hz]
    w_cur_bw: float = 2 * np.pi * 1500.0  # current-loop bandwidth [rad/s]
    # --- sensors ------------------------------------------------------------
    enc_bits: int = 14       # AS5048A resolution                [bits]
    enc_noise_lsb: float = 1.0  # measurement noise              [LSB std]


@dataclass
class PlantState:
    theta_m: float = 0.0
    omega_m: float = 0.0
    theta_l: float = 0.0
    omega_l: float = 0.0
    iq: float = 0.0
    vq: float = 0.0
    vq_sat: float = 0.0
    iq_pi_int: float = 0.0
    tau_s: float = 0.0
    tau_m: float = 0.0
    tau_ext: float = 0.0

    def as_array(self) -> np.ndarray:
        return np.array([self.theta_m, self.omega_m, self.theta_l, self.omega_l, self.iq])


class SeaPlant:
    """RK4 simulation of the SEA plant with an internal PI current loop."""

    def __init__(self, params: PlantParams | None = None, dt: float = 1e-5):
        self.p = params if params is not None else PlantParams()
        self.dt = dt
        # PI current controller (q-axis), tuned for the requested bandwidth.
        self.cur_kp = self.p.L * self.p.w_cur_bw
        self.cur_ki = self.p.R * self.p.w_cur_bw
        self.v_max = self.p.Vbus / np.sqrt(3.0)  # SVPWM linear range
        # calibrated spring curve used by the torque observer (set after ID)
        self.obs_ks = self.p.ks
        self.obs_knl = self.p.knl
        # blocked-output fixture (stiff spring-damper from load to ground),
        # part of the *continuous* dynamics — a ZOH version at 2 kHz would be
        # an unstable discrete loop at the ~460 Hz load mode
        self.k_block = 0.0
        self.d_block = 0.0
        # one-sided rigid wall for collision tests (continuous, same reason)
        self.theta_wall = None
        self.k_wall = 0.0
        self.d_wall = 0.0
        self.reset()

    def set_blocked_output(self, k_block: float, d_block: float) -> None:
        self.k_block = k_block
        self.d_block = d_block

    def set_wall(self, theta_stop: float, k: float, d: float) -> None:
        """One-sided rigid obstacle: theta_l cannot exceed theta_stop."""
        self.theta_wall = theta_stop
        self.k_wall = k
        self.d_wall = d

    def clear_wall(self) -> None:
        self.theta_wall = None
        self.k_wall = 0.0
        self.d_wall = 0.0

    # -- helpers ------------------------------------------------------------

    def _friction(self, w: float, tc: float, tst: float, wst: float,
                  bv: float, eps: float = 0.05) -> float:
        """Smooth Stribeck friction model: Coulomb + Stribeck + viscous."""
        s = np.tanh(w / eps)  # smooth sign
        stribeck = (tst - tc) * np.exp(-(w / wst) ** 2)
        return (tc + stribeck) * s + bv * w

    def _ripple(self, theta_m: float, iq: float) -> float:
        p = self.p
        cog = (p.cog_A6 * np.sin(6.0 * theta_m + p.cog_phi6)
               + p.cog_A12 * np.sin(12.0 * theta_m + p.cog_phi12))
        ripple = iq * p.rip_frac * np.sin(6.0 * theta_m)
        return cog + ripple

    def spring_torque(self, theta_m: float, theta_l: float) -> float:
        """True spring torque (linear + cubic)."""
        p = self.p
        d = theta_m - theta_l
        return p.ks * d + p.knl * d ** 3

    # -- dynamics -----------------------------------------------------------

    def _deriv(self, tm: float, wm: float, tl: float, wl: float, iq: float,
               vq: float, tau_ext: float, tau_dist_motor: float = 0.0) -> tuple:
        """Continuous dynamics given applied q-axis voltage and external torque.

        Float-only hot path (no numpy allocation) — this is called 100k
        times per simulated second.
        """
        p = self.p
        d = tm - tl
        tau_spring = p.ks * d + p.knl * d ** 3
        cog = (p.cog_A6 * sin(6.0 * tm + p.cog_phi6)
               + p.cog_A12 * sin(12.0 * tm + p.cog_phi12))
        tau_motor = p.Kt * iq + cog + iq * p.rip_frac * sin(6.0 * tm)
        sm = tanh(wm / 0.05)
        sl = tanh(wl / 0.05)
        f_m = (p.tau_c_m + (p.tau_st_m - p.tau_c_m) * exp(-(wm / p.w_st_m) ** 2)) * sm + p.bv_m * wm
        f_l = (p.tau_c_l + (p.tau_st_l - p.tau_c_l) * exp(-(wl / p.w_st_l) ** 2)) * sl + p.bv_l * wl
        diq = (vq - p.R * iq - p.Ke * wm) / p.L
        dwm = (tau_motor + tau_dist_motor - tau_spring - f_m - p.bm * wm) / p.Jm
        block = self.k_block * tl + self.d_block * wl   # blocked-output fixture
        if self.theta_wall is not None and tl > self.theta_wall:
            block += self.k_wall * (tl - self.theta_wall) + self.d_wall * wl
        dwl = (tau_spring - f_l - p.bl * wl - tau_ext - block) / p.Jl
        return wm, dwm, wl, dwl, diq

    def _current_pi(self, iq_ref: float, iq: float, wm: float,
                    int_state: float) -> tuple[float, float]:
        """PI + back-EMF feedforward with conditional anti-windup.

        Returns (vq_applied, new_integral).
        """
        p = self.p
        err = iq_ref - iq
        int_state += self.cur_ki * err * self.dt
        vq = int_state + self.cur_kp * err + p.Ke * wm
        vq_sat = np.clip(vq, -self.v_max, self.v_max)
        if vq_sat != vq:  # conditional integration (freeze on saturation)
            int_state -= self.cur_ki * err * self.dt
        return vq_sat, int_state

    def step(self, iq_ref: float, tau_ext: float = 0.0, n_steps: int = 1,
             tau_dist_motor: float = 0.0) -> None:
        """Advance the plant by n_steps integrator steps (default 1).

        The internal current loop runs at f_cur (10 kHz): the PI update
        happens every `f_cur * dt` integrator steps; between updates the
        applied voltage is held (zero-order hold).
        """
        p = self.p
        steps_per_cur = max(1, round(1.0 / (p.f_cur * self.dt)))
        dt = self.dt
        s = self.s
        tau_dm = tau_dist_motor
        for _ in range(n_steps):
            if self._cur_tick == 0:
                vq, s.iq_pi_int = self._current_pi(iq_ref, s.iq, s.omega_m, s.iq_pi_int)
                s.vq = vq
            tm, wm, tl, wl, iq = s.theta_m, s.omega_m, s.theta_l, s.omega_l, s.iq
            vq = s.vq
            # RK4 (float-only)
            k1 = self._deriv(tm, wm, tl, wl, iq, vq, tau_ext, tau_dm)
            k2 = self._deriv(tm + 0.5 * dt * k1[0], wm + 0.5 * dt * k1[1],
                             tl + 0.5 * dt * k1[2], wl + 0.5 * dt * k1[3],
                             iq + 0.5 * dt * k1[4], vq, tau_ext, tau_dm)
            k3 = self._deriv(tm + 0.5 * dt * k2[0], wm + 0.5 * dt * k2[1],
                             tl + 0.5 * dt * k2[2], wl + 0.5 * dt * k2[3],
                             iq + 0.5 * dt * k2[4], vq, tau_ext, tau_dm)
            k4 = self._deriv(tm + dt * k3[0], wm + dt * k3[1],
                             tl + dt * k3[2], wl + dt * k3[3],
                             iq + dt * k3[4], vq, tau_ext, tau_dm)
            s.theta_m = tm + (dt / 6.0) * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            s.omega_m = wm + (dt / 6.0) * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            s.theta_l = tl + (dt / 6.0) * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
            s.omega_l = wl + (dt / 6.0) * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
            s.iq = iq + (dt / 6.0) * (k1[4] + 2 * k2[4] + 2 * k3[4] + k4[4])
            d = s.theta_m - s.theta_l
            s.tau_s = p.ks * d + p.knl * d ** 3
            s.tau_m = p.Kt * s.iq + (p.cog_A6 * sin(6.0 * s.theta_m + p.cog_phi6)
                                     + p.cog_A12 * sin(12.0 * s.theta_m + p.cog_phi12)
                                     + s.iq * p.rip_frac * sin(6.0 * s.theta_m))
            s.tau_ext = tau_ext
            self._cur_tick = (self._cur_tick + 1) % steps_per_cur
            self.t += dt

    # -- sensing ------------------------------------------------------------

    def _quantize(self, angle: float, rng: np.random.Generator) -> float:
        p = self.p
        res = 2.0 * np.pi / (2 ** p.enc_bits)
        q = np.round(angle / res) * res
        if p.enc_noise_lsb > 0:
            q += rng.normal(0.0, p.enc_noise_lsb * res / np.sqrt(12.0))
        return q

    def observe(self, rng: np.random.Generator) -> dict:
        """Controller-visible measurements (quantized, noisy).

        The torque estimate uses the *calibrated* spring curve
        (obs_ks, obs_knl), set after the calibration step — exactly like the
        firmware observer.
        """
        tm_q = self._quantize(self.s.theta_m, rng)
        tl_q = self._quantize(self.s.theta_l, rng)
        d = tm_q - tl_q
        return {
            "theta_m": tm_q,
            "theta_l": tl_q,
            "omega_m": self.s.omega_m,      # differentiated in firmware; raw here
            "omega_l": self.s.omega_l,
            "iq": self.s.iq,
            "tau_s_true": self.s.tau_s,
            "tau_s_est": self.obs_ks * d + self.obs_knl * d ** 3,
            "delta_theta": d,
        }

    # -- bookkeeping ---------------------------------------------------------

    def reset(self, theta_m: float = 0.0, theta_l: float = 0.0) -> None:
        self.t = 0.0
        self._cur_tick = 0
        self.s = PlantState(theta_m=theta_m, theta_l=theta_l)

    def state_vector(self) -> np.ndarray:
        return self.s.as_array()
