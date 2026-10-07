"""Run the full experiment suite: ID -> learned disturbance -> comparisons.

Outputs (written to results/):
  results/results.json   — the headline numbers
  results/plots/*.png    — figures for the writeup

Usage:
  python -m sim.run_experiments            # full run (~4-5 min)
  python -m sim.run_experiments --fast     # reduced durations
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from importlib.metadata import version

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learn.residual import LearnedDisturbance, ResidualConfig            # noqa: E402
from learn.system_id import (calibrate_spring, collect_excitation,       # noqa: E402
                             identify_from_data)
from model.impedance import ImpedanceConfig, ImpedanceSafety             # noqa: E402
from model.mpc import MPCConfig                                          # noqa: E402
from model.plant import PlantParams, SeaPlant                            # noqa: E402
from model.pid import PIDConfig                                         # noqa: E402
from sim import bench, plotting                                          # noqa: E402


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))


def backward_diff(x: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Causal (k-1 -> k) derivative: the learned FF must not see the future.

    np.gradient uses central differences (needs x_{k+1}), so a residual
    computed from it is not predictable at sample k on sharp edges.
    """
    w = np.empty_like(x)
    w[0] = 0.0
    w[1:] = np.diff(x) / np.diff(t)
    return w


K_BLOCK = 1e4   # blocked-output fixture stiffness [N.m/rad]
D_BLOCK = 50.0  # blocked-output fixture damping [N.m.s/rad] (in the MPC model too)


def run_all(fast: bool = False, quiet: bool = False,
            r: float | None = None, l: float | None = None,
            kt: float | None = None, jm: float | None = None,
            u_max: float | None = None, n: int | None = None,
            out_dir: str = "results") -> dict:
    """Run the experiment suite.

    Optional overrides (used for as-built real-motor runs; the defaults in
    model/plant.py stay as the *nominal* design values):
        r    — winding resistance [ohm]
        l    — winding inductance [H]
        kt   — torque constant [N.m/A] (Ke set equal)
        jm   — rotor inertia [kg.m^2]
        u_max— MPC current limit [A]
        n    — MPC prediction horizon [steps]
        out_dir — write results.json, mpc_model.h, learned_model.h and
                  plots here instead of results/ (baseline stays untouched)
    """
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    p = PlantParams()
    if r is not None:
        p.R = r
    if l is not None:
        p.L = l
    if kt is not None:
        p.Kt = kt
        p.Ke = kt
    if jm is not None:
        p.Jm = jm
    if u_max is not None or n is not None:
        kw = {}
        if u_max is not None:
            kw["u_max"] = u_max
        if n is not None:
            kw["N"] = n
        cfg = MPCConfig(**kw)
    else:
        cfg = MPCConfig()
    plotting.OUT_DIR = os.path.join(out_dir, "plots")
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
        if idp.Jm_freq is not None:
            print(f"      freq-domain cross-check: f_res={idp.f_res_hz:.2f} Hz "
                  f"(coherence {idp.fd_coherence:.2f}) -> Jm_fd={idp.Jm_freq:.3e}")
            print(f"      Jm fusion (ridge w={idp.jm_prior_weight:.2f}): "
                  f"td {idp.Jm_td:.3e} + fd {idp.Jm_freq:.3e} -> "
                  f"{idp.Jm:.3e} (td-vs-fd agreement "
                  f"{idp.fd_vs_td_rel_diff:.1%})")
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

    # The controller is *model-based*: build it (and the exported header) from
    # the identified/fused inertia, not the nominal plant value.  Keep the
    # true value around to quantify the mis-modeling impact below.
    jm_mpc = idp.Jm
    mpc_plain = bench.make_mpc(p, cfg, k_block=K_BLOCK, d_block=D_BLOCK,
                               jm=jm_mpc)
    rec_train = bench.run_bench(plant, bench.SeaLoop(mpc_plain, plant),
                                train_ref, D["train"], seed=11, blocked=True)

    # disturbance target: torque the motor puts in the spring beyond the model.
    # (Viscous friction bm*omega is deliberately *not* subtracted — the learned
    # model absorbs it via its omega features, so bm ID errors cannot bias it.)
    # Backward difference (causal): the FF at sample k must not depend on
    # x_{k+1} — with central differences the map cannot generalize to edges.
    wm_dot = backward_diff(rec_train["omega_m"], rec_train["t"])
    d_train = (p.Kt * rec_train["u_cmd"]
               - idp.Jm * wm_dot - rec_train["tau_s_est"])
    learned = LearnedDisturbance(ResidualConfig(), kt=p.Kt)
    fit_meta = learned.fit(rec_train["theta_m"], rec_train["omega_m"],
                           rec_train["u_cmd"], d_train)

    # held-out evaluation on the *smooth* evaluation trajectory (same tuned
    # MPC config as the comparison runs below)
    rec_eval_plain = bench.run_bench(
        plant, bench.SeaLoop(bench.make_mpc(p, cfg, k_block=K_BLOCK,
                                            d_block=D_BLOCK, jm=jm_mpc), plant),
        bench.ref_smooth, D["eval"], seed=13, blocked=True)
    wm_dot_e = backward_diff(rec_eval_plain["omega_m"], rec_eval_plain["t"])
    d_eval = (p.Kt * rec_eval_plain["u_cmd"]
              - idp.Jm * wm_dot_e - rec_eval_plain["tau_s_est"])
    d_hat_eval = learned.predict(rec_eval_plain["theta_m"], rec_eval_plain["omega_m"],
                                 rec_eval_plain["u_cmd"])
    ss_res = float(np.sum((d_eval - d_hat_eval) ** 2))
    ss_tot = float(np.sum((d_eval - np.mean(d_eval)) ** 2))
    eval_r2 = 1.0 - ss_res / ss_tot
    if not quiet:
        print(f"      held-out R² of learned disturbance: {eval_r2:.4f}")
    learned.export_to_c(os.path.join(out_dir, "learned_model.h"))
    # export the condensed MPC constants for the firmware (blocked rig),
    # using the *identified* Jm so the deployed controller matches the
    # identified plant (not the nominal design value)
    bench.make_mpc(p, cfg, k_block=K_BLOCK, d_block=D_BLOCK,
                   jm=jm_mpc).export_to_c(os.path.join(out_dir, "mpc_model.h"))
    plotting.plot_disturbance_fit(fit_meta, eval_r2, rec_eval_plain, d_eval,
                                  d_hat_eval, learned)

    # ------------------------------------------------------- comparisons
    if not quiet:
        print("[3/4] Controller comparison (PID vs MPC vs MPC+learned) ...",
              flush=True)

    def run_ctrl(kind: str, aug: str = "none", ref=bench.ref_smooth,
                 jm: float | None = None) -> dict:
        if kind == "pid":
            tc = bench.make_pid(PIDConfig(u_max=cfg.u_max))
        else:
            tc = bench.make_mpc(p, cfg, k_block=K_BLOCK, d_block=D_BLOCK,
                               jm=jm if jm is not None else jm_mpc)
        ff = idp.friction_m if aug == "ff_id" else None
        lr = learned if aug == "learned" else None
        loop = bench.SeaLoop(tc, plant, friction_ff=ff, learned=lr, u_max=cfg.u_max)
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

    # --- quantify Jm mis-modeling: plain MPC built on the *true* inertia vs.
    # on the *identified* inertia.  Same controller weights, same references;
    # only the prediction-model Jm changes, so the delta is attributable to
    # the identified-vs-true model used by the deployed controller.
    if not quiet:
        print("      -- MPC sensitivity to model Jm (true vs identified) --")
    jm_impact = {}
    for name, ref in (("smooth", bench.ref_smooth),
                      ("edges", bench.ref_tracking)):
        m_true = _metrics(run_ctrl("mpc", ref=ref, jm=p.Jm))
        m_id = _metrics(run_ctrl("mpc", ref=ref, jm=jm_mpc))
        jm_impact[name] = {
            "true_RMS_mNm": m_true["rms_error_mNm"],
            "identified_RMS_mNm": m_id["rms_error_mNm"],
            "delta_RMS_mNm": m_id["rms_error_mNm"] - m_true["rms_error_mNm"],
            "delta_pct": (m_id["rms_error_mNm"] / m_true["rms_error_mNm"]
                          - 1.0) * 100.0,
        }
        if not quiet:
            print(f"      {name:6s} MPC RMS err {m_true['rms_error_mNm']:6.2f} "
                  f"mN·m (true Jm) -> {m_id['rms_error_mNm']:6.2f} mN·m "
                  f"(identified Jm), delta "
                  f"{jm_impact[name]['delta_pct']:+.2f}%")

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
                                      plant, p, learned, cfg, jm=jm_mpc)
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
    # and a grip pins the output at t=0.1 s.  Torque builds
    # against the grip; the stall detector trips; the actuator gives way.
    imp = ImpedanceSafety(ImpedanceConfig())
    imp.set_friction_model(learned.friction_only)
    pid_c = bench.make_pid(PIDConfig(u_max=cfg.u_max))
    loop_coll = bench.SeaLoop(pid_c, plant, impedance=imp, learned=learned,
                              u_max=cfg.u_max)
    rec_coll = bench.run_bench(plant, loop_coll, bench.ref_zero, D["coll"],
                               theta_d=0.5, grab=(0.1, 2000.0, 5.0), seed=5)
    plotting.plot_collision(rec_coll, grab_time=0.1)

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
            float(np.max(np.abs(rec_coll["tau_s_est"][rec_coll["t"] >= t_grab])) * 1e3)),
    }
    if not quiet:
        if coll_metrics["detection_latency_ms"] is not None:
            print(f"      output grabbed at t={t_grab:.2f} s; collision detected "
                  f"{coll_metrics['detection_latency_ms']:.0f} ms later")
        else:
            print("      collision NOT detected")

    # -------------------------------------------------------------- results
    results = {
        "schema_version": 2,
        "provenance": {
            "simulation_only": True,
            "fast": fast,
            "plant_parameters": asdict(p),
            "mpc_config": asdict(cfg),
            "pid_config": asdict(PIDConfig(u_max=cfg.u_max)),
            "residual_config": asdict(learned.cfg),
            "integration_dt_s": plant.dt,
            "durations_s": D,
            "fixture": {"k_block": K_BLOCK, "d_block": D_BLOCK},
            "seeds": {"spring_calibration": 7, "system_id_excitation": 3,
                      "system_id_measurement_noise": 7,
                      "training": 11, "evaluation": 13,
                      "disturbance": 17, "collision": 5},
            "python_version": sys.version.split()[0],
            "dependencies": {name: version(name) for name in
                             ("numpy", "scipy", "matplotlib")},
        },
        "plant": {"Jm": p.Jm, "Jl": p.Jl, "ks": p.ks, "knl": p.knl, "Kt": p.Kt,
                  "resonance_Hz": float(np.sqrt(p.ks * (1 / p.Jm + 1 / p.Jl))
                                        / (2 * np.pi))},
        "identified": {"ks": ks, "knl": knl,
                       "Jm_td": idp.Jm_td,
                       "Jm_freq": idp.Jm_freq,
                       "jm_prior_weight": idp.jm_prior_weight,
                       "f_res_est_hz": idp.f_res_hz,
                       "fd_coherence": idp.fd_coherence,
                       "fd_vs_td_rel_diff": idp.fd_vs_td_rel_diff,
                       "rel_errors": {k: float(v) for k, v in idp.rel_err.items()}},
        "learned_disturbance": {"heldout_r2": float(eval_r2),
                                "beta": [float(b) for b in learned.beta],
                                "friction_beta": [float(b) for b in learned.friction_beta]},
        "tracking": metrics,
        "identified_model_impact": {
            "model_Jm": jm_mpc,
            "true_Jm": p.Jm,
            "Jm_rel_diff": (jm_mpc - p.Jm) / p.Jm,
            "jm_impact": jm_impact,
        },
        "disturbance": dist_metrics,
        "collision": coll_metrics,
        "mpc": mpc_timing,
        "wall_seconds": time.time() - t0,
    }
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, allow_nan=False)
        f.write("\n")
    if not quiet:
        print(f"\nDone in {results['wall_seconds']:.1f} s — {out_path}")
    return results


def run_ctrl_dist(kind: str, aug: str, dist_motor_fn, duration: float,
                  plant: SeaPlant, p: PlantParams, learned,
                  cfg: MPCConfig | None = None,
                  jm: float | None = None) -> dict:
    if kind == "pid":
        tc = bench.make_pid(PIDConfig(u_max=(cfg or MPCConfig()).u_max))
    else:
        tc = bench.make_mpc(p, cfg if cfg is not None else MPCConfig(),
                            k_block=K_BLOCK, d_block=D_BLOCK, jm=jm)
    lr = learned if aug == "learned" else None
    loop = bench.SeaLoop(tc, plant, learned=lr, u_max=(cfg or MPCConfig()).u_max)
    return bench.run_bench(plant, loop, bench.ref_hold, duration,
                           dist_motor_fn=dist_motor_fn, seed=17, blocked=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--r", type=float, default=None,
                    help="winding resistance [ohm] (GM5208: 6.85 per-phase "
                         "if 13.7 is line-to-line, or 13.7)")
    ap.add_argument("--l", type=float, default=None,
                    help="winding inductance [H] (GM5208: ~10e-3)")
    ap.add_argument("--kt", type=float, default=None,
                    help="torque constant [N.m/A] (GM5208: ~0.2; 4015: 0.1562)")
    ap.add_argument("--jm", type=float, default=None,
                    help="rotor inertia [kg.m^2] (4015: ~3e-5 -> ~30 Hz)")
    ap.add_argument("--u-max", type=float, default=None,
                    help="MPC current limit [A] (4015: 3.0-4.0)")
    ap.add_argument("--n", type=int, default=None,
                    help="MPC prediction horizon [steps] (4015: 20-40)")
    ap.add_argument("--out-dir", default="results",
                    help="output directory for results.json, exports, plots")
    args = ap.parse_args()
    run_all(fast=args.fast, quiet=args.quiet, r=args.r, l=args.l, kt=args.kt,
            jm=args.jm, u_max=args.u_max, n=args.n, out_dir=args.out_dir)
