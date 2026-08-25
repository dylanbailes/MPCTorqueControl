# Week 4 — FOC Current Loop (M0)

**Phase 1 · Motor control** — ~12 hours — *hardware should have arrived*

## Exit criteria (week done when…)

- [ ] Motor spins under FOC; the current loop holds iq_ref at 10 kHz with
      < 5% steady-state error up to ±5 A (within the bus limit).
- [ ] d-axis current regulated to ~0 (±0.2 A) while q-axis is driven.
- [ ] Commutation is correct in both directions (no stall, no runaway).
- [ ] Electrical-angle alignment procedure documented and repeatable.

## Why this week

M0 of the milestone plan. Until the current loop is solid, *nothing* on
this project is real — the torque loop commands iq_ref and assumes it
happens. This week closes that loop for real.

## Theory

### Electrical angle and alignment

FOC needs θe, the rotor's *electrical* angle, every current-loop tick.
You have θm from the encoder — but the encoder zero is arbitrary, and the
motor has `p` pole pairs:

```
θe = p · θm + θ_offset
```

The **alignment procedure** finds θ_offset: command a constant d-axis
current vector at θe = 0 (i.e., energize one electrical position), let the
rotor snap to it, and record θm. That θm *is* −θ_offset/p. Repeat 3× and
average. This is `foc_align()` in the firmware sketch and
`model/foc.py::align` in the Python twin — read both.

Critical subtlety: if you get alignment wrong by 90° electrical, the motor
**runs away** (positive feedback on back-EMF). The first motor test must be
at low current with a current limit in software and a finger on the kill
switch.

### Two-shunt current reconstruction

From week 2's ADC setup: you sample i_a and i_b mid-PWM-window, then

```
i_c = −(i_a + i_b)          (balanced three-phase)
```

Reconstruction fails near the PWM boundaries where a phase's active time is
too short to sample — the standard fix is to insert "injection" (measurement
windows) or accept dead zones near the voltage vector edges and let the PI
ride through them. At 100 kHz PWM you have 10 µs per period; the sense
window needs ~2–3 µs.

### The dq PI controllers

Two PI controllers on (i_d, i_q), tuned from the electrical time constant
τ_e = L/R ≈ 0.2 ms. The bandwidth-based tuning used in the repo:

```
kp = L · ω_bw        ki = R · ω_bw
```

with ω_bw = 2π·1500 rad/s (`PlantParams.w_cur_bw`). Why this works:
the plant seen by the PI is approximately `1/(R + sL)` (back-EMF is
feedforward-compensated), so the closed loop is first-order with bandwidth
ω_bw. The **back-EMF feedforward** term `+Ke·ωm` on the v_q output is what
keeps the loop from fighting the motor's own voltage at speed — without it,
steady-state error grows with speed.

**Anti-windup** (conditional integration) matters here more than anywhere:
when v_q saturates against the bus, the integral must freeze or the loop
recovers with a huge overshoot. The Python plant implements exactly this
(`model/plant.py::_current_pi`) — mirror it.

### SVPWM

Space-vector PWM generates the three phase duty cycles from the (v_d, v_q)
command by inverse-Park → (v_α, v_β), then decomposes the voltage vector
into the nearest two of six inverter sectors and times the switches
accordingly. Its linear range extends to Vbus/√3 (that's the saturation
limit used everywhere in the repo: `v_max = Vbus/√3` ≈ 13.9 V at 24 V bus).

## Build plan

1. **Current-loop skeleton (3 h).** Implement `foc.c` fully: Clarke, Park,
   inverse-Park, dq PIs with conditional anti-windup, back-EMF feedforward,
   SVPWM → TIM1 duty registers. Drive it from the TIM2 (10 kHz) ISR.
2. **Alignment (1.5 h).** Implement and run `foc_align()`. Record the
   offset; hard-code it into the build (don't align at boot every time —
   that takes a second you don't have at power-up).
3. **First spin (2 h).** Current-limited (start at 1 A) q-axis step through
   USB. Watch i_a/i_b/i_c in the dashboard from week 2. Confirm
   sinusoidal currents at the right frequency for a slow commanded ramp.
4. **Tune (2 h).** Measure the step response of i_q. Check bandwidth
   against the design (1500 Hz); adjust kp/ki only if the measured loop is
   visibly slower or ringing. **Do not touch the gains yet if it's fine** —
   weeks 6–8 depend on a stable, documented baseline.
5. **Saturation test (1.5 h).** Command iq_ref beyond the achievable limit;
   verify clean recovery (no windup overshoot). This is the safety-critical
   behavior.
6. **Compare with the twin (1 h).** Feed the same iq_ref profile into
   `model/plant.py`; overlay simulated vs. measured i_q. Expect agreement
   within a few % — if not, your Kt/R/L estimates are off, and weeks 6–7
   will fix that, but note it now.
7. **Document (1 h).** `TRACKER.md`: M0 complete if all criteria pass;
   record alignment offset, measured bandwidth, saturation behavior.

## Verification

- i_q step: rise time ≈ 1/ω_bw ≈ 0.1 ms, overshoot < 10%, no limit cycles.
- i_d held at ~0 while i_q tracks ±5 A.
- Both rotation directions commanded through the torque loop's sign.

## Pitfalls

- **Alignment off by 90° → runaway.** First test at 0.5 A with current
  limit + kill switch. Not negotiable.
- **Sampling near the PWM edge.** Current spikes that appear at exactly
  the PWM frequency are sampling artifacts, not motor reality. Move the
  ADC trigger, don't retune the PI.
- **Dead-time distortion** (current flat-spot near zero crossings) is
  normal at low current; if it bothers you, note it and move on — the
  torque loop's learning (week 12) eats this class of error.
- **"The motor hums."** If the phase currents look right but the rotor
  doesn't move: check θe sign convention (clockwise vs counterclockwise
  Park). One sign flip and the whole thing is a motor brake.
