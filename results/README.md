# Published simulation evidence

`results.json`, `plots/`, `mpc_model.h`, and `learned_model.h` form one
published snapshot of the selected 4015 parameter scenario. The generated
headers are also copied into `firmware/Core/Inc/`. The full configuration,
durations, seeds, dependency versions, and integration step are recorded in
`results.json` under `provenance`.

Reproduce it from the repository root:

```bash
python -m sim.run_experiments --r 4.8 --l 0.0026 --kt 0.1562 --jm 0.00003 --u-max 3 --n 30 --out-dir results/scratch/4015
```

`--fast` uses shorter windows and is a smoke run, not the published experiment.
The default plant parameters describe a separate nominal scenario. Timing
reported in `wall_seconds` measures a desktop run, not embedded loop timing.

Other retained evidence:

- `params_4015.json`: earlier horizon/current design study.
- `jm_robustness.json`: earlier inertia sensitivity study.
- [archive/](archive/README.md): earlier GM5208 parameter scenarios and pre-lag fits.

Those older studies predate the public-release controller fixes and are kept
for context. Regenerate them before relying on their numbers. New experiments
belong in the ignored `scratch/` directory until reviewed for publication.

[Website visuals](website/README.md) provide presentation graphics in PNG/SVG.
Regenerate them with `python scripts/website_visuals.py` when promoting a new
snapshot. Detailed time-domain plots remain in `plots/`.
