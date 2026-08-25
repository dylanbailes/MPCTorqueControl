# Paper pitch — what this project contributes

This is the *research framing* of the project: the question, the gap, and
the evidence — written so you can pitch it in a grad-school application, a
lab meeting, or a 4-page workshop paper (ICRA/CDC-style format). Everything
below is reproducible from this repo; the sim numbers are in
`docs/RESULTS.md`.

## Title (working)

**Learning to Compensate Series-Elastic Actuators: Embedded Model-Predictive
Torque Control with Residual Disturbance Feedforward**

## The problem

Series-elastic actuators (SEAs) are the backbone of safe physical
interaction — from legged robots (MIT Cheetah, ANYmal) to collaborative
arms. Their control problem is torque tracking through a compliant element,
which is exactly the case where naive PID performs worst: the resonance
limits bandwidth, friction and cogging sit between the current command and
the spring torque, and the torque *estimate* (spring deflection × stiffness)
is only as good as the calibration.

Two things make this hard in practice:

1. **The plant is imperfectly known** — friction, cogging, and torque ripple
   are significant (here: ~10–15% of rated torque) and never in the linear
   model an MPC uses.
2. **The computation must run in microseconds on a $20 microcontroller** —
   general-purpose nonlinear MPC is out of reach; the field-standard answer
   is a condensed QP with an embedded solver.

## The gap this project addresses

The robotics literature has two separate threads: *learning residual
dynamics* for feedforward compensation (mostly validated in simulation or
on large, expensive platforms) and *embedded MPC* (mostly validated on
rigid-joint systems where the compliance problem is absent). Almost nobody
demonstrates the combination on a compliant actuator where both are
genuinely needed — and where the *compliant element itself* is designed by
the builder (a mechanical-design degree of freedom the controls literature
usually takes as given).

## The claim

> A learned residual disturbance model, embedded as feedforward in a
> condensed ADMM-solved MPC, measurably improves torque tracking and
> disturbance rejection on a series-elastic actuator — and the same learned
> friction model is what makes a collision observer sensitive without false
> alarms — all at 2 kHz on an STM32G431.

## Evidence (this repo)

- **MPC vs PID on the same rig:** 5.7 vs 32.9 mN·m RMS torque tracking
  (5.8×), 1.08 vs 15.8 mN·m steady-state disturbance error (15×).
- **The learning adds a further, honest increment:** disturbance
  steady-state error 1.08 → 0.91 mN·m; edge-rich tracking 28.0 → 24.1 mN·m;
  smooth overall 15.6 → 13.2 mN·m. Held-out residual R² = 0.62.
- **Safety:** collision detected in 102 ms with give-way, enabled by the
  friction-aware observer.
- **Portability:** the same math runs in Python (sim), MATLAB (design), and
  C (firmware); the MPC constants are *generated* from the design tool, so
  the deployed controller is provably the designed one.

## Why it's novel enough to be interesting

- **The compliant element is a design variable.** The spring is sized,
  calibrated, and its error characterized (ks to 1.5%) — most SEA papers
  take the spring from a datasheet.
- **The learning/control split is principled, not ad hoc:** what is
  observable from motor-side data (friction, cogging, ripple) is learned;
  what is not (spring nonlinearity, invisible to a linear observer) is
  calibrated externally. This is a clean, defensible design rule.
- **Full embedded story:** condensed QP + warm-started ADMM + generated
  Cholesky/gradient maps — the exact deployment pattern used in industry
  (acados/OSQP-style) on a $20 part.

## Foreseeable extensions (your next papers)

1. **Online adaptation** — recursive least squares on the residual
   coefficients at 1 kHz: the feedforward tracks slow parameter drift
   (temperature, wear). Directly comparable to adaptive-control baselines.
2. **Spring-aware MPC** — a second, nonlinear spring with the cubic term in
   the prediction model; the calibration pipeline makes this a config
   change, and the comparison "learned residual vs. modeled nonlinearity"
   is a clean ablation.
3. **Multi-DOF** — two SEAs on a 2-DOF arm with the same controller, which
   tests the MPC's handling of coupling through the structure.
4. **HIL validation** — the firmware on the ESC1 driving a real motor into
   a hardware-in-the-loop load, closing the loop between the sim numbers
   and the bench.

## 30-second version

"Nearly every controls résumé has a PID on a hobby servo. Mine has a
torque-controlled series-elastic actuator where I wrote the FOC, the
spring, the calibration, the MPC — solved in real time with ADMM on an
STM32 — and a learned friction model that makes it both more accurate and
safer. Sim says 6× better than PID; the hardware milestones are in the
repo."
