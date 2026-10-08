# Hardware design and planned build

The planned actuator couples a 4015 BLDC motor to a load through a torsion
spring. An integrated MT6701 motor encoder and AS5048A load encoder provide
differential angle feedback. The B-G431B-ESC1 is the intended drive board.
Assembly, calibration, and physical performance are not established by the
simulation results.

- [Spring design calculations](spring_design.py): run with `python hardware/spring_design.py`.
- [Bill of materials](BOM.md): planning estimates and source links.
- [Parts notes](parts/README.md): candidate specifications and acceptance checks.
- [Custom Fusion parts and CAD inventory](cad/README.md): current custom-part exports, inertia sweeps, and supplier reference notes.
- [Hardware milestones](../docs/MILESTONES.md): measurements required for validation.

Parts notes include earlier GM5208 design assumptions. For the selected 4015
simulation scenario, use [the results provenance](../results/results.json).
Supplier specifications and simulation assumptions require bench confirmation;
published simulation numbers do not qualify the hardware or establish safety.
