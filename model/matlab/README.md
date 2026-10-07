# MATLAB formulations

These scripts provide an independent formulation of the plant, condensed
MPC/ADMM, and system identification. They use MATLAB functions rather than
a checked-in Simulink model. They are not part of the Python/C CI checks.

From the repository root in MATLAB:

```matlab
addpath('model/matlab');
sea_plant_model;
mpc_design;
system_id;
```

Script parameters, references, and integration settings may differ from the
published Python experiment. Compare configurations before comparing metrics.
MATLAB execution has not been reverified as part of the public-release review.
