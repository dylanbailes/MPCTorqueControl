# Milestones — from repo to bench

The simulation side of every milestone is already done and verified
(`results/`, `test/`). These are the hardware bring-up steps, roughly one
weekend each. Do them in order; each leaves you with something demonstrable.

## M0 — Power stack bring-up (weekend 1)

- [ ] Flash `firmware/` to the B-G431B-ESC1 (CubeMX project per
      `firmware/README.md`).
- [ ] Verify ADC current sensing: spin the motor with a hand, see sinusoidal
      phase currents in the USB telemetry.
- [ ] Encoder alignment: `foc_align()` — find the electrical-angle offset
      per phase; verify FOC holds a commanded dq current (scope: phase
      currents sinusoidal at 60°/120°/240° commutation steps).
- **Exit criteria:** current loop holds iq_ref within a few % at 5 A peak.

## M1 — Digital twin vs. hardware (validation)

- [ ] Build the bench rig: motor → torsion bar (2.5 mm drill rod, 304 mm,
      per `hardware/spring_design.py`) → load disc; AS5048A on both shafts.
- [ ] Log 10 s of chirp excitation at 2 kHz on hardware; overlay the
      digital twin response (`model/plant.py` with the same input).
- [ ] Tune plant parameters (Jm, bm, friction) until RMS mismatch < 10%.
- **Exit criteria:** the digital twin reproduces the hardware signals
      closely enough that the MPC weights transfer without re-tuning.

## M2 — Calibration + system ID on hardware

- [ ] Spring calibration: hold the motor with the current loop, hang
      weights on the output, record (torque, deflection) — run the fit from
      `learn/system_id.py::calibrate_spring`.
- [ ] Chirp + PRBS + square excitation (`system_id.m` / `collect_excitation`),
      fit with integrated-equation LS.
- [ ] Write identified Jm, bm, Jl, bl, ks into the plant model.
- **Exit criteria:** ks within ~2%, Jl within ~5%; regenerated
      `results/mpc_model.h` + `results/learned_model.h` copied to `Core/Inc/`.

## M3 — FOC torque loop on the bench (blocked output)

- [ ] Clamp the load disc (blocked-output fixture).
- [ ] PID torque loop first (baseline), then switch the MPC in via a config
      flag. Measure RMS tracking error on the smooth reference waveform.
- **Exit criteria:** MPC beats PID on the bench like it does in sim
      (sim: 5.7 vs 32.9 mN·m RMS). If not, re-check ID and loop timing.

## M4 — Learned disturbance feedforward

- [ ] Log residual data (τ_hat vs. model prediction) under rich excitation.
- [ ] Fit the residual basis (`learn/residual.py`), export the coefficients
      to `results/learned_model.h`.
- [ ] Enable `learned_feedforward()` in `tasks.c`; re-measure the smooth /
      edge-rich tracking and the disturbance-step tests.
- **Exit criteria:** measurable improvement on at least one metric
      (disturbance steady-state error and edge tracking in sim: 1.08→0.91
      and 28→24 mN·m).

## M5 — Impedance + collision safety demo

- [ ] Free the load. Impedance reference `τ_ref = K(θd−θl) − D·ωl`.
- [ ] Grab-the-output test: arm swings toward target, hand pins the output,
      stall detector fires < 150 ms, actuator gives way (u → 0).
- [ ] Verify no false alarms during normal motion (learned friction model on).
- **Exit criteria:** clean video of the demo — this is the money shot for
      interviews.

## M6 — Polish + narrative

- [ ] Write the README hardware section with real numbers and photos.
- [ ] (Optional) push the learning further: RLS online adaptation of the
      residual coefficients, or a second spring with different ks and
      re-calibration to show the pipeline transfers.
- [ ] Record a 3-minute walkthrough video: architecture → ID → closed loop
      → collision demo.
- **Exit criteria:** the story "I built a learned-MPC torque-controlled SEA
      end-to-end" survives a 30-second elevator pitch with the video behind it.
