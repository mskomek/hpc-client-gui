"""W65 SFTP-014: remote lint through the shipped SSH backend over real SFTP."""
from __future__ import annotations

import os

from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path
from sftp_harness_support import ROOT_ENV, remote_backend, serve


def _case(tmp_path, *, stale_surface: bool, with_allrun: bool, broken: bool):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    control = "application icoFoam" if broken else "application icoFoam;"
    (case / "system" / "controlDict").write_text(control + "\n", encoding="utf-8")
    (case / "0").mkdir()
    (case / "0" / "U").write_text("dimensions [0 1 -1 0 0 0 0];\n", encoding="utf-8")
    (case / "0" / "p").write_text("dimensions [0 2 -2 0 0 0 0];\n", encoding="utf-8")
    if with_allrun:
        (case / "Allrun").write_text("echo run\n", encoding="utf-8")
    mesh = case / "constant" / "polyMesh"
    mesh.mkdir(parents=True)
    points = mesh / "points"
    points.write_text("0\n", encoding="utf-8")
    surface = case / "constant" / "triSurface"
    surface.mkdir()
    body = surface / "body.stl"
    body.write_text("solid body\n", encoding="utf-8")
    if stale_surface:
        os.utime(points, (1_900_000_000, 1_900_000_000))
        os.utime(body, (2_000_000_000, 2_000_000_000))
    else:
        os.utime(body, (1_900_000_000, 1_900_000_000))
        os.utime(points, (2_000_000_000, 2_000_000_000))
    return case


def test_remote_lint_through_shipped_backend(tmp_path, monkeypatch):
    case = _case(tmp_path, stale_surface=True, with_allrun=True, broken=True)
    monkeypatch.setenv(ROOT_ENV, str(case))
    with serve() as port, remote_backend(port) as backend:
        result = lint_remote_path("/", backend)

    ids = {d.rule_id for d in result.diagnostics}
    assert "OF-SEC-005" in ids
    assert "OF-CROSS-006" in ids
    assert "/system/controlDict" in result.files_checked
    assert "OF-CASE-001" not in ids
    assert any(rule.startswith("OF-DICT-") for rule in ids)
    assert any(d.path.endswith("Allrun") for d in result.diagnostics if d.rule_id == "OF-SEC-005")


def test_clean_remote_case_has_no_findings(tmp_path, monkeypatch):
    case = _case(tmp_path, stale_surface=False, with_allrun=False, broken=False)
    monkeypatch.setenv(ROOT_ENV, str(case))
    with serve() as port, remote_backend(port) as backend:
        result = lint_remote_path("/", backend)

    ids = {d.rule_id for d in result.diagnostics}
    assert "OF-SEC-005" not in ids
    assert "OF-CROSS-006" not in ids
    assert "/system/controlDict" in result.files_checked
