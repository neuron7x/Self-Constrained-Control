from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt


@dataclass
class PolicyArtifact:
    schema_version: str
    algo: str
    hyperparams: dict[str, Any]
    weights: npt.NDArray[np.float32]
    feature_spec: dict[str, Any]
    action_mapping: list[int]
    seed: int
    timestamp: float
    policy_version: str


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def save_policy_artifact(
    artifact: PolicyArtifact, path: str = "artifacts/models/rl_policy.npz"
) -> Path:
    model_path = Path(path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_path,
        schema_version=artifact.schema_version,
        algo=artifact.algo,
        hyperparams=json.dumps(artifact.hyperparams),
        weights=artifact.weights,
        feature_spec=json.dumps(artifact.feature_spec),
        action_mapping=np.array(artifact.action_mapping, dtype=np.int32),
        seed=np.array([artifact.seed], dtype=np.int32),
        timestamp=np.array([artifact.timestamp], dtype=np.float64),
        policy_version=artifact.policy_version,
    )
    sha = _compute_sha256(model_path)
    sha_path = model_path.with_suffix(model_path.suffix + ".sha256")
    sha_path.write_text(sha, encoding="utf-8")
    return model_path


def load_policy_artifact(path: str = "artifacts/models/rl_policy.npz") -> PolicyArtifact:
    model_path = Path(path)
    sha_path = model_path.with_suffix(model_path.suffix + ".sha256")
    if not model_path.exists() or not sha_path.exists():
        raise FileNotFoundError("policy artifact or checksum missing")
    expected_sha = sha_path.read_text(encoding="utf-8").strip()
    actual_sha = _compute_sha256(model_path)
    if expected_sha != actual_sha:
        raise ValueError("sha256 mismatch for policy artifact")

    data = np.load(model_path, allow_pickle=False)
    return PolicyArtifact(
        schema_version=str(data["schema_version"].item()),
        algo=str(data["algo"].item()),
        hyperparams=json.loads(str(data["hyperparams"].item())),
        weights=np.array(data["weights"], dtype=np.float32),
        feature_spec=json.loads(str(data["feature_spec"].item())),
        action_mapping=[int(x) for x in data["action_mapping"]],
        seed=int(data["seed"][0]),
        timestamp=float(data["timestamp"][0]),
        policy_version=str(data["policy_version"].item()),
    )
