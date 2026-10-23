"""One editable journal page hosted inside the application's wx event loop."""

from __future__ import annotations

import difflib
from threading import Thread

from hpc_gui.core.i18n import t
from hpc_gui.journal_studio.document import JournalDocument
from hpc_gui.journal_studio.models import JournalDiagnostic, ParsedJournal
from hpc_gui.journal_studio.parser import parse_journal
from hpc_gui.services.journal_studio_files import save_local, save_remote
from hpc_gui.wx_journal_studio_editor_view import build_editor_view


MAX_VISUAL_STRUCTURE_LINES = 10_000


def _display_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class JournalEditorPage:
    def __init__(self, parent, document: JournalDocument, *, session_state, registry, mode="solution", language="tui"):
        import wx

        self.wx = wx
        self.page = wx.Panel(parent)
        self.document = document
        self.session_state = session_state
        self.registry = registry
        session = session_state.get("session") or {}
        self.files_backend = session.get("files") if document.remote else None
        self.mode = mode
        self.language = language
        self._source_model_at_render = document.text
        self._source_text_at_render = _display_text(document.text)
        self._undo_text: list[str] = []
        self._redo_text: list[str] = []
        build_editor_view(self)
        self._render_source()
        self._refresh_blocks()
        self._refresh_status()

    def _make_source_control(self, parent):
        wx = self.wx
        try:
            import wx.stc as stc

            control = stc.StyledTextCtrl(parent, style=wx.TE_MULTILINE)
            control.SetCodePage(stc.STC_CP_UTF8)
            control.SetMarginType(0, stc.STC_MARGIN_NUMBER)
            control.SetMarginWidth(0, 44)
            control.SetUseTabs(False)
            control.SetTabWidth(2)
            control.SetLexer(stc.STC_LEX_LISP)
            control.StyleSetForeground(stc.STC_LISP_COMMENT, wx.Colour(80, 130, 80))
            control.StyleSetForeground(stc.STC_LISP_STRING, wx.Colour(160, 90, 50))
            if "\r\n" in self.document.text:
                control.SetEOLMode(stc.STC_EOL_CRLF)
            return control
        except Exception:
            return wx.TextCtrl(parent, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL)

    def _readonly_tab(self, parent):
        return self.wx.TextCtrl(parent, style=self.wx.TE_MULTILINE | self.wx.TE_READONLY | self.wx.HSCROLL)

    def _source_value(self) -> str:
        getter = getattr(self.source, "GetText", None) or getattr(self.source, "GetValue")
        return getter()

    def _set_source_value(self, text: str) -> None:
        self._source_model_at_render = text
        self._source_text_at_render = _display_text(text)
        setter = getattr(self.source, "SetText", None) or getattr(self.source, "SetValue")
        setter(self._source_text_at_render)

    def _render_source(self) -> None:
        self._set_source_value(self.document.text)
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        timer = getattr(self, "_refresh_timer", None)
        if timer is not None:
            timer.Stop()
        self._refresh_timer = self.wx.CallLater(180, self._refresh_after_edit)

    def _source_changed(self, event):
        value = self._source_value()
        if _display_text(value) == self._source_text_at_render:
            self.document.text = self._source_model_at_render
        else:
            newline = self.document.newline
            value = value.replace("\r\n", "\n").replace("\r", "\n")
            self.document.text = value.replace("\n", newline) if newline != "\n" else value
        timer = getattr(self, "_refresh_timer", None)
        if timer is not None:
            timer.Stop()
        self._refresh_timer = self.wx.CallLater(180, self._refresh_after_edit)
        self._refresh_status()
        try:
            event.Skip()
        except Exception:
            pass

    def _refresh_after_edit(self):
        self._refresh_blocks()
        if len(self.document.text) <= 256 * 1024:
            self.diff.SetValue("".join(difflib.unified_diff(
                self.document.saved_text.splitlines(keepends=True),
                self.document.text.splitlines(keepends=True),
                fromfile="saved", tofile="edited",
            )))
            self.preview.SetValue(self.document.text)
        else:
            self.diff.SetValue("Diff preview paused for journals over 256 KiB.")
            self.preview.SetValue(self.document.text[:256 * 1024])

    def _source_caret_changed(self, event):
        try:
            line = self.source.LineFromPosition(self.source.GetCurrentPos()) + 1
            index = next((
                i for i, block in enumerate(self._parsed.blocks)
                if block.line <= line < (self._parsed.blocks[i + 1].line if i + 1 < len(self._parsed.blocks) else 10**12)
            ), -1)
            if index >= 0 and self.structure.GetSelection() != index:
                self.structure.SetSelection(index)
                self._select_block(None)
        except Exception:
            pass
        event.Skip()

    def _refresh_blocks(self):
        text = self.document.text
        line_count = len(text.splitlines())
        if len(text) > 4 * 1024 * 1024 or line_count > MAX_VISUAL_STRUCTURE_LINES:
            message = (
                "Visual structure is paused for journals over 10,000 lines or 4 MiB; "
                "source text remains available."
            )
            self._parsed = ParsedJournal(
                text, (),
                (JournalDiagnostic("visual-limit", message, 1, 1, "info"),),
            )
            self.structure.Set([])
            self.problems.SetValue(message)
            return
        parsed = parse_journal(self.document.text, known_command_paths=frozenset(
            item.get("command_path", "") for item in self.registry.get("commands", [])
        ))
        current = self.structure.GetSelection()
        self._parsed = parsed
        # Freeze: an unfrozen ListBox.Set on MSW costs ~3 s for 9k blocks (measured), freezing ~0.8 s.
        self.structure.Freeze()
        try:
            self.structure.Set([f"{block.line:>5}  {block.kind}: {(block.command_path or self.document.text[block.start:block.end].strip().splitlines()[0][:64] if self.document.text[block.start:block.end].strip() else '')}" for block in parsed.blocks])
        finally:
            self.structure.Thaw()
        if parsed.blocks:
            self.structure.SetSelection(min(max(current, 0), len(parsed.blocks) - 1))
        messages = [f"{item.line}:{item.column}  {item.code}: {item.message}" for item in parsed.diagnostics]
        self.problems.SetValue("\n".join(messages) or "No structural parser diagnostics.")

    def _refresh_status(self):
        origin = "Remote" if self.document.remote else "Local"
        state = t("journal_studio.modified") if self.document.modified else t("journal_studio.saved")
        warning = f" — {self.document.decode_warning}" if self.document.decode_warning else ""
        self.status.SetLabel(f"{origin} | {self.document.encoding} | {self.document.newline.replace(chr(13), 'CR').replace(chr(10), 'LF')} | {state}{warning}")
        if not self.document.modified:
            self.diff.SetValue("No saved changes.")
        self.preview.SetValue(self.document.text[:256 * 1024])

    def _select_block(self, _event):
        index = self.structure.GetSelection()
        if index < 0 or index >= len(self._parsed.blocks):
            return
        block = self._parsed.blocks[index]
        content = self.document.text[block.start:block.end]
        if hasattr(self.source, "PositionFromLine"):
            start = self.source.PositionFromLine(block.line - 1)
            stop_line = self._parsed.blocks[index + 1].line - 1 if index + 1 < len(self._parsed.blocks) else self.source.GetLineCount()
            end = self.source.PositionFromLine(stop_line)
            self.source.SetSelection(start, max(start, end))
            self.source.ShowPosition(start)
        self.inspector.SetValue(
            f"{block.kind}\nLine: {block.line}\nColumn: {block.column}\n"
            f"Path: {block.command_path or '—'}\nVerification: {block.verification_status}\n\n{content}"
        )

    def _populate_library(self):
        query = self.search.GetValue().strip().casefold()
        commands = self.registry.get("commands", [])
        entries = [item for item in commands if query in item.get("command_path", "").casefold()]
        self._library_entries = entries
        self.library.Set([f"{item['command_path']}  [{item['category']}; unverified]" for item in entries[:1000]])

    def _select_command(self, _event):
        index = self.library.GetSelection()
        if index < 0 or index >= len(self._library_entries):
            return
        command = self._library_entries[index]
        self.inspector.SetValue(
            f"{command['command_path']}\nCategory: {command['category']}\n"
            f"Mode: unknown\nParameters: none verified\n"
            f"Status: {command['verification_status']}\n\n{t('journal_studio.unverified')}"
        )

    def insert_selected_command(self):
        if self.language != "tui":
            self.wx.MessageBox("The catalog contains TUI paths only. Select TUI before inserting a command.", t("journal_studio.insert_command"), self.wx.OK | self.wx.ICON_WARNING, self.page)
            return False
        index = self.library.GetSelection()
        if index < 0 or index >= len(self._library_entries):
            return False
        prompt = t("journal_studio.unverified") + "\n\nInsert only the raw TUI path?"
        if self.wx.MessageBox(prompt, t("journal_studio.insert_command"), self.wx.YES_NO | self.wx.ICON_WARNING, self.page) != self.wx.YES:
            return False
        command = self._library_entries[index]["command_path"]
        newline = self.document.newline
        insert = command + newline
        self._push_undo()
        text = self.document.text
        separator = "" if not text or text.endswith(("\n", "\r")) else newline
        self.document.text = text + separator + insert
        self._render_source()
        self._refresh_blocks()
        self._refresh_status()
        self.validation.SetValue(t("journal_studio.unverified"))
        return True

    def add_comment(self):
        newline = self.document.newline
        self._push_undo()
        self.document.text += ("" if not self.document.text or self.document.text.endswith(("\n", "\r")) else newline) + "; " + newline
        self._render_source()
        self._refresh_blocks()
        self._refresh_status()

    def _push_undo(self):
        self._undo_text.append(self.document.text)
        del self._undo_text[:-100]
        self._redo_text.clear()

    def _move(self, direction: int):
        index = self.structure.GetSelection()
        target = index + direction
        if index < 0 or target < 0 or target >= len(self._parsed.blocks):
            return
        if self.wx.MessageBox(t("journal_studio.reorder_warning"), t("journal_studio.flow"), self.wx.YES_NO | self.wx.ICON_WARNING, self.page) != self.wx.YES:
            return
        order = list(range(len(self._parsed.blocks)))
        order[index], order[target] = order[target], order[index]
        self._push_undo()
        self.document.text = self._parsed.reorder(tuple(order))
        self._render_source()
        self._refresh_blocks()
        self.structure.SetSelection(target)
        self._refresh_status()

    def _delete(self):
        index = self.structure.GetSelection()
        if index < 0 or index >= len(self._parsed.blocks):
            return
        if self.wx.MessageBox(t("journal_studio.delete_warning"), t("journal_studio.delete"), self.wx.YES_NO | self.wx.ICON_WARNING, self.page) != self.wx.YES:
            return
        block = self._parsed.blocks[index]
        self._push_undo()
        self.document.text = self.document.text[:block.start] + self.document.text[block.end:]
        self._render_source()
        self._refresh_blocks()
        self._refresh_status()

    def _duplicate(self):
        index = self.structure.GetSelection()
        if index < 0 or index >= len(self._parsed.blocks):
            return
        block = self._parsed.blocks[index]
        original = self.document.text[block.start:block.end]
        self._push_undo()
        self.document.text = self.document.text[:block.end] + original + self.document.text[block.end:]
        self._render_source()
        self._refresh_blocks()
        self._refresh_status()

    def save(self):
        value = self._source_value()
        if _display_text(value) == self._source_text_at_render:
            self.document.text = self._source_model_at_render
        else:
            normalized = value.replace("\r\n", "\n").replace("\r", "\n")
            self.document.text = normalized.replace("\n", self.document.newline) if self.document.newline != "\n" else normalized
        if not self.document.path:
            return False
        try:
            payload = self.document.to_bytes()
        except ValueError as exc:
            self.status.SetLabel(str(exc))
            return False
        saved_text = self.document.text
        self.status.SetLabel(t("journal_studio.saved") + "…")

        def worker():
            try:
                if self.document.remote:
                    digest = save_remote(self.files_backend, self.document.path, payload, expected_sha256=self.document.expected_sha256)
                else:
                    digest = save_local(self.document.path, payload, expected_sha256=self.document.expected_sha256)
                self.wx.CallAfter(self._save_done, payload, saved_text, digest, None)
            except Exception as exc:
                self.wx.CallAfter(self._save_done, payload, saved_text, None, str(exc))

        Thread(target=worker, daemon=True).start()
        return True

    def undo_flow(self):
        if not self._undo_text:
            return False
        self._redo_text.append(self.document.text)
        self.document.text = self._undo_text.pop()
        self._render_source()
        self._refresh_blocks()
        self._refresh_status()
        return True

    def undo(self):
        can_undo = getattr(self.source, "CanUndo", None)
        if callable(can_undo) and can_undo():
            self.source.Undo()
            return True
        return self.undo_flow()

    def redo_flow(self):
        if not self._redo_text:
            return False
        self._undo_text.append(self.document.text)
        self.document.text = self._redo_text.pop()
        self._render_source()
        self._refresh_blocks()
        self._refresh_status()
        return True

    def redo(self):
        can_redo = getattr(self.source, "CanRedo", None)
        if callable(can_redo) and can_redo():
            self.source.Redo()
            return True
        return self.redo_flow()

    def _save_done(self, payload, saved_text, digest, error):
        if error:
            self.status.SetLabel(error)
            return
        self.document.mark_saved(payload, saved_text=saved_text)
        self._refresh_status()

    def validate(self):
        source = self.document.text
        name = self.document.path or "untitled.jou"
        self.validation.SetValue(t("journal_studio.static_only") + "\nRunning installed ANSYS linter…")

        def worker():
            try:
                from hpc_gui.plugins.linter_tools import lint_text_with_tool

                result = lint_text_with_tool(source, file_name=name)
                lines = [t("journal_studio.static_only"), f"Detected: {result.detection.product} / {result.detection.dialect}"]
                lines.extend(
                    f"{item.line or 0}:{item.column or 0} {item.severity.value} {item.code} [{item.confidence.value}] — {item.message}"
                    for item in result.sorted_diagnostics()
                )
                if not result.diagnostics:
                    lines.append("No static diagnostics.")
                payload = "\n".join(lines)
            except Exception as exc:
                payload = f"{t('journal_studio.no_linter')}\n{exc}"
            self.wx.CallAfter(self.validation.SetValue, payload)

        Thread(target=worker, daemon=True).start()
