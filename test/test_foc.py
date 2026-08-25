"""FOC math tests (Clarke/Park/SVPWM)."""

import numpy as np

from model.foc import clarke, park, inv_park, svpwm, mechanical_to_electrical


def test_park_clarke_round_trip():
    # balanced three-phase currents with ia+ib+ic=0
    ia, ib = 1.0, -0.4
    ic = -ia - ib
    theta_e = 0.7
    i_alpha, i_beta = clarke(ia, ib, ic)
    i_d, i_q = park(i_alpha, i_beta, theta_e)
    # q-axis should carry the bulk of the current for this alignment
    assert abs(i_q) > 0.5
    # round trip through inverse park
    a, b = inv_park(i_d, i_q, theta_e)
    assert abs(a - i_alpha) < 1e-9
    assert abs(b - i_beta) < 1e-9


def test_park_rotation_is_unitary():
    # the (d, q) frame preserves the vector magnitude
    i_alpha, i_beta = 0.8, 0.6
    for theta_e in (0.0, 1.1, 5.9):
        i_d, i_q = park(i_alpha, i_beta, theta_e)
        assert abs(np.hypot(i_d, i_q) - 1.0) < 1e-9


def test_svpwm_duty_cycle_bounds():
    for v_alpha, v_beta in [(0.0, 0.0), (5.0, 0.0), (-5.0, 5.0), (3.0, -4.0)]:
        d_a, d_b, d_c = svpwm(v_alpha, v_beta, v_max=13.86)
        assert 0.0 <= d_a <= 1.0 and 0.0 <= d_b <= 1.0 and 0.0 <= d_c <= 1.0


def test_svpwm_zero_vector_gives_half_duty():
    d_a, d_b, d_c = svpwm(0.0, 0.0, v_max=13.86)
    assert abs(d_a - 0.5) < 1e-9 and abs(d_b - 0.5) < 1e-9 and abs(d_c - 0.5) < 1e-9


def test_mechanical_to_electrical():
    assert abs(mechanical_to_electrical(0.0, 7) - 0.0) < 1e-9
    assert abs(mechanical_to_electrical(2 * np.pi / 7, 7)) < 1e-6
