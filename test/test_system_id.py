"""System ID tests: spring calibration and inertia/friction recovery."""

import numpy as np

from learn.system_id import calibrate_spring, collect_excitation, identify_from_data
from model.plant import PlantParams, SeaPlant


def test_spring_calibration_recovers_stiffness():
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)
    ks, knl, _ = calibrate_spring(plant, duration=4.0)
    assert abs(ks - p.ks) / p.ks < 0.05
    assert abs(knl) < 0.2


def test_inertia_identification():
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)
    ks, knl, _ = calibrate_spring(plant, duration=4.0)
    plant.obs_ks, plant.obs_knl = ks, knl
    data = collect_excitation(plant, duration=3.0, seed=3)
    idp = identify_from_data(data, p, ks=ks, knl=knl)
    assert idp.rel_err["Jm"] < 0.40
    assert idp.rel_err["Jl"] < 0.15
    assert idp.rel_err["ks"] < 0.05


def test_friction_model_is_bounded():
    p = PlantParams()
    plant = SeaPlant(p, dt=2e-5)
    ks, knl, _ = calibrate_spring(plant, duration=3.0)
    data = collect_excitation(plant, duration=2.0, seed=3)
    idp = identify_from_data(data, p, ks=ks, knl=knl)
    for w in (-5.0, -1.0, 0.5, 3.0):
        f = idp.friction_m(w)
        assert abs(f) < 0.05  # friction magnitude stays sane
        assert np.sign(f) == np.sign(w) or abs(w) < 0.1
