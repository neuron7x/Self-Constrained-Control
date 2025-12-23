from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def delta_v_penalty(delta_v: float) -> float:
    # Positive or zero dv means instability -> strong negative penalty.
    return -max(0.0, float(delta_v)) - 0.5 if delta_v >= 0.0 else 0.5


def budget_efficiency(spent: float, available: float) -> float:
    if available <= 0.0:
        return -1.0
    ratio = np.clip(1.0 - float(spent) / float(available), 0.0, 1.0)
    return float(ratio)


def sla_penalty(latency_ms: float, sla_ms: float) -> float:
    if sla_ms <= 0.0:
        return -1.0
    over = max(0.0, float(latency_ms) - float(sla_ms))
    return -float(over / sla_ms)


def task_success(intent: str, action_name: str, approved: bool) -> float:
    return 1.0 if approved and intent == action_name else 0.0


@dataclass
class RewardWeights:
    w_delta_v: float = 1.0
    w_budget: float = 0.5
    w_sla: float = 0.5
    w_success: float = 1.0


def compute_reward(
    delta_v: float,
    spent: float,
    available: float,
    latency_ms: float,
    sla_ms: float,
    intent: str,
    action_name: str,
    approved: bool,
    weights: RewardWeights | None = None,
) -> float:
    w = weights or RewardWeights()
    dv_term = delta_v_penalty(delta_v)
    budget_term = budget_efficiency(spent, available)
    sla_term = sla_penalty(latency_ms, sla_ms)
    success_term = task_success(intent, action_name, approved)
    reward = (
        w.w_delta_v * dv_term
        + w.w_budget * budget_term
        + w.w_sla * sla_term
        + w.w_success * success_term
    )
    return float(np.clip(reward, -10.0, 10.0))
