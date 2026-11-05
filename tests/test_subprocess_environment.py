"""Regression tests for inherited runtime paths in test subprocesses."""

import os

from support.subprocess_environment import project_python_environment


def test_project_python_environment_keeps_runtime_and_adds_sources(tmp_path):
    root = tmp_path / "checkout"
    runtime = tmp_path / "wx-runtime"
    environment = project_python_environment(
        root,
        {"PATH": "system-path", "PYTHONPATH": os.pathsep.join((str(runtime), "src"))},
    )

    paths = environment["PYTHONPATH"].split(os.pathsep)
    assert paths[0] == str((root / "src").resolve())
    assert str(runtime) in paths
    assert sum(os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(root / "src")) for path in paths) == 1
    assert environment["PATH"] == "system-path"
