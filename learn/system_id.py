"""System identification of the SEA plant from bench-style experiments.

Three procedures (mirroring what you do on the real bench in milestone M2):

1. **Spring calibration with an external torque reference.**  Hold the motor
   rotor in place with a stiff position loop, apply a dithered external
   torque to the output ("hanging weights"), and record (tau_ext, delta_theta)
   over many cycles.  Dithering averages out load friction, so a cubic fit
   on the (tau_ext, delta_theta) pairs yields (k_s, k_nl) accurately.  The
   fitted curve is what the torque observer uses:
   tau_s_hat = k_s * delta_theta + k_nl * delta_theta^3.

2. **Inertia/damping/friction (integrated least squares).**  With the spring
   curve known, the *integrated* equations of motion are linear in the
   remaining parameters:

       Jm * d(omega_m) = Kt * sum(iq) - bm * sum(omega_m)
                         - sum(tau_s_hat) - tau_c_m * sum(tanh(omega_m/eps))
       Jl * d(omega_l)  = sum(tau_s_hat) - bl * sum(omega_l)
                         - tau_c_l * sum(tanh(omega_l/eps))

   Integration (cumulative sums) is far more noise-robust than
   differentiating quantized encoder angles, which is the classic failure
   mode of naive least-squares ID on small-inertia rigs.

3. **Stribeck friction refinement** on the residuals for the momentum
   observer's friction estimate.

Velocities come from Savitzky-Golay differentiation of the *quantized*
encoder angles — the same approach used in firmware.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter

from model.plant import PlantParams, SeaPlant


def stribeck(w: np.ndarray, tc: float, tst: float, wst: float,
             bv: float, eps: float = 0.05) -> np.ndarray:
    s = np.tanh(w / eps)
    return (tc + (tst - tc) * np.exp(-(w / wst) ** 2)) * s + bv * w


class IdentifiedParams:
    def __init__(self):
        self.Jm = self.bm = self.Jl = self.bl = None
        self.ks = self.knl = None
        self.fric_m = None   # (tc, tst, wst, bv)
        self.fric_l = None
        self.rel_err: dict[str, float] = {}

    def friction_m(self, w: float) -> float:
        tc, tst, wst, bv = self.fric_m
        return float(stribeck(np.asarray(w, dtype=float), tc, tst, wst, bv))

    def friction_l(self, w: float) -> float:
        tc, tst, wst, bv = self.fric_l
        return float(stribeck(np.asarray(w, dtype=float), tc, tst, wst, bv))

    def __repr__(self) -> str:
        return (f"IdentifiedParams(Jm={self.Jm:.3e}, bm={self.bm:.3e}, "
                f"Jl={self.Jl:.3e}, bl={self.bl:.3e}, ks={self.ks:.3f}, "
                f"knl={self.knl:.3f}, fric_m={self.fric_m}, fric_l={self.fric_l})")


# ---------------------------------------------------------------------------
# 1. Spring calibration
# ---------------------------------------------------------------------------


def calibrate_spring(plant: SeaPlant, A: float = 0.2, f_dither: float = 0.5,
                     duration: float = 8.0, fs: int = 2000,
                     kp_hold: float = 30.0, kd_hold: float = 0.2,
                     u_hold_max: float = 6.0) -> tuple[float, float, dict]:
    """Calibrate (k_s, k_nl) by dithering an external torque against a held rotor.

    The motor is held at theta_m = 0 by a stiff PD position loop while a
    slowly oscillating external torque acts on the output.  The dither
    amplitude A must stay within the motor's holding torque (Kt * u_hold_max)
    or the rotor is dragged and the measurement is garbage.  At each instant
    tau_s ~= tau_ext (dither averages out load friction), so a cubic fit of
    tau_ext vs delta_theta recovers (k_s, k_nl).
    """
    n = int(duration * fs)
    t = np.arange(n) / fs
    tau_ext = A * np.sin(2 * np.pi * f_dither * t) + 0.15 * A * np.sin(2 * np.pi * 1.7 * f_dither * t)

    rng = np.random.default_rng(7)
    n_sub = max(1, int(1.0 / (fs * plant.dt)))
    plant.reset()
    theta_m, theta_l, tau_ext_rec, tau_s_true = [], [], [], []
    for k in range(n):
        obs = plant.observe(rng)
        # PD position hold on the motor (clamped to the current limit)
        u = float(np.clip(kp_hold * (0.0 - obs["theta_m"]) - kd_hold * obs["omega_m"],
                          -u_hold_max, u_hold_max))
        plant.step(u, tau_ext=tau_ext[k], n_steps=n_sub)
        theta_m.append(obs["theta_m"]); theta_l.append(obs["theta_l"])
        tau_ext_rec.append(tau_ext[k]); tau_s_true.append(plant.s.tau_s)

    theta_m = np.array(theta_m); theta_l = np.array(theta_l)
    delta = theta_m - theta_l
    tau_ext = np.array(tau_ext_rec)
    # linear fit first; adopt the cubic term only if it meaningfully helps
    Xl = np.column_stack([delta, np.ones_like(delta)])
    bl_, *_ = np.linalg.lstsq(Xl, tau_ext, rcond=None)
    lin_res = tau_ext - Xl @ bl_
    Xc = np.column_stack([delta, delta ** 3, np.ones_like(delta)])
    bc, *_ = np.linalg.lstsq(Xc, tau_ext, rcond=None)
    cub_res = tau_ext - Xc @ bc
    if np.sum(cub_res ** 2) < 0.8 * np.sum(lin_res ** 2):
        ks, knl = float(bc[0]), float(bc[1])
    else:
        ks, knl = float(bl_[0]), 0.0   # linear spring chosen
    data = {"t": t, "delta_theta": delta, "tau_ext": tau_ext,
            "tau_s_true": np.array(tau_s_true),
            "theta_m": theta_m, "theta_l": theta_l}
    return ks, knl, data


# ---------------------------------------------------------------------------
# 2. Excitation for inertia/friction ID
# ---------------------------------------------------------------------------


def collect_excitation(plant: SeaPlant, duration: float = 6.0,
                       fs: int = 2000, seed: int = 3) -> dict:
    """Chirp + PRBS + slow square current excitation (wide velocity range)."""
    rng = np.random.default_rng(seed)
    n = int(duration * fs)
    t = np.arange(n) / fs
    f0, f1 = 0.3, 10.0
    chirp = np.sin(2 * np.pi * (f0 * t + 0.5 * (f1 - f0) / duration * t ** 2))
    prbs = rng.normal(0.0, 0.25, n)
    square = 0.3 * np.sign(np.sin(2 * np.pi * 0.4 * t))
    u = np.clip(0.9 * chirp + prbs + square, -1.5, 1.5)

    rng2 = np.random.default_rng(7)
    n_sub = max(1, int(1.0 / (fs * plant.dt)))
    plant.reset()
    tm, tl, iq, tau_s, t_rec = [], [], [], [], []
    for k in range(n):
        plant.step(u[k], tau_ext=0.0, n_steps=n_sub)
        obs = plant.observe(rng2)
        tm.append(obs["theta_m"]); tl.append(obs["theta_l"])
        iq.append(plant.s.iq); tau_s.append(plant.s.tau_s)
        t_rec.append(plant.t)
    data = {"t": np.array(t_rec), "u": np.array(u),
            "theta_m": np.array(tm), "theta_l": np.array(tl),
            "iq": np.array(iq), "tau_s_true": np.array(tau_s)}
    data["omega_m"] = _vel(data["theta_m"], fs)
    data["omega_l"] = _vel(data["theta_l"], fs)
    return data


def _vel(ang: np.ndarray, fs: int) -> np.ndarray:
    w = min(31, (len(ang) - 1) | 1)
    return savgol_filter(np.unwrap(ang), window_length=w, polyorder=3, deriv=1) * fs


# ---------------------------------------------------------------------------
# 3. Inertia / damping / friction fit
# ---------------------------------------------------------------------------


def identify_from_data(data: dict, p: PlantParams,
                       ks: float, knl: float) -> IdentifiedParams:
    """Integrated-equation least squares for (J, b, tau_c) on both inertias."""
    out = IdentifiedParams()
    out.ks, out.knl = ks, knl

    t = data["t"]
    dt = t[1] - t[0]
    wm, wl = data["omega_m"], data["omega_l"]
    iq, u = data["iq"], data["u"]
    delta = data["theta_m"] - data["theta_l"]
    tau_s = ks * delta + knl * delta ** 3   # calibrated spring torque

    eps = 0.05

    # --- load side: Jl dwl = sum(tau_s) - bl sum(wl) - tau_c_l sum(tanh(wl/eps))
    Yl = np.cumsum(tau_s) * dt
    Xl = np.column_stack([wl - wl[0], np.cumsum(wl) * dt,
                          np.cumsum(np.tanh(wl / eps)) * dt])
    beta_l, *_ = np.linalg.lstsq(Xl, Yl, rcond=None)
    out.Jl, out.bl = float(beta_l[0]), float(beta_l[1])
    out.fric_l = (float(beta_l[2]), 0.0, 1.0, 0.0)

    # --- motor side: Jm dwm = Kt sum(iq) - bm sum(wm) - sum(tau_s) - tau_c_m sum(tanh)
    Y = p.Kt * np.cumsum(iq) * dt - np.cumsum(tau_s) * dt
    X = np.column_stack([wm - wm[0], np.cumsum(wm) * dt,
                         np.cumsum(np.tanh(wm / eps)) * dt])
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    out.Jm, out.bm = float(beta[0]), float(beta[1])
    out.fric_m = (float(beta[2]), 0.0, 1.0, 0.0)

    # --- Stribeck refinement on residuals (for the momentum observer)
    wm_dot = np.gradient(wm, t)
    wl_dot = np.gradient(wl, t)
    res_m = p.Kt * iq - out.Jm * wm_dot - out.bm * wm - tau_s
    res_l = tau_s - out.Jl * wl_dot - out.bl * wl

    def fit_stribeck(w: np.ndarray, r: np.ndarray, p0, bounds):
        mask = np.abs(w) > 0.02
        if mask.sum() < 50:
            return tuple(p0)
        try:
            popt, _ = curve_fit(
                lambda ww, tc, tst, wst, bv: stribeck(ww, tc, tst, wst, bv),
                w[mask], r[mask], p0=p0, bounds=bounds, maxfev=8000)
            return tuple(float(v) for v in popt)
        except (RuntimeError, ValueError):
            return tuple(p0)

    out.fric_m = fit_stribeck(wm, res_m, (5e-3, 8e-3, 0.5, 1e-4),
                              ([1e-4, 1e-4, 0.05, 0], [0.1, 0.1, 5.0, 1e-2]))
    out.fric_l = fit_stribeck(wl, res_l, (3e-3, 5e-3, 0.4, 1e-4),
                              ([1e-4, 1e-4, 0.05, 0], [0.1, 0.1, 5.0, 1e-2]))

    out.rel_err = {
        "Jm": abs(out.Jm - p.Jm) / p.Jm,
        "bm": abs(out.bm - p.bm) / p.bm,
        "Jl": abs(out.Jl - p.Jl) / p.Jl,
        "bl": abs(out.bl - p.bl) / p.bl,
        "ks": abs(out.ks - p.ks) / p.ks,
        "knl": abs(out.knl - p.knl) / max(abs(p.knl), 1e-9),
    }
    return out


def identify(plant: SeaPlant, p: PlantParams, duration: float = 6.0,
             fs: int = 2000, seed: int = 3) -> tuple[IdentifiedParams, dict]:
    """Full pipeline: spring calibration, then inertia/friction fit."""
    ks, knl, _ = calibrate_spring(plant, fs=fs)
    data = collect_excitation(plant, duration=duration, fs=fs, seed=seed)
    return identify_from_data(data, p, ks=ks, knl=knl), data
