# Parts — verified spec sheets

**Planning notes:** these supplier/specification notes were recorded during
earlier design work and include legacy GM5208 assumptions. They are not
bench validation or a fresh purchasing audit. For the current 4015 simulation
scenario, see [results](../../docs/RESULTS.md) and
[implementation status](../../docs/STATUS.md).

One file per major part (or subsystem) of the SEA torque-control rig.
These files are the **single source of truth** for what to buy, why, and
how to verify it. `hardware/BOM.md` is the shopping list (quantities,
prices, links); the files here carry the specs, acceptance checks,
alternatives, and the audit verdicts. If the two disagree, the part file
wins.

Every spec was verified in Aug 2026 against the manufacturer's own pages /
datasheets (links in each file) or re-derived from the design tools in this
repo (`python hardware/spring_design.py`).

## The decision table (from the v4 audit)

| Part | Verdict | Rule |
|---|---|---|
| B-G431B-ESC1 | **USE** | Only board the firmware targets. Caveat: current sensing is scaled ±40 A (~20–30 mA/LSB) — expect a 2–5 mN·m torque-quantization floor; current-loop acceptance is **±2 A**, not ±5 A |
| 4015 BLDC + integrated MT6701 | **USE (selected)** | 0.30 N·m at 24 V; 1.4 A rated, 4 A max; 10 mm OD / 7.5 mm hollow bore; ABZ + I²C exposed. Use ABZ for real-time motor feedback and I²C for diagnostics |
| MT6701 motor encoder | **USE** | ABZ is the deterministic motor feedback path; I²C is diagnostic/configuration only |
| Generic 5208 clone | Acceptable | Cheapest (~$20–35) but shaft is solid 6/8 mm and KV/R vary — pass the acceptance checks before committing the hub design |
| Salvaged DJI gimbal motors | **Avoid** | Nonstandard shafts/connectors; more bench time than the dollars saved |
| High-KV multirotor outrunners | **Avoid** | KV 300+, higher cogging/ripple — eats torque authority, noisier ID |
| 4006/4108 gimbal motors | **Avoid** | Kt ≈ 0.03–0.05 → can't reach the 0.35 N·m envelope at ≤ 2 A |
| AS5048A + 6×3 mm N45 magnet | **USE** | 14-bit, ±0.05°, SPI load-side encoder; magnet must be diametric (DOA check) |
| 24 V / 5 A PSU, XT60, bullets | **USE** | Within ESC1 3S–6S range; ≥ 5 A covers the ~2 A motor |
| 2.5 mm torsion bar (Option A) | **USE** | k = 1.000 N·m/rad at 304 mm, SF ≈ 5×; Option B springs acceptable |
| 8 mm load shaft + 608ZZ ×2 | **USE** | 608ZZ bore = 8 mm |
| 2020 extrusion + M5 T-nuts | **USE** | European 2020 = 6 mm slot |
| Weights + luggage scale | **USE** | Calibration apparatus (weeks 6, 11) |

## Requirements vs the chosen combo (4015 + MT6701 ABZ/I²C + AS5048A SPI + B-G431B-ESC1)

The project requirements, exactly as the design code encodes them, and
whether the combo satisfies each.

| # | Requirement | Value (source) | Board | Motor | Verdict |
|---|---|---|---|---|---|
| 1 | FOC drive on STM32G431 | 3-ph BLDC; 10 kHz current loop (TIM2), 2 kHz torque loop (TIM3) — `docs/DESIGN.md`, `firmware/` | ✓ G431CB, L6387, STL180N6F7 | ✓ 24N/22P BLDC | PASS |
| 2 | 24 V DC bus | Vbus = 24 V (`model/plant.py`); ESC input 3S–6S | ✓ 9.9–25.2 V | ✓ rated 3–5S, safe at low duty | PASS |
| 3 | Torque envelope | τ_s ≤ 0.35 N·m, deflection ≤ 0.35 rad (`hardware/spring_design.py`); reference peaks ≈ 0.4 N·m (`sim/run_experiments.py`) | ✓ 40 A ≫ need | ⚠ 0.35 N·m needs the full 1.75 A stall — only if R_line ≈ 13.7 Ω *and* Kt ≈ 0.2; **fails if R_line ≈ 25.6 Ω** (0.9 A → ≈ 0.18 N·m) | CONDITIONAL — gate = DMM R (DOA #8) |
| 4 | Current authority | u_max = 4 A @ Kt 0.1 → 0.4 N·m (`model/mpc.py`); ≈ 2 A at real Kt ≈ 0.2 | ✓ | ✓ 1.75 A stall | PASS (re-export u_max) |
| 5 | Current-loop accuracy | iq < 5 % at ±2 A, 10 kHz (TRACKER, week04) | ⚠ ±40 A sensing → 20–30 mA/LSB vs the 100 mA (5 %) budget — OK | ✓ | PASS (retune PI from real R, L) |
| 6 | Encoders | Motor-side MT6701 ABZ + I²C; load-side AS5048A 14-bit SPI (`docs/DESIGN.md`) | ✓ timer encoder + I²C + SPI | ✓ integrated motor encoder + load encoder/magnet | PASS, verify module voltage/pinout |
| 7 | Resonance | two-mass ω ≈ 115 rad/s (18 Hz), lightly damped; must act at oscillation speeds ≈ 40 rad/s | ✓ 2 kHz MPC | ✓ no-load ≈ 500 RPM (52 rad/s); thin torque margin in transients | PASS |
| 8 | Low cogging | cogging/ripple ~10–15 % of rated, learned + fed forward (`learn/residual.py`) | — | ✓ gimbal class; real cogging > sim's 4.5 mN·m | PASS (hardware RMS will exceed sim's 4 mN·m — target = beat PID) |
| 9 | Torque tracking | MPC < PID on the rig (sim: 4.0 vs 32.9 mN·m RMS — `docs/RESULTS.md`) | — | — | CONDITIONAL on #3; floor ≈ current quantization 2–5 mN·m |
| 10 | Safety | momentum observer, stall latch (`docs/DESIGN.md` §6, `firmware/.../safety.c`) | ✓ runs on MCU | — | PASS |
| 11 | Structure | 15 mm hollow shaft, parametric hub, magnet plug (v4 audit) | — | ✓ | PASS |
| 12 | Identifiable | R, L, Kt, J from bench ID (`learn/system_id.py`) | — | ✓ (expect R ≈ 13.7 Ω, Kt ≈ 0.2) | PASS |

**Bottom line:** the board meets every requirement. The motor meets every
requirement *except the torque envelope, which is a conditional pass*: it
lands exactly on 0.35 N·m at the 1.75 A stall current (Kt ≈ 0.2,
R_line ≈ 13.7 Ω) with zero margin, and fails if the unit measures ≈ 25.6 Ω.
The DMM test in DOA #8 decides it — measure before assembly, and fall back
to the −12 or a smaller envelope if it fails.

**Must-do before the torque-loop milestone (week 8):** measure R on
arrival; identify Kt in weeks 6–7; re-export `results/mpc_model.h` and
`results/learned_model.h` (Kt, u_max ≈ 2 A, du_max); retune the current-loop
PI from the real R and L; keep acceptance targets at ±2 A.

## Files

| File | Covers (BOM rows) |
|---|---|
| `esc1.md` | B-G431B-ESC1, ST-Link clone (optional), 5 V buck (optional) |
| `motor.md` | Selected 4015 + MT6701 motor, AS5600 alternative, and legacy motor alternatives |
| `encoders.md` | MT6701 ABZ/I²C motor encoder, AS5048A load encoder, diametric magnets, magnet plug |
| `power.md` | 24 V PSU, XT60, bullets, breadboard/jumpers, USB cable, solder |
| `spring.md` | torsion bar / extension springs (design math) |
| `drivetrain.md` | load shaft, 608ZZ, hub plates + plug, dowel pins, M3 fasteners, load disc, 2020 base, filament |
| `calibration.md` | weight set, luggage scale, string/eyelet |

## How to verify

- Motor, encoder, ESC1 numbers: manufacturer pages / datasheets (linked in
  each file).
- Spring stiffness and load inertia: `python hardware/spring_design.py`
  (the numbers in `spring.md` were captured from its output).
- Torque-envelope math: `k = G·J/L`, `τ = Kt·i`, `I_stall = V_bus / R_line`.
