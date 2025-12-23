from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from .rl.buffer import TrajectoryBuffer, Transition
from .rl.persistence import PolicyArtifact, load_policy_artifact, save_policy_artifact
from .rl.policy import TabularPolicy
from .rl.reward import compute_reward
from .rl.trainer import QLearningTrainer

logger = logging.getLogger(__name__)


class LyapunovStabilityAnalyzer:
    def __init__(self) -> None:
        self.P = np.array([[2.0, 0.1], [0.1, 2.0]], dtype=np.float32)

    def V(self, state: npt.NDArray[Any], target: npt.NDArray[Any]) -> float:
        err = state - target
        return float(err.T @ self.P @ err)

    def stable(
        self, state: npt.NDArray[Any], next_state: npt.NDArray[Any], target: npt.NDArray[Any]
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
        self.K: npt.NDArray[Any] | None = None

    def _solve(self, max_iter: int = 500, tol: float = 1e-6) -> npt.NDArray[Any]:
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

    def control(self, state: npt.NDArray[Any], target: npt.NDArray[Any]) -> npt.NDArray[Any]:
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
    epsilon_greedy: float = 0.1
    alpha: float = 0.1
    max_episodes: int = 3
    max_steps_per_episode: int = 8
    artifact_path: str = "artifacts/models/rl_policy.npz"


class PlannerModule:
    def __init__(
        self,
        state_size: int = 2,
        action_size: int = 3,
        gamma: float = 0.95,
        epsilon: float = 1e-6,
        seed: int = 1337,
    ) -> None:
        self.seed = seed
        self.cfg = PlannerConfig(
            state_size=state_size,
            action_size=action_size,
            gamma=gamma,
            epsilon=epsilon,
        )
        self.lyapunov = LyapunovStabilityAnalyzer()
        self.lqr = LQRController(state_size, action_size, seed=seed)
        self.target_state = np.array([75.0, 75.0], dtype=np.float32)
        self.force_simplify = False
        self.rng = np.random.default_rng(seed)
        self.rl_policy = TabularPolicy(
            action_size=action_size, epsilon=self.cfg.epsilon_greedy, seed=seed
        )
        self.rl_buffer = TrajectoryBuffer()
        self.rl_trainer = QLearningTrainer(
            policy=self.rl_policy,
            gamma=self.cfg.gamma,
            alpha=self.cfg.alpha,
            max_steps_per_epoch=self.cfg.max_steps_per_episode,
        )
        self.rl_enabled = True
        self.rl_last_td_error: float = 0.0
        self.rl_updates: int = 0
        self.rl_policy_version: str = "v0"
        self.rl_gate_rejections: int = 0
        self.rl_fallbacks: int = 0
        self.rl_decisions: int = 0
        self._load_model(Path(self.cfg.artifact_path))

    def estimate_params(self, action: int) -> tuple[float, float, float]:
        base = np.array(
            [
                [10.0, 5.0, 8.0],
                [5.0, 2.0, 4.0],
                [0.0, 0.0, 10.0],
            ],
            dtype=np.float32,
        )[action]
        noise = self.rng.normal(0.0, 0.5, 3).astype(np.float32)
        r, c, s = base + noise
        return float(r), float(c), float(s)

    def decide_rule_based(self, state: npt.NDArray[Any]) -> int:
        if self.force_simplify:
            return 1
        battery, energy = float(state[0]), float(state[1])
        if energy > 50.0 and battery > 30.0:
            return 0
        if energy > 30.0 and battery > 15.0:
            return 1
        return 2

    def decide_with_stability(self, state: npt.NDArray[Any]) -> int:
        self.rl_decisions += 1
        u = self.lqr.control(state, self.target_state)
        baseline = self.decide_rule_based(state)
        action_lqr = int(np.clip(int(np.argmax(u)), 0, self.cfg.action_size - 1))
        candidates: list[int] = []
        if self.rl_enabled:
            for a, _p, _q in self.rl_policy.propose_action_distribution(
                state, k=self.cfg.action_size
            ):
                candidates.append(a)
        candidates.extend([action_lqr, baseline])
        best_action = 2
        best_score = -float("inf")
        seen: set[int] = set()
        for action in candidates:
            if action in seen:
                continue
            seen.add(action)
            if not self._budget_gate(state, action):
                self.rl_gate_rejections += 1
                continue
            _, cost, _ = self.estimate_params(action)
            next_state = np.maximum(state - np.array([cost, 0.5 * cost], dtype=np.float32), 0.0)
            stable, dv = self.lyapunov.stable(state, next_state, self.target_state)
            if not stable:
                self.rl_gate_rejections += 1
                continue
            score = float(self.rl_policy.q_values(state)[action]) if self.rl_enabled else 0.0
            score += float(-dv)
            if score > best_score:
                best_score = score
                best_action = action
        if best_action == 2:
            self.rl_fallbacks += 1
        return best_action

    def get_reason(self, action_idx: int) -> str:
        return [
            "Approved: stable & beneficial",
            "Simplified: conserve resources",
            "Rejected: stability/risk",
        ][action_idx]

    def compute_bellman_error(
        self, state: npt.NDArray[Any], action: int, reward: float, next_state: npt.NDArray[Any]
    ) -> float:
        # Scaffold TD proxy (kept deterministic & torch-free).
        r, c, _ = self.estimate_params(action)
        target = reward + self.cfg.gamma * (r - c)
        pred = r - c
        return float(abs(pred - target))

    async def train(self, epochs: int = 1) -> None:
        if not self.rl_enabled:
            return
        self.rl_buffer.clear()
        for episode in range(self.cfg.max_episodes):
            state = np.array([80.0 - 2.0 * episode, 75.0 - 2.0 * episode], dtype=np.float32)
            for step in range(self.cfg.max_steps_per_episode):
                action = self.rl_policy.propose_action(state)
                reward, next_state, done = self._simulate_transition(state, action)
                self.rl_buffer.add(
                    Transition(
                        state=state.copy(),
                        action=action,
                        reward=reward,
                        next_state=next_state.copy(),
                        done=done,
                    )
                )
                state = next_state
                if done or step + 1 >= self.cfg.max_steps_per_episode:
                    break
        td_errors = self.rl_trainer.train_epochs(self.rl_buffer, epochs)
        if td_errors:
            self.rl_last_td_error = float(np.mean(np.abs(td_errors)))
        self.rl_updates += len(td_errors)
        self.rl_policy_version = f"v{int(time.time())}"
        artifact = PolicyArtifact(
            schema_version="1.0",
            algo="tabular_q_learning",
            hyperparams={
                "gamma": self.cfg.gamma,
                "alpha": self.cfg.alpha,
                "epsilon": self.cfg.epsilon_greedy,
                "max_episodes": self.cfg.max_episodes,
                "max_steps_per_episode": self.cfg.max_steps_per_episode,
            },
            weights=self.rl_policy.export_weights(),
            feature_spec={"state_bins": self.rl_policy.bins},
            action_mapping=list(range(self.cfg.action_size)),
            seed=self.seed,
            timestamp=time.time(),
            policy_version=self.rl_policy_version,
        )
        save_policy_artifact(artifact, path=self.cfg.artifact_path)

    def _budget_gate(self, state: npt.NDArray[Any], action: int) -> bool:
        _, cost, _ = self.estimate_params(action)
        return bool(cost <= float(state[0]) and cost * 0.5 <= float(state[1]))

    def _simulate_transition(
        self, state: npt.NDArray[np.float32], action: int
    ) -> tuple[float, npt.NDArray[np.float32], bool]:
        reward_signal, cost, success_prob = self.estimate_params(action)
        next_state = np.maximum(state - np.array([cost, 0.5 * cost], dtype=np.float32), 0.0)
        stable, dv = self.lyapunov.stable(state, next_state, self.target_state)
        reward = compute_reward(
            delta_v=dv,
            spent=cost,
            available=float(max(state[0], 1.0)),
            latency_ms=20.0,
            sla_ms=50.0,
            intent="train",
            action_name="train",
            approved=stable and success_prob >= 0.0,
        )
        done = bool(next_state[0] < 5.0 or next_state[1] < 5.0)
        return reward_signal + reward, next_state, done

    def _load_model(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            artifact = load_policy_artifact(str(path))
        except Exception:
            self.rl_enabled = False
            return
        self.rl_policy.load_weights(artifact.weights)
        self.rl_policy_version = artifact.policy_version

    def rl_metrics_snapshot(self) -> dict[str, float | str]:
        decisions = max(1, self.rl_decisions)
        return {
            "rl/epsilon": float(self.rl_policy.epsilon),
            "rl/td_error_mean": float(self.rl_last_td_error),
            "rl/updates": float(self.rl_updates),
            "rl/policy_version": self.rl_policy_version,
            "rl/fallback_rate": float(self.rl_fallbacks) / decisions,
            "rl/gate_rejection_rate": float(self.rl_gate_rejections) / decisions,
        }
