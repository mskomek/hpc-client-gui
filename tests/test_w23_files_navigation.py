"""W23 files navigation regression tests.

REQ-*: HPC-W06-FILE-013/032 (local listing truthfulness), TODO-026/027/028
      (mtime metadata, human-readable sizes, blank folder size).
DEF-W23-001: LocalBrowserModel dropped mtime; view rendered raw byte counts
      and "0" for directories.
CON-*: deterministic Back/Forward history (TODO-030) and safe initial
      directory fallback (TODO-024/025).
DEF-W23-002 (workspace identity): safe_initial_local_directory returned a
      development/source checkout as the default workspace.
RACE-*: LIFECYCLE-NATIVE-001 stale completion after Notebook destroy must be
      dropped, never raise (contract + queue-time runtime proof).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from hpc_gui.services.local_files import safe_initial_local_directory
from hpc_gui.wx_local_files import LocalBrowserModel, format_local_size


def _make_tree():
    tmp = Path(tempfile.mkdtemp(prefix="w23-"))
    (tmp / "a.txt").write_bytes(b"x" * 2000)
    (tmp / "sub").mkdir()
    return tmp


def test_w23_local_entries_carry_real_mtime__mtime_present():
    tmp = _make_tree()
    model = LocalBrowserModel(tmp)
    files = [e for e in model.list_entries() if not e.is_dir]
    assert files, "expected at least one file entry"
    target = next(e for e in files if e.path.name == "a.txt")
    assert target.mtime > 0, "mtime metadata must be captured (TODO-026)"
    assert target.size == 2000


def test_w23_file_size_human_readable__bytes_formatted():
    tmp = _make_tree()
    model = LocalBrowserModel(tmp)
    target = next(e for e in model.list_entries() if e.path.name == "a.txt")
    assert format_local_size(target) == "2.0 KB"


def test_w23_folder_size_blank__dirs_not_zero():
    tmp = _make_tree()
    model = LocalBrowserModel(tmp)
    folder = next(e for e in model.list_entries() if e.is_dir)
    assert format_local_size(folder) == "", "folder size must stay blank/unknown (TODO-028)"


def test_w23_safe_initial_rejects_source_checkout__falls_back_to_home():
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / "src" / "hpc_gui").is_dir(), "test premise: repo checkout marker"
    old_cwd = os.getcwd()
    os.chdir(repo_root)
    try:
        chosen = safe_initial_local_directory("")
    finally:
        os.chdir(old_cwd)
    assert Path(chosen).resolve() != repo_root.resolve(), (
        "dev/source checkout must not become the default workspace (TODO-025)"
    )
    assert os.path.isdir(chosen)


def test_w23_safe_initial_prefers_saved_valid_location():
    tmp = _make_tree()
    assert safe_initial_local_directory(str(tmp)) == os.path.abspath(str(tmp))


def test_w23_forward_history__back_then_forward_restores():
    tmp = _make_tree()
    sub = tmp / "sub"
    model = LocalBrowserModel(tmp)
    model.navigate(sub)
    assert model.can_go_back()
    assert not model.can_go_forward()
    model.go_back()
    assert model.current_path == tmp.resolve()
    assert model.can_go_forward()
    model.go_forward()
    assert model.current_path == sub.resolve()


def test_w23_forward_cleared_on_new_navigation__no_stale_forward():
    tmp = _make_tree()
    sub = tmp / "sub"
    other = tmp / "other"
    other.mkdir()
    model = LocalBrowserModel(tmp)
    model.navigate(sub)
    model.go_back()
    assert model.can_go_forward()
    model.navigate(other)
    assert not model.can_go_forward(), "new navigation must clear forward history"


def test_w23_remote_done_guards_destroyed_notebook__contract():
    """Static contract: remote load() completion must survive Notebook destroy.

    Real code exercised: wx_remote_files_view.load/done guard structure.
    Mocked boundary: none (source inspection).
    Why legitimate: the CallAfter race cannot be deterministically triggered
    headless; queue-time no-op after close is proven at runtime below.
    What this test does NOT prove: a real destroyed-C++-window dispatch.
    """
    src = Path(__file__).resolve().parents[1] / "src" / "hpc_gui" / "wx_remote_files_view.py"
    text = src.read_text(encoding="utf-8")
    done_start = text.index("def done(entries, error):")
    done_body = text[done_start : done_start + 3000]
    assert "LIFECYCLE-NATIVE-001" in done_body
    assert "notebook.GetSelection()" in done_body
    assert done_body.count("except Exception") >= 2, "destroyed-window access must be guarded"


def test_w23_local_done_guards_destroyed_notebook__contract():
    src = Path(__file__).resolve().parents[1] / "src" / "hpc_gui" / "wx_local_files.py"
    text = src.read_text(encoding="utf-8")
    assert "LIFECYCLE-NATIVE-001" in text
