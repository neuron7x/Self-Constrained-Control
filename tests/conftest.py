from __future__ import annotations

import pathlib
import sys

import pytest

from self_constrained_control.utils import load_config
# Make src-layout importable for local `pytest` runs without `pip install -e .`
_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture()
def config_path(tmp_path: pathlib.Path) -> str:
    # copy default config but reduce channels for faster tests
    src = pathlib.Path("data/n1_config.yaml")
    dst = tmp_path / "n1_config.yaml"
    text = src.read_text(encoding="utf-8")
    text = text.replace("n_channels: 128", "n_channels: 32")
    dst.write_text(text, encoding="utf-8")
    return str(dst)


@pytest.fixture()
def config_data(config_path: str) -> dict[str, object]:
    return load_config(config_path)
