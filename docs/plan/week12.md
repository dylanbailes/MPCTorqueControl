# Week 12 — Learned Disturbance Feedforward (M4)

**Phase 4 · Learning, impedance, safety** — ~11 hours

## Exit criteria (week done when…)

- [ ] Motor-side residual logged under rich excitation; the basis-function
      model fit on half the data, held-out R² ≥ 0.5 on the other half.
- [ ] `results/learned_model.h` regenerated; feedforward enabled in
      firmware (the `learned_feedforward()` hook in `tasks.c`).
- [ ] Measured improvement over plain MPC on at least one metric
      (targets from sim: disturbance steady-state 1.08 → 0.91 mN·m;
      edge-rich overall 28 → 24 mN·m). If hardware shows *no* improvement,
      you've found a real limitation — document it, don't fake it.
- [ ] You can explain the design split (learned vs. calibrated) in one
      minute — this is the project's thesis statement.

## Why this week

M4. This is the "learning" in the project title, and the part that makes
it a research-y resume item rather than a textbook MPC demo. The honest
framing (from the sim results): the learned model's *headline* gain on
smooth tracking is modest (~15%) because deflection-feedback torque
control already rejects friction automatically; its real value is in
disturbance steady-state error, edge tracking, and (week 13) enabling a
collision observer that doesn't false-trigger. Know this before you start,
so you measure the right things.

## Theory

### What to learn, and why (the design split)

From week 6: the spring curve is *calibrated* (external reference). The
thing left to learn is the **motor-side disturbance** — everything between
the commanded current and the torque it actually produces:

```
τ_dist(θm, ωm, iq) = Kt·iq − (Jm·dωm/dt + τ_s + bm·ωm)      [from the EOM]
                   = friction(ωm) + cogging(θm) + ripple(iq, θm) + …
```

Why not learn the whole dynamics? Because of what's observable: with only
motor-side measurements, friction and cogging are cleanly separable (they
depend on ωm vs θm), but a *spring nonlinearity* is invisible to a linear
observer (it would leak into the residual and corrupt the fit — the
"observability trap" of week 6). The principled rule:

> **Calibrate what is not observable from motor-side data (the spring
> curve); learn what is (friction + cogging + ripple).**

This rule is the one-sentence thesis of the whole project and should be in
your writeup, your paper pitch, and your interview answers.

### The model and the fit

Basis functions in (θm, ωm) — matching `learn/residual.py`:

```
τ_hat_dist = Σ_j β_j · φ_j(θm, ωm)
           = β₁·tanh(ωm/ε)                    # Coulomb-ish
           + β₂·ωm                              # viscous
           + β₃·exp(−(ωm/w_st)²)·tanh(ωm/ε)    # Stribeck peak
           + β₄·sin(6θm) + β₅·cos(6θm)          # 6th-harmonic cogging
           + β₆·sin(12θm) + β₇·cos(12θm)        # 12th-harmonic cogging
           + β₈·iq·sin(6θm) + β₉·iq·cos(6θm)    # current ripple
```

Linear in β → **ordinary least squares**, cheap, no neural net needed (a
net would overfit 9 coefficients' worth of signal; this is a case where
the *structure* is known — use it). The residual samples come from the
week-11 logs (or a fresh rich-excitation run): compute τ_dist from the
equation above with the *measured* iq and ωm, then regress.

**Honesty tools:**

- **Held-out R²**: fit on the first half of the log, evaluate on the
  second. R² = 1 − SSE_resid/SSE_mean. Sim value: 0.62 (the rest is
  measurement noise and current-loop lag — a bench R² of 0.4–0.7 is
  expected and fine).
- **Ablation**: measure MPC and MPC+learned on the *same* bench script
  from week 11. Report the delta per metric. If the delta is ~0 on
  smooth tracking but real on disturbances, that's the correct, honest
  result — and it's exactly the sim's result.

### Embedding as feedforward

The learned model is *not* in the QP (that would double the solve time
and complicate the ADMM). It's an additive feedforward:

```
u_total = u_mpc + u_ff(θm, ωm, iq),   clipped to ±u_max
```

The MPC handles dynamics and constraints; the feedforward cancels the
static disturbance at the source. This is the standard "MPC + disturbance
compensation" architecture in industry (the same pattern as DOB/MFC
disturbance observers), and it's what `SeaMPC.step` already implements
(the `ff` hook) and `tasks.c` calls `learned_feedforward()`.

## Build plan

1. **Residual data (2 h).** Reuse the week-7 excitation or the week-11
   logs. Compute τ_dist per sample from the identified EOM. Plot it vs.
   ωm (should show the friction curve) and vs. θm at constant speed
   (should show the cogging sinusoid) — these two plots are your
   "the disturbance exists and it looks like this" evidence.
2. **Fit + evaluate (2 h).** `learn/residual.py` fit on half, R² on the
   other half. Report coefficients; sanity-check signs/magnitudes against
   `model/plant.py` truth (e.g. τ_c ≈ 8e-3 N·m, cogging amplitude ≈
   3e-3 N·m).
3. **Export (1 h).** Generate `results/learned_model.h`; copy to
   firmware; review `learned_feedforward()` in `tasks.c` against the
   Python `ff` function for 1:1 agreement (host test like week 10).
4. **Benchmark delta (3 h).** Week-11 script with `MPC` and `MPC+learned`
   cells, N=3. Table: smooth, edges, disturbance. The delta per metric is
   the week's headline number.
5. **Failure-mode check (1.5 h).** Feedforward clipping: verify u_total
   never exceeds u_max (the clip is in the Python and C). Verify the FF
   doesn't fight the MPC on the disturbance step (settle time should not
   get worse).
6. **Write-up (1.5 h).** Hardware results into `docs/RESULTS.md`; the
   thesis paragraph drafted (calibrate-vs-learn rule). Tracker: M4
   progress.

## Verification

- Held-out R² ≥ 0.5 (report the number; 0.4 is still publishable-honest,
  < 0.3 means the residual computation is wrong — check ωm sign and ks).
- MPC+learned ≥ MPC on at least one metric by ≥ 5% relative (sim
  deltas: −15% overall edges, −16% disturbance steady).
- No regression on the other metrics (> −5%).
- Coefficients within 2× of sim truth.

## Pitfalls

- **Learning the observer's own error.** τ_dist must be computed from the
  *calibrated* spring curve (week 6), never from the controller's
  observer — otherwise you're fitting your own measurement error.
- **Velocity filter lag** (week 3) biases the friction coefficients
  (lagged ωm shifts the curve). Use the same filter at fit time and at
  runtime — the firmware must apply the identical filter to ωm before
  `learned_feedforward()`.
- **Overfitting the noise**: with 9 coefficients and thousands of samples,
  R² on the fit set will look great — only the *held-out* R² is honest.
- **Expecting a big smooth-tracking win.** The sim says ~15% overall; if
  you present a 3× improvement on smooth tracking, you've almost surely
  measured something wrong (or overfit). The honest story is: small,
  real gains everywhere, big enabler for safety (week 13).
