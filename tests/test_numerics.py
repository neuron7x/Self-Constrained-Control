from __future__ import annotations

import numpy as np

from self_constrained_control.neural_interface import _vtrap_py


def test_vtrap_limit_is_y() -> None:
    # limit x->0 of x/(1-exp(-x/y)) is y
    assert abs(_vtrap_py(0.0, 10.0) - 10.0) < 1e-9
    assert abs(_vtrap_py(1e-12, 10.0) - 10.0) < 1e-6


def test_vtrap_no_nan_inf_near_singularities() -> None:
    # Classical HH singularities around -40 and -55 appear in alpha functions.
    xs = np.array([0.0, 1e-9, -1e-9, 1e-6, -1e-6], dtype=np.float64)
    ys = [10.0, 8.0, 12.0]
    for y in ys:
        vals = np.array([_vtrap_py(float(x), float(y)) for x in xs], dtype=np.float64)
        assert np.all(np.isfinite(vals))
