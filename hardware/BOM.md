# Bill of Materials — SEA torque-control bench rig

Total ~$180–260 (depending on motor choice). All parts are off-the-shelf;
nothing is custom-machined beyond drill rod and 3D-printed brackets.
Prices are approximate street prices (2025) — shop around.

## Electronics

| Qty | Part | Purpose | ~Price |
|-----|------|---------|--------|
| 1 | **ST B-G431B-ESC1** Discovery kit | STM32G431 MCU + 3-phase inverter + current sensing + encoder header — the exact board the firmware targets | $20–40 |
| 1 | BLDC motor, ~100 W class, Kt ≈ 0.1 N·m/A, 24 V (e.g. iFlight gimbal motor, T-Motor, or a cheap outrunner) | Motor side of the SEA | $25–60 |
| 2 | **AS5048A** 14-bit magnetic encoder boards (SPI/I2C) | Motor + load shaft angle, differential deflection | $10–20 |
| 1 | 24 V / 5 A bench PSU | DC bus | $25–40 |
| 1 | 5 V regulator or USB-C breakout | Encoder/logic rail | $5 |
| 2 | 2×20 pin headers, jumper wires, small breadboard | Wiring | $10 |
| 1 | (Optional) ST-Link/V2 clone — the ESC1 has an on-board ST-Link, skip if using that | Flashing | $0–15 |

## Mechanical (Option A — torsion bar; see `spring_design.py`)

| Qty | Part | Purpose | ~Price |
|-----|------|---------|--------|
| 1 | **2.5 mm drill rod, ~310 mm** (music wire also works) | Series spring, k ≈ 1 N·m/rad | $3 |
| 2 | Motor + load hub plates (3D print, PLA+/PETG, or aluminum) | Clamp the bar ends; bolt to motor shaft / load disc | $5 |
| 1 | Load disc, ~250 g at ~100 mm radius (3D-print + steel washers for mass) | J_l ≈ 1.2e-3 kg·m² | $5 |
| 2 | Ground dowel pins or set screws | Pin the bar into the hubs | $2 |
| 1 | Base plate (aluminum extrusion or plywood) + bearing blocks | Rigid frame so the bar is the only compliance | $15–30 |

Option B (no metalworking): 2 extension springs ≈ 310 N/m at r = 40 mm
(see `spring_design.py`) + printed lever arm + printed anchors — $8.

## Tools (assume you have or borrow)

- STM32CubeIDE (free) + ST-Link (on-board)
- 3D printer or access to one
- Dremel / hacksaw for the drill rod
- Multimeter, scope optional

## Where the money goes

The B-G431B-ESC1 is the single most important purchase: it is the same
silicon used in real drone ESCs, has integrated gate drivers + current
sensing, and costs less than a hobby ESC — that is why the entire firmware
stack targets it.
