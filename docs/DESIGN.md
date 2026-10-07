# Design — SEA torque-control stack

The architecture below describes the intended board integration. Python
experiments and portable C modules are implemented; physical performance,
board timing, and peripheral integration remain unverified. Current evidence
is in [RESULTS.md](RESULTS.md); implementation gaps are in
[the firmware guide](../firmware/README.md).

## 1. System architecture

```
                ┌─────────────────────────────────────────────────┐
                │                STM32G431 (B-G431B-ESC1)         │
  host ──USB──> │  telemetry / setpoints                          │
                │                                                 │
                │  ┌─────────┐   ┌──────────┐   ┌──────────────┐  │
                │  │ current │   │  torque  │   │  impedance / │  │
  torque ref ──>│  │  loop   │<──│   loop   │<──│  safety      │  │
                │  │ (10 kHz)│   │ (2 kHz)  │   │  (1 kHz)     │  │
                │  │ FOC + PI│   │ MPC+FF   │   │  momentum    │  │
                │  └────┬────┘   └────┬─────┘   │  observer    │  │
                │       │             │         └──────────────┘  │
                │  PWM  │       tau_s_hat, theta, omega            │
                └───────┼─────────────┼───────────────────────────┘
                        ▼             ▼
                ┌────────────┐  ┌──────────────┐
                │ 3-ph bridge │  │ MT6701 ABZ │  (motor angle/velocity)
                └────────────┘  │ AS5048A SPI│  (load angle; differential
                                └────────────┘   deflection = torque)
                        │
        [ BLDC motor ] ── k_s spring ── [ load inertia ]
```

Intended loop structure (rates are design targets):

| Loop | Rate | Runs | Content |
|---|---|---|---|
| Current | 10 kHz | TIM2 ISR | Clarke/Park, q-d PI + back-EMF feedforward, SVPWM |
| Torque | 2 kHz | TIM3 ISR | spring-torque observer, MPC solve (ADMM), learned feedforward |
| Impedance/collision | 2 kHz in current scaffold | TIM3 ISR | impedance reference, filtered torque residual, stall detection |

The torque loop is the "MPC" loop: it computes the q-axis current reference
for the inner current loop from the torque reference and the measured state.

## 2. Plant model (the digital twin)

Two-mass system coupled by a torsion spring (`model/plant.py`):

```
theta_m" = (Kt·iq + cog(θm) + ripple − k_s·Δθ − f_m(ωm) − bm·ωm) / Jm
theta_l" = (k_s·Δθ − f_l(ωl) − bl·ωl − τ_ext) / Jl
diq/dt   = (vq − R·iq − Ke·ωm) / L
```

- Stribeck friction on both inertias: `(τc + (τst−τc)e^{−(ω/ωst)²})·tanh(ω/ε) + bv·ω`
- Motor cogging (6th/12th harmonic), current-proportional ripple
- PI current loop with back-EMF feedforward and conditional anti-windup,
  voltage saturation against the 24 V bus
- encoder quantization + measurement noise on both angles; the selected
  4015's integrated MT6701 motor encoder is read through ABZ for deterministic
  timer feedback, while the load-side AS5048A remains the 14-bit SPI torque
  measurement
- Fixed-step RK4 at 50 kHz in the published experiment (`dt=2e-5`);
  the standalone plant defaults to 100 kHz

Torque sensing is *differential*: `τ_s = k_s(θm − θl)` with the calibrated
spring curve. On the bench, torque control is well-posed on a
**blocked-output fixture** (stiff spring-damper from the load to ground,
part of the continuous dynamics — a ZOH version would be an unstable
discrete loop at the ~460 Hz load mode).

## 3. FOC (field-oriented control)

`model/foc.py` + `firmware/Core/Src/foc.c`:

- Clarke: 3-phase currents → αβ; Park: αβ → dq at the rotor electrical angle
- Python plant models q-axis PI current dynamics. C implements q-axis PI;
  d-axis voltage is zero, but d-axis current regulation remains to be added
- Back-EMF feedforward `Ke·ωm` on the q-axis for near-decoupled response
- SVPWM with dead time; output clipped to the bus linear range Vbus/√3

## 4. MPC formulation (condensed, embedded-friendly)

`model/mpc.py` — linear prediction model, exact ZOH discretization of the
2-mass plant (blocked output: `k_block = 1e4`, `d_block = 50` — the
fixture's damper is *part of the prediction model*, since omitting it
makes the MPC overdrive the real resonance), horizon N = 30 at T = 0.5 ms
for the selected 4015 build. The exported model uses the fused identified
`Jm` (approximately `2.966e-5 kg·m²` in the current simulation), rather than
the nominal `3e-5 kg·m²` value:

```
min   Σ_k Qy·(y_k − yref)² + Ru·u_k² + S_rate·(u_k − u_{k−1})²
s.t.  |u_k| ≤ u_max,   |u_0 − u_prev| ≤ du_max
```

Authority is **matched to the selected 4015 envelope**: `u_max = 3 A`, below
the motor's 4 A hardware maximum and compatible with the tested 0.30 N·m
torque envelope. The current limit is intentionally not raised without
repeating the current, thermal, and resonance checks. The same clamp applies
in firmware (`MPC_U_MAX`, including feedforward).

> **Aug 2026 selected-build note:** the 4015 motor is modeled with
> `R=4.8 Ω`, `L=2.6 mH`, `Kt≈0.1562 N·m/A`, and `u_max=3 A` under a 4 A
> hardware maximum. The current export is generated from the fused system-ID
> inertia and copied to `firmware/Core/Inc/mpc_model.h`; regenerate it after
> hardware identification changes.

Because the full input sequence over the horizon is the variable, the QP
has only box constraints. It is solved with **warm-started ADMM**
(`model/qp.py`, `firmware/Core/Src/admm.c`): the `H + ρI` system is
Cholesky-factorized once (constant for an LTI plant), so each iteration is
two triangular solves + a box projection — the same structure as OSQP /
acados. 10–25 warm-started iterations are enough in practice.

The condensed MPC is a *constant affine map* in (x₀, yref, u_prev), so the
firmware needs only the exported gradient maps + Cholesky factor:
`results/mpc_model.h` (auto-generated by `export_to_c`).

## 5. Learning pipeline

`learn/system_id.py` + `learn/residual.py`:

1. **Spring calibration** — hold the motor with a stiff PD loop, dither an
   external torque on the output ("hang weights"), fit the spring curve.
   The observer then uses the *calibrated* ks (1.5% error in sim).
2. **Integrated-equation least squares** — with the spring known, the
   integrated EOMs are linear in (J, b, τc); cumulative sums are far more
   noise-robust than differentiating quantized encoder angles (the classic
   failure mode on small-inertia rigs).
3. **Learned residual model** — motor-side residual torque is fit using
   angle, velocity, command, and lagged velocity/command features. The
   causal backward-difference target also contains inertia mismatch and
   current-loop dynamics. A separate three-feature friction fit feeds the
   collision observer. Current fit scores are in [RESULTS.md](RESULTS.md).

Why this split is honest: a spring *cubic* nonlinearity is invisible to a
linear-spring observer by construction, so the spring curve is calibrated
externally and the learning targets what is actually observable from
motor-side data.

## 6. Impedance + collision detection

`model/impedance.py` + `firmware/Core/Src/impedance.c` + `safety.c`:

- Impedance reference: desired stiffness/damping on the output
  (`τ_ref = K·(θ_d − θ_l) − D·ω_l`), tracked by the torque loop.
- Implemented filtered torque-balance residual:
  `rho_dot = k_obs * (Kt*iq - tau_s_hat - friction_hat(omega_m) - rho)`.
  It does not subtract motor acceleration, so motion can contribute to
  the residual; it is not a complete momentum observer.
- Stall detection: torque builds while velocity ≈ 0 → collision.
- On detection: command u → 0 (give way), latch, report over USB.
- The learned friction model is intended to reduce bias; its hardware
  contribution and false-trigger behavior require measurement.

## 7. Engineering scope

The repository implements the control and solver math directly, using NumPy
and SciPy for numerical operations. MATLAB scripts provide another formulation;
host tests compare the C MPC against Python. This is simulation and portable
control-code evidence. A complete STM32 build, measured execution budget,
and physical actuator validation remain the next milestones.
