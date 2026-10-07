# Week 10 — MPC on the MCU (M3 finish)

**Phase 3 · MPC** — ~12 hours

## Exit criteria (week done when…)

- [ ] MPC runs in the 2 kHz torque-loop ISR, end-to-end (observer → g → ADMM
      → iq_ref), with worst-case solve time < 200 µs (budget 250 µs).
- [ ] The firmware MPC and the Python MPC produce **matching inputs** for
      the same (x₀, yref, u_prev) — a logged hardware solve compared against
      `model/mpc.py::solve_sequence` within 1e-3 A.
- [ ] Constraint behavior verified on hardware: commanded u saturates at
      u_max and du_max cleanly, no integrator blowup.
- [ ] `mpc_model.h` regenerated from the identified plant (week 7) and in
      the build.

## Why this week

The whole project's credibility rests on this: the deployed controller
must be *provably* the designed one. Because the condensed MPC is a
constant affine map + a fixed Cholesky factor, the firmware contains zero
tuning knobs — it computes exactly what the Python/MATLAB design tools
produce. This week closes that loop on real silicon.

## Theory

### What the firmware must compute each 0.5 ms

From week 9, the runtime is only three steps:

```
1. g = M_x·x₀ + m_y·yref + m_prev·u_prev      # affine gradient (constants in mpc_model.h)
2. U = ADMM(g, lo, hi)                         # ~20–25 warm-started iterations
3. u_mpc = U[0]                                # first action; u_prev ← u_mpc
```

The constants — M_x (N×4), m_y (N), m_prev (N), L (N×N Cholesky), ρ,
u_max, du_max — are *generated* by `SeaMPC.export_to_c` into
`results/mpc_model.h`. That generation step is the contract between design
and deployment: you never hand-type a matrix into firmware.

### Float32 vs float64

The design tools use float64; the MCU (STM32G431 has a hardware FPU, but
single-precision) uses float32. The exported headers are float32. Is that
enough? The ADMM linear solve is the sensitive part: (H + ρI) has
condition ~65 (measured during development), so float32 gives ~7 digits of
margin — plenty. Verify numerically anyway: run the Python solver in
float32 (the export path does exactly this — `np.float32` arrays) and
confirm the first input changes by < 1e-3 A vs float64. That's the
acceptance test, and it's part of the pytest suite.

### Timing budget

Per ADMM iteration: two triangular solves (N=20 → 210 multiply-adds each)
+ box projection. At 170 MHz with FPU:

```
~25 iterations × (2 × ~210 + 20) flops ≈ 11k flops ≈ 5–15 µs
```

plus g (4·N + 2·N ≈ 120 flops) and the observer — realistically **30–60
µs**, against a 250 µs budget. You have 4–8× headroom; the risk is not
speed but *jitter* — measure worst-case, not average (a cache miss or an
interrupt collision can double a solve).

### The fixed-point question (probably skip)

Single-precision float on this part is fine for N=20. Fixed-point (Q15/
Q31) only becomes necessary for much larger N or a cheaper MCU. Don't do
it — document why float32 suffices (condition number + required accuracy)
instead. That's a *better* engineering answer than a port you don't need.

## Build plan

1. **Regenerate headers (1 h).** Run the export with the identified plant
   params. `results/mpc_model.h` → copy to `firmware/Core/Inc/`. Diff vs.
   the committed nominal version to see the model update.
2. **Port the solver (3 h).** `firmware/Core/Src/admm.c` is already
   written — *review it line by line* against `model/qp.py::AdmmQP`
   (they must match; there's a pytest cross-checking the Python side, and
   the C is a 1:1 port). Implement `mpc.c`: compute g from the header
   constants, call ADMM, apply the box to u₀, write iq_ref.
3. **Unit-test the solve on host (2 h).** Compile `admm.c` + `mpc.c` on
   your PC (a tiny `test/host_mpc_test.c` with a main() that feeds the
   same (x₀, yref, u_prev) as a Python test case and prints the input).
   Match within 1e-3 A. This host test *is* the contract — run it every
   time you change the solver.
4. **Integrate into the ISR (2 h).** TIM3 ISR: observer (week 6) → MPC →
   iq_ref. Keep the PID torque loop compiled behind a `#define TORQUE_MPC`
   so you can A/B switch in firmware (week 11 needs this).
5. **Timing measurement (2 h).** Toggle a GPIO around the MPC call; log
   the high-time over 1000 solves via a spare timer or the USB telemetry.
   Record mean + worst-case. Confirm < 200 µs worst case.
6. **Constraint test on bench (1.5 h).** Command a reference that exceeds
   the limits; confirm u saturates at u_max (4 A) and the slew never
   exceeds du_max (1.5 A/step). Compare the logged u against the Python
   MPC's prediction for the same trajectory.
7. **Tracker (0.5 h).** Record solve times, float32-vs-float64 max diff,
   and the host-test pass.

## Verification

- Host test: firmware input == Python input within 1e-3 A on ≥ 5
  operating points (including a saturated one).
- GPIO timing: worst-case solve < 200 µs over 1000 consecutive calls.
- Bench: u saturates cleanly; no windup; current loop tracks the
  commanded iq_ref (week 4 behavior unchanged).

## Pitfalls

- **The triangular-solve order bug** (week 9's warning is a real one):
  if the firmware MPC commands the wrong sign vs. the design tools, check
  `L' \ (L \ rhs)` ordering *first*.
- **Interrupt collisions**: the 10 kHz current-loop ISR can preempt the
  MPC mid-solve. Either guard with a critical section around the MPC call
  (it's short) or accept the jitter — but measure it, don't assume.
- **`u_prev` bookkeeping**: the slew constraint uses the *applied* input
  (including learned FF, week 12) — decide and document whether u_prev is
  the MPC output or the final applied command, and keep Python and C
  consistent (the Python reference uses the applied value).
- **Optimizer flags**: compile the torque loop with `-O2` and no FPU
  pitfalls (check that the FPU is actually enabled — the CubeMX default
  sometimes leaves it off, and then the "fast" MPC is 10× slower).
