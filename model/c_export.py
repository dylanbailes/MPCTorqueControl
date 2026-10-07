"""Portable C99 float literals and row-major array initializers."""

import math

import numpy as np


def c_float(value: float) -> str:
    value = float(np.float32(value))
    if not math.isfinite(value):
        raise ValueError("Cannot export a non-finite model coefficient")
    literal = format(value, ".9g")
    if "." not in literal and "e" not in literal.lower():
        literal += ".0"
    return literal + "f"


def c_array(values) -> str:
    flat = np.asarray(values).ravel(order="C")
    rows = [", ".join(c_float(v) for v in flat[i:i + 4])
            for i in range(0, len(flat), 4)]
    return "{\n    " + ",\n    ".join(rows) + "\n}"
