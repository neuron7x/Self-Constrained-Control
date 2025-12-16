from __future__ import annotations

import pytest

from self_constrained_control.neural_interface import N1Simulator

@pytest.mark.asyncio
async def test_benchmark_simulator(benchmark):
    sim = N1Simulator(n_channels=64, sim_window_s=0.01, seed=123)
    await benchmark(sim.get_neural_spikes)
