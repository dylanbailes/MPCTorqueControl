"""Regression checks for controller state and augmentation limits."""

import numpy as np
import pytest

from learn.residual import LearnedDisturbance, ResidualConfig, _lagged
from model.impedance import ImpedanceSafety
from model.mpc import MPCConfig
from model.pid import PidTorqueController
from model.plant import PlantParams, SeaPlant
from sim.bench import SeaLoop, make_mpc
from sim.bench import make_pid, ref_zero, run_bench


@pytest.mark.parametrize("solver", ["admm", "pg"])
def test_mpc_reset_replays_identical_commands(solver):
    ctrl = make_mpc(PlantParams(), MPCConfig(solver=solver))
    states = np.random.default_rng(42).normal(0, 0.01, (12, 4))
    first = [ctrl.step(x, 0.1) for x in states]
    ctrl.reset()
    second = [ctrl.step(x, 0.1) for x in states]
    np.testing.assert_allclose(second, first, atol=1e-12)


def test_pid_reset_clears_derivative_state():
    ctrl = PidTorqueController()
    first = [ctrl.step(ref, 0.0, 0.0005) for ref in (0.2, -0.1, 0.0)]
    ctrl.reset()
    second = [ctrl.step(ref, 0.0, 0.0005) for ref in (0.2, -0.1, 0.0)]
    np.testing.assert_allclose(second, first)


def test_impedance_reset_preserves_friction_configuration():
    imp = ImpedanceSafety()
    imp.set_friction_model(lambda omega: 0.02)
    imp.update_observer(0.02, 0.0, 0.0, 0.0005)
    imp.coll.detected = True
    imp.reset()
    assert not imp.coll.detected
    assert imp.update_observer(0.02, 0.0, 0.0, 0.0005) == 0.0


def test_augmentation_shares_current_limit_and_updates_mpc_history():
    plant = SeaPlant()
    ctrl = make_mpc(plant.p, MPCConfig(u_max=0.3))
    loop = SeaLoop(ctrl, plant, friction_ff=lambda omega: 10.0)
    obs = plant.observe(np.random.default_rng(0))
    applied = loop.update(0.0, obs, 0.5, 0.0005)
    assert applied == 0.3
    assert ctrl.u_prev == applied


@pytest.mark.parametrize("lag", [0, 2, 4])
def test_residual_online_features_match_batch_prediction(lag):
    model = LearnedDisturbance(ResidualConfig(lag=lag, u_ff_max=100.0))
    model.beta = np.arange(9 + 2 * lag) * 0.001
    theta, omega, u = np.random.default_rng(7).normal(0, 0.1, (3, 8))
    batch = model.predict(theta, omega, u)
    online = [model.feedforward(t, w, command, 1.0)
              for t, w, command in zip(theta, omega, u)]
    np.testing.assert_allclose(online, batch, atol=1e-12)


def test_short_trajectory_lags_keep_sample_count():
    lagged = _lagged(np.array([2.0]), 3)
    assert all(len(values) == 1 for values in lagged)
    assert all(values[0] == 0.0 for values in lagged)


def test_impedance_benchmark_records_actual_torque_reference():
    plant = SeaPlant()
    imp = ImpedanceSafety()
    loop = SeaLoop(make_pid(), plant, impedance=imp)
    rec = run_bench(plant, loop, ref_zero, 0.01, theta_d=0.5)
    expected = (imp.cfg.k_imp * (0.5 - rec["theta_l"])
                - imp.cfg.b_imp * rec["omega_l"])
    np.testing.assert_allclose(rec["tau_ref"], expected)
