"""W65 security: untrusted case shell scripts are reported, never executed."""
from __future__ import annotations

import builtins
import io
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.openfoam_core.cancellation import ScanCancelledError
from hpc_gui.plugin_engines.openfoam_lint.api import lint_paths, rule_catalog
from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path
from hpc_gui.plugin_engines.openfoam_lint.shell_scripts import shell_script_findings


def _case(tmp_path, script_name: str, body: str = "touch EXECUTED_MARKER\n"):
    case = tmp_path / "case"
    system = case / "system"
    system.mkdir(parents=True)
    (system / "controlDict").write_text("application icoFoam\n", encoding="utf-8")
    (case / script_name).write_text(body, encoding="utf-8")
    return case


def _reported(result):
    return [d.path for d in result.diagnostics if d.rule_id == "OF-SEC-005"]


def test_allrun_presence_is_warned_without_execution(tmp_path):
    case = _case(tmp_path, "Allrun")

    result = lint_paths([str(case)])

    assert _reported(result) == ["Allrun"]
    warning = [d for d in result.diagnostics if d.rule_id == "OF-SEC-005"][0]
    assert warning.severity == "warning"
    assert warning.verification_level == "contextual"
    assert not (case / "EXECUTED_MARKER").exists()


def test_case_variant_names_are_reported(tmp_path):
    case = _case(tmp_path, "allrun")
    (case / "AllClean").write_text("rm -rf ./*\n", encoding="utf-8")

    result = lint_paths([str(case)])

    assert _reported(result) == ["AllClean", "allrun"]


def test_allclean_variants_are_reported_in_stable_order(tmp_path):
    case = _case(tmp_path, "Allrun.pre")
    (case / "Allclean").write_text("rm -rf ./*\n", encoding="utf-8")
    (case / "Allrun").write_text("echo run\n", encoding="utf-8")

    result = lint_paths([str(case)])

    assert _reported(result) == ["Allclean", "Allrun", "Allrun.pre"]
    assert not (case / "EXECUTED_MARKER").exists()


def test_case_without_shell_scripts_has_no_security_script_warning(tmp_path):
    case = tmp_path / "plain"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application icoFoam\n", encoding="utf-8")

    result = lint_paths([str(case)])

    assert _reported(result) == []


def test_directory_named_allrun_is_not_reported(tmp_path):
    case = tmp_path / "dirlike"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application icoFoam\n", encoding="utf-8")
    (case / "Allrun").mkdir()

    result = lint_paths([str(case)])

    assert _reported(result) == []


def test_script_contents_are_never_opened(tmp_path, monkeypatch):
    case = _case(tmp_path, "Allrun")
    script = case / "Allrun"
    real_path_open = Path.open
    real_builtin_open = builtins.open
    real_os_open = os.open

    def guarded_path_open(self, *args, **kwargs):
        if self == script:
            raise AssertionError("lint opened the case script")
        return real_path_open(self, *args, **kwargs)

    def guarded_builtin_open(file, *args, **kwargs):
        if Path(str(file)) == script:
            raise AssertionError("lint opened the case script")
        return real_builtin_open(file, *args, **kwargs)

    def guarded_os_open(path, *args, **kwargs):
        if Path(str(path)) == script:
            raise AssertionError("lint opened the case script")
        return real_os_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_path_open)
    monkeypatch.setattr(builtins, "open", guarded_builtin_open)
    monkeypatch.setattr(io, "open", guarded_builtin_open)
    monkeypatch.setattr(os, "open", guarded_os_open)

    result = lint_paths([str(case)])

    assert _reported(result) == ["Allrun"]


def test_symlinked_script_is_not_followed(tmp_path):
    case = tmp_path / "linked"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application icoFoam\n", encoding="utf-8")
    target = tmp_path / "outside.sh"
    target.write_text("touch EXECUTED_MARKER\n", encoding="utf-8")
    try:
        (case / "Allrun").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted in this environment")

    result = lint_paths([str(case)])

    assert _reported(result) == []
    assert not (tmp_path / "EXECUTED_MARKER").exists()


def test_more_than_eight_scripts_are_capped_with_a_summary(tmp_path):
    case = tmp_path / "many"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application icoFoam\n", encoding="utf-8")
    for index in range(10):
        (case / f"Allrun.step{index}").write_text("echo step\n", encoding="utf-8")

    result = lint_paths([str(case)])

    reported = [d for d in result.diagnostics if d.rule_id == "OF-SEC-005"]
    assert len(reported) == 9
    summary = [d for d in reported if d.path == "<scripts:cap>"]
    assert len(summary) == 1
    assert "10 untrusted" in summary[0].message


def test_listing_error_keeps_matches_already_found(tmp_path, monkeypatch):
    case = tmp_path / "broken"
    (case / "system").mkdir(parents=True)

    class Entry:
        name = "Allrun"

        @staticmethod
        def is_symlink():
            return False

        @staticmethod
        def is_junction():
            return False

        @staticmethod
        def is_file():
            return True

    class BrokenListing:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def __iter__(self):
            return self

        def __next__(self):
            if not getattr(self, "yielded", False):
                self.yielded = True
                return Entry()
            raise OSError("listing failed mid-way")

    import hpc_gui.plugin_engines.openfoam_lint.shell_scripts as module

    monkeypatch.setattr(module.os, "scandir", lambda _root: BrokenListing())

    findings = shell_script_findings(case)

    paths = [item.path for item in findings]
    assert "Allrun" in paths
    assert "<scripts:limit>" in paths


def test_cancellation_stops_the_script_scan(tmp_path):
    case = _case(tmp_path, "Allrun")
    calls = {"count": 0}

    class CancelAfterFirstEntry:
        def is_set(self):
            calls["count"] += 1
            return calls["count"] >= 2

    with pytest.raises(ScanCancelledError):
        shell_script_findings(case, CancelAfterFirstEntry())


def test_rule_catalog_documents_the_new_rule():
    metadata = rule_catalog()["OF-SEC-005"]
    assert metadata["title"] == "Untrusted shell script"
    assert metadata["severity"] == "warning"
    assert metadata["confidence"] == "certain"
    assert metadata["verification_level"] == "contextual"


class _RemoteCase:
    """Minimal read-only SFTP adapter for /case with system/controlDict."""

    CONTROL = b"application icoFoam;\n"

    def __init__(self, extra=None):
        self.extra = dict(extra or {})

    def _mode(self, path):
        if path in ("/", "/case", "/case/system"):
            return stat.S_IFDIR | 0o755
        if path in self.extra:
            return self.extra[path]
        if path == "/case/system/controlDict":
            return stat.S_IFREG | 0o644
        if path == "/case/Allrun":
            return stat.S_IFREG | 0o755
        raise OSError(path)

    def lstat_entry(self, path):
        return SimpleNamespace(mode=self._mode(path), size=len(self.CONTROL))

    def stat(self, path):
        self._mode(path)
        return len(self.CONTROL), 0

    def listdir(self, path):
        if path == "/case":
            return ["system", *self.extra.get("<case-extra>", []), "Allrun"]
        if path == "/case/system":
            return ["controlDict"]
        raise OSError(path)

    def download(self, remote, local):
        if remote != "/case/system/controlDict":
            raise OSError(remote)
        Path(local).write_bytes(self.CONTROL)


def test_remote_case_reports_allrun_from_listing():
    result = lint_remote_path("/case", _RemoteCase())

    reported = [d for d in result.diagnostics if d.rule_id == "OF-SEC-005"]
    assert [d.path for d in reported] == ["/case/Allrun"]
    assert reported[0].verification_level == "contextual"


def test_remote_case_skips_symlinked_script():
    class Linked(_RemoteCase):
        def listdir(self, path):
            if path == "/case":
                return ["system", "Allrun"]
            return super().listdir(path)

        def _mode(self, path):
            if path == "/case/Allrun":
                return stat.S_IFLNK | 0o777
            return super()._mode(path)

    result = lint_remote_path("/case", Linked())

    assert [d for d in result.diagnostics if d.rule_id == "OF-SEC-005"] == []


def test_remote_case_without_scripts_has_no_warning():
    class Plain(_RemoteCase):
        def listdir(self, path):
            if path == "/case":
                return ["system"]
            return super().listdir(path)

    result = lint_remote_path("/case", Plain())

    assert [d for d in result.diagnostics if d.rule_id == "OF-SEC-005"] == []


def test_remote_case_skips_non_regular_script_entry():
    class Fifo(_RemoteCase):
        def listdir(self, path):
            if path == "/case":
                return ["system", "Allrun"]
            return super().listdir(path)

        def _mode(self, path):
            if path == "/case/Allrun":
                return stat.S_IFIFO | 0o600
            return super()._mode(path)

    result = lint_remote_path("/case", Fifo())

    assert [d for d in result.diagnostics if d.rule_id == "OF-SEC-005"] == []


def test_remote_listing_truncation_is_reported(monkeypatch):
    import hpc_gui.plugin_engines.openfoam_lint.remote_case as module

    class Many(_RemoteCase):
        def listdir(self, path):
            if path == "/case":
                return ["system", "Allrun.a", "Allrun.b", "Allrun.c"]
            return super().listdir(path)

        def _mode(self, path):
            if path.startswith("/case/Allrun"):
                return stat.S_IFREG | 0o755
            return super()._mode(path)

    monkeypatch.setattr(module, "MAX_REMOTE_SCRIPT_ENTRIES", 2)

    result = lint_remote_path("/case", Many())

    reported = [d.path for d in result.diagnostics if d.rule_id == "OF-SEC-005"]
    assert "<scripts:limit>" in reported
