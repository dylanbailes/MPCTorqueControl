"""Export website-ready graphics from the published simulation snapshot.

Usage: python scripts/website_visuals.py
Outputs: results/website/*.{png,svg}, in light and dark themes.
"""

from pathlib import Path
import json
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/website"
THEMES = {
    "light": dict(bg="#F7F8FA", panel="#FFFFFF", ink="#182531", muted="#586975",
                  grid="#DDE3E8", pid="#8B96A0", mpc="#2868B2", learned="#138578"),
    "dark": dict(bg="#111B24", panel="#192733", ink="#F1F5F7", muted="#AEC0CD",
                 grid="#324655", pid="#94A2AD", mpc="#76ABE8", learned="#67C8B8"),
}


def canvas(theme, title, subtitle, height=9):
    fig = plt.figure(figsize=(16, height), facecolor=theme["bg"])
    fig.text(0.065, 0.93, "SEA–MPC  /  PROJECT EVIDENCE", color=theme["muted"],
             fontsize=12, weight="bold", va="top")
    fig.text(0.065, 0.86, title, color=theme["ink"], fontsize=30,
             weight="bold", va="top")
    fig.text(0.065, 0.78, subtitle, color=theme["muted"], fontsize=14, va="top")
    return fig


def save(fig, name, theme_name):
    OUT.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        path = OUT / f"{name}-{theme_name}.{extension}"
        options = {"metadata": {"Date": None}} if extension == "svg" else {}
        fig.savefig(path, dpi=160, facecolor=fig.get_facecolor(), **options)
        if extension == "svg":
            contents = path.read_text(encoding="utf-8")
            path.write_text("\n".join(line.rstrip() for line in contents.splitlines()) + "\n",
                            encoding="utf-8", newline="\n")
    plt.close(fig)


def result_comparison(result, theme_name, theme):
    fig = canvas(theme, "Model-based control improves torque tracking",
                 "Selected 4015 motor scenario · blocked-output fixture · simulation results")
    panels = (
        ("Smooth tracking", "RMS error · latter half of 6 s run",
         result["tracking"]["smooth"], "rms_error_mNm"),
        ("Edge-rich tracking", "RMS error · full 6 s run",
         result["tracking"]["edges"], "rms_error_overall_mNm"),
        ("Disturbance rejection", "Mean absolute error · 1.9–2.2 s",
         result["disturbance"], "steady_error_mNm"),
    )
    colors = [theme["pid"], theme["mpc"], theme["learned"]]
    for i, (title, definition, data, key) in enumerate(panels):
        left = 0.075 + i * 0.31
        fig.text(left, 0.655, title, fontsize=18, weight="bold", color=theme["ink"])
        fig.text(left, 0.61, definition, fontsize=11, color=theme["muted"])
        ax = fig.add_axes([left, 0.24, 0.245, 0.305], facecolor=theme["bg"])
        values = [data[c][key] for c in ("PID", "MPC", "MPC+learned")]
        ax.barh([0, 1, 2], values, color=colors, height=0.48, zorder=3)
        ax.set_yticks([0, 1, 2], ["PID", "MPC", "MPC + FF"], color=theme["ink"], fontsize=12)
        ax.invert_yaxis()
        limit = max(values) * 1.24
        ax.set_xlim(0, limit)
        for row, value in enumerate(values):
            ax.text(value + limit * 0.025, row, f"{value:.2f}", va="center",
                    fontsize=13, color=theme["ink"], weight="bold")
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))
        ax.grid(axis="x", color=theme["grid"], zorder=0)
        ax.tick_params(axis="both", colors=theme["muted"], length=0, pad=9)
        ax.set_xlabel("Error [mN·m]  ·  lower is better", color=theme["muted"],
                      fontsize=11, labelpad=14)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.text(0.065, 0.11, "FF = learned feedforward  ·  Matched current budget: ±3 A  ·  2 kHz modeled torque loop  ·  Fixed gains",
             color=theme["ink"], fontsize=12)
    fig.text(0.065, 0.065, "Simulation evidence, not measured hardware performance.  Source: results/results.json",
             color=theme["muted"], fontsize=11)
    save(fig, "controller-comparison", theme_name)


def learned_contribution(result, theme_name, theme):
    fig = canvas(theme, "Where learned feedforward helps",
                 "Error reduction relative to plain MPC · same current budget · simulation results")
    specifications = (
        ("Smooth tracking", "RMS · latter half", result["tracking"]["smooth"], "rms_error_mNm"),
        ("Edge-rich tracking", "RMS · full run", result["tracking"]["edges"], "rms_error_overall_mNm"),
        ("Disturbance rejection", "Mean absolute error · steady window", result["disturbance"], "steady_error_mNm"),
    )
    ax = fig.add_axes([0.40, 0.24, 0.38, 0.40], facecolor=theme["bg"])
    reductions = []
    for row, (label, definition, data, metric) in enumerate(specifications):
        base, augmented = data["MPC"][metric], data["MPC+learned"][metric]
        reductions.append((base - augmented) / base * 100)
        y = 0.24 + 0.40 * (1 - (row + 0.5) / 3)
        fig.text(0.065, y + 0.023, label, color=theme["ink"], fontsize=18, weight="bold")
        fig.text(0.065, y - 0.020, definition, color=theme["muted"], fontsize=12)
        fig.text(0.875, y + 0.012, f"{base:.2f} → {augmented:.2f}", color=theme["ink"],
                 fontsize=14, ha="center", weight="bold")
        fig.text(0.875, y - 0.022, "mN·m", color=theme["muted"], fontsize=11, ha="center")
    ax.barh([0, 1, 2], reductions, height=0.40,
            color=[theme["pid"], theme["learned"], theme["learned"]], zorder=3)
    ax.set_ylim(2.5, -0.5)
    ax.set_xlim(min(0, min(reductions) - 5), max(40, max(reductions) * 1.15))
    ax.set_yticks([])
    ax.set_xticks([0, 10, 20, 30, 40])
    ax.grid(axis="x", color=theme["grid"], zorder=0)
    ax.tick_params(colors=theme["muted"], length=0, pad=8)
    for row, reduction in enumerate(reductions):
        ax.text(max(0, reduction) + 0.7, row, f"{reduction:.1f}%", va="center",
                fontsize=15, color=theme["ink"], weight="bold")
    ax.set_xlabel("Reduction in reported error [%]", color=theme["muted"], fontsize=12, labelpad=14)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(0.065, 0.12, "Plain MPC delivers the main improvement. Feedforward adds a smaller, scenario-dependent gain.",
             color=theme["ink"], fontsize=13)
    fig.text(0.065, 0.065, "One deterministic simulation scenario; differences are not statistical significance claims.",
             color=theme["muted"], fontsize=11)
    save(fig, "learned-feedforward", theme_name)


def project_progress(theme_name, theme):
    fig = canvas(theme, "From actuator mechanics to measured control",
                 "Implemented simulation and host checks · STM32 integration and physical validation remain ahead")
    ax = fig.add_axes([0.065, 0.43, 0.87, 0.28], facecolor=theme["bg"])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 3)
    ax.axis("off")
    for center, label, symbol in ((2, "Motor inertia", "M"), (11, "Load inertia", "L")):
        ax.add_patch(Circle((center, 1.6), 0.58, facecolor=theme["panel"],
                           edgecolor=theme["mpc"], linewidth=2.5))
        ax.text(center, 1.6, symbol, color=theme["ink"], fontsize=22, ha="center", va="center")
        ax.text(center, 0.50, label, color=theme["muted"], fontsize=12, ha="center")
    ax.plot([2.58, 4.4], [1.6, 1.6], color=theme["ink"], lw=2)
    points = np.linspace(4.4, 8.6, 17)
    y = np.array([1.6] + [1.9 if i % 2 else 1.3 for i in range(1, 16)] + [1.6])
    ax.plot(points, y, color=theme["learned"], lw=2.5)
    ax.plot([8.6, 10.42], [1.6, 1.6], color=theme["ink"], lw=2)
    ax.text(6.5, 2.45, "Torsion spring", color=theme["ink"], fontsize=15, ha="center", weight="bold")
    ax.text(6.5, 0.42, "Torque estimated from differential deflection", color=theme["muted"],
            fontsize=12, ha="center")
    ax.annotate("Torque output", xy=(11.7, 1.6), xytext=(14.3, 1.6),
                color=theme["ink"], fontsize=13, ha="center", va="center",
                arrowprops=dict(arrowstyle="<-", color=theme["ink"], lw=1.7))
    stages = (
        ("01", "Simulation", "Implemented", "ID, PID/MPC, residual FF,\ndisturbance and grip tests"),
        ("02", "Portable C", "Host checked", "Modules compile; MPC\ncompared against Python"),
        ("03", "STM32 integration", "In progress", "Board support, sensing,\nalignment and loop timing"),
        ("04", "Physical validation", "Pending", "Calibrated bench results,\nrepeatability and demo"),
    )
    for i, (number, title, status, detail) in enumerate(stages):
        left = 0.065 + i * 0.225
        patch = FancyBboxPatch((left, 0.14), 0.207, 0.255, transform=fig.transFigure,
                               boxstyle="round,pad=0.008,rounding_size=0.012",
                               facecolor=theme["panel"], edgecolor=theme["grid"], linewidth=1)
        fig.add_artist(patch)
        fig.text(left + 0.013, 0.355, number, color=theme["muted"], fontsize=12, weight="bold")
        fig.text(left + 0.013, 0.31, title, color=theme["ink"], fontsize=17, weight="bold")
        fig.text(left + 0.013, 0.266, status, color=theme["learned"] if i < 2 else theme["muted"],
                 fontsize=13, weight="bold")
        fig.text(left + 0.013, 0.21, detail, color=theme["muted"], fontsize=12,
                 linespacing=1.55, va="top")
    fig.text(0.065, 0.07, "Architecture schematic, not a completed hardware assembly.  Status: October 7, 2026",
             color=theme["muted"], fontsize=11)
    save(fig, "project-progress", theme_name)


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none",
                         "svg.hashsalt": "sea-mpc-website"})
    result = json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))
    for name, theme in THEMES.items():
        result_comparison(result, name, theme)
        learned_contribution(result, name, theme)
        project_progress(name, theme)
    assets = sorted([*OUT.glob("*.png"), *OUT.glob("*.svg"), OUT / "README.md"])
    with zipfile.ZipFile(OUT / "sea-mpc-website-visuals.zip", "w",
                         compression=zipfile.ZIP_DEFLATED) as archive:
        for asset in assets:
            archive.write(asset, arcname=asset.name)
    print("Website visuals exported: 3 graphics × 2 themes × PNG/SVG")


if __name__ == "__main__":
    main()
