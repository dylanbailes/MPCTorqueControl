# Week 1 — Launch, Toolchain, and the Physics of the Rig

**Phase 0 · Foundations** — ~11 hours

## Exit criteria (week done when…)

- [ ] `pip install -r requirements.txt` clean on a fresh venv.
- [ ] `python -m sim.run_experiments` runs end-to-end and `results/results.json`
      regenerates with numbers close to the committed ones (MPC ≈ 5.7 vs
      PID ≈ 32.9 mN·m on smooth tracking).
- [ ] `pytest test/ -q` → 33 passed.
- [ ] You can explain, out loud, the **three loops** of the stack and what
      each one does, and can point at the file that implements each.
- [ ] You have ordered the hardware from `hardware/BOM.md` (it arrives before
      week 4 — this is the long-lead item).

## Why this week

Everything else assumes you can run the code and understand what it does.
This week converts the repo from "someone else's project" into *your*
model. Ordering the BOM now is the single most important scheduling action
of the semester.

## Theory — the physical picture

### The series-elastic actuator

A series-elastic actuator inserts a compliant element (here: a torsion bar)
between the motor and the load:

```
[BLDC] --Kt·iq--> Jm ──[spring k_s]── Jl ──> output (load disc)
```

The spring is a **torque sensor by construction**: measure the deflection
Δθ = θm − θl with two encoders, multiply by the calibrated stiffness,
and you have the torque transmitted to the load:

```
τ_s = k_s · (θm − θl)
```

Three consequences you'll feel all semester:

1. **The spring filters impacts** — that's why SEAs are safe: a collision
   compresses the spring before the motor feels it, buying the controller
   milliseconds to react.
2. **Torque control is now a position-difference problem** — you command
   Δθ, not force. This is exactly where a naive PID underperforms: the
   two-mass system has a lightly damped resonance at

   ```
   f_res ≈ (1/2π)·√(k_s·(Jm + Jl)/(Jm·Jl))   ≈ 18 Hz here
   ```

   push torque too hard and the spring rings; push too softly and you have
   bandwidth you paid for but can't use.
3. **The torque estimate is only as good as the spring calibration** — a
   2% stiffness error is a 2% torque error everywhere. That's why week 6
   exists.

### The PMSM model and why we control in dq

The motor is a permanent-magnet synchronous machine. The phase voltages
relate to currents and back-EMF through the electrical dynamics:

```
v_a = R·i_a + L·di_a/dt + e_a(θe)
```

The back-EMF terms are sinusoidal in the rotor angle, which makes
three-phase PID control a losing game. The fix is the **Clarke transform**
(3-phase → stationary αβ):

```
i_α = i_a
i_β = (i_a + 2·i_b)/√3          (balanced, i_a+i_b+i_c = 0)
```

then the **Park transform** (stationary → rotor frame, at electrical angle θe):

```
i_d = i_α·cos θe + i_β·sin θe
i_q = −i_α·sin θe + i_β·cos θe
```

In the rotor frame the dynamics become (nearly) DC:

```
v_d = R·i_d + L·di_d/dt − ωe·L·i_q
v_q = R·i_q + L·di_q/dt + ωe·L·i_d + Ke·ωm
```

Now **i_q is proportional to torque**: τ_m = (3/2)·p·λ·i_q = Kt·i_q, and
i_d is a magnetizing current we drive to zero. Two PI controllers in dq
replace three impossible phase controllers. This is implemented in
`model/foc.py` (Python reference) and `firmware/Core/Src/foc.c` — read both
side by side this week.

### Why MPC (one paragraph)

The torque loop's job: given τ_ref, produce i_q_ref such that the *spring
torque* tracks, while respecting the current limit and slew limit. PID
reacts to the error it already has; **MPC predicts** — it uses a model of
the two-mass system to plan a whole input sequence over the next 10 ms
(N=20 steps at 2 kHz), picks the first action, and replans. With a known
plant (that's weeks 6–7) MPC is dramatically better on disturbance
rejection and constraint handling — 15× on the steady-state disturbance
error in sim. The price: a QP solve every 0.5 ms on a $20 MCU (week 9–10).

## Build plan

1. **Environment (2 h).** Create a venv, install `requirements.txt`
   (numpy/scipy/matplotlib/pytest). Confirm Python ≥ 3.10.
2. **Repo tour (2 h).** Read `README.md`, then trace one full experiment:
   `sim/run_experiments.py` → `sim/bench.py` → `model/mpc.py` →
   `model/plant.py`. Open each plot in `results/plots/` and connect it to
   the code that made it. Make a one-page architecture sketch in your own
   words (this becomes the first slide of your final talk).
3. **Run everything (1.5 h).** `python -m sim.run_experiments` (≈4 min),
   `pytest test/ -q` (≈1 min), `python hardware/spring_design.py`.
4. **Read the firmware (2 h).** `firmware/README.md`, then
   `foc.c` + `admm.c` + `tasks.c`. You don't need to understand every line —
   just the loop structure and where the generated headers
   (`mpc_model.h`, `learned_model.h`) plug in.
5. **Run the MATLAB scripts (1 h, if you have MATLAB).**
   `addpath('model/matlab'); sea_plant_model; mpc_design; system_id;` —
   confirms the second toolchain works before you need it.
6. **Order hardware (2 h).** Work through `hardware/BOM.md` and
   `hardware/spring_design.py`. Order: B-G431B-ESC1, motor, 2× AS5048A,
   24 V PSU, drill rod, load-disc material. Note lead times; if the motor
   is back-ordered pick a Kt ≈ 0.1 N·m/A equivalent (the sim tolerates
   ±20% — re-run the sim with the new Kt to confirm).
7. **Journal (0.5 h).** Start `docs/plan/TRACKER.md` habits: tick week 1.

## Verification

- `pytest test/ -q` → 33 passed.
- `results/results.json` regenerated; `tracking.smooth.MPC.rms_error_mNm`
  ≈ 5.7 ± 0.5.
- You can answer: "Where does the 18 Hz resonance come from, and which file
  would I edit to change it?"

## Pitfalls

- **Don't optimize the sim yet.** It runs in 4 minutes; that's fine. Speed
  comes in week 10 if you need it.
- **Don't skip ordering.** Every later week assumes the hardware is on the
  bench. The single biggest schedule killer in this project is a
  back-ordered motor discovered in week 4.
- **Don't read the firmware cover to cover.** Read for structure; details
  come when you're debugging that specific loop.
