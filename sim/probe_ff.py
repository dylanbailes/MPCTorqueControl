"""Fast probe of learned-FF variants on the GM5208 real-motor parameters.

Iterates the edge-rich and disturbance tests only (skips ID/plots) so we
can tune the feedforward quickly before committing to a full suite run.

Usage:  python -m sim.probe_ff
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learn.residual import LearnedDisturbance, ResidualConfig          # noqa: E402
from model.mpc import MPCConfig                                       # noqa: E402
from model.plant import PlantParams, SeaPlant                         # noqa: E402
from sim import bench                                                 # noqa: E402
from sim.run_experiments import backward_diff                         # noqa: E402

K_BLOCK, D_BLOCK = 1e4, 50.0
# identified Jm from the deterministic ID step at these params (32% high)
JM_HAT = 1.057e-4


def train_and_fit(p, cfg, u_ff_max: float):
    plant = SeaPlant(p, dt=2e-5)
    mpc = bench.make_mpc(p, cfg, k_block=K_BLOCK, d_block=D_BLOCK)
    rec = bench.run_bench(plant, bench.SeaLoop(mpc, plant), bench.ref_smooth,
                          4.0, seed=11, blocked=True)
    wm = backward_diff(rec["omega_m"], rec["t"])
    d = p.Kt * rec["u_cmd"] - JM_HAT * wm - rec["tau_s_est"]
    lr = LearnedDisturbance(ResidualConfig(u_ff_max=u_ff_max), kt=p.Kt)
    meta = lr.fit(rec["theta_m"], rec["omega_m"], rec["u_cmd"], d)
    return plant, mpc, lr, meta["r2"]


def edge_rms(plant, mpc, lr, dur: float = 3.0, seed: int = 13) -> float:
    r = bench.run_bench(plant, bench.SeaLoop(mpc, plant, learned=lr),
                        bench.ref_tracking, dur, seed=seed, blocked=True)
    err = r["tau_s_est"] - r["tau_ref"]
    return float(np.sqrt((err ** 2).mean()) * 1e3)


def disturb_steady(plant, mpc, lr, dur: float = 3.0) -> float:
    def dist(t):
        return 0.15 if t >= 1.5 else 0.0
    rd = bench.run_bench(plant, bench.SeaLoop(mpc, plant, learned=lr),
                         bench.ref_hold, dur, dist_motor_fn=dist,
                         seed=17, blocked=True)
    er = np.abs(rd["tau_s_est"] - rd["tau_ref"])
    return float(np.mean(er[(rd["t"] >= 1.9) & (rd["t"] < 2.2)]) * 1e3)


if __name__ == "__main__":
    p = PlantParams()
    p.R, p.L, p.Kt, p.Ke = 6.85, 0.01, 0.2, 0.2
    cfg = MPCConfig(u_max=2.0)

    # baselines (no learned FF)
    plant0 = SeaPlant(p, dt=2e-5)
    mpc0 = bench.make_mpc(p, cfg, k_block=K_BLOCK, d_block=D_BLOCK)
    print(f"MPC alone        : edges RMS {edge_rms(plant0, mpc0, None):7.2f} "
          f"mN·m | disturb steady {disturb_steady(plant0, mpc0, None):6.3f} mN·m")

    for ff in (1.0, 0.5, 0.25):
        plant, mpc, lr, r2 = train_and_fit(p, cfg, ff)
        e = edge_rms(plant, mpc, lr)
        d = disturb_steady(plant, mpc, lr)
        print(f"u_ff_max={ff:<4.2f} (fit R²={r2:.3f}): edges RMS {e:7.2f} "
              f"mN·m | disturb steady {d:6.3f} mN·m")
