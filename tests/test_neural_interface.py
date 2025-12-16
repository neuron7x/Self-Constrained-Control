from __future__ import annotations

import pytest
import numpy as np

from self_constrained_control.neural_interface import N1Simulator

@pytest.mark.asyncio
async def test_simulator_rates_shape_and_range():
    sim = N1Simulator(n_channels=32, sim_window_s=0.01, seed=1)
    rates = await sim.get_neural_spikes()
    assert rates.shape == (32,)
    assert np.all(np.isfinite(rates))
    assert np.min(rates) >= 0.0
    assert np.max(rates) <= sim.max_firing_hz + 1e-6

@pytest.mark.asyncio
async def test_decode_energy_range():
    sim = N1Simulator(n_channels=32, sim_window_s=0.01, seed=2)
    rates = await sim.get_neural_spikes()
    e = sim.decode_energy(rates)
    assert 0.0 <= e <= 100.0
