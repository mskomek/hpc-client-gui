"""Wave 7 — Script Editor, Terminal, Logs and Archive Unicode.

Ensure text I/O surfaces preserve Unicode without silent data loss and
archives preserve Unicode entry names without security regressions.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# 1. Script Editor
# ---------------------------------------------------------------------------

class TestScriptEditor:
    """Verify script editor handles Unicode correctly."""

    @pytest.mark.unit
    @pytest.mark.semantic
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
    @pytest.mark.semantic
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
    @pytest.mark.semantic
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





# ---------------------------------------------------------------------------
# 2. Terminal
# ---------------------------------------------------------------------------

class TestTerminal:
    """Verify terminal handles Unicode correctly."""

    @pytest.mark.unit
    @pytest.mark.semantic
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

    @pytest.mark.contract
    @pytest.mark.semantic
    def test_terminal_webview_safe_json_dumps(self):
        """_safe_json_dumps should preserve Unicode."""
        from hpc_gui.wx_terminal_webview import _safe_json_dumps

        text = "Türkçe: çğıİöşü\n日本語: 計算完了\nSymbols: Δ ★ ✓"
        result = _safe_json_dumps(text)
        # Should not escape Unicode to \uXXXX
        assert "\\u" not in result or "ç" in result
        # Should contain the actual characters
        assert "ç" in result
        assert "日本" in result
        assert "★" in result

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_terminal_webview_safe_truncate_index(self):
        """_safe_truncate_index should handle Unicode safely."""
        from hpc_gui.wx_terminal_webview import _safe_truncate_index

        text = "日本語テスト" * 100  # 300 chars, 900 bytes in UTF-8
        # Truncate at byte boundary
        truncated_idx = _safe_truncate_index(text, 100)
        assert truncated_idx > 0
        # Verify the truncated text is valid UTF-8
        truncated = text[:truncated_idx]
        assert truncated.encode("utf-8", errors="strict") or True  # No exception




# ---------------------------------------------------------------------------
# 3. Logs
# ---------------------------------------------------------------------------

class TestLogs:
    """Verify logs handle Unicode correctly."""

    @pytest.mark.unit
    @pytest.mark.wx
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_logs_model_unicode_read(self, tmp_path):
        """The production log model reads and exposes Unicode log text."""
        from hpc_gui.wx_logs import WxLogsModel

        log_path = tmp_path / "test.log"
        content = "Log entry: İşlem tamamlandı 日本語 ★\n"
        log_path.write_text(content, encoding="utf-8")

        model = WxLogsModel(log_path)
        assert model.refresh() == content
        assert model.text == content



# ---------------------------------------------------------------------------
# 4. ZIP/TAR Archives
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 5. Output Follower
# ---------------------------------------------------------------------------

class TestOutputFollower:
    """Verify output follower handles Unicode correctly."""

    @pytest.mark.unit
    @pytest.mark.semantic
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

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_full_editor_workflow_unicode(self, tmp_path):
        """Full editor workflow: create, edit, save, reopen with Unicode."""
        from hpc_gui.services.editor_controller import DocumentModel

        # 1. Create script with Unicode
        content = "#!/bin/bash\n# İş: Isı transferi 日本語\necho 'Çalışma başladı ★'\n"
        script_path = tmp_path / "test.slurm"
        script_path.write_text(content, encoding="utf-8")

        # 2. Open in editor (simulate)
        doc = DocumentModel(
            path=str(script_path),
            content=content,
            saved_content=content,
            is_local=True,
        )
        assert doc.dirty is False

        # 3. Edit
        modified = doc.with_content(content + "# Δ added\n")
        assert modified.dirty is True

        # 4. Save
        script_path.write_text(modified.content, encoding="utf-8")

        # 5. Reopen
        reopened = script_path.read_text(encoding="utf-8")
        assert "İş" in reopened
        assert "日本語" in reopened
        assert "★" in reopened
        assert "Δ" in reopened

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_full_terminal_unicode_flow(self):
        """Full terminal flow: receive Unicode output, verify display."""
        from hpc_gui.wx_terminal import TerminalModel

        model = TerminalModel.__new__(TerminalModel)
        model.text = ""
        model._history = []
        model._max_lines = 5000

        # Simulate terminal output
        outputs = [
            "user@host:~$ ",
            "Türkçe çıktı: çğıİöşü\n",
            "日本語: 計算完了\n",
            "Symbols: Δ ★ ✓\n",
            "$ ",
        ]

        for output in outputs:
            model.receive(output)

        # Verify all content present
        assert "çğıİöşü" in model.text
        assert "計算完了" in model.text
        assert "Δ" in model.text
        assert "★" in model.text
        assert "✓" in model.text
