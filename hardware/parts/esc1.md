# B-G431B-ESC1 — FOC power stage + MCU

> The board the entire firmware stack targets (`firmware/`). Everything else
> is chosen around it. BOM row, $28–40 (DigiKey / Mouser / Newark / ST).

## Verified spec sheet (Aug 2026)

| Parameter | Value | Source |
|---|---|---|
| MCU | STM32G431CB, Cortex-M4 @ 170 MHz | ST UM2516 / DigiKey |
| Gate driver | L6387 | UM2516 |
| Power FETs | STL180N6F7 (60 V, 180 A) | UM2516 |
| Input voltage | 3S–6S LiPo (9.9–25.2 V) → **24 V bus OK** | UM2516; Eirbot guide runs 24 V |
| Current rating | 40 A peak | ST reference design |
| Current sensing | 3-phase shunt, on-chip PGA gain 16, polarization network scaled for **±40 A** → ~20–30 mA/LSB at 12-bit | ST community (2020) |
| Programming | On-board ST-Link/V2-1, micro-USB (**data** cable required) | Newark / UM2516 |
| Power input | VDC+/GND pads — solder the XT60 pigtail here (UM2516 §7.2) | UM2516 |
| Extra I/O | USB CDC telemetry, CAN, PWM inputs | UM2516 |

## Why this part

- Same silicon family as production drone ESCs, with gate drivers, shunt
  sensing, and ST-Link all integrated — the 10 kHz FOC current loop and the
  2 kHz torque loop are implemented on it in `firmware/`.
- At $28–40 it is cheaper than any hobby ESC that exposes raw FOC access.

## Use / Don't use

- **USE.** No substitute without rewriting the firmware for another MCU.
- Optional add-ons, both *skip*: external ST-Link/V2 clone (on-board one
  exists) and the 5 V buck for the encoders (3.3 V rail is fine — see
  `encoders.md`).

## Acceptance checks (on arrival)

1. PSU on VDC+/GND; ST-Link enumerates over USB (a **charge-only cable is
   the classic silent failure** — use a known-good data cable).
2. Flash `firmware/`; spin the motor by hand and see sinusoidal phase
   currents in the USB telemetry (M0).

## Risks & caveats (audit)

- **Current quantization floor:** ±40 A range → ~20–30 mA/LSB → ~2–5 mN·m
  torque steps at Kt ≈ 0.2. Fine for the milestones; the 4 mN·m RMS torque
  headline is a sim number — don't chase it on hardware.
- **±5 A acceptance is unreachable** with the recommended motor (24 V /
  13.7 Ω ≈ 1.75 A stall). Use **±2 A** for the M0/M1 current-loop targets.
- 24 V is near the 25.2 V (6S) ceiling — fine, but don't exceed it.
