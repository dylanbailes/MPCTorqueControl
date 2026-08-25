"""Run the full experiment suite: ID -> learned disturbance -> comparisons.

Outputs (written to results/):
  results/results.json   — the headline numbers
  results/plots/*.png    — figures for the writeup

Usage:
  python -m sim.run_experiments            # full run (~2-3 min)
  python -m sim.run_experiments --fast     # reduced durations
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learn.residual import LearnedDisturbance, ResidualConfig            # noqa: E402
from learn.system_id import (calibrate_spring, collect_excitation,       # noqa: E402
                             identify_from_data)
from model.impedance import ImpedanceConfig, ImpedanceSafety             # noqa: E402
from model.mpc import MPCConfig                                          # noqa: E402
from model.plant import PlantParams, SeaPlant                            # noqa: E402
from sim import bench, plotting                                          # noqa: E402


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))


K_BLOCK = 1e4   # blocked-output fixture stiffness [N.m/rad]


def run_all(fast: bool = False, quiet: bool = False) -> dict:
    t0 = time.time()
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)

    D = dict(calib=8.0, id=5.0, train=6.0, eval=6.0, disturb=4.0, coll=3.5)
    if fast:
        D = dict(calib=4.0, id=3.0, train=3.0, eval=3.0, disturb=2.5, coll=2.5)

    # ------------------------------------------------------------------ ID
    if not quiet:
        print("[1/4] System identification (spring calibration + inertia) ...",
              flush=True)
    ks, knl, calib_data = calibrate_spring(plant, duration=D["calib"])
    data_id = collect_excitation(plant, duration=D["id"], seed=3)
    idp = identify_from_data(data_id, p, ks=ks, knl=knl)
    # switch the torque observer to the calibrated spring curve
    plant.obs_ks, plant.obs_knl = ks, knl
    if not quiet:
        print(f"      spring: ks={ks:.3f} (true {p.ks}), knl={knl:.4f} (true {p.knl})")
        print(f"      inertia: Jm={idp.Jm:.3e} (true {p.Jm}), "
              f"Jl={idp.Jl:.3e} (true {p.Jl})")
        print(f"      rel errors: { {k: f'{v:.1%}' for k, v in idp.rel_err.items()} }")
    plotting.plot_id(idp, data_id, calib_data, p)

    # ------------------------------------------------- learned disturbance
    if not quiet:
        print("[2/4] Learning disturbance model (friction + cogging) ...", flush=True)

    def train_ref(t: float) -> float:
        s = (0.15 + 0.12 * np.sin(2 * np.pi * 0.7 * t)
             + 0.07 * np.sin(2 * np.pi * 1.9 * t + 0.8)
             + 0.05 * np.sin(2 * np.pi * 4.2 * t + 2.0)
             + 0.04 * np.sin(2 * np.pi * 7.0 * t))
        return float(s + 0.05 * np.sign(np.sin(2 * np.pi * 0.5 * t)))

    mpc_plain = bench.make_mpc(p, MPCConfig(), k_block=K_BLOCK)
    rec_train = bench.run_bench(plant, bench.SeaLoop(mpc_plain, plant),
                                train_ref, D["train"], seed=11, blocked=True)

    # disturbance target: torque the motor puts in the spring beyond the model.
    # (Viscous friction bm*omega is deliberately *not* subtracted — the learned
    # model absorbs it via its omega features, so bm ID errors cannot bias it.)
    wm_dot = np.gradient(rec_train["omega_m"], rec_train["t"])
    d_train = (p.Kt * rec_train["u_cmd"]
               - idp.Jm * wm_dot - rec_train["tau_s_est"])
    learned = LearnedDisturbance(ResidualConfig())
    fit_meta = learned.fit(rec_train["theta_m"], rec_train["omega_m"],
                           rec_train["u_cmd"], d_train)

    # held-out evaluation on the *smooth* evaluation trajectory
    rec_eval_plain = bench.run_bench(
        plant, bench.SeaLoop(bench.make_mpc(p, MPCConfig(), k_block=K_BLOCK),
                             plant),
        bench.ref_smooth, D["eval"], seed=13, blocked=True)
    wm_dot_e = np.gradient(rec_eval_plain["omega_m"], rec_eval_plain["t"])
    d_eval = (p.Kt * rec_eval_plain["u_cmd"]
              - idp.Jm * wm_dot_e - rec_eval_plain["tau_s_est"])
    d_hat_eval = learned.predict(rec_eval_plain["theta_m"], rec_eval_plain["omega_m"],
                                 rec_eval_plain["u_cmd"])
    ss_res = float(np.sum((d_eval - d_hat_eval) ** 2))
    ss_tot = float(np.sum((d_eval - np.mean(d_eval)) ** 2))
    eval_r2 = 1.0 - ss_res / ss_tot
    if not quiet:
        print(f"      held-out R² of learned disturbance: {eval_r2:.4f}")
    learned.export_to_c("results/learned_model.h")
    # export the condensed MPC constants for the firmware (blocked rig)
    bench.make_mpc(p, MPCConfig(), k_block=K_BLOCK).export_to_c(
        "results/mpc_model.h")
    plotting.plot_disturbance_fit(fit_meta, eval_r2, rec_eval_plain, d_eval,
                                  d_hat_eval, learned)

    # ------------------------------------------------------- comparisons
    if not quiet:
        print("[3/4] Controller comparison (PID vs MPC vs MPC+learned) ...",
              flush=True)

    def run_ctrl(kind: str, aug: str = "none", ref=bench.ref_smooth) -> dict:
        if kind == "pid":
            tc = bench.make_pid()
        else:
            tc = bench.make_mpc(p, MPCConfig(), k_block=K_BLOCK)
        ff = idp.friction_m if aug == "ff_id" else None
        lr = learned if aug == "learned" else None
        loop = bench.SeaLoop(tc, plant, friction_ff=ff, learned=lr)
        return bench.run_bench(plant, loop, ref, D["eval"], seed=13, blocked=True)

    # smooth tracking (the headline learning metric) + edge-rich stress test
    runs_smooth = {
        "PID": run_ctrl("pid"),
        "MPC": run_ctrl("mpc"),
        "MPC+FF-ID": run_ctrl("mpc", aug="ff_id"),
        "MPC+learned": run_ctrl("mpc", aug="learned"),
    }
    runs_edges = {
        "PID": run_ctrl("pid", ref=bench.ref_tracking),
        "MPC": run_ctrl("mpc", ref=bench.ref_tracking),
        "MPC+learned": run_ctrl("mpc", aug="learned", ref=bench.ref_tracking),
    }
    plotting.plot_tracking(runs_smooth, name="tracking_smooth.png")
    plotting.plot_tracking(runs_edges, name="tracking_edges.png")

    def _metrics(rec: dict) -> dict:
        err = rec["tau_s_est"] - rec["tau_ref"]
        settle = int(0.5 * len(rec["t"]))
        return {"rms_error_mNm": rms(err[settle:]) * 1e3,
                "max_error_mNm": float(np.max(np.abs(err[settle:])) * 1e3),
                "rms_error_overall_mNm": rms(err) * 1e3}

    metrics = {"smooth": {l: _metrics(r) for l, r in runs_smooth.items()},
               "edges": {l: _metrics(r) for l, r in runs_edges.items()}}
    if not quiet:
        print("      -- smooth tracking (settle window) --")
        for label, m in metrics["smooth"].items():
            print(f"      {label:14s} RMS err {m['rms_error_mNm']:6.2f} "
                  f"mN·m | max {m['max_error_mNm']:6.2f} mN·m")
        print("      -- edge-rich tracking (settle window) --")
        for label, m in metrics["edges"].items():
            print(f"      {label:14s} RMS err {m['rms_error_mNm']:6.2f} "
                  f"mN·m | max {m['max_error_mNm']:6.2f} mN·m")

    mpc_timing = {
        "solver": mpc_plain.cfg.solver,
        "qp_iterations": mpc_plain.solver.iterations,
        "horizon_steps": mpc_plain.cfg.N,
        "period_ms": mpc_plain.cfg.T * 1e3,
    }

    # ------------------------------------------------- disturbance rejection
    if not quiet:
        print("[4/4] Disturbance rejection + collision demo ...", flush=True)

    def dist_motor_fn(t: float) -> float:
        return 0.15 if t >= 1.5 else 0.0   # persistent step disturbance

    d_runs = {}
    for label, (kind, aug) in {"PID": ("pid", "none"),
                               "MPC": ("mpc", "none"),
                               "MPC+learned": ("mpc", "learned")}.items():
        d_runs[label] = run_ctrl_dist(kind, aug, dist_motor_fn, D["disturb"],
                                      plant, p, learned)
    plotting.plot_disturbance(d_runs)
    dist_metrics = {}
    for label, rec in d_runs.items():
        window = (rec["t"] >= 1.5) & (rec["t"] < 1.7)     # transient
        steady = (rec["t"] >= 1.9) & (rec["t"] < 2.2)     # after settling
        err = np.abs(rec["tau_s_est"] - rec["tau_ref"])
        dist_metrics[label] = {
            "peak_error_mNm": float(np.max(err[window]) * 1e3),
            "steady_error_mNm": float(np.mean(err[steady]) * 1e3),
        }
        if not quiet:
            print(f"      {label:14s} disturbance step: peak "
                  f"{dist_metrics[label]['peak_error_mNm']:6.2f} mN·m | steady "
                  f"{dist_metrics[label]['steady_error_mNm']:6.2f} mN·m")

    # collision demo: the arm swings under impedance control (theta_d = 0.5)
    # and a hand grabs the output at t=0.8 s (theta_l pinned).  Torque builds
    # against the grip; the stall detector trips; the actuator gives way.
    imp = ImpedanceSafety(ImpedanceConfig())
    imp.set_friction_model(learned.friction_only)
    pid_c = bench.make_pid()  # model-free inner loop is more robust at contact
    loop_coll = bench.SeaLoop(pid_c, plant, impedance=imp, learned=learned)
    rec_coll = bench.run_bench(plant, loop_coll, bench.ref_zero, D["coll"],
                               theta_d=0.5, grab=(0.1, 2000.0, 5.0), seed=5)
    plotting.plot_collision(rec_coll)

    det_t = (rec_coll["t"][np.argmax(rec_coll["collision"])]
             if rec_coll["collision"].any() else np.inf)
    t_grab = 0.1
    coll_metrics = {
        "detected": bool(rec_coll["collision"].any()),
        "grab_time_s": t_grab,
        "detection_latency_ms": (
            float((det_t - t_grab) * 1e3)
            if np.isfinite(det_t) else None),
        "post_collision_peak_torque_mNm": (
            float(np.max(np.abs(rec_coll["tau_s_est"][rec_coll["collision"] > 0])) * 1e3)
            if rec_coll["collision"].any() else None),
    }
    if not quiet:
        if coll_metrics["detection_latency_ms"] is not None:
            print(f"      output grabbed at t={t_grab:.2f} s; collision detected "
                  f"{coll_metrics['detection_latency_ms']:.0f} ms later")
        else:
            print("      collision NOT detected")

    # -------------------------------------------------------------- results
    results = {
        "plant": {"Jm": p.Jm, "Jl": p.Jl, "ks": p.ks, "knl": p.knl, "Kt": p.Kt,
                  "resonance_Hz": float(np.sqrt(p.ks * (1 / p.Jm + 1 / p.Jl))
                                        / (2 * np.pi))},
        "identified": {"ks": ks, "knl": knl,
                       "rel_errors": {k: float(v) for k, v in idp.rel_err.items()}},
        "learned_disturbance": {"heldout_r2": float(eval_r2),
                                "beta": [float(b) for b in learned.beta]},
        "tracking": metrics,
        "disturbance": dist_metrics,
        "collision": coll_metrics,
        "mpc": mpc_timing,
        "wall_seconds": time.time() - t0,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/results.json", "w") as f:
        json.dump(results, f, indent=2)
    if not quiet:
        print(f"\nDone in {results['wall_seconds']:.1f} s — results/results.json")
    return results


def run_ctrl_dist(kind: str, aug: str, dist_motor_fn, duration: float,
                  plant: SeaPlant, p: PlantParams, learned) -> dict:
    if kind == "pid":
        tc = bench.make_pid()
    else:
        tc = bench.make_mpc(p, MPCConfig(), k_block=K_BLOCK)
    lr = learned if aug == "learned" else None
    loop = bench.SeaLoop(tc, plant, learned=lr)
    return bench.run_bench(plant, loop, bench.ref_hold, duration,
                           dist_motor_fn=dist_motor_fn, seed=17, blocked=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    run_all(fast=args.fast, quiet=args.quiet)
