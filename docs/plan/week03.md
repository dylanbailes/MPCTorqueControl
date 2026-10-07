# Week 3 — Encoders & Velocity Estimation

**Phase 0 · Foundations** — ~10 hours

## Exit criteria (week done when…)

- [ ] MT6701 motor encoder reads reliably through ABZ timer quadrature at ≥
      2 kHz; load-side AS5048A reads reliably at ≥ 2 kHz over SPI.
- [ ] Raw angle noise measured: < 1 LSB standard deviation after
      decimation; dropout/garbage frames detected and flagged.
- [ ] Velocity estimates from the *quantized* angles are smooth enough to
      drive a differentiator-based controller (compare against sim
      `model/plant.py` `observe()` behavior).
- [ ] You have a working "encoder dashboard": live plots of θm, θl, Δθ,
      ωm, ωl.

## Why this week

Δθ = θm − θl **is** your torque sensor (times ks). Every later week —
calibration, ID, MPC, collision detection — reads these two angles. The
quality of this week's measurement pipeline sets the ceiling on everything
after it.

## Theory

### The selected encoders: MT6701 motor ABZ + AS5048A load SPI

Both encoders read the angle of a diametrically magnetized magnet rotating
over the chip. The selected motor-side MT6701 exposes ABZ and I²C; the
load-side AS5048A remains the torque-critical 14-bit SPI measurement.

- **MT6701 ABZ:** configure up to 1,024 PPR and use 4× timer decoding,
  yielding 4,096 counts/revolution for deterministic motor angle/velocity.
- **MT6701 I²C:** retain for absolute-angle, zero-offset, configuration, and
  ABZ-count diagnostics; it is not the primary real-time feedback path.
- **AS5048A SPI:** read the 14-bit angle register (2 bytes, MSB-first); check
  its error/parity bit on every frame and retry corrupted reads.
- **Magnet/gap:** use the required diametric magnet, center it carefully, and
  verify the module-specific air gap.
- **Mounting matters**: the magnet must be centered on the shaft within
  ~0.1 mm and at the rated gap (0.5–1.5 mm typical). Eccentricity shows up
  as a **once-per-rev sinusoidal error** in the angle — you can measure it
  (week 5) and, if needed, calibrate it out.

### Quantization and the velocity problem

The angle is a staircase: θ_q = round(θ/res)·res, where res = 2π/16384.
Differentiating a staircase is disastrous:

```
ω = (θ_q[k] − θ_q[k−1]) / T
```

produces spikes of ±res/T — at 2 kHz that's ±0.022°·(π/180)/0.5 ms ≈
±0.77 rad/s of pure quantization noise. Three remedies, in increasing
sophistication:

1. **Longer difference window**: ω = (θ_q[k] − θ_q[k−m])/(m·T). Kills
   noise, adds m/2 samples of lag. Fine for the torque loop's friction
   model; bad for anything needing phase margin.
2. **Low-pass filter** the differenced velocity (first-order, ~200 Hz).
   Simple, standard, matches the firmware's "filtered difference".
3. **Savitzky–Golay** (polynomial fit over a sliding window, derivative
   taken analytically). This is what `learn/system_id.py::_vel` uses
   (window 31, poly 3) — it's the right tool for *offline* ID, where you
   can afford the window.

The deep lesson: **every velocity used by a controller or estimator is a
filtering decision**, and the filter's lag is a real cost. Write it down
per signal: which filter, what lag, why that's acceptable.

### The differential measurement

θm and θl are read by *separate* chips, so Δθ carries the sum of both
quantization errors (±2 LSB worst case) but *no* common-mode error (e.g.,
a sagging base plate moves both by the same amount — invisible to Δθ).
This common-mode rejection is why differential deflection sensing is the
right topology for torque, and it's worth stating in your writeup.

## Build plan

1. **Encoder-interface bring-up (2 h).** Configure a timer in encoder mode
   for MT6701 A/B, connect Z to an index/GPIO input, and configure I²C for
   MT6701 diagnostics. Configure SPI for the load-side AS5048A. Implement
   the driver so bad AS5048A frames are retried and ABZ counter wraparound is
   handled with signed modular arithmetic.
2. **Rate test (2 h).** Stream both angles at 2 kHz for 60 s, stationary.
   Plot histograms of consecutive-difference noise. Targets: no frames
   with > 2 LSB jumps; error flags < 0.1%.
3. **Velocity pipeline (2 h).** Add differenced velocity + first-order
   filter in firmware. Tune the filter to the noise you measured. Compare
   your noise+lag against the sim's quantization model
   (`PlantParams.enc_bits=14`, `enc_noise_lsb=1.0`).
4. **Dashboard (2 h).** Extend `scripts/plot_telemetry.py` from week 2:
   live θm, θl, Δθ, ωm, ωl. Keep it scriptable (log to CSV, replay offline)
   — week 7's ID consumes offline logs.
5. **Alignment check (1 h).** Rotate the motor by hand; confirm Δθ tracks
   your hand motion with no wrap artifacts (angles are modulo 2π — decide
   now whether you keep raw angles and unwrap in software, or use the
   chip's zero-position register. The sim uses raw continuous angles +
   unwrap; mirror that).
6. **Tracker (0.5 h).** Tick week 3; record the measured LSB noise and the
   filter choice.

## Verification

- Stationary noise: |Δ(θ_q)| ≤ 2 LSB for 99.9% of frames, 60 s.
- Manual rotation: Δθ smooth, no discontinuities at 0/2π boundary.
- `python scripts/plot_telemetry.py --replay log.csv` reproduces the live
  dashboard offline.

## Pitfalls- **Unchecked parity/error bit.** A corrupted AS5048A frame can create a giant
  velocity spike and a false collision; check every SPI frame and retry.
- **ABZ voltage mismatch.** Verify A/B/Z logic levels before connecting to the
  STM32; level-shift 5 V push-pull outputs and add 3.3 V pull-ups for
  open-drain outputs as required.
- **ABZ configuration mismatch.** Record the MT6701 PPR and timer decode mode;
  a wrong counts/revolution value corrupts velocity and electrical-angle
  scaling.
- **Eccentric magnet.** Symptom: once-per-rev sinusoid in the noise. Fix
  mechanically (re-center), don't filter it away blindly — a 0.1 mm
  eccentricity can be a 0.3° error, which is *torque error* at ks=1.
- **Different filter per consumer.** The MPC needs fast ωm; the friction
  model needs smooth ωm; the ID needs unfiltered truth. Don't share one
  velocity signal everywhere — store raw and filtered, and label which is
  which in the telemetry frame.
- **Unwrap bugs** at the 2π boundary will look like 1000 rad/s blips once
  a month. Test rotation through the boundary explicitly.
