# Public-release review

Review date: October 7, 2026. The public presentation should describe this
project as **simulation-tested SEA torque control with portable C modules
and ongoing STM32/hardware integration**.

## Cleanup and verification

- Final local suite: **49 tests passed**, with Python 3.12 and the Clang host
  compiler supplied by Zig. Full selected-scenario experiment completed;
  disturbance/collision figure refresh reproduced the recorded metrics.
- Replaced stale headline claims and metrics with the current selected
  4015 simulation snapshot, including configuration, seeds, and dependency versions.
- Fixed C export formatting, current-budget handling, controller resets,
  applied-command history, solver stopping, and firmware interface/math defects.
- Added host C compilation/parity checks and GitHub Actions configuration.
- Generated matched README/results summaries and website PNG/SVG graphics.
- Moved older parameter experiments under `results/archive/`, with historical
  labels. Kept local development metadata and superseded exports in ignored backups.
- Excluded environments, tool state, credentials, scratch runs, and downloaded
  CAD from the publishable working tree. Original code/documentation use MIT;
  third-party rights are documented separately.
- Checked local documentation links, finite JSON, matching generated headers,
  installed dependencies, and patch whitespace.
- Inspected the publishable working tree and all reachable pre-release history
  for common private-key, GitHub-token, AWS-key, and OpenAI-token
  patterns. No matches were found. This is a pattern-based check, not a
  guarantee that every possible secret format was recognized.

## Publication verification

On October 7, 2026, the repository's GitHub settings and existing content were
inspected before publication. The account has repository administration access;
there are no existing issues, pull requests, review comments, releases,
workflow runs, or workflow artifacts to expose. The only branch is `main`.

The release procedure commits the reviewed changes, pushes to `main`, checks
the Linux/Python 3.11 and 3.12 CI jobs, and then switches repository visibility
to public. The repository description and topics reflect the simulation-stage
project. Git history is preserved. The Actions tab is the live source for
remote check results after publication.

## Next milestone that strengthens the portfolio

Complete board bring-up and publish a calibrated physical test with timing
measurements, repeated runs, and a short demo. That will connect the existing
simulation/control work to the mechanical and embedded implementation.
See [STATUS.md](STATUS.md) for the engineering priorities.
