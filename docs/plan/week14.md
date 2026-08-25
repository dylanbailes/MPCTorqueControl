# Week 14 — Repeatability, Robustness, Edge Cases

**Phase 4 · Learning, impedance, safety** — ~10 hours

## Exit criteria (week done when…)

- [ ] Every headline number has N ≥ 5 runs with mean ± std reported
      (torque tracking ×3 experiments, disturbance, collision latency).
- [ ] Sensitivity study: at least one parameter varied ±20% (e.g. ks used
      by the MPC, or the load inertia) with the measured effect on RMS
      error recorded.
- [ ] Saturation/limit behavior documented: what happens at u_max, at
      θ_d beyond the workspace, at power-on with the load clamped.
- [ ] A "known issues" list exists in the repo (what's still off, what
      would you do with another month).

## Why this week

Any set of numbers can be produced once. What separates a project from a
demo is *reproducibility* — and the self-knowledge of where it breaks.
This week converts week 11's table and week 13's latency into statistics,
and finds the edges of the operating envelope. It's also the week that
keeps you honest in interviews: "what happens when…" questions get real
answers.

## Theory

### Experimental design in one page

- **Mean ± std over N runs**, never best-of-N. With friction-dominated
  systems, run-to-run spread of ±20% is normal; report it, don't hide it.
- **Paired comparisons**: for MPC vs. MPC+learned (week 12), run the two
  configs *interleaved* in time so temperature drift affects both
  equally — the *paired delta* is the honest quantity, and its std is
  usually much smaller than the individual stds.
- **Confounds checklist** (write it once, apply every session):
  temperature, time-since-power-on, bearing condition, encoder mounting,
  base-plate tightness, cable strain on the load.
- **The reproducibility contract**: a script (like the week-11 bench
  script) that takes a config name, runs the experiment, writes JSON.
  Anyone (including 3-months-later you) can re-run any cell.

### Sensitivity: why it matters and how to do it cheaply

The MPC's advantage rests on the model. The natural question: *how wrong
can the model be before the advantage disappears?* In sim this is
answered by the learned/MPC results with the *calibrated* (slightly off)
ks — the pipeline survives a 1.5% ks error. On hardware, do a ±20% sweep
on one parameter (easiest: run the MPC with ks deliberately scaled 0.8×
and 1.2× in the *model*, keeping the real plant fixed). Expected outcome:
RMS degrades smoothly, MPC stays below PID until the model error gets
large. That graceful degradation is itself a result (it's the difference
between a controller and a fragile gadget).

### Edge cases that actually bite

1. **Power-on with the load clamped**: the observer starts at Δθ=0, the
   clamp holds θl, and the first reference step asks for torque the clamp
   resists — fine, but the *initial* state must be handled (zero-velocity
   start, no integral windup at t=0).
2. **Reference beyond the workspace**: θ_d where the arm would hit the
   frame. The impedance loop should stop it softly (the wall fixture in
   the sim models exactly this — `set_wall`); verify on the bench.
3. **Saturation cascade**: u_max → current loop saturates → torque loop
   sees lag → MPC model mismatch for a few ms. Verify the system recovers
   (no limit cycle) after a sustained-saturation episode.
4. **Encoder dropout** (week 3's error flag): a dropped frame must never
   reach the MPC. Verify the firmware's stale-data guard with an
   intentional fault injection (wiggle an SPI wire).
5. **Cold start**: friction at 20 °C vs. 40 °C motor is different —
   re-run one week-11 cell cold vs. warm and report the delta (this is
   the *motivation* for online adaptation, your extension #1).

## Build plan

1. **Stats pass (3 h).** Re-run the full week-11/12/13 battery with N=5.
   Compute means ± stds; update `docs/RESULTS.md` (hardware) with
   statistics, not single runs.
2. **Sensitivity study (2.5 h).** ks sweep (0.8×, 1.0×, 1.2× in the MPC
   model), N=3 each, smooth-tracking RMS. Plot RMS vs. model-ks. If the
   curve is flat, say so (robustness result); if it's steep, that's the
   argument for week 6's calibration precision.
3. **Edge-case pass (2.5 h).** Work through the five edge cases above;
   for each: reproduce, fix if needed, document the behavior + any
   mitigation. Fault-injection on the encoder is the most valuable —
   safety code must be tested with broken inputs.
4. **Known-issues list (1 h).** `docs/KNOWN_ISSUES.md` (or a section in
   RESULTS.md): what's unexplained, what's approximate, what you'd do
   with another month (RLS online adaptation, second spring, 2-DOF arm).
   This list is interview gold — it shows the boundary of your work.
5. **Tracker (1 h).** Full status; decide what week 16 (buffer) needs to
   absorb.

## Verification

- All headline metrics now mean ± std, N ≥ 5.
- Sensitivity plot exists (RMS vs. model-ks).
- Edge-case checklist: 5/5 documented (fixed or explicitly noted).
- KNOWN_ISSUES written with ≥ 3 real items.

## Pitfalls

- **Inflating N without controlling confounds** — 20 runs across an
  afternoon of warming motor is *worse* than 5 interleaved runs.
- **"The experiment passed, ship it"** — run the edge cases *before* the
  final demo (week 16); the demo is where they show up.
- **Hiding the sensitivity curve** because it's not flat — a flat curve
  is a great robustness result; a steep curve is the calibration
  argument. Both are publishable. Only "didn't measure" is bad.
- **Fixing bugs during the stats run** — freeze the firmware during the
  battery; any code change invalidates the runs after it. Run, analyze,
  then fix, then re-run affected cells.
