# Adjustable inertial disk: compact and raised designs

The current Fusion snapshot is a separate **70 Ã— 6 mm** disk with an **8.2 mm
bore**, **eight 6.4 mm holes on 50 mm PCD**, and **three 3.2 mm mounting holes
on 16 mm PCD**. See [native exports and its matching sweep](../cad/custom/README.md).
The dimensions below describe proposed alternatives, not edits to that snapshot.

Revised 7 October 2026 from the user's CAD image and measurements: the shaft
center is **41 mm above ground**, the space beneath the disk is clear, and
approximately **100 mm along the shaft** is available. First iteration is
3D printed. The user wants many inertia settings and a wide experimental
range, and authorized comparing the existing-height and raised alternatives.

## Recommendation and comparison

Start testing with the **existing 70 × 6 mm disk** using its matching
[as-modeled sweep](../cad/inertial_disk/as_modeled/calculations.json). It already
fits the current hub pattern. The **72 mm compact carrier** below is an
alternative, not a required replacement. Fixed studs let you collect a dense
sweep without rebuilding the supports.
Use the **196 mm raised carrier** if the experiment must include the original
1.2e-3 kg m^2 model value and higher loads. Raise both load bearings AND the
motor axis together; preserve spring alignment and active length.

| Feature | Compact: existing rig | Raised: broader absolute range |
|---|---|---|
| Shaft height above ground | 41 mm | 110 mm (+69 mm) |
| Carrier OD x thickness | **72 x 4 mm** | **196 x 4 mm** |
| Ground clearance | 5 mm | 12 mm |
| Weight radii / PCDs | **26 / 52 mm** | **40 / 80; 52 / 104; 80 / 160 mm** |
| Weight stations per occupied circle | 8 at 45-degree intervals | 8 at 45-degree intervals |
| Steel mass washers | **M6: OD18, ID6.4, nominal t1.6 mm** | **M8: OD24, ID8.4, nominal t2 mm** |
| Estimated metal washer mass | 2.792 g | 6.232 g |
| Carrier locator holes | 8 x diameter 6.6 mm | 24 x diameter 8.4 mm |
| Maximum calculated washers per face per station | 12 | 4 |
| Maximum mass-washer count | 192 | 64 |
| Physical configurations including bare carrier | **26** | **28** |
| Estimated total J range, kg m^2 | **0.000022 to 0.000466** | **0.000705 to 0.003833** |
| With permanent kits installed, J range | 0.000076 to 0.000466 | 0.000833 to 0.003833 |
| Carrier + kits + weights at maximum | ~638 g | ~626 g |
| Axial stud envelope | 75 mm | 75 mm |

The J ranges include a **1e-5 kg m^2 external allowance** for rotating shaft,
hubs, central fasteners, magnet holder etc. They are not calibrated values.
The listed masses exclude those external parts' masses. Higher stack counts
are proposed configurations, not verified load or speed ratings.

The compact rotor cannot conveniently reproduce the original model inertia:
even an ideal thin ring of radius 36 mm would require about 926 g to reach
1.2e-3. At the actual 26 mm stations the real steel mass required is higher;
with this layout the calculated requirement is roughly 1.6 kg of mass washers
and approximately 72 mm of washer stack on EACH face. That exceeds the
100 mm axial space before hardware is added. Dense compact loads are useful
for lower-inertia experiments, rather than forcing the original target.

## Make weight changes repeatable: two four-station groups

Number the eight stations from +X, counterclockwise in a front view.

- **Group A:** stations 1, 3, 5, 7 (0, 90, 180, 270 degrees).
- **Group B:** stations 2, 4, 6, 8 (45, 135, 225, 315 degrees).

Within each group, every station has the same number of mass washers on
both faces. A and B can have different layer counts. Each group independently
has four-fold symmetry: center of mass remains on the shaft, Ixx = Iyy,
and ideal products of inertia vanish. Two opposite weights alone would
balance the center of mass but would not give equal transverse moments.

The sweep uses A/B face counts **0/0, 1/0, 1/1, 2/1, 2/2, ...**.
Each step adds eight washers: one on each face at four stations. Compact
increments are about **1.625e-5 kg m^2**, including the printed washer inserts.
Use one occupied circle at a time in the raised carrier. Adjacent radial
holes are too close to install overlapping washer stacks simultaneously.

An A/B value of 3/2 means three washers on EACH face at all four A stations
and two washers on EACH face at all four B stations: 40 washers total.
All permanent retention kits stay installed during the normal sweep.
The separate BARE configuration removes those kits too.

| Compact example | Total mass washers | Estimated J, kg m^2 |
|---|---:|---:|
| Bare carrier | 0, kits removed | 0.000022 |
| A/B 0/0 | 0, kits installed | 0.000076 |
| A/B 1/0 | 8 | 0.000092 |
| A/B 1/1 | 16 | 0.000109 |
| A/B 3/3 | 48 | 0.000174 |
| A/B 6/6 | 96 | 0.000271 |
| A/B 9/9 | 144 | 0.000369 |
| A/B 12/12 | 192 | 0.000466 |

For the raised disk, one washer per face everywhere at **R52** gives about
**0.001202 kg m^2**, close to the original target with these fixed kits.
Moving those SAME assemblies between R40, R52 and R80 gives about
0.001003, 0.001202 and 0.001871 kg m^2 at the same total mass. That helps
separate inertia effects from changes in static bearing load.

## Permanent studs and washer locating inserts

Use **eight M4 steel threaded studs, 75 mm long**, centered through the
carrier. They can be cut from threaded rod and deburred. Lock each stud to
its carrier with a plain M4 nut and a retaining flat washer on BOTH faces.
Use nominal 3.2 mm plain nuts and nominal 0.8 mm retaining washers. Outer
retaining washers and M4 locking nuts clamp the changing mass stacks.
Retaining washers should be at least 9 mm OD to bridge the M6 washer bores.
For the M8 weights, use at least 12 mm OD retaining washers.

Keep the complete stud kit installed at every setting, including zero mass
washers. This avoids changing screw mass when changing stack height. Each
step requires moving four outer nuts on each face, then installing eight
mass washers. Pre-sort the washers in eight-piece bags and label the disks'
A/B groups. Measure complete station masses, not just the washer count.

A short **3.8 mm long** locator sleeve centers each stud through the 4 mm
carrier: compact OD6.2 / ID4.3; raised OD8.2 / ID4.3. The retaining washers
and nuts clamp the carrier rather than bottoming on the short sleeve.

Each mass washer gets its own printed centering insert:

| Insert | Outside diameter | Bore | Thickness |
|---|---:|---:|---:|
| Compact M6 washer insert | 6.2 | 4.3 | 1.2 mm |
| Raised M8 washer insert | 8.2 | 4.3 | 1.6 mm |

Each insert is thinner than the minimum purchased washer thickness, so
steel washers bear against each other rather than loading the inserts.
Inserts guide the washer bores around the M4 studs; they prevent the large
bores from permitting several mm of off-center movement. Verify clearances
with a print coupon and the actual batch. If the nominal loose sleeve does
not adequately locate a washer, adjust OD to measured fit; no forced press
fit is required. Inserts are small parts; a high-quality print or machined
polymer version is preferable to poor, inconsistent FDM holes.

The compact maximum, assuming worst-case 1.8 mm washers, requires about
**69.6 mm** including carrier, inner nuts/washers, both mass stacks, outer
washers, 5 mm locking nuts, and two projecting thread pitches at each end.
The 75 mm studs leave margin and fit the stated 100 mm slot, with about
12.5 mm clearance on each side when centered. Actual nut dimensions and
stud centering must be checked. Raised stacks use less axial space.

Planning **retention-kit mass is 10 g per station**, including one stud,
two inner plain nuts, two outer locking nuts, four retaining washers and
the carrier sleeve. Weigh the actual kit and replace that estimate. The
calculator treats kit mass at the station radius and omits its small
intrinsic polar inertia. Its long axial extent DOES affect transverse
inertia; four-fold symmetry keeps transverse moments equal but does not
make the rotor behave like a thin planar lamina.

## Disk-to-shaft interface and placement

The now-open Fusion assembly was read without editing it. It shows an
**8 x 200 mm steel shaft**. The component named `Hub for Load Disc` has an
approximately **22 mm OD, 30 mm long** envelope and an **8.05 mm bore**.
It appears to be the spring-to-shaft coupler near the first bearing, rather
than a disk mounting flange. Use a **separate disk collar/flange** within
the bearing span; avoid putting the inertial load on the projecting spring
bar or requiring a modification of that existing coupler.

Proposed common disk interface for both carriers:

- Center pilot hole **14.2 mm**, mating pilot **14.0 mm**.
- Four **3.4 mm through holes** for M3 screws, **22 mm PCD**.
- Hole angles **22.5, 112.5, 202.5, 292.5 degrees**.
- Separate flange **28 mm OD**, about 4 mm thick, flat seating face.
- Split shaft-clamping collar: measured 8 mm shaft bore (8.05-8.10 mm is
  a starting print-fit value), about 22 mm OD and 10-12 mm axial length.

These flange/collar dimensions are proposed, not measured existing features.
The flange should locate concentrically and positively transmit torque.
Size its clamp screw, heat-set inserts and wall sections in the final collar
CAD; do not substitute a friction-only loose disk bore around the shaft.
Both disks' DXFs use this common interface. An 8 mm shaft hole by itself
would not secure the carrier.

Place the compact carrier roughly midway along the **100 mm clear slot**,
with its studs centered through it. Reserve the full 75 mm swept axial
volume, and rotate the complete envelope through 360 degrees in CAD.
Verify clearance to the diagonal braces, rails, bearing supports, collars
and encoder hardware. Ground clearance alone does not prove assembly
clearance; the user image does not provide every brace measurement.

A read-only transient CAD check then tested a **72 mm diameter x 75 mm
axial envelope**, centered at assembly coordinates approximately
**(-6.742, 463.521, 18.690) mm**, aligned with the shaft. It did not intersect
the ten modeled rail/brace bodies overlapping that axial interval. The same
test passed at radii **37 and 38 mm**, providing 2 mm radial allowance against
those modeled parts. The intentional shaft intersection was excluded.
The document remained unmodified. Ground, new collar/rotor hardware and
unmodeled fasteners were not part of that collision check; verify them in
the final assembly. Evidence is in `compact/assembly_clearance.json`.

For the raised option, the shaft datum increases by **69 mm** to 110 mm.
Prefer new, gusseted bearing towers and a matching motor mount over a tall
unsupported printed spacer. Support stiffness changes can affect identified
modes; preserve bearing spacing and the spring geometry, and repeat ID after
changing mount height. The 196 mm disk also needs full brace/rail checks.

The live CAD assigns **Steel** to the existing load hub (~68.5 g in CAD).
If that hub will be printed, set its actual polymer material before trusting
its mass properties. Its volume corresponds to roughly 10.8 g at the PLA+
planning density. The steel 200 mm shaft mass reported by CAD is ~78.3 g;
its own polar inertia is about 0.63e-6 kg m^2. The external 1e-5 allowance
remains provisional until all actual rotating parts are included.

## Printing and initial verification

Print the flat carriers in PLA+ for the first iteration, 0.2 mm layers,
5-6 perimeters and fully solid thickness. A 4 mm plate can be printed as
20 solid layers. Full solidity is chosen for predictable mass distribution
and local clamping, not because infill alone guarantees strength. Measure
actual flatness and mass; the planning density is 1240 kg/m^3.
Keep labels shallow and repeated symmetrically; avoid a single heavy tab.

Match opposite complete stations within about **0.05 g**, using a scale
resolving 0.01 g. Match face-stack thicknesses as well as mass. Check rim
radial runout (~0.2 mm TIR initial goal), face runout (~0.3 mm TIR), clamp
settling, stud retention and bearing friction. Static balance checks can be
masked by bearing drag; validate running vibration too.

Begin with the zero-weight and low-stack configurations and bounded slow
motion with a guard. Check the highest load later, including printed carrier
flexure, shaft deflection and fastener retention. The ~0.64 kg compact
maximum is a calculation case, not an approved load capacity. No maximum
RPM has been established. Update the physical plant's load inertia before
using a controller tuned for the old 1.2e-3 model on the compact rotor.

## Experimental design for useful analysis

The geometry gives **54 nominal configurations** across both carriers.
Some raised settings have almost identical J at different mass/radius; they
are useful comparisons but should not be counted as independently resolved
inertia levels until their uncertainty is known. A supplied initial subset
keeps successive estimated inertias at least 5% apart: **22 compact and
20 raised settings**. Five percent is a planning interval, not a guaranteed
measurement resolution; merge/space settings based on measured uncertainty.

For each chosen configuration:

1. Record A/B counts, radius, actual weight/kit masses, carrier identity and
   measured/identified J with uncertainty. Save raw time-stamped angle,
   velocity, current, torque reference and estimated spring torque data.
2. Run the same defined excitation and reference family, with both motion
   directions. Fit J and friction together using the existing integrated
   system-ID workflow; changing mass can change bearing friction.
3. Repeat at least three times, with randomized configuration order in
   repeated blocks. Check a common baseline every 5-6 configurations to
   detect temperature, wear or clamp changes. Reconfiguration time may
   justify short blocks, but do not always increase weights monotonically.
4. Separate fixed-controller robustness experiments from experiments where
   the controller is retuned/re-exported for each J. Record which mode was
   used; otherwise tuning changes can be mistaken for inertia effects.
5. Compare tracking RMS, peak error, settling time, current RMS/peak,
   saturation duration, identified load modes and execution timing under
   matched excitation, temperature and current limits.

There are **78 compact and 84 raised planned runs** in the full three-repeat
manifests. They are templates, not collected data. For the raised carrier,
include fixed-mass radius changes to help distinguish inertia effects from
mass-dependent friction. As inertia increases, choose excitation that stays
within current and travel limits; record any changed excitation explicitly.

## Artifacts and recalculation

Current references are in `hardware/cad/inertial_disk/compact/` and
`hardware/cad/inertial_disk/raised/`. Each contains a mm DXF, PNG/SVG layout,
all configurations, a recommended sweep subset, calculations JSON and a
three-repeat run manifest. The root-level files from the first proposal
are obsolete and are replaced by a redirect note.

Run `python hardware/inertial_disk_design.py` for compact or add
`--profile raised`. Options include `--carrier-mass-g`, `--washer-mass-g`,
`--insert-mass-g`, `--kit-mass-g`, and `--external-inertia`. Measure each
actual component; a uniform carrier-mass correction assumes a fully solid
part. Pattern quantity is unitless in native Fusion CAD; derive sketches
from named diameter, thickness, radius and count parameters.

Formula for one washer: `J = m * (r^2 + (Ro^2+Ri^2)/2)`.
The calculator includes metal washers and printed inserts separately,
carrier cutouts, kit mass at radius, and the supplied external inertia.
Ideal first/second planar moments, hole separation and washer separation
are checked for every configuration. Native Fusion parts were not modified.

Sources: user's dimensions and image; read-only Fusion `Full Assembly FOR SEA`;
project `model/plant.py` and `learn/system_id.py`;
[Bolt Depot M6 x 18 steel washers](https://boltdepot.com/Product-Details?product=17831)
(1.4-1.8 mm thickness),
[Bolt Depot M8 x 24 steel washers](https://boltdepot.com/Product-Details?product=17832)
(1.8-2.2 mm thickness),
[McMaster fender washer catalog](https://www.mcmaster.com/products/fender-washers/)
(nominal bores vary by product),
[MIT inertia matrix and parallel-axis theorem](https://ocw.mit.edu/courses/2-003sc-engineering-dynamics-fall-2011/resources/parallel-axis-theorem/),
[Prusa layers/perimeters](https://help.prusa3d.com/article/layers-and-perimeters_1748),
[Prusa infill guidance](https://help.prusa3d.com/article/infill_42).
