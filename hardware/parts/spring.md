# Series-elastic element — 2.5 mm torsion bar (Option A)

> The torque transducer: `τ_s = k_s(θ_m − θ_l)`, k_s = 1.0 N·m/rad.
> BOM row: spring wire 2.5 mm ($13–17). Design tool:
> `hardware/spring_design.py`.

## Verified design math (captured from `python hardware/spring_design.py`, Aug 2026)

```
k = G·J / L,   J = π·d⁴/32,   shear = 16·T / (π·d³)
G = 79.3 GPa (steel); drill-rod yield 620 MPa (conservative)

d = 2.0 mm  ->  L = 124.6 mm   shear 222.8 MPa   SF ≈ 3×
d = 2.5 mm  ->  L = 304.1 mm   shear 114.1 MPa   SF ≈ 5×   ← recommended
d = 3.0 mm  ->  L = 630.6 mm   shear  66.0 MPa   SF ≈ 9×

Targets: k_s = 1.00 N·m/rad, τ_max = 0.35 N·m, deflection 0.350 rad = 20.1°
Tune by grinding length: dL = −L·(dk/k)
```

## Why this part

- Round rod is linear, hysteresis-free, and machinable (music wire / drill
  rod + 2 ground dowel pins at the hubs). The stiffness is *calibrated*
  with hanging weights (week 6), never trusted from the datasheet.
- Option B (2× extension springs at r = 40 mm, ~312 N/m each, preloaded to
  ~10 N) is the all-printed fallback if you want zero metalworking.

## Use / Don't use

- **USE** the 2.5 mm bar. 2.0 mm only if you want a softer rig (SF drops to
  3×); 3.0 mm is too long (630 mm).

## Acceptance checks

1. Roll on a flat surface: lies straight (kinked music wire is permanent).
2. Caliper: 2.5 mm, not 2.4 mm (2.4 mm packs exist).
3. Both ends positively pinned (2.5 mm dowels) — no slip at the hubs.
4. Calibrated k within ±2 % of the fitted curve (week 6).

## Risks & caveats

- 2.5 mm metric vs imperial confusion; kinked-in-shipping wire.
- Dowel pins: metric 2.5 mm vs imperial 3/32″ (2.38 mm) — nearly identical,
  the wrong one won't fit.
