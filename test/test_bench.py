"""End-to-end bench tests: MPC beats PID; collision detection + give-way."""

import numpy as np

from model.impedance import ImpedanceConfig, ImpedanceSafety
from model.plant import PlantParams, SeaPlant
from sim.bench import SeaLoop, make_mpc, make_pid, ref_smooth, ref_zero, run_bench


def _rms(rec, settle_frac=0.5):
    err = rec["tau_s_est"] - rec["tau_ref"]
    return float((err[int(settle_frac * len(err)):] ** 2).mean() ** 0.5) * 1e3


def test_mpc_beats_pid_on_smooth_tracking():
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)
    rms_pid = _rms(run_bench(plant, SeaLoop(make_pid(), plant), ref_smooth, 2.5,
                             seed=13, blocked=True))
    rms_mpc = _rms(run_bench(plant, SeaLoop(make_mpc(p), plant), ref_smooth, 2.5,
                             seed=13, blocked=True))
    assert rms_mpc < 0.5 * rms_pid


def test_collision_detection_and_give_way():
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)
    imp = ImpedanceSafety(ImpedanceConfig())
    loop = SeaLoop(make_pid(), plant, impedance=imp)
    rec = run_bench(plant, loop, ref_zero, 2.0, theta_d=0.5,
                    grab=(0.1, 2000.0, 5.0), seed=5)
    assert rec["collision"].any()
    det_t = rec["t"][np.argmax(rec["collision"])]
    assert det_t - 0.1 < 0.6                     # detection within 0.6 s
    post = rec["u_cmd"][rec["collision"] > 0]
    assert np.all(np.abs(post) < 1e-6)           # actuator gives way (u -> 0)
    # peak torque stays bounded well below the motor limit
    assert np.abs(rec["tau_s_est"]).max() < 0.5


def test_no_false_collision_during_normal_motion():
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)
    imp = ImpedanceSafety(ImpedanceConfig())
    loop = SeaLoop(make_pid(), plant, impedance=imp)
    rec = run_bench(plant, loop, ref_zero, 1.5, theta_d=0.5, seed=5)
    assert not rec["collision"].any()
