from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "self_constrained_control"
SYSTEM_PY = SRC / "system.py"


def fail(msg: str) -> None:
    print(f"::error::{msg}")
    raise SystemExit(1)


def has_top_level_call(tree: ast.Module, predicate) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if predicate(node.value):
                return True
    return False


def _is_setup_logging_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id == "setup_logging"
    if isinstance(func, ast.Attribute):
        return func.attr == "setup_logging"
    return False


def _is_logging_basicconfig_call(call: ast.Call) -> bool:
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "logging"
        and func.attr == "basicConfig"
    )


def main() -> int:
    if not SYSTEM_PY.exists():
        fail("NOT FOUND: src/self_constrained_control/system.py")

    tree = ast.parse(SYSTEM_PY.read_text(encoding="utf-8"))
    if has_top_level_call(tree, _is_setup_logging_call):
        fail("Import-time side effect: system.py calls setup_logging() at module top-level. Move to CLI.")

    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if has_top_level_call(tree, _is_logging_basicconfig_call):
            offenders.append(str(path.relative_to(ROOT)))

    if offenders:
        fail(
            f"Import-time side effect: logging.basicConfig() executed at module top-level in {', '.join(sorted(offenders))}"
        )

    print("OK: no import-time logging side effects in core modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
