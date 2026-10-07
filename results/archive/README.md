# Historical experiments

These simulation artifacts document earlier design decisions. They are not
the current benchmark and predate fixes to current budget handling,
applied-command history, resets, and solver stopping criteria.

| Directory / file | Meaning |
|---|---|
| `results_real_r137/` | GM5208 scenario, R = 13.7 Ω/phase |
| `results_real_r685/` | GM5208 scenario, R = 6.85 Ω/phase |
| `results_real_r137_prelag/` | Residual fit without lag features |
| `results_real_r685_prelag/` | Residual fit without lag features |
| `tracking_comparison.png` | Superseded nominal tracking figure |

The historical name `real` means a motor parameter scenario; these are
simulation results, not physical bench measurements. Superseded C exports
are retained only in local development backups; regenerate from current code
before using an archived scenario.
Current evidence lives in [the parent directory](../README.md).
