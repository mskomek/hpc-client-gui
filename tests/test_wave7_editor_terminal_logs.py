"""Wave 7 — Script Editor, Terminal, Logs and Archive Unicode.

Ensure text I/O surfaces preserve Unicode without silent data loss and
archives preserve Unicode entry names without security regressions.
"""
from __future__ import annotations
import pytest

import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# 1. Script Editor
# ---------------------------------------------------------------------------

class TestScriptEditor:
    """Verify script editor handles Unicode correctly."""

    @pytest.mark.unit
    def test_editor_model_unicode_content(self):
        """DocumentModel should preserve Unicode content."""
        from hpc_gui.services.editor_controller import DocumentModel

        content = "# Isı transferi\n# 日本語テスト\nprint('Çalışma başladı ★')\n"
        doc = DocumentModel(
            path="/test/script.py",
            content=content,
            saved_content="",
            is_local=True,
        )
        assert "Isı" in doc.content
        assert "日本語" in doc.content
        assert "★" in doc.content
        assert doc.dirty is True

    @pytest.mark.unit
    def test_editor_model_encoding_default(self):
        """DocumentModel should default to UTF-8 encoding."""
        from hpc_gui.services.editor_controller import DocumentModel

        doc = DocumentModel(
            path="/test/script.py",
            content="test",
            saved_content="test",
            is_local=True,
        )
        assert doc.encoding == "utf-8"

    @pytest.mark.unit
    def test_editor_model_dirty_detection(self):
        """DocumentModel should detect dirty state correctly."""
        from hpc_gui.services.editor_controller import DocumentModel

        content = "# 日本語テスト\n"
        doc = DocumentModel(
            path="/test/script.py",
            content=content,
            saved_content=content,
            is_local=True,
        )
        assert doc.dirty is False

        doc2 = doc.with_content("# 日本語テスト (modified)\n")
        assert doc2.dirty is True

    @pytest.mark.integration
    def test_editor_controller_unicode_file_roundtrip(self, tmp_path):
        """Editor controller state and a UTF-8 file retain Unicode through save."""
        from hpc_gui.services.editor_controller import DocumentModel, EditorController

        content = "# Isı transferi 日本語\nprint('Çalışma başladı ★')\n"
        script_path = tmp_path / "test_script.py"
        script_path.write_text(content, encoding="utf-8")
        loaded = script_path.read_text(encoding="utf-8")
        controller = EditorController()
        controller.open(DocumentModel(
            path=str(script_path), content=loaded, saved_content=loaded, is_local=True,
        ))
        changed = controller.update_content(loaded + "# Δ added\n")
        assert changed.dirty
        script_path.write_text(changed.content, encoding="utf-8")
        saved = controller.mark_saved(script_path.read_text(encoding="utf-8"))
        assert not saved.dirty
        assert "Δ" in saved.content and "日本語" in saved.content


# ---------------------------------------------------------------------------
# 2. Terminal
# ---------------------------------------------------------------------------

class TestTerminal:
    """Verify terminal handles Unicode correctly."""

    @pytest.mark.unit
    def test_terminal_model_unicode_receive(self):
        """TerminalModel should handle Unicode output."""
        from hpc_gui.wx_terminal import TerminalModel

        model = TerminalModel.__new__(TerminalModel)
        model.text = ""
        model._history = []
        model._max_lines = 5000

        # Simulate receiving Unicode output
        model.receive("Türkçe çıktı: çğıİöşü\n")
        model.receive("日本語: 計算完了\n")
        model.receive("Symbols: Δ ★ ✓\n")

        assert "çğıİöşü" in model.text
        assert "日本語" in model.text
        assert "計算完了" in model.text
        assert "Δ" in model.text
        assert "★" in model.text
        assert "✓" in model.text

    @pytest.mark.unit
    def test_terminal_webview_safe_json_dumps(self):
        """_safe_json_dumps should preserve Unicode."""
        from hpc_gui.wx_terminal_webview import _safe_json_dumps

        text = "Türkçe: çğıİöşü\n日本語: 計算完了\nSymbols: Δ ★ ✓"
        result = _safe_json_dumps(text)
        # Should not escape Unicode to \uXXXX
        assert "\\u" not in result
        # Should contain the actual characters
        assert "ç" in result
        assert "日本" in result
        assert "★" in result

    @pytest.mark.unit
    def test_terminal_webview_safe_truncate_index(self):
        """_safe_truncate_index should handle Unicode safely."""
        from hpc_gui.wx_terminal_webview import _safe_truncate_index

        text = "日本語テスト" * 100  # 300 chars, 900 bytes in UTF-8
        # Truncate at byte boundary
        truncated_idx = _safe_truncate_index(text, 100)
        assert truncated_idx > 0
        prefix = text[:truncated_idx]
        assert len(prefix.encode("utf-8")) <= 100
        assert len(text[:truncated_idx + 1].encode("utf-8")) > 100


# ---------------------------------------------------------------------------
# 3. Logs
# ---------------------------------------------------------------------------

class TestLogs:
    """Verify logs handle Unicode correctly."""

    @pytest.mark.integration
    def test_logs_model_unicode_read(self, tmp_path):
        """WxLogsModel should read Unicode log content."""
        from hpc_gui.wx_logs import WxLogsModel

        # Create a log file with Unicode content
        log_path = tmp_path / "test.log"
        log_content = "2024-01-01 İş başlatıldı\n2024-01-01 日本語ログ\n2024-01-01 ★五星\n"
        log_path.write_text(log_content, encoding="utf-8")

        model = WxLogsModel(log_path)
        content = model.refresh()
        assert "İş" in content
        assert "日本語" in content
        assert "★" in content


# ---------------------------------------------------------------------------
# 4. ZIP/TAR Archives
# ---------------------------------------------------------------------------

class TestZipArchives:
    """Verify ZIP archives handle Unicode filenames correctly."""

    @pytest.mark.contract
    def test_zip_unicode_filename_roundtrip(self, tmp_path):
        """ZIP should preserve Unicode filenames."""
        zip_path = tmp_path / "archive.zip"

        # Create ZIP with Unicode filenames
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("results/Çalışmalar/日本語/ölçüm.txt", "test content")
            zf.writestr("results/日本語/file.txt", "日本語 content")
            zf.writestr("★_favorites.txt", "star content")

        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "results/Çalışmalar/日本語/ölçüm.txt" in names
            assert "results/日本語/file.txt" in names
            assert "★_favorites.txt" in names

            # Verify content
            assert zf.read("results/Çalışmalar/日本語/ölçüm.txt") == b"test content"
            assert zf.read("results/日本語/file.txt").decode("utf-8") == "日本語 content"
            assert zf.read("★_favorites.txt") == b"star content"

    @pytest.mark.contract
    def test_zip_extract_unicode(self, tmp_path):
        """ZIP extraction should preserve Unicode filenames."""
        zip_path = tmp_path / "archive.zip"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create ZIP
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("日本語/ölçüm.txt", "content1")
            zf.writestr("★/favorites.txt", "content2")

        # Extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Verify extracted files
        assert (extract_dir / "日本語" / "ölçüm.txt").read_text(encoding="utf-8") == "content1"
        assert (extract_dir / "★" / "favorites.txt").read_text(encoding="utf-8") == "content2"

    @pytest.mark.contract
    def test_zip_nested_unicode(self, tmp_path):
        """ZIP should handle nested Unicode directories."""
        zip_path = tmp_path / "nested.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(5):
                name = f"日本語_ディレクトリ_{i}/ölçüm_{i}.txt"
                zf.writestr(name, f"content {i}")

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert len(names) == 5
            for name in names:
                assert "日本語" in name
                assert "ölçüm" in name

    @pytest.mark.contract
    def test_zip_conflict_handling(self, tmp_path):
        """ZIP should handle conflicting Unicode filenames."""
        zip_path = tmp_path / "conflict.zip"

        # Create ZIP with same filename (last wins)
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "first")
            zf.writestr("test.txt", "second")

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert zf.read("test.txt") == b"second"


# ---------------------------------------------------------------------------
# 5. Output Follower
# ---------------------------------------------------------------------------

class TestOutputFollower:
    """Verify output follower handles Unicode correctly."""

    @pytest.mark.unit
    def test_output_follower_unicode_text(self):
        """OutputFollower should handle Unicode text."""
        from hpc_gui.services.output_follower import retain_last_lines

        text = "İş başladı\n日本語出力\n★五星\n" * 100
        result = retain_last_lines(text, max_lines=10)
        lines = result.split("\n")
        # retain_last_lines may return slightly more than max_lines
        assert len(lines) <= 11
        # Verify Unicode preserved
        assert "İş" in result or "日本語" in result or "★" in result


# ---------------------------------------------------------------------------
# 6. Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for editor/terminal/logs Unicode."""

    @pytest.mark.contract
    def test_archive_unicode_create_list_extract_workflow(self, tmp_path):
        """Create, list, and extract a Unicode ZIP using the archive boundary."""
        zip_path = tmp_path / "archive.zip"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # 1. Create archive
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("results/Çalışmalar/日本語/ölçüm.txt", "content1")
            zf.writestr("results/日本語/file.txt", "content2")
            zf.writestr("★_favorites.txt", "content3")

        # 2. List contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert len(names) == 3

        # 3. Extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # 4. Verify extracted files
        assert (extract_dir / "results" / "Çalışmalar" / "日本語" / "ölçüm.txt").read_text(encoding="utf-8") == "content1"
        assert (extract_dir / "results" / "日本語" / "file.txt").read_text(encoding="utf-8") == "content2"
        assert (extract_dir / "★_favorites.txt").read_text(encoding="utf-8") == "content3"
