# STM32 firmware: control modules and integration scaffold

Target board: STM32G431 on the B-G431B-ESC1. The portable control modules
implement the Python project's control math. This directory does not contain
a complete CubeMX project, HAL sources, linker script, or a verified board
build. `main.c` has an explicit compile-time integration guard because its
platform functions still contain placeholders.

## Implemented modules

| Source | Responsibility |
|---|---|
| `Core/Src/foc.c` | Clarke/Park, q-axis PI, SVPWM math |
| `Core/Src/encoder.c` | AS5048A angle decode and filtered wrapped velocity |
| `Core/Src/sea_observer.c` | Calibrated spring-torque estimate |
| `Core/Src/admm.c` | Box-constrained ADMM using exported Cholesky factor |
| `Core/Src/mpc.c` | Condensed MPC gradient and current/slew constraints |
| `Core/Src/impedance.c`, `safety.c` | Experimental impedance and collision response |
| `Core/Src/tasks.c` | Proposed loop composition, telemetry, and FF history |
| `Core/Src/main.c` | Board-integration sketch; requires replacement |

Generated `mpc_model.h` and `learned_model.h` match the published simulation
snapshot in [results/](../results/README.md). The fixture-specific MPC export
assumes blocked output; it must be redesigned for free-load operation.

Host tests compile portable modules with warnings treated as errors and
compare the C MPC against Python. They also compile `tasks.c` without linking
board support. This checks math and interfaces, not hardware timing,
peripheral correctness, or safe operation.

## Board integration still required

1. Generate an STM32CubeMX project with the actual pin map, clock tree,
   HAL, startup code, linker script, and RTOS configuration. Integrate the
   modules rather than attempting to flash this scaffold.
2. Implement the selected motor's MT6701 ABZ timer driver and commissioning
   I²C path. The current encoder module is an AS5048A SPI implementation;
   `tasks.c` still uses the legacy two-SPI setup.
3. Implement and validate AS5048A command parity, pipelined read responses,
   error handling, chip select, and angle unwrapping across revolutions.
4. Replace ADC placeholders with synchronized current acquisition and
   calibrated offsets/scales. Replace `pwm_update()` with actual PWM writes
   and gate-driver enable/fault handling. Avoid blocking HAL polling in ISRs.
5. Commission electrical angle offset and pole-pair count. The FOC module
   implements q-axis PI only; d-axis regulation and dq decoupling remain
   to be completed. Back-EMF compensation uses measured velocity.
6. Replace legacy electrical parameters in `control_init()` with measured
   motor values. Configure offsets, current limits, spring calibration,
   and exports together. The supplied constants are simulation fits.
7. Use real CMSIS-RTOS functions and telemetry transport. Remove sketch
   stubs, establish interrupt priorities, and verify coherent state sharing.
8. Measure ISR execution and jitter, encoder failure behavior, current/thermal
   limits, and physical collision response before proceeding through
   [the hardware milestones](../docs/MILESTONES.md).

## Intended loop rates

| Loop | Target rate | Validation |
|---|---|---|
| Current | 10 kHz | Timing and sensing not measured on board |
| Torque | 2 kHz | Modeled period; host math checked |
| Impedance/collision | Composed in the 2 kHz torque ISR | Hardware behavior unverified |
| Telemetry | 1 kHz | Transport and scheduling unimplemented |

The final current command, including feedforward, is clamped to `MPC_U_MAX`.
The QP's next-step history uses that applied command. Collision detection
commands zero current and latches; it is an experimental mechanism, not a
validated human-safety guarantee.

After hardware identification, regenerate both headers into a scratch output
directory, validate the configuration, and copy them into `Core/Inc/` together.
`MPC_MAX_ITER` records the exported iteration budget. Re-exporting a residual
model with a lag other than two requires updating the history call in `tasks.c`.
