# Week 9 — MPC Theory + Design Study in MATLAB

**Phase 3 · MPC** — ~11 hours

## Exit criteria (week done when…)

- [ ] You can derive the condensed MPC QP from the linear model on paper
      (the Y = Cx·F·x₀ + Cx·G·U factorization) and state what each matrix
      is.
- [ ] You can explain the ADMM iteration (u, z, λ updates) and *why*
      warm-starting + a fixed Cholesky factor make it embeddable.
- [ ] Using `model/matlab/mpc_design.m`, you've swept horizon/weights and
      can justify the chosen (N=20, Qy=3e4, Ru=5e-3, S_rate=0.3) on the
      identified plant.
- [ ] You've reproduced the sim's MPC-vs-PID gap in MATLAB on the linear
      plant (MPC well below PID) and understand *why* the gap exists.

## Why this week

Weeks 10–11 put MPC on the MCU. Before writing a line of firmware, this
week makes the *mathematics* yours: you should be able to re-derive the
whole formulation, because the firmware is just this math in C. The MATLAB
script is your design sandbox — it mirrors the Python MPC exactly (same
model, same cost, same ADMM), so anything you learn here transfers 1:1.

## Theory

### The condensed formulation

The linear prediction model (discretized by exact ZOH — see
`model/mpc.py::LinearSeaModel`):

```
x_{k+1} = Ad·x_k + Bd·u_k        x = [θm, ωm, θl, ωl]ᵀ
y_k = C·x_k                      y = τ_s = ks·(θm − θl)
```

Roll out N steps as a function of the initial state and the *whole input
sequence* U = [u_0 … u_{N−1}]ᵀ:

```
Y = Cx·F·x₀ + Cx·G·U

F = [Ad; Ad²; …; Adᴺ]            (block-column of state powers)
G = [Ad⁰Bd 0 … 0; Ad¹Bd Ad⁰Bd … 0; …]   (lower block-Toeplitz)
Cx = blkdiag(C, …, C)
```

**Condensing** means making U the optimization variable instead of
tracking x and u as separate sequences — the QP then has *only box
constraints*, which is what makes a cheap embedded solver possible.

### The QP

Cost (torque tracking + control effort + slew rate):

```
J(U) = ‖Cx·F·x₀ + Cx·G·U − yref·1‖²_Qy  +  ‖U‖²_Ru  +  S_rate·‖E·U − u_prev·e₁‖²
```

where E is the lower-bidiagonal difference matrix (E·U = [u₀−u_prev,
u₁−u₀, …]). Expanding and dropping constants:

```
J(U) = ½·Uᵀ·H·U + g(x₀, yref, u_prev)ᵀ·U + const

H = 2·(Gᵀ·Cxᵀ·Qy·Cx·G + Ru·I + S_rate·EᵀE)      (constant! LTI plant)
g = 2·(Cx·G)ᵀ·Qy·(Cx·F·x₀ − yref·1) − 2·S_rate·Eᵀ·e₁·u_prev
```

**The gradient is an affine function of (x₀, yref, u_prev)** — that's the
key fact for the firmware: the MCU never rebuilds H or G; it computes g
with three matrix-vector products against constants exported to
`mpc_model.h`.

Constraints:

```
|u_k| ≤ u_max,   |u_0 − u_prev| ≤ du_max      →  box: lo ≤ U ≤ hi
```

### ADMM for the box-constrained QP

Split: min f(U) + g_box(Z) s.t. U = Z, with f(U) = ½UᵀHU + gᵀU and
g_box = indicator of the box. The augmented-Lagrangian iteration:

```
U ← (H + ρI)⁻¹ · (−g + ρ(Z − λ))          # linear solve, ρ fixed
Z ← clip(U + λ, lo, hi)                    # box projection
λ ← λ + U − Z                              # dual update
```

Because H + ρI is constant, its Cholesky factor L (L·Lᵀ = H + ρI) is
computed **once**. Each iteration is then two triangular solves + a clip —
O(N²) total, ~25 iterations warm-started is enough in practice (this is
the same structure as OSQP/acados). **Warm-starting**: carry (Z, λ) from
the previous control period — consecutive QPs are nearly the same problem,
so the solver converges in a few iterations instead of dozens.

> ⚠️ A real bug found during development: the MATLAB port solved the
> triangular systems in the wrong order (`L \ (L' \ rhs)` instead of
> `L' \ (L \ rhs)`), silently solving (L'L)⁻¹ instead of (LL')⁻¹ = M⁻¹ —
> the ADMM then converged to a *worse* point and the controller commanded
> the wrong sign. `model/matlab/mpc_design.m` has the fix. If you ever
> port this solver yourself, test the linear solve against a known answer
> *first* (there's a pytest for exactly this).

### Why MPC beats PID (the intuition you'll present)

PID acts on the torque *error* it has; MPC acts on the torque *predicted*
10 ms ahead. Three structural advantages:

1. **It knows the resonance** — the model predicts the 18 Hz ringing, so
   the optimizer shapes the input to avoid exciting it (visible as
   anti-ringing input profiles on reference edges).
2. **It has integral-like action through the horizon** — the N-step plan
   reacts to steady-state offset *before* it accumulates (plus the learned
   feedforward in week 12 handles the static nonlinear part).
3. **It respects constraints by design** — current and slew limits are
   hard constraints in the QP, not saturation clamps that destabilize.

## Build plan

1. **Paper derivation (2 h).** Derive the condensed form by hand for N=2
   (two steps, scalar u). Write out H and g explicitly. Then check against
   `model/mpc.py::SeaMPC._g` — the code *is* the answer key.
2. **MATLAB design study (3 h).** Run `mpc_design` on the *identified*
   plant (edit the `p` struct with your week-7 numbers). Sweep:
   - N ∈ {10, 20, 40} — longer horizon = better lookahead, slower solve.
   - Qy/Ru ratio — higher = tighter tracking, more ringing.
   - S_rate — higher = smoother inputs, slower response.
   Record RMS error + peak error per config; pick the config that sits at
   the knee of the trade (the repo defaults are a good starting point, not
   an oracle).
3. **Reproduce the PID gap (2 h).** Add a PID to the MATLAB loop (or reuse
   the Python sim's PID trace); confirm MPC < PID on the same reference.
   This is your first "MPC beats PID" data point, in the design tool.
4. **Read the Python MPC carefully (2 h).** `model/mpc.py` end to end:
   condensation, bounds, the `_g` affine gradient, the learned-FF hook, and
   `export_to_c` (the code that generates the firmware headers). Understand
   *exactly* what the firmware will compute.
5. **Constraint behavior (1.5 h).** In MATLAB, drive a reference that
   violates u_max and du_max; confirm the solution stays feasible and the
   response degrades gracefully (this is the safety argument for MPC).
6. **Tracker (0.5 h).** Record the design-study table.

## Verification

- MATLAB MPC RMS < MATLAB PID RMS on the same reference (expect a 2–5× gap
  on the linear plant).
- You can write down H and g for N=2 without notes.
- The chosen (N, Qy, Ru, S_rate) config has a one-line justification.

## Pitfalls

- **Copying weights from the sim without re-checking.** The sim's weights
  were tuned on the nominal plant; re-tune on your identified plant (the
  procedure is the same, the numbers shift).
- **Believing the unconstrained optimum.** The box constraint (u_max,
  du_max) is doing real work — the unconstrained solution overdrives (a
  genuine finding during development: unconstrained u₀ = 49.6 A on a
  6 A limit). Always look at the constrained solution.
- **Horizon too short** (N < ~10) → the MPC can't see the resonance cycle
  (T_res ≈ 55 ms ≈ 110 steps!); the finite-horizon truncation then
  produces weird terminal behavior (the optimizer "wastes" the tail —
  visible as a dive to the constraint at horizon end). N=20 is a
  compromise; N=40 is cleaner but slower to solve.
