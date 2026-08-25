# Week 8 — Torque Loop: PID Baseline (M3)

**Phase 2 · Calibration, ID, torque loop** — ~11 hours

## Exit criteria (week done when…)

- [ ] Blocked-output fixture engaged; torque loop running at 2 kHz with the
      week-6 observer and week-7 model.
- [ ] PID torque tracking measured on the *same* smooth reference the sim
      uses (multi-sine, ±0.15 N·m) → RMS error within 2× of the sim's
      32.9 mN·m (i.e. ≤ ~66 mN·m; expect to land ~30–50 mN·m).
- [ ] You have a repeatable measurement script: N ≥ 3 runs per config,
      RMS + peak error, plotted against the sim's PID trace.
- [ ] The resonance is visible in the closed-loop response and you can
      explain why the PID can't go faster (phase margin at 18 Hz).

## Why this week

M3's first half. The PID is the *baseline* every later claim is measured
against. If you can't make a solid PID torque loop, you won't be able to
show MPC beating anything; and the measurement discipline you build this
week (same reference, same window, N runs) is what makes week 11's MPC-vs-
PID table trustworthy.

## Theory

### The torque loop plant and its resonance

Closed around the spring torque, the loop sees (approximately, with the
output blocked and the current loop fast):

```
τ_s(s)/iq_ref(s) ≈  Kt · ks / (Jm·s² + bm·s + ks) · (1/(τ_cur·s+1))
```

i.e. a second-order resonance at ~18 Hz plus the current-loop lag. The
resonance peak is tall because damping is light (ζ ≈ 0.02–0.1 from
week 5). A PID with real gains can:

- use **D** to add damping at the resonance (D acts like extra bm),
- use **I** to kill steady-state error from friction,
- but every unit of gain at 18 Hz costs you phase margin; the practical
  torque-loop bandwidth lands near 5–10 Hz — *below* the resonance.

That's the honest ceiling: PID on a compliant actuator trades bandwidth
for stability, and the price shows up as ringing on every reference edge
and slow rejection of load disturbances. The sim's numbers (32.9 mN·m RMS)
include exactly this ringing.

### The blocked-output fixture (from the sim, week 5)

With the load clamped by a stiff spring-damper (k_block ≈ 1e4), the
"output" can't run away — torque tracking is well-posed, and the plant the
controller sees is the two-mass + block system `model/mpc.py` models with
`k_block = 1e4`. On the bench: clamp the disc with a high-stiffness brake
or bolt it to the base through a stiff mount. **The clamp's stiffness is
part of the plant** — measure the fixture's contribution to the resonance
if the measured f_res moves between week 5 (free) and now (blocked).

### A fair comparison methodology

The sim's comparison (see `sim/run_experiments.py` and `docs/RESULTS.md`)
uses:

1. **The same reference waveform** for every controller (a smooth
   multi-sine; a separate edge-rich square-ish test for robustness).
2. **A settle window** — RMS computed after the initial transient, so the
   metric measures steady tracking, not the step response.
3. **Separate metrics**: RMS, max error, and (for disturbance) peak +
   steady-state error.

Copy this exactly. Your hardware script (`scripts/bench_torque.py`) should
emit the same JSON shape as `results/results.json` so the comparison is
apples-to-apples. Decide the settle window *now*, before you see the
results (that's what makes it honest).

## Build plan

1. **Block the output (1 h).** Engage the fixture; re-measure the
   resonance (impulse) — record the blocked f_res (should be near the
   18 Hz + block dynamics; expect it to shift up somewhat).
2. **Torque loop skeleton (2 h).** TIM3 ISR: read observer τ_hat →
   PID (kp, ki, kd on torque error) → iq_ref → current loop. Start with
   kp = 0 and I = 0, D = 0; add terms one at a time (below).
3. **Tune on the bench (3 h).** Reference: the sim's smooth multi-sine.
   - P alone: raise kp until the RMS error stops improving or the
     resonance rings on edges (watch the 18 Hz component of τ_hat).
   - Add D: damp the ringing, raise kp a bit more.
   - Add I: kill the steady-state error; watch for low-frequency limit
     cycles (integral + Coulomb friction can oscillate at ~1 Hz).
   - Record gains. Target ≤ 2× the sim's RMS; if you're at 3–4×, the
     likely culprits are current-loop lag or the week-7 model being off —
     debug before blaming the tuning.
4. **Measurement script (2 h).** `scripts/bench_torque.py`: runs N=3+
   trials per config, computes RMS/max in the settle window, saves JSON +
   overlay plot vs. the sim trace. **This script is now the project's
   measurement instrument — it will be reused unchanged in weeks 11, 12,
   14.**
5. **Resonance-in-the-loop diagnosis (1.5 h).** With the loop closed,
   compute the power spectrum of τ_hat during tracking; show the 18 Hz
   peak. Sweep a small kp up and down to demonstrate the gain/ringing
   trade. Screenshot for your writeup — this is the "why PID has a
   ceiling" figure.
6. **Document (0.5 h).** Tracker: PID gains, RMS, max, and the blocked
   f_res. Update `docs/MILESTONES.md` M3 progress.

## Verification

- PID RMS within 2× of sim (32.9 mN·m), N=3 runs, spread < 15%.
- Spectrogram/power spectrum shows the 18 Hz ringing on reference edges.
- Steady-state torque error < 5 mN·m on a constant reference (I-term
  working).

## Pitfalls

- **Tuning against one lucky run.** Always N ≥ 3, always same reference,
  always same settle window. A single run's RMS can vary ±30% from
  friction alone.
- **Current-loop lag masquerading as torque-loop instability.** If the
  torque loop limit-cycles at a frequency you didn't expect, check the
  inner loop's step response (week 4) before adding more D.
- **Integral windup on reference edges** — with slew-limited references
  this is mild, but implement anti-windup on the torque PID too (mirror
  the current loop's conditional integration).
- **Comparing to the sim with different parameters.** The sim's PID is
  tuned for the *nominal* plant. Re-run the sim PID with your identified
  params before comparing — the comparison must be "same plant, different
  controller", not "sim vs. reality".
