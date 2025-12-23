from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Set
from xml.etree import ElementTree as ET


def _normalize_path(path: str, repo_root: Path) -> str:
    candidate = Path(path)
    if str(candidate).startswith(("a/", "b/")):
        candidate = Path(str(candidate)[2:])

    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()

    try:
        return candidate.relative_to(repo_root).as_posix()
    except ValueError:
        return candidate.as_posix()


def load_coverage_map(coverage_xml: Path, repo_root: Path) -> Dict[str, Set[int]]:
    tree = ET.parse(coverage_xml)
    coverage: MutableMapping[str, Set[int]] = defaultdict(set)

    for cls in tree.findall(".//class"):
        filename = cls.get("filename")
        if not filename:
            continue

        normalized = _normalize_path(filename, repo_root)
        for line in cls.findall("./lines/line"):
            hits = int(line.get("hits", "0"))
            if hits > 0:
                coverage[normalized].add(int(line.get("number", "0")))

    return dict(coverage)


def parse_unified_diff(diff_text: str) -> Dict[str, Set[int]]:
    changed: MutableMapping[str, Set[int]] = defaultdict(set)
    current_file: str | None = None
    new_line_number: int | None = None

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            target = raw_line[4:]
            if target == "/dev/null":
                current_file = None
                continue
            current_file = target[2:] if target.startswith("b/") else target
        elif raw_line.startswith("@@"):
            parts = raw_line.split(" ")
            add_section = parts[2] if len(parts) > 2 else ""
            add_segment = add_section.strip("+").split(",")
            start_line = int(add_segment[0]) if add_segment and add_segment[0] else 0
            new_line_number = start_line
        elif raw_line.startswith("+") and not raw_line.startswith("+++"):
            if current_file is not None and new_line_number is not None:
                changed[current_file].add(new_line_number)
            if new_line_number is not None:
                new_line_number += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        else:
            if new_line_number is not None:
                new_line_number += 1

    return dict(changed)


def compute_diff_coverage(
    changed_lines: Mapping[str, Iterable[int]],
    covered_lines: Mapping[str, Set[int]],
) -> tuple[float, Dict[str, Set[int]]]:
    python_changes = {
        path: set(lines) for path, lines in changed_lines.items() if path.endswith(".py")
    }

    total_changed = sum(len(lines) for lines in python_changes.values())
    if total_changed == 0:
        return 100.0, {}

    uncovered: MutableMapping[str, Set[int]] = defaultdict(set)
    for file_path, lines in python_changes.items():
        covered_for_file = covered_lines.get(file_path, set())
        missing = lines.difference(covered_for_file)
        if missing:
            uncovered[file_path].update(sorted(missing))

    covered_count = total_changed - sum(len(v) for v in uncovered.values())
    percent = (covered_count / total_changed) * 100
    return percent, dict(uncovered)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute diff coverage from coverage.xml and git diff.")
    parser.add_argument("--coverage", type=Path, required=True, help="Path to coverage.xml")
    parser.add_argument(
        "--diff",
        type=Path,
        required=False,
        help="Path to unified diff file (defaults to stdin)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=95.0,
        help="Minimum acceptable diff coverage percentage.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root for path normalization.",
    )

    args = parser.parse_args()
    diff_text = args.diff.read_text() if args.diff else sys.stdin.read()

    coverage_map = load_coverage_map(args.coverage, args.repo_root)
    changed = parse_unified_diff(diff_text)
    percent, uncovered = compute_diff_coverage(changed, coverage_map)

    print(f"Diff coverage: {percent:.2f}% (threshold {args.threshold:.2f}%)")
    if uncovered:
        for file_path, lines in uncovered.items():
            sorted_lines = ", ".join(str(line) for line in sorted(lines))
            print(f"Missing coverage in {file_path}: lines {sorted_lines}", file=sys.stderr)

    if percent + 1e-9 < args.threshold:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
