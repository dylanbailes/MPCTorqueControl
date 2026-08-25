# Results — measured on the digital twin

All numbers come from `python -m sim.run_experiments` (deterministic seeds),
which runs the full pipeline: system ID → learned disturbance → closed-loop
comparisons on the 2 kHz torque loop with the *blocked-output* fixture
(load clamped to ground by a stiff spring — the classic torque-control test
rig). Plots: `results/plots/`. Raw numbers: `results/results.json`.

## 1. System identification

| Quantity | True | Identified | Rel. error |
|---|---|---|---|
| Spring stiffness ks [N·m/rad] | 1.000 | 0.985 | **1.5%** |
| Load inertia Jl [kg·m²] | 1.2e-3 | 1.216e-3 | 1.3% |
| Motor inertia Jm [kg·m²] | 8.0e-5 | 7.26e-5 | 9.3% |
| Viscous damping bm / bl | small | large rel. error | poor |

The spring and load inertia identify beautifully — that's what the torque
control and the MPC model actually need. The motor-side viscous terms are
poorly observable from this excitation (their effect is small and correlated
with friction); this is honest and expected for small-inertia rigs.

## 2. Torque tracking (blocked output, 2 kHz)

Smooth multi-sine reference (±0.15 N·m):

| Controller | RMS error [mN·m] | Max error [mN·m] | Overall RMS [mN·m] |
|---|---|---|---|
| PID (torque) | 32.9 | 80.5 | 35.6 |
| MPC | **5.7** | 43.4 | 15.6 |
| MPC + learned FF | 5.7 | 42.2 | **13.2** |

**MPC ≈ 5.8× better than PID** on the steady metric. The learned
feedforward adds a further ~15% on the overall metric (it cancels the
friction/cogging that the model-based and deflection-feedback loops leave
behind). MPC's max error is dominated by the 18 Hz resonance ringing on
reference edges — the price of a stiff torque loop.

Disturbance step (+0.1 N·m external at t = 1 s):

| Controller | Peak error [mN·m] | Steady-state error [mN·m] |
|---|---|---|
| PID | 48.3 | 15.8 |
| MPC | 3.1 | 1.08 |
| MPC + learned | 3.8 | **0.91** |

**MPC ≈ 15× lower steady-state disturbance error than PID.**

Edge-rich reference (0.6 Hz square-ish steps, robustness stress test):

| Controller | RMS [mN·m] | Overall RMS [mN·m] |
|---|---|---|
| PID | 41.8 | 42.4 |
| MPC | 22.6 | 28.0 |
| MPC + learned | 19.3 | **24.1** |

## 3. Learned disturbance model

Held-out R² = 0.62 on the motor-side residual (friction + cogging + ripple
basis in θm, ωm). The unexplained fraction is measurement noise at the
torque-loop rate and current-loop lag — reasonable for a bench setup, and
enough to measurably improve disturbance rejection.

## 4. Collision detection (human-safety demo)

Impedance control swings the output toward a target; a "hand" pins the
output at t = 0.1 s. The stall detector (torque builds, velocity ≈ 0,
learned-friction-aware momentum residual) fires in **102 ms** at a
post-collision peak torque of 201 mN·m, then the actuator yields (u → 0).

## 5. MATLAB cross-validation

`model/matlab/mpc_design.m` reproduces the condensed MPC with the same
weights on the linear plant: **13.7 mN·m RMS** tracking error (its
reference is a richer waveform than the Python smooth test, so the numbers
are not directly comparable — the point is the solver and model agree).
`model/matlab/system_id.m` recovers Jl to 0.4% and ks to 1.5% from fresh
chirp data, matching the Python pipeline.

## Honest caveats

- **Sim, not yet hardware.** The digital twin is high-fidelity (friction,
  cogging, quantization, voltage saturation) but the *numbers* are
  simulated. The hardware milestones (M0–M6) exist to reproduce them.
- **The learned model's headline contribution is modest** on smooth
  tracking (~15%) — that's the truthful picture. Its strongest, cleanest
  effect is disturbance steady-state error (1.08 → 0.91 mN·m) and edge
  tracking (28 → 24 mN·m), plus enabling a *sensitive* collision observer
  that doesn't false-trigger on cogging.
- **MPC wins big because the plant is known** — the ID step feeds the model
  the real ks and Jl. That's the honest framing: the full pipeline (ID +
  MPC + learning) is what produces the numbers, not MPC alone in a vacuum.
