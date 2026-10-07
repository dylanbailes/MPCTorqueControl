# 4015 BLDC — motor side of the SEA

> Selected configuration: 4015 motor with integrated **MT6701 magnetic encoder**.
> Torque source: `τ_m = Kt · i_q` drives the spring. The motor-side encoder
> is used through its ABZ output for real-time control; I²C is retained for
> commissioning and diagnostics.

## Selected motor specification (Aug 2026 Amazon listing / as-built model)

| Parameter | Value | Source |
|---|---|---|
| Motor | 4015 BLDC, 24N/22P | Selected Amazon listing |
| Torque envelope | **0.30 N·m at 24 V** | Selected motor listing |
| Rated current | **1.4 A** | Selected motor listing |
| Maximum current | **4 A** | Selected motor listing |
| KV | **61 RPM/V** | Selected motor listing |
| Winding resistance | **4.8 Ω** | Selected motor listing / as-built model |
| Wound-phase inductance | **2.6 mH** | Selected motor listing / as-built model |
| Shaft | **10 mm OD / 7.5 mm hollow bore** | Selected motor listing |
| Motor encoder | **Integrated MT6701**, ABZ + I²C exposed | Selected motor listing |
| Encoder angle data | 14-bit absolute internally; ABZ programmable up to 1,024 PPR | MT6701 datasheet |
| Encoder supply | 3.3–5 V sensor supply; verify module logic level | MT6701 datasheet / module |
| Encoder speed / delay | Up to 55,000 RPM; output delay <5 µs (device specification) | MT6701 datasheet |

## Encoder-interface decision

The integrated MT6701 exposes both **ABZ** and **I²C**. The final design uses:

- **ABZ for the motor-side real-time loop:** connect A/B to an STM32 timer in
  quadrature encoder mode and Z to an index input (or GPIO/timer index input).
  Configure the highest available ABZ resolution, preferably 1,024 PPR, and
  use 4× decoding for 4,096 counts/revolution.
- **I²C for commissioning/diagnostics:** use it to verify absolute angle,
  zero offset, configuration, and ABZ-count agreement. It is not the primary
  2 kHz FOC/torque-loop feedback path.
- **Load-side encoder:** retain the separate AS5048A on SPI for the load angle.
  Spring torque remains `τ_s = k_s(θ_m − θ_l)`.

ABZ does not expose the full 14-bit absolute resolution: 1,024 PPR with 4×
quadrature is 4,096 counts/revolution. That is intentional—the timer-based,
deterministic interface is preferred for motor feedback, while the load-side
AS5048A remains the torque-critical measurement.

Before energizing the motor, verify that the module's A/B/Z outputs are 3.3 V
compatible. If they are 5 V push-pull, use level translation; if open-drain,
use pull-ups to 3.3 V. Confirm A/B phase order, one Z pulse/revolution, magnet
type, and air gap.

## Design implications (the motor-model finding)

- The 4015 build uses the identified model values `R=4.8 Ω`, `L=2.6 mH`,
  `Kt≈0.1562 N·m/A`, `Jm≈3e-5 kg·m²`, with MPC configuration `N=30` and
  `u_max=3 A`. The 0.30 N·m motor envelope is compatible with the selected
  current limit; verify actual Kt and current behavior during bring-up.
- The motor's hardware maximum is 4 A, while the exported MPC uses a 3 A
  current limit to stay inside the tested simulation envelope. Do not raise
  `MPC_U_MAX` without repeating the current, thermal, and resonance checks.
- Published motor constants are treated as initial values; measure phase
  resistance, identify Kt/Jm, and re-export the generated model headers before
  final results.

## Encoder alternatives on the selected motor

| Option | Interface/use | Verdict |
|---|---|---|
| **MT6701** | 14-bit internal angle; ABZ + I²C exposed | **Selected** — ABZ is deterministic for FOC; I²C is useful for diagnostics |
| AS5600 | 12-bit contactless encoder, typically I²C/PWM/analog | Not selected — lower resolution and less suitable as the primary 2 kHz motor-feedback path |

The AS5600 option would require a different firmware path and must not be
assumed to share the MT6701 module's pinout, voltage, latency, or output type.

## Alternatives (audit-verified; not selected)

- **Generic 5208 clones** (~$20–35): same class, but shaft is solid 6 or
  8 mm and KV/R vary — acceptable only if the acceptance checks pass before
  you commit the hub design.
- **Salvaged DJI gimbal yaw motors** (~$10–20): real low-cogging motors but
  nonstandard shafts/connectors — **avoid** unless you enjoy re-termination.
- **GM4108/4006 gimbal motors**: Kt ≈ 0.03–0.05 → can't reach the envelope.
  **Avoid.**
- **High-KV multirotor outrunners**: more cogging/ripple, KV 300+.
  **Avoid.**

## Acceptance checks (on arrival, before assembly)

1. Confirm the 4015 motor and the **MT6701** encoder option, not AS5600.
2. Measure the shaft: **10 mm OD / 7.5 mm bore**; update the motor hub only
   if the physical measurement differs.
3. Measure and record winding resistance with the project's documented phase
   convention; compare against the expected 4.8 Ω specification.
4. Verify the A/B/Z connector pinout and output voltage with the motor
   unpowered. Confirm A/B phase order and one Z/index event per revolution.
5. Confirm the MT6701 magnet is diametrically magnetized, centered, and within
   the module's specified air gap.
6. Connect I²C temporarily and compare its absolute angle against the ABZ
   count while turning the shaft by hand.
7. Spin by hand: clean, no grinding, no encoder dropouts, and no connector
   intermittency.

## Risks & caveats

- Published R and KV are inconsistent across listings — never trust, always
  measure.
- Rated 3–5S but the rig runs a 24 V bus: slightly above spec — safe because
  R limits current and duty stays low; no full-duty continuous operation.
- Low cogging is why this class was chosen; whatever residual cogging/ripple
  exists (~10–15% of rated) is learned and cancelled by
  `learn/residual.py`.
