# Semester Tracker

The single source of truth for pace. Tick exit criteria as you hit them.
**Rule: a week is done only when its criteria are ticked — not when the
calendar says so.** If you're more than one week behind at any phase
boundary, execute the fallback for that phase (see `README.md` in this
folder) and note it here.

Legend: `[ ]` open · `[x]` done · `[~]` deferred with reason (reason in the
week's doc or `docs/KNOWN_ISSUES.md`)

---

## Phase 0 — Foundations (Weeks 1–3)

### Week 1 — Launch & toolchain
- [ ] `pip install -r requirements.txt` clean on a fresh venv
- [ ] `python -m sim.run_experiments` regenerates `results/results.json`
      (MPC ≈ 4.0 vs PID ≈ 32.9 mN·m on smooth tracking)
- [ ] `pytest test/ -q` → all tests passed
- [ ] Can explain the three loops and point at the implementing files
- [ ] Order A placed per `docs/plan/ordering_checklist.md` (ESC1, motor,
      sensors, structure)
- [ ] Every Order A arrival checked against the DOA list and logged here
      (magnet present, shaft/dowel/slot sizes measured, spin tests passed)

### Week 2 — CubeMX + telemetry
- [ ] CubeMX project: 170 MHz, TIM1 3×PWM @ 100 kHz + dead time, TIM2 10 kHz,
      TIM3 2 kHz, USB CDC
- [ ] Firmware compiles; board enumerates as a COM port
- [ ] 1 kHz heartbeat telemetry streamed and plotted in Python (5 min clean)
- [ ] Can explain clock tree + timer→PWM→ADC trigger chain from memory

### Week 3 — Encoders & velocity
- [ ] MT6701 motor A/B decoded by timer at ≥ 2 kHz; Z index verified; load-side AS5048A read at ≥ 2 kHz over SPI; MT6701 I²C diagnostic angle agrees with ABZ count
- [ ] Stationary noise: |Δ(θ_q)| ≤ 2 LSB for 99.9% of frames (60 s)
- [ ] Velocity pipeline (filtered difference) smooth enough for control
- [ ] Dashboard: live θm, θl, Δθ, ωm, ωl (+ offline replay)

## Phase 1 — Motor + build (Weeks 4–5)

### Week 4 — FOC current loop (M0)
- [ ] Motor spins under FOC; iq held < 5% error up to ±2 A at 10 kHz (bus-limited stall ≈ 1.75 A)
- [ ] i_d ≈ 0 while i_q tracks
- [ ] Correct commutation both directions (no stall/runaway)
- [ ] Alignment procedure documented + repeatable

### Week 5 — Mechanical build (M1)
- [ ] Rig assembled: motor → torsion bar → load disc; MT6701 motor encoder and AS5048A load encoder mounted
- [ ] Free-spin test clean (Δθ smooth, < 0.05 rad, no stick-slip)
- [ ] Resonance measured ≈ 18 Hz ± 30%; ζ recorded
- [ ] Spring coupling disassembles/reassembles in < 10 min

## Phase 2 — Calibration, ID, torque loop (Weeks 6–8)

### Week 6 — Spring calibration (M2)
- [ ] ks identified ±2% (two independent runs agree within 2%)
- [ ] Firmware observer uses calibrated curve; τ_hat within ±3% of reference
- [ ] Can state why the spring curve must be calibrated externally

### Week 7 — System ID (M2)
- [ ] Jl ±5%, ks ±2%, Jm ±20% from one logged excitation run
- [ ] Open-loop validation on fresh log: RMS mismatch < 10%
- [ ] Identified params written back; `results/mpc_model.h` regenerated
- [ ] Can explain in one sentence why bm/bl are poorly identifiable

### Week 8 — PID torque loop (M3)
- [ ] Blocked-output fixture engaged; torque loop at 2 kHz
- [ ] PID RMS within 2× of sim's 32.9 mN·m; N ≥ 3 runs, spread < 15%
- [ ] Repeatable measurement script (`scripts/bench_torque.py`) frozen
- [ ] 18 Hz ringing visible in closed-loop spectrum; explanation in hand

## Phase 3 — MPC (Weeks 9–11)

### Week 9 — MPC theory + MATLAB design
- [ ] Can derive the condensed QP (Y = Cx·F·x₀ + Cx·G·U) on paper
- [ ] Can explain ADMM (u, z, λ) and why warm start + fixed Cholesky embed
- [ ] Design study done in MATLAB; (N, Qy, Ru, S_rate) justified
- [ ] Reproduced MPC < PID gap in MATLAB on the linear plant

### Week 10 — MPC on firmware (M3)
- [ ] MPC in the 2 kHz ISR, worst-case solve < 200 µs
- [ ] Host test: firmware input == Python input within 1e-3 A (≥ 5 points)
- [ ] Constraint behavior verified on bench (u_max, du_max clean)
- [ ] `mpc_model.h` regenerated from identified plant and in build

### Week 11 — MPC benchmark (M3 complete)
- [ ] Full table: PID vs MPC × (smooth, edges, disturbance) × N ≥ 3,
      mean ± spread, sim-defined metrics
- [ ] MPC/PID ratio ≥ 2× smooth, ≥ 4× disturbance steady-state
- [ ] Gap between sim and hardware explained in writing
- [ ] Hardware numbers written into `docs/RESULTS.md`

## Phase 4 — Learning + safety (Weeks 12–14)

### Week 12 — Learned residual (M4)
- [ ] Residual logged; basis model fit; held-out R² ≥ 0.5
- [ ] `learned_model.h` regenerated; feedforward enabled in firmware
- [ ] MPC+learned ≥ MPC on ≥ 1 metric by ≥ 5% (no regression > 5% elsewhere)
- [ ] Can explain the calibrate-vs-learn design rule in one minute

### Week 13 — Impedance + collision (M5)
- [ ] Impedance tracking with tunable (K, D); soft-arm feel
- [ ] Grab test: detection < 150 ms mean over 5 grabs; give-way (u → 0)
- [ ] Zero false alarms in 5 min soak
- [ ] Clean demo video recorded

### Week 14 — Repeatability & edge cases
- [ ] All headline metrics mean ± std, N ≥ 5
- [ ] Sensitivity study (ks ± 20% in MPC model) with plot
- [ ] Edge cases 5/5 documented (clamped start, workspace limit,
      saturation cascade, encoder dropout, cold start)
- [ ] `docs/KNOWN_ISSUES.md` written with ≥ 3 real items

## Phase 5 — Writeup (Weeks 15–16)

### Week 15 — Writeup & pitch
- [ ] RESULTS.md hardware section complete (sim + hardware, limitations)
- [ ] PAPER_PITCH.md updated with hardware numbers + one figure
- [ ] 3-minute demo video with voiceover
- [ ] Resume bullet + 30-second pitch written and practiced

### Week 16 — Buffer + final demo
- [ ] All open criteria done or explicitly deferred with reason
- [ ] Demo rehearsed twice; second run flawless from cold power-on
- [ ] Repo presentable: tests green, results regenerated, README accurate
- [ ] (Stretch) One next step started (RLS adaptation preferred)

---

## Final status

| Phase | Weeks | Status |
|---|---|---|
| 0 Foundations | 1–3 | [ ] |
| 1 Motor + build | 4–5 | [ ] |
| 2 Cal + ID + torque | 6–8 | [ ] |
| 3 MPC | 9–11 | [ ] |
| 4 Learning + safety | 12–14 | [ ] |
| 5 Writeup | 15–16 | [ ] |

**Demo spine (never cut):** week-11 MPC-vs-PID table → week-13 collision
demo → week-15 video.
