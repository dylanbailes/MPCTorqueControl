# Week 7 — System Identification (M2)

**Phase 2 · Calibration, ID, torque loop** — ~11 hours

## Exit criteria (week done when…)

- [ ] Jl identified to ±5%, ks ±2% (from week 6), Jm ±20%, from a single
      logged excitation run.
- [ ] Open-loop model validation: simulate the identified model against a
      *fresh* hardware log (different excitation) — RMS mismatch < 10% on
      θm, θl, Δθ.
- [ ] The identified parameters are written back into the sim and the MPC
      model (`results/mpc_model.h` regenerated).
- [ ] You understand *why* bm/bl are poorly identifiable and can say so in
      one sentence (this will be in your writeup's limitations section).

## Why this week

The MPC (weeks 9–11) is only as good as its model. This week converts the
bench into a measurement instrument: one excitation run, one least-squares
fit, and the model the controller will trust. The *method* matters as much
as the numbers — this is the week where the "integrated least squares vs.
naive differentiation" choice (a real, documented failure mode) earns its
keep.

## Theory

### The integrated-equation trick

The load-side dynamics (with τ_s known from week 6):

```
Jl·dωl/dt = τ_s − bl·ωl − τ_c·tanh(ωl/ε)
```

Naive LS differentiates the quantized ωl → noise amplification (the
encoder staircase from week 3 blows up under differentiation). Instead,
**integrate both sides** over the experiment:

```
Jl·(ωl(t) − ωl(0)) = ∫τ_s dt − bl·∫ωl dt − τ_c·∫tanh(ωl/ε) dt
```

Now every term is a *cumulative sum* of measured signals — integration
averages the noise instead of amplifying it. The equation is linear in the
unknowns (Jl, bl, τ_c):

```
y = [ωl − ωl(0), ∫ωl dt, ∫tanh(ωl/ε) dt] · [Jl, −bl, −τ_c]ᵀ
```

This is exactly the regression `learn/system_id.py::identify_from_data`
and `model/matlab/system_id.m` implement (Xl, Yl; Xm_, Ym). The motor side
is the same with the motor torque balance:

```
Jm·dωm/dt = Kt·iq − τ_s − bm·ωm − τ_c,m·tanh(ωm/ε)
```

### Conditioning and persistence of excitation

Least squares is only as good as the regressor matrix's conditioning. The
motor-side columns `[ωm−ωm(0), ∫ωm dt, ∫tanh(ωm/ε) dt]` become nearly
collinear if the excitation doesn't move the motor through a wide velocity
range — the classic failure is **negative identified inertia** (a real bug
hit during development when the excitation was a bare chirp: the MATLAB ID
returned Jm = −2.8e-5). The fix is the excitation itself, mirroring
`collect_excitation`: **chirp (0.3→10 Hz) + PRBS noise + slow square**,
clipped to ±1.5 A. The square term drives large velocity excursions
(Jm is observable from big accelerations), the chirp covers the spring
dynamics, and the PRBS whitens the residuals. Rule: **if a parameter comes
out negative or 10× its expected value, suspect the excitation, not the
physics.**

### What's identifiable and what isn't

From the sim's honest numbers (`docs/RESULTS.md`):

| Parameter | Sim accuracy | Why |
|---|---|---|
| ks | 1.5% | directly measured (week 6) |
| Jl | 1.3% | load is big, well-excited, low friction |
| Jm | 9.3% | motor is small; cogging/friction correlated with its motion |
| bm, bl | poor (100s of %) | viscous terms are small vs. Coulomb friction at bench speeds |

The deep point: **Jm, bm, bl barely matter for torque control** — the MPC
needs ks and Jl (the compliant mode), and Kt (which enters via the current
loop). Don't chase bm; report it as poorly observable and move on. This is
a *limitations* paragraph in the writeup, not a flaw.

## Build plan

1. **Logging rig (2 h).** Extend the telemetry: log at 2 kHz for 8 s —
   θm, θl, ωm, ωl (filtered), iq, u (the command), τ_s_hat, timestamps.
   Fixed sample rate, no gaps (check dropped-frame counter from week 2).
   Save to CSV with a header.
2. **Excitation task (1.5 h).** Implement the chirp+PRBS+square current
   command in firmware (precompute the chirp table or generate on the fly;
   the PRBS can be a short LFSR — deterministic, same seed every run).
   Same signal the sim uses (`learn/system_id.py::collect_excitation`).
3. **First run + sanity (1.5 h).** Run it. Immediately check in the
   dashboard: did θm actually move through a wide range? Did iq saturate?
   Is the log gap-free? Fix and re-run until the log is clean.
4. **Fit (2 h).** Run the CSV through `learn/system_id.py::identify_from_data`
   (write a small `scripts/identify_from_log.py` wrapper that reads your
   CSV format). Report Jm, Jl, bm, bl, τ_c, and the residuals.
5. **Model validation (2 h).** Fresh excitation run (different seed/pattern).
   Simulate `model/plant.py` with the identified params against the fresh
   log. Compute RMS mismatch on Δθ and ωl. Target < 10%. If you're at
   20–30%, check: did you use the right Kt? Is the base flexing (week 5)?
   Is the current loop actually tracking (week 4)?
6. **Write back (1.5 h).** Update the plant params in the repo
   (`model/plant.py` defaults stay as the *nominal* design values — add an
   `identified.json` or a params override file so the sim can run "as
   built"). Regenerate `results/mpc_model.h` with the identified model
   (the MPC export takes the model params — see `SeaMPC.export_to_c`).
7. **Tracker (0.5 h).** Record all parameters + validation mismatch.

## Verification

- Validation RMS < 10% on a fresh log (the single most important number
  this week).
- Jl within ±5% of the design value (1.2e-3 kg·m²) if your disc matches
  the sizing; if it doesn't, your disc is the truth, not the design.
- `mpc_model.h` regenerated from identified params; diff shows the change.

## Pitfalls

- **Differentiating the encoders** for ID (instead of integrating the
  equations) → garbage Jm. If your Jm is negative or 10×, you're either
  differentiating or the excitation is too weak.
- **Saturated iq.** If the command clips, the plant sees a different input
  than you logged. Log u *and* iq; fit with the measured iq (the repo does).
- **Sample-rate drift.** A missing frame silently corrupts every
  cumulative sum after it. Check the drop counter on every run.
- **Ignoring the offset/preload** in τ_s_hat: the week-6 calibration
  includes the bias term; carry it through.
