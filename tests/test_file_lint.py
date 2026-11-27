"""Portable read-only local and remote lint workflow contracts."""
from types import SimpleNamespace as NS
import stat

import pytest

from hpc_gui.services import file_lint
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.lint.models import Severity


def catalog():
    tool = NS(plugin_id="org.test", title="Test", version="1")
    return file_lint.LintCatalog((), ((tool, frozenset({".jou"})),))


def test_local_recursive_snapshot_and_explicit_unsupported(tmp_path):
    (tmp_path / "a.jou").write_text("journal", encoding="utf-8")
    (tmp_path / "other.txt").write_text("ignore", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.jou").write_text("other", encoding="utf-8")
    docs = file_lint.collect_documents([(str(tmp_path), True)], catalog())
    assert {d.text for d in docs} == {"journal", "other"}
    assert (tmp_path / "a.jou").read_text() == "journal"
    with pytest.raises(ValueError, match="No installed lint"):
        file_lint.collect_documents([(str(tmp_path / "other.txt"), False)], catalog())


def test_local_selection_limits_and_cancel(tmp_path, monkeypatch):
    (tmp_path / "a.jou").write_text("a", encoding="utf-8")
    (tmp_path / "b.jou").write_text("b", encoding="utf-8")
    monkeypatch.setattr(file_lint, "MAX_FILES", 1)
    with pytest.raises(ValueError, match="exceeds 1"):
        file_lint.collect_documents([(str(tmp_path), True)], catalog())
    with pytest.raises(file_lint.FileLintCancelled):
        file_lint.collect_documents([(str(tmp_path), True)], catalog(), current=lambda: False)


class Remote:
    def __init__(self):
        self.reads = []
        self.entries = [RemoteEntry("a.jou", "/job/a.jou", False, 2, mode=stat.S_IFREG),
                        RemoteEntry("link.jou", "/job/link.jou", False, 2, mode=stat.S_IFLNK)]
    def is_dir(self, path):
        return path == "/job"
    def iterdir_entries(self, path):
        assert path == "/job"
        yield from self.entries
    def stat(self, path):
        return 2, 0
    def read_text(self, path):
        self.reads.append(path)
        return "ok"


def test_remote_folder_only_reads_supported_regular_children():
    files = Remote()
    docs = file_lint.collect_documents([("/job", True)], catalog(), files=files)
    assert [d.path for d in docs] == ["/job/a.jou"]
    assert files.reads == ["/job/a.jou"]


def test_remote_listing_escape_rejected_before_read():
    files = Remote()
    files.entries = [RemoteEntry("a.jou", "/elsewhere/a.jou", False, 1)]
    with pytest.raises(ValueError, match="listing mismatch"):
        file_lint.collect_documents([("/job", True)], catalog(), files=files)
    assert files.reads == []


def test_grouped_findings_and_engine_failure(monkeypatch):
    def lint(tool, text, file_name):
        if text == "bad":
            raise RuntimeError("engine broken")
        diag = NS(code="W1", severity=NS(value="warning"), message="finding",
                  line=2, column=1, explanation="why", suggested_fix="fix", source_url="https://example.test")
        return NS(diagnostics=[diag], detection=NS(product="fluent", detected_version="25.2"))
    monkeypatch.setattr("hpc_gui.plugins.linter_tools.lint_text_with_tool_for", lint)
    docs = (file_lint.Document("/job/a.jou", "ok"), file_lint.Document("/job/b.jou", "bad"))
    run = file_lint.lint_documents(docs, catalog())
    assert run.files[0].summary["warning"] == 1
    assert run.files[0].diagnostics[0].suggested_fix == "fix"
    assert run.files[0].detection.product == "fluent"
    assert run.files[1].diagnostics[0].severity == Severity.ERROR
    assert "engine broken" in run.files[1].diagnostics[0].message
    assert len(catalog().common_tools(docs)) == 1



def test_scan_limit_counts_skipped_remote_entries(monkeypatch):
    files = Remote()
    files.entries = [RemoteEntry(f"link{i}", f"/job/link{i}", False, 1, mode=stat.S_IFLNK)
                     for i in range(10)]
    monkeypatch.setattr(file_lint, "MAX_SCAN_ENTRIES", 4)
    with pytest.raises(ValueError, match="discovery exceeds 4"):
        file_lint.collect_documents([("/job", True)], catalog(), files=files)
    assert files.reads == []
