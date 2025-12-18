from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


def _vtrap_py(x: float, y: float) -> float:
    """Numerically stable x/(1-exp(-x/y)) with correct limit as x->0 (returns y)."""
    if abs(x) < 1e-7:
        return y
    return x / (1.0 - float(np.exp(-x / y)))


try:
    from numba import njit, prange  # type: ignore

    _HAVE_NUMBA = True
except Exception:  # pragma: no cover
    _HAVE_NUMBA = False
    njit = None  # type: ignore
    prange = range  # type: ignore


def _safe_div(x: float, y: float, eps: float = 1e-9) -> float:
    if abs(y) < eps:
        return x / eps
    return x / y


def _build_neighbor_graph(n: int, k_neighbors: int = 8) -> tuple[np.ndarray, np.ndarray]:
    # Returns (neighbors, weights) arrays of shape (n, k)
    k = max(1, k_neighbors)
    neighbors = np.zeros((n, k), dtype=np.int32)
    weights = np.zeros((n, k), dtype=np.float32)
    half = k // 2
    for i in range(n):
        idxs = []
        for j in range(i - half, i + half + 1):
            if j == i:
                continue
            if 0 <= j < n:
                idxs.append(j)
        # pad
        while len(idxs) < k:
            idxs.append(i)
        idxs = idxs[:k]
        neighbors[i] = np.array(idxs, dtype=np.int32)
        # distance-based weight
        for t, j in enumerate(idxs):
            d = abs(i - int(j))
            weights[i, t] = float(0.1 * np.exp(-d / 2.0))
    return neighbors, weights


if _HAVE_NUMBA:

    @njit(fastmath=True, cache=True)  # type: ignore[misc]
    def _vtrap_nb(x: float, y: float) -> float:
        if abs(x) < 1e-7:
            return y
        return x / (1.0 - np.exp(-x / y))

    @njit(parallel=True, fastmath=True, cache=True)  # type: ignore[misc]
    def _hh_step(
        V: np.ndarray,
        m: np.ndarray,
        h: np.ndarray,
        n: np.ndarray,
        I: np.ndarray,
        dt: float,
        g_Na: float,
        g_K: float,
        g_L: float,
        E_Na: float,
        E_K: float,
        E_L: float,
        C_m: float,
        temp_factor: float,
    ) -> None:
        for i in prange(V.shape[0]):
            # HH rate constants (with numerical stability guards)
            v = V[i]
            a_m = temp_factor * 0.1 * _vtrap_nb(v + 40.0, 10.0)
            b_m = temp_factor * 4.0 * np.exp(-(v + 65.0) / 18.0)
            a_h = temp_factor * 0.07 * np.exp(-(v + 65.0) / 20.0)
            b_h = temp_factor * 1.0 / (1.0 + np.exp(-(v + 35.0) / 10.0))
            a_n = temp_factor * 0.01 * _vtrap_nb(v + 55.0, 10.0)
            b_n = temp_factor * 0.125 * np.exp(-(v + 65.0) / 80.0)

            I_Na = g_Na * (m[i] ** 3) * h[i] * (v - E_Na)
            I_K = g_K * (n[i] ** 4) * (v - E_K)
            I_L = g_L * (v - E_L)

            dV = (-I_Na - I_K - I_L + I[i]) / C_m
            dm = a_m * (1.0 - m[i]) - b_m * m[i]
            dh = a_h * (1.0 - h[i]) - b_h * h[i]
            dn = a_n * (1.0 - n[i]) - b_n * n[i]

            V[i] = v + dV * dt
            m[i] = min(1.0, max(0.0, m[i] + dm * dt))
            h[i] = min(1.0, max(0.0, h[i] + dh * dt))
            n[i] = min(1.0, max(0.0, n[i] + dn * dt))

    @njit(parallel=True, fastmath=True, cache=True)  # type: ignore[misc]
    def _apply_neighbors(
        rates: np.ndarray, neighbors: np.ndarray, weights: np.ndarray, noise_scale: float
    ) -> np.ndarray:
        out = rates.copy()
        for i in prange(rates.shape[0]):
            s = 0.0
            for j in range(neighbors.shape[1]):
                s += weights[i, j] * rates[neighbors[i, j]]
            out[i] = rates[i] + noise_scale * s
        return out

    @njit(parallel=True, fastmath=True, cache=True)  # type: ignore[misc]
    def hh_dynamics_vectorized(
        V: np.ndarray,
        m: np.ndarray,
        h: np.ndarray,
        n: np.ndarray,
        I_inj: np.ndarray,
        dt: float,
        n_steps: int,
        g_Na: float,
        g_K: float,
        g_L: float,
        E_Na: float,
        E_K: float,
        E_L: float,
        C_m: float,
        temp_factor: float,
    ) -> tuple[np.ndarray, np.ndarray, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        V_local = V.copy()
        m_local = m.copy()
        h_local = h.copy()
        n_local = n.copy()
        V_trace = np.empty((V.shape[0], n_steps), dtype=np.float32)
        spike_counts = np.zeros(V.shape[0], dtype=np.int32)
        for t in range(n_steps):
            _hh_step(
                V_local,
                m_local,
                h_local,
                n_local,
                I_inj,
                dt,
                g_Na,
                g_K,
                g_L,
                E_Na,
                E_K,
                E_L,
                C_m,
                temp_factor,
            )
            for i in prange(V_local.shape[0]):
                if V_local[i] > 0.0:
                    spike_counts[i] += 1
            V_trace[:, t] = V_local
        return V_trace, spike_counts, (V_local, m_local, h_local, n_local)

    @njit(parallel=True, fastmath=True, cache=True)  # type: ignore[misc]
    def apply_sparse_correlation_nb(
        rates: np.ndarray,
        indices: np.ndarray,
        indptr: np.ndarray,
        data: np.ndarray,
        noise_scale: float,
    ) -> np.ndarray:
        out = rates.copy()
        n_rows = indptr.shape[0] - 1
        for i in prange(n_rows):
            s = 0.0
            start = indptr[i]
            end = indptr[i + 1]
            for k in range(start, end):
                s += data[k] * rates[indices[k]]
            out[i] = rates[i] + noise_scale * s
        return out

else:

    def _hh_step(
        V: np.ndarray,
        m: np.ndarray,
        h: np.ndarray,
        n: np.ndarray,
        I: np.ndarray,
        dt: float,
        g_Na: float,
        g_K: float,
        g_L: float,
        E_Na: float,
        E_K: float,
        E_L: float,
        C_m: float,
        temp_factor: float,
    ) -> None:
        """Pure-Python HH step (Numba-unavailable fallback)."""
        for i in range(V.shape[0]):
            v = float(V[i])

            a_m = float(temp_factor) * 0.1 * _vtrap_py(v + 40.0, 10.0)
            b_m = float(temp_factor) * 4.0 * float(np.exp(-(v + 65.0) / 18.0))
            a_h = float(temp_factor) * 0.07 * float(np.exp(-(v + 65.0) / 20.0))
            b_h = float(temp_factor) * 1.0 / (1.0 + float(np.exp(-(v + 35.0) / 10.0)))
            a_n = float(temp_factor) * 0.01 * _vtrap_py(v + 55.0, 10.0)
            b_n = float(temp_factor) * 0.125 * float(np.exp(-(v + 65.0) / 80.0))

            m_i = float(m[i])
            h_i = float(h[i])
            n_i = float(n[i])

            dm = a_m * (1.0 - m_i) - b_m * m_i
            dh = a_h * (1.0 - h_i) - b_h * h_i
            dn = a_n * (1.0 - n_i) - b_n * n_i

            m_i = m_i + dm * dt
            h_i = h_i + dh * dt
            n_i = n_i + dn * dt

            m_i = 0.0 if m_i < 0.0 else (1.0 if m_i > 1.0 else m_i)
            h_i = 0.0 if h_i < 0.0 else (1.0 if h_i > 1.0 else h_i)
            n_i = 0.0 if n_i < 0.0 else (1.0 if n_i > 1.0 else n_i)

            I_Na = g_Na * (m_i**3) * h_i * (v - E_Na)
            I_K = g_K * (n_i**4) * (v - E_K)
            I_L = g_L * (v - E_L)
            dV = (-I_Na - I_K - I_L + float(I[i])) / C_m

            V[i] = v + dV * dt
            m[i] = m_i
            h[i] = h_i
            n[i] = n_i

    def _apply_neighbors(
        rates: np.ndarray, neighbors: np.ndarray, weights: np.ndarray, noise_scale: float
    ) -> np.ndarray:
        """Pure-Python sparse-neighbor correlation apply (Numba-unavailable fallback)."""
        out = rates.copy()
        for i in range(rates.shape[0]):
            s = 0.0
            for j in range(neighbors.shape[1]):
                nidx = int(neighbors[i, j])
                w = float(weights[i, j])
                if nidx >= 0 and w != 0.0:
                    s += w * float(rates[nidx])
            out[i] = float(out[i]) + s * float(noise_scale)
        return out

    def hh_dynamics_vectorized(
        V: np.ndarray,
        m: np.ndarray,
        h: np.ndarray,
        n: np.ndarray,
        I_inj: np.ndarray,
        dt: float,
        n_steps: int,
        g_Na: float,
        g_K: float,
        g_L: float,
        E_Na: float,
        E_K: float,
        E_L: float,
        C_m: float,
        temp_factor: float,
    ) -> tuple[np.ndarray, np.ndarray, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        V_local = V.copy()
        m_local = m.copy()
        h_local = h.copy()
        n_local = n.copy()
        V_trace = np.empty((V.shape[0], n_steps), dtype=np.float32)
        spike_counts = np.zeros(V.shape[0], dtype=np.int32)
        for t in range(n_steps):
            _hh_step(
                V_local,
                m_local,
                h_local,
                n_local,
                I_inj,
                dt,
                g_Na,
                g_K,
                g_L,
                E_Na,
                E_K,
                E_L,
                C_m,
                temp_factor,
            )
            for i in range(V_local.shape[0]):
                if V_local[i] > 0.0:
                    spike_counts[i] += 1
            V_trace[:, t] = V_local
        return V_trace, spike_counts, (V_local, m_local, h_local, n_local)

    def apply_sparse_correlation_nb(
        rates: np.ndarray,
        indices: np.ndarray,
        indptr: np.ndarray,
        data: np.ndarray,
        noise_scale: float,
    ) -> np.ndarray:
        out = rates.copy()
        n_rows = indptr.shape[0] - 1
        for i in range(n_rows):
            s = 0.0
            start = int(indptr[i])
            end = int(indptr[i + 1])
            for k in range(start, end):
                s += float(data[k]) * float(rates[int(indices[k])])
            out[i] = float(rates[i]) + float(noise_scale) * s
        return out


def apply_sparse_correlation(
    rates: np.ndarray,
    indices: np.ndarray,
    indptr: np.ndarray,
    data: np.ndarray,
    noise_scale: float = 0.1,
) -> np.ndarray:
    out = rates.copy()
    n_rows = indptr.shape[0] - 1
    for i in range(n_rows):
        start = int(indptr[i])
        end = int(indptr[i + 1])
        if end > start:
            contrib = float(np.dot(data[start:end], rates[indices[start:end]]))
            out[i] = float(rates[i]) + noise_scale * contrib
    return out


@dataclass
class DetailedMetabolicState:
    ATP: float = 5.0e-3
    ADP: float = 0.05e-3
    AMP: float = 0.01e-3
    PCr: float = 25.0e-3
    Cr: float = 5.0e-3
    glucose: float = 5.0e-3
    lactate: float = 1.0e-3
    O2: float = 0.1e-3

    def update(
        self,
        dt: float,
        spike_count: int | None = None,
        I_total: float = 0.0,
        pump_rate: float = 0.0,
        n_neurons: int = 1024,
        total_spikes: int | None = None,
    ) -> float:
        ATP_per_spike_per_neuron = 1.67e-18
        spikes = float(spike_count if spike_count is not None else total_spikes or 0)
        total_spike_cost = (ATP_per_spike_per_neuron * spikes) / max(1.0, float(n_neurons))
        pump_cost = float(pump_rate) * float(dt)
        basal_cost = 1e-6 * dt
        cost = total_spike_cost + pump_cost + basal_cost
        self.ATP = float(np.clip(self.ATP - cost, 0.0, 10e-3))
        return float(self.ATP / 5.0e-3)


class NeuromodulationController:
    def __init__(self) -> None:
        self.dopamine = 1.0
        self.norepinephrine = 1.0

    def update_from_success(self, reward: float) -> None:
        self.dopamine = float(np.clip(self.dopamine + 0.1 * reward, 0.5, 2.0))

    def update_from_stress(self, stressed: bool) -> None:
        if stressed:
            self.norepinephrine = float(np.clip(self.norepinephrine + 0.2, 0.5, 2.0))
        else:
            self.norepinephrine = float(np.clip(self.norepinephrine - 0.05, 0.5, 2.0))

    def modulate(self, base_current: np.ndarray) -> np.ndarray:
        scale = self.dopamine * (0.5 + 0.5 * self.norepinephrine)
        return base_current * float(scale)


class N1DataValidator:
    def __init__(self, expected_channels: int, max_rate_hz: float) -> None:
        self.expected_channels = expected_channels
        self.max_rate_hz = max_rate_hz

    def validate(self, rates: np.ndarray) -> tuple[bool, str]:
        if rates.shape != (self.expected_channels,):
            return False, f"shape mismatch {rates.shape} != ({self.expected_channels},)"
        if not np.all(np.isfinite(rates)):
            return False, "non-finite values"
        if np.any(rates < 0.0) or np.any(rates > self.max_rate_hz):
            return False, "rates out of range"
        return True, "ok"


class IntentionDecoder:
    def __init__(self) -> None:
        self.thresholds: dict[str, float] = {"move_arm": 30.0, "plan_route": 15.0, "stop": 0.0}

    async def decode_intent(self, firing_rates: np.ndarray) -> str:
        mean_rate = float(np.mean(firing_rates))
        for intent, thr in sorted(self.thresholds.items(), key=lambda x: x[1], reverse=True):
            if mean_rate > thr:
                return intent
        return "stop"


class N1Simulator:
    def __init__(
        self,
        tau: float = 10.0,
        n_channels: int = 128,
        sim_window_s: float = 0.02,
        max_firing_hz: float = 200.0,
        seed: int | None = None,
    ) -> None:
        self.tau = float(tau)
        self.channels = int(n_channels)
        self.sim_window_s = float(sim_window_s)
        self.max_firing_hz = float(max_firing_hz)
        self.sampling_rate_hz = 20000.0

        self.g_Na = 120.0
        self.g_K = 36.0
        self.g_L = 0.3
        self.E_Na = 50.0
        self.E_K = -77.0
        self.E_L = -54.4
        self.C_m = 1.0

        self.T = 37.0
        self.T_ref = 6.3
        self.Q10 = 3.0
        self.temp_factor = float(self.Q10 ** ((self.T - self.T_ref) / 10.0))

        self.rng = np.random.default_rng(seed)

        self.V = np.full(self.channels, -65.0, dtype=np.float32)
        self.m = np.full(self.channels, 0.05, dtype=np.float32)
        self.h = np.full(self.channels, 0.6, dtype=np.float32)
        self.n = np.full(self.channels, 0.32, dtype=np.float32)

        self.neighbors, self.weights = _build_neighbor_graph(self.channels, k_neighbors=8)
        self._init_sparse_correlation(k_neighbors=8)

        self.metabolic = DetailedMetabolicState()
        self.neuromod = NeuromodulationController()
        self.validator = N1DataValidator(self.channels, self.max_firing_hz)

    def _init_sparse_correlation(self, k_neighbors: int = 8) -> None:
        indices: list[int] = []
        data: list[float] = []
        indptr = [0]
        half = k_neighbors // 2
        for i in range(self.channels):
            for j in range(max(0, i - half), min(self.channels, i + half + 1)):
                if j == i:
                    continue
                distance = abs(i - j)
                correlation = 0.1 * np.exp(-distance / 2.0)
                indices.append(int(j))
                data.append(float(correlation))
            indptr.append(len(indices))
        self.cov_indices = np.array(indices, dtype=np.int32)
        self.cov_data = np.array(data, dtype=np.float32)
        self.cov_indptr = np.array(indptr, dtype=np.int32)

    async def get_neural_spikes(self) -> np.ndarray:
        dt = 1.0 / self.sampling_rate_hz
        n_steps = int(self.sim_window_s / dt)
        # Baseline injected current
        I = self.rng.normal(5.0, 1.0, self.channels).astype(np.float32)
        I = self.neuromod.modulate(I).astype(np.float32)

        if _HAVE_NUMBA:
            # Integrate
            for _ in range(n_steps):
                _hh_step(
                    self.V,
                    self.m,
                    self.h,
                    self.n,
                    I,
                    dt,
                    self.g_Na,
                    self.g_K,
                    self.g_L,
                    self.E_Na,
                    self.E_K,
                    self.E_L,
                    self.C_m,
                    self.temp_factor,
                )
        else:
            # Numba-less fallback (slower, but correct)
            for _ in range(n_steps):
                for i in range(self.channels):
                    v = float(self.V[i])
                    a_m = (
                        self.temp_factor
                        * 0.1
                        * (v + 40.0)
                        / max(1e-9, (1.0 - np.exp(-(v + 40.0) / 10.0)))
                    )
                    b_m = self.temp_factor * 4.0 * np.exp(-(v + 65.0) / 18.0)
                    a_h = self.temp_factor * 0.07 * np.exp(-(v + 65.0) / 20.0)
                    b_h = self.temp_factor * 1.0 / (1.0 + np.exp(-(v + 35.0) / 10.0))
                    a_n = (
                        self.temp_factor
                        * 0.01
                        * (v + 55.0)
                        / max(1e-9, (1.0 - np.exp(-(v + 55.0) / 10.0)))
                    )
                    b_n = self.temp_factor * 0.125 * np.exp(-(v + 65.0) / 80.0)

                    I_Na = self.g_Na * (float(self.m[i]) ** 3) * float(self.h[i]) * (v - self.E_Na)
                    I_K = self.g_K * (float(self.n[i]) ** 4) * (v - self.E_K)
                    I_L = self.g_L * (v - self.E_L)

                    dV = (-I_Na - I_K - I_L + float(I[i])) / self.C_m
                    dm = a_m * (1.0 - float(self.m[i])) - b_m * float(self.m[i])
                    dh = a_h * (1.0 - float(self.h[i])) - b_h * float(self.h[i])
                    dn = a_n * (1.0 - float(self.n[i])) - b_n * float(self.n[i])

                    self.V[i] = np.float32(v + dV * dt)
                    self.m[i] = np.float32(min(1.0, max(0.0, float(self.m[i]) + dm * dt)))
                    self.h[i] = np.float32(min(1.0, max(0.0, float(self.h[i]) + dh * dt)))
                    self.n[i] = np.float32(min(1.0, max(0.0, float(self.n[i]) + dn * dt)))

        # Spike proxy: count threshold crossings in voltage after integration window
        # For a fast scaffold, use firing rate approximation from membrane potential distribution.
        # Scale to 0..max_firing_hz.
        rates = np.maximum(0.0, (self.V.astype(np.float32) + 55.0))  # shift
        rates = rates / max(1e-6, float(rates.max())) * float(self.max_firing_hz)

        if _HAVE_NUMBA:
            rates = apply_sparse_correlation_nb(
                rates.astype(np.float32),
                self.cov_indices,
                self.cov_indptr,
                self.cov_data,
                0.1,
            )
        else:
            rates = apply_sparse_correlation(
                rates.astype(np.float32),
                self.cov_indices,
                self.cov_indptr,
                self.cov_data,
                0.1,
            )

        rates = np.clip(rates.astype(np.float32), 0.0, float(self.max_firing_hz))
        # metabolic update
        total_spikes = int(np.sum(rates) * self.sim_window_s / 10.0)
        I_total = float(np.sum(np.abs(I)))
        _ = self.metabolic.update(
            dt=self.sim_window_s,
            spike_count=total_spikes,
            I_total=I_total,
            pump_rate=1e-18,
            n_neurons=self.channels,
        )

        ok, msg = self.validator.validate(rates)
        if not ok:
            raise ValueError(msg)
        return rates

    def decode_energy(self, firing_rates: np.ndarray) -> float:
        mean_rate = float(np.mean(firing_rates))
        baseline = 25.0
        energy = 100.0 * (mean_rate / baseline) * float(self.metabolic.ATP / 5.0e-3)
        return float(np.clip(energy, 0.0, 100.0))
