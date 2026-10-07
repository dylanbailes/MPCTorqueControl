"""MPC robustness to Jm misidentification on the 4015 build.

Builds the condensed MPC prediction model with deliberately wrong motor
inertias (a mis-modeling multiplier around the true Jm) and measures torque
tracking on the smooth and edge-rich references, plus whether the chosen
u_max/du_max ever saturates differently.  Same plant, same controller
weights, same seeds — only the prediction-model Jm changes.

Prints a table and writes results/jm_robustness.json.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.mpc import MPCConfig                          # noqa: E402
from model.plant import PlantParams, SeaPlant            # noqa: E402
from sim import bench                                    # noqa: E402


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))


def metrics(rec: dict) -> dict:
    err = rec["tau_s_est"] - rec["tau_ref"]
    settle = int(0.5 * len(rec["t"]))
    return {"rms_mNm": rms(err[settle:]) * 1e3,
            "max_mNm": float(np.max(np.abs(err[settle:])) * 1e3)}


def main():
    K_BLOCK, D_BLOCK = 1e4, 50.0
    cfg = MPCConfig(N=30, u_max=3.0)
    p = PlantParams()
    p.R, p.L, p.Kt, p.Ke, p.Jm, p.Jl = 4.8, 2.6e-3, 0.1562, 0.1562, 3e-5, 1.2e-3
    plant = SeaPlant(p, dt=2e-5)

    # model-Jm multipliers around true (1.0).  >1.0 = controller assumes a
    # heavier rotor than reality; <1.0 = assumes lighter.
    mults = [-0.75, -0.50, -0.30, -0.15, 0.0, +0.30, +0.50, +1.0, +2.0, +3.0,
             +4.0, +5.0, +6.0, +8.0]

    rows = []
    for mult in mults:
        jm_model = p.Jm * (1.0 + mult)
        mpc = bench.make_mpc(p, cfg, k_block=K_BLOCK, d_block=D_BLOCK, jm=jm_model)
        sm = metrics(bench.run_bench(plant, bench.SeaLoop(mpc, plant),
                                     bench.ref_smooth, 4.0, seed=13,
                                     blocked=True))
        ed = bench.run_bench(plant, bench.SeaLoop(mpc, plant),
                             bench.ref_tracking, 4.0, seed=13, blocked=True)
        ed_met = metrics(ed)
        peak_u = float(np.max(np.abs(ed["u_cmd"])))
        rows.append({"mult": mult, "jm_model": jm_model,
                     "smooth_rms_mNm": sm["rms_mNm"], "smooth_max_mNm": sm["max_mNm"],
                     "edges_rms_mNm": ed_met["rms_mNm"],
                     "edges_max_mNm": ed_met["max_mNm"],
                     "peak_u_cmd_A": peak_u, "u_max": cfg.u_max})
        print(f"jm_model={jm_model:.2e} (x{mult:+5.2f})  smooth {sm['rms_mNm']:6.2f}/{sm['max_mNm']:6.2f} "
              f"mN·m | edges {ed_met['rms_mNm']:6.2f}/{ed_met['max_mNm']:6.2f} mN·m | "
              f"peak |u| {peak_u:.2f}/{cfg.u_max} A")

    baseline = next(r for r in rows if r["mult"] == 0.0)
    summary = {
        "true_Jm": p.Jm,
        "cfg": {"N": cfg.N, "u_max": cfg.u_max, "du_max": cfg.du_max},
        "baseline_model_Jm": baseline["jm_model"],
        "baseline": {"smooth_rms_mNm": baseline["smooth_rms_mNm"],
                     "edges_rms_mNm": baseline["edges_rms_mNm"]},
        "rows": rows,
    }
    with open("results/jm_robustness.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nwrote results/jm_robustness.json")


if __name__ == "__main__":
    main()