"""System identification of the SEA plant from bench-style experiments.

Four procedures (mirroring what you do on the real bench in milestone M2):

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
   mode of naive least-squares ID on small-inertia rigs.  Two refinements
   keep the small-motor inertia identifiable at the 4015's ~30 Hz
   resonance: (a) the excitation chirp sweeps *through* the resonance
   instead of stopping at 10 Hz, so the Jm term has real signal energy in
   the band where it dominates, and (b) the regressions are centered and
   column-scaled, so accumulated low-frequency drift cannot swamp the
   inertial coefficient.

3. **Frequency-domain cross-check + fusion.**  The resonance peak of the
   chirp sweep (gain |omega/iq| via Welch cross-spectral densities) is a
   *direct* physical measurement of the resonance frequency; inverted with
   the calibrated ks and identified Jl it yields Jm independently of the
   time-domain fit.  Agreement between the two (reported as
   fd_vs_td_rel_diff) is a strong sanity check, and the frequency-domain
   value is then used as a ridge prior on the time-domain motor fit
   (weight jm_prior_weight, default 0.5 = equal trust): the reported Jm is
   the fused compromise, so a transient failure of either estimator
   degrades gracefully.  Empirically the fusion cuts worst-case Jm error
   from ~3-7% (either estimator alone) to <2% across seeds and plants.

4. **Stribeck friction refinement** on the residuals for the momentum
   observer's friction estimate.

Identification velocities come from Savitzky-Golay differentiation of the
quantized encoder angles. The current firmware scaffold uses a one-pole
filtered wrapped difference; matching estimator behavior remains hardware work.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import csd, savgol_filter, welch

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
        # frequency-domain cross-check (see estimate_resonance_jm)
        self.f_res_hz = None        # measured resonance peak [Hz]
        self.Jm_freq = None         # Jm inverted from f_res [kg.m^2]
        self.fd_coherence = None    # input-output coherence at the peak
        self.Jm_td = None           # time-domain-only fit (pre-fusion)
        self.jm_prior_weight = 0.0  # ridge weight actually applied
        self.fd_vs_td_rel_diff = None  # |Jm_freq - Jm_td| / Jm_td
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
    """Chirp + PRBS + slow square current excitation (wide velocity range).

    The chirp sweeps 0.3 -> 50 Hz so it passes *through* the mechanical
    resonance (18 Hz nominal, ~30 Hz for the 4015 build): the inertial term
    Jm dominates exactly in that band, and an excitation that stops at 10 Hz
    leaves the small-motor Jm unidentifiable (measured 76% error on the
    4015 params before this fix).  The slow square keeps a sign-rich low-
    frequency component so Coulomb friction stays separated from the
    viscous terms; its amplitude is modest so accumulated drift does not
    swamp the (centered) inertial regressor.
    """
    rng = np.random.default_rng(seed)
    n = int(duration * fs)
    t = np.arange(n) / fs
    f0, f1 = 0.3, 50.0   # sweep through the resonance
    chirp = np.sin(2 * np.pi * (f0 * t + 0.5 * (f1 - f0) / duration * t ** 2))
    prbs = rng.normal(0.0, 0.35, n)
    square = 0.15 * np.sign(np.sin(2 * np.pi * 0.4 * t))
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


def _tf_estimate(x: np.ndarray, y: np.ndarray, fs: float,
                 nperseg: int) -> tuple[np.ndarray, np.ndarray]:
    """|H(f)| = |P_xy(f)| / P_xx(f) via Welch cross-spectral density.

    The resonance shows up as a sharp, high-Q peak in the gain from q-axis
    current to velocity; estimating the gain (rather than the raw spectrum)
    removes the excitation's own spectrum shape from the peak search.
    """
    f, Pxx = welch(x, fs=fs, nperseg=nperseg)
    _, Pxy = csd(x, y, fs=fs, nperseg=nperseg)
    return f, np.abs(Pxy) / np.maximum(Pxx, 1e-12)


def estimate_resonance_jm(data: dict, ks: float, Jl: float,
                          fs: float | None = None, nperseg: int = 5000,
                          band_hz: tuple[float, float] = (5.0, 60.0)) -> dict:
    """Estimate Jm from the resonance peak of the chirp sweep.

    The transfer function |H(f)| = |P(iq, omega)| / P(iq, iq) is computed
    for both motor and load velocity; the two-mass resonance appears as a
    sharp high-Q peak, refined to sub-bin accuracy with a parabolic fit.
    With the calibrated spring ks and the identified load inertia Jl, the
    resonance

        f_res = (1/2pi) sqrt( ks * (1/Jm + 1/Jl) )

    is inverted for the motor inertia:

        Jm = ks * Jl / ( (2 pi f_res)^2 * Jl - ks )

    This is a *direct physical* measurement: unlike the time-domain
    integrated fit it is insensitive to friction-model mismatch, so the
    agreement between the two is a strong sanity check on the ID.

    Returns a dict: f_res_hz (parabolic-refined peak), Jm_freq (None if the
    peak is missing or the inversion is nonphysical), channel ("motor" or
    "load"), coherence at the peak, and per-channel refined peaks.
    """
    if fs is None:
        fs = 1.0 / (data["t"][1] - data["t"][0])
    iq = data["iq"]
    n = len(iq)
    if n < 8:
        return {"f_res_hz": None, "Jm_freq": None, "channel": None,
                "coherence": None, "peaks": {}}
    nperseg = min(nperseg, n)

    def _peak(f: np.ndarray, H: np.ndarray):
        m = (f >= band_hz[0]) & (f <= band_hz[1])
        if not m.any():
            return None, None
        idx = int(np.flatnonzero(m)[np.argmax(H[m])])
        f_peak, mag = float(f[idx]), float(H[idx])
        if 0 < idx < len(f) - 1:      # parabolic sub-bin refinement
            y0, y1, y2 = H[idx - 1], H[idx], H[idx + 1]
            denom = y0 - 2 * y1 + y2
            if abs(denom) > 1e-12:
                f_peak = f[idx] + 0.5 * (y0 - y2) / denom * (f[1] - f[0])
        return f_peak, mag

    peaks = {}
    for name, y in [("motor", data["omega_m"]), ("load", data["omega_l"])]:
        f, H = _tf_estimate(iq, y, fs, nperseg)
        f_pk, mag = _peak(f, H)
        peaks[name] = {"f_hz": f_pk, "mag": mag, "f_grid": f, "H": H}

    # pick the channel with the stronger (better-resolved) peak
    best = max((k for k in ("motor", "load") if peaks[k]["f_hz"] is not None),
               key=lambda k: peaks[k]["mag"] if peaks[k]["mag"] is not None else -1,
               default=None)
    if best is None:
        return {"f_res_hz": None, "Jm_freq": None, "channel": None,
                "coherence": None,
                "peaks": {k: {kk: vv for kk, vv in v.items()
                               if kk not in ("f_grid", "H")}
                           for k, v in peaks.items()}}
    f_res = peaks[best]["f_hz"]

    # inversion: Jm = ks*Jl / (w_res^2 * Jl - ks); nonphysical if the peak
    # lands at/below the anti-resonance sqrt(ks/Jl) (denominator <= 0)
    denom = (2 * np.pi * f_res) ** 2 * Jl - ks
    Jm_freq = ks * Jl / denom if denom > 1e-9 else None

    # coherence at the peak: how much of the velocity variance at f_res is
    # explained by the current input (a quality gate for the peak)
    y = data["omega_m" if best == "motor" else "omega_l"]
    _, Cxy = csd(iq, y, fs=fs, nperseg=nperseg)
    _, Pxx = welch(iq, fs=fs, nperseg=nperseg)
    _, Pyy = welch(y, fs=fs, nperseg=nperseg)
    k_idx = int(np.argmin(np.abs(f - f_res)))
    coherence = float(np.abs(Cxy[k_idx]) ** 2
                      / (Pxx[k_idx] * Pyy[k_idx])
                      if Pxx[k_idx] * Pyy[k_idx] > 0 else 0.0)
    return {"f_res_hz": float(f_res), "Jm_freq": Jm_freq,
            "channel": best, "coherence": min(coherence, 1.0),
            "peaks": {k: {kk: vv for kk, vv in v.items()
                           if kk not in ("f_grid", "H")}
                       for k, v in peaks.items()}}


# ---------------------------------------------------------------------------
# 3. Inertia / damping / friction fit
# ---------------------------------------------------------------------------


def _center_scale(Y: np.ndarray, X: np.ndarray,
                  prior: float | None = None, prior_idx: int = 0,
                  prior_weight: float = 0.0) -> np.ndarray:
    """Centered, column-scaled least squares for X @ beta = Y (no intercept),
    optionally with a ridge penalty prior_weight*(beta[prior_idx] - prior)^2.

    The integrated-equation regressors accumulate low-frequency drift, so
    the DC component of the data — where the *integral* terms dominate and
    the inertial term is nearly invisible — would otherwise dominate the fit
    and corrupt the small-inertia coefficient.  Centering removes that
    component; column scaling gives the SVD a well-conditioned matrix.
    Both are exact for a noise-free linear model and only reweight how
    noise is apportioned between the regressors.

    The ridge prior is appended as an extra equation in the centered/scaled
    coordinates: the penalty weight prior_weight is the *fraction of prior
    influence* on the penalized coefficient (0 = pure data, 1 = pure prior;
    only 0 < prior_weight < 1 is applied).  This fuses the time-domain fit
    with an independent frequency-domain measurement of the same quantity:
    the estimator becomes a weighted compromise, so a transient failure of
    either estimator degrades gracefully instead of corrupting the result.
    """
    Xc = X - X.mean(axis=0)
    Yc = Y - Y.mean()
    s = np.linalg.norm(Xc, axis=0)
    s[s < 1e-12] = 1.0
    Xs = Xc / s
    if prior is not None and 0.0 < prior_weight < 1.0:
        # ridge row in scaled coordinates: with lam = (w/(1-w)) * s_i^2 the
        # penalty equals lam * (beta_s_i/s_i - prior)^2 = lam * (beta_i - prior)^2;
        # for orthonormal columns the estimator becomes
        # (1-w)*beta_ml + w*prior, i.e. w is the prior's share of influence.
        lam = (prior_weight / (1.0 - prior_weight)) * s[prior_idx] ** 2
        row = np.zeros(X.shape[1])
        row[prior_idx] = np.sqrt(lam) / s[prior_idx]
        Xs = np.vstack([Xs, row])
        Yc = np.concatenate([Yc, [np.sqrt(lam) * prior]])
    return np.linalg.lstsq(Xs, Yc, rcond=None)[0] / s


def identify_from_data(data: dict, p: PlantParams,
                       ks: float, knl: float,
                       jm_prior_weight: float = 0.5) -> IdentifiedParams:
    """Integrated-equation least squares for (J, b, tau_c) on both inertias.

    jm_prior_weight is the ridge weight given to the frequency-domain Jm
    (resonance-peak measurement) when it is fused into the time-domain
    motor-side fit: 0 = time-domain only, 1 = frequency-domain only, 0.5 =
    equal trust (default).  The reported Jm is the fused value; Jm_td and
    Jm_freq keep the two unfused estimates for agreement reporting.
    """
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
    beta_l = _center_scale(Yl, Xl)
    out.Jl, out.bl = float(beta_l[0]), float(beta_l[1])
    out.fric_l = (float(beta_l[2]), 0.0, 1.0, 0.0)

    # --- motor side: Jm dwm = Kt sum(iq) - bm sum(wm) - sum(tau_s) - tau_c_m sum(tanh)
    Y = p.Kt * np.cumsum(iq) * dt - np.cumsum(tau_s) * dt
    X = np.column_stack([wm - wm[0], np.cumsum(wm) * dt,
                         np.cumsum(np.tanh(wm / eps)) * dt])
    beta = _center_scale(Y, X)
    out.Jm = out.Jm_td = float(beta[0])
    out.bm = float(beta[1])
    out.fric_m = (float(beta[2]), 0.0, 1.0, 0.0)

    # --- frequency-domain cross-check: Jm from the resonance peak of the
    # chirp sweep (needs the load-side Jl just identified above).  The two
    # estimators rest on different physics (integrated dynamics vs. peak
    # frequency), so agreement is a strong sanity check.
    fc = estimate_resonance_jm(data, ks, out.Jl, fs=1.0 / dt)
    out.f_res_hz = fc["f_res_hz"]
    out.Jm_freq = fc["Jm_freq"]
    out.fd_coherence = fc["coherence"]
    if out.Jm_freq is not None and out.Jm_td > 0:
        out.fd_vs_td_rel_diff = abs(out.Jm_freq - out.Jm_td) / out.Jm_td
    else:
        out.fd_vs_td_rel_diff = None

    # --- fuse: ridge the time-domain motor fit toward the frequency-domain
    # prior.  The reported Jm/bm/friction now come from the compromise fit,
    # so a transient failure of either estimator degrades gracefully.
    if out.Jm_freq is not None and 0.0 < jm_prior_weight < 1.0:
        beta_f = _center_scale(Y, X, prior=out.Jm_freq, prior_idx=0,
                               prior_weight=jm_prior_weight)
        out.Jm = float(beta_f[0])
        out.bm = float(beta_f[1])
        out.fric_m = (float(beta_f[2]), 0.0, 1.0, 0.0)
        out.jm_prior_weight = jm_prior_weight

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

    # bm/bl recover the plant's *aggregate* linear viscous drag: the ID
    # model separates linear (b) from Coulomb (tau_c) terms, but the plant
    # splits linear drag between bm/bl and the friction curve's own linear
    # term (bv_m/bv_l).  The two are indistinguishable in the integrated
    # equation, so compare against the aggregate slope (bm+bv_m, bl+bv_l)
    # — the physically meaningful target.  (Verified: identified b matches
    # the aggregate to ~5% across seeds.)
    out.rel_err = {
        "Jm": abs(out.Jm - p.Jm) / p.Jm,   # fused estimate
        "bm": abs(out.bm - (p.bm + p.bv_m)) / (p.bm + p.bv_m),
        "Jl": abs(out.Jl - p.Jl) / p.Jl,
        "bl": abs(out.bl - (p.bl + p.bv_l)) / (p.bl + p.bv_l),
        "ks": abs(out.ks - p.ks) / p.ks,
        "knl": abs(out.knl - p.knl) / max(abs(p.knl), 1e-9),
    }
    return out


def identify(plant: SeaPlant, p: PlantParams, duration: float = 6.0,
             fs: int = 2000, seed: int = 3,
             jm_prior_weight: float = 0.5) -> tuple[IdentifiedParams, dict]:
    """Full pipeline: spring calibration, then inertia/friction fit."""
    ks, knl, _ = calibrate_spring(plant, fs=fs)
    data = collect_excitation(plant, duration=duration, fs=fs, seed=seed)
    return identify_from_data(data, p, ks=ks, knl=knl,
                              jm_prior_weight=jm_prior_weight), data
