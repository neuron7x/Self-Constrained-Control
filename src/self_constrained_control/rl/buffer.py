from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt


@dataclass
class Transition:
    state: npt.NDArray[np.float32]
    action: int
    reward: float
    next_state: npt.NDArray[np.float32]
    done: bool


@dataclass
class TrajectoryBuffer:
    capacity: int = 256
    _data: list[Transition] = field(default_factory=list)

    def add(self, transition: Transition) -> None:
        if len(self._data) >= self.capacity:
            self._data.pop(0)
        self._data.append(transition)

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:
        self._data.clear()

    def all(self) -> list[Transition]:
        return list(self._data)

    def iter_deterministic(self) -> Iterable[Transition]:
        # Preserve insertion order for deterministic training
        return tuple(self._data)
