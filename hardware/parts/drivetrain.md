# Drivetrain & structure — shaft, bearings, hubs, base

> Everything mechanical between the motor and the load disc. BOM rows:
> hub plates, load disc, 8 mm shaft, 608ZZ, dowel pins, M3 hardware,
> 2020 extrusion + T-nuts, washers, filament.

## Verified spec sheet (Aug 2026)

| Item | Spec | Check |
|---|---|---|
| Load shaft | 8 × 300 mm stainless/steel rod (7.98–8.00 mm OK; imperial 5/16″ = 7.94 mm **no**) | Calipers |
| Bearings | 608ZZ × 2, 8 × 22 × 7 mm (ZZ = metal shields) | Clean whirr, no click, no radial play |
| Hub plates (printed) | Motor hub bore = **measured** shaft: genuine 15.0 mm OD hollow; clones 6/8 mm solid. Load hub = 8 mm. **Plus a printed plug for the encoder magnet into the 12.6 mm hollow bore** | Calipers |
| Dowel pins | 2.5 mm metric × 2 (bar-to-hub positive drive) | Metric vs 3/32″ (2.38 mm) |
| Fasteners | M3 set screws (grub) + M3 socket-head assortment; blue thread-locker | — |
| Load disc | ~250 g at ~98 mm radius → J = 0.5·m·R² = 1.2005e-3 kg·m² (script output) | Weigh washers |
| Disc mass | M12/fender washers, ~6–7 g ea; 25–30 pc ≈ 180–200 g | Luggage scale |
| Base | European 2020 extrusion (20 × 20 mm, **6 mm slot**) + M5 T-nuts | T-nut slides with light friction |
| Filament | PLA+ 1.75 mm ± 0.05 | — |

## Use / Don't use

- **USE** all rows. A 12 mm plywood base is the documented cheaper variant
  if you want to save ~$15–20.
- The motor hub must be **parametric on shaft diameter** — the genuine
  hollow shaft is 15.0 mm OD; a clone may be 6 or 8 mm solid. Measure first,
  print second.

## Acceptance checks (on arrival)

1. Bearings: hand-spin clean, no click (grit shows up as unexplained damping
   in the week-7 ID).
2. T-nut ↔ slot fit (European 2020 = 6 mm slot; US 80/20-style ≠).
3. Hub bore + magnet plug fit the measured shaft.
4. Disc mass ≈ 250 g on the luggage scale.

## Risks & caveats

- Bearing grit/friction contaminates the ID (week 7) — check early.
- Extrusion/T-nut slot mismatch is the classic trap.
- The motor-side AS5048A magnet needs the bore plug to sit concentric
  (hollow shaft — see `encoders.md`).
