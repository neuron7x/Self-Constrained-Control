from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field
from pydantic.functional_validators import field_validator

from .actuator_module import ActuatorModule
from .budget_manager import GameTheoreticBudgetManager
from .contracts import (
    BudgetSnapshot,
    SystemScalars,
    validate_budget_snapshot,
    validate_system_scalars,
)
from .metrics import MetricsCollector
from .monitoring import AnomalyDetector, BudgetHealthMonitor, GracefulDegradation
from .neural_interface import IntentionDecoder, N1Simulator
from .planner_module import PlannerModule
from .utils import CircuitBreaker, StateManager
logger = logging.getLogger(__name__)


class SystemConfig(BaseModel):
    initial_battery: float = Field(default=100.0, ge=0.0, le=100.0)
    initial_user_energy: float = Field(default=100.0, ge=0.0, le=100.0)

    gamma: float = Field(default=0.95, gt=0.0, lt=1.0)
    tau: float = Field(default=10.0, gt=0.0)
    epsilon: float = Field(default=1e-6, gt=0.0)

    safety_mode: Literal["strict", "moderate", "minimal"] = "strict"
    watchdog_timeout_s: float = Field(default=1.0, gt=0.0)

    energy_threshold: float = Field(default=20.0, ge=0.0, le=100.0)
    battery_threshold: float = Field(default=10.0, ge=0.0, le=100.0)

    global_resource_pool: float = Field(default=1000.0, gt=0.0)
    decoder_budget: float = Field(default=200.0, gt=0.0)
    planner_budget: float = Field(default=400.0, gt=0.0)
    actuator_budget: float = Field(default=400.0, gt=0.0)

    decoder_sla_ms: float = Field(default=20.0, gt=0.0)
    planner_sla_ms: float = Field(default=50.0, gt=0.0)
    actuator_sla_ms: float = Field(default=30.0, gt=0.0)

    n_channels: int = Field(default=128, ge=1, le=4096)
    sim_window_s: float = Field(default=0.02, gt=0.0, le=1.0)
    max_firing_hz: float = Field(default=200.0, gt=0.0)
    seed: int = Field(default=1337)

    @field_validator("tau")
    @classmethod
    def _tau_range(cls, v: float) -> float:
        if not 1.0 <= float(v) <= 100.0:
            raise ValueError("Tau outside biological range [1, 100]")
        return float(v)


@dataclass
class WatchdogTimer:
    timeout_s: float
    last_update: float = field(default_factory=lambda: time.time())

    def reset(self) -> None:
        self.last_update = time.time()

    def check(self) -> None:
        if time.time() - self.last_update > self.timeout_s:
            raise RuntimeError("Watchdog timeout")


class ResourceAwareSystem:
    def __init__(
        self, config: SystemConfig | dict[str, Any], *, config_path: str | None = None
    ) -> None:
        if isinstance(config, SystemConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = SystemConfig(**config)
        else:
            raise TypeError("config must be a SystemConfig or dict")
        self.config_path = config_path
        self.rng = np.random.default_rng(self.config.seed)

        self.battery = float(self.config.initial_battery)
        self.user_energy = float(self.config.initial_user_energy)

        self.resource_lock = asyncio.Lock()

        self.n1 = N1Simulator(
            tau=self.config.tau,
            n_channels=self.config.n_channels,
            sim_window_s=self.config.sim_window_s,
            max_firing_hz=self.config.max_firing_hz,
            seed=self.config.seed,
        )
        self.decoder = IntentionDecoder()
        self.planner = PlannerModule(
            state_size=2,
            action_size=3,
            gamma=self.config.gamma,
            epsilon=self.config.epsilon,
            seed=self.config.seed,
        )
        self.actuator = ActuatorModule(safety_mode=self.config.safety_mode)

        self.budget_manager = GameTheoreticBudgetManager(
            self.config.global_resource_pool,
            {
                "decoder": (self.config.decoder_budget, self.config.decoder_sla_ms),
                "planner": (self.config.planner_budget, self.config.planner_sla_ms),
                "actuator": (self.config.actuator_budget, self.config.actuator_sla_ms),
            },
        )

        self.metrics = MetricsCollector()
        self.circuit_breaker = CircuitBreaker()
        self.state = StateManager()

        self.anomaly = AnomalyDetector()
        self.health = BudgetHealthMonitor({"decoder": 50.0, "planner": 100.0, "actuator": 100.0})
        self.degradation = GracefulDegradation()
        self.degradation_mode = "FULL"

    async def monitor_resources(self) -> tuple[float, float]:
        async with self.resource_lock:
            firing = await self.circuit_breaker.call(self.n1.get_neural_spikes)
            self.user_energy = float(self.n1.decode_energy(firing))
            # simple depletion model
            self.battery = float(max(0.0, self.battery - max(0.0, 3.0 + self.rng.normal(0.0, 1.0))))
            self.metrics.battery_level = self.battery
            self.metrics.user_energy_level = self.user_energy
            validate_system_scalars(
                SystemScalars(self.battery, self.user_energy, self.degradation_mode)
            )
            return self.battery, self.user_energy

    async def process_action(self, action_name: str) -> None:
        # Decoder
        t0 = time.time()
        if not self.budget_manager.modules["decoder"].request(100.0):
            return
        firing = await self.circuit_breaker.call(self.n1.get_neural_spikes)
        intent = await self.decoder.decode_intent(firing)
        dec_ms = (time.time() - t0) * 1000.0
        self.budget_manager.check_sla("decoder", dec_ms)
        self.metrics.record_latency("decoder", dec_ms / 1000.0)
        self.anomaly.add_sample("decoder", dec_ms / 1000.0)

        if intent != action_name:
            return

        # Planner
        t1 = time.time()
        if not self.budget_manager.modules["planner"].request(200.0):
            return
        state = np.array([self.battery, self.user_energy], dtype=np.float32)
        a = self.planner.decide_with_stability(state)
        self.metrics.set_rl_metrics(self.planner.rl_metrics_snapshot())
        approve = a in (0, 1)
        r, c, _ = self.planner.estimate_params(a)
        next_state = np.maximum(state - np.array([c, 0.5 * c], dtype=np.float32), 0.0)
        self.metrics.bellman_error = float(
            self.planner.compute_bellman_error(state, a, r - c, next_state)
        )
        plan_ms = (time.time() - t1) * 1000.0
        self.budget_manager.check_sla("planner", plan_ms)
        self.metrics.record_latency("planner", plan_ms / 1000.0)
        self.anomaly.add_sample("planner", plan_ms / 1000.0)

        if not approve:
            return

        # Actuator
        t2 = time.time()
        if not self.budget_manager.modules["actuator"].request(150.0):
            return
        await self.circuit_breaker.call(self.actuator.perform, action_name, simplified=(a == 1))
        act_ms = (time.time() - t2) * 1000.0
        self.budget_manager.check_sla("actuator", act_ms)
        self.metrics.record_latency("actuator", act_ms / 1000.0)
        self.anomaly.add_sample("actuator", act_ms / 1000.0)

        # Update neuromodulation
        self.n1.neuromod.update_from_success(r)
        self.n1.neuromod.update_from_stress(self.metrics.bellman_error > 0.1)

        await self.monitor_resources()
        self.metrics.export_json()

    async def run_loop(self, actions: list[str], epochs: int = 1) -> None:
        wd = WatchdogTimer(self.config.watchdog_timeout_s)
        await self.planner.train(epochs)
        self.metrics.set_rl_metrics(self.planner.rl_metrics_snapshot())
        for i, act in enumerate(actions, start=1):
            wd.reset()

            self.budget_manager.allocate_cycle()
            self.budget_manager.negotiate_resources()
            validate_budget_snapshot(
                BudgetSnapshot(
                    budgets={
                        k: float(v.budget_remaining) for k, v in self.budget_manager.modules.items()
                    },
                    slas_ms={k: float(v.sla_ms) for k, v in self.budget_manager.modules.items()},
                ),
                known_modules=self.budget_manager.modules.keys(),
            )
            eq = self.budget_manager.find_nash_equilibrium()
            for k, v in eq.items():
                self.budget_manager.modules[k].budget_remaining = float(v)

            await self.process_action(act)

            self.budget_manager.end_cycle()
            health = self.health.check_health(self.budget_manager)
            self.degradation.assess_and_degrade(
                self.battery,
                self.user_energy,
                health,
                thresholds=(self.config.battery_threshold, self.config.energy_threshold),
            )
            self.degradation.apply_mode(self)
            self.state.save_state(
                {"cycle": i, "action": act, "battery": self.battery, "energy": self.user_energy},
                f"cycle_{i}_{act}",
            )

            wd.check()

        self.metrics.export_parquet("artifacts/metrics/metrics.parquet")
        # Always emit a JSON snapshot for downstream consumers and tests
        self.metrics.export_json("artifacts/metrics/metrics.json")
