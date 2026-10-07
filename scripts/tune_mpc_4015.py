"""MPC design study for the as-built 4015 motor (hybrid build).

Runs the same closed-loop benchmark the week-9 design study would, but on
the *identified* 4015 two-mass plant instead of the nominal one, and sweeps
the two design knobs that physically shift with the motor swap:

    N     — prediction horizon (the resonance moved 18 Hz -> ~30 Hz, so the
            N=20 horizon sees less of the cycle)
    u_max — current authority (the 4015 is rated 4 A max; the old 4 A
            authority was unreachable on the GM5208, here it is real)

As-built 4015 parameters (verified Aug 2026, QiuLovesYT listing):
    Kt = Ke = 0.1562 N.m/A   (KV = 61 RPM/V -> 60/(2*pi*KV) = 0.1566)
    R  = 4.8 ohm             (winding phase resistance)
    L  = 2.6 mH              (winding phase inductance)
    Jm ~ 3e-5 kg.m^2         (estimate; 129 g motor -> f_res ~ 30 Hz)
    rated torque 0.3 N.m @ 24 V, max current 4 A
    practical standstill current ceiling ~ Vbus/sqrt(3)/R ~ 2.9 A
    (SVPWM linear range on the 24 V bus), so u_max is a soft bound; the
    0.35 N.m spring envelope needs only ~2.25 A.

Everything else (Jl = 1.2e-3, ks = 1.0, friction) stays at the nominal
design values — Jl/ks are hardware-measured (weeks 5-6) and friction is
re-identified in week 7 regardless.

Usage:
    python scripts/tune_mpc_4015.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.mpc import MPCConfig
from model.plant import PlantParams, SeaPlant
from sim import bench

K_BLOCK = 1e4
D_BLOCK = 50.0
DUR = 4.0          # per-run duration [s] (sweep speed)
FS = 2000

# ------------------------------------------------------------------ as-built
P4015 = dict(
    R=4.8, L=2.6e-3, Kt=0.1562, Ke=0.1562, Jm=3.0e-5,
)


def build_plant() -> SeaPlant:
    p = PlantParams()
    for k, v in P4015.items():
        setattr(p, k, v)
    return SeaPlant(p, dt=2e-5)


def f_res(p: PlantParams) -> float:
    return float(np.sqrt(p.ks * (1.0 / p.Jm + 1.0 / p.Jl)) / (2 * np.pi))


def metrics(rec: dict) -> dict:
    err = rec["tau_s_est"] - rec["tau_ref"]
    settle = int(0.5 * len(rec["t"]))
    return {
        "rms_mNm": float(np.sqrt(np.mean(err[settle:] ** 2)) * 1e3),
        "max_mNm": float(np.max(np.abs(err[settle:])) * 1e3),
        "overall_rms_mNm": float(np.sqrt(np.mean(err ** 2)) * 1e3),
    }


def run_smooth(plant: SeaPlant, cfg: MPCConfig) -> dict:
    loop = bench.SeaLoop(bench.make_mpc(plant.p, cfg, k_block=K_BLOCK,
                                        d_block=D_BLOCK), plant)
    return bench.run_bench(plant, loop, bench.ref_smooth, DUR, fs=FS,
                           seed=13, blocked=True)


def run_edges(plant: SeaPlant, cfg: MPCConfig) -> dict:
    loop = bench.SeaLoop(bench.make_mpc(plant.p, cfg, k_block=K_BLOCK,
                                        d_block=D_BLOCK), plant)
    return bench.run_bench(plant, loop, bench.ref_tracking, DUR, fs=FS,
                           seed=13, blocked=True)


def run_disturbance(plant: SeaPlant, cfg: MPCConfig) -> dict:
    loop = bench.SeaLoop(bench.make_mpc(plant.p, cfg, k_block=K_BLOCK,
                                        d_block=D_BLOCK), plant)
    dist = lambda t: 0.15 if t >= 1.5 else 0.0
    return bench.run_bench(plant, loop, bench.ref_hold, DUR, fs=FS,
                           dist_motor_fn=dist, seed=17, blocked=True)


def dist_metrics(rec: dict) -> dict:
    window = (rec["t"] >= 1.5) & (rec["t"] < 1.7)
    steady = (rec["t"] >= 1.9) & (rec["t"] < 2.2)
    err = np.abs(rec["tau_s_est"] - rec["tau_ref"])
    return {"peak_mNm": float(np.max(err[window]) * 1e3),
            "steady_mNm": float(np.mean(err[steady]) * 1e3)}


def main() -> None:
    plant = build_plant()
    p = plant.p
    print("=" * 74)
    print("4015 MPC design study")
    print("=" * 74)
    print(f"  Kt={p.Kt:.4f} Nm/A  R={p.R:.1f} ohm  L={p.L*1e3:.2f} mH  "
          f"Jm={p.Jm:.2e} kg m^2")
    print(f"  resonance f_res = {f_res(p):.1f} Hz "
          f"(T_res = {1/f_res(p)*1e3:.0f} ms = {1/f_res(p)/(0.5e-3):.0f} steps)")
    print(f"  practical current ceiling (SVPWM, 24 V) "
          f"~= {24.0/np.sqrt(3)/p.R:.2f} A "
          f"-> envelope {0.35/p.Kt:.2f} A at tau_max")
    print()

    grid = []
    for N in (20, 30, 40):
        for umax in (2.5, 3.0, 4.0):
            cfg = MPCConfig(N=N, u_max=umax)
            sm = metrics(run_smooth(plant, cfg))
            ed = metrics(run_edges(plant, cfg))
            grid.append((N, umax, sm, ed))
            print(f"  N={N:2d} u_max={umax:4.1f} | "
                  f"smooth RMS {sm['rms_mNm']:6.2f} max {sm['max_mNm']:6.2f} | "
                  f"edges RMS {ed['rms_mNm']:6.2f} max {ed['max_mNm']:6.2f}")

    # rank by smooth RMS, tie-break on edges max
    grid.sort(key=lambda g: (g[2]["rms_mNm"], g[3]["max_mNm"]))
    top = grid[:3]
    print("\n  top-3 by smooth RMS, disturbance check:")
    best = None
    for N, umax, sm, ed in top:
        dm = dist_metrics(run_disturbance(plant, MPCConfig(N=N, u_max=umax)))
        print(f"  N={N:2d} u_max={umax:4.1f} | smooth {sm['rms_mNm']:6.2f} | "
              f"edges max {ed['max_mNm']:6.2f} | disturb peak {dm['peak_mNm']:6.2f} "
              f"steady {dm['steady_mNm']:6.2f}")
        if best is None or (dm["steady_mNm"], dm["peak_mNm"]) < \
                (best["dm"]["steady_mNm"], best["dm"]["peak_mNm"]):
            best = dict(N=N, u_max=umax, sm=sm, ed=ed, dm=dm)

    out = {
        "motor": "QiuLovesYT 4015 BLDC + MT6701 encoder (hybrid build)",
        "as_built": {**P4015, "Jl": p.Jl, "ks": p.ks, "Vbus": p.Vbus,
                     "resonance_Hz": f_res(p),
                     "rated_torque_Nm": 0.3, "max_current_A": 4.0},
        "chosen_mpc": {"N": best["N"], "u_max": best["u_max"],
                       "Q_y": 3e4, "R_u": 5e-3, "S_rate": 0.3, "du_max": 1.5,
                       "T_s": 0.5e-3},
        "sweep_results": [{"N": N, "u_max": u, "smooth": sm, "edges": ed}
                          for N, u, sm, ed in
                          sorted(grid, key=lambda g: (g[2]["rms_mNm"],
                                                      g[3]["max_mNm"]))],
        "rationale": ("N covers ~30-45% of the ~33 ms resonance cycle (vs 18% "
                      "at N=20 for the old 18 Hz plant); u_max stays at or "
                      "above the 2.25 A the 0.35 N·m envelope needs, and below "
                      "the 4 A hardware limit so authority is matched, not "
                      "over-authoritative."),
    }
    os.makedirs("results", exist_ok=True)
    with open("results/params_4015.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  chosen config -> results/params_4015.json "
          f"(N={best['N']}, u_max={best['u_max']})")


if __name__ == "__main__":
    main()
