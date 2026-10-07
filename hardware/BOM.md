# Bill of Materials — SEA torque-control bench rig

Total **~$285–315** with the selected 4015 motor/MT6701 configuration and the calibration apparatus (see totals below). Every line has at least one **Amazon** link
(easiest, shortest lead time, often Prime) plus lower-cost or specialized
alternates so you can compare. Prices are approximate US street prices
(Aug 2026) — they drift; the links are the stable part.

> **Ordering rule of thumb:** anything with a long lead time (motor,
> ESC1, extrusion) goes in the *first* order. Amazon stock on commodity
> parts (screws, wire, magnets) is usually 1–2 days. See
> `docs/plan/ordering_checklist.md` for the two-batch order plan, the DOA
> flags, and the on-arrival acceptance checks.
>
> **Spec source of truth:** verified spec sheets, acceptance checks, and audit
> verdicts live in `hardware/parts/` — one file per major part. This BOM is the
> shopping list (quantities, prices, links). If they disagree, the part file wins.

---

## Electronics

| Qty | Item | Purpose | ~$ | Buy |
|-----|------|---------|-----|-----|
| 1 | **ST B-G431B-ESC1** Discovery kit (STM32G431CB + 3-ph inverter + current sensing + on-board ST-Link) | The FOC power stage the firmware targets | **$28–40** | Cheapest: [DigiKey ~$28](https://www.digikey.com/en/products/detail/stmicroelectronics/B-G431B-ESC1/10321670) · [Mouser ~$37](https://www.mouser.com/ProductDetail/STMicroelectronics/B-G431B-ESC1) · [Newark ~$39](https://www.newark.com/stmicroelectronics/b-g431b-esc1/discovery-board-32bit-arm-cortex/dp/39AH4955) · [ST store](https://www.st.com/en/evaluation-tools/b-g431b-esc1.html) · Amazon: search "B-G431B-ESC1" (3rd-party, stock varies — [Amazon.ca listing](https://www.amazon.ca/B-G431B-ESC1-Electronic-Controller-STM32G431CB-Performance/dp/B0F48VM6Z5)) · [AliExpress ~$46+](https://www.aliexpress.com/item/1005008180464793.html) |
| 1 | **4015 BLDC motor with integrated MT6701 encoder** — 0.30 N·m at 24 V, 1.4 A rated / 4 A max, KV 61 RPM/V, R 4.8 Ω, L 2.6 mH, **10 mm OD / 7.5 mm hollow bore**, ABZ + I²C exposed. **Selected motor configuration.** Use ABZ for real-time motor feedback and I²C for diagnostics/configuration. | Motor and motor-side encoder | **~$40** | [Amazon selected 4015 listing](https://www.amazon.com/dp/B0G2LR85GW) |
| 1 | **AS5048A 14-bit encoder module** (load side only) — the motor-side encoder is integrated in the selected 4015 motor | Differential deflection (`θm`, `θl`) = torque sensor | **$8–12** | Amazon: [generic module](https://www.amazon.com/AS5048A-Accuracy-Magnetic-Peripheral-Interface/dp/B08LW1K6F7) · [ViaGasaFamido](https://www.amazon.com/As5048A-Magnetic-Peripheral-Interface-Accuracy/dp/B093QFXFT8) |
| 1 | **Diametric encoder magnets, 6×3 mm** — one for the load-side AS5048A; verify whether the integrated MT6701 motor assembly already includes its magnet | Encoder magnets | $10–23 | Amazon: [20 pc 6.35 mm diametric](https://www.amazon.com/clp/B0D2C9VNVR) · [Magnet Baron 6×3 mm rings](https://themagnetbaron.com/products/diametrically-magnetized-20pcs-6m3mm-1-4-x-1-8-ring-magnets) |

| 1 | **24 V / 5 A (120 W) PSU** | DC bus (Vbus = 24 V) | $18–25 | Amazon: [ALITOVE](https://www.amazon.com/clp/B0865Q22SZ) · [SHNITPWR](https://www.amazon.com/clp/B07PWZQ4MB) · [PAUTIX](https://www.amazon.com/clp/B09VBNZ6ZC) |
| 1 | **XT60 pigtail pair** (male + female, 14 AWG silicone) — solder the ESC1 side to the board's VDC+/GND pads (see UM2516 §7.2) | 24 V → ESC1 power input | $8–10 | Amazon: [JFtech 5 pairs](https://www.amazon.com/clp/B07HQBDW7V) · [Hobbyant 5 pairs](https://www.amazon.com/clp/B0CHDQQVP4) · [BDHI XT60+JST](https://www.amazon.com/clp/B0969R75Q4) |
| 1 | **3.5 mm bullet connectors** (motor phase wires ↔ ESC1 U/V/W slots) | Motor wiring | $8 | Amazon: [Hobbypower 20 pairs](https://www.amazon.com/Hobbypower-3-5mm-Bullet-Connector-Battery/dp/B00EZKW1T4) · [Amass MR60 10 pairs](https://www.amazon.com/Connector-Female-Bullet-Sheath-Connection/dp/B07X223LK3) |
| 1 | **Breadboard + Dupont jumper wires** (F/M, M/M, F/F) | Encoder + logic wiring to the ESC1 header | $8–12 | Amazon: [EDGELEC 120 pc](https://www.amazon.com/EDGELEC-Optional-Breadboard-Assorted-Multicolored/dp/B07GCZ52WF) · [840 pc set](https://www.amazon.com/clp/B08GPCZVFN) |
| 1 | **USB data cable** (micro-USB or USB-C — check the board's connector; a phone cable with data lines works) | Programming + telemetry | $0–8 | Use one you own, or [Amazon search](https://www.amazon.com/s?k=USB+data+cable) |
| 1 | **Solder + flux + heat-shrink** (60/40 rosin-core; you're wiring the XT60 pigtail and bullets) | Power-wiring consumables | $8–12 | Amazon: [solder + flux kit](https://www.amazon.com/Solder-Wire-Rosin-Paste-Flux/dp/B08BL339LX) · [heat-shrink assortment](https://www.amazon.com/s?k=heat+shrink+tubing+assortment) |

### Optional electronics

| Qty | Item | Purpose | ~$ | Buy |
|-----|------|---------|-----|-----|
| 1 | **ST-Link/V2 clone** — *skip*: the ESC1 has an on-board ST-Link; only needed if you plan to flash another STM32 | Backup flashing | $8 | [Amazon search](https://www.amazon.com/s?k=ST-Link+V2+clone) |
| 1 | **5 V buck converter** — *skip*: run the AS5048A modules from the ESC1's 3.3 V rail (accuracy spec is at 5 V; 3.3 V is fine for the bench). Add only if you want the full 5 V spec | Encoder rail at 5 V | $7 | [Amazon search](https://www.amazon.com/s?k=5V+3A+DC+DC+buck+converter) |

---

## Mechanical (Option A — torsion bar; see `spring_design.py`)

| Qty | Item | Purpose | ~$ | Buy |
|-----|------|---------|-----|-----|
| 1 | **Spring steel / music wire, 2.5 mm** — one 300+ mm length (the 500 mm × 20 pc packs give you spares to tune ks) | Torsion spring, k ≈ 1 N·m/rad at 304 mm | $13–17 | Amazon: [20 pc 500 mm carbon spring wire (2.5 mm incl.)](https://www.amazon.com/20pcs-500mm-Strength-Carbon-Spring/dp/B0GY8B66CL) · [K&S Metals 2.5 mm × 1 m, 8 pc, $16.99](https://ksmetals.com/collections/music-wire) |
| 1 | **Motor + load hub plates** (3D print, PLA+/PETG) — bore the motor hub for the selected 4015 shaft: **10 mm OD / 7.5 mm hollow bore**. The integrated MT6701 magnet/encoder is part of the motor assembly; the load-side AS5048A uses the separately sourced diametric magnet. | Clamp the bar ends; bolt to motor shaft / load disc | $5 | Print from your own model (PLA+ row further down) |
| 1 | **Load disc, ~250 g at ~100 mm radius** (3D-print + steel washers for mass — washers sourced below) | J_l ≈ 1.2e-3 kg·m² | $5 | Print (PLA+ row further down) |
| 1 | **8 mm × 300 mm stainless/steel shaft** — the load shaft the 608ZZ bearings (8 mm bore) ride on; load disc + hub spin on this | Load-side shaft | $9–12 | Amazon: [2× 8×300 mm 304 rod](https://www.amazon.com/-/es/DeiWhisper-2ptR8mm300/dp/B0F1RYJM72) · [303 stainless 8 mm rod](https://www.amazon.com/clp/B0CL45ZZRS) |
| 2 | **2.5 mm dowel pins** (pin the bar into the hubs) | Bar-to-hub positive drive (no slip) | $8–10 | Amazon: [50 pc 2.5 mm stainless](https://www.amazon.com/Othim-Diameter-Stainless-Elements-Location/dp/B0BC8W6V6D) · [search "2.5 mm dowel pin"](https://www.amazon.com/s?k=2.5mm+dowel+pin) |
| 1 | **M3 set screws (grub screws)** + hex keys (pin the hubs to the shafts) | Shaft/hub clamping | $8–10 | Amazon: [60 pc M3–M8 assortment](https://www.amazon.com/clp/B0DG33PLM2) · [M3×8, 50 pc](https://www.amazon.com/clp/B09HXP26RP) |
| 1 | **M3 socket-head screw + nut assortment** (mounting motor, hubs, bearings) | Assembly hardware | $12–15 | Amazon: [CARLWIN 420 pc](https://www.amazon.com/Premium-Metric-Socket-Assortment-Washers/dp/B0CWXPDM1K) · [300 pc](https://www.amazon.com/clp/B073VKDZJ2) |
| 1 | **2020 aluminum extrusion** (2× ~400–500 mm) — or a 12 mm plywood base if you want cheaper | Rigid base (frame resonance ≥ 5× the 18 Hz spring mode) | $15–35 | Amazon: [4× 400 mm T-slot set](https://www.amazon.com/2020-Aluminum-Extrusion-Precision-Compatibility/dp/B0CNLBCL75) · [single 500 mm profile (SANTIE)](https://www.amazon.com/SANTIE-Aluminum-Profiles-500mm-Silver-Extrusion/dp/B09WD4WYKF) |
| 1 | **M5 T-nuts for 2020 extrusion, ~50 pc** (drop-in or roll-in) — bolt the motor plate, hub brackets, and bearing blocks to the base | Mounting hardware for the extrusion base | $9–15 | Amazon: [TOPINSTOCK 100 pc M5](https://www.amazon.com/TOPINSTOCK-European-Aluminum-Extrusions-Thread/dp/B01FOC6A8E) · [JCSPBYL 100 pc](https://www.amazon.com/JCSPBYL-Sliding-Hammer-Aluminum-Profiles/dp/B0BK75LJNF) · [Qjaiune 25 pc](https://www.amazon.com/Qjaiune-Spring-T-Nut/dp/B09H5B7F2T) |
| 2 | **608ZZ bearings** (load-shaft support, 8×22×7 mm) | Free-spinning load with low friction | $10 | Amazon: [SHANDERBAR 10 pc](https://www.amazon.com/clp/B07CK2W9ND) · [LCWLYOBM 10 pc](https://www.amazon.com/clp/B0DC4519DY) |
| 1 | **Large steel flat washers (M12 / 1.2″ OD fender style), 25–50 pc** (~7 g each — 25–30 pc adds the missing ~200 g) | Bolt-on mass for the load disc (Jl ≈ 1.2e-3 kg·m²) | $8–10 | Amazon: [1.2″ OD fender washers, 50 pc](https://www.amazon.com/clp/B0B3895G98) · [search "M12 flat washers pack"](https://www.amazon.com/Metric-M12-Flat-Washers-Pack/s?k=Metric+M12+Flat+Washers+Pack) |
| 1 | **PLA+ filament, 1.75 mm, 1 kg** (PETG also fine) | Hub plates, load disc, hanger arm | $15–26 | Amazon: [ELEGOO PLA+ $14.99](https://www.amazon.com/ELEGOO-Filament-Toughness-Dimensional-Accuracy/dp/B0D41ZDC47) · [eSUN PLA+ $25.99](https://www.amazon.com/Printer-Filament-eSUN-1-75mm-Spool/dp/B095MTT7D3) · [SUNLU PLA+](https://www.amazon.com/SUNLU-PLA-Plus-Filament-Printer/dp/B0DPM2HL5V) |

### Option B (no metalworking) — extension-spring SEA instead of the torsion bar

2× extension springs ≈ 310 N/m at r = 40 mm (sizing in `spring_design.py`)
+ printed lever arm and anchors — ~$10.
Buy: [compression/extension spring assortment, Amazon](https://www.amazon.com/uxcell-0-8mmx12mmx30mm-Stainless-Compression-Springs/dp/B076LR8D3T) ·
[search "extension springs assortment"](https://www.amazon.com/s?k=extension+springs+assortment).
The rest of the mechanical list is unchanged.

### Calibration apparatus (week 6 spring cal + week 11 disturbance fixture)

| Qty | Item | Purpose | ~$ | Buy |
|-----|------|---------|-----|-----|
| 1 | **Slotted weight set, 1 kg total** (9× 100 g + 100 g hanger) — add hooked weights or a 2nd set to reach 1.5 kg | Known torque reference τ = m·g·r on the printed hanger arm | $18–22 | Amazon: [QWORK 1000 g slotted set](https://www.amazon.com/QWORK-Slotted-Chromium-Plated-Metal-Weights/dp/B0BCJY75WZ) · [Eisco 1 kg](https://www.amazon.com/clp/B014LLF4K4) · [hooked weights add-on](https://www.amazon.com/hooked-weight-set/s?k=hooked+weight+set) |
| 1 | **Digital hanging scale, 50 kg** | Verify weight masses; known-force reference for the ±3% τ_hat check; week-11 weight-drop | $10–15 | Amazon: [Flexzion 50 kg](https://www.amazon.com/Flexzion-Digital-Hanging-Electronic-Balance/dp/B018QH7NA8) · [Dr.meter 50 kg](https://www.amazon.com/Backlight-Display-Dr-meter-Electronic-Temperature/dp/B00XVB48E4) · [travel inspira](https://www.amazon.com/travel-inspira-Portable-Suitcase-Included/dp/B0CM3N3BX2) |

Also useful: ~1 m of thin string/fishing line + a small eyelet hook so the
weights hang without pendulum swing (week 6 pitfall) — a few dollars.

---

## Sample total (selected 4015 + MT6701 configuration)

| Item | ~$ |
|------|-----|
| B-G431B-ESC1 (DigiKey) | 28 |
| 4015 motor + integrated MT6701 (Amazon) | 40 |
| AS5048A load-side module | 10 |
| Diametric magnets | 10 |
| 24 V 5 A PSU | 20 |
| XT60 pigtail | 9 |
| Bullet connectors | 8 |
| Breadboard + jumpers | 8 |
| Solder + flux + heat-shrink | 10 |
| Spring wire (2.5 mm) | 15 |
| Dowel pins + set screws | 16 |
| M3 assortment | 12 |
| 2020 extrusion | 25 |
| M5 T-nuts | 12 |
| 8 mm load shaft | 10 |
| 608ZZ bearings | 10 |
| Disc-mass washers | 8 |
| PLA+ filament | 15 |
| Weight set (1 kg slotted) | 20 |
| Luggage scale (50 kg) | 12 |
| **Total** | **≈ $309** |

Cheaper variants: GM5208-12-with-encoder (−$10 net), plywood base (−$15),
generic gimbal motor (−$20). The core rig (ESC1 + motor + sensors +
structure) floors out around ~$180; the calibration apparatus adds ~$40.

## Completeness & necessity review (v2 changes)

**Added — genuinely needed, previously missing:**
- **Diametric encoder magnets** — most cheap AS5048A modules ship without
  a magnet; without these the encoders are dead on arrival.
- **XT60 pigtail / power wiring** — the ESC1 has no AC input; you must
  connect the 24 V PSU to its VDC+/GND.
- **3.5 mm bullet connectors** — the motor's phase leads need to reach the
  ESC1's U/V/W slots.
- **2.5 mm dowel pins + M3 grub screws** — the torsion bar and hubs
  *must* be positively pinned (week 5's mechanical truth); the old BOM
  listed them but had no sourcing.
- **608ZZ bearings** — the load shaft needs real bearings, not printed
  bushings, for the low-friction free-spin test (week 5).
- **M3 screw assortment, 2020 extrusion, PLA+ filament, USB cable** —
  assembly hardware, base, printed parts, and programming, respectively.

**Removed or demoted — not strictly necessary:**
- **5 V regulator → optional.** The AS5048A runs fine from the ESC1's
  3.3 V rail (or the USB 5 V when plugged in); the full 5 V accuracy spec
  is a nice-to-have on a bench.
- **ST-Link → optional.** The ESC1 has an on-board ST-Link.
- **2×20 pin headers → dropped.** The ESC1's connectors + Dupont wires
  cover all wiring.

**Cross-checked against the build plan** (`docs/plan/week01–16`): every
item the milestones actually use is present — nothing referenced in the
weeks is missing, and no listed part goes unused.

## Completeness & necessity review (v3 — adversarial audit, Aug 2026)

**Added — traced to actual milestone requirements:**
- **M5 T-nuts for the 2020 base** — the extrusion is useless without them;
  the motor plate, hub brackets, and bearing blocks all bolt through
  T-slots (week 5).
- **8 mm × 300 mm load shaft** — the 608ZZ bearings have an 8 mm bore; the
  load disc spins on this shaft between them (week 5). The v2 BOM had the
  bearings but nothing for them to ride on.
- **Calibration weight set (1 kg slotted)** — week 6 *requires* hanging
  weights 0.1–1.5 kg at a known radius; without them the spring can't be
  calibrated to ±2%.
- **Digital hanging scale (50 kg)** — week 6's ±3% τ_hat verification uses
  a known-force reference; also verifies weight masses and sizes the
  week-11 weight-drop.
- **Steel washers for disc mass** — the load-disc row already promised
  "steel washers for mass" (Jl ≈ 1.2e-3); now actually sourced (M12/fender
  washers, ~7 g each, 25–30 pc ≈ 200 g).
- **Solder + flux + heat-shrink** — the XT60 pigtail and bullet-connector
  work assumed soldering consumables that were never listed.

**Still not listed (deliberately — a few dollars, in Tools):** thread
locker for hub set screws, C-clamps/bench vise, string + eyelet for the
weight hanger.

**Link audit (this pass):** every link re-verified against live search
results (Aug 2026). Amazon product pages preferred over search URLs — the
2020-extrusion row, previously a bare search URL, now points at concrete
product pages. DigiKey/Mouser/Newark/ST links return 403 to bots but load
in a browser; the two `/clp/` Amazon pages verified as real category
listings.

## Part-by-part spec audit (v4 — Aug 2026)

Every row below was checked against the manufacturer datasheet / official
store spec (linked where it matters) or re-derived from the design math in
`spring_design.py`. Verdicts: ✓ verified, ⚠ caveat, ✗ corrected.

| Part | BOM claim | Verified (Aug 2026) | Verdict |
|---|---|---|---|
| B-G431B-ESC1 (ST) | STM32G431CB + 3-ph inverter + current sensing + on-board ST-Link | STM32G431CB (Cortex-M4, 170 MHz); L6387 gate driver + STL180N6F7 MOSFETs; input **3S–6S (9.9–25.2 V) → 24 V bus OK**; **40 A peak**; on-board ST-Link; micro-USB; VDC+/GND pads per UM2516 §7.2 | ✓ — caveat: 3-shunt sensing is scaled for ±40 A (PGA gain 16) → ~20–30 mA/LSB at 12-bit, i.e. a 2–5 mN·m torque-quantization floor at Kt ≈ 0.2 (the 4 mN·m RMS headline is sim-only) |
| GM5208-24 motor | KV 100–300 RPM/V, Kt 0.05–0.1 N·m/A, ≥ 0.5 N·m peak | Official iFlight sheet: KV ≈ 20–22 (no-load 396–436 RPM @ 20 V); load torque 1800–2500 g·cm @ 1 A → Kt ≈ 0.18–0.25; R = 13.7 Ω ± 5 % (RobotShop lists 25.6 Ω — measure yours); ≤ 40 W; rated 3–5S; 204 g; hollow shaft 15.0 mm OD / 12.6 mm ID | ✗ spec corrected — real Kt ≈ 2× the sim's 0.1, and u_max = 4 A is unreachable: 24 V / 13.7 Ω ≈ 1.75 A stall (0.9 A if your unit measures 25.6 Ω → only ≈ 0.18 N·m, below the 0.35 N·m envelope). Re-export MPC/results with measured R + Kt after week-6–8 ID |
| GM5208-12 w/ AS5048A (Option B) | 12 V version; "−24 ≈ 2× the −12's R" | Official iFlight sheet: R = 15.2 Ω ± 5 % (**higher** than the −24 — old ratio note wrong); no-load 456–504 RPM; hollow shaft 15.0 mm OD / **12.0 mm ID** (≠ −24) | ⚠ — onboard encoder is a real AS5048A (14-bit ✓); same Kt/voltage caveats as Option A |
| AS5048A modules | 14-bit SPI/PWM | 14-bit absolute (16 384 counts/rev), ±0.05° accuracy, SPI (to 10 MHz) + PWM out, 3.3–5 V supply | ✓ |
| Diametric magnets 6×3 mm | rotor magnet for AS5048A | Datasheet: 6–8 mm dia × ≥ 2.5 mm tall, ~30–70 mT at the die — the 6×3 mm N45 diametric is the standard pairing | ✓ — keep the DOA check (modules often ship magnetless) |
| 24 V / 5 A PSU | 24 V bus | Within ESC1 3S–6S range; ≥ 5 A covers the ~2 A motor current with margin; motor ≤ 40 W | ✓ |
| XT60 pigtail, 3.5 mm bullets | 24 V power + motor wiring | XT60 → ESC1 VDC+/GND pads (UM2516 §7.2); 3.5 mm bullets fine for ≤ 40 W | ✓ |
| Spring wire 2.5 mm | k ≈ 1 N·m/rad at 304 mm | Re-derived: J = πd⁴/32 = 3.84e-12 m⁴, k = G·J/L = 79.3e9 × 3.84e-12 / 0.304 = 1.00 N·m/rad ✓; shear at 0.35 N·m = 16T/πd³ = 114 MPa → SF ≈ 5.4× vs 620 MPa (drill rod) ✓ | ✓ (matches spring_design.py) |
| 8 mm × 300 mm load shaft | load shaft for 608ZZ | 608ZZ bore = 8 mm ✓ | ✓ |
| 608ZZ bearings | 8×22×7 mm | Standard metric 608 dimensions ✓ | ✓ |
| Dowel pins 2.5 mm | bar-to-hub pinning | Metric 2.5 mm ✓; imperial 3/32″ (2.38 mm) trap already flagged | ✓ |
| M3 set screws + assortment | hub clamping | M3 grub screws into printed hubs ✓ (blue thread-locker advised) | ✓ |
| 2020 extrusion + M5 T-nuts | rigid base | European 2020 = 20×20 mm profile, 6 mm slot; T-nuts must match the slot ✓ | ✓ |
| Fender washers ~7 g | disc mass | M12 / 1.2″ OD ≈ 6–7 g ea → 25–30 pc ≈ 180–200 g; disc J = 0.5 × 0.25 × 0.098² = 1.2e-3 kg·m² ✓ | ✓ |
| Weight set 1 kg + luggage scale | calibration refs | Slotted 100 g × 9 + hanger; 50 kg scale (±10–50 g) fine for the ±2–3 % cal targets | ✓ |
| PLA+ filament | printed parts | 1.75 mm ± 0.05 ✓ | ✓ |

**Watch list (things the audit surfaced):**

- **Motor electricals are the main risk.** Official R/KV figures are internally
  inconsistent (13.7 vs 25.6 Ω across listings; no-load-KV ≈ 20 implies Kt ≈ 0.45
  while the load-torque spec implies ≈ 0.2). The sim, MPC export, and
  `LEARNED_KT` all assume Kt = 0.1 with u_max = 4 A — plan to re-export
  `results/` with the measured R, L, and Kt after week-6–8 ID and retune
  `MPC_U_MAX` (the real motor reaches the 0.35 N·m envelope at ~1.5–2 A, not 3.8 A).
  If your unit measures ≈ 25 Ω line-to-line, it *cannot* reach the envelope on a
  24 V bus — drop the envelope or use the −12 variant.
- **ESC1 current quantization** (~20–30 mA/LSB over ±40 A) is the hardware floor
  for torque precision — ~2–5 mN·m at Kt ≈ 0.2. Fine for the milestones; don't
  chase the sim's 4 mN·m RMS on hardware.
- **Motor hub is parametric**: genuine shaft is a hollow 15.0 mm OD tube (clamp
  the OD); clones may be solid 6 or 8 mm — bore the printed hub for what you
  measure. The motor-side AS5048A magnet needs a small plug into the 12.6 mm bore
  to sit concentric with the axis.
- **−24 voltage rating is 3–5S (11.1–18.5 V nominal)** — the 24 V bus is slightly
  above spec. Safe here (R limits current, duty stays low) but don't run full-duty
  continuously.
- The old "−24 ≈ 2× the −12's phase R" note is wrong (iFlight lists 13.7 vs
  15.2 Ω) — measure, don't trust.

## Tools (assume you have or borrow)

- STM32CubeIDE (free) + the ESC1's on-board ST-Link
- 3D printer or access to one
- Soldering iron + solder/flux/heat-shrink (or the $10 kit in Electronics)
- Dremel / hacksaw for the spring wire
- Multimeter; scope optional
- C-clamps or a small bench vise (hold the rig while assembling)
- Thread locker (blue) for hub set screws; string + eyelet for the hanger

## Where the money goes

The B-G431B-ESC1 is the single most important purchase: it is the same
silicon used in real drone ESCs, has integrated gate drivers + current
sensing + ST-Link, and costs less than a hobby ESC — that is why the entire
firmware stack targets it. The motor is the second decision: a big
low-speed gimbal motor (GM5208 class) gives you the low cogging and high
peak torque the torque-control story needs.
