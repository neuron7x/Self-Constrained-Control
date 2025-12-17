from __future__ import annotations

import pytest
import numpy as np

from self_constrained_control.neural_interface import (
    DetailedMetabolicState,
    N1Simulator,
    apply_sparse_correlation,
    hh_dynamics_vectorized,
)

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


def test_atp_normalization():
    metabolic = DetailedMetabolicState()
    cost_1024 = metabolic.update(dt=0.001, spike_count=1024, I_total=5.0, pump_rate=1e-18, n_neurons=1024)
    metabolic = DetailedMetabolicState()
    cost_512 = metabolic.update(dt=0.001, spike_count=512, I_total=5.0, pump_rate=1e-18, n_neurons=512)
    assert abs(cost_1024 - cost_512) < 0.1 * cost_1024


def test_numba_compilation():
    V = np.full(1024, -65.0, dtype=np.float32)
    m = np.full(1024, 0.05, dtype=np.float32)
    h = np.full(1024, 0.6, dtype=np.float32)
    n = np.full(1024, 0.32, dtype=np.float32)
    I_inj = np.full(1024, 5.0, dtype=np.float32)

    V_trace, spike_counts, final_states = hh_dynamics_vectorized(
        V,
        m,
        h,
        n,
        I_inj,
        0.00005,
        10,
        120.0,
        36.0,
        0.3,
        50.0,
        -77.0,
        -54.4,
        1.0,
        1.0,
    )
    assert V_trace.shape == (1024, 10)
    assert spike_counts.shape == (1024,)
    assert len(final_states) == 4


def test_sparse_correlation_efficiency():
    import time

    sim = N1Simulator(n_channels=128)
    firing_rates = np.random.uniform(0, 50, sim.channels).astype(np.float32)

    start = time.perf_counter()
    for _ in range(100):
        _ = apply_sparse_correlation(firing_rates, sim.cov_indices, sim.cov_indptr, sim.cov_data, noise_scale=0.1)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.2
