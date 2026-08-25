"""Field-Oriented Control (FOC) math — reference implementation.

This module is the Python twin of `firmware/Core/Src/foc.c`.  It contains the
transforms and PWM generation used by the current loop:

    Clarke : (ia, ib, ic) -> (i_alpha, i_beta)
    Park   : (i_alpha, i_beta, theta_e) -> (i_d, i_q)
    inv Park + SVPWM: (v_d, v_q, theta_e) -> duty cycles

The digital-twin plant uses a lumped q-axis current loop; these functions are
kept here so the firmware math is unit-testable before it runs on hardware.
"""

from __future__ import annotations

import numpy as np

SQRT3 = np.sqrt(3.0)
SQRT3_2 = SQRT3 / 2.0


def clarke(ia: float, ib: float, ic: float) -> tuple[float, float]:
    """Three-phase currents -> stationary (alpha, beta)."""
    i_alpha = ia
    i_beta = (ia + 2.0 * ib) / SQRT3  # from ib - (ia+ic)/2, with ia+ib+ic=0
    return i_alpha, i_beta


def park(i_alpha: float, i_beta: float, theta_e: float) -> tuple[float, float]:
    """Stationary (alpha, beta) -> rotating (d, q) at electrical angle theta_e."""
    c, s = np.cos(theta_e), np.sin(theta_e)
    i_d = c * i_alpha + s * i_beta
    i_q = -s * i_alpha + c * i_beta
    return i_d, i_q


def inv_park(v_d: float, v_q: float, theta_e: float) -> tuple[float, float]:
    """Rotating (d, q) -> stationary (alpha, beta)."""
    c, s = np.cos(theta_e), np.sin(theta_e)
    v_alpha = c * v_d - s * v_q
    v_beta = s * v_d + c * v_q
    return v_alpha, v_beta


def svpwm(v_alpha: float, v_beta: float, v_max: float) -> tuple[float, float, float]:
    """Space-vector PWM: (v_alpha, v_beta) -> duty cycles (0..1) per phase.

    Uses the min/max centering (equivalent to the standard SVPWM zero-vector
    placement) so the linear modulation range is |v| <= v_max = Vbus/sqrt(3).
    """
    va, vb, vc = v_alpha, -0.5 * v_alpha + SQRT3_2 * v_beta, -0.5 * v_alpha - SQRT3_2 * v_beta
    vmin = min(va, vb, vc)
    vmax = max(va, vb, vc)
    offset = 0.5 * (vmax + vmin)
    va, vb, vc = va - offset, vb - offset, vc - offset
    # normalize to duty 0..1 with v_max mapping to (1 - deadtime) roughly
    d_a = 0.5 + 0.5 * np.clip(va / v_max, -1.0, 1.0)
    d_b = 0.5 + 0.5 * np.clip(vb / v_max, -1.0, 1.0)
    d_c = 0.5 + 0.5 * np.clip(vc / v_max, -1.0, 1.0)
    return d_a, d_b, d_c


def mechanical_to_electrical(theta_m: float, pole_pairs: int) -> float:
    """Mechanical rotor angle -> electrical angle (mod 2*pi)."""
    return (pole_pairs * theta_m) % (2.0 * np.pi)
