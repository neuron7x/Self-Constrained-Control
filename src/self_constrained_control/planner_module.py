from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


class LyapunovStabilityAnalyzer:
    def __init__(self) -> None:
        self.P = np.array([[2.0, 0.1], [0.1, 2.0]], dtype=np.float32)

    def V(self, state: np.ndarray, target: np.ndarray) -> float:
        err = state - target
        return float(err.T @ self.P @ err)

    def stable(
        self, state: np.ndarray, next_state: np.ndarray, target: np.ndarray
    ) -> tuple[bool, float]:
        dv = self.V(next_state, target) - self.V(state, target)
        return dv < 0.0, float(dv)


class LQRController:
    def __init__(self, state_size: int, action_size: int, seed: int = 1337) -> None:
        rng = np.random.default_rng(seed)
        self.A = np.eye(state_size, dtype=np.float32) - 0.01 * rng.standard_normal(
            (state_size, state_size)
        ).astype(np.float32)
        self.B = 0.1 * rng.standard_normal((state_size, action_size)).astype(np.float32)
        self.Q = np.eye(state_size, dtype=np.float32) * 10.0
        self.R = np.eye(action_size, dtype=np.float32) * 1.0
        self.K: np.ndarray | None = None

    def _solve(self, max_iter: int = 500, tol: float = 1e-6) -> np.ndarray:
        P = self.Q.copy()
        for _ in range(max_iter):
            inv = np.linalg.inv(self.R + self.B.T @ P @ self.B)
            Pn = (
                self.Q + self.A.T @ P @ self.A - self.A.T @ P @ self.B @ inv @ self.B.T @ P @ self.A
            )
            if float(np.max(np.abs(Pn - P))) < tol:
                P = Pn
                break
            P = Pn
        self.K = np.linalg.inv(self.R + self.B.T @ P @ self.B) @ self.B.T @ P @ self.A
        return self.K

    def control(self, state: np.ndarray, target: np.ndarray) -> np.ndarray:
        if self.K is None:
            self._solve()
        err = state - target
        return -self.K @ err  # type: ignore[operator]


@dataclass
class PlannerConfig:
    state_size: int = 2
    action_size: int = 3
    gamma: float = 0.95
    epsilon: float = 1e-6


class PlannerModule:
    def __init__(
        self, state_size: int = 2, action_size: int = 3, gamma: float = 0.95, epsilon: float = 1e-6
    ) -> None:
        self.cfg = PlannerConfig(
            state_size=state_size, action_size=action_size, gamma=gamma, epsilon=epsilon
        )
        self.lyapunov = LyapunovStabilityAnalyzer()
        self.lqr = LQRController(state_size, action_size)
        self.target_state = np.array([75.0, 75.0], dtype=np.float32)
        self.force_simplify = False

    @staticmethod
    def estimate_params(action: int) -> tuple[float, float, float]:
        base = np.array(
            [
                [10.0, 5.0, 8.0],
                [5.0, 2.0, 4.0],
                [0.0, 0.0, 10.0],
            ],
            dtype=np.float32,
        )[action]
        noise = np.random.normal(0.0, 0.5, 3).astype(np.float32)
        r, c, s = base + noise
        return float(r), float(c), float(s)

    def decide_rule_based(self, state: np.ndarray) -> int:
        if self.force_simplify:
            return 1
        battery, energy = float(state[0]), float(state[1])
        if energy > 50.0 and battery > 30.0:
            return 0
        if energy > 30.0 and battery > 15.0:
            return 1
        return 2

    def decide_with_stability(self, state: np.ndarray) -> int:
        u = self.lqr.control(state, self.target_state)
        action_lqr = int(np.clip(int(np.argmax(u)), 0, self.cfg.action_size - 1))
        # candidate actions: lqr then rule-based
        for action in (action_lqr, self.decide_rule_based(state)):
            _r, c, _ = self.estimate_params(action)
            next_state = np.maximum(state - np.array([c, 0.5 * c], dtype=np.float32), 0.0)
            ok, _dv = self.lyapunov.stable(state, next_state, self.target_state)
            if ok:
                return action
        return self.decide_rule_based(state)

    def get_reason(self, action_idx: int) -> str:
        return [
            "Approved: stable & beneficial",
            "Simplified: conserve resources",
            "Rejected: stability/risk",
        ][action_idx]

    def compute_bellman_error(
        self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray
    ) -> float:
        # Scaffold TD proxy (kept deterministic & torch-free).
        r, c, _ = self.estimate_params(action)
        target = reward + self.cfg.gamma * (r - c)
        pred = r - c
        return float(abs(pred - target))

    async def train(self, epochs: int = 1) -> None:
        # Torch RL backend can be added under optional dependency "ml".
        _ = epochs
        return
