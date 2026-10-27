"""OpenFOAM Case Studio locale-sensitive dialog behavior (W65)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hpc_gui.core.i18n import current_language, load_language, t
from hpc_gui.plugin_engines.openfoam_studio import qt_actions
from hpc_gui.plugin_engines.openfoam_studio.qt_actions import QtCaseManagerActions


@pytest.mark.qt
@pytest.mark.parametrize("language", ("en", "tr"))
def test_snapshot_remote_choice_uses_current_translation(monkeypatch, language):
    previous = current_language()
    opened = []
    choices = []
    try:
        load_language(language)

        def choose_item(_parent, _title, _label, items, *_args):
            choices.extend(items)
            return t("openfoam.remote"), True

        dialogs = SimpleNamespace(
            getItem=choose_item,
            getText=lambda *_args, **_kwargs: ("/case", True),
        )
        monkeypatch.setattr(qt_actions, "QInputDialog", dialogs)
        page = SimpleNamespace(
            session_state={"session": {"files": object()}},
            open_target=lambda path, **kwargs: opened.append((path, kwargs)),
        )

        QtCaseManagerActions(page)._open_snapshot()

        assert choices == [t("openfoam.local"), t("openfoam.remote")]
        assert opened == [("/case", {"remote": True, "read_only": True})]
    finally:
        load_language(previous)
