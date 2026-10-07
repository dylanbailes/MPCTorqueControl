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
    assert idp.rel_err["Jm"] < 0.10   # resonance-sweeping excitation + centering
    assert idp.rel_err["Jl"] < 0.15
    assert idp.rel_err["ks"] < 0.05


def test_inertia_identification_4015_high_resonance():
    """The 4015 build (Jm=3e-5 -> ~30 Hz resonance) must not regress the
    small-inertia conditioning: the chirp sweeps through the resonance, so
    Jm is identifiable from the band where it dominates.  (Before the
    excitation + conditioning fix this measured 76%.)"""
    p = PlantParams()
    p.R, p.L, p.Kt, p.Ke, p.Jm = 4.8, 2.6e-3, 0.1562, 0.1562, 3e-5
    plant = SeaPlant(p, dt=2e-5)
    ks, knl, _ = calibrate_spring(plant, duration=4.0)
    plant.obs_ks, plant.obs_knl = ks, knl
    data = collect_excitation(plant, duration=3.0, seed=3)
    idp = identify_from_data(data, p, ks=ks, knl=knl)
    assert idp.rel_err["Jm"] < 0.10
    assert idp.rel_err["Jl"] < 0.15
    assert idp.rel_err["ks"] < 0.05


def test_frequency_domain_jm_cross_check_matches_time_domain():
    """Jm from the resonance peak (frequency domain) must agree with the
    integrated-equation fit (time domain) — the cross-check corroborates
    the ID from independent physics.  Checked for both the 4015 (~30 Hz)
    and the nominal (~18 Hz) plants."""
    for jm in (3e-5, 8e-5):
        p = PlantParams()
        p.R, p.L, p.Kt, p.Ke, p.Jm = 4.8, 2.6e-3, 0.1562, 0.1562, jm
        plant = SeaPlant(p, dt=2e-5)
        ks, knl, _ = calibrate_spring(plant, duration=4.0)
        plant.obs_ks, plant.obs_knl = ks, knl
        data = collect_excitation(plant, duration=3.0, seed=3)
        idp = identify_from_data(data, p, ks=ks, knl=knl)
        assert idp.Jm_freq is not None          # peak found in band
        assert idp.f_res_hz is not None
        assert idp.fd_coherence is not None
        # each estimator is individually accurate ...
        assert abs(idp.Jm_freq - p.Jm) / p.Jm < 0.10
        assert abs(idp.Jm_td - p.Jm) / p.Jm < 0.10
        # ... and they agree with each other
        assert idp.fd_vs_td_rel_diff < 0.15
        # the fused Jm sits between the two unfused estimates ...
        lo, hi = sorted((idp.Jm_td, idp.Jm_freq))
        assert lo <= idp.Jm <= hi
        # ... and never does worse than the worse estimator (convexity:
        # the blend's error is bounded by the max of the two)
        err = lambda v: abs(v - p.Jm) / p.Jm
        assert err(idp.Jm) <= max(err(idp.Jm_td), err(idp.Jm_freq)) + 1e-12
        assert idp.rel_err["Jm"] < 0.10


def test_fusion_gracefully_degrades_without_prior():
    """If the frequency-domain prior is unavailable (peak missed / non-
    physical inversion), the ID falls back to the time-domain fit instead of
    failing — the fused path must not corrupt the result."""
    p = PlantParams()
    p.R, p.L, p.Kt, p.Ke, p.Jm = 4.8, 2.6e-3, 0.1562, 0.1562, 3e-5
    plant = SeaPlant(p, dt=2e-5)
    ks, knl, _ = calibrate_spring(plant, duration=4.0)
    plant.obs_ks, plant.obs_knl = ks, knl
    data = collect_excitation(plant, duration=3.0, seed=3)
    # force the prior to be unavailable by sweeping a band that excludes
    # the resonance entirely
    data_bad = dict(data)
    idp = identify_from_data(data_bad, p, ks=ks, knl=knl)
    # band with no peak -> no prior: simulate by monkeying the band arg
    import learn.system_id as sid
    orig = sid.estimate_resonance_jm
    sid.estimate_resonance_jm = lambda d, k, jl, **kw: {
        "f_res_hz": None, "Jm_freq": None, "coherence": None, "peaks": {}}
    try:
        idp_noprior = identify_from_data(data_bad, p, ks=ks, knl=knl)
    finally:
        sid.estimate_resonance_jm = orig
    assert idp_noprior.Jm_freq is None
    assert idp_noprior.Jm == idp_noprior.Jm_td        # pure time-domain fallback
    assert idp_noprior.jm_prior_weight == 0.0
    assert idp_noprior.rel_err["Jm"] < 0.10


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
