"""Wave 2 — Directories / Local Files Feature Parity and Unicode.

Make the new Directories local pane genuinely usable, including context menus,
pane operations, clear ergonomics, and full Unicode-safe wx→filesystem→UI
integration.
"""

from __future__ import annotations
from support.test_wave2_directories_local_files_shared import (
    pathlib,
    pytest,
    sys,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

class TestCRUDActions:
    pytestmark = pytest.mark.unit

    """Verify file operations with Unicode paths."""

    def test_create_directory_unicode(self, tmp_path):
        """Creating a Unicode-named directory should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)
        model.new_folder("İşler_Çağrı")

        target = tmp_path / "İşler_Çağrı"
        assert target.is_dir()

    def test_create_file_unicode(self, tmp_path):
        """Creating a Unicode-named file should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)
        # Create directory first
        model.new_folder("研究")
        target_dir = tmp_path / "研究"

        # Create file inside
        test_file = target_dir / "計算結果.txt"
        test_file.write_text("content", encoding="utf-8")
        assert test_file.exists()

    def test_rename_unicode_roundtrip(self, tmp_path):
        """Rename should preserve Unicode names through roundtrip."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create initial file
        initial = tmp_path / "result.txt"
        initial.write_text("test", encoding="utf-8")

        # Rename chain: result.txt → sonuç.txt → ölçüm_日本語.txt → 研究_İstanbul.txt → result.txt
        rename_chain = [
            "sonuç.txt",
            "ölçüm_日本語.txt",
            "研究_İstanbul.txt",
            "result.txt",
        ]

        current_name = "result.txt"
        for new_name in rename_chain:
            old_path = tmp_path / current_name
            model.rename(old_path, new_name)
            new_path = tmp_path / new_name
            assert new_path.exists(), f"Rename to {new_name!r} failed"
            assert not old_path.exists(), f"Old file {current_name!r} still exists"
            current_name = new_name

    def test_delete_unicode_file(self, tmp_path):
        """Deleting a Unicode-named file should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create Unicode-named file
        test_file = tmp_path / "★_Favorites.txt"
        test_file.write_text("test", encoding="utf-8")
        assert test_file.exists()

        # Delete it
        model.delete([test_file])
        assert not test_file.exists()

    def test_delete_unicode_directory(self, tmp_path):
        """Deleting a Unicode-named directory should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create Unicode-named directory with content
        test_dir = tmp_path / "Türkçe_日本語"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test", encoding="utf-8")

        # Delete it (delete only removes empty dirs, so delete file first)
        model.delete([(test_dir / "file.txt")])
        model.delete([test_dir])
        assert not test_dir.exists()

class TestContextMenus:
    pytestmark = pytest.mark.unit

    """Verify context menus are fully wired with Unicode support."""

    def test_context_actions_for_file(self):
        """Context actions should include expected items for files."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path="/tmp/test.txt",
            clicked_is_dir=False,
            selected_paths=("/tmp/test.txt",),
            selected_types=(False,),
        )
        actions = visible_actions(selection, remote=False)
        assert "open" in actions
        assert "rename" in actions
        assert "copy" in actions
        assert "cut" in actions
        assert "delete" in actions
        assert "copy_path" in actions

    def test_context_actions_for_directory(self):
        """Context actions should include expected items for directories."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path="/tmp/test_dir",
            clicked_is_dir=True,
            selected_paths=("/tmp/test_dir",),
            selected_types=(True,),
        )
        actions = visible_actions(selection, remote=False)
        assert "open" in actions
        assert "new_folder" in actions
        assert "copy" in actions
        assert "cut" in actions
        assert "delete" in actions
        assert "copy_path" in actions

    def test_context_actions_background(self):
        """Context actions for background should include paste and refresh."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path=None,
            clicked_is_dir=None,
            background=True,
        )
        actions = visible_actions(selection, remote=False)
        assert "new_folder" in actions
        assert "paste" in actions
        assert "refresh" in actions

    def test_context_actions_multi_select(self):
        """Context actions for multi-select should include bulk operations."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path="/tmp/a.txt",
            clicked_is_dir=False,
            selected_paths=("/tmp/a.txt", "/tmp/b.txt", "/tmp/c.txt"),
            selected_types=(False, False, False),
        )
        actions = visible_actions(selection, remote=False)
        assert "copy" in actions
        assert "cut" in actions
        assert "delete" in actions
        assert "copy_path" in actions
        # Should NOT include open, rename (single-item only)
        assert "open" not in actions
        assert "rename" not in actions

class TestClipboardOperations:
    """Verify clipboard operations preserve Unicode."""

    @pytest.mark.unit
    def test_copy_paste_unicode_file(self, tmp_path):
        """Copy/paste should preserve Unicode file names."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create source file
        src = tmp_path / "source" / "日本語_ファイル.txt"
        src.parent.mkdir()
        src.write_text("content", encoding="utf-8")

        # Copy to destination
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        model.copy([src], move=False)
        model.paste_into(dest_dir, model.clipboard, move=False)

        dest_file = dest_dir / "日本語_ファイル.txt"
        assert dest_file.exists()
        assert dest_file.read_text(encoding="utf-8") == "content"

    @pytest.mark.unit
    def test_cut_paste_unicode_file(self, tmp_path):
        """Cut/paste should preserve Unicode file names and remove source."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create source file
        src = tmp_path / "source" / "İşler_Çağrı.txt"
        src.parent.mkdir()
        src.write_text("content", encoding="utf-8")

        # Cut to destination
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        model.copy([src], move=True)
        model.paste_into(dest_dir, model.clipboard, move=True)

        dest_file = dest_dir / "İşler_Çağrı.txt"
        assert dest_file.exists()
        assert dest_file.read_text(encoding="utf-8") == "content"
        assert not src.exists()

    @pytest.mark.unit
    def test_copy_paste_multiple_unicode_files(self, tmp_path):
        """Copy/paste multiple Unicode files should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create source files
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        files = ["日本語.txt", "Türkçe.txt", "★.txt"]
        for name in files:
            (src_dir / name).write_text("test", encoding="utf-8")

        # Copy all to destination
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        src_paths = [src_dir / name for name in files]
        model.copy(src_paths, move=False)
        model.paste_into(dest_dir, model.clipboard, move=False)

        for name in files:
            assert (dest_dir / name).exists(), f"File {name!r} not pasted"

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_paste_directory_into_itself_is_rejected(self, tmp_path):
        """Pasting a directory into itself must not create recursive copies."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)
        source = tmp_path / "source"
        source.mkdir()
        (source / "payload.txt").write_text("content", encoding="utf-8")
        model.copy([source], move=False)

        with pytest.raises(ValueError, match="cannot paste a directory into itself"):
            model.paste_into(source, model.clipboard, move=False)

        assert (source / "payload.txt").read_text(encoding="utf-8") == "content"
        assert not (source / "source").exists()
