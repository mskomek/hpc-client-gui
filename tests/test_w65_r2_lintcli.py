"""W65r2 F3: standalone Linter CLI + suppression policy (G38)."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from hpc_gui.plugins.openfoam_lint import api, cli
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


def test_cli_counts_match_gui_positions(tmp_path, capsys):
    target = tmp_path / "controlDict"
    text = "FoamFile\n{\n    version 2.0;\n}\n"
    target.write_text(text, encoding="utf-8")
    gui = api.lint_text(str(target), text)
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
