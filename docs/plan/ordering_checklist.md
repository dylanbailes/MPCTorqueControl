# Ordering Checklist — Week 1

Everything here maps to `hardware/BOM.md` (prices/links live there; this
file is the *when* and the *watch-out*). Two orders total:

- **Order A — week 1, day 1.** Everything the build needs through week 5.
  This is the long-lead order: motor, ESC1, and China-shipped parts.
- **Order B — end of week 3.** The calibration apparatus only (needed
  week 6). Everything in it is Amazon Prime, so a slip costs nothing.

> Rule: never let a back-ordered motor or ESC1 stall weeks 2–4. Those
> weeks are sim + firmware work and need **zero hardware**. If a part is
> delayed, keep building — the bench catches up later.

---

## Order A — place in week 1 (everything through week 5)

| Part (BOM row) | Where | Lead time | Arrival risk |
|---|---|---|---|
| B-G431B-ESC1 | DigiKey/Mouser (cheapest) or Amazon 3rd-party | **1–4 wks** (DigiKey) / days (Amazon, if in stock) | Stock varies wildly on Amazon; DigiKey back-orders fill slowly |
| 4015 motor with integrated MT6701 | Amazon selected listing | **1–3 wks** | Confirm MT6701 option (not AS5600), 10 mm OD / 7.5 mm bore, ABZ + I²C connector, 3.3 V-compatible logic, magnet and air gap; verify R/Kt before assembly |
| AS5048A load-side module ×1 | Amazon (China sellers) | 3–10 days | **Most common DOA: ships without the magnet** (BOM warns; verify listing) |
| Diametric encoder magnets | Amazon or Magnet Baron (small shop) | 3–10 days | Wrong size (needs 6 mm × 2.5–3 mm, *diametric*, not axial) |
| 24 V / 5 A PSU | Amazon | 1–2 days | Wrong voltage/current rating on the label; noisy/whining units |
| XT60 pigtail pair | Amazon | 1–2 days | Loose-fit counterfeits; solder joints cold |
| 3.5 mm bullet connectors | Amazon | 1–2 days | Loose fit (plug/unplug test); wrong diameter (3.5 vs 4 mm) |
| Solder + flux + heat-shrink | Amazon | 1–2 days | — |
| Breadboard + Dupont jumpers | Amazon | 1–2 days | — |
| USB data cable | Your drawer or Amazon | same-day | **Charge-only cable is the classic silent failure** — ST-Link won't enumerate |
| Spring wire 2.5 mm | Amazon (carbon spring pack) or K&S | 1–2 days / 1 wk | **Kinked in shipping** (music wire kinks permanently); 2.4 mm vs 2.5 mm confusion |
| 8 mm × 300 mm shaft | Amazon | 1–2 days | 7.98 vs 8.00 mm tolerance is fine; imperial 5/16″ (7.94 mm) is *not* |
| 608ZZ bearings ×2 | Amazon | 1–2 days | Gritty/clicking cheap units; ZZ = metal shield (correct) |
| Dowel pins 2.5 mm | Amazon | 1–2 days | **Metric 2.5 vs imperial 3/32″ (2.38 mm) — nearly identical, wrong one won't fit** |
| M3 set screws + hex keys | Amazon | 1–2 days | — |
| M3 socket-head assortment | Amazon | 1–2 days | — |
| M5 T-nuts (2020) | Amazon | 1–2 days | **Must match the extrusion's slot** (European 2020 = 6 mm slot) |
| 2020 extrusion | Amazon | 3–7 days (bulky/freight handling) | Slot size mismatch (US 80/20 style ≠ European 2020); bent ends |
| Disc-mass washers | Amazon | 1–2 days | — |
| PLA+ filament | Amazon | 1–2 days | Diameter variance (1.75 ± 0.05 mm spec) — matters for print quality |

**Also in week 1:** start the 3D prints for the hub plates, load disc, and
hanger arm as soon as you have filament — print iterations are calendar
time, and week 5 assembly needs finished parts.

## Order B — end of week 3 (needed week 6)

| Part (BOM row) | Where | Lead time | Arrival risk |
|---|---|---|---|
| Slotted weight set (1 kg) | Amazon | 1–2 days | Verify mass markings vs the luggage scale |
| Digital hanging scale 50 kg | Amazon | 1–2 days | ±50 g resolution is fine; check the display unit (kg/lb) |
| String + eyelet for the hanger | Hardware store | same-day | — |

---

## The DOA list — parts most likely to arrive broken or wrong

Check these *inside the box, on day of arrival* (calipers + 15 min):

1. **Encoder module without a magnet.** The load-side AS5048A commonly ships
   without its magnet. Acceptance: after the diametric magnets arrive, spin a
   magnet above each sensor — the AS5048A angle must sweep 0–16383 smoothly;
   the MT6701's I²C angle must agree with its ABZ count during hand rotation.
2. **Encoder magnets: axial instead of diametric, or wrong size.**
   A 5×5 axial magnet reads garbage. Acceptance: reading is smooth over a
   full rotation and *monotonic* (diametric) — an axial magnet gives a
   folded/periodic pattern.
3. **Dowel pins: 2.5 mm metric vs 3/32″ imperial (2.38 mm).** Measure
   with calipers before drilling/pinning the hubs.
4. **Spring wire kinked or undersized.** Roll it on a flat surface — it
   must lie straight. Measure 2.5 mm with calipers (2.4 mm packs exist).
5. **608ZZ bearings gritty.** Spin by hand: clean whirr, no clicking,
   no radial play. A gritty bearing is a friction term that will show up
   in week 7's ID as unexplained damping.
6. **XT60/bullets loose.** Plug/unplug: snug, positive detent, no wobble.
7. **PSU label mismatch.** 24 V ±5%, ≥ 5 A continuous. Test with a light
   load before ever connecting the motor.8. **Motor/encoder wrong variant.** Confirm the selected 4015 with
   **MT6701**, not AS5600. Measure the shaft as 10 mm OD / 7.5 mm bore,
   verify ABZ + I²C are exposed, check the output voltage and connector
   pinout, and confirm the integrated magnet/air gap before energizing.
9. **Extrusion/T-nut slot mismatch.** European 2020 has a 6 mm slot;
   US "80/20-style" profiles are different. A T-nut must slide in with
   light friction, not rattle or jam.
10. **Charge-only USB cable.** ST-Link won't enumerate. Keep a known-good
    data cable in the bench box forever.

## If something is back-ordered

- **ESC1:** the sim + firmware are fully runnable now — do not wait.
  Check DigiKey/Mouser restock weekly; keep the Amazon 3rd-party listing
  as a fallback.
- **Motor:** sub a Kt ≈ 0.1 N·m/A equivalent (the sim tolerates ±20% —
  re-run `python -m sim.run_experiments` with the new Kt to confirm the
  MPC/PID comparison still holds). Note the GM5208 measures closer to
  Kt ≈ 0.2 N·m/A — expect to re-export `results/` and retune `MPC_U_MAX`
  with the measured value after week-6–8 ID, whatever motor you receive.
- **Extrusion:** a 12 mm plywood base works (BOM's cheaper variant) —
  buy it locally, swap to extrusion later if you want.

## Log it

Tick each arrival in `docs/plan/TRACKER.md` with the acceptance result.
The photo of each unpacked box is also your build-log content for week 15.
