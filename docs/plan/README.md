# Semester Plan — Building the SEA-MPC Project

This is the week-by-week build plan for bringing the repo (`model/`,
`learn/`, `sim/`, `firmware/`, `hardware/`) to life on the bench. Each week
is its own document (`docs/plan/weekNN.md`) with:

1. **Exit criteria** — the concrete, checkable definition of "week done".
2. **Theory** — the depth needed for *that* week's work (derivations,
   formulas, physical intuition), tied to the repo files that implement it.
3. **Build plan** — exactly what to make/do and how, in order.
4. **Verification** — how to prove the week's work.
5. **Pitfalls** — the failure modes that actually eat students' weekends.

The plan assumes **~10–12 focused hours/week** alongside coursework.
Phases have built-in slack; if you fall behind, the "cut here" note in each
phase tells you what to drop without breaking the story.

## The arc (16 weeks)

| Phase | Weeks | Theme | Milestone |
|---|---|---|---|
| 0 | 1–3 | Foundations: repo, toolchain, encoders | — |
| 1 | 4–5 | Motor control + mechanical build | **M0, M1** |
| 2 | 6–8 | Calibration, system ID, torque loop | **M2, M3** |
| 3 | 9–11 | MPC on hardware | **M3 done** |
| 4 | 12–14 | Learning, impedance, safety, rigor | **M4, M5** |
| 5 | 15–16 | Writeup, paper pitch, final demo | **M6** |

## The weekly map

| Wk | Title | Core deliverable | Theory focus |
|----|-------|------------------|--------------|
| 1 | Launch & toolchain | sim re-run, repo tour, environment | SEA + PMSM/dq model, why MPC |
| 2 | CubeMX project + USB telemetry | blinking firmware streaming telemetry | STM32 clocks, TIM1 PWM, ADC, USB CDC |
| 3 | Encoders & velocity | both AS5048A at 2 kHz, velocities | SPI, quantization, Savitzky–Golay |
| 4 | FOC current loop | current loop closed at 10 kHz | two-shunt sensing, SVPWM, dq PI tuning |
| 5 | Mechanical build | rig assembled, resonance measured | torsion-bar mechanics, blocked-output rig |
| 6 | Spring calibration | ks to ±2% from weights | least squares, model selection, observability |
| 7 | System ID | Jm/Jl/friction from chirp data | integrated LS, conditioning, PE condition |
| 8 | Torque loop (PID) | PID torque tracking on the bench | loop shaping, resonance, fair comparison |
| 9 | MPC theory + MATLAB | weights/horizon chosen in MATLAB | condensed MPC, QP, ADMM derivation |
| 10 | MPC on firmware | MPC at 2 kHz on the STM32 | real-time implementation, generated headers |
| 11 | MPC benchmark | MPC vs PID table on hardware | disturbance rejection, stats, artifacts |
| 12 | Learned residual | feedforward on hardware, gain measured | basis regression, R², held-out, honesty |
| 13 | Impedance + collision | grab demo, <150 ms detection | impedance, passivity, momentum observer |
| 14 | Repeatability & edge cases | N-run statistics, robustness | experimental design, saturation |
| 15 | Writeup & pitch | hardware RESULTS.md, paper pitch, video | honest result reporting |
| 16 | Buffer + final demo | catch-up + polished demo | — |

## How to use this plan

- **Each week, start by reading that week's document** (15 min), then do the
  build plan in order. Never skip the verification section — it's how you
  know you're actually on pace.
- **Tick exit criteria in `TRACKER.md`** as you hit them; the tracker is
  the single source of truth for "am I behind?"
- **Theory first, then code.** The theory sections are sized so that 30–45
  min of reading makes the day's coding obvious instead of cargo-culted.
- **The sim is your oracle.** Every hardware number you measure should be
  compared against the digital twin (`model/plant.py`, `results/`). If the
  bench and the twin disagree by >10% on a controlled experiment, stop and
  find out why — that investigation *is* the project's value.

## The one-line version of the whole semester

> Weeks 1–4 make a motor that spins under current control; weeks 5–8 make
> that motor a *calibrated, identified* torque source; weeks 9–11 replace
> the torque PID with an MPC that beats it; weeks 12–13 add the learned
> friction model and the safety layer; weeks 14–16 prove it didn't happen
> by luck and write it up.

## Hours budget per phase

| Phase | Weeks | Hours | Fallback if behind |
|---|---|---|---|
| 0 Foundations | 1–3 | ~33 | Week 2's ADC work can fold into week 4 |
| 1 Motor + build | 4–5 | ~22 | Use a printed hub + zip-ties for the rig; skip the fancy base plate |
| 2 Cal + ID + torque | 6–8 | ~33 | ID can be run on sim data if bench logging lags; catch up in week 16 |
| 3 MPC | 9–11 | ~33 | Week 11's statistics can shrink to a 3-run table |
| 4 Learning + safety | 12–14 | ~33 | If week 14 slips, the repeatability run collapses into week 15 |
| 5 Writeup | 15–16 | ~22 | The paper pitch is skippable; RESULTS.md + video are not |

Total ≈ 176 hours ≈ a real semester's worth of project work.
