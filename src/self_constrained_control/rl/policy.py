from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


def encode_state(
    state: npt.NDArray[np.float32], bins: tuple[int, int] = (11, 11)
) -> tuple[int, int]:
    """Discretize battery/energy into stable bins (0-100 inclusive)."""
    battery_bin = int(np.clip(np.floor(float(state[0]) / 10.0), 0, bins[0] - 1))
    energy_bin = int(np.clip(np.floor(float(state[1]) / 10.0), 0, bins[1] - 1))
    return battery_bin, energy_bin


class Policy:
    def propose_action_distribution(
        self, state: npt.NDArray[np.float32], k: int = 1
    ) -> list[tuple[int, float, float]]:
        raise NotImplementedError

    def propose_action(self, state: npt.NDArray[np.float32]) -> int:
        raise NotImplementedError


@dataclass
class TabularPolicy(Policy):
    action_size: int
    bins: tuple[int, int] = (11, 11)
    epsilon: float = 0.1
    seed: int = 1337

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng(self.seed)
        self.q_table: npt.NDArray[np.float32] = np.zeros(
            (self.bins[0], self.bins[1], self.action_size), dtype=np.float32
        )

    def _state_idx(self, state: npt.NDArray[np.float32]) -> tuple[int, int]:
        return encode_state(state, self.bins)

    def q_values(self, state: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        return self.q_table[self._state_idx(state)]

    def update_q(self, state: npt.NDArray[np.float32], action: int, value: float) -> None:
        idx = self._state_idx(state)
        self.q_table[idx][action] = np.float32(value)

    def propose_action_distribution(
        self, state: npt.NDArray[np.float32], k: int = 1
    ) -> list[tuple[int, float, float]]:
        q_vals = self.q_values(state)
        # Shift to non-negative for probability calculation
        shifted = q_vals - float(np.min(q_vals))
        shifted = shifted + 1e-6  # avoid zeros
        probs = shifted / float(np.sum(shifted))
        ranked_actions = list(
            sorted(
                [(i, float(probs[i]), float(q_vals[i])) for i in range(self.action_size)],
                key=lambda x: (-x[2], -x[1], x[0]),
            )
        )
        return ranked_actions[: max(1, min(k, len(ranked_actions)))]

    def propose_action(self, state: npt.NDArray[np.float32]) -> int:
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, self.action_size))
        q_vals = self.q_values(state)
        return int(np.argmax(q_vals))

    def load_weights(self, weights: npt.NDArray[np.float32]) -> None:
        self.q_table = np.array(weights, dtype=np.float32)

    def export_weights(self) -> npt.NDArray[np.float32]:
        return np.array(self.q_table, copy=True)
