# Week 11 — MPC vs. PID Benchmark (M3 complete)

**Phase 3 · MPC** — ~11 hours

## Exit criteria (week done when…)

- [ ] Complete benchmark table on hardware: PID vs MPC on smooth tracking,
      edge-rich tracking, and a disturbance step — N ≥ 3 runs per cell,
      RMS + peak + steady-state error, matching the sim's metric definitions
      exactly.
- [ ] MPC beats PID on hardware the way it does in sim (expect: 3–8× on
      smooth RMS, 5–15× on disturbance steady-state). If the gap is < 2×,
      you have a model/ID problem to find this week.
- [ ] The hardware table is written into `docs/RESULTS.md` (hardware
      section), with the sim numbers alongside.
- [ ] You can explain any *disagreement* between the sim gap and the
      hardware gap (there will be one — find and name it).

## Why this week

The headline of the whole project. Everything so far — ID, calibration,
the MPC port — gets judged by this table. And it's the week where
intellectual honesty earns its keep: the numbers will not exactly match
sim, and the *explanation of the difference* is a large part of the
project's value.

## Theory

### Disturbance rejection: why MPC wins and how to measure it

Inject a step of external torque (a weight dropped on the hanger, or a
second motor) mid-tracking. The error response has two numbers:

```
peak error      — the worst transient (stiffness of the loop to shocks)
steady-state    — the residual after settling (integral action / model)
```

PID's steady state is set by its integrator's gain and the friction that
remains; MPC's is set by how well the model predicts the persistent
disturbance and commands compensating current. In sim: PID 15.8 mN·m vs
MPC 1.06 mN·m steady-state — 15×. On hardware you will *not* see 15×
(noise, current-loop lag, model error) — 5–10× is a good outcome, and the
explanation ("the residual gap is the unmodeled part, which week 12's
learning attacks") is the thesis of the project.

### Measurement hygiene (the discipline from week 8, now non-negotiable)

1. **Same reference, same window, same settle time** for every cell.
   Frozen in the bench script before this week's runs.
2. **Interleaved order**: PID, MPC, PID, MPC (not PID×3 then MPC×3) —
   drifts in temperature/friction hit both controllers equally.
3. **N ≥ 3 per cell**, report mean ± spread, not best run.
4. **Watch for saturation**: if u hits u_max during a cell, that cell is
   a constraint test, not a tracking test — flag it.
5. **Log everything**: θm, θl, Δθ, τ_hat, u, iq_ref, iq, yref, per-run
   metadata (temperature, time since power-on). Reproducibility is the
   whole game.

### How to diagnose a missing MPC advantage

If MPC doesn't clearly win, in order of likelihood:

1. **Model mismatch** — re-run week-7 validation; check ks (week 6) and
   Jl; a 20% ks error halves the MPC's advantage.
2. **The QP isn't solving on target** — re-run the host test (week 10);
   a wrong u is the classic silent killer.
3. **The current loop is the bottleneck** — if iq ≠ iq_ref by >5% at
   torque-loop rates, no torque controller can win; fix the inner loop
   first.
4. **Reference too easy** — if the reference is quasi-static, PID with a
   good I-term matches MPC; the gap shows on edges and disturbances. Use
   the sim's references (they were chosen to expose the gap).

## Build plan

1. **Bench script update (2 h).** Extend `scripts/bench_torque.py`:
   config dict {PID, MPC}, the three experiments (smooth, edges,
   disturbance), N runs, JSON output with the same schema as
   `results/results.json`, and an overlay plot vs. sim traces. Freeze the
   settle windows *now*.
2. **Disturbance fixture (1 h).** Weight-drop: a solenoid/hook or a
   hand-released weight on the load hanger at a known radius; trigger
   marker in the log (a GPIO pulse) so the disturbance time is exact.
3. **Run the matrix (3 h).** 2 controllers × 3 experiments × 3 runs ≈ 18
   trials × ~15 s each ≈ 10 min of bench time + setup. Do it in one
   sitting, interleaved. Keep the room still (no fans on the rig — the
   50/60 Hz vibration is real friction change).
4. **Analyze (2 h).** Compute the table + spreads; plot overlays. Answer:
   does the gap direction match sim? Where is the biggest absolute
   difference? (Expected: hardware RMS is 1.5–3× sim RMS everywhere —
   noise + unmodeled friction — but the *ratios* MPC/PID should survive.)
5. **Explain the gap (1.5 h).** Write 3–5 sentences: what's the largest
   unmodeled term (candidate: current-loop lag, encoder noise, friction
   at the couplings), and which experiment is it most visible in? This
   becomes the motivation for week 12.
6. **Write-up (1 h).** Hardware section of `docs/RESULTS.md` + tracker.
   Update `docs/MILESTONES.md`: M3 complete.

## Verification

- Table complete: 2×3×3, means + spreads, all metrics defined.
- MPC/PID ratio on smooth RMS ≥ 2× (sim says ~8×; hardware 2–6×).
- MPC/PID ratio on disturbance steady-state ≥ 4× (sim says ~15×).
- The gap explanation is written down and specific.

## Pitfalls

- **Comparing to sim with different references** — the sim metrics are
  defined in `sim/run_experiments.py`; copy the *definition*, not the
  vibe.
- **Best-of-N cherry-picking** — report mean, and report the spread. A
  spread > 30% means the rig's friction is drifting; fix the rig (clean
  bearings, tighter couplings) before concluding anything about the
  controllers.
- **Temperature drift** — the motor warms up over an hour and Kt/bm
  change a few %. Interleave runs and timestamp everything.
- **A "disturbance" that saturates the current** — then both controllers
  hit the same limit and the comparison is meaningless; use a disturbance
  at ~30% of rated torque.
