from __future__ import annotations

import hashlib
import logging
import os
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

import yaml

logger = logging.getLogger(__name__)
T = TypeVar("T")


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_config(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Config must be a mapping")
    return data


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_timeout_s: float = 60.0

    failures: int = 0
    opened_at: Optional[float] = None

    async def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        now = time.time()
        if self.opened_at is not None:
            if now - self.opened_at < self.reset_timeout_s:
                raise RuntimeError("Circuit breaker is open")
            self.opened_at = None
            self.failures = 0

        try:
            out = fn(*args, **kwargs)
            if hasattr(out, "__await__"):
                out = await out
            self.failures = 0
            return out
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = time.time()
            raise


class StateManager:
    def __init__(self, base_dir: str = "artifacts/state") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _digest(self, payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    def save_state(self, obj: Any, name: str) -> Path:
        # Do not store arbitrary user-provided objects in production without hardening.
        payload = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        digest = self._digest(payload)
        out = self.base_dir / f"{name}.pkl"
        out.write_bytes(payload)
        (self.base_dir / f"{name}.sha256").write_text(digest, encoding="utf-8")
        return out

    def load_state(self, name: str) -> Any:
        p = self.base_dir / f"{name}.pkl"
        h = self.base_dir / f"{name}.sha256"
        payload = p.read_bytes()
        digest = h.read_text(encoding="utf-8").strip()
        if self._digest(payload) != digest:
            raise ValueError("State hash mismatch")
        return pickle.loads(payload)
