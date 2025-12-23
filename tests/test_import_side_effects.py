from __future__ import annotations

import importlib
import logging

from scripts.ci import check_import_side_effects


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
    assert check_import_side_effects.main() == 0
