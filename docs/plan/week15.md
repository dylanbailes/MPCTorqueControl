# Week 15 — Writeup, Paper Pitch, and the Narrative

**Phase 5 · Writeup** — ~10 hours

## Exit criteria (week done when…)

- [ ] `docs/RESULTS.md` (hardware section) is complete: all metrics with
      mean ± std, sim-vs-hardware comparison table, and the honest
      limitations paragraph.
- [ ] `docs/PAPER_PITCH.md` updated with hardware numbers and at least one
      hardware-specific figure (the tracking overlay or the collision
      trace).
- [ ] A 3-minute demo video exists (from week 13, tightened) with a
      voiceover that follows the project's arc.
- [ ] Your one-paragraph resume summary and a 30-second spoken pitch are
      written and practiced.

## Why this week

The engineering is done; this week converts it into *credibility*. A
resume bullet and a paper pitch are different genres — both need to be
written deliberately, and the video is the artifact that survives a
30-second glance.

## Theory — writing honest results

### The structure that works for technical audiences

1. **The claim up front**: "A learned-augmented MPC achieves X on Y,
   measured on Z, compared against a PID baseline." (One sentence.)
2. **The system**: one diagram (the three-loop stack from week 1's sketch).
3. **The method**: ID → calibration → MPC → learning → safety, each with
   its verification step (this repo's docs already mirror this).
4. **The results**: table + figure, sim alongside hardware, *both*
   columns reported (never hide the sim).
5. **The limitations**: the bm/bl identifiability, the modest
   learning delta on smooth tracking, sim-vs-hardware gap. Three honest
   bullets.
6. **The next step**: one sentence (online adaptation, second spring,
   2-DOF arm — from week 14's known-issues list).

### The three numbers to memorize

Pick the three strongest, most defensible numbers and make them the
spine of every pitch:

- MPC vs. PID torque tracking (sim 5.8×; hardware ≥ 2× — report your
  actual).
- Disturbance steady-state error (sim 15×; hardware ≥ 4×).
- Collision detection latency (sim 102 ms; hardware < 150 ms).

If a hardware number is weaker than sim, *lead with the sim number and
show the hardware number beside it* — the pairing is a feature ("my
digital twin predicts the bench within 2–3×, and the ratios survive").

### Resume bullet anatomy

```
[Strong verb] [what you built] [how it works] [measured result]

"Built a torque-controlled series-elastic actuator from scratch —
  wrote the FOC current loop and an ADMM-solved MPC (2 kHz) on an STM32,
  calibrated the spring to 1.5%, identified the plant to <10% model
  error, and added a learned friction model enabling 150 ms collision
  detection — beating a PID baseline by [N]× on [metric]."
```

Rules: one bullet, numbers on the right, no filler ("passionate",
"hardworking" — delete). The measurable results carry it.

## Build plan

1. **RESULTS.md hardware section (3 h).** Assemble week-11/12/13/14
   numbers into the same schema as the sim section. Write the
   limitations paragraph. Include the sim-vs-hardware table.
2. **Paper pitch update (2 h).** `docs/PAPER_PITCH.md`: swap sim-only
   numbers for the paired sim+hardware story; add one figure (tracking
   overlay or collision trace) with a real caption. Trim to what you can
   defend in a 4-page format.
3. **Video (2.5 h).** Edit the week-13 footage into a 3-minute cut:
   (a) the rig and the stack, (b) the ID/calibration evidence,
   (c) tracking + disturbance, (d) the collision demo, (e) the numbers.
   Voiceover: write a 250-word script first, record in one take per
   section. Add the dashboard overlay for the collision.
4. **Resume + pitch practice (1.5 h).** Write the bullet (above), the
   one-paragraph summary, and the 30-second spoken pitch. Practice aloud
   until it's under 35 seconds without rushing. Have someone ask "what
   was the hardest bug?" — you have real answers (the ADMM solve-order
   bug, the discrete-wall instability, the negative-Jm excitation issue
   — all documented in the repo; tell the one that shows how you debug).
5. **Tracker (1 h).** Full-semester status; hand week 16 a concrete
   buffer list.

## Verification

- RESULTS.md hardware section read aloud end-to-end in < 5 min with no
  "um" (record yourself if needed).
- The three spine numbers roll off the tongue with their qualifiers
  ("in sim", "on hardware", "N=5").
- The video plays cleanly on a phone, sound audible, < 3:30.

## Pitfalls

- **The 10-slide deck of your own work.** For interviews you need 3
  numbers + 1 video + 1 story, not a slide dump. The paper pitch is for
  the conference; the 30-second pitch is for the recruiter.
- **Overclaiming the learning.** The honest delta (modest on smooth,
  real on disturbance/safety) is *more* credible than a faked 3×. The
  project's differentiator is the whole stack + the design rule
  (calibrate-vs-learn), not a single number.
- **Deleting the sim section** from RESULTS.md. Sim + hardware together
  is the strongest evidence; sim alone looks like homework, hardware
  alone looks lucky.
- **Polishing the video forever.** The week-13 footage is fine; ship a
  tightened cut this week, not week 17.
