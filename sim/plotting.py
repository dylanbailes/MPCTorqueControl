"""Plotting helpers (Agg backend — headless-safe)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = "results/plots"


def _save(fig, name: str) -> str:
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    path = f"{OUT_DIR}/{name}"
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_id(id_params, data, calib, true: "PlantParams") -> str:
    """Spring calibration curve + excitation + identified friction."""
    fig, axes = plt.subplots(3, 1, figsize=(9, 9))
    # 1) spring calibration: tau_ext vs delta_theta with cubic fit
    d, te = calib["delta_theta"], calib["tau_ext"]
    axes[0].plot(d, te, ".", ms=2, alpha=0.4, label="measurements")
    grid = np.linspace(d.min(), d.max(), 300)
    axes[0].plot(grid, id_params.ks * grid + id_params.knl * grid ** 3, "r-", lw=2,
                 label="cubic fit")
    axes[0].set_xlabel(r"$\delta\theta$ [rad]")
    axes[0].set_ylabel(r"$\tau_{ext}$ [N.m]")
    axes[0].set_title(f"spring calibration: $k_s$={id_params.ks:.3f}, "
                      f"$k_{{nl}}$={id_params.knl:.4f}")
    axes[0].legend(loc="upper left")
    # 2) excitation currents
    t = data["t"]
    axes[1].plot(t, data["u"], lw=0.6, label="i_q command [A]")
    axes[1].plot(t, data["omega_m"], lw=0.6, alpha=0.7, label=r"$\omega_m$ (SG est.)")
    axes[1].set_ylabel("current [A] / vel [rad/s]")
    axes[1].legend(loc="upper right")
    # 3) identified friction curves
    w = np.linspace(-6, 6, 400)
    from learn.system_id import stribeck
    tc, tst, wst, bv = id_params.fric_m
    axes[2].plot(w, stribeck(w, tc, tst, wst, bv), lw=1.6,
                 label="identified motor friction")
    axes[2].plot(w, true.tau_c_m * np.tanh(w / 0.05) + true.bv_m * w, "k--", lw=1,
                 label="true motor (Coulomb+viscous)")
    axes[2].set_xlabel(r"$\omega_m$ [rad/s]")
    axes[2].set_ylabel(r"friction [N.m]")
    axes[2].legend()
    return _save(fig, "system_id.png")


def plot_tracking(runs: dict, name: str = "tracking_comparison.png") -> str:
    """torque reference vs response for several controllers."""
    n = len(runs)
    fig, axes = plt.subplots(n + 1, 1, figsize=(10, 3.0 * (n + 1)), sharex=True)
    for i, (label, rec) in enumerate(runs.items()):
        t = rec["t"]
        axes[i].plot(t, rec["tau_ref"], "k--", lw=1.2, label="reference")
        axes[i].plot(t, rec["tau_s_est"], lw=1.0, label="response (est.)")
        axes[i].set_ylabel(r"$\tau$ [N.m]")
        axes[i].set_title(label, fontsize=10)
        axes[i].legend(loc="upper right", fontsize=8)
        axes[-1].plot(t, rec["tau_s_est"] - rec["tau_ref"], lw=0.7,
                      label=f"{label} (err)")
    axes[-1].set_ylabel("error [N.m]")
    axes[-1].set_xlabel("t [s]")
    axes[-1].legend(loc="upper right", fontsize=8)
    axes[0].set_xlim(0, runs[next(iter(runs))]["t"][-1])
    return _save(fig, name)


def plot_disturbance_fit(fit_meta: dict, eval_r2: float, rec: dict,
                         d_eval: np.ndarray, d_hat: np.ndarray,
                         learned) -> str:
    """Learned disturbance: prediction vs measurement vs velocity."""
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    axes[0].plot(rec["omega_m"], d_eval, ".", ms=1.5, alpha=0.35, label="measured")
    axes[0].plot(rec["omega_m"], d_hat, ".", ms=1.2, alpha=0.35, label=r"$\hat d$")
    axes[0].set_xlabel(r"$\omega_m$ [rad/s]")
    axes[0].set_ylabel(r"disturbance [N.m]")
    axes[0].legend()
    t = rec["t"]
    axes[1].plot(t, d_eval, lw=0.8, label="measured")
    axes[1].plot(t, d_hat, lw=0.8, label=r"$\hat d$")
    axes[1].set_xlabel("t [s]")
    axes[1].set_title(f"held-out R² = {eval_r2:.4f}")
    axes[1].legend()
    names = ["bias", "tanh(w)", "w", "sin6t", "cos6t", "sin12t", "cos12t", "u", "u sin6t"]
    axes[2].barh(names, learned.beta, color="steelblue")
    axes[2].set_title("learned coefficients")
    axes[2].set_xlabel(r"$\beta$")
    return _save(fig, "learned_disturbance.png")


def plot_disturbance(runs: dict, name: str = "disturbance_rejection.png") -> str:
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for label, rec in runs.items():
        axes[0].plot(rec["t"], rec["tau_s_est"], lw=1.2, label=label)
        axes[1].plot(rec["t"], rec["tau_s_est"] - rec["tau_ref"], lw=1.0, label=label)
    axes[0].plot(runs["PID"]["t"], runs["PID"]["tau_ext"], "k:", lw=1.2,
                 label="external torque")
    axes[0].set_ylabel(r"$\tau$ [N.m]")
    axes[0].legend()
    axes[1].set_ylabel("error [N.m]")
    axes[1].set_xlabel("t [s]")
    axes[1].legend()
    return _save(fig, name)


def plot_collision(rec: dict, name: str = "collision_demo.png") -> str:
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    t = rec["t"]
    axes[0].plot(t, rec["theta_l"], lw=1.2, label=r"$\theta_l$")
    axes[0].axhline(0.2, color="r", ls=":", lw=1, label="wall")
    axes[0].set_ylabel(r"$\theta_l$ [rad]")
    axes[0].legend()
    axes[1].plot(t, rec["tau_ref"], "k--", lw=1, label="ref")
    axes[1].plot(t, rec["tau_s_est"], lw=1.2, label=r"$\tau_s$")
    axes[1].set_ylabel(r"$\tau$ [N.m]")
    axes[1].legend()
    axes[2].plot(t, rec["u_cmd"], lw=1.0, label="i_q command")
    axes[2].axhline(0, color="k", lw=0.5)
    axes[2].set_ylabel("current [A]")
    axes[2].legend()
    axes[3].plot(t, rec["collision"], drawstyle="steps-post", label="collision flag")
    axes[3].plot(t, rec["tau_coll_hat"], lw=1.0, label=r"$\hat\tau_{coll}$")
    axes[3].set_ylabel("flag / [N.m]")
    axes[3].set_xlabel("t [s]")
    axes[3].legend()
    return _save(fig, name)
