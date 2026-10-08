# Inertial disk reference variants

The [proposed specification](../../parts/inertial_disk.md) supersedes the
first, 196 mm-only proposal after the user supplied the 41 mm shaft height
and 100 mm axial space.

- `as_modeled/`: current Fusion disk, 70 × 6 mm with 8.2 mm bore and three
  mounting holes on a 16 mm circle; 26 configurations. Native geometry is in
  [the custom parts snapshot](../custom/README.md).
- `compact/`: 72 x 4 mm carrier at 41 mm shaft height; 26 configurations.
- `raised/`: 196 x 4 mm carrier at 110 mm shaft height; 28 configurations.

Each folder has a mm DXF profile, PNG/SVG reference, estimated configuration
table, recommended sweep subset and randomized three-repeat run manifest.
The compact folder also includes the read-only CAD envelope check.

For the compact and raised proposals, the central mounting pattern is for a
proposed separate disk collar/flange,
not the existing spring-to-shaft coupler. Verify final hub fit, hardware,
retention and load capacity before manufacturing. Generated tables are
planning estimates; they contain no experimental measurements.

Regenerate with `python hardware/inertial_disk_design.py` or add
`--profile raised` or `--profile as_modeled`. Supply measured masses for final experimental estimates.
