from __future__ import annotations

import numpy as np
import pytest

from self_constrained_control.neural_interface import DetailedMetabolicState

def test_metabolic_state_updates_and_clamps():
    m = DetailedMetabolicState()
    a0 = m.ATP
    lvl = m.update(dt=0.01, total_spikes=1000, n_neurons=32)
    assert 0.0 <= lvl <= 2.0
    assert m.ATP <= a0 + 1e-9
    assert m.ATP >= 0.0
