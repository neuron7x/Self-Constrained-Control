from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path


def test_import_does_not_mutate_root_logger():
    root = logging.getLogger()
    before_handlers = list(root.handlers)
    before_level = root.level

    importlib.import_module("self_constrained_control.system")

    after_handlers = list(root.handlers)
    after_level = root.level

    assert after_handlers == before_handlers, "Import must not change root handlers"
    assert after_level == before_level, "Import must not change root level"


def test_gate_script_passes():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "check_import_side_effects.py"
    spec = importlib.util.spec_from_file_location("check_import_side_effects", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
