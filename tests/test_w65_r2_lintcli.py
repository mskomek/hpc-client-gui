"""W65r2 F3: standalone Linter CLI + suppression policy (G38)."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from hpc_gui.plugins.openfoam_lint import api, cli
from hpc_gui.plugin_engines.openfoam_lint import cli as engine_cli
from hpc_gui.plugins.openfoam_lint.policy import LintPolicy


def test_cli_json_clean_and_error_exit_codes(tmp_path, capsys):
    good = tmp_path / "controlDict"
    good.write_text("FoamFile\n{\n    version 2.0;\n}\n", encoding="utf-8")
    assert cli.main([str(good)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["counts"]["total"] == len(out["diagnostics"])
    bad = tmp_path / "badDict"
    bad.write_text("application simpleFoam\n", encoding="utf-8")  # missing ';' -> OF-DICT-001
    assert cli.main([str(bad)]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["counts"]["error"] >= 1
    assert all({"rule", "severity", "file", "line"} <= set(d) for d in out["diagnostics"])


def test_cli_release_is_explicit_in_result(tmp_path, capsys):
    target = tmp_path / "controlDict"
    target.write_text("application simpleFoam;\n", encoding="utf-8")
    assert cli.main(["--release", "v1912", str(target)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["edition"] == "OpenFOAM.com / ESI"
    assert out["version"] == "v1912"


def test_hpc_gui_cli_release_is_explicit_in_result(tmp_path, capsys):
    target = tmp_path / "controlDict"
    target.write_text("application simpleFoam;\n", encoding="utf-8")
    parser = __import__("argparse").ArgumentParser()
    commands = parser.add_subparsers()
    engine_cli.add_parser(commands)
    args = parser.parse_args([
        "openfoam", "lint", "--release", "v1912", str(target),
        "--format", "json",
    ])
    assert engine_cli.run_lint(args) == 0
    assert '"version": "v1912"' in capsys.readouterr().out


def test_cli_counts_match_gui_positions(tmp_path, capsys):
    target = tmp_path / "controlDict"
    text = "FoamFile\n{\n    version 2.0;\n}\n"
    target.write_text(text, encoding="utf-8")
    gui = api.lint_text(target.name, text)
    assert cli.main([str(target), "--format", "json"]) == (1 if any(
        d.severity == "error" for d in gui) else 0)
    out = json.loads(capsys.readouterr().out)
    assert out["counts"]["total"] == len(gui)
    assert cli.main([str(tmp_path / "missing")]) == 2


def test_policy_disable_severity_suppress():
    policy = LintPolicy()
    diags = api.lint_text("system/controlDict", "key value\n")
    assert diags, "fixture must produce at least one diagnostic"
    rule = diags[0].rule
    policy.disable(rule)
    assert all(d.rule != rule for d in policy.apply(list(diags)))
    policy.enable(rule)
    policy.set_severity(rule, "info")
    assert policy.apply(list(diags))[0].severity == "info"
    first = diags[0]
    policy.suppress(first.rule, path=first.file, line=first.line, reason="accepted for test")
    assert policy.suppressed(first.rule, first.file, first.line) == "accepted for test"
    assert all(not (d.rule == first.rule and d.line == first.line)
               for d in policy.apply(list(diags)))
    with pytest.raises(ValueError):
        policy.suppress(rule, path="", line=1, reason="x")
    with pytest.raises(ValueError):
        policy.suppress(rule, path="f", line=1, reason="  ")
    with pytest.raises(ValueError):
        policy.suppress("OF-NOPE-000", path="f", line=1, reason="x")
    with pytest.raises(ValueError):
        policy.set_severity(rule, "critical")


def test_cli_runs_without_studio_import():
    code = ("import sys; "
            "from hpc_gui.plugins.openfoam_lint import cli; "
            "sys.exit(0 if 'hpc_gui.plugins.openfoam_studio' not in sys.modules else 3)")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env={"PYTHONPATH": "src", "PATH": ""})
    assert proc.returncode == 0, proc.stderr[-500:]


def test_linter_text_rejects_bytes_and_bounds_utf8_size(tmp_path):
    with pytest.raises(TypeError, match="must be str"):
        api.lint_text("system/controlDict", b"FoamFile {}")

    oversized_unicode = "é" * (api.MAX_INPUT_BYTES // 2 + 1)
    with pytest.raises(ValueError, match="exceeds"):
        api.lint_text("system/controlDict", oversized_unicode)

    oversized_file = tmp_path / "oversizedDict"
    oversized_file.write_bytes(b"x" * (api.MAX_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match="exceeds"):
        api.read_text_limited(str(oversized_file))
