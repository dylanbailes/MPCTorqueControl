# Firmware — STM32G431 (B-G431B-ESC1)

The firmware mirrors the Python digital twin 1:1 (same math, same structure),
so the control stack is validated in simulation before it runs on hardware.

## Hardware

* **ST B-G431B-ESC1** (STM32G431CB, 170 MHz, with 3-phase inverter, current
  sensing, USB and CAN on board).  This is the "FOC power stage" — you write
  the field-oriented control yourself on the STM32.
* **2× AS5048A magnetic encoders** (14-bit, SPI): motor-side and output-side.
* Motor + torsional spring + load per the hardware BOM in `../hardware/`.

## Project setup (STM32CubeMX)

1. New STM32G431CB project in CubeMX (or STM32CubeIDE).
2. Clock: PLL to 170 MHz (SYSCLK = 170 MHz, APB1 = 170 MHz).
3. Timer **TIM1** (advanced) → PWM generation on CH1/CH2/CH3 (motor phases),
   with dead-time insertion (~0.5 us).  PWM counter period 1700 → 100 kHz PWM.
4. Timer **TIM2** → 10 kHz update interrupt (current loop), `TIM2_IRQHandler`.
5. Timer **TIM3** → 2 kHz update interrupt (torque loop), `TIM3_IRQHandler`.
6. **SPI1** → AS5048A motor encoder; **SPI2** → AS5048A output encoder
   (or a second CS line on one SPI).  CS = GPIO outputs.
7. **ADC1** → 3 phase currents (with the B-G431B-ESC1 sense resistors), or
   use the two-shunt method; trigger from TIM1.
8. **USB** (CDC) for logging/telemetry; optionally **CAN** for the torque
   reference from a host.
9. FreeRTOS (CMSIS-RTOS v2) with tasks as in `Core/Src/tasks.c`.

## File map

| File | Role |
|---|---|
| `Core/Src/main.c` | init, ISR wiring, calls into the loop |
| `Core/Src/tasks.c` | FreeRTOS tasks: telemetry, safety, impedance setpoint |
| `Core/Inc/foc.h/.c` | Clarke/Park/SVPWM + current PI (port of `model/foc.py`) |
| `Core/Inc/encoder.h/.c` | AS5048A SPI read, velocity via filtered difference |
| `Core/Inc/sea_observer.h/.c` | torque from calibrated spring curve |
| `Core/Inc/admm.h/.c` | ADMM QP solver (port of `model/qp.py`) |
| `Core/Inc/mpc.h/.c` | condensed MPC, uses `mpc_model.h` (port of `model/mpc.py`) |
| `Core/Inc/impedance.h/.c` | impedance reference + momentum observer |
| `Core/Inc/safety.h/.c` | stall detection + safe-stop |
| `Core/Inc/learned_model.h` | **generated** — copy from `results/learned_model.h` |
| `Core/Inc/mpc_model.h` | **generated** — copy from `results/mpc_model.h` |

## Calibration workflow on hardware (see `../docs/milestones.md`)

1. **Encoder alignment**: find the electrical angle offset per motor phase
   (feed 0 V dq, rotate, record) — `foc_align()`.
2. **Spring calibration**: hold the motor with the current loop, hang weights
   on the output, record (torque, deflection); fit k_s (Python script in
   `../learn/system_id.py`, reuse the same least-squares fit).
3. **System ID**: run the chirp excitation, log at 2 kHz, fit with
   `../learn/system_id.py`; write Jm, bm, Jl, bl into the MPC model export.
4. **Regenerate** `results/mpc_model.h` and `results/learned_model.h` with the
   identified parameters, copy into `Core/Inc/`.

## Loop timing budget (170 MHz, FPU on)

* Current loop (10 kHz): FOC transforms + 2 PI + SVPWM ~ 5-10 us.
* Torque loop (2 kHz): observer + MPC solve (N=20, 25 ADMM iterations:
  2 triangular solves + box project per iteration) ~ 30-60 us; budget 250 us.
* Impedance/safety (1 kHz): trivial.

> The firmware is written to compile on your machine with the ST toolchain.
> The `Core/` layout follows CubeMX conventions; `model/` and `learn/` in the
> repo root are the validated Python twins.
