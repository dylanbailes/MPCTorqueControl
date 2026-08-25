# Week 6 — Spring Calibration (M2)

**Phase 2 · Calibration, ID, torque loop** — ~10 hours

## Exit criteria (week done when…)

- [ ] ks identified from the weights experiment to ±2% (cross-check: two
      independent data sets agree within 2%).
- [ ] The torque observer in firmware uses the calibrated curve, and the
      estimate matches a reference torque measurement within ±3%.
- [ ] You can state *why* the spring curve must be calibrated externally
      and why the linear-vs-cubic decision is a model-selection problem.

## Why this week

Every torque number in this project — the torque loop, the MPC's output,
the collision threshold — is `τ = ks·Δθ`. A 2% ks error is a 2% torque
error, always, everywhere, invisible in any controller comparison. This
week removes the largest systematic error in the whole measurement chain.

## Theory

### What's actually being measured

The torque transmitted through the spring is:

```
τ_s = k_s·Δθ + k_nl·Δθ³ + (friction + inertia + sensor effects)
```

To identify (k_s, k_nl) we need a *known* torque reference applied while
the load is (nearly) static. The classic method: **hold the motor** with a
stiff position/current loop and **hang weights** on the output at a known
radius r:

```
τ_ext = m·g·r
```

With the output static, τ_s ≈ τ_ext (inertia and load friction are ~zero
at rest), so each (m, Δθ) pair is one point on the spring curve.

### The observability trap (why this must be external)

The torque *observer* is `τ_hat = k_s·Δθ` — a linear map. If the true
spring had a cubic term, a linear observer would attribute the residual to
friction/other disturbances, and **any learning on that residual would be
fitting the spring's own nonlinearity back into the wrong place**. You
cannot separate "spring is cubic" from "there's extra friction" using only
motor-side data — the system is not observable that way. The fix is
structural: measure the spring curve *directly* with an external reference,
so the observer is accurate, and let the learning (week 12) target what is
actually observable: motor-side friction/cogging/ripple. This split is the
design principle that makes the whole project's learning story honest.

### Least squares and model selection

Given N pairs (Δθ_i, τ_i), fit both candidate models:

```
linear:  τ = a·Δθ + b                     (b = offset/preload)
cubic:   τ = a·Δθ + c·Δθ³ + b
```

with ordinary least squares (the normal equations — in Python:
`np.linalg.lstsq`; in MATLAB: `\`). Then **choose the cubic only if it
meaningfully reduces residual variance**. The repo's guard
(`learn/system_id.py::calibrate_spring`) adopts the cubic term only when
the sum of squared residuals drops by ≥ 20%. Why a guard and not
"always cubic": the cubic term on a *linear* spring fits measurement
noise, and then the observer inherits that noise. Model selection by
residual improvement is the honest version of "does my spring have
perceptible nonlinearity?" — with the 2.5 mm torsion bar the answer should
be no (knl ≈ 0), which is itself a result worth reporting.

### Dithering to kill friction

Hanging weights and reading Δθ is slow and friction-polluted (the load
bearing's Coulomb friction biases each reading). The refinement used in
the repo: **dither** — slowly oscillate the external torque
(τ_ext = A·sin(2π·0.5·t), amplitude within the motor's holding torque)
while the PD hold keeps θm ≈ 0. Over many cycles the friction terms
average out and the (τ_ext, Δθ) cloud collapses onto the spring curve.
The amplitude must stay below the holding capability (Kt·u_max ≈ 0.6 N·m
here) or the rotor is dragged and the measurement is garbage.

## Build plan

1. **Weight set + fixture (1 h).** Make a hanger that applies torque at a
   known radius r on the load disc (a printed arm + a hook; measure r to
   ±0.5 mm). Weights: 0.1–1.5 kg in steps (≈ 0.02–0.3 N·m at r = 4 cm).
2. **Hold loop (2 h).** Firmware: a PD position hold on θm
   (kp_hold ≈ 30, kd_hold ≈ 0.2, clamped to ±6 A — same constants as
   `learn/system_id.py::calibrate_spring`). The current loop (week 4) is
   the inner loop; the hold runs on top at 2 kHz.
3. **Static calibration (2 h).** For each weight: wait for settle, record
   (τ_ext, Δθ) for 2 s, average. Build the dataset. Fit linear + cubic;
   apply the model-selection guard; report ks, knl, offset.
4. **Dither calibration (2 h).** Implement the oscillating external torque
   (either by hand-cycling weights slowly, or better: a second small motor
   / a motorized cam if you have one — otherwise hand-cycling at ~0.3 Hz
   is fine). Record (τ_ext, Δθ) continuously; fit on the whole cloud.
   Compare ks from methods 3 and 4 — agreement within 2% is your
   repeatability proof.
5. **Observer update (1.5 h).** Write ks, knl into the firmware observer
   (`sea_observer.c`); verify τ_hat tracks a manual push on the load
   (known sign, magnitude sanity).
6. **Sim mirror (1 h).** Run the same procedure on the digital twin
   (`learn/system_id.py` in a notebook) and confirm your hardware ks is
   within 3% of the sim's 1.0 N·m/rad. If it's off by more, re-measure r
   and the weight masses before suspecting the spring.
7. **Tracker (0.5 h).** Record ks, knl, both methods, and the 2% agreement
   check.

## Verification

- Two independent calibration runs → ks within 2%.
- τ_hat vs a manual reference (push with a known-force spring scale): ±3%.
- Model-selection guard output: knl = 0 (linear) for the torsion bar —
  with the number recorded.

## Pitfalls

- **Weights swinging** (pendulum mode) pollute every sample. Hang them
  through a nearly frictionless eyelet and wait for settle.
- **Dither amplitude too large** → rotor dragged → ks biased low. Watch
  θm in the dashboard during the run: it should stay within ±0.02 rad.
- **Preload/offset**: the (τ_ext, Δθ) fit *must* include a bias term b —
  the assembly preloads the bar (week 5) and Δθ=0 does not mean τ=0.
- **Measuring r wrong** biases ks linearly. Measure the effective radius
  to the hanger, not the disc edge.
