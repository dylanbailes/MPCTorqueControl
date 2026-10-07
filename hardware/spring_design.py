"""Series-elastic element design for the SEA torque-control rig.

Targets (from the digital twin / MPC design in model/ and results/):
    ks         = 1.0 N.m/rad   (linear stiffness used by the MPC model)
    tau_max    = 0.35 N.m      (peak torque reference + collision peak)
    defl_max   = 0.35 rad      (max spring deflection at tau_max)

Two build options are sized and stress-checked:

  A. Torsion bar (drill rod / music wire, 2 ground dowel pins) — machinable,
     no custom parts, extremely linear, no hysteresis.  Primary choice.
  B. Extension-spring rotary SEA (2 off-the-shelf springs at radius r) —
     the classic DLR-style design, fully 3D-printable, no metalworking.

Run:  python hardware/spring_design.py
"""

from math import pi, sqrt

# ---- material properties ---------------------------------------------------
E_STEEL = 196.5e9   # Young's modulus, spring steel      [Pa]
G_STEEL = 79.3e9    # shear modulus, steel               [Pa]
S_Y_MUSIC = 1.6e9   # yield, music wire (ASTM A228)      [Pa]
S_Y_DRIL = 0.62e9   # yield, 1144 drill rod (as-is)      [Pa] (conservative)

# ---- design targets --------------------------------------------------------
ks = 1.0            # target stiffness                   [N.m/rad]
tau_max = 0.35      # max spring torque                  [N.m]
defl_max = tau_max / ks

print("=" * 68)
print("SEA spring design — targets")
print("=" * 68)
print(f"  ks        = {ks:.2f} N.m/rad")
print(f"  tau_max   = {tau_max:.2f} N.m")
print(f"  defl_max  = {defl_max:.3f} rad = {defl_max*180/pi:.1f} deg")

# ---------------------------------------------------------------------------
# Option A: torsion bar (round rod, both ends pinned to motor and load hubs)
#   k = G * J / L,   J = pi*d^4/32,   tau_max = T*c/J = 16*T/(pi*d^3)
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("Option A — torsion bar")
print("-" * 68)
results_a = []
for d_mm in (2.0, 2.5, 3.0):
    d = d_mm * 1e-3
    J = pi * d**4 / 32.0
    # solve L = G*J / ks
    L = G_STEEL * J / ks
    tau_shear = 16.0 * tau_max / (pi * d**3)
    sf = S_Y_DRIL / tau_shear
    # deflection-induced stress is the same formula; check angular deflection
    results_a.append((d_mm, L, tau_shear, sf))
    print(f"  d = {d_mm:.1f} mm  ->  L = {L*1e3:6.1f} mm   "
          f"shear {tau_shear/1e6:7.1f} MPa  (yield {S_Y_DRIL/1e6:.0f} MPa, "
          f"SF {sf:.0f}x)")

d_mm, L, _, _ = results_a[1]   # pick the 2.5 mm bar
d = d_mm * 1e-3
J = pi * d**4 / 32.0
k_check = G_STEEL * J / L
print(f"\n  Recommended: 2.5 mm drill rod, {L*1e3:.0f} mm long "
      f"(k = {k_check:.3f} N.m/rad, within {(k_check-ks)/ks*100:+.1f}% of target)")
print("  Tune by grinding length: dL = -dL * (dk/k) — or use 2.0 mm for a softer rig.")

# ---------------------------------------------------------------------------
# Option B: extension-spring rotary SEA
#   two identical springs, anchors at radius r from the pivot;
#   linearized rotary stiffness  K = 2 * k_lin * r^2
#   spring force at tau_max:  F = tau_max / (2 r)
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("Option B — extension-spring rotary SEA (DLR-style)")
print("-" * 68)
for r_mm in (30.0, 40.0, 50.0):
    r = r_mm * 1e-3
    k_lin = ks / (2.0 * r**2)
    F_max = tau_max / (2.0 * r)
    stretch = F_max / k_lin
    print(f"  r = {r_mm:2.0f} mm -> need k_lin = {k_lin:6.1f} N/m per spring, "
          f"F_max = {F_max:5.1f} N ({F_max/9.81:.2f} kg), "
          f"stretch at tau_max = {stretch*1e3:5.1f} mm")

r = 0.04
k_lin = ks / (2.0 * r**2)
print(f"\n  Recommended: r = 40 mm with 2x extension springs ~{k_lin:.0f} N/m "
      f"(e.g. 0.8 mm wire, ~25 mm free length), preloaded to ~10 N")
print("  Exact geometry: K = 2*k_lin*r^2*cos^2 — mounting-angle effects are")
print("  handled by the calibration step (learn/system_id.py), not the model.")

# ---------------------------------------------------------------------------
# Load inertia sizing (Jl = 1.2e-3 kg.m^2, the MPC model value)
#   flat disc: J = 0.5*m*R^2
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("Load inertia (Jl = 1.2e-3 kg.m^2)")
print("-" * 68)
for m, R_mm in ((0.25, 98.0), (0.30, 89.0), (0.20, 110.0)):
    J = 0.5 * m * (R_mm * 1e-3) ** 2
    print(f"  m = {m:.2f} kg, R = {R_mm:.0f} mm -> J = {J:.4e} kg.m^2")

# ---------------------------------------------------------------------------
# Variable load inertia — washer-count tuning. The disc was built for this:
# 28 bolt holes at the radius-of-gyration circle r = 68.44 mm, so J changes
# LINEARLY with washer count and every washer adds the same dJ.
#   Jl(n) = J_base + n * dJ_w,   dJ_w = m_w * (r^2 + (Ro^2 + Ri^2)/2)
# Weigh your actual disc and washers, update the constants, re-run.
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("Variable load inertia — washer-count table (Jl = J_base + n*dJ_w)")
print("-" * 68)

m_disc = 0.0562   # printed Ø196 × 1.8 mm disc alone [kg] — verify on scale
R_disc = 0.098    # disc outer radius [m]
m_w = 0.0069      # one M12 fender washer [kg] — verify on scale
r_w = 0.06844     # washer bolt-circle radius [m] (radius of gyration)
Ro_w, Ri_w = 0.014, 0.00625   # washer outer/inner radius [m]
Jm_motor = 3.0e-5 # motor inertia (hybrid 4015 build) [kg.m^2]

J_base = 0.5 * m_disc * R_disc**2 + 1.0e-5    # + hub/bolts/plug allowance
dJ_w = m_w * (r_w**2 + (Ro_w**2 + Ri_w**2) / 2.0)

print(f"  J_base (disc+hub, 0 washers) = {J_base:.3e} kg.m^2")
print(f"  dJ_w per washer at r={r_w*1e3:.1f} mm  = {dJ_w:.3e} kg.m^2")
print()
print("  target Jl   washers  stacking       Jl achieved   f_res  f_antires")
for Jt in (J_base, 6.0e-4, 9.0e-4, 1.2e-3, 1.8e-3, 2.4e-3):
    n = max(0, round((Jt - J_base) / dJ_w))
    J = J_base + n * dJ_w
    if n <= 28:
        stack = f"{n} x1"
    elif n <= 56:
        stack = f"{n - 28} x2 + {56 - n} x1"
    else:
        stack = f"{n - 56} x3 + {84 - n} x2"
    f_res = sqrt(ks * (1.0 / Jm_motor + 1.0 / J)) / (2.0 * pi)
    f_anti = sqrt(ks / J) / (2.0 * pi)
    print(f"  {Jt:8.1e}   {n:5d}   {stack:12s}   {J:.3e}   {f_res:5.1f}  {f_anti:6.2f}")

print()
print("  Encoders: MT6701 ABZ on the motor + AS5048A SPI on the load — the")
print("  deflection is measured differentially, so ks is calibrated from the")
print("  *torque* reference, never from datasheet stiffness.")
