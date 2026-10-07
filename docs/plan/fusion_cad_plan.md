# Fusion 360 CAD Plan — SEA Torsion-MPC Bench Rig

Complete mechanical design of the rig in Fusion 360, built and maintained
through the **Fusion MCP** (the official Autodesk Fusion MCP add-in already
configured in `.agents/mcp.json`, live and verified working against the
hub: 8 projects reachable, full Python script execution + screenshots +
undo available).

**Everything lives in a `Torsion MPC` folder in Fusion.** Parts that have
real models online (motor, bearings, shaft, extrusion, fasteners, boards)
are **imported as STEP, not redesigned**. Everything custom (printed hubs,
load disc, mounts, calibration fixtures) is built **parametrically** so a
measured dimension or a design change is a one-value edit that propagates
through every part, subassembly, and the top-level assembly.

---

## 1. Goal & success criteria

1. A complete, dimensionally-correct 3D model of the rig from
   `hardware/BOM.md` / `hardware/parts/*` — motor → torsion bar → load
   disc, integrated MT6701 motor encoder, AS5048A load encoder, base, mounts,
   and calibration apparatus.
2. Every custom part is **parametric** (user parameters + parameter-driven
   sketches/features), so updating = changing a parameter value.
3. The full rig is an **assembly of linked documents** (external
   references), so a part edit propagates to the assembly.
4. Imported parts are the real STEP models where they exist; nothing is
   redesigned from scratch that already has a model online.
5. Mass/inertia cross-check against the BOM: motor 204 g, load disc
   ~250 g with **J_l = 1.2005e-3 kg·m²**, total rig ~$309 BOM parts.
6. STL exports for the 3D-printed parts, ready to slice.
7. Everything saved under `Torsion MPC/` in the hub, with a documented
   maintenance loop ("change a parameter → assembly updates").

## 2. Tooling — what the Fusion MCP can do (verified against the live API)

| Capability | MCP call | Use here |
|---|---|---|
| Run Python scripts in Fusion (full `adsk.core` / `adsk.fusion` API) | `fusion_mcp_execute` (featureType `script`) | Build sketches/features, params, joints, imports, saves |
| Create / read / edit **UserParameters** | script via `design.userParameters` | The parametric backbone |
| Insert linked components (X-Refs) | script via `occurrences.addExistingComponent` / `addByInsert` / `addNewExternalComponent` | Parametric assembly that updates |
| Import STEP into a new doc or existing component | `adsk.core.ImportManager` (`importToNewDocument` / `importToTarget`) | Pull real online models in |
| Create hub **folders** + save docs into them | `adsk.core.DataFolder` / `DataFile`, `document.saveAs(...)` | "Torsion MPC" folder structure |
| List projects / search docs | `fusion_mcp_read` (projects, document search) | Locate/create everything |
| Screenshot the active view | `fusion_mcp_read` (screenshot) | Visual verification after every step |
| API documentation on demand | `fusion_mcp_read` (apiDocumentation) | Look up exact method signatures while scripting |
| Undo / redo | `fusion_mcp_update` | Recover from a bad operation |
| Electronics (schematic/PCB) | `fusion_mcp_electronics_read` | Only if we model the ESC1/encoder PCBs in Fusion Electronics (optional, see §9) |

**Constraint:** scripts execute synchronously on Fusion's UI thread —
Fusion must be open and idle while a script runs, no dialog boxes open,
and the add-in's script-execution prompt accepted on first run.

## 3. Part inventory — custom vs. imported

### 3a. Custom parametric parts (modeled, driven by UserParameters)

| Part | Key parameters | Source dims |
|---|---|---|
| `Motor_Hub` | bore = `motor_shaft_od` + clearance, bar pocket Ø2.5, dowel Ø2.5, M3 grub hole, depth | `drivetrain.md` — bore follows the *measured* shaft (15.0 hollow, or 6/8 solid clone) |
| `Motor_Encoder_Plug` | seats in `motor_shaft_id` (12.6), magnet pocket Ø6 × 3.2 deep, concentric | `encoders.md` |
| `Load_Hub` | bore Ø8, bar pocket, dowel, M3 grub | `drivetrain.md` |
| `Load_Disc` | `disc_od` (R≈98), `disc_thk`, washer bolt circle + holes, mass target 250 g → J_l 1.2e-3 | `spring_design.py`, `drivetrain.md` |
| `Bearing_Block_L/R` | 608ZZ seat Ø22 +0.05, width 7+1, M5 T-nut slots (6 mm slot), shaft center height | `drivetrain.md` |
| `Motor_Mount_Plate` | bolt PCD + hole dia (**measured** from the motor face), M5 slots to 2020 | `motor.md` (PCD not published — measure) |
| `Calibration_Hanger_Arm` | known radius r, hanger/eyelet, weight positions | `calibration.md` |
| `Blocked_Output_Clamp` | clamps the load disc (M3 milestone) | `MILESTONES.md` M3 |
| `Weight_Drop_Fixture` (optional, week 11) | drop mass + guide | `MILESTONES.md` / week 11 |
| `Option_B_Spring_Anchors` (only if Option B SEA chosen) | lever arm + 2 spring anchors at r=40 | `spring_design.py` |

### 3b. Imported parts (STEP from online — not redesigned)

| Part | Source (download → `hardware/cad/step/`) | Fallback if no STEP |
|---|---|---|
| Selected **4015 BLDC + integrated MT6701** | Selected Amazon motor listing; use a simplified parametric motor body if no STEP is available | Parametric body from `motor.md` with 10 mm OD / 7.5 mm hollow shaft; represent the integrated encoder/magnet assembly, named `Motor_Simplified` |
|
| | **Decision (Aug 26):** the BMG5208-200-12 GrabCAD STEP is accepted as **reference/visual geometry**. At import (P2) it gets a scripted bounding-box + shaft check against `motor.md` (Ø59.5 × 31.2, hollow 15/12.6). If it carries bolt holes, measure the mounting PCD off the STEP instead of calipering the motor. Fit-critical dims (hub bore, plug) NEVER come from the STEP — they come from the measured `motor_shaft_od` / `motor_shaft_id` parameters. |
|
| | **Measured at import (Aug 26, Fusion script):** body Ø63 × 24 mm (spec 59.5 × 31.2 → +6 % OD, −7 mm height); hollow shaft **Ø14.56 / 12.6 mm** (spec 15.0 / 12.6 → ID matches exactly, OD −0.44 mm). **No mounting-bolt circles in the model** → `motor_mount_pcd` stays a caliper measurement. Use as visual reference only; do not scale. |
| **608ZZ bearings ×2** | McMaster "608 ball bearings" (8×22×7) — STEP on product page | Parametric Ø8×22×7 body |
|
| | **Imported + validated (Aug 26):** McMaster **6153K111** (440C stainless) — union bbox 22 × 22 × 7 mm, bore Ø8 ✓ exactly matches the BOM's 608 requirement |
| **8 mm × 300 mm shaft** | **User-made STEP** (done Aug 26) — **validated: Ø8 × 300 mm exactly** ✓. Length changes are easier as a parametric cylinder: I'll keep the parametric `Load_Shaft` in `01_Parts` and use whichever matches reality | Parametric cylinder, `load_shaft_L` |
| **2020 extrusion ×2** | ⚠ **McMaster 5537T101 is metric but NOT verified European-2020-compatible** (McMaster sells Fath/own T-nuts for it — see §8 note). If buying it: pair with McMaster's own metric T-nuts for that rail, or verify the 6.0 mm slot + nut seat with calipers. **Safer default: the Amazon European-2020 sets already in the BOM** (SANTIE 4×400 mm etc.) which match the BOM's European spring T-nuts. Rail length decision: **order 2× 2 ft (609.6 mm)**, `rail_L` = 610 mm — the 1.5 ft (457 mm) option is too short once the load-side fixtures (hanger arm, blocked-output clamp, week-11 drop fixture) are on the rails | Parametric 20×20 profile with slot sketch |
| **M3/M5 screws, M3 grub, M5 T-nuts, 2.5 mm dowels, M12 fender washers** | McMaster per-item STEP (or one combined "fastener kit" file) | Simplified cylinders |
| **MT6701 integrated motor encoder + AS5048A load module** | Selected 4015 motor listing + generic AS5048A breakout STEP | Represent the integrated motor encoder with the motor assembly; model one load-side AS5048A board |
| **B-G431B-ESC1** | ST website STEP if available | Parametric board outline + heatsink |
| **Weight set** (calibration) | optional — GrabCAD weight model or simplified | Simplified cylinders |
| Torsion bar (music wire Ø2.5) | nothing online worth importing | Parametric cylinder, `bar_L` from `spring_design.py` |

Imported STEP bodies stay **dumb bodies** (that's fine — they're reference
geometry, not redesigned). Each import is saved as its own .f3d under
`Torsion MPC/02_Imports/`.

### 3c. Level of detail (agreed upfront)

- **Threads**: cosmetic only (no thread geometry) — speeds up the model.
- **Fasteners**: simplified correct-dimension cylinders/hexes; real ones
  only where they affect fit (grub screws in hubs).
- **Electronics**: board outline + connectors, non-structural.
- **2020 profile**: real imported profile (slots matter for T-nut fit).
- **Motor**: real STEP if found; otherwise the simplified parametric body.

## 4. Fusion folder layout ("Torsion MPC")

```
Project "Torsion MPC"  (created by user Aug 26 — files currently at the project root folder)
└── Torsion MPC/
    ├── (root)            BGM5208-200-12, 8mm x 300mm Steel Rod, 6153K111 bearing  ← imported + validated
    ├── 01_Parts/          parametric .f3d files (printed + parametric stand-ins)   ← to create
    ├── 02_Imports/        remaining imported STEP .f3d files (2020 ext., fasteners, boards)
    ├── 03_Subassemblies/  Motor_Side, Load_Side, Base
    ├── 04_Assembly/       SEA_Torsion_MPC_Assembly.f3d  (the master)
    └── 05_Outputs/        STL/STEP exports + BOM snapshot
```

Local mirror (repo):
```
hardware/cad/
├── README.md        (this workflow, naming, how to add a part)
├── step/            ← you drop downloaded STEPs here
└── stl/             ← exported STLs for the printed parts land here
```

## 5. Parametric strategy

### 5.1 Rules (what makes it "parametrically updatable")

1. **One source of truth per dimension**: every dimension is a named
   `UserParameter` or an equation referencing named parameters. Zero
   hard-coded numbers in sketches/features.
2. **Parameter naming**: `GROUP_name` (e.g. `motor_shaft_od`,
   `bar_d`, `disc_od`), units attached to each parameter (mm, deg, rad,
   kg, `N*m/rad`, `kg*m^2`).
3. **Equations live in the parameters**: derived values (e.g.
   `bar_L_active = G_STEEL * bar_J / ks_target`) are parameters too, so
   changing `ks_target` re-sizes the bar.
4. **Materials assigned per body** (PLA+, 6061, 1144 drill rod, 52100,
   steel) so **physical properties** (mass, inertia) are real and
   checkable against the BOM.
5. **Variant handling**: measured-dimension parameters (motor shaft OD,
   motor PCD, phase R — R is electrical, not CAD) have a documented
   default + a named alternative. Switching to a clone motor = set
   `motor_shaft_od` 15.0 → 8.0. Option B SEA = swap the spring
   subassembly (kept as a separate file, never deleted).

### 5.2 Parameter dictionary (defaults from `hardware/parts/*`)

| Group | Parameter | Default | Unit | Notes / source |
|---|---|---|---|---|
| MOTOR | `motor_od` | 59.5 | mm | iFlight sheet |
| MOTOR | `motor_h` | 31.2 | mm | iFlight sheet |
| MOTOR | `motor_shaft_od` | 15.0 | mm | genuine hollow; clone 6/8 — **measure** |
| MOTOR | `motor_shaft_id` | 12.6 | mm | GM5208-12 = 12.0 |
| MOTOR | `motor_mass` | 204 | g | physical-props check |
| MOTOR | `motor_mount_pcd` | **measure** | mm | not published; calipers at build |
| MOTOR | `motor_mount_hole_d` | **measure** | mm | |
| SEA | `bar_d` | 2.5 | mm | spring wire |
| SEA | `bar_L_active` | 304.1 | mm | = G·J/ks (2.5 mm bar, k=1.000) |
| SEA | `bar_L_total` | = `bar_L_active` + 2·`hub_bar_embed` | mm | includes hub embedment |
| SEA | `ks_target` | 1.0 | N*m/rad | design target |
| SEA | `tau_max` | 0.35 | N*m | envelope |
| SEA | `defl_max` | 0.350 | rad | 20.1° |
| SEA | `bar_pocket_d` | 2.5 + 0.05 | mm | hub pockets |
| SEA | `dowel_d` | 2.5 | mm | positive drive, both hubs |
| LOAD | `load_shaft_d` | 8 | mm | 608ZZ bore |
| LOAD | `load_shaft_L` | 300 | mm | rod length |
| LOAD | `disc_od` | 196 | mm | R≈98 → J = 0.5·m·R² |
| LOAD | `disc_mass_target` | 250 | g | incl. ~180–200 g washers |
| LOAD | `disc_thk` | param-driven | mm | solved so disc + washers ≈ target |
| LOAD | `washer_d` | 12.5 | mm | M12 / 1.2″ fender |
| LOAD | `washer_bc_r` | 68.44 | mm | **radius of gyration — DECISION Aug 26:** washers at the disc's radius of gyration make J = 0.5·m·R² = 1.2005e-3 independent of the disc/washer mass split. Nominal R/√2 = 69.3 mm; **68.44 mm is the exact value** accounting for the washer's own Ø28 spread (built: mass 250.0 g, J = 1.200500e-3). The plan's original r=80 gives J ≈ 1.5e-3 (point mass at r=80 contributes 0.0064 kg·m²/kg > the disc's 0.004802) — impossible with any washer mass there. |
| LOAD | `washer_count` | 28 | pc | 25–30 pc ≈ 200 g |
| LOAD | `washer_mass` | 7 | g | |
| LOAD | `Jl_target` | 1.2005e-3 | kg*m^2 | MPC model value — verify in Fusion |
| BEARING | `b608_d` / `b608_od` / `b608_w` | 8 / 22 / 7 | mm | 608ZZ |
| BEARING | `block_bore` | 22 + 0.05 | mm | bearing seat |
| BASE | `rail_L` | 610 | mm | 2× 2 ft McMaster 5537T101 (or 400–500 mm Amazon 2020) — set to whatever is ordered |
| BASE | `rail_xs` | 20 | mm | 2020 profile |
| BASE | `tslot_w` | 6 | mm | European 2020 slot |
| BASE | `tnut_m` | M5 | — | |
| BASE | `shaft_center_h` | layout param | mm | bearing block height → align axis |
| PRINT | `hub_bore_clr` | 0.1 | mm | hub clearance |
| PRINT | `hub_od` / `hub_thk` | design | mm | printed hub envelope |
| PRINT | `grub_d` | M3 | mm | set screws, blue thread-locker |
| ENC | `magnet_d` / `magnet_h` | 6 / 3 | mm | diametric N45 |
| ENC | `enc_air_gap` | 1.5 | mm | module ↔ magnet |
| ENC | `plug_od` | = `motor_shaft_id` − 0.05 | mm | magnet plug in hollow bore |
| CAL | `hanger_r` | 100 | mm | known torque radius |
| CAL | `hanger_max_m` | 1.5 | kg | 1.5 kg → τ = m·g·r |
| ASM | `theta_m` / `theta_l` | 0 | deg | demo: show spring deflection |

### 5.3 The update loop (how any change gets made, forever)

1. You ask for a change (e.g. "shaft measured 8.0 solid" or "switch to the −12").
2. I edit the `UserParameter` in the part document (or re-run the part's
   regeneration script with new values).
3. Save the part → Fusion marks the assembly's child reference out of date.
4. I refresh/update the reference in the assembly (reopen / update link).
5. Screenshot + physical-property check to confirm, and re-export STLs if
   the printed parts changed.

## 6. Assembly & joints

Top-level `SEA_Torsion_MPC_Assembly.f3d` = linked X-Refs of the three
subassemblies + imported parts. Two rotational DOF (that's the physics:
`τ = ks·(θm − θl)`).

```
G_base   = rails, T-nuts, motor mount plate, bearing blocks        (grounded)
G_stator = motor body → mount plate → base                          (rigid)
G_rotor  = motor rotor/shaft + Motor_Hub + plug + torsion bar       (spins)
G_load   = Load_Hub + Load_Disc + washers + load shaft + magnet     (spins)
J1  revolute   rotor ↔ stator                (θm — the motor DOF)
J2  revolute   load shaft ↔ bearing blocks   (θl — the load DOF)
rigid groups + as-built joints for everything else (bar→hubs via dowels, etc.)
```

- `theta_m` / `theta_l` user parameters at assembly level let us *render*
  a deflected pose (spring twist) for screenshots and the paper.
- Encoder modules rigid to the frame; magnets rigid to their shafts;
  `enc_air_gap` guarantees the 1–2 mm clearance.

## 7. Phased execution plan (each phase = MCP script run + verification)

| Phase | What | Verification | Est. |
|---|---|---|---|
| **P0 Setup** | Pick project (default `Default Project`); create `Torsion MPC/` + 5 subfolders via `DataFolder`; create `hardware/cad/` locally | `fusion_mcp_read` lists folders; `ls hardware/cad/` | 10 min |
| **P1 Parametric parts** | One script per printed part: new design → UserParameters (§5.2) → parameter-driven sketch/extrude/holes → material → save to `01_Parts` | screenshot per part; physical props: disc 250 g / J 1.2e-3, hub bores = params | 1–2 h |
| **P2 Imports** | You drop STEPs in `hardware/cad/step/`; script imports each (`ImportManager.importToNewDocument`) → save to `02_Imports`. Any part without a STEP gets the parametric fallback | screenshot per import; document search finds each file | 30–60 min |
| **P3 Subassemblies** | `Motor_Side`, `Load_Side`, `Base` — insert part X-Refs, joint internally, save to `03_Subassemblies` | screenshots; occurrence transforms correct | 1 h |
| **P4 Top assembly** | Master assembly: insert subassemblies, J1/J2 revolute joints + rigid groups, ground base, deflection demo params | full-rig screenshots (iso + front); total mass vs BOM; clearance spot-checks | 1 h |
| **P5 Parametric proof** | Change `motor_shaft_od` 15.0 → 8.0 (clone variant), save, update assembly references, screenshot before/after | before/after screenshots show hub + plug regenerate; assembly updates | 30 min |
| **P6 Outputs** | Export STLs of printed parts → `hardware/cad/stl/`; export assembly STEP → `05_Outputs`; generate BOM snapshot (approx, from occurrence list) and diff vs `hardware/BOM.md` | STL files exist; BOM diff reviewed | 30 min |

**Interference check** (no API for it): you run Fusion's *Inspect →
Interference* on the final assembly once, per this checklist, and report
hits; I fix the offending parameter. Same for the final rendered
screenshots you may want for `README.md`.

## 8. What I need from you (accuracy & execution enablers)

1. **Keep Fusion 360 open** with the Fusion MCP add-in running (it is —
   verified). Don't interact with Fusion while a script runs; accept the
   add-in's first-run script prompt.
2. **Project resolved** — you created a **"Torsion MPC" project** (id
   `202608261131116876`) with the three imports already in it. I'll build
   the `01_Parts … 05_Outputs` subfolders inside it and leave the existing
   docs where they are (optionally move them into `02_Imports` later).
3. **Drop the STEPs** in `hardware/cad/step/` (the single biggest
   accuracy lever — real geometry beats my re-creation):
   - Motor: **the BMG5208 GrabCAD STEP you found** — accepted, see §3b
   - Ø8 rod: **your manually-made STEP** — accepted, see §3b
   - 608ZZ ×2: McMaster → bearings → 608 (STEP on the product page)
   - 2020 extrusion: ⚠ see the rail note in §3b — either McMaster
     5537T101 **with McMaster's own matching T-nuts** (and tell me which
     you bought), or the Amazon European-2020 set from the BOM
   - M3/M3-grub/M5-T-nut/dowel/M12-fender-washer: McMaster per item (skip
     if you order the Amazon European 2020 set — its T-nuts cover the base)
   - AS5048A breakout: any STEP/GrabCAD model
   - B-G431B-ESC1: ST's page if a STEP exists (else simplified board)
   - Naming convention: `mfr_part_thing.step` (e.g. `mcm_608zz.step`, `bmg5208.step`)
4. **Caliper measurements** when parts arrive (feed back as parameter
   edits): motor shaft OD/ID, motor mounting PCD + hole size, T-nut ↔
   slot fit, bar diameter (2.5 vs 2.4), disc mass on the luggage scale.
5. **Expect cloud-save latency**: hub saves take seconds; I verify every
   save via document search before proceeding.

## 9. Other MCPs / tools — do you need more?

**No additional MCP is required.** The Fusion MCP already covers modeling,
assembly, imports, parameters, screenshots, and undo — and I can look up
any Fusion API signature live. More MCPs would not improve accuracy; the
real accuracy levers are the items in §8 (STEPs + measurements).

Optional considerations, in order of value:

- **Fusion Electronics MCP** (already in your config) — only useful if we
  want the ESC1 / AS5048A boards as real PCB designs (schematic/board
  + 3D package). Nice for realism in renders, zero structural value.
  Recommend: skip, model boards as simplified bodies.
- **A browser-automation MCP** (e.g. Playwright) — could auto-download
  GrabCAD/McMaster STEPs, but both are auth/click-through gated and
  flaky; you grabbing 8 files by hand is faster and more reliable.
- **Filesystem MCP** — redundant; I already have terminal access to
  `hardware/cad/`.
- Nothing else touches Fusion. (Web search, docs, etc. are built in.)

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| MCP script runs synchronously; a buggy script could spam operations | One logical operation per script; `fusion_mcp_update` undo; screenshot after each run |
| Hub save latency / missing save | Verify with document search after every save |
| GrabCAD model is a mesh (STL) not STEP | Prefer STEP; if only STL, import as mesh — acceptable for a reference part |
| External X-Ref insert API nuance | `addExistingComponent` / `addByInsert` verified present; fallback = `addNewExternalComponent` + save, or insert-then-replace |
| Motor mounting PCD unpublished | Measured parameter, flagged; placeholder until calipers |
| Load disc mass/inertia off target | `disc_thk`/`disc_od` are parameters; verified against J_l in Fusion physical props, iterate until 1.2e-3 |
| T-nut ↔ slot mismatch | Use the imported real 2020 profile; check slot width param |
| Interference only detectable in UI | You run Fusion *Interference* once (checklist in P6); I fix by parameter |
| Fusion closed / logged out mid-build | P0 verifies connection first; scripts check `app.isOffline` and fail loudly |

## 11. Definition of done

- [ ] `Torsion MPC/` exists with all 5 subfolders; every file referenced by
      the master assembly lives inside it
- [ ] All custom parts parametric (dictionary in §5.2); zero magic numbers
- [ ] Real STEPs imported for every part that has one online; simplified
      stand-ins clearly named `*_Simplified`
- [ ] Master assembly complete: 2 revolute DOF, rigid groups, grounded
      base, deflection demo works
- [ ] Physical properties match BOM targets (motor 204 g, disc ~250 g,
      J_l ≈ 1.2e-3 kg·m²)
- [ ] Parametric proof (P5) recorded: a parameter edit regenerates parts
      and updates the assembly
- [ ] STLs for printed parts exported to `hardware/cad/stl/`; BOM diff
      reviewed
- [ ] You ran *Interference* once and we fixed whatever it found

## 12. Appendix — P1 API findings (learned the hard way, verified live)

Recorded after building Motor_Hub + Motor_Encoder_Plug. Follow these recipes;
anything not listed here should be probed with a throwaway script first.

**Extrude cuts (the big one).** In this MCP environment:

- `setAllExtent` on a cut extrude removes only a ~0.5 cm slug — it does NOT
  behave as through-all. Do not rely on it.
- **XZ/YZ-plane cut extrudes are broken**: the cut depth caps at ~0.55 cm
  per side regardless of requested distance. XY-plane cut extrudes work
  perfectly, even with circles offset from the origin.
- **Boolean `combine` cuts on the X/Y axes remove only ONE half-length from
  the cutter's center** (effective cut = `[center − body_half, center]`).
  Z-direction combines are exact.
- Working recipe for radial holes (dowel/grub): build the cutter as a
  cylinder on the XY plane (working extrude), `move`-rotate it to the target
  axis, then boolean-cut with **two cutters per hole** — one centered on the
  body axis, one at the +edge — so their one-half cuts tile the full extent.
  Verify by dumping cylindrical faces; the hole is correct when you see two
  wall segments (dowel) or one wall reaching the bore (grub).

**Holes feature.** `HoleFeatures` positions come from UI selection
(`setPositionBySketchPoint` exists but the input requires a selected point),
so holes are not script-friendly here. Use sketch circles + cut extrudes /
boolean cutters instead.

**Sketches.**

- Sketching on a bounded face creates MULTIPLE profiles (e.g. the inner disc
  AND the annulus). `profile.item(0)` is often the annulus — selecting it
  cuts away the whole ring and leaves a stray column. Pick the profile by
  `profile.area` (min-area = inner), or verify after the cut.
- `SketchCircles.addByCenterRadius` takes a plain `float`, not a `ValueInput`.
  To keep radii parametric: draw the circle, then set the dimension's
  `parameter.expression` (via `sketchDimensions`) to the user-parameter name.
- Position dimensions require the 4th `orientation` argument
  (`HorizontalDimensionOrientation`/`VerticalDimensionOrientation`).

**Environment quirks.**

- `design.userParameters.defaultLengthUnits` is read-only; every expression
  must carry explicit units (e.g. `"15 mm"`, `"2.5 deg"`).
- The root component name is fixed and cannot be renamed via script.
- `feature.name` raises `RuntimeError` (not `AttributeError`) for some
  features — use `try/except RuntimeError` when walking the timeline.
- `saveAs` requires the `description` argument.
- After any script run, verify via document search before moving on; an
  unsaved failed run leaves an orphan doc — close it without saving.

**Verification trick.** Face/edge class names differ from docs
(e.g. `Cylinder`, not `CylinderSurface`). To check a hole exists, iterate
`body.faces` and match geometry type + axis/radius instead of filtering by
edge class. Use the face's `boundingBox` to read the actual hole extent
(the cylinder's reported `origin` is the tool cutter's base, not the hole
position).

### 12b. P2 findings (Load_Hub, Bearing_Block, Motor_Mount_Plate — Aug 26)

All three built, verified, saved to `01_Parts`, material = **ABS Plastic**
(no PLA in the library; 1.06 g/cm³ is close enough for mass checks).

**Cut-extrude rules (probe-verified on a throwaway box):**

- A cut profile must lie **inside the body footprint** on the sketch plane;
  a profile whose center is outside the body fails with "No target body
  found to cut or intersect!". (This is what bit the first bearing-block
  attempt: the T-nut bolt holes were placed at x=±15 mm, outside the
  8 mm-thick block.)
- A cut's depth must **end at or inside the body** — depth exactly equal to
the body extent works; depth beyond the body fails. "Through" = depth
exactly `body_height`, never `body_height + margin`.
- Profiles whose edges sit **exactly flush with the body's side faces**
can fail; inset them ~0.15 mm.

**Bearing-block design correction (important):** the bearing seat fixes the
block at 8 mm thick along the shaft, but the two M5 T-nut bolts need ~30 mm
spacing *along the rail* — which is the same axis. The working design is a
**base + tower**: a 40×40×8 mm base plate (X = rail direction) carries the
T-nut bolts and locating groove; an 8 mm tower on top holds the 608ZZ seat
at `shaft_center_h`. Both are +Z extrusions from the XY plane joined with
`JoinFeatureOperation` (proven working; the L-shaped motor mount uses the
same trick — foot and plate are both +Z extrusions, plate joined on).

**Radial (X/Y-axis) holes** — the two-cutter boolean recipe from P1 is now
proven on three parts (hub dowel/grub, seat Ø22.05, plate Ø20 + 4×Ø3.4 PCD):
cutters at `x=0` and `x=+body_half` tile the full thickness. The grub hole
came out **full-through (double wall)** rather than the motor hub's
single-wall — functionally fine (an M3×8+ screw clamps the shaft either
way); expect either variant and verify with the face-bbox dump.

**Motor_Mount_Plate** uses `motor_mount_pcd = 36 mm` as a **placeholder**
(4 holes at 45°, Ø3.4 clearance) — the plan's flagged caliper measurement
when the motor arrives. One parameter edit propagates.

**`Motor_Encoder_Plug`-style load-side magnet holder is still missing**
(load-shaft end, beyond the last bearing) — noted for the subassembly phase.

### 12c. P2b findings (Load_Disc — Aug 26)

Built + verified: **Ø196 × 1.80 mm disc** (ABS, 56.2 g) + **28× M12 fender
washers** (Ø28/Ø12.5×1.8, **steel** — 6.9 g each, matches the BOM's ~7 g) at
**r = 68.44 mm** → total **250.0 g**, analytic **J = 1.200500e-3 kg·m²**
(target hit to 7 sig figs). The washer bolt circle + 28 bolt holes are
circular patterns (features and bodies — both work with **literal**
quantity values). Note the printed disc is thin (1.8 mm) by design — the
steel washers carry ~78 % of the mass; the bolts/washers stiffen the disc.
The 0.5 mm-radius fine-tune (69.3 → 68.44) accounts for the washers' own
Ø28 spread: `r² = (J_t − ½·m_d·R² − m_w·(R_o²+R_i²)/2)/m_w`.

New environment lessons:

- **Parameter units bite silently**: `add(name, '28', 'mm')` makes a
  *length* parameter — its value becomes 2.8 cm → circular patterns of
  "28" silently created 2–3 instances. Counts must be **unitless** (`''`).
  The `unit` property is read-only post-hoc; delete + re-add to fix.
- `getXYZMomentsOfInertia()` returns a list
  `[success, xx, yy, zz, xy, yz, xz]` (zz = index 3, kg·cm²), but its values
  were **unreliable in this environment** (never matched hand-math, by
  varying factors 1.7–12× across states). `mass` and `volume` always match
  hand calcs — verify inertia analytically from the masses
  (`J = 0.5·m_d·R² + Σ m_w·(r² + (R_o²+R_i²)/2)`), and have the user spot-
  check Fusion's own *Inspect → Physical Properties* dialog once.
- Mass-target iteration is one exact pass: `t_new = t·(target−m_w)/m_d`
  (all in kg / cm) — thickness is linear in mass.
