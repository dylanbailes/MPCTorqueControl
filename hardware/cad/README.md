# CAD parts and references

The [current custom Fusion parts](custom/README.md) include eight independent
Fusion archives, STEP solids, and millimeter STL meshes. The current assembly
disk is 70 × 6 mm; its [as-modeled inertia sweep](inertial_disk/as_modeled/calculations.json)
uses that exact geometry. The export manifest separates original feature history
from clean solid snapshots where supplier children were omitted.

The [proposed adjustable inertial disk](../parts/inertial_disk.md) has a
dimensioned reference, an importable DXF profile, and calculated symmetric
weight configurations in `inertial_disk/compact/` and `inertial_disk/raised/`.
The compact swept envelope clears the modeled rails/braces at the recorded
placement. The new mounting collar, strength and operating speed remain
provisional; these are not released manufacturing drawings.

This directory documents reference geometry used during mechanical planning.
Downloaded STEP files and local STL exports are ignored by Git pending
confirmation of redistribution rights. Obtain geometry from the original
provider and verify dimensions against the actual parts before use.

| Local reference filename | Recorded source / purpose |
|---|---|
| `BGM5208-200-12.step` | GrabCAD; legacy motor envelope, not the selected 4015 |
| `B-G431B-ESC1.step` | ST board reference |
| `AS5048A_breakout.STEP` | Encoder breakout reference; module dimensions vary |
| `6153K111_Corrosion-Resistant 440C Stainless Steel Ball Bearing.STEP` | McMaster-Carr bearing reference |
| `2020_Extruded_Aluminum_600mm.STEP` | Extrusion reference; verify slot geometry |

The [Fusion design plan](../../docs/plan/fusion_cad_plan.md) records the earlier
assembly approach. It contains legacy motor geometry and placeholders. A complete assembly archive and validated manufacturing
releases are not supplied; the current custom-part snapshots are available above. See [third-party terms](../../THIRD_PARTY.md).
