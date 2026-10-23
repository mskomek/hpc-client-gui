"""Journal Studio -> Slurm draft UI: action, unsaved block, validation and single hand-off.

Runs the real JournalStudioWorkspace and dialog inside a hidden wx.Frame. Every
submit, upload and ssh-facing backend is a mock; the tests assert none is used.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from hpc_gui.core.i18n import t
from hpc_gui.journal_studio.document import JournalDocument


PLUGIN_ID = "org.hpcclient.ansysjournalstudio"
REGISTRY = {
    "product_id": "fluent",
    "version_id": "25.2",
    "commands": [
        {"command_path": "/file/read-case", "category": "file", "verification_status": "unverified", "mode_scope": "unknown", "parameters": []},
    ],
}
JOURNAL_TEXT = b"/file/read-case \"case.cas\"\n"


def make_plugin(root: Path):
    data = json.dumps(REGISTRY).encode("utf-8")
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "command_registry.json").write_bytes(data)
    record = SimpleNamespace(path="data/command_registry.json", size=len(data), sha256=hashlib.sha256(data).hexdigest())
    return SimpleNamespace(directory=str(root), manifest=SimpleNamespace(id=PLUGIN_ID, files=[record]))


@pytest.fixture(scope="module")
def wx_app():
    import wx

    yield wx.App.Get() or wx.App(False)


@pytest.fixture
def studio(tmp_path, wx_app):
    import wx
    from hpc_gui.core.i18n import load_language
    from hpc_gui.wx_journal_studio import JournalStudioWorkspace

    load_language("en")
    frame = wx.Frame(None, size=(1200, 800))
    frame.CreateStatusBar()
    notebook = wx.Notebook(frame)
    state = {"_embedded_main_notebook": notebook, "session": {}}
    workspace = JournalStudioWorkspace(frame, state, make_plugin(tmp_path / "plugin"))
    yield SimpleNamespace(wx=wx, frame=frame, state=state, ws=workspace, tmp=tmp_path)
    frame.Destroy()


def saved_document(tmp_path: Path, name: str = "run.jou") -> JournalDocument:
    path = tmp_path / name
    path.write_bytes(JOURNAL_TEXT)
    document = JournalDocument.from_bytes(JOURNAL_TEXT, path=str(path), remote=False)
    assert not document.modified
    return document


def make_dialog(studio, document, on_handoff):
    from hpc_gui.wx_journal_slurm_draft_dialog import SlurmDraftDialog

    return SlurmDraftDialog(studio.frame, document, None, on_handoff)


def fill_valid(dialog) -> None:
    values = {
        "partition": "debug",
        "account": "proj-1",
        "job_name": "journal_studio",
        "workdir": "/arf/scratch/user/case",
        "journal_path": "run.jou",
    }
    for name, value in values.items():
        dialog.fields[name].SetValue(value)


def test_toolbar_action_is_present_with_translated_label(studio):
    assert studio.ws.btn_slurm.GetLabel() == t("journal_studio.create_slurm_draft")
    assert "Slurm" in studio.ws.btn_slurm.GetLabel()


def test_unsaved_document_is_blocked_before_dialog_opens(studio, monkeypatch):
    from hpc_gui.journal_studio.document import JournalDocument as Doc

    unsaved = Doc.new(path=str(studio.tmp / "draft.jou"), text=JOURNAL_TEXT.decode("utf-8"))
    studio.ws._add_document(unsaved)
    assert unsaved.modified
    dialog_class = Mock()
    monkeypatch.setattr("hpc_gui.wx_journal_slurm_draft_dialog.SlurmDraftDialog", dialog_class)
    message_box = Mock()
    monkeypatch.setattr(studio.wx, "MessageBox", message_box)

    assert studio.ws.create_slurm_draft() is False

    dialog_class.assert_not_called()
    message_box.assert_called_once()
    assert message_box.call_args.args[0] == t("journal_studio.slurm_unsaved")


def test_no_open_document_is_blocked(studio, monkeypatch):
    dialog_class = Mock()
    monkeypatch.setattr("hpc_gui.wx_journal_slurm_draft_dialog.SlurmDraftDialog", dialog_class)
    monkeypatch.setattr(studio.wx, "MessageBox", Mock())

    assert studio.ws.create_slurm_draft() is False
    dialog_class.assert_not_called()


def test_saved_document_opens_dialog_once(studio, monkeypatch):
    studio.ws._add_document(saved_document(studio.tmp))
    dialog_class = Mock()
    monkeypatch.setattr("hpc_gui.wx_journal_slurm_draft_dialog.SlurmDraftDialog", dialog_class)

    assert studio.ws.create_slurm_draft() is True

    dialog_class.assert_called_once()
    dialog_class.return_value.show_modal.assert_called_once_with()


def test_invalid_input_shows_errors_and_never_hands_off(studio):
    handoff = Mock(return_value=True)
    dialog = make_dialog(studio, saved_document(studio.tmp), handoff)
    try:
        fill_valid(dialog)
        dialog.fields["partition"].SetValue("")
        dialog.fields["cpus_per_task"].SetValue("0")

        assert dialog.generate() is None

        shown = dialog.errors.GetValue()
        assert t("journal_studio.slurm_errors") in shown
        assert "partition is required" in shown
        assert "cpus per task must be between 1 and 128" in shown
        assert dialog.draft is None
        assert dialog.btn_handoff.IsEnabled() is False
        assert dialog.hand_off() is False
        handoff.assert_not_called()
    finally:
        dialog.dialog.Destroy()


def test_valid_input_hands_off_exactly_once_without_submitting(studio):
    slurm, files, ssh = MagicMock(), MagicMock(), MagicMock()
    manager = MagicMock()
    state = {"editor_manager": manager, "session": {"slurm": slurm, "files": files, "ssh": ssh}}
    from hpc_gui.wx_journal_slurm_draft_dialog import open_draft_in_editor

    handoff = Mock(side_effect=lambda path, text: open_draft_in_editor(state, path, text))
    dialog = make_dialog(studio, saved_document(studio.tmp), handoff)
    try:
        fill_valid(dialog)
        draft = dialog.generate()
        assert draft is not None
        assert dialog.errors.GetValue() == ""
        assert dialog.btn_handoff.IsEnabled() is True

        assert dialog.hand_off() is True
        assert dialog.hand_off() is False

        handoff.assert_called_once_with(draft.script_path, draft.script_text)
        manager.open_new_window.assert_called_once_with(draft.script_path, draft.script_text, is_local=False)
        assert draft.script_path == "/arf/scratch/user/case/journal_studio_draft.slurm"
        assert "#SBATCH --partition=debug" in draft.script_text
    finally:
        dialog.dialog.Destroy()
    slurm.assert_not_called()
    assert slurm.method_calls == []
    assert files.method_calls == []
    assert ssh.method_calls == []


def test_handoff_failure_keeps_draft_available_for_retry(studio):
    handoff = Mock(return_value=False)
    dialog = make_dialog(studio, saved_document(studio.tmp), handoff)
    try:
        fill_valid(dialog)
        assert dialog.generate() is not None
        assert dialog.hand_off() is False
        assert dialog.btn_handoff.IsEnabled() is True
        assert dialog.status.GetLabel() == t("journal_studio.slurm_handoff_unavailable")
    finally:
        dialog.dialog.Destroy()


def test_open_draft_in_editor_requires_existing_editor_manager(tmp_path):
    from hpc_gui.wx_journal_slurm_draft_dialog import open_draft_in_editor

    assert open_draft_in_editor({"session": {}}, "/w/x.slurm", "#!/bin/bash\n") is False
    manager = MagicMock()
    assert open_draft_in_editor({"editor_manager": manager}, "/w/x.slurm", "#!/bin/bash\n") is True
    manager.open_new_window.assert_called_once_with("/w/x.slurm", "#!/bin/bash\n", is_local=False)
