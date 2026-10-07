# AS5048A encoders + diametric magnets

> The torque sensor: `τ_s = k_s(θ_m − θ_l)` from two 14-bit absolute angle
> readings. BOM rows: AS5048A modules ($8–12 ea) + magnets ($10–23).

## Verified spec sheet (Aug 2026)

| Parameter | Value | Source |
|---|---|---|
| Resolution | 14-bit absolute, 16 384 counts/rev | ams AS5048 datasheet |
| Accuracy | ±0.05° (system, with linearization) | ams datasheet |
| Interface | SPI (to 10 MHz) + PWM output | ams datasheet |
| Supply | 3.3–5 V (the ESC1 3.3 V rail is fine on the bench) | ams datasheet |
| Magnet requirement | 6–8 mm dia × ≥ 2.5 mm tall, ~30–70 mT at the die | ams datasheet |
| Package | TSSOP-14 (breakout modules) | ams |

## Quantity logic

- Plain motor (GM5208-24): **2 modules + 2 magnets** (motor side + load side).
- GM5208-12-with-encoder: **1 module + 1 magnet** (load side only).

## Mounting (hollow shaft!)

- Motor-side magnet: the GM5208 shaft is a **12.6 mm hollow bore** — glue the
  magnet into a small printed **plug** that seats in the bore, concentric
  with the rotation axis (don't drop it on the tube wall).
- Load side: magnet on the 8 mm load-shaft end; module fixed to the frame.
- Keep the module ~1–2 mm from the magnet; center it within the shaft runout
  (≤ 0.1 mm motor spec).

## Acceptance checks

1. **DOA check (most common failure):** the module must include a magnet —
   many Chinese breakouts ship without one. Verify the listing or test on
   arrival.
2. Diametric, not axial: spinning the magnet must sweep 0–16383 smoothly and
   *monotonically* (an axial magnet gives a folded/periodic pattern).
3. SPI readback at 3.3 V matches a known angle.

## Risks & caveats

- Modules ship magnetless → verify before ordering extras.
- 5 V is the accuracy-spec rail, but 3.3 V is fine — the optional buck stays
  optional.
