import io
import runpy
import sys
from pathlib import Path

from pytest import approx

from scripts.diff_coverage import (
    compute_diff_coverage,
    load_coverage_map,
    main,
    parse_unified_diff,
    _normalize_path,
)


def _write_coverage(
    tmp_path: Path, filename: str, lines: list[int], zero_hit_lines: list[int] | None = None, absolute: bool = False
) -> Path:
    path = tmp_path / filename
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(
        '<?xml version="1.0" ?>\n'
        '<coverage branch-rate="0" line-rate="1" version="1.0">\n'
        "  <packages>\n"
        "    <package name=\"pkg\" branch-rate=\"0\" line-rate=\"1\">\n"
        "      <classes>\n"
        f"        <class name=\"cls\" filename=\"{path if absolute else filename}\" line-rate=\"1\" branch-rate=\"0\">\n"
        "          <lines>\n"
        + "\n".join(f'            <line number="{line}" hits="1"/>' for line in lines)
        + ("\n" if lines else "")
        + "\n".join(f'            <line number="{line}" hits="0"/>' for line in (zero_hit_lines or []))
        + "\n"
        "          </lines>\n"
        "        </class>\n"
        "      </classes>\n"
        "    </package>\n"
        "  </packages>\n"
        "</coverage>\n"
    )
    return coverage_xml


def test_load_coverage_resolves_basename(tmp_path: Path) -> None:
    repo_root = tmp_path
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir()
    target = scripts_dir / "example.py"
    target.write_text("# sample\n")

    coverage_xml = _write_coverage(tmp_path, "example.py", lines=[1])
    covered, measured = load_coverage_map(coverage_xml, repo_root)

    assert "scripts/example.py" in covered


def test_diff_coverage_full_when_all_changed_lines_are_covered(tmp_path: Path) -> None:
    filename = "src/self_constrained_control/example.py"
    coverage_xml = _write_coverage(tmp_path, filename, lines=[1, 2])
    diff_text = (
        "diff --git a/src/self_constrained_control/example.py b/src/self_constrained_control/example.py\n"
        "--- a/src/self_constrained_control/example.py\n"
        "+++ b/src/self_constrained_control/example.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+new\n"
        "+lines\n"
    )

    covered, measured = load_coverage_map(coverage_xml, tmp_path)
    changed = parse_unified_diff(diff_text)
    percent, uncovered = compute_diff_coverage(changed, covered, measured)

    assert percent == 100.0
    assert uncovered == {}


def test_diff_coverage_reports_missing_lines(tmp_path: Path) -> None:
    filename = "src/self_constrained_control/example.py"
    coverage_xml = _write_coverage(tmp_path, filename, lines=[3], zero_hit_lines=[1, 2])
    diff_text = (
        "diff --git a/src/self_constrained_control/example.py b/src/self_constrained_control/example.py\n"
        "--- a/src/self_constrained_control/example.py\n"
        "+++ b/src/self_constrained_control/example.py\n"
        "@@ -1,0 +1,3 @@\n"
        "+covered\n"
        "+uncovered\n"
        "+also_uncovered\n"
    )

    covered, measured = load_coverage_map(coverage_xml, tmp_path)
    changed = parse_unified_diff(diff_text)
    percent, uncovered = compute_diff_coverage(changed, covered, measured)

    assert percent == approx(33.3333, rel=1e-4)
    assert uncovered == {filename: {1, 2}}


def test_diff_coverage_handles_absolute_paths(tmp_path: Path) -> None:
    repo_root = tmp_path
    filename = "src/self_constrained_control/absolute.py"
    absolute_path = (repo_root / filename).resolve()
    coverage_xml = _write_coverage(tmp_path, str(absolute_path), lines=[10], absolute=True)
    diff_text = (
        "diff --git a/src/self_constrained_control/absolute.py b/src/self_constrained_control/absolute.py\n"
        "--- a/src/self_constrained_control/absolute.py\n"
        "+++ b/src/self_constrained_control/absolute.py\n"
        "@@ -5,0 +10,1 @@\n"
        "+touch\n"
    )

    covered, measured = load_coverage_map(coverage_xml, repo_root)
    changed = parse_unified_diff(diff_text)
    percent, uncovered = compute_diff_coverage(changed, covered, measured)

    assert percent == 100.0
    assert uncovered == {}


def test_diff_coverage_zero_changes_is_perfect(tmp_path: Path) -> None:
    coverage_xml = _write_coverage(tmp_path, "src/self_constrained_control/empty.py", lines=[])
    covered, measured = load_coverage_map(coverage_xml, tmp_path)
    changed = parse_unified_diff("")
    percent, uncovered = compute_diff_coverage(changed, covered, measured)

    assert percent == 100.0
    assert uncovered == {}


def test_diff_coverage_ignores_non_python_files(tmp_path: Path) -> None:
    coverage_xml = _write_coverage(tmp_path, "src/self_constrained_control/example.py", lines=[1])
    covered, measured = load_coverage_map(coverage_xml, tmp_path)
    diff_text = (
        "diff --git a/README.md b/README.md\n"
        "--- a/README.md\n"
        "+++ b/README.md\n"
        "@@ -1,0 +1,1 @@\n"
        "+change\n"
    )
    changed = parse_unified_diff(diff_text)
    percent, uncovered = compute_diff_coverage(changed, covered, measured)

    assert percent == 100.0
    assert uncovered == {}


def test_diff_coverage_ignores_tests(tmp_path: Path) -> None:
    coverage_xml = _write_coverage(tmp_path, "src/self_constrained_control/example.py", lines=[1])
    covered, measured = load_coverage_map(coverage_xml, tmp_path)
    diff_text = (
        "diff --git a/tests/test_new.py b/tests/test_new.py\n"
        "--- a/tests/test_new.py\n"
        "+++ b/tests/test_new.py\n"
        "@@ -0,0 +1,1 @@\n"
        "+assert True\n"
    )
    changed = parse_unified_diff(diff_text)
    percent, uncovered = compute_diff_coverage(changed, covered, measured)

    assert percent == 100.0
    assert uncovered == {}


def test_normalize_path_outside_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside_file = tmp_path / "outside" / "file.py"
    outside_file.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_path(str(outside_file), repo_root)

    assert normalized == outside_file.resolve().as_posix()


def test_normalize_path_strips_patch_prefix(tmp_path: Path) -> None:
    repo_root = tmp_path
    target = repo_root / "src" / "file.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# sample\n")

    normalized = _normalize_path("a/src/file.py", repo_root)

    assert normalized == "src/file.py"


def test_main_cli_success(tmp_path: Path, monkeypatch) -> None:
    filename = "src/self_constrained_control/example.py"
    coverage_xml = _write_coverage(tmp_path, filename, lines=[5])
    diff_file = tmp_path / "diff.patch"
    diff_file.write_text(
        "diff --git a/src/self_constrained_control/example.py b/src/self_constrained_control/example.py\n"
        "--- a/src/self_constrained_control/example.py\n"
        "+++ b/src/self_constrained_control/example.py\n"
        "@@ -3,0 +5,1 @@\n"
        "+line\n"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diff_coverage.py",
            "--coverage",
            str(coverage_xml),
            "--diff",
            str(diff_file),
            "--threshold",
            "95",
            "--repo-root",
            str(tmp_path),
        ],
    )

    exit_code = main()
    assert exit_code == 0


def test_main_cli_failure_uses_stdin(tmp_path: Path, monkeypatch, capsys) -> None:
    filename = "src/self_constrained_control/example.py"
    coverage_xml = _write_coverage(tmp_path, filename, lines=[1], zero_hit_lines=[2])
    diff_text = (
        "diff --git a/src/self_constrained_control/example.py b/src/self_constrained_control/example.py\n"
        "--- a/src/self_constrained_control/example.py\n"
        "+++ b/src/self_constrained_control/example.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+first\n"
        "+second\n"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diff_coverage.py",
            "--coverage",
            str(coverage_xml),
            "--threshold",
            "95",
            "--repo-root",
            str(tmp_path),
        ],
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(diff_text))

    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Missing coverage" in captured.err


def test_load_coverage_map_ignores_missing_filename(tmp_path: Path) -> None:
    coverage_xml = tmp_path / "cov.xml"
    coverage_xml.write_text(
        "<?xml version=\"1.0\" ?>\n"
        "<coverage branch-rate=\"0\" line-rate=\"0\" version=\"1.0\">\n"
        "  <packages>\n"
        "    <package name=\"pkg\" branch-rate=\"0\" line-rate=\"0\">\n"
        "      <classes>\n"
        "        <class name=\"cls\" filename=\"\" line-rate=\"0\" branch-rate=\"0\">\n"
        "          <lines>\n"
        "            <line number=\"1\" hits=\"0\"/>\n"
        "          </lines>\n"
        "        </class>\n"
        "      </classes>\n"
        "    </package>\n"
        "  </packages>\n"
        "</coverage>\n"
    )

    covered, measured = load_coverage_map(coverage_xml, tmp_path)

    assert covered == {}
    assert measured == {}


def test_parse_unified_diff_handles_deletions_and_context() -> None:
    diff_text = (
        "diff --git a/src/file.py b/src/file.py\n"
        "--- a/src/file.py\n"
        "+++ b/src/file.py\n"
        "@@ -2,2 +2,1 @@\n"
        "-removed\n"
        " context\n"
        "+added\n"
    )

    changed = parse_unified_diff(diff_text)

    assert changed == {"src/file.py": {3}}


def test_parse_unified_diff_skips_dev_null() -> None:
    diff_text = (
        "diff --git a/src/file.py b/src/file.py\n"
        "--- /dev/null\n"
        "+++ /dev/null\n"
        "@@ -0,0 +0,0 @@\n"
    )

    changed = parse_unified_diff(diff_text)

    assert changed == {}


def test_compute_diff_coverage_skips_unmeasured_files() -> None:
    percent, uncovered = compute_diff_coverage({"src/extra.py": {1}}, {}, {})

    assert percent == 100.0
    assert uncovered == {}


def test_entrypoint_runs_main(tmp_path: Path, monkeypatch) -> None:
    filename = "src/self_constrained_control/example.py"
    coverage_xml = _write_coverage(tmp_path, filename, lines=[1])
    diff_file = tmp_path / "diff.patch"
    diff_file.write_text(
        "diff --git a/src/self_constrained_control/example.py b/src/self_constrained_control/example.py\n"
        "--- a/src/self_constrained_control/example.py\n"
        "+++ b/src/self_constrained_control/example.py\n"
        "@@ -0,0 +1,1 @@\n"
        "+line\n"
    )

    exit_calls: list[int] = []
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diff_coverage.py",
            "--coverage",
            str(coverage_xml),
            "--diff",
            str(diff_file),
            "--repo-root",
            str(tmp_path),
        ],
    )
    monkeypatch.setattr(sys, "exit", lambda code=0: exit_calls.append(code))
    sys.modules.pop("scripts.diff_coverage", None)
    runpy.run_module("scripts.diff_coverage", run_name="__main__")

    assert exit_calls and exit_calls[-1] == 0
