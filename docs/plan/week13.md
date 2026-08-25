# Week 13 — Impedance Control + Collision Safety (M5)

**Phase 4 · Learning, impedance, safety** — ~12 hours

## Exit criteria (week done when…)

- [ ] Load unclamped (free); impedance control tracks a position reference
      with tunable stiffness/damping (the "soft arm" feel).
- [ ] Grab-the-output test (hand pins the output mid-swing): stall detector
      fires **< 150 ms** (sim: 102 ms), actuator gives way (u → 0), no
      damage, no violence.
- [ ] No false alarms: 5 min of normal motion (including the collision-free
      impedance tracking) produces zero detections.
- [ ] Clean video of the demo — this is the money shot for interviews.

## Why this week

M5 — the safety layer is what makes this a *human-interaction* robotics
project rather than a motor-control exercise, and it's where the learned
friction model (week 12) pays its biggest dividend: a collision observer
that is sensitive without being trigger-happy.

## Theory

### Impedance control: making the arm feel like a spring

Rather than commanding a torque directly, impedance control commands a
*relationship* between the output motion and the torque:

```
τ_ref = K·(θ_d − θ_l) − D·ω_l
```

The user-facing parameters are (K, D): K is the virtual stiffness (how
hard the arm pushes back when displaced), D the virtual damping (how
quickly it settles). The torque loop (MPC) then tracks τ_ref — the inner
loop's bandwidth is what makes the arm *feel* like a clean spring instead
of a motor with gears. Why this is the right abstraction for safety: with
K small (soft arm), a human grabbing the output meets a gentle spring, and
the motor *cannot* push through the compliance — the compliance is the
safety mechanism, and the spring in the hardware makes even K=0 soft.

In the sim the impedance demo is exactly this: θ_d chosen, arm swings,
hand pins the output, torque builds against the pin, detector fires,
actuator yields. Reproduce it on the bench with the same reference profile.

### Momentum observer: impact without a force sensor

We don't have a force sensor — we have the model. The standard trick
(De Luca et al., "collision detection and reaction") is the **momentum
observer** residual:

```
r(t) = Kt·∫iq dt − ( Jm·(ωm(t) − ωm(0)) + ∫(τ_s_hat + friction_hat(ωm) + bm·ωm) dt )
```

Think of it as an energy bookkeeping: the motor's torque, minus what the
model says should have gone into inertia, spring, and friction, leaves a
residual r. Under normal operation r ≈ noise; on impact, the unmodeled
external torque shows up in r within milliseconds. The residual is a
**first-order filtered** version of the unknown external torque — set the
observer pole (the λ gain in the standard formulation) to balance
sensitivity vs. noise.

The catch this project exists to solve: **the friction term**.
`friction_hat(ωm)` from week 12 is what makes the residual accurate.
Without it, every cogging torque and every friction transient looks like a
collision — the classic false-alarm problem. This is the cleanest possible
statement of the project's thesis: *the learned friction model is what
makes the safety layer trustworthy.*

### Stall detection: the primary channel for this rig

The momentum observer is great for *impacts* (fast, energetic). But the
sim showed the honest limit: this 0.35 N·m motor produces soft impacts —
the residual from a hand grab peaks ~0.2 N·m, which can be below the noise
floor of the momentum channel. The *robust* detector for a bench SEA is
**stall detection**:

```
torque builds (|τ_s_hat| above threshold)  AND  |ω_l| ≈ 0 (output pinned)
```

Torque building at zero velocity is physically impossible in free motion —
it *must* mean something is holding the output. The detector fires on that
condition; the momentum observer remains as the fast channel for true
impacts (a dropped weight, a swung tool). Both are in
`firmware/Core/Src/safety.c`; the sim uses stall as primary, with the
learned-friction-aware momentum residual as the sensitive secondary.

### Reaction: give way

On detection: command u → 0 (release torque), latch the state, report over
USB, require a manual reset. Releasing torque, not reversing it, is the
right reaction for human safety — the actuator goes soft instantly. (In
the sim: u→0 and τ→0 within a few ms.)

## Build plan

1. **Impedance reference (2 h).** Unclamp the load. Implement
   `impedance.c`: τ_ref = K(θd − θl) − D·ωl at 1 kHz, torque loop tracks
   it. Tune (K, D) on the bench: the arm should follow slow θd commands
   without overshoot and feel springy when pushed by hand.
2. **Momentum observer (2 h).** Implement the residual with
   `friction_hat` from week 12's coefficients. Log r during (a) normal
   tracking, (b) a hand grab. Set the threshold at ~5× the RMS of case (a).
3. **Stall detector (1.5 h).** |τ_hat| > τ_stall AND |ωl| < ω_stall for
   T_hold ms → collision. Tune thresholds so a *deliberate* push (slow,
   soft) doesn't trigger but a grab during a swing does.
4. **Grab test (2 h).** The sim's exact profile: arm swings toward θ_d;
   a hand pins the output at a fixed time; measure detection latency
   (log timestamp of pin vs. detector fire). Repeat 5×; report
   mean/max latency. Target < 150 ms mean.
5. **False-alarm soak (2 h).** 5 min of normal impedance tracking + manual
   pokes *below* the detection threshold. Count detections: must be 0.
   If alarms fire, the friction model is off (recheck week 12) or the
   thresholds are too tight (recheck 3).
6. **Video (2 h).** Two takes: (a) the soft-arm impedance feel, (b) the
   grab → detection → give-way sequence, with a live overlay of τ_hat and
   u from the dashboard. This video is your demo artifact — make it
   clean, stable camera, good light.
7. **Write-up + tracker (0.5 h).** M5 complete; record latency stats and
   thresholds.

## Verification

- Mean detection latency < 150 ms over 5 grabs; worst case < 250 ms.
- Zero false alarms in a 5-minute soak.
- Post-detection: u → 0, τ_hat → ~0, latch + USB report, manual reset.
- Video exists and shows all three phases clearly.

## Pitfalls

- **Thresholds tuned on one grab.** Friction changes with temperature
  (week 11's lesson). Re-run the soak after 30 min of motor warmth.
- **Momentum observer without the learned friction** → false alarms on
  every cogging pass. If you're tempted to raise the threshold instead of
  fixing the model, you've missed the project's point.
- **Impedance K too high** → the arm fights the grab, torque spikes before
  detection, the "safe" demo looks violent. Demo with a soft K (the
  spring does the compliance).
- **Detection latency measured from the wrong event** — the clock starts
  when the output is *actually pinned* (log the pin via a separate GPIO/
  sensor or infer it from ωl dropping), not when you "feel" the grab.
- **Give-way that reverses** — commanding a *negative* torque on
  detection can pinch a hand; command u → 0, never u → −something.
