# Power & wiring — PSU, XT60, bullets, bench wiring

> 24 V DC bus → ESC1 → motor. BOM rows: PSU ($18–25), XT60 ($8–10),
> bullets ($8), breadboard/jumpers ($8–12), USB cable, solder kit.

## Verified spec sheet (Aug 2026)

| Item | Spec | Checks |
|---|---|---|
| PSU 24 V / 5 A (120 W) | Inside the ESC1's 3S–6S range (max 25.2 V); ≥ 5 A covers the ~2 A motor with margin; motor ≤ 40 W | Label match; light-load test before the motor |
| XT60 pigtail pair, 14 AWG | Solder to the ESC1 VDC+/GND pads (UM2516 §7.2) | Snug fit, no cold joints |
| 3.5 mm bullets | Motor phase wires ↔ ESC1 U/V/W | Plug/unplug: positive detent |
| Breadboard + Dupont | Encoder SPI + logic wiring at 3.3 V | — |
| USB data cable | ST-Link programming + telemetry | Must be a *data* cable (charge-only is the classic silent failure) |

## Use / Don't use

- **USE** all rows; no substitutions needed.
- Don't exceed 25.2 V on the bus, and don't run the motor at full duty on
  24 V (its rating is 3–5S — see `motor.md`).

## Acceptance checks (on arrival)

1. PSU: 24 V ± 5 %, ≥ 5 A continuous; test with a light load first.
2. XT60/bullets: snug, positive detent, no wobble.
3. ST-Link enumerates (data cable).

## Risks & caveats

- Cheap XT60 counterfeits: loose fit / cold solder joints.
- 3.5 mm vs 4 mm bullet confusion — caliper if unsure.
