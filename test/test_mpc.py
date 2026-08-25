"""MPC tests: condensation consistency, constraint satisfaction."""

import numpy as np

from model.mpc import LinearSeaModel, MPCConfig, SeaMPC
from model.plant import PlantParams


def _model():
    p = PlantParams()
    return LinearSeaModel(p.Jm, p.bm, p.Jl, p.bl, p.ks, p.Kt, 0.5e-3, k_block=0.0)


def test_condensation_predicts_correctly():
    """The condensed prediction Y = Cx F x0 + Cx G U must match a rollout."""
    model = _model()
    N = 12
    F, G, Cx = model.condense(N)
    rng = np.random.default_rng(0)
    x0 = rng.normal(size=model.nx) * 0.1
    U = rng.normal(size=N) * 0.5
    Y_cond = Cx @ (F @ x0 + G @ U)
    # rollout the discrete model directly (output after each input is applied)
    x = x0.copy()
    Y_roll = []
    for u in U:
        x = model.Ad @ x + model.Bd.reshape(-1) * u
        Y_roll.append((model.Cd @ x)[0])
    assert np.max(np.abs(Y_cond - np.array(Y_roll))) < 1e-9


def test_mpc_respects_input_and_slew_constraints():
    p = PlantParams()
    cfg = MPCConfig(N=12)
    mpc = SeaMPC(_model(), cfg)
    rng = np.random.default_rng(1)
    for _ in range(50):
        x0 = rng.normal(size=4) * 0.1
        u = mpc.step(x0, 0.3)
        assert abs(u) <= cfg.u_max + 1e-9
        assert abs(u - mpc.u_prev) <= cfg.du_max + 1e-9 or _ == 0
    # slew limit after a large previous input
    mpc.u_prev = 4.0
    u = mpc.step(np.zeros(4), 0.3)
    assert abs(u - 4.0) <= cfg.du_max + 1e-9


def test_mpc_tracks_constant_reference_on_linear_plant():
    """On the *linear* model, MPC should drive torque to the reference."""
    p = PlantParams()
    mpc = SeaMPC(_model(), MPCConfig())
    x = np.zeros(4)
    for _ in range(500):
        x = mpc.model.Ad @ x + mpc.model.Bd.reshape(-1) * mpc.step(x, 0.25)
    y = mpc.model.Cd @ x
    assert abs(y[0] - 0.25) < 0.01


def test_hessian_is_positive_definite():
    mpc = SeaMPC(_model(), MPCConfig())
    w, _ = np.linalg.eigh(mpc.H)
    assert w.min() > 0
