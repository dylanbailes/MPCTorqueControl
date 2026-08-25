# Week 2 — CubeMX Project + USB Telemetry

**Phase 0 · Foundations** — ~11 hours

## Exit criteria (week done when…)

- [ ] STM32CubeMX project generated for the B-G431B-ESC1: 170 MHz clock,
      TIM1 PWM on 3 channels with dead time, TIM2 10 kHz, TIM3 2 kHz,
      USB CDC.
- [ ] Firmware compiles with the ST toolchain; the board enumerates as a
      COM port.
- [ ] A 1 kHz "heartbeat" task streams `t, count, Vbus` frames over USB
      that you can plot in Python (5 min of clean data).
- [ ] You can explain the clock tree and the timer→PWM→ADC trigger chain
      from memory.

## Why this week

The B-G431B-ESC1 is a blank canvas: no example code does your job. This
week builds the *skeleton* every later week hangs off — timers, PWM, ADC,
USB. Week 4's current loop is trivial once the plumbing exists.

## Theory

### The STM32G431 clock tree

The chip runs off an HSI (16 MHz) or HSE crystal; a PLL multiplies it up.
Target: **SYSCLK = 170 MHz** (the G431's max). The peripherals get derived
clocks:

```
SYSCLK 170 MHz
 ├─ AHB   (HCLK) 170 MHz   → CPU, GPIO, DMA
 ├─ APB1  (PCLK1) 170 MHz  → TIM2, TIM3 (timer clock can be 2×APB if prescaler ≠ 1)
 └─ APB2  (PCLK2) 170 MHz  → TIM1 (advanced), ADC
```

Timer *counters* clock at the timer clock (170 MHz here). A PWM period of
`PSC+1` prescaler ticks and `ARR+1` counter ticks gives:

```
f_PWM = 170 MHz / ((PSC+1)·(ARR+1))
```

For **100 kHz PWM**: PSC = 0, ARR = 1699 (1700 ticks → 100 kHz). The
B-G431B-ESC1 gate drivers are rated for the common 20–100 kHz range; the
repo assumes 100 kHz PWM (see `firmware/README.md`).

### TIM1 advanced timer and dead time

TIM1 is the *advanced* timer — it can drive complementary outputs with
**programmable dead time**, mandatory for half-bridge MOSFET drivers to
avoid shoot-through (both FETs on). Dead time ~0.5 µs is set in the
break/dead-time register. In CubeMX: TIM1 → PWM Generation CH1/CH2/CH3,
enable "Complementary output" only if your board's inverter needs it (the
ESC1 has integrated drivers; check the schematic).

### ADC and the two-shunt current sensing

Current sensing needs a sample *synchronized* to the PWM. The ESC1's sense
resistors sit in the low side; the classic approach is **two-shunt
sensing**: sample two phase currents during the active PWM window and
reconstruct the third from Kirchhoff (i_a + i_b + i_c = 0). CubeMX: trigger
ADC1 from TIM1's TRGO, sample-and-hold timed so you read mid-window where
the current is settled (avoid switching noise). The current-loop rate
(10 kHz) is then naturally the ADC trigger rate.

The current measurement is the *quality floor* of everything after it:
quantization, offset drift, and switching glitches here become torque
ripple in week 4. Expect to spend a chunk of this week just *looking* at
the ADC trace.

### USB CDC (virtual COM port)

USB CDC presents the MCU as a serial port to the PC — no driver, just
`pyserial`-readable bytes. Frame format matters: fixed-length, checksummed,
newline-terminated. A simple design that will serve all semester:

```
magic(2) | t_ms(4) | id(1) | payload(…, fixed per id) | crc8(1) | \n
```

Logging at 2 kHz must be non-blocking: push to a ring buffer in the ISR,
drain to USB in a low-priority task. If USB ever stalls the torque loop,
you've created a control bug for the sake of telemetry — the number-one
beginner mistake this week.

## Build plan

1. **CubeMX project (3 h).** Per `firmware/README.md` "Project setup":
   G431CB, PLL → 170 MHz; TIM1 → 3×PWM @ 100 kHz + dead time; TIM2 →
   10 kHz update interrupt; TIM3 → 2 kHz update interrupt; USB device →
   CDC; ADC1 → 3 channels triggered from TIM1; SPI1/SPI2 as GPIO for now.
   Generate, open in CubeIDE, confirm it builds *before* writing code.
2. **Heartbeat + USB (3 h).** Implement `main.c` → `tasks.c`: a 1 kHz
   software timer increments a counter and formats a telemetry frame; a
   FreeRTOS task drains the ring buffer to the CDC handle. Use the
   ST USB device middleware (CDC) — don't hand-roll USB descriptors.
3. **ADC sanity (2 h).** Configure ADC + DMA in circular mode, stream raw
   codes over USB, plot in Python. You're looking for: (a) sensible noise
   floor, (b) no aliasing at 10 kHz, (c) stable offsets. Write
   `scripts/plot_telemetry.py` — this becomes your bench dashboard all
   semester.
4. **Timer chain (2 h).** Wire TIM1 TRGO → ADC start-of-conversion so the
   current sample happens mid-PWM-window. Verify by logging a synthetic
   pattern (toggle a GPIO in the ADC ISR, measure with a scope if you have
   one).
5. **Document (1 h).** In `docs/plan/TRACKER.md` tick week 2; note the
   exact frame format you chose (you'll thank yourself in week 7).

## Verification

- Scope or logic-analyzer (even a cheap one): 100 kHz PWM on 3 channels,
  correct dead time (no overlap).
- `t, count, Vbus` streams at ≥ 1 kHz with < 1% dropped frames for 5 min.
- Python script parses the frames and plots Vbus noise.

## Pitfalls

- **APB prescaler confusion.** If your timer counts at half what you
  computed, the APB prescaler ≠ 1. Recheck the clock tree, don't fight it.
- **USB in the ISR.** Never call CDC send from an ISR. Ring buffer + task.
- **ADC sample too early/late in the PWM window** → current spikes every
  cycle. Move the trigger; 20–50% into the active pulse is the usual sweet
  spot.
- **Dead time too small** → shoot-through → blown FETs (and possibly the
  board). 0.5 µs is a sane start; verify before applying bus power.
