# Week 5 — Mechanical Build: the SEA Rig (M1)

**Phase 1 · Motor + build** — ~11 hours

## Exit criteria (week done when…)

- [ ] Rig assembled: motor → torsion bar → load disc, rigid base, MT6701
      motor encoder and AS5048A load encoder mounted on their shafts.
- [ ] Free-spin test: with the load free, a slow current ramp produces
      smooth motion with no binding; Δθ stays within ±0.05 rad during slow
      motion (no gross eccentricity or preload).
- [ ] Resonance measured empirically (sine sweep or impulse) and it matches
      the model's ~18 Hz within ±30%.
- [ ] You can disassemble and reassemble the spring coupling in < 10 min
      (you'll do it again in week 12 if you test a second spring).

## Why this week

This is the week your mechanical-engineering background becomes the
project's moat. The sim's resonance, the MPC's model, and the collision
demo all live inside this piece of hardware. A sloppy build is not a
"mechanical detail" — it's a plant-model mismatch that week 7's ID will
have to explain.

## Theory

### The torsion bar as a spring

For a round rod of diameter d and length L, shear modulus G, the torsional
stiffness and peak shear stress are:

```
k = G·J/L,      J = π·d⁴/32          (polar moment of inertia)
τ_max = 16·T/(π·d³)                  (solid round cross-section)
```

With the design values from `hardware/spring_design.py`
(2.5 mm × 304 mm, G = 79.3 GPa): k ≈ 1.0 N·m/rad, and at the design
torque 0.35 N·m the shear stress is ~114 MPa against a ~620 MPa yield —
**safety factor ~5**, essentially a linear spring over the whole operating
range.

Two mechanical truths that dominate everything:

1. **The bar is only as good as its end fixings.** A pinched, sloppy, or
   compliant coupling adds a series compliance that *lowers* effective ks
   and adds hysteresis. The bar must be rigidly pinned (dowel pins / set
   screws into hubs) — this is where torsion-bar SEAs fail in practice.
2. **The base must be rigid.** Any compliance in the frame is *in series*
   with the spring from the controller's point of view. Rule of thumb: the
   frame's first resonance should be ≥ 5× the spring's 18 Hz, i.e. ≥ 90 Hz.
   Extruded-aluminum + bolted plates achieves this; flexy 3D-printed PLA
   brackets do not.

### The blocked-output fixture (why it's in the sim)

Torque tracking through a spring is only well-posed when the output is
constrained — otherwise torque commands just accelerate the free load and
"tracking" is ill-defined. The classic bench fixture (and what
`model/plant.py` models with `k_block = 1e4`) is a **stiff spring-damper
from the load to ground** (clamp the disc with a high-stiffness brake, or
bolt the disc to the base through a stiff rubber mount). The sim showed
this fixture is a real dynamic: its ~460 Hz load mode must live in the
*continuous* plant, not in the 2 kHz controller's ZOH path (a discrete
feedback loop at that mode is unstable — this was a genuine bug found and
fixed during development; see the git history/`docs/RESULTS.md`).

**For this week:** build the fixture but keep the load *free* for the
resonance measurement; clamp it in week 8.

### Measuring the resonance

Two easy methods:

1. **Sine sweep:** hold the motor still (current loop at 0), apply a small
   sinusoidal *external* torque to the load (or command a tiny motor
   torque via the current loop) from 5–60 Hz, log Δθ amplitude, find the
   peak. Expect the peak near f_res = (1/2π)·√(ks(Jm+Jl)/(Jm·Jl)) ≈ 18 Hz
   with the design inertias.
2. **Impulse:** give the load a sharp tap, log the free decay of Δθ
   (or ωl), count zero crossings → frequency, fit the envelope → damping
   ratio. The damping you measure here is *the* number that determines how
   hard torque control is (week 8) — the sim's ζ comes from bm, bl and the
   fixture; compare honestly.

## Build plan

1. **Cut and pin the torsion bar (1.5 h).** Cut 2.5 mm drill rod to
   304 mm; deburr the ends; fit into printed/metal hubs; pin with dowel
   pins or set screws. Verify no play by hand-twisting: the bar should
   return to zero with no visible hysteresis.
2. **Assemble the rig (3 h).** Motor bolted to base; bar coupled to motor
   shaft hub on one end and load disc hub on the other; load disc with
   added mass to reach Jl ≈ 1.2e-3 kg·m² (see `spring_design.py` sizing:
   ~250 g at ~98 mm radius). Mount the integrated MT6701 magnet/encoder on
   the motor and the AS5048A board/magnet on the load; re-run the week-3
   noise and ABZ/I²C agreement tests after mounting.
3. **Free-spin test (1.5 h).** Command a slow current ramp (±1 A, 0.2 Hz)
   through the current loop; watch θm, θl, Δθ in the dashboard. Δθ should
   track smoothly; any stick-slip (Δθ staircase) is friction at a coupling
   or bearing — find and fix it now.
4. **Resonance sweep (2 h).** Run the sine sweep or impulse test; log the
   data to CSV. Fit f_res and ζ; compare with the model prediction.
   Update `model/plant.py` params (Jl, bm, bl) if the measurement says the
   sim is off — the sim is the oracle *after* you've explained why.
5. **Disassembly drill (1 h).** Practice taking the bar coupling apart and
   back together. Time it. (Week 12 needs a 10-minute swap.)
6. **Photo/video the build (1 h).** You'll want assembly photos for the
   writeup and the final demo; take them *now* while everything is clean.
7. **Tracker (0.5 h).** Record: measured f_res, ζ, effective ks guess from
   the decay, and any parameter updates to the twin.

## Verification

- Δθ smooth under slow ramp, |Δθ| < 0.05 rad, no stick-slip.
- Measured f_res within ±30% of 18 Hz; ζ recorded (expect 0.02–0.1).
- Bar returns to zero with < 0.5° residual after ±0.3 rad deflection.

## Pitfalls

- **Compliant base plate.** If the resonance measurement comes back at
  ~8 Hz when you expected 18, the *frame* is the spring. Rebuild the base
  before touching any controller gain.
- **Eccentric encoder magnet** (from week 3) will masquerade as a 1×/rev
  torque ripple all semester. Recheck it after assembly.
- **Bar preload from assembly** shifts the Δθ zero. Measure Δθ with the
  system at rest before every calibration session (week 6 builds this in).
- **Oversized hub set screws** can bend the bar locally → stress
  concentration → fatigue crack at exactly the wrong moment. Two small
  set screws beat one big one.
