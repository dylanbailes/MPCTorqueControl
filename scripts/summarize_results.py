"""Generate public metric tables from the curated results snapshot."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summaries(result):
    controllers = ("PID", "MPC", "MPC+learned")
    rows = ["| Metric [mN·m] | PID | MPC | MPC + learned FF |",
            "|---|---:|---:|---:|"]
    for label, section, metric in (
        ("Smooth tracking RMS, latter half", result["tracking"]["smooth"], "rms_error_mNm"),
        ("Smooth tracking RMS, full run", result["tracking"]["smooth"], "rms_error_overall_mNm"),
        ("Edge-rich tracking RMS, full run", result["tracking"]["edges"], "rms_error_overall_mNm"),
        ("Disturbance mean absolute error, steady window", result["disturbance"], "steady_error_mNm"),
    ):
        rows.append("| " + label + " | " + " | ".join(
            f"{section[c][metric]:.2f}" for c in controllers) + " |")
    table = "\n".join(rows)
    p = result["provenance"]
    plant, cfg = p["plant_parameters"], p["mpc_config"]
    collision = result["collision"]
    latency = collision["detection_latency_ms"]
    detection = f"{latency:.1f} ms" if latency is not None else "not detected"
    id_rows = "\n".join(f"| `{name}` | {100 * value:.2f}% |"
                         for name, value in result["identified"]["rel_errors"].items())
    doc = f'''# Results: selected 4015 simulation scenario

This page is generated from [the raw snapshot](../results/results.json) by
`python scripts/summarize_results.py`. All measurements are from simulation.
The plotted data, generated headers, and this table come from the same run.

## Configuration and metric definitions

- Motor scenario: R = {plant['R']:g} Ω, L = {plant['L']:g} H,
  Kt = {plant['Kt']:g} N·m/A, Jm = {plant['Jm']:g} kg·m².
- MPC: N = {cfg['N']}, T = {cfg['T'] * 1000:g} ms,
  current budget = ±{cfg['u_max']:g} A, at most {cfg['max_iter']} ADMM iterations.
- PID uses fixed gains, the same sample period, and the same final current
  budget. This is a comparison of these configurations, not optimal tuning
  of each controller across all possible operating conditions.
- RK4 integration step = {p['integration_dt_s']:g} s. The torque fixture
  uses stiffness {p['fixture']['k_block']:g} N·m/rad and damping
  {p['fixture']['d_block']:g} N·m·s/rad, included in the MPC prediction model.
- Tracking runs last {p['durations_s']['eval']:g} s. The steady tracking
  metric uses the latter half; overall RMS includes startup and edges.
  Smooth reference has a 0.15 N·m bias with four sine components; the edge
  reference adds a ±0.05 N·m square component.
- Disturbance: +0.15 N·m on the **motor** at t = 1.5 s, while holding a
  0.25 N·m torque reference. Peak error uses [1.5, 1.7) s; steady error is
  **mean absolute error**, not signed bias, over [1.9, 2.2) s.
- Angles include quantization and seeded sensor noise. Velocities and
  current feedback use simulator states. There is no process/thermal drift.

## Controller comparison

{table}

![Smooth torque tracking](../results/plots/tracking_smooth.png)
![Edge-rich torque tracking](../results/plots/tracking_edges.png)
![Motor-side disturbance rejection](../results/plots/disturbance_rejection.png)

## Identification and learning

| Identified quantity | Relative error against simulated truth |
|---|---:|
{id_rows}

Time-domain inertia fitting is cross-checked against the resonance estimate
and fused with a frequency-domain prior. MPC uses the identified motor
inertia; other prediction parameters remain the configured values, with
spring calibration used by the torque observer. This is not a fully
identified, independent hardware model.

Held-out residual-model R² = {result['learned_disturbance']['heldout_r2']:.4f}.
Training and evaluation use different trajectories. A high score can include
inertia mismatch and current-loop dynamics; it does not prove a physically
accurate friction map. The separately fitted friction model still needs
validation against hardware data.

![System identification](../results/plots/system_id.png)
![Held-out residual fit](../results/plots/learned_disturbance.png)

## Collision-response demonstration

A simulated grip pins the output at t = {collision['grab_time_s']:g} s.
Detection latency: **{detection}**. Maximum absolute estimated torque from
grip onset through the end of the run:
**{collision['post_collision_peak_torque_mNm']:.2f} mN·m**.
This metric includes the interval before detection, not just the zero-current
response afterward. The collision demo uses a PID inner torque controller,
impedance reference, learned FF, and stall/residual detection; it is separate
from the blocked-output MPC benchmarks.

![Collision-response simulation](../results/plots/collision_demo.png)

## Interpretation and limitations

Plain MPC provides the main tracking improvement in this fixture. Learned
feedforward must be judged by closed-loop metrics rather than R² alone;
it shares the current budget and can displace useful control at saturation.
Small differences in a deterministic run do not establish statistical
significance. Retuning PID and testing more fixtures may change the comparison.

Physical actuator performance, STM32 execution timing, sensor/driver faults,
and human interaction remain unverified. The safety mechanism is a modeled
zero-current latch, not a safety certification. MATLAB results have not been
rerun and are not included in this table. See [status and next steps](STATUS.md).
Historical scenarios are retained in [the archive](../results/archive/README.md)
and should not be combined with the current snapshot.
'''
    return table, doc


def main(check=False):
    result = json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))
    table, doc = summaries(result)
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    start, end = "<!-- RESULTS_TABLE_START -->", "<!-- RESULTS_TABLE_END -->"
    before, rest = readme.split(start, 1)
    _, after = rest.split(end, 1)
    updated = before + start + "\n" + table + "\n" + end + after
    outputs = {readme_path: updated, ROOT / "docs/RESULTS.md": doc}
    for path, contents in outputs.items():
        if check:
            if path.read_text(encoding="utf-8") != contents:
                raise SystemExit(f"Stale result summary: {path.relative_to(ROOT)}")
        else:
            path.write_text(contents, encoding="utf-8", newline="\n")
    print("Result summaries match snapshot" if check else "Result summaries updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    main(check=parser.parse_args().check)
