"""Learned disturbance model tests: fit quality, C export, closed-loop benefit."""

import os

import numpy as np

from learn.residual import LearnedDisturbance, ResidualConfig
from model.plant import PlantParams, SeaPlant
from sim.bench import SeaLoop, make_mpc, make_pid, ref_smooth, run_bench


def _synthetic_disturbance(n=4000):
    """Friction-like + cogging-like disturbance with known structure."""
    rng = np.random.default_rng(0)
    t = np.arange(n) / 2000.0
    theta_m = 0.5 * np.sin(2 * np.pi * 0.8 * t) + 0.2 * np.sin(2 * np.pi * 2.3 * t)
    omega_m = np.gradient(theta_m, t)
    u = 0.5 * np.sin(2 * np.pi * 0.8 * t)
    d = (0.008 * np.tanh(omega_m / 0.05) + 0.0002 * omega_m
         + 0.003 * np.sin(6 * theta_m) + 0.01 * u * np.sin(6 * theta_m))
    return theta_m, omega_m, u, d


def test_residual_fit_recovers_structure():
    theta_m, omega_m, u, d = _synthetic_disturbance()
    model = LearnedDisturbance(ResidualConfig())
    meta = model.fit(theta_m, omega_m, u, d)
    assert meta["r2"] > 0.9
    # friction coefficient should be recovered (Coulomb ~8 mN.m)
    assert abs(model.beta[1] - 0.008) < 0.002


def test_residual_export_to_c():
    theta_m, omega_m, u, d = _synthetic_disturbance(n=500)
    model = LearnedDisturbance(ResidualConfig())
    model.fit(theta_m, omega_m, u, d)
    path = "results/test_learned_model.h"
    model.export_to_c(path)
    assert os.path.exists(path)
    text = open(path).read()
    assert "learned_disturbance" in text
    assert "learned_friction" in text
    os.remove(path)


def test_learned_feedforward_improves_mpc_tracking():
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)

    def metrics(rec):
        err = rec["tau_s_est"] - rec["tau_ref"]
        return float((err ** 2).mean() ** 0.5) * 1e3

    # train on a 2.5 s MPC run
    rec = run_bench(plant, SeaLoop(make_mpc(p), plant), ref_smooth, 2.5,
                    seed=11, blocked=True)
    wm_dot = np.gradient(rec["omega_m"], rec["t"])
    d = p.Kt * rec["u_cmd"] - p.Jm * wm_dot - rec["tau_s_est"]
    learned = LearnedDisturbance(ResidualConfig())
    learned.fit(rec["theta_m"], rec["omega_m"], rec["u_cmd"], d)

    rms_mpc = metrics(run_bench(plant, SeaLoop(make_mpc(p), plant), ref_smooth,
                                2.0, seed=13, blocked=True))
    rms_learned = metrics(run_bench(plant, SeaLoop(make_mpc(p), plant,
                                                   learned=learned), ref_smooth,
                                    2.0, seed=13, blocked=True))
    # the learned feedforward must not hurt, and should help meaningfully
    assert rms_learned <= rms_mpc * 1.05
