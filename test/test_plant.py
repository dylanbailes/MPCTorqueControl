"""Plant model tests: spring torque, friction, current loop, observer, block."""

import numpy as np

from model.plant import PlantParams, SeaPlant


def test_static_spring_torque():
    p = PlantParams()
    plant = SeaPlant(p)
    plant.reset(theta_m=0.4, theta_l=0.1)
    expected = p.ks * 0.3 + p.knl * 0.3 ** 3
    assert abs(plant.spring_torque(0.4, 0.1) - expected) < 1e-12


def test_friction_opposes_motion():
    p = PlantParams()
    plant = SeaPlant(p)
    assert plant._friction(1.0, p.tau_c_m, p.tau_st_m, p.w_st_m, p.bv_m) > 0
    assert plant._friction(-1.0, p.tau_c_m, p.tau_st_m, p.w_st_m, p.bv_m) < 0
    assert abs(plant._friction(0.0, p.tau_c_m, p.tau_st_m, p.w_st_m, p.bv_m)) < 1e-9


def test_current_loop_tracks_step():
    plant = SeaPlant(PlantParams(), dt=2e-5)
    plant.reset()
    plant.step(3.0, n_steps=500)  # 10 ms
    assert abs(plant.s.iq - 3.0) < 0.05


def test_current_loop_saturates_at_bus_voltage():
    plant = SeaPlant(PlantParams(), dt=2e-5)
    plant.reset()
    plant.step(50.0, n_steps=500)
    # steady-state current limited by Vbus/sqrt(3) / R
    assert plant.s.iq < plant.p.Vbus / np.sqrt(3.0) / plant.p.R + 0.5


def test_observer_uses_calibrated_spring():
    plant = SeaPlant(PlantParams(), dt=2e-5)
    plant.obs_ks = 0.9
    plant.obs_knl = 0.05
    plant.reset(theta_m=0.3, theta_l=0.1)
    rng = np.random.default_rng(0)
    obs = plant.observe(rng)
    d = obs["theta_m"] - obs["theta_l"]
    expected = 0.9 * d + 0.05 * d ** 3
    assert abs(obs["tau_s_est"] - expected) < 1e-3


def test_blocked_output_stable():
    plant = SeaPlant(PlantParams(), dt=2e-5)
    plant.set_blocked_output(1e4, 50.0)
    plant.reset()
    for _ in range(500):
        plant.step(0.0, n_steps=25)  # 0.25 s
    assert abs(plant.s.theta_l) < 1e-3
    assert np.isfinite(plant.s.theta_m)


def test_wall_pins_load():
    plant = SeaPlant(PlantParams(), dt=2e-5)
    plant.set_wall(0.2, 2000.0, 5.0)
    plant.reset(theta_m=0.0, theta_l=0.3)
    plant.s.omega_l = 5.0
    for _ in range(200):
        plant.step(0.0, n_steps=25)
    assert plant.s.theta_l <= 0.2 + 1e-3
    assert abs(plant.s.omega_l) < 0.5
