from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class ActuatorModule:
    safety_mode: Literal["strict", "moderate", "minimal"] = "strict"

    async def perform(self, action_name: str, simplified: bool = False) -> None:
        # Safety envelope stub. Replace with ROS2/hardware integration behind strict interfaces.
        if self.safety_mode == "strict" and action_name not in {"move_arm", "plan_route", "stop"}:
            raise ValueError(f"Action not allowed in strict mode: {action_name}")
        # Simulate execution latency
        await asyncio.sleep(0.001 if simplified else 0.003)
        logger.info("Actuator executed action=%s simplified=%s", action_name, simplified)
