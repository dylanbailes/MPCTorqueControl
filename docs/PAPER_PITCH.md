# Research proposal: residual feedforward for SEA torque control

This document proposes follow-up experiments. It is not a publication,
a demonstrated novelty claim, or evidence of completed STM32/hardware work.
Current measurements are in [RESULTS.md](RESULTS.md); implementation status
is in [STATUS.md](STATUS.md).

## Research question

When does a compact learned motor-side residual improve a constrained
torque controller for a series-elastic actuator, compared with plain MPC
and a simpler identified friction model?

The spring introduces a lightly damped mode, while friction, current-loop
dynamics, and identification error affect the torque estimate and command.
Feedforward can compensate some residuals but also consumes current authority.
The useful question is the operating range where that tradeoff pays off.

## Existing evidence

The repository implements a two-mass simulation, spring/inertia identification,
PID and condensed MPC, a causal residual fit, and portable C control modules.
In the selected 4015 scenario, MPC reduces tracking error relative to the
fixed PID configuration. Learned FF has little effect on smooth tracking,
with gains on some edge-rich and disturbance metrics. The exact comparison
and measurement windows are in [the generated results](RESULTS.md).

The held-out fit score is a diagnostic: residuals include inertia mismatch
and electrical dynamics as well as friction/cogging. Host C comparisons
establish numerical agreement for tested cases, not complete board behavior.
The collision demo uses PID, impedance, and a stall/residual latch; it does
not establish that learning is necessary for detection or prove human safety.

## Experiments needed to support a paper

1. Establish a measured hardware model, calibrated torque reference, actual
   sampling/compute timing, and uncertainty in inertia/stiffness estimates.
2. Compare separately tuned PID, plain MPC, friction FF, and learned FF with
   matched current budgets across multiple references and load fixtures.
3. Test held-out operating ranges, sensor noise, measurement delay,
   temperature changes, and saturation; report repeated-run uncertainty.
4. Ablate lag features and inertia mismatch to distinguish compensation of
   physical disturbances from compensation of identification error.
5. Compare collision response with and without the friction estimate and
   identify which detector fires, false-trigger rates, and peak contact torque.
6. Review related work before claiming novelty. Document failure conditions
   and added computation alongside performance improvements.

## Possible extensions after validation

Online parameter adaptation, nonlinear spring prediction, and coupled
multi-actuator experiments are plausible follow-ups. Each introduces new
stability and validation requirements; they are outside the present result.
