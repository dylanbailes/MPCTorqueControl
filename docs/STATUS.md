# Project status and next steps

## Completed in the repository

- Two-mass actuator simulation with RK4 integration, current-loop dynamics,
  voltage saturation, friction, cogging, torque ripple, and quantized angles.
- Spring calibration and inertia identification with an independent
  frequency-domain cross-check.
- PID and constrained MPC comparisons on smooth/edge-rich references,
  motor-side disturbance steps, and an impedance/stall-response demo.
- Residual fitting with causal history, held-out evaluation, generated C
  constants, and portable C modules checked against Python on a host.
- Automated Python and host C regression checks, reproducible experiment
  commands, and a curated simulation snapshot.

## Limits of the evidence

Simulation uses true velocities and current states; angle measurements are
quantized and include seeded noise. Hardware velocity estimation, current
sensing, thermal drift, delay, and changing friction are not validated.
All comparisons use fixed controller gains and a narrow fixture/reference
set. They do not establish a generally optimal MPC/PID comparison.

The observer implemented here is a filtered torque-balance residual; it
does not subtract rotor acceleration as a full momentum observer would.
The demonstrated grip detection primarily relies on a stall latch. Setting
zero current after detection does not guarantee safe physical interaction.

The slew constraint applies to the optimized first MPC command. Added
feedforward can change the final slew; it shares the hard current limit.
There is no formal stability/passivity proof for the augmented controller.

The MATLAB scripts, CubeMX integration, and physical actuator have not been
reverified in this review. The supplied firmware is not a complete board build.

## Next engineering priorities

1. Complete board support, calibrated current sensing, MT6701 feedback, and
   motor alignment; measure loop timing before enabling torque control.
2. Assemble and calibrate the spring/load, identify actual motor parameters,
   and overlay logged bench data against the simulation.
3. Reproduce PID/MPC comparisons with matched authority and separately tuned
   gains, multiple runs, uncertainty intervals, and timing measurements.
4. Evaluate noise/delay sensitivity and thermal/current limits. Compare
   plain MPC, identified friction FF, and learned FF using held-out bench data.
5. Record a physical demo with scope traces and measured results, then update
   the project status and website description to reflect that evidence.

The [milestones](MILESTONES.md) and [semester plan](plan/README.md) are planning
documents. Unchecked tasks and older parameter targets are not completed work.
