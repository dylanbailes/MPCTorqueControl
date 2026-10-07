# Development and verification

Use Python 3.11 or 3.12 and install `requirements.txt` into a virtual
environment. The published snapshot's exact Python 3.12 dependencies are
recorded in `requirements-lock.txt`.

Before proposing a change:

```bash
python -m pytest -q
python hardware/spring_design.py
python scripts/check_repo.py
```

Use GCC or Clang for the host C tests (`CC=gcc` on Linux). A missing compiler
is reported as skipped tests. GitHub Actions runs the host checks with GCC.
Board integration and MATLAB require their own toolchains and verification.

Write scratch experiments to `results/scratch/<name>/`. When promoting a
result to the published snapshot, include the exact command and configuration,
retain simulation/hardware labels, copy both generated headers into
`firmware/Core/Inc/`, and regenerate the summaries:

```bash
python scripts/summarize_results.py
```

Metric windows and controller budgets must remain explicit. Keep meaningful
regression tests for changes to solver behavior, controller history, exports,
or measurement logic. Do not commit environments, credentials, assistant
configuration, or downloaded CAD without established redistribution rights.
