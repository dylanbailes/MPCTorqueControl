"""Benchmark harness: run the digital-twin plant in closed loop.

`SeaLoop` composes the full control stack exactly like the firmware:

    impedance (virtual spring-damper)
        -> torque controller (MPC or PID)
            -> learned feedforward (friction compensation)
                -> safety (collision clamp)
                    -> plant (internal FOC current loop)

`run_bench` advances the plant at 100 kHz while controllers sample at fs.
"""

from __future__ import annotations

import numpy as np

from model.impedance import ImpedanceSafety
from model.mpc import LinearSeaModel, MPCConfig, SeaMPC
from model.pid import PidTorqueController, PIDConfig
from model.plant import PlantParams, SeaPlant


class SeaLoop:
    """Full control stack adapter with configurable augmentation."""

    def __init__(self, torque_ctrl, plant: SeaPlant,
                 impedance: ImpedanceSafety | None = None,
                 friction_ff=None, learned=None):
        self.torque_ctrl = torque_ctrl
        self.plant = plant
        self.imp = impedance
        self.friction_ff = friction_ff   # tau_fric_hat(omega_m) -> N.m
        self.learned = learned           # LearnedResidual -> d_hat
        self.theta_d = 0.0

    def update(self, t: float, obs: dict, tau_ref_ext: float, dt: float) -> float:
        p = self.plant.p
        x = np.array([obs["theta_m"], obs["omega_m"], obs["theta_l"], obs["omega_l"]])
        tau_ref = tau_ref_ext
        if self.imp is not None:
            tau_ref = self.imp.torque_reference(self.theta_d, obs["theta_l"],
                                                obs["omega_l"])

        # torque controller (MPC or PID)
        if isinstance(self.torque_ctrl, SeaMPC):
            u = self.torque_ctrl.step(x, tau_ref)
        else:
            u = self.torque_ctrl.step(tau_ref, obs["tau_s_est"], dt)

        # learned disturbance compensation (friction + cogging + ripple)
        if self.friction_ff is not None:      # classical identified friction
            u += self.friction_ff(obs["omega_m"]) / p.Kt
        if self.learned is not None:          # learned disturbance model
            u += self.learned.feedforward(obs["theta_m"], obs["omega_m"], u, p.Kt)

        # safety (momentum observer + stall detection)
        if self.imp is not None:
            self.imp.update_observer(p.Kt * obs["iq"], obs["tau_s_est"],
                                     obs["omega_m"], dt)
            self.imp.check(obs["tau_s_est"], obs["omega_l"], tau_ref, dt)
            u = self.imp.safe_command(u)
        return float(np.clip(u, -3.0, 3.0))


def run_bench(plant: SeaPlant, loop: SeaLoop, ref_fn, duration: float,
              fs: int = 2000, dist_fn=None, dist_motor_fn=None, collision=None,
              seed: int = 7, theta_d=0.0, blocked: bool = False,
              k_block: float = 1e4, d_block: float = 50.0,
              wall: tuple | None = None, grab: tuple | None = None) -> dict:
    """Run a closed-loop experiment.

    ref_fn(t)         -> torque reference [N.m] (ignored if impedance enabled)
    dist_fn(t)        -> external torque on the load [N.m]
    dist_motor_fn(t)  -> external torque on the motor rotor [N.m]
    collision         -> (t_start, duration, amplitude) torque pulse on the load
    blocked           -> clamp the output with a stiff spring to ground
                         (the classic blocked-output torque-control rig)
    """
    rng = np.random.default_rng(seed)
    dt = 1.0 / fs
    n = int(duration * fs)
    steps_per_tick = max(1, int(1.0 / (fs * plant.dt)))
    loop.theta_d = theta_d
    if hasattr(loop.torque_ctrl, "reset"):
        loop.torque_ctrl.reset()
    if loop.imp is not None:
        loop.imp.reset()
    if blocked:
        plant.set_blocked_output(k_block, d_block)
    else:
        plant.set_blocked_output(0.0, 0.0)
    if wall is not None:
        plant.set_wall(*wall)
    else:
        plant.clear_wall()
    grab_t, grab_k, grab_d = grab if grab else (1e9, 0.0, 0.0)

    plant.reset()
    rec = {k: np.zeros(n) for k in
           ["t", "tau_ref", "tau_s_est", "tau_s_true", "u_cmd",
            "theta_m", "omega_m", "theta_l", "omega_l", "iq",
            "tau_coll_hat", "collision", "tau_ext", "tau_dm"]}

    for k in range(n):
        t = k * dt
        tau_ref = ref_fn(t) if ref_fn else 0.0
        tau_ext = dist_fn(t) if dist_fn else 0.0
        if collision is not None:
            t0, dur, amp = collision
            if t0 <= t < t0 + dur:
                tau_ext += amp

        obs = plant.observe(rng)
        if t >= grab_t and plant.theta_wall is None:
            # a hand grabs the output: pin theta_l at its current position
            plant.set_wall(plant.s.theta_l, grab_k, grab_d)
        u = loop.update(t, obs, tau_ref, dt)
        tau_dm = dist_motor_fn(t) if dist_motor_fn else 0.0
        plant.step(u, tau_ext=tau_ext, n_steps=steps_per_tick,
                   tau_dist_motor=tau_dm)

        rec["t"][k] = t
        rec["tau_ref"][k] = tau_ref
        rec["tau_s_est"][k] = obs["tau_s_est"]
        rec["tau_s_true"][k] = obs["tau_s_true"]
        rec["u_cmd"][k] = u
        rec["theta_m"][k] = obs["theta_m"]
        rec["omega_m"][k] = obs["omega_m"]
        rec["theta_l"][k] = obs["theta_l"]
        rec["omega_l"][k] = obs["omega_l"]
        rec["iq"][k] = obs["iq"]
        rec["tau_coll_hat"][k] = loop.imp.coll.tau_coll_hat if loop.imp else 0.0
        rec["collision"][k] = 1.0 if (loop.imp and loop.imp.coll.detected) else 0.0
        rec["tau_ext"][k] = tau_ext
        rec["tau_dm"][k] = tau_dm
    return rec


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_mpc(p: PlantParams, cfg: MPCConfig | None = None,
             k_block: float = 0.0) -> SeaMPC:
    cfg = cfg if cfg is not None else MPCConfig()
    model = LinearSeaModel(p.Jm, p.bm, p.Jl, p.bl, p.ks, p.Kt, cfg.T,
                           k_block=k_block)
    return SeaMPC(model, cfg)


def make_pid(cfg: PIDConfig | None = None) -> PidTorqueController:
    return PidTorqueController(cfg if cfg is not None else PIDConfig())


# ---------------------------------------------------------------------------
# Reference trajectories
# ---------------------------------------------------------------------------


def ref_smooth(t: float) -> float:
    """Smooth rich torque reference (steady-state tracking test)."""
    import numpy as _np
    return float(0.15 + 0.10 * _np.sin(2 * _np.pi * 0.8 * t)
                 + 0.06 * _np.sin(2 * _np.pi * 2.3 * t + 1.0)
                 + 0.04 * _np.sin(2 * _np.pi * 5.0 * t + 0.4)
                 + 0.03 * _np.sin(2 * _np.pi * 7.3 * t + 0.2))


def ref_tracking(t: float) -> float:
    """Rich torque reference: sines + a square-wave edge (stress test)."""
    import numpy as _np
    s = ref_smooth(t)
    sq = 0.05 * _np.sign(_np.sin(2 * _np.pi * 0.6 * t))
    return float(s + sq)


def ref_hold(t: float) -> float:
    """Constant torque reference (for disturbance-rejection tests)."""
    return 0.25


def ref_zero(t: float) -> float:
    """Zero torque reference."""
    return 0.0
