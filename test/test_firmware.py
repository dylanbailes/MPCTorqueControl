"""Host C checks; board/HAL integration is deliberately outside this test."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess

import numpy as np
import pytest

from learn.residual import LearnedDisturbance, ResidualConfig
from model.plant import PlantParams
from sim.bench import make_mpc


ROOT = Path(__file__).resolve().parents[1]


def compiler():
    configured = os.environ.get("CC")
    if configured:
        return shlex.split(configured)
    for name in ("cc", "gcc", "clang"):
        if shutil.which(name):
            return [name]
    pytest.skip("Host C compiler unavailable; set CC or install GCC/Clang")


def build(cc, inc, sources, target):
    subprocess.run([*cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-I", str(inc), *map(str, sources), "-o", str(target), "-lm"],
                   check=True, capture_output=True, text=True)


def test_foc_velocity_feedforward_and_encoder_register_width(tmp_path):
    source = tmp_path / "io_math.c"
    source.write_text('''#include <math.h>
#include "foc.h"
#include "encoder.h"
static uint16_t address;
static uint16_t read_angle(uint16_t reg) { address = reg; return 8192; }
int main(void) {
    FocCtl f;
    foc_init(&f, 1.5f, 0.0003f, 0.1f, 13.86f, 10000.0f);
    f.pole_pairs = 2;
    f.electrical_offset = 0.3f;
    float vq = foc_current_loop(&f, 0.0f, 0.0f, 0.4f, 2.0f, 0.0001f);
    if (fabsf(vq - 0.2f) > 1e-6f) return 1;
    if (fabsf(f.theta_e - 1.1f) > 1e-6f) return 2;
    Encoder e;
    encoder_init(&e, read_angle);
    encoder_update(&e, 0.0005f);
    if (address != 0x3fff) return 3;
    if (fabsf(e.angle - 3.14159265f) > 1e-6f) return 4;
    return 0;
}
''', encoding="utf-8")
    core = ROOT / "firmware/Core/Src"
    target = tmp_path / ("io_math.exe" if os.name == "nt" else "io_math")
    build(compiler(), ROOT / "firmware/Core/Inc",
          [source, core / "foc.c", core / "encoder.c"], target)
    subprocess.run([str(target)], check=True)


@pytest.mark.parametrize("generated", [False, True])
def test_c_mpc_matches_python_and_portable_modules_compile(tmp_path, generated):
    cc = compiler()
    inc = tmp_path / "inc"
    shutil.copytree(ROOT / "firmware/Core/Inc", inc)
    if generated:
        ctrl = make_mpc(PlantParams(), k_block=1e4, d_block=50.0)
        ctrl.export_to_c(inc / "mpc_model.h")
        learned = LearnedDisturbance(ResidualConfig())
        learned.n_features = 13
        learned.beta = np.arange(13) * 0.001
        learned.friction_beta = np.array([0.0, 0.008, 0.0002])
        learned.export_to_c(inc / "learned_model.h")
    else:
        # Stored export: compare its MPC against the same identified plant.
        import json
        from model.mpc import MPCConfig
        snapshot = json.loads((ROOT / "results/results.json").read_text())
        provenance = snapshot["provenance"]
        params = PlantParams(**provenance["plant_parameters"])
        ctrl = make_mpc(params, MPCConfig(**provenance["mpc_config"]),
                        jm=snapshot["identified_model_impact"]["model_Jm"],
                        **provenance["fixture"])
    source = tmp_path / "host.c"
    source.write_text('''#include <stdio.h>
#include "mpc.h"
int main(void) {
    MpcConfig cfg = { .max_iter = MPC_MAX_ITER };
    mpc_init(&cfg);
    float x[4], ref;
    while (scanf("%f %f %f %f %f", &x[0], &x[1], &x[2], &x[3], &ref) == 5)
        printf("%.9g\\n", mpc_step(x, ref));
    return 0;
}
''', encoding="utf-8")
    core = ROOT / "firmware/Core/Src"
    sources = [core / f"{name}.c" for name in
               ("mpc", "admm", "foc", "encoder", "impedance", "safety", "sea_observer")]
    target = tmp_path / ("host.exe" if os.name == "nt" else "host")
    build(cc, inc, [source, *sources], target)
    states = np.random.default_rng(9).normal(0, 0.01, (30, 4))
    payload = "\n".join(" ".join(map(str, [*x, 0.1])) for x in states)
    process = subprocess.run([str(target)], input=payload, capture_output=True,
                             text=True, check=True)
    actual = np.array([float(v) for v in process.stdout.split()])
    expected = np.array([ctrl.step(x, 0.1) for x in states])
    np.testing.assert_allclose(actual, expected, atol=0.002, rtol=0.002)
    # Catch mismatched declarations and ISR source regressions without HAL.
    subprocess.run([*cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-I", str(inc), "-c", str(core / "tasks.c"),
                    "-o", str(tmp_path / "tasks.o")],
                   check=True, capture_output=True, text=True)
