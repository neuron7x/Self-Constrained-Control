from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .buffer import TrajectoryBuffer, Transition
from .policy import TabularPolicy


class Trainer:
    def train_step(self, transition: Transition) -> float:
        raise NotImplementedError

    def train_epochs(self, buffer: TrajectoryBuffer, epochs: int) -> list[float]:
        raise NotImplementedError


@dataclass
class QLearningTrainer(Trainer):
    policy: TabularPolicy
    gamma: float = 0.95
    alpha: float = 0.1
    max_steps_per_epoch: int = 64
    td_errors: list[float] = field(default_factory=list)

    def train_step(self, transition: Transition) -> float:
        q_vals = self.policy.q_values(transition.state)
        q_sa = float(q_vals[transition.action])
        next_q = float(np.max(self.policy.q_values(transition.next_state)))
        target = transition.reward + self.gamma * next_q * (1.0 - float(transition.done))
        td_error = target - q_sa
        updated = q_sa + self.alpha * td_error
        self.policy.update_q(transition.state, transition.action, updated)
        self.td_errors.append(float(td_error))
        return float(td_error)

    def train_epochs(self, buffer: TrajectoryBuffer, epochs: int) -> list[float]:
        self.td_errors.clear()
        for _ in range(epochs):
            for steps, transition in enumerate(buffer.iter_deterministic(), start=1):
                self.train_step(transition)
                if steps >= self.max_steps_per_epoch:
                    break
        return list(self.td_errors)
